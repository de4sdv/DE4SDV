"""A minimal stand-in for CARLA 0.9.16's Python API, for the local tests.

Only the surface the exporters touch is implemented: ``Client`` -> ``World`` ->
``Map`` with waypoints, topology, spawn points, crosswalks, traffic-light
actors, and ``Transform``/``Location``/``Rotation`` types.  The scene is a
straight two-lane road that turns left into a second road, with one junction,
one crosswalk and one traffic light, which is enough to exercise every export
path on a machine without CARLA (no aarch64 wheel exists).

This file is a test double.  It is not used on the bench.
"""

from __future__ import annotations

import math

LANE_WIDTH = 3.5


class Location:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)

    def __repr__(self):
        return f"Location({self.x}, {self.y}, {self.z})"


class Rotation:
    def __init__(self, pitch=0.0, yaw=0.0, roll=0.0):
        self.pitch = float(pitch)
        self.yaw = float(yaw)
        self.roll = float(roll)


class Vector3D:
    def __init__(self, x=0.0, y=0.0, z=0.0):
        self.x = float(x)
        self.y = float(y)
        self.z = float(z)


class Transform:
    def __init__(self, location=None, rotation=None):
        self.location = location or Location()
        self.rotation = rotation or Rotation()

    def get_right_vector(self):
        yaw = math.radians(self.rotation.yaw)
        return Vector3D(math.cos(yaw + math.pi / 2.0),
                        math.sin(yaw + math.pi / 2.0), 0.0)

    def get_forward_vector(self):
        yaw = math.radians(self.rotation.yaw)
        return Vector3D(math.cos(yaw), math.sin(yaw), 0.0)


class Junction:
    def __init__(self, junction_id):
        self.id = int(junction_id)


class Waypoint:
    def __init__(self, *, road_id, section_id, lane_id, s, x, y, yaw_deg,
                 is_junction=False, lane_width=LANE_WIDTH, junction_id=None,
                 carla_map=None):
        self.road_id = int(road_id)
        self.section_id = int(section_id)
        self.lane_id = int(lane_id)
        self.s = float(s)
        self.is_junction = bool(is_junction)
        self.lane_width = float(lane_width)
        self.transform = Transform(
            Location(x, y, 0.0), Rotation(0.0, yaw_deg, 0.0)
        )
        self._junction_id = junction_id
        self._map = carla_map

    def get_junction(self):
        if self._junction_id is None:
            raise RuntimeError("waypoint is not in a junction")
        return Junction(self._junction_id)

    def get_left_lane(self):
        return None if self._map is None else self._map.neighbour(self, -1)

    def get_right_lane(self):
        return None if self._map is None else self._map.neighbour(self, +1)


class _ActorList:
    def __init__(self, actors):
        self._actors = list(actors)

    def filter(self, pattern):
        if pattern in ("traffic.traffic_light", "*"):
            return _ActorList(self._actors)
        return _ActorList([])

    def __iter__(self):
        return iter(self._actors)

    def __len__(self):
        return len(self._actors)


class TrafficLight:
    def __init__(self, transform):
        self._transform = transform

    def get_transform(self):
        return self._transform


class Map:
    """The scene: two roads, two waypoint groups per road and one junction."""

    def __init__(self, name="Town10HD_Test"):
        self.name = name
        self._lanes: dict[tuple[int, int, int], list[Waypoint]] = {}
        self._topology: list[tuple[Waypoint, Waypoint]] = []
        self._build()

    # ---------------------------------------------------------------- scene
    def _add_lane(self, road_id, section_id, lane_id, start, end, yaw_deg,
                  junction_from=None, junction_id=None, junction_to=None):
        x0, y0 = start
        x1, y1 = end
        length = math.hypot(x1 - x0, y1 - y0)
        count = max(2, int(round(length / 2.0)) + 1)
        points = []
        for index in range(count):
            fraction = index / (count - 1)
            x = x0 + fraction * (x1 - x0)
            y = y0 + fraction * (y1 - y0)
            s = fraction * length
            in_junction = junction_from is not None and s >= junction_from and (
                junction_to is None or s <= junction_to
            )
            points.append(
                Waypoint(
                    road_id=road_id,
                    section_id=section_id,
                    lane_id=lane_id,
                    s=s,
                    x=x,
                    y=y,
                    yaw_deg=yaw_deg,
                    is_junction=in_junction,
                    junction_id=junction_id if in_junction else None,
                    carla_map=self,
                )
            )
        self._lanes[(road_id, section_id, lane_id)] = points
        return points

    def _build(self):
        # Road 1: +x, 0..100 m.  Lane +1 is 1.75 m to the driver's left (-y),
        # lane -1 is 1.75 m to the right (+y): CARLA y grows to the right.
        left = self._add_lane(1, 0, 1, (0.0, -1.75), (100.0, -1.75), 0.0,
                              junction_from=96.0, junction_id=7)
        right = self._add_lane(1, 0, -1, (0.0, 1.75), (100.0, 1.75), 0.0,
                               junction_from=96.0, junction_id=7)
        # Road 2: +y, 0..100 m from (100, 0), a left turn from road 1.
        turn_left = self._add_lane(2, 0, 1, (98.25, 0.0), (98.25, 100.0), 90.0,
                                   junction_from=0.0, junction_id=7,
                                   junction_to=4.0)
        turn_right = self._add_lane(2, 0, -1, (101.75, 0.0), (101.75, 100.0),
                                    90.0, junction_from=0.0, junction_id=7,
                                    junction_to=4.0)
        self._topology = [
            (left[-1], turn_left[0]),
            (right[-1], turn_right[0]),
        ]

    # ------------------------------------------------------------------ API
    def generate_waypoints(self, distance):
        step = float(distance)
        out = []
        for key in sorted(self._lanes):
            points = self._lanes[key]
            accumulated = 0.0
            out.append(points[0])
            for previous, current in zip(points, points[1:]):
                segment = math.hypot(
                    current.transform.location.x - previous.transform.location.x,
                    current.transform.location.y - previous.transform.location.y,
                )
                accumulated += segment
                if accumulated >= step - 1e-9:
                    out.append(current)
                    accumulated = 0.0
        return out

    def get_topology(self):
        return list(self._topology)

    def get_spawn_points(self):
        return [
            Transform(Location(5.0, -1.75, 0.0), Rotation(0.0, 0.0, 0.0)),
            Transform(Location(98.25, 50.0, 0.0), Rotation(0.0, 90.0, 0.0)),
            Transform(Location(5.0, 1.75, 0.0), Rotation(0.0, 0.0, 0.0)),
        ]

    def get_crosswalks(self):
        return [
            Location(98.0, -5.0), Location(102.0, -5.0),
            Location(102.0, 5.0), Location(98.0, 5.0),
        ]

    def all_waypoints(self):
        return [point for key in sorted(self._lanes) for point in self._lanes[key]]

    def get_waypoint(self, location, project_to_road=True, lane_type=None):
        best = None
        best_distance = float("inf")
        for waypoint in self.all_waypoints():
            distance = math.hypot(
                waypoint.transform.location.x - location.x,
                waypoint.transform.location.y - location.y,
            )
            if distance < best_distance:
                best_distance = distance
                best = waypoint
        if best is None:
            raise RuntimeError("no waypoint")
        return best

    def neighbour(self, waypoint, offset):
        key = (waypoint.road_id, waypoint.section_id, waypoint.lane_id + offset)
        points = self._lanes.get(key)
        if not points:
            return None
        return min(points, key=lambda item: abs(item.s - waypoint.s))

    def lane_polyline(self, road_id, section_id, lane_id):
        return self._lanes[(road_id, section_id, lane_id)]


class WorldSettings:
    def __init__(self, synchronous_mode=True, fixed_delta_seconds=0.1):
        self.synchronous_mode = bool(synchronous_mode)
        self.fixed_delta_seconds = float(fixed_delta_seconds)


class _Snapshot:
    def __init__(self, frame):
        self.frame = int(frame)
        self.timestamp = frame * 0.1


class World:
    def __init__(self, carla_map, frame=0):
        self._map = carla_map
        self._frame = int(frame)
        self._callbacks = []
        self._traffic_lights = [
            TrafficLight(Transform(Location(95.0, -1.75, 5.0), Rotation()))
        ]

    def get_map(self):
        return self._map

    def get_actors(self):
        return _ActorList(self._traffic_lights)

    def get_snapshot(self):
        return _Snapshot(self._frame)

    def get_settings(self):
        return WorldSettings()

    def on_tick(self, callback):
        self._callbacks.append(callback)

    def has_tick_callbacks(self):
        return bool(self._callbacks)

    def tick(self, seconds=0.1):
        """Advance one fake tick and run the registered callbacks."""
        self._frame += 1
        snapshot = self.get_snapshot()
        for callback in list(self._callbacks):
            callback(snapshot)


class Client:
    """Fake RPC client; ``last`` exposes the instance to the test thread."""

    last = None

    def __init__(self, host="127.0.0.1", port=2000):
        self.host = host
        self.port = int(port)
        self.timeout = 5.0
        self.world = World(Map())
        Client.last = self

    def set_timeout(self, seconds):
        self.timeout = float(seconds)

    def get_world(self):
        return self.world

    def get_client_version(self):
        return "0.9.16-fake"


def make_world():
    """A fresh fake world (each test gets its own)."""
    return World(Map())
