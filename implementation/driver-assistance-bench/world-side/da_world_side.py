#!/usr/bin/env python3
"""World side of the driver-assistance bench (INC-DRIVING-002) on CARLA 1.0.

The process on the simulator host that owns the simulated world: synchronous mode at a fixed step of 0.05 s,
paced on the wall clock, the hero with its front camera, the stationary target of SC-DRIVING-012, a world record
per tick, the entry-condition checks of each run and its setting record. It never drives the hero in a run of a
setting: the candidate drives it through the actuation adapter from the first tick to the last (see README.md).

Subcommands (all print one JSON line per event to stdout and write their files under --run-dir):

  survey        find straight driving lanes long enough for a setting (no actor is spawned)
  warmup        the warm-up pass: hero, front camera and target along the road of the setting, no control
  run           one run of a setting of SC-DRIVING-012
  calib-steer   the ASM-DRIVING-006 run: the hero right of its lane center, the candidate drives, no target
  calib-decel   the ASM-DRIVING-005 run: the world side commands the adapter's Ackermann rule itself
  camera-capture  the camera-calibration frame: upstream's checkerboards laid on the road, one front image

Every tick this process makes is also a row of ``simulator/tick_times.csv`` (``sim_time_s,unix_s``: the snapshot's
elapsed seconds after the tick and this host's real time when the tick returned), the chase view's time base for
``recording/compose_side_by_side.py --tick-times``. ``run`` and ``calib-steer`` take an optional handshake with the
session (``--go-file``, ``--release-file``): the world spawns, writes ``ready.json`` and holds its first tick until
the go file appears (the S-CORE side starts meanwhile); after the run's end it writes ``run_end.json`` and keeps
ticking until the release file appears, so the session can stop the S-CORE side before the world stops ticking
(launch-manager/README.md, "What the session must do").

Needs Python 3.10 with the ``carla`` module of the CARLA 1.0 package (14ac3b1a50) on the simulator host. It
imports ``carla`` only when it connects, so ``--dry-run`` runs anywhere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import calibration  # noqa: E402
import camera_calibration as camcal  # noqa: E402
import scenarios  # noqa: E402

# ---------------------------------------------------------------- model values
# PSR = driver_assistance_physical_software_realization.sysml at 1f6ad003.
STEP_S = 0.05                   # PSR, DriverAssistanceSimulationServer: fixed step of 0.05 s
FRONT_SENSOR_TICK_S = 0.1       # PSR, FrontCameraRig: one image per 0.1 s of simulation time
# PSR, FrontCameraRig and MAP-DRIVING-DA-CAMERA-IMAGE: upstream's rig, 1920 x 1280, fov 50, at the pose of
# Simulation/CARLA/ROS2/config/carla916.json:5-15, which config_carla.py:91-99 converts to CARLA's frame
# (y, pitch and yaw negated): x 1.544, y 0.0243, z 2.116 m, roll -0.10, pitch -0.11, yaw -0.23 deg.
FRONT_CAMERA = {"image_size_x": 1920, "image_size_y": 1280, "fov": 50.0,
                "x": 1.544, "y": 0.0243, "z": 2.116, "roll": -0.10, "pitch": -0.11, "yaw": -0.23}
# PSR: upstream's vehicle.lincoln.mkz_2020 is not in CARLA 1.0, "so the bench mounts the camera on another
# vehicle". The brief's substitute is vehicle.lincoln.mkz (DA-P8 g found it in the 1.0 catalogue).
VEHICLE_CANDIDATES = ("vehicle.lincoln.mkz_2020", "vehicle.lincoln.mkz")
# ------------------------------------------------------------- bench contracts
HERO_ROLE = "hero"              # the adapter's and the camera interface's hero_role
CAMERA_ROLE = "front"           # the camera interface's carla.camera_role (score-interface settings)
TARGET_ROLE = "sc012_target"
CALIBRATION_ROLE = "de4sdv_calibration"   # calib-decel and camera-capture: no candidate client attaches
TARGET_BLUEPRINT = "vehicle.tesla.model3"   # DA-P8's target (da8_target.py:23); a bench choice
DEFAULT_MAP = "Town04"          # brief R7: a long straight highway; in CARLA's AdditionalMaps pack
STALL_S = 0.2                   # a tick started more than 0.2 s after the one before is a stall
LATE_TOLERANCE_S = 0.001
CONTACT_HOLD_S = 3.0            # proposal: ticks kept after the first contact with the target
REST_HOLD_S = 3.0               # proposal: ticks kept once the hero is at rest after it moved
SETTLE_TICKS = 10               # setup ticks after spawning, before the run's first tick
STRAIGHT_STEP_M = 5.0
STRAIGHT_YAW_MAX_DEG = 0.5      # survey: heading change over the stretch
STRAIGHT_LATERAL_MAX_M = 0.3    # survey: distance of each waypoint from the start's line
MIN_SAME_DIRECTION_LANES = 2    # survey: a highway-type road, proxy: two driving lanes in one direction
# Lead answer B7.4 of 2026-11-18: upstream's L stays; the run records the hero's wheelbase against it and flags a
# difference of more than 2 %. vision_pilot.conf:21 at the pin reads "L = 2.860  # Front axle to CoG (m).
# Wheelbase L = Lf + Lr"; the lead reads it as the wheelbase.
VISION_PILOT_L_M = 2.860
WHEELBASE_FLAG_PCT = 2.0
WHEELBASE_PLAUSIBLE_M = (1.5, 5.0)
GO_POLL_S = 0.5                 # handshake: how often the world side looks for the go and release files


class BenchError(Exception):
    """A failure the bench reports and stops on."""


def num(value: Any) -> float | None:
    try:
        out = float(value)
    except (TypeError, ValueError):
        return None
    return out if math.isfinite(out) else None


def wrap_deg(angle: float) -> float:
    return (angle + 180.0) % 360.0 - 180.0


def last_path_element(name: str) -> str:
    return str(name).rstrip("/").split("/")[-1]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------- records


class JsonlWriter:
    """One JSON object per line, in the envelope of the INC-DRIVING-001 world side (ICD section 6 there)."""

    def __init__(self, path: Path, component: str = "worldSide"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._component = component
        self._seq = 0
        self._lock = threading.Lock()
        self._file = self.path.open("a", encoding="utf-8")

    def write(self, event: str, data: dict | None = None) -> None:
        with self._lock:
            self._seq += 1
            record = {"t_mono_ns": time.monotonic_ns(), "t_real_ns": time.time_ns(), "host": "simulator",
                      "component": self._component, "event": event, "seq": self._seq, "data": data or {}}
            self._file.write(json.dumps(record, separators=(",", ":"), allow_nan=False) + "\n")
            self._file.flush()

    def close(self) -> None:
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None


class Pacer:
    """Wall-clock pacing: tick k of a phase is due at t0 + k * period; a late tick runs at once and moves the
    schedule, never a burst to catch up. Each phase starts its own schedule (DA-P8 g_main2's lesson: a first
    frame of 13.4 s must not shorten the ticks of the next phase)."""

    def __init__(self, period_s: float, clock: Callable[[], float], sleep: Callable[[float], None]):
        self.period, self.clock, self.sleep = float(period_s), clock, sleep
        self.next_deadline = 0.0
        self.late_ticks = 0
        self.max_lateness_s = 0.0

    def start_phase(self) -> None:
        self.next_deadline = self.clock()

    def wait_turn(self) -> tuple[float, float]:
        now = self.clock()
        if now < self.next_deadline:
            self.sleep(self.next_deadline - now)
        start = self.clock()
        lateness = max(0.0, start - self.next_deadline)
        if lateness > LATE_TOLERANCE_S:
            self.late_ticks += 1
            self.max_lateness_s = max(self.max_lateness_s, lateness)
        return start, lateness

    def finish_turn(self, end: float) -> None:
        self.next_deadline += self.period
        if end > self.next_deadline:
            self.next_deadline = end


# ------------------------------------------------------------------ the bench


class WorldSide:
    """Connection, settings, spawns, ticks, records and teardown, shared by the subcommands."""

    def __init__(self, args: argparse.Namespace, *, client_factory: Callable[[str, int], Any] | None = None,
                 clock: Callable[[], float] = time.monotonic, sleep: Callable[[float], None] = time.sleep,
                 stop_requested: threading.Event | None = None, out: Callable[[str], None] = print,
                 wall: Callable[[], float] = time.time):
        self.args = args
        self.wall = wall
        self.client_factory = client_factory
        self.clock, self.sleep = clock, sleep
        self.stop_requested = stop_requested or threading.Event()
        self.out = out
        self.run_dir = Path(args.run_dir)
        self.sim_dir = self.run_dir / "simulator"
        self.sim_dir.mkdir(parents=True, exist_ok=True)
        self.side_log = JsonlWriter(self.sim_dir / "worldSide.jsonl")
        self.world_log: JsonlWriter | None = None
        self.pacer = Pacer(STEP_S, clock, sleep)
        self.client: Any = None
        self.world: Any = None
        self.map: Any = None
        self.carla: Any = None
        self.hero: Any = None
        self.camera: Any = None
        self.target: Any = None
        self.sensors: list[Any] = []
        self._spawned: list[Any] = []
        self.original_settings: dict | None = None
        self._events: list[dict] = []
        self._events_lock = threading.Lock()
        self.control_calls = 0          # controls this process applied to the hero (0 in a run)
        self.tick_starts: list[float] = []
        self.stalls: list[dict] = []
        self.ticks_written = 0
        self.first_elapsed: float | None = None
        self._torn_down = False
        self.tick_times_path = self.sim_dir / "tick_times.csv"
        self._tick_times = None
        self.world_ticks = 0

    # ------------------------------------------------------------- logging
    def event(self, name: str, **data) -> None:
        self.side_log.write(name, data)
        self.out(json.dumps({"event": name, **data}, separators=(",", ":"), default=str))

    # ---------------------------------------------------------- connection
    def connect(self) -> None:
        import carla  # noqa: WPS433 - only on the simulator host

        self.carla = carla
        factory = self.client_factory or (lambda host, port: carla.Client(host, port))
        self.client = factory(self.args.host, int(self.args.port))
        self.client.set_timeout(float(self.args.client_timeout))
        self.world = self.client.get_world()
        wanted = last_path_element(self.args.map)
        current = last_path_element(self.world.get_map().name)
        if current != wanted:
            try:
                self.world = self.client.load_world(self.args.map)
            except Exception as exc:  # noqa: BLE001
                raise BenchError(f"cannot load map {self.args.map!r} (Town04 is in CARLA's AdditionalMaps "
                                 f"pack): {exc}") from exc
        self.map = self.world.get_map()
        versions = {"client": self.client.get_client_version(), "server": self.client.get_server_version()}
        self.versions = versions
        self.event("connected", map=self.map.name, **versions)

    def apply_settings(self) -> None:
        original = self.world.get_settings()
        self.original_settings = {"synchronous_mode": bool(original.synchronous_mode),
                                  "fixed_delta_seconds": original.fixed_delta_seconds}
        settings = self.world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = STEP_S
        self.world.apply_settings(settings)
        read_back = self.world.get_settings()
        if not read_back.synchronous_mode or abs(float(read_back.fixed_delta_seconds) - STEP_S) > 1e-9:
            raise BenchError(f"settings not applied: synchronous {read_back.synchronous_mode}, "
                             f"step {read_back.fixed_delta_seconds}")
        self.event("settings", synchronous_mode=True, fixed_delta_seconds=STEP_S,
                   before=self.original_settings)

    def restore_settings(self) -> None:
        if self.world is None or self.original_settings is None:
            return
        try:
            settings = self.world.get_settings()
            settings.synchronous_mode = self.original_settings["synchronous_mode"]
            settings.fixed_delta_seconds = self.original_settings["fixed_delta_seconds"]
            self.world.apply_settings(settings)
        except Exception:  # noqa: BLE001 - teardown is best effort
            pass
        self.original_settings = None

    # ------------------------------------------------------------- the road
    def straight_length(self, waypoint, needed_m: float) -> float:
        """Length of the straight driving lane ahead of ``waypoint``, up to ``needed_m``."""
        start = waypoint.transform
        yaw0 = start.rotation.yaw
        fx, fy = math.cos(math.radians(yaw0)), math.sin(math.radians(yaw0))
        run, current = 0.0, waypoint
        while run < needed_m:
            nxt = current.next(STRAIGHT_STEP_M)
            if not nxt:
                break
            current = nxt[0]
            loc = current.transform.location
            dx, dy = loc.x - start.location.x, loc.y - start.location.y
            lateral = abs(-fy * dx + fx * dy)
            if current.is_junction or abs(wrap_deg(current.transform.rotation.yaw - yaw0)) > STRAIGHT_YAW_MAX_DEG \
                    or lateral > STRAIGHT_LATERAL_MAX_M:
                break
            run += STRAIGHT_STEP_M
        return run

    @staticmethod
    def same_direction_lanes(waypoint) -> int:
        count = 1
        for step in ("get_left_lane", "get_right_lane"):
            current = waypoint
            for _ in range(8):
                current = getattr(current, step)()
                if current is None or current.lane_id * waypoint.lane_id <= 0 \
                        or str(current.lane_type) != str(waypoint.lane_type):
                    break
                count += 1
        return count

    def survey(self, needed_m: float, sample_m: float = 10.0, limit: int = 20) -> list[dict]:
        found = []
        for wp in self.map.generate_waypoints(sample_m):
            if wp.is_junction:
                continue
            length = self.straight_length(wp, needed_m)
            if length < needed_m:
                continue
            lanes = self.same_direction_lanes(wp)
            if lanes < MIN_SAME_DIRECTION_LANES:
                continue
            loc = wp.transform.location
            found.append({"start": f"{wp.road_id}:{wp.lane_id}:{round(wp.s, 3)}", "road": wp.road_id,
                          "lane": wp.lane_id, "s": round(wp.s, 3), "straightM": length,
                          "laneWidthM": round(wp.lane_width, 3), "sameDirectionLanes": lanes,
                          "x": round(loc.x, 3), "y": round(loc.y, 3), "yawDeg": round(wp.transform.rotation.yaw, 3)})
        found.sort(key=lambda c: (c["road"], c["lane"], c["s"]))
        return found[:limit] if limit else found

    def start_waypoint(self, needed_m: float):
        if self.args.start:
            try:
                road, lane, s = self.args.start.split(":")
                wp = self.map.get_waypoint_xodr(int(road), int(lane), float(s))
            except ValueError as exc:
                raise BenchError(f"--start {self.args.start!r}: expected road:lane:s") from exc
            if wp is None:
                raise BenchError(f"--start {self.args.start}: no waypoint on the map")
            rule = "--start"
        else:
            candidates = self.survey(needed_m, limit=1)
            if not candidates:
                raise BenchError(f"no straight driving lane of {needed_m} m with {MIN_SAME_DIRECTION_LANES} "
                                 f"lanes in one direction on {self.map.name}")
            c = candidates[0]
            wp = self.map.get_waypoint_xodr(c["road"], c["lane"], c["s"])
            rule = "survey: the first by (road, lane, s)"
        length = self.straight_length(wp, needed_m)
        if length < needed_m:
            raise BenchError(f"the lane at {wp.road_id}:{wp.lane_id}:{wp.s:.3f} is straight for {length} m, "
                             f"the setting needs {needed_m} m")
        self.start_info = {"road": wp.road_id, "lane": wp.lane_id, "s": round(wp.s, 3), "rule": rule,
                           "straightM": length, "laneWidthM": round(wp.lane_width, 3),
                           "sameDirectionLanes": self.same_direction_lanes(wp), "neededM": needed_m}
        return wp

    # -------------------------------------------------------------- spawns
    def _transform_at(self, waypoint, lateral_m: float = 0.0, lift_m: float = 0.3):
        carla = self.carla
        t = waypoint.transform
        yaw = math.radians(t.rotation.yaw)
        right = (-math.sin(yaw), math.cos(yaw))
        loc = carla.Location(t.location.x + right[0] * lateral_m, t.location.y + right[1] * lateral_m,
                             t.location.z + lift_m)
        return carla.Transform(loc, carla.Rotation(pitch=0.0, yaw=t.rotation.yaw, roll=0.0))

    def vehicle_blueprint(self):
        library = self.world.get_blueprint_library()
        wanted = (self.args.vehicle,) if getattr(self.args, "vehicle", None) else VEHICLE_CANDIDATES
        for name in wanted:
            try:
                return library.find(name)
            except IndexError:
                continue
        raise BenchError(f"none of the vehicles {list(wanted)} is in the blueprint library")

    def spawn_hero(self, waypoint, lateral_m: float = 0.0, role: str = HERO_ROLE):
        blueprint = self.vehicle_blueprint()
        blueprint.set_attribute("role_name", role)
        transform = self._transform_at(waypoint, lateral_m)
        try:
            self.hero = self.world.spawn_actor(blueprint, transform)
        except Exception as exc:  # noqa: BLE001
            raise BenchError(f"cannot spawn the hero: {exc}") from exc
        self._spawned.append(self.hero)
        self.event("hero", actor_id=self.hero.id, type_id=self.hero.type_id, role=role, lateral_m=lateral_m,
                   spawn={"x": transform.location.x, "y": transform.location.y, "z": transform.location.z,
                          "yaw": transform.rotation.yaw})
        return self.hero

    def spawn_front_camera(self):
        carla = self.carla
        blueprint = self.world.get_blueprint_library().find("sensor.camera.rgb")
        for key in ("image_size_x", "image_size_y", "fov"):
            blueprint.set_attribute(key, str(FRONT_CAMERA[key]))
        blueprint.set_attribute("sensor_tick", str(FRONT_SENSOR_TICK_S))
        blueprint.set_attribute("role_name", CAMERA_ROLE)
        pose = carla.Transform(carla.Location(x=FRONT_CAMERA["x"], y=FRONT_CAMERA["y"], z=FRONT_CAMERA["z"]),
                               carla.Rotation(roll=FRONT_CAMERA["roll"], pitch=FRONT_CAMERA["pitch"],
                                              yaw=FRONT_CAMERA["yaw"]))
        self.camera = self.world.spawn_actor(blueprint, pose, attach_to=self.hero,
                                             attachment_type=carla.AttachmentType.Rigid)
        self._spawned.append(self.camera)
        attrs = self.camera.attributes
        self.camera_info = {"actor_id": self.camera.id, "role": CAMERA_ROLE,
                            **{k: attrs.get(k) for k in ("image_size_x", "image_size_y", "fov", "sensor_tick")},
                            "pose": {k: FRONT_CAMERA[k] for k in ("x", "y", "z", "roll", "pitch", "yaw")}}
        self.event("front_camera", **self.camera_info)
        return self.camera

    def spawn_hero_sensors(self) -> None:
        library = self.world.get_blueprint_library()
        for name, callback in (("sensor.other.collision", self._on_collision),
                               ("sensor.other.lane_invasion", self._on_lane_invasion)):
            sensor = self.world.spawn_actor(library.find(name), self.carla.Transform(), attach_to=self.hero)
            sensor.listen(callback)
            self.sensors.append(sensor)
            self._spawned.append(sensor)

    def spawn_target(self, start_wp, ahead_m: float):
        ahead = start_wp.next(ahead_m)
        if not ahead:
            raise BenchError(f"no waypoint {ahead_m} m ahead of the start")
        wp = ahead[0]
        blueprint = self.world.get_blueprint_library().find(TARGET_BLUEPRINT)
        blueprint.set_attribute("role_name", TARGET_ROLE)
        transform = self._transform_at(wp)
        try:
            self.target = self.world.spawn_actor(blueprint, transform)
        except Exception as exc:  # noqa: BLE001
            raise BenchError(f"cannot spawn the target: {exc}") from exc
        self._spawned.append(self.target)
        # The target, not the hero: held where it stands (DA-P8's da8_target.py:73 holds it the same way).
        self.target.apply_control(self.carla.VehicleControl(throttle=0.0, brake=1.0, hand_brake=True))
        self.target_info = {"actor_id": self.target.id, "type_id": self.target.type_id, "role": TARGET_ROLE,
                            "aheadM": ahead_m, "road": wp.road_id, "lane": wp.lane_id, "s": round(wp.s, 3),
                            "speedKmh": 0.0, "hold": "hand brake"}
        self.event("target", **self.target_info)
        return self.target

    # ------------------------------------------------------------- sensors
    def _on_collision(self, event) -> None:
        other = getattr(event, "other_actor", None)
        with self._events_lock:
            self._events.append({"type": "collision", "frame": int(getattr(event, "frame", -1)),
                                 "other_actor_id": getattr(other, "id", None),
                                 "other_actor": getattr(other, "type_id", None)})

    def _on_lane_invasion(self, event) -> None:
        markings = getattr(event, "crossed_lane_markings", None) or []
        with self._events_lock:
            self._events.append({"type": "lane_invasion", "frame": int(getattr(event, "frame", -1)),
                                 "markings": [str(getattr(m, "type", m)) for m in markings]})

    def _take_events(self, frame: int) -> list[dict]:
        with self._events_lock:
            mine = [e for e in self._events if e["frame"] <= frame]
            self._events = [e for e in self._events if e["frame"] > frame]
        return mine

    # --------------------------------------------------------------- ticks
    def tick(self) -> int:
        """One world tick, and its row in tick_times.csv: the snapshot's elapsed seconds after the tick and this
        host's real time when the tick returned. Every tick of this process goes through here, the unpaced setup
        and teardown ticks included, so that every chase frame finds its tick."""
        frame = int(self.world.tick())
        unix_s = self.wall()
        sim_s = float(self.world.get_snapshot().timestamp.elapsed_seconds)
        if self._tick_times is None:
            self._tick_times = self.tick_times_path.open("a", encoding="utf-8")
            if self._tick_times.tell() == 0:
                self._tick_times.write("sim_time_s,unix_s\n")
        self._tick_times.write(f"{sim_s:.6f},{unix_s:.6f}\n")
        self._tick_times.flush()
        self.world_ticks += 1
        return frame

    def settle(self, ticks: int = SETTLE_TICKS) -> None:
        """Unpaced setup ticks: CARLA realizes a new actor only at the next tick, and the hero drops onto its
        suspension. Not part of any run; no world record."""
        for _ in range(ticks):
            self.tick()
        self.event("settled", ticks=ticks, frame=self.world.get_snapshot().frame)

    def paced_tick(self) -> tuple[int, float, float]:
        start, lateness = self.pacer.wait_turn()
        if self.tick_starts and start - self.tick_starts[-1] > STALL_S:
            self.stalls.append({"afterFrame": self._last_frame, "gapS": round(start - self.tick_starts[-1], 4)})
        self.tick_starts.append(start)
        frame = self.tick()
        self._last_frame = frame
        end = self.clock()
        self.pacer.finish_turn(end)
        return frame, end - start, lateness

    _last_frame = None

    @staticmethod
    def _bb(actor) -> tuple[float, float]:
        bb = actor.bounding_box
        return float(bb.location.x), float(bb.extent.x)

    def tick_record(self, frame: int, duration: float, lateness: float, phase: str) -> dict:
        snapshot = self.world.get_snapshot()
        elapsed = float(snapshot.timestamp.elapsed_seconds)
        if self.first_elapsed is None:
            self.first_elapsed = elapsed
        ht = self.hero.get_transform()
        hv = self.hero.get_velocity()
        ha = self.hero.get_acceleration()
        yaw = math.radians(ht.rotation.yaw)
        fwd = (math.cos(yaw), math.sin(yaw))
        speed = math.hypot(hv.x, hv.y)
        lane = self.map.get_waypoint(ht.location, project_to_road=True)
        lane_info = None
        if lane is not None:
            lyaw = math.radians(lane.transform.rotation.yaw)
            dx, dy = ht.location.x - lane.transform.location.x, ht.location.y - lane.transform.location.y
            lane_info = {"road": lane.road_id, "lane": lane.lane_id,
                         "offsetM": num(-math.sin(lyaw) * dx + math.cos(lyaw) * dy)}   # positive: right
        events = self._take_events(frame)
        collisions = [e for e in events if e["type"] == "collision"]
        control = self.hero.get_control()
        record = {
            "frame": frame, "phase": phase, "simTimeS": num(elapsed),
            "scenarioTimeS": num(round(elapsed - self.first_elapsed, 6)),
            "ego": {"x": num(ht.location.x), "y": num(ht.location.y), "z": num(ht.location.z),
                    "yawDegCarla": num(ht.rotation.yaw), "speedMps": num(speed),
                    "longAccelMps2": num(ha.x * fwd[0] + ha.y * fwd[1]),
                    "yawRateDegSCarla": num(self.hero.get_angular_velocity().z), "lane": lane_info},
            "control": {"throttle": num(control.throttle), "steer": num(control.steer),
                        "brake": num(control.brake), "handBrake": bool(control.hand_brake)},
            "worldSideControlCalls": self.control_calls,
            "collisions": collisions,
            "laneInvasions": [e for e in events if e["type"] == "lane_invasion"],
            "tickDurationS": num(round(duration, 6)), "latenessS": num(round(lateness, 6)),
            "target": None, "relative": None, "targetContact": False,
        }
        if self.target is not None:
            tt = self.target.get_transform()
            tv = self.target.get_velocity()
            tyaw = math.radians(tt.rotation.yaw)
            rel_x, rel_y = tt.location.x - ht.location.x, tt.location.y - ht.location.y
            along = rel_x * fwd[0] + rel_y * fwd[1]
            hbx, hex_ = self._bb(self.hero)
            tbx, tex = self._bb(self.target)
            gap = along - (hbx + hex_) - (tex - tbx)
            closing = (hv.x - tv.x) * fwd[0] + (hv.y - tv.y) * fwd[1]
            offset = (-math.sin(tyaw)) * (-rel_x) + math.cos(tyaw) * (-rel_y)
            record["target"] = {"x": num(tt.location.x), "y": num(tt.location.y),
                                "yawDegCarla": num(tt.rotation.yaw), "speedMps": num(math.hypot(tv.x, tv.y))}
            record["relative"] = {
                "gapM": num(gap), "closingMps": num(closing), "centerLineOffsetM": num(offset),
                "headingDiffDeg": num(wrap_deg(ht.rotation.yaw - tt.rotation.yaw)),
                "ttcS": num(scenarios.time_to_collision(gap, closing)),
                "neededDecelMps2": num(scenarios.needed_deceleration(gap, closing)),
            }
            record["targetContact"] = any(c["other_actor_id"] == self.target.id for c in collisions)
        return record

    def open_world_log(self, name: str = "world.jsonl") -> None:
        self.world_log = JsonlWriter(self.sim_dir / name)

    def write_tick(self, record: dict) -> None:
        self.world_log.write("tick", record)
        self.ticks_written += 1

    # ------------------------------------------------------------ teardown
    def teardown(self) -> None:
        if self._torn_down:
            return
        self._torn_down = True
        for sensor in list(self.sensors) + ([self.camera] if self.camera is not None else []):
            try:
                sensor.stop()
            except Exception:  # noqa: BLE001
                pass
        for actor in reversed(self._spawned):
            try:
                actor.destroy()
            except Exception:  # noqa: BLE001
                pass
        # Destroying in synchronous mode takes effect at the next tick: one tick before leaving it.
        try:
            if self.original_settings is not None:
                self.tick()
        except Exception:  # noqa: BLE001
            pass
        self.restore_settings()
        if self.world_log is not None:
            self.world_log.close()
        if self._tick_times is not None:
            self._tick_times.close()
            self._tick_times = None
        self.side_log.close()

    def pacing_summary(self) -> dict:
        return {"stepS": STEP_S, "lateTicks": self.pacer.late_ticks,
                "maxLatenessS": round(self.pacer.max_lateness_s, 6), "stalls": self.stalls,
                "stallRule": f"a tick started more than {STALL_S} s after the one before"}


# ------------------------------------------------------------------ subcommands


def needed_road_m(st: scenarios.Setting, ahead_m: float) -> float:
    return ahead_m + 40.0


def cmd_survey(ws: WorldSide) -> dict:
    ws.connect()
    st = scenarios.setting(ws.args.setting)
    ahead = ws.args.target_ahead_m or st.target_ahead_m
    found = ws.survey(needed_road_m(st, ahead), limit=ws.args.limit)
    result = {"map": ws.map.name, "setting": st.setting_id, "neededM": needed_road_m(st, ahead),
              "rule": {"stepM": STRAIGHT_STEP_M, "yawMaxDeg": STRAIGHT_YAW_MAX_DEG,
                       "lateralMaxM": STRAIGHT_LATERAL_MAX_M, "minSameDirectionLanes": MIN_SAME_DIRECTION_LANES},
              "candidates": found}
    (ws.sim_dir / "survey.json").write_text(json.dumps(result, indent=1))
    ws.event("survey", count=len(found), first=found[0] if found else None)
    return result


def _scenario_setup(ws: WorldSide, *, lateral_m: float, with_target: bool, role: str = HERO_ROLE):
    st = scenarios.setting(ws.args.setting)
    ahead = ws.args.target_ahead_m or st.target_ahead_m
    ws.connect()
    ws.apply_settings()
    start = ws.start_waypoint(needed_road_m(st, ahead))
    ws.spawn_hero(start, lateral_m, role)
    ws.spawn_front_camera()
    ws.spawn_hero_sensors()
    if with_target:
        ws.spawn_target(start, ahead)
    ws.settle()
    return st, start, ahead


def _vec(v) -> dict | None:
    if v is None:
        return None
    return {k: num(getattr(v, k, None)) for k in ("x", "y", "z")}


def hero_wheelbase(hero) -> dict:
    """The hero's wheelbase against vision_pilot.conf's L (lead answer B7.4): flagged when they differ by more
    than 2 %. Read from the physics control; CARLA 1.0's WheelPhysicsControl carries no wheel position
    (PythonAPI/carla/src/Control.cpp:439-462 at 14ac3b1a50: axle_type, offset, radius, ...), so the wheel
    positions then come from the vehicle's wheel bones (Actor.cpp:123,126 there: get_bone_names,
    get_bone_world_transforms). The method used is part of the record; no wheelbase is never a pass."""
    rec: dict = {"visionPilotLM": VISION_PILOT_L_M, "flagAbovePct": WHEELBASE_FLAG_PCT,
                 "visionPilotLComment": "vision_pilot.conf:21: Front axle to CoG (m). Wheelbase L = Lf + Lr",
                 "wheelbaseM": None, "method": None, "deviationPct": None, "flagged": None}
    t = hero.get_transform()
    yaw = math.radians(t.rotation.yaw)
    fwd = (math.cos(yaw), math.sin(yaw))

    def along(x: float, y: float) -> float:
        return (x - t.location.x) * fwd[0] + (y - t.location.y) * fwd[1]

    longitudinal: list[float] = []
    try:
        pc = hero.get_physics_control()
        wheels = list(getattr(pc, "wheels", []) or [])
        rec["physicsControl"] = {
            "mass": num(getattr(pc, "mass", None)), "centerOfMass": _vec(getattr(pc, "center_of_mass", None)),
            "wheels": [{"axleType": str(getattr(w, "axle_type", None)), "offset": _vec(getattr(w, "offset", None)),
                        "radius": num(getattr(w, "wheel_radius", None)),
                        "maxSteerAngleDeg": num(getattr(w, "max_steer_angle", None)),
                        "position": _vec(getattr(w, "position", None))} for w in wheels]}
        if wheels and all(getattr(w, "position", None) is not None for w in wheels):
            # CARLA 0.9's WheelPhysicsControl.position: world position in centimeters
            longitudinal = [along(w.position.x / 100.0, w.position.y / 100.0) for w in wheels]
            rec["method"] = "physics control: wheel positions (cm, world)"
    except Exception as exc:  # noqa: BLE001
        rec["physicsControlError"] = str(exc)
    if not longitudinal:
        try:
            names = list(hero.get_bone_names())
            transforms = list(hero.get_bone_world_transforms())
            bones = [(n, tr) for n, tr in zip(names, transforms) if "wheel" in str(n).lower()]
            rec["wheelBones"] = [n for n, _ in bones]
            longitudinal = [along(tr.location.x, tr.location.y) for _, tr in bones]
            rec["method"] = "wheel bones' world transforms (the physics control has no wheel position)"
        except Exception as exc:  # noqa: BLE001
            rec["bonesError"] = str(exc)
    if len(longitudinal) >= 2:
        mean = sum(longitudinal) / len(longitudinal)
        front = [x for x in longitudinal if x > mean]
        rear = [x for x in longitudinal if x < mean]
        if front and rear:
            wb = sum(front) / len(front) - sum(rear) / len(rear)
            if WHEELBASE_PLAUSIBLE_M[0] <= wb <= WHEELBASE_PLAUSIBLE_M[1]:
                rec["wheelbaseM"] = round(wb, 4)
                rec["deviationPct"] = round(abs(wb - VISION_PILOT_L_M) / VISION_PILOT_L_M * 100.0, 3)
                rec["flagged"] = rec["deviationPct"] > WHEELBASE_FLAG_PCT
            else:
                rec["implausible"] = f"{wb:.4f} m is outside {list(WHEELBASE_PLAUSIBLE_M)} m (units?)"
    if rec["wheelbaseM"] is None:
        rec["unmeasured"] = "no wheel positions to compute the wheelbase from"
    return rec


def setting_record(ws: WorldSide, st: scenarios.Setting, kind: str, ahead_m: float | None, lateral_m: float,
                   run_cap_s: float) -> dict:
    hero_bb = ws.hero.bounding_box
    return {
        "kind": kind, "setting": st.as_record(), "map": ws.map.name, "start": ws.start_info,
        "simulator": {"versions": ws.versions, "stepS": STEP_S, "synchronous": True},
        "hero": {"actor_id": ws.hero.id, "type_id": ws.hero.type_id, "role": HERO_ROLE, "lateralOffsetM": lateral_m,
                 "boundingBox": {"x": num(hero_bb.location.x), "z": num(hero_bb.location.z),
                                 "extent": [num(hero_bb.extent.x), num(hero_bb.extent.y), num(hero_bb.extent.z)]},
                 "frontBumperXM": num(hero_bb.location.x + hero_bb.extent.x),
                 "wheelbase": hero_wheelbase(ws.hero)},
        "frontCamera": ws.camera_info,
        # Lead answer B7.1 of 2026-11-18: the bench's reading of "travels straight", stated in every record
        "benchReadings": {"travelsStraight": f"the heading within {scenarios.STRAIGHT_HEADING_MAX_DEG} deg of the "
                                             "target's heading",
                          "straightHeadingMaxDeg": scenarios.STRAIGHT_HEADING_MAX_DEG,
                          "atRestMps": scenarios.AT_REST_MPS},
        "target": getattr(ws, "target_info", None) if ahead_m is not None else None,
        "runCapS": run_cap_s,
        "controlOfTheHero": "the actuation adapter only; this process applies no control to the hero, no "
                            "autopilot and no Traffic Manager (PSR DriverAssistanceSimulationServer)",
        "candidateSpeedLimitMps": st.speed_limit_mps,
    }


def _run_loop(ws: WorldSide, cap_s: float, phase: str, end_on_target: bool) -> tuple[list[dict], str]:
    ticks: list[dict] = []
    ws.open_world_log()
    ws.pacer.start_phase()
    reason, contact_at, rest_at, moved = "run cap", None, None, False
    while True:
        if ws.stop_requested.is_set():
            reason = "stop requested"
            break
        frame, duration, lateness = ws.paced_tick()
        record = ws.tick_record(frame, duration, lateness, phase)
        ws.write_tick(record)
        ticks.append(record)
        t = record["scenarioTimeS"] or 0.0
        speed = record["ego"]["speedMps"] or 0.0
        if end_on_target and record["targetContact"] and contact_at is None:
            contact_at = t
            ws.event("target_contact", frame=frame, scenarioTimeS=t, speedMps=speed)
        moved = moved or speed > 1.0
        if moved and speed <= scenarios.AT_REST_MPS:
            rest_at = t if rest_at is None else rest_at
        else:
            rest_at = None
        if contact_at is not None and t - contact_at >= CONTACT_HOLD_S:
            reason = "contact with the target"
            break
        if rest_at is not None and t - rest_at >= REST_HOLD_S:
            reason = "at rest"
            break
        if t >= cap_s - 1e-9:
            break
    return ticks, reason


def cmd_run(ws: WorldSide, kind: str = "run") -> dict:
    lateral = float(ws.args.lateral_offset_m or 0.0)
    with_target = kind == "run"
    st, _start, ahead = _scenario_setup(ws, lateral_m=lateral, with_target=with_target)
    cap = float(ws.args.run_s or st.run_cap_s)
    record = setting_record(ws, st, kind, ahead if with_target else None, lateral, cap)
    (ws.sim_dir / "setting_record.json").write_text(json.dumps(record, indent=1))
    ws.event("setting_record", path=str(ws.sim_dir / "setting_record.json"), setting=st.setting_id, kind=kind)
    ready = ws.sim_dir / "ready.json"
    ready.write_text(json.dumps({"hero_role": HERO_ROLE, "camera_role": CAMERA_ROLE,
                                 "hero_actor_id": ws.hero.id, "camera_actor_id": ws.camera.id}))
    ws.event("ready", path=str(ready))
    if ws.args.go_file:
        waited = _wait_for_file(ws, Path(ws.args.go_file), float(ws.args.go_wait_s))
        if waited is None:
            raise BenchError(f"no go file {ws.args.go_file} within {ws.args.go_wait_s} s: the run did not start")
        ws.event("go", path=ws.args.go_file, waitedS=round(waited, 3))
    ticks, reason = _run_loop(ws, cap, kind, end_on_target=with_target)
    summary = {"kind": kind, "setting": st.setting_id, "endReason": reason, "ticks": len(ticks),
               "worldSideControlCallsOnTheHero": ws.control_calls, "pacing": ws.pacing_summary()}
    if with_target:
        summary["entry"] = scenarios.evaluate_entry(ticks, st)
        (ws.sim_dir / "entry_checks.json").write_text(json.dumps(summary["entry"], indent=1))
        # Lead answer B7.2: the literal check stays; the record flags a hero above the tolerance after the
        # functional part started, and says where that part starts. The evaluators decide.
        record["runFlags"] = scenarios.tolerance_after_start(ticks, st, summary["entry"])
        (ws.sim_dir / "setting_record.json").write_text(json.dumps(record, indent=1))
    else:
        summary["steering"] = calibration.analyse_steering(ticks, lateral)
        (ws.sim_dir / "calibration_steering.json").write_text(json.dumps(
            calibration.steering_record(summary["steering"], record), indent=1))
    (ws.sim_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    (ws.sim_dir / "run_end.json").write_text(json.dumps({"endReason": reason, "ticks": len(ticks)}))
    ws.event("end", reason=reason, ticks=len(ticks), stalls=len(ws.stalls))
    if ws.args.release_file:
        summary["hold"] = _hold_until_release(ws, Path(ws.args.release_file), float(ws.args.release_wait_s))
        (ws.sim_dir / "summary.json").write_text(json.dumps(summary, indent=1))
    return summary


def _wait_for_file(ws: WorldSide, path: Path, wait_s: float) -> float | None:
    """Waits without ticking (synchronous mode: the world stands still) until ``path`` exists; the waited
    seconds, or None at the time-out or on a stop request."""
    t0 = ws.clock()
    while not path.exists():
        if ws.stop_requested.is_set() or ws.clock() - t0 >= wait_s:
            return None
        ws.sleep(GO_POLL_S)
    return ws.clock() - t0


def _hold_until_release(ws: WorldSide, path: Path, wait_s: float) -> dict:
    """After the run: paced ticks go on (phase ``hold``, in hold.jsonl, not in the run's world.jsonl) until the
    session's release file appears, so that the S-CORE side is stopped while the world still ticks."""
    log = JsonlWriter(ws.sim_dir / "hold.jsonl")
    ws.pacer.start_phase()
    t0, n, how = ws.clock(), 0, "release file"
    try:
        while not path.exists():
            if ws.stop_requested.is_set():
                how = "stop requested"
                break
            if ws.clock() - t0 >= wait_s:
                how = f"no release file within {wait_s} s"
                break
            frame, duration, lateness = ws.paced_tick()
            log.write("tick", ws.tick_record(frame, duration, lateness, "hold"))
            n += 1
    finally:
        log.close()
    ws.event("released", how=how, holdTicks=n)
    return {"holdTicks": n, "endedBy": how, "file": str(path)}


def cmd_warmup(ws: WorldSide) -> dict:
    """Moves the hero along the road of the setting by setting its pose each tick, with its front camera and
    the target rendering, so that the first renders of the road happen before any run. Not a run: the hero
    of the warm-up is destroyed at the end. Its pose is set, no control is applied."""
    st, start, ahead = _scenario_setup(ws, lateral_m=0.0, with_target=True, role=ws.args.role)
    ws.hero.set_simulate_physics(False)
    step_m = float(ws.args.warmup_step_m)
    ws.open_world_log("warmup.jsonl")
    ws.pacer.start_phase()
    distance, wp, ticks = 0.0, start, 0
    while distance < ahead - 10.0 and not ws.stop_requested.is_set():
        nxt = wp.next(step_m)
        if not nxt:
            break
        wp = nxt[0]
        distance += step_m
        ws.hero.set_transform(ws._transform_at(wp, 0.0, 0.3))
        frame, duration, lateness = ws.paced_tick()
        ws.write_tick({"frame": frame, "phase": "warmup", "distanceM": distance,
                       "tickDurationS": round(duration, 6), "latenessS": round(lateness, 6)})
        ticks += 1
    summary = {"kind": "warmup", "setting": st.setting_id, "ticks": ticks, "distanceM": distance,
               "start": ws.start_info, "pacing": ws.pacing_summary()}
    (ws.sim_dir / "warmup_summary.json").write_text(json.dumps(summary, indent=1))
    ws.event("end", reason="warm-up done", ticks=ticks)
    return summary


def cmd_calib_decel(ws: WorldSide) -> dict:
    """ASM-DRIVING-005: the world side itself commands CARLA's Ackermann control by the adapter's rule
    (MAP-DRIVING-DA-COMMAND: speed = max(0, v + 2 * acceleration), acceleration unchanged, jerk 10.0,
    steer 0, steer_speed 0), one command per 0.1 s of simulation time as the camera's cadence gives, on the
    vehicle and the road of the setting. Not a run of a setting; the adapter binary is not in this loop."""
    st = scenarios.setting(ws.args.setting)
    ws.connect()
    ws.apply_settings()
    speeds = [float(v) for v in ws.args.speeds.split(",")]
    decels = [float(d) for d in ws.args.decels.split(",")]
    start = ws.start_waypoint(ws.args.road_m)
    ws.open_world_log("calibration_decel.jsonl")
    passes = []
    for v_kmh in speeds:
        for decel in decels:
            ws.spawn_hero(start, 0.0, ws.args.role)
            ws.settle()
            samples = _decel_pass(ws, v_kmh / 3.6, decel)
            passes.append({"approachKmh": v_kmh, "commandedDecelMps2": decel, "samples": samples})
            ws.hero.destroy()
            ws._spawned.remove(ws.hero)
            ws.tick()
    record = calibration.decel_record([calibration.analyse_decel(p) for p in passes], {
        "setting": st.setting_id, "map": ws.map.name, "start": ws.start_info,
        "vehicle": ws.vehicle_blueprint().id, "simulator": ws.versions, "stepS": STEP_S,
        "rule": "speed = max(0, v + 2 * acceleration), acceleration unchanged, jerk 10.0, steer 0, "
                "steer_speed 0 (MAP-DRIVING-DA-COMMAND); one command per 0.1 s",
        "accelerateMps2": calibration.ACCELERATE_MPS2, "holdS": calibration.HOLD_S})
    (ws.sim_dir / "calibration_decel.json").write_text(json.dumps(record, indent=1))
    ws.event("end", reason="calibration done", passes=len(passes))
    return record


def _decel_pass(ws: WorldSide, v_target: float, decel: float) -> list[dict]:
    carla = ws.carla
    samples: list[dict] = []
    ws.pacer.start_phase()
    phase, hold_from, commanded, k = "accelerate", None, calibration.ACCELERATE_MPS2, 0
    while not ws.stop_requested.is_set():
        snapshot_speed = math.hypot(ws.hero.get_velocity().x, ws.hero.get_velocity().y)
        if phase == "accelerate" and snapshot_speed >= v_target:
            phase, commanded, hold_from = "hold", 0.0, k
        if phase == "hold" and (k - hold_from) * STEP_S >= calibration.HOLD_S:
            phase, commanded = "brake", -decel
        if k % 2 == 0:      # one command per 0.1 s
            control = carla.VehicleAckermannControl(steer=0.0, steer_speed=0.0,
                                                    speed=max(0.0, snapshot_speed + 2.0 * commanded),
                                                    acceleration=commanded, jerk=10.0)
            ws.hero.apply_ackermann_control(control)
            ws.control_calls += 1
        frame, duration, lateness = ws.paced_tick()
        rec = ws.tick_record(frame, duration, lateness, "calib-decel")
        rec["calibration"] = {"phase": phase, "commandedAccelMps2": commanded, "targetMps": v_target}
        ws.write_tick(rec)
        samples.append({"t": rec["simTimeS"], "speed": rec["ego"]["speedMps"],
                        "accel": rec["ego"]["longAccelMps2"], "commanded": commanded, "phase": phase})
        k += 1
        if phase == "brake" and (rec["ego"]["speedMps"] or 0.0) <= 0.1:
            break
        if k * STEP_S > calibration.PASS_CAP_S:
            break
    return samples


def _pose(t) -> dict:
    return {"x": float(t.location.x), "y": float(t.location.y), "z": float(t.location.z),
            "pitch": float(t.rotation.pitch), "yaw": float(t.rotation.yaw), "roll": float(t.rotation.roll)}


def cmd_camera_capture(ws: WorldSide) -> dict:
    """Lays four of upstream's checkerboards flat on the road ahead of the hero, captures one front image and
    writes the boards' ground-truth centers in upstream's frame (X forward, Y left, origin at the front
    bumper's center on the ground: Calibration/README.md:23)."""
    st = scenarios.setting(ws.args.setting)
    ws.connect()
    ws.apply_settings()
    start = ws.start_waypoint(60.0)
    ws.spawn_hero(start, 0.0, ws.args.role)
    ws.spawn_front_camera()
    ws.settle()
    png = Path(ws.args.checkerboard)
    width, height, rgba = camcal.read_png_rgba(png.read_bytes())
    texture = ws.carla.TextureColor(width, height)
    for y in range(height):
        for x in range(width):
            r, g, b, a = rgba[y][x]
            texture.set(x, height - y - 1, ws.carla.Color(r, g, b, a))   # as PythonAPI/util/apply_texture.py
    layout = camcal.board_layout(ws.args.near_m, ws.args.far_m, ws.args.half_spacing_m)
    hero_t = ws.hero.get_transform()
    bb = ws.hero.bounding_box
    bumper_x = float(bb.location.x + bb.extent.x)
    ground_z = float(start.transform.location.z)
    boards = []
    library = ws.world.get_blueprint_library()
    for label, (bx, by) in layout.items():
        blueprint = library.find("static.prop.mesh")
        blueprint.set_attribute("mesh_path", ws.args.mesh_path)
        blueprint.set_attribute("scale", str(ws.args.board_scale))
        # upstream frame -> CARLA world: forward along the hero, Y left = -CARLA y.
        yaw = math.radians(hero_t.rotation.yaw)
        vx, vy = bumper_x + bx, -by
        wx = hero_t.location.x + vx * math.cos(yaw) - vy * math.sin(yaw)
        wy = hero_t.location.y + vx * math.sin(yaw) + vy * math.cos(yaw)
        transform = ws.carla.Transform(ws.carla.Location(wx, wy, ground_z + ws.args.board_lift_m),
                                       ws.carla.Rotation(pitch=0.0, yaw=hero_t.rotation.yaw, roll=0.0))
        board = ws.world.spawn_actor(blueprint, transform)
        board.set_simulate_physics(False)
        board.apply_texture(ws.carla.MaterialParameter.Diffuse, texture)
        ws._spawned.append(board)
        boards.append({"label": label, "upstreamXY": [bx, by], "actor_id": board.id,
                       "world": {"x": wx, "y": wy, "z": ground_z + ws.args.board_lift_m}})
    images: list = []
    ws.camera.listen(images.append)
    for _ in range(int(ws.args.capture_ticks)):
        ws.tick()
    ws.camera.stop()
    if not images:
        raise BenchError("the front camera delivered no image")
    image = images[-1]
    out_png = ws.sim_dir / "calibration_frame.png"
    out_png.write_bytes(camcal.bgra_to_png(bytes(image.raw_data), image.width, image.height))
    capture = {
        "kind": "camera-capture", "setting": st.setting_id, "map": ws.map.name, "start": ws.start_info,
        "vehicle": ws.hero.type_id, "frontCamera": ws.camera_info, "frontBumperXM": bumper_x,
        "groundZ": ground_z, "heroZ": float(hero_t.location.z), "heroPitchDeg": float(hero_t.rotation.pitch),
        "heroRollDeg": float(hero_t.rotation.roll), "boardLiftM": float(ws.args.board_lift_m),
        "heroWorld": _pose(hero_t), "cameraWorld": _pose(ws.camera.get_transform()),
        "boards": boards, "meshPath": ws.args.mesh_path, "boardScale": ws.args.board_scale,
        "checkerboard": {"path": str(png), "sha256": sha256_file(png), "width": width, "height": height},
        "frame": {"path": out_png.name, "sha256": sha256_file(out_png), "carlaFrame": image.frame,
                  "width": image.width, "height": image.height},
        "upstreamArgs": {label: b["upstreamXY"] for label, b in zip(layout, boards)},
    }
    (ws.sim_dir / "camera_capture.json").write_text(json.dumps(capture, indent=1))
    ws.event("end", reason="frame captured", frame=image.frame)
    return capture


# ----------------------------------------------------------------------- CLI


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("command", choices=["survey", "warmup", "run", "calib-steer", "calib-decel", "camera-capture"])
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=2000)
    p.add_argument("--client-timeout", type=float, default=60.0)
    p.add_argument("--map", default=DEFAULT_MAP)
    p.add_argument("--setting", default="SC-DRIVING-012@20", choices=sorted(scenarios.SETTINGS))
    p.add_argument("--start", default=None, help="road:lane:s of the hero's start; default: the survey's first")
    p.add_argument("--vehicle", default=None, help="the hero's blueprint; default: " + ", ".join(VEHICLE_CANDIDATES))
    p.add_argument("--role", default=None,
                   help=f"role_name of the vehicle in warmup ({HERO_ROLE}), calib-decel and camera-capture "
                        f"({CALIBRATION_ROLE}: neither the adapter nor the camera interface attaches to it)")
    p.add_argument("--run-dir", required=True)
    p.add_argument("--run-s", type=float, default=None, help="run cap in simulation seconds")
    p.add_argument("--target-ahead-m", type=float, default=None)
    p.add_argument("--lateral-offset-m", type=float, default=None,
                   help="calib-steer: the hero's start right of its lane center (positive right)")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--warmup-step-m", type=float, default=1.0)
    p.add_argument("--speeds", default="20,42,60", help="calib-decel: approach speeds, km/h")
    p.add_argument("--decels", default="1,2,3,4,5", help="calib-decel: commanded decelerations, m/s2")
    p.add_argument("--road-m", type=float, default=300.0, help="calib-decel: straight road needed")
    p.add_argument("--checkerboard", default=None, help="camera-capture: upstream's checkerboard-bw-4x4.png")
    p.add_argument("--mesh-path", default=camcal.DEFAULT_MESH_PATH)
    p.add_argument("--board-scale", type=float, default=camcal.DEFAULT_BOARD_SCALE)
    p.add_argument("--board-lift-m", type=float, default=0.01)
    p.add_argument("--near-m", type=float, default=camcal.DEFAULT_NEAR_M)
    p.add_argument("--far-m", type=float, default=camcal.DEFAULT_FAR_M)
    p.add_argument("--half-spacing-m", type=float, default=camcal.DEFAULT_HALF_SPACING_M)
    p.add_argument("--capture-ticks", type=int, default=20)
    p.add_argument("--go-file", default=None,
                   help="run, calib-steer: after ready.json, hold the first tick until this file exists")
    p.add_argument("--go-wait-s", type=float, default=900.0)
    p.add_argument("--release-file", default=None,
                   help="run, calib-steer: after the run, keep ticking (hold.jsonl) until this file exists")
    p.add_argument("--release-wait-s", type=float, default=300.0)
    p.add_argument("--dry-run", action="store_true", help="print the plan; no client")
    return p


def plan(args: argparse.Namespace) -> dict:
    st = scenarios.setting(args.setting)
    return {"command": args.command, "setting": st.as_record(), "map": args.map, "stepS": STEP_S,
            "frontCamera": {**FRONT_CAMERA, "sensor_tick": FRONT_SENSOR_TICK_S, "role": CAMERA_ROLE},
            "heroRole": HERO_ROLE, "vehicleCandidates": list(VEHICLE_CANDIDATES), "target": TARGET_BLUEPRINT,
            "start": args.start or "survey", "runCapS": args.run_s or st.run_cap_s,
            "targetAheadM": args.target_ahead_m or st.target_ahead_m}


COMMANDS = {"survey": cmd_survey, "warmup": cmd_warmup, "run": cmd_run,
            "calib-steer": lambda ws: cmd_run(ws, "calib-steer"), "calib-decel": cmd_calib_decel,
            "camera-capture": cmd_camera_capture}


def main(argv: Iterable[str] | None = None, *, client_factory=None, clock=time.monotonic, sleep=time.sleep,
         stop_requested: threading.Event | None = None, out: Callable[[str], None] = print,
         wall: Callable[[], float] = time.time) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    if args.role is None:
        args.role = CALIBRATION_ROLE if args.command in ("calib-decel", "camera-capture") else HERO_ROLE
    if args.command == "calib-steer" and args.lateral_offset_m is None:
        args.lateral_offset_m = calibration.STEER_OFFSET_M
    if args.command == "camera-capture" and not args.checkerboard:
        out(json.dumps({"event": "error", "reason": "camera-capture needs --checkerboard"}))
        return 2
    if args.dry_run:
        out(json.dumps(plan(args), indent=1))
        return 0
    stop = stop_requested or threading.Event()
    if stop_requested is None and threading.current_thread() is threading.main_thread():
        for sig in (signal.SIGINT, signal.SIGTERM):
            signal.signal(sig, lambda *_: stop.set())
    ws = WorldSide(args, client_factory=client_factory, clock=clock, sleep=sleep, stop_requested=stop, out=out,
                   wall=wall)
    try:
        COMMANDS[args.command](ws)
        return 0
    except BenchError as exc:
        ws.event("error", reason=str(exc))
        (ws.sim_dir / "error.json").write_text(json.dumps({"reason": str(exc)}))
        return 2
    finally:
        ws.teardown()


if __name__ == "__main__":
    sys.exit(main())
