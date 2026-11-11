"""A minimal stand-in for CARLA 0.9.16's Python API, for the local tests.

Only the surface the exporters touch is implemented: ``Client`` -> ``World`` ->
``Map`` with waypoints, topology, spawn points, crosswalks, traffic-light
actors, and ``Transform``/``Location``/``Rotation`` types.  The scene is a
straight two-lane road that turns left into a second road, with one junction,
one crosswalk and one traffic light, which is enough to exercise every export
path on a machine without CARLA (no aarch64 wheel exists).

Where a lane starts and ends follows LibCarla 0.9.16 (``road/Map.cpp``,
``client/Waypoint.cpp``), because the exporter depends on it:

* ``generate_waypoints(d)`` samples each road at s = EPSILON, EPSILON + d, ...
  below the road's length, for every lane of the lane section there.  A lane's
  samples therefore stop up to ``d`` short of the road's far end (s = length),
  and a lane section between two sample positions has none.
* ``get_topology()`` pairs every lane of every lane section, at its start in
  its driving direction, with the start of each lane it leads into, or, when
  it leads nowhere, with its own end.
* ``Waypoint.next`` and ``Waypoint.next_until_lane_end`` move along the
  driving direction as LibCarla does; the last waypoint of
  ``next_until_lane_end`` is at the end of the road.

A lane drives along s when its yaw points from its ``start`` to its ``end``
(the order of s), against s otherwise.  CARLA derives that from the sign of the
lane id; the first scene below keeps both lanes of a road in one direction.

This file is a test double.  It is not used on the bench.
"""

from __future__ import annotations

import math

LANE_WIDTH = 3.5
# road::Map's EPSILON (LibCarla/source/carla/road/Map.cpp:43).
EPSILON = 10.0 * 2.220446049250313e-16


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

    def next(self, distance):
        if self._map is None:
            raise RuntimeError("waypoint without a map")
        return self._map.next_waypoints(self, float(distance))

    def next_until_lane_end(self, distance):
        if self._map is None:
            raise RuntimeError("waypoint without a map")
        return self._map.next_until_lane_end(self, float(distance))


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


class _Lane:
    """One lane of one lane section: a straight piece from ``start`` (at s0) to
    ``end`` (at s1), in the order of s."""

    def __init__(self, key, start, end, s0, yaw_deg, junction_from, junction_to,
                 junction_id):
        self.key = key
        self.start = (float(start[0]), float(start[1]))
        self.end = (float(end[0]), float(end[1]))
        self.length = math.hypot(self.end[0] - self.start[0], self.end[1] - self.start[1])
        self.s0 = float(s0)
        self.s1 = self.s0 + self.length
        self.yaw_deg = float(yaw_deg)
        along = math.atan2(self.end[1] - self.start[1], self.end[0] - self.start[0])
        self.forward = math.cos(math.radians(self.yaw_deg) - along) > 0.0
        self.junction_from = junction_from
        self.junction_to = junction_to
        self.junction_id = junction_id


class Map:
    """The scene: two roads, two waypoint groups per road and one junction."""

    def __init__(self, name="Town10HD_Test"):
        self.name = name
        self._lanes: dict[tuple[int, int, int], list[Waypoint]] = {}
        self._pieces: dict[tuple[int, int, int], _Lane] = {}
        # The lanes each lane leads into, in its driving direction.
        self._successors: dict[tuple[int, int, int], list[tuple[int, int, int]]] = {}
        self._build()

    # ---------------------------------------------------------------- scene
    def _add_lane(self, road_id, section_id, lane_id, start, end, yaw_deg,
                  junction_from=None, junction_id=None, junction_to=None,
                  s_start=0.0):
        key = (road_id, section_id, lane_id)
        piece = _Lane(key, start, end, s_start, yaw_deg, junction_from,
                      junction_to, junction_id)
        self._pieces[key] = piece
        count = max(2, int(round(piece.length / 2.0)) + 1)
        points = [
            self._waypoint_at(piece, piece.s0 + piece.length * index / (count - 1))
            for index in range(count)
        ]
        self._lanes[key] = points
        return points

    def _build(self):
        # Road 1: +x, 0..100 m.  Lane +1 is 1.75 m to the driver's left (-y),
        # lane -1 is 1.75 m to the right (+y): CARLA y grows to the right.
        self._add_lane(1, 0, 1, (0.0, -1.75), (100.0, -1.75), 0.0,
                       junction_from=96.0, junction_id=7)
        self._add_lane(1, 0, -1, (0.0, 1.75), (100.0, 1.75), 0.0,
                       junction_from=96.0, junction_id=7)
        # Road 2: +y, 0..100 m from (100, 0), a left turn from road 1.
        self._add_lane(2, 0, 1, (98.25, 0.0), (98.25, 100.0), 90.0,
                       junction_from=0.0, junction_id=7, junction_to=4.0)
        self._add_lane(2, 0, -1, (101.75, 0.0), (101.75, 100.0), 90.0,
                       junction_from=0.0, junction_id=7, junction_to=4.0)
        self._successors = {
            (1, 0, 1): [(2, 0, 1)],
            (1, 0, -1): [(2, 0, -1)],
        }

    def _waypoint_at(self, piece, s):
        fraction = 0.0 if piece.length <= 0.0 else (s - piece.s0) / piece.length
        relative = s - piece.s0
        in_junction = piece.junction_from is not None and relative >= piece.junction_from and (
            piece.junction_to is None or relative <= piece.junction_to
        )
        road_id, section_id, lane_id = piece.key
        return Waypoint(
            road_id=road_id,
            section_id=section_id,
            lane_id=lane_id,
            s=s,
            x=piece.start[0] + fraction * (piece.end[0] - piece.start[0]),
            y=piece.start[1] + fraction * (piece.end[1] - piece.start[1]),
            yaw_deg=piece.yaw_deg,
            is_junction=in_junction,
            junction_id=piece.junction_id if in_junction else None,
            carla_map=self,
        )

    def _road_length(self, road_id):
        return max(piece.s1 for piece in self._pieces.values() if piece.key[0] == road_id)

    def _start_of(self, piece):
        # GetDistanceAtStartOfLane (road/Map.cpp:61-67).
        s = piece.s0 + 10.0 * EPSILON if piece.forward else piece.s1 - 10.0 * EPSILON
        return self._waypoint_at(piece, s)

    def _end_of(self, piece):
        # GetDistanceAtEndOfLane (road/Map.cpp:69-75).
        s = piece.s1 - 10.0 * EPSILON if piece.forward else piece.s0 + 10.0 * EPSILON
        return self._waypoint_at(piece, s)

    @staticmethod
    def _key(waypoint):
        return (waypoint.road_id, waypoint.section_id, waypoint.lane_id)

    # ------------------------------------------------------------------ API
    def generate_waypoints(self, distance):
        """road::Map::GenerateWaypoints (road/Map.cpp:783-795)."""
        step = float(distance)
        out = []
        for road_id in sorted({key[0] for key in self._pieces}):
            pieces = [self._pieces[key] for key in sorted(self._pieces) if key[0] == road_id]
            length = self._road_length(road_id)
            s = EPSILON
            while s < length - EPSILON:
                for piece in pieces:
                    if piece.s0 <= s < piece.s1:
                        out.append(self._waypoint_at(piece, s))
                s += step
        return out

    def get_topology(self):
        """road::Map::GenerateTopology (road/Map.cpp:856-877)."""
        pairs = []
        for key in sorted(self._pieces):
            entry = self._start_of(self._pieces[key])
            followers = self._successors.get(key, [])
            if followers:
                pairs.extend((entry, self._start_of(self._pieces[other])) for other in followers)
            else:
                pairs.append((entry, self._end_of(self._pieces[key])))
        return pairs

    def next_waypoints(self, waypoint, distance):
        """road::Map::GetNext (road/Map.cpp:641-688), without its loop guard."""
        if distance <= EPSILON:
            return [waypoint]
        piece = self._pieces[self._key(waypoint)]
        remaining = piece.s1 - waypoint.s if piece.forward else waypoint.s - piece.s0
        if distance <= remaining:
            if piece.forward:
                return [self._waypoint_at(piece, waypoint.s + distance - EPSILON)]
            return [self._waypoint_at(piece, waypoint.s - distance + EPSILON)]
        out = []
        for other in self._successors.get(piece.key, []):
            out.extend(self.next_waypoints(self._start_of(self._pieces[other]),
                                           distance - remaining))
        return out

    def next_until_lane_end(self, waypoint, distance):
        """client::Waypoint::GetNextUntilLaneEnd (client/Waypoint.cpp): steps of
        ``distance`` while one waypoint follows on the same road, then the rest
        of the road, so the last waypoint is at the road's end."""
        result = []
        following = self.next_waypoints(waypoint, distance)
        while len(following) == 1 and following[0].road_id == waypoint.road_id:
            result.append(following[0])
            following = self.next_waypoints(result[-1], distance)
        base = result[-1] if result else waypoint
        if self._pieces[self._key(waypoint)].forward:
            remaining = self._road_length(waypoint.road_id) - base.s
        else:
            remaining = base.s
        remaining -= 2.220446049250313e-16
        result.append(self.next_waypoints(base, remaining)[0])
        return result

    def get_spawn_points(self):
        return [
            Transform(Location(5.0, -1.75, 0.0), Rotation(0.0, 0.0, 0.0)),
            Transform(Location(98.25, 50.0, 0.0), Rotation(0.0, 90.0, 0.0)),
            Transform(Location(5.0, 1.75, 0.0), Rotation(0.0, 0.0, 0.0)),
        ]

    def get_crosswalks(self):
        # As CARLA gives them: a closed polygon, its first point repeated at its end.
        return [
            Location(98.0, -5.0), Location(102.0, -5.0),
            Location(102.0, 5.0), Location(98.0, 5.0), Location(98.0, -5.0),
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
