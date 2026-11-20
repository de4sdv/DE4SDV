"""A fake ``carla`` module for the world-side tests (the CARLA 1.0 surface that the world side uses).

Not a simulator. It keeps one shared server state and gives each ``Client`` its own handles, so a test can
tell which client applied a control: the world side, or a stand-in for the actuation adapter. What it models:

- synchronous mode with ``fixed_delta_seconds``; the snapshot's ``elapsed_seconds`` advances by the step;
- a sensor's ``sensor_tick``: a camera with ``sensor_tick`` 0.1 at a step of 0.05 delivers an image every
  second tick, stamped with the frame and the elapsed time of the tick it was rendered in;
- ``apply_ackermann_control`` (steer rad positive right, speed, acceleration, jerk, steer_speed) moving a
  vehicle by a kinematic bicycle: the speed moves toward the commanded speed at ``|acceleration|`` per
  second, and the yaw rate is ``v * tan(steer) / wheelbase`` (CARLA yaw is clockwise seen from above);
- ``enable_constant_velocity`` (a velocity in the actor's local frame, m/s, as CARLA's Actor.cpp): the actor then
  moves at that velocity every tick, along its heading, until ``disable_constant_velocity``;
- a collision event when two vehicle bounding boxes overlap along a straight road;
- a map of straight lanes along +x (two driving lanes in one direction), with waypoints, ``next`` and a
  junction zone, and textures applied to actors (recorded, not rendered);
- with ``_Server.actor_list_at_last_tick`` set (or FAKE_CARLA_LAST_TICK_ACTORS=1), a synchronous world that is not
  ticking: a client's ``get_actors()`` and ``get_snapshot()`` give the actors of the last tick, so an actor spawned
  since (by any client, the caller's own camera included) appears only after the next tick. The real CARLA 1.0
  server did this in session 20261119T174606Z: the chase recorder's own camera (157) was missing from its actor list
  while the world side waited for the go without ticking. Each tick's ``WorldSnapshot`` holds that tick's actors
  (``find``, ``has_actor``, ``len``, iteration). A client that connected after the last tick lists no actor at all
  until the next one: on the real server (G4, 2026-11-19) a second client connecting in such a pause listed 0 actors
  and a snapshot of frame 0 for 85 s, then 98 actors at the first tick after the go. Off by default, so the world
  side's own tests keep the live list;
- the map read of the real server (lane A2, G4, 2026-11-20; ``tests/data/town06_opt_g4_read.json``): the 83
  ``static.prop.*`` blueprints the server lists (a name it does not list is refused, as ``find`` refuses any unknown
  blueprint), and Town06_Opt's own OpenDRIVE (``Map.to_opendrive()``, ``tests/data/town06_opt_g4.xodr.xz``, the bytes
  of sha256 a90b6131...); a map without a replayed read refuses ``to_opendrive()`` rather than invent one;
- ``_SHARED_SERVER``: when a test sets it, ``Client(host, port)`` without ``_server`` joins that server, so a
  program that creates its own client (the chase recorder) shares the world with the test's world side.

The API names follow the Python bindings of CARLA at 14ac3b1a502da45a44506cb2ed82ab800f1baf4c
(PythonAPI/carla/src/World.cpp, Actor.cpp, Map.cpp, Control.cpp, read on 2026-11-18).
"""

from __future__ import annotations

import fnmatch
import json
import lzma
import math
import os
from pathlib import Path

__version__ = "1.0-fake"


# --------------------------------------------------------------------- values


class Location:
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0):
        self.x, self.y, self.z = float(x), float(y), float(z)

    def distance(self, other) -> float:
        return math.sqrt((self.x - other.x) ** 2 + (self.y - other.y) ** 2 + (self.z - other.z) ** 2)

    def __repr__(self) -> str:
        return f"Location(x={self.x!r}, y={self.y!r}, z={self.z!r})"


class Vector3D(Location):
    pass


class Rotation:
    def __init__(self, pitch: float = 0.0, yaw: float = 0.0, roll: float = 0.0):
        self.pitch, self.yaw, self.roll = float(pitch), float(yaw), float(roll)

    def get_forward_vector(self) -> Vector3D:
        cp, sp = math.cos(math.radians(self.pitch)), math.sin(math.radians(self.pitch))
        cy, sy = math.cos(math.radians(self.yaw)), math.sin(math.radians(self.yaw))
        return Vector3D(cp * cy, cp * sy, sp)

    def get_right_vector(self) -> Vector3D:
        yaw = math.radians(self.yaw)
        return Vector3D(-math.sin(yaw), math.cos(yaw), 0.0)


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

    def get_forward_vector(self) -> Vector3D:
        return self.rotation.get_forward_vector()


class BoundingBox:
    def __init__(self, location: Location, extent: Vector3D):
        self.location = location
        self.extent = extent


class VehicleControl:
    def __init__(self, throttle=0.0, steer=0.0, brake=0.0, hand_brake=False, reverse=False,
                 manual_gear_shift=False, gear=0):
        self.throttle, self.steer, self.brake = float(throttle), float(steer), float(brake)
        self.hand_brake, self.reverse = bool(hand_brake), bool(reverse)
        self.manual_gear_shift, self.gear = bool(manual_gear_shift), int(gear)


class VehicleAckermannControl:
    def __init__(self, steer=0.0, steer_speed=0.0, speed=0.0, acceleration=0.0, jerk=0.0):
        self.steer, self.steer_speed = float(steer), float(steer_speed)
        self.speed, self.acceleration, self.jerk = float(speed), float(acceleration), float(jerk)


class AckermannControllerSettings:
    """CARLA 1.0's ``carla.AckermannControllerSettings``. The defaults are what the real server read back on a fresh
    vehicle.lincoln.mkz (the G4 read of 2026-11-20, s1-map/FACTS.md)."""

    FIELDS = ("speed_kp", "speed_ki", "speed_kd", "accel_kp", "accel_ki", "accel_kd")
    DEFAULTS = (0.15, 0.0, 0.25, 0.01, 0.0, 0.01)

    def __init__(self, speed_kp=0.15, speed_ki=0.0, speed_kd=0.25, accel_kp=0.01, accel_ki=0.0, accel_kd=0.01):
        self.speed_kp, self.speed_ki, self.speed_kd = float(speed_kp), float(speed_ki), float(speed_kd)
        self.accel_kp, self.accel_ki, self.accel_kd = float(accel_kp), float(accel_ki), float(accel_kd)


class Color:
    def __init__(self, r=0, g=0, b=0, a=255):
        self.r, self.g, self.b, self.a = int(r), int(g), int(b), int(a)


class TextureColor:
    def __init__(self, width: int, height: int):
        self.width, self.height = int(width), int(height)
        self._px: dict[tuple[int, int], Color] = {}
        self.set_calls = 0

    def set(self, x: int, y: int, color: Color) -> None:
        if not (0 <= x < self.width and 0 <= y < self.height):
            raise IndexError("texel outside the texture")
        self._px[(int(x), int(y))] = color
        self.set_calls += 1

    def get(self, x: int, y: int) -> Color:
        return self._px.get((int(x), int(y)), Color(0, 0, 0, 0))


class MaterialParameter:
    Normal = "Normal"
    AO_Roughness_Metallic_Emissive = "AO_Roughness_Metallic_Emissive"
    Diffuse = "Diffuse"
    Emissive = "Emissive"


class AttachmentType:
    Rigid = 0
    SpringArm = 1
    SpringArmGhost = 2


class LaneType:
    Any = -2
    Driving = 2


class ColorConverter:
    Raw = 0


class Timestamp:
    def __init__(self, frame: int, elapsed_seconds: float):
        self.frame, self.elapsed_seconds = int(frame), float(elapsed_seconds)


class ActorSnapshot:
    def __init__(self, actor_id: int):
        self.id = int(actor_id)


class WorldSnapshot:
    def __init__(self, frame: int, elapsed_seconds: float, actor_ids=()):
        self.frame = int(frame)
        self.timestamp = Timestamp(frame, elapsed_seconds)
        self._ids = tuple(int(i) for i in actor_ids)

    def find(self, actor_id: int):
        return ActorSnapshot(actor_id) if int(actor_id) in self._ids else None

    def has_actor(self, actor_id: int) -> bool:
        return int(actor_id) in self._ids

    def __len__(self) -> int:
        return len(self._ids)

    def __iter__(self):
        return iter([ActorSnapshot(i) for i in self._ids])


class WorldSettings:
    def __init__(self, synchronous_mode=False, fixed_delta_seconds=None, no_rendering_mode=False):
        self.synchronous_mode = bool(synchronous_mode)
        self.fixed_delta_seconds = fixed_delta_seconds
        self.no_rendering_mode = bool(no_rendering_mode)

    def copy(self) -> "WorldSettings":
        return WorldSettings(self.synchronous_mode, self.fixed_delta_seconds, self.no_rendering_mode)


# ----------------------------------------------------------------- blueprints


class ActorAttribute:
    def __init__(self, value: str):
        self.value = str(value)

    def as_str(self) -> str:
        return self.value


class Blueprint:
    def __init__(self, blueprint_id: str, attributes: dict | None = None):
        self.id = blueprint_id
        self._attributes = dict(attributes or {})
        self._attributes.setdefault("role_name", "")
        if blueprint_id.startswith("sensor.camera"):
            for key, value in (("image_size_x", "800"), ("image_size_y", "600"), ("fov", "90"),
                               ("sensor_tick", "0.0")):
                self._attributes.setdefault(key, value)

    def set_attribute(self, key: str, value) -> None:
        if key not in self._attributes and not self.id.startswith("static.prop.mesh"):
            raise IndexError(f"blueprint {self.id} has no attribute {key}")
        self._attributes[key] = str(value)

    def has_attribute(self, key: str) -> bool:
        return key in self._attributes

    def get_attribute(self, key: str) -> ActorAttribute:
        return ActorAttribute(self._attributes[key])

    def copy(self) -> "Blueprint":
        return Blueprint(self.id, self._attributes)


class BlueprintLibrary:
    def __init__(self, blueprints):
        self._blueprints = list(blueprints)

    def find(self, blueprint_id: str) -> Blueprint:
        for blueprint in self._blueprints:
            if blueprint.id == blueprint_id:
                return blueprint.copy()
        raise IndexError(f"blueprint '{blueprint_id}' not found")

    def filter(self, pattern: str):
        return [b.copy() for b in self._blueprints if fnmatch.fnmatchcase(b.id, pattern)]

    def __iter__(self):
        return iter([b.copy() for b in self._blueprints])


class WheelPhysicsControl:
    def __init__(self, axle_type: int = 0, offset=None, wheel_radius: float = 35.0, max_steer_angle: float = 70.0):
        self.axle_type = axle_type
        self.offset = offset if offset is not None else Vector3D(0.0, 0.0, 0.0)
        self.wheel_radius = wheel_radius
        self.max_steer_angle = max_steer_angle


class VehiclePhysicsControl:
    def __init__(self, wheels=None, mass: float = 1500.0, center_of_mass=None):
        self.wheels = list(wheels or [])
        self.mass = mass
        self.center_of_mass = center_of_mass if center_of_mass is not None else Vector3D(0.0, 0.0, 0.0)


# get_available_maps() of the real server, 1.0-14ac3b1a5 on the G4 (p10-1-world-maps-20261119/FACTS.md): bare names.
# The base package alone (the paid p10-1 of 20261119T123937Z): four maps.
BASE_PACKAGE_MAPS = ("EmptyMap", "Town10HD_Opt", "Town12", "Town15")
# With CARLA's AdditionalMaps pack installed (CarlaUnreal/Packs/AdditionalMaps): sixteen.
WITH_ADDITIONAL_MAPS = ("Eixample", "EmptyMap", "Mine_01", "Town01_Opt", "Town02_Opt", "Town03_Opt", "Town04_Opt",
                        "Town05_Opt", "Town06_Opt", "Town07_Opt", "Town10HD_Opt", "Town11", "Town12", "Town13",
                        "Town15", "Town_C")

_DATA = Path(__file__).resolve().parents[2] / "data"
# The map read of the real server (lane A2, 2026-11-20): what the fake replays
REAL_READ = json.loads((_DATA / "town06_opt_g4_read.json").read_text(encoding="utf-8"))
REAL_STATIC_PROPS = tuple(REAL_READ["static_prop"])
REPLAY_XODR = {"Town06_Opt": _DATA / REAL_READ["xodr_file"]}

# A spawned prop's bounding box on the real server (F3 of lane I-W, G4, 2026-11-20, contact_probe.py): extent, location
PROP_BOUNDING_BOXES = {
    "static.prop.streetbarrier": ((0.6073904633522034, 0.18604671955108643, 0.534582257270813),
                                  (0.0, 0.0, 0.5347943902015686)),
}

VEHICLE_SHAPES = {                      # extent (half sizes, m), wheelbase (m)
    "vehicle.lincoln.mkz": ((2.45, 1.05, 0.75), 2.85),
    "vehicle.tesla.model3": ((2.40, 1.05, 0.75), 2.87),
}


def default_blueprints() -> list[Blueprint]:
    out = [Blueprint(name) for name in VEHICLE_SHAPES]
    out += [Blueprint("sensor.camera.rgb"), Blueprint("sensor.other.collision"),
            Blueprint("sensor.other.lane_invasion"),
            Blueprint("static.prop.mesh", {"mesh_path": "", "mass": "", "scale": "1.0"})]
    out += [Blueprint(name, {"size": "", "mesh_path": ""}) for name in REAL_STATIC_PROPS if name != "static.prop.mesh"]
    return out


# ----------------------------------------------------------------------- maps


class Waypoint:
    def __init__(self, map_, lane_id: int, s: float):
        self._map = map_
        self.lane_id = int(lane_id)
        self.s = float(s)
        self.road_id = map_.road_id
        self.section_id = 0
        self.lane_width = map_.lane_width
        self.lane_type = LaneType.Driving
        self.is_junction = map_.junction_from <= s <= map_.junction_to
        self.id = hash((self.road_id, self.lane_id, round(self.s, 3)))

    @property
    def transform(self) -> Transform:
        x, y, yaw = self._map.pose_at(self.lane_id, self.s)
        return Transform(Location(x, y, self._map.ground_z), Rotation(0.0, yaw, 0.0))

    def next(self, distance: float):
        s = self.s + float(distance)
        return [Waypoint(self._map, self.lane_id, s)] if s <= self._map.length else []

    def previous(self, distance: float):
        s = self.s - float(distance)
        return [Waypoint(self._map, self.lane_id, s)] if s >= 0.0 else []

    def get_left_lane(self):
        lane = self.lane_id + 1
        return Waypoint(self._map, lane, self.s) if lane in self._map.lanes else None

    def get_right_lane(self):
        lane = self.lane_id - 1
        return Waypoint(self._map, lane, self.s) if lane in self._map.lanes else None


class Map:
    """Straight lanes along +x; lane -1 centered at y = 0, lane -2 at y = +lane_width (CARLA's y is right).

    ``bend_from`` adds a constant-radius left bend from that s on, so that a straight-stretch search has
    something to reject.
    """

    def __init__(self, name: str = "Carla/Maps/Town06_Opt", length: float = 1000.0):
        self.name = name
        self.length = float(length)
        self.road_id = 35
        self.lanes = (-1, -2)
        self.lane_width = 3.5
        self.ground_z = 0.0
        self.junction_from, self.junction_to = 1e9, 1e9
        self.bend_from = 1e9
        self.bend_radius = 200.0

    def pose_at(self, lane_id: int, s: float) -> tuple[float, float, float]:
        offset = (-1 - lane_id) * self.lane_width
        if s <= self.bend_from:
            return s, offset, 0.0
        phi = (s - self.bend_from) / self.bend_radius          # left bend: yaw decreases in CARLA
        r = self.bend_radius
        cx, cy = self.bend_from, -r                           # center of the bend, to the left
        rr = r + offset
        return cx + rr * math.sin(phi), cy + rr * math.cos(phi), -math.degrees(phi)

    def get_spawn_points(self):
        return [Waypoint(self, -1, s).transform for s in (10.0, 50.0)]

    def to_opendrive(self) -> str:
        """The map's OpenDRIVE text, replayed from the real server's read; the waypoints of this fake stay its own
        straight lanes."""
        short = self.name.rstrip("/").split("/")[-1]
        path = REPLAY_XODR.get(short)
        if path is None:
            raise RuntimeError(f"fake carla: no OpenDRIVE read of {short} to replay")
        with lzma.open(path, "rt", encoding="utf-8") as f:
            return f.read()

    def generate_waypoints(self, distance: float):
        out, s = [], 0.0
        while s <= self.length:
            out += [Waypoint(self, lane, s) for lane in self.lanes]
            s += float(distance)
        return out

    def get_waypoint_xodr(self, road_id: int, lane_id: int, s: float):
        # the real server gives no waypoint at a road's own length (F3, G4, 2026-11-20: 54:6:62.56, road 54's length)
        if road_id != self.road_id or lane_id not in self.lanes or not 0 <= s < self.length:
            return None
        return Waypoint(self, lane_id, s)

    def get_waypoint(self, location, project_to_road: bool = True, lane_type=LaneType.Driving):
        if location.x <= self.bend_from:
            if not project_to_road and not 0.0 <= location.x <= self.length:
                return None                 # beyond the road's ends: on no lane
            s = max(0.0, min(self.length, location.x))
            lane = -1 if location.y < self.lane_width / 2.0 else -2
            if not project_to_road and (location.y < -self.lane_width / 2 or
                                        location.y > 1.5 * self.lane_width):
                return None
            return Waypoint(self, lane, s)
        dx, dy = location.x - self.bend_from, location.y + self.bend_radius
        phi = math.atan2(dx, dy)
        rr = math.hypot(dx, dy)
        lane = -1 if rr < self.bend_radius + self.lane_width / 2 else -2
        return Waypoint(self, lane, self.bend_from + phi * self.bend_radius)


# --------------------------------------------------------------------- actors


class _ActorState:
    """The server's state of one actor."""

    def __init__(self, server, actor_id: int, blueprint: Blueprint, transform: Transform, parent_id):
        self.server = server
        self.id = actor_id
        self.type_id = blueprint.id
        self.attributes = dict(blueprint._attributes)
        self.transform = Transform(Location(transform.location.x, transform.location.y, transform.location.z),
                                   Rotation(transform.rotation.pitch, transform.rotation.yaw,
                                            transform.rotation.roll))
        self.parent_id = parent_id
        self.alive = True
        self.speed = 0.0
        self.yaw_rate_deg = 0.0
        self.accel = 0.0
        self.ackermann = None
        self.ackermann_settings = AckermannControllerSettings()
        self.constant_velocity = None
        self.control = VehicleControl()
        self.simulate_physics = True
        self.listeners: list = []
        self.textures: list = []
        self.spawned_at_frame = server.frame
        shape = VEHICLE_SHAPES.get(self.type_id)
        if shape is not None:
            (ex, ey, ez), self.wheelbase = shape
            self.bounding_box = BoundingBox(Location(0.0, 0.0, ez), Vector3D(ex, ey, ez))
        else:
            self.wheelbase = 0.0
            ext, loc = PROP_BOUNDING_BOXES.get(self.type_id, ((0.05, 0.05, 0.05), (0.0, 0.0, 0.0)))
            self.bounding_box = BoundingBox(Location(*loc), Vector3D(*ext))
        self.next_sensor_time: float | None = None
        self.attachment_type = AttachmentType.Rigid


class Actor:
    """A client's handle on a server actor."""

    def __init__(self, client, state: _ActorState):
        self._client = client
        self._state = state

    id = property(lambda self: self._state.id)
    type_id = property(lambda self: self._state.type_id)
    attributes = property(lambda self: dict(self._state.attributes))
    is_alive = property(lambda self: self._state.alive)
    bounding_box = property(lambda self: self._state.bounding_box)

    @property
    def parent(self):
        pid = self._state.parent_id
        return None if pid is None else Actor(self._client, self._state.server.actors[pid])

    def _log(self, call: str, value) -> None:
        self._state.server.control_log.append({"client": self._client.name, "call": call, "actor": self.id,
                                               "frame": self._state.server.frame, "value": value})

    def get_transform(self) -> Transform:
        t = self._state.server.world_transform(self._state)
        return Transform(Location(t.location.x, t.location.y, t.location.z),
                         Rotation(t.rotation.pitch, t.rotation.yaw, t.rotation.roll))

    def get_location(self) -> Location:
        return self.get_transform().location

    def set_transform(self, transform) -> None:
        self._log("set_transform", (transform.location.x, transform.location.y))
        self._state.transform = Transform(Location(transform.location.x, transform.location.y,
                                                   transform.location.z),
                                          Rotation(transform.rotation.pitch, transform.rotation.yaw,
                                                   transform.rotation.roll))

    def get_velocity(self) -> Vector3D:
        f = self._state.transform.rotation.get_forward_vector()
        return Vector3D(f.x * self._state.speed, f.y * self._state.speed, 0.0)

    def get_acceleration(self) -> Vector3D:
        f = self._state.transform.rotation.get_forward_vector()
        return Vector3D(f.x * self._state.accel, f.y * self._state.accel, 0.0)

    def get_angular_velocity(self) -> Vector3D:
        return Vector3D(0.0, 0.0, self._state.yaw_rate_deg)

    def get_control(self) -> VehicleControl:
        return self._state.control

    def apply_ackermann_control(self, control) -> None:
        self._log("apply_ackermann_control", (control.steer, control.speed, control.acceleration, control.jerk))
        self._state.ackermann = control

    def apply_ackermann_controller_settings(self, settings) -> None:
        self._log("apply_ackermann_controller_settings",
                  tuple(getattr(settings, k) for k in AckermannControllerSettings.FIELDS))
        self._state.ackermann_settings = AckermannControllerSettings(
            **{k: getattr(settings, k) for k in AckermannControllerSettings.FIELDS})

    def get_ackermann_controller_settings(self):
        st = self._state.ackermann_settings
        return AckermannControllerSettings(**{k: getattr(st, k) for k in AckermannControllerSettings.FIELDS})

    def apply_control(self, control) -> None:
        self._log("apply_control", (control.throttle, control.steer, control.brake, control.hand_brake))
        self._state.control = control

    def set_autopilot(self, enabled: bool = True, tm_port: int = 8000) -> None:
        self._log("set_autopilot", bool(enabled))

    def set_target_velocity(self, velocity) -> None:
        self._log("set_target_velocity", (velocity.x, velocity.y))
        self._state.speed = math.hypot(velocity.x, velocity.y)

    def enable_constant_velocity(self, velocity) -> None:
        self._log("enable_constant_velocity", (velocity.x, velocity.y))
        self._state.constant_velocity = Vector3D(velocity.x, velocity.y, velocity.z)

    def disable_constant_velocity(self) -> None:
        self._log("disable_constant_velocity", None)
        self._state.constant_velocity = None

    def set_simulate_physics(self, enabled: bool = True) -> None:
        self._state.simulate_physics = bool(enabled)

    # CARLA 1.0's physics control: WheelPhysicsControl has axle_type, offset, radius, ... but no wheel position
    # (PythonAPI/carla/src/Control.cpp:439-462 at 14ac3b1a50); the wheel positions are the wheel bones'.
    def get_physics_control(self):
        if not self._state.wheelbase:
            raise RuntimeError("not a vehicle")
        wheels = [WheelPhysicsControl(axle_type=0 if i < 2 else 1) for i in range(4)]
        return VehiclePhysicsControl(wheels=wheels, mass=1800.0, center_of_mass=Vector3D(0.0, 0.0, 0.0))

    def _wheel_points(self):
        ex, ey = self._state.bounding_box.extent.x, self._state.bounding_box.extent.y
        half = self._state.wheelbase / 2.0
        return [("Wheel_Front_Left", half, -ey), ("Wheel_Front_Right", half, ey),
                ("Wheel_Rear_Left", -half, -ey), ("Wheel_Rear_Right", -half, ey)]

    def get_bone_names(self):
        if not self._state.wheelbase:
            return []
        return ["Root", "Body"] + [n for n, _, _ in self._wheel_points()]

    def get_bone_world_transforms(self):
        if not self._state.wheelbase:
            return []
        t = self.get_transform()
        yaw = math.radians(t.rotation.yaw)
        out = [Transform(Location(t.location.x, t.location.y, t.location.z), Rotation(0.0, t.rotation.yaw, 0.0))
               for _ in range(2)]
        for _name, ax, ay in self._wheel_points():
            out.append(Transform(Location(t.location.x + ax * math.cos(yaw) - ay * math.sin(yaw),
                                          t.location.y + ax * math.sin(yaw) + ay * math.cos(yaw), 0.35),
                                 Rotation(0.0, t.rotation.yaw, 0.0)))
        return out

    def apply_texture(self, material_parameter, texture) -> None:
        self._state.textures.append((material_parameter, texture))

    def listen(self, callback) -> None:
        self._state.listeners.append(callback)

    def is_listening(self) -> bool:
        return bool(self._state.listeners)

    def stop(self) -> None:
        self._state.listeners.clear()

    def destroy(self) -> bool:
        if not self._state.alive:
            return False
        self._state.alive = False
        self._state.listeners.clear()
        self._state.server.actors.pop(self._state.id, None)
        self._state.server.log.append(("destroy", self._state.id, self._state.server.frame))
        return True


class ActorList(list):
    def filter(self, pattern: str) -> "ActorList":
        return ActorList(a for a in self if fnmatch.fnmatchcase(a.type_id, pattern))

    def find(self, actor_id: int):
        for actor in self:
            if actor.id == actor_id:
                return actor
        return None


class WeatherParameters:
    def __init__(self, name: str = "Default"):
        self.name = name


for _preset in ("Default", "ClearNoon", "CloudyNoon", "WetNoon", "ClearSunset", "HardRainNoon"):
    setattr(WeatherParameters, _preset, WeatherParameters(_preset))


def _cam_axes(pitch, yaw, roll):
    """CARLA's forward, right and up vectors of a rotation (as tests/synthetic_render.py)."""
    p, y, r = (math.radians(v) for v in (pitch, yaw, roll))
    fwd = (math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p))
    right = (math.cos(y) * math.sin(p) * math.sin(r) - math.sin(y) * math.cos(r),
             math.sin(y) * math.sin(p) * math.sin(r) + math.cos(y) * math.cos(r), -math.cos(p) * math.sin(r))
    up = (-math.cos(y) * math.sin(p) * math.cos(r) - math.sin(y) * math.sin(r),
          -math.sin(y) * math.sin(p) * math.cos(r) + math.cos(y) * math.sin(r), math.cos(p) * math.cos(r))
    return fwd, right, up


class Image:
    """A grey frame; flat boards (static.prop.mesh of side 1 m x scale, lying flat) whose texture took
    (FAKE_TEXTURE_TAKES, default every parameter) are drawn by ray casting, nothing else is rendered."""

    def __init__(self, frame: int, timestamp: float, width: int, height: int, transform: Transform,
                 fov: float = 50.0, boards: list | None = None):
        self.frame, self.timestamp = int(frame), float(timestamp)
        self.width, self.height = int(width), int(height)
        self.fov = float(fov)
        self.transform = transform
        self._boards = boards or []
        self._raw: bytes | None = None

    @property
    def raw_data(self) -> bytes:
        if self._raw is None:
            self._raw = self._render()
        return self._raw

    def _render(self) -> bytes:
        w, h = self.width, self.height
        out = bytearray(bytes([90, 90, 90, 255]) * (w * h))
        if not self._boards:
            return bytes(out)
        f = w / (2.0 * math.tan(math.radians(self.fov) / 2.0))
        t = self.transform
        fwd, right, up = _cam_axes(t.rotation.pitch, t.rotation.yaw, t.rotation.roll)
        o = (t.location.x, t.location.y, t.location.z)
        for bt, side, tex in self._boards:
            half = side / 2.0
            c, sn = math.cos(math.radians(bt.rotation.yaw)), math.sin(math.radians(bt.rotation.yaw))
            corners = [(bt.location.x + dx * c - dy * sn, bt.location.y + dx * sn + dy * c, bt.location.z)
                       for dx in (-half, half) for dy in (-half, half)]
            pix = []
            for p in corners:
                d = [p[k] - o[k] for k in range(3)]
                x = sum(d[k] * fwd[k] for k in range(3))
                if x <= 0.1:
                    continue
                pix.append((w / 2.0 + f * sum(d[k] * right[k] for k in range(3)) / x,
                            h / 2.0 - f * sum(d[k] * up[k] for k in range(3)) / x))
            if len(pix) < 4:
                continue
            u0, u1 = max(0, int(min(q[0] for q in pix))), min(w - 1, int(max(q[0] for q in pix)) + 1)
            v0, v1 = max(0, int(min(q[1] for q in pix))), min(h - 1, int(max(q[1] for q in pix)) + 1)
            for v in range(v0, v1 + 1):
                b = -(v + 0.5 - h / 2.0) / f
                for u in range(u0, u1 + 1):
                    a = (u + 0.5 - w / 2.0) / f
                    dz = fwd[2] + a * right[2] + b * up[2]
                    if dz >= -1e-9:
                        continue
                    s = (bt.location.z - o[2]) / dz
                    gx = o[0] + s * (fwd[0] + a * right[0] + b * up[0]) - bt.location.x
                    gy = o[1] + s * (fwd[1] + a * right[1] + b * up[1]) - bt.location.y
                    lx, ly = gx * c + gy * sn, -gx * sn + gy * c
                    if abs(lx) >= half or abs(ly) >= half:
                        continue
                    col = tex.get(min(tex.width - 1, int((ly + half) / side * tex.width)),
                                  min(tex.height - 1, int((lx + half) / side * tex.height)))
                    i = 4 * (v * w + u)
                    out[i:i + 4] = bytes([col.b, col.g, col.r, 255])
        return bytes(out)


class CollisionEvent:
    def __init__(self, frame: int, timestamp: float, actor, other_actor, impulse: float):
        self.frame, self.timestamp = frame, timestamp
        self.actor, self.other_actor = actor, other_actor
        self.normal_impulse = Vector3D(impulse, 0.0, 0.0)


# ------------------------------------------------------------------- server


class _Server:
    """State shared by every client of one fake server."""

    def __init__(self, map_name: str):
        self.map = Map(map_name)
        # FAKE_CARLA_MAPS (comma-separated) replaces the list, e.g. with BASE_PACKAGE_MAPS for a host without the pack
        env_maps = os.environ.get("FAKE_CARLA_MAPS")
        self.available_maps = list(env_maps.split(",") if env_maps is not None else WITH_ADDITIONAL_MAPS)
        self.settings = WorldSettings()
        self.frame = 0
        self.elapsed = 0.0
        self.actors: dict[int, _ActorState] = {}
        self.next_id = 100
        self.log: list[tuple] = []
        self.control_log: list[dict] = []
        self.tick_callbacks: list = []
        self.blueprints = BlueprintLibrary(default_blueprints())
        self.spawn_failures: set[str] = set()
        self.tick_cost_s = 0.0
        self.clock = None
        self.pre_tick_hooks: list = []       # called with (server) before the physics step
        self.object_names = ["Road_Road_Town04_1", "Road_Marking_Town04_1"]
        self.named_textures: list = []
        self.actor_list_at_last_tick = os.environ.get("FAKE_CARLA_LAST_TICK_ACTORS") == "1"
        self.tick_actor_ids: tuple = ()      # the actors of the last tick (none before the first)
        self.ticks = 0                       # ticks since the server started (frame also moves on load_world)
        self.tick_callback_ids: dict = {}

    def _textured_boards(self) -> list:
        """The flat boards the camera can see: static.prop.mesh actors with a texture applied as a parameter that
        takes on this server (FAKE_TEXTURE_TAKES, comma-separated MaterialParameter names; default all)."""
        takes = os.environ.get("FAKE_TEXTURE_TAKES")
        ok = None if takes is None else {t.strip() for t in takes.split(",") if t.strip()}
        out = []
        for st in self.actors.values():
            if st.type_id != "static.prop.mesh" or not st.alive:
                continue
            tex = [t for p, t in st.textures if ok is None or p in ok]
            if tex:
                out.append((st.transform, float(st.attributes.get("scale") or 1.0), tex[-1]))
        return out

    def world_transform(self, state: _ActorState) -> Transform:
        if state.parent_id is None:
            return state.transform
        parent = self.actors.get(state.parent_id)
        if parent is None:
            return state.transform
        m = parent.transform.get_matrix()
        loc = state.transform.location
        wx = m[0][0] * loc.x + m[0][1] * loc.y + m[0][2] * loc.z + m[0][3]
        wy = m[1][0] * loc.x + m[1][1] * loc.y + m[1][2] * loc.z + m[1][3]
        wz = m[2][0] * loc.x + m[2][1] * loc.y + m[2][2] * loc.z + m[2][3]
        rot = Rotation(parent.transform.rotation.pitch + state.transform.rotation.pitch,
                       parent.transform.rotation.yaw + state.transform.rotation.yaw,
                       parent.transform.rotation.roll + state.transform.rotation.roll)
        return Transform(Location(wx, wy, wz), rot)

    def step_vehicle(self, state: _ActorState, dt: float) -> None:
        if state.constant_velocity is not None and state.simulate_physics:
            old = state.speed
            state.speed = state.constant_velocity.x
            state.accel = (state.speed - old) / dt if old else 0.0
            state.yaw_rate_deg = 0.0
            yaw = math.radians(state.transform.rotation.yaw)
            state.transform.location.x += state.speed * math.cos(yaw) * dt
            state.transform.location.y += state.speed * math.sin(yaw) * dt
            return
        control = state.ackermann
        if control is None or not state.simulate_physics:
            state.accel = 0.0
            state.yaw_rate_deg = 0.0
            return
        rate = abs(control.acceleration) if control.acceleration != 0.0 else 3.0
        target = max(0.0, control.speed)
        old = state.speed
        if state.speed < target:
            state.speed = min(target, state.speed + rate * dt)
        else:
            state.speed = max(target, state.speed - rate * dt)
        state.accel = (state.speed - old) / dt
        mean_speed = 0.5 * (old + state.speed)
        state.yaw_rate_deg = math.degrees(mean_speed * math.tan(control.steer) / state.wheelbase) \
            if state.wheelbase else 0.0
        yaw = math.radians(state.transform.rotation.yaw + 0.5 * state.yaw_rate_deg * dt)
        state.transform.location.x += mean_speed * math.cos(yaw) * dt
        state.transform.location.y += mean_speed * math.sin(yaw) * dt
        state.transform.rotation.yaw += state.yaw_rate_deg * dt
        state.control = VehicleControl(throttle=0.5 if state.accel > 0 else 0.0, steer=control.steer / 1.22,
                                       brake=0.5 if state.accel < 0 else 0.0)

    def tick(self) -> int:
        if self.tick_cost_s and self.clock is not None:
            self.clock.advance(self.tick_cost_s)
        dt = float(self.settings.fixed_delta_seconds or 0.05)
        for hook in list(self.pre_tick_hooks):
            hook(self)
        self.frame += 1
        self.elapsed += dt
        vehicles = [s for s in self.actors.values() if s.type_id.startswith("vehicle.")]
        for state in vehicles:
            self.step_vehicle(state, dt)
        self._collisions(vehicles)
        self._sensors()
        self.ticks += 1
        self.tick_actor_ids = tuple(self.actors)
        snapshot = WorldSnapshot(self.frame, self.elapsed, self.tick_actor_ids)
        for callback in list(self.tick_callbacks):
            callback(snapshot)
        return self.frame

    def _collisions(self, vehicles) -> None:
        for a in vehicles:
            for b in vehicles:
                if a.id >= b.id:
                    continue
                dx = abs(a.transform.location.x - b.transform.location.x)
                dy = abs(a.transform.location.y - b.transform.location.y)
                if dx <= a.bounding_box.extent.x + b.bounding_box.extent.x and \
                        dy <= a.bounding_box.extent.y + b.bounding_box.extent.y:
                    for me, other in ((a, b), (b, a)):
                        for s in self.actors.values():
                            if s.parent_id == me.id and s.type_id == "sensor.other.collision":
                                event = CollisionEvent(self.frame, self.elapsed, None,
                                                       _Other(other.id, other.type_id), 100.0)
                                for cb in list(s.listeners):
                                    cb(event)

    def _sensors(self) -> None:
        for state in list(self.actors.values()):
            if not state.type_id.startswith("sensor.camera") or not state.listeners:
                continue
            tick = float(state.attributes.get("sensor_tick") or 0.0)
            if state.next_sensor_time is None:
                state.next_sensor_time = self.elapsed
            if tick > 0.0 and self.elapsed + 1e-9 < state.next_sensor_time:
                continue
            state.next_sensor_time = self.elapsed + tick
            image = Image(self.frame, self.elapsed, int(state.attributes["image_size_x"]),
                          int(state.attributes["image_size_y"]), self.world_transform(state),
                          float(state.attributes.get("fov") or 50.0), self._textured_boards())
            for cb in list(state.listeners):
                cb(image)


class _Other:
    def __init__(self, actor_id: int, type_id: str):
        self.id, self.type_id = actor_id, type_id


class World:
    """A client's view of the server's world."""

    def __init__(self, client):
        self._client = client
        self._server = client._server

    @property
    def id(self) -> int:
        return 1

    def get_settings(self) -> WorldSettings:
        return self._server.settings.copy()

    def apply_settings(self, settings) -> int:
        self._server.settings = settings.copy()
        self._server.log.append(("settings", bool(settings.synchronous_mode), settings.fixed_delta_seconds))
        return self._server.frame

    def get_map(self) -> Map:
        return self._server.map

    def get_blueprint_library(self) -> BlueprintLibrary:
        return self._server.blueprints

    def _listed_ids(self) -> tuple:
        if self._server.actor_list_at_last_tick:
            if self._client._connect_ticks == self._server.ticks:
                return ()                    # this client has received no tick yet
            return tuple(i for i in self._server.tick_actor_ids if i in self._server.actors)
        return tuple(self._server.actors)

    def get_snapshot(self) -> WorldSnapshot:
        if self._server.actor_list_at_last_tick and self._client._connect_ticks == self._server.ticks:
            return WorldSnapshot(0, 0.0, ())
        return WorldSnapshot(self._server.frame, self._server.elapsed, self._listed_ids())

    def get_actors(self, actor_ids=None) -> ActorList:
        listed = set(self._listed_ids())
        states = [s for s in list(self._server.actors.values()) if s.id in listed]
        if actor_ids is not None:
            states = [s for s in states if s.id in set(actor_ids)]
        return ActorList(Actor(self._client, s) for s in states)

    def get_actor(self, actor_id: int):
        state = self._server.actors.get(int(actor_id))
        return None if state is None else Actor(self._client, state)

    def on_tick(self, callback) -> int:
        self._server.tick_callbacks.append(callback)
        callback_id = len(self._server.tick_callback_ids) + 1
        self._server.tick_callback_ids[callback_id] = callback
        return callback_id

    def remove_on_tick(self, callback_id: int) -> None:
        callback = self._server.tick_callback_ids.pop(callback_id, None)
        if callback is not None and callback in self._server.tick_callbacks:
            self._server.tick_callbacks.remove(callback)

    def tick(self, seconds: float = 10.0) -> int:
        if not self._server.settings.synchronous_mode:
            raise RuntimeError("tick() in asynchronous mode")
        return self._server.tick()

    def wait_for_tick(self, seconds: float = 10.0) -> WorldSnapshot:
        return self.get_snapshot()

    def spawn_actor(self, blueprint, transform, attach_to=None, attachment_type=AttachmentType.Rigid):
        if blueprint.id in self._server.spawn_failures:
            raise RuntimeError(f"Spawn failed because of collision at spawn position ({blueprint.id})")
        if blueprint.id == "static.prop.mesh" and not blueprint._attributes.get("mesh_path"):
            raise RuntimeError("empty mesh_path; spawn refused")
        actor_id = self._server.next_id
        self._server.next_id += 1
        state = _ActorState(self._server, actor_id, blueprint, transform,
                            None if attach_to is None else attach_to.id)
        state.attachment_type = attachment_type
        self._server.actors[actor_id] = state
        self._server.log.append(("spawn", actor_id, blueprint.id, self._client.name))
        return Actor(self._client, state)

    def try_spawn_actor(self, blueprint, transform, attach_to=None, attachment_type=AttachmentType.Rigid):
        try:
            return self.spawn_actor(blueprint, transform, attach_to, attachment_type)
        except RuntimeError:
            return None

    def set_weather(self, weather) -> None:
        self._server.weather = weather
        self._server.log.append(("weather", getattr(weather, "name", str(weather))))

    def get_weather(self):
        return getattr(self._server, "weather", WeatherParameters.Default)

    def get_names_of_all_objects(self):
        return list(self._server.object_names)

    def apply_color_texture_to_object(self, object_name, material_parameter, texture) -> None:
        self._server.named_textures.append((object_name, material_parameter, texture))


_SHARED_SERVER = None


class TrafficManager:
    def __init__(self, server, port: int):
        self.port = port
        server.log.append(("traffic_manager", port))

    def set_synchronous_mode(self, enabled: bool) -> None:
        pass


class Client:
    """``Client(host, port)``; ``_server`` and ``name`` are test-only keywords."""

    def __init__(self, host: str, port: int = 2000, worker_threads: int = 0, *, _server=None,
                 name: str = "world_side"):
        self.host, self.port = host, int(port)
        self._server = _server or _SHARED_SERVER or _Server("Carla/Maps/Town10HD_Opt")
        self._connect_ticks = self._server.ticks
        self.name = name
        self.timeout = 5.0
        self.load_calls: list[str] = []

    def set_timeout(self, seconds: float) -> None:
        self.timeout = float(seconds)

    def get_client_version(self) -> str:
        return "1.0-fake"

    def get_server_version(self) -> str:
        return "1.0-fake"

    def get_world(self) -> World:
        return World(self)

    def get_available_maps(self):
        return list(self._server.available_maps)

    def load_world(self, map_name: str, reset_settings: bool = True) -> World:
        # The real server (1.0-14ac3b1a5 on the G4, 2026-11-19) loads a name of get_available_maps() and nothing
        # else: load_world('Town04') -> RuntimeError "Map 'Town04' not found" with Town04_Opt installed
        self.load_calls.append(map_name)
        if map_name not in self._server.available_maps:
            raise RuntimeError(f"Map '{map_name}' not found")
        short = map_name.split("/")[-1]
        self._server.map = Map(f"Carla/Maps/{short}")
        self._server.actors.clear()
        return World(self)

    def get_trafficmanager(self, port: int = 8000) -> TrafficManager:
        return TrafficManager(self._server, port)
