"""Pure INC-AEBS-009E non-activation matrix over 009B observations.

The matrix verifies bounded silence — the absence of AEB warning, intervention,
and braking — across four target configurations that should not trigger AEB.
ROS adapters may construct the inputs, but all verdict logic stays middleware
independent and fail closed.
"""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path

import yaml

from .scenario_evaluator import Observation, ObservationKind


class NonActivationScenario(str, Enum):
    """Closed scenario vocabulary for the 009E non-activation matrix."""

    CLEAR_PATH = "clear_path"
    ADJACENT_OBJECT = "adjacent_object"
    NON_CLOSING_TARGET = "non_closing_target"
    BELOW_TRIGGER = "below_trigger"


class NonActivationOutcome(str, Enum):
    """Closed terminal outcome vocabulary for one non-activation scenario."""

    PASS_BOUNDED_SILENCE = "pass_bounded_silence"
    FAIL_UNEXPECTED_ACTIVATION = "fail_unexpected_activation"
    INCONCLUSIVE_INCOMPLETE_COVERAGE = "inconclusive_incomplete_coverage"
    ERROR_EVIDENCE = "error_evidence"


@dataclass(frozen=True)
class NonActivationMatrixContract:
    """Behavioral contract for one non-activation scenario execution."""

    observation_duration_s: float
    sample_max_gap_s: float
    required_input_max_age_s: float
    diagnostic_node: str = "autonomous_emergency_braking"
    diagnostic_task: str = "aeb_emergency_stop"
    diagnostic_level: str = "OK"

    def __post_init__(self) -> None:
        for name in ("observation_duration_s", "sample_max_gap_s", "required_input_max_age_s"):
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
        ):
            if not isinstance(getattr(self, name), str) or not getattr(self, name):
                raise TypeError(f"{name} must be a nonempty string")


@dataclass(frozen=True)
class NonActivationScenarioResult:
    """One independent closed verdict for exactly one non-activation scenario."""

    scenario: NonActivationScenario
    passed: bool
    outcome: NonActivationOutcome
    warning_observation_index: int | None
    intervention_observation_index: int | None
    braking_request_observation_index: int | None
    reason: str


# ---------------------------------------------------------------------------
# Runtime / matrix configuration types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MatrixScenario:
    scenario_id: str
    expected_outcome: NonActivationOutcome
    scenario_config: str


@dataclass(frozen=True)
class MatrixConfig:
    contract: NonActivationMatrixContract
    graph_sampling_max_gap_s: float
    expected_nominal_publisher: str
    scenarios: Mapping[NonActivationScenario, MatrixScenario]


SCENARIO_CONFIG_MAP: Mapping[NonActivationScenario, str] = {
    NonActivationScenario.CLEAR_PATH: "config/scenario-009e-clear-path.yaml",
    NonActivationScenario.ADJACENT_OBJECT: "config/scenario-009e-adjacent-object.yaml",
    NonActivationScenario.NON_CLOSING_TARGET: "config/scenario-009e-non-closing-target.yaml",
    NonActivationScenario.BELOW_TRIGGER: "config/scenario-009e-below-trigger.yaml",
}


def load_matrix_contract(path: str | Path) -> MatrixConfig:
    """Load the exact four-scenario matrix and reject an open/ambiguous contract."""
    try:
        value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(f"cannot load 009E matrix: {error}") from error
    required_root = {
        "schema",
        "inherits_runtime",
        "native_observations",
        "contract",
        "scenarios",
        "non_claims",
    }
    if not isinstance(value, Mapping) or set(value) != required_root:
        raise ValueError("009E matrix root does not match the closed contract")
    if (
        value["schema"] != "de4sdv.aebs-009e-non-activation-matrix.v1"
        or value["inherits_runtime"] != "INC-AEBS-009B"
    ):
        raise ValueError("009E matrix identity or inherited runtime is incorrect")
    contract = value["contract"]
    required_contract = {
        "observation_duration_s",
        "sample_max_gap_s",
        "required_input_max_age_s",
        "graph_sampling_max_gap_s",
        "expected_nominal_publisher",
        "diagnostic_node",
        "diagnostic_task",
        "diagnostic_level",
    }
    if not isinstance(contract, Mapping) or set(contract) != required_contract:
        raise ValueError("009E matrix behavior contract is open or incomplete")
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
        raise TypeError("009E scenarios must be a list")
    scenarios: dict[NonActivationScenario, MatrixScenario] = {}
    canonical: dict[NonActivationScenario, NonActivationOutcome] = {
        scenario: NonActivationOutcome.PASS_BOUNDED_SILENCE
        for scenario in NonActivationScenario
    }
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != {
            "id",
            "profile",
            "expected_outcome",
            "scenario_config",
        }:
            raise ValueError("009E scenario entry has an open or incomplete shape")
        try:
            profile = NonActivationScenario(entry["profile"])
            outcome = NonActivationOutcome(entry["expected_outcome"])
        except (TypeError, ValueError) as error:
            raise ValueError(
                "009E scenario has an unknown profile or outcome"
            ) from error
        if profile in scenarios:
            raise ValueError("each closed 009E profile must occur exactly once")
        if not isinstance(entry["id"], str) or not entry["id"].startswith(
            "SCN-AEBS-009E-"
        ):
            raise ValueError("009E scenario ID is invalid")
        if not isinstance(entry["scenario_config"], str) or not entry["scenario_config"]:
            raise ValueError("009E scenario_config must be a nonempty string")
        if outcome != canonical[profile]:
            raise ValueError(
                "009E scenario outcome contradicts its closed profile"
            )
        if entry["scenario_config"] != SCENARIO_CONFIG_MAP[profile]:
            raise ValueError(
                "009E scenario_config path contradicts the closed profile mapping"
            )
        scenarios[profile] = MatrixScenario(
            entry["id"], outcome, entry["scenario_config"]
        )
    if set(scenarios) != set(NonActivationScenario):
        raise ValueError("each closed 009E profile must occur exactly once")
    return MatrixConfig(
        NonActivationMatrixContract(
            contract["observation_duration_s"],
            contract["sample_max_gap_s"],
            contract["required_input_max_age_s"],
            contract["diagnostic_node"],
            contract["diagnostic_task"],
            contract["diagnostic_level"],
        ),
        float(gap),
        publisher,
        scenarios,
    )


# ---------------------------------------------------------------------------
# Pure evaluator
# ---------------------------------------------------------------------------


def evaluate_non_activation_scenario(
    contract: NonActivationMatrixContract,
    scenario: NonActivationScenario,
    observations: Iterable[Observation],
    *,
    window_end_receipt_s: float,
) -> NonActivationScenarioResult:
    """Return one independent closed verdict for exactly one non-activation scenario."""

    if not isinstance(contract, NonActivationMatrixContract):
        raise TypeError("contract must be NonActivationMatrixContract")
    if not isinstance(scenario, NonActivationScenario):
        raise TypeError("scenario must be NonActivationScenario")
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
        outcome: NonActivationOutcome,
        reason: str,
        warning_index: int | None = None,
        intervention_index: int | None = None,
        brake_index: int | None = None,
    ) -> NonActivationScenarioResult:
        return NonActivationScenarioResult(
            scenario,
            passed,
            outcome,
            warning_index,
            intervention_index,
            brake_index,
            reason,
        )

    # --- 1. No AEB warning was activated ---------------------------------
    warning = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if item.kind is ObservationKind.WARNING_REQUEST
            and item.payload["active"] is True
        ),
        None,
    )
    if warning is not None:
        return result(
            False,
            NonActivationOutcome.FAIL_UNEXPECTED_ACTIVATION,
            "AEB warning was activated during the non-activation scenario",
            warning_index=warning[0],
        )

    # --- 2. No AEB intervention was triggered ----------------------------
    intervention = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if item.kind is ObservationKind.AEB_INTERVENTION
        ),
        None,
    )
    if intervention is not None:
        return result(
            False,
            NonActivationOutcome.FAIL_UNEXPECTED_ACTIVATION,
            "AEB intervention was triggered during the non-activation scenario",
            intervention_index=intervention[0],
        )

    # --- 3. No braking request was issued --------------------------------
    brake = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if item.kind is ObservationKind.BRAKING_REQUEST
        ),
        None,
    )
    if brake is not None:
        return result(
            False,
            NonActivationOutcome.FAIL_UNEXPECTED_ACTIVATION,
            "braking request was issued during the non-activation scenario",
            brake_index=brake[0],
        )

    # --- 4. No ERROR diagnostic on the AEB node --------------------------
    error_diag = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if item.kind is ObservationKind.DIAGNOSTIC
            and item.payload["node"] == contract.diagnostic_node
            and item.payload["task"] == contract.diagnostic_task
            and item.payload["level"] == "ERROR"
        ),
        None,
    )
    if error_diag is not None:
        return result(
            False,
            NonActivationOutcome.FAIL_UNEXPECTED_ACTIVATION,
            "AEB diagnostic escalated to ERROR during the non-activation scenario",
        )

    # --- 5. Sufficient observation coverage -------------------------------
    if not items:
        return result(
            False,
            NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE,
            "no observations were collected for the non-activation scenario",
        )
    start = items[0].receipt_monotonic_s
    if window_end - start < contract.observation_duration_s:
        return result(
            False,
            NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE,
            "observation window does not cover the required duration",
        )

    # --- 6. Runtime graph coverage (publisher isolation) -----------------
    graphs = [
        item
        for item in items
        if item.kind is ObservationKind.RUNTIME_GRAPH
    ]
    if not graphs:
        return result(
            False,
            NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE,
            "no runtime graph observations were collected",
        )
    previous = graphs[0].receipt_monotonic_s
    for graph in graphs:
        payload = graph.payload
        if (
            payload["nominal_publisher_count"] != 1.0
            or payload["mrm_publisher_count"] != 0.0
        ):
            return result(
                False,
                NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE,
                "runtime graph contains publisher contamination",
            )
        if graph.receipt_monotonic_s - previous > contract.sample_max_gap_s:
            return result(
                False,
                NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE,
                "runtime graph sampling coverage contains a gap",
            )
        previous = graph.receipt_monotonic_s
    if window_end - graphs[-1].receipt_monotonic_s > contract.sample_max_gap_s:
        return result(
            False,
            NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE,
            "runtime graph lacks fresh terminal coverage",
        )

    # --- 7. All checks pass: bounded silence -----------------------------
    return result(
        True,
        NonActivationOutcome.PASS_BOUNDED_SILENCE,
        "AEB remained silent for the full observation window",
    )


# ---------------------------------------------------------------------------
# Runtime policy
# ---------------------------------------------------------------------------


def _failure(scenario: NonActivationScenario, reason: str) -> NonActivationScenarioResult:
    return NonActivationScenarioResult(
        scenario=scenario,
        passed=False,
        outcome=NonActivationOutcome.ERROR_EVIDENCE,
        warning_observation_index=None,
        intervention_observation_index=None,
        braking_request_observation_index=None,
        reason=reason,
    )


def _graph_reason(
    matrix: MatrixConfig,
    observations: tuple[Observation, ...],
    window_end: float,
) -> str | None:
    graphs = [
        item
        for item in observations
        if item.kind is ObservationKind.RUNTIME_GRAPH
    ]
    if not graphs:
        return "runtime graph observations are required for publisher isolation"
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
    if window_end - graphs[-1].receipt_monotonic_s > matrix.graph_sampling_max_gap_s:
        return "runtime graph lacks fresh terminal coverage"
    return None


def evaluate_profile(
    matrix: MatrixConfig,
    scenario: NonActivationScenario,
    observations: Iterable[Observation],
    *,
    window_end_receipt_s: float,
) -> NonActivationScenarioResult:
    """Evaluate exactly one non-activation scenario fail closed."""
    if not isinstance(matrix, MatrixConfig) or not isinstance(
        scenario, NonActivationScenario
    ):
        raise TypeError("matrix and scenario must use closed 009E types")
    items = tuple(observations)
    result = evaluate_non_activation_scenario(
        matrix.contract,
        scenario,
        items,
        window_end_receipt_s=window_end_receipt_s,
    )
    expected = matrix.scenarios[scenario]
    if result.outcome is not expected.expected_outcome and result.passed:
        return _failure(
            scenario,
            "runtime result contradicts authoritative expected outcome",
        )
    graph_reason = _graph_reason(
        matrix,
        items,
        float(window_end_receipt_s),
    )
    if graph_reason is not None:
        return _failure(scenario, graph_reason)
    return result


def non_activation_result_to_json(result: NonActivationScenarioResult) -> dict[str, object]:
    value = asdict(result)
    value["scenario"] = result.scenario.value
    value["outcome"] = result.outcome.value
    return value


def terminal_non_activation_result(result: NonActivationScenarioResult) -> str | None:
    """Return terminal policy; incomplete coverage keeps collecting."""
    if result.passed:
        return "pass_bounded_silence"
    if result.outcome is NonActivationOutcome.INCONCLUSIVE_INCOMPLETE_COVERAGE:
        return None
    return "terminal_non_activation_failure"
