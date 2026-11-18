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


def env_for(tmp: Path, **extra: str) -> dict[str, str]:
    (tmp / "fake").mkdir(parents=True, exist_ok=True)
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
    cvd = r.guest_stops()
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
    rec, scen, cap_stop = r.ssh(G4, "start rec_run1")[0], r.ssh(G4, "start world_run1")[0], \
        r.ssh(GH, "run capture_stop_run1")[0]
    assert rec < scen < cap_stop
    assert r.ssh(G4, "start rec_warmup")[0] < r.ssh(G4, "run warmup")[0] < rec
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
    assert not r.ssh(G4, "touch") and not r.ssh(G4, "world_run1")   # nothing after the failed step
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
    while time.monotonic() < deadline and not (calls.exists() and "run inject" in calls.read_text()):
        time.sleep(0.1)
    time.sleep(0.5)
    p.send_signal(signal.SIGTERM)
    out, _ = p.communicate(timeout=60)
    r = Run(tmp_path, rc=p.returncode, stdout=out)
    assert r.rc == 143, r.log
    assert "signal TERM" in r.log
    assert r.guest_stops()[0] < r.stops(GH)[0]
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


def test_guests_that_do_not_stop_keep_their_host_running(tmp_path: Path) -> None:
    # lead answer B13.3: never a stop of the guest host with guests running; the session says so and exits 11
    r = run(tmp_path, "p10-3", "--owner-ok-guest-host", FAKE_GUEST_STOP_FAIL="1")
    assert r.rc == 11, r.log
    assert len(r.guest_stops()) == 2                         # one retry
    assert not r.stops(GH) and r.state[GH] == "RUNNING"
    assert "GUEST HOST LEFT RUNNING" in r.log
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

P10_1_SEQ = ["score:p10_1"]
GUEST_UP_SEQ = ["guest:guest_up", "guest:guest_prepare", "guest:vxlan_guest", "score:vxlan_score"]
P10_3_SEQ = GUEST_UP_SEQ + [
    "score:score_start", "guest:mcast_route", "guest:unit_inject", "guest:app_restart_inject",
    "guest:ivi_clock_inject", "guest:capture_inject&", "score:inject", "guest:capture_stop_inject",
    "guest:wait-capture_inject", "score:score_stop"]


def _p10_2_run(n: int, first: bool, guest: bool = True) -> list[str]:
    w = f"run{n}"
    window = ((["guest:mcast_route"] if first else []) + [f"guest:unit_{w}", f"guest:app_restart_{w}",
              f"guest:ivi_clock_{w}", f"guest:capture_{w}&"]) if guest else []
    close = [f"guest:capture_stop_{w}", f"guest:wait-capture_{w}"] if guest else []
    return [f"sim:rec_{w}&", f"sim:world_{w}&", "sim:file-ready.json", f"score:score_start_{w}", *window,
            "sim:touch-go", "sim:file-run_end.json", f"score:score_stop_{w}", "sim:touch-release",
            f"sim:wait-world_{w}", f"sim:wait-rec_{w}", *close]


def p10_2_seq(guest: bool = True) -> list[str]:
    return (["sim:sim_setup", "score:carla_reach"] + (GUEST_UP_SEQ if guest else []) + [
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
    starts = r.ssh(L4, "score_start_")
    assert len(starts) == 3 and up[0] < starts[0]
    assert all("DA_CAMERA_CALIBRATION_DIR=" in r.command(i) for i in starts)
    # the capture came from the simulator host's calibrate step, before make-h
    fetch = r.index(lambda c: c[2:4] == ["compute", "scp"] and any("calibrate/camcal/simulator/camera_capture.json"
                                                                   in a for a in c))
    assert fetch and r.ssh(G4, "run calibrate")[0] < fetch[0] < up[0]
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
    assert not r.ssh(L4, "score_start_")
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
    ips = {G4: "10.10.0.7", L4: "10.164.0.20", GH: "10.164.0.33"}   # the D5 placement, say
    r = run(tmp_path, "p10-2", "--owner-ok-guest-host", FAKE_IP=",".join(f"{k}:{v}" for k, v in ips.items()))
    assert r.rc == 0, r.log
    assert "/dev/tcp/10.10.0.7/2000" in r.command(r.ssh(L4, "run carla_reach")[0])
    assert r.command(r.ssh(GH, "run vxlan_guest")[0]).endswith("add 10.164.0.20")
    assert r.command(r.ssh(L4, "run vxlan_score")[0]).endswith("add 10.164.0.33")
    assert all(r.command(i).split()[-1] == "10.10.0.7" for i in r.ssh(L4, "score_start_"))
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
    assert "IVI_PERMISSIVE=0" in r.command(r.ssh(GH, "run guest_up")[0])
    assert json.loads((r.incoming / "session.json").read_text())["conditional_on_permissive_ivi"] is False
    r2 = run(tmp_path / "b", "p10-3", "--owner-ok-guest-host", "--permissive-ivi")
    assert r2.rc == 0, r2.log
    for step in ("run guest_up", "run guest_prepare"):
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
