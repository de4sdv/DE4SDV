"""R8: the C1 record, as the case evaluators read it."""

from __future__ import annotations

import json
import math
import sys
from types import SimpleNamespace

import carla
import pytest

import cases
import runio
import world_side as W
from conftest import (BENCH, FakeClock, make_tool, read_jsonl, run_tool, write_run_record,
                      write_route)

RECORD_FIELDS = {
    "frame", "sim_ms", "handoverFrame", "egoPose", "velocity", "acceleration",
    "angular_velocity", "lane", "control", "controlSource", "autopilotEnabled",
    "trafficManagerEnabled", "sensors", "collisions", "laneInvasions",
    "tickDurationMonoNs", "latenessMonoNs",
}
POSE_FIELDS = {"x", "y", "yaw"}
VELOCITY_FIELDS = {"speed_mps", "heading_rad"}
ACCEL_FIELDS = {"longitudinal_mps2", "lateral_mps2"}
ANGULAR_FIELDS = {"roll_rad_s", "pitch_rad_s", "yaw_rad_s"}
LANE_FIELDS = {"road", "lane", "lat_m", "junction"}
CONTROL_FIELDS = {"throttle", "brake", "steer", "accelMps2"}
SENSOR_FIELDS = {"name", "actor_id", "alive", "attached"}


def records(run_dir):
    return [r for r in read_jsonl(run_dir / "simulator/world.jsonl") if r["event"] == "tick"]


def test_every_record_has_exactly_the_c1_fields(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.5, run_s=0.5)
    assert code == 0
    recs = records(run_dir)
    assert recs
    for rec in recs:
        data = rec["data"]
        assert set(data) == RECORD_FIELDS
        assert set(data["egoPose"]) == POSE_FIELDS
        assert set(data["velocity"]) == VELOCITY_FIELDS
        assert set(data["acceleration"]) == ACCEL_FIELDS
        assert set(data["angular_velocity"]) == ANGULAR_FIELDS
        assert set(data["lane"]) == LANE_FIELDS
        assert set(data["control"]) == CONTROL_FIELDS
        assert len(data["sensors"]) == 6
        assert all(set(s) == SENSOR_FIELDS for s in data["sensors"])
        assert isinstance(data["frame"], int) and isinstance(data["sim_ms"], int)
        assert data["sim_ms"] == data["frame"] * 100
        assert isinstance(data["collisions"], list) and isinstance(data["laneInvasions"], list)
        assert isinstance(data["autopilotEnabled"], bool)
        assert isinstance(data["trafficManagerEnabled"], bool)
        assert data["controlSource"] in ("actuationAdapter", "autopilot")


def test_world_jsonl_holds_ticks_only_and_lifecycle_goes_to_the_side_log(tmp_path, route,
                                                                        profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.3, run_s=0.3)
    assert code == 0
    world = read_jsonl(run_dir / "simulator/world.jsonl")
    assert {r["event"] for r in world} == {"tick"}
    side = read_jsonl(run_dir / "simulator/worldSide.jsonl")
    assert [r["event"] for r in side][0] == "start"
    assert "config" in [r["event"] for r in side]
    assert [r["event"] for r in side][-1] == "stop"
    assert all(r["host"] == "simulator" for r in world + side)
    assert all(r["component"] == "worldSide" for r in world + side)


def test_envelope_is_the_route_provider_envelope(tmp_path):
    sys.path.insert(0, str(BENCH / "navigation"))
    from route_provider import RunLog

    log = RunLog(tmp_path / "ref.jsonl")
    log.write("tick", {"frame": 1})
    log.close()
    reference = read_jsonl(tmp_path / "ref.jsonl")[0]

    writer = W.JsonlWriter(tmp_path / "mine.jsonl")
    writer.write("tick", {"frame": 1})
    writer.close()
    mine = read_jsonl(tmp_path / "mine.jsonl")[0]
    assert list(mine) == list(reference) == list(runio.ENVELOPE)
    assert type(mine["seq"]) is type(reference["seq"]) is int
    assert isinstance(mine["t_mono_ns"], int) and isinstance(mine["t_real_ns"], int)


def test_pose_is_the_map_frame_of_icd_section_9(tmp_path, profile):
    # spawn at CARLA (10, -4) yaw 30 deg; the route start in the map frame is
    # (10, 4) heading -30 deg -- the ICD 9 mirror
    route = write_route(tmp_path / "route.json", start=(10.0, 4.0, -math.pi / 6))
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    client.world.map.spawn_transforms[0] = carla.Transform(
        carla.Location(10.0, -4.0, 0.0), carla.Rotation(0.0, 30.0, 0.0))
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.2, run_s=0.2)
    assert code == 0
    data = records(run_dir)[0]["data"]
    assert data["egoPose"]["x"] == pytest.approx(10.0)
    assert data["egoPose"]["y"] == pytest.approx(4.0)          # -(-4)
    assert data["egoPose"]["yaw"] == pytest.approx(-math.radians(30.0))
    assert data["velocity"]["heading_rad"] == pytest.approx(-math.radians(30.0))
    # the fake map puts the lane centre 1 m at CARLA -y; right of the lane is +y
    assert data["lane"]["lat_m"] == pytest.approx(1.0)
    assert data["lane"]["road"] == 296 and data["lane"]["junction"] is False


def test_non_finite_kinematics_are_null_not_dropped(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)

    def hook(world, frame):
        hero = world.get_actors().filter("vehicle.*")[0]
        if frame == 4:
            hero._velocity = carla.Vector3D(float("nan"), 0.0, 0.0)
            hero._acceleration = carla.Vector3D(float("inf"), 0.0, 0.0)

    client.world.motion_hook = hook
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.3, run_s=0.3)
    assert code == 0
    bad = next(r["data"] for r in records(run_dir) if r["data"]["frame"] == 4)
    assert bad["velocity"]["speed_mps"] is None
    assert bad["acceleration"]["longitudinal_mps2"] is None
    # runio reads a null as non-finite, not as an absent field
    assert math.isnan(runio.num(bad["velocity"], "speed_mps"))
    assert math.isnan(runio.num(bad["acceleration"], "longitudinal_mps2"))


def test_collision_and_lane_events_are_attached_to_their_frame(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    client.world.queue_event(5, "collision", {"other_actor": "vehicle.tesla.model3",
                                              "other_actor_id": 9010,
                                              "normal_impulse": (1.0, 2.0, 3.0)})
    client.world.queue_event(5, "lane_invasion", {"markings": ["Solid", "Broken"]})
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.3, run_s=0.4)
    assert code == 0
    rec = next(r["data"] for r in records(run_dir) if r["data"]["frame"] == 5)
    assert rec["collisions"] == [{"frame": 5, "other_actor": "vehicle.tesla.model3",
                                  "other_actor_id": 9010,
                                  "impulse_mps": {"x": 1.0, "y": 2.0, "z": 3.0}}]
    assert rec["laneInvasions"] == [{"frame": 5, "markings": ["Solid", "Broken"]}]
    others = [r for r in records(run_dir) if r["data"]["frame"] != 5]
    assert all(not r["data"]["collisions"] and not r["data"]["laneInvasions"]
               for r in others)


def test_a_callback_that_arrives_late_is_kept_and_counted(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)

    def hook(world, frame):
        if frame != 6:
            return
        sensor = world.get_actors().filter("sensor.other.collision")[0]
        late = SimpleNamespace(frame=5, other_actor=None, normal_impulse=None)
        for callback in list(sensor.listeners):
            callback(late)

    client.world.motion_hook = hook
    tool = make_tool(route, profile, tmp_path / "run", client, clock, warmup=0.3, run_s=0.4)
    tool.start()
    try:
        tool.run()
        tool.write_summary()
        rec = next(r["data"] for r in records(tmp_path / "run")
                   if r["data"]["frame"] == 6)
        assert [c["frame"] for c in rec["collisions"]] == [5]
        summary = json.loads((tmp_path / "run/simulator/summary.json").read_text())
        assert summary["lateSensorEvents"] == 1
    finally:
        tool.teardown()


# ------------------------------------------------- the evaluators read it (R8)


def _evaluable_run(tmp_path, profile, *, warmup: float, fault: str | None = None):
    route = write_route(tmp_path / "route.json")
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    faults = (fault,) if fault else ()
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=warmup, run_s=1.0, faults=faults)
    assert code == 0
    write_run_record(run_dir, scenario="closedLoopRoute", fault="camera_missing"
                     if fault else "none")
    return run_dir


def test_runio_reads_the_world_records(tmp_path, profile):
    run_dir = _evaluable_run(tmp_path, profile, warmup=1.0)
    run = runio.Run(run_dir)
    world = run.world()
    by_frame = run.world_by_frame()
    first = W.SETTLE_MIN_TICKS + 1                  # the run's first frame, after setup
    assert len(world) == len(by_frame) == 20
    assert sorted(by_frame) == list(range(first, first + 20))
    assert run.world_last_frame() == first + 19
    assert run.world_frame(first + 6)["data"]["frame"] == first + 6
    with pytest.raises(runio.MissingEvidence):
        run.world_frame(999)
    # no C8 record on a fault-free run: injections() says so instead of inventing one
    with pytest.raises(runio.MissingEvidence):
        run.injections()


def test_cases_helpers_read_the_world_records(tmp_path, profile):
    run_dir = _evaluable_run(tmp_path, profile, warmup=1.0)
    run = runio.Run(run_dir)
    first = W.SETTLE_MIN_TICKS + 1
    sensors = cases.sensors_at(run)
    assert sorted(sensors) == list(range(first, first + 20))
    assert [s["name"] for s in sensors[first + 2]] == [
        "cam_front", "cam_front_left", "cam_front_right",
        "cam_rear_left", "cam_rear", "cam_rear_right"]
    pose = cases.ego_pose_at(run, first + 2)
    assert set(pose) == {"x", "y", "yaw"}
    assert cases._speed_mps(run, first + 2) == pytest.approx(0.0)
    rec = run.world_frame(first + 2)
    assert float(cases.wd_get(rec, "velocity", "speed_mps")) == 0.0
    assert float(cases.wd_get(rec, "acceleration", "longitudinal_mps2")) == 0.0
    assert cases.wd_get(rec, "lane", "road") == 296
    # C2's camera metadata is not the world side's: the case says so, it does not guess
    with pytest.raises(runio.MissingEvidence):
        cases.first_camera_condition(run)
    with pytest.raises(runio.MissingEvidence):
        cases.camera_views(run)


def test_vc011_cannot_judge_a_world_only_run(tmp_path, profile):
    """What the evaluator does with a run that has the C1 records only.

    VC-011 needs the agent's `out.command`, `out.mode` and `in.plan` records, so
    on a world-only run it is inconclusive and names the missing record -- it
    never passes. Its world loop (cases.py, the `for f, rec in wb.items()`
    block) has no handover filter: every tick must say
    controlSource == 'actuationAdapter'. The announced warm-up ticks say
    'autopilot', so on a real run those ticks are reported as foreign control.
    That is a bench-controller/case concern, not something the world side can
    fix without breaking C1 (one record per tick).
    """
    run_dir = _evaluable_run(tmp_path, profile, warmup=1.0)
    run = runio.Run(run_dir)
    result = cases.evaluate_case(run, "VC-DRIVING-011").as_dict()
    assert result["verdict"] == "inconclusive"
    assert "score/drivingAgent.jsonl" in " ".join(result["missing"])
    assert result["notes"] or result["missing"]
    # the world side's own part is exact: the switch is at F_h, per record
    summary = json.loads((run_dir / "simulator/summary.json").read_text())
    fh = summary["handoverFrame"]
    for frame, rec in run.world_by_frame().items():
        expected = "autopilot" if frame < fh else "actuationAdapter"
        assert rec["data"]["controlSource"] == expected
        assert rec["data"]["autopilotEnabled"] == (frame < fh)
