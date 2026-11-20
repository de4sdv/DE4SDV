"""Two session options of lane I-S of the S1 integration (INC-DRIVING-002; lead decision 2026-11-20).

- --ackermann-gains default|v1: env DA_ACKERMANN_GAINS on every simulator-host world and calibration step (the contract
  with lane I-W, whose world side reads it), recorded in session.json, top level and per run; SEQUENCE unchanged.
- --rehearsal with --runs <tsv>: a shorter run list for a real s1, which is then no evidence. Without --rehearsal a run
  list that is not the committed one stays refused.

The expected orders and values are written out here, not taken from the script.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from test_session_dryrun import G4, assert_invariants, run, vp_clone, _vp_env  # noqa: F401
from test_session_s1 import LABELS, record, s1_env, s1_run, s1_seq

SESSION_DIR = Path(__file__).resolve().parents[1]


# ───────────── h: --ackermann-gains ─────────────

WORLD_STEPS_S1 = ["warmup", "calibrate", "world_calib_steer"] + [f"world_{w}" for w in LABELS]


def _sim_step(r, name: str) -> str:
    (i,) = r.ssh(G4, f"host_step.sh start {name} ")
    return r.command(i)


@pytest.mark.parametrize("given", [None, "default", "v1"])
def test_s1_every_world_and_calibration_step_gets_the_ackermann_gains(tmp_path: Path, given: str | None) -> None:
    more = ["--ackermann-gains", given] if given else []
    r = s1_run(tmp_path, "--without-guest-host", *more)
    assert r.rc == 0, r.stdout + r.log
    want = given or "default"
    for name in WORLD_STEPS_S1:
        assert f"DA_ACKERMANN_GAINS={want} " in _sim_step(r, name), (name, _sim_step(r, name))
    # only the world and calibration steps: never the recorders, the setup or another host
    for name in ["sim_setup", "rec_warmup"] + [f"rec_{w}" for w in LABELS]:
        assert "DA_ACKERMANN_GAINS" not in _sim_step(r, name), name
    assert not [i for i in r.index(lambda c: any("DA_ACKERMANN_GAINS" in a for a in c)) if G4 not in r.calls[i]]
    assert r.sequence() == s1_seq(guest=False)
    rec = record(r)
    assert rec["ackermann_gains"] == want
    assert {w: d.get("ackermann_gains") for w, d in rec["score_runs"].items()} == \
        {w: want for w in ["calib_steer"] + LABELS}


def test_p10_2_and_p10_1_world_steps_get_the_ackermann_gains(tmp_path: Path) -> None:
    r = run(tmp_path / "a", "p10-2", "--without-guest-host", "--ackermann-gains", "v1")
    assert r.rc == 0, r.stdout + r.log
    for name in ("warmup", "calibrate", "world_calib_steer", "world_run1", "world_run2"):
        assert "DA_ACKERMANN_GAINS=v1 " in _sim_step(r, name), name
    assert record(r)["ackermann_gains"] == "v1"
    assert record(r)["score_runs"]["run1"]["ackermann_gains"] == "v1"
    r = run(tmp_path / "b", "p10-1", "--ackermann-gains", "v1")
    assert r.rc == 0, r.stdout + r.log
    for name in ("warmup", "world_p10_1"):
        assert "DA_ACKERMANN_GAINS=v1 " in _sim_step(r, name), name
    assert record(r)["ackermann_gains"] == "v1"


@pytest.mark.parametrize("value", ["v2", "", "V1", "default "])
def test_any_other_ackermann_gains_is_refused_before_any_vm(tmp_path: Path, value: str) -> None:
    r = s1_run(tmp_path, "--without-guest-host", "--ackermann-gains", value)
    assert r.rc == 2, r.stdout + r.log
    assert f"refused: --ackermann-gains takes default or v1, not '{value}'" in r.stdout, r.stdout
    assert not r.index(lambda c: c[2:5] == ["compute", "instances", "start"])


# ───────────── i: the rehearsal ─────────────

REHEARSAL_RUNS = "# a rehearsal: one run, then the stop run\nSC-DRIVING-012@20\tr1\nstop\tfurther\n"

# the rehearsal dry run's SEQUENCE (runs [012_20_r1, stop], --without-guest-host), written out
REHEARSAL_SEQ = [
    "sim:sim_setup", "score:carla_reach",
    "sim:rec_warmup&", "sim:warmup", "sim:wait-rec_warmup", "sim:calibrate", "lead:make_h",
    "score:disk_check_calib_steer", "sim:world_calib_steer&", "sim:file-ready.json", "score:score_start_calib_steer",
    "sim:touch-go", "sim:file-run_end.json", "score:score_stop_calib_steer", "sim:touch-release",
    "sim:wait-world_calib_steer",
    "score:disk_check_012_20_r1", "sim:rec_012_20_r1&", "sim:world_012_20_r1&", "sim:file-ready.json",
    "score:score_start_012_20_r1", "sim:touch-go", "sim:file-run_end.json", "score:score_stop_012_20_r1",
    "sim:touch-release", "sim:wait-world_012_20_r1", "sim:wait-rec_012_20_r1",
    "score:disk_check_stop", "sim:rec_stop&", "sim:world_stop&", "sim:file-ready.json", "score:score_start_stop",
    "sim:touch-go", "score:path_stop_stop", "sim:file-run_end.json", "score:score_stop_stop", "sim:touch-release",
    "sim:wait-world_stop", "sim:wait-rec_stop",
]


def _rehearsal(tmp: Path, *more: str, runs: str = REHEARSAL_RUNS, list_knob: bool = False, **extra: str):
    tmp.mkdir(parents=True, exist_ok=True)
    env = s1_env(tmp, **extra)
    if not list_knob:
        del env["DA_S1_RUNS"]
    lst = tmp / "rehearsal_runs.tsv"
    lst.write_text(runs)
    args = [a.replace("@LIST@", str(lst)) for a in more]
    return run(tmp, "s1", "--kit-extra", str(tmp / "stubs"), *args, timeout=240, **env), lst


def test_a_run_list_without_rehearsal_is_refused_before_any_vm(tmp_path: Path) -> None:
    r, _ = _rehearsal(tmp_path, "--without-guest-host", "--runs", "@LIST@")
    assert r.rc == 2, r.stdout + r.log
    assert "refused: --runs needs --rehearsal (a real s1 runs the committed session/s1_runs.tsv)" in r.stdout, r.stdout
    assert not r.index(lambda c: c[2:5] == ["compute", "instances", "start"])


@pytest.mark.parametrize("more, why", [
    (["--rehearsal"], "refused: --rehearsal needs --runs <tsv>"),
    (["--rehearsal", "--runs", "/nonexistent/runs.tsv"], "refused: no run list /nonexistent/runs.tsv"),
])
def test_a_rehearsal_needs_a_readable_run_list(tmp_path: Path, more: list[str], why: str) -> None:
    r, _ = _rehearsal(tmp_path, "--without-guest-host", *more)
    assert r.rc == 2, r.stdout + r.log
    assert why in r.stdout + r.log, r.stdout + r.log
    assert not r.index(lambda c: c[2:5] == ["compute", "instances", "start"])


def test_a_rehearsal_is_for_s1_only_and_never_beside_the_dry_run_list(tmp_path: Path) -> None:
    lst = tmp_path / "l.tsv"
    lst.write_text(REHEARSAL_RUNS)
    r = run(tmp_path / "a", "p10-2", "--without-guest-host", "--rehearsal", "--runs", str(lst))
    assert r.rc == 2 and "refused: --rehearsal and --runs are for --kind s1 only" in r.stdout, r.stdout
    r, _ = _rehearsal(tmp_path / "b", "--without-guest-host", "--rehearsal", "--runs", "@LIST@", list_knob=True)
    assert r.rc == 2 and "refused: DA_S1_RUNS and --runs both name a run list" in r.stdout, r.stdout


def test_the_rehearsal_dry_run_of_one_run_and_the_stop_run(tmp_path: Path) -> None:
    r, lst = _rehearsal(tmp_path, "--without-guest-host", "--rehearsal", "--runs", "@LIST@")
    assert r.rc == 0, r.stdout + r.log
    assert r.sequence() == REHEARSAL_SEQ
    assert_invariants(r)
    assert "rehearsal: not evidence" in r.log, r.log
    rec = record(r)
    assert rec["rehearsal"] is True
    assert rec["runList"] == {"path": str(lst), "sha256": hashlib.sha256(lst.read_bytes()).hexdigest()}
    assert rec["cap_eur"] == 2.0
    assert [x["label"] for x in rec["s1"]["runs"]] == ["012_20_r1", "stop"]
    assert rec["s1"]["runs_done"] == ["012_20_r1", "stop"] and rec["exit_code"] == 0


def test_a_rehearsal_takes_the_cap_it_is_given(tmp_path: Path) -> None:
    r, _ = _rehearsal(tmp_path, "--without-guest-host", "--rehearsal", "--runs", "@LIST@", "--cap-eur", "1.25",
                      runs="SC-DRIVING-012@20\tr1\n")
    assert r.rc == 0, r.stdout + r.log
    assert record(r)["cap_eur"] == 1.25 and record(r)["rehearsal"] is True


def test_a_session_that_is_no_rehearsal_says_so(tmp_path: Path) -> None:
    r = s1_run(tmp_path, "--without-guest-host")
    assert r.rc == 0, r.stdout + r.log
    rec = record(r)
    assert rec["rehearsal"] is False and rec["runList"] is None and rec["cap_eur"] == 8.0
    assert "rehearsal" not in r.log


def test_the_readme_has_the_rehearsal_line() -> None:
    text = (SESSION_DIR / "README.md").read_text()
    lines = [ln for ln in text.splitlines() if "da_session.sh --kind s1" in ln and "--rehearsal" in ln]
    assert any("--runs" in ln and "--without-guest-host" in ln and "--dry-run" not in ln for ln in lines), lines
    assert any("--dry-run" in ln and "--runs" in ln for ln in lines), lines
