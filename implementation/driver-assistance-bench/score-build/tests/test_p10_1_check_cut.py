"""A cut p10-1 check: a TERM, INT or HUP to the step's process group (the session's step TERM, its time-out, the cap).

The check starts its Launch Manager with setsid (score-path/scripts/start_score_side.sh), in a session of its own,
so the step's group signal never reaches it. Review V1 of the p10-1 session at 58f0039c: after a cut the Launch
Manager and its five components ran on, and their records stayed uncollected in the stage, which the S-CORE host's
/tmp loses at its next boot. V6: the verdicts the check had judged were lost too (no p10_1_verdicts.json).
Same fakes as test_p10_1_check.py (fake_bundle, the probe and ort stand-ins).
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

from test_p10_1_check import BENCH, SCRIPT, binaries, setup  # noqa: F401  (the fixtures)
import fake_bundle

STOP = BENCH / "score-path" / "scripts" / "stop_score_side.sh"
START = BENCH / "score-path" / "scripts" / "start_score_side.sh"


def _start(setup: dict, out: Path, **env: str) -> subprocess.Popen:
    # its own process group, as host_step.sh starts a detached step (setsid)
    return subprocess.Popen(["bash", str(SCRIPT), str(out)], env={**setup["env"], **env}, cwd=BENCH,
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)


def _wait_for(pred, timeout: float = 60) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if pred():
            return
        time.sleep(0.1)
    raise AssertionError("not seen in time")


def _cut(p: subprocess.Popen, sig: int = signal.SIGTERM, timeout: float = 90) -> int:
    os.killpg(p.pid, sig)
    try:
        p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        raise
    return p.returncode


def _verdicts(out: Path) -> tuple[dict, dict]:
    doc = json.loads((out / "p10_1_verdicts.json").read_text())
    return {r["check"].split("_", 1)[0]: (r["verdict"], r["detail"]) for r in doc["checks"]}, doc


def test_a_term_in_part_3_stops_and_collects_the_full_start_and_keeps_the_verdicts_so_far(setup: dict,
                                                                                         tmp_path: Path) -> None:
    out = tmp_path / "out"
    p = _start(setup, out, DA_P10_1_CARLA_HOST="127.0.0.1", DA_P10_1_SKIP_PORT_CHECK="1", FAKE_LM_SUPERVISE="1",
               DA_CAMERA_CALIBRATION_DIR=str(setup["calibration"]), DA_P10_1_ALIVE_HOLD_S="60")
    verdicts = out / "p10_1_verdicts.txt"
    _wait_for(lambda: verdicts.exists() and "C1_" in verdicts.read_text())
    time.sleep(1.0)
    rc = _cut(p)
    assert rc == 143
    # V1: no staged process outlives the cut, and the full start's records are collected where the fetch finds them
    assert fake_bundle.staged_processes(setup["stage"]) == [], "the check's Launch Manager outlived the cut"
    assert (out / "full" / "score_side" / "state" / "launch_manager.log").is_file()
    assert (out / "full" / "score_side" / "SHA256SUMS").is_file()
    assert (setup["stage"] / "state" / "collected").is_file()
    # V6: the verdicts judged before the cut are kept; the rest are NOT RUN with the cut named
    v, doc = _verdicts(out)
    assert sorted(v) == ["C%d" % i for i in range(1, 9)], v
    for check in ("C1", "C6", "C7"):
        assert v[check][0] == "PASS", (check, v[check])
    for check in ("C2", "C3", "C4", "C8"):
        assert v[check][0] == "NOT RUN" and "cut by TERM" in v[check][1], (check, v[check])
    assert doc["cut"]["signal"] == "TERM" and doc["cut"]["part"].startswith("3"), doc["cut"]
    assert len(verdicts.read_text().splitlines()) == 8


def test_a_term_in_part_1_stops_and_collects_the_path_start(setup: dict, tmp_path: Path) -> None:
    out = tmp_path / "out"
    p = _start(setup, out, DA_P10_1_LATE_WAIT_S="60")
    _wait_for(lambda: (setup["stage"] / "run" / "score" / "identityRecorder.jsonl").exists() and
              (out / "path" / "score_side_state.env").exists())
    time.sleep(1.5)
    rc = _cut(p)
    assert rc == 143
    assert fake_bundle.staged_processes(setup["stage"]) == [], "the path start outlived the cut"
    assert (out / "path" / "score_side" / "state" / "launch_manager.log").is_file()
    v, doc = _verdicts(out)
    assert sorted(v) == ["C%d" % i for i in range(1, 9)]
    assert all(x[0] == "NOT RUN" and "cut by TERM" in x[1] for x in v.values()), v
    assert doc["cut"]["part"].startswith("1"), doc["cut"]


@pytest.mark.parametrize("sig, rc", [(signal.SIGINT, 130), (signal.SIGHUP, 129)])
def test_int_and_hup_cut_the_check_like_term(setup: dict, tmp_path: Path, sig: int, rc: int) -> None:
    out = tmp_path / "out"
    p = _start(setup, out, DA_P10_1_LATE_WAIT_S="60")
    _wait_for(lambda: (out / "path" / "score_side_state.env").exists())
    time.sleep(1.5)
    assert _cut(p, sig) == rc
    assert fake_bundle.staged_processes(setup["stage"]) == []
    _, doc = _verdicts(out)
    assert doc["cut"]["signal"] == signal.Signals(sig).name[3:]


def test_two_stops_of_one_stage_run_one_after_the_other(setup: dict, tmp_path: Path) -> None:
    # the check's cut handler and the session's trap may stop the same stage at once: the second waits for the
    # first, then finds nothing running (one SIGTERM to the Launch Manager), and both collect
    env = {**setup["env"], "FAKE_LM_IGNORE_TERM": "1", "DA_STOP_TIMEOUT_S": "3"}
    up = subprocess.run(["bash", str(START), str(tmp_path / "up"), "none"], env=env, cwd=BENCH, capture_output=True,
                        text=True, timeout=120)
    assert up.returncode == 0, up.stdout + up.stderr
    a = subprocess.Popen(["bash", str(STOP), str(tmp_path / "a")], env=env, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    time.sleep(0.3)
    b = subprocess.Popen(["bash", str(STOP), str(tmp_path / "b")], env=env, stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
    assert a.wait(timeout=120) == 7 and b.wait(timeout=120) == 0
    la, lb = ((tmp_path / x / "stop_score_side.log").read_text() for x in "ab")
    assert "SIGTERM sent to the Launch Manager" in la and "SIGTERM sent" not in lb, (la, lb)
    assert "nothing was started" in lb
    assert (tmp_path / "b" / "score_side" / "SHA256SUMS").is_file()
    assert fake_bundle.staged_processes(setup["stage"]) == []
