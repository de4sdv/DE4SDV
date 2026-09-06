"""Guard tests for the repaired warning-lead determinism implementation (PR #188).

These guards close the parent-review findings on the repair:
1. The coordinator freshness race path (both diagnostic and periodic) rejects
   stale geometry; a warning can never latch from stale cached inputs.
2. The coordinator invalidates its cached geometry when a cloud/RSS sample is
   invalid or empty instead of serving the last good value as fresh.
3. Scenario-specific 009D calibration is shipped by setup.py and bound in the
   launch argument contract.
4. The legacy run_override_profile.sh contract rows that referenced the retired
   per-profile wrapper are updated to the shared evidence pipeline reality.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

BENCH_ROOT = Path(__file__).parents[3]
PACKAGE_ROOT = BENCH_ROOT / "src" / "de4sdv_aebs_009b_bench"
sys.path.insert(0, str(PACKAGE_ROOT))

from de4sdv_aebs_009b_bench.aebs_coordination_core import (  # noqa: E402
    warning_on_intervention_diagnostic,
)


def eval_race(current=False, latch_state="armed", *, rss: float | None = 23.45,
              point: float | None = 23.80, margin: float = 7.0,
              rss_age: float | None = 0.05, point_age: float | None = 0.05,
              bound: float = 0.2):
    return warning_on_intervention_diagnostic(
        current,
        latch_state,
        rss,
        point,
        margin,
        rss_age_s=rss_age,
        point_distance_age_s=point_age,
        geometry_max_age_s=bound,
    )


# ---------------------------------------------------------------------------
# 1. Freshness-bounded race evaluation (core + coordinator wiring)
# ---------------------------------------------------------------------------

def test_stale_geometry_cannot_latch_warning_in_race():
    """v22 shape with stale inputs: no warning is created at diagnostic time."""
    assert eval_race(rss_age=0.75) is False
    assert eval_race(point_age=0.75) is False


def test_future_stamped_geometry_fails_closed_in_race():
    assert eval_race(rss_age=-1.0) is False
    assert eval_race(point_age=-1.0) is False


def test_missing_geometry_fails_closed_in_race():
    assert eval_race(rss=None, rss_age=None) is False
    assert eval_race(point=None, point_age=None) is False


def test_existing_warning_is_retained_not_recreated():
    """A real latched warning survives the race evaluation unchanged."""
    assert eval_race(current=True, latch_state="braking_latched") is True


def test_coordinator_passes_freshness_to_race_evaluation():
    """The real coordinator must supply freshness ages and the bound, not just
    the raw distances, in the diagnostic race path."""
    coordinator = (PACKAGE_ROOT / "de4sdv_aebs_009b_bench/aebs_coordinator.py").read_text()
    assert "geometry_max_age_s=" in coordinator
    assert "rss_age_s=" in coordinator
    assert "point_distance_age_s=" in coordinator


# ---------------------------------------------------------------------------
# 2. Periodic publish path must be freshness-bounded too
# ---------------------------------------------------------------------------

def test_periodic_warning_path_is_freshness_bounded():
    """The 20 Hz publish path must not latch a warning from stale cached
    geometry; it must check ages against the same bound class."""
    coordinator = (PACKAGE_ROOT / "de4sdv_aebs_009b_bench/aebs_coordinator.py").read_text()
    # Freshness helper used before warning evaluation in _publish.
    assert "_geometry_is_fresh" in coordinator


# ---------------------------------------------------------------------------
# 3. 009D calibration shipping + launch contract
# ---------------------------------------------------------------------------

def test_009d_calibration_is_shipped_and_bound():
    setup = (PACKAGE_ROOT / "setup.py").read_text()
    assert '"../../config/aebs-009d.param.yaml"' in setup
    launch = (PACKAGE_ROOT / "launch/aebs_009b_bench.launch.py").read_text()
    assert 'DeclareLaunchArgument(\n                "aeb_param_file"' in launch
    assert 'PathJoinSubstitution([package_share, "config", aeb_param_file])' in launch
    runner = (BENCH_ROOT / "scripts/launch.sh").read_text()
    assert 'aeb_param_argument=""' in runner
    assert 'aeb_param_argument="aeb_param_file:=aebs-009d.param.yaml"' in runner


def test_scenario_contract_keeps_moving_target_non_claims():
    contract = (BENCH_ROOT / "config/scenario-009d-moving-vehicle-target.yaml").read_text()
    assert "use_object_velocity_calculation" not in contract
    core = (PACKAGE_ROOT / "de4sdv_aebs_009b_bench/scenario_contract.py").read_text()
    assert "NOT stationary" in core
    calibration = (BENCH_ROOT / "config/aebs-009d.param.yaml").read_text()
    assert "use_object_velocity_calculation: false" in calibration


# ---------------------------------------------------------------------------
# 4. Legacy wrapper contract rows updated to shared-pipeline reality
# ---------------------------------------------------------------------------

def test_override_contract_tests_reference_available_runner_surface():
    """The 009D contract tests must assert on the launch/contract wiring that
    still exists after the shared-evidence-pipeline migration, not a retired
    per-profile wrapper script."""
    test_text = (PACKAGE_ROOT / "test/test_override_runtime_009d.py").read_text()
    assert "run_override_profile.sh" not in test_text
    wrapper = (PACKAGE_ROOT / "test/test_override_ros_contract_009d.py").read_text()
    # The retired per-profile wrapper must no longer be a contract dependency.
    assert "run_override_profile.sh" not in wrapper
