"""Dry runs of the session orchestrator da_session.sh against a stateful fake gcloud.

Every test runs the real script with --dry-run; the fake (fake_gcloud.py) keeps the VMs' states and logs each call.
The expected orders and outcomes come from the brief's start and stop rules, not from the script.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
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
STUB_ENTRIES = {
    "ENTRY_SCORE_P10_1": "extra/p10_1_check.sh", "ENTRY_SCORE_START": "extra/start_score_side.sh",
    "ENTRY_SCORE_STOP": "extra/stop_score_side.sh", "ENTRY_SCORE_INJECT": "extra/inject_warning_requests.sh",
    "ENTRY_SIM_WARMUP": "extra/warmup.sh", "ENTRY_SIM_RUN": "extra/run_scenario.sh",
}


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


def env_for(tmp: Path, **extra: str) -> dict[str, str]:
    (tmp / "fake").mkdir(exist_ok=True)
    env = dict(os.environ, FAKE_DIR=str(tmp / "fake"), DA_GCLOUD=str(FAKE), TMPDIR=str(tmp), **FAST, **STUB_ENTRIES)
    env.update(extra)
    return env


def args_for(tmp: Path, kind: str, *more: str) -> list[str]:
    return ["bash", str(SESSION), "--kind", kind, "--dry-run", "--evidence-root", str(tmp / "ev"),
            "--kit-from-worktree", "--kit-extra", str(STUBS), "--session-id", "T", *more]


def run(tmp: Path, kind: str, *more: str, timeout: float = 120, **extra: str) -> Run:
    proc = subprocess.run(args_for(tmp, kind, *more), env=env_for(tmp, **extra), capture_output=True, text=True,
                          timeout=timeout)
    return Run(tmp, proc)


def assert_invariants(r: Run) -> None:
    # nothing is ever created or deleted, and every VM ends stopped
    assert not r.index(lambda c: "delete" in c or "create" in c)
    assert all(st == "TERMINATED" for st in r.state.values()), r.state
    # every VM that got a start call got a stop call after it
    for vm in VMS:
        if r.starts(vm):
            assert r.stops(vm) and r.stops(vm)[-1] > r.starts(vm)[-1], vm


def test_p10_1_touches_only_the_score_host(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1")
    assert r.rc == 0, r.stdout + r.log
    assert len(r.starts(L4)) == 1 and not r.starts(G4) and not r.starts(GH)
    assert not r.stops(G4) and not r.stops(GH)
    step = r.ssh(L4, "host_step.sh run p10_1")
    assert step and r.starts(L4)[0] < step[0] < r.stops(L4)[0]
    assert_invariants(r)
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["exit_code"] == 0 and rec["started"] == ["score"] and rec["kind"] == "p10-1"
    assert (r.incoming / "score" / "out" / "session_id").read_text().strip() == "T"


def test_p10_3_starts_score_then_guest_and_stops_guests_before_their_host(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host")
    assert r.rc == 0, r.stdout + r.log
    assert r.starts(L4)[0] < r.starts(GH)[0] and not r.starts(G4)
    cvd = r.ssh(GH, "smoke_boot.sh --stop-only")
    assert cvd and cvd[0] < r.stops(GH)[0]
    # the window: clock set, capture started, injection on the S-CORE host, capture stopped
    order = [r.ssh(GH, "run ivi_clock")[0], r.ssh(GH, "start capture")[0], r.ssh(L4, "run inject")[0],
             r.ssh(GH, "run capture_stop")[0]]
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
    rec, scen, cap_stop = r.ssh(G4, "start rec_run")[0], r.ssh(G4, "run run ")[0], r.ssh(GH, "run capture_stop")[0]
    assert rec < scen < cap_stop
    assert r.ssh(G4, "start rec_warmup")[0] < r.ssh(G4, "run warmup")[0] < rec
    assert r.ssh(GH, "smoke_boot.sh --stop-only")[0] < r.stops(GH)[0]
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
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_FAIL_STEP="score_start")
    assert r.rc == 5
    assert "step score_start failed" in r.log
    for vm in VMS:
        assert r.stops(vm)
    assert r.ssh(GH, "smoke_boot.sh --stop-only")[0] < r.stops(GH)[0]
    assert not r.ssh(G4, "run warmup")                       # nothing after the failed step
    assert r.ssh(L4, "host_step.sh pack")                    # the evidence so far is fetched
    assert json.loads((r.incoming / "session.json").read_text())["failed_step"] == "score_start"
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
    while time.monotonic() < deadline and not (calls.exists() and "run inject" in calls.read_text()):
        time.sleep(0.1)
    time.sleep(0.5)
    p.send_signal(signal.SIGTERM)
    out, _ = p.communicate(timeout=60)
    r = Run(tmp_path, rc=p.returncode, stdout=out)
    assert r.rc == 143, r.log
    assert "signal TERM" in r.log
    assert r.ssh(GH, "smoke_boot.sh --stop-only")[0] < r.stops(GH)[0]
    assert_invariants(r)


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


def test_an_unconfirmed_guest_stop_is_reported_and_the_host_still_stops(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_GUEST_STOP_FAIL="1")
    assert "WARNING guests' stop not confirmed" in r.log
    assert r.stops(GH)
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
