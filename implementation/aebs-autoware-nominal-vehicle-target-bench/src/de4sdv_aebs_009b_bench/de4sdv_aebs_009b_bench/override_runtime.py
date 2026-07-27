"""Pure runtime/replay policy for INC-AEBS-009D override profiles."""

from __future__ import annotations

import math
from collections.abc import Iterable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path

import yaml

from .override_matrix import (
    DiagnosticAuthorization,
    OverrideDisposition,
    OverrideMatrixContract,
    OverrideSample,
    OverrideScenario,
    OverrideScenarioResult,
    evaluate_override_scenario,
)
from .scenario_evaluator import Observation, ObservationKind


@dataclass(frozen=True)
class MatrixScenario:
    scenario_id: str
    expected_disposition: OverrideDisposition
    expected_braking_request: bool


@dataclass(frozen=True)
class MatrixConfig:
    contract: OverrideMatrixContract
    graph_sampling_max_gap_s: float
    expected_nominal_publisher: str
    scenarios: Mapping[OverrideScenario, MatrixScenario]


def load_matrix_contract(path: str | Path) -> MatrixConfig:
    """Load the exact six-profile matrix and reject an open/ambiguous contract."""
    try:
        value = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as error:
        raise ValueError(f"cannot load 009D matrix: {error}") from error
    required_root = {
        "schema",
        "inherits_runtime",
        "source_topic",
        "authorization_topic",
        "native_observations",
        "contract",
        "scenarios",
        "non_claims",
    }
    if not isinstance(value, Mapping) or set(value) != required_root:
        raise ValueError("009D matrix root does not match the closed contract")
    if (
        value["schema"] != "de4sdv.aebs-009d-conscious-override-matrix.v1"
        or value["inherits_runtime"] != "INC-AEBS-009B"
    ):
        raise ValueError("009D matrix identity or inherited runtime is incorrect")
    contract = value["contract"]
    required_contract = {
        "override_max_age_s",
        "closed_suppression_window_s",
        "graph_sampling_max_gap_s",
        "expected_nominal_publisher",
        "diagnostic_node",
        "diagnostic_task",
        "diagnostic_level",
        "diagnostic_message",
    }
    if not isinstance(contract, Mapping) or set(contract) != required_contract:
        raise ValueError("009D matrix behavior contract is open or incomplete")
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
        raise TypeError("009D scenarios must be a list")
    scenarios: dict[OverrideScenario, MatrixScenario] = {}
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != {
            "id",
            "profile",
            "expected_disposition",
            "expected_braking_request",
        }:
            raise ValueError("009D scenario entry has an open or incomplete shape")
        try:
            profile = OverrideScenario(entry["profile"])
            disposition = OverrideDisposition(entry["expected_disposition"])
        except (TypeError, ValueError) as error:
            raise ValueError(
                "009D scenario has an unknown profile or disposition"
            ) from error
        if profile in scenarios:
            raise ValueError("each closed 009D profile must occur exactly once")
        if not isinstance(entry["id"], str) or not entry["id"].startswith(
            "SCN-AEBS-009D-"
        ):
            raise ValueError("009D scenario ID is invalid")
        if type(entry["expected_braking_request"]) is not bool:
            raise TypeError("expected_braking_request must be boolean")
        scenarios[profile] = MatrixScenario(
            entry["id"], disposition, entry["expected_braking_request"]
        )
    if set(scenarios) != set(OverrideScenario):
        raise ValueError("each closed 009D profile must occur exactly once")
    return MatrixConfig(
        OverrideMatrixContract(
            contract["override_max_age_s"],
            contract["closed_suppression_window_s"],
        ),
        float(gap),
        publisher,
        scenarios,
    )


def _failure(scenario: OverrideScenario, reason: str) -> OverrideScenarioResult:
    return OverrideScenarioResult(
        scenario=scenario,
        passed=False,
        disposition=OverrideDisposition.ERROR_SCENARIO_CONTRACT,
        conscious_override=False,
        override_source_stamp=None,
        authorization_diagnostic_source_stamp="none",
        native_rss_observation_index=None,
        native_intervention_observation_index=None,
        braking_request_observation_index=None,
        reason=reason,
    )


def _authorization_inputs(
    scenario: OverrideScenario, observations: tuple[Observation, ...]
) -> tuple[OverrideSample, DiagnosticAuthorization] | OverrideScenarioResult:
    intervention = next(
        (
            item
            for item in observations
            if item.kind is ObservationKind.AEB_INTERVENTION
        ),
        None,
    )
    if intervention is None or intervention.source_stamp is None:
        return _failure(
            scenario, "native intervention is required before authorization"
        )
    authorizations = [
        item
        for item in observations
        if item.kind is ObservationKind.OVERRIDE_AUTHORIZATION
        and item.source_stamp == intervention.source_stamp
    ]
    if len(authorizations) != 1:
        return _failure(
            scenario,
            "exactly one typed override authorization must match the first native intervention",
        )
    item = authorizations[0]
    payload = item.payload
    diagnostic_stamp = payload["authorization_diagnostic_source_stamp"]
    if item.source_stamp != diagnostic_stamp:
        return _failure(
            scenario, "typed authorization source stamp contradicts its payload"
        )
    source_value = payload["override_source_value"]
    source_stamp = payload["override_source_stamp"]
    if source_value == "none":
        if source_stamp != "none":
            return _failure(
                scenario, "missing override value contradicts its source stamp"
            )
        sample = OverrideSample(False, None, None)
    else:
        sample = OverrideSample(True, source_value == "true", source_stamp)
    authorization = DiagnosticAuthorization(
        source_stamp=diagnostic_stamp,
        node="autonomous_emergency_braking",
        task="aeb_emergency_stop",
        level="ERROR",
        message="[AEB]: Emergency Brake",
    )
    return sample, authorization


def _graph_reason(
    matrix: MatrixConfig,
    observations: tuple[Observation, ...],
    intervention_index: int | None,
    window_end: float,
) -> str | None:
    if intervention_index is None:
        return None
    risk = next(
        (item for item in observations if item.kind is ObservationKind.RISK_ASSESSMENT),
        None,
    )
    if risk is None:
        return "runtime graph coverage cannot be anchored before native risk"
    graphs = [
        item
        for item in observations
        if item.kind is ObservationKind.RUNTIME_GRAPH
        and risk.receipt_monotonic_s - matrix.graph_sampling_max_gap_s
        <= item.receipt_monotonic_s
        <= window_end
    ]
    if not graphs or graphs[0].receipt_monotonic_s > risk.receipt_monotonic_s:
        return "runtime graph lacks pre-risk coverage"
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
    scenario: OverrideScenario,
    observations: Iterable[Observation],
    *,
    window_end_receipt_s: float,
) -> OverrideScenarioResult:
    """Reconstruct typed inputs and evaluate exactly one profile fail closed."""
    if not isinstance(matrix, MatrixConfig) or not isinstance(
        scenario, OverrideScenario
    ):
        raise TypeError("matrix and scenario must use closed 009D types")
    items = tuple(observations)
    inputs = _authorization_inputs(scenario, items)
    if isinstance(inputs, OverrideScenarioResult):
        return inputs
    sample, authorization = inputs
    result = evaluate_override_scenario(
        matrix.contract,
        scenario,
        sample,
        authorization,
        items,
        window_end_receipt_s=window_end_receipt_s,
    )
    expected = matrix.scenarios[scenario]
    authorization_disposition = next(
        item.payload["disposition"]
        for item in items
        if item.kind is ObservationKind.OVERRIDE_AUTHORIZATION
        and item.source_stamp == result.authorization_diagnostic_source_stamp
    )
    if authorization_disposition != expected.expected_disposition.value:
        return _failure(
            scenario,
            "typed authorization disposition contradicts the authoritative profile",
        )
    if result.disposition is not expected.expected_disposition and result.passed:
        return _failure(
            scenario, "runtime result contradicts authoritative expected disposition"
        )
    graph_reason = _graph_reason(
        matrix,
        items,
        result.native_intervention_observation_index,
        float(window_end_receipt_s),
    )
    if graph_reason is not None:
        return _failure(scenario, graph_reason)
    return result


def override_result_to_json(result: OverrideScenarioResult) -> dict[str, object]:
    value = asdict(result)
    value["scenario"] = result.scenario.value
    value["disposition"] = result.disposition.value
    return value


def terminal_override_result(result: OverrideScenarioResult) -> str | None:
    """Return terminal policy; an open suppression window keeps collecting."""
    if result.passed:
        return "pass_override_profile"
    if result.disposition in {
        OverrideDisposition.INCONCLUSIVE_OPEN_WINDOW,
        OverrideDisposition.INCONCLUSIVE_NATIVE_CHAIN,
    }:
        return None
    return "terminal_override_failure"
