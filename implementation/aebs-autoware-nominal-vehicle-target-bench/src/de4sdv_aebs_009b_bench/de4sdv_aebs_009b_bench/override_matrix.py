"""Pure INC-AEBS-009D conscious-override matrix over 009B observations.

The matrix deliberately reuses the pinned bench's native RSS, warning, AEB
intervention diagnostic, and braking-request observations.  ROS adapters may
construct the inputs, but all authorization and verdict logic stays middleware
independent and fail closed.
"""

from __future__ import annotations

import math
import re
from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from enum import Enum

from .scenario_evaluator import Observation, ObservationKind

_STAMP = re.compile(r"(?:0|[1-9][0-9]*)\.[0-9]{9}\Z")
class OverrideScenario(str, Enum):
    FRESH_FALSE_CONTROL = "fresh_false_control"
    FRESH_TRUE_CONSCIOUS = "fresh_true_conscious_override"
    STALE = "stale"
    MISSING = "missing"
    MALFORMED = "malformed"
    FUTURE_STAMPED = "future_stamped"


class OverrideDisposition(str, Enum):
    CONTROL_CLEAR = "control_clear"
    CONSCIOUS_OVERRIDE = "conscious_override"
    DEGRADED_STALE_SOURCE = "degraded_stale_source"
    INCONCLUSIVE_MISSING_SOURCE = "inconclusive_missing_source"
    ERROR_MALFORMED_SOURCE = "error_malformed_source"
    ERROR_FUTURE_SOURCE = "error_future_source"
    ERROR_DIAGNOSTIC_AUTHORIZATION = "error_diagnostic_authorization"
    INCONCLUSIVE_NATIVE_CHAIN = "inconclusive_native_chain"
    INCONCLUSIVE_OPEN_WINDOW = "inconclusive_open_window"
    ERROR_FAIL_CLOSED_BREACH = "error_fail_closed_breach"
    ERROR_SCENARIO_CONTRACT = "error_scenario_contract"


@dataclass(frozen=True)
class OverrideMatrixContract:
    max_source_age_s: float
    closed_window_s: float
    diagnostic_node: str = "autonomous_emergency_braking"
    diagnostic_task: str = "aeb_emergency_stop"
    diagnostic_level: str = "ERROR"
    diagnostic_message: str = "[AEB]: Emergency Brake"

    def __post_init__(self) -> None:
        for name in ("max_source_age_s", "closed_window_s"):
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
class OverrideSample:
    received: bool
    value: bool | None
    source_stamp: str | None

    def __post_init__(self) -> None:
        if type(self.received) is not bool:
            raise TypeError("received must be boolean")
        if self.received:
            if type(self.value) is not bool:
                raise TypeError("received override value must be boolean")
            if self.source_stamp is not None and not isinstance(self.source_stamp, str):
                raise TypeError("source_stamp must be a string or None")
        elif self.value is not None or self.source_stamp is not None:
            raise ValueError("a missing sample cannot carry a value or source stamp")


@dataclass(frozen=True)
class DiagnosticAuthorization:
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
class OverrideScenarioResult:
    scenario: OverrideScenario
    passed: bool
    disposition: OverrideDisposition
    conscious_override: bool
    override_source_stamp: str | None
    authorization_diagnostic_source_stamp: str
    native_rss_observation_index: int | None
    native_intervention_observation_index: int | None
    braking_request_observation_index: int | None
    reason: str


def _stamp_decimal(value: str | None) -> Decimal | None:
    if value is None or _STAMP.fullmatch(value) is None:
        return None
    try:
        stamp = Decimal(value)
    except InvalidOperation:
        return None
    return stamp if stamp > 0 else None


def _sample_disposition(
    contract: OverrideMatrixContract,
    sample: OverrideSample,
    diagnostic_stamp: str,
) -> tuple[OverrideDisposition, bool]:
    if not sample.received:
        return OverrideDisposition.INCONCLUSIVE_MISSING_SOURCE, False
    source = _stamp_decimal(sample.source_stamp)
    diagnostic = _stamp_decimal(diagnostic_stamp)
    if source is None or diagnostic is None:
        return OverrideDisposition.ERROR_MALFORMED_SOURCE, False
    age = diagnostic - source
    if age < 0:
        return OverrideDisposition.ERROR_FUTURE_SOURCE, False
    if age > Decimal(str(contract.max_source_age_s)):
        return OverrideDisposition.DEGRADED_STALE_SOURCE, False
    if sample.value is True:
        return OverrideDisposition.CONSCIOUS_OVERRIDE, True
    return OverrideDisposition.CONTROL_CLEAR, False


def _expected_disposition(scenario: OverrideScenario) -> OverrideDisposition:
    return {
        OverrideScenario.FRESH_FALSE_CONTROL: OverrideDisposition.CONTROL_CLEAR,
        OverrideScenario.FRESH_TRUE_CONSCIOUS: OverrideDisposition.CONSCIOUS_OVERRIDE,
        OverrideScenario.STALE: OverrideDisposition.DEGRADED_STALE_SOURCE,
        OverrideScenario.MISSING: OverrideDisposition.INCONCLUSIVE_MISSING_SOURCE,
        OverrideScenario.MALFORMED: OverrideDisposition.ERROR_MALFORMED_SOURCE,
        OverrideScenario.FUTURE_STAMPED: OverrideDisposition.ERROR_FUTURE_SOURCE,
    }[scenario]


def evaluate_override_scenario(
    contract: OverrideMatrixContract,
    scenario: OverrideScenario,
    sample: OverrideSample,
    authorization: DiagnosticAuthorization,
    observations: Iterable[Observation],
    *,
    window_end_receipt_s: float,
) -> OverrideScenarioResult:
    """Return one independent closed verdict for exactly one matrix scenario."""

    if not isinstance(contract, OverrideMatrixContract):
        raise TypeError("contract must be OverrideMatrixContract")
    if not isinstance(scenario, OverrideScenario):
        raise TypeError("scenario must be OverrideScenario")
    if not isinstance(sample, OverrideSample):
        raise TypeError("sample must be OverrideSample")
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
        disposition: OverrideDisposition,
        conscious: bool,
        reason: str,
        risk_index: int | None = None,
        intervention_index: int | None = None,
        brake_index: int | None = None,
    ) -> OverrideScenarioResult:
        return OverrideScenarioResult(
            scenario,
            passed,
            disposition,
            conscious,
            sample.source_stamp,
            authorization.source_stamp,
            risk_index,
            intervention_index,
            brake_index,
            reason,
        )

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
    if risk is None or warning is None:
        return result(
            False,
            OverrideDisposition.INCONCLUSIVE_NATIVE_CHAIN,
            False,
            "native RSS/warning observations were incomplete",
        )
    diagnostic = next(
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
    intervention = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if diagnostic is not None
            and item.kind is ObservationKind.AEB_INTERVENTION
            and item.source_stamp == authorization.source_stamp
            and item.receipt_monotonic_s == diagnostic[1].receipt_monotonic_s
            and item.payload["node"] == contract.diagnostic_node
            and item.payload["task"] == contract.diagnostic_task
            and item.payload["level"] == contract.diagnostic_level
            and item.payload["message"] == contract.diagnostic_message
            and item.payload["object_distance_m"] <= item.payload["rss_distance_m"]
        ),
        None,
    )
    authorization_exact = (
        authorization.node == contract.diagnostic_node
        and authorization.task == contract.diagnostic_task
        and authorization.level == contract.diagnostic_level
        and authorization.message == contract.diagnostic_message
        and diagnostic is not None
        and intervention is not None
    )
    if not authorization_exact:
        return result(
            False,
            OverrideDisposition.ERROR_DIAGNOSTIC_AUTHORIZATION,
            False,
            "authorization did not exact-match the observed native AEB diagnostic source",
            risk[0] if risk else None,
            intervention[0] if intervention else None,
        )
    assert intervention is not None

    disposition, conscious = _sample_disposition(
        contract, sample, authorization.source_stamp
    )
    expected = _expected_disposition(scenario)
    if disposition is not expected:
        return result(
            False,
            OverrideDisposition.ERROR_SCENARIO_CONTRACT,
            False,
            f"configured scenario expected {expected.value}, observed {disposition.value}",
            risk[0],
            intervention[0],
        )

    brake = next(
        (
            (index, item)
            for index, item in enumerate(items)
            if item.kind is ObservationKind.BRAKING_REQUEST
            and item.receipt_monotonic_s >= intervention[1].receipt_monotonic_s
        ),
        None,
    )
    if disposition is not OverrideDisposition.CONSCIOUS_OVERRIDE:
        if brake is None:
            if window_end - intervention[1].receipt_monotonic_s < contract.closed_window_s:
                return result(
                    False,
                    OverrideDisposition.INCONCLUSIVE_OPEN_WINDOW,
                    False,
                    "post-intervention braking-observation window is not closed",
                    risk[0],
                    intervention[0],
                )
            return result(
                False,
                OverrideDisposition.ERROR_FAIL_CLOSED_BREACH,
                False,
                "non-override disposition did not preserve the native intervention-to-braking chain",
                risk[0],
                intervention[0],
            )
        return result(
            True,
            disposition,
            False,
            "non-override disposition preserved 009B native intervention and braking",
            risk[0],
            intervention[0],
            brake[0],
        )

    if brake is not None:
        return result(
            False,
            OverrideDisposition.ERROR_FAIL_CLOSED_BREACH,
            False,
            "braking was authorized despite a fresh conscious override",
            risk[0],
            intervention[0],
            brake[0],
        )
    if window_end - intervention[1].receipt_monotonic_s < contract.closed_window_s:
        return result(
            False,
            OverrideDisposition.INCONCLUSIVE_OPEN_WINDOW,
            False,
            "post-diagnostic suppression window is not closed",
            risk[0],
            intervention[0],
        )
    return result(
        True,
        disposition,
        conscious,
        "native AEB intervention was observed and braking remained suppressed for the closed window",
        risk[0],
        intervention[0],
    )
