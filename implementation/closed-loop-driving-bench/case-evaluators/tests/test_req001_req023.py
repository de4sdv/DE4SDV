"""REQ-DRIVING-001 as amended and REQ-DRIVING-023 as written.

REQ-DRIVING-001: from the end of priming to the end of the run or the start of
the stop response, no two consecutive 100 ms steps of simulation time pass
without a new plan. A single step without its own plan is allowed: a frame FEO
merged into the next step after an overrun gets no plan (ICD A23), nor does a
step whose camera image missed the step's frame deadline.

Each test edits a hard-linked copy of a fixture run, never the fixture.
"""

from __future__ import annotations

import cases
import gaps
from conftest import edit_jsonl, verdict
from runio import Run
from test_review_findings import AGENT, C2, copied, records

VC001 = "VC-DRIVING-001"


def drop_plans(d, frames):
    """Remove the plans of `frames`, as the agent leaves a step without one."""
    dropped = 0
    for event in ("out.plan", "in.plan"):
        n = edit_jsonl(d / AGENT, event,
                       lambda data: None if data.get("frameIndex") in frames else data)
        if event == "out.plan":
            dropped = n
    assert dropped == len(frames), (frames, dropped)


def merge_frame(d, frame):
    """Frame `frame` merged by FEO into the next step after an overrun (ICD A23,
    `ConditionMerged` in agent/cc/agent_ffi.cpp): no C2 step record and no plan of its own;
    the next step's C2 record lists it under mergedFrames."""
    def fn(data):
        if data["frame"] == frame:
            return None
        if data["frame"] == frame + 1:
            data["mergedFrames"] = [{"frame": frame, "conditioned": True,
                                     "condition_ms": 0.5, "readyByDeadline": False}]
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", fn) == 2
    drop_plans(d, [frame])


# ------------------------------------------------------------------ REQ-DRIVING-001
def test_vc001_one_step_without_a_plan_passes(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "001-one-step")
    drop_plans(d, [300])
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["steps_without_a_new_plan"] == 1, res.measured
    assert res.measured["longest_run_without_a_new_plan"] == 1, res.measured
    assert res.measured["failing_pairs"] == [], res.measured
    assert res.thresholds["consecutive_steps_without_a_new_plan_max"] == 1, res.thresholds


def test_vc001_a_merged_frame_without_a_plan_passes(run_for, tmp_path):
    # the shape of run M1: FEO merged frame 300 into step 301 after an overrun
    d = copied(run_for, tmp_path, "nominal", "001-merged")
    merge_frame(d, 300)
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    m = res.measured
    assert m["steps_in_window"] == 635, m            # frames 65 .. 699
    assert m["steps_without_a_new_plan"] == 1, m
    assert m["merged_frames_without_a_plan"] == 1, m
    assert m["longest_run_without_a_new_plan"] == 1, m
    assert m["failing_pairs"] == [], m
    assert "A23" in gaps.amendments_for(VC001)


def test_vc001_a_merged_frame_next_to_a_step_without_a_plan_fails(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "001-merged-and-late")
    merge_frame(d, 300)
    drop_plans(d, [301])                 # e.g. the step after it missed an image
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    m = res.measured
    assert m.get("failing_pairs") == [[300, 301]], m
    assert m["steps_without_a_new_plan"] == 2 and m["merged_frames_without_a_plan"] == 1, m
    assert m["longest_run_without_a_new_plan"] == 2, m


def test_vc001_the_windows_first_step_needs_no_plan_before_it(run_for, tmp_path):
    # frame 65 is the end of priming; frame 64 is outside the window
    d = copied(run_for, tmp_path, "nominal", "001-first-step")
    drop_plans(d, [65])
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["first_step"] == 65 and res.measured["failing_pairs"] == []


def test_vc001_the_windows_first_two_steps_without_plans_fail(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "001-first-two")
    drop_plans(d, [65, 66])
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured.get("failing_pairs") == [[65, 66]], res.measured


# ------------------------------------------------------------------ REQ-DRIVING-023
# One reading for both halves (README, "Readings"): camera c has a condition at
# step k when it has no valid image to date (kCameraMissing), its image of k is
# invalid (kCameraInvalid), or its newest valid image is more than 200 ms of
# simulation time older than k (kCameraStale), whether or not the image of k
# arrived. Exactly 200 ms is not a condition. A camera whose images are withheld
# from step k therefore has a condition from k + 2.
MISSING_IMAGE = {"image_frame": None, "capture_sim_ms": None, "arrival_mono_ns": None,
                 "valid": False, "status": "missing"}


def set_camera(d, frames, slot, **fields):
    """Rewrite camera `slot` of the C2 records of `frames`
    (`de4sdv_condition_step` in agent/cc/agent_ffi.cpp)."""
    def fn(data):
        if data["frame"] in frames:
            data["cameras"][slot].update(fields)
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", fn) == len(frames)


def test_vc023_an_invalid_image_without_a_status_is_never_the_newest(run_for, tmp_path):
    # Records from before the C2 status field mark an invalid image only with valid false. As in the
    # agent (ICD A28), it is a condition at its own step and never becomes the camera's newest image.
    d = copied(run_for, tmp_path, "nominal", "023-legacy-invalid")

    def fn(data):
        if data["frame"] == 298:
            data["cameras"][5].pop("status", None)
            data["cameras"][5]["valid"] = False
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", fn) == 1
    set_camera(d, [299, 300], 5, **MISSING_IMAGE)
    got = {f: c["cause"] for f, c in cases.camera_conditions_by_reading(Run(d)).items() if f >= 298}
    # the newest valid image stays the one of frame 297: 300 ms old at 300
    assert got == {298: "kCameraInvalid", 300: "kCameraStale"}, got


def test_vc023_reading_decision_table(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "023-table")
    set_camera(d, [0, 1, 2, 3], 2, **MISSING_IMAGE)          # no image to date
    set_camera(d, [298, 299, 300], 5, **MISSING_IMAGE)       # newest: frame 297
    set_camera(d, [400], 1, valid=False, status="invalid")   # a corrupt image
    # images of frame 497 delivered at steps 498 .. 500: 300 ms old at 500
    set_camera(d, [498, 499], 4, image_frame=497, capture_sim_ms=49700)
    set_camera(d, [500], 4, image_frame=497, capture_sim_ms=49700,
               valid=False, status="stale")
    got = {f: c["cause"] for f, c in cases.camera_conditions_by_reading(Run(d)).items()}
    assert got == {0: "kCameraMissing", 1: "kCameraMissing", 2: "kCameraMissing",
                   3: "kCameraMissing",
                   300: "kCameraStale",       # absent, newest image 300 ms old
                   400: "kCameraInvalid", 500: "kCameraStale"}, got
    # 298 (100 ms) and 299 (exactly 200 ms) are not conditions


# The fault half (SC-DRIVING-003). The fixture withholds the images of rear_left
# from frame 250 (the last at 249) and the agent stops at 252 with kCameraStale.
VC023 = "VC-DRIVING-023"


def set_stop_begin(d, frame, cause):
    """Move the agent's stop_response.begin (agent/cc/agent_logic.cpp:623-633)."""
    assert len(records(d / AGENT, "stop_response.begin")) == 1

    def fn(data):
        data.update(frame=frame, capture_sim_ms=frame * 100, cause=cause,
                    causeValue=cases.CAUSES.index(cause))
        return data
    edit_jsonl(d / AGENT, "stop_response.begin", fn)


def test_vc023_withheld_camera_stop_when_the_newest_image_passes_200_ms(run_for):
    res = verdict(run_for("fault-camera_missing"), VC023)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["condition_frame"] == 252, res.measured
    assert res.measured["condition"] == "kCameraStale", res.measured
    assert abs(res.measured["delay_s"]) < 1e-9, res.measured


def test_vc023_withheld_camera_stop_at_the_first_missing_image_fails(run_for, tmp_path):
    # one late image is tolerated: a stop at 250 has no condition in the 100 ms before it
    d = copied(run_for, tmp_path, "fault-camera_missing", "023-first-missing")
    set_stop_begin(d, 250, "kCameraMissing")
    res = verdict(Run(d), VC023)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured.get("stop_without_condition_frame") == 250, res.measured


def test_vc023_stop_when_the_newest_image_is_exactly_200_ms_old_fails(run_for, tmp_path):
    d = copied(run_for, tmp_path, "fault-camera_missing", "023-exactly-200")
    set_stop_begin(d, 251, "kCameraStale")
    res = verdict(Run(d), VC023)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured.get("stop_without_condition_frame") == 251, res.measured


def test_vc023_stop_200_ms_after_the_first_condition_fails(run_for, tmp_path):
    # the camera still has a condition at 253 and 254, but the limit runs from 252
    d = copied(run_for, tmp_path, "fault-camera_missing", "023-late")
    set_stop_begin(d, 254, "kCameraStale")
    res = verdict(Run(d), VC023)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["condition_frame"] == 252, res.measured
    assert abs(res.measured["delay_s"] - 0.2) < 1e-9, res.measured


def test_vc023_corrupt_image_is_a_condition_at_its_own_step(run_for):
    res = verdict(run_for("fault-camera_invalid"), VC023)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["condition_frame"] == 250, res.measured
    assert res.measured["condition"] == "kCameraInvalid", res.measured


def test_vc023_images_delivered_more_than_200_ms_old_are_a_condition(run_for):
    res = verdict(run_for("fault-camera_stale"), VC023)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["condition_frame"] == 252, res.measured
    assert res.measured["condition"] == "kCameraStale", res.measured
