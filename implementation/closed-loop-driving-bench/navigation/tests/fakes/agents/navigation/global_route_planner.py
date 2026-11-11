"""Test double for CARLA's ``agents.navigation.global_route_planner``.

Implements the two calls ``route_from_carla.py`` makes -- construction with
``(carla_map, sampling_resolution)`` and ``trace_route(start_location,
end_location)`` returning ``(Waypoint, RoadOption)`` pairs -- by walking the
fake map's topology.  Test-only; the bench uses CARLA's real planner.
"""

from __future__ import annotations

import math


class RoadOption:
    LANEFOLLOW = "LANEFOLLOW"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


class GlobalRoutePlanner:
    def __init__(self, carla_map, sampling_resolution):
        self._map = carla_map
        self._sampling = float(sampling_resolution)

    # --------------------------------------------------------------- helpers
    def _lane_key(self, waypoint):
        return (waypoint.road_id, waypoint.section_id, waypoint.lane_id)

    def _start_of(self, waypoint):
        return self._map.lane_polyline(*self._lane_key(waypoint))[0]

    def _end_of(self, waypoint):
        return self._map.lane_polyline(*self._lane_key(waypoint))[-1]

    def _nearest(self, location):
        return self._map.get_waypoint(location)

    def _lane_path(self, start_waypoint, end_waypoint):
        """Breadth-first lane path over the map topology."""
        start_key = self._lane_key(start_waypoint)
        goal_key = self._lane_key(end_waypoint)
        successors: dict[tuple, list[tuple]] = {}
        for entry, exit_waypoint in self._map.get_topology():
            successors.setdefault(self._lane_key(entry), []).append(
                self._lane_key(exit_waypoint)
            )
        queue = [start_key]
        parents = {start_key: None}
        while queue:
            current = queue.pop(0)
            if current == goal_key:
                break
            for following in successors.get(current, []):
                if following in parents:
                    continue
                parents[following] = current
                queue.append(following)
        if goal_key not in parents:
            raise RuntimeError("no route between the given waypoints")
        path = []
        node = goal_key
        while node is not None:
            path.append(node)
            node = parents[node]
        return list(reversed(path))

    def _resample(self, polyline):
        """Waypoints every ``sampling_resolution`` metres along a polyline."""
        if not polyline:
            return []
        out = [polyline[0]]
        step = self._sampling
        carry = 0.0
        for previous, current in zip(polyline, polyline[1:]):
            x0 = previous.transform.location.x
            y0 = previous.transform.location.y
            x1 = current.transform.location.x
            y1 = current.transform.location.y
            segment = math.hypot(x1 - x0, y1 - y0)
            if segment <= 0.0:
                continue
            travelled = step - carry
            while travelled <= segment:
                fraction = travelled / segment
                # A lane change does not blend headings: take the target lane's.
                yaw = current.transform.rotation.yaw
                out.append(
                    type(current)(
                        road_id=current.road_id,
                        section_id=current.section_id,
                        lane_id=current.lane_id,
                        s=previous.s + travelled,
                        x=x0 + fraction * (x1 - x0),
                        y=y0 + fraction * (y1 - y0),
                        yaw_deg=yaw,
                        carla_map=self._map,
                    )
                )
                travelled += step
            carry = segment - (travelled - step)
        return out

    # ------------------------------------------------------------------- API
    def trace_route(self, start_location, end_location):
        start = self._nearest(start_location)
        end = self._nearest(end_location)
        polyline = []
        for index, key in enumerate(self._lane_path(start, end)):
            lane = self._map.lane_polyline(*key)
            first = 0
            last = len(lane)
            if index == 0:
                first = min(range(len(lane)),
                            key=lambda item: abs(lane[item].s - start.s))
            if key == self._lane_key(end):
                last = min(range(len(lane)),
                           key=lambda item: abs(lane[item].s - end.s)) + 1
            polyline.extend(lane[first:last])
        return [(waypoint, RoadOption.LANEFOLLOW)
                for waypoint in self._resample(polyline)]
