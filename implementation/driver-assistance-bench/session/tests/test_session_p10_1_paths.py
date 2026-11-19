"""p10-1's cut, cap, abort and FAIL paths (review of the p10-1 session at 58f0039c, V1-V3, V7), as dry runs.

The helpers and the stub entries are test_session_dryrun.py's: the fake gcloud answers for every remote host.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

from test_session_dryrun import (G4, HERE, L4, assert_invariants, finish, popen, run,  # noqa: F401
                                 wait_for_call)

README = HERE.parent / "README.md"
NORMAL_SEQUENCE = ["sim:sim_setup", "score:port_test", "sim:warmup", "sim:world_p10_1&", "sim:file-ready.json",
                   "sim:touch-go", "score:p10_1", "sim:file-run_end.json", "sim:touch-release",
                   "sim:wait-world_p10_1"]


def _first(r, vm: str, needle: str) -> int:
    hits = r.ssh(vm, needle)
    assert hits, (vm, needle, r.log)
    return hits[0]


def _term_in_p10_1(tmp_path: Path, **extra: str):
    p = popen(tmp_path, "p10-1", FAKE_HANG_STEP="p10_1:30", **extra)
    wait_for_call(tmp_path, lambda c: any("start p10_1" in a for a in c))
    time.sleep(0.5)
    p.send_signal(15)
    return finish(tmp_path, p)


def _score_stop_of_the_check(r) -> int:
    # the session's own stop of the check's S-CORE side, into the check's folder, before the S-CORE host's fetch
    i = _first(r, L4, "score_stop_on_failure")
    assert "out/p10_1/trap_stop" in r.command(i), r.command(i)
    assert i < _first(r, L4, "host_step.sh pack") < r.stops(L4)[0]
    return i


def _world_ended_before_the_fetch(r, step: str = "world_p10_1") -> None:
    # V3: the detached world side gets its release file and a TERM before the simulator host is packed
    rel = [i for i in r.ssh(G4, f"{step}/release")]
    sig = r.ssh(G4, f"host_step.sh signal {step} TERM")
    assert rel and sig, r.log
    assert rel[-1] < _first(r, G4, "host_step.sh pack") and sig[-1] < _first(r, G4, "host_step.sh pack")


def test_v1_a_term_during_the_check_stops_its_score_side_from_the_session_too(tmp_path: Path) -> None:
    r = _term_in_p10_1(tmp_path)
    assert r.rc == 143, r.log
    i = _score_stop_of_the_check(r)
    assert _first(r, L4, "host_step.sh signal p10_1 TERM") < i      # the check's own handler had its turn first
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["score_stops"] == {"p10_1": {"step": "score_stop_on_failure", "rc": 0, "stop_killed": False}}
    assert_invariants(r)


def test_v1_the_cap_during_the_check_stops_its_score_side_from_the_session_too(tmp_path: Path) -> None:
    # EUR 10 at 3600 EUR/h: the cap comes about 10 s after the S-CORE host's start, while the check runs
    r = run(tmp_path, "p10-1", "--cap-eur", "10", SCORE_EUR_H="3600", FAKE_HANG_STEP="p10_1:90")
    assert r.rc == 10, r.log
    assert r.ssh(L4, "host_step.sh start p10_1"), r.log
    _score_stop_of_the_check(r)
    assert_invariants(r)


def test_v1_a_check_that_ended_leaves_no_score_side_for_the_session_to_stop(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1")
    assert r.rc == 0, r.log
    assert not r.ssh(L4, "score_stop_on_failure")
    assert r.sequence() == NORMAL_SEQUENCE


def test_v2_a_judged_fail_releases_the_world_and_exits_12(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_STEP_RC="p10_1:1")
    assert r.rc == 12, r.log
    assert r.sequence() == NORMAL_SEQUENCE                           # run_end, release and the world's end ran
    rel = _first(r, G4, "world_p10_1/release")
    assert _first(r, L4, "host_step.sh status p10_1") < rel < _first(r, G4, "host_step.sh pack")
    assert not r.ssh(G4, "host_step.sh signal world_p10_1")
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["exit_code"] == 12 and rec["failed_step"] is None and rec["fetched"] == ["sim", "score"]
    assert "p10_1 check FAIL" in rec["ended_by"], rec["ended_by"]
    assert_invariants(r)


def test_v2_any_other_check_exit_is_still_a_step_failure(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_STEP_RC="p10_1:2")
    assert r.rc == 5, r.log
    rec = json.loads((r.incoming / "session.json").read_text())
    assert rec["failed_step"] == "p10_1"
    _world_ended_before_the_fetch(r)
    assert_invariants(r)


def test_v3_a_term_during_the_check_ends_the_world_side_before_the_fetch(tmp_path: Path) -> None:
    r = _term_in_p10_1(tmp_path)
    assert r.rc == 143
    _world_ended_before_the_fetch(r)
    # the S-CORE side stops while the world still ticks, then the world is ended
    assert _first(r, L4, "score_stop_on_failure") < r.ssh(G4, "world_p10_1/release")[-1]
    assert_invariants(r)


def test_v3_a_world_that_never_gets_ready_is_ended_before_the_fetch(tmp_path: Path) -> None:
    r = run(tmp_path, "p10-1", FAKE_NO_FILE="ready.json", DA_T_T_READY="2", FAKE_HANG_STEP="world_p10_1:60")
    assert r.rc == 5, r.log
    _world_ended_before_the_fetch(r)
    assert_invariants(r)


def test_v3_p10_2_a_term_during_a_run_ends_its_world_side_before_the_fetch(tmp_path: Path) -> None:
    p = popen(tmp_path, "p10-2", "--without-guest-host", FAKE_NO_FILE="world_run1/simulator/run_end.json",
              FAKE_HANG_STEP="world_run1:90")
    try:
        wait_for_call(tmp_path, lambda c: any("world_run1/go" in a for a in c), timeout=90)
    except AssertionError:
        p.kill()
        raise AssertionError(p.communicate()[0][-3000:])
    time.sleep(0.5)
    p.send_signal(15)
    r = finish(tmp_path, p)
    assert r.rc == 143, r.log
    _world_ended_before_the_fetch(r, "world_run1")
    assert_invariants(r)


def test_v6_a_cut_check_is_named_in_the_line_and_in_session_json(tmp_path: Path) -> None:
    # V6: the check's cut handler writes the verdicts judged so far and names the cut; the session's line says so
    rows = [{"verdict": "PASS", "check": "C1_launch_manager_config_and_start_order", "detail": "ok"}] + \
        [{"verdict": "NOT RUN", "check": "C%d_x" % i, "detail": "cut by TERM during part 3 (the full configuration)"}
         for i in range(2, 9)]
    f = tmp_path / "verdicts.json"
    f.write_text(json.dumps({"checks": rows, "cut": {"signal": "TERM", "part": "3 (the full configuration)",
                                                    "stop_rc": "0"}}))
    r = run(tmp_path, "p10-1", FAKE_PACK_ADD=f"out/p10_1/p10_1_verdicts.json={f}")
    assert r.rc == 0, r.log
    p = json.loads((r.incoming / "session.json").read_text())["p10_1"]
    assert p["cut"]["signal"] == "TERM" and p["passed"] is False and p["pass"] == [rows[0]["check"]]
    assert p["line"].startswith("P10-1: 7 of 8 checks NOT RUN")
    assert "the check was cut by TERM during part 3 (the full configuration)" in p["line"], p["line"]


def test_v2_v7_the_readme_lists_exit_12_and_the_best_p10_1_outcome() -> None:
    text = README.read_text()
    codes = re.search(r"Exit codes: (.*?)\n\n", text, re.S).group(1)
    assert "12 a p10-1 check FAILed" in " ".join(codes.split()), codes
    one = " ".join(text.split())
    assert "The best a p10-1 session can read is not a pass." in one
    assert "2 of 8 checks NOT RUN: C5_gatewayd_receives_from_asil_b_process, C8_candidate_on_a_replayed_clip" in one
