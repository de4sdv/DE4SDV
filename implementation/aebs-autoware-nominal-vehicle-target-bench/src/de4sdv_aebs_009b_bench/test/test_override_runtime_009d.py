import sys
from pathlib import Path

import pytest
import yaml

PACKAGE_ROOT = Path(__file__).parents[1]
BENCH_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PACKAGE_ROOT))
sys.path.insert(0, str(BENCH_ROOT / "scripts"))

from de4sdv_aebs_009b_bench.override_matrix import OverrideDisposition, OverrideScenario
from de4sdv_aebs_009b_bench.override_runtime import (
    evaluate_profile,
    load_matrix_contract,
    override_result_to_json,
    terminal_override_result,
)
from de4sdv_aebs_009b_bench.scenario_contract import load_scenario_config
from de4sdv_aebs_009b_bench.scenario_evaluator import (
    Observation,
    ObservationKind,
    evaluate_scenario,
)
from evidence_document import (
    CLOCK_BOUNDARY,
    evaluation_to_json,
    observation_to_json,
    validate_raw_semantics,
)
from evidence_pipeline import build_evidence, load_contract
from evidence_validator import ValidationError


def _verify_009d_artifact_paths(document, profile):
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, dict):
        raise ValidationError("009D artifacts must be an object")
    paths = [record.get("path") for record in artifacts.values() if isinstance(record, dict)]
    if len(paths) != len(artifacts) or len(set(paths)) != len(paths):
        raise ValidationError("009D artifact roles require distinct paths")
    prefix = f"evidence/009d/profiles/{profile.value}/runs/"
    if any(not isinstance(path, str) or not path.startswith(prefix) for path in paths):
        raise ValidationError("009D artifact path is not profile-specific")
    run_parents = {str(Path(path).parent) for path in paths}
    if len(run_parents) != 1:
        raise ValidationError("009D artifacts must belong to one isolated run bundle")


def _require_exact_execution_head(stored_head, expected_head):
    if stored_head != expected_head:
        raise ValidationError("recorded 009D repository head differs from exact campaign head")


def build_override_evidence(raw, profile, provenance, artifacts, *, matrix_path):
    contract = load_contract(BENCH_ROOT / "config/contract-009d.yaml")
    return build_evidence(
        raw,
        profile,
        provenance,
        artifacts,
        contract=contract,
        bench_root=BENCH_ROOT,
    )


def obs(kind, at, source_stamp=None, **payload):
    return Observation(kind, payload, at, source_stamp=source_stamp)


def observations(
    *,
    disposition="conscious_override",
    source_value="true",
    source_stamp="100.100000000",
    brake=False,
    end=10.5,
):
    values = [
        obs(
            ObservationKind.RUNTIME_GRAPH,
            9.9,
            nominal_publisher_count=1.0,
            nominal_publishers="/:de4sdv_aebs_coordinator",
            mrm_publisher_count=0.0,
            mrm_publishers="none",
        ),
        obs(
            ObservationKind.RISK_ASSESSMENT,
            10.0,
            rss_distance_m=8.0,
            object_distance_m=7.5,
            warning=True,
            intervention=False,
        ),
        obs(
            ObservationKind.RUNTIME_GRAPH,
            10.05,
            nominal_publisher_count=1.0,
            nominal_publishers="/:de4sdv_aebs_coordinator",
            mrm_publisher_count=0.0,
            mrm_publishers="none",
        ),
        obs(ObservationKind.WARNING_REQUEST, 10.1, active=True),
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
        obs(
            ObservationKind.OVERRIDE_AUTHORIZATION,
            10.2,
            source_stamp="100.200000000",
            override_source_value=source_value,
            override_source_stamp=source_stamp,
            authorization_diagnostic_source_stamp="100.200000000",
            disposition=disposition,
        ),
        obs(
            ObservationKind.RUNTIME_GRAPH,
            10.25,
            nominal_publisher_count=1.0,
            nominal_publishers="/:de4sdv_aebs_coordinator",
            mrm_publisher_count=0.0,
            mrm_publishers="none",
        ),
        obs(
            ObservationKind.RUNTIME_GRAPH,
            min(10.4, end),
            nominal_publisher_count=1.0,
            nominal_publishers="/:de4sdv_aebs_coordinator",
            mrm_publisher_count=0.0,
            mrm_publishers="none",
        ),
        obs(
            ObservationKind.RUNTIME_GRAPH,
            end,
            nominal_publisher_count=1.0,
            nominal_publishers="/:de4sdv_aebs_coordinator",
            mrm_publisher_count=0.0,
            mrm_publishers="none",
        ),
    ]
    if brake:
        values.insert(
            -2,
            obs(
                ObservationKind.BRAKING_REQUEST,
                10.21,
                speed_mps=0.0,
                acceleration_mps2=-6.0,
            ),
        )
    return sorted(values, key=lambda item: item.receipt_monotonic_s)


def valid_raw(profile, items, evaluation):
    config = load_scenario_config(
        BENCH_ROOT / "config/scenario-009b-moving-vehicle-target.yaml"
    )
    timeout = config.scenario_timeout_s
    return {
        "collector_id": "de4sdv.scenario_observer.v1",
        "monotonic_start_s": 9.0,
        "monotonic_end_s": 10.5,
        "clock_boundary": CLOCK_BOUNDARY,
        "observations": [observation_to_json(item) for item in items],
        "evaluator_result": evaluation_to_json(evaluate_scenario(config, items)),
        "activation": {
            "request_time_s": 9.1,
            "response_time_s": 9.2,
            "status": "succeeded",
            "response_message": "accepted",
        },
        "errors": [],
        "terminal_reason": "pass_override_profile",
        "command_exit": 0,
        "limits": {
            "timeout_s": timeout,
            "deadline_s": 9.0 + timeout,
            "observation_cap": min(100_000, max(1_000, int(timeout * 1_000))),
            "error_cap": 256,
        },
        "override_profile": profile.value,
        "override_evaluator_result": evaluation,
    }


def test_authoritative_matrix_contract_contains_six_unique_profiles():
    matrix = load_matrix_contract(
        BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    )
    assert tuple(matrix.scenarios) == tuple(OverrideScenario)
    assert len({entry.scenario_id for entry in matrix.scenarios.values()}) == 6


def test_runtime_profile_replays_typed_authorization_and_closed_window():
    matrix = load_matrix_contract(
        BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    )
    result = evaluate_profile(
        matrix,
        OverrideScenario.FRESH_TRUE_CONSCIOUS,
        observations(),
        window_end_receipt_s=10.5,
    )
    assert result.passed
    assert result.disposition is OverrideDisposition.CONSCIOUS_OVERRIDE
    assert terminal_override_result(result) == "pass_override_profile"
    assert (
        override_result_to_json(result)["scenario"] == "fresh_true_conscious_override"
    )


def test_runtime_profile_rejects_authorization_contradiction_duplicate_and_graph_gap():
    matrix = load_matrix_contract(
        BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    )
    contradictory = observations(disposition="control_clear")
    assert not evaluate_profile(
        matrix,
        OverrideScenario.FRESH_TRUE_CONSCIOUS,
        contradictory,
        window_end_receipt_s=10.5,
    ).passed
    duplicate = observations()
    duplicate.append(duplicate[6])
    assert not evaluate_profile(
        matrix,
        OverrideScenario.FRESH_TRUE_CONSCIOUS,
        duplicate,
        window_end_receipt_s=10.5,
    ).passed
    gap = [
        item
        for item in observations()
        if item.kind is not ObservationKind.RUNTIME_GRAPH
        or item.receipt_monotonic_s in {9.9, 10.5}
    ]
    result = evaluate_profile(
        matrix, OverrideScenario.FRESH_TRUE_CONSCIOUS, gap, window_end_receipt_s=10.5
    )
    assert not result.passed
    assert "graph" in result.reason.lower()


def test_suppression_open_window_remains_pending_then_closes():
    matrix = load_matrix_contract(
        BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    )
    open_result = evaluate_profile(
        matrix,
        OverrideScenario.FRESH_TRUE_CONSCIOUS,
        observations(end=10.3),
        window_end_receipt_s=10.3,
    )
    assert open_result.disposition is OverrideDisposition.INCONCLUSIVE_OPEN_WINDOW
    assert terminal_override_result(open_result) is None
    closed = evaluate_profile(
        matrix,
        OverrideScenario.FRESH_TRUE_CONSCIOUS,
        observations(),
        window_end_receipt_s=10.5,
    )
    assert terminal_override_result(closed) == "pass_override_profile"


def test_warning_precursor_need_not_already_cross_native_intervention_threshold():
    matrix = load_matrix_contract(
        BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    )
    items = observations(
        disposition="control_clear", source_value="false", brake=True
    )
    risk_index = next(
        index
        for index, item in enumerate(items)
        if item.kind is ObservationKind.RISK_ASSESSMENT
    )
    items[risk_index] = obs(
        ObservationKind.RISK_ASSESSMENT,
        items[risk_index].receipt_monotonic_s,
        rss_distance_m=8.0,
        object_distance_m=9.0,
        warning=True,
        intervention=False,
    )
    result = evaluate_profile(
        matrix,
        OverrideScenario.FRESH_FALSE_CONTROL,
        items,
        window_end_receipt_s=10.5,
    )
    assert result.passed


def test_exact_authorization_waits_for_late_native_risk_precursor():
    matrix = load_matrix_contract(
        BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    )
    items = [
        item
        for item in observations()
        if item.kind is not ObservationKind.RISK_ASSESSMENT
    ]
    result = evaluate_profile(
        matrix,
        OverrideScenario.FRESH_TRUE_CONSCIOUS,
        items,
        window_end_receipt_s=10.5,
    )
    assert result.disposition is OverrideDisposition.INCONCLUSIVE_NATIVE_CHAIN
    assert terminal_override_result(result) is None


def test_fresh_false_waits_through_transient_stale_authorization():
    result = evaluate_profile(
        load_matrix_contract(
            BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
        ),
        OverrideScenario.FRESH_FALSE_CONTROL,
        observations(
            disposition="degraded_stale_source",
            source_value="false",
            source_stamp="99.900000000",
            brake=True,
        ),
        window_end_receipt_s=10.5,
    )
    assert not result.passed
    assert result.disposition is OverrideDisposition.ERROR_SCENARIO_CONTRACT
    assert terminal_override_result(result) is None


@pytest.mark.parametrize(
    "fabricated",
    [
        "f7f53d77cb3e541b88646b708e9343680bb5596e",
        "a1d1c5dc66f8406e9d571e902c33b2d10aa4dc5e",
    ],
)
def test_retained_campaign_rejects_stale_or_future_execution_head(fabricated):
    with pytest.raises(ValidationError, match="exact campaign head"):
        _require_exact_execution_head(
            fabricated, "01d9f586865bf7fb4bc0b3f76be2b5a916451da4"
        )


def test_clear_control_waits_for_braking_until_observation_window_closes():
    matrix = load_matrix_contract(
        BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    )
    pending = evaluate_profile(
        matrix,
        OverrideScenario.FRESH_FALSE_CONTROL,
        observations(disposition="control_clear", source_value="false", end=10.3),
        window_end_receipt_s=10.3,
    )
    assert pending.disposition is OverrideDisposition.INCONCLUSIVE_OPEN_WINDOW
    assert terminal_override_result(pending) is None

    failed = evaluate_profile(
        matrix,
        OverrideScenario.FRESH_FALSE_CONTROL,
        observations(disposition="control_clear", source_value="false"),
        window_end_receipt_s=10.5,
    )
    assert failed.disposition is OverrideDisposition.ERROR_FAIL_CLOSED_BREACH
    assert terminal_override_result(failed) == "terminal_override_failure"


def test_failed_009d_terminal_is_known_but_cannot_be_a_success_terminal():
    profile = OverrideScenario.FRESH_TRUE_CONSCIOUS
    matrix = load_matrix_contract(
        BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    )
    items = observations()
    result = override_result_to_json(
        evaluate_profile(matrix, profile, items, window_end_receipt_s=10.5)
    )
    raw = valid_raw(profile, items, result)
    raw["terminal_reason"] = "terminal_override_failure"
    raw["command_exit"] = 1
    config = load_scenario_config(
        BENCH_ROOT / "config/scenario-009b-moving-vehicle-target.yaml"
    )
    validate_raw_semantics(
        raw,
        config,
        raw["evaluator_result"],
        success_terminal="pass_override_profile",
        success_evaluation_outcome=None,
        additional_terminal_reasons={"terminal_override_failure"},
    )


def test_009d_resolved_timing_input_preserves_criterion_and_adds_margin():
    inherited = load_scenario_config(
        BENCH_ROOT / "config/scenario-009b-moving-vehicle-target.yaml"
    )
    resolved = load_scenario_config(
        BENCH_ROOT / "config/scenario-009d-moving-vehicle-target.yaml"
    )
    assert resolved.scenario_id == "SCN-AEBS-009D-INHERITED-MOVING-VEHICLE-001"
    assert resolved.scenario_id != inherited.scenario_id
    assert resolved.outcome_contract.warning_lead_min_s == 0.8
    assert inherited.outcome_contract.warning_margin_m == 6.0
    assert resolved.outcome_contract.warning_margin_m == 7.0
    setup = (PACKAGE_ROOT / "setup.py").read_text()
    launch = (BENCH_ROOT / "scripts/launch.sh").read_text()
    runner = (BENCH_ROOT / "scripts/run_override_profile.sh").read_text()
    assert '"../../config/scenario-009d-moving-vehicle-target.yaml"' in setup
    assert "scenario_config_name:=scenario-009d-moving-vehicle-target.yaml" in launch
    assert '"warning_margin_m"' in launch
    assert "config/scenario-009d-moving-vehicle-target.yaml" in launch
    assert "config/scenario-009d-moving-vehicle-target.yaml" in runner


def test_matrix_loader_rejects_duplicate_profiles(tmp_path):
    source = yaml.safe_load(
        (BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml").read_text()
    )
    source["scenarios"][1]["profile"] = source["scenarios"][0]["profile"]
    path = tmp_path / "matrix.yaml"
    path.write_text(yaml.safe_dump(source))
    with pytest.raises(ValueError, match="exactly once"):
        load_matrix_contract(path)


@pytest.mark.parametrize(
    "profile,disposition,value,stamp,brake",
    [
        (
            OverrideScenario.FRESH_FALSE_CONTROL,
            "control_clear",
            "false",
            "100.100000000",
            True,
        ),
        (
            OverrideScenario.FRESH_TRUE_CONSCIOUS,
            "conscious_override",
            "true",
            "100.100000000",
            False,
        ),
        (
            OverrideScenario.STALE,
            "degraded_stale_source",
            "true",
            "99.900000000",
            True,
        ),
        (
            OverrideScenario.MISSING,
            "inconclusive_missing_source",
            "none",
            "none",
            True,
        ),
        (
            OverrideScenario.MALFORMED,
            "error_malformed_source",
            "true",
            "0.000000000",
            True,
        ),
        (
            OverrideScenario.FUTURE_STAMPED,
            "error_future_source",
            "true",
            "100.300000000",
            True,
        ),
    ],
)
def test_evidence_builder_independently_replays_each_profile(
    profile, disposition, value, stamp, brake
):
    items = observations(
        disposition=disposition,
        source_value=value,
        source_stamp=stamp,
        brake=brake,
    )
    matrix = load_matrix_contract(
        BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    )
    evaluation = override_result_to_json(
        evaluate_profile(matrix, profile, items, window_end_receipt_s=10.5)
    )
    raw = valid_raw(profile, items, evaluation)
    document = build_override_evidence(
        raw,
        profile,
        {"override_profile": profile.value},
        {},
        matrix_path=BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml",
    )
    assert document["profile"] == profile.value
    assert document["evaluation"]["passed"] is True
    raw["override_evaluator_result"] = {**evaluation, "passed": False}
    with pytest.raises(ValueError, match="independent replay"):
        build_override_evidence(
            raw,
            profile,
            {},
            {},
            matrix_path=BENCH_ROOT
            / "config/scenario-009d-conscious-override-matrix.yaml",
        )


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda raw: raw.update(monotonic_start_s=999.0), "reversed"),
        (lambda raw: raw.update(collector_id="fabricated"), "collector_id"),
        (lambda raw: raw.update(clock_boundary="fabricated"), "clock_boundary"),
        (
            lambda raw: raw.update(
                activation={
                    "request_time_s": 9.1,
                    "response_time_s": 9.2,
                    "status": "failed",
                    "response_message": "rejected",
                }
            ),
            "passing result",
        ),
        (lambda raw: raw.update(errors=["native observer exception"]), "passing result"),
        (
            lambda raw: raw["limits"].update(timeout_s=-1.0),
            "finite number|positive|authoritative scenario timeout",
        ),
        (lambda raw: raw.update(evaluator_result={}), "inherited 009B result"),
        (
            lambda raw: raw["observations"].reverse(),
            "inherited 009B result|monotonic receipt order",
        ),
    ],
)
def test_evidence_builder_rejects_contradictory_collector_envelope(mutation, match):
    profile = OverrideScenario.FRESH_TRUE_CONSCIOUS
    items = observations()
    matrix_path = BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml"
    matrix = load_matrix_contract(matrix_path)
    evaluation = override_result_to_json(
        evaluate_profile(matrix, profile, items, window_end_receipt_s=10.5)
    )
    raw = valid_raw(profile, items, evaluation)
    mutation(raw)
    with pytest.raises((TypeError, ValueError), match=match):
        build_override_evidence(raw, profile, {}, {}, matrix_path=matrix_path)


@pytest.mark.parametrize(
    "field,value",
    [
        ("diagnostic_node", "wrong_node"),
        ("diagnostic_task", "wrong_task"),
        ("diagnostic_level", "WARN"),
        ("diagnostic_message", "wrong message"),
    ],
)
def test_matrix_diagnostic_identity_is_authoritative(tmp_path, field, value):
    source = yaml.safe_load(
        (BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml").read_text()
    )
    source["contract"][field] = value
    path = tmp_path / "matrix.yaml"
    path.write_text(yaml.safe_dump(source))
    result = evaluate_profile(
        load_matrix_contract(path),
        OverrideScenario.FRESH_TRUE_CONSCIOUS,
        observations(),
        window_end_receipt_s=10.5,
    )
    assert not result.passed
    assert "authorization" in result.reason


def test_matrix_rejects_profile_braking_or_disposition_contradiction(tmp_path):
    source = yaml.safe_load(
        (BENCH_ROOT / "config/scenario-009d-conscious-override-matrix.yaml").read_text()
    )
    source["scenarios"][1]["expected_braking_request"] = True
    path = tmp_path / "matrix.yaml"
    path.write_text(yaml.safe_dump(source))
    with pytest.raises(ValueError, match="contradicts"):
        load_matrix_contract(path)


def test_validator_requires_distinct_profile_specific_artifact_paths():
    profile = OverrideScenario.STALE
    prefix = "evidence/009d/profiles/stale/runs/run-1"
    artifacts = {
        role: {"path": f"{prefix}/{role}.json", "sha256": "0" * 64}
        for role in (
            "observer_raw",
            "observer_log",
            "launch_log",
            "run_metadata",
            "map_runtime",
        )
    }
    _verify_009d_artifact_paths({"artifacts": artifacts}, profile)
    artifacts["observer_log"]["path"] = artifacts["observer_raw"]["path"]
    with pytest.raises(ValidationError, match="distinct"):
        _verify_009d_artifact_paths({"artifacts": artifacts}, profile)
    artifacts["observer_log"]["path"] = "evidence/009b/runs/run-1/observer.log"
    with pytest.raises(ValidationError, match="profile-specific"):
        _verify_009d_artifact_paths({"artifacts": artifacts}, profile)
