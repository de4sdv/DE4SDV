"""Tests for evaluator defects found by the independent review of the case
evaluators.

* VC-DRIVING-017 compared the HEALTH mode with names and strings, but the
  observer records it as its u32 value, so a stopped publication without a
  cause was never found.

Each test builds its run from the fixture of make_synthetic_run.py and edits a
hard-linked copy, streaming each record file into a new file, so the fixture's
bytes are never touched.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

import cases
import strip
from conftest import CASE_RUN, verdict
from runio import Run

OBSERVER = "guest/observer.jsonl"


def copied(run_for, tmp_path, name: str, tag: str) -> Path:
    return strip.copy_run(run_for(name).root, tmp_path / f"{name}-{tag}")


def rewrite_jsonl(path: Path, fn) -> int:
    """Stream a JSONL file through fn(record) -> record, or None to drop it,
    into a new file that then replaces it (the copy's file is a hard link to
    the fixture). Returns the number of records changed or dropped."""
    fd, tmp = tempfile.mkstemp(dir=str(path.parent))
    changed = 0
    with os.fdopen(fd, "w") as out, path.open() as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            before = json.dumps(rec, sort_keys=True)
            new = fn(rec)
            if new is None or json.dumps(new, sort_keys=True) != before:
                changed += 1
            if new is not None:
                out.write(json.dumps(new, separators=(",", ":")) + "\n")
    os.replace(tmp, path)
    return changed


# ------------------------------------------------------------------ VC-DRIVING-017
# REQ-DRIVING-017: each health publication "holds the mode, the cause of the
# stop while stopped, ...". The observer records HEALTH fields 30 and 31 as
# their u32 values (ICD section 3: "HEALTH: `Mode` value", "HEALTH: `Cause`
# value"; ivi-observer/app/src/org/de4sdv/drivingstate/StateRecord.java:138-141
# writes the number, and the name only as mode_name and cause_name). Mode 2 is
# kStopResponse, 3 kStandstill; cause 0 is kNone (interfaces/include/de4sdv/
# driving/payloads.h). The publisher's own record names the mode.
def set_health(d: Path, t_from: float, t_to: float, mode, cause) -> int:
    """Give the health publications from t_from to t_to seconds after the
    first one this mode and cause."""
    path = d / OBSERVER
    t0 = None
    with path.open() as fh:
        for line in fh:
            if '"rx.health"' in line:
                t = json.loads(line)["t_real_ns"]
                t0 = t if t0 is None else min(t0, t)

    def fn(rec):
        if rec["event"] == "rx.health" and \
                t_from <= (rec["t_real_ns"] - t0) / 1e9 <= t_to:
            rec["data"].update(mode=mode, cause=cause)
        return rec
    return rewrite_jsonl(path, fn)


@pytest.mark.parametrize("mode, cause", [
    pytest.param(2, 0, id="kStopResponse-as-the-observer-records-it"),
    pytest.param(3, 0, id="kStandstill-as-the-observer-records-it"),
    pytest.param("kStopResponse", "kNone", id="kStopResponse-by-name"),
    pytest.param("kStandstill", "kNone", id="kStandstill-by-name"),
])
def test_vc017_stopped_health_without_a_cause_fails(run_for, tmp_path, mode, cause):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-017"], "stopped-no-cause")
    assert set_health(d, 30.0, 40.0, mode, cause) > 90
    res = verdict(Run(d), "VC-DRIVING-017")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    problems = res.measured["field_problems"]
    assert problems, res.measured
    assert {p["problem"] for p in problems} == {"stopped without a cause"}, problems
    assert problems[0]["t"] >= 30.0 - 1e-6, problems


@pytest.mark.parametrize("mode", [
    pytest.param(2, id="kStopResponse"),
    pytest.param(3, id="kStandstill"),
])
def test_vc017_stopped_health_with_its_cause_passes(run_for, tmp_path, mode):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-017"], "stopped-with-cause")
    assert set_health(d, 30.0, 40.0, mode, cases.CAUSES.index("kCameraMissing")) > 90
    res = verdict(Run(d), "VC-DRIVING-017")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["field_problems"] == []
