"""Pure INC-AEBS-009F degraded-input matrix over 009B observations.

The matrix reuses the pinned bench's native RSS, warning, AEB intervention
diagnostic, and braking-request observations.  ROS adapters may construct the
inputs, but all degraded-input authorization and verdict logic stays middleware
independent and fail closed.  Observer failure must be inconclusive, NEVER pass.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import yaml

from .scenario_evaluator import Observation, ObservationKind


class DegradedInputScenario(str, Enum):
    STALE_INPUT = "stale_input"
    MISSING_INPUT = "missing_input"
    MALFORMED_INPUT = "malformed_input"
    INCONSISTENT_INPUT = "inconsistent_input"
    UNAVAILABLE_INPUT = "unavailable_input"


class DegradedInputDisposition(str, Enum):
    PASS_BOUNDED_DETECTION = "pass_bounded_detection"
    FAIL_WRONG_DISPOSITION = "fail_wrong_disposition"
    INCONCLUSIVE_INSTRUMENTATION = "inconclusive_instrumentation"
    ERROR_EVIDENCE = "error_evidence"


@dataclass(frozen=True)
class DegradedInputMatrixContract:
    degraded_state_max_age_s: float
    closed_detection_window_s: float
    diagnostic_node: str = "autonomous_emergency_braking"
    diagnostic_task: str = "aeb_emergency_stop"
    diagnostic_level: str = "ERROR"
    diagnostic_message: str = "[AEB]: Emergency Brake"

    def __post_init__(self) -> None:
        for name in ("degraded_state_max_age_s", "closed_detection_window_s"):
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
class DegradedInputAuthorization:
    """Typed authorization record extracted from a DEGRADED_INPUT_AUTHORIZATION observation."""

    degraded_input_profile: str
    affected_topic: str
    input_health: str
    degraded_state_source_stamp: str
    authorization_diagnostic_source_stamp: str
    disposition: str

    def __post_init__(self) -> None:
        for name in (
            "degraded_input_profile",
            "affected_topic",
            "input_health",
            "degraded_state_source_stamp",
            "authorization_diagnostic_source_stamp",
            "disposition",
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise TypeError(f"{name} must be a nonempty string")


@dataclass(frozen=True)
class DegradedInputScenarioResult:
    scenario: DegradedInputScenario
    passed: bool
    disposition: DegradedInputDisposition
    degraded_input_profile: str
    affected_topic: str
    input_health: str
    degraded_state_source_stamp: str
    authorization_diagnostic_source_stamp: str
    authorization_observation_index: int | None
    transition_observation_index: int | None
    status_observation_index: int | None
    reason: str


# ---------------------------------------------------------------------------
# Matrix config loading (runtime/replay policy)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatrixScenario:
    scenario_id: str
    expected_disposition: DegradedInputDisposition
    expected_input_health: str


@dataclass(frozen=True)
class MatrixConfig:
    contract: DegradedInputMatrixContract
    graph_sampling_max_gap_s: float
    expected_nominal_publisher: str
    scenarios: Mapping[DegradedInputScenario, MatrixScenario]


def load_matrix_contract(path: str | Path) -> MatrixConfig:
    """Load the exact five-profile matrix and reject an open/ambiguous contract."""
    try:
        value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(f"cannot load 009F matrix: {error}") from error
    required_root = {
        "schema",
        "inherits_runtime",
        "source_topic",
        "native_observations",
        "contract",
        "scenarios",
        "non_claims",
    }
    if not isinstance(value, Mapping) or set(value) != required_root:
        raise ValueError("009F matrix root does not match the closed contract")
    if (
        value["schema"] != "de4sdv.aebs-009f-degraded-input-matrix.v1"
        or value["inherits_runtime"] != "INC-AEBS-009B"
    ):
        raise ValueError("009F matrix identity or inherited runtime is incorrect")
    contract = value["contract"]
    required_contract = {
        "degraded_state_max_age_s",
        "closed_detection_window_s",
        "graph_sampling_max_gap_s",
        "expected_nominal_publisher",
        "diagnostic_node",
        "diagnostic_task",
        "diagnostic_level",
        "diagnostic_message",
    }
    if not isinstance(contract, Mapping) or set(contract) != required_contract:
        raise ValueError("009F matrix behavior contract is open or incomplete")
    gap = contract["graph_sampling_max_gap_s"]
    if (
        isinstance(gap, bool)
        or not isinstance(gap, (int, float))
        or not math.isfinite(float(gap))
        or gap <= 0
    ):
        raise ValueError("graph_sampling_max_gap_s must be finite and positive")
    publisher = contract["expected_nominal_publisher"]
    if not isinstance(publisher, str) or not publisher:
        raise ValueError("expected_nominal_publisher must be nonempty")
    entries = value["scenarios"]
    if not isinstance(entries, list):
        raise TypeError("009F scenarios must be a list")
    scenarios: dict[DegradedInputScenario, MatrixScenario] = {}
    canonical: dict[DegradedInputScenario, tuple[DegradedInputDisposition, str]] = {
        DegradedInputScenario.STALE_INPUT: (
            DegradedInputDisposition.PASS_BOUNDED_DETECTION,
            "stale",
        ),
        DegradedInputScenario.MISSING_INPUT: (
            DegradedInputDisposition.PASS_BOUNDED_DETECTION,
            "missing",
        ),
        DegradedInputScenario.MALFORMED_INPUT: (
            DegradedInputDisposition.PASS_BOUNDED_DETECTION,
            "malformed",
        ),
        DegradedInputScenario.INCONSISTENT_INPUT: (
            DegradedInputDisposition.PASS_BOUNDED_DETECTION,
            "inconsistent",
        ),
        DegradedInputScenario.UNAVAILABLE_INPUT: (
            DegradedInputDisposition.PASS_BOUNDED_DETECTION,
            "unavailable",
        ),
    }
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != {
            "id",
            "profile",
            "expected_disposition",
            "expected_input_health",
        }:
            raise ValueError("009F scenario entry has an open or incomplete shape")
        try:
            profile = DegradedInputScenario(entry["profile"])
            disposition = DegradedInputDisposition(entry["expected_disposition"])
        except (TypeError, ValueError) as error:
            raise ValueError(
                "009F scenario has an unknown profile or disposition"
            ) from error
        if profile in scenarios:
            raise ValueError("each closed 009F profile must occur exactly once")
        if not isinstance(entry["id"], str) or not entry["id"].startswith(
            "SCN-AEBS-009F-"
        ):
            raise ValueError("009F scenario ID is invalid")
        if not isinstance(entry["expected_input_health"], str) or not entry[
            "expected_input_health"
        ]:
            raise TypeError("expected_input_health must be a nonempty string")
        if (disposition, entry["expected_input_health"]) != canonical[profile]:
            raise ValueError(
                "009F scenario disposition/input-health expectation contradicts its closed profile"
            )
        scenarios[profile] = MatrixScenario(
            entry["id"], disposition, entry["expected_input_health"]
        )
    if set(scenarios) != set(DegradedInputScenario):
        raise ValueError("each closed 009F profile must occur exactly once")
    return MatrixConfig(
        DegradedInputMatrixContract(
            contract["degraded_state_max_age_s"],
            contract["closed_detection_window_s"],
            contract["diagnostic_node"],
            contract["diagnostic_task"],
            contract["diagnostic_level"],
            contract["diagnostic_message"],
        ),
        float(gap),
        publisher,
        scenarios,
    )


# ---------------------------------------------------------------------------
# Pure evaluator
# ---------------------------------------------------------------------------


def _expected_input_health(scenario: DegradedInputScenario) -> str:
    return {
        DegradedInputScenario.STALE_INPUT: "stale",
        DegradedInputScenario.MISSING_INPUT: "missing",
        DegradedInputScenario.MALFORMED_INPUT: "malformed",
        DegradedInputScenario.INCONSISTENT_INPUT: "inconsistent",
        DegradedInputScenario.UNAVAILABLE_INPUT: "unavailable",
    }[scenario]


def evaluate_degraded_input_scenario(
    contract: DegradedInputMatrixContract,
    scenario: DegradedInputScenario,
    authorization: DegradedInputAuthorization,
    observations: Iterable[Observation],
    *,
    window_end_receipt_s: float,
) -> DegradedInputScenarioResult:
    """Return one independent closed verdict for exactly one matrix scenario."""

    if not isinstance(contract, DegradedInputMatrixContract):
        raise TypeError("contract must be DegradedInputMatrixContract")
    if not isinstance(scenario, DegradedInputScenario):
        raise TypeError("scenario must be DegradedInputScenario")
    if not isinstance(authorization, DegradedInputAuthorization):
        raise TypeError("authorization must be DegradedInputAuthorization")
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
        disposition: DegradedInputDisposition,
        reason: str,
        auth_index: int | None = None,
        transition_index: int | None = None,
        status_index: int | None = None,
    ) -> DegradedInputScenarioResult:
        return DegradedInputScenarioResult(
            scenario,
            passed,
            disposition,
            authorization.degraded_input_profile,
            authorization.affected_topic,
            authorization.input_health,
            authorization.degraded_state_source_stamp,
            authorization.authorization_diagnostic_source_stamp,
            auth_index,
            transition_index,
            status_index,
            reason,
        )

    # Find the DEGRADED_STATE_TRANSITION matching the authorization's source stamp.
    transition = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if item.kind is ObservationKind.DEGRADED_STATE_TRANSITION
            and item.payload["input_health"] == authorization.input_health
            and item.payload["degraded_state_source_stamp"]
            == authorization.degraded_state_source_stamp
            and item.payload["affected_topic"] == authorization.affected_topic
        ),
        None,
    )
    if transition is None:
        return result(
            False,
            DegradedInputDisposition.INCONCLUSIVE_INSTRUMENTATION,
            "degraded state transition was not observed for the authorization",
        )

    _, transition_item = transition
    if (
        transition_item.payload["previous_state"] != "nominal"
        or transition_item.payload["current_state"] != "degraded"
    ):
        return result(
            False,
            DegradedInputDisposition.FAIL_WRONG_DISPOSITION,
            "state transition did not show nominal-to-degraded",
            transition_index=transition[0],
        )

    # Find the DEGRADED_STATUS_INDICATION matching the affected topic.
    status = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if item.kind is ObservationKind.DEGRADED_STATUS_INDICATION
            and item.payload["affected_topic"] == authorization.affected_topic
            and item.receipt_monotonic_s >= transition_item.receipt_monotonic_s
            and item.payload["status"] == "degraded"
            and item.payload["indicated_degraded"] is True
        ),
        None,
    )
    if status is None:
        return result(
            False,
            DegradedInputDisposition.INCONCLUSIVE_INSTRUMENTATION,
            "degraded status indication was not observed after the transition",
            transition_index=transition[0],
        )

    # Verify the detection window is closed.
    if window_end - status[1].receipt_monotonic_s < contract.closed_detection_window_s:
        return result(
            False,
            DegradedInputDisposition.INCONCLUSIVE_INSTRUMENTATION,
            "post-detection status window is not closed",
            transition_index=transition[0],
            status_index=status[0],
        )

    # Check that the authorization disposition is pass_bounded_detection.
    if authorization.disposition != DegradedInputDisposition.PASS_BOUNDED_DETECTION.value:
        return result(
            False,
            DegradedInputDisposition.FAIL_WRONG_DISPOSITION,
            f"authorization disposition was {authorization.disposition}, expected pass_bounded_detection",
            transition_index=transition[0],
            status_index=status[0],
        )

    return result(
        True,
        DegradedInputDisposition.PASS_BOUNDED_DETECTION,
        "degraded input was detected, transitioned, and indicated within the closed window",
        transition_index=transition[0],
        status_index=status[0],
    )


# ---------------------------------------------------------------------------
# Runtime/replay policy
# ---------------------------------------------------------------------------


def _failure(scenario: DegradedInputScenario, reason: str) -> DegradedInputScenarioResult:
    return DegradedInputScenarioResult(
        scenario=scenario,
        passed=False,
        disposition=DegradedInputDisposition.ERROR_EVIDENCE,
        degraded_input_profile=scenario.value,
        affected_topic="none",
        input_health="none",
        degraded_state_source_stamp="none",
        authorization_diagnostic_source_stamp="none",
        authorization_observation_index=None,
        transition_observation_index=None,
        status_observation_index=None,
        reason=reason,
    )


def _authorization_inputs(
    scenario: DegradedInputScenario, observations: tuple[Observation, ...]
) -> tuple[int, DegradedInputAuthorization] | DegradedInputScenarioResult:
    """Extract the typed authorization record from the matching observation."""
    authorizations = [
        (index, item)
        for index, item in enumerate(observations)
        if item.kind is ObservationKind.DEGRADED_INPUT_AUTHORIZATION
        and item.payload["degraded_input_profile"] == scenario.value
    ]
    if len(authorizations) != 1:
        return _failure(
            scenario,
            "exactly one degraded input authorization must match the selected profile",
        )
    index, item = authorizations[0]
    payload = item.payload
    authorization = DegradedInputAuthorization(
        degraded_input_profile=payload["degraded_input_profile"],
        affected_topic=payload["affected_topic"],
        input_health=payload["input_health"],
        degraded_state_source_stamp=payload["degraded_state_source_stamp"],
        authorization_diagnostic_source_stamp=payload[
            "authorization_diagnostic_source_stamp"
        ],
        disposition=payload["disposition"],
    )
    return index, authorization


def _graph_reason(
    matrix: MatrixConfig,
    observations: tuple[Observation, ...],
    window_end: float,
) -> str | None:
    """Verify runtime graph isolation through the detection window."""
    graphs = [
        item
        for item in observations
        if item.kind is ObservationKind.RUNTIME_GRAPH
        and item.receipt_monotonic_s <= window_end
    ]
    if not graphs:
        return "runtime graph has no observations within the collection window"
    if window_end - graphs[-1].receipt_monotonic_s > matrix.graph_sampling_max_gap_s:
        return "runtime graph lacks fresh terminal coverage"
    previous = graphs[0].receipt_monotonic_s
    for graph in graphs:
        payload = graph.payload
        if (
            payload["nominal_publisher_count"] != 1.0
            or payload["nominal_publishers"] != matrix.expected_nominal_publisher
            or payload["mrm_publisher_count"] != 0.0
            or payload["mrm_publishers"] != "none"
        ):
            return "runtime graph contains publisher contamination"
        if graph.receipt_monotonic_s - previous > matrix.graph_sampling_max_gap_s:
            return "runtime graph sampling coverage contains a gap"
        previous = graph.receipt_monotonic_s
    return None


def evaluate_profile(
    matrix: MatrixConfig,
    scenario: DegradedInputScenario,
    observations: Iterable[Observation],
    *,
    window_end_receipt_s: float,
) -> DegradedInputScenarioResult:
    """Reconstruct typed inputs and evaluate exactly one profile fail closed."""
    if not isinstance(matrix, MatrixConfig) or not isinstance(
        scenario, DegradedInputScenario
    ):
        raise TypeError("matrix and scenario must use closed 009F types")
    items = tuple(observations)
    inputs = _authorization_inputs(scenario, items)
    if isinstance(inputs, DegradedInputScenarioResult):
        return inputs
    auth_index, authorization = inputs

    # Check that the authorization's input_health matches the expected scenario.
    expected = matrix.scenarios[scenario]
    if authorization.input_health != expected.expected_input_health:
        return _failure(
            scenario,
            "authorization input_health contradicts the authoritative profile",
        )

    result = evaluate_degraded_input_scenario(
        matrix.contract,
        scenario,
        authorization,
        items,
        window_end_receipt_s=window_end_receipt_s,
    )

    # Attach the authorization observation index.
    result = DegradedInputScenarioResult(
        scenario=result.scenario,
        passed=result.passed,
        disposition=result.disposition,
        degraded_input_profile=result.degraded_input_profile,
        affected_topic=result.affected_topic,
        input_health=result.input_health,
        degraded_state_source_stamp=result.degraded_state_source_stamp,
        authorization_diagnostic_source_stamp=result.authorization_diagnostic_source_stamp,
        authorization_observation_index=auth_index,
        transition_observation_index=result.transition_observation_index,
        status_observation_index=result.status_observation_index,
        reason=result.reason,
    )

    # Cross-check the authorization disposition against the matrix expectation.
    auth_disposition = next(
        item.payload["disposition"]
        for item in items
        if item.kind is ObservationKind.DEGRADED_INPUT_AUTHORIZATION
        and item.payload["degraded_input_profile"] == scenario.value
    )
    if auth_disposition != expected.expected_disposition.value:
        return _failure(
            scenario,
            "typed authorization disposition contradicts the authoritative profile",
        )

    if result.disposition is not expected.expected_disposition and result.passed:
        return _failure(
            scenario, "runtime result contradicts authoritative expected disposition"
        )

    graph_reason = _graph_reason(matrix, items, float(window_end_receipt_s))
    if graph_reason is not None:
        return _failure(scenario, graph_reason)

    return result


def degraded_input_result_to_json(result: DegradedInputScenarioResult) -> dict[str, object]:
    value = asdict(result)
    value["scenario"] = result.scenario.value
    value["disposition"] = result.disposition.value
    return value


def terminal_degraded_input_result(result: DegradedInputScenarioResult) -> str | None:
    """Return terminal policy; an open detection window keeps collecting."""
    if result.passed:
        return "pass_degraded_input_profile"
    if result.disposition is DegradedInputDisposition.INCONCLUSIVE_INSTRUMENTATION:
        return None
    return "terminal_degraded_input_failure"
