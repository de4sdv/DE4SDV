"""Tests for evaluator defects found by the independent review of the case
evaluators.

* VC-DRIVING-017 compared the HEALTH mode with names and strings, but the
  observer records it as its u32 value, so a stopped publication without a
  cause was never found.
* VC-DRIVING-030 read a camera slot without capture_sim_ms and image_frame as
  a slot without an image, so an image recorded without its capture time
  passed, and a run whose records hold no image at all passed with none judged.
* VC-DRIVING-021 judged a stop that never reached standstill up to the end of
  the records and passed it, where VC-DRIVING-020 and -022 are inconclusive.

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
            if '"in.operational_state"' in line:
                rec = json.loads(line)
                if rec["data"]["kind"] == 3:
                    t = rec["t_real_ns"]
                    t0 = t if t0 is None else min(t0, t)

    def fn(rec):
        if rec["event"] == "in.operational_state" and rec["data"]["kind"] == 3 and \
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


# ------------------------------------------------------------------ VC-DRIVING-030
# REQ-DRIVING-030: "Met when every camera image and motion sample in the
# records of a run of SC-DRIVING-001 carries a capture time marked as
# simulation time." A camera slot without an image at its step has status
# "missing" and null stamps (ICD A28; agent/cc/agent_ffi.cpp:552, 1039-1044).
# Every other status the agent writes ("valid", "invalid", "stale") describes
# an image of the records, which must carry its capture_sim_ms.
C2 = "score/checkpointInputs.jsonl"
MISSING_SLOT = {"image_frame": None, "capture_sim_ms": None, "arrival_mono_ns": None,
                "valid": False, "status": "missing"}


class StubRun:
    """The two records VC-DRIVING-030 reads, in the shape runio returns them:
    one step with the given camera slots, one motion sample."""

    def __init__(self, cameras: list[dict]):
        self.cameras = cameras

    def input_steps(self):
        return [{"frame": 100, "sim_ms": 10000, "cameras": self.cameras,
                 "file": C2, "rec": {"seq": 1}}]

    def ego_samples(self):
        return [{"step": 100, "capture_ms": 10000.0, "capture_clock": "simulation"}]


def test_vc030_valid_images_without_a_capture_stamp_fail():
    cams = [{"name": name, "status": "valid", "valid": True, "capture_sim_ms": None,
             "image_frame": None} for name in cases.CAMERAS]
    res = cases.vc030(StubRun(cams))
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["images"] == 6, res.measured
    assert res.measured["problem_count"] == 6, res.measured
    assert {p["problem"] for p in res.measured["problems"]} == {"no capture_sim_ms stamp"}


@pytest.mark.parametrize("status", ["valid", "invalid", "stale"])
def test_vc030_an_image_recorded_without_its_capture_time_fails(run_for, tmp_path, status):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-030"], f"unstamped-{status}")

    def fn(rec):
        if rec["event"] == "out.checkpoint_inputs" and rec["data"]["frame"] == 300:
            rec["data"]["cameras"][2].update(image_frame=None, capture_sim_ms=None,
                                             arrival_mono_ns=None,
                                             valid=status == "valid", status=status)
        return rec
    assert rewrite_jsonl(d / C2, fn) == 1
    res = verdict(Run(d), "VC-DRIVING-030")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["problems"] == [{"frame": 300, "camera": cases.CAMERAS[2],
                                         "problem": "no capture_sim_ms stamp"}]
    assert res.measured["images"] == 700 * 6, res.measured


@pytest.mark.parametrize("shape", ["every-slot-missing", "no-camera-slots"])
def test_vc030_records_without_any_image_are_inconclusive(run_for, tmp_path, shape):
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-030"], f"no-image-{shape}")

    def fn(rec):
        if rec["event"] == "out.checkpoint_inputs":
            if shape == "no-camera-slots":
                rec["data"]["cameras"] = []
            else:
                for cam in rec["data"]["cameras"]:
                    cam.update(MISSING_SLOT)
        return rec
    assert rewrite_jsonl(d / C2, fn) == 700
    res = verdict(Run(d), "VC-DRIVING-030")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    assert res.measured["images"] == 0, res.measured


def test_vc030_a_motion_sample_without_its_capture_time_fails_without_images(run_for,
                                                                             tmp_path):
    # A sample without its capture time is not met whether or not the records
    # hold an image: the missing images do not hide it.
    d = copied(run_for, tmp_path, CASE_RUN["VC-DRIVING-030"], "no-image-unstamped-sample")

    def cams(rec):
        if rec["event"] == "out.checkpoint_inputs":
            for cam in rec["data"]["cameras"]:
                cam.update(MISSING_SLOT)
        return rec

    def sample(rec):
        if rec["event"] == "out.ego_motion_sample" and rec["data"]["frame"] == 300:
            rec["data"].pop("captureTime")
        return rec
    assert rewrite_jsonl(d / C2, cams) == 700
    assert rewrite_jsonl(d / "score/drivingAgent.jsonl", sample) == 1
    res = verdict(Run(d), "VC-DRIVING-030")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["problems"] == [{"sample": 300, "problem": "no capture time"}]


# ------------------------------------------------------------------ VC-DRIVING-021
# REQ-DRIVING-021: "Met when, in the runs of the criteria of REQ-DRIVING-020,
# the steering command stays at the last value computed from a valid plan from
# the start of the stop response until standstill." A run without a
# stop_response.standstill record never shows the end of that window, so it
# cannot show the criterion met; VC-DRIVING-020 and -022 are inconclusive on it.
def drop_standstill(d: Path) -> int:
    return sum(rewrite_jsonl(p, lambda rec: None
                             if rec["event"] == "stop_response.standstill" else rec)
               for p in sorted((d / "score").glob("*.jsonl")))


@pytest.mark.parametrize("vc", ["VC-DRIVING-020", "VC-DRIVING-021", "VC-DRIVING-022"])
def test_stop_cases_without_standstill_are_inconclusive(run_for, tmp_path, vc):
    d = copied(run_for, tmp_path, CASE_RUN[vc], "no-standstill")
    assert Run(d).standstill() is not None
    assert drop_standstill(d) >= 1
    run = Run(d)
    assert run.stop_begin() is not None and run.standstill() is None
    res = verdict(run, vc)
    assert res.outcome == cases.INCONCL, (vc, res.outcome, res.measured, res.notes)
    assert res.missing == ["stop_response.standstill"], res.missing
