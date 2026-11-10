"""Tests for the findings R1 to R16 of the independent review of the evaluators.

Each test states a producer's real record shape (with the producer file and
line) or a documented reading, and fails on the evaluator the review found.
The fixture runs come from make_synthetic_run.py; a test that needs another
shape edits a hard-linked copy, never the fixture.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import cases
import strip
from conftest import CASE_RUN, edit_jsonl, verdict
import pytest
from runio import MissingEvidence, Run

AGENT = "score/drivingAgent.jsonl"
ADAPTER = "score/actuationAdapter.jsonl"
C2 = "score/checkpointInputs.jsonl"


def copied(run_for, tmp_path, name, tag):
    return strip.copy_run(run_for(name).root, tmp_path / f"{name}-{tag}")


def records(path, event=None):
    out = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    return [r for r in out if event is None or r["event"] == event]


def rewrite(path, fn):
    """Apply fn(record) to every record of a JSONL file; fn returns the new
    record or None to drop it."""
    out = []
    for rec in records(path):
        new = fn(rec)
        if new is not None:
            out.append(json.dumps(new, separators=(",", ":")))
    strip._replace(path, "\n".join(out) + "\n")


def rename_event(path, old, new):
    def fn(rec):
        if rec["event"] == old:
            rec["event"] = new
        return rec
    rewrite(path, fn)


def write_run(root, record: dict, files: dict) -> Path:
    """A small run directory: run_record.json plus JSONL files, each record
    in the envelope of ICD section 6. `files` maps a relative path to a list
    of (event, data, t_mono_s) tuples."""
    root.mkdir(parents=True)
    base = {"contractIdentity": "de4sdv.driving.icd.v2"}
    (root / "run_record.json").write_text(json.dumps(dict(base, **record), indent=1) + "\n")
    for rel, recs in files.items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        lines = []
        for seq, (event, data, t) in enumerate(recs, 1):
            lines.append(json.dumps({"t_mono_ns": int(t * 1e9), "t_real_ns": int((t + 1e9) * 1e9),
                                     "host": "score", "component": "drivingAgent",
                                     "event": event, "seq": seq, "data": data}))
        p.write_text("\n".join(lines) + "\n")
    return root


def agent_sample(frame: int, capture_frame: int | None = None, speed=18.0) -> tuple:
    """out.ego_motion_sample as agent/cc/agent_ffi.cpp:1088-1095 writes it."""
    cf = frame if capture_frame is None else capture_frame
    return ("out.ego_motion_sample",
            {"stage": "synthetic", "speed": speed, "longitudinalAcceleration": 0.0,
             "lateralAcceleration": 0.0, "yawRate": 0.0, "captureTime": round(cf * 0.1, 4),
             "frame": frame, "clocks": {"captureTime": "simulation"}}, frame * 0.1)


def agent_mode(frame: int, mode: str, cause: str = "kNone") -> tuple:
    """out.mode as agent/cc/agent_logic.cpp:600-621 writes it."""
    return ("out.mode", {"mode": cases.MODES.index(mode), "modeName": mode,
                         "cause": cases.CAUSES.index(cause), "causeName": cause,
                         "frameIndex": frame, "captureTime": round(frame * 0.1, 4),
                         "decisionTime": frame * 0.1 + 0.03,
                         "clocks": {"captureTime": "simulation", "decisionTime": "monotonic"}},
            frame * 0.1 + 0.03)


def agent_stop_begin(frame: int, cause: str) -> tuple:
    """stop_response.begin as agent/cc/agent_logic.cpp:623-633 writes it."""
    return ("stop_response.begin",
            {"cause": cause, "causeValue": cases.CAUSES.index(cause), "frame": frame,
             "capture_sim_ms": frame * 100, "source": "superviseLoop",
             "decision_mono_s": frame * 0.1 + 0.04,
             "clocks": {"capture_sim_ms": "simulation", "decision_mono_s": "monotonic"}},
            frame * 0.1 + 0.04)


# ------------------------------------------------------------------ R1
# The agent logs the motion sample of each step as out.ego_motion_sample, with
# the step frame and a clocks entry (agent/cc/agent_ffi.cpp:1088-1095). No
# producer writes in.ego_motion.
def test_r1_fixture_writes_the_agents_ego_motion_sample_record(run_for):
    path = run_for("nominal").root / AGENT
    names = Counter(r["event"] for r in records(path))
    assert names["in.ego_motion"] == 0, "the fixture writes an event no producer writes"
    assert names["out.ego_motion_sample"] == 700
    first = records(path, "out.ego_motion_sample")[0]["data"]
    assert isinstance(first["frame"], int)
    assert first["clocks"] == {"captureTime": "simulation"}


def test_r1_evaluator_reads_out_ego_motion_sample(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r1")
    rename_event(d / AGENT, "in.ego_motion", "out.ego_motion_sample")
    run = Run(d)
    assert len(run.ego_samples()) == 700, "the agent's motion samples are not read"
    for vc in ("VC-DRIVING-016", "VC-DRIVING-030"):
        res = verdict(run, vc)
        assert res.outcome == cases.PASS, (vc, res.outcome, res.missing, res.notes)


# ------------------------------------------------------------------ R9
# Real runs start at frame 48 or 5000, so a record index is not a frame. The
# motion sample carries its step frame (agent/cc/agent_ffi.cpp:1094).
def motion_stale_run(tmp_path, first=5000, last=5100, frozen_from=5050, stop_at=5052,
                     prime=5010, name="motion-stale"):
    agent = [("priming.complete", {"stage": "synthetic", "frame": prime,
                                   "sim_ms": prime * 100, "historiesReady": True},
              prime * 0.1 + 0.02)]
    for f in range(first, last + 1):
        mode = ("kStarting" if f < prime else "kDriving" if f < stop_at
                else "kStopResponse")
        agent.append(agent_sample(f, min(f, frozen_from - 1)))
        agent.append(agent_mode(f, mode, "kMotionStale" if f >= stop_at else "kNone"))
        if f == stop_at:
            agent.append(agent_stop_begin(f, "kMotionStale"))
    return write_run(tmp_path / name,
                     {"scenario": "degradedInputOrPlan",
                      "scenarioVariant": {"fault": "motion_stale"}},
                     {AGENT: agent})


def test_r9_vc024_takes_the_step_from_the_samples_frame(tmp_path):
    res = verdict(Run(motion_stale_run(tmp_path)), "VC-DRIVING-024")
    assert res.outcome == cases.PASS, (res.outcome, res.missing, res.notes, res.measured)
    assert res.measured["condition_frame"] == 5052


def test_r9_vc024_same_run_from_frame_zero_gives_the_same_frame(tmp_path):
    res = verdict(Run(motion_stale_run(tmp_path, first=0, last=100, frozen_from=50,
                                       stop_at=52, prime=10, name="from-zero")),
                  "VC-DRIVING-024")
    assert res.outcome == cases.PASS, (res.outcome, res.missing, res.notes, res.measured)
    assert res.measured["condition_frame"] == 52


# ------------------------------------------------------------------ R14
# A camera with no image at a step is written with null image_frame,
# capture_sim_ms and arrival_mono_ns (agent/cc/agent_ffi.cpp:1028-1033): it is
# not an image, so it carries no capture time to mark.
def test_r14_vc030_skips_a_camera_slot_without_an_image(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r14-missing-slot")

    def fn(data):
        if data["frame"] == 300:
            cam = data["cameras"][5]
            cam.update({"image_frame": None, "capture_sim_ms": None, "arrival_mono_ns": None,
                        "valid": False, "status": "missing"})
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", fn) == 1
    res = verdict(Run(d), "VC-DRIVING-030")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)


# The engine says when its histories are complete: C2 `primed` (ICD A26,
# agent/cc/agent_ffi.cpp:1018 and 1072). The release is the first primed step,
# not a count of history references or motion samples.
def test_r14_vc009_release_is_the_first_primed_step(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r14-primed-late")

    def fn(data):
        data["primed"] = data["frame"] >= 100
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", fn) > 0
    res = verdict(Run(d), "VC-DRIVING-009")
    # the fixture's vehicle accelerates from the end of priming, so with the
    # engine primed at frame 100 it was released too early
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["release_frame"] == 100


def test_r14_vc009_needs_the_primed_field(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r14-no-primed")

    def fn(data):
        data.pop("primed", None)
        return data
    edit_jsonl(d / C2, "out.checkpoint_inputs", fn)
    res = verdict(Run(d), "VC-DRIVING-009")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    assert any("primed" in m for m in res.missing)


# ------------------------------------------------------------------ R2
# The adapter stamps its stop records with a payload time plus clocks, or a
# suffixed field (actuation-adapter/log_records.h:117-142): begin carries
# actuationTime with clocks {actuationTime: simulation}; standstill carries
# t_sim_ms. ICD section 6 allows both forms.
ADAPTER_BEGIN_KEYS = {"cause", "actuationTime", "stopSinceMono", "acceleration",
                      "steeringAngle", "clocks"}
ADAPTER_STANDSTILL_KEYS = {"cause", "frame", "t_sim_ms", "speedMps", "clocks"}


def adapter_shape(rec):
    """Rewrite an adapter stop record into the adapter's own shape."""
    d = rec["data"]
    t_ms = d.get("capture_sim_ms", d.get("t_sim_ms"))
    if t_ms is None:
        t_ms = round(d["actuationTime"] * 1000.0)
    cause = cases.enum_name(d.get("cause"), cases.CAUSES)
    if rec["event"] == "stop_response.begin":
        rec["data"] = {"cause": cause, "actuationTime": round(t_ms / 1000.0, 4),
                       "stopSinceMono": rec["t_mono_ns"] / 1e9, "acceleration": -4.0,
                       "steeringAngle": 0.0,
                       "clocks": {"actuationTime": "simulation",
                                  "stopSinceMono": "monotonic"}}
    elif rec["event"] == "stop_response.standstill":
        rec["data"] = {"cause": cause, "frame": int(round(t_ms / 100)), "t_sim_ms": t_ms,
                       "speedMps": 0.0, "clocks": {"t_sim_ms": "simulation"}}
    return rec


def test_r2_fixture_writes_the_adapters_stop_records(run_for):
    path = run_for("comm-stop").root / ADAPTER
    begin = records(path, "stop_response.begin")
    stand = records(path, "stop_response.standstill")
    assert begin and stand
    assert set(begin[0]["data"]) == ADAPTER_BEGIN_KEYS, begin[0]["data"]
    assert begin[0]["data"]["cause"] == "kCommandTimeout"
    assert set(stand[0]["data"]) == ADAPTER_STANDSTILL_KEYS, stand[0]["data"]


def test_r2_adapter_shaped_stop_records_are_read(run_for, tmp_path):
    d = copied(run_for, tmp_path, "comm-stop", "r2-shape")
    before = Run(run_for("comm-stop").root).stop_begin()["t_sim"]
    rewrite(d / ADAPTER, lambda rec: adapter_shape(rec)
            if rec["event"].startswith("stop_response.") else rec)
    run = Run(d)
    assert abs(run.stop_begin()["t_sim"] - before) < 1e-9
    for vc in ("VC-DRIVING-001", "VC-DRIVING-028", "VC-DRIVING-029"):
        res = verdict(run, vc)
        assert res.outcome != cases.ERROR, (vc, res.notes)
    res = verdict(run, "VC-DRIVING-029")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)


def test_r2_stop_record_without_a_simulation_stamp_is_missing_c9(run_for, tmp_path):
    d = copied(run_for, tmp_path, "comm-stop", "r2-unstamped")

    def fn(rec):
        if rec["event"] == "stop_response.begin":
            rec = adapter_shape(rec)
            rec["data"].pop("clocks")
        return rec
    rewrite(d / ADAPTER, fn)
    res = verdict(Run(d), "VC-DRIVING-029")
    assert res.outcome == cases.INCONCL, (res.outcome, res.notes)
    assert "C9" in res.icd_changes


# ------------------------------------------------------------------ R16 (A24, held)
# A24 (ICD section 4): the adapter's stop begins once more than 200 ms of
# simulation time have passed since the last valid command, at the third
# tick (actuation-adapter/adapter_core.cpp:10-14, 231-235). After a lost
# command path the stop reaches the actuation 300 ms after the last applied
# command, the limit of REQ-DRIVING-028.
def test_r16_adapter_stop_reaches_the_actuation_300_ms_after_the_last_command(run_for):
    res = verdict(run_for("comm-stop"), "VC-DRIVING-028")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert abs(res.measured["delay_s"] - 0.3) < 1e-9, res.measured


# After its stop the adapter applies the stop control at every tick and logs
# it as out.vehicle_control with trigger "stop" (actuation-adapter/
# actuation_adapter_main.cpp:182-186, log_records.h:84-97); it publishes no
# further out.actuation_state.
def test_r16_fixture_logs_the_adapters_vehicle_control(run_for):
    path = run_for("comm-stop").root / ADAPTER
    controls = records(path, "out.vehicle_control")
    assert controls, "the fixture writes no out.vehicle_control"
    stop_frame = round(records(path, "stop_response.begin")[0]["data"]["actuationTime"] * 10)
    after = [c["data"] for c in controls if c["data"]["frame"] >= stop_frame]
    assert after and all(c["trigger"] == "stop" for c in after)
    states = [r["data"] for r in records(path, "out.actuation_state") if r["data"]["stopInForce"]]
    assert len(states) == 1


def test_r16_vc028_fails_when_a_control_after_the_stop_is_not_the_stop(run_for, tmp_path):
    d = copied(run_for, tmp_path, "comm-stop", "r16-not-held")
    stop_s = Run(d).stop_begin()["t_sim"]
    frame = int(round(stop_s / 0.1)) + 3
    # the adapter's shape (actuation-adapter/log_records.h:84-97), trigger "tick"
    extra = {"t_mono_ns": int((1000.0 + frame * 0.1 + 0.046) * 1e9),
             "t_real_ns": int((1762300000.0 + frame * 0.1 + 0.046) * 1e9),
             "host": "score", "component": "actuationAdapter",
             "event": "out.vehicle_control", "seq": 999999,
             "data": {"frame": frame, "t_sim_ms": frame * 100, "throttle": 0.4, "brake": 0.0,
                      "steer": 0.0, "handBrake": False, "trigger": "tick",
                      "controlSource": "actuationAdapter",
                      "clocks": {"t_sim_ms": "simulation"}}}
    p = d / ADAPTER
    strip.replace_bytes(p, p.read_bytes() + (json.dumps(extra) + "\n").encode())
    res = verdict(Run(d), "VC-DRIVING-028")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)


def test_r16_vc028_without_vehicle_control_is_inconclusive(run_for, tmp_path):
    d = copied(run_for, tmp_path, "comm-stop", "r16-no-controls")
    rewrite(d / ADAPTER, lambda rec: None if rec["event"] == "out.vehicle_control" else rec)
    res = verdict(Run(d), "VC-DRIVING-028")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    assert any("out.vehicle_control" in m for m in res.missing)


# ------------------------------------------------------------------ R3
# A16's waypointsInWindow counts the points of the route's centre lines; the
# navigation library builds one centre line per road-id run of two or more
# points (navigation/navigation_raster.cpp:815-827, agent/cc/
# navigation_input.cpp:108-124). With no accepted route both counts are 0.
def test_r3_fixture_route_has_a_single_point_road_run(run_for):
    route = json.loads((run_for("nominal").root / "navigation/route.json").read_text())
    roads = [w[3] for w in route["waypoints"]]
    singles = [i for i in range(1, len(roads) - 1)
               if roads[i] != roads[i - 1] and roads[i] != roads[i + 1]]
    assert singles, "the fixture route has no road-id run of one point"


def test_r3_recount_counts_centre_line_points_only(run_for):
    res = verdict(run_for("nominal"), "VC-DRIVING-007")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["recount_done"] is True
    assert res.measured["recount_mismatches"] == []


def test_r3_steps_without_an_accepted_route_are_not_recounted(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r3-no-route")

    def step(data):
        if data["frame"] == 300:
            data["routeMask"].update({"routeSha256": None, "corridorCells": 0,
                                      "waypointsInWindow": 0, "waypointsOnCorridor": 0})
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", step) == 1
    # a step without an accepted route is not planned (agent/cc/agent_ffi.cpp:997, 1161)
    for event in ("out.plan", "in.plan"):
        edit_jsonl(d / AGENT, event, lambda data: None if data.get("frameIndex") == 300 else data)
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)


# ------------------------------------------------------------------ R12
# A step without an accepted route is not planned (agent/cc/agent_ffi.cpp:997,
# 1161), so a null routeSha256 belongs on steps without a plan only. Without a
# route in the run record, a step's sha is compared with the route
# announcement in force at that step (score/route_provider.jsonl, ICD A18).
def drop_record_route(d):
    rec = json.loads((d / "run_record.json").read_text())
    rec.pop("route", None)
    strip._replace(d / "run_record.json", json.dumps(rec, indent=1, sort_keys=True) + "\n")


def test_r12_null_route_sha_on_a_plan_step_fails_vc007(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r12-null-on-plan")

    def step(data):
        if data["frame"] == 300:
            data["routeMask"].update({"routeSha256": None, "corridorCells": 0,
                                      "waypointsInWindow": 0, "waypointsOnCorridor": 0})
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", step) == 1
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["sha_mismatches"][0]["frame"] == 300


def append_announcement(d, frame, sha):
    p = d / "score/route_provider.jsonl"
    last = records(p)[-1]
    rec = dict(last, seq=last["seq"] + 1, t_mono_ns=int((1000.0 + frame * 0.1) * 1e9),
               t_real_ns=int((1762300000.0 + frame * 0.1) * 1e9))
    rec["data"] = dict(last["data"], issueTime=round(frame * 0.1, 4), routeSha256=sha)
    strip.replace_bytes(p, p.read_bytes() + (json.dumps(rec) + "\n").encode())


def test_r12_an_announcement_after_the_last_step_is_in_force_at_no_step(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r12-late-announcement")
    drop_record_route(d)
    append_announcement(d, 800, "0" * 64)       # the run ends at frame 699
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)


def test_r12_a_step_differing_from_the_announcement_in_force_fails(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r12-other-route")
    drop_record_route(d)

    def ann(data):
        if 40.0 <= data["issueTime"] <= 45.0:
            data["routeSha256"] = "f" * 64
        return data
    assert edit_jsonl(d / "score/route_provider.jsonl", "out.route_announcement", ann) > 0
    res = verdict(Run(d), "VC-DRIVING-007")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["sha_mismatches"][0]["frame"] == 400


# ------------------------------------------------------------------ R5
# The success criteria of REQ-DRIVING-003, -004, -006, -007, -008 and -010 are
# stated for the inputs recorded for every plan. The agent writes a C2 record
# for every step, primed or not (agent/cc/agent_ffi.cpp:1020-1079); a step
# without a plan is not judged, and a run without plans decides nothing.
PER_PLAN = ("VC-DRIVING-003", "VC-DRIVING-004", "VC-DRIVING-006", "VC-DRIVING-007",
            "VC-DRIVING-008", "VC-DRIVING-010")


def test_r5_per_plan_cases_are_inconclusive_without_plans(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r5-no-plans")
    rewrite(d / AGENT, lambda rec: None if rec["event"] in ("out.plan", "in.plan") else rec)
    run = Run(d)
    got = {vc: verdict(run, vc) for vc in PER_PLAN}
    bad = {vc: (r.outcome, r.missing) for vc, r in got.items()
           if r.outcome != cases.INCONCL or not any("out.plan" in m for m in r.missing)}
    assert not bad, bad


def test_r5_steps_without_a_plan_are_not_judged(run_for):
    # the fixture's steps before the end of priming have no plan and no rows
    run = run_for("nominal")
    assert any(not s["ego_motion_history"] for s in run.input_steps())
    for vc in PER_PLAN:
        res = verdict(run, vc)
        assert res.outcome == cases.PASS, (vc, res.outcome, res.measured, res.notes)


# The engine's newest row is the sample of frame k-1: the rows are worked out
# from the poses of frames k-65 .. k with numpy.gradient, rows [1:-1]
# (agent/DESIGN.md, "Ego-motion history"). Row j is compared with the source's
# sample of frame k-64+j (REQ-DRIVING-008 as amended on 2026-11-10).
def test_r5_vc008_rows_end_one_frame_before_the_step(run_for):
    import math
    run = run_for("nominal")
    wb = run.world_by_frame()
    ox, oy, _ = run.events(AGENT, "rig")[0]["data"]["result"]["origin"]

    def ref(g):                 # frame g's pose moved to the rig origin (vehicle y right)
        p = wb[g]["data"]["egoPose"]
        c, s = math.cos(p["yaw"]), math.sin(p["yaw"])
        return p["x"] + ox * c + oy * s, p["y"] + ox * s - oy * c

    def dist(a, b):
        return math.hypot(ref(a)[0] - ref(b)[0], ref(a)[1] - ref(b)[1])

    def newest(k):              # row 63 of step k: frame k-1, inside a window ending at k
        speed_k = dist(k, k - 1) / 0.1                   # the window's end: one-sided
        return [dist(k, k - 2) / 0.2,
                (speed_k - dist(k - 1, k - 3) / 0.2) / 0.2]

    step = next(s for s in run.input_steps() if s["frame"] == 100)
    row = step["ego_motion_history"][-1]
    assert abs(row[0] - newest(100)[0]) < 1e-6 and abs(row[1] - newest(100)[1]) < 1e-6, \
        (row, newest(100))
    # the vehicle speeds up at frame 100: the sample of the step itself is another
    assert abs(row[0] - newest(101)[0]) > 0.1, (row, newest(101))


def test_r5_vc008_rows_ending_at_the_step_fail(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r5-rows-at-step")
    wb = Run(d).world_by_frame()

    def fn(data):
        # every primed step's rows for frames k-63 .. k: the newest at the step
        f = data["frame"]
        if data["ego_motion_history"]:
            data["ego_motion_history"] = [
                [wb[f - 63 + j]["data"]["velocity"]["speed_mps"],
                 wb[f - 63 + j]["data"]["acceleration"]["longitudinal_mps2"], 0.0, 0.0]
                for j in range(64)]
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", fn) > 0
    res = verdict(Run(d), "VC-DRIVING-008")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    # judged on the values of the rows, not on a missing record or a row count
    assert res.measured["worst_abs_error"]["speed"] > cases.THRESHOLDS["ego_speed_tol_mps"]
    assert all(p["problems"][0].startswith("sample frame") for p in res.measured["problems"])


# ------------------------------------------------------------------ R13
# A25: C2 names each camera by the checkpoint's slot; before A25 the agent
# wrote the CARLA role names cam_<slot> (agent DESIGN.md, conditionInputs
# startup). A17: the stub engine hands the simulator image as it is, so the
# 512x512 tile sizes belong to the checkpoint engine only. The agent names its
# engine in the `engine` record (agent/cc/agent_ffi.cpp:656-657).
def set_engine(d, engine):
    def fn(rec):
        if rec["event"] == "engine":
            rec["data"]["setup"]["engine"] = engine
            rec["data"]["setup"]["engineRecord"]["engine"] = engine
        return rec
    rewrite(d / AGENT, fn)


def test_r13_fixture_logs_the_agents_engine_record(run_for):
    eng = records(run_for("nominal").root / AGENT, "engine")
    assert eng, "the fixture writes no engine record"
    assert eng[0]["data"]["setup"]["engine"] == "checkpoint"


def test_r13_old_camera_names_are_read_as_the_slots(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r13-old-names")

    def fn(data):
        for c in data["cameras"]:
            c["name"] = "cam_" + c["name"]
        return data
    edit_jsonl(d / C2, "out.checkpoint_inputs", fn)
    res = verdict(Run(d), "VC-DRIVING-003")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert any("A25" in n for n in res.notes), res.notes


def test_r13_unknown_camera_names_do_not_fail_vc003(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r13-unknown-names")

    def fn(data):
        for i, c in enumerate(data["cameras"]):
            c["name"] = f"camera{i}"
        return data
    edit_jsonl(d / C2, "out.checkpoint_inputs", fn)
    res = verdict(Run(d), "VC-DRIVING-003")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)


def test_r13_slots_out_of_order_still_fail_vc003(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r13-order")

    def fn(data):
        if data["frame"] == 300:
            data["cameras"][1], data["cameras"][2] = data["cameras"][2], data["cameras"][1]
        return data
    edit_jsonl(d / C2, "out.checkpoint_inputs", fn)
    res = verdict(Run(d), "VC-DRIVING-003")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)


def test_r13_stub_engine_makes_vc002_and_vc003_inconclusive(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r13-stub")
    rewrite(d / AGENT, lambda rec: rec)
    if not records(d / AGENT, "engine"):
        # the agent's engine record (agent/cc/agent_ffi.cpp:656-657)
        p = d / AGENT
        first = records(p)[0]
        eng = dict(first, event="engine", seq=0,
                   data={"stage": "synthetic", "setup_s": 0.2, "refused": False,
                         "setup": {"engine": "stub", "engineRecord": {"engine": "stub"}}})
        strip.replace_bytes(p, (json.dumps(eng) + "\n").encode() + p.read_bytes())
    set_engine(d, "stub")
    run = Run(d)
    for vc in ("VC-DRIVING-002", "VC-DRIVING-003"):
        res = verdict(run, vc)
        assert res.outcome == cases.INCONCL, (vc, res.outcome, res.notes)
        assert any("stub" in n for n in res.notes), (vc, res.notes)


def test_stub_engine_makes_vc013_inconclusive(run_for, tmp_path):
    # REQ-DRIVING-013 bounds the time the driving system takes to plan. A stub
    # engine makes no inference, so its plan times say nothing about the bound.
    d = copied(run_for, tmp_path, "nominal", "vc013-stub")
    if not records(d / AGENT, "engine"):
        # the agent's engine record (agent/cc/agent_ffi.cpp:656-657)
        p = d / AGENT
        first = records(p)[0]
        eng = dict(first, event="engine", seq=0,
                   data={"stage": "synthetic", "setup_s": 0.2, "refused": False,
                         "setup": {"engine": "stub", "engineRecord": {"engine": "stub"}}})
        strip.replace_bytes(p, (json.dumps(eng) + "\n").encode() + p.read_bytes())
    set_engine(d, "stub")
    res = verdict(Run(d), "VC-DRIVING-013")
    assert res.outcome == cases.INCONCL, (res.outcome, res.notes)
    assert any("stub" in n for n in res.notes), res.notes


# ------------------------------------------------------------------ R4
# Reading of REQ-DRIVING-023 to -025 (README, "Readings"): the stop response
# presupposes a driving vehicle. While starting, the agent logs a fault but
# starts no stop and primes again (agent/cc/agent_logic.cpp:335-338). The
# baseline is the first condition at a step at or after priming.complete
# whose previous mode record is kDriving; without one the case is inconclusive.
def set_c2_camera_missing(d, frame, slot=5):
    def fn(data):
        if data["frame"] == frame:
            data["cameras"][slot].update({"image_frame": None, "capture_sim_ms": None,
                                          "arrival_mono_ns": None, "valid": False,
                                          "status": "missing"})
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", fn) == 1


def test_r4_vc023_ignores_a_camera_condition_before_driving(run_for, tmp_path):
    d = copied(run_for, tmp_path, "fault-camera_missing", "r4-cam-early")
    for f in (10, 11, 12):               # newest image frame 9: a condition at 12
        set_c2_camera_missing(d, f)
    res = verdict(Run(d), "VC-DRIVING-023")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["condition_frame"] == 252


def test_r4_vc023_is_inconclusive_when_the_agent_never_drives(run_for, tmp_path):
    d = copied(run_for, tmp_path, "fault-camera_missing", "r4-never-drives")

    def fn(data):
        data["mode"] = cases.MODES.index("kStarting")
        return data
    edit_jsonl(d / AGENT, "out.mode", fn)
    res = verdict(Run(d), "VC-DRIVING-023")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)


def test_r4_vc024_ignores_a_motion_condition_before_driving(run_for, tmp_path):
    d = copied(run_for, tmp_path, "fault-motion_stale", "r4-motion-early")

    def fn(data):
        if data["frame"] == 10:
            data["speed"] = None
        return data
    assert edit_jsonl(d / AGENT, "out.ego_motion_sample", fn) == 1
    res = verdict(Run(d), "VC-DRIVING-024")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["condition_frame"] == 252


def test_r4_vc025_ignores_a_route_condition_before_driving(run_for, tmp_path):
    d = copied(run_for, tmp_path, "fault-route_empty", "r4-route-early")

    def fn(data):
        if abs(data["issueTime"] - 1.0) < 1e-9:
            data["corridorPoints"] = 0
        return data
    assert edit_jsonl(d / "score/route_provider.jsonl", "out.route_announcement", fn) == 1
    res = verdict(Run(d), "VC-DRIVING-025")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["condition_frame"] == 250


# ------------------------------------------------------------------ R10
# VC-DRIVING-023's no-fault half, on runs of SC-DRIVING-001. Reading of
# REQ-DRIVING-023 (statement and rationale "one late image is tolerated, a
# second means the camera has stopped"; README, "Readings"): a camera
# condition exists at a step when the camera has had no image, its image is
# invalid, or its newest image is more than 200 ms of simulation time older
# than the step. A camera-caused stop that begins without such a condition
# fails the no-fault half.
def nominal_with_camera_stop(run_for, tmp_path, tag, missing_frames, stop_frame,
                             cause="kCameraMissing"):
    d = copied(run_for, tmp_path, "nominal", tag)
    for f in missing_frames:
        set_c2_camera_missing(d, f)
    ev, data, t = agent_stop_begin(stop_frame, cause)
    last = records(d / AGENT)[-1]
    rec = {"t_mono_ns": int((1000.0 + t) * 1e9), "t_real_ns": int((1762300000.0 + t) * 1e9),
           "host": "score", "component": "drivingAgent", "event": ev,
           "seq": last["seq"] + 1, "data": data}
    p = d / AGENT
    strip.replace_bytes(p, p.read_bytes() + (json.dumps(rec) + "\n").encode())
    return d


def test_r10_vc023_is_judged_on_closed_loop_route_runs(run_for):
    import evaluate_run
    report = evaluate_run.evaluate(run_for("nominal").root)
    assert "VC-DRIVING-023" in report["cases"], report["skipped"].get("VC-DRIVING-023")
    assert report["cases"]["VC-DRIVING-023"]["outcome"] == cases.PASS


def test_r10_camera_stop_after_one_missing_image_fails(run_for, tmp_path):
    d = nominal_with_camera_stop(run_for, tmp_path, "r10-one-late", [300], 300)
    res = verdict(Run(d), "VC-DRIVING-023")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)


def test_r10_newest_image_exactly_200_ms_old_is_not_a_condition(run_for, tmp_path):
    assert cases.CAMERA_NEWEST_IMAGE_LIMIT_MS == 200
    d = nominal_with_camera_stop(run_for, tmp_path, "r10-two-late", [299, 300], 300,
                                 cause="kCameraStale")
    res = verdict(Run(d), "VC-DRIVING-023")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured.get("stop_without_condition_frame") == 300, res.measured


def test_r10_newest_image_300_ms_old_is_a_condition(run_for, tmp_path):
    # the camera has images, the newest 300 ms old: kCameraStale, as the agent names it
    d = nominal_with_camera_stop(run_for, tmp_path, "r10-stopped", [298, 299, 300], 300,
                                 cause="kCameraStale")
    res = verdict(Run(d), "VC-DRIVING-023")
    # the stop was due: it began at the step of the condition
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["first_condition_frame"] == 300


def test_r10_a_condition_while_driving_without_a_stop_fails(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r10-no-stop")
    for f in (298, 299, 300):
        set_c2_camera_missing(d, f)
    res = verdict(Run(d), "VC-DRIVING-023")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)


# ------------------------------------------------------------------ R6
# REQ-DRIVING-032: for every command, input age at actuation and planning
# interval in simulation time, planning time and S-CORE transport delay on the
# monotonic clock. Its success criterion sets no ranges. Every stop command
# names one frozen plan (ICD section 4), so commands are not joined by
# planReference: the agent's out.command and the adapter's in.command carry
# the same productionTime (agent/cc/agent_logic.cpp:653,
# actuation-adapter/log_records.h:46-63), and the adapter logs a command's
# out.actuation_state right after its in.command (actuation_adapter_main.cpp:244-256).
ADAPTER_IN_COMMAND_KEYS = {"acceleration", "steeringAngle", "productionTime", "planReference",
                           "arrival_mono_s", "valid", "rejectReason", "clocks"}


def test_r6_fixture_in_command_has_the_adapters_shape(run_for):
    recs = records(run_for("nominal").root / ADAPTER, "in.command")
    assert recs and set(recs[0]["data"]) == ADAPTER_IN_COMMAND_KEYS, sorted(recs[0]["data"])


def test_r6_vc032_joins_each_command_not_its_plan_reference(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r6-frozen")
    frozen = next(p["data"]["planReference"] for p in records(d / AGENT, "out.plan")
                  if p["data"]["frameIndex"] == 299)

    def agent(rec):
        if rec["event"] == "out.command" and 300 <= rec["data"]["step_capture_sim_ms"] // 100 < 310:
            rec["data"].update(planReference=frozen, plan_capture_sim_ms=29900)
        return rec
    rewrite(d / AGENT, agent)
    window = {round(r["data"]["productionTime"], 6) for r in records(d / AGENT, "out.command")
              if r["data"]["planReference"] == frozen}

    def adapter(rec):
        if rec["event"] == "in.command" and round(rec["data"]["productionTime"], 6) in window:
            rec["data"]["planReference"] = frozen
        return rec
    rewrite(d / ADAPTER, adapter)
    res = verdict(Run(d), "VC-DRIVING-032")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    n = len(records(d / AGENT, "out.command"))
    assert res.measured["samples"]["transport"] == n, res.measured["samples"]


def test_r6_vc032_sets_no_range_without_a_model_source(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r6-slow-plan")

    def fn(data):
        if data["frameIndex"] == 300:
            data["productionTime"] = round(data["productionTime"] + 0.6, 6)
        return data
    assert edit_jsonl(d / AGENT, "out.plan", fn) == 1
    res = verdict(Run(d), "VC-DRIVING-032")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["planning_time_s"]["max"] > 0.6


def test_r6_vc032_a_reception_before_its_production_is_no_measurement(run_for, tmp_path):
    # The agent and the adapter stamp production and arrival on the score host's
    # monotonic clock. An arrival before the production means a wrong join or a
    # wrong stamp: the run then cannot show the four quantities. A join by plan
    # reference (the review's R6) yields such values while the plan is frozen.
    d = copied(run_for, tmp_path, "nominal", "r6-negative-transport")
    target = round(records(d / ADAPTER, "in.command")[40]["data"]["productionTime"], 6)

    def adapter(rec):
        if rec["event"] == "in.command" and round(rec["data"]["productionTime"], 6) == target:
            rec["data"]["arrival_mono_s"] = round(rec["data"]["productionTime"] - 0.5, 6)
        return rec
    rewrite(d / ADAPTER, adapter)
    res = verdict(Run(d), "VC-DRIVING-032")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    assert any("negative" in n for n in res.notes), res.notes


# ------------------------------------------------------------------ R7
# REQ-DRIVING-013: over a 60 s wall-clock window that starts at the end of
# priming, with the simulation at a real-time factor of at least 0.95. Plans
# made while stopped are not driving plans (run N: 209 of 241 plans in
# kStandstill). REQ-DRIVING-015/-016/-017: over a 60 s window of the run.
def test_r7_vc013_needs_60_s_of_driving_plans(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r7-standstill")

    def fn(data):
        if data["frameIndex"] >= 400:
            data.update(mode=cases.MODES.index("kStandstill"), modeName="kStandstill")
        return data
    assert edit_jsonl(d / AGENT, "out.mode", fn) > 0
    res = verdict(Run(d), "VC-DRIVING-013")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)


def test_r7_vc013_rtf_over_the_window_not_the_run(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r7-late-pause")

    def fn(rec):
        if rec["data"].get("frame", -1) >= 690:          # after the window
            rec["t_mono_ns"] += 20_000_000_000
            rec["t_real_ns"] += 20_000_000_000
        return rec
    rewrite(d / "simulator/world.jsonl", fn)
    res = verdict(Run(d), "VC-DRIVING-013")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["rtf"] >= 0.95


def drop_after(d, rel, event, key, last):
    return edit_jsonl(d / rel, event, lambda data: None if data[key] > last else data)


def test_r7_vc015_window_must_be_covered(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r7-short-plans")
    assert drop_after(d, AGENT, "out.plan", "frameIndex", 400) > 0
    res = verdict(Run(d), "VC-DRIVING-015")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)


def test_r7_vc016_window_must_be_covered(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r7-short-samples")
    assert drop_after(d, AGENT, "out.ego_motion_sample", "frame", 400) > 0
    res = verdict(Run(d), "VC-DRIVING-016")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)


def test_r7_vc017_window_must_be_covered(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r7-short-health")
    p = d / "guest/observer.jsonl"
    health = records(p, "rx.health")
    t_end = health[0]["t_real_ns"] + 30_000_000_000
    rewrite(p, lambda rec: None if rec["event"] == "rx.health" and rec["t_real_ns"] > t_end
            else rec)
    res = verdict(Run(d), "VC-DRIVING-017")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)


# ------------------------------------------------------------------ R8
# The model identifies a start with a checkpoint that is not pinned as
# checkpointRefusal (DrivingScenarioIdentity; VC-DRIVING-035). Run R of the
# bench is labelled closedLoopRoute with checkpointCase wrong_pin and kRefused
# at every step: it is judged as a refusal run and the label conflict flagged.
def relabel(d, **changes):
    rec = json.loads((d / "run_record.json").read_text())
    for k, v in changes.items():
        if k == "checkpointCase":
            rec["scenarioVariant"]["checkpointCase"] = v
        else:
            rec[k] = v
    strip._replace(d / "run_record.json", json.dumps(rec, indent=1, sort_keys=True) + "\n")


def test_r8_refusal_labelled_route_goes_to_vc035(run_for, tmp_path):
    import evaluate_run
    d = copied(run_for, tmp_path, "refusal-mismatch", "r8-label")
    relabel(d, scenario="closedLoopRoute")
    report = evaluate_run.evaluate(d)
    assert list(report["cases"]) == ["VC-DRIVING-035"], list(report["cases"])
    assert report["cases"]["VC-DRIVING-035"]["outcome"] == cases.PASS
    assert report["label_conflicts"], report.get("label_conflicts")
    assert "checkpointRefusal" in report["label_conflicts"][0]


def test_r8_refused_modes_alone_route_to_vc035(run_for, tmp_path):
    d = copied(run_for, tmp_path, "refusal-mismatch", "r8-modes")
    relabel(d, scenario="closedLoopRoute", checkpointCase="pinned")
    run = Run(d)
    assert cases.applicable(run) == ["VC-DRIVING-035"], cases.applicable(run)
    assert any("kRefused" in c for c in cases.label_conflicts(run))


def test_r8_campaign_exits_non_zero_on_a_label_conflict(run_for, tmp_path, monkeypatch):
    import sys
    import evaluate_campaign
    root = tmp_path / "campaign"
    root.mkdir()
    d = copied(run_for, root, "refusal-mismatch", "R")
    relabel(d, scenario="closedLoopRoute", campaignId="wp2-g4-checkpoint")
    out = tmp_path / "campaign_verdicts.json"
    monkeypatch.setattr(sys, "argv", ["evaluate_campaign.py", str(root), "--out", str(out),
                                      "--quiet"])
    rc = evaluate_campaign.main()
    report = json.loads(out.read_text())
    assert rc != 0, report
    assert report.get("label_conflicts"), report


# ------------------------------------------------------------------ R11
# Run N's priming.complete (frame 113) predates A26: its step is not
# conditioned, and the engine's first conditioned primed step is 179, where
# its plans begin. The end of priming is then taken from C2 (A26:
# agent/cc/agent_ffi.cpp:1018, 1072-1073) and the record is flagged. The run
# ends at the agent's last step (its last C2 record), not at the simulator's.
def test_r11_vc001_flags_priming_complete_on_an_unconditioned_step(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r11-early-priming")

    def prime(data):
        data.update(frame=50, sim_ms=5000)
        return data
    assert edit_jsonl(d / AGENT, "priming.complete", prime) == 1

    def step(data):
        if data["frame"] == 50:          # the pre-A26 shape of run N at frame 113
            data.update(conditioned=False, primed=True)
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", step) == 1
    res = verdict(Run(d), "VC-DRIVING-001")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)
    assert res.measured["first_step"] == 65, res.measured
    assert res.measured["priming_record_conflict"]["frame"] == 50, res.measured


def test_r11_vc001_run_end_is_the_agents_last_step(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r11-world-runs-on")
    p = d / "simulator/world.jsonl"
    world = records(p)
    last = world[-1]
    extra = []
    for k in range(1, 21):             # the simulator ticks on after the agent ended
        rec = json.loads(json.dumps(last))
        rec["seq"] = last["seq"] + k
        rec["t_mono_ns"] += k * 100_000_000
        rec["t_real_ns"] += k * 100_000_000
        rec["data"]["frame"] += k
        rec["data"]["sim_ms"] += k * 100
        extra.append(json.dumps(rec))
    strip.replace_bytes(p, p.read_bytes() + ("\n".join(extra) + "\n").encode())
    res = verdict(Run(d), "VC-DRIVING-001")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)


def test_r11_cases_reading_the_world_declare_c1():
    for vc in ("VC-DRIVING-010", "VC-DRIVING-013"):
        assert "C1" in cases.CASES[vc]["needs"], (vc, cases.CASES[vc]["needs"])
    assert "C1" not in cases.CASES["VC-DRIVING-001"]["needs"]


def test_r11_a_missing_world_record_names_c1(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r11-no-world")
    (d / "simulator/world.jsonl").unlink()
    for vc in ("VC-DRIVING-010", "VC-DRIVING-013"):
        res = verdict(Run(d), vc)
        assert res.outcome == cases.INCONCL, (vc, res.outcome)
        assert "C1" in res.icd_changes, (vc, res.icd_changes, res.missing)


# ------------------------------------------------------------------ R15
# The vehicle configuration (ICD section 5) is named by the run record with its
# SHA-256 (C7). The limits are used only from a file whose SHA-256 is the
# recorded one; an absolute path names a file on the bench host, and a file at
# that path on the evaluating host is not evidence unless its hash agrees.
def vehicle_entry(d):
    return json.loads((d / "run_record.json").read_text())["vehicleConfiguration"]


def test_r15_vc012_with_a_changed_vehicle_configuration_is_inconclusive(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r15-changed")
    p = d / vehicle_entry(d)["path"]
    cfg = json.loads(p.read_text())
    cfg["max_road_wheel_angle_deg"] = 70.0
    strip._replace(p, json.dumps(cfg, indent=1) + "\n")
    res = verdict(Run(d), "VC-DRIVING-012")
    assert res.outcome == cases.INCONCL, (res.outcome, res.measured, res.notes)
    assert "C7" in res.icd_changes


def test_r15_absolute_path_with_another_file_is_not_used(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r15-absolute")
    original = json.loads((d / vehicle_entry(d)["path"]).read_text())
    host = tmp_path / "evaluating-host" / "vehicle_limits.json"
    host.parent.mkdir()
    host.write_text(json.dumps(dict(original, max_road_wheel_angle_deg=70.0)) + "\n")
    (d / vehicle_entry(d)["path"]).unlink()           # not retained in the run
    relabel(d, vehicleConfiguration=dict(vehicle_entry(d), path=str(host)))
    for vc in ("VC-DRIVING-012", "VC-DRIVING-033"):
        res = verdict(Run(d), vc)
        assert res.outcome == cases.INCONCL, (vc, res.outcome, res.measured, res.notes)


def test_r15_absolute_path_with_the_recorded_file_is_used(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r15-absolute-same")
    retained = d / vehicle_entry(d)["path"]
    host = tmp_path / "bench-host" / "vehicle_limits.json"
    host.parent.mkdir()
    host.write_bytes(retained.read_bytes())
    retained.unlink()
    relabel(d, vehicleConfiguration=dict(vehicle_entry(d), path=str(host)))
    res = verdict(Run(d), "VC-DRIVING-012")
    assert res.outcome == cases.PASS, (res.outcome, res.measured, res.notes)


# ------------------------------------------------------------------ R16 (amendments, boundary)
def test_r16_run_report_names_the_amendments_a_case_relies_on(run_for):
    import evaluate_run
    report = evaluate_run.evaluate(run_for("nominal").root)
    assert report["cases"]["VC-DRIVING-007"]["amendments"] == ["A11", "A16", "A18"]
    assert "A26" in report["cases"]["VC-DRIVING-001"]["amendments"]
    report = evaluate_run.evaluate(run_for("comm-stop").root)
    assert "A24" in report["cases"]["VC-DRIVING-028"]["amendments"]


def test_r16_adapter_stop_one_step_after_300_ms_fails(run_for, tmp_path):
    d = copied(run_for, tmp_path, "comm-stop", "r16-late")

    def fn(rec):
        dd = rec["data"]
        if rec["event"] == "out.actuation_state" and dd.get("stopInForce") == 1:
            dd["actuationTime"] = round(dd["actuationTime"] + 0.1, 4)
            dd["stopSince"] = round(dd["stopSince"] + 0.1, 4)
        if rec["event"] == "stop_response.begin":
            dd["actuationTime"] = round(dd["actuationTime"] + 0.1, 4)
        return rec
    rewrite(d / ADAPTER, fn)
    res = verdict(Run(d), "VC-DRIVING-028")
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert abs(res.measured["delay_s"] - 0.4) < 1e-9, res.measured


# A merged frame the agent conditioned had every camera valid (A23,
# agent/cc/agent_ffi.cpp:575-615); its images count as the camera's newest.
def test_r10_a_conditioned_merged_frame_counts_as_the_newest_image(run_for, tmp_path):
    d = nominal_with_camera_stop(run_for, tmp_path, "r10-merged", [298, 300], 300)

    def fn(data):
        if data["frame"] == 299:
            return None                  # a merged frame has no C2 record of its own
        if data["frame"] == 300:
            data["mergedFrames"] = [{"frame": 299, "conditioned": True, "condition_ms": 0.5,
                                     "readyByDeadline": False}]
        return data
    assert edit_jsonl(d / C2, "out.checkpoint_inputs", fn) == 2
    res = verdict(Run(d), "VC-DRIVING-023")
    # newest image of the camera is frame 299 (100 ms old): no condition at 300
    assert res.outcome == cases.FAIL, (res.outcome, res.measured, res.notes)
    assert res.measured["stop_without_condition_frame"] == 300


# The agent's records test (agent/cc/tests/test_records_against_evaluators.py,
# check_cases_that_need_other_components) judges VC-032 on a run with neither
# C2 nor adapter records and expects the adapter log named, as before R6.
def test_r6_vc032_names_the_adapter_log_first(run_for, tmp_path):
    d = copied(run_for, tmp_path, "nominal", "r6-no-adapter")
    (d / ADAPTER).unlink()
    (d / C2).unlink()
    with pytest.raises(MissingEvidence) as exc:
        cases.vc032(Run(d))
    assert "actuationAdapter" in exc.value.what, exc.value.what
