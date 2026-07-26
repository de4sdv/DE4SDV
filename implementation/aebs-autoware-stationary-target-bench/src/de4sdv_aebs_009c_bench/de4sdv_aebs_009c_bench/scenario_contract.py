"""Pure, ROS-independent contract primitives for scenario 009C.

The numeric geometry values are constraints of the pinned test fixture. They are
not product braking requirements.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import math
from pathlib import Path
from typing import Any, Mapping

import yaml


class Outcome(str, Enum):
    """Closed terminal outcome vocabulary for one scenario execution."""

    PASS_OBSERVED_CHAIN = "pass_observed_chain"
    FAIL_SCENARIO = "fail_scenario"
    INCONCLUSIVE_PRECONDITION = "inconclusive_precondition"
    INCONCLUSIVE_INSTRUMENTATION = "inconclusive_instrumentation"
    ABORTED = "aborted"


BASELINE_REQUIRED_INPUTS = (
    "/diagnostics",
    "/system/operation_mode/availability",
    "/system/fail_safe/mrm_state",
    "/system/mrm/emergency_stop/status",
    "/control/trajectory_follower/control_cmd",
    "/control/command/control_cmd",
    "/localization/kinematic_state",
)

REQUIRED_NON_CLAIMS = (
    "Numeric fixture values are not braking-performance requirements.",
    "A passing run is not a safety, certification, compliance, or homologation claim.",
    "Simulator deceleration is test-double behavior, not physical brake-actuation evidence.",
    "This is partial 009C evidence for the native AEB intervention-to-MRM/gate path, not nominal AEBS evidence.",
    "The native AEB ERROR diagnostic is an intentional intervention signal, not evidence of a component fault.",
    "This fixture does not cover moving targets, driver warning, driver override, direct AEBS braking requests, or collision outcome.",
)


def _finite_number(name: str, value: object) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name} must be a number")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite")
    return result


def _positive_number(name: str, value: object) -> float:
    result = _finite_number(name, value)
    if result <= 0.0:
        raise ValueError(f"{name} must be positive")
    return result


def _positive_int(name: str, value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be an integer")
    if value <= 0:
        raise ValueError(f"{name} must be positive")
    return value


def _normalize_yaw(yaw_rad: float) -> float:
    return (yaw_rad + math.pi) % (2.0 * math.pi) - math.pi


@dataclass(frozen=True)
class Pose2D:
    """Planar pose whose coordinates and yaw are expressed in one named frame."""

    x: float
    y: float
    yaw_rad: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite_number("x", self.x))
        object.__setattr__(self, "y", _finite_number("y", self.y))
        object.__setattr__(self, "yaw_rad", _finite_number("yaw_rad", self.yaw_rad))


def map_pose_to_base_link(target_map: Pose2D, ego_map: Pose2D) -> Pose2D:
    """Express a fixed map-frame target pose in the moving ego base frame."""

    dx = target_map.x - ego_map.x
    dy = target_map.y - ego_map.y
    cosine = math.cos(ego_map.yaw_rad)
    sine = math.sin(ego_map.yaw_rad)
    return Pose2D(
        x=cosine * dx + sine * dy,
        y=-sine * dx + cosine * dy,
        yaw_rad=_normalize_yaw(target_map.yaw_rad - ego_map.yaw_rad),
    )


def anchor_target_pose_map(target_base_link: Pose2D, ego_map: Pose2D) -> Pose2D:
    """Anchor a target once in map from the live ego pose at injection time."""

    cosine = math.cos(ego_map.yaw_rad)
    sine = math.sin(ego_map.yaw_rad)
    return Pose2D(
        x=ego_map.x + cosine * target_base_link.x - sine * target_base_link.y,
        y=ego_map.y + sine * target_base_link.x + cosine * target_base_link.y,
        yaw_rad=_normalize_yaw(ego_map.yaw_rad + target_base_link.yaw_rad),
    )


@dataclass(frozen=True)
class Point3D:
    """A dependency-free Cartesian point."""

    x: float
    y: float
    z: float

    def __post_init__(self) -> None:
        object.__setattr__(self, "x", _finite_number("x", self.x))
        object.__setattr__(self, "y", _finite_number("y", self.y))
        object.__setattr__(self, "z", _finite_number("z", self.z))


@dataclass(frozen=True)
class FixtureConstraints:
    """IMU-path limits derived from the pinned AEB configuration."""

    imu_path_horizon_s: float
    imu_path_max_length_m: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "imu_path_horizon_s",
            _positive_number("imu_path_horizon_s", self.imu_path_horizon_s),
        )
        object.__setattr__(
            self,
            "imu_path_max_length_m",
            _positive_number("imu_path_max_length_m", self.imu_path_max_length_m),
        )


@dataclass(frozen=True)
class BaselineContract:
    """Exact normal-state precondition that must remain stable before injection."""

    stable_duration_s: float
    ego_speed_min_mps: float
    required_input_max_age_s: float
    diagnostic_node: str = "autonomous_emergency_braking"
    diagnostic_task: str = "aeb_emergency_stop"
    diagnostic_joined_key: str = "autonomous_emergency_braking: aeb_emergency_stop"
    required_inputs: tuple[str, ...] = BASELINE_REQUIRED_INPUTS
    diagnostic_level: str = "OK"
    autonomous_available: bool = True
    mrm_state: str = "NORMAL"
    mrm_behavior: str = "NONE"
    emergency_operator_state: str = "AVAILABLE"
    gate_path: str = "nominal"

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "stable_duration_s",
            _positive_number("stable_duration_s", self.stable_duration_s),
        )
        object.__setattr__(
            self,
            "ego_speed_min_mps",
            _positive_number("ego_speed_min_mps", self.ego_speed_min_mps),
        )
        object.__setattr__(
            self,
            "required_input_max_age_s",
            _positive_number("required_input_max_age_s", self.required_input_max_age_s),
        )
        if self.autonomous_available is not True:
            raise TypeError("baseline autonomous_available must be the boolean true")
        if not isinstance(self.required_inputs, tuple):
            raise TypeError("baseline required_inputs must be an immutable tuple")
        if self.required_inputs != BASELINE_REQUIRED_INPUTS:
            raise ValueError("baseline required_inputs must match the closed 009C input set")
        expected_strings = {
            "diagnostic_node": "autonomous_emergency_braking",
            "diagnostic_task": "aeb_emergency_stop",
            "diagnostic_joined_key": "autonomous_emergency_braking: aeb_emergency_stop",
            "diagnostic_level": "OK",
            "mrm_state": "NORMAL",
            "mrm_behavior": "NONE",
            "emergency_operator_state": "AVAILABLE",
            "gate_path": "nominal",
        }
        for name, expected_value in expected_strings.items():
            if getattr(self, name) != expected_value:
                raise ValueError(f"baseline {name} must be {expected_value!r}")


@dataclass(frozen=True)
class ClockContract:
    """Clock domains retained by the collector; they are not interchangeable."""

    source_stamp: str
    receipt_time: str
    host_utc: str
    causal_order: str
    cross_domain_comparison: str

    def __post_init__(self) -> None:
        expected = {
            "source_stamp": "ros_message_header_when_available",
            "receipt_time": "collector_monotonic",
            "host_utc": "optional",
            "causal_order": "collector_monotonic_within_one_collector",
            "cross_domain_comparison": "forbidden_without_explicit_rule",
        }
        for name, expected_value in expected.items():
            if getattr(self, name) != expected_value:
                raise ValueError(f"clock {name} must be {expected_value!r}")


@dataclass(frozen=True)
class ObstacleGeometry:
    """Validated sampling inputs tied to the pinned AEB point-cloud pipeline."""

    length_m: float
    width_m: float
    height_m: float
    point_spacing_m: float
    voxel_size_x_m: float
    voxel_size_y_m: float
    voxel_size_z_m: float
    cluster_tolerance_m: float
    cluster_minimum_height_m: float
    minimum_cluster_size: int

    def __post_init__(self) -> None:
        for name in (
            "length_m",
            "width_m",
            "height_m",
            "point_spacing_m",
            "voxel_size_x_m",
            "voxel_size_y_m",
            "voxel_size_z_m",
            "cluster_tolerance_m",
            "cluster_minimum_height_m",
        ):
            object.__setattr__(self, name, _positive_number(name, getattr(self, name)))
        object.__setattr__(
            self,
            "minimum_cluster_size",
            _positive_int("minimum_cluster_size", self.minimum_cluster_size),
        )
        if self.point_spacing_m > min(
            self.voxel_size_x_m,
            self.voxel_size_y_m,
            self.cluster_tolerance_m,
        ):
            raise ValueError("point spacing must preserve XY voxel density and connectivity")
        if self.length_m <= self.voxel_size_x_m or self.width_m <= self.voxel_size_y_m:
            raise ValueError("horizontal dimensions must exceed one XY voxel")
        if self.height_m <= self.cluster_minimum_height_m:
            raise ValueError("obstacle height must exceed the strict cluster-height threshold")


def _axis_samples(start: float, extent: float, maximum_step: float) -> tuple[float, ...]:
    intervals = math.ceil(extent / maximum_step)
    step = extent / intervals
    return tuple(start + index * step for index in range(intervals + 1))


def rectangular_obstacle_points(
    pose: Pose2D, geometry: ObstacleGeometry
) -> tuple[Point3D, ...]:
    """Return a deterministic connected lattice filling an oriented rectangular solid."""

    xs = _axis_samples(-geometry.length_m / 2.0, geometry.length_m, geometry.point_spacing_m)
    ys = _axis_samples(-geometry.width_m / 2.0, geometry.width_m, geometry.point_spacing_m)
    zs = _axis_samples(0.0, geometry.height_m, geometry.point_spacing_m)
    cosine = math.cos(pose.yaw_rad)
    sine = math.sin(pose.yaw_rad)

    local_layer: list[tuple[float, float]] = []
    for y_index, y in enumerate(ys):
        row = xs if y_index % 2 == 0 else tuple(reversed(xs))
        local_layer.extend((x, y) for x in row)

    points: list[Point3D] = []
    for z_index, z in enumerate(zs):
        layer = local_layer if z_index % 2 == 0 else reversed(local_layer)
        for x, y in layer:
            points.append(
                Point3D(
                    x=pose.x + cosine * x - sine * y,
                    y=pose.y + sine * x + cosine * y,
                    z=z,
                )
            )
    return tuple(points)


def _post_voxel_components(geometry: ObstacleGeometry) -> tuple[tuple[Point3D, ...], ...]:
    """Approximate the pinned PCL VoxelGrid + Euclidean clustering contract."""

    buckets: dict[tuple[int, int, int], list[Point3D]] = {}
    for point in rectangular_obstacle_points(Pose2D(0.0, 0.0, 0.0), geometry):
        key = (
            math.floor(point.x / geometry.voxel_size_x_m),
            math.floor(point.y / geometry.voxel_size_y_m),
            math.floor(point.z / geometry.voxel_size_z_m),
        )
        buckets.setdefault(key, []).append(point)
    centroids = tuple(
        Point3D(
            sum(point.x for point in bucket) / len(bucket),
            sum(point.y for point in bucket) / len(bucket),
            sum(point.z for point in bucket) / len(bucket),
        )
        for _, bucket in sorted(buckets.items())
    )
    tolerance_squared = geometry.cluster_tolerance_m**2
    unvisited = set(range(len(centroids)))
    components: list[tuple[Point3D, ...]] = []
    while unvisited:
        seed = unvisited.pop()
        reached = {seed}
        frontier = [seed]
        while frontier:
            current = frontier.pop()
            origin = centroids[current]
            neighbors = {
                candidate
                for candidate in unvisited
                if (centroids[candidate].x - origin.x) ** 2
                + (centroids[candidate].y - origin.y) ** 2
                + (centroids[candidate].z - origin.z) ** 2
                <= tolerance_squared
            }
            unvisited.difference_update(neighbors)
            reached.update(neighbors)
            frontier.extend(neighbors)
        components.append(tuple(centroids[index] for index in sorted(reached)))
    return tuple(components)


def _closed_mapping(value: object, keys: set[str], name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    if not all(isinstance(key, str) for key in value):
        raise TypeError(f"{name} keys must be strings")
    actual = set(value)
    if actual != keys:
        raise ValueError(
            f"{name} keys must be {sorted(keys)}; missing={sorted(keys - actual)}, "
            f"unknown={sorted(actual - keys)}"
        )
    return value


def _pose_from_mapping(value: object, name: str) -> Pose2D:
    pose = _closed_mapping(value, {"x", "y", "yaw_rad"}, name)
    return Pose2D(pose["x"], pose["y"], pose["yaw_rad"])


@dataclass(frozen=True)
class ScenarioConfig:
    """Immutable inputs for the sole 009C stationary-target fixture."""

    scenario_id: str
    initial_pose_map: Pose2D
    nominal_command_speed_mps: float
    nominal_command_acceleration_mps2: float
    target_injection_pose_base_link: Pose2D
    geometry: ObstacleGeometry
    fixture_constraints: FixtureConstraints
    baseline: BaselineContract
    clocks: ClockContract
    pointcloud_rate_hz: float
    ego_state_rate_hz: float
    startup_timeout_s: float
    scenario_timeout_s: float
    allowed_outcomes: tuple[Outcome, ...]
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        typed = {
            "initial_pose_map": Pose2D,
            "target_injection_pose_base_link": Pose2D,
            "geometry": ObstacleGeometry,
            "fixture_constraints": FixtureConstraints,
            "baseline": BaselineContract,
            "clocks": ClockContract,
        }
        for name, expected_type in typed.items():
            if not isinstance(getattr(self, name), expected_type):
                raise TypeError(f"{name} must be {expected_type.__name__}")
        if not isinstance(self.allowed_outcomes, tuple) or not all(
            isinstance(outcome, Outcome) for outcome in self.allowed_outcomes
        ):
            raise TypeError("allowed_outcomes must be a tuple of Outcome values")
        if not isinstance(self.non_claims, tuple):
            raise TypeError("non_claims must be a tuple")
        if self.scenario_id != "SCN-AEBS-009C-AEB-MRM-001":
            raise ValueError("unexpected 009C scenario ID")
        object.__setattr__(
            self,
            "nominal_command_speed_mps",
            _positive_number("nominal_command_speed_mps", self.nominal_command_speed_mps),
        )
        if self.nominal_command_speed_mps <= self.baseline.ego_speed_min_mps:
            raise ValueError("nominal command speed must exceed the baseline speed threshold")
        object.__setattr__(
            self,
            "nominal_command_acceleration_mps2",
            _positive_number(
                "nominal_command_acceleration_mps2", self.nominal_command_acceleration_mps2
            ),
        )
        for name in (
            "pointcloud_rate_hz",
            "ego_state_rate_hz",
            "startup_timeout_s",
            "scenario_timeout_s",
        ):
            object.__setattr__(self, name, _positive_number(name, getattr(self, name)))
        if self.scenario_timeout_s <= self.startup_timeout_s:
            raise ValueError("scenario timeout must exceed startup timeout")
        if self.baseline.stable_duration_s >= self.startup_timeout_s:
            raise ValueError("stable baseline duration must be less than startup timeout")
        if self.target_injection_pose_base_link.x <= 0.0:
            raise ValueError("target injection pose must be ahead of the ego")
        if not math.isclose(self.target_injection_pose_base_link.y, 0.0, abs_tol=1e-12):
            raise ValueError("the closed 009C fixture requires a path-centered target")
        if not math.isclose(self.target_injection_pose_base_link.yaw_rad, 0.0, abs_tol=1e-12):
            raise ValueError("the closed 009C fixture requires an unrotated target")
        target_far_edge = self.target_injection_pose_base_link.x + self.geometry.length_m / 2.0
        if target_far_edge >= self.fixture_constraints.imu_path_max_length_m:
            raise ValueError("target must remain inside the pinned IMU-path length cap")
        pinned_floats = {
            "voxel_size_x_m": (self.geometry.voxel_size_x_m, 0.1),
            "voxel_size_y_m": (self.geometry.voxel_size_y_m, 0.1),
            "voxel_size_z_m": (self.geometry.voxel_size_z_m, 0.5),
            "cluster_tolerance_m": (self.geometry.cluster_tolerance_m, 0.15),
            "cluster_minimum_height_m": (self.geometry.cluster_minimum_height_m, 0.1),
            "imu_path_horizon_s": (self.fixture_constraints.imu_path_horizon_s, 1.5),
            "imu_path_max_length_m": (self.fixture_constraints.imu_path_max_length_m, 10.0),
        }
        for name, (actual, expected) in pinned_floats.items():
            if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError(f"{name} must match pinned fixture value {expected}")
        if self.geometry.minimum_cluster_size != 10:
            raise ValueError("minimum_cluster_size must match pinned fixture value 10")
        components = _post_voxel_components(self.geometry)
        if not any(
            len(component) >= self.geometry.minimum_cluster_size
            and max(point.z for point in component) > self.geometry.cluster_minimum_height_m
            for component in components
        ):
            raise ValueError(
                "generated obstacle must retain a sufficiently large and tall post-voxel cluster"
            )
        if len(self.allowed_outcomes) != len(Outcome) or set(self.allowed_outcomes) != set(Outcome):
            raise ValueError("allowed_outcomes must contain the closed outcome vocabulary once")
        if self.non_claims != REQUIRED_NON_CLAIMS:
            raise ValueError("non_claims must match the closed 009C claim-boundary set")

    @classmethod
    def from_mapping(cls, value: object) -> "ScenarioConfig":
        root = _closed_mapping(
            value,
            {
                "schema",
                "scenario_id",
                "initial_ego",
                "nominal_control",
                "target",
                "fixture_constraints",
                "baseline",
                "publication",
                "timeouts",
                "clocks",
                "allowed_outcomes",
                "non_claims",
            },
            "scenario",
        )
        if root["schema"] != "de4sdv.aebs-009c-scenario.v1":
            raise ValueError("unsupported scenario schema")
        initial = _closed_mapping(root["initial_ego"], {"pose_map"}, "initial_ego")
        nominal = _closed_mapping(
            root["nominal_control"], {"speed_mps", "acceleration_mps2"}, "nominal_control"
        )
        target = _closed_mapping(
            root["target"], {"stationary", "injection_pose_base_link", "geometry"}, "target"
        )
        if target["stationary"] is not True:
            raise ValueError("009C target must be stationary")
        geometry = _closed_mapping(
            target["geometry"],
            {
                "length_m",
                "width_m",
                "height_m",
                "point_spacing_m",
                "voxel_size_x_m",
                "voxel_size_y_m",
                "voxel_size_z_m",
                "cluster_tolerance_m",
                "cluster_minimum_height_m",
                "minimum_cluster_size",
            },
            "target.geometry",
        )
        constraints = _closed_mapping(
            root["fixture_constraints"],
            {"imu_path_horizon_s", "imu_path_max_length_m"},
            "fixture_constraints",
        )
        baseline = _closed_mapping(
            root["baseline"],
            {
                "stable_duration_s",
                "ego_speed_min_mps",
                "required_input_max_age_s",
                "diagnostic_node",
                "diagnostic_task",
                "diagnostic_joined_key",
                "required_inputs",
                "diagnostic_level",
                "autonomous_available",
                "mrm_state",
                "mrm_behavior",
                "emergency_operator_state",
                "gate_path",
            },
            "baseline",
        )
        publication = _closed_mapping(
            root["publication"], {"pointcloud_rate_hz", "ego_state_rate_hz"}, "publication"
        )
        timeouts = _closed_mapping(root["timeouts"], {"startup_s", "scenario_s"}, "timeouts")
        clocks = _closed_mapping(
            root["clocks"],
            {
                "source_stamp",
                "receipt_time",
                "host_utc",
                "causal_order",
                "cross_domain_comparison",
            },
            "clocks",
        )
        raw_outcomes = root["allowed_outcomes"]
        raw_non_claims = root["non_claims"]
        if not isinstance(raw_outcomes, list):
            raise TypeError("allowed_outcomes must be a list")
        if not isinstance(raw_non_claims, list):
            raise TypeError("non_claims must be a list")
        raw_required_inputs = baseline["required_inputs"]
        if not isinstance(raw_required_inputs, list):
            raise TypeError("baseline.required_inputs must be a list")
        baseline_values = dict(baseline)
        baseline_values["required_inputs"] = tuple(raw_required_inputs)
        try:
            outcomes = tuple(Outcome(item) for item in raw_outcomes)
        except (TypeError, ValueError) as error:
            raise ValueError("allowed_outcomes contains an unknown outcome") from error
        if not isinstance(root["scenario_id"], str):
            raise TypeError("scenario_id must be a string")
        return cls(
            scenario_id=root["scenario_id"],
            initial_pose_map=_pose_from_mapping(initial["pose_map"], "initial_ego.pose_map"),
            nominal_command_speed_mps=nominal["speed_mps"],
            nominal_command_acceleration_mps2=nominal["acceleration_mps2"],
            target_injection_pose_base_link=_pose_from_mapping(
                target["injection_pose_base_link"], "target.injection_pose_base_link"
            ),
            geometry=ObstacleGeometry(**geometry),
            fixture_constraints=FixtureConstraints(**constraints),
            baseline=BaselineContract(**baseline_values),
            clocks=ClockContract(**clocks),
            pointcloud_rate_hz=publication["pointcloud_rate_hz"],
            ego_state_rate_hz=publication["ego_state_rate_hz"],
            startup_timeout_s=timeouts["startup_s"],
            scenario_timeout_s=timeouts["scenario_s"],
            allowed_outcomes=outcomes,
            non_claims=tuple(raw_non_claims),
        )

    def to_mapping(self) -> dict[str, Any]:
        """Return a fresh serializable mapping for validator mutation tests."""

        def pose(item: Pose2D) -> dict[str, float]:
            return {"x": item.x, "y": item.y, "yaw_rad": item.yaw_rad}

        return {
            "schema": "de4sdv.aebs-009c-scenario.v1",
            "scenario_id": self.scenario_id,
            "initial_ego": {"pose_map": pose(self.initial_pose_map)},
            "nominal_control": {
                "speed_mps": self.nominal_command_speed_mps,
                "acceleration_mps2": self.nominal_command_acceleration_mps2,
            },
            "target": {
                "stationary": True,
                "injection_pose_base_link": pose(self.target_injection_pose_base_link),
                "geometry": {
                    "length_m": self.geometry.length_m,
                    "width_m": self.geometry.width_m,
                    "height_m": self.geometry.height_m,
                    "point_spacing_m": self.geometry.point_spacing_m,
                    "voxel_size_x_m": self.geometry.voxel_size_x_m,
                    "voxel_size_y_m": self.geometry.voxel_size_y_m,
                    "voxel_size_z_m": self.geometry.voxel_size_z_m,
                    "cluster_tolerance_m": self.geometry.cluster_tolerance_m,
                    "cluster_minimum_height_m": self.geometry.cluster_minimum_height_m,
                    "minimum_cluster_size": self.geometry.minimum_cluster_size,
                },
            },
            "fixture_constraints": {
                "imu_path_horizon_s": self.fixture_constraints.imu_path_horizon_s,
                "imu_path_max_length_m": self.fixture_constraints.imu_path_max_length_m,
            },
            "baseline": {
                "stable_duration_s": self.baseline.stable_duration_s,
                "ego_speed_min_mps": self.baseline.ego_speed_min_mps,
                "required_input_max_age_s": self.baseline.required_input_max_age_s,
                "diagnostic_node": self.baseline.diagnostic_node,
                "diagnostic_task": self.baseline.diagnostic_task,
                "diagnostic_joined_key": self.baseline.diagnostic_joined_key,
                "required_inputs": list(self.baseline.required_inputs),
                "diagnostic_level": self.baseline.diagnostic_level,
                "autonomous_available": self.baseline.autonomous_available,
                "mrm_state": self.baseline.mrm_state,
                "mrm_behavior": self.baseline.mrm_behavior,
                "emergency_operator_state": self.baseline.emergency_operator_state,
                "gate_path": self.baseline.gate_path,
            },
            "publication": {
                "pointcloud_rate_hz": self.pointcloud_rate_hz,
                "ego_state_rate_hz": self.ego_state_rate_hz,
            },
            "timeouts": {
                "startup_s": self.startup_timeout_s,
                "scenario_s": self.scenario_timeout_s,
            },
            "clocks": {
                "source_stamp": self.clocks.source_stamp,
                "receipt_time": self.clocks.receipt_time,
                "host_utc": self.clocks.host_utc,
                "causal_order": self.clocks.causal_order,
                "cross_domain_comparison": self.clocks.cross_domain_comparison,
            },
            "allowed_outcomes": [outcome.value for outcome in self.allowed_outcomes],
            "non_claims": list(self.non_claims),
        }


def load_scenario_config(path: str | Path) -> ScenarioConfig:
    """Load and strictly validate a YAML scenario fixture."""

    with Path(path).open("r", encoding="utf-8") as stream:
        return ScenarioConfig.from_mapping(yaml.safe_load(stream))
