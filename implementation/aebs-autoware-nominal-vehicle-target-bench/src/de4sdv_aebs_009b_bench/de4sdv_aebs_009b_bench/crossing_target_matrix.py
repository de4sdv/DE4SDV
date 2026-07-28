"""Pure INC-AEBS-009G/009H crossing-target matrix over 009B observations.

The matrix deliberately reuses the pinned bench's native RSS, warning, AEB
intervention diagnostic, and braking-request observations.  ROS adapters may
construct the inputs, but all authorization and verdict logic stays middleware
independent and fail closed.

009G is a pedestrian crossing-target scenario.  009H is a bicycle crossing-target
scenario.  Both share the crossing-target pattern: the target moves laterally
(perpendicular to the ego direction of travel) across the ego path.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum
from pathlib import Path
from typing import Any

import yaml

from .footprint_geometry import FootprintRelation, _overlap, _point_segment_distance, ego_corners
from .scenario_contract import Pose2D, VehicleFootprint, _finite_number, _positive_number
from .scenario_evaluator import Observation, ObservationKind

_STAMP = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{9}\Z")


class TargetType(str, Enum):
    """Crossing target type vocabulary for 009G/009H."""

    PEDESTRIAN = "pedestrian"
    BICYCLE = "bicycle"


class CrossingEvidenceOutcome(str, Enum):
    """Closed terminal outcome vocabulary for one crossing-target scenario."""

    PASS_BOUNDED_TARGET_RESPONSE = "passBoundedTargetResponse"
    FAIL_CONFIGURED_OUTCOME = "failConfiguredOutcome"
    INCONCLUSIVE_COVERAGE = "inconclusiveCoverage"
    ERROR_EVIDENCE = "errorEvidence"


@dataclass(frozen=True)
class CrossingTargetGeometry:
    """Geometry for one crossing target type."""

    length_m: float
    width_m: float
    height_m: float

    def __post_init__(self) -> None:
        for name in ("length_m", "width_m", "height_m"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a number")
            normalized = float(value)
            if not math.isfinite(normalized) or normalized <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
            object.__setattr__(self, name, normalized)


EXPECTED_GEOMETRY: Mapping[TargetType, CrossingTargetGeometry] = {
    TargetType.PEDESTRIAN: CrossingTargetGeometry(0.3, 0.5, 1.8),
    TargetType.BICYCLE: CrossingTargetGeometry(1.8, 0.6, 1.2),
}


@dataclass(frozen=True)
class CrossingTargetContract:
    """Behavioral contract for one crossing-target scenario execution."""

    max_source_age_s: float
    closed_window_s: float
    crossing_speed_mps: float
    diagnostic_node: str = "autonomous_emergency_braking"
    diagnostic_task: str = "aeb_emergency_stop"
    diagnostic_level: str = "ERROR"
    diagnostic_message: str = "[AEB]: Emergency Brake"

    def __post_init__(self) -> None:
        for name in ("max_source_age_s", "closed_window_s", "crossing_speed_mps"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise TypeError(f"{name} must be a number")
            normalized = float(value)
            if not math.isfinite(normalized) or normalized <= 0.0:
                raise ValueError(f"{name} must be finite and positive")
            object.__setattr__(self, name, normalized)
        for name in (
            "diagnostic_node",
            "diagnostic_task",
            "diagnostic_level",
            "diagnostic_message",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise TypeError(f"{name} must be a nonempty string")


@dataclass(frozen=True)
class CrossingTargetSample:
    """One map-frame crossing-target observation sample."""

    received: bool
    target_pose_map: Pose2D | None
    ego_pose_map: Pose2D | None
    source_stamp: str | None

    def __post_init__(self) -> None:
        if type(self.received) is not bool:
            raise TypeError("received must be boolean")
        if self.received:
            if not isinstance(self.target_pose_map, Pose2D):
                raise TypeError("received target_pose_map must be Pose2D")
            if not isinstance(self.ego_pose_map, Pose2D):
                raise TypeError("received ego_pose_map must be Pose2D")
            if self.source_stamp is not None and not isinstance(self.source_stamp, str):
                raise TypeError("source_stamp must be a string or None")
        elif (
            self.target_pose_map is not None
            or self.ego_pose_map is not None
            or self.source_stamp is not None
        ):
            raise ValueError("a missing sample cannot carry a pose or source stamp")


@dataclass(frozen=True)
class DiagnosticAuthorization:
    """Authorization diagnostic tied to one native AEB intervention."""

    source_stamp: str
    node: str
    task: str
    level: str
    message: str

    def __post_init__(self) -> None:
        for name in ("source_stamp", "node", "task", "level", "message"):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise TypeError(f"{name} must be a nonempty string")


@dataclass(frozen=True)
class CrossingTargetScenarioResult:
    """One independent closed verdict for exactly one crossing-target scenario."""

    target_type: TargetType
    passed: bool
    outcome: CrossingEvidenceOutcome
    crossing_trajectory_observation_index: int | None
    native_intervention_observation_index: int | None
    braking_request_observation_index: int | None
    footprint_reconstruction_observation_index: int | None
    authorization_diagnostic_source_stamp: str
    reason: str


@dataclass(frozen=True)
class CrossingTargetScenarioConfig:
    """Immutable inputs for one 009G/009H crossing-target fixture."""

    scenario_id: str
    increment_id: str
    target_type: TargetType
    geometry: CrossingTargetGeometry
    ego_footprint: VehicleFootprint
    contract: CrossingTargetContract
    non_claims: tuple[str, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.target_type, TargetType):
            raise TypeError("target_type must be TargetType")
        if not isinstance(self.geometry, CrossingTargetGeometry):
            raise TypeError("geometry must be CrossingTargetGeometry")
        if not isinstance(self.ego_footprint, VehicleFootprint):
            raise TypeError("ego_footprint must be VehicleFootprint")
        if not isinstance(self.contract, CrossingTargetContract):
            raise TypeError("contract must be CrossingTargetContract")
        if not isinstance(self.non_claims, tuple):
            raise TypeError("non_claims must be a tuple")
        expected = EXPECTED_GEOMETRY[self.target_type]
        if self.geometry != expected:
            raise ValueError(
                f"geometry must match the pinned {self.target_type.value} target geometry"
            )
        valid_ids = {
            (TargetType.PEDESTRIAN, "INC-AEBS-009G", "SCN-AEBS-009G-PEDESTRIAN-CROSSING-001"),
            (TargetType.BICYCLE, "INC-AEBS-009H", "SCN-AEBS-009H-BICYCLE-CROSSING-001"),
        }
        if (self.target_type, self.increment_id, self.scenario_id) not in valid_ids:
            raise ValueError("crossing-target scenario identity is incorrect")


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

Point2D = tuple[float, float]


def _crossing_target_corners(
    pose: Pose2D, geometry: CrossingTargetGeometry
) -> tuple[Point2D, ...]:
    """Return the four oriented corners of a crossing target from map pose."""

    half_length = geometry.length_m / 2.0
    half_width = geometry.width_m / 2.0
    cosine = math.cos(pose.yaw_rad)
    sine = math.sin(pose.yaw_rad)
    return tuple(
        (pose.x + cosine * x - sine * y, pose.y + sine * x + cosine * y)
        for x, y in (
            (half_length, half_width),
            (half_length, -half_width),
            (-half_length, -half_width),
            (-half_length, half_width),
        )
    )


def _crossing_footprint_relation(
    ego_pose: Pose2D,
    ego_footprint: VehicleFootprint,
    target_pose: Pose2D,
    target_geometry: CrossingTargetGeometry,
) -> FootprintRelation:
    """Compute overlap and Euclidean polygon separation from map poses only."""

    ego = ego_corners(ego_pose, ego_footprint)
    target = _crossing_target_corners(target_pose, target_geometry)
    if _overlap(ego, target):
        return FootprintRelation(overlap=True, separation_m=0.0)
    distances: list[float] = []
    for polygon, other in ((ego, target), (target, ego)):
        edges = tuple(zip(other, other[1:] + other[:1]))
        distances.extend(
            _point_segment_distance(point, start, end)
            for point in polygon
            for start, end in edges
        )
    return FootprintRelation(overlap=False, separation_m=min(distances))


# ---------------------------------------------------------------------------
# Stamp helpers
# ---------------------------------------------------------------------------


def _stamp_decimal(value: str | None) -> Decimal | None:
    if value is None or _STAMP.fullmatch(value) is None:
        return None
    try:
        stamp = Decimal(value)
    except InvalidOperation:
        return None
    return stamp if stamp > 0 else None


def _is_crossing_trajectory(target_pose: Pose2D, ego_pose: Pose2D) -> bool:
    """Check that the target motion direction is perpendicular to the ego."""

    relative_yaw = target_pose.yaw_rad - ego_pose.yaw_rad
    normalized = (relative_yaw + math.pi) % (2.0 * math.pi) - math.pi
    return math.isclose(abs(normalized), math.pi / 2.0, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# Evaluator
# ---------------------------------------------------------------------------


def evaluate_crossing_target_scenario(
    contract: CrossingTargetContract,
    target_type: TargetType,
    geometry: CrossingTargetGeometry,
    ego_footprint: VehicleFootprint,
    sample: CrossingTargetSample,
    authorization: DiagnosticAuthorization,
    observations: Iterable[Observation],
    *,
    window_end_receipt_s: float,
) -> CrossingTargetScenarioResult:
    """Return one independent closed verdict for exactly one crossing-target scenario."""

    if not isinstance(contract, CrossingTargetContract):
        raise TypeError("contract must be CrossingTargetContract")
    if not isinstance(target_type, TargetType):
        raise TypeError("target_type must be TargetType")
    if not isinstance(geometry, CrossingTargetGeometry):
        raise TypeError("geometry must be CrossingTargetGeometry")
    if not isinstance(ego_footprint, VehicleFootprint):
        raise TypeError("ego_footprint must be VehicleFootprint")
    if not isinstance(sample, CrossingTargetSample):
        raise TypeError("sample must be CrossingTargetSample")
    if not isinstance(authorization, DiagnosticAuthorization):
        raise TypeError("authorization must be DiagnosticAuthorization")
    if isinstance(window_end_receipt_s, bool) or not isinstance(
        window_end_receipt_s, (int, float)
    ):
        raise TypeError("window_end_receipt_s must be a number")
    window_end = float(window_end_receipt_s)
    if not math.isfinite(window_end) or window_end < 0.0:
        raise ValueError("window_end_receipt_s must be finite and nonnegative")
    items = tuple(observations)
    if any(not isinstance(item, Observation) for item in items):
        raise TypeError("observations must contain only 009B Observation values")

    def result(
        passed: bool,
        outcome: CrossingEvidenceOutcome,
        reason: str,
        crossing_index: int | None = None,
        intervention_index: int | None = None,
        brake_index: int | None = None,
        footprint_index: int | None = None,
    ) -> CrossingTargetScenarioResult:
        return CrossingTargetScenarioResult(
            target_type,
            passed,
            outcome,
            crossing_index,
            intervention_index,
            brake_index,
            footprint_index,
            authorization.source_stamp,
            reason,
        )

    # --- 1. Sample received and valid --------------------------------------
    if not sample.received:
        return result(
            False,
            CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE,
            "crossing-target sample was not received",
        )

    assert sample.target_pose_map is not None
    assert sample.ego_pose_map is not None
    target_pose_map = sample.target_pose_map
    ego_pose_map = sample.ego_pose_map

    # --- 2. Source stamp freshness -----------------------------------------
    source = _stamp_decimal(sample.source_stamp)
    diagnostic = _stamp_decimal(authorization.source_stamp)
    if source is None or diagnostic is None:
        return result(
            False,
            CrossingEvidenceOutcome.ERROR_EVIDENCE,
            "crossing-target source stamp or authorization stamp is malformed",
        )
    age = diagnostic - source
    if age < 0:
        return result(
            False,
            CrossingEvidenceOutcome.ERROR_EVIDENCE,
            "crossing-target source stamp is future-stamped relative to authorization",
        )
    if age > Decimal(str(contract.max_source_age_s)):
        return result(
            False,
            CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE,
            "crossing-target source is stale beyond the configured maximum age",
        )

    # --- 3. Crossing trajectory perpendicular -------------------------------
    if not _is_crossing_trajectory(target_pose_map, ego_pose_map):
        return result(
            False,
            CrossingEvidenceOutcome.FAIL_CONFIGURED_OUTCOME,
            "target trajectory is not perpendicular to the ego direction",
        )

    # --- 4. Geometry matches target type ------------------------------------
    expected_geometry = EXPECTED_GEOMETRY[target_type]
    if geometry != expected_geometry:
        return result(
            False,
            CrossingEvidenceOutcome.FAIL_CONFIGURED_OUTCOME,
            f"geometry does not match the pinned {target_type.value} target geometry",
        )

    # --- 5. Native AEB intervention chain ------------------------------------
    risk = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if item.kind is ObservationKind.RISK_ASSESSMENT
            and item.payload["warning"] is True
            and item.payload["intervention"] is False
        ),
        None,
    )
    if risk is None:
        return result(
            False,
            CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE,
            "native risk assessment was not observed for the crossing target",
        )

    warning = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if risk is not None
            and item.kind is ObservationKind.WARNING_REQUEST
            and item.receipt_monotonic_s > risk[1].receipt_monotonic_s
            and item.payload["active"] is True
        ),
        None,
    )
    if warning is None:
        return result(
            False,
            CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE,
            "native warning request was not observed for the crossing target",
        )

    diagnostic_obs = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if warning is not None
            and item.kind is ObservationKind.DIAGNOSTIC
            and item.receipt_monotonic_s > warning[1].receipt_monotonic_s
            and item.source_stamp == authorization.source_stamp
            and item.payload
            == {
                "node": contract.diagnostic_node,
                "task": contract.diagnostic_task,
                "level": contract.diagnostic_level,
            }
        ),
        None,
    )
    if diagnostic_obs is None:
        return result(
            False,
            CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE,
            "native AEB diagnostic was not observed for the crossing target",
        )

    intervention = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if diagnostic_obs is not None
            and item.kind is ObservationKind.AEB_INTERVENTION
            and item.source_stamp == authorization.source_stamp
            and item.receipt_monotonic_s == diagnostic_obs[1].receipt_monotonic_s
            and item.payload["node"] == contract.diagnostic_node
            and item.payload["task"] == contract.diagnostic_task
            and item.payload["level"] == contract.diagnostic_level
            and item.payload["message"] == contract.diagnostic_message
            and item.payload["object_distance_m"] <= item.payload["rss_distance_m"]
        ),
        None,
    )
    if intervention is None:
        return result(
            False,
            CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE,
            "native AEB intervention was not observed for the crossing target",
        )

    # --- 6. Authorization exact match --------------------------------------
    authorization_exact = (
        authorization.node == contract.diagnostic_node
        and authorization.task == contract.diagnostic_task
        and authorization.level == contract.diagnostic_level
        and authorization.message == contract.diagnostic_message
    )
    if not authorization_exact:
        return result(
            False,
            CrossingEvidenceOutcome.ERROR_EVIDENCE,
            "authorization did not exact-match the observed native AEB diagnostic source",
            risk[0],
            intervention[0],
        )

    # --- 7. Independent footprint reconstruction ----------------------------
    footprint_states = [
        (index, item)
        for index, item in enumerate(items)
        if item.kind is ObservationKind.FOOTPRINT_STATE
        and item.receipt_monotonic_s > intervention[1].receipt_monotonic_s
    ]
    if not footprint_states:
        return result(
            False,
            CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE,
            "no footprint-state observations were retained after intervention",
            risk[0],
            intervention[0],
        )

    reconstructed: list[tuple[int, Observation, FootprintRelation]] = []
    for index, item in footprint_states:
        ego_pose = Pose2D(
            item.payload["ego_x"],
            item.payload["ego_y"],
            item.payload["ego_yaw_rad"],
        )
        target_pose = Pose2D(
            item.payload["target_x"],
            item.payload["target_y"],
            item.payload["target_yaw_rad"],
        )
        relation = _crossing_footprint_relation(
            ego_pose, ego_footprint, target_pose, geometry
        )
        if relation.overlap is not item.payload["overlap"] or not math.isclose(
            relation.separation_m,
            item.payload["separation_m"],
            rel_tol=0.0,
            abs_tol=1e-6,
        ):
            return result(
                False,
                CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE,
                "recorded footprint relation does not replay from preserved map poses",
                risk[0],
                intervention[0],
                None,
                index,
            )
        reconstructed.append((index, item, relation))

    # Reject contradictory samples: separation must be non-overlapping
    if any(r.overlap for _, _, r in reconstructed):
        return result(
            False,
            CrossingEvidenceOutcome.FAIL_CONFIGURED_OUTCOME,
            "independent footprint reconstruction detected an overlap after intervention",
            risk[0],
            intervention[0],
            None,
            next(idx for idx, _, r in reconstructed if r.overlap),
        )

    footprint_index = reconstructed[-1][0]

    # --- 8. Braking request after intervention ------------------------------
    brake = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if item.kind is ObservationKind.BRAKING_REQUEST
            and item.receipt_monotonic_s >= intervention[1].receipt_monotonic_s
        ),
        None,
    )
    if brake is None:
        if window_end - intervention[1].receipt_monotonic_s < contract.closed_window_s:
            return result(
                False,
                CrossingEvidenceOutcome.INCONCLUSIVE_COVERAGE,
                "post-intervention braking-observation window is not closed",
                risk[0],
                intervention[0],
                None,
                footprint_index,
            )
        return result(
            False,
            CrossingEvidenceOutcome.FAIL_CONFIGURED_OUTCOME,
            "bounded target response did not produce a braking request",
            risk[0],
            intervention[0],
            None,
            footprint_index,
        )

    # --- 9. All checks pass: bounded target response ------------------------
    return result(
        True,
        CrossingEvidenceOutcome.PASS_BOUNDED_TARGET_RESPONSE,
        "native AEB intervention observed for the crossing target with independent footprint reconstruction",
        risk[0],
        intervention[0],
        brake[0],
        footprint_index,
    )


# ---------------------------------------------------------------------------
# Serialization
# ---------------------------------------------------------------------------


def crossing_target_result_to_json(
    result: CrossingTargetScenarioResult,
) -> dict[str, object]:
    """Serialize one crossing-target verdict for replayable evidence."""

    value = asdict(result)
    value["target_type"] = result.target_type.value
    value["outcome"] = result.outcome.value
    return value


# ---------------------------------------------------------------------------
# Config loading
# ---------------------------------------------------------------------------


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


def load_crossing_target_config(
    path: str | Path,
) -> CrossingTargetScenarioConfig:
    """Load and strictly validate a YAML crossing-target scenario fixture."""

    try:
        raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(f"cannot load crossing-target config: {error}") from error

    root = _closed_mapping(
        raw,
        {
            "schema",
            "increment_id",
            "scenario_id",
            "target_type",
            "target",
            "ego_footprint",
            "contract",
            "non_claims",
        },
        "scenario",
    )

    schema = root["schema"]
    valid_schemas = {
        TargetType.PEDESTRIAN: "de4sdv.aebs-009g-pedestrian-crossing.v1",
        TargetType.BICYCLE: "de4sdv.aebs-009h-bicycle-crossing.v1",
    }

    try:
        target_type = TargetType(root["target_type"])
    except (TypeError, ValueError) as error:
        raise ValueError("unknown crossing target_type") from error

    if schema != valid_schemas[target_type]:
        raise ValueError("crossing-target schema does not match target_type")

    increment_id = root["increment_id"]
    scenario_id = root["scenario_id"]
    valid_ids = {
        TargetType.PEDESTRIAN: ("INC-AEBS-009G", "SCN-AEBS-009G-PEDESTRIAN-CROSSING-001"),
        TargetType.BICYCLE: ("INC-AEBS-009H", "SCN-AEBS-009H-BICYCLE-CROSSING-001"),
    }
    if (increment_id, scenario_id) != valid_ids[target_type]:
        raise ValueError("crossing-target increment or scenario identity is incorrect")

    target = _closed_mapping(
        root["target"],
        {"geometry", "crossing_speed_mps", "injection_pose_base_link"},
        "target",
    )
    geometry_raw = _closed_mapping(
        target["geometry"],
        {"length_m", "width_m", "height_m"},
        "target.geometry",
    )
    ego_footprint_raw = _closed_mapping(
        root["ego_footprint"],
        {"front_offset_m", "rear_offset_m", "width_m"},
        "ego_footprint",
    )
    contract_raw = _closed_mapping(
        root["contract"],
        {
            "max_source_age_s",
            "closed_window_s",
            "crossing_speed_mps",
            "diagnostic_node",
            "diagnostic_task",
            "diagnostic_level",
            "diagnostic_message",
        },
        "contract",
    )
    non_claims = root["non_claims"]
    if not isinstance(non_claims, list):
        raise TypeError("non_claims must be a list")

    geometry = CrossingTargetGeometry(
        geometry_raw["length_m"],
        geometry_raw["width_m"],
        geometry_raw["height_m"],
    )
    ego_footprint = VehicleFootprint(**ego_footprint_raw)
    contract = CrossingTargetContract(
        max_source_age_s=contract_raw["max_source_age_s"],
        closed_window_s=contract_raw["closed_window_s"],
        crossing_speed_mps=contract_raw["crossing_speed_mps"],
        diagnostic_node=contract_raw["diagnostic_node"],
        diagnostic_task=contract_raw["diagnostic_task"],
        diagnostic_level=contract_raw["diagnostic_level"],
        diagnostic_message=contract_raw["diagnostic_message"],
    )

    return CrossingTargetScenarioConfig(
        scenario_id=scenario_id,
        increment_id=increment_id,
        target_type=target_type,
        geometry=geometry,
        ego_footprint=ego_footprint,
        contract=contract,
        non_claims=tuple(non_claims),
    )
