import sys
from pathlib import Path

import pytest

PACKAGE_ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(PACKAGE_ROOT))

from de4sdv_aebs_009b_bench.override_matrix import (
    DiagnosticAuthorization,
    OverrideDisposition,
    OverrideMatrixContract,
    OverrideSample,
    OverrideScenario,
    evaluate_override_scenario,
)
from de4sdv_aebs_009b_bench.scenario_evaluator import Observation, ObservationKind

CONTRACT = OverrideMatrixContract(max_source_age_s=0.2, closed_window_s=0.25)


def obs(kind, at, source_stamp=None, **payload):
    return Observation(kind, payload, at, source_stamp=source_stamp)


def native_observations(*, brake):
    values = [
        obs(
            ObservationKind.RISK_ASSESSMENT,
            10.0,
            rss_distance_m=8.0,
            object_distance_m=7.5,
            warning=True,
            intervention=False,
        ),
        obs(
            ObservationKind.WARNING_REQUEST,
            10.1,
            active=True,
        ),
        obs(
            ObservationKind.DIAGNOSTIC,
            10.2,
            source_stamp="100.200000000",
            node="autonomous_emergency_braking",
            task="aeb_emergency_stop",
            level="ERROR",
        ),
        obs(
            ObservationKind.AEB_INTERVENTION,
            10.2,
            source_stamp="100.200000000",
            node="autonomous_emergency_braking",
            task="aeb_emergency_stop",
            level="ERROR",
            message="[AEB]: Emergency Brake",
            rss_distance_m=8.0,
            object_distance_m=7.5,
            object_speed_mps=1.0,
        ),
    ]
    if brake:
        values.append(
            obs(
                ObservationKind.BRAKING_REQUEST,
                10.21,
                speed_mps=0.0,
                acceleration_mps2=-6.0,
            )
        )
    return values


def diagnostic(stamp="100.200000000"):
    return DiagnosticAuthorization(
        source_stamp=stamp,
        node="autonomous_emergency_braking",
        task="aeb_emergency_stop",
        level="ERROR",
        message="[AEB]: Emergency Brake",
    )


@pytest.mark.parametrize(
    "scenario,sample,brake,expected,conscious",
    [
        (
            OverrideScenario.FRESH_FALSE_CONTROL,
            OverrideSample(received=True, value=False, source_stamp="100.100000000"),
            True,
            OverrideDisposition.CONTROL_CLEAR,
            False,
        ),
        (
            OverrideScenario.FRESH_TRUE_CONSCIOUS,
            OverrideSample(received=True, value=True, source_stamp="100.100000000"),
            False,
            OverrideDisposition.CONSCIOUS_OVERRIDE,
            True,
        ),
        (
            OverrideScenario.STALE,
            OverrideSample(received=True, value=True, source_stamp="99.900000000"),
            False,
            OverrideDisposition.DEGRADED_STALE_SOURCE,
            False,
        ),
        (
            OverrideScenario.MISSING,
            OverrideSample(received=False, value=None, source_stamp=None),
            False,
            OverrideDisposition.INCONCLUSIVE_MISSING_SOURCE,
            False,
        ),
        (
            OverrideScenario.MALFORMED,
            OverrideSample(received=True, value=True, source_stamp="0.000000000"),
            False,
            OverrideDisposition.ERROR_MALFORMED_SOURCE,
            False,
        ),
        (
            OverrideScenario.FUTURE_STAMPED,
            OverrideSample(received=True, value=True, source_stamp="100.300000000"),
            False,
            OverrideDisposition.ERROR_FUTURE_SOURCE,
            False,
        ),
    ],
)
def test_closed_override_matrix(scenario, sample, brake, expected, conscious):
    result = evaluate_override_scenario(
        CONTRACT,
        scenario,
        sample,
        diagnostic(),
        native_observations(brake=brake),
        window_end_receipt_s=10.5,
    )
    assert result.passed
    assert result.disposition is expected
    assert result.conscious_override is conscious
    assert result.override_source_stamp == sample.source_stamp
    assert result.authorization_diagnostic_source_stamp == "100.200000000"


def test_true_is_not_authorized_by_unmatched_or_forged_diagnostic_source():
    observations = native_observations(brake=False)
    forged = diagnostic("100.200000001")
    result = evaluate_override_scenario(
        CONTRACT,
        OverrideScenario.FRESH_TRUE_CONSCIOUS,
        OverrideSample(True, True, "100.100000000"),
        forged,
        observations,
        window_end_receipt_s=10.5,
    )
    assert not result.passed
    assert result.disposition is OverrideDisposition.ERROR_DIAGNOSTIC_AUTHORIZATION
    assert not result.conscious_override


def test_suppression_requires_a_closed_post_diagnostic_window():
    result = evaluate_override_scenario(
        CONTRACT,
        OverrideScenario.FRESH_TRUE_CONSCIOUS,
        OverrideSample(True, True, "100.100000000"),
        diagnostic(),
        native_observations(brake=False),
        window_end_receipt_s=10.3,
    )
    assert not result.passed
    assert result.disposition is OverrideDisposition.INCONCLUSIVE_OPEN_WINDOW


def test_invalid_freshness_fails_if_braking_is_allowed():
    result = evaluate_override_scenario(
        CONTRACT,
        OverrideScenario.STALE,
        OverrideSample(True, True, "99.900000000"),
        diagnostic(),
        native_observations(brake=True),
        window_end_receipt_s=10.5,
    )
    assert not result.passed
    assert result.disposition is OverrideDisposition.ERROR_FAIL_CLOSED_BREACH
    assert not result.conscious_override


def test_matrix_contract_rejects_unknown_scenarios_and_non_boolean_samples():
    with pytest.raises(TypeError, match="boolean"):
        OverrideSample(True, "true", "100.100000000")
    with pytest.raises(TypeError, match="OverrideScenario"):
        evaluate_override_scenario(
            CONTRACT,
            "fresh_true_conscious",
            OverrideSample(True, True, "100.100000000"),
            diagnostic(),
            native_observations(brake=False),
            window_end_receipt_s=10.5,
        )
