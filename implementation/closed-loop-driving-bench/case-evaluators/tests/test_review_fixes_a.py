"""Tests for review findings on VC-DRIVING-001, -003, -004, -010 and -014.

Each test builds its synthetic run with make_synthetic_run.py in a pytest
temporary directory and edits a hard-linked copy of it, the way the review's
probes edited theirs. A test fails on the evaluator the review found.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

import cases
import make_synthetic_run
import strip
from conftest import verdict
from runio import Run

AGENT = "score/drivingAgent.jsonl"
C2 = "score/checkpointInputs.jsonl"
WORLD = "simulator/world.jsonl"


def rewrite(path: Path, fn) -> int:
    """Stream a JSONL file through fn(record), which returns the record (edited
    or not) or None to drop it. The file is replaced, never written into, so the
    hard-linked original keeps its bytes. Returns the records changed or dropped."""
    out, changed = [], 0
    with open(path) as fh:
        for line in fh:
            if not line.strip():
                continue
            rec = json.loads(line)
            before = json.dumps(rec, sort_keys=True)
            new = fn(rec)
            if new is None:
                changed += 1
                continue
            if json.dumps(new, sort_keys=True) != before:
                changed += 1
            out.append(json.dumps(new, separators=(",", ":")))
    strip._replace(path, "\n".join(out) + "\n")
    return changed


@pytest.fixture(scope="module")
def straight(tmp_path_factory) -> Path:
    """A run of SC-DRIVING-001 without a fault: 400 steps, primed at frame 65,
    a plan at every step from 65 to 399, no stop response."""
    return make_synthetic_run.build(tmp_path_factory.mktemp("fixes-a") / "straight",
                                    scenario="closedLoopRoute", frames=400)


# ------------------------------------------------------------------ VC-DRIVING-001
# REQ-DRIVING-001: "... no two consecutive steps without one, from the end of
# priming to the end of the run or the start of the stop response." The run
# goes on while the world ticks. An agent that stops planning in mid-run
# (it hangs, crashes or is killed) leaves the steps after it without a plan.
VC001 = "VC-DRIVING-001"
CUT = 300


def agent_stops_after(d: Path, cut: int) -> None:
    """The agent writes no plan and no C2 record after step `cut`; the world
    ticks on to frame 399 and no stop response is recorded."""
    def fn(rec):
        data = rec["data"]
        f = data.get("frame", data.get("frameIndex"))
        if rec["event"] in ("out.checkpoint_inputs", "out.plan") and isinstance(f, int) \
                and f > cut:
            return None
        return rec
    assert rewrite(d / C2, fn) == 399 - cut
    assert rewrite(d / AGENT, fn) == 399 - cut


def test_vc001_an_agent_that_stops_planning_while_the_world_ticks_on_fails(straight, tmp_path):
    d = strip.copy_run(straight, tmp_path / "agent-stops")
    agent_stops_after(d, CUT)
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    m = res.measured
    assert m["last_step"] == 399, m                  # the world's last tick
    assert m["steps_without_a_new_plan"] == 399 - CUT, m
    assert m["failing_pairs"][0] == [CUT + 1, CUT + 2], m


def test_vc001_the_unedited_run_passes_to_the_worlds_last_tick(straight):
    res = verdict(Run(straight), VC001)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["first_step"] == 65 and res.measured["last_step"] == 399, res.measured
    assert res.measured["steps_without_a_new_plan"] == 0, res.measured


def test_vc001_a_shorter_world_record_does_not_shorten_the_window(straight, tmp_path):
    # the world record ends at frame 300; the agent's steps go on to 399
    d = strip.copy_run(straight, tmp_path / "short-world")
    assert rewrite(d / WORLD, lambda r: None if r["data"]["frame"] > CUT else r) == 399 - CUT
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["last_step"] == 399, res.measured


def test_vc001_without_a_world_record_the_window_ends_at_the_agents_last_step(straight,
                                                                           tmp_path):
    # as before the fix: with no world record the run's end is the agent's last
    # C2 record, and the verdict says so
    d = strip.copy_run(straight, tmp_path / "agent-stops-no-world")
    agent_stops_after(d, CUT)
    (d / WORLD).unlink()
    res = verdict(Run(d), VC001)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["last_step"] == CUT, res.measured
    assert any(WORLD in n for n in res.notes), res.notes


# ------------------------------------------------------------------ VC-DRIVING-003, -004, -010
# REQ-DRIVING-003: "Met when the inputs recorded for every plan ... hold six
# current images of 512 by 512 pixels in that order and a current front image
# of 1024 by 1024 pixels." REQ-DRIVING-004: "... hold, for each camera, seven
# earlier images ...". REQ-DRIVING-010: "every image and sample given to the
# checkpoint ... has its own capture record of the run ...". The six cameras
# are the slots of ICD A25. A plan whose C2 record lacks one has no current
# image of it, none of its seven earlier images and no capture record of them.
CAMERA_CASES = ("VC-DRIVING-003", "VC-DRIVING-004", "VC-DRIVING-010")
PLAN_FRAMES = (200, 201)


def edit_cameras(d: Path, fn, frames=PLAN_FRAMES) -> None:
    """Apply fn(cameras) -> cameras to the C2 records of `frames`."""
    def edit(rec):
        data = rec["data"]
        if rec["event"] == "out.checkpoint_inputs" and data.get("frame") in frames:
            data["cameras"] = fn(data["cameras"])
        return rec
    assert rewrite(d / C2, edit) == len(frames)


SIX = ", ".join(cases.CAMERAS)
# edit of a plan step's cameras -> the problem the cases must name
DROP = {"drop_one": (lambda cams: [c for c in cams if c.get("name") != "rear"],
                     "no rear camera"),
        "drop_all": (lambda cams: [], f"no {SIX} camera"),
        # a record from before ICD A25 names the cameras cam_<slot>
        "drop_one_cam_names": (lambda cams: [dict(c, name="cam_" + c["name"]) for c in cams
                                             if c.get("name") != "rear"],
                               "no rear camera")}


def reported_frames(vc: str, measured: dict) -> set:
    key = "steps_without_the_six_cameras" if vc == "VC-DRIVING-010" else "problems"
    return {e["frame"] for e in measured[key]}


@pytest.mark.parametrize("mode", sorted(DROP))
@pytest.mark.parametrize("vc", CAMERA_CASES)
def test_a_plan_whose_inputs_lack_a_camera_fails(straight, tmp_path, vc, mode):
    edit, problem = DROP[mode]
    d = strip.copy_run(straight, tmp_path / mode)
    edit_cameras(d, edit)
    run = Run(d)
    assert set(PLAN_FRAMES) <= {s["frame"] for s in cases.plan_steps(run)}
    res = verdict(run, vc)
    assert res.outcome == cases.FAIL, (vc, mode, res.outcome, res.measured, res.notes)
    assert set(PLAN_FRAMES) <= reported_frames(vc, res.measured), res.measured
    assert problem in json.dumps(res.measured), res.measured     # the missing camera is named


@pytest.mark.parametrize("vc", CAMERA_CASES)
def test_the_unedited_run_passes_the_camera_cases(straight, vc):
    res = verdict(Run(straight), vc)
    assert res.outcome == cases.PASS, (vc, res.outcome, res.measured, res.notes)


@pytest.mark.parametrize("vc", CAMERA_CASES)
def test_camera_names_before_a25_are_read_as_the_slots(straight, tmp_path, vc):
    # the agent wrote the CARLA role names cam_<slot> before ICD A25
    d = strip.copy_run(straight, tmp_path / "cam-names")

    def fn(rec):
        if rec["event"] == "out.checkpoint_inputs":
            for c in rec["data"]["cameras"]:
                c["name"] = "cam_" + c["name"]
        return rec
    assert rewrite(d / C2, fn) == 400
    res = verdict(Run(d), vc)
    assert res.outcome == cases.PASS, (vc, res.outcome, res.measured, res.notes)


def test_six_cameras_under_unknown_names_are_not_called_missing(straight, tmp_path):
    # names that are no slot cannot show which camera is missing: VC-DRIVING-003
    # stays inconclusive on them, and the histories are judged per camera
    d = strip.copy_run(straight, tmp_path / "unknown-names")
    edit_cameras(d, lambda cams: [dict(c, name=f"camera{i}") for i, c in enumerate(cams)])
    run = Run(d)
    got = {vc: verdict(run, vc).outcome for vc in CAMERA_CASES}
    assert got == {"VC-DRIVING-003": cases.INCONCL, "VC-DRIVING-004": cases.PASS,
                   "VC-DRIVING-010": cases.PASS}, got


@pytest.mark.parametrize("vc", CAMERA_CASES)
def test_fewer_than_six_cameras_under_unknown_names_fail(straight, tmp_path, vc):
    d = strip.copy_run(straight, tmp_path / "five-unknown")
    edit_cameras(d, lambda cams: [dict(c, name=f"camera{i}")
                                  for i, c in enumerate(DROP["drop_one"][0](cams))])
    res = verdict(Run(d), vc)
    assert res.outcome == cases.FAIL, (vc, res.outcome, res.measured, res.notes)
    assert set(PLAN_FRAMES) <= reported_frames(vc, res.measured), res.measured
    assert "5 cameras, not six" in json.dumps(res.measured), res.measured


# ------------------------------------------------------------------ VC-DRIVING-014
# REQ-DRIVING-014: "Met when, in a run of SC-DRIVING-001, every command that
# reaches the actuation of the vehicle is matched in the Eclipse S-CORE
# communication records to the plan it was computed from, and when, after the
# Eclipse S-CORE communication of the driving system is stopped in the run, no
# further command computed from a plan reaches the actuation." The adapter
# applies no command without a plan reference (actuation-adapter/adapter_core.cpp:
# 118-121); its own stop names no plan (adapter_core.cpp:373-385).
VC014 = "VC-DRIVING-014"
ADAPTER = "score/actuationAdapter.jsonl"


@pytest.fixture(scope="module")
def comm(tmp_path_factory) -> Path:
    """A run of SC-DRIVING-001 whose S-CORE communication is stopped at frame
    500 (50.0 s): 620 steps, the adapter's own stop at 50.2 s."""
    return make_synthetic_run.build(tmp_path_factory.mktemp("fixes-a") / "comm",
                                    scenario="closedLoopRoute", fault="comm_stop",
                                    frames=620, fault_frame=500)


def test_vc014_the_unedited_run_passes(comm):
    res = verdict(Run(comm), VC014)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["commands_matched"] == 435, res.measured


def test_vc014_an_applied_command_that_names_no_plan_fails(comm, tmp_path):
    # the applied, not-stopped actuation states at 20.0 to 20.4 s name no plan
    d = strip.copy_run(comm, tmp_path / "no-plan-reference")

    def fn(rec):
        data = rec["data"]
        if rec["event"] == "out.actuation_state" and data.get("applied") \
                and not data.get("stopInForce") and 20.0 <= float(data["actuationTime"]) <= 20.4:
            data.update(planReference="", acceleration=2.5)
        return rec
    assert rewrite(d / ADAPTER, fn) == 5
    res = verdict(Run(d), VC014)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    unmatched = res.measured["commands_unmatched"]
    assert [(round(u["t"], 1), u["planReference"]) for u in unmatched] == \
        [(20.0, ""), (20.1, ""), (20.2, ""), (20.3, ""), (20.4, "")], unmatched


def test_vc014_an_applied_command_that_names_no_plan_after_the_stop_fails(comm, tmp_path):
    # one more applied, not-stopped actuation state at 50.5 s, after the stop at
    # 50.0 s, naming no plan
    d = strip.copy_run(comm, tmp_path / "no-plan-after-stop")
    p = d / ADAPTER
    last, top = None, 0
    with open(p) as fh:
        for line in fh:
            rec = json.loads(line)
            top = max(top, rec["seq"])
            if rec["event"] == "out.actuation_state" and rec["data"].get("applied"):
                last = rec
    assert last is not None
    extra = json.loads(json.dumps(last))
    extra.update(seq=top + 1, t_mono_ns=last["t_mono_ns"] + 600_000_000,
                 t_real_ns=last["t_real_ns"] + 600_000_000)
    extra["data"].update(actuationTime=50.5, planReference="", acceleration=2.5)
    strip.replace_bytes(p, p.read_bytes() + (json.dumps(extra) + "\n").encode())
    res = verdict(Run(d), VC014)
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["commands_unmatched"] == [{"t": 50.5, "planReference": ""}], \
        res.measured


def test_vc014_the_adapters_own_stop_is_not_a_command_without_a_plan(comm, tmp_path):
    # the adapter's stop state names no plan; marked applied, it is still the
    # adapter's own stop (stopInForce 1), not a command that came from no plan
    d = strip.copy_run(comm, tmp_path / "own-stop-applied")

    def fn(rec):
        if rec["event"] == "out.actuation_state" and rec["data"].get("stopInForce"):
            rec["data"]["applied"] = 1
        return rec
    assert rewrite(d / ADAPTER, fn) == 1
    res = verdict(Run(d), VC014)
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
