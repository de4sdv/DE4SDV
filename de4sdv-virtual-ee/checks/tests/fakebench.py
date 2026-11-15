#!/usr/bin/env python3
"""A fake testbed for driving checks/run_demo.sh and checks/run_backbone.sh.

Installed as podman, vxedge, sudo, sleep, tcpdump and vxota in a scratch bin
directory, and as the demo's client and UDS interpreters. It keeps its state
under $FAKE_STATE and records every call in $FAKE_STATE/calls. Bus traffic is
synthesised from the commands the client was actually asked to send, so a
capture only holds what the run drove.

Fault switches (environment):
  FAKE_UP_RC            exit code of `vxedge experiment up`
  FAKE_MUTATE_ON_UP     a file appended to during `experiment up` (mid-run change)
  FAKE_CAPTURE_RC       exit code of the background candump captures (default 124)
  FAKE_COPY_FAIL        capture name (demo-gwr ...) whose copy-out fails
  FAKE_PRIME_FAIL       priming commands do not converge
  FAKE_UDS_RC           exit code of the UDS tool
  FAKE_LOGS_FAIL        container whose `podman logs` fails after its first call
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import evidence_fixtures as fx  # noqa: E402

STATE = Path(os.environ.get("FAKE_STATE", "/nonexistent"))
BACKBONE = HERE.parent.parent / "results" / "20261115T022118Z-04ee8739-backbone"
CAPTURE_KEYS = {"demo-fl": "fl", "demo-rl": "rl", "demo-gwf": "gwf", "demo-gwr": "gwr"}


def record(tool: str, argv: list[str]) -> None:
    with (STATE / "calls").open("a") as fh:
        fh.write(json.dumps([tool, *argv]) + "\n")


def clock() -> float:
    """A virtual clock: 1.5 s per command, so windows never overlap."""
    path = STATE / "clock"
    now = float(path.read_text()) if path.exists() else 1794704073.0
    path.write_text(repr(now + 1.5))
    return now


def capturing() -> bool:
    return any(STATE.glob("started-*"))


def podman(argv: list[str]) -> int:
    if not argv:
        return 2
    verb = argv[0]
    if verb == "inspect":
        fmt = argv[argv.index("-f") + 1] if "-f" in argv else ""
        print("4242" if "Pid" in fmt else "running")
        return 0
    if verb in ("container", "start", "stop", "rm", "ps"):
        return 0
    if verb == "logs":
        ctr = argv[-1]
        seen = STATE / f"logs-seen-{ctr}"
        if os.environ.get("FAKE_LOGS_FAIL") == ctr and seen.exists():
            # readiness polling succeeded once; the later collection fails
            print(f"Error: no container with name or ID {ctr}", file=sys.stderr)
            return 125
        seen.write_text("")
        if ctr == "vx-zone-fl-payload":
            for line in (BACKBONE / "provider.jsonl").read_text().splitlines():
                print(f"[someip] {line}")
        elif ctr == "vx-zone-rl-payload":
            for line in (BACKBONE / "client.jsonl").read_text().splitlines():
                print(f"[someip] {line}")
        else:
            print("gateway stats\n  forwarded 1\n")
        return 0
    if verb == "exec":
        ctr, rest = argv[1], argv[2:]
        if rest[:2] == ["sh", "-c"]:
            cmd = rest[2]
            if "-n 1" in cmd:
                print(" (1794704071.283491)  vcan0  281   [8]  00 00 01 00 00 00 00 00")
                return 0
            if "candump -ta" in cmd:
                name = cmd.split("/tmp/")[1].split(".log")[0]
                (STATE / f"started-{name}").write_text("")
                return int(os.environ.get("FAKE_CAPTURE_RC", "124"))
            return 0
        if rest[0] == "cat":
            name = rest[1].split("/tmp/")[1].split(".log")[0]
            if os.environ.get("FAKE_COPY_FAIL") == name:
                print(f"cat: {rest[1]}: No such file or directory", file=sys.stderr)
                return 1
            commands = [json.loads(ln) for ln in (STATE / "driven.jsonl").read_text().splitlines()] \
                if (STATE / "driven.jsonl").exists() else []
            uds_at = float((STATE / "uds_at").read_text()) if (STATE / "uds_at").exists() else None
            caps = fx.captures_for(commands, uds_at)
            sys.stdout.write("\n".join(caps[CAPTURE_KEYS[name]]) + "\n")
            return 0
    return 0


def vxedge(argv: list[str]) -> int:
    if argv[:1] == ["--version"]:
        print("vxedge 0.30.0 (fake)")
        return 0
    if argv[:2] == ["experiment", "up"]:
        target = os.environ.get("FAKE_MUTATE_ON_UP")
        if target:
            with open(target, "a") as fh:
                fh.write("# changed while the run was in flight\n")
        return int(os.environ.get("FAKE_UP_RC", "0"))
    return 0


def sudo(argv: list[str]) -> int:
    if argv[:2] == ["-n", "true"] or argv[:1] == ["chown"]:
        return 0
    if argv[:1] == ["nsenter"]:
        argv = argv[argv.index("--") + 1:]
    os.execvp(argv[0], argv)
    return 127


def tcpdump(argv: list[str]) -> int:
    if "-w" in argv:
        Path(argv[argv.index("-w") + 1]).write_bytes(b"")
    return 0


def client(argv: list[str]) -> int:
    # argv: measure_client.py PATH VALUE TIMEOUT
    path, raw = argv[1], argv[2]
    value = {"true": True, "false": False}.get(raw.lower(), raw)
    prime = not capturing()
    t0 = clock()
    ok = not (prime and os.environ.get("FAKE_PRIME_FAIL"))
    rec = {"path": path, "value": value, "t0": t0, "t5": t0 + 0.07 if ok else None, "ok": ok,
           "polls": 20, "poll_s": 0.002}
    if not prime:
        arm = "headlamp" if "Lights" in path else "wiper"
        with (STATE / "driven.jsonl").open("a") as fh:
            fh.write(json.dumps({**rec, "arm": arm}) + "\n")
    print(json.dumps(rec))
    return 0 if ok else 1


def uds(argv: list[str]) -> int:
    (STATE / "uds_at").write_text(repr(clock()))
    sys.stdout.write(fx.POSITIVE_UDS_TEXT)
    return int(os.environ.get("FAKE_UDS_RC", "0"))


TOOLS = {"podman": podman, "vxedge": vxedge, "sudo": sudo, "tcpdump": tcpdump,
         "sleep": lambda argv: 0, "vxota": lambda argv: 0, "client": client, "uds": uds}


def main() -> int:
    tool, argv = sys.argv[1], sys.argv[2:]
    record(tool, argv)
    return TOOLS[tool](argv)


if __name__ == "__main__":
    sys.exit(main())
