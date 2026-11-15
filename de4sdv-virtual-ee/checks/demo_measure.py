#!/usr/bin/env python3
"""Turn one demo run's captures into numbers.

Inputs are the four `candump -ta` files (absolute epoch timestamps, one clock
domain because the whole vehicle is containers on one kernel), the demo's own
command records, and the gateway's shutdown stats.

What it computes, and why each is a separate claim:

  counts    frames per bus per id. The policy is visible on the wire: the
            headlamp command exists on the front bus and on no other, the wiper
            command on the rear bus and on no other.
  route     one-frame latency for the two diagnostic frames (0x7E0 forward,
            0x7E8 back). Their payloads are unique, so a pair is certain.
  periodic  latency for the periodic status frames, matched by payload then in
            time order. Counts are printed next to the numbers because a
            pairing is only as good as the two streams it came from.
  command   t0->t2, t2->t3, t3->t5 and t0->t5 per commanded value, reported as
            median with the sample count, never as a single number.

Nothing here claims T1 or T4: provider receive and provider publish happen
inside kuksa-can-provider and are not instrumented. S1 and S3 contain them.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from pathlib import Path

FRAME = re.compile(r"\((\d+\.\d+)\)\s+(\S+)\s+([0-9A-Fa-f]+)\s+\[(\d+)\]\s+([0-9A-Fa-f ]+)")

CMD_ID = {"headlamp": 0x180, "wiper": 0x280}
STATUS_ID = {"headlamp": 0x181, "wiper": 0x281}
# command byte -> (index, mask, value on, value off) as the DBC defines it
BYTE = {
    "headlamp": (0, 0x01, 0x01, 0x00),
    "wiper": (0, 0xFF, 0x03, 0x00),  # FAST = 3, OFF = 0 per wiper.dbc
}
UDS_REQUEST = 0x7E0
UDS_RESPONSE = 0x7E8


def parse(path: Path) -> list[tuple[float, str, int, bytes]]:
    frames = []
    if not path.exists():
        return frames
    for line in path.read_text(errors="replace").splitlines():
        m = FRAME.search(line)
        if not m:
            continue
        ts, _iface, arb, _dlc, payload = m.groups()
        frames.append((float(ts), _iface, int(arb, 16), bytes.fromhex(payload.replace(" ", "").strip())))
    return frames


def by_id(frames, arb):
    return [f for f in frames if f[2] == arb]


def first_match(frames, arb, index, mask, expected, after, before=None):
    for ts, _iface, _arb, data in frames:
        if _arb != arb or ts < after or len(data) <= index:
            continue
        if before is not None and ts > before:
            return None
        if (data[index] & mask) == (expected & mask):
            return ts
    return None


def match_pairs(src, dst, window=0.020):
    """Pair frames seen on two buses by identical payload, in time order.

    Greedy and first-come: status frames repeat, so the first unconsumed frame
    with the same payload after the source frame is the same frame. A window
    keeps a match from pairing across two periods of the same payload.
    """
    used: set[int] = set()
    deltas = []
    for ts, _iface, _arb, data in src:
        for i, (dts, _dif, _darb, ddata) in enumerate(dst):
            if i in used or dts < ts:
                continue
            if dts - ts > window:
                break
            if ddata == data:
                used.add(i)
                deltas.append(dts - ts)
                break
    return deltas


def stats(values):
    if not values:
        return None
    return {
        "n": len(values),
        "median_ms": round(statistics.median(values) * 1000, 3),
        "min_ms": round(min(values) * 1000, 3),
        "max_ms": round(max(values) * 1000, 3),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--fl", required=True, help="front-left zone bus capture")
    p.add_argument("--rl", required=True, help="rear-left zone bus capture")
    p.add_argument("--gw-front", required=True)
    p.add_argument("--gw-rear", required=True)
    p.add_argument("--commands", required=True, help="JSONL from the demo driver")
    p.add_argument("--uds", help="captured UdsTool output")
    p.add_argument("--out", required=True)
    args = p.parse_args()

    fl = parse(Path(args.fl))
    rl = parse(Path(args.rl))
    gw_front = parse(Path(args.gw_front))
    gw_rear = parse(Path(args.gw_rear))
    buses = {"front-left": fl, "rear-left": rl, "gw-front": gw_front, "gw-rear": gw_rear}

    counts = {}
    for name, frames in buses.items():
        per_id: dict[str, int] = {}
        for _ts, _iface, arb, _data in frames:
            key = f"0x{arb:03X}"
            per_id[key] = per_id.get(key, 0) + 1
        counts[name] = dict(sorted(per_id.items()))

    # The policy as it appears on the wire, not as it was configured. A command
    # belongs to exactly one side of the gateway: the headlamp command exists on
    # the front bus and nowhere on the rear, the wiper command the other way.
    # The diagnostic has no denied direction - the tester injects 0x7E0 on the
    # front bus and the ECU answers 0x7E8 on the rear, both by design.
    leaks = {
        "0x180_on_rear_side": counts["rear-left"].get("0x180", 0) + counts["gw-rear"].get("0x180", 0),
        "0x280_on_front_side": counts["front-left"].get("0x280", 0) + counts["gw-front"].get("0x280", 0),
    }

    routed = {
        "headlamp_status_front_to_rear": stats(match_pairs(by_id(fl, 0x181), by_id(rl, 0x181))),
        "wiper_status_rear_to_front": stats(match_pairs(by_id(rl, 0x281), by_id(fl, 0x281))),
        "uds_request_front_to_rear": stats(match_pairs(by_id(fl, UDS_REQUEST), by_id(rl, UDS_REQUEST), 0.050)),
        "uds_response_rear_to_front": stats(match_pairs(by_id(rl, UDS_RESPONSE), by_id(fl, UDS_RESPONSE), 0.050)),
    }

    commands = []
    last_value: dict[str, object] = {}
    for line in Path(args.commands).read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rec = json.loads(line)
        arm = rec["arm"]
        index, mask, on, off = BYTE[arm]
        # The client reports JSON true/false, the record carries the label as a
        # string; compare them as labels or every boolean ON reads as OFF.
        is_on = str(rec["value"]).strip().lower() == str(rec["on"]).strip().lower()
        expected = on if is_on else off
        t0 = rec.get("t0")
        # A command that does not change the value is not a transition: the
        # provider has nothing new to send, so no frame marks it and any timing
        # built on one would be an artefact of the next command.
        transition = arm not in last_value or last_value[arm] != rec["value"]
        last_value[arm] = rec["value"]
        cmd_ts = status_ts = None
        if t0 is not None and transition:
            cmd_ts = first_match(fl if arm == "headlamp" else rl, CMD_ID[arm], index, mask, expected, t0 - 0.05, t0 + 0.300)
            if cmd_ts is not None:
                status_ts = first_match(fl if arm == "headlamp" else rl, STATUS_ID[arm], 0, 0xFF, expected, cmd_ts, cmd_ts + 0.300)
        commands.append(
            {
                "arm": arm,
                "value": rec["value"],
                "transition": transition,
                "converged": bool(rec.get("ok")),
                "polls": rec.get("polls"),
                "s1_target_to_bus_ms": round((cmd_ts - t0) * 1000, 3) if cmd_ts and t0 else None,
                "s2_bus_turnaround_ms": round((status_ts - cmd_ts) * 1000, 3) if status_ts and cmd_ts else None,
                "s3_bus_to_app_ms": round((rec["t5"] - status_ts) * 1000, 3) if status_ts and rec.get("t5") else None,
                "total_ms": round((rec["t5"] - t0) * 1000, 3)
                if rec.get("t5") and t0 and (cmd_ts is not None or not transition)
                else None,
            }
        )

    uds = None
    if args.uds and Path(args.uds).exists():
        text = Path(args.uds).read_text(errors="replace")
        flat = text.replace(" ", "").replace("\n", "")
        uds = {
            # udsoncan prints the raw payload (5003003201f4) and a decoded
            # PositiveResponse; either is proof the answer crossed the gateway.
            "positive_response": bool(re.search(r"5003|PositiveResponse", flat, re.I)),
            "excerpt": [ln for ln in text.splitlines() if ln.strip()][-3:],
        }

    summary = {
        "claimed_clock": "one host, one kernel CLOCK_REALTIME: candump -ta and the client share it",
        "not_claimed": ["T1 provider receive", "T4 provider publish", "any bus latency from S1 or S3"],
        "frames_per_bus": counts,
        "leaks": leaks,
        "routed": routed,
        "commands": commands,
        "uds": uds,
    }
    Path(args.out).write_text(json.dumps(summary, indent=2) + "\n")

    print(json.dumps({"frames_per_bus": counts, "leaks": leaks, "routed": routed}, indent=2))
    if commands:
        print("\ncommand  value   trans  conv  S1 ms   S2 ms   S3 ms   total ms")
        for c in commands:
            def f(v):
                return "   —  " if v is None else f"{v:7.2f}"
            print(
                f"{c['arm']:8s} {str(c['value']):6s}  {str(c['transition']):5s}  {str(c['converged']):5s} "
                f"{f(c['s1_target_to_bus_ms'])} {f(c['s2_bus_turnaround_ms'])} "
                f"{f(c['s3_bus_to_app_ms'])} {f(c['total_ms'])}"
            )
        print("\nper arm, transitions only (median with the sample count):")
        for arm in ("headlamp", "wiper"):
            rows = [c for c in commands if c["arm"] == arm and c["transition"]]

            def agg(key):
                vals = [c[key] for c in rows if c[key] is not None]
                return f"{statistics.median(vals):.2f} (n={len(vals)})" if vals else "—"

            print(
                f"  {arm:9s} S1 {agg('s1_target_to_bus_ms'):>13s}  S2 {agg('s2_bus_turnaround_ms'):>13s}"
                f"  S3 {agg('s3_bus_to_app_ms'):>13s}  total {agg('total_ms'):>13s}"
            )
    if uds:
        print(f"\nUDS positive response: {uds['positive_response']}")

    failed = []
    if any(leaks.values()):
        failed.append("a frame crossed a boundary the policy denies")
    if not any(c["converged"] for c in commands):
        failed.append("no command converged")
    if uds is not None and not uds["positive_response"]:
        failed.append("no positive UDS response crossed the gateway")
    if failed:
        print("\nDEMO FAILED: " + "; ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
