"""VC-DRIVING-017 judges every health publication of the run (REQ-DRIVING-017).

The success criterion of REQ-DRIVING-017, from the model
(closed_loop_driving_needs_requirements.sysml):

    "Met when, over a 60 s window of a run of SC-DRIVING-001 that includes
    priming, driving and a stop, no two consecutive health publications are
    more than 200 ms of wall-clock time apart, and each holds the mode, the
    cause of the stop while stopped, and the age of the newest valid plan, with
    its producer and its production time."

The evaluator reads the observer's health receipts (guest/observer.jsonl,
`in.operational_state` of kind 3, ICD A34). Before this change it judged the
first 60 s of receipts only; on a real closed-loop run those were all
kStarting. The runs here are the generator's closed-loop runs: `comm-stop`
(priming, driving, and the adapter's stop from 50.2 s, 62 s of receipts) and
`nominal` (priming and driving, no stop). Each test edits a hard-linked copy.
"""

from __future__ import annotations

import json
import os
import tempfile
from collections import Counter
from pathlib import Path

import pytest

import cases
import strip
from conftest import CASE_RUN, verdict
from runio import Run

OBSERVER = "guest/observer.jsonl"
VC = "VC-DRIVING-017"
STOPPED = (cases.MODES.index("kStopResponse"), cases.MODES.index("kStandstill"))
STARTING, DRIVING = cases.MODES.index("kStarting"), cases.MODES.index("kDriving")


def copied(run_for, tmp_path: Path, name: str, tag: str) -> Path:
    return strip.copy_run(run_for(name).root, tmp_path / f"{name}-{tag}")


def is_health(rec: dict) -> bool:
    return rec["event"] == "in.operational_state" and rec["data"].get("kind") == 3


def rewrite(path: Path, fn) -> int:
    """Stream a JSONL file through fn(record) -> record into a new file that
    replaces it (the copy's file is a hard link to the fixture). Returns the
    number of records fn changed."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    changed = 0
    with os.fdopen(fd, "w") as out, path.open() as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            before = json.dumps(rec, sort_keys=True)
            rec = fn(rec)
            if json.dumps(rec, sort_keys=True) != before:
                changed += 1
            out.write(json.dumps(rec, separators=(",", ":")) + "\n")
    os.replace(tmp, path)
    return changed


def health_receipts(path: Path) -> list[dict]:
    out = []
    with path.open() as fh:
        for line in fh:
            if line.strip():
                rec = json.loads(line)
                if is_health(rec):
                    out.append(rec)
    return sorted(out, key=lambda r: r["t_real_ns"])


def modes_of(path: Path) -> Counter:
    return Counter(cases.MODES[r["data"]["mode"]] for r in health_receipts(path))


def set_modes(d: Path, fn) -> int:
    """Give every health receipt the mode fn(mode) returns (names kept beside)."""
    def edit(rec):
        if is_health(rec):
            m = fn(rec["data"]["mode"])
            rec["data"].update(mode=m, mode_name=cases.MODES[m])
        return rec
    return rewrite(d / OBSERVER, edit)


# ------------------------------------------------------------------ the run it passes on
def test_vc017_case_run_is_a_closed_loop_run_with_priming_driving_and_a_stop(run_for):
    run = run_for(CASE_RUN[VC])
    assert run.scenario == "closedLoopRoute", run.scenario
    modes = modes_of(run.root / OBSERVER)
    assert modes["kStarting"] and modes["kDriving"], modes
    assert modes["kStopResponse"] + modes["kStandstill"], modes


def test_vc017_the_run_with_priming_driving_and_a_stop_passes_on_every_receipt(run_for):
    run = run_for("comm-stop")
    receipts = health_receipts(run.root / OBSERVER)
    modes = modes_of(run.root / OBSERVER)
    assert len(receipts) == 620 and modes["kStandstill"] > 0, (len(receipts), modes)
    res = verdict(run, VC)
    assert res.outcome == cases.PASS, (res.outcome, res.missing, res.notes, res.measured)
    m = res.measured
    assert m["publications"] == len(receipts), m          # every receipt, not the first 60 s
    assert m["count_per_mode"] == dict(modes), m
    span = (receipts[-1]["t_real_ns"] - receipts[0]["t_real_ns"]) / 1e9
    assert m["span_s"] == pytest.approx(span, abs=1e-6), m
    assert m["worst_gap_s"] == pytest.approx(0.1, abs=1e-6), m
    assert m["gaps_over_200ms"] == [] and m["field_problems"] == [], m
    # while starting there is no plan yet (last_plan_capture_ms 0): those
    # receipts are not plan ages; while driving the generator plans every step
    assert m["plan_age_while_driving_s"] == {"min": 0.0, "max": 0.0}, m
    assert "ages_s" not in m, m


# ------------------------------------------------------------------ priming, driving and a stop
def test_vc017_a_run_whose_receipts_are_all_kstarting_is_inconclusive_and_names_driving_and_the_stop(
        run_for, tmp_path):
    d = copied(run_for, tmp_path, "comm-stop", "all-starting")
    assert set_modes(d, lambda m: STARTING) > 500
    res = verdict(Run(d), VC)
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    text = " ".join(res.missing + res.notes)
    assert "kDriving" in text and "kStopResponse" in text and "kStandstill" in text, text
    assert "no priming" not in text, text
    assert res.measured["count_per_mode"] == {"kStarting": 620}, res.measured


def test_vc017_a_run_without_a_stop_is_inconclusive(run_for):
    run = run_for("nominal")
    assert not ({"kStopResponse", "kStandstill"} & set(modes_of(run.root / OBSERVER)))
    res = verdict(run, VC)
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    text = " ".join(res.missing + res.notes)
    assert "no stop" in text and "kStopResponse" in text, text
    assert "no priming" not in text and "no driving" not in text, text


@pytest.mark.parametrize("absent, relabel", [
    pytest.param("priming", lambda m: DRIVING if m == STARTING else m, id="no-priming"),
    pytest.param("driving", lambda m: STARTING if m == DRIVING else m, id="no-driving"),
    pytest.param("stop", lambda m: DRIVING if m in STOPPED else m, id="no-stop"),
])
def test_vc017_a_run_without_one_of_the_three_names_what_is_absent(run_for, tmp_path, absent,
                                                                   relabel):
    d = copied(run_for, tmp_path, "comm-stop", "without-" + absent)
    assert set_modes(d, relabel) > 0
    res = verdict(Run(d), VC)
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    text = " ".join(res.missing + res.notes)
    assert f"no {absent}" in text, text
    others = {"priming", "driving", "stop"} - {absent}
    assert not any(f"no {o}" in text for o in others), text


# ------------------------------------------------------------------ every receipt of the run
def test_vc017_a_gap_of_250_ms_after_the_first_60_s_in_the_stop_fails(run_for, tmp_path):
    d = copied(run_for, tmp_path, "comm-stop", "late-gap")
    receipts = health_receipts(d / OBSERVER)
    t0 = receipts[0]["t_real_ns"]
    # the receipt at about 60.5 s; the ones after it come 150 ms later
    k = next(i for i, r in enumerate(receipts) if r["t_real_ns"] - t0 >= 60_500_000_000)
    after = receipts[k]
    assert cases.MODES[after["data"]["mode"]] in ("kStopResponse", "kStandstill")
    cut = after["t_real_ns"]

    def shift(rec):
        if is_health(rec) and rec["t_real_ns"] > cut:
            rec["t_real_ns"] += 150_000_000
        return rec
    assert rewrite(d / OBSERVER, shift) == len(receipts) - k - 1
    res = verdict(Run(d), VC)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    gap = res.measured["gaps_over_200ms"][0]
    assert gap["gap_s"] == pytest.approx(0.25, abs=1e-6), gap
    assert gap["after"] == pytest.approx((cut - t0) / 1e9, abs=1e-6), gap
    assert gap["mode"] == cases.MODES[after["data"]["mode"]], gap
    assert res.measured["worst_gap_s"] == pytest.approx(0.25, abs=1e-6), res.measured


def test_vc017_a_stopped_receipt_without_a_cause_after_the_first_60_s_fails(run_for, tmp_path):
    d = copied(run_for, tmp_path, "comm-stop", "late-no-cause")
    receipts = health_receipts(d / OBSERVER)
    t0 = receipts[0]["t_real_ns"]
    late = receipts[-3]
    assert late["t_real_ns"] - t0 > 61_000_000_000
    assert late["data"]["mode"] in STOPPED and late["data"]["cause"] != 0

    def edit(rec):
        if is_health(rec) and rec["t_real_ns"] == late["t_real_ns"]:
            rec["data"].update(cause=0, cause_name="kNone")
        return rec
    assert rewrite(d / OBSERVER, edit) == 1
    res = verdict(Run(d), VC)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    problems = res.measured["field_problems"]
    assert [p["problem"] for p in problems] == ["stopped without a cause"], problems
    assert problems[0]["t"] == pytest.approx((late["t_real_ns"] - t0) / 1e9, abs=1e-6), problems
