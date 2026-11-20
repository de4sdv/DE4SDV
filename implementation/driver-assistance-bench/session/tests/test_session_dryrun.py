"""Dry runs of the session orchestrator da_session.sh against a stateful fake gcloud.

Every test runs the real script with --dry-run; the fake (fake_gcloud.py) keeps the VMs' states and logs each call.
The expected orders and outcomes come from the brief's start and stop rules, not from the script.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import signal
import subprocess
import tarfile
import time
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SESSION = HERE.parent / "da_session.sh"
FAKE = HERE / "fake_gcloud.py"
STUBS = HERE / "stubs"

G4 = "de4sdv-probe-g4-carla"
L4 = "de4sdv-probe-da8-carla"
GH = "de4sdv-aaos-build"
VMS = (G4, L4, GH)

FAST = {
    "DA_T_PREEMPT_CHECK_S": "0.3", "DA_T_ROUND_PAUSE_S": "0.1", "DA_T_SSH_PAUSE_S": "0.1", "DA_T_POLL_S": "0.1",
    "DA_T_WATCH_S": "0.2", "DA_T_STOP_POLL_S": "0.1", "DA_T_RUNNING_WAIT_S": "1", "DA_T_SSH_TRIES": "3",
}
# The S-CORE side's entries are another lane's (stubs honoring session/README.md "Entry-point contracts"); the
# world side's and the guest host's entries are the real ones in the kit (the fake gcloud answers for the host).
STUB_ENTRIES = {
    "ENTRY_SCORE_P10_1": "extra/p10_1_check.sh", "ENTRY_SCORE_START": "extra/start_score_side.sh",
    "ENTRY_SCORE_STOP": "extra/stop_score_side.sh", "ENTRY_SCORE_INJECT": "extra/inject_warning_requests.sh",
    "DA_MAKE_H": str(STUBS / "make_h.sh"),
}
UPSTREAM = ("Calibration/checkerboard-bw-4x4.png", "Calibration/calc_front_camera_homography.py",
            "VisionPilot/scripts/find_homography_C_matrix.py")


FAKE_GIT = """#!/bin/bash
# fake git of the dry runs: serves `git -C <stand-in clone> cat-file -e|show <pin>:<path>` from plain files, so
# the tests need no git (the GCC 13 image has none); every other call goes to the real git, if there is one
if [ "$1" = -C ] && [ "$2" = "$FAKE_VP_DIR" ]; then
  case "$3" in cat-file) spec=$5 ;; show) spec=$4 ;; *) exit 1 ;; esac
  pin=${spec%%:*}; path=${spec#*:}
  [ "$pin" = "$FAKE_VP_PIN" ] && [ -f "$FAKE_VP_DIR/$path" ] || exit 128
  [ "$3" = show ] && cat "$FAKE_VP_DIR/$path"
  exit 0
fi
real=$(PATH=${PATH#*:} command -v git) || exit 1
exec "$real" "$@"
"""


@pytest.fixture(scope="session")
def vp_clone(tmp_path_factory) -> tuple[Path, str]:
    """A stand-in VisionPilot clone at a stand-in pin: the three upstream files the session takes from the pin."""
    d = tmp_path_factory.mktemp("vp")
    for i, rel in enumerate(UPSTREAM):
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        (d / rel).write_bytes(b"stub %d of %s\n" % (i, rel.encode()))
    bin_dir = tmp_path_factory.mktemp("bin")
    (bin_dir / "git").write_text(FAKE_GIT)
    (bin_dir / "git").chmod(0o755)
    return d, "5" * 40, bin_dir


@pytest.fixture(autouse=True)
def _vp_env(vp_clone, monkeypatch) -> None:
    d, pin, bin_dir = vp_clone
    monkeypatch.setenv("VP_CLONE", str(d))
    monkeypatch.setenv("VP_PIN", pin)
    monkeypatch.setenv("FAKE_VP_DIR", str(d))
    monkeypatch.setenv("FAKE_VP_PIN", pin)
    monkeypatch.setenv("PATH", f"{bin_dir}:{os.environ['PATH']}")


class Run:
    def __init__(self, tmp: Path, proc: subprocess.CompletedProcess | None = None, rc: int | None = None,
                 stdout: str = ""):
        self.tmp = tmp
        self.rc = proc.returncode if proc is not None else rc
        self.stdout = proc.stdout if proc is not None else stdout
        self.calls = [json.loads(line)[1:] for line in (tmp / "fake" / "calls.log").read_text().splitlines()] \
            if (tmp / "fake" / "calls.log").exists() else []
        incoming = list((tmp / "ev").glob("incoming_*"))
        self.incoming = incoming[0] if incoming else None
        log = self.incoming / "session.log" if self.incoming else None
        self.log = log.read_text() if log is not None and log.exists() else ""
        state = tmp / "fake" / "state.json"
        self.state = json.loads(state.read_text())["vm"] if state.exists() else {}

    def index(self, pred) -> list[int]:
        return [i for i, c in enumerate(self.calls) if pred(c)]

    def starts(self, vm: str) -> list[int]:
        return self.index(lambda c: c[2:5] == ["compute", "instances", "start"] and c[5] == vm)

    def stops(self, vm: str) -> list[int]:
        return self.index(lambda c: c[2:5] == ["compute", "instances", "stop"] and c[5] == vm)

    def ssh(self, vm: str, needle: str) -> list[int]:
        return self.index(lambda c: c[2:4] == ["compute", "ssh"] and c[4] == vm and any(needle in a for a in c))

    def guest_stops(self) -> list[int]:
        """The guests' stop calls (guest_stop.sh), not the safety net's arming that names it."""
        return [i for i in self.ssh(GH, "guest_stop.sh") if not any("safety_net.sh" in a for a in self.calls[i])]

    def command(self, i: int) -> str:
        c = self.calls[i]
        return c[c.index("--command") + 1] if "--command" in c else ""

    def sequence(self) -> list[str]:
        lines = [line for line in self.log.splitlines() if " SEQUENCE " in line]
        assert lines, self.log
        return lines[-1].split(" SEQUENCE ", 1)[1].split()


# the per-session settings of the remote entries (da_session.sh REMOTE_ENV_*): a test sets them only on purpose
REMOTE_ENV = ("UNIT_SOURCE", "UNIT_REGISTERED_RE", "UNIT_NEGATION_RE", "BROKER_ERROR_RE", "UNIT_WAIT_S", "B12_DIR", "VERIFY_WAIT_S",
              "ADB_TIMEOUT_S", "UP_TIMEOUT_S", "CLOCK_READS", "CLOCK_MAX_OFFSET_S", "START_WAIT_S", "APP_SUBSCRIBE_WAIT_S",
              "DA_P10_1_CARLA_HOST",
              "GATEWAYD_RX_REGEX", "DA_P10_1_LATE_WAIT_S", "DA_P10_1_CUDA_RUNS", "DA_P10_1_ALIVE_HOLD_S",
              "DA_P10_1_STALL_HOLD_S", "DA_P10_1_SUPERVISED_WAIT_S")


def env_for(tmp: Path, **extra: str) -> dict[str, str]:
    (tmp / "fake").mkdir(parents=True, exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k not in REMOTE_ENV}
    env.update(FAKE_DIR=str(tmp / "fake"), DA_GCLOUD=str(FAKE), TMPDIR=str(tmp), **FAST, **STUB_ENTRIES)
    env.update(extra)
    return env


def args_for(tmp: Path, kind: str, *more: str) -> list[str]:
    return ["bash", str(SESSION), "--kind", kind, "--dry-run", "--evidence-root", str(tmp / "ev"),
            "--kit-from-worktree", "--kit-extra", str(STUBS), "--session-id", "T", *more]


def run(tmp: Path, kind: str, *more: str, timeout: float = 120, **extra: str) -> Run:
    # the session in its own process group, which a time-out ends whole: a session SIGKILLed alone would leave its
    # cost watchdog behind (R5)
    p = subprocess.Popen(args_for(tmp, kind, *more), env=env_for(tmp, **extra), stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        raise
    return Run(tmp, rc=p.returncode, stdout=out)


def popen(tmp: Path, kind: str, *more: str, **extra: str) -> subprocess.Popen:
    """The session in the background, in its own process group (as a terminal runs it): signals go to the group."""
    return subprocess.Popen(args_for(tmp, kind, *more), env=env_for(tmp, **extra), stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, start_new_session=True)


def wait_for_call(tmp: Path, pred, timeout: float = 60) -> None:
    calls = tmp / "fake" / "calls.log"
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if calls.exists() and any(pred(json.loads(line)[1:]) for line in calls.read_text().splitlines()):
            return
        time.sleep(0.05)
    raise AssertionError("call not seen")


def finish(tmp: Path, p: subprocess.Popen, timeout: float = 90) -> Run:
    try:
        out, _ = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        out, _ = p.communicate()
    return Run(tmp, rc=p.returncode, stdout=out)


def assert_invariants(r: Run) -> None:
    # nothing is ever created or deleted, and every VM ends stopped
    assert not r.index(lambda c: "delete" in c or "create" in c)
    assert all(st == "TERMINATED" for st in r.state.values()), r.state
    # every VM that got a start call got a stop call after it
    for vm in VMS:
        if r.starts(vm):
            assert r.stops(vm) and r.stops(vm)[-1] > r.starts(vm)[-1], vm


def test_p10_1_starts_the_simulator_host_first_and_runs_the_check_while_the_world_ticks(tmp_path: Path) -> None:
    # lead decision of 2026-11-19, part 2: p10-1 also takes the simulator host, so C1-C4 run against a ticking world
    r = run(tmp_path, "p10-1")
    assert r.rc == 0, r.stdout + r.log
    assert len(r.starts(G4)) == 1 and len(r.starts(L4)) == 1 and not r.starts(GH) and not r.stops(GH)
    assert r.starts(G4)[0] < r.starts(L4)[0]
    # the world ticks from the go file on until the release file: the check runs in between, and the release comes
    # only after it ended (the check stops its own Launch Manager start while the world still ticks)
    go, step = r.ssh(G4, "world_p10_1/go"), r.ssh(L4, "host_step.sh start p10_1")
    ends = [i for i in r.ssh(L4, "host_step.sh status p10_1")]
    release = r.ssh(G4, "world_p10_1/release")
    assert go and step and ends and release and go[0] < step[0] < ends[-1] < release[0]
    assert r.starts(L4)[0] < step[0] < r.stops(L4)[0]
    assert_invariants(r)
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["exit_code"] == 0 and rec["started"] == ["sim", "score"] and rec["kind"] == "p10-1"
    assert rec["fetched"] == ["sim", "score"]
    assert (r.incoming / "score" / "out" / "session_id").read_text().strip() == "T"


def test_p10_1_gives_the_check_the_simulator_hosts_address_from_gcloud_never_the_callers(tmp_path: Path) -> None:
    # DA_P10_1_CARLA_HOST comes from the session's own simulator host (hosts.env's VM, its IP read from gcloud),
    # never from the caller's environment
    r = run(tmp_path, "p10-1", FAKE_IP=f"{G4}:10.10.0.7", DA_P10_1_CARLA_HOST="192.0.2.99")
    assert r.rc == 0, r.log
    (step,) = [r.command(i) for i in r.ssh(L4, "host_step.sh start p10_1")]
    assert step.endswith("host_step.sh start p10_1 -- env DA_P10_1_CARLA_HOST=10.10.0.7 bash extra/p10_1_check.sh "
                         "$HOME/da-kit/T/out/p10_1"), step
    assert not any("192.0.2.99" in a for c in r.calls for a in c)
    assert json.loads((r.incoming / "session.json").read_text())["internal_ips_from_gcloud"]["sim"] == "10.10.0.7"


def test_p10_1_refuses_the_carla_host_as_a_remote_setting(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", "--remote-env", "DA_P10_1_CARLA_HOST=192.0.2.99")
    assert r.rc == 2 and "not on the allow-list" in r.stdout and not r.calls, r.stdout


def test_p10_1_port_test_is_the_first_cross_host_step_and_logs_each_port(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1")
    assert r.rc == 0, r.log
    (pt,) = r.index(lambda c: c[2:4] == ["compute", "ssh"] and c[4] == L4 and "/dev/tcp/" in " ".join(c))
    cmd = r.command(pt)
    for port in ("2000", "2001", "2002"):
        assert port in cmd
    assert "timeout 5 bash -c" in cmd and "10.10.0.2" in cmd       # bounded, to the address from gcloud
    assert r.ssh(G4, "host_step.sh status sim_setup")[-1] < pt < r.ssh(G4, "host_step.sh start warmup")[0]
    assert ("PORT TEST from de4sdv-probe-da8-carla to the simulator host 10.10.0.2: tcp 2000 open, tcp 2001 open, "
            "tcp 2002 open") in r.log


@pytest.mark.parametrize("closed, seen", [("2000", "tcp 2000 closed"), ("2002", "tcp 2002 closed"),
                                          ("*", "tcp 2000 no answer")])
def test_p10_1_a_closed_carla_port_ends_the_session_before_any_launch_manager_start(tmp_path: Path, closed: str,
                                                                                    seen: str) -> None:
    # "*": the port test's SSH call answers nothing at all (a time-out, say): no port counts as open
    r = run(tmp_path, "p10-1", FAKE_PORT_CLOSED=closed)
    assert r.rc == 5, r.log
    assert seen in r.log and "PORT TEST FAILED" in r.log
    assert "no Launch Manager start" in r.log
    assert not r.ssh(L4, "host_step.sh start p10_1") and not r.ssh(G4, "host_step.sh start world_p10_1")
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["failed_step"] == "port_test" and rec["exit_code"] == 5
    assert_invariants(r)


def test_p10_1_world_keeps_ticking_for_as_long_as_the_check_may_run(tmp_path: Path) -> None:
    # after run_end.json the world side holds (ticks) until the release file or RELEASE_WAIT_S: that hold must cover
    # the check's own bound (T_P10_1), or the world would stop ticking under the check's part 3
    r = run(tmp_path, "p10-1")
    assert r.rc == 0, r.log
    (cmd,) = [r.command(i) for i in r.ssh(G4, "host_step.sh start world_p10_1")]
    m = re.search(r"RELEASE_WAIT_S=(\d+) ", cmd)
    assert m and int(m.group(1)) > 2400, cmd   # T_P10_1 2400 s (review V5 of 58f0039c)
    assert cmd.endswith("run_scenario.sh $HOME/da-kit/T/out/world_p10_1 SC-DRIVING-012 20kmh"), cmd
    assert not r.ssh(G4, "host_step.sh start rec_")                  # no recording: p10-1 judges no driving


@pytest.mark.parametrize("entry", ["ENTRY_SIM_SETUP", "ENTRY_SIM_WARMUP", "ENTRY_SIM_RUN"])
def test_p10_1_checks_the_simulator_hosts_entries_before_any_start(tmp_path: Path, entry: str) -> None:
    r = run(tmp_path, "p10-1", **{entry: "extra/does_not_exist.sh"})
    assert r.rc == 2 and "entry points not ready in the kit" in r.log, r.log
    assert not r.starts(G4) and not r.starts(L4)


def test_p10_1_cap_defaults_to_3_50_eur_for_both_hosts() -> None:
    assert _hosts_env("CAP_EUR_P10_1") == ["3.50"]


def test_p10_3_starts_score_then_guest_and_stops_guests_before_their_host(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host")
    assert r.rc == 0, r.stdout + r.log
    assert r.starts(L4)[0] < r.starts(GH)[0] and not r.starts(G4)
    cvd = r.guest_stops()
    assert cvd and cvd[0] < r.stops(GH)[0]
    # the window: clock set, capture started, injection on the S-CORE host, capture stopped
    order = [r.ssh(GH, "start ivi_clock")[0], r.ssh(GH, "start capture")[0], r.ssh(L4, "start inject")[0],
             r.ssh(GH, "start capture_stop")[0]]
    assert order == sorted(order)
    assert_invariants(r)


def test_p10_2_starts_g4_first_and_checks_it_still_runs_before_the_l4(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host")
    assert r.rc == 0, r.stdout + r.log
    g4, l4, gh = r.starts(G4)[0], r.starts(L4)[0], r.starts(GH)[0]
    assert g4 < l4 < gh
    reads = r.index(lambda c: c[2:5] == ["compute", "instances", "describe"] and c[5] == G4
                    and "--format=value(status)" in c)
    assert len([i for i in reads if g4 < i < l4]) >= 2       # RUNNING, then RUNNING again after the check
    assert "still RUNNING after 0.3 s" in r.log
    # the recorded run: recorder started before the scenario run, capture stopped after it
    rec, scen, cap_stop = r.ssh(G4, "start rec_run1")[0], r.ssh(G4, "start world_run1")[0], \
        r.ssh(GH, "start capture_stop_run1")[0]
    assert rec < scen < cap_stop
    assert r.ssh(G4, "start rec_warmup")[0] < r.ssh(G4, "start warmup")[0] < rec
    assert r.guest_stops()[0] < r.stops(GH)[0]
    assert_invariants(r)


def test_p10_2_preempted_g4_is_started_again_before_the_l4(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_PREEMPT=f"{G4}:2")
    assert r.rc == 0, r.stdout + r.log
    assert len(r.starts(G4)) == 2
    assert r.starts(G4)[1] < r.starts(L4)[0]
    assert "(preempted)" in r.log
    assert_invariants(r)


def test_capacity_rounds_retry_until_the_start_works(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_START=f"{L4}:STOCKOUT|POOL|OK")
    assert r.rc == 0, r.log
    assert len(r.starts(L4)) == 3
    assert r.log.count("no capacity") == 2
    assert_invariants(r)


def test_quota_on_the_l4_stops_the_g4_and_never_starts_the_guest_host(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_START=f"{L4}:QUOTA")
    assert r.rc == 6
    assert len(r.starts(L4)) == 1                            # no retry on a quota error
    assert r.stops(G4) and not r.starts(GH) and not r.stops(GH)
    assert "Limit" not in r.log                              # quota limits are never logged
    assert_invariants(r)


def test_a_failed_step_stops_every_started_vm_guests_first(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_FAIL_STEP="score_start_calib_steer")
    assert r.rc == 5
    assert "step score_start_calib_steer failed" in r.log
    for vm in VMS:
        assert r.stops(vm)
    assert r.guest_stops()[0] < r.stops(GH)[0]
    # nothing after the failed step but the end of the world side already started (review V3 of 58f0039c)
    assert [r.command(i) for i in r.ssh(G4, "touch")] == [
        "touch $HOME/da-kit/T/out/world_calib_steer/release; bash $HOME/da-kit/T/bench/session/remote/host_step.sh "
        "signal world_calib_steer TERM"]
    assert not r.ssh(G4, "world_run1")
    assert r.ssh(L4, "host_step.sh pack")                    # the evidence so far is fetched
    assert json.loads((r.incoming / "session.json").read_text())["failed_step"] == "score_start_calib_steer"
    assert_invariants(r)


def test_the_cost_cap_ends_the_session_and_stops_the_vm(tmp_path: Path) -> None:
    t0 = time.monotonic()
    r = run(tmp_path, "p10-1", "--cap-eur", "2", SCORE_EUR_H="3600", FAKE_HANG_STEP="p10_1:30")
    assert r.rc == 10, r.log
    assert time.monotonic() - t0 < 25                        # ended by the cap, not by the 30 s step
    assert "COST CAP reached" in r.log
    assert "COST CAP reached" in (r.incoming / "cost.log").read_text()
    assert_invariants(r)


def test_sigterm_mid_session_stops_the_started_vms(tmp_path: Path) -> None:
    p = subprocess.Popen(args_for(tmp_path, "p10-3", "--owner-ok-guest-host"),
                         env=env_for(tmp_path, FAKE_HANG_STEP="inject:30"), stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    calls = tmp_path / "fake" / "calls.log"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline and not (calls.exists() and "start inject" in calls.read_text()):
        time.sleep(0.1)
    time.sleep(0.5)
    p.send_signal(signal.SIGTERM)
    out, _ = p.communicate(timeout=60)
    r = Run(tmp_path, rc=p.returncode, stdout=out)
    assert r.rc == 143, r.log
    assert "signal TERM" in r.log
    assert r.guest_stops()[0] < r.stops(GH)[0]
    assert_invariants(r)


def _is_guest_stop(c: list[str]) -> bool:
    return c[2:4] == ["compute", "ssh"] and any("guest_stop.sh" in a for a in c) and \
        not any("safety_net.sh" in a for a in c)


@pytest.mark.parametrize("sig, rc", [(signal.SIGINT, 130), (signal.SIGHUP, 129), (signal.SIGTERM, 143)])
def test_a_second_signal_during_the_exit_trap_does_not_end_it(tmp_path: Path, sig, rc: int) -> None:
    # R1: a terminal's Ctrl-C (or a hangup) goes to the whole process group; a second one while the trap stops the
    # guests must not end the trap before the guest host's stop, SESSION_END and session.json
    p = popen(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_HANG_STEP="inject:30", FAKE_SLOW_GUEST_STOP="3")
    wait_for_call(tmp_path, lambda c: any("start inject" in a for a in c))
    time.sleep(0.5)
    os.killpg(p.pid, sig)
    wait_for_call(tmp_path, _is_guest_stop)
    time.sleep(0.3)
    os.killpg(p.pid, sig)
    r = finish(tmp_path, p)
    assert r.rc == rc, r.log
    assert f"signal {sig.name[3:]}" in r.log and f"SESSION_END T rc={rc}" in r.log
    assert (r.incoming / "session.json").exists()
    assert r.guest_stops()[0] < r.stops(GH)[0]
    assert_invariants(r)


@pytest.mark.parametrize("flakes, rc", [("1", 0), ("99", 11)])
def test_a_failed_status_read_never_stops_the_guest_host_before_its_guests(tmp_path: Path, flakes: str,
                                                                           rc: int) -> None:
    # R2: a status read of the guest host that fails in the trap (once, or every time) is no "no guests": the
    # guests' stop runs, and the host stops only after this session's crosvm count of 0
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_DESCRIBE_FLAKE=f"{GH}:{flakes}", DA_T_STOP_TRIES="3")
    assert r.rc == rc, r.log
    assert "no guest can run there" not in r.log
    stops = r.guest_stops()
    assert stops and stops[0] < r.ssh(GH, "pgrep -c -x crosvm")[0] < r.stops(GH)[0]
    assert r.state[GH] == "TERMINATED"


def test_a_broken_stdout_neither_ends_the_session_nor_empties_its_log(tmp_path: Path) -> None:
    # R3: the README's outer `| tee` killed with its terminal: the reader of the session's stdout goes away
    p = popen(tmp_path, "p10-1")
    for _ in range(3):
        p.stdout.readline()
    p.stdout.close()
    p.wait(timeout=120)
    r = Run(tmp_path, rc=p.returncode)
    assert r.rc == 0, r.log
    assert "session steps done" in r.log and "SESSION_END T rc=0" in r.log
    assert json.loads((r.incoming / "session.json").read_text())["exit_code"] == 0
    assert_invariants(r)


def test_a_vm_that_does_not_stop_is_stopped_again_and_overrides_every_exit_code(tmp_path: Path) -> None:
    # R4: a failed step (exit 5) with a VM still running after its stop exits 11, names the VM last, and records it
    r = run(tmp_path, "p10-1", FAKE_STEP_RC="p10_1:2", FAKE_NO_STOP=L4, DA_T_STOP_TRIES="7",
            DA_T_STOP_AGAIN_EVERY="3")
    assert r.rc == 11, r.log
    assert len(r.stops(L4)) == 3                             # the first stop, then again at polls 3 and 6
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["exit_code"] == 11 and rec["exit_code_without_left_running"] == 5 and rec["failed_step"] == "p10_1"
    assert rec["left_running"] == [L4] and rec["vm_status_after"] == {"sim": "TERMINATED", "score": "RUNNING"}
    last = r.log.strip().splitlines()[-1]
    assert "VMS LEFT RUNNING" in last and L4 in last
    assert "VMS LEFT RUNNING" in r.stdout.strip().splitlines()[-1]


def test_a_good_session_records_every_vm_terminated(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host")
    rec = json.loads((r.incoming / "session.json").read_text())
    assert r.rc == 0 and rec["left_running"] == [] and rec["exit_code_without_left_running"] == 0
    assert rec["vm_status_after"] == {"score": "TERMINATED", "guest": "TERMINATED"}


def test_the_cost_watchdog_ends_with_a_session_killed_without_its_trap(tmp_path: Path) -> None:
    # R5: a SIGKILLed session (a tool time-out, the OOM killer) runs no trap; its watchdog must not live on and
    # later signal a PID number that may belong to another process
    p = popen(tmp_path, "p10-1", FAKE_HANG_STEP="p10_1:20")
    try:
        wait_for_call(tmp_path, lambda c: any("start p10_1" in a for a in c))
        inc = next((tmp_path / "ev").glob("incoming_*"))
        time.sleep(0.5)
        p.kill()
        p.wait(timeout=10)
        time.sleep(1.0)                                      # 5 rounds of the watchdog (DA_T_WATCH_S 0.2)
        n = len((inc / "cost.log").read_text().splitlines())
        time.sleep(1.5)
        assert len((inc / "cost.log").read_text().splitlines()) == n, "the watchdog outlived its session"
        assert re.search(r"cost watchdog pid \d+", (inc / "session.log").read_text())
    finally:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        p.communicate()


def test_guest_host_needs_the_owners_ok(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3")
    assert r.rc == 2
    assert "owner's OK" in r.log
    assert not r.index(lambda c: "start" in c or "stop" in c)


def test_a_running_vm_is_not_adopted(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_INIT=f"{L4}:RUNNING")
    assert r.rc == 2
    assert not r.starts(L4) and not r.stops(L4)


def test_one_gpu_per_project(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_GPU_RUNNING="project-f2215f73-3d53-48a7-895:another-l4")
    assert r.rc == 2
    assert "one GPU per project" in r.log
    assert not r.starts(L4)


@pytest.mark.parametrize("entry", ["extra/does_not_exist.sh", "extra/README-not-executable.txt"])
def test_entry_points_are_checked_in_the_kit_before_any_start(tmp_path: Path, entry: str) -> None:
    r = run(tmp_path, "p10-1", ENTRY_SCORE_P10_1=entry)
    assert r.rc == 2
    assert "entry points not ready in the kit" in r.log
    assert not r.starts(L4)


def test_a_foreign_fetch_fails_the_session(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_FOREIGN_FETCH="1")
    assert r.rc == 5
    assert "not this session's" in r.log
    assert_invariants(r)


def test_guests_that_do_not_stop_keep_their_host_running(tmp_path: Path) -> None:
    # lead answer B13.3: never a stop of the guest host with guests running; the session says so and exits 11
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_GUEST_STOP_FAIL="1")
    assert r.rc == 11, r.log
    assert len(r.guest_stops()) == 2                         # one retry
    assert not r.stops(GH) and r.state[GH] == "RUNNING"
    assert "GUEST HOST LEFT RUNNING" in r.log
    assert r.stops(L4) and r.state[L4] == "TERMINATED"


def test_a_guest_host_that_never_answered_ssh_and_got_no_guest_step_is_stopped(tmp_path: Path) -> None:
    # S1: started by this session, never reached over SSH, so never sent a guest step: no guest can run there (the
    # image starts no Cuttlefish at boot). It was left running, unarmed, billing; now it stops after a bounded wait
    t0 = time.monotonic()
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_SSH_DOWN=GH, DA_T_GUEST_NOSSH_S="1")
    assert r.rc == 4, r.log
    assert r.stops(GH) and r.state[GH] == "TERMINATED"
    assert "never answered SSH" in r.log and "nothing on its image starts Cuttlefish at boot" in r.log
    assert "GUEST HOST LEFT RUNNING" not in r.log and not r.guest_stops()
    assert time.monotonic() - t0 < 60
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["left_running"] == [] and rec["vm_status_after"]["guest"] == "TERMINATED"
    assert_invariants(r)


def test_an_ssh_loss_after_a_guest_step_keeps_the_guest_host_running(tmp_path: Path) -> None:
    # R2, S12 (Y02): once a guest step went out, guests may run; an unknown crosvm count (no SSH in the trap) never
    # stops their host
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_FAIL_STEP="inject",
            FAKE_SSH_DOWN_AFTER=f"{GH}:score_stop_on_failure", DA_T_GUEST_NOSSH_S="1")
    assert r.rc == 11, r.log
    assert r.guest_stops() and not r.stops(GH) and r.state[GH] == "RUNNING"
    assert "crosvm processes left on de4sdv-aaos-build: unknown" in r.log and "GUEST HOST LEFT RUNNING" in r.log
    assert r.stops(L4) and r.state[L4] == "TERMINATED"


def test_a_second_guest_stop_that_works_lets_the_host_stop(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_GUEST_STOP_FAIL="once")
    assert r.rc == 0, r.log
    stops = r.guest_stops()
    checks = r.ssh(GH, "pgrep -c -x crosvm")
    assert len(stops) == 2 and stops[0] < checks[0] < stops[1] < checks[1] < r.stops(GH)[0]
    assert_invariants(r)


def test_an_existing_session_folder_is_refused(tmp_path: Path) -> None:
    (tmp_path / "ev" / "incoming_T").mkdir(parents=True)
    r = run(tmp_path, "p10-1")
    assert r.rc == 2
    assert not r.calls


def test_dry_run_refuses_a_real_gcloud(tmp_path: Path) -> None:
    real = tmp_path / "google-cloud-sdk" / "bin" / "gcloud"
    real.parent.mkdir(parents=True)
    real.write_text("#!/bin/sh\nexit 0\n")
    real.chmod(0o755)
    r = run(tmp_path, "p10-1", DA_GCLOUD=str(real))
    assert r.rc == 9
    assert not r.calls


def test_a_real_session_refuses_the_dry_run_knobs(tmp_path: Path) -> None:
    # HOME points into tmp, so no real gcloud exists under it even if the check were missing
    proc = subprocess.run(["bash", str(SESSION), "--kind", "p10-1", "--evidence-root", str(tmp_path / "ev")],
                          env=dict(env_for(tmp_path), HOME=str(tmp_path)), capture_output=True, text=True, timeout=30)
    assert proc.returncode == 2
    assert "dry-run knob" in proc.stdout


def test_the_dry_run_prints_every_command(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host")
    printed = [line for line in r.stdout.splitlines() if line.startswith(("+ gcloud", "+ ssh", "+ scp"))]
    assert len(printed) == len(r.calls)
    assert printed[0].startswith("+ gcloud --configuration=de4sdv-gcp --project=")


# ------------------------------------------------------------------------------- the sequence of each kind
# Expected from the work order: world-side/README.md "Commands on the simulator host" (survey and warm-up, the
# calibrations without the candidate, the calibration file before the identity record, calib-steer with the S-CORE
# side after ready.json, two runs), launch-manager/README.md (stop the S-CORE side before the world stops ticking),
# the lead's B10.2 (am start -S before each window) and the guest-prep-20261118 operator's P10-3 order (VXLAN,
# the offer, the multicast route, the broker's unit, the IVI clock just before the window). Written out here, not
# taken from the script.

# p10-1 (lead decision of 2026-11-19, part 2): CARLA up, the port test as the first cross-host step, the session's
# road (the warm-up entry's survey), the world spawned, its go before the check (the world ticks through the check's
# three parts) and its release only after the check ended (the check stops its own Launch Manager starts while the
# world still ticks); no recorder, no calibration (p10-1 judges no driving and no geometry)
P10_1_SEQ = ["sim:sim_setup", "score:port_test", "sim:warmup", "sim:world_p10_1&", "sim:file-ready.json", "sim:touch-go",
             "score:p10_1", "sim:file-run_end.json", "sim:touch-release", "sim:wait-world_p10_1"]
GUEST_UP_SEQ = ["guest:guest_up", "guest:guest_prepare", "guest:vxlan_guest", "score:vxlan_score", "guest:neigh_flush"]
P10_3_SEQ = GUEST_UP_SEQ + [
    "guest:logmark_inject", "score:score_start", "guest:mcast_route", "guest:unit_inject", "guest:app_restart_inject",
    "guest:ivi_clock_inject", "guest:capture_inject&", "score:inject", "guest:capture_stop_inject",
    "guest:wait-capture_inject", "guest:receipts_inject", "score:score_stop"]


def _p10_2_run(n: int, first: bool, guest: bool = True) -> list[str]:
    w = f"run{n}"
    window = ((["guest:mcast_route"] if first else []) + [f"guest:unit_{w}", f"guest:app_restart_{w}",
              f"guest:ivi_clock_{w}", f"guest:capture_{w}&"]) if guest else []
    close = [f"guest:capture_stop_{w}", f"guest:wait-capture_{w}", f"guest:receipts_{w}"] if guest else []
    mark = [f"guest:logmark_{w}"] if guest else []
    return [f"sim:rec_{w}&", f"sim:world_{w}&", "sim:file-ready.json", *mark, f"score:score_start_{w}", *window,
            "sim:touch-go", "sim:file-run_end.json", f"score:score_stop_{w}", "sim:touch-release",
            f"sim:wait-world_{w}", f"sim:wait-rec_{w}", *close]


def p10_2_seq(guest: bool = True) -> list[str]:
    # F3 of 20261119T174606Z: the S-CORE host's disk check is the first step, before any run and before the
    # simulator host's setup, so a short disk costs the least
    return (["score:disk_check", "sim:sim_setup", "score:carla_reach"] + (GUEST_UP_SEQ if guest else []) + [
        "sim:rec_warmup&", "sim:warmup", "sim:wait-rec_warmup", "sim:calibrate", "lead:make_h",
        "sim:world_calib_steer&", "sim:file-ready.json", "score:score_start_calib_steer", "sim:touch-go",
        "sim:file-run_end.json", "score:score_stop_calib_steer", "sim:touch-release", "sim:wait-world_calib_steer"]
        + _p10_2_run(1, True, guest) + _p10_2_run(2, False, guest))


@pytest.mark.parametrize("kind, more, expected", [
    ("p10-1", (), P10_1_SEQ),
    ("p10-3", ("--owner-ok-guest-host",), P10_3_SEQ),
    ("p10-2", ("--owner-ok-guest-host",), p10_2_seq()),
    ("p10-2", ("--without-guest-host",), p10_2_seq(guest=False)),
])
def test_the_sequence_of_each_kind(tmp_path: Path, kind: str, more: tuple, expected: list[str]) -> None:
    r = run(tmp_path, kind, *more)
    assert r.rc == 0, r.stdout + r.log
    assert r.sequence() == expected
    assert_invariants(r)


def test_p10_2_puts_the_calibration_file_on_the_score_host_before_every_score_start(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host")
    assert r.rc == 0, r.log
    up = r.index(lambda c: c[2:4] == ["compute", "scp"] and any(a.endswith("camera_calibration/") for a in c))
    assert up and all(any(a.endswith(n) for a in r.calls[up[0]]) for n in ("H.yaml", "homography_C_matrix.yaml"))
    starts = r.ssh(L4, "start score_start_")
    assert len(starts) == 3 and up[0] < starts[0]
    assert all("DA_CAMERA_CALIBRATION_DIR=" in r.command(i) for i in starts)
    # the capture came from the simulator host's calibrate step, before make-h
    fetch = r.index(lambda c: c[2:4] == ["compute", "scp"] and any("calibrate/camcal/simulator/camera_capture.json"
                                                                   in a for a in c))
    assert fetch and r.ssh(G4, "start calibrate")[0] < fetch[0] < up[0]
    rec = json.loads((r.incoming / "session.json").read_text())
    h = (r.incoming / "camcal" / "h" / "H.yaml").read_bytes()
    assert rec["camera_calibration_sha256"]["H.yaml"] == hashlib.sha256(h).hexdigest()


def test_p10_2_kit_carries_the_pinned_checkerboard(tmp_path: Path, vp_clone) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host")
    assert r.rc == 0, r.log
    with tarfile.open(r.incoming / "kit.tgz") as t:
        data = t.extractfile("bench/session-inputs/checkerboard-bw-4x4.png").read()
    assert data == (vp_clone[0] / UPSTREAM[0]).read_bytes()


@pytest.mark.parametrize("env, needle", [
    ({"ENTRY_SIM_CALIBRATE": ""}, "needs ENTRY_SIM_CALIBRATE"),
    ({"VP_PIN": "0" * 40}, "is not at"),
    ({"ENTRY_GUEST_PREPARE": ""}, "fresh guests start without the app"),
])
def test_p10_2_refusals_before_any_start(tmp_path: Path, env: dict, needle: str) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", **env)
    assert r.rc == 2, r.log
    assert needle in r.log
    assert not r.index(lambda c: "start" in c or "stop" in c)


def test_a_real_session_refuses_the_make_h_stand_in(tmp_path: Path) -> None:
    env = {k: v for k, v in env_for(tmp_path).items() if not k.startswith("DA_T_")}
    proc = subprocess.run(["bash", str(SESSION), "--kind", "p10-2", "--evidence-root", str(tmp_path / "ev")],
                          env=dict(env, HOME=str(tmp_path)), capture_output=True, text=True, timeout=30)
    assert proc.returncode == 2 and "DA_MAKE_H is a dry-run knob" in proc.stdout


def test_a_world_side_that_never_gets_ready_ends_the_session_before_the_score_start(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_NO_FILE="ready.json", DA_T_T_READY="1")
    assert r.rc == 5, r.log
    assert "the world side of calib_steer is not ready" in r.log
    assert not r.ssh(L4, "start score_start_")
    assert_invariants(r)


@pytest.mark.parametrize("iap", ["0", "1"])
def test_sim_ssh_iap_tunnels_every_ssh_and_scp_to_the_simulator_host_only(tmp_path: Path, iap: str) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", SIM_SSH_IAP=iap)
    assert r.rc == 0, r.log
    remote = r.index(lambda c: c[2:4] in (["compute", "ssh"], ["compute", "scp"]))
    to_sim = [i for i in remote if any(a == G4 or a.startswith(G4 + ":") for a in r.calls[i])]
    others = [i for i in remote if i not in to_sim]
    assert to_sim and others
    assert all(("--tunnel-through-iap" in r.calls[i]) == (iap == "1") for i in to_sim)
    assert not any("--tunnel-through-iap" in r.calls[i] for i in others)
    assert json.loads((r.incoming / "session.json").read_text())["sim_ssh_iap"] is (iap == "1")


def test_every_internal_ip_comes_from_gcloud(tmp_path: Path) -> None:
    ips = {G4: "10.10.0.7", L4: "10.164.0.20", GH: "10.164.0.33"}   # made-up addresses only the fake gcloud knows
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_IP=",".join(f"{k}:{v}" for k, v in ips.items()))
    assert r.rc == 0, r.log
    assert "/dev/tcp/10.10.0.7/2000" in r.command(r.ssh(L4, "start carla_reach")[0])
    assert r.command(r.ssh(GH, "start vxlan_guest")[0]).endswith("add 10.164.0.20")
    assert r.command(r.ssh(L4, "start vxlan_score")[0]).endswith("add 10.164.0.33")
    assert all(r.command(i).split()[-1] == "10.10.0.7" for i in r.ssh(L4, "start score_start_"))
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["internal_ips_from_gcloud"] == {"sim": "10.10.0.7", "guest": "10.164.0.33", "score": "10.164.0.20"}


def test_no_address_is_configured_in_the_session_files() -> None:
    files = [HERE.parent / "da_session.sh", HERE.parent / "hosts.env", HERE.parent / "entrypoints.env",
             *sorted((HERE.parent / "remote").glob("*.sh"))]
    for f in files:
        # code, not comments (hosts.env's comment quotes D5's firewall); 192.168.98.x is the guest network's own
        text = "\n".join(line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
                         for line in f.read_text().splitlines())
        found = re.findall(r"\b10\.\d+\.\d+\.\d+\b", text)
        assert not found, (f.name, found)


def test_the_guest_host_safety_net_stops_the_guests_first(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host")
    assert r.rc == 0, r.log
    arm = [r.command(i) for i in r.ssh(GH, "safety_net.sh arm")]
    assert len(arm) == 1 and "guest_stop.sh" in arm[0] and "shutdown -h" not in arm[0]
    assert "$DA_SESSION_ID" not in arm[0] and "da-kit/T/bench/session/remote/guest_stop.sh" in arm[0]
    score_arm = [r.command(i) for i in r.ssh(L4, "safety_net.sh arm")]
    assert len(score_arm) == 1 and "guest_stop" not in score_arm[0]


def test_permissive_ivi_is_opt_in_and_marks_the_session(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host")
    assert "IVI_PERMISSIVE=0" in r.command(r.ssh(GH, "start guest_up")[0])
    assert json.loads((r.incoming / "session.json").read_text())["conditional_on_permissive_ivi"] is False
    r2 = run(tmp_path / "b", "p10-3", "--owner-ok-guest-host", "--permissive-ivi")
    assert r2.rc == 0, r2.log
    for step in ("start guest_up", "start guest_prepare"):
        assert "IVI_PERMISSIVE=1" in r2.command(r2.ssh(GH, step)[0])
    assert json.loads((r2.incoming / "session.json").read_text())["conditional_on_permissive_ivi"] is True
    assert "conditional on a permissive IVI" in r2.log


def test_the_app_entries_match_the_app_manifest_and_its_record() -> None:
    bench = HERE.parent.parent
    env = subprocess.run(["bash", "-c", '. "$1/hosts.env"; . "$1/entrypoints.env"; '
                          'printf "%s\\n" "$APP_PACKAGE" "$APP_COMPONENT" "$APP_RECORD_PATHS"', "_",
                          str(HERE.parent)], capture_output=True, text=True, check=True).stdout.split("\n")
    manifest = ET.parse(bench / "ivi-warning-app" / "app" / "AndroidManifest.xml").getroot()
    ns = "{http://schemas.android.com/apk/res/android}"
    package = manifest.get("package")
    launcher = [a.get(ns + "name") for a in manifest.iter("activity")
                if any(c.get(ns + "name") == "android.intent.category.LAUNCHER" for c in a.iter("category"))]
    record = re.search(r'FILE = "([^"]+)"', (bench / "ivi-warning-app" / "app" / "src" / "org" / "de4sdv" /
                                            "collisionwarning" / "WarningRecord.java").read_text()).group(1)
    assert env[0] == package
    assert env[1] == f"{package}/{launcher[0]}"
    assert env[2] == f"/data/user/@user@/{package}/files/{record}"


# ------------------------------------------------------------------------------- per-session settings (R6)


def test_per_session_settings_reach_the_steps_of_their_host_only(tmp_path: Path) -> None:
    # R6: a guessed pattern or time-out of a remote entry changes for a session without a commit
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", "--remote-env", "UNIT_REGISTERED_RE=unit .* registered",
            "--remote-env", "UNIT_WAIT_S=600", "--remote-env", "GATEWAYD_RX_REGEX=rx [0-9]+", NOT_ON_THE_LIST="x")
    assert r.rc == 0, r.log
    unit = r.command(r.ssh(GH, "start unit_inject")[0])
    assert "env UNIT_REGISTERED_RE=unit\\ .\\*\\ registered UNIT_WAIT_S=600 bash" in unit
    for i in r.ssh(GH, "host_step.sh start"):
        assert "UNIT_WAIT_S=600" in r.command(i) and "GATEWAYD_RX_REGEX" not in r.command(i)
    for i in r.ssh(L4, "host_step.sh start"):
        assert "GATEWAYD_RX_REGEX=" in r.command(i) and "UNIT_WAIT_S" not in r.command(i)
    assert not any("NOT_ON_THE_LIST" in a for c in r.calls for a in c)
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["remote_env"] == {"guest": {"UNIT_REGISTERED_RE": "unit .* registered", "UNIT_WAIT_S": "600"},
                                 "score": {"GATEWAYD_RX_REGEX": "rx [0-9]+"}}


def test_the_unit_gates_source_is_a_per_session_setting_of_the_guest_host(tmp_path: Path) -> None:
    # the default source is the IVI app's own link line; UNIT_SOURCE=core keeps the core-log check, on purpose only
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", "--remote-env", "UNIT_SOURCE=core", UNIT_SOURCE="app")
    assert r.rc == 0, r.log
    assert "env UNIT_SOURCE=core bash" in r.command(r.ssh(GH, "start unit_inject")[0])
    assert json.loads((r.incoming / "session.json").read_text())["remote_env"] == {"guest": {"UNIT_SOURCE": "core"}}
    plain = run(tmp_path / "b", "p10-3", "--owner-ok-guest-host", UNIT_SOURCE="core")   # exported: never reaches
    assert plain.rc == 0 and not any("UNIT_SOURCE" in a for c in plain.calls for a in c)


@pytest.mark.parametrize("tail, logged, recorded", [
    ("guest_up:CROSVM_BEFORE_LAUNCH 0", "crosvm processes on the guest host before guest_up: 0 (S1 held", 0),
    ("guest_up:CROSVM_BEFORE_LAUNCH 2", "S1 VOID: 2 crosvm process(es) on the guest host before guest_up", 2),
    ("guest_up:CROSVM_BEFORE_LAUNCH unknown", "crosvm processes on the guest host before guest_up: unknown", None),
    ("", "crosvm processes on the guest host before guest_up: unknown", None),
])
def test_the_session_logs_the_crosvm_count_before_guest_up(tmp_path: Path, tail: str, logged: str,
                                                           recorded) -> None:
    # S1's real assumption, checked every run: no guest runs on the guest host before the session starts one
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_TAIL_ADD=tail)
    assert r.rc == 0, r.log
    assert logged in r.log, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["crosvm_before_guest_up"] == recorded
    assert r.sequence() == P10_3_SEQ


def test_an_exported_setting_never_reaches_a_remote_step(tmp_path: Path) -> None:
    # S4: another worker's UNIT_WAIT_S=0 exported in the shell made a paid P10-3's unit check fail at once; only the
    # --remote-env option sets a remote entry's setting
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", UNIT_WAIT_S="0", START_WAIT_S="1", B12_DIR="/lead/path",
            GATEWAYD_RX_REGEX="x")
    assert r.rc == 0, r.log
    for name in ("UNIT_WAIT_S", "START_WAIT_S", "B12_DIR", "GATEWAYD_RX_REGEX"):
        assert not any(name in a for c in r.calls for a in c), name
    assert "per-session settings" not in r.log
    assert json.loads((r.incoming / "session.json").read_text())["remote_env"] == {}


@pytest.mark.parametrize("opts", [("--remote-env", "NOT_ON_THE_LIST=x"), ("--remote-env", "UNIT_WAIT_S"),
                                  ("--remote-env", "UNIT_WAIT_S=1", "--remote-env", "UNIT_WAIT_S=2"),
                                  ("--remote-env", "GUEST_STOP_CMD=true")])
def test_a_remote_setting_off_the_allow_list_or_malformed_is_refused(tmp_path: Path, opts: tuple) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", *opts)
    assert r.rc == 2 and "--remote-env" in r.stdout and not r.calls, r.stdout


def test_without_per_session_settings_the_commands_are_unchanged(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1")
    assert r.rc == 0, r.log
    assert r.command(r.ssh(L4, "start p10_1")[0]).endswith(
        "host_step.sh start p10_1 -- env DA_P10_1_CARLA_HOST=10.10.0.2 bash extra/p10_1_check.sh $HOME/da-kit/T/out/p10_1")
    assert json.loads((r.incoming / "session.json").read_text())["remote_env"] == {}


def test_the_window_counts_the_app_records_receipts_and_says_so_loudly_when_none(tmp_path: Path) -> None:
    # R7: a window whose app record holds no receipt did not carry, whatever the unit check said
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host")
    assert r.rc == 0, r.log
    assert "window inject: 2 receipt event(s) in the app's record since the window's app start" in r.log
    assert json.loads((r.incoming / "session.json").read_text())["app_record_receipts"] == {"inject": 2}
    r0 = run(tmp_path / "b", "p10-3", "--owner-ok-guest-host", FAKE_RECEIPTS="0")
    assert "NO RECEIPT IN THE APP'S RECORD OF WINDOW inject" in r0.log
    assert json.loads((r0.incoming / "session.json").read_text())["app_record_receipts"] == {"inject": 0}


def test_p10_3_is_passed_only_with_a_receipt_in_every_windows_app_record(tmp_path: Path) -> None:
    # T4: with no receipt in the app's record a p10-3 exits 0 (its steps ran) and read like a pass
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host")
    assert r.rc == 0, r.log
    rec = json.loads((r.incoming / "session.json").read_text())["p10_3"]
    assert rec["passed"] is True and "inject" in rec["reason"], rec
    assert "p10-3 passed:" in r.log
    r0 = run(tmp_path / "b", "p10-3", "--owner-ok-guest-host", FAKE_RECEIPTS="0")
    assert r0.rc == 0, r0.log   # the exit code stays the documented one: the steps ran
    rec0 = json.loads((r0.incoming / "session.json").read_text())["p10_3"]
    assert rec0["passed"] is False and "no receipt event since the app's start in the record of window inject" \
        in rec0["reason"], rec0
    assert "p10-3 NOT passed:" in r0.log
    assert json.loads((run(tmp_path / "c", "p10-1").incoming / "session.json").read_text())["p10_3"] is None


def _record(tmp_path: Path, name: str, receipts_after_the_start: int) -> Path:
    """An app record in the app's own JSONL format (WarningRecord.json): guest_prepare's start (pid 3205), a stop,
    the window's restart (pid 4242, the fake's restart record), each start with its lifecycle, link and status lines."""
    def jl(event: str, **kv) -> str:
        return json.dumps({"event": event, "t_mono_ns": 1, "t_real_ns": 2, **kv}, separators=(",", ":")) + "\n"
    def start(pid: int) -> str:
        return (jl("lifecycle", phase="start", pid=pid, unit="de4sdv-driving-warning-request")
                + jl("lifecycle", phase="link", link="SUBSCRIBED", detail="instance1")
                + jl("status", link="SUBSCRIBED", receipts=0, requests=0, refused=0))
    text = (start(3205) + jl("receipt", seq=1, request=1, verdict="ACCEPTED") + jl("lifecycle", phase="stop", receipts=1)
            + start(4242) + "".join(jl("receipt", seq=i, request=i, verdict="ACCEPTED")
                                    for i in range(1, receipts_after_the_start + 1)))
    tmp_path.mkdir(parents=True, exist_ok=True)
    (tmp_path / name).write_text(text)
    return tmp_path / name


def test_p10_3_with_no_receipt_since_the_windows_app_start_is_not_passed(tmp_path: Path) -> None:
    # W1 of the re-check at 437a833b: the record is appended and every app start writes lifecycle, link and status
    # lines, so a line count was never 0 and p10_3.passed read true with zero receipts
    r = run(tmp_path / "a", "p10-3", "--owner-ok-guest-host", FAKE_APP_RECORD=str(_record(tmp_path, "r0.jsonl", 0)))
    assert r.rc == 0, r.log
    j = json.loads((r.incoming / "session.json").read_text())
    assert j["app_record_receipts"] == {"inject": 0}, j["app_record_receipts"]
    assert j["p10_3"]["passed"] is False and "no receipt event" in j["p10_3"]["reason"], j["p10_3"]
    assert "NO RECEIPT IN THE APP'S RECORD OF WINDOW inject" in r.log
    i = r.ssh(GH, "start receipts_inject")[0]
    assert r.command(i).endswith("receipts $HOME/da-kit/T/out/capture_inject $HOME/da-kit/T/out/app_restart/"
                                 "app_restart_inject.txt"), r.command(i)
    r2 = run(tmp_path / "b", "p10-3", "--owner-ok-guest-host", FAKE_APP_RECORD=str(_record(tmp_path, "r2.jsonl", 2)))
    j2 = json.loads((r2.incoming / "session.json").read_text())
    assert j2["app_record_receipts"] == {"inject": 2} and j2["p10_3"]["passed"] is True, j2["p10_3"]
    assert "receipt events since the window's app start" in j2["p10_3"]["reason"], j2["p10_3"]


def test_p10_2_windows_count_only_receipt_events_since_their_app_start(tmp_path: Path) -> None:
    r = run(tmp_path / "a", "p10-2", "--owner-ok-guest-host", FAKE_APP_RECORD=str(_record(tmp_path, "r0.jsonl", 0)))
    assert r.rc == 0, r.log
    got = json.loads((r.incoming / "session.json").read_text())["app_record_receipts"]
    assert got and set(got.values()) == {0}, got
    for w in got:
        assert f"NO RECEIPT IN THE APP'S RECORD OF WINDOW {w}" in r.log
        i = r.ssh(GH, f"start receipts_{w}")[0]
        assert r.command(i).endswith(f"app_restart/app_restart_{w}.txt"), r.command(i)


def _bounds(r: Run) -> dict[str, int]:
    line = [x for x in r.log.splitlines() if " step bounds: " in x]
    assert line, r.log
    return {k: int(v) for k, v in re.findall(r"(\w+) (\d+) s", line[-1].split(" step bounds: ", 1)[1])}


def test_the_unit_and_app_restart_bounds_follow_their_waits(tmp_path: Path) -> None:
    # W4: T_UNIT = UNIT_WAIT_S + 240 (the last poll: 2 reads of 30 s and POLL_S 5; on a fail the diagnostics: 4 adb
    # calls of 30 s). W2: the app restart's step = START_WAIT_S + APP_SUBSCRIBE_WAIT_S + 10 adb calls of 30 s
    b = _bounds(run(tmp_path / "a", "p10-3", "--owner-ok-guest-host"))
    assert b["unit"] == 360 and b["app_restart"] == 335, b
    b = _bounds(run(tmp_path / "b", "p10-3", "--owner-ok-guest-host", "--remote-env", "UNIT_WAIT_S=300",
                    "--remote-env", "APP_SUBSCRIBE_WAIT_S=60", "--remote-env", "START_WAIT_S=10"))
    assert b["unit"] == 540 and b["app_restart"] == 370, b
    readme = (HERE.parent / "README.md").read_text()   # the README's own example is the 540 s case above
    assert re.findall(r"--remote-env UNIT_WAIT_S=(\d+)", readme) == ["300"]
    r = run(tmp_path / "c", "p10-3", "--owner-ok-guest-host", "--remote-env", "UNIT_WAIT_S=2m")
    assert r.rc == 2 and "UNIT_WAIT_S" in r.stdout and not r.starts(GH), r.stdout


def test_the_app_restart_step_is_bounded_by_t_app_restart(tmp_path: Path) -> None:
    # m35 of the lane's harness: the step's bound is T_APP_RESTART, not T_STEP (300 s here): a step that hangs 30 s
    # past a T_APP_RESTART of 2 s is signalled at its time-out
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_HANG_STEP="app_restart_inject:30", DA_T_T_APP_RESTART="2")
    assert r.rc == 5, r.log
    sig = r.ssh(GH, "host_step.sh signal app_restart_inject TERM")
    assert sig and sig[0] < r.ssh(GH, "host_step.sh tail app_restart_inject")[0], r.log
    assert "step app_restart_inject rc=124" in r.log, r.log
    assert not r.ssh(GH, "start ivi_clock_inject")


def test_the_app_subscribe_wait_is_a_per_session_setting(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", "--remote-env", "APP_SUBSCRIBE_WAIT_S=45")
    assert r.rc == 0, r.log
    i = r.ssh(GH, "start app_restart_inject")[0]
    assert "APP_SUBSCRIBE_WAIT_S=45" in r.command(i), r.command(i)


def test_the_unit_check_reads_the_log_since_the_mark_before_the_score_start(tmp_path: Path) -> None:
    # R7: the mark is the SDV Core guest's clock just before the S-CORE side starts; the unit check names it
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host")
    mark, start, unit = r.ssh(GH, "start logmark_inject"), r.ssh(L4, "start score_start"), r.ssh(GH, "start unit_inject")
    assert mark[0] < start[0] < unit[0]
    assert r.command(unit[0]).endswith("unit $HOME/da-kit/T/out/unit_inject $HOME/da-kit/T/out/logmark_inject")


# ------------------------------------------------------------------- failures after the S-CORE side's start (R8, R13)


def test_a_failure_after_the_score_start_stops_the_score_side_before_the_fetch(tmp_path: Path) -> None:
    # R8: the S-CORE side's stop is the only collector of its records; a failure after its start runs it, then fetches
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_FAIL_STEP="unit_inject")
    assert r.rc == 5, r.log
    stop = r.ssh(L4, "run score_stop_on_failure")
    assert len(stop) == 1 and r.command(stop[0]).endswith("stop_score_side.sh $HOME/da-kit/T/out/score")
    assert r.ssh(L4, "start score_start")[0] < stop[0] < r.ssh(L4, "host_step.sh pack")[0] < r.stops(L4)[0]
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["ended_by"] == "step unit_inject" and rec["fetched"] == ["score", "guest"] and rec["not_fetched"] == []
    assert_invariants(r)


def test_a_failure_before_the_score_start_or_after_its_stop_does_not_stop_it_again(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_FAIL_STEP="guest_prepare")
    assert r.rc == 5 and not r.ssh(L4, "score_stop"), r.log
    r2 = run(tmp_path / "b", "p10-2", "--owner-ok-guest-host", FAKE_FAIL_STEP="world_calib_steer")
    assert r2.rc == 5 and r2.ssh(L4, "start score_stop_calib_steer") and not r2.ssh(L4, "score_stop_on_failure")


def test_a_signal_stops_the_score_side_and_fetches_every_host_before_its_stop(tmp_path: Path) -> None:
    # R8, R13: a signal mid-window (the inject step) still collects the S-CORE side and fetches both hosts (bounded),
    # and session.json says what ended the session and what was fetched
    p = popen(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_HANG_STEP="inject:30")
    wait_for_call(tmp_path, lambda c: any("start inject" in a for a in c))
    time.sleep(0.5)
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    stop = r.ssh(L4, "run score_stop_on_failure")
    assert stop and stop[0] < r.ssh(L4, "host_step.sh pack")[0] < r.stops(L4)[0]
    assert r.ssh(GH, "host_step.sh pack")[0] < r.guest_stops()[0]
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["ended_by"] == "signal TERM" and sorted(rec["fetched"]) == ["guest", "score"]
    assert (r.incoming / "score" / "out" / "session_id").read_text().strip() == "T"
    assert_invariants(r)


# ------------------------------------------------------------- the S-CORE side's stop that had to kill (S7)


def test_a_final_score_stop_that_had_to_kill_is_recorded_and_does_not_fail_the_session(tmp_path: Path) -> None:
    # S7: stop_score_side.sh exit 7 = stopped and collected, something had to be killed: the evidence is complete
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_STEP_RC="score_stop:7")
    assert r.rc == 0, r.log
    assert "step score_stop rc=7" in r.log and "had to be killed" in r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["score_stops"] == {"inject": {"step": "score_stop", "rc": 7, "stop_killed": True}}
    assert rec["failed_step"] is None and rec["fetched"] == ["score", "guest"]
    assert_invariants(r)


def test_p10_2_final_score_stop_that_had_to_kill_is_recorded_and_the_session_passes(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--without-guest-host", FAKE_STEP_RC="score_stop_run2:7")
    assert r.rc == 0, r.log
    stops = json.loads((r.incoming / "session.json").read_text())["score_stops"]
    assert stops["run2"] == {"step": "score_stop_run2", "rc": 7, "stop_killed": True}
    assert stops["run1"]["stop_killed"] is False and stops["calib_steer"]["rc"] == 0
    assert r.sequence() == p10_2_seq(guest=False)


@pytest.mark.parametrize("step, nxt", [("score_stop_calib_steer", "world_run1"), ("score_stop_run1", "world_run2")])
def test_p10_2_a_score_stop_that_had_to_kill_before_another_run_ends_the_session(tmp_path: Path, step: str,
                                                                               nxt: str) -> None:
    # S7, the lead's decision: the next run would start from a suspect state while three VMs bill
    r = run(tmp_path, "p10-2", "--without-guest-host", FAKE_STEP_RC=f"{step}:7")
    assert r.rc == 5, r.log
    assert not r.ssh(G4, f"start {nxt}")
    w = step[len("score_stop_"):]
    assert r.ssh(G4, f"world_{w}/release") and r.ssh(G4, f"status world_{w}")    # the run itself completed
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["score_stops"][w] == {"step": step, "rc": 7, "stop_killed": True}
    assert rec["failed_step"] == step and "had to kill" in rec["ended_by"]
    assert not r.ssh(L4, "score_stop_on_failure")
    assert_invariants(r)


def test_a_score_stop_whose_collection_failed_still_fails_the_session(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_STEP_RC="score_stop:8")
    assert r.rc == 5, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["failed_step"] == "score_stop" and rec["score_stops"]["inject"]["stop_killed"] is False


def test_a_failed_fetch_is_named_in_the_record(tmp_path: Path) -> None:
    # R13: exit 5 with failed_step null said nothing about which host's files are missing
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_FETCH_FAIL=GH)
    assert r.rc == 5, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["ended_by"] == "fetch" and rec["fetched"] == ["score"] and rec["not_fetched"] == ["guest"]


def test_the_cap_names_itself_as_the_end(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", "--cap-eur", "2", SCORE_EUR_H="3600", FAKE_HANG_STEP="p10_1:30")
    assert r.rc == 10, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["ended_by"] == "cap" and rec["fetched"] == ["sim", "score"]


def _call_times(tmp: Path, pred) -> list[float]:
    return [json.loads(line)[0] for line in (tmp / "fake" / "calls.log").read_text().splitlines()
            if pred(json.loads(line)[1:])]


def test_a_signal_before_the_steps_still_fetches_an_uploaded_host(tmp_path: Path) -> None:
    # the trap's fetch and the S-CORE side's stop were defined only after the SSH and upload section: a signal or the
    # cap there gave "fetch: command not found", and the uploaded host stopped unfetched
    p = popen(tmp_path, "p10-2", "--without-guest-host", FAKE_SSH_DOWN=L4, DA_T_SSH_TRIES="2000")
    wait_for_call(tmp_path, lambda c: c[2:4] == ["compute", "ssh"] and c[4] == L4)
    time.sleep(0.3)
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    assert "command not found" not in r.stdout, r.stdout
    assert r.ssh(G4, "host_step.sh pack") and r.ssh(G4, "host_step.sh pack")[0] < r.stops(G4)[0]
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["fetched"] == ["sim"] and rec["not_fetched"] == ["score"]
    assert_invariants(r)


def test_the_pre_stop_phase_of_the_trap_is_bounded_as_a_whole(tmp_path: Path) -> None:
    # S9: after the cap or a signal the trap fetched every host before any stop, each with its own bound (120 s
    # pack, 300 s copy): up to 23 min past the cap with every VM billing. The whole phase now has one bound
    p = popen(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_HANG_STEP="inject:60", FAKE_SLOW_FETCH="6",
              DA_T_PRESTOP_S="3")
    wait_for_call(tmp_path, lambda c: any("start inject" in a for a in c))
    time.sleep(0.5)
    t0 = time.time()
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    first_stop = min(_call_times(tmp_path, lambda c: c[2:5] == ["compute", "instances", "stop"]))
    assert first_stop - t0 < 9, first_stop - t0
    assert "pre-stop phase" in r.log
    assert_invariants(r)


def test_on_the_cap_a_host_with_nothing_to_fetch_stops_first(tmp_path: Path) -> None:
    # S9: the S-CORE host never answered SSH (no kit, nothing to collect or fetch): it stops before the simulator
    # host's fetch, not after it
    r = run(tmp_path, "p10-2", "--without-guest-host", "--cap-eur", "0.01", FAKE_SSH_DOWN=L4, SCORE_EUR_H="3.6",
            DA_T_SSH_TRIES="2000")
    assert r.rc == 10, r.log
    assert "COST CAP reached" in r.log
    assert r.stops(L4)[0] < r.ssh(G4, "host_step.sh pack")[0] < r.stops(G4)[0]
    assert_invariants(r)


def test_the_traps_status_reads_wait_30_s_at_most_and_ignore_an_exported_gc_to(tmp_path: Path) -> None:
    # S10: each status read in the trap's stop loop waited up to 120 s on a hanging gcloud (30 reads per VM, every
    # signal ignored); and GC_TO came from the caller's shell
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", GC_TO="2")
    assert r.rc == 0, r.log
    cmds = (r.incoming / "commands.log").read_text().splitlines()
    first_stop = next(i for i, c in enumerate(cmds) if " compute instances stop " in c)
    before = [c for c in cmds[:first_stop] if " compute instances describe " in c]
    after = [c for c in cmds[first_stop:] if " compute instances describe " in c]
    assert before and all(c.endswith("[timeout 120 s]") for c in before), before[:2]
    assert after and all(c.endswith("[timeout 30 s]") for c in after), after[:2]


def test_a_signal_during_a_fetch_ends_the_session_at_once(tmp_path: Path) -> None:
    # R19: a fetch scp inside a pipeline made the trap (and the cap) wait for the whole scp
    # p10-1 fetches the simulator host first: its copy is the slow one, the S-CORE host's is fetched in the trap
    # (the simulator host by direct SSH here: its single scp; the ranged fetch through IAP has its own test, F7)
    p = popen(tmp_path, "p10-1", FAKE_SLOW_FETCH=f"{G4}:15", SIM_SSH_IAP="0")
    wait_for_call(tmp_path, lambda c: c[2:4] == ["compute", "scp"] and any(a.endswith("/out.tgz") for a in c))
    time.sleep(0.5)
    t0 = time.monotonic()
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    assert time.monotonic() - t0 < 8, "the trap waited for the fetch"
    copies = r.index(lambda c: c[2:4] == ["compute", "scp"] and any(a.startswith(G4 + ":") and a.endswith("/out.tgz")
                                                                     for a in c))
    assert len(copies) == 1                                       # the interrupted fetch is not tried again
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["fetched"] == ["score"] and rec["not_fetched"] == ["sim"]   # the interrupted fetch is named
    assert_invariants(r)


# --------------------------------------------------------------------------- the safety net and Spot (R15, R11)


@pytest.mark.parametrize("vm", [L4, GH])
def test_a_safety_net_that_does_not_arm_ends_the_session(tmp_path: Path, vm: str) -> None:
    # R15: no host runs on without its backstop for the lead host's loss
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_ARM_FAIL=vm)
    assert r.rc == 4, r.log
    assert "is not armed" in r.log and not r.ssh(GH, "start guest_up")
    assert_invariants(r)


def test_the_safety_net_timer_is_in_the_log(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1")
    assert r.rc == 0
    assert re.search(r"power-off safety net in \d+ min: timer: .*da-safety-net", r.log)


@pytest.mark.parametrize("vm", [G4, L4, GH])
def test_a_start_reclaimed_before_the_first_status_read_is_a_new_round(tmp_path: Path, vm: str) -> None:
    # R11: rc 0 with TERMINATED is a reclaimed Spot start, not "other, no retry"
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_PREEMPT=f"{vm}:1")
    assert r.rc == 0, r.log
    assert len(r.starts(vm)) == 2 and "reclaimed" in r.log
    assert_invariants(r)


@pytest.mark.parametrize("vm", [L4, GH])
def test_every_host_gets_the_preemption_check(tmp_path: Path, vm: str) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_PREEMPT=f"{vm}:2")
    assert r.rc == 0, r.log
    assert len(r.starts(vm)) == 2 and "(preempted)" in r.log
    assert_invariants(r)


def test_a_host_reclaimed_while_waiting_for_ssh_ends_the_session_as_preempted(tmp_path: Path) -> None:
    # R11: ssh_ready polled 20 x 55 s without a status read
    r = run(tmp_path, "p10-1", FAKE_SSH_DOWN=L4, FAKE_PREEMPT=f"{L4}:3")
    assert r.rc == 3, r.log
    assert "while waiting for SSH (reclaimed)" in r.log
    assert len(r.ssh(L4, "true")) == 1


# ------------------------------------------------------------------ detached steps and lost hosts (R10, R12)


def test_every_step_is_detached_and_polled_with_short_ssh_calls(tmp_path: Path) -> None:
    # R10: no step runs in the foreground of one long SSH call that a dropped connection would end unseen
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host")
    assert r.rc == 0, r.log
    assert not r.index(lambda c: c[2:4] == ["compute", "ssh"] and any("host_step.sh run " in a for a in c))
    for step in ("guest_up", "guest_prepare", "calibrate", "warmup", "sim_setup", "score_start_run1"):
        vm = {"guest_up": GH, "guest_prepare": GH, "score_start_run1": L4}.get(step, G4)
        start, status = r.ssh(vm, f"host_step.sh start {step} "), r.ssh(vm, f"host_step.sh status {step}")
        assert start and status and start[0] < status[0], step


def test_a_step_past_its_time_out_is_signalled_on_its_host_before_the_guests_stop(tmp_path: Path) -> None:
    # R10: the step still runs on its host when this host gives up; the guests' stop must not race a launch
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_HANG_STEP="guest_up:30", DA_T_T_GUEST_UP="1")
    assert r.rc == 5, r.log
    sig = r.ssh(GH, "host_step.sh signal guest_up TERM")
    assert sig and sig[0] < r.guest_stops()[0]
    # at the time-out itself, by rstep, not only later by the exit trap (which TERMs a step still running, S2)
    assert len(sig) == 1 and sig[0] < r.ssh(GH, "host_step.sh tail guest_up")[0]
    assert "after the TERM: rc 143" in r.log and "step guest_up rc=124" in r.log
    assert_invariants(r)


@pytest.mark.parametrize("step, more", [("guest_up", ()), ("guest_prepare", ())])
def test_a_signal_during_a_guest_step_signals_the_step_before_the_guests_stop(tmp_path: Path, step: str,
                                                                              more: tuple) -> None:
    # S2: a Ctrl-C, a kill or the cap during the guests' launch: the trap TERMs the running step on its host and
    # waits for its end before the S-CORE side's stop, the fetch and any guests' stop
    p = popen(tmp_path, "p10-3", "--owner-ok-guest-host", *more, FAKE_HANG_STEP=f"{step}:60")
    wait_for_call(tmp_path, lambda c: any(f"host_step.sh status {step}" in a for a in c))
    time.sleep(0.3)
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    sig = r.ssh(GH, f"host_step.sh signal {step} TERM")
    assert sig, r.log
    after = [i for i in r.ssh(GH, f"host_step.sh status {step}") if i > sig[0]]
    assert after and after[0] < r.guest_stops()[0] < r.stops(GH)[0]
    assert sig[0] < r.ssh(GH, "host_step.sh pack")[0]
    assert f"step {step} after the TERM: rc 143" in r.log
    assert_invariants(r)


def test_the_record_names_the_guest_launch_the_traps_term_cut(tmp_path: Path) -> None:
    # T1: a TERM during guest_up ends the launch (guest_up.sh awaits it and prints its own FAIL line); session.json
    # said only exit_code 143, so nothing named the launch that was cut
    fail = "FAIL launch ended by TERM (the launch's rc 143; its end awaited before this step ended; see launch.log)"
    p = popen(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_HANG_STEP="guest_up:60", FAKE_TERM_TAIL=f"guest_up:{fail}")
    wait_for_call(tmp_path, lambda c: any("host_step.sh status guest_up" in a for a in c))
    time.sleep(0.3)
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    tail = r.ssh(GH, "host_step.sh tail guest_up")
    assert tail and r.ssh(GH, "host_step.sh signal guest_up TERM")[0] < tail[0] < r.guest_stops()[0]
    assert f"step guest_up ended by the session's TERM: {fail}" in r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["step_ended_by_term"] == {"host": "guest", "step": "guest_up", "status_after_term": "rc 143",
                                         "fail_line": fail}
    assert_invariants(r)


def test_a_guest_step_alive_after_its_term_keeps_the_guest_host_running(tmp_path: Path) -> None:
    # S2: a launch that outlives its TERM may still create guests: a crosvm count of 0 then proves nothing
    p = popen(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_HANG_STEP="guest_up:60",
              FAKE_STEP_IGNORES_TERM="guest_up", DA_T_STEP_TERM_POLLS="2")
    wait_for_call(tmp_path, lambda c: any("host_step.sh status guest_up" in a for a in c))
    time.sleep(0.3)
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    assert r.rc == 11, r.log
    assert r.ssh(GH, "host_step.sh signal guest_up TERM") and r.guest_stops()
    assert not r.stops(GH) and r.state[GH] == "RUNNING"
    assert "step guest_up did not end after its TERM" in r.log
    assert r.stops(L4) and r.state[L4] == "TERMINATED"


def test_a_host_lost_mid_run_ends_the_session_at_once_and_is_not_fetched(tmp_path: Path) -> None:
    # R12: polls of a reclaimed G4 ran until T_RUN, then its fetch tried 600 + 1200 s
    t0 = time.monotonic()
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_LOST_AFTER=f"{G4}:world_calib_steer/go",
            DA_T_T_RUN="60")
    assert r.rc == 3, r.log
    assert time.monotonic() - t0 < 40
    go = r.ssh(G4, "world_calib_steer/go")[0]
    assert not [i for i in r.ssh(G4, "host_step.sh pack") if i > go]
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["ended_by"].startswith("host lost: sim") and f"sim: {OWED}" in rec["not_fetched"]
    assert r.ssh(L4, "run score_stop_on_failure")             # the S-CORE side still collected
    assert_invariants(r)


# ------------------------------------------------------------- the p10-1 session's report (R9, the reporting half)

P10_1_CHECKS = ["C1_launch_manager_config_and_start_order", "C2_alive_notifications", "C3_stalled_candidate_fallback",
                "C4_asil_b_command_path", "C5_gatewayd_receives_from_asil_b_process", "C6_cuda_pass_time",
                "C7_candidate_record_late_subscriber", "C8_candidate_on_a_replayed_clip"]


def _verdicts(tmp: Path, verdicts: dict[str, str]) -> str:
    """A p10_1_verdicts.json in p10_1_check.sh's form ({"checks": [{verdict, check, detail}]})."""
    f = tmp / "p10_1_verdicts.json"
    f.write_text(json.dumps({"checks": [{"verdict": v, "check": c, "detail": "d"} for c, v in verdicts.items()]}))
    return f"out/p10_1/p10_1_verdicts.json={f}"


def test_a_p10_1_session_names_its_not_run_checks_and_is_not_reported_passed(tmp_path: Path) -> None:
    # a p10-1 session without a CARLA server runs only the checks that need the S-CORE host alone: C1's full start
    # and C2-C4 need a CARLA server (C2-C4 a ticking world), C5 a receive line of gatewayd, C8 a replayer; the record
    # must never read as P10-1 passed
    (tmp_path / "v").mkdir()
    v = {c: "PASS" for c in P10_1_CHECKS}
    v.update({c: "NOT RUN" for c in P10_1_CHECKS if c[:2] in ("C1", "C2", "C3", "C4", "C5", "C8")})
    v["C6_cuda_pass_time"] = "FAIL"
    r = run(tmp_path, "p10-1", FAKE_PACK_ADD=_verdicts(tmp_path / "v", v))
    line = ("P10-1: 6 of 8 checks NOT RUN: C1_launch_manager_config_and_start_order, C2_alive_notifications, "
            "C3_stalled_candidate_fallback, C4_asil_b_command_path, C5_gatewayd_receives_from_asil_b_process, "
            "C8_candidate_on_a_replayed_clip; FAIL: C6_cuda_pass_time; P10-1 NOT passed")
    assert line in r.log, r.log
    rec = json.loads((r.incoming / "session.json").read_text())["p10_1"]
    assert rec["line"] == line and rec["passed"] is False and rec["fail"] == ["C6_cuda_pass_time"]
    assert [c[:2] for c in rec["not_run"]] == ["C1", "C2", "C3", "C4", "C5", "C8"]


def test_a_p10_1_session_with_every_check_passed_or_no_verdicts(tmp_path: Path) -> None:
    (tmp_path / "v").mkdir()
    r = run(tmp_path, "p10-1", FAKE_PACK_ADD=_verdicts(tmp_path / "v", {c: "PASS" for c in P10_1_CHECKS}))
    rec = json.loads((r.incoming / "session.json").read_text())["p10_1"]
    assert rec["passed"] is True and rec["line"] == "P10-1: 0 of 8 checks NOT RUN; P10-1 passed"
    r2 = run(tmp_path / "b", "p10-1")                        # no verdicts file in the fetched folder
    rec2 = json.loads((r2.incoming / "session.json").read_text())["p10_1"]
    assert rec2["passed"] is False and rec2["verdicts_file_fetched"] is False
    assert "P10-1: 8 of 8 checks NOT RUN" in r2.log and "P10-1 NOT passed" in r2.log
    r3 = run(tmp_path / "c", "p10-3", "--owner-ok-guest-host")
    assert json.loads((r3.incoming / "session.json").read_text())["p10_1"] is None


# ----------------------------------------------------------------------- the go bound, ids, the cap (R14, R20, R21)


def test_a_go_later_than_the_bound_after_the_score_start_is_refused(tmp_path: Path) -> None:
    # R14: the candidate's 420 s ready time-out; the steps between the S-CORE start and the go had no bound
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_HANG_STEP="unit_run1:3", DA_T_GO_LIMIT_S="1")
    assert r.rc == 5, r.log
    assert "INVALID RUN run1" in r.log and not r.ssh(G4, "world_run1/go")
    assert r.ssh(G4, "host_step.sh signal world_run1 TERM") and r.ssh(L4, "run score_stop_on_failure")
    assert "go of calib_steer" in r.log                      # the bound held for the run before
    assert_invariants(r)


def test_the_go_clock_starts_before_the_score_start_step(tmp_path: Path) -> None:
    # S5: the clock started only once the session had seen the start step end (poll latency, the tail call), while
    # the candidate's 420 s ready time-out runs from its process start inside that step
    r = run(tmp_path, "p10-2", "--without-guest-host", FAKE_HANG_STEP="score_start_run1:4", DA_T_GO_LIMIT_S="3")
    assert r.rc == 5, r.log
    assert "INVALID RUN run1" in r.log and not r.ssh(G4, "world_run1/go") and r.ssh(G4, "world_calib_steer/go")
    assert_invariants(r)


def test_a_session_id_of_an_archived_session_is_refused(tmp_path: Path) -> None:
    # R20: after the rule-15 rename incoming_T -> session1_..._T the id was free again
    (tmp_path / "ev" / "session1_p10-1_archived_T").mkdir(parents=True)
    r = run(tmp_path, "p10-1")
    assert r.rc == 2 and "is taken by" in r.stdout and not r.calls


@pytest.mark.parametrize("sid", ["x;touch PWN", "*", "T*", "../escape", ".hidden", "-T", "a b", "T$(id)"])
def test_a_session_id_outside_its_alphabet_is_refused(tmp_path: Path, sid: str) -> None:
    # S6: the id goes unquoted into remote commands (~/da-kit/<id>, mkdir, tar -C, the safety net's unit)
    args = [a if a != "T" else sid for a in args_for(tmp_path, "p10-1")]
    p = subprocess.run(args, env=env_for(tmp_path), capture_output=True, text=True, timeout=60)
    assert p.returncode == 2 and "refused: session id" in p.stdout, p.stdout + p.stderr
    assert not (tmp_path / "fake" / "calls.log").exists()
    assert not (tmp_path / "ev").exists() or not any((tmp_path / "ev").iterdir())
    assert not (tmp_path / "escape").exists() and not (tmp_path / "incoming_..").exists()


def test_a_session_id_with_a_kit_on_the_host_is_refused(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_KIT_EXISTS=L4)
    assert r.rc == 4 and "exists on de4sdv-probe-da8-carla" in r.log
    assert not r.ssh(L4, "host_step.sh start")
    assert_invariants(r)


@pytest.mark.parametrize("cap", ["6EUR", "0", "-1", "1e3"])
def test_the_cap_must_be_a_positive_number(tmp_path: Path, cap: str) -> None:
    # R21: "6EUR" wrote no session.json and made the watchdog compare strings
    r = run(tmp_path, "p10-1", "--cap-eur", cap)
    assert r.rc == 2 and "--cap-eur must be a positive number" in r.stdout and not r.calls


# ------------------------------------------------------------------------- the README's command lines (S3)


def _readme_commands() -> list[str]:
    """The command lines of the README's bash blocks, continuations joined, comments dropped."""
    text = (HERE.parent / "README.md").read_text()
    lines = []
    for block in re.findall(r"```bash\n(.*?)```", text, re.S):
        for line in block.replace("\\\n", " ").splitlines():
            code = line.strip()
            if code and not code.startswith("#"):
                lines.append(re.sub(r"\s+", " ", code))
    return lines


def test_the_readme_starts_sessions_only_from_a_clean_environment_in_a_unit_that_never_sigkills_the_trap() -> None:
    # S3: `nohup ... &` is refused by the lead's terminal tool, and systemd-run's defaults SIGKILL the exit trap 90 s
    # after a stop: no VM stopped, no session.json. S4: a session starts from env -i
    cmds = _readme_commands()
    sessions = [c for c in cmds if "da_session.sh" in c and "--dry-run" not in c]
    dry = [c for c in cmds if "da_session.sh" in c and "--dry-run" in c]
    assert {k for k in ("p10-1", "p10-3", "p10-2") if any(f"--kind {k}" in c for c in sessions)} == \
        {"p10-1", "p10-3", "p10-2"}
    assert {k for k in ("p10-1", "p10-3", "p10-2") if any(f"--kind {k}" in c for c in dry)} == \
        {"p10-1", "p10-3", "p10-2"}
    for c in sessions:
        assert c.startswith("systemd-run --user "), c
        for prop in ("-p KillMode=mixed", "-p TimeoutStopSec=infinity", "-p SendSIGHUP=no"):
            assert prop in c, (prop, c)
        assert "/usr/bin/env -i " in c and c.index("/usr/bin/env -i ") < c.index("da_session.sh"), c
    for c in dry:
        assert c.startswith("env -i "), c
    for c in cmds:
        assert "nohup" not in c and not c.endswith("&") and "kill -9" not in c and "-s KILL" not in c, c
    text = (HERE.parent / "README.md").read_text()
    assert "never `kill -9` a session" in text.lower()
    assert "systemctl list-unit-files | grep -i -E 'cvd|cuttlefish'" in text     # S1's assumption, checked once
    # T3 of the closure review of f67241db: the lead host's systemd 249 refuses --kill-whom; p10-1's block says
    # --kill-who=main
    p10_1 = text.split("### `p10-1`", 1)[1].split("\n### ", 1)[0]
    assert "systemctl --user kill --kill-who=main -s TERM da-session-$SID" in p10_1 and "--kill-whom" not in p10_1


def test_the_readme_p10_1_block_sets_c_and_stops_when_the_cd_fails() -> None:
    # T5 of the closure review of f67241db, for p10-1: in a new shell C is empty, the cd fails and the block went on in
    # the current directory, whose HEAD the session then shipped
    text = (HERE.parent / "README.md").read_text()
    block = text.split("### `p10-1`", 1)[1].split("\n### ", 1)[0]
    (body,) = re.findall(r"```bash\n(.*?)```", block, re.S)
    code = [re.sub(r"\s+", " ", line.strip()) for line in body.replace("\\\n", " ").splitlines()
            if line.strip() and not line.strip().startswith("#")]
    assert code[0].startswith("C="), code[0]
    (cd,) = [c for c in code if c.startswith("cd ")]
    assert cd.startswith("cd /home/mrk/de4sdv-worktrees/p10-$C") and re.search(r"\|\| exit 1(\s|$)", cd), cd


# ------------------------------------------------- the review's surviving mutants Y12-Y16 (S12; Y02 above, with S1)


def _hosts_env(*names: str) -> list[str]:
    out = subprocess.run(["bash", "-c", '. "$1/hosts.env"; shift; for n; do printf "%s\\n" "${!n}"; done', "_",
                          str(HERE.parent), *names], capture_output=True, text=True, check=True,
                         env={"PATH": os.environ["PATH"]}).stdout
    return out.splitlines()


def test_the_safety_net_fires_at_the_cap_plus_the_pre_stop_bound_plus_its_margin(tmp_path: Path) -> None:
    # Y12: a deadline far after the cap passed every test; it is (CAP_S + the kind's pre-stop budget) / 60 + 10 min
    # from the arming (P1: the budget is the sum of the trap's step bounds, test_p1_...)
    r = run(tmp_path, "p10-1")
    assert r.rc == 0, r.log
    cap, sim_h, score_h = (float(x) for x in _hosts_env("CAP_EUR_P10_1", "SIM_EUR_H", "SCORE_EUR_H"))
    pre = _prestop_sums("p10-1", dict(_prestop_defaults(), POLL_S=1))["total"]
    gmin = (int(cap / (sim_h + score_h) * 3600) + pre) // 60 + 10
    for vm in (G4, L4):
        (arm,) = [r.command(i) for i in r.ssh(vm, "safety_net.sh arm")]
        assert re.search(rf"safety_net\.sh arm {gmin}$", arm), (vm, arm, gmin)
    assert f"power-off safety net in {gmin} min" in r.log


def test_the_default_go_bound_is_380_s_and_leaves_room_for_the_go_call(tmp_path: Path) -> None:
    # Y13: the tests always set DA_T_GO_LIMIT_S, so a default of 3800 s passed; 380 s + the go's SSH call (35 s at
    # most) stay under the candidate's 420 s ready time-out
    r = run(tmp_path, "p10-2", "--without-guest-host")
    assert r.rc == 0, r.log
    m = re.findall(r"go of \w+ \d+ s after the S-CORE side's start step began \(limit (\d+) s, the go's SSH call at "
                   r"most (\d+) s\)", r.log)
    assert m and all(int(a) == 380 and int(a) + int(b) < 420 for a, b in m), m
    gos = [c for c in (r.incoming / "commands.log").read_text().splitlines() if re.search(r"touch \S+/go &&", c)]
    assert len(gos) == 3 and all(c.endswith("[timeout 35 s]") for c in gos), gos


def test_a_session_id_named_only_in_an_archived_session_json_is_refused(tmp_path: Path) -> None:
    # Y14: only the folder-name form was tested
    d = tmp_path / "ev" / "session7_p10-3_renamed"
    d.mkdir(parents=True)
    (d / "session.json").write_text(json.dumps({"session_id": "T", "kind": "p10-3"}, indent=1))
    r = run(tmp_path, "p10-1")
    assert r.rc == 2 and "is taken by" in r.stdout and str(d) in r.stdout and not r.calls


def test_the_traps_fetch_packs_within_120_s_and_copies_within_300_s(tmp_path: Path) -> None:
    # Y15: the trap's fetch with the defaults of the end-of-session fetch (600 s pack, 1200 s copy) passed every test
    p = popen(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_HANG_STEP="inject:30")
    wait_for_call(tmp_path, lambda c: any("start inject" in a for a in c))
    time.sleep(0.5)
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    cmds = (r.incoming / "commands.log").read_text().splitlines()
    packs = [c for c in cmds if "host_step.sh pack" in c]
    copies = [c for c in cmds if " + scp " in c and c.split(" [timeout")[0].endswith("/")
              and "out.tgz" in c]
    assert len(packs) == 2 and all(c.endswith("[timeout 120 s]") for c in packs), packs
    assert len(copies) == 2
    for c in copies:
        t = int(re.search(r"\[timeout (\d+) s\]$", c).group(1))
        assert 200 <= t <= 300, c


@pytest.mark.parametrize("status", ["STOPPING", "TERMINATED"])
def test_a_guest_host_found_stopping_in_the_trap_is_stopped_without_a_count(tmp_path: Path, status: str) -> None:
    # Y16: a guest host that is shutting down runs no guest: its stop goes out, with no SSH count it could not get
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_LOST_AFTER=f"{GH}:start capture_inject",
            FAKE_LOST_STATUS=status)
    assert r.rc == 3, r.log
    assert f"guest host status {status}: no guest can run there" in r.log
    assert r.stops(GH) and r.state[GH] == "TERMINATED" and not r.guest_stops()
    assert_invariants(r)


def _readme_block(kind: str) -> list[str]:
    """The lines (comments kept) of the bash block under the README's heading for <kind>."""
    text = (HERE.parent / "README.md").read_text()
    m = re.search(r"^### `" + re.escape(kind) + r"`.*?\n```bash\n(.*?)```", text, re.S | re.M)
    assert m, kind
    return [re.sub(r"\s+", " ", ln.strip()) for ln in m.group(1).replace("\\\n", " ").splitlines() if ln.strip()]


def test_the_readme_p10_3_block_runs_permissive_from_its_start() -> None:
    # T2: the lead's decision of 2026-11-19: p10-3 runs with --permissive-ivi from its start (B12's Enforcing run
    # failed the Gateway lookup on the same images); an Enforcing p10-3 only costs a session
    lines = [c for c in _readme_block("p10-3") if "da_session.sh" in c and not c.startswith("#")]
    assert len(lines) == 2 and any("--dry-run" in c for c in lines), lines
    assert all("--kind p10-3 --owner-ok-guest-host --permissive-ivi" in c for c in lines), lines
    text = (HERE.parent / "README.md").read_text()
    assert "conditional on a permissive IVI" in text and "getenforce" in text


def test_the_readme_p10_2_block_runs_permissive_from_its_start() -> None:
    # R2 of the closure check of 7befc3c1, the lead's decision of 2026-11-19: p10-2 runs the IVI guest permissive,
    # as p10-3 does. Its unit gate and app_restart wait for the IVI app's own SUBSCRIBED line, and the app's Gateway
    # lookup fails under Enforcing on these images (B12), so an Enforcing p10-2 ends at unit_run1
    lines = [c for c in _readme_block("p10-2") if "da_session.sh" in c and not c.startswith("#")]
    assert len(lines) == 2 and sum("--dry-run" in c for c in lines) == 1, lines
    assert all("--kind p10-2 --owner-ok-guest-host --permissive-ivi" in c for c in lines), lines
    block = " ".join(_readme_block("p10-2"))
    assert "conditional on a permissive IVI" in block, block


def test_p10_2_with_permissive_ivi_marks_the_session_and_its_report(tmp_path: Path) -> None:
    # R2: the README's p10-2 line as written; every result is conditional on a permissive IVI, in session.json and in
    # its p10_2 report
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", "--permissive-ivi")
    assert r.rc == 0, r.log
    assert r.sequence() == p10_2_seq(), r.sequence()
    for step in ("start guest_up", "start guest_prepare"):
        assert "IVI_PERMISSIVE=1" in r.command(r.ssh(GH, step)[0])
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["conditional_on_permissive_ivi"] is True
    assert rec["p10_2"]["conditional_on_permissive_ivi"] is True, rec["p10_2"]
    assert "conditional on a permissive IVI" in r.log
    assert re.search(r"p10-2 display recording complete: .*\(conditional on a permissive IVI\)", r.log), r.log
    r2 = run(tmp_path / "b", "p10-2", "--owner-ok-guest-host")
    rec2 = json.loads((r2.incoming / "session.json").read_text())
    assert rec2["conditional_on_permissive_ivi"] is False and rec2["p10_2"]["conditional_on_permissive_ivi"] is False


def test_r8_abort_ends_a_step_alive_after_its_time_out_before_any_fetch(tmp_path: Path) -> None:
    # R8 of the closure check of 7befc3c1: after its own time-out rstep keeps a step still alive in CUR_STEP and
    # aborts; abort() fetched before the trap's step_down sent the TERM again and waited, so a late-ending step's last
    # records missed the fetch. Now abort() runs step_down first
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_HANG_STEP="guest_up:30", DA_T_T_GUEST_UP="1",
            FAKE_STEP_IGNORES_TERM="guest_up", DA_T_STEP_TERM_POLLS="2")
    assert r.rc == 11, r.log
    sig = r.ssh(GH, "host_step.sh signal guest_up TERM")
    pack = r.ssh(GH, "host_step.sh pack")
    assert len(sig) == 2 and pack and sig[1] < pack[0], (sig, pack)


def test_the_readme_p10_2_block_takes_the_camera_calibration_from_the_settings() -> None:
    # the lead's decision of 2026-11-19 (owner informed): CARLA 1.0's apply_texture never reaches the engine plane's
    # material (CarlaGameModeBase.cpp:505-548 at 14ac3b1a50), so the boards render flat grey and upstream's script
    # finds 0 boards; p10-2's H.yaml comes from the simulated camera's settings, chosen by the flag only
    lines = [c for c in _readme_block("p10-2") if "da_session.sh" in c and not c.startswith("#")]
    assert len(lines) == 2 and sum("--dry-run" in c for c in lines) == 1, lines
    assert all("--kind p10-2 --owner-ok-guest-host --permissive-ivi --camcal settings" in c for c in lines), lines
    block = " ".join(_readme_block("p10-2"))
    assert "CarlaGameModeBase.cpp:505-548" in block and "gapCameraImageAndGeometry" in block, block


def test_p10_2_with_camcal_settings_makes_h_from_the_settings_and_records_why(tmp_path: Path) -> None:
    # the README's p10-2 line as written: calibrate keeps the capture with its pre-check recorded only, make-h runs
    # with --source settings, and session.json and its p10_2 report name the source, the reason and the cross-check
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", "--permissive-ivi", "--camcal", "settings")
    assert r.rc == 0, r.log
    assert r.sequence() == p10_2_seq(), r.sequence()
    cal = r.command(r.ssh(G4, "start calibrate")[0])
    assert re.search(r"calibrate\.sh \S+/calibrate settings$", cal), cal
    made = json.loads((r.incoming / "camcal" / "h" / "camera_calibration_record.json").read_text())
    assert made["source"] == "settings", made
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["camera_calibration_source"] == "settings"
    assert "CarlaGameModeBase.cpp:505-548" in rec["camera_calibration_source_reason"]
    assert rec["camera_calibration_cross_check"] == "not run: no board rendered"
    for k in ("camera_calibration_source", "camera_calibration_source_reason", "camera_calibration_cross_check"):
        assert rec["p10_2"][k] == rec[k], rec["p10_2"]
    assert re.search(r"p10-2 camera calibration source: settings \(.*CarlaGameModeBase\.cpp:505-548.*\); "
                     r"cross-check: not run: no board rendered", r.log), r.log
    # the default: upstream's procedure on the frame, its pre-check enforced, as before
    r2 = run(tmp_path / "b", "p10-2", "--owner-ok-guest-host", "--permissive-ivi")
    assert r2.rc == 0 and r2.sequence() == p10_2_seq()
    assert re.search(r"calibrate\.sh \S+/calibrate checkerboard$", r2.command(r2.ssh(G4, "start calibrate")[0]))
    rec2 = json.loads((r2.incoming / "session.json").read_text())
    assert rec2["camera_calibration_source"] == "checkerboard" and rec2["p10_2"]["camera_calibration_source"] == \
        "checkerboard"
    made2 = json.loads((r2.incoming / "camcal" / "h" / "camera_calibration_record.json").read_text())
    assert made2["source"] == "checkerboard"


@pytest.mark.parametrize("more, needle", [
    (("--kind", "p10-2", "--owner-ok-guest-host", "--camcal", "guess"), "--camcal takes checkerboard or settings"),
    (("--kind", "p10-3", "--owner-ok-guest-host", "--camcal", "settings"), "--camcal is for p10-2 only"),
])
def test_camcal_refusals_before_any_start(tmp_path: Path, more: tuple, needle: str) -> None:
    r = run(tmp_path, more[1], *more[2:])
    assert r.rc == 2, r.stdout + r.log
    assert needle in r.stdout + r.log
    assert not r.index(lambda c: "start" in c or "stop" in c)


def test_p10_2_make_h_whose_record_names_another_source_ends_the_session(tmp_path: Path) -> None:
    # never a silent fallback: the record of make-h must name the source the flag chose, or the session ends at make_h
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", "--camcal", "settings", STUB_MAKE_H_SOURCE="checkerboard")
    assert r.rc == 5, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["failed_step"] == "make_h"
    assert "make_h: the record names the source checkerboard, not --camcal settings" in r.log
    assert not r.ssh(L4, "start score_start_")


def test_the_readme_ends_a_session_early_with_the_spelling_systemd_249_knows() -> None:
    # T3: the lead host's systemd 249 refuses --kill-whom ("unrecognized option"); --kill-who works there
    text = (HERE.parent / "README.md").read_text()
    assert "--kill-whom" not in text
    for kind in ("p10-1", "p10-3", "p10-2"):
        assert any("systemctl --user kill --kill-who=main -s TERM da-session-$SID" in c for c in _readme_block(kind)), kind


def test_the_readme_p10_3_and_p10_2_blocks_set_c_and_stop_when_the_cd_fails() -> None:
    # T5: in a new shell C is empty, the cd failed and the block went on in the current directory, whose HEAD the
    # session then shipped
    for kind in ("p10-3", "p10-2"):
        code = [c for c in _readme_block(kind) if not c.startswith("#")]
        assert code[0].startswith("C="), (kind, code[0])
        (cd,) = [c for c in code if c.startswith("cd ")]
        assert cd.startswith("cd /home/mrk/de4sdv-worktrees/p10-$C") and re.search(r"\|\| exit 1(\s|$)", cd), cd


def test_the_readme_says_exit_0_of_p10_3_alone_is_not_a_pass() -> None:
    # T4
    block = " ".join(_readme_block("p10-3"))
    assert "exit 0 alone is not a pass" in block and "p10_3.passed" in block


# ------------------------------------------------- the display capture of a window the session leaves (Q1-Q4)
# The fake models the guest host's captures (FAKE_CAPTURE_END in fake_gcloud.py): a pack while a capture records
# holds only its seg_1.pending and a growing seg_1.mp4.part; after its stop, capture.json, capture.done, the app
# record and the segment.


def _guest_files(r: Run) -> set[str]:
    with tarfile.open(r.incoming / "guest" / "out.tgz") as t:
        return set(t.getnames())


def _capture_stops(r: Run, w: str) -> list[int]:
    return r.index(lambda c: c[2:4] == ["compute", "ssh"] and c[4] == GH and any(
        "display_capture.sh stop $HOME/da-kit/T/out/capture_%s " % w in a + " " for a in c))


def _assert_capture_stopped_before_the_fetch(r: Run, w: str) -> None:
    stops, pack = _capture_stops(r, w), r.ssh(GH, "host_step.sh pack")
    assert stops and pack and stops[0] < pack[0] < r.guest_stops()[0], (stops, pack, r.log)
    got = _guest_files(r)
    cap = "out/capture_%s/" % w
    assert {cap + "capture.json", cap + "app_record_warning.jsonl"} <= got, sorted(got)
    assert got & {cap + "seg_1.mp4", cap + "seg_1.mp4.part", cap + "seg_1.mp4.partial"}, sorted(got)
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["display_capture"][w]["closed_by"] == "session end", rec["display_capture"]
    assert rec["p10_2"]["display_recording_complete"] is False and w in rec["p10_2"]["reason"], rec["p10_2"]


def test_q1_a_run_end_that_never_comes_still_stops_the_open_capture_before_the_guest_fetch(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_NO_FILE="world_run1/simulator/run_end", DA_T_T_RUN="1")
    assert r.rc == 5 and "the run run1 did not end" in r.log, r.log
    _assert_capture_stopped_before_the_fetch(r, "run1")
    assert "the display capture of window run1 is still open" in r.log, r.log
    assert_invariants(r)


def test_q1_a_term_inside_a_window_stops_its_capture_before_the_guest_fetch(tmp_path: Path) -> None:
    p = popen(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_NO_FILE="world_run1/simulator/run_end")
    wait_for_call(tmp_path, lambda c: any("start capture_run1 " in a for a in c), timeout=120)
    time.sleep(0.5)
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    _assert_capture_stopped_before_the_fetch(r, "run1")
    assert_invariants(r)


def test_q1_the_cost_cap_inside_a_window_stops_its_capture_before_the_guest_fetch(tmp_path: Path) -> None:
    p = popen(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_NO_FILE="world_run1/simulator/run_end")
    wait_for_call(tmp_path, lambda c: any("start capture_run1 " in a for a in c), timeout=120)
    time.sleep(0.5)
    # the cap, reached now: a start line that costs more than the cap at once (the watchdog sums starts.tsv)
    with open(tmp_path / "ev" / "incoming_T" / "starts.tsv", "a") as f:
        f.write("captest 0 1000000000\n")
    r = finish(tmp_path, p)
    assert r.rc == 10 and "COST CAP reached" in r.log, r.log
    _assert_capture_stopped_before_the_fetch(r, "run1")
    assert_invariants(r)


def test_q2_a_capture_error_is_recorded_and_skips_neither_the_receipts_nor_the_next_run(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_CAPTURE_END="capture_run1:error",
            FAKE_STEP_RC="capture_run1:1")
    assert r.rc == 0, r.log
    assert r.sequence() == p10_2_seq(), r.sequence()
    rec = json.loads((r.incoming / "session.json").read_text())
    # R7 of the closure check of 7befc3c1: the recorded capture error is the window's result, not a failed step of a
    # session that went on and ended 0 (session.json named capture_run1 as failed_step)
    assert rec["exit_code"] == 0 and rec["failed_step"] is None, (rec["exit_code"], rec["failed_step"])
    assert rec["display_capture"]["run1"] == {"end": "error", "capture_rc": 1, "closed_by": "window close",
                                              "guest_files_kept": False}, rec["display_capture"]
    assert rec["display_capture"]["run2"]["end"] == "stop" and rec["display_capture"]["run2"]["capture_rc"] == 0
    assert rec["app_record_receipts"] == {"run1": 2, "run2": 2}, rec["app_record_receipts"]
    assert rec["p10_2"]["display_recording_complete"] is False, rec["p10_2"]
    assert "run1" in rec["p10_2"]["reason"] and "error" in rec["p10_2"]["reason"], rec["p10_2"]
    assert "DISPLAY CAPTURE ERROR IN WINDOW run1" in r.log and "p10-2 display recording NOT complete" in r.log


def test_q2_a_good_p10_2_reports_the_recording_complete_and_without_guest_host_none(tmp_path: Path) -> None:
    r = run(tmp_path / "a", "p10-2", "--owner-ok-guest-host")
    assert r.rc == 0, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert set(rec["display_capture"]) == {"run1", "run2"}
    assert all(v == {"end": "stop", "capture_rc": 0, "closed_by": "window close", "guest_files_kept": False}
               for v in rec["display_capture"].values()), rec["display_capture"]
    assert rec["p10_2"]["display_recording_complete"] is True, rec["p10_2"]
    r2 = run(tmp_path / "b", "p10-2", "--without-guest-host")
    rec2 = json.loads((r2.incoming / "session.json").read_text())
    assert rec2["display_capture"] == {} and rec2["p10_2"]["display_recording_complete"] is None, rec2["p10_2"]
    assert "--without-guest-host" in rec2["p10_2"]["reason"]


def _session_defaults() -> dict[str, int]:
    text = SESSION.read_text()
    return {k: int(re.search(r"\b%s=(\d+)\b" % k, text).group(1))
            for k in ("T_CAPTURE_END", "POLL_S", "GO_SSH_S", "T_RUN", "T_SCORE_START", "T_RELEASE", "T_REC_END",
                      "T_INJECT")}


def _cap_sums(d: dict[str, int]) -> dict[str, int]:
    """The test's own sums (Q3, Q4). The stop's cap: T_CAPTURE_END less rstep's start SSH call (60 s), the stop's own
    last poll and exit (2 s), one status poll's SSH call (60 s) and POLL_S. A window's worst case, every step inside
    it ending well at its bound: each rwait/rwaitfile its bound + POLL_S + one poll's SSH call; each rstep its start
    SSH call + its bound + POLL_S + one poll + its tail call; each touch its SSH bound; then capture_stop's start."""
    p, poll = d["POLL_S"], 60
    step = lambda t: 60 + t + p + poll + 60   # noqa: E731
    wait = lambda t: t + p + poll             # noqa: E731
    return {"wait_cap": d["T_CAPTURE_END"] - 60 - 2 - poll - p,
            "p10-2": d["GO_SSH_S"] + wait(d["T_RUN"]) + step(d["T_SCORE_START"]) + 60 + wait(d["T_RELEASE"])
            + wait(d["T_REC_END"]) + 60,
            "p10-3": step(d["T_INJECT"]) + 60}


@pytest.mark.parametrize("kind", ["p10-2", "p10-3"])
def test_q3_q4_the_capture_gets_its_caps_from_the_sessions_bounds(tmp_path: Path, kind: str) -> None:
    r = run(tmp_path, kind, "--owner-ok-guest-host")
    assert r.rc == 0, r.log
    d = dict(_session_defaults(), POLL_S=1)   # the dry run's POLL_S 0.1, counted as a whole second
    want = _cap_sums(d)
    w = "run1" if kind == "p10-2" else "inject"
    start = r.command(r.ssh(GH, "start capture_%s " % w)[0])
    stop = r.command(r.ssh(GH, "start capture_stop_%s " % w)[0])
    assert start.endswith("display_capture.sh start $HOME/da-kit/T/out/capture_%s --max-s %d" % (w, want[kind])), start
    assert stop.endswith("display_capture.sh stop $HOME/da-kit/T/out/capture_%s --wait-cap-s %d"
                         % (w, want["wait_cap"])), stop


def test_q3_q4_the_readme_shows_both_sums_at_the_sessions_defaults() -> None:
    want = _cap_sums(_session_defaults())
    readme = (HERE.parent / "README.md").read_text()
    assert re.search(r"= --wait-cap-s +(\d+) s", readme).group(1) == str(want["wait_cap"])
    assert re.search(r"= --max-s of a p10-2 window +(\d+) s", readme).group(1) == str(want["p10-2"])
    assert re.search(r"= --max-s of the p10-3 window +(\d+) s", readme).group(1) == str(want["p10-3"])


# ───────────── P1: the exit trap's pre-stop phase holds each of its steps at its bound ─────────────
def _prestop_sums(kind: str, d: dict[str, int]) -> dict[str, int]:
    """The test's own pre-stop budget (P1): the running step's end (its TERM's call 60 s, STEP_TERM_POLLS waits of
    POLL_S, the last poll 60 s, its tail 60 s); the open window's capture stop (guest kinds: T_CAPTURE_END, then its
    status poll 60 s); the S-CORE side's stop (TRAP_SCORE_S); the world side's end (sim kinds: its release and TERM
    call 60 s, 3 polls of 60 s and POLL_S); each host's fetch (TRAP_PACK_S + TRAP_SCP_S)."""
    hosts = {"p10-1": ["sim", "score"], "p10-3": ["score", "guest"], "p10-2": ["sim", "score", "guest"],
             "p10-2-without-guest": ["sim", "score"]}[kind]
    p = d["POLL_S"]
    parts = {"step": 60 + d["STEP_TERM_POLLS"] * p + 60 + 60, "score": d["TRAP_SCORE_S"],
             "fetch": len(hosts) * (d["TRAP_PACK_S"] + d["TRAP_SCP_S"])}
    if "guest" in hosts:
        parts["capture"] = d["T_CAPTURE_END"] + 60
    if "sim" in hosts:
        parts["world"] = 60 + 3 * (60 + p)
    parts["total"] = sum(parts.values())
    return parts


def _prestop_defaults() -> dict[str, int]:
    text = SESSION.read_text()
    return {k: int(re.search(r"\b%s=(\d+)\b" % k, text).group(1))
            for k in ("T_CAPTURE_END", "POLL_S", "STEP_TERM_POLLS", "TRAP_SCORE_S", "TRAP_PACK_S", "TRAP_SCP_S")}


_KIND_ARGS = {"p10-1": ("p10-1",), "p10-3": ("p10-3", "--owner-ok-guest-host"),
              "p10-2": ("p10-2", "--owner-ok-guest-host"), "p10-2-without-guest": ("p10-2", "--without-guest-host")}


@pytest.mark.parametrize("kind", list(_KIND_ARGS))
def test_p1_the_pre_stop_phase_is_the_sum_of_its_steps_bounds_and_the_safety_net_holds_it(tmp_path: Path,
                                                                                          kind: str) -> None:
    # P1: PRESTOP_S was 300 s for every kind, while capture_down alone may use T_CAPTURE_END 240 s of it: with the
    # capture's and the S-CORE side's stops at their bounds the guest host's fetch was skipped. The phase is now the
    # sum of the bounds of every step the trap runs before a VM stops, per kind, and the safety net counts it
    r = run(tmp_path, *_KIND_ARGS[kind])
    assert r.rc == 0, r.log
    want = _prestop_sums(kind, dict(_prestop_defaults(), POLL_S=1))   # the dry run's POLL_S 0.1 as a whole second
    m = re.search(r"pre-stop budget: (\d+) s \(([^)]*)\)", r.log)
    assert m and int(m.group(1)) == want["total"], (m and m.group(0), want)
    for k, v in want.items():
        if k != "total":
            assert "%s %d" % (k, v) in m.group(2), (k, v, m.group(2))
    cap_s = int(re.search(r"the cap of [0-9.]+ EUR is (\d+) s", r.log).group(1))
    gmin = (cap_s + want["total"]) // 60 + 10
    assert re.findall(r"power-off safety net in (\d+) min", r.log) and \
        set(re.findall(r"power-off safety net in (\d+) min", r.log)) == {str(gmin)}, (gmin, r.log)


def test_p1_the_readme_shows_the_pre_stop_sums_of_every_kind_at_the_sessions_defaults() -> None:
    readme = (HERE.parent / "README.md").read_text()
    d = _prestop_defaults()
    for kind, label in (("p10-1", "p10-1"), ("p10-3", "p10-3"), ("p10-2", "p10-2 with the guest host"),
                        ("p10-2-without-guest", "p10-2 --without-guest-host")):
        m = re.search(r"\| %s \| (\d+) s \|" % re.escape(label), readme)
        assert m and int(m.group(1)) == _prestop_sums(kind, d)["total"], (label, m and m.group(0))


def test_p1_with_the_capture_and_score_stops_at_their_bounds_the_guest_host_is_still_fetched(tmp_path: Path) -> None:
    # P1: a TERM inside a recorded window whose capture stop and S-CORE stop both run to their bounds: each is cut at
    # its own bound, the world side gets its release, and the guest host is still packed and fetched before the
    # guests' stop
    p = popen(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_NO_FILE="world_run1/simulator/run_end",
              FAKE_HANG_STEP="capture_down1_run1:120,score_stop_on_failure:120",
              DA_T_T_CAPTURE_END="8", DA_T_TRAP_SCORE_S="6")
    wait_for_call(tmp_path, lambda c: any("start capture_run1 " in a for a in c), timeout=120)
    time.sleep(0.5)
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p, timeout=150)
    assert r.rc == 143, r.log
    cmds = (r.incoming / "commands.log").read_text()
    assert re.search(r"run capture_down1_run1 -- .* \[timeout 8 s\]", cmds), cmds
    assert re.search(r"run score_stop_on_failure -- .* \[timeout 6 s\]", cmds), cmds
    t_cap = _call_times(tmp_path, lambda c: any("run capture_down1_run1" in a for a in c))
    t_score = _call_times(tmp_path, lambda c: any("run score_stop_on_failure" in a for a in c))
    t_pack = _call_times(tmp_path, lambda c: c[2:4] == ["compute", "ssh"] and c[4] == GH
                         and any("host_step.sh pack" in a for a in c))
    assert t_cap and t_score and t_pack and t_cap[0] + 7 < t_score[0] and t_score[0] + 5 < t_pack[0], \
        (t_cap, t_score, t_pack)
    assert r.ssh(GH, "host_step.sh pack")[0] < r.guest_stops()[0]
    rec = json.loads((r.incoming / "session.json").read_text())
    assert set(rec["fetched"]) == {"sim", "score", "guest"} and rec["not_fetched"] == [], rec
    assert rec["display_capture"]["run1"]["closed_by"] == "session end", rec["display_capture"]
    assert "pre-stop phase's bound reached" not in r.log, r.log
    assert_invariants(r)


# ------------------------------------------------------- F2 of the first recorded p10-2: speed_limit per run
# The model (PSR VisionPilotSCOREApplication) asks that speed_limit be set per scenario by System 2. The setting
# SC-DRIVING-012@20 has the tolerance 20 to 22 km/h (world-side/scenarios.py, the model's settings); its middle,
# 21 km/h, is 5.833 m/s. calib_steer (ASM-DRIVING-006 on that setting's road and vehicle) takes the same value.
SPEED_20 = 5.833


def test_p10_2_sets_each_runs_speed_limit_from_its_setting_and_records_it(tmp_path: Path) -> None:
    staged = ("SCORE_CONFIG speed_limit=5.833 speed_limit_requested=5.833 hero_wait_s=400.0 source.mode=score "
              "engine.provider=cuda model.precision=fp32 visualization_on=false rrd_on=true conf_sha256=" + "a" * 64
              + " conf_recorded=1")
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_TAIL_ADD=f"score_start_run1:{staged}")
    assert r.rc == 0, r.log
    starts = r.ssh(L4, "start score_start_")
    assert len(starts) == 3
    for i in starts:
        assert f"DA_SPEED_LIMIT={SPEED_20}" in r.command(i).split(), r.command(i)
    rec = json.loads((r.incoming / "session.json").read_text())
    runs = rec["score_runs"]
    assert set(runs) == {"calib_steer", "run1", "run2"}, runs
    for w in runs:
        assert runs[w]["setting"] == "SC-DRIVING-012@20" and runs[w]["speed_limit_mps"] == SPEED_20, runs[w]
        assert "20" in runs[w]["speed_limit_source"] and "22" in runs[w]["speed_limit_source"], runs[w]
    assert runs["run1"]["staged"]["speed_limit"] == "5.833" and runs["run1"]["staged"]["hero_wait_s"] == "400.0"
    assert runs["run1"]["staged"]["conf_recorded"] == "1"
    # the stub start printed no SCORE_CONFIG line for the other runs: recorded as unknown, never guessed
    assert runs["run2"]["staged"] is None and runs["calib_steer"]["staged"] is None
    assert "speed_limit 5.833 m/s for run1" in r.log


def test_p10_2_a_staged_conf_without_the_runs_speed_limit_ends_the_session_before_the_go(tmp_path: Path) -> None:
    staged = "SCORE_CONFIG speed_limit=33.3 speed_limit_requested=5.833 hero_wait_s=400.0 conf_recorded=1"
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_TAIL_ADD=f"score_start_calib_steer:{staged}")
    assert r.rc == 5, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["failed_step"] == "score_start_calib_steer", rec["failed_step"]
    assert "does not carry the run's speed limit" in r.log
    assert not r.ssh(G4, "world_calib_steer/go")
    assert_invariants(r)


# ------------------------------------------- F3 of the first recorded p10-2: the Rerun records stay on the host
# The rate: calib_steer's visionpilot.rrd, 4,729,613,610 B in 542 passes (score_interface.jsonl), so 8,726,224 B a
# pass, at most 10 passes a second (the front camera's sensor_tick 0.1 s), rounded up to 88 MB per second of
# candidate running. A run's planned running: its setting's run cap (scenarios.py: 60 s for SC-DRIVING-012@20 since the
# S1 build of 2026-11-20 cut the SC-DRIVING-012 caps from 90 s) plus 60 s of hold until its S-CORE stop. The budget:
# the rate times the running seconds, plus 10 % and 5 GB.
RRD_RATE = 88_000_000
RUN_CAP_012_20_S = 60
RUN_RUNNING_S = RUN_CAP_012_20_S + 60


def _budget(seconds: int) -> int:
    return RRD_RATE * seconds * 11 // 10 + 5_000_000_000


def test_p10_2_checks_the_score_hosts_disk_for_every_runs_rerun_record_first(tmp_path: Path) -> None:
    out = subprocess.run(["python3", str(HERE.parent / "run_setting.py"), "SC-DRIVING-012", "20kmh"],
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0 and float(out.stdout.split()[2]) == RUN_CAP_012_20_S, out.stdout + out.stderr
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host",
            FAKE_TAIL_ADD="disk_check:DISK_CHECK ok need_bytes=1 avail_bytes=2 same_filesystem=1")
    assert r.rc == 0, r.log
    check = r.ssh(L4, "start disk_check")
    assert check and check[0] < r.ssh(G4, "start sim_setup")[0]
    words = r.command(check[0]).split()
    assert words[-2:] == [str(_budget(3 * RUN_RUNNING_S)), str(_budget(RUN_RUNNING_S))], words
    rec = json.loads((r.incoming / "session.json").read_text())
    d = rec["score_disk_check"]
    assert d["rate_bytes_per_s"] == RRD_RATE and d["need_bytes"] == _budget(3 * RUN_RUNNING_S)
    assert d["planned_running_s"] == {"calib_steer": RUN_RUNNING_S, "run1": RUN_RUNNING_S, "run2": RUN_RUNNING_S}
    assert d["rc"] == 0 and d["result"] == {"need_bytes": "1", "avail_bytes": "2", "same_filesystem": "1"}, d
    assert rec["score_runs"]["run1"]["planned_running_s"] == RUN_RUNNING_S


def test_p10_2_a_short_disk_ends_the_session_named_before_any_run(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_STEP_RC="disk_check:9")
    assert r.rc == 5, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["failed_step"] == "disk_check" and rec["score_disk_check"]["rc"] == 9, rec["failed_step"]
    assert "DISK SPACE SHORT on de4sdv-probe-da8-carla" in r.log
    assert not r.ssh(G4, "start sim_setup") and not r.ssh(G4, "start world_")
    assert_invariants(r)


def test_p10_2_records_each_runs_rerun_record_kept_on_the_score_host(tmp_path: Path) -> None:
    rrd = [{"path": "/home/x/da-kit/T/out/score_run1/score_side/vision_pilot/visionpilot.rrd", "bytes": 4729613610,
            "sha256": "b" * 64, "stage_path": "/tmp/de4sdv-da-bench/vision_pilot/visionpilot.rrd",
            "collected_as": "hard link"}]
    f = tmp_path / "rrd.json"
    f.write_text(json.dumps(rrd))
    ex = tmp_path / "ex.tsv"
    ex.write_text("out/score_run1/score_side/vision_pilot/visionpilot.rrd\t4729613610\n")
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host",
            FAKE_PACK_ADD=f"out/score_run1/candidate_rrd.json={f},out/pack_excluded.tsv={ex}")
    assert r.rc == 0, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["score_runs"]["run1"]["candidate_rrd"] == rrd
    assert rec["score_runs"]["run2"]["candidate_rrd"] is None
    assert rec["not_fetched_from_hosts"]["score"] == [
        {"path": "out/score_run1/score_side/vision_pilot/visionpilot.rrd", "bytes": 4729613610}]
    assert "kept on the S-CORE host, not fetched: run1 4729613610 B sha256 " + "b" * 64 in r.log


# ------------------------------------------- F4 of the first recorded p10-2: a chase recorder's failure is recorded
# In 20261119T174606Z the run's recorder ended rc 1 ("ego or camera deleted by another client", 0 frames), the
# session took the end path and skipped receipts_run1 and the whole of run 2, although the window's capture and the
# app's records were there. A recorder that ended with its own rc is the window's result: recorded per run
# (session.json chase_view: complete, rc, the recorder summary's end), named in the p10-2 report, and the session
# goes on with the window's capture stop, its receipts and the next run.
REC_END = "ego or camera deleted by another client"


def test_f4_a_chase_recorder_that_ends_rc_1_is_recorded_and_the_session_goes_on(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({"ego_id": 152, "written": 0, "end": REC_END, "ffmpeg_rc": 0}, indent=1))
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_STEP_RC="rec_run1:1",
            FAKE_PACK_ADD=f"out/rec_run1/summary.json={summary}")
    assert r.rc == 0, r.log
    assert r.sequence() == p10_2_seq(), r.sequence()
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["exit_code"] == 0 and rec["failed_step"] is None, (rec["exit_code"], rec["failed_step"])
    none = {"written": None, "gaps": None, "ticks_seen": None}
    assert rec["chase_view"] == {"run1": {"complete": False, "rc": 1, "end": REC_END, **none, "written": 0},
                                 "run2": {"complete": True, "rc": 0, "end": None, **none}}, rec["chase_view"]
    assert rec["app_record_receipts"] == {"run1": 2, "run2": 2}, rec["app_record_receipts"]
    assert rec["p10_2"]["chase_view_complete"] is False, rec["p10_2"]
    assert "CHASE VIEW NOT COMPLETE IN RUN run1: the recorder ended rc 1" in r.log
    assert f"p10-2 chase recorder NOT rc 0 in every run: run1 (recorder rc 1: {REC_END})" in r.log


def test_f4_a_good_p10_2_reports_every_chase_view_complete(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--without-guest-host")
    assert r.rc == 0, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    none = {"end": None, "written": None, "gaps": None, "ticks_seen": None}
    assert rec["chase_view"] == {"run1": {"complete": True, "rc": 0, **none},
                                 "run2": {"complete": True, "rc": 0, **none}}, rec["chase_view"]
    assert rec["p10_2"]["chase_view_complete"] is True
    assert "p10-2 chase recorder ended rc 0 in every run: run1, run2" in r.log


def test_f4_a_chase_recorder_still_running_after_its_bound_still_ends_the_session(tmp_path: Path) -> None:
    # guard: a recorder that never ends would attach to the next run's hero; only its own end is a result
    r = run(tmp_path, "p10-2", "--without-guest-host", FAKE_HANG_STEP="rec_run1:30", DA_T_T_REC_END="1")
    assert r.rc == 5, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["failed_step"] == "rec_run1" and not r.ssh(G4, "start world_run2")


# ------------------------------------------- R12b: a role VM lost while none of its steps is polled (p10-2 attempt 2)
# In 20261119T203947Z the S-CORE host was preempted at 21:00:19Z while the session ran guest steps. Nothing polled it:
# a guest step failed 87 s later on the missing offer (exit 5, ended_by "step app_restart_run1"), the S-CORE stop and
# the fetch SSHed to the stopped VM (rc 255, "fetch ... failed or changed (remote '', local '')"), and the loss was
# never named. A host watch now reads the started VMs' states; an SSH failure in the stop path reads the VM's state.
FIX_AT = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\.\d{3})?Z$")
OWED = "records on its disk under ~/da-kit/T/out (fetch owed)"


def _watch_lists(r: Run) -> list[int]:
    """The host watch's reads: `compute instances list` without the preflight's RUNNING filter, before the trap."""
    end = r.index(lambda c: c[2:5] == ["compute", "instances", "stop"])
    first_stop = end[0] if end else len(r.calls)
    return [i for i in r.index(lambda c: c[2:5] == ["compute", "instances", "list"]
                               and not any(a.startswith("--filter") for a in c)) if i < first_stop]


def _lost_ok(rec: dict, role: str, status: str, by: str) -> None:
    lost = rec["hosts_lost"][role]
    assert lost["status"] == status and by in lost["detected_by"], lost
    assert FIX_AT.match(lost["detected_at"]) and FIX_AT.match(lost["preempted_at"] or ""), lost
    assert f"{role}: {OWED}" in rec["not_fetched"], rec["not_fetched"]


def test_r12b_a_host_lost_while_none_of_its_steps_is_polled_ends_the_session_within_the_host_watch(
        tmp_path: Path) -> None:
    t0 = time.monotonic()
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_LOST_AFTER=f"{L4}:tail score_start_run1",
            FAKE_HANG_STEP="unit_run1:40", DA_T_HOST_WATCH_S="0.5")
    took = time.monotonic() - t0
    assert r.rc == 3, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["ended_by"] == "host lost: score (TERMINATED)", rec["ended_by"]
    assert took < 30, took                            # the guest step's 40 s were not waited for
    _lost_ok(rec, "score", "TERMINATED", "host watch")
    lost = r.ssh(L4, "tail score_start_run1")[0]
    assert not [i for i in r.ssh(L4, "") if i > lost], "an SSH to the lost host"   # no stop step, no fetch
    assert set(rec["fetched"]) == {"sim", "guest"}, rec["fetched"]
    ops = r.index(lambda c: c[2:5] == ["compute", "operations", "list"])
    assert ops and any(f"targetLink~instances/{L4}$" in a and "operationType=compute.instances.preempted" in a
                       for a in r.calls[ops[0]]), [r.calls[i] for i in ops]
    assert "HOST LOST: de4sdv-probe-da8-carla (score) reads TERMINATED in the host watch" in r.log
    assert "p10-2 host lost: score (TERMINATED" in r.log and OWED in r.log
    assert_invariants(r)


def test_r12b_the_host_watch_reads_only_vms_this_session_started_once_up(tmp_path: Path) -> None:
    # p10-1 never starts the guest host, which reads TERMINATED in the S-CORE host's project; the L4 reads TERMINATED
    # between its start rounds: neither is a lost host
    r = run(tmp_path, "p10-1", FAKE_START=f"{L4}:STOCKOUT|STOCKOUT|OK", DA_T_ROUND_PAUSE_S="0.6",
            DA_T_HOST_WATCH_S="0.1", FAKE_HANG_STEP="p10_1:2")
    assert r.rc == 0, r.log
    assert len(_watch_lists(r)) >= 4, "no host watch"
    assert "HOST LOST" not in r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["hosts_lost"] == {} and rec["ended_by"] == "steps"
    cmds = (r.incoming / "commands.log").read_text()
    assert re.search(r"compute instances list --format=\S+ \[host watch\] \[timeout \d+ s\]", cmds), cmds[-2000:]


def test_r12b_the_host_watch_ends_where_the_trap_begins_its_stops(tmp_path: Path) -> None:
    # the trap fetches and stops the S-CORE host, then tries the guest host's SSH for GUEST_NOSSH_S: the S-CORE host
    # reads TERMINATED by the trap's own stop meanwhile, which is no loss
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_SSH_DOWN=GH, DA_T_GUEST_NOSSH_S="3",
            DA_T_HOST_WATCH_S="0.1")
    assert r.rc == 4, r.log
    assert r.stops(L4) and "GUEST HOST STOPPED WITHOUT A CROSVM COUNT" in r.log
    assert "HOST LOST" not in r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["hosts_lost"] == {} and not rec["ended_by"].startswith("host lost"), rec["ended_by"]


def test_r12b_a_step_that_fails_after_the_score_host_was_lost_names_the_loss_and_skips_its_ssh(
        tmp_path: Path) -> None:
    # the 20261119T203947Z order: the L4 lost after score_start_run1, the guest step fails on the missing offer before
    # the host watch reads it; the S-CORE stop's SSH fails (rc 255) and reads the VM's state
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_LOST_AFTER=f"{L4}:tail score_start_run1",
            FAKE_FAIL_STEP="app_restart_run1", DA_T_HOST_WATCH_S="600")
    assert r.rc == 3, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["failed_step"] == "app_restart_run1", rec["failed_step"]
    assert rec["ended_by"] == "host lost: score (TERMINATED)", rec["ended_by"]
    _lost_ok(rec, "score", "TERMINATED", "score_stop_on_failure")
    assert not r.ssh(L4, "host_step.sh pack") and "failed or changed (remote ''" not in r.log
    assert set(rec["fetched"]) == {"sim", "guest"}, rec["fetched"]
    assert "step app_restart_run1 failed after the loss of score" in r.log
    assert_invariants(r)


def test_r12b_a_step_that_fails_before_the_loss_stays_the_end(tmp_path: Path) -> None:
    # guard of the order: the loss came after the failure (the S-CORE stop's own SSH answered, the host went after
    # it), so ended_by stays the step and exit 5; the loss is recorded all the same
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_LOST_AFTER=f"{L4}:run score_stop_on_failure",
            FAKE_FAIL_STEP="app_restart_run1", DA_T_HOST_WATCH_S="600")
    assert r.rc == 5, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["failed_step"] == "app_restart_run1" and rec["ended_by"] == "step app_restart_run1", rec["ended_by"]
    _lost_ok(rec, "score", "TERMINATED", "fetch")
    # the pack's SSH found the loss: no copy from the lost host follows, and no failed fetch is reported
    assert not r.index(lambda c: c[2:4] == ["compute", "scp"] and f"{L4}:da-kit/T/out.tgz" in c)
    assert "failed or changed (remote ''" not in r.log
    assert_invariants(r)


@pytest.mark.parametrize("after, by", [("tail score_stop_run2", "ssh: fetch (pack)"),
                                       ("host_step.sh pack", "scp: fetch")])
def test_r12b_a_host_lost_before_the_final_fetch_is_named_not_a_failed_fetch(tmp_path: Path, after: str,
                                                                              by: str) -> None:
    # lost before the pack's SSH, or between the pack and the copy: each failed call reads the VM's state
    r = run(tmp_path, "p10-2", "--without-guest-host", FAKE_LOST_AFTER=f"{L4}:{after}", DA_T_HOST_WATCH_S="600")
    assert r.rc == 3, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["ended_by"] == "host lost: score (TERMINATED)" and rec["failed_step"] is None, rec["ended_by"]
    _lost_ok(rec, "score", "TERMINATED", by)
    assert rec["hosts_lost"]["score"]["detected_by"] == by
    assert "failed or changed (remote ''" not in r.log and rec["fetched"] == ["sim"], rec["fetched"]
    assert_invariants(r)


# ------------------------------------------- T4, T6, T8 of the closure check of 8fae4100
ADAPTER_CONFIG = ('{"t_mono_ns":872376290692,"t_real_ns":1795121733966229000,"host":"score","component":'
                  '"actuationAdapter","event":"config","seq":2,"data":{"carla_host":"10.10.0.2","carla_port":2000,'
                  '"client_timeout_s":30,"hero_role_name":"hero","clientVersion":"1.0-14ac3b1a5","serverVersion":'
                  '"1.0-14ac3b1a5","heroActorId":148,"heroTypeId":"vehicle.lincoln.mkz"}}\n')
ADAPTER_ERROR = ('{"t_mono_ns":1036865930466,"t_real_ns":1795111480448812235,"host":"score","component":'
                 '"actuationAdapter","event":"start","seq":1,"data":{"pid":9613,"config":'
                 '"/tmp/de4sdv-da-bench/config/adapter.json","mw_com_config":'
                 '"/tmp/de4sdv-da-bench/config/mw_com_config_actuation_adapter.json","run_dir":'
                 '"/tmp/de4sdv-da-bench/run"}}\n'
                 '{"t_mono_ns":1056885197482,"t_real_ns":1795111500468079203,"host":"score","component":'
                 '"actuationAdapter","event":"error","seq":2,"data":{"what":"simulator client","message":'
                 '"no vehicle with role_name hero"}}\n')


def test_t4_each_runs_adapter_attach_is_recorded_and_a_run_without_one_is_named(tmp_path: Path) -> None:
    # the lines are the adapter's own records of 20261119T203947Z (calib_steer) and 20261119T174606Z (run1)
    ok, bad = tmp_path / "ok.jsonl", tmp_path / "bad.jsonl"
    ok.write_text(ADAPTER_CONFIG)
    bad.write_text(ADAPTER_ERROR)
    a = "score_side/run/score/actuationAdapter.jsonl"
    r = run(tmp_path, "p10-2", "--without-guest-host",
            FAKE_PACK_ADD=f"out/score_calib_steer/{a}={ok},out/score_run1/{a}={bad}")
    assert r.rc == 0, r.log
    runs = json.loads((r.incoming / "session.json").read_text())["score_runs"]
    assert runs["calib_steer"]["adapter"] == {"heroActorId": 148, "error": None}, runs["calib_steer"]
    assert runs["run1"]["adapter"] == {"heroActorId": None,
                                       "error": "simulator client: no vehicle with role_name hero"}, runs["run1"]
    assert runs["run2"]["adapter"] == "no adapter record fetched", runs["run2"]
    assert ("p10-2 adapter NO ATTACH in run1 (simulator client: no vehicle with role_name hero), run2 (no adapter "
            "record fetched); attached in calib_steer (hero 148)") in r.log


def test_t4_a_score_host_not_fetched_reads_not_fetched_for_each_runs_adapter(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-2", "--without-guest-host", FAKE_FETCH_FAIL=L4)
    assert r.rc == 5, r.log
    runs = json.loads((r.incoming / "session.json").read_text())["score_runs"]
    assert {w: d["adapter"] for w, d in runs.items()} == {w: "not fetched" for w in ("calib_steer", "run1", "run2")}


def test_t6_t8_chase_view_says_what_its_rc_means_and_the_speed_limit_is_a_proposal(tmp_path: Path) -> None:
    summary = tmp_path / "summary.json"
    summary.write_text(json.dumps({"ego_id": 152, "written": 591, "gaps": [[10, 12]], "ticks_seen": 1803,
                                   "end": "hero deleted", "ffmpeg_rc": 0}))
    r = run(tmp_path, "p10-2", "--without-guest-host", FAKE_PACK_ADD=f"out/rec_run1/summary.json={summary}")
    assert r.rc == 0, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["chase_view"]["run1"] == {"complete": True, "rc": 0, "end": "hero deleted", "written": 591,
                                         "gaps": [[10, 12]], "ticks_seen": 1803}, rec["chase_view"]
    assert rec["chase_view"]["run2"]["written"] is None
    assert "p10-2 chase recorder ended rc 0 in every run: run1, run2" in r.log and "chase view complete" not in r.log
    for d in rec["score_runs"].values():
        assert d["speed_limit_source"].startswith("bench proposal: world-side/scenarios.py "), d


# ------------------------------------------- F7 of 20261120T092051Z: the simulator host's fetch through IAP, by ranges
# The G4's out.tgz held two chase videos (305,986,299 B). One `gcloud compute scp --tunnel-through-iap` ran at about
# 150-175 KB/s, was cut at its 1200 s bound at about 208 MB, and the session ended exit 5 by \"fetch\". The lead then
# read the same file as 37 ranges of 8 MiB with `dd` over 8 parallel IAP tunnels in 4 min 57 s (about 1.03 MB/s).
MIB = 1048576
# a pack of several 1 MiB ranges: 3.5 MiB of incompressible bytes, so the last range is short
RANGED = {"FETCH_RANGE_MIB": "1", "FAKE_PACK_PAD": str(3 * MIB + MIB // 2)}
DD = re.compile(r"^dd if=\$HOME/da-kit/T/out\.tgz bs=1M skip=(\d+) count=(\d+) status=none$")


def _dd(r: Run, vm: str = G4) -> list[int]:
    return [i for i in r.ssh(vm, "dd if=") if DD.match(r.command(i))]


def _ranges_tsv(r: Run, role: str = "sim") -> list[dict]:
    rows = (r.incoming / role / "fetch_ranges.tsv").read_text().splitlines()
    head = rows[0].split("\t")
    return [dict(zip(head, x.split("\t"))) for x in rows[1:]]


def test_f7_an_iap_host_is_fetched_as_ranges_over_parallel_tunnels_and_joined(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", **RANGED)
    assert r.rc == 0, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["fetched"] == ["sim", "score"], rec["fetched"]
    size = (tmp_path / "fake" / f"{G4}_out.tgz").stat().st_size
    n = -(-size // MIB)
    assert n >= 4 and size % MIB, size
    reads = _dd(r)
    assert sorted(int(DD.match(r.command(i)).group(1)) for i in reads) == list(range(n))
    assert all(DD.match(r.command(i)).group(2) == "1" for i in reads)
    for i in reads:   # through IAP, without a pty, and nothing written on the host
        assert "--tunnel-through-iap" in r.calls[i] and "--ssh-flag=-T" in r.calls[i], r.calls[i]
    # the simulator host gets no scp of out.tgz; the S-CORE host (direct SSH) keeps its single scp
    assert not r.index(lambda c: c[2:4] == ["compute", "scp"] and any(a.startswith(G4 + ":") and a.endswith("/out.tgz")
                                                                       for a in c))
    assert len(r.index(lambda c: c[2:4] == ["compute", "scp"] and any(a.startswith(L4 + ":") and
                                                                       a.endswith("/out.tgz") for a in c))) == 1
    assert not _dd(r, L4)
    got = (r.incoming / "sim" / "out.tgz").read_bytes()
    assert got == (tmp_path / "fake" / f"{G4}_out.tgz").read_bytes()
    assert (r.incoming / "sim" / "out" / "pad.bin").stat().st_size == 3 * MIB + MIB // 2
    rows = _ranges_tsv(r)
    assert sorted(int(x["range"]) for x in rows) == list(range(n)) and {x["result"] for x in rows} == {"ok"}
    last = next(x for x in rows if int(x["range"]) == n - 1)
    assert int(last["bytes"]) == int(last["want"]) == size - (n - 1) * MIB   # the short last range, size-checked
    assert all(float(x["end_s"]) >= float(x["start_s"]) > 0 for x in rows)
    f = rec["fetch"]
    assert f["sim"]["method"] == "ranges" and f["sim"]["bytes"] == size and f["sim"]["ranges"] == n, f
    assert f["sim"]["parallel"] == 8 and f["sim"]["range_mib"] == 1 and f["sim"]["result"] == "ok", f
    assert f["sim"]["sha256"] == hashlib.sha256(got).hexdigest() and f["sim"]["tries"] == n, f
    assert f["score"]["method"] == "scp" and f["score"]["result"] == "ok", f
    assert f"fetched {G4}: out.tgz {f['sim']['sha256']}" in r.log
    printed = [line for line in r.stdout.splitlines() if line.startswith(("+ gcloud", "+ ssh", "+ scp"))]
    assert len(printed) == len(r.calls)   # the dry run prints every range read too


def test_f7_the_ranges_run_over_at_most_fetch_parallel_tunnels_at_once(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FETCH_PARALLEL="2", FAKE_SLOW_FETCH=f"{G4}:0.6", **RANGED)
    assert r.rc == 0, r.log
    rows = _ranges_tsv(r)
    spans = [(float(x["start_s"]), float(x["end_s"])) for x in rows]
    most = max(sum(1 for s, e in spans if s <= t < e) for t, _ in spans)
    assert most == 2, spans


def test_f7_a_short_range_is_read_again_and_a_hung_try_is_cut_at_its_bound(tmp_path: Path) -> None:
    # range 2 comes back half (the tunnel dropped, rc 255) once; range 1 hangs 40 s on its first try. Each try is
    # bounded (here 2 s: the try's base of 1 s plus 2 x the range at its tunnel's share of the planning rate)
    t0 = time.monotonic()
    r = run(tmp_path, "p10-1", FAKE_RANGE_SHORT="2:1", FAKE_RANGE_HANG="1:1:40", DA_T_FETCH_TRY_BASE_S="1",
            DA_T_FETCH_PLAN_BPS="100000000", **RANGED)
    assert r.rc == 0, r.log
    assert time.monotonic() - t0 < 35
    rows = _ranges_tsv(r)
    two = sorted((x for x in rows if x["range"] == "2"), key=lambda x: int(x["try"]))
    assert [x["result"] for x in two] == ["short", "ok"] and int(two[0]["bytes"]) == MIB // 2, two
    one = sorted((x for x in rows if x["range"] == "1"), key=lambda x: int(x["try"]))
    assert [x["result"] for x in one] == ["rc 124", "ok"], one
    assert float(one[0]["end_s"]) - float(one[0]["start_s"]) < 10, one
    tos = [int(re.search(r"\[timeout (\d+) s\]$", c).group(1))
           for c in (r.incoming / "commands.log").read_text().splitlines() if " dd if=" in c]
    assert tos and max(tos) == 2, tos
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["fetch"]["sim"]["result"] == "ok" and rec["fetch"]["sim"]["tries"] == len(rows), rec["fetch"]
    assert (r.incoming / "sim" / "out.tgz").read_bytes() == (tmp_path / "fake" / f"{G4}_out.tgz").read_bytes()


def test_f7_a_range_that_fails_three_tries_on_a_running_host_fails_the_fetch(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_RANGE_SHORT="1:9", **RANGED)
    assert r.rc == 5, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    # since the closure check of 1bfbd6b4 (R2) a failed ranged fetch names its pack as a fetch owed, with the whole
    # ranges it kept (test_session_closure_r.py)
    assert rec["ended_by"] == "fetch" and rec["hosts_lost"] == {}, rec
    (nf,) = rec["not_fetched"]
    assert nf.startswith("sim: ~/da-kit/T/out.tgz sha256 ") and nf.endswith("(fetch owed; 3 of 4 ranges whole in "
                                                                          "sim/.ranges)"), nf
    assert len([i for i in _dd(r) if DD.match(r.command(i)).group(1) == "1"]) == 3
    assert f"fetch from {G4} failed" in r.log and "range 1" in r.log, r.log
    assert rec["fetch"]["sim"]["result"].startswith("failed"), rec["fetch"]
    # the VM's state was read after the failure (lost_check): RUNNING, so a failed fetch, not a lost host
    first_bad = [i for i in _dd(r) if DD.match(r.command(i)).group(1) == "1"][0]
    assert r.index(lambda c: c[2:5] == ["compute", "instances", "describe"] and c[5] == G4
                   and "--format=value(status)" in c and c is not None)[-1] > first_bad
    assert not (r.incoming / "sim" / "out.tgz").exists()
    assert_invariants(r)


def test_f7_a_range_that_fails_on_a_host_no_longer_running_is_a_lost_host(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_LOST_AFTER=f"{G4}:dd if=", FETCH_PARALLEL="1", DA_T_HOST_WATCH_S="600", **RANGED)
    assert r.rc == 3, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["ended_by"] == "host lost: sim (TERMINATED)" and rec["failed_step"] is None, rec["ended_by"]
    _lost_ok(rec, "sim", "TERMINATED", "ranges: fetch")
    assert "failed or changed" not in r.log and f"fetch from {G4} failed" not in r.log, r.log
    assert rec["fetched"] == ["score"], rec["fetched"]
    # range 0 came whole, range 1 failed its 3 tries; no later range is read (the fetch cannot be whole)
    assert len(_dd(r)) == 4, [r.command(i) for i in _dd(r)]
    assert rec["fetch"]["sim"]["result"] == "host lost", rec["fetch"]
    assert_invariants(r)


@pytest.mark.parametrize("lost", [False, True])
def test_f7_a_pack_that_gives_no_size_reads_the_hosts_state(tmp_path: Path, lost: bool) -> None:
    # an IAP error ends the pack's call with rc 1, not 255: the VM's state decides all the same
    extra = {"FAKE_LOST_AFTER": f"{G4}:host_step.sh pack", "DA_T_HOST_WATCH_S": "600"} if lost else {}
    r = run(tmp_path, "p10-1", FAKE_PACK_FAIL=G4, **extra, **RANGED)
    rec = json.loads((r.incoming / "session.json").read_text())
    assert not _dd(r)
    if lost:
        assert r.rc == 3 and rec["ended_by"] == "host lost: sim (TERMINATED)", r.log
        _lost_ok(rec, "sim", "TERMINATED", "ssh: fetch (pack)")
        assert f"fetch from {G4} failed" not in r.log
    else:
        assert r.rc == 5 and rec["ended_by"] == "fetch" and rec["hosts_lost"] == {}, r.log
        assert f"fetch from {G4} failed: its pack gave no sha256 and size" in r.log
    assert rec["not_fetched"][0].startswith("sim") and rec["fetched"] == ["score"], rec
    assert_invariants(r)


def test_f7_the_fetch_bound_follows_the_packs_size_and_is_logged_before_the_fetch(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", **RANGED)
    assert r.rc == 0, r.log
    size = (tmp_path / "fake" / f"{G4}_out.tgz").stat().st_size
    # 60 s plus the pack at 1 MB/s (F7: 8 tunnels gave 1.03 MB/s), never above the pre-stop phase's fetch budget of a
    # host (120 s pack + 300 s copy)
    want = min(60 + -(-size // 1000000), 420)
    lines = [x for x in r.log.splitlines() if f"fetch of {G4} by ranges" in x]
    assert len(lines) == 1 and f"bound {want} s" in lines[0] and f"{size} B" in lines[0], lines
    assert json.loads((r.incoming / "session.json").read_text())["fetch"]["sim"]["bound_s"] == want
    import calendar
    t_log = calendar.timegm(time.strptime(lines[0].split()[0], "%Y-%m-%dT%H:%M:%SZ"))
    first_dd = min(_call_times(tmp_path, lambda c: c[2:4] == ["compute", "ssh"] and any(DD.match(a) for a in c)))
    assert t_log <= first_dd + 1


def test_f7_the_fetch_bound_never_exceeds_the_pre_stop_fetch_budget_and_ends_a_slow_fetch(tmp_path: Path) -> None:
    # the pre-stop phase's fetch budget of a host here 2 + 3 = 5 s; every range read takes 30 s
    t0 = time.monotonic()
    r = run(tmp_path, "p10-1", FAKE_SLOW_FETCH=f"{G4}:30", DA_T_TRAP_PACK_S="2", DA_T_TRAP_SCP_S="3", **RANGED)
    took = time.monotonic() - t0
    assert r.rc == 5, r.log
    lines = [x for x in r.log.splitlines() if f"fetch of {G4} by ranges" in x]
    assert len(lines) == 1 and "bound 5 s" in lines[0], lines
    rec = json.loads((r.incoming / "session.json").read_text())
    # since the closure check of 1bfbd6b4 (R2) a pack over the budget is not read at all and is named as a fetch owed
    assert rec["ended_by"] == "fetch" and rec["fetch"]["sim"]["bound_s"] == 5 and not _dd(r), rec
    (nf,) = rec["not_fetched"]
    assert nf.startswith("sim: ~/da-kit/T/out.tgz sha256 ") and nf.endswith(" B (fetch owed)"), nf
    assert took < 60, took
    assert_invariants(r)


def test_f7_a_direct_ssh_simulator_host_keeps_the_single_scp(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", SIM_SSH_IAP="0", **RANGED)
    assert r.rc == 0, r.log
    assert not _dd(r)
    assert len(r.index(lambda c: c[2:4] == ["compute", "scp"] and any(a.startswith(G4 + ":") and
                                                                       a.endswith("/out.tgz") for a in c))) == 1
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["fetch"]["sim"]["method"] == "scp" and rec["fetch"]["sim"]["result"] == "ok", rec["fetch"]


def test_f7_a_signal_during_a_ranged_fetch_ends_the_session_at_once(tmp_path: Path) -> None:
    p = popen(tmp_path, "p10-1", FAKE_SLOW_FETCH=f"{G4}:8", **RANGED)
    wait_for_call(tmp_path, lambda c: c[2:4] == ["compute", "ssh"] and any(DD.match(a) for a in c))
    t_dd = time.monotonic()
    time.sleep(0.5)
    t0 = time.monotonic()
    os.killpg(p.pid, signal.SIGTERM)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    assert time.monotonic() - t0 < 8, "the trap waited for the fetch"
    n_before = len(_dd(r))
    # no range read after the trap, and no tunnel outlives it: past the reads' 8 s nothing arrived in a range's file
    time.sleep(max(0.0, t_dd + 9.5 - time.monotonic()))
    assert len(Run(tmp_path).calls) == len(r.calls) and len(_dd(r)) == n_before
    parts = list((r.incoming / "sim" / ".ranges").glob("p[0-9]*"))   # beside the file "pack" (R2 of 1bfbd6b4)
    assert sum(f.stat().st_size for f in parts) == 0, [(f.name, f.stat().st_size) for f in parts]
    assert (r.incoming / "sim" / "fetch_ranges.tsv").read_text().count("\n") == 1   # its header only
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["fetched"] == ["score"] and rec["not_fetched"] == ["sim"]
    assert_invariants(r)


@pytest.mark.parametrize("bad", [("FETCH_PARALLEL", "0"), ("FETCH_RANGE_MIB", "x")])
def test_f7_fetch_settings_must_be_positive_whole_numbers(tmp_path: Path, bad: tuple) -> None:
    r = run(tmp_path, "p10-1", **{bad[0]: bad[1]})
    assert r.rc == 2 and bad[0] in r.stdout and not r.starts(G4), r.stdout


def test_f7_the_readme_describes_the_ranged_fetch() -> None:
    text = (HERE.parent / "README.md").read_text()
    sec = text.split("### The evidence fetch", 1)[1].split("\n## ", 1)[0].split("\n### ", 1)[0]
    for word in ("FETCH_PARALLEL", "FETCH_RANGE_MIB", "fetch_ranges.tsv", "--ssh-flag=-T", "dd", "lost_check",
                 "`fetch`", "1 MB/s", "420 s", "3 tries"):
        assert word in sec, word
