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

The verdict fails closed. Each of the four captures must exist and hold only
candump frames; the declared scenario (--scenario) must be completed command
by command, each converged (JSON true), with finite stamps and its command and
status frames on the bus; each routed path must carry matched pairs; the UDS
payload line must be a positive 50 03 that also appears as the 0x7E8 frame on
the tester's bus. summary.json carries the verdict and every failure.
"""

from __future__ import annotations

import argparse
import json
import math
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
# DiagnosticSessionControl (0x10) answered positively (0x50) for the extended
# session (0x03) that run_demo.sh requests with `session --id 3`.
UDS_POSITIVE_PREFIX = bytes([0x50, 0x03])

# The command matrix a run must complete, per arm and in order. checks/run_demo.sh
# primes both plants to OFF and then drives exactly this: eight alternating
# values per arm, so every command is a transition. Archives of another shape
# (the historical twelve-command runs) do not pass as this scenario.
SCENARIOS = {
    "alternating-8": {
        "headlamp": [True, False] * 4,
        "wiper": ["FAST", "OFF"] * 4,
    },
}


def finite(value) -> bool:
    """A real, finite number; JSON true is not a timestamp."""
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


FRAME_LINE = re.compile(r"^\s*" + FRAME.pattern + r"\s*$")


def parse(path: Path, problems: list[str] | None = None) -> list[tuple[float, str, int, bytes]]:
    """Read one required capture; every defect is a problem, never an empty list.

    A missing or empty capture would otherwise read as "no forbidden frame", and
    a line that is not a frame (an interface error, the NULs a truncated live
    file leaves) would silently shrink the evidence.
    """
    problems = [] if problems is None else problems
    frames = []
    if not path.is_file():
        problems.append(f"required capture missing: {path.name}")
        return frames
    bad = 0
    for line in path.read_text(errors="replace").splitlines():
        if not line.strip():
            continue
        m = FRAME_LINE.match(line)
        ts = float(m.group(1)) if m else float("nan")
        if not m or not math.isfinite(ts) or int(m.group(4)) != len(m.group(5).split()):
            bad += 1
            continue
        _ts, _iface, arb, _dlc, payload = m.groups()
        frames.append((ts, _iface, int(arb, 16), bytes.fromhex(payload.replace(" ", "").strip())))
    if bad:
        problems.append(f"malformed capture: {path.name} has {bad} line(s) that are not candump -ta frames")
    if not frames:
        problems.append(f"required capture empty: {path.name} holds no frames")
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


HEX_LINE = re.compile(r"^(?:[0-9a-fA-F]{2})+$")


def isotp_single_frame(data: bytes) -> bytes | None:
    """The payload of an ISO-TP single frame, or None for any other frame."""
    if not data or data[0] >> 4 != 0:
        return None
    length = data[0] & 0x0F
    return data[1 : 1 + length] if 0 < length <= len(data) - 1 else None


def evaluate_uds(path: Path, tester_bus, failed: list[str]) -> dict:
    """Judge the diagnostic from its payload bytes, never from text.

    UdsTool prints the raw response payload on a line of its own (positive:
    5003...; negative: 7f10<nrc>) and then a Python object repr whose memory
    address is arbitrary hex: "at 0x7215003c8320" contains 5003. Only the
    payload line is read, and it must also be the 0x7E8 single frame seen on
    the tester's bus, i.e. the answer that actually crossed the gateway.
    """
    result = {"response_payload": None, "bus_response_payload": None, "positive_response": False, "excerpt": []}
    if not path.is_file():
        failed.append(f"UDS output missing: {path.name}")
        return result
    text = path.read_text(errors="replace")
    result["excerpt"] = [ln for ln in text.splitlines() if ln.strip()][-3:]
    payloads = [bytes.fromhex(ln.strip()) for ln in text.splitlines() if HEX_LINE.match(ln.strip())]
    if not payloads:
        failed.append(f"no UDS response payload in {path.name}")
        return result
    payload = payloads[-1]
    result["response_payload"] = payload.hex()
    if payload[:1] == b"\x7f":
        nrc = payload[2] if len(payload) > 2 else None
        failed.append(f"UDS negative response to 0x10 (NRC {'0x%02x' % nrc if nrc is not None else 'missing'})")
        return result
    if payload[:2] != UDS_POSITIVE_PREFIX:
        failed.append(f"UDS response {payload.hex()} is not DiagnosticSessionControl(extended) positive 50 03")
        return result
    bus = [isotp_single_frame(d) for _ts, _if, arb, d in tester_bus if arb == UDS_RESPONSE]
    match = next((b for b in bus if b is not None and b == payload), None)
    if match is None:
        failed.append("no positive 0x7E8 response 50 03 equal to the tool's payload on the tester bus")
        return result
    result["bus_response_payload"] = match.hex()
    result["positive_response"] = True
    return result


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
    p.add_argument("--uds", required=True, help="captured UdsTool output")
    p.add_argument("--out", required=True)
    p.add_argument("--scenario", default="alternating-8", choices=sorted(SCENARIOS),
                   help="the command matrix the driver declared; the verdict counts against it")
    args = p.parse_args()

    failed: list[str] = []
    fl = parse(Path(args.fl), failed)
    rl = parse(Path(args.rl), failed)
    gw_front = parse(Path(args.gw_front), failed)
    gw_rear = parse(Path(args.gw_rear), failed)
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
    per_arm: dict[str, list[tuple[dict, dict]]] = {arm: [] for arm in BYTE}
    for lineno, line in enumerate(Path(args.commands).read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as exc:
            failed.append(f"commands.jsonl line {lineno}: not a JSON record ({exc.msg})")
            continue
        if not isinstance(rec, dict) or rec.get("arm") not in BYTE or "value" not in rec or "on" not in rec:
            failed.append(f"commands.jsonl line {lineno}: not a command record of a known arm")
            continue
        arm = rec["arm"]
        index, mask, on, off = BYTE[arm]
        # The client reports JSON true/false, the record carries the label as a
        # string; compare them as labels or every boolean ON reads as OFF.
        is_on = str(rec["value"]).strip().lower() == str(rec["on"]).strip().lower()
        expected = on if is_on else off
        t0 = rec.get("t0") if finite(rec.get("t0")) else None
        t5 = rec.get("t5") if finite(rec.get("t5")) else None
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
        row = {
            "arm": arm,
            "value": rec["value"],
            "transition": transition,
            # Only a JSON true is a convergence; "false" is a truthy string.
            "converged": rec.get("ok") is True,
            "polls": rec.get("polls"),
            "s1_target_to_bus_ms": round((cmd_ts - t0) * 1000, 3) if cmd_ts and t0 else None,
            "s2_bus_turnaround_ms": round((status_ts - cmd_ts) * 1000, 3) if status_ts and cmd_ts else None,
            "s3_bus_to_app_ms": round((t5 - status_ts) * 1000, 3) if status_ts and t5 else None,
            "total_ms": round((t5 - t0) * 1000, 3) if t5 and t0 and (cmd_ts is not None or not transition) else None,
        }
        commands.append(row)
        per_arm[arm].append((rec, row | {"cmd_ts": cmd_ts, "status_ts": status_ts}))

    # The declared matrix, command by command: every one must be the declared
    # value, converge, carry finite stamps, and show its command and status
    # frames on the commanded zone's bus. One success among failures is a fail.
    for arm, declared in SCENARIOS[args.scenario].items():
        got = per_arm.get(arm, [])
        if len(got) != len(declared):
            failed.append(f"{arm}: {len(got)} of {len(declared)} commands of scenario {args.scenario}")
        for i, ((rec, row), want) in enumerate(zip(got, declared), 1):
            who = f"{arm} command {i}"
            if str(rec["value"]).strip().lower() != str(want).lower():
                failed.append(f"{who}: value {rec['value']!r}, expected {str(want)!r}")
            if rec.get("ok") is not True:
                failed.append(f"{who}: did not converge (ok={rec.get('ok')!r})")
            for field in ("t0", "t5"):
                if not finite(rec.get(field)):
                    failed.append(f"{who}: {field} is not a finite timestamp ({rec.get(field)!r})")
            if finite(rec.get("t0")) and finite(rec.get("t5")) and rec["t5"] < rec["t0"]:
                failed.append(f"{who}: t5 precedes t0")
            if row["cmd_ts"] is None:
                failed.append(f"{who}: no 0x{CMD_ID[arm]:03X} command frame within 300 ms of t0")
            elif row["status_ts"] is None:
                failed.append(f"{who}: no 0x{STATUS_ID[arm]:03X} status frame within 300 ms of the command frame")

    # Each routed path must carry at least one matched pair: zero leaks on a
    # path that carried nothing is not isolation evidence.
    for path_name, metric in routed.items():
        if not metric or metric["n"] < 1:
            failed.append(f"{path_name}: no routed samples")

    uds = evaluate_uds(Path(args.uds), fl, failed)

    if any(leaks.values()):
        failed.append("a frame crossed a boundary the policy denies")

    summary = {
        "scenario": args.scenario,
        "verdict": {"pass": not failed, "failures": failed},
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
    print(f"\nUDS positive response: {uds['positive_response']}")

    if failed:
        print("\nDEMO FAILED: " + "; ".join(failed), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
