"""Orchestrator review of the world side (2026-11-09): behaviour of the real CARLA 0.9.16 API
that the first fake did not model, and the frames of the C1 kinematics.

  - a new actor's transform reads as zero until the next tick (synchronous mode), while
    get_physics_control answers at once: the rig origin must come from a simulated, settled hero;
  - BlueprintLibrary.find raises IndexError for an unknown id;
  - C1 kinematics in the map frame of ICD section 9, as the evaluators' reference producer
    (make_synthetic_run.py) writes them: yaw rate counter-clockwise positive (the sign of
    d egoPose.yaw / dt), lateral acceleration positive to the left (= speed x yaw rate);
  - control.accelMps2 is what was applied, which the world side cannot see: null;
  - the default run has no autopilot warm-up (REQ-DRIVING-011: no autopilot at any time of the run).
"""

from __future__ import annotations

import math

import carla
import numpy as np
import pytest

import world_side as W
from conftest import FakeClock, RIG_PATH, make_tool, read_json, read_jsonl, run_tool, write_route


def world_records(run_dir):
    return [r for r in read_jsonl(run_dir / "simulator/world.jsonl") if r["event"] == "tick"]


def test_rig_origin_is_the_settled_vehicle_origin(tmp_path, profile):
    """Away from the world origin and with a heading, as on Town10HD_Opt's route start: the
    synthetic route of conftest starts at (0, 0) facing 0, where a zero transform equals the true
    one and the pre-tick read cannot show."""
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    client.world.map.spawn_transforms = [carla.Transform(carla.Location(-64.83, 24.50, 0.3),
                                                         carla.Rotation(pitch=0.0, yaw=20.0, roll=0.0))]
    route = write_route(tmp_path / "route_town10.json", start=(-64.83, -24.50, -math.radians(20.0)))
    tool = make_tool(route, profile, tmp_path / "run", client, clock, warmup=0.0, run_s=0.3)
    tool.start()
    try:
        hero = tool.hero
        rig = W.load_rig_module(str(RIG_PATH))
        if not hero._simulated():
            client.world.tick()          # what the agent reads later: the simulated hero
        expected, _info = rig.ref_origin_from_vehicle(hero)
        assert tool.origin is not None
        assert np.allclose(np.asarray(tool.origin), expected, atol=1e-6), (tool.origin, expected)
        _payload, cams = rig.load_profile(str(profile))
        spawns = [s for s in client.world.spawned if s["type_id"] == "sensor.camera.rgb"]
        for spawn, cam in zip(spawns, cams):
            T = np.asarray(cam["camera_to_reference"], dtype=np.float64).reshape(4, 4)
            loc, (pitch, yaw, roll) = rig.actor_pose_in_vehicle(T, expected)
            t = spawn["transform"]
            assert np.allclose([t.location.x, t.location.y, t.location.z], loc, atol=1e-6)
            assert np.allclose([t.rotation.pitch, t.rotation.yaw, t.rotation.roll], [pitch, yaw, roll], atol=1e-6)
    finally:
        tool.teardown()


def test_setup_ticks_settle_the_hero_and_are_not_run_records(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock, warmup=0.0, run_s=0.3)
    assert code == 0
    side = read_jsonl(run_dir / "simulator/worldSide.jsonl")
    setup = [r["data"] for r in side if r["event"] == "setup"]
    assert len(setup) == 1 and setup[0]["settled"] is True
    assert setup[0]["setupTicks"] >= 2
    recs = world_records(run_dir)
    assert recs[0]["data"]["frame"] > setup[0]["settledAtFrame"]
    # the cameras exist from the first run tick on
    assert all(len(r["data"]["sensors"]) == 6 for r in recs)


def test_unknown_vehicle_blueprint_is_a_bench_error(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    vehicle = tmp_path / "vehicle.json"
    vehicle.write_text('{"vehicle_blueprint": "vehicle.nobody.nothing"}')
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock, warmup=0.0, run_s=0.3,
                             extra=("--vehicle-config", str(vehicle)))
    assert code == 1
    errors = [r["data"]["reason"] for r in read_jsonl(run_dir / "simulator/worldSide.jsonl") if r["event"] == "error"]
    assert errors and "vehicle.nobody.nothing" in errors[0] and "not in the blueprint library" in errors[0]


def test_marker_falls_back_to_another_static_prop(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    lib = client.world._blueprints
    lib._blueprints = [b for b in lib._blueprints if b.id not in W.STATIC_PROP_CANDIDATES]
    lib._blueprints.append(carla.Blueprint("static.prop.bench01"))
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock, warmup=0.0, run_s=0.3)
    assert code == 0
    markers = [s for s in client.world.spawned if s["type_id"].startswith("static.prop.")]
    assert [m["type_id"] for m in markers] == ["static.prop.bench01"]
    assert markers[0]["attributes"]["role_name"].startswith(W.MARKER_PREFIX)


def _turning_hook(yaw_rate_carla_dps, speed=10.0, roll_dps=3.0, pitch_dps=4.0):
    """The hero turns at a constant CARLA yaw rate (deg/s; CARLA is left-handed, so a negative rate
    turns left), with the centripetal acceleration of that turn."""
    def hook(world, frame):
        if frame <= W.SETTLE_MIN_TICKS:
            return                       # nothing drives the hero during setup (real CARLA alike)
        hero = world.get_actors().filter("vehicle.*")[0]
        yaw_deg = hero.transform.rotation.yaw + yaw_rate_carla_dps * 0.1
        hero.transform = carla.Transform(hero.transform.location,
                                         carla.Rotation(pitch=0.0, yaw=yaw_deg, roll=0.0))
        psi = math.radians(yaw_deg)
        fwd = (math.cos(psi), math.sin(psi))
        right = (-math.sin(psi), math.cos(psi))          # CARLA: y is right
        a_right = speed * math.radians(yaw_rate_carla_dps)  # a right turn pulls to the right
        hero._velocity = carla.Vector3D(speed * fwd[0], speed * fwd[1], 0.0)
        hero._acceleration = carla.Vector3D(a_right * right[0], a_right * right[1], 0.0)
        hero._angular_velocity = carla.Vector3D(roll_dps, pitch_dps, yaw_rate_carla_dps)
    return hook


@pytest.mark.parametrize("yaw_rate_carla_dps", [-10.0, 10.0])
def test_kinematics_are_in_the_map_frame(tmp_path, route, profile, yaw_rate_carla_dps):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    client.world.motion_hook = _turning_hook(yaw_rate_carla_dps)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock, warmup=0.0, run_s=1.0)
    assert code == 0
    recs = [r["data"] for r in world_records(run_dir)]
    assert len(recs) >= 5
    left_turn = yaw_rate_carla_dps < 0
    for prev, cur in zip(recs, recs[1:]):
        dyaw = math.remainder(cur["egoPose"]["yaw"] - prev["egoPose"]["yaw"], 2 * math.pi)
        assert (dyaw > 0) == left_turn                      # map frame: counter-clockwise positive
    for d in recs[1:]:
        w = d["angular_velocity"]
        assert w["yaw_rad_s"] == pytest.approx(-math.radians(yaw_rate_carla_dps))
        assert (w["yaw_rad_s"] > 0) == left_turn            # the sign of d egoPose.yaw / dt
        assert w["roll_rad_s"] == pytest.approx(-math.radians(3.0))
        assert w["pitch_rad_s"] == pytest.approx(math.radians(4.0))
        # the reference producer's identity: lateral = speed x yaw rate, left positive
        lat = d["acceleration"]["lateral_mps2"]
        assert lat == pytest.approx(d["velocity"]["speed_mps"] * w["yaw_rad_s"], abs=1e-9)
        assert (lat > 0) == left_turn
    # the run's own check of the convention: CARLA's yaw rate against the logged poses
    check = read_json(run_dir / "simulator/summary.json")["yawRateCheck"]
    assert check["ticksCompared"] >= 5 and check["signAgreement"] == 1.0
    assert check["medianAbsDiffRadS"] < 1e-6


def test_control_accel_is_null_the_world_side_does_not_see_the_command(tmp_path, route, profile):
    clock = FakeClock()
    client = carla.Client("127.0.0.1", 2000, clock=clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock, warmup=0.0, run_s=0.3)
    assert code == 0
    assert all(r["data"]["control"]["accelMps2"] is None for r in world_records(run_dir))


def test_default_run_has_no_autopilot_warmup():
    args = W.build_parser().parse_args(["--route", "r.json", "--profile", "p.json", "--run-dir", "run"])
    assert args.warmup_s == 0.0
