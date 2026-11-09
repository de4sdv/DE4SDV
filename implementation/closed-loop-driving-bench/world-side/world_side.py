#!/usr/bin/env python3
"""World side of the DE4SDV closed-loop driving bench (ICD v2, section 10 C1).

Runs on the simulator host next to CARLA 0.9.16. It is the only client that
ticks the world: synchronous mode, one tick = 100 ms of simulation time, paced
on the wall clock. It

* spawns the hero (role_name ``hero``) at the route start and the six-camera rig
  the agent looks for, at the poses ``de4sdv_planner.rig`` computes;
* announces the handover frame with a marker actor named
  ``de4sdv_handover_<F_h>``, drives the warm-up on the Traffic Manager and hands
  the hero over at F_h;
* injects the world-side faults of SC-DRIVING-003 (C8);
* writes one C1 record per tick to ``<run_dir>/simulator/world.jsonl``.

Records: ``world.jsonl`` holds tick records only. ``runio.world_by_frame()``
raises on any record whose data has no integer frame, so lifecycle records
(``start``, ``config``, ``stop``, ``error``) go to the companion file
``<run_dir>/simulator/worldSide.jsonl`` with the same ICD section 6 envelope.

Frames: ``egoPose`` and ``velocity.heading_rad`` are in the map frame of ICD
section 9 (x_map = x_carla, y_map = -y_carla, yaw_map = -yaw_carla); the other
kinematics are CARLA frame and the README (R8) says which is which.

Only ``carla`` and numpy are needed at run time. The camera profile module
(``de4sdv_planner/rig.py``) is loaded by path; the agent ships it and the rig
must be spawned with its functions so the agent's set_rig round trip matches.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import signal
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Iterable

STEP_S = 0.1
STEP_MS = 100
LATE_TOLERANCE_S = 0.001      # a tick later than this past its deadline is counted
COMPONENT = "worldSide"
HOST = "simulator"
WORLD_LOG = "simulator/world.jsonl"
SIDE_LOG = "simulator/worldSide.jsonl"
INJECTION_LOG = "bench/injection.jsonl"
SUMMARY = "simulator/summary.json"

SLOTS = ["front", "front_left", "front_right", "rear_left", "rear", "rear_right"]
MARKER_PREFIX = "de4sdv_handover_"
DEFAULT_VEHICLE = "vehicle.lincoln.mkz_2020"
SPAWN_MATCH_M = 2.0
ROUTE_END_M = 5.0
# Setup ticks before the run: until CARLA has simulated the new hero and it rests on its wheels.
SETTLE_MIN_TICKS = 2
SETTLE_MAX_TICKS = 50
SETTLE_SPEED_MPS = 0.05
SETTLE_DZ_M = 0.002
# yawRateCheck in the summary: ticks whose pose-derived yaw rate exceeds this are compared.
YAW_CHECK_MIN_RAD_S = 0.05

# static.prop blueprints to try, in order; any other static.prop.* is a fallback
STATIC_PROP_CANDIDATES = (
    "static.prop.trafficcone01",
    "static.prop.constructioncone",
    "static.prop.streetbarrier",
)

SENSOR_CAMERA = "sensor.camera.rgb"
SENSOR_COLLISION = "sensor.other.collision"
SENSOR_LANE = "sensor.other.lane_invasion"


class BenchError(Exception):
    """A configuration or simulator condition the tool refuses to run with."""


# --------------------------------------------------------------------- helpers


def as_num(value: Any) -> float | None:
    """ICD section 6: a non-finite value is JSON null."""
    try:
        x = float(value)
    except (TypeError, ValueError):
        return None
    return x if math.isfinite(x) else None


def frames_of(seconds: float) -> int:
    """Whole ticks in a duration; a tick is 100 ms of simulation time."""
    return int(round(float(seconds) / STEP_S))


def map_to_carla_xy(x_map: float, y_map: float) -> tuple[float, float]:
    """ICD section 9 map frame -> CARLA world (navigation/carla_frame.py)."""
    return float(x_map), -float(y_map)


def carla_to_map_xy(x_carla: float, y_carla: float) -> tuple[float, float]:
    return float(x_carla), -float(y_carla)


def map_to_carla_heading(yaw_map_rad: float) -> float:
    return -float(yaw_map_rad)


def carla_to_map_heading(yaw_carla_rad: float) -> float:
    return -float(yaw_carla_rad)


def find_blueprint(library, blueprint_id: str):
    """The blueprint with this id, or None. CARLA 0.9.16's BlueprintLibrary.find raises
    IndexError for an unknown id (BlueprintLibrary::at); it never returns None."""
    try:
        return library.find(blueprint_id)
    except IndexError:
        return None


def last_path_element(name: str) -> str:
    """'Carla/Maps/Town10HD_Opt' -> 'Town10HD_Opt'."""
    return str(name).rstrip("/").split("/")[-1]


# ------------------------------------------------------------------- containers


class Route:
    """An ICD section 9 route file, in the map frame."""

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.is_file():
            raise BenchError(f"route file not found: {self.path}")
        raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        try:
            payload = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise BenchError(f"route file {self.path}: {exc}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("waypoints"), list):
            raise BenchError(f"route file {self.path}: not an ICD section 9 route")
        self.map_name = str(payload.get("map") or "")
        self.waypoints: list[tuple[float, float, float, Any]] = []
        for i, wp in enumerate(payload["waypoints"]):
            if not isinstance(wp, list) or len(wp) < 3:
                raise BenchError(f"route file {self.path}: waypoint {i} is not [x, y, heading, road_id]")
            self.waypoints.append((float(wp[0]), float(wp[1]), float(wp[2]),
                                   wp[3] if len(wp) > 3 else None))
        if not self.waypoints:
            raise BenchError(f"route file {self.path}: no waypoints")
        dest = payload.get("destination")
        if not (isinstance(dest, list) and len(dest) >= 2):
            raise BenchError(f"route file {self.path}: no destination [x, y]")
        self.destination = (float(dest[0]), float(dest[1]))

    @property
    def start(self) -> tuple[float, float, float]:
        x, y, heading, _ = self.waypoints[0]
        return x, y, heading

    def carla_points(self, z: float = 0.0) -> list[tuple[float, float, float]]:
        """Waypoints as CARLA world points (x, y, yaw_rad), for the Traffic Manager."""
        out = []
        for x, y, heading, _ in self.waypoints:
            cx, cy = map_to_carla_xy(x, y)
            out.append((cx, cy, map_to_carla_heading(heading)))
        return out


class Camera:
    """One rig camera actor and the render spec it was spawned with."""

    def __init__(self, slot: str, actor: Any, width: int, height: int, fov: float):
        self.slot = slot
        self.name = f"cam_{slot}"
        self.actor = actor
        self.width = int(width)
        self.height = int(height)
        self.fov = float(fov)
        self.destroyed_at_frame: int | None = None

    def actor_id(self) -> int:
        return int(getattr(self.actor, "id", -1))


class Fault:
    """A parsed --fault argument. ``frame`` is filled in once F_h is known."""

    def __init__(self, kind: str, text: str, slot: str | None = None, after_s: float = 0.0):
        self.kind = kind
        self.text = text
        self.slot = slot
        self.after_s = float(after_s)
        self.frame: int | None = None
        self.fired = False

    def describe(self) -> dict:
        return {"fault": self.kind, "argument": self.text, "camera": self.slot,
                "afterHandoverS": self.after_s, "frame": self.frame, "fired": self.fired}


# ------------------------------------------------------------------- envelopes


class JsonlWriter:
    """ICD section 6 JSONL writer (the envelope of navigation/route_provider.py)."""

    def __init__(self, path: str | Path, *, host: str = HOST, component: str = COMPONENT):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._host = host
        self._component = component
        self._sequence = 0
        self._lock = threading.Lock()
        self._file = self.path.open("a", encoding="utf-8")

    def write(self, event: str, data: dict | None = None) -> int:
        with self._lock:
            self._sequence += 1
            record = {
                "t_mono_ns": time.monotonic_ns(),
                "t_real_ns": time.time_ns(),
                "host": self._host,
                "component": self._component,
                "event": event,
                "seq": self._sequence,
                "data": data or {},
            }
            self._file.write(json.dumps(record, separators=(",", ":"), allow_nan=False) + "\n")
            self._file.flush()
            return self._sequence

    def close(self) -> None:
        with self._lock:
            if self._file is not None:
                self._file.close()
                self._file = None


# --------------------------------------------------------------------- pacing


class Pacer:
    """Real-time pacing of the tick loop (R3).

    Deadlines come from the injected monotonic clock. A tick that overruns its
    slot moves the schedule forward and is counted; the loop never bursts to
    catch up.
    """

    def __init__(self, period_s: float = STEP_S, *,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep):
        self.period = float(period_s)
        self.clock = clock
        self.sleep = sleep
        self.next_deadline = 0.0
        self.ticks = 0
        self.late_ticks = 0
        self.schedule_slips = 0
        self.max_lateness_s = 0.0
        self.max_slip_s = 0.0

    def start(self) -> None:
        self.next_deadline = self.clock()

    def wait_turn(self) -> tuple[float, float]:
        """Sleep until this tick's deadline; returns (start, lateness)."""
        now = self.clock()
        if now < self.next_deadline:
            self.sleep(self.next_deadline - now)
        start = self.clock()
        lateness = max(0.0, start - self.next_deadline)
        if lateness > LATE_TOLERANCE_S:
            self.late_ticks += 1
            self.max_lateness_s = max(self.max_lateness_s, lateness)
        return start, lateness

    def finish_turn(self, end: float) -> float:
        """Close the slot; returns the schedule slip (s), 0 when on time."""
        self.ticks += 1
        self.next_deadline += self.period
        slip = end - self.next_deadline
        if slip > 1e-6:
            self.schedule_slips += 1
            self.max_slip_s = max(self.max_slip_s, slip)
            self.next_deadline = end
            return slip
        return 0.0


class Tick:
    """One completed world tick."""

    def __init__(self, frame: int, start: float, end: float, lateness: float, duration: float):
        self.frame = int(frame)
        self.start = start
        self.end = end
        self.lateness = lateness
        self.duration = duration


# ---------------------------------------------------------------------- faults


def parse_camera_stop(text: str) -> Fault:
    body = text.split(":", 1)[1]
    if "@" not in body:
        raise BenchError(f"{text}: expected camera_stop:<slot>@<seconds after handover>")
    slot, seconds = body.split("@", 1)
    slot = slot.strip()
    name = slot[len("cam_"):] if slot.startswith("cam_") else slot
    if name not in SLOTS:
        raise BenchError(f"{text}: unknown camera slot {slot!r}; known: {', '.join(SLOTS)}")
    try:
        after = float(seconds)
    except ValueError as exc:
        raise BenchError(f"{text}: {seconds!r} is not a number of seconds") from exc
    if after < 0.0:
        raise BenchError(f"{text}: the fault time must not be negative")
    return Fault("camera_stop", text, slot=name, after_s=after)


def parse_run_end_brake(text: str) -> Fault:
    # accepted for the C8 vocabulary; the world side applies no vehicle control
    return Fault("run_end_brake", text)


FAULT_PARSERS: dict[str, Callable[[str], Fault]] = {
    "camera_stop": parse_camera_stop,
    "run_end_brake": parse_run_end_brake,
}


def parse_fault(text: str) -> Fault:
    kind = text.split(":", 1)[0]
    parser = FAULT_PARSERS.get(kind)
    if parser is None:
        raise BenchError(f"unknown fault {text!r}; supported: "
                         + ", ".join(sorted(FAULT_PARSERS)))
    return parser(text)


# -------------------------------------------------------------------- rig load


def load_rig_module(path: str | None):
    """The camera profile module: --rig-path, else ``de4sdv_planner.rig``."""
    if path:
        target = Path(path)
        if not target.is_file():
            raise BenchError(f"rig module not found: {target}")
        spec = importlib.util.spec_from_file_location("de4sdv_rig", str(target))
        if spec is None or spec.loader is None:
            raise BenchError(f"cannot load the rig module {target}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    else:
        try:
            from de4sdv_planner import rig as module  # noqa: WPS433
        except ImportError as exc:
            raise BenchError("de4sdv_planner.rig is not importable; pass --rig-path "
                             "to the agent's python/de4sdv_planner/rig.py") from exc
    for name in ("load_profile", "render_spec", "actor_pose_in_vehicle",
                 "ref_origin_from_vehicle"):
        if not hasattr(module, name):
            raise BenchError(f"rig module {getattr(module, '__file__', '?')} has no {name}()")
    return module


# ------------------------------------------------------------------ the tool


class WorldSide:
    """Map, hero, rig, warm-up, handover, faults, C1 records."""

    def __init__(self, args: argparse.Namespace, *,
                 client_factory: Callable[[str, int], Any] | None = None,
                 clock: Callable[[], float] = time.monotonic,
                 sleep: Callable[[float], None] = time.sleep,
                 rig_module: Any = None,
                 stop_requested: threading.Event | None = None):
        self.args = args
        self.clock = clock
        self.sleep = sleep
        self.client_factory = client_factory
        self.rig = rig_module
        self.stop_requested = stop_requested or threading.Event()

        self.run_dir = Path(args.run_dir)
        self.route = Route(args.route)
        if self.route.map_name and last_path_element(self.route.map_name) \
                != last_path_element(args.map):
            raise BenchError(f"map mismatch: the route names {self.route.map_name!r}, "
                             f"--map is {args.map!r}")
        if not Path(args.profile).is_file():
            raise BenchError(f"camera profile not found: {args.profile}")
        self.faults = [parse_fault(text) for text in (args.fault or [])]

        self.client = None
        self.world = None
        self.map = None
        self.tm = None
        self.hero = None
        self.marker = None
        self.cameras: list[Camera] = []
        self.extra_sensors: list[Any] = []
        self.origin = None
        self.origin_info: dict = {}

        self.original_settings: dict[str, Any] = {}
        self.settings_applied = False
        self.tm_synchronous = False
        self._torn_down = False
        self._teardown_lock = threading.Lock()
        self._spawned: list[Any] = []

        self.pacer = Pacer(clock=clock, sleep=sleep)
        self.autopilot = False
        self.handover_done = False
        self.handover_frame: int | None = None
        self.first_frame: int | None = None
        self.end_frame: int | None = None
        self.last_frame: int | None = None
        self.stop_reason: str | None = None
        self.frame_skips = 0
        self.late_sensor_events = 0
        self.tick_durations: list[float] = []
        self.wall_start: float | None = None
        self.wall_end: float | None = None

        self._events: list[dict] = []
        self._events_lock = threading.Lock()
        self.setup_info: dict = {}
        self._prev_yaw: tuple[int, float] | None = None
        self._yaw_check = {"compared": 0, "agree": 0, "diffs": []}

        self.world_log = JsonlWriter(self.run_dir / WORLD_LOG)
        self.side_log = JsonlWriter(self.run_dir / SIDE_LOG)
        self.injection_log = JsonlWriter(self.run_dir / INJECTION_LOG)

    # ------------------------------------------------------------- connection
    def connect(self) -> None:
        import carla  # noqa: WPS433 (only on the simulator host)

        self.carla = carla
        factory = self.client_factory or (lambda host, port: carla.Client(host, port))
        self.client = factory(self.args.host, int(self.args.port))
        self.client.set_timeout(float(self.args.client_timeout))
        self.world = self.client.get_world()

    def ensure_map(self) -> None:
        """Load --map only if the current map differs (last path element)."""
        current = last_path_element(self.world.get_map().name)
        wanted = last_path_element(self.args.map)
        if current != wanted:
            try:
                self.world = self.client.load_world(self.args.map)
            except Exception as exc:  # noqa: BLE001 - reported as a bench error
                raise BenchError(f"cannot load map {self.args.map!r} "
                                 f"(current map {current!r}): {exc}") from exc
            loaded = last_path_element(self.world.get_map().name)
            if loaded != wanted:
                raise BenchError(f"loaded map is {loaded!r}, expected {wanted!r}")
        self.map = self.world.get_map()

    # --------------------------------------------------------------- settings
    def apply_settings(self) -> None:
        original = self.world.get_settings()
        self.original_settings = {
            "synchronous_mode": bool(original.synchronous_mode),
            "fixed_delta_seconds": original.fixed_delta_seconds,
        }
        settings = self.world.get_settings()
        settings.synchronous_mode = True
        settings.fixed_delta_seconds = STEP_S
        self.world.apply_settings(settings)
        self.settings_applied = True

        self.tm = self.client.get_trafficmanager(int(self.args.tm_port))
        self.tm.set_synchronous_mode(True)
        self.tm_synchronous = True
        if hasattr(self.tm, "set_random_device_seed"):
            self.tm.set_random_device_seed(int(self.args.seed))

    def restore_settings(self) -> None:
        if self.tm is not None and self.tm_synchronous:
            try:
                self.tm.set_synchronous_mode(False)
            except Exception:  # noqa: BLE001 - teardown is best effort
                pass
            self.tm_synchronous = False
        if self.world is not None and self.settings_applied:
            try:
                settings = self.world.get_settings()
                settings.synchronous_mode = self.original_settings.get("synchronous_mode", False)
                settings.fixed_delta_seconds = self.original_settings.get("fixed_delta_seconds")
                self.world.apply_settings(settings)
            except Exception:  # noqa: BLE001
                pass
            self.settings_applied = False

    # ------------------------------------------------------------------ spawn
    def spawn_points(self) -> list[Any]:
        points = list(self.world.get_map().get_spawn_points())
        if not points:
            raise BenchError("the map has no spawn points")
        return points

    def pick_spawn(self) -> tuple[int, Any]:
        points = self.spawn_points()
        if self.args.spawn_index is not None:
            index = int(self.args.spawn_index)
            if not 0 <= index < len(points):
                raise BenchError(f"--spawn-index {index} is outside 0..{len(points) - 1}")
            return index, points[index]
        x_map, y_map, _ = self.route.start
        x_carla, y_carla = map_to_carla_xy(x_map, y_map)
        best, best_d = None, None
        for i, point in enumerate(points):
            d = math.hypot(point.location.x - x_carla, point.location.y - y_carla)
            if best_d is None or d < best_d:
                best, best_d = i, d
        if best_d is None or best_d > SPAWN_MATCH_M:
            raise BenchError(
                f"no spawn point within {SPAWN_MATCH_M:g} m of the route start "
                f"({x_carla:.3f}, {y_carla:.3f}) in CARLA coordinates; nearest is "
                f"{best_d:.3f} m away (index {best}); pass --spawn-index")
        return best, points[best]

    def spawn_hero(self) -> None:
        index, transform = self.pick_spawn()
        self.spawn_index = index
        blueprint_id = DEFAULT_VEHICLE
        if self.args.vehicle_config:
            path = Path(self.args.vehicle_config)
            if not path.is_file():
                raise BenchError(f"vehicle configuration not found: {path}")
            try:
                payload = json.loads(path.read_text())
            except json.JSONDecodeError as exc:
                raise BenchError(f"vehicle configuration {path}: {exc}") from exc
            blueprint_id = str(payload.get("vehicle_blueprint") or DEFAULT_VEHICLE)
        library = self.world.get_blueprint_library()
        blueprint = find_blueprint(library, blueprint_id)
        if blueprint is None:
            raise BenchError(f"vehicle blueprint {blueprint_id!r} is not in the blueprint library")
        blueprint.set_attribute("role_name", "hero")
        try:
            self.hero = self.world.spawn_actor(blueprint, transform)
        except Exception as exc:  # noqa: BLE001
            raise BenchError(f"cannot spawn the hero at spawn point {index}: {exc}") from exc
        if self.hero is None:
            raise BenchError(f"cannot spawn the hero at spawn point {index}")
        self._spawned.append(self.hero)
        self.spawn_transform = transform

    def settle_hero(self) -> None:
        """Tick until CARLA has simulated the hero and it rests on its wheels.

        In synchronous mode a new actor is in no world snapshot before the next tick, so its
        transform reads as zero, while get_physics_control answers from the server at once; and a
        spawned vehicle drops onto its suspension over the first ticks. The rig origin is read
        only from a settled hero, the state the agent reads at its attach. These ticks are setup,
        not run: no C1 record; worldSide.jsonl logs one 'setup' record.
        """
        last_z = None
        z = speed = None
        for i in range(1, SETTLE_MAX_TICKS + 1):
            frame = int(self.world.tick())
            location = self.hero.get_location()
            v = self.hero.get_velocity()
            speed = math.sqrt(float(v.x) ** 2 + float(v.y) ** 2 + float(v.z) ** 2)
            z = float(location.z)
            settled = (i >= SETTLE_MIN_TICKS and last_z is not None
                       and abs(z - last_z) < SETTLE_DZ_M and speed < SETTLE_SPEED_MPS)
            last_z = z
            if settled:
                self.setup_info = {"settled": True, "setupTicks": i, "settledAtFrame": frame,
                                   "heroZ": as_num(z), "speedMps": as_num(speed)}
                self.side_log.write("setup", self.setup_info)
                return
        raise BenchError(f"the hero did not settle within {SETTLE_MAX_TICKS} ticks "
                         f"(last z {z}, speed {speed} m/s)")

    def spawn_rig(self) -> None:
        if self.rig is None:
            raise BenchError("no rig module loaded")
        profile, cams = self.rig.load_profile(self.args.profile)
        self.profile = profile
        slots = [cam.get("slot") for cam in cams]
        if slots != SLOTS:
            raise BenchError(f"camera profile slots are {slots}, expected {SLOTS}")

        origin = self.rig.ref_origin_from_vehicle(self.hero)
        self.origin_info = {}
        if isinstance(origin, tuple) and len(origin) == 2:
            origin, self.origin_info = origin[0], dict(origin[1] or {})
        self.origin = origin

        library = self.world.get_blueprint_library()
        for i, cam in enumerate(cams):
            width = int(self.args.front_width if i == 0 else self.args.width)
            W, H, _f, hfov = self.rig.render_spec(cam, width)
            T = self.rig_matrix(cam)
            location, (pitch, yaw, roll) = self.rig.actor_pose_in_vehicle(T, origin)
            blueprint = find_blueprint(library, SENSOR_CAMERA)
            if blueprint is None:
                raise BenchError(f"{SENSOR_CAMERA} is not in the blueprint library")
            role = f"cam_{cam['slot']}"
            blueprint.set_attribute("role_name", role)
            blueprint.set_attribute("image_size_x", str(int(W)))
            blueprint.set_attribute("image_size_y", str(int(H)))
            blueprint.set_attribute("fov", f"{float(hfov):.6f}")
            blueprint.set_attribute("sensor_tick", "0.0")
            transform = self.carla.Transform(
                self.carla.Location(x=float(location[0]), y=float(location[1]),
                                    z=float(location[2])),
                self.carla.Rotation(pitch=float(pitch), yaw=float(yaw), roll=float(roll)),
            )
            try:
                actor = self.world.spawn_actor(blueprint, transform, attach_to=self.hero)
            except Exception as exc:  # noqa: BLE001
                raise BenchError(f"cannot spawn camera {role}: {exc}") from exc
            if actor is None:
                raise BenchError(f"cannot spawn camera {role}")
            self.cameras.append(Camera(cam["slot"], actor, W, H, hfov))
            self._spawned.append(actor)

        sensor_plan = ((SENSOR_COLLISION, self._on_collision),
                       (SENSOR_LANE, self._on_lane_invasion))
        for blueprint_id, handler in (sensor_plan if self.args.collision_sensors else ()):
            blueprint = find_blueprint(library, blueprint_id)
            if blueprint is None:
                raise BenchError(f"{blueprint_id} is not in the blueprint library")
            try:
                actor = self.world.spawn_actor(blueprint, self.carla.Transform(),
                                               attach_to=self.hero)
            except Exception as exc:  # noqa: BLE001
                raise BenchError(f"cannot spawn {blueprint_id}: {exc}") from exc
            actor.listen(handler)
            self.extra_sensors.append(actor)
            self._spawned.append(actor)

    @staticmethod
    def rig_matrix(cam: dict):
        import numpy as np

        return np.asarray(cam["camera_to_reference"], dtype=np.float64).reshape(4, 4)

    def start_warmup(self) -> None:
        """Hand the hero to the Traffic Manager until F_h (R6)."""
        if self.args.warmup_s <= 0:
            return
        points = self.route.carla_points(z=float(self.spawn_transform.location.z))
        path = [self.carla.Location(x=x, y=y, z=z) for x, y, z in points]
        self.hero.set_autopilot(True, int(self.args.tm_port))
        self.autopilot = True
        try:
            self.tm.set_path(self.hero, path)
        except Exception as exc:  # noqa: BLE001
            raise BenchError(f"traffic manager set_path failed: {exc}") from exc
        if hasattr(self.tm, "set_desired_speed"):
            self.tm.set_desired_speed(self.hero, float(self.args.warmup_speed_kmh))
        if hasattr(self.tm, "auto_lane_change"):
            self.tm.auto_lane_change(self.hero, False)
        if hasattr(self.tm, "ignore_lights_percentage"):
            # The exported Town10HD_Opt route crosses signalised junctions; the
            # warm-up must reach F_h at the route's start, so lights are ignored.
            self.tm.ignore_lights_percentage(self.hero, 100.0)
        if hasattr(self.tm, "vehicle_percentage_speed_difference"):
            self.tm.vehicle_percentage_speed_difference(self.hero, 0.0)

    def spawn_marker(self) -> None:
        library = self.world.get_blueprint_library()
        blueprint = None
        for candidate in STATIC_PROP_CANDIDATES:
            blueprint = find_blueprint(library, candidate)
            if blueprint is not None:
                break
        if blueprint is None:
            for candidate in library.filter("static.prop.*"):
                blueprint = candidate
                break
        if blueprint is None:
            raise BenchError("no static.prop.* blueprint for the handover marker")
        blueprint.set_attribute("role_name", f"{MARKER_PREFIX}{self.handover_frame}")
        transform = self.carla.Transform(
            self.carla.Location(x=0.0, y=0.0, z=-500.0),
            self.carla.Rotation(pitch=0.0, yaw=0.0, roll=0.0),
        )
        try:
            self.marker = self.world.spawn_actor(blueprint, transform)
        except Exception as exc:  # noqa: BLE001
            raise BenchError(f"cannot spawn the handover marker: {exc}") from exc
        if self.marker is None:
            raise BenchError("cannot spawn the handover marker")
        try:
            self.marker.set_simulate_physics(False)
        except Exception:  # noqa: BLE001 - props accept it; the marker is inert anyway
            pass
        self._spawned.append(self.marker)

    # --------------------------------------------------------------- sensors
    def _on_collision(self, event) -> None:
        other = getattr(event, "other_actor", None)
        impulse = getattr(event, "normal_impulse", None)
        with self._events_lock:
            self._events.append({
                "type": "collision",
                "frame": int(getattr(event, "frame", -1)),
                "other_actor": getattr(other, "type_id", None),
                "other_actor_id": getattr(other, "id", None),
                "impulse_mps": None if impulse is None else
                {"x": as_num(getattr(impulse, "x", None)),
                 "y": as_num(getattr(impulse, "y", None)),
                 "z": as_num(getattr(impulse, "z", None))},
            })

    def _on_lane_invasion(self, event) -> None:
        markings = getattr(event, "crossed_lane_markings", None) or []
        with self._events_lock:
            self._events.append({
                "type": "lane_invasion",
                "frame": int(getattr(event, "frame", -1)),
                "markings": [str(getattr(m, "type", m)) for m in markings],
            })

    def take_events(self, frame: int) -> tuple[list[dict], list[dict], int]:
        """Events for ``frame``, late events, and the count of future events."""
        with self._events_lock:
            pending, self._events = self._events, []
        for_this, late, future = [], [], []
        for event in pending:
            if event["frame"] == frame:
                for_this.append(event)
            elif event["frame"] < frame:
                late.append(event)
            else:
                future.append(event)
        if future:
            with self._events_lock:
                self._events.extend(future)
        if late:
            self.late_sensor_events += len(late)
        return for_this, late, len(future)

    # ------------------------------------------------------------------ ticks
    def _do_tick(self) -> Tick:
        start, lateness = self.pacer.wait_turn()
        frame = int(self.world.tick())
        end = self.clock()
        self.pacer.finish_turn(end)
        tick = Tick(frame, start, end, lateness, end - start)
        self.tick_durations.append(tick.duration)
        return tick

    def _apply_due(self, frame: int) -> None:
        """Actions that must happen before the tick of ``frame``."""
        if not self.handover_done and self.handover_frame is not None \
                and frame >= self.handover_frame:
            self.hero.set_autopilot(False, int(self.args.tm_port))
            self.autopilot = False
            self.handover_done = True
        for fault in self.faults:
            if fault.fired or fault.frame is None or frame < fault.frame:
                continue
            if fault.kind == "camera_stop":
                self._fire_camera_stop(fault)
            else:
                fault.fired = True

    def _fire_camera_stop(self, fault: Fault) -> None:
        camera = next((c for c in self.cameras if c.slot == fault.slot), None)
        if camera is None:
            raise BenchError(f"camera_stop: no camera {fault.slot!r} on the rig")
        try:
            camera.actor.destroy()
        except Exception as exc:  # noqa: BLE001
            raise BenchError(f"cannot destroy cam_{camera.slot}: {exc}") from exc
        camera.destroyed_at_frame = fault.frame
        fault.fired = True
        now_mono = time.monotonic_ns()
        self.injection_log.write("injection", {
            "action": "camera_stop",
            "t_sim_ms": int(fault.frame) * STEP_MS,
            "t_mono_ns": now_mono,
            "t_real_ns": time.time_ns(),
            "detail": {
                "camera": camera.name,
                "actor_id": camera.actor_id(),
                "fault": "camera_missing",
                "handoverFrame": self.handover_frame,
                "afterHandoverS": fault.after_s,
            },
        })

    # ---------------------------------------------------------------- records
    def _autopilot_enabled(self) -> bool:
        """The tool's own switch, cross-checked with the vehicle when CARLA can say."""
        getter = getattr(self.hero, "get_autopilot", None)
        if callable(getter):
            try:
                return bool(getter())
            except Exception:  # noqa: BLE001 - not every build exposes it
                pass
        return bool(self.autopilot)

    def _alive(self, actor) -> bool:
        if actor is None:
            return False
        try:
            return bool(actor.is_alive())
        except Exception:  # noqa: BLE001 - a dead handle is not alive
            return False

    def _attached(self, actor) -> bool:
        if not self._alive(actor):
            return False
        try:
            parent = actor.parent
        except Exception:  # noqa: BLE001
            return False
        return parent is not None and getattr(parent, "id", None) == getattr(self.hero, "id", None)

    def _lane(self, location) -> dict:
        try:
            waypoint = self.map.get_waypoint(location, project_to_road=True)
        except Exception:  # noqa: BLE001 - off-road is recorded as null lane info
            waypoint = None
        if waypoint is None:
            return {"road": None, "lane": None, "lat_m": None, "junction": None}
        wp_transform = waypoint.transform
        wp_location = wp_transform.location
        yaw = math.radians(getattr(wp_transform.rotation, "yaw", 0.0))
        right = (-math.sin(yaw), math.cos(yaw))     # driver's right in CARLA
        dx = float(location.x) - float(wp_location.x)
        dy = float(location.y) - float(wp_location.y)
        return {
            "road": getattr(waypoint, "road_id", None),
            "lane": getattr(waypoint, "lane_id", None),
            "lat_m": as_num(dx * right[0] + dy * right[1]),
            "junction": bool(getattr(waypoint, "is_junction", False)),
        }

    def _control(self) -> dict:
        try:
            control = self.hero.get_control()
        except Exception:  # noqa: BLE001
            control = None
        if control is None:
            return {"throttle": None, "brake": None, "steer": None, "accelMps2": None}
        return {
            "throttle": as_num(getattr(control, "throttle", None)),
            "brake": as_num(getattr(control, "brake", None)),
            "steer": as_num(getattr(control, "steer", None)),
            # "what was applied": the adapter's commanded acceleration never reaches this
            # process, so null; the measured value is acceleration.longitudinal_mps2
            "accelMps2": None,
        }

    def tick_data(self, tick: Tick) -> dict:
        frame = tick.frame
        transform = self.hero.get_transform()
        location = transform.location
        yaw_carla = math.radians(float(getattr(transform.rotation, "yaw", 0.0)))
        x_map, y_map = carla_to_map_xy(location.x, location.y)
        yaw_map = carla_to_map_heading(yaw_carla)

        velocity = self.hero.get_velocity()
        vx, vy, vz = float(velocity.x), float(velocity.y), float(velocity.z)
        speed = math.sqrt(vx * vx + vy * vy + vz * vz)

        # Kinematics in the map frame of ICD section 9 (y negated), as the evaluators' reference
        # producer (make_synthetic_run.py) writes them: longitudinal along the heading, lateral
        # positive to the vehicle's left (CARLA's y is right). For a planar turn, lateral equals
        # speed x yaw rate.
        accel = self.hero.get_acceleration()
        ax, ay = float(accel.x), float(accel.y)
        cos_y, sin_y = math.cos(yaw_carla), math.sin(yaw_carla)
        longitudinal = ax * cos_y + ay * sin_y
        lateral = ax * sin_y - ay * cos_y

        # CARLA reports deg/s about its left-handed world axes. Angular velocity is a pseudovector:
        # under the y reflection it becomes (-wx, wy, -wz), so the yaw rate is counter-clockwise
        # positive, the sign of d egoPose.yaw / dt (summary.yawRateCheck measures that on a run).
        angular = self.hero.get_angular_velocity()
        events, late, _future = self.take_events(frame)
        collisions = [e for e in events + late if e["type"] == "collision"]
        invasions = [e for e in events + late if e["type"] == "lane_invasion"]

        data = {
            "frame": frame,
            "sim_ms": frame * STEP_MS,
            "handoverFrame": self.handover_frame,
            "egoPose": {"x": as_num(x_map), "y": as_num(y_map), "yaw": as_num(yaw_map)},
            "velocity": {"speed_mps": as_num(speed), "heading_rad": as_num(yaw_map)},
            "acceleration": {"longitudinal_mps2": as_num(longitudinal),
                             "lateral_mps2": as_num(lateral)},
            "angular_velocity": {
                "roll_rad_s": as_num(-math.radians(float(angular.x))),
                "pitch_rad_s": as_num(math.radians(float(angular.y))),
                "yaw_rad_s": as_num(-math.radians(float(angular.z))),
            },
            "lane": self._lane(location),
            "control": self._control(),
            "controlSource": "autopilot" if frame < (self.handover_frame or 0)
                             else "actuationAdapter",
            "autopilotEnabled": self._autopilot_enabled(),
            "trafficManagerEnabled": bool(self._autopilot_enabled() and self.tm_synchronous),
            "sensors": [
                {"name": cam.name, "actor_id": cam.actor_id(),
                 "alive": self._alive(cam.actor), "attached": self._attached(cam.actor)}
                for cam in self.cameras
            ],
            "collisions": [{"frame": e["frame"], "other_actor": e["other_actor"],
                            "other_actor_id": e["other_actor_id"],
                            "impulse_mps": e["impulse_mps"]} for e in collisions],
            "laneInvasions": [{"frame": e["frame"], "markings": e["markings"]}
                              for e in invasions],
            "tickDurationMonoNs": int(round(tick.duration * 1e9)),
            "latenessMonoNs": int(round(tick.lateness * 1e9)),
        }
        return data

    def write_tick(self, tick: Tick) -> None:
        data = self.tick_data(tick)
        self.world_log.write("tick", data)
        self.last_frame = tick.frame
        self._check_yaw_rate(tick.frame, data)

    def _check_yaw_rate(self, frame: int, data: dict) -> None:
        """Compare CARLA's yaw rate with the yaw rate of the logged poses: the frame and sign
        convention of angular_velocity is otherwise an assumption about CARLA."""
        yaw = data["egoPose"]["yaw"]
        rate = data["angular_velocity"]["yaw_rad_s"]
        if yaw is None:
            return
        if self._prev_yaw is not None and rate is not None and frame > self._prev_yaw[0]:
            derived = math.remainder(yaw - self._prev_yaw[1], 2.0 * math.pi) / (
                (frame - self._prev_yaw[0]) * STEP_S)
            if abs(derived) > YAW_CHECK_MIN_RAD_S:
                self._yaw_check["compared"] += 1
                self._yaw_check["agree"] += int((derived > 0) == (rate > 0))
                self._yaw_check["diffs"].append(abs(derived - rate))
        self._prev_yaw = (frame, yaw)

    # ------------------------------------------------------------------- run
    def start(self) -> None:
        self.side_log.write("start", {
            "component": COMPONENT,
            "map": self.args.map,
            "route": str(self.route.path),
            "routeSha256": self.route.sha256,
            "profile": str(self.args.profile),
            "runDir": str(self.run_dir),
            "host": self.args.host,
            "port": int(self.args.port),
            "tmPort": int(self.args.tm_port),
            "fixedDeltaSeconds": STEP_S,
        })
        self.connect()
        self.ensure_map()
        self.apply_settings()
        self.spawn_hero()
        self.settle_hero()
        if self.rig is None:
            self.rig = load_rig_module(self.args.rig_path)
        self.spawn_rig()
        self.start_warmup()
        self.side_log.write("config", {
            "spawnIndex": self.spawn_index,
            "spawnTransform": {"x": as_num(self.spawn_transform.location.x),
                               "y": as_num(self.spawn_transform.location.y),
                               "z": as_num(self.spawn_transform.location.z),
                               "yaw": as_num(self.spawn_transform.rotation.yaw)},
            "vehicleBlueprint": str(getattr(self.hero, "type_id", DEFAULT_VEHICLE)),
            "warmupS": float(self.args.warmup_s),
            "runS": float(self.args.run_s),
            "warmupSpeedKmh": float(self.args.warmup_speed_kmh),
            "seed": int(self.args.seed),
            "cameras": [{"name": c.name, "actor_id": c.actor_id(), "width": c.width,
                         "height": c.height, "fov": as_num(c.fov)} for c in self.cameras],
            "refOriginUe": [as_num(v) for v in (self.origin if self.origin is not None else [])],
            "refOriginInfo": self.origin_info,
            "faults": [f.describe() for f in self.faults],
        })

    def run(self) -> None:
        self.wall_start = self.clock()
        self.pacer.start()

        tick = self._do_tick()
        self.first_frame = tick.frame
        warmup_frames = frames_of(self.args.warmup_s)
        if warmup_frames <= 0:
            self.handover_frame = tick.frame
            self.handover_done = True
            if self.autopilot:
                self.hero.set_autopilot(False, int(self.args.tm_port))
                self.autopilot = False
        else:
            self.handover_frame = tick.frame + warmup_frames
        run_frames = max(1, frames_of(self.args.run_s))
        self.end_frame = self.handover_frame + run_frames
        for fault in self.faults:
            fault.frame = self.handover_frame + frames_of(fault.after_s)

        self.spawn_marker()
        self.write_tick(tick)
        self.wall_end = tick.end

        expected = tick.frame + 1
        reason = None
        while True:
            if self.stop_requested.is_set():
                reason = "interrupt"
                break
            if expected >= self.end_frame:
                reason = "runDuration"
                break
            self._apply_due(expected)
            tick = self._do_tick()
            if tick.frame != expected:
                self.frame_skips += 1
                self._apply_due(tick.frame)
            self.write_tick(tick)
            self.wall_end = tick.end
            if self._route_end():
                reason = "routeEnd"
                break
            if tick.frame + 1 >= self.end_frame:
                reason = "runDuration"
                break
            expected = tick.frame + 1

        self.stop_reason = reason
        self.side_log.write("stop", self.summary(pending=True))

    def _route_end(self) -> bool:
        transform = self.hero.get_transform()
        x_map, y_map = carla_to_map_xy(transform.location.x, transform.location.y)
        return math.hypot(x_map - self.route.destination[0],
                          y_map - self.route.destination[1]) <= ROUTE_END_M

    # ---------------------------------------------------------------- summary
    def summary(self, pending: bool = False) -> dict:
        ticks = len(self.tick_durations)
        sim_seconds = ticks * STEP_S
        wall = 0.0
        if self.wall_start is not None:
            wall = max(0.0, (self.wall_end if self.wall_end is not None else self.clock())
                       - self.wall_start)
        durations = self.tick_durations
        return {
            "component": COMPONENT,
            "host": HOST,
            "done": not pending,
            "stopReason": self.stop_reason,
            "handoverFrame": self.handover_frame,
            "firstFrame": self.first_frame,
            "lastFrame": self.last_frame,
            "endFrame": self.end_frame,
            "ticks": ticks,
            "simSeconds": round(sim_seconds, 6),
            "wallSeconds": round(wall, 6),
            "realTimeFactor": round(sim_seconds / wall, 6) if wall > 0.0 else None,
            "lateTicks": self.pacer.late_ticks,
            "scheduleSlips": self.pacer.schedule_slips,
            "maxLatenessMonoNs": int(round(self.pacer.max_lateness_s * 1e9)),
            "maxSlipMonoNs": int(round(self.pacer.max_slip_s * 1e9)),
            "meanTickDurationMonoNs": (int(round(sum(durations) / len(durations) * 1e9))
                                       if durations else None),
            "maxTickDurationMonoNs": int(round(max(durations) * 1e9)) if durations else None,
            "frameSkips": self.frame_skips,
            "lateSensorEvents": self.late_sensor_events,
            "setup": dict(self.setup_info),
            "yawRateCheck": self._yaw_check_summary(),
            "map": self.args.map,
            "route": str(self.route.path),
            "routeSha256": self.route.sha256,
            "destination": list(self.route.destination),
            "warmup": {"enabled": frames_of(self.args.warmup_s) > 0,
                       "frames": frames_of(self.args.warmup_s),
                       "speedKmh": float(self.args.warmup_speed_kmh),
                       "path": "trafficManager", "laneChanges": False,
                       "ignoreLightsPercentage": 100.0},
            "cameras": [{"name": c.name, "actor_id": c.actor_id(), "width": c.width,
                         "height": c.height, "fov": as_num(c.fov),
                         "destroyedAtFrame": c.destroyed_at_frame} for c in self.cameras],
            "faults": [f.describe() for f in self.faults],
        }

    def _yaw_check_summary(self) -> dict:
        n = self._yaw_check["compared"]
        diffs = sorted(self._yaw_check["diffs"])
        return {"ticksCompared": n,
                "minDerivedRateRadS": YAW_CHECK_MIN_RAD_S,
                "signAgreement": round(self._yaw_check["agree"] / n, 6) if n else None,
                "medianAbsDiffRadS": round(diffs[len(diffs) // 2], 6) if diffs else None}

    def write_summary(self) -> None:
        path = self.run_dir / SUMMARY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.summary(), indent=1) + "\n")

    # --------------------------------------------------------------- teardown
    def teardown(self) -> None:
        """Restore the settings, TM off, stop and destroy every actor (idempotent)."""
        with self._teardown_lock:
            if self._torn_down:
                return
            self._torn_down = True

        if self.hero is not None:
            try:
                self.hero.set_autopilot(False, int(self.args.tm_port))
            except Exception:  # noqa: BLE001
                pass
            self.autopilot = False
        self.restore_settings()

        for sensor in list(self.extra_sensors) + [c.actor for c in self.cameras]:
            try:
                sensor.stop()
            except Exception:  # noqa: BLE001 - not every actor listens
                pass
        for actor in self._spawned:
            try:
                actor.destroy()
            except Exception:  # noqa: BLE001
                pass
        self._spawned.clear()
        self.extra_sensors.clear()

        for writer in (self.injection_log, self.world_log, self.side_log):
            try:
                writer.close()
            except Exception:  # noqa: BLE001
                pass


# ------------------------------------------------------------------------ CLI


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="world_side.py",
        description="CARLA world side of the closed-loop driving bench: paced "
                    "synchronous ticks, hero + six-camera rig, autopilot warm-up, "
                    "announced handover, world-side faults, C1 world records.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2000)
    parser.add_argument("--tm-port", type=int, default=8000)
    parser.add_argument("--map", default="Town10HD_Opt")
    parser.add_argument("--route", required=True, help="ICD section 9 route JSON")
    parser.add_argument("--profile", required=True, help="camera calibration JSON")
    parser.add_argument("--rig-path", default=None,
                        help="path to de4sdv_planner/rig.py (default: import it)")
    parser.add_argument("--vehicle-config", default=None,
                        help="vehicle configuration JSON (ICD section 5); its "
                             "vehicle_blueprint names the hero's blueprint")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--front-width", type=int, default=1920)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--warmup-s", type=float, default=0.0,
                        help="seconds of Traffic Manager autopilot before the handover. 0 "
                             "(default): no autopilot; the agent drives from the first run "
                             "tick. REQ-DRIVING-011 allows the autopilot no control at any time "
                             "of the run, so a run with a warm-up fails VC-DRIVING-011")
    parser.add_argument("--run-s", type=float, default=120.0)
    parser.add_argument("--warmup-speed-kmh", type=float, default=30.0)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--spawn-index", type=int, default=None)
    parser.add_argument("--fault", action="append", default=[], metavar="KIND",
                        help="repeatable; camera_stop:<slot>@<seconds after handover>, "
                             "run_end_brake")
    parser.add_argument("--dry-run", action="store_true",
                        help="print the plan and spawn nothing")
    parser.add_argument("--client-timeout", type=float, default=60.0)
    parser.add_argument("--no-collision-sensors", dest="collision_sensors",
                        action="store_false", help="skip the collision and lane sensors")
    return parser


def print_plan(args: argparse.Namespace) -> int:
    route = Route(args.route)
    if route.map_name and last_path_element(route.map_name) != last_path_element(args.map):
        raise BenchError(f"map mismatch: the route names {route.map_name!r}, "
                         f"--map is {args.map!r}")
    profile = Path(args.profile)
    if not profile.is_file():
        raise BenchError(f"camera profile not found: {profile}")
    rig = load_rig_module(args.rig_path)
    _payload, cams = rig.load_profile(str(profile))
    if [c.get("slot") for c in cams] != SLOTS:
        raise BenchError(f"camera profile slots are {[c.get('slot') for c in cams]}, "
                         f"expected {SLOTS}")
    faults = [parse_fault(text) for text in (args.fault or [])]
    warmup_frames = frames_of(args.warmup_s)
    run_frames = frames_of(args.run_s)

    print("world side plan (dry run; nothing is spawned, no CARLA client is created)")
    print(f"  carla              {args.host}:{args.port}  traffic manager port {args.tm_port}")
    print(f"  map                {args.map} (loaded only if the current map differs)")
    print(f"  host / clock       simulator; simulation time = frame x 100 ms; "
          f"one tick per {STEP_S:g} s of wall time")
    print(f"  route              {route.path} ({len(route.waypoints)} waypoints, "
          f"sha256 {route.sha256[:16]}...)")
    print(f"  route map field    {route.map_name or '(none)'}")
    x, y, heading = route.start
    cx, cy = map_to_carla_xy(x, y)
    print(f"  route start        map ({x:.3f}, {y:.3f}) yaw {heading:.4f} rad "
          f"-> carla ({cx:.3f}, {cy:.3f}) yaw {math.degrees(map_to_carla_heading(heading)):.3f} deg")
    print(f"  route destination  map ({route.destination[0]:.3f}, {route.destination[1]:.3f})")
    if args.spawn_index is None:
        print(f"  spawn point        nearest to the route start, must be within "
              f"{SPAWN_MATCH_M:g} m (resolved at connect)")
    else:
        print(f"  spawn point        index {args.spawn_index} (validated at connect)")
    print(f"  warm-up            {warmup_frames} ticks ({args.warmup_s:g} s) on the traffic "
          f"manager at {args.warmup_speed_kmh:g} km/h, no lane changes, lights ignored")
    print(f"  handover frame     first tick frame + {warmup_frames}  (F_h)")
    print(f"  handover marker    actor role_name '{MARKER_PREFIX}<F_h>' at (0, 0, -500)")
    print(f"  run                {run_frames} ticks ({args.run_s:g} s) after F_h")
    print(f"  run end            after the run duration, within {ROUTE_END_M:g} m of the "
          f"destination, or on SIGINT")
    print(f"  run dir            {args.run_dir}")
    print(f"    {WORLD_LOG}")
    print(f"    {SIDE_LOG}")
    print(f"    {INJECTION_LOG}")
    print(f"    {SUMMARY}")
    print(f"  cameras            front at {args.front_width} px, others at {args.width} px")
    for i, cam in enumerate(cams):
        width = args.front_width if i == 0 else args.width
        W, H, _f, hfov = rig.render_spec(cam, width)
        print(f"    cam_{cam['slot']:<11} {W}x{H}  fov {hfov:.4f} deg")
    for fault in faults:
        frame = f"F_h + {frames_of(fault.after_s)}" if fault.slot else "no world-side effect"
        print(f"  fault              {fault.text}  -> {frame}")
    return 0


def write_startup_error(run_dir: str, reason: str) -> None:
    """A failure before the tool exists still leaves an 'error' record (R10)."""
    try:
        writer = JsonlWriter(Path(run_dir) / SIDE_LOG)
        writer.write("error", {"reason": reason})
        writer.close()
    except OSError:
        pass


def install_stop_handlers(stop_requested: threading.Event) -> list[int]:
    """SIGINT/SIGTERM request a clean stop; the loop ends after the current tick."""
    signals = []

    def _handler(_signum, _frame):
        stop_requested.set()

    for name in ("SIGINT", "SIGTERM"):
        number = getattr(signal, name, None)
        if number is None:
            continue
        try:
            signal.signal(number, _handler)
            signals.append(number)
        except (ValueError, OSError):   # not the main thread
            pass
    return signals


def main(argv: Iterable[str] | None = None, *,
         client_factory: Callable[[str, int], Any] | None = None,
         clock: Callable[[], float] = time.monotonic,
         sleep: Callable[[float], None] = time.sleep,
         stop_requested: threading.Event | None = None,
         install_signals: bool = True) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.width <= 0 or args.front_width <= 0:
        print("world side: --width and --front-width must be positive", file=sys.stderr)
        return 2

    if args.dry_run:
        try:
            return print_plan(args)
        except BenchError as exc:
            print(f"world side: {exc}", file=sys.stderr)
            return 1

    stop_requested = stop_requested or threading.Event()
    if install_signals:
        install_stop_handlers(stop_requested)

    Path(args.run_dir).mkdir(parents=True, exist_ok=True)
    tool: WorldSide | None = None
    code = 0
    try:
        tool = WorldSide(args, client_factory=client_factory, clock=clock, sleep=sleep,
                         rig_module=load_rig_module(args.rig_path),
                         stop_requested=stop_requested)
        tool.start()
        tool.run()
    except KeyboardInterrupt:
        if tool is not None:
            tool.stop_reason = "interrupt"
            tool.wall_end = clock()
            tool.side_log.write("stop", tool.summary(pending=True))
        code = 0
    except BenchError as exc:
        code = 1
        if tool is not None:
            tool.stop_reason = "error"
            tool.side_log.write("error", {"reason": str(exc)})
        else:
            write_startup_error(args.run_dir, str(exc))
        print(f"world side: {exc}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 - loud, teardown first
        code = 1
        reason = f"{type(exc).__name__}: {exc}"
        if tool is not None:
            tool.stop_reason = "error"
            tool.side_log.write("error", {"reason": reason})
        else:
            write_startup_error(args.run_dir, reason)
        print(f"world side: {reason}", file=sys.stderr)
    finally:
        if tool is not None:
            if tool.stop_reason is None:
                tool.stop_reason = "error"
            tool.teardown()
            tool.write_summary()

    return code


if __name__ == "__main__":
    sys.exit(main())
