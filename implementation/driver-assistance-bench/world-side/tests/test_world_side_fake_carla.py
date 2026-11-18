"""Self-tests of the fake CARLA 1.0 module (brief B0): the step, the camera's sensor tick, the Ackermann motion,
the collision event and the per-client control log. Expected values are computed here by hand from the step."""

from __future__ import annotations

import math

import carla


def _sync(world, step=0.05):
    s = world.get_settings()
    s.synchronous_mode, s.fixed_delta_seconds = True, step
    world.apply_settings(s)


def test_step_and_snapshot_time(server):
    world = carla.Client("h", 2000, _server=server).get_world()
    _sync(world)
    for _ in range(7):
        world.tick()
    snap = world.get_snapshot()
    assert snap.frame == 7
    assert math.isclose(snap.timestamp.elapsed_seconds, 7 * 0.05, abs_tol=1e-12)


def test_tick_refuses_asynchronous_mode(server):
    world = carla.Client("h", 2000, _server=server).get_world()
    try:
        world.tick()
    except RuntimeError:
        return
    raise AssertionError("tick in asynchronous mode must fail")


def test_camera_with_sensor_tick_point_one_renders_every_second_step(server):
    world = carla.Client("h", 2000, _server=server).get_world()
    _sync(world)
    lib = world.get_blueprint_library()
    hero = world.spawn_actor(lib.find("vehicle.lincoln.mkz"), carla.Transform())
    bp = lib.find("sensor.camera.rgb")
    bp.set_attribute("sensor_tick", "0.1")
    cam = world.spawn_actor(bp, carla.Transform(), attach_to=hero)
    images = []
    cam.listen(images.append)
    for _ in range(10):
        world.tick()
    assert [i.frame for i in images] == [1, 3, 5, 7, 9]
    assert [round(i.timestamp, 6) for i in images] == [0.05, 0.15, 0.25, 0.35, 0.45]
    assert all(b - a == 2 for a, b in zip([i.frame for i in images], [i.frame for i in images][1:]))


def test_ackermann_moves_the_vehicle_and_the_log_names_the_client(server):
    adapter = carla.Client("h", 2000, _server=server, name="adapter")
    world = adapter.get_world()
    _sync(world)
    hero = world.spawn_actor(world.get_blueprint_library().find("vehicle.lincoln.mkz"), carla.Transform())
    hero.apply_ackermann_control(carla.VehicleAckermannControl(speed=5.0, acceleration=2.0, jerk=10.0))
    for _ in range(20):            # 1 s at 2 m/s2: 2 m/s
        world.tick()
    v = hero.get_velocity()
    assert math.isclose(math.hypot(v.x, v.y), 2.0, abs_tol=1e-9)
    assert server.control_log[-1]["client"] == "adapter"
    assert server.control_log[-1]["call"] == "apply_ackermann_control"


def test_steer_positive_right_increases_carla_yaw(server):
    world = carla.Client("h", 2000, _server=server).get_world()
    _sync(world)
    hero = world.spawn_actor(world.get_blueprint_library().find("vehicle.lincoln.mkz"), carla.Transform())
    hero._state.speed = 5.0
    hero.apply_ackermann_control(carla.VehicleAckermannControl(steer=0.05, speed=5.0, acceleration=0.0))
    world.tick()
    # yaw rate = v tan(steer) / wheelbase, CARLA's yaw clockwise from above: a right turn raises it
    assert math.isclose(hero.get_angular_velocity().z, math.degrees(5.0 * math.tan(0.05) / 2.85), rel_tol=1e-9)
    assert hero.get_transform().rotation.yaw > 0.0


def test_collision_event_reaches_the_hero_sensor(server):
    world = carla.Client("h", 2000, _server=server).get_world()
    _sync(world)
    lib = world.get_blueprint_library()
    hero = world.spawn_actor(lib.find("vehicle.lincoln.mkz"), carla.Transform(carla.Location(0, 0, 0)))
    target = world.spawn_actor(lib.find("vehicle.tesla.model3"), carla.Transform(carla.Location(6.0, 0, 0)))
    events = []
    world.spawn_actor(lib.find("sensor.other.collision"), carla.Transform(), attach_to=hero).listen(events.append)
    world.tick()
    assert events == []
    hero._state.transform.location.x = 1.5          # 4.5 m apart < 2.45 + 2.40
    world.tick()
    assert events and events[0].other_actor.id == target.id


def test_waypoints_follow_the_straight_lane_and_the_bend(server):
    m = server.map
    wp = m.get_waypoint_xodr(m.road_id, -1, 100.0)
    assert math.isclose(wp.next(50.0)[0].transform.location.x, 150.0)
    m.bend_from = 200.0
    after = m.get_waypoint_xodr(m.road_id, -1, 200.0 + math.pi / 2 * m.bend_radius)
    assert math.isclose(after.transform.rotation.yaw, -90.0, abs_tol=1e-9)    # a left bend
