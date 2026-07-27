from pathlib import Path


PACKAGE_ROOT = Path(__file__).parents[1]
BENCH_ROOT = Path(__file__).parents[3]


def test_nominal_launch_has_no_mrm_or_diagnostic_failure_route():
    launch = (PACKAGE_ROOT / "launch/aebs_009b_bench.launch.py").read_text()
    assert "autoware_mrm" not in launch
    assert "diagnostic_graph" not in launch
    assert '"use_emergency_handling": False' in launch
    assert '"warning_margin_m": 6.0' in launch
    assert '"stop_speed_mps": 0.1' in launch
    assert '"stop_hold_s": 0.5' in launch
    assert '"odometry_max_age_s": 0.2' in launch


def test_nominal_fixture_does_not_fabricate_mrm_baseline():
    fixture = (PACKAGE_ROOT / "de4sdv_aebs_009b_bench/scenario_fixture.py").read_text()
    assert "MrmState" not in fixture
    assert "MrmBehaviorStatus" not in fixture
    assert "/system/fail_safe/mrm_state" not in fixture
    assert "/system/mrm/emergency_stop/status" not in fixture


def test_override_input_is_stamped_and_freshness_bounded():
    fixture = (PACKAGE_ROOT / "de4sdv_aebs_009b_bench/scenario_fixture.py").read_text()
    coordinator = (PACKAGE_ROOT / "de4sdv_aebs_009b_bench/aebs_coordinator.py").read_text()
    contract = (BENCH_ROOT / "config/scenario-009b-moving-vehicle-target.yaml").read_text()
    assert "BoolStamped" in fixture
    assert "BoolStamped" in coordinator
    assert "override_max_age_s" in coordinator
    assert "override_max_age_s:" in contract


def test_execution_identity_binds_native_aeb_calibration():
    identity = (BENCH_ROOT / "scripts/execution_identity.py").read_text()
    assert '"config/aebs-009b.param.yaml"' in identity


def test_independent_validator_semantically_checks_map_runtime():
    validator = (BENCH_ROOT / "scripts/validate_scenario_evidence.py").read_text()
    assert "def _verify_map_runtime(" in validator
    assert '"map_files_verified": True' in validator
    assert '"command_exit_status": 0' in validator
    assert '_verify_map_runtime(document, artifacts, root)' in validator
    assert 'map-runtime extracted map digests do not match runtime lock' in validator


def test_aeb_calibration_keeps_vehicle_hull_vertices_in_target_path():
    aeb = (BENCH_ROOT / "config/aebs-009b.param.yaml").read_text()
    assert "expand_width: 0.2" in aeb
    assert "min_generated_imu_path_length: 15.0" in aeb
    assert "max_generated_imu_path_length: 25.0" in aeb


def test_runtime_log_geometry_and_process_failures_cannot_be_published():
    runner = (BENCH_ROOT / "scripts/run_scenario.sh").read_text()
    assert "QH[0-9]+ qhull input error" in runner
    assert "ConvexHull::.*ERROR" in runner
    assert "process has died" in runner
    assert "observer_exit=97" in runner


def test_baseline_contract_has_no_mrm_observations():
    contract = (BENCH_ROOT / "config/scenario-009b-moving-vehicle-target.yaml").read_text()
    assert "/system/fail_safe/mrm_state" not in contract
    assert "/system/mrm/emergency_stop/status" not in contract
