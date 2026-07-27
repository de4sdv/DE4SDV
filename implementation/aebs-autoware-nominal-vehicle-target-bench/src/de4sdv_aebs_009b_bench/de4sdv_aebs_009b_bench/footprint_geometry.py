"""Independent map-pose footprint geometry for replayable outcome evidence."""

from __future__ import annotations

from dataclasses import dataclass
import math

from .scenario_contract import ObstacleGeometry, Pose2D, VehicleFootprint

Point2D = tuple[float, float]


@dataclass(frozen=True)
class FootprintRelation:
    overlap: bool
    separation_m: float


def _transform(pose: Pose2D, x: float, y: float) -> Point2D:
    cosine = math.cos(pose.yaw_rad)
    sine = math.sin(pose.yaw_rad)
    return pose.x + cosine * x - sine * y, pose.y + sine * x + cosine * y


def ego_corners(pose: Pose2D, geometry: VehicleFootprint) -> tuple[Point2D, ...]:
    half_width = geometry.width_m / 2.0
    return tuple(
        _transform(pose, x, y)
        for x, y in (
            (geometry.front_offset_m, half_width),
            (geometry.front_offset_m, -half_width),
            (-geometry.rear_offset_m, -half_width),
            (-geometry.rear_offset_m, half_width),
        )
    )


def target_corners(pose: Pose2D, geometry: ObstacleGeometry) -> tuple[Point2D, ...]:
    half_length = geometry.length_m / 2.0
    half_width = geometry.width_m / 2.0
    return tuple(
        _transform(pose, x, y)
        for x, y in (
            (half_length, half_width),
            (half_length, -half_width),
            (-half_length, -half_width),
            (-half_length, half_width),
        )
    )


def _axes(polygon: tuple[Point2D, ...]) -> tuple[Point2D, ...]:
    result = []
    for start, end in zip(polygon, polygon[1:] + polygon[:1]):
        dx, dy = end[0] - start[0], end[1] - start[1]
        length = math.hypot(dx, dy)
        result.append((-dy / length, dx / length))
    return tuple(result)


def _project(polygon: tuple[Point2D, ...], axis: Point2D) -> tuple[float, float]:
    values = tuple(x * axis[0] + y * axis[1] for x, y in polygon)
    return min(values), max(values)


def _overlap(first: tuple[Point2D, ...], second: tuple[Point2D, ...]) -> bool:
    for axis in _axes(first) + _axes(second):
        first_min, first_max = _project(first, axis)
        second_min, second_max = _project(second, axis)
        if first_max < second_min or second_max < first_min:
            return False
    return True


def _point_segment_distance(point: Point2D, start: Point2D, end: Point2D) -> float:
    dx, dy = end[0] - start[0], end[1] - start[1]
    denominator = dx * dx + dy * dy
    projection = ((point[0] - start[0]) * dx + (point[1] - start[1]) * dy) / denominator
    projection = min(1.0, max(0.0, projection))
    nearest = start[0] + projection * dx, start[1] + projection * dy
    return math.hypot(point[0] - nearest[0], point[1] - nearest[1])


def footprint_relation(
    ego_pose: Pose2D,
    ego_geometry: VehicleFootprint,
    target_pose: Pose2D,
    target_geometry: ObstacleGeometry,
) -> FootprintRelation:
    """Compute overlap and Euclidean polygon separation from map poses only."""

    ego = ego_corners(ego_pose, ego_geometry)
    target = target_corners(target_pose, target_geometry)
    if _overlap(ego, target):
        return FootprintRelation(overlap=True, separation_m=0.0)
    distances = []
    for polygon, other in ((ego, target), (target, ego)):
        edges = tuple(zip(other, other[1:] + other[:1]))
        distances.extend(
            _point_segment_distance(point, start, end)
            for point in polygon
            for start, end in edges
        )
    return FootprintRelation(overlap=False, separation_m=min(distances))
