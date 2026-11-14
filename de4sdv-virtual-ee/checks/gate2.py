#!/usr/bin/env python3
"""Gate 2 — the failure matrix, measured.

Runs on the testbed host as root (it needs `podman`, `nsenter` and `tc`) and
drives one scenario per invocation. Every iteration writes one JSON record with
the four stamps it can actually observe:

    t0  app writes the target            (central client, realtime clock)
    t2  command frame on the zone's bus  (candump, same host clock)
    t3  status frame carrying the ACK    (candump)
    t5  app reads the new value          (central client)

T1 (provider receive) and T4 (provider publish) are *not* observable without
instrumenting kuksa-can-provider, so they are not claimed: S1 (t0->t2) and
S3 (t3->t5) contain them by construction and the report says so.

A denied-by-routing result would show zero frames and no reply; a denied-by-
policy result shows frames. The leakage counters make that distinction explicit
instead of inferred.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

VENV = "/home/mrk/kv/bin/python"
CANDUMP_RE = re.compile(r"\((\d+\.\d+)\)\s+vcan0\s+([0-9A-F]+)\s+\[(\d+)\]\s+((?:[0-9A-F]{2} ?)+)")

# scenario arm -> (vss path, "on" value, "off" value, frame id, byte index, mask)
ARMS = {
    "headlamp": (
        "Vehicle.Body.Lights.Beam.Low.IsOn",
        "true",
        "false",
        0x180,
        0,
        0x01,
    ),
    "wiper": (
        "Vehicle.Body.Windshield.Front.Wiping.Mode",
        "FAST",
        "OFF",
        0x280,
        0,
        0xFF,
    ),
}
STATUS_ID = {"headlamp": 0x181, "wiper": 0x281}
ZONE = {"headlamp": "vx-zone-fl-payload", "wiper": "vx-zone-rl-payload"}
OTHER = {"headlamp": "vx-zone-rl-payload", "wiper": "vx-zone-fl-payload"}


def sh(cmd: str, timeout: int = 60) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)


def hpc_pid() -> str:
    out = sh("podman inspect -f '{{.State.Pid}}' vx-hpc1-payload").stdout.strip()
    if not out.isdigit():
        sys.exit("central node container is not running")
    return out


def parse_candump(path: Path) -> list[tuple[float, int, bytes]]:
    frames = []
    if not path.exists():
        return frames
    for line in path.read_text(errors="replace").splitlines():
        m = CANDUMP_RE.search(line)
        if not m:
            continue
        ts, arb, _dlc, payload = m.groups()
        frames.append((float(ts), int(arb, 16), bytes.fromhex(payload.replace(" ", ""))))
    return frames


def first_frame(frames, arb, byte_index, expected, t_after, mask=0xFF):
    for ts, frame_id, data in frames:
        if frame_id != arb or ts < t_after or len(data) <= byte_index:
            continue
        if (data[byte_index] & mask) == (expected & mask):
            return ts
    return None


def run_client(pid: str, path: str, value: str, timeout: float = 3.0) -> dict:
    # the harness runs as the image-store owner; nsenter needs root, which is
    # passwordless for this user. Running the whole script as root would look at
    # root's empty Podman store and see no containers at all.
    cmd = f"sudo nsenter -n -t {pid} -- {VENV} /opt/ee/measure_client.py {path} {value} {timeout}"
    res = sh(cmd, timeout=int(timeout) + 15)
    line = res.stdout.strip().splitlines()[-1] if res.stdout.strip() else ""
    try:
        return json.loads(line)
    except Exception:
        return {"ok": False, "error": (res.stderr or res.stdout)[-200:], "t0": None, "t5": None}


def measure_arm(pid, arm, value, expect_byte, frames, label, rep, idx, leaks):
    rec = run_client(pid, ARMS[arm][0], value)
    if rec.get("t0") is None:
        rec.update(arm=arm, label=label, rep=rep, idx=idx, scenario=None, leaks=leaks)
        return rec
    t2 = first_frame(frames, ARMS[arm][3], ARMS[arm][4], expect_byte, rec["t0"] - 0.05)
    t3 = first_frame(frames, STATUS_ID[arm], 0, expect_byte, t2 or rec["t0"] - 0.05)
    t5 = rec.get("t5")
    rec.update(
        arm=arm,
        label=label,
        rep=rep,
        idx=idx,
        t2=t2,
        t3=t3,
        s1=(t2 - rec["t0"]) if t2 else None,
        s2=(t3 - t2) if (t2 and t3) else None,
        s3=(t5 - t3) if (t3 and t5) else None,
        total=(t5 - rec["t0"]) if t5 else None,
        cmd_seen=t2 is not None,
        ack_seen=t3 is not None,
        leaks=leaks,
    )
    return rec


def candump(container: str, seconds: int, out: Path) -> subprocess.Popen:
    return subprocess.Popen(
        f"timeout {seconds} podman exec {container} candump -ta vcan0",
        shell=True,
        stdout=out.open("w"),
        stderr=subprocess.DEVNULL,
    )


def scenario_baseline(pid, reps, per_arm):
    """Both arms, no interference. The reference numbers."""
    return None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenario", required=True,
                    choices=["baseline", "impairment", "concurrency", "restart", "linkloss"])
    ap.add_argument("--rep", type=int, default=1)
    ap.add_argument("--iterations", type=int, default=8)
    ap.add_argument("--out", default="/tmp/gate2.jsonl")
    args = ap.parse_args()

    pid = hpc_pid()
    seconds = 30 + args.iterations * 6
    tmpdir = Path(tempfile.mkdtemp(prefix="gate2-"))
    taps = {}
    for arm in ARMS:
        taps[arm] = (tmpdir / f"{arm}.candump", candump(ZONE[arm], seconds, tmpdir / f"{arm}.candump"))
        # the other zone's bus is tapped too: leakage is evidence, not assumption
        taps[f"{arm}_other"] = (tmpdir / f"{arm}_other.candump", candump(OTHER[arm], seconds, tmpdir / f"{arm}_other.candump"))

    records = []
    try:
        time.sleep(2)
        if args.scenario == "impairment":
            for arm in ARMS:
                sh(f"podman exec {ZONE[arm]} tc qdisc add dev eth0 root netem delay 20ms 5ms loss 1%")

        if args.scenario in ("baseline", "impairment"):
            for i in range(args.iterations):
                for arm in ARMS:
                    on = i % 2 == 0
                    value = ARMS[arm][1] if on else ARMS[arm][2]
                    expect = 1 if (arm == "headlamp" and on) else (3 if (arm == "wiper" and on) else 0)
                    records.append(measure_arm(pid, arm, value, expect, [], args.scenario, args.rep, i, {}))

        elif args.scenario == "concurrency":
            # both ECUs commanded at the same instant, twice per iteration
            for i in range(args.iterations):
                on = i % 2 == 0
                procs = []
                for arm in ARMS:
                    value = ARMS[arm][1] if on else ARMS[arm][2]
                    procs.append(
                        (
                            arm,
                            subprocess.Popen(
                                f"sudo nsenter -n -t {pid} -- {VENV} /opt/ee/measure_client.py {ARMS[arm][0]} {value} 3",
                                shell=True, stdout=subprocess.PIPE, text=True,
                            ),
                        )
                    )
                for arm, p in procs:
                    out, _ = p.communicate(timeout=30)
                    try:
                        rec = json.loads(out.strip().splitlines()[-1])
                    except Exception:
                        rec = {"ok": False, "t0": None}
                    expect = 1 if (arm == "headlamp" and on) else (3 if (arm == "wiper" and on) else 0)
                    rec.update(arm=arm, label=args.scenario, rep=args.rep, idx=i, leaks={})
                    records.append(rec)

        elif args.scenario == "restart":
            sh("podman stop -t 2 vx-zone-fl-payload")
            dead = measure_arm(pid, "headlamp", "true", 1, [], "restart-down", args.rep, 0, {})
            records.append(dead)
            sh("podman start vx-zone-fl-payload")
            time.sleep(6)
            for i in range(args.iterations):
                on = i % 2 == 0
                value = ARMS["headlamp"][1] if on else ARMS["headlamp"][2]
                records.append(measure_arm(pid, "headlamp", value, 1 if on else 0, [], "restart-up", args.rep, i, {}))

        elif args.scenario == "linkloss":
            sh(f"podman exec {ZONE['headlamp']} ip link set eth0 down")
            lost = measure_arm(pid, "headlamp", "true", 1, [], "linkloss-down", args.rep, 0, {})
            records.append(lost)
            sh(f"podman exec {ZONE['headlamp']} ip link set eth0 up")
            time.sleep(6)
            for i in range(args.iterations):
                on = i % 2 == 0
                value = ARMS["headlamp"][1] if on else ARMS["headlamp"][2]
                records.append(measure_arm(pid, "headlamp", value, 1 if on else 0, [], "linkloss-up", args.rep, i, {}))
    finally:
        for arm in ARMS:
            sh(f"podman exec {ZONE[arm]} tc qdisc del dev eth0 root 2>/dev/null || true")
            for key in (arm, f"{arm}_other"):
                p = taps.get(key)
                if p:
                    p[1].terminate()
        time.sleep(1)

    frames = {arm: parse_candump(taps[arm][0]) for arm in ARMS}
    other = {arm: parse_candump(taps[f"{arm}_other"][0]) for arm in ARMS}

    # re-correlate now that the captures are complete
    for rec in records:
        arm = rec.get("arm")
        if not arm or not rec.get("t0"):
            continue
        expect = {"headlamp": 0x180, "wiper": 0x280}[arm]
        idx = ARMS[arm][4]
        # the client reports a JSON bool for the lamps and a label for the wiper
        v = rec.get("value")
        off = v is False or v == "OFF" or v == 0
        expect_byte = 0 if off else (1 if arm == "headlamp" else 3)
        t2 = first_frame(frames[arm], expect, idx, expect_byte, rec["t0"] - 0.05)
        t3 = first_frame(frames[arm], STATUS_ID[arm], 0, expect_byte, t2 or rec["t0"] - 0.05)
        rec["t2"], rec["t3"] = t2, t3
        rec["s1"] = (t2 - rec["t0"]) if t2 else None
        rec["s2"] = (t3 - t2) if (t2 and t3) else None
        rec["s3"] = (rec["t5"] - t3) if (t3 and rec.get("t5")) else None
        rec["total"] = (rec["t5"] - rec["t0"]) if rec.get("t5") else None
        rec["cmd_seen"], rec["ack_seen"] = t2 is not None, t3 is not None
        # Only this ECU's frame ids on the other zone's bus count as leakage.
        # The other bus constantly carries its own status frames, so counting
        # every known id there would report thousands of false positives.
        own_ids = {0x180, 0x181} if arm == "headlamp" else {0x280, 0x281}
        rec["leaks"] = {
            "other_bus_frames_of_this_ecu": sum(1 for _, fid, _ in other[arm] if fid in own_ids),
        }
        # A steady state can put a matching frame on the bus with no new command
        # behind it, so frame presence is not evidence in the down-state records.
        rec["frame_presence_is_evidence"] = bool(rec.get("ok"))

    with open(args.out, "a") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")

    ok = sum(1 for r in records if r.get("ok"))
    print(f"{args.scenario} rep{args.rep}: {ok}/{len(records)} converged -> {args.out}")
    return 0 if ok == len(records) else 1


if __name__ == "__main__":
    sys.exit(main())
