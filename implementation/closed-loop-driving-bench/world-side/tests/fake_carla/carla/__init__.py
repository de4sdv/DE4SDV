"""A fake ``carla`` module for the world-side tests (CARLA 0.9.16 surface).

Only what world_side.py uses, plus what the tests inspect: actors and their
blueprints, synchronous settings, spawn points, the Traffic Manager, sensor
callbacks and an injected clock. ``Transform.get_matrix()`` follows CARLA's
formula (same as agent/scripts/make_fake_rig.py), so the rig geometry is real.

Not a simulator: vehicles do not move unless a test installs ``motion_hook``.
"""

from __future__ import annotations

import fnmatch
import math

__version__ = "0.9.16-fake"


# --------------------------------------------------------------------- values


class Location:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __sub__(self, other):
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __add__(self, other):
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def distance(self, other) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2
                         + (self.z - other.z) ** 2)

    def __repr__(self) -> str:
        return f"Location(x={self.x!r}, y={self.y!r}, z={self.z!r})"


class Vector3D:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __repr__(self) -> str:
        return f"Vector3D(x={self.x!r}, y={self.y!r}, z={self.z!r})"


class Rotation:
    def __init__(self, pitch: float = 0.0, yaw: float = 0.0, roll: float = 0.0):
        self.pitch = float(pitch)
        self.yaw = float(yaw)
        self.roll = float(roll)

    def __repr__(self) -> str:
        return f"Rotation(pitch={self.pitch!r}, yaw={self.yaw!r}, roll={self.roll!r})"


class Transform:
    def __init__(self, location=None, rotation=None):
        self.location = location if location is not None else Location()
        self.rotation = rotation if rotation is not None else Rotation()

    def get_matrix(self):
        """UE local->world matrix, degrees (CARLA's Transform::GetMatrix)."""
        x, y, z = self.location.x, self.location.y, self.location.z
        cy, sy = math.cos(math.radians(self.rotation.yaw)), math.sin(math.radians(self.rotation.yaw))
        cr, sr = math.cos(math.radians(self.rotation.roll)), math.sin(math.radians(self.rotation.roll))
        cp, sp = math.cos(math.radians(self.rotation.pitch)), math.sin(math.radians(self.rotation.pitch))
        return [[cp * cy, cy * sp * sr - sy * cr, -cy * sp * cr - sy * sr, x],
                [cp * sy, sy * sp * sr + cy * cr, -sy * sp * cr + cy * sr, y],
                [sp, -cp * sr, cp * cr, z],
                [0.0, 0.0, 0.0, 1.0]]

    def __repr__(self) -> str:
        return f"Transform({self.location!r}, {self.rotation!r})"


class VehicleControl:
    def __init__(self, throttle=0.0, steer=0.0, brake=0.0, hand_brake=False,
                 reverse=False, manual_gear_shift=False, gear=1):
        self.throttle = float(throttle)
        self.steer = float(steer)
        self.brake = float(brake)
        self.hand_brake = bool(hand_brake)
        self.reverse = bool(reverse)
        self.manual_gear_shift = bool(manual_gear_shift)
        self.gear = int(gear)


class AttachmentType:
    Rigid = 0
    SpringArm = 1
    SpringArmGhost = 2


class LaneType:
    Any = 0
    Driving = 1


class WeatherParameters:
    ClearNoon = "ClearNoon"


class Timestamp:
    def __init__(self, frame: int = 0, elapsed_seconds: float = 0.0):
        self.frame = int(frame)
        self.elapsed_seconds = float(elapsed_seconds)


class Snapshot:
    def __init__(self, frame: int = 0, elapsed_seconds: float = 0.0):
        self.frame = int(frame)
        self.timestamp = Timestamp(frame, elapsed_seconds)


# ------------------------------------------------------------------- settings


class Settings:
    def __init__(self, synchronous_mode: bool = False, fixed_delta_seconds=None,
                 no_rendering_mode: bool = False, substepping: bool = False,
                 max_substep_delta_time: float = 0.01, max_substeps: int = 10):
        self.synchronous_mode = bool(synchronous_mode)
        self.fixed_delta_seconds = fixed_delta_seconds
        self.no_rendering_mode = bool(no_rendering_mode)
        self.substepping = bool(substepping)
        self.max_substep_delta_time = float(max_substep_delta_time)
        self.max_substeps = int(max_substeps)

    def copy(self) -> "Settings":
        return Settings(self.synchronous_mode, self.fixed_delta_seconds,
                        self.no_rendering_mode, self.substepping,
                        self.max_substep_delta_time, self.max_substeps)

    def as_dict(self) -> dict:
        return {"synchronous_mode": self.synchronous_mode,
                "fixed_delta_seconds": self.fixed_delta_seconds,
                "no_rendering_mode": self.no_rendering_mode}


# ----------------------------------------------------------------- blueprints


class Blueprint:
    def __init__(self, blueprint_id: str, attributes: dict | None = None):
        self.id = blueprint_id
        self.tags: list[str] = []
        self._attributes = dict(attributes or {})
        for key in ("role_name", "image_size_x", "image_size_y", "fov", "sensor_tick"):
            self._attributes.setdefault(key, "")

    def set_attribute(self, key: str, value) -> None:
        self._attributes[key] = str(value)

    def get_attribute(self, key: str):
        return self._attributes.get(key)

    def has_attribute(self, key: str) -> bool:
        return key in self._attributes

    def copy(self) -> "Blueprint":
        out = Blueprint(self.id, self._attributes)
        out.tags = list(self.tags)
        return out

    def __repr__(self) -> str:
        return f"Blueprint({self.id!r})"


class BlueprintLibrary:
    def __init__(self, blueprints):
        self._blueprints = list(blueprints)

    def find(self, blueprint_id: str):
        for blueprint in self._blueprints:
            if blueprint.id == blueprint_id:
                return blueprint.copy()
        # As CARLA 0.9.16: the binding calls BlueprintLibrary::at, which throws std::out_of_range,
        # raised in Python as IndexError. find() never returns None.
        raise IndexError(f"blueprint '{blueprint_id}' not found")

    def filter(self, pattern: str):
        return [b.copy() for b in self._blueprints if fnmatch.fnmatchcase(b.id, pattern)]

    def __iter__(self):
        return iter(self._blueprints)


def default_blueprints() -> list[Blueprint]:
    return [Blueprint("vehicle.lincoln.mkz_2020"),
            Blueprint("vehicle.tesla.model3"),
            Blueprint("sensor.camera.rgb"),
            Blueprint("sensor.other.collision"),
            Blueprint("sensor.other.lane_invasion"),
            Blueprint("static.prop.trafficcone01"),
            Blueprint("static.prop.streetbarrier"),
            Blueprint("static.prop.constructioncone")]


# --------------------------------------------------------------------- actors


class ActorList(list):
    def filter(self, pattern: str) -> "ActorList":
        return ActorList(a for a in self if fnmatch.fnmatchcase(a.type_id, pattern))


class Wheel:
    def __init__(self, position: Location, radius: float = 35.0):
        self.position = position
        self.radius = float(radius)


class PhysicsControl:
    def __init__(self, wheels):
        self.wheels = list(wheels)


class Actor:
    def __init__(self, world, actor_id: int, type_id: str, transform: Transform,
                 attributes: dict | None = None, parent=None):
        self._world = world
        self.id = int(actor_id)
        self.type_id = type_id
        self.attributes = dict(attributes or {})
        self.transform = Transform(transform.location, transform.rotation)
        self.parent = parent
        self._alive = True
        self._velocity = Vector3D()
        self._acceleration = Vector3D()
        self._angular_velocity = Vector3D()
        self._control = VehicleControl()
        self.autopilot = False
        self.autopilot_calls: list[tuple] = []
        self.listeners: list = []
        self.stopped = False
        # As CARLA in synchronous mode: the client's actor state comes from the world snapshot, and
        # a new actor is in no snapshot before the next tick, so its transform reads as zero until
        # then. get_physics_control is an RPC and answers from the server at once (world wheels).
        self.spawned_at_frame = int(getattr(world, "frame", 0))

    def _simulated(self) -> bool:
        return self._world.frame > self.spawned_at_frame

    # -- state
    @property
    def is_alive(self) -> bool:
        """A bool property in the real API (`actor.is_alive`), not a method."""
        return bool(self._alive)

    def get_transform(self) -> Transform:
        if not self._simulated():
            return Transform()
        return Transform(self.transform.location, self.transform.rotation)

    def set_transform(self, transform) -> None:
        self.transform = Transform(transform.location, transform.rotation)

    def get_location(self) -> Location:
        if not self._simulated():
            return Location()
        loc = self.transform.location
        return Location(loc.x, loc.y, loc.z)

    def get_velocity(self) -> Vector3D:
        return Vector3D(self._velocity.x, self._velocity.y, self._velocity.z)

    def get_acceleration(self) -> Vector3D:
        return Vector3D(self._acceleration.x, self._acceleration.y, self._acceleration.z)

    def get_angular_velocity(self) -> Vector3D:
        return Vector3D(self._angular_velocity.x, self._angular_velocity.y,
                        self._angular_velocity.z)

    def get_control(self) -> VehicleControl:
        return self._control

    # -- vehicle API (harmless on a static prop)
    def set_autopilot(self, enabled: bool = True, tm_port: int = 8000) -> None:
        self.autopilot = bool(enabled)
        self.autopilot_calls.append((bool(enabled), int(tm_port), self._world.frame))

    def get_autopilot(self) -> bool:
        return bool(self.autopilot)

    def get_physics_control(self) -> PhysicsControl:
        matrix = self.transform.get_matrix()
        wheels = []
        # FL, FR, RL, RR in vehicle-local metres; world positions as CARLA reports them
        for lx, ly, lz in ((1.40, -0.80, 0.35), (1.40, 0.80, 0.35),
                           (-1.45, -0.80, 0.35), (-1.45, 0.80, 0.35)):
            wx = matrix[0][0] * lx + matrix[0][1] * ly + matrix[0][2] * lz + matrix[0][3]
            wy = matrix[1][0] * lx + matrix[1][1] * ly + matrix[1][2] * lz + matrix[1][3]
            wz = matrix[2][0] * lx + matrix[2][1] * ly + matrix[2][2] * lz + matrix[2][3]
            wheels.append(Wheel(Location(wx, wy, wz), 35.0))
        return PhysicsControl(wheels)

    def set_simulate_physics(self, enabled: bool = True) -> None:
        self.simulate_physics = bool(enabled)

    # -- lifecycle
    def destroy(self) -> None:
        if not self._alive:
            return
        self._alive = False
        self._world.log.append(("destroy", self.id, self._world.frame))
        self._world.remove(self)


class Sensor(Actor):
    def listen(self, callback) -> None:
        self.listeners.append(callback)

    def stop(self) -> None:
        self.stopped = True
        self.listeners.clear()
        self._world.log.append(("stop", self.id, self._world.frame))


# ----------------------------------------------------------------------- maps


class Waypoint:
    def __init__(self, transform: Transform, road_id: int = 296, lane_id: int = -1,
                 lane_width: float = 3.5, is_junction: bool = False):
        self.transform = transform
        self.road_id = int(road_id)
        self.lane_id = int(lane_id)
        self.lane_width = float(lane_width)
        self.is_junction = bool(is_junction)

    def get_right_vector(self):
        yaw = math.radians(self.transform.rotation.yaw)
        return Vector3D(-math.sin(yaw), math.cos(yaw), 0.0)


class Map:
    """A flat map: spawn points on a grid, one lane 1 m to the left of the query."""

    def __init__(self, name: str = "Carla/Maps/Town10HD_Opt"):
        self.name = name
        self.spawn_transforms = [Transform(Location(x, 0.0, 0.0), Rotation(0.0, 0.0, 0.0))
                                 for x in (0.0, 10.0, 20.0, 30.0)]
        self.lane_offset_m = 1.0      # waypoint centre sits 1 m at -y of the query
        self.waypoint_calls: list = []

    def get_spawn_points(self) -> list:
        return [Transform(t.location, t.rotation) for t in self.spawn_transforms]

    def get_waypoint(self, location, project_to_road: bool = True, lane_type=None):
        self.waypoint_calls.append((location.x, location.y, project_to_road))
        centre = Location(location.x, location.y - self.lane_offset_m, 0.0)
        return Waypoint(Transform(centre, Rotation(0.0, 0.0, 0.0)))


# ------------------------------------------------------------------- the world


class World:
    def __init__(self, client, clock=None, map_name: str = "Carla/Maps/Town10HD_Opt"):
        self.client = client
        self.clock = clock
        self.settings = Settings()
        self.map = Map(map_name)
        self._frame = 0
        self._next_id = 100
        self._actors: dict[int, Actor] = {}
        self._blueprints = BlueprintLibrary(default_blueprints())
        self.log: list[tuple] = []
        self.apply_settings_calls: list[dict] = []
        self.spawned: list[dict] = []
        self.tick_cost_s = 0.0
        self.motion_hook = None
        self.spawn_failures: set[str] = set()
        self.queued_events: dict[int, list[tuple]] = {}
        self.tick_callbacks: list = []
        self.snapshot = Snapshot(0, 0.0)

    # -- settings
    def get_settings(self) -> Settings:
        return self.settings.copy()

    def apply_settings(self, settings) -> None:
        self.settings = settings.copy()
        self.apply_settings_calls.append(self.settings.as_dict())
        self.log.append(("settings", bool(self.settings.synchronous_mode)))

    # -- world
    @property
    def frame(self) -> int:
        return self._frame

    def get_map(self) -> Map:
        return self.map

    def get_blueprint_library(self) -> BlueprintLibrary:
        return self._blueprints

    def get_actors(self) -> ActorList:
        return ActorList(self._actors.values())

    def get_snapshot(self) -> Snapshot:
        return self.snapshot

    def on_tick(self, callback) -> None:
        self.tick_callbacks.append(callback)

    def set_weather(self, weather) -> None:
        self.weather = weather

    def remove(self, actor) -> None:
        self._actors.pop(actor.id, None)

    # -- spawning
    def spawn_actor(self, blueprint, transform, attach_to=None):
        if blueprint.id in self.spawn_failures:
            raise RuntimeError(f"failed to spawn {blueprint.id}")
        actor_id = self._next_id
        self._next_id += 1
        if blueprint.id.startswith("sensor."):
            actor = Sensor(self, actor_id, blueprint.id, transform,
                           attributes=dict(blueprint._attributes), parent=attach_to)
        else:
            actor = Actor(self, actor_id, blueprint.id, transform,
                          attributes=dict(blueprint._attributes), parent=attach_to)
        self._actors[actor_id] = actor
        self.spawned.append({"id": actor_id, "type_id": blueprint.id,
                             "transform": Transform(transform.location, transform.rotation),
                             "attach_to": getattr(attach_to, "id", None),
                             "attributes": dict(blueprint._attributes)})
        return actor

    def try_spawn_actor(self, blueprint, transform, attach_to=None):
        try:
            return self.spawn_actor(blueprint, transform, attach_to=attach_to)
        except RuntimeError:
            return None

    # -- ticking
    def queue_event(self, frame: int, kind: str, payload: dict) -> None:
        self.queued_events.setdefault(int(frame), []).append((kind, payload))

    def tick(self) -> int:
        if self.tick_cost_s and self.clock is not None:
            self.clock.advance(self.tick_cost_s)
        self._frame += 1
        self.log.append(("tick", self._frame))
        if self.motion_hook is not None:
            self.motion_hook(self, self._frame)
        for kind, payload in self.queued_events.pop(self._frame, []):
            for actor in list(self._actors.values()):
                if actor.type_id.endswith("collision" if kind == "collision"
                                          else "lane_invasion"):
                    event = _SensorEvent(self._frame, payload)
                    for callback in list(actor.listeners):
                        callback(event)
        self.snapshot = Snapshot(self._frame, self._frame * 0.1)
        for callback in list(self.tick_callbacks):
            callback(self.snapshot)
        return self._frame


class _OtherActor:
    def __init__(self, type_id: str, actor_id: int = 9001):
        self.type_id = type_id
        self.id = actor_id


class _Marking:
    def __init__(self, kind: str):
        self.type = kind


class _SensorEvent:
    def __init__(self, frame: int, payload: dict):
        self.frame = int(frame)
        self.other_actor = _OtherActor(payload.get("other_actor", "vehicle.tesla.model3"),
                                       payload.get("other_actor_id", 9001))
        self.normal_impulse = Vector3D(*payload.get("normal_impulse", (0.0, 0.0, 0.0)))
        self.crossed_lane_markings = [_Marking(m) for m in payload.get("markings", ["Solid"])]


# ----------------------------------------------------------------- traffic mgr


class TrafficManager:
    def __init__(self, port: int = 8000):
        self.port = int(port)
        self.calls: list[tuple] = []
        self.synchronous = False
        self.path: list = []
        self.desired_speed_kmh = None

    def set_synchronous_mode(self, enabled: bool) -> None:
        self.synchronous = bool(enabled)
        self.calls.append(("set_synchronous_mode", bool(enabled)))

    def set_random_device_seed(self, seed: int) -> None:
        self.calls.append(("set_random_device_seed", int(seed)))

    def set_path(self, actor, path) -> None:
        self.path = list(path)
        self.calls.append(("set_path", getattr(actor, "id", None), len(self.path)))

    def set_desired_speed(self, actor, speed_kmh: float) -> None:
        self.desired_speed_kmh = float(speed_kmh)
        self.calls.append(("set_desired_speed", getattr(actor, "id", None), float(speed_kmh)))

    def auto_lane_change(self, actor, enabled: bool) -> None:
        self.calls.append(("auto_lane_change", getattr(actor, "id", None), bool(enabled)))

    def ignore_lights_percentage(self, actor, percent: float) -> None:
        self.calls.append(("ignore_lights_percentage", getattr(actor, "id", None), float(percent)))

    def vehicle_percentage_speed_difference(self, actor, percent: float) -> None:
        self.calls.append(("vehicle_percentage_speed_difference", getattr(actor, "id", None),
                           float(percent)))

    def names(self) -> list[str]:
        return [call[0] for call in self.calls]


# ---------------------------------------------------------------------- client


class Client:
    def __init__(self, host: str, port: int = 2000, *,
                 clock=None, map_name: str = "Carla/Maps/Town10HD_Opt"):
        self.host = host
        self.port = int(port)
        self.timeout = 5.0
        self.clock = clock
        self.world = World(self, clock=clock, map_name=map_name)
        self.load_calls: list[str] = []
        self.traffic_managers: dict[int, TrafficManager] = {}
        self.load_failure: str | None = None

    def set_timeout(self, seconds: float) -> None:
        self.timeout = float(seconds)

    def get_world(self) -> World:
        return self.world

    def load_world(self, map_name: str) -> World:
        if self.load_failure:
            raise RuntimeError(self.load_failure)
        self.load_calls.append(map_name)
        short = map_name.split("/")[-1]
        self.world = World(self, clock=self.clock, map_name=f"Carla/Maps/{short}")
        return self.world

    def get_trafficmanager(self, port: int = 8000) -> TrafficManager:
        tm = self.traffic_managers.get(int(port))
        if tm is None:
            tm = TrafficManager(int(port))
            self.traffic_managers[int(port)] = tm
        return tm

    def get_available_maps(self) -> list[str]:
        return ["Carla/Maps/Town10HD_Opt", "Carla/Maps/Town01"]
