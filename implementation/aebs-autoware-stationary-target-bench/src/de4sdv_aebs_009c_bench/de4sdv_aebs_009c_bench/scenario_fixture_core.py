"""ROS-independent state machine for the one-authority 009C target fixture."""

from __future__ import annotations

import math
import struct

from .scenario_contract import (
    Point3D,
    Pose2D,
    ScenarioConfig,
    anchor_target_pose_map,
    map_pose_to_base_link,
    rectangular_obstacle_points,
)

FLOAT32_MAX = float.fromhex("0x1.fffffep+127")


def _require_float32(name: str, value: float) -> float:
    value = float(value)
    if not math.isfinite(value) or abs(value) > FLOAT32_MAX:
        raise ValueError(f"{name} must be finite and representable as float32")
    return value


def quaternion_to_yaw(x: float, y: float, z: float, w: float) -> float:
    """Normalize a finite float32-representable quaternion without norm overflow."""

    values = tuple(_require_float32("quaternion component", value) for value in (x, y, z, w))
    scale = max(abs(value) for value in values)
    if scale <= 1.0e-12:
        raise ValueError("odometry quaternion must have nonzero norm")
    scaled = tuple(value / scale for value in values)
    scaled_norm = math.sqrt(sum(value * value for value in scaled))
    norm = scale * scaled_norm
    if not math.isfinite(norm) or norm > FLOAT32_MAX:
        raise ValueError("odometry quaternion norm must be representable as float32")
    x, y, z, w = (value / scaled_norm for value in scaled)
    sine = 2.0 * (w * z + x * y)
    cosine = 1.0 - 2.0 * (y * y + z * z)
    return math.atan2(sine, cosine)


def pack_xyz_float32(points: tuple[Point3D, ...]) -> bytes:
    """Pack complete XYZ points or reject before exposing any partial payload."""

    chunks: list[bytes] = []
    for index, point in enumerate(points):
        if not isinstance(point, Point3D):
            raise TypeError(f"points[{index}] must be Point3D")
        values = tuple(
            _require_float32(f"points[{index}].{axis}", value)
            for axis, value in zip(("x", "y", "z"), (point.x, point.y, point.z), strict=True)
        )
        try:
            chunks.append(struct.pack("<fff", *values))
        except (OverflowError, struct.error) as error:
            raise ValueError(f"points[{index}] cannot be packed as float32") from error
    return b"".join(chunks)


class ScenarioFixtureState:
    """Own live ego state and anchor exactly one stationary map-frame target."""

    def __init__(self, config: ScenarioConfig) -> None:
        if not isinstance(config, ScenarioConfig):
            raise TypeError("config must be ScenarioConfig")
        self._config = config
        self._ego_pose_map: Pose2D | None = None
        self._anchored_target_pose_map: Pose2D | None = None

    @property
    def config(self) -> ScenarioConfig:
        return self._config

    @property
    def anchored_target_pose_map(self) -> Pose2D | None:
        return self._anchored_target_pose_map

    def update_ego(self, pose_map: Pose2D) -> None:
        if not isinstance(pose_map, Pose2D):
            raise TypeError("pose_map must be Pose2D")
        _require_float32("pose_map.x", pose_map.x)
        _require_float32("pose_map.y", pose_map.y)
        self._ego_pose_map = pose_map

    def activate(self) -> Pose2D:
        if self._anchored_target_pose_map is not None:
            raise RuntimeError("target is already activated")
        if self._ego_pose_map is None:
            raise RuntimeError("target activation requires current ego pose")
        self._anchored_target_pose_map = anchor_target_pose_map(
            self._config.target_injection_pose_base_link,
            self._ego_pose_map,
        )
        return self._anchored_target_pose_map

    def target_points(self) -> tuple[Point3D, ...]:
        if self._anchored_target_pose_map is None:
            return ()
        if self._ego_pose_map is None:  # defensive: activation establishes this invariant
            raise RuntimeError("activated target requires current ego pose")
        target_base_link = map_pose_to_base_link(
            self._anchored_target_pose_map,
            self._ego_pose_map,
        )
        return rectangular_obstacle_points(target_base_link, self._config.geometry)
