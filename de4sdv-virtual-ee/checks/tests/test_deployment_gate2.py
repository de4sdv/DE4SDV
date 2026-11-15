"""gate2.py, run for real against the committed demo captures (R9).

Only `podman` and `sudo` are replaced. The `podman exec <zone> candump` stub
replays a committed zone capture from results/20261115T005422Z-657d64c6; the
`sudo nsenter … measure_client.py` stub replays client lines, taken from that
run's commands.jsonl where the client converged. The captures are read, never
edited. This proves the gate's verdict on real captured traffic, not a live run.

Policy since the gateway (gateway/router.py): a zone's status crosses to the
other bus and must be seen there; its command must never be seen there.
"""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parents[1]
EE = CHECKS.parent
RUN = EE / "results" / "20261115T005422Z-657d64c6"
FRONT = RUN / "candump-front-left.log"
REAR = RUN / "candump-rear-left.log"
CLIENT_KEYS = ("path", "value", "t0", "t5", "ok", "polls", "poll_s")

PODMAN_STUB = r'''#!/usr/bin/python3
import os, sys
args = sys.argv[1:]
with open(os.environ["STUB_LOG"], "a") as fh:
    fh.write("podman " + " ".join(args) + "\n")
if args[:1] == ["inspect"]:
    print("4242")
    sys.exit(0)
if args[:1] == ["exec"] and "candump" in args:
    f = os.path.join(os.environ["STUB_CAPTURES"], args[1] + ".log")
    if os.path.exists(f):
        sys.stdout.write(open(f).read())
    sys.exit(0)
sys.exit(0)
'''

SUDO_STUB = r'''#!/usr/bin/python3
import json, os, sys
with open(os.environ["STUB_LOG"], "a") as fh:
    fh.write("sudo " + " ".join(sys.argv[1:]) + "\n")
q = os.environ["STUB_QUEUE"]
lines = open(q).read().splitlines()
n_path = q + ".n"
n = int(open(n_path).read()) if os.path.exists(n_path) else 0
open(n_path, "w").write(str(n + 1))
line = lines[n]
if line == "ERROR":
    print("grpc: connection refused", file=sys.stderr)
    sys.exit(1)
print(line)
sys.exit(0 if json.loads(line)["ok"] else 1)
'''


def demo_commands():
    recs = [json.loads(line) for line in (RUN / "commands.jsonl").read_text().splitlines() if line.strip()]
    return [{k: r[k] for k in CLIENT_KEYS} for r in recs]


def _bench(tmp_path, queue, front=FRONT, rear=REAR):
    stubs = tmp_path / "bin"
    stubs.mkdir()
    for name, body in (("podman", PODMAN_STUB), ("sudo", SUDO_STUB)):
        (stubs / name).write_text(body)
        (stubs / name).chmod(0o755)
    caps = tmp_path / "captures"
    caps.mkdir()
    if front is not None:
        (caps / "vx-zone-fl-payload.log").write_text(Path(front).read_text())
    if rear is not None:
        (caps / "vx-zone-rl-payload.log").write_text(Path(rear).read_text())
    qf = tmp_path / "queue.jsonl"
    qf.write_text("\n".join(q if isinstance(q, str) else json.dumps(q) for q in queue) + "\n")
    return stubs, caps, qf


def run_gate2(tmp_path, scenario, queue, iterations, **caps):
    stubs, captures, qf = _bench(tmp_path, queue, **caps)
    out = tmp_path / "gate2.jsonl"
    env = {k: v for k, v in os.environ.items() if not k.startswith("PYTHON")}
    env.update(
        PATH=f"{stubs}:{os.environ['PATH']}",
        STUB_LOG=str(tmp_path / "calls.log"),
        STUB_CAPTURES=str(captures),
        STUB_QUEUE=str(qf),
        TMPDIR=str(tmp_path),
        PYTHONDONTWRITEBYTECODE="1",
    )
    res = subprocess.run(
        [sys.executable, str(CHECKS / "gate2.py"), "--scenario", scenario,
         "--iterations", str(iterations), "--out", str(out)],
        capture_output=True, text=True, env=env, timeout=120,
    )
    res.records = [json.loads(line) for line in out.read_text().splitlines()] if out.exists() else []
    return res


def baseline_queue():
    c = demo_commands()
    # gate2 order: per iteration headlamp then wiper, ON first
    return [c[0], c[6], c[1], c[7]]


def split(records):
    iso = [r for r in records if r.get("kind") == "isolation"]
    cmds = [r for r in records if r.get("kind") != "isolation"]
    return cmds, iso


def test_routed_status_is_required_and_counted_once_per_capture(tmp_path):
    res = run_gate2(tmp_path, "baseline", baseline_queue(), 2)
    cmds, iso = split(res.records)
    by_arm = {r["arm"]: r for r in iso}
    assert len(iso) == 2 and set(by_arm) == {"headlamp", "wiper"}, res.records
    assert (by_arm["headlamp"]["routed_status_frames"], by_arm["headlamp"]["denied_command_frames"]) == (798, 0)
    assert (by_arm["wiper"]["routed_status_frames"], by_arm["wiper"]["denied_command_frames"]) == (799, 0)
    assert len(cmds) == 4 and not any(r.get("leaks") for r in cmds), cmds
    assert all(r["cmd_seen"] and r["ack_seen"] for r in cmds), cmds
    assert res.returncode == 0, res.stdout + res.stderr


def test_summary_of_the_committed_captures_passes_once_counted(tmp_path):
    res = run_gate2(tmp_path, "baseline", baseline_queue(), 2)
    summary = subprocess.run(
        [sys.executable, str(CHECKS / "summarize_gate2.py"), str(tmp_path / "gate2.jsonl")],
        capture_output=True, text=True, timeout=60,
        env={k: v for k, v in os.environ.items() if not k.startswith("PYTHON")},
    )
    assert summary.returncode == 0, summary.stdout + summary.stderr
    assert "forbidden command frames on the other bus: 0" in summary.stdout
    assert "routed status frames on the other bus: 1597 (required, present in 2/2 captures)" in summary.stdout


def test_forbidden_command_on_the_other_bus_fails(tmp_path):
    rear = tmp_path / "rear-with-leak.log"
    rear.write_text(REAR.read_text() + " (1794704090.500000)  vcan0  180   [8]  01 00 00 00 00 00 00 00\n")
    res = run_gate2(tmp_path, "baseline", baseline_queue(), 2, rear=rear)
    assert res.returncode == 1, res.stdout + res.stderr
    iso = {r["arm"]: r for r in split(res.records)[1]}
    assert iso["headlamp"]["denied_command_frames"] == 1


def test_unexercised_route_is_missing_evidence(tmp_path):
    # the rear capture without the routed headlamp status: zero leaks proves nothing
    rear = tmp_path / "rear-no-route.log"
    rear.write_text("".join(line for line in REAR.read_text().splitlines(True) if "  181  " not in line))
    res = run_gate2(tmp_path, "baseline", baseline_queue(), 2, rear=rear)
    assert res.returncode == 1, res.stdout + res.stderr


def test_no_captures_at_all_fail(tmp_path):
    res = run_gate2(tmp_path, "baseline", baseline_queue(), 2, front=None, rear=None)
    assert res.returncode == 1, res.stdout + res.stderr


def _down(converged):
    c = demo_commands()[0]
    t0 = c["t0"] - 1.0
    return {**c, "t0": t0, "t5": (t0 + 0.07) if converged else None, "ok": converged}


@pytest.mark.parametrize("scenario", ["restart", "linkloss"])
def test_expected_down_passes_when_the_command_does_not_converge(tmp_path, scenario):
    c = demo_commands()
    res = run_gate2(tmp_path, scenario, [_down(False), c[0], c[1]], 2)
    assert res.returncode == 0, res.stdout + res.stderr
    cmds, _ = split(res.records)
    down = [r for r in cmds if r["label"].endswith("-down")]
    assert len(down) == 1 and down[0]["expected"] == "no-converge"


def test_expected_down_fails_when_the_command_converges(tmp_path):
    c = demo_commands()
    res = run_gate2(tmp_path, "restart", [_down(True), c[0], c[1]], 2)
    assert res.returncode == 1, res.stdout + res.stderr


def test_expected_down_without_a_write_is_missing_evidence(tmp_path):
    c = demo_commands()
    res = run_gate2(tmp_path, "restart", ["ERROR", c[0], c[1]], 2)
    assert res.returncode == 1, res.stdout + res.stderr


def test_gate_policy_matches_the_gateway_allow_list():
    sys.path.insert(0, str(CHECKS))
    import gate2

    spec = importlib.util.spec_from_file_location("router_under_test", EE / "gateway" / "router.py")
    router = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(router)
    direction = {"headlamp": "front->rear", "wiper": "rear->front"}
    allowed = set().union(*router.POLICY.values())
    for arm, d in direction.items():
        assert gate2.ROUTED_STATUS[arm] in router.POLICY[d]
        assert gate2.DENIED_COMMAND[arm] not in allowed
