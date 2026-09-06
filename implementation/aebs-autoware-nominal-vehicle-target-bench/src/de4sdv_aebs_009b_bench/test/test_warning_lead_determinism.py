"""Warning-lead determinism regression tests (INC-AEBS-009D).

Covers the 2026-09-02 v22 root cause: a native intervention diagnostic that
arrives between coordinator publish ticks must not permanently erase a warning
condition that already holds from observed geometry, while no warning may be
fabricated without geometry inputs. Also pins the scenario config that makes
the warning-lead contract (>= 0.8 s) deterministic.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from de4sdv_aebs_009b_bench.aebs_coordination_core import (
    InterventionLatch,
    next_warning_state,
    warning_on_intervention_diagnostic,
)


BENCH_ROOT = Path(__file__).parents[3]

# Freshness bound mirrors the coordinator input contract (override/odometry
# max-age class = 0.2 s: two nominal AEB periods at the 10 Hz diagnostic rate
# (0.1 s each).
GEOMETRY_MAX_AGE = 0.2
FRESH_AGE = 0.05   # well within bound (20 Hz cloud / 10 Hz RSS cadence)
STALE_AGE = 0.75   # beyond bound
V22_POINT_M = 23.80
V22_RSS_M = 23.45


def race_eval(current, latch_state, *, rss_age, point_age, rss=V22_RSS_M, point=V22_POINT_M,
              margin=7.0, bound=GEOMETRY_MAX_AGE):
    return warning_on_intervention_diagnostic(
        current, latch_state,
        rss_age_s=rss_age, point_distance_age_s=point_age,
        rss_distance_m=rss, point_distance_m=point,
        warning_margin_m=margin, geometry_max_age_s=bound,
    )


def test_warning_evaluable_before_latch_transition_when_geometry_present():
    """Race case: intervention diagnostic arrives with geometry already in hand.

    The warning condition (bumper gap <= rss + margin) must be evaluated against
    the PRE-diagnostic latch state ("armed") so it latches in the same tick.
    This is the exact v22 failure instant: point distance 23.80 (bumper gap
    20.06), inflated rss 23.45, margin 7.0 — the condition genuinely held.
    """
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    assert latch.state == "armed"
    warning = race_eval(False, latch.state, rss_age=FRESH_AGE, point_age=FRESH_AGE)
    assert warning is True
    # The diagnostic then transitions the latch; the warning was already latched.
    latch.observe_diagnostic(True, True)
    assert latch.state == "braking_latched"
    # A latched warning persists (warning is a latch, not a level).
    assert next_warning_state(True, latch.state, 23.80, 23.45, 7.0) is True


def test_no_warning_fabricated_without_geometry_inputs():
    """Race case: intervention diagnostic arrives before any geometry.

    With no distance/RSS observed the coordinator must not evaluate (and thus
    not fabricate) a warning; the latch transitions and warning stays False.
    """
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    warning = race_eval(False, latch.state, rss_age=None, point_age=None, rss=None, point=None)
    assert warning is False
    latch.observe_diagnostic(True, True)
    assert latch.state == "braking_latched"
    # Post-latch the warning condition can never latch (armed-only rule), so the
    # absence is permanent — matching the honest MONITORING→INTERVENTION HMI path.
    assert next_warning_state(False, latch.state, 23.80, 23.45, 7.0) is False


def test_warning_condition_absent_at_latch_stays_absent():
    """No fabrication: if the warning condition did NOT hold pre-diagnostic,
    the latch transition must not create one."""
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    # Geometry far from any risk: point distance 63.74 (bumper gap 60 m), rss 10 m.
    warning = race_eval(False, latch.state, rss_age=FRESH_AGE, point_age=FRESH_AGE,
                        rss=10.0, point=63.74)
    assert warning is False
    latch.observe_diagnostic(True, True)
    assert latch.state == "braking_latched"
    assert next_warning_state(False, latch.state, 63.74, 10.0, 7.0) is False


def test_warning_lead_contract_configured_in_scenario():
    """The scenario contract carries warning_lead_min_s = 0.8 (the acceptance
    criterion the evaluator gates on)."""
    from de4sdv_aebs_009b_bench.scenario_contract import load_scenario_config

    config = load_scenario_config(
        BENCH_ROOT / "config" / "scenario-009d-moving-vehicle-target.yaml"
    )
    assert config.outcome_contract.warning_lead_min_s == 0.8


# ---------------------------------------------------------------------------
# Evaluator-level gates (reuse the nominal passing stream)
# ---------------------------------------------------------------------------

import sys

sys.path.insert(0, str(Path(__file__).parent))
from test_nominal_009b import (  # noqa: E402
    CONFIG,
    passing,
)
from de4sdv_aebs_009b_bench.scenario_contract import Outcome  # noqa: E402
from de4sdv_aebs_009b_bench.scenario_evaluator import (  # noqa: E402
    Observation,
    ObservationKind,
    evaluate_scenario,
)


def _o(kind, at, **payload):
    return Observation(kind, payload, at, source_stamp=None)


def test_valid_lifecycle_with_sufficient_lead_passes():
    """Case A: warning appears early, intervention follows >= 0.8 s later -> pass."""
    items = passing()
    result = evaluate_scenario(CONFIG, items)
    # The passing stream is the canonical valid lifecycle (warning at 2.2x,
    # intervention at 3.1 => lead ~0.9 s >= 0.8).
    assert result.outcome is Outcome.PASS_OBSERVED_CHAIN
    assert result.details["warning_lead_s"] >= 0.8


def test_intervention_before_any_warning_fails_without_fabricating():
    """Case B (v22 shape): native intervention arrives before any warning=true.

    The evaluator must fail the run with the earliest failing gate
    (native_risk_assessment) — it must NOT report a pass and must NOT
    fabricate a warning-lead value.
    """
    items = passing()
    # Remove every warning-side observation: risk with warning=true, warning_request.
    items = [
        x for x in items
        if not (x.kind is ObservationKind.RISK_ASSESSMENT and x.payload.get("warning") is True)
        and x.kind is not ObservationKind.WARNING_REQUEST
    ]
    # Make the pre-intervention risk warning=false (intervention-side only), as v22 saw.
    items = [
        _o(x.kind, x.receipt_monotonic_s, **{**x.payload, "warning": False})
        if x.kind is ObservationKind.RISK_ASSESSMENT else x
        for x in items
    ]
    items.sort(key=lambda item: item.receipt_monotonic_s)
    result = evaluate_scenario(CONFIG, items)
    assert result.outcome is Outcome.FAIL_SCENARIO
    assert result.details["failed_event"] == "native_risk_assessment"
    assert "warning_lead_s" not in result.details


def test_warning_lead_values_are_recorded_not_inferred():
    """The evaluator must record first-warning and first-intervention timing as
    explicit accepted-event references with receipt timestamps."""
    items = passing()
    result = evaluate_scenario(CONFIG, items)
    labels = {event.label for event in result.accepted_events}
    assert "warning_request" in labels
    assert "native_aeb_intervention" in labels
    warning_ts = next(
        e.receipt_monotonic_s for e in result.accepted_events if e.label == "warning_request"
    )
    intervention_ts = next(
        e.receipt_monotonic_s for e in result.accepted_events if e.label == "native_aeb_intervention"
    )
    assert result.details["warning_lead_s"] == pytest.approx(intervention_ts - warning_ts)


# ---------------------------------------------------------------------------
# Freshness-bounded race evaluation (v22 follow-up review requirements)
# ---------------------------------------------------------------------------

def test_fresh_geometry_legitimate_warning_latches_pre_diagnostic():
    """Fresh geometry at diagnostic arrival -> warning may latch (armed state)."""
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    assert race_eval(False, latch.state, rss_age=FRESH_AGE, point_age=FRESH_AGE) is True


def test_missing_geometry_no_warning():
    """No geometry at all -> no evaluation, no warning."""
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    assert race_eval(False, latch.state, rss_age=None, point_age=None, rss=None, point=None) is False
    # Values present but ages missing (unstampable) behave the same.
    assert race_eval(False, latch.state, rss_age=None, point_age=None) is False
    assert race_eval(False, latch.state, rss_age=FRESH_AGE, point_age=None) is False
    assert race_eval(False, latch.state, rss_age=None, point_age=FRESH_AGE) is False


def test_stale_rss_no_warning():
    """RSS beyond the freshness bound -> behaves like unavailable -> no warning."""
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    assert race_eval(False, latch.state, rss_age=STALE_AGE, point_age=FRESH_AGE) is False


def test_stale_point_geometry_no_warning():
    """Point distance beyond the freshness bound -> no warning."""
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    assert race_eval(False, latch.state, rss_age=FRESH_AGE, point_age=STALE_AGE) is False


def test_both_stale_no_warning():
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    assert race_eval(False, latch.state, rss_age=STALE_AGE, point_age=STALE_AGE) is False


def test_future_stamped_geometry_fails_closed():
    """Negative age (future-stamped source) -> invalid input -> no warning."""
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    assert race_eval(False, latch.state, rss_age=-1.0, point_age=FRESH_AGE) is False
    assert race_eval(False, latch.state, rss_age=FRESH_AGE, point_age=-0.5) is False


def test_geometry_present_but_stale_matches_v22_shape_without_warning():
    """If the race happens with only stale geometry, the run stays honestly
    MONITORING -> INTERVENTION (the v22 outcome) rather than fabricating."""
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    assert race_eval(False, latch.state, rss_age=STALE_AGE, point_age=STALE_AGE) is False
    latch.observe_diagnostic(True, True)
    assert latch.state == "braking_latched"
    assert next_warning_state(False, latch.state, V22_POINT_M, V22_RSS_M, 7.0) is False


def test_boundary_age_exactly_at_bound_is_still_fresh():
    """age == geometry_max_age_s is within the closed bound (0.0 <= age <= bound)."""
    latch = InterventionLatch(stop_speed_mps=0.1, stop_hold_s=0.5, odometry_max_age_s=0.2)
    assert race_eval(False, latch.state, rss_age=GEOMETRY_MAX_AGE, point_age=0.0) is True


def test_009b_shared_param_reverted_to_pinned_authority():
    """The shared 009B AEB param file keeps the pinned upstream value; the 009D
    override lives in its own file so 009B behavior is unchanged."""
    text = (BENCH_ROOT / "config" / "aebs-009b.param.yaml").read_text()
    match = next(
        line for line in text.splitlines()
        if line.strip().startswith("use_object_velocity_calculation:")
    )
    assert match.strip() == "use_object_velocity_calculation: true"
    dtext = (BENCH_ROOT / "config" / "aebs-009d.param.yaml").read_text()
    dmatch = next(
        line for line in dtext.splitlines()
        if line.strip().startswith("use_object_velocity_calculation:")
    )
    assert dmatch.strip() == "use_object_velocity_calculation: false"


def test_launch_wires_aeb_param_file_argument():
    """The launch file takes aeb_param_file (default: shared 009B file); the
    runner passes the 009D file only in 009D mode."""
    launch = (
        BENCH_ROOT / "src/de4sdv_aebs_009b_bench/launch/aebs_009b_bench.launch.py"
    ).read_text()
    assert '"aeb_param_file"' in launch
    assert 'default_value="aebs-009b.param.yaml"' in launch
    runner = (BENCH_ROOT / "scripts/launch.sh").read_text()
    assert "aeb_param_file:=aebs-009d.param.yaml" in runner
    assert 'aeb_param_argument=""' in runner  # 009B path passes nothing (default)
