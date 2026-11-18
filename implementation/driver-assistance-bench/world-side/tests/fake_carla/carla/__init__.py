"""A fake ``carla`` module for the world-side tests (the CARLA 1.0 surface that the world side uses).

Not a simulator. It keeps one shared server state and gives each ``Client`` its own handles, so a test can
tell which client applied a control: the world side, or a stand-in for the actuation adapter. What it models:

- synchronous mode with ``fixed_delta_seconds``; the snapshot's ``elapsed_seconds`` advances by the step;
- a sensor's ``sensor_tick``: a camera with ``sensor_tick`` 0.1 at a step of 0.05 delivers an image every
  second tick, stamped with the frame and the elapsed time of the tick it was rendered in;
- ``apply_ackermann_control`` (steer rad positive right, speed, acceleration, jerk, steer_speed) moving a
  vehicle by a kinematic bicycle: the speed moves toward the commanded speed at ``|acceleration|`` per
  second, and the yaw rate is ``v * tan(steer) / wheelbase`` (CARLA yaw is clockwise seen from above);
- a collision event when two vehicle bounding boxes overlap along a straight road;
- a map of straight lanes along +x (two driving lanes in one direction), with waypoints, ``next`` and a
  junction zone, and textures applied to actors (recorded, not rendered).

The API names follow the Python bindings of CARLA at 14ac3b1a502da45a44506cb2ed82ab800f1baf4c
(PythonAPI/carla/src/World.cpp, Actor.cpp, Map.cpp, Control.cpp, read on 2026-11-18).
"""

from __future__ import annotations

import fnmatch
import math

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


class WorldSnapshot:
    def __init__(self, frame: int, elapsed_seconds: float):
        self.frame = int(frame)
        self.timestamp = Timestamp(frame, elapsed_seconds)


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


VEHICLE_SHAPES = {                      # extent (half sizes, m), wheelbase (m)
    "vehicle.lincoln.mkz": ((2.45, 1.05, 0.75), 2.85),
    "vehicle.tesla.model3": ((2.40, 1.05, 0.75), 2.87),
}


def default_blueprints() -> list[Blueprint]:
    out = [Blueprint(name) for name in VEHICLE_SHAPES]
    out += [Blueprint("sensor.camera.rgb"), Blueprint("sensor.other.collision"),
            Blueprint("sensor.other.lane_invasion"),
            Blueprint("static.prop.mesh", {"mesh_path": "", "mass": "", "scale": "1.0"})]
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

    def __init__(self, name: str = "Carla/Maps/Town04", length: float = 1000.0):
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

    def generate_waypoints(self, distance: float):
        out, s = [], 0.0
        while s <= self.length:
            out += [Waypoint(self, lane, s) for lane in self.lanes]
            s += float(distance)
        return out

    def get_waypoint_xodr(self, road_id: int, lane_id: int, s: float):
        if road_id != self.road_id or lane_id not in self.lanes or not 0 <= s <= self.length:
            return None
        return Waypoint(self, lane_id, s)

    def get_waypoint(self, location, project_to_road: bool = True, lane_type=LaneType.Driving):
        if location.x <= self.bend_from:
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
            self.bounding_box = BoundingBox(Location(), Vector3D(0.05, 0.05, 0.05))
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

    def set_simulate_physics(self, enabled: bool = True) -> None:
        self._state.simulate_physics = bool(enabled)

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


class Image:
    def __init__(self, frame: int, timestamp: float, width: int, height: int, transform: Transform):
        self.frame, self.timestamp = int(frame), float(timestamp)
        self.width, self.height = int(width), int(height)
        self.fov = 50.0
        self.transform = transform

    @property
    def raw_data(self) -> bytes:
        """BGRA, a flat grey; rendering is not modeled."""
        return bytes([90, 90, 90, 255]) * (self.width * self.height)


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
        snapshot = WorldSnapshot(self.frame, self.elapsed)
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
                          int(state.attributes["image_size_y"]), self.world_transform(state))
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

    def get_snapshot(self) -> WorldSnapshot:
        return WorldSnapshot(self._server.frame, self._server.elapsed)

    def get_actors(self, actor_ids=None) -> ActorList:
        states = list(self._server.actors.values())
        if actor_ids is not None:
            states = [s for s in states if s.id in set(actor_ids)]
        return ActorList(Actor(self._client, s) for s in states)

    def get_actor(self, actor_id: int):
        state = self._server.actors.get(int(actor_id))
        return None if state is None else Actor(self._client, state)

    def on_tick(self, callback) -> int:
        self._server.tick_callbacks.append(callback)
        return len(self._server.tick_callbacks)

    def remove_on_tick(self, callback_id: int) -> None:
        pass

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

    def get_names_of_all_objects(self):
        return list(self._server.object_names)

    def apply_color_texture_to_object(self, object_name, material_parameter, texture) -> None:
        self._server.named_textures.append((object_name, material_parameter, texture))


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
        self._server = _server or _Server("Carla/Maps/Town10HD_Opt")
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
        return ["/Game/Carla/Maps/Town10HD_Opt", "/Game/Carla/Maps/Town04"]

    def load_world(self, map_name: str, reset_settings: bool = True) -> World:
        self.load_calls.append(map_name)
        short = map_name.split("/")[-1]
        self._server.map = Map(f"Carla/Maps/{short}")
        self._server.actors.clear()
        return World(self)

    def get_trafficmanager(self, port: int = 8000) -> TrafficManager:
        return TrafficManager(self._server, port)
