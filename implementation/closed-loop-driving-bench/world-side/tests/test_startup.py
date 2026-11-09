"""R1, R2, R4, R5, R6: CLI, settings, rig, handover marker, warm-up handover."""

from __future__ import annotations

import math

import carla
import numpy as np
import pytest

import world_side as W
from conftest import (FakeClock, RIG_PATH, read_json, read_jsonl, make_tool, run_tool,
                      write_route, tool_args, profile_payload)


def a_client(clock, map_name: str = "Carla/Maps/Town10HD_Opt"):
    return carla.Client("127.0.0.1", 2000, clock=clock, map_name=map_name)


def world_records(run_dir):
    return [r for r in read_jsonl(run_dir / "simulator/world.jsonl") if r["event"] == "tick"]


def camera_spawns(client):
    return [s for s in client.world.spawned if s["type_id"] == "sensor.camera.rgb"]


# --------------------------------------------------------------------- R1: CLI


def test_cli_defaults():
    args = W.build_parser().parse_args(["--route", "r.json", "--profile", "p.json",
                                        "--run-dir", "run"])
    assert (args.host, args.port, args.tm_port) == ("127.0.0.1", 2000, 8000)
    assert args.map == "Town10HD_Opt"
    assert (args.warmup_s, args.run_s, args.warmup_speed_kmh, args.seed) == (0.0, 120.0, 30.0, 7)
    assert (args.width, args.front_width) == (1920, 1920)
    assert args.spawn_index is None
    assert args.fault == []
    assert args.dry_run is False


def test_dry_run_prints_plan_and_spawns_nothing(tmp_path, route, profile, capsys):
    def never(host, port):                      # a client would be a failure here
        raise AssertionError("--dry-run must not create a CARLA client")

    code = W.main(["--dry-run", "--route", str(route), "--profile", str(profile),
                   "--rig-path", str(RIG_PATH), "--run-dir", str(tmp_path / "run"),
                   "--warmup-s", "20", "--run-s", "120",
                   "--fault", "camera_stop:rear_left@3"],
                  client_factory=never, install_signals=False)
    out = capsys.readouterr().out
    assert code == 0
    assert "handover frame" in out and "first tick frame + 200" in out
    assert "de4sdv_handover_<F_h>" in out
    assert "camera_stop:rear_left@3" in out and "F_h + 30" in out
    assert "cam_front_left" in out and "1920x" in out
    assert not (tmp_path / "run").exists()


def test_dry_run_rejects_an_unknown_fault(tmp_path, route, profile, capsys):
    code = W.main(["--dry-run", "--route", str(route), "--profile", str(profile),
                   "--rig-path", str(RIG_PATH), "--run-dir", str(tmp_path / "run"),
                   "--fault", "steer_left:2"],
                  install_signals=False)
    assert code == 1
    assert "unknown fault" in capsys.readouterr().err


def test_map_loaded_only_when_different(tmp_path, route, profile):
    clock = FakeClock()
    other = a_client(clock, "Carla/Maps/Town01")
    code, run_dir = run_tool(route, profile, tmp_path / "a", other, clock, warmup=0.0, run_s=0.2)
    assert code == 0
    assert other.load_calls == ["Town10HD_Opt"]
    assert other.world.get_map().name == "Carla/Maps/Town10HD_Opt"

    clock = FakeClock()
    same = a_client(clock, "Carla/Maps/Town10HD_Opt")
    code, _ = run_tool(route, profile, tmp_path / "b", same, clock, warmup=0.0, run_s=0.2)
    assert code == 0
    assert same.load_calls == []


def test_route_map_mismatch_is_loud(tmp_path, profile):
    route = write_route(tmp_path / "route.json", map_name="Town03")
    clock = FakeClock()
    code, run_dir = run_tool(route, profile, tmp_path / "run", a_client(clock), clock)
    assert code == 1
    errors = [r for r in read_jsonl(run_dir / "simulator/worldSide.jsonl") if r["event"] == "error"]
    assert errors and "map mismatch" in errors[0]["data"]["reason"]
    # --dry-run refuses the same mismatch instead of printing a plan for it
    dry = W.main(["--dry-run", "--route", str(route), "--profile", str(profile),
                  "--rig-path", str(RIG_PATH), "--run-dir", str(tmp_path / "dry")],
                 install_signals=False)
    assert dry == 1


def test_spawn_point_is_the_nearest_within_two_metres(tmp_path, profile):
    route = write_route(tmp_path / "route.json", start=(10.0, 0.0, 0.0))
    clock = FakeClock()
    client = a_client(clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.0, run_s=0.2)
    assert code == 0
    config = [r for r in read_jsonl(run_dir / "simulator/worldSide.jsonl")
              if r["event"] == "config"][0]
    assert config["data"]["spawnIndex"] == 1


def test_spawn_point_far_away_is_loud(tmp_path, profile):
    route = write_route(tmp_path / "route.json", start=(500.0, 500.0, 0.0))
    clock = FakeClock()
    code, run_dir = run_tool(route, profile, tmp_path / "run", a_client(clock), clock)
    assert code == 1
    errors = [r for r in read_jsonl(run_dir / "simulator/worldSide.jsonl") if r["event"] == "error"]
    assert "no spawn point within 2 m" in errors[0]["data"]["reason"]


def test_spawn_index_out_of_range_is_loud(tmp_path, route, profile):
    clock = FakeClock()
    code, run_dir = run_tool(route, profile, tmp_path / "run", a_client(clock), clock,
                             extra=("--spawn-index", "99"))
    assert code == 1
    errors = [r for r in read_jsonl(run_dir / "simulator/worldSide.jsonl") if r["event"] == "error"]
    assert "outside 0.." in errors[0]["data"]["reason"]


# ---------------------------------------------------------------- R2: settings


def test_settings_applied_and_restored(tmp_path, route, profile):
    clock = FakeClock()
    client = a_client(clock)
    original = client.world.get_settings()
    assert (original.synchronous_mode, original.fixed_delta_seconds) == (False, None)

    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=1.0, run_s=0.5)
    assert code == 0

    applied = client.world.apply_settings_calls
    assert applied[0] == {"synchronous_mode": True, "fixed_delta_seconds": 0.1,
                          "no_rendering_mode": False}
    assert applied[-1] == {"synchronous_mode": False, "fixed_delta_seconds": None,
                           "no_rendering_mode": False}
    assert client.world.get_settings().synchronous_mode is False
    tm = client.traffic_managers[8000]
    assert tm.synchronous is False
    assert [c for c in tm.calls if c[0] == "set_synchronous_mode"] == [
        ("set_synchronous_mode", True), ("set_synchronous_mode", False)]
    assert list(client.world.get_actors()) == []

    # every sensor stopped before its destroy
    log = client.world.log
    for entry in [e for e in log if e[0] == "destroy"]:
        stops = [i for i, e in enumerate(log) if e[0] == "stop" and e[1] == entry[1]]
        destroys = [i for i, e in enumerate(log) if e[0] == "destroy" and e[1] == entry[1]]
        if stops:
            assert min(stops) < min(destroys)


def test_settings_restored_when_a_camera_fails_to_spawn(tmp_path, route, profile):
    clock = FakeClock()
    client = a_client(clock)
    client.world.spawn_failures = {"sensor.camera.rgb"}
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock)
    assert code == 1
    assert client.world.get_settings().synchronous_mode is False
    assert client.traffic_managers[8000].synchronous is False
    assert list(client.world.get_actors()) == []
    errors = [r for r in read_jsonl(run_dir / "simulator/worldSide.jsonl") if r["event"] == "error"]
    assert "cannot spawn camera cam_front" in errors[0]["data"]["reason"]
    assert read_json(run_dir / "simulator/summary.json")["stopReason"] == "error"


def test_teardown_is_idempotent(tmp_path, route, profile):
    clock = FakeClock()
    client = a_client(clock)
    tool = make_tool(route, profile, tmp_path / "run", client, clock, warmup=0.5, run_s=0.2)
    tool.start()
    tool.run()
    tool.teardown()
    destroys = len([e for e in client.world.log if e[0] == "destroy"])
    tool.teardown()
    assert len([e for e in client.world.log if e[0] == "destroy"]) == destroys
    assert list(client.world.get_actors()) == []


# --------------------------------------------------------------------- R4: rig


def test_six_cameras_named_from_the_profile(tmp_path, route, profile):
    clock = FakeClock()
    client = a_client(clock)
    tool = make_tool(route, profile, tmp_path / "run", client, clock)
    tool.start()
    try:
        rig = W.load_rig_module(str(RIG_PATH))
        _payload, cams = rig.load_profile(str(profile))
        spawns = camera_spawns(client)
        assert len(spawns) == 6
        hero_id = tool.hero.id
        for i, (spawn, cam) in enumerate(zip(spawns, cams)):
            width = 1024 if i == 0 else 640
            W_px, H_px, _f, hfov = rig.render_spec(cam, width)
            assert spawn["type_id"] == "sensor.camera.rgb"
            assert spawn["attach_to"] == hero_id
            assert spawn["attributes"]["role_name"] == f"cam_{cam['slot']}"
            assert spawn["attributes"]["image_size_x"] == str(W_px)
            assert spawn["attributes"]["image_size_y"] == str(H_px)
            assert abs(float(spawn["attributes"]["fov"]) - hfov) < 1e-6
            assert spawn["attributes"]["sensor_tick"] == "0.0"
        roles = [c["attributes"]["role_name"] for c in spawns]
        assert roles == ["cam_front", "cam_front_left", "cam_front_right",
                         "cam_rear_left", "cam_rear", "cam_rear_right"]
        others = [s["type_id"] for s in client.world.spawned
                  if s["type_id"].startswith("sensor.other")]
        assert others == ["sensor.other.collision", "sensor.other.lane_invasion"]
        # the world side never listens to the cameras: it receives no images
        for actor in client.world.get_actors().filter("sensor.camera.*"):
            assert actor.listeners == []
    finally:
        tool.teardown()


def test_rig_pose_is_actor_pose_in_vehicle(tmp_path, route, profile):
    """The spawn transform must be what the agent's set_rig round trip expects."""
    clock = FakeClock()
    client = a_client(clock)
    tool = make_tool(route, profile, tmp_path / "run", client, clock)
    tool.start()
    try:
        rig = W.load_rig_module(str(RIG_PATH))
        _payload, cams = rig.load_profile(str(profile))
        origin = tool.origin
        assert origin is not None and len(origin) == 3
        for spawn, cam in zip(camera_spawns(client), cams):
            T = np.asarray(cam["camera_to_reference"], dtype=np.float64).reshape(4, 4)
            expected_loc, expected_euler = rig.actor_pose_in_vehicle(T, origin)
            got = carla.Transform(carla.Location(*[float(v) for v in [
                spawn["transform"].location.x, spawn["transform"].location.y,
                spawn["transform"].location.z]]),
                carla.Rotation(spawn["transform"].rotation.pitch,
                               spawn["transform"].rotation.yaw,
                               spawn["transform"].rotation.roll))
            assert np.allclose([got.location.x, got.location.y, got.location.z],
                               np.asarray(expected_loc), atol=1e-9)
            assert np.allclose([got.rotation.pitch, got.rotation.yaw, got.rotation.roll],
                               np.asarray(expected_euler), atol=1e-9)
            # the agent's direction: vehicle-local matrix -> T_ref_opt
            back = rig.T_ref_opt_from_actor(np.asarray(got.get_matrix()), origin)
            assert np.linalg.norm(back[:3, 3] - T[:3, 3]) < 1e-3      # 1 mm
            assert rig.rotation_angle_deg(back[:3, :3] @ T[:3, :3].T) < 0.01
    finally:
        tool.teardown()


def test_rig_uses_the_real_agent_module():
    rig = W.load_rig_module(str(RIG_PATH))
    for name in ("load_profile", "render_spec", "actor_pose_in_vehicle",
                 "ref_origin_from_vehicle", "T_ref_opt_from_actor"):
        assert hasattr(rig, name)
    assert "de4sdv_planner" in str(getattr(rig, "__file__", ""))


# --------------------------------------------------------------------- R5: F_h


def test_handover_marker_names_the_frame(tmp_path, route, profile):
    clock = FakeClock()
    client = a_client(clock)
    tool = make_tool(route, profile, tmp_path / "run", client, clock, warmup=2.0, run_s=1.0)
    tool.start()
    try:
        tool.run()
        tool.write_summary()
        summary = read_json(tmp_path / "run/simulator/summary.json")
        assert summary["handoverFrame"] == summary["firstFrame"] + 20
        markers = [a for a in client.world.get_actors()
                   if str(a.attributes.get("role_name", "")).startswith("de4sdv_handover_")]
        role = f"de4sdv_handover_{summary['handoverFrame']}"
        assert [m.attributes["role_name"] for m in markers] == [role]
        assert int(role.rsplit("_", 1)[1]) == summary["handoverFrame"]
        assert markers[0].transform.location.z == -500.0
        assert markers[0].simulate_physics is False
        records = world_records(tmp_path / "run")
        assert records
        assert all(r["data"]["handoverFrame"] == summary["handoverFrame"] for r in records)
    finally:
        tool.teardown()


# ----------------------------------------------------------- R6: warm-up/handover


def test_autopilot_off_before_the_handover_tick(tmp_path, route, profile):
    clock = FakeClock()
    client = a_client(clock)
    tool = make_tool(route, profile, tmp_path / "run", client, clock, warmup=2.0, run_s=1.0)
    tool.start()
    try:
        hero = tool.hero
        setup = W.SETTLE_MIN_TICKS                   # the warm-up starts after the setup ticks
        assert hero.autopilot_calls == [(True, 8000, setup)]
        tool.run()
        assert hero.autopilot_calls == [(True, 8000, setup), (False, 8000, tool.handover_frame - 1)]
        records = world_records(tmp_path / "run")
        fh = tool.handover_frame
        before = [r["data"] for r in records if r["data"]["frame"] < fh]
        after = [r["data"] for r in records if r["data"]["frame"] >= fh]
        assert before and after
        assert all(r["controlSource"] == "autopilot" and r["autopilotEnabled"]
                   and r["trafficManagerEnabled"] for r in before)
        assert all(r["controlSource"] == "actuationAdapter" and not r["autopilotEnabled"]
                   and not r["trafficManagerEnabled"] for r in after)
    finally:
        tool.teardown()


def test_autopilot_state_follows_the_vehicle_when_the_api_offers_it(tmp_path, route,
                                                                    profile):
    clock = FakeClock()
    client = a_client(clock)
    tool = make_tool(route, profile, tmp_path / "run", client, clock)
    tool.start()
    try:
        assert tool._autopilot_enabled() is True           # the warm-up is running
        tool.hero.autopilot = False                        # the vehicle's own state
        assert tool._autopilot_enabled() is False
        tool.autopilot = True                              # bookkeeping says otherwise
        assert tool._autopilot_enabled() is False
    finally:
        tool.teardown()


def test_warmup_follows_the_route_in_carla_coordinates(tmp_path, profile):
    # spawn point 0 is at CARLA (0, -3); the route start in the map frame is (0, 3)
    route = write_route(tmp_path / "route.json", start=(0.0, 3.0, 0.0), count=4, step_m=5.0)
    clock = FakeClock()
    client = a_client(clock)
    client.world.map.spawn_transforms[0] = carla.Transform(
        carla.Location(0.0, -3.0, 0.0), carla.Rotation(0.0, 0.0, 0.0))
    client.world.map.spawn_transforms[1] = carla.Transform(
        carla.Location(20.0, -3.0, 0.0), carla.Rotation(0.0, 0.0, 0.0))
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=1.0, run_s=0.3)
    assert code == 0
    tm = client.traffic_managers[8000]
    path_call = [c for c in tm.calls if c[0] == "set_path"][0]
    assert path_call[2] == 4
    assert [(round(p.x, 6), round(p.y, 6)) for p in tm.path] == [
        (0.0, -3.0), (5.0, -3.0), (10.0, -3.0), (15.0, -3.0)]
    assert ("set_desired_speed", path_call[1], 30.0) in tm.calls
    assert ("auto_lane_change", path_call[1], False) in tm.calls
    assert ("ignore_lights_percentage", path_call[1], 100.0) in tm.calls
    assert ("set_random_device_seed", 7) in tm.calls


def test_warmup_path_lies_at_the_spawn_height(tmp_path, profile):
    """The Traffic Manager's path is at the height of the spawn point; the route's heading went into
    z instead, up to 3.14 m off the road."""
    route = write_route(tmp_path / "route.json", start=(0.0, 3.0, 1.0), count=4, step_m=5.0)
    clock = FakeClock()
    client = a_client(clock)
    client.world.map.spawn_transforms[0] = carla.Transform(
        carla.Location(0.0, -3.0, 0.6), carla.Rotation(0.0, 0.0, 0.0))
    code, _ = run_tool(route, profile, tmp_path / "run", client, clock, warmup=1.0, run_s=0.3)
    assert code == 0
    tm = client.traffic_managers[8000]
    assert [(round(p.x, 6), round(p.y, 6)) for p in tm.path] == [
        (0.0, -3.0), (5.0, -3.0), (10.0, -3.0), (15.0, -3.0)]
    assert [p.z for p in tm.path] == [0.6] * 4


def test_no_warmup_leaves_the_adapter_in_control_from_the_first_tick(tmp_path, route,
                                                                    profile):
    clock = FakeClock()
    client = a_client(clock)
    code, run_dir = run_tool(route, profile, tmp_path / "run", client, clock,
                             warmup=0.0, run_s=0.3)
    assert code == 0
    summary = read_json(run_dir / "simulator/summary.json")
    assert summary["handoverFrame"] == summary["firstFrame"]
    records = world_records(run_dir)
    assert all(r["data"]["controlSource"] == "actuationAdapter" for r in records)
    assert all(not r["data"]["autopilotEnabled"] for r in records)
    assert "set_path" not in client.traffic_managers[8000].names()
