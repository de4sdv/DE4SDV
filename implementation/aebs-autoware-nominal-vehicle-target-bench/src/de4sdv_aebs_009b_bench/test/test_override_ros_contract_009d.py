import os
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

PACKAGE_ROOT = Path(__file__).parents[1]
BENCH_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PACKAGE_ROOT))

from de4sdv_aebs_009b_bench.aebs_coordination_core import classify_override_source
from de4sdv_aebs_009b_bench.override_fixture_core import override_publication
from de4sdv_aebs_009b_bench.override_matrix import OverrideScenario
from de4sdv_aebs_009b_bench.scenario_evaluator import Observation, ObservationKind


@pytest.mark.parametrize(
    "scenario,expected",
    [
        (OverrideScenario.FRESH_FALSE_CONTROL, (False, 100_000_000_000)),
        (OverrideScenario.FRESH_TRUE_CONSCIOUS, (True, 100_000_000_000)),
        (OverrideScenario.STALE, (True, 99_700_000_000)),
        (OverrideScenario.MISSING, None),
        (OverrideScenario.MALFORMED, (True, 0)),
        (OverrideScenario.FUTURE_STAMPED, (True, 100_100_000_000)),
    ],
)
def test_typed_fixture_publication_matrix(scenario, expected):
    assert override_publication(scenario, 100_000_000_000) == expected


def test_override_source_classification_is_closed_and_diagnostic_relative():
    assert (
        classify_override_source(False, 100_100_000_000, 100_200_000_000, 0.2)
        == "control_clear"
    )
    assert (
        classify_override_source(True, 100_100_000_000, 100_200_000_000, 0.2)
        == "conscious_override"
    )
    assert (
        classify_override_source(True, 99_900_000_000, 100_200_000_000, 0.2)
        == "degraded_stale_source"
    )
    assert (
        classify_override_source(None, None, 100_200_000_000, 0.2)
        == "inconclusive_missing_source"
    )
    assert (
        classify_override_source(True, 0, 100_200_000_000, 0.2)
        == "error_malformed_source"
    )
    assert (
        classify_override_source(True, 100_300_000_000, 100_200_000_000, 0.2)
        == "error_future_source"
    )


def test_fixture_and_coordinator_keep_ros_transport_typed():
    fixture = (PACKAGE_ROOT / "de4sdv_aebs_009b_bench/scenario_fixture.py").read_text()
    coordinator = (
        PACKAGE_ROOT / "de4sdv_aebs_009b_bench/aebs_coordinator.py"
    ).read_text()
    assert 'declare_parameter("override_scenario"' in fixture
    assert "BoolStamped" in fixture
    assert '"/de4sdv/aebs_009d/override_authorization"' in coordinator
    assert "DiagnosticArray" in coordinator
    assert "KeyValue" in coordinator
    observer = (
        PACKAGE_ROOT / "de4sdv_aebs_009b_bench/scenario_observer.py"
    ).read_text()
    assert '"/de4sdv/aebs_009d/override_authorization"' in observer


def test_typed_authorization_is_a_closed_replayable_observation():
    item = Observation(
        ObservationKind.OVERRIDE_AUTHORIZATION,
        {
            "override_source_value": "true",
            "override_source_stamp": "100.100000000",
            "authorization_diagnostic_source_stamp": "100.200000000",
            "disposition": "conscious_override",
        },
        10.2,
        source_stamp="100.200000000",
    )
    assert item.payload["disposition"] == "conscious_override"


def test_installed_matrix_config_is_closed_and_package_owned():
    setup = (PACKAGE_ROOT / "setup.py").read_text()
    matrix = (
        BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    ).read_text()
    for value in OverrideScenario:
        assert value.value in matrix
    assert "scenario-009d-conscious-override-matrix.yaml" in setup
    launch = (PACKAGE_ROOT / "launch/aebs_009b_bench.launch.py").read_text()
    assert 'DeclareLaunchArgument("override_scenario"' in launch
    assert '"override_scenario": LaunchConfiguration("override_scenario")' in launch


def test_launch_rejects_unclosed_profile_before_any_runtime_action():
    environment = {**os.environ, "DE4SDV_009D_PROFILE": "not-a-profile"}
    result = subprocess.run(
        [str(BENCH_ROOT / "scripts/launch.sh")],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "Invalid 009D override profile" in result.stderr


def test_matrix_wrapper_retains_six_separate_profile_destinations():
    launch = (BENCH_ROOT / "scripts/launch.sh").read_text()
    contract = yaml.safe_load(
        (BENCH_ROOT / "config/contract-009d.yaml").read_text()
    )
    # The closed 009D profile set drives per-profile evidence destinations via
    # the shared framework contract (artifact_path_prefix_template), replacing
    # the retired per-profile wrapper script.
    assert contract["profile_values"] == [p.value for p in OverrideScenario]
    assert contract["artifact_path_prefix_template"] == (
        "{evidence_dir}/profiles/{profile}"
    )
    assert "override_scenario:=$profile" in launch
    assert contract["evidence_dir"] == "evidence/009d"
