from __future__ import annotations
from pathlib import Path
import hashlib
import json
import runpy
import pytest

from de4sdv_aebs_009b_bench.aebs_coordination_core import (
    InterventionLatch,
    next_warning_state,
    warning_requested,
)
from de4sdv_aebs_009b_bench.scenario_contract import Outcome, Pose2D, load_scenario_config
from de4sdv_aebs_009b_bench.scenario_evaluator import Observation, ObservationKind, evaluate_scenario
from de4sdv_aebs_009b_bench.footprint_geometry import footprint_relation
from de4sdv_aebs_009b_bench.scenario_observer_core import failure_is_pending, normalize_risk_payload
from de4sdv_aebs_009b_bench.scenario_fixture_core import (
    ScenarioFixtureState,
    nominal_acceleration_for_speed,
)

CONFIG_PATH = Path(__file__).parents[3] / "config" / "scenario-009b-moving-vehicle-target.yaml"
CONFIG = load_scenario_config(CONFIG_PATH)

def o(kind, at, source_stamp=None, **payload):
    return Observation(kind, payload, at, source_stamp=source_stamp)

def baseline():
    result=[]
    for at in (0.0,.4,.8,1.2,1.6,2.0):
        result += [
            o(ObservationKind.DIAGNOSTIC,at,node="autonomous_emergency_braking",task="aeb_emergency_stop",level="OK"),
            o(ObservationKind.AUTONOMOUS_AVAILABILITY,at,available=True),
            o(ObservationKind.NOMINAL_COMMAND,at,speed_mps=6.0,acceleration_mps2=1.5),
            o(ObservationKind.GATE_COMMAND,at,path="nominal",acceleration_mps2=1.5),
            o(ObservationKind.ODOMETRY,at,speed_mps=6.0,acceleration_mps2=0.0,collector_ros_stamp=f"{at:.9f}"),
        ]
    return result

def passing():
    return baseline()+[
        o(ObservationKind.TARGET_PUBLICATION,2.1,identity="target-1",frame="map",x=12.0,y=0.0,yaw_rad=0.0),
        o(ObservationKind.RISK_ASSESSMENT,2.2,rss_distance_m=8.0,object_distance_m=10.5,warning=True,intervention=False),
        o(ObservationKind.RELATIVE_STATE,2.2,gap_m=6.71,ego_speed_mps=6.0,target_speed_mps=4.0,closing_speed_mps=2.0),
        o(ObservationKind.WARNING_REQUEST,2.21,active=True),
        o(ObservationKind.RUNTIME_GRAPH,2.9,nominal_publisher_count=1.0,nominal_publishers="/:de4sdv_aebs_coordinator",mrm_publisher_count=0.0,mrm_publishers="none"),
        o(ObservationKind.OVERRIDE_EVALUATION,3.0,source_stamp="3.000000000",clear=True,source_value=False,source_age_s=0.01, context="intervention", diagnostic_source_stamp="3.100000000"),
        o(ObservationKind.DIAGNOSTIC,3.1,source_stamp="3.100000000",node="autonomous_emergency_braking",task="aeb_emergency_stop",level="ERROR"),
        o(ObservationKind.AEB_INTERVENTION,3.1,source_stamp="3.100000000",node="autonomous_emergency_braking",task="aeb_emergency_stop",level="ERROR",message="[AEB]: Emergency Brake",rss_distance_m=8.0,object_distance_m=7.5,object_speed_mps=-2.0),
        o(ObservationKind.BRAKING_REQUEST,3.11,speed_mps=0.0,acceleration_mps2=-6.0),
        o(ObservationKind.GATE_COMMAND,3.12,path="nominal",acceleration_mps2=-5.8),
        o(ObservationKind.RELATIVE_STATE,3.2,gap_m=2.0,ego_speed_mps=5.5,target_speed_mps=4.0,closing_speed_mps=1.5),
        o(ObservationKind.FOOTPRINT_STATE,3.2,ego_x=10.0,ego_y=0.0,ego_yaw_rad=0.0,target_x=17.0,target_y=0.0,target_yaw_rad=0.0,sample_skew_s=0.01,separation_m=1.16,overlap=False),
        o(ObservationKind.RUNTIME_GRAPH,3.4,nominal_publisher_count=1.0,nominal_publishers="/:de4sdv_aebs_coordinator",mrm_publisher_count=0.0,mrm_publishers="none"),
        o(ObservationKind.ODOMETRY,3.4,speed_mps=4.5,acceleration_mps2=-5.5,collector_ros_stamp="3.410000000"),
        o(ObservationKind.FOOTPRINT_STATE,3.5,ego_x=10.0,ego_y=0.0,ego_yaw_rad=0.0,target_x=17.1,target_y=0.0,target_yaw_rad=0.0,sample_skew_s=0.01,separation_m=1.26,overlap=False),
        o(ObservationKind.ODOMETRY,3.5,source_stamp="3.500000000",speed_mps=0.05,acceleration_mps2=0.0,collector_ros_stamp="3.510000000"),
        o(ObservationKind.ODOMETRY,3.6,source_stamp="3.600000000",speed_mps=0.05,acceleration_mps2=0.0,collector_ros_stamp="3.610000000"),
        o(ObservationKind.DIAGNOSTIC,3.7,source_stamp="3.700000000",node="autonomous_emergency_braking",task="aeb_emergency_stop",level="ERROR"),
        o(ObservationKind.AEB_INTERVENTION,3.7,source_stamp="3.700000000",node="autonomous_emergency_braking",task="aeb_emergency_stop",level="ERROR",message="[AEB]: Emergency Brake",rss_distance_m=8.0,object_distance_m=7.5,object_speed_mps=-2.0),
        o(ObservationKind.ODOMETRY,3.7,source_stamp="3.700000000",speed_mps=0.04,acceleration_mps2=0.0,collector_ros_stamp="3.710000000"),
        o(ObservationKind.ODOMETRY,3.8,source_stamp="3.800000000",speed_mps=0.04,acceleration_mps2=0.0,collector_ros_stamp="3.810000000"),
        o(ObservationKind.RUNTIME_GRAPH,3.9,nominal_publisher_count=1.0,nominal_publishers="/:de4sdv_aebs_coordinator",mrm_publisher_count=0.0,mrm_publishers="none"),
        o(ObservationKind.ODOMETRY,3.9,source_stamp="3.900000000",speed_mps=0.04,acceleration_mps2=0.0,collector_ros_stamp="3.910000000"),
        o(ObservationKind.COORDINATION_STATE,3.96,state="braking_latched"),
        o(ObservationKind.RUNTIME_GRAPH,4.0,nominal_publisher_count=1.0,nominal_publishers="/:de4sdv_aebs_coordinator",mrm_publisher_count=0.0,mrm_publishers="none"),
        o(ObservationKind.ODOMETRY,4.0,source_stamp="4.000000000",speed_mps=0.04,acceleration_mps2=0.0,collector_ros_stamp="4.010000000"),
        o(ObservationKind.FOOTPRINT_STATE,4.0,ego_x=10.0,ego_y=0.0,ego_yaw_rad=0.0,target_x=17.6,target_y=0.0,target_yaw_rad=0.0,sample_skew_s=0.01,separation_m=1.76,overlap=False),
        o(ObservationKind.COORDINATION_STATE,4.01,state="released_verified_stop"),
    ]

def test_contract_is_moving_same_lane_and_noncompliance_claiming():
    assert CONFIG.target_speed_mps == 1.0
    assert CONFIG.nominal_command_speed_mps > CONFIG.target_speed_mps
    assert CONFIG.target_injection_pose_base_link.y == 0.0
    nearest_target_face_m = (
        CONFIG.target_injection_pose_base_link.x - CONFIG.geometry.length_m / 2.0
    )
    assert nearest_target_face_m < CONFIG.fixture_constraints.imu_path_max_length_m
    assert any("not a safety" in item for item in CONFIG.non_claims)

def test_intervention_latch_requires_fresh_clear_entry_and_verified_stop_release():
    latch = InterventionLatch(0.1, 0.5, 0.2)
    latch.observe_diagnostic(True, False)
    assert not latch.active
    latch.observe_diagnostic(True, True)
    assert latch.active and latch.state == "braking_latched"
    latch.observe_motion(0.0, 0.3, 1.0)  # stale odometry cannot release
    latch.observe_motion(0.0, 0.01, 1.1)
    latch.observe_motion(0.0, 0.01, 1.3)
    latch.observe_motion(0.0, 0.01, 1.5)
    assert latch.active
    latch.observe_motion(0.0, 0.01, 1.6)
    assert not latch.active
    assert latch.state == "released_verified_stop"


def test_odometry_gap_resets_held_stop_release_evidence():
    latch = InterventionLatch(0.1, 0.5, 0.2)
    latch.observe_diagnostic(True, True)
    latch.observe_motion(0.0, 0.01, 1.0)
    latch.observe_motion(0.0, 0.01, 100.0)
    assert latch.active


def test_released_latch_is_absorbing_despite_diagnostic_clear_and_retention():
    latch = InterventionLatch(0.1, 0.5, 0.2)
    latch.observe_diagnostic(True, True)
    latch.observe_motion(0.0, 0.01, 1.0)
    latch.observe_motion(0.0, 0.01, 1.2)
    latch.observe_motion(0.0, 0.01, 1.4)
    latch.observe_motion(0.0, 0.01, 1.5)
    assert not latch.active
    latch.observe_diagnostic(True, True)
    latch.observe_diagnostic(False, True)
    latch.observe_diagnostic(True, True)
    assert not latch.active
    assert not latch.armed
    assert latch.state == "released_verified_stop"


def test_map_pose_footprints_detect_positive_separation_and_overlap():
    separated = footprint_relation(
        Pose2D(10.0, 0.0, 0.0), CONFIG.ego_footprint,
        Pose2D(20.0, 0.0, 0.0), CONFIG.geometry,
    )
    assert not separated.overlap
    assert separated.separation_m == pytest.approx(4.16)
    overlapping = footprint_relation(
        Pose2D(10.0, 0.0, 0.0), CONFIG.ego_footprint,
        Pose2D(14.0, 0.0, 0.0), CONFIG.geometry,
    )
    assert overlapping.overlap
    assert overlapping.separation_m == 0.0


def test_warning_compares_native_rss_with_bumper_gap_not_base_link_distance():
    assert warning_requested(17.94, 13.69, 6.0)
    assert not warning_requested(24.0, 13.69, 6.0)


def test_warning_transition_is_risk_driven_without_override_input():
    assert next_warning_state(False, "armed", 17.94, 13.69, 7.0)
    assert next_warning_state(True, "armed", 24.0, 13.69, 7.0)
    assert not next_warning_state(False, "braking_latched", 17.94, 13.69, 7.0)


def test_nominal_acceleration_stops_driving_speed_above_setpoint():
    assert nominal_acceleration_for_speed(CONFIG, 5.0) == pytest.approx(1.5)
    assert nominal_acceleration_for_speed(CONFIG, 6.0) == pytest.approx(0.0)
    assert nominal_acceleration_for_speed(CONFIG, 6.5) == pytest.approx(0.0)


def test_target_state_moves_in_map_frame():
    state = ScenarioFixtureState(CONFIG)
    state.update_ego(Pose2D(0, 0, 0))
    state.activate(10.0)
    moving = state.target_pose_map(12.0)
    assert moving is not None
    assert moving.x == pytest.approx(
        CONFIG.target_injection_pose_base_link.x + 2.0 * CONFIG.target_speed_mps
    )

def test_complete_nominal_chain_passes():
    result=evaluate_scenario(CONFIG,passing())
    assert result.outcome is Outcome.PASS_OBSERVED_CHAIN
    labels={e.label for e in result.accepted_events}
    assert {"warning_request","override_evaluated_clear","native_aeb_intervention","emergency_braking_request","normal_path_gate_command","positive_minimum_footprint_separation","opening_footprint_separation","ego_speed_reduction","verified_stop_release"} <= labels
    assert result.details["warning_lead_s"] >= .8
    assert result.details["minimum_footprint_separation_m"] > 0

@pytest.mark.parametrize("kind,failed",[
    (ObservationKind.WARNING_REQUEST,"warning_request"),
    (ObservationKind.OVERRIDE_EVALUATION,"override_evaluated_clear"),
    (ObservationKind.BRAKING_REQUEST,"emergency_braking_request"),
])
def test_missing_required_nominal_stage_fails(kind,failed):
    result=evaluate_scenario(CONFIG,[x for x in passing() if x.kind is not kind])
    assert result.outcome is Outcome.FAIL_SCENARIO
    assert result.details["failed_event"] == failed

def test_override_not_clear_cannot_trigger_brake_chain():
    items = passing()
    idx = next(i for i, x in enumerate(items) if x.kind is ObservationKind.OVERRIDE_EVALUATION)
    items[idx] = o(ObservationKind.OVERRIDE_EVALUATION, 3.0, source_stamp="3.000000000", clear=False, source_value=True, source_age_s=0.01, context="intervention", diagnostic_source_stamp="3.100000000")
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "override_evaluated_clear"


def test_override_must_remain_fresh_and_clear_at_intervention():
    items = passing()
    idx = next(i for i, x in enumerate(items) if x.kind is ObservationKind.OVERRIDE_EVALUATION)
    items[idx] = o(ObservationKind.OVERRIDE_EVALUATION, 3.0, source_stamp="2.700000000", clear=True, source_value=False, source_age_s=0.3, context="intervention", diagnostic_source_stamp="3.100000000")
    items.sort(key=lambda item: item.receipt_monotonic_s)
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "override_evaluated_clear"


def test_contradictory_baseline_sample_fails_stability():
    items = passing()
    items.append(o(ObservationKind.AUTONOMOUS_AVAILABILITY, 1.0, available=False))
    items.sort(key=lambda item: item.receipt_monotonic_s)
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "baseline_precondition"


def test_emergency_gate_status_contaminates_nominal_path():
    items = passing() + [o(ObservationKind.GATE_EMERGENCY_STATUS, 3.115, emergency=True)]
    items.sort(key=lambda item: item.receipt_monotonic_s)
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "nominal_path_isolation"


def test_runtime_graph_requires_sole_coordinator_and_no_mrm_publishers():
    items = passing()
    idx = next(i for i, x in enumerate(items) if x.kind is ObservationKind.RUNTIME_GRAPH)
    items[idx] = o(ObservationKind.RUNTIME_GRAPH,2.9,nominal_publisher_count=2.0,nominal_publishers="/:de4sdv_aebs_coordinator,/:rogue",mrm_publisher_count=1.0,mrm_publishers="/:rogue_mrm")
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "runtime_graph_isolation"

def test_runtime_graph_requires_bounded_coverage_through_release():
    items = [
        item for item in passing()
        if item.kind is not ObservationKind.RUNTIME_GRAPH
        or item.receipt_monotonic_s <= 2.9
    ]
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "runtime_graph_isolation"


def test_post_intervention_runtime_graph_contamination_fails():
    items = passing() + [o(
        ObservationKind.RUNTIME_GRAPH, 3.13,
        nominal_publisher_count=2.0,
        nominal_publishers="/:de4sdv_aebs_coordinator,/:rogue",
        mrm_publisher_count=1.0,
        mrm_publishers="/:rogue_mrm",
    )]
    items.sort(key=lambda item: item.receipt_monotonic_s)
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "runtime_graph_isolation"


def test_held_stop_replay_rejects_ancient_source_stamps():
    items = passing()
    for index, item in enumerate(items):
        if item.kind is ObservationKind.ODOMETRY and 3.5 <= item.receipt_monotonic_s <= 4.0:
            items[index] = o(
                ObservationKind.ODOMETRY,
                item.receipt_monotonic_s,
                source_stamp="0.000000001",
                **item.payload,
            )
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "verified_ego_stop"


def test_scenario_config_round_trip_preserves_complete_contract():
    assert type(CONFIG).from_mapping(CONFIG.to_mapping()) == CONFIG


def test_short_warning_lead_fails():
    items = passing()
    override_i = next(i for i, x in enumerate(items) if x.kind is ObservationKind.OVERRIDE_EVALUATION)
    diagnostic_i = next(i for i, x in enumerate(items) if x.kind is ObservationKind.DIAGNOSTIC and x.payload["level"] == "ERROR")
    intervention_i = next(i for i, x in enumerate(items) if x.kind is ObservationKind.AEB_INTERVENTION)
    items[override_i] = o(ObservationKind.OVERRIDE_EVALUATION, 2.8, source_stamp="2.800000000", clear=True, source_value=False, source_age_s=0.01, context="intervention", diagnostic_source_stamp="2.900000000")
    items[diagnostic_i] = o(ObservationKind.DIAGNOSTIC, 2.9, source_stamp="2.900000000", node="autonomous_emergency_braking", task="aeb_emergency_stop", level="ERROR")
    items[intervention_i] = o(ObservationKind.AEB_INTERVENTION, 2.9, source_stamp="2.900000000", node="autonomous_emergency_braking", task="aeb_emergency_stop", level="ERROR", message="[AEB]: Emergency Brake", rss_distance_m=8.0, object_distance_m=7.5, object_speed_mps=2.0)
    items.sort(key=lambda item: item.receipt_monotonic_s)
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "warning_lead"

def test_weak_braking_request_fails():
    items = passing()
    idx = next(i for i, x in enumerate(items) if x.kind is ObservationKind.BRAKING_REQUEST)
    items[idx] = o(ObservationKind.BRAKING_REQUEST, 3.11, speed_mps=0.0, acceleration_mps2=-4.9)
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "emergency_braking_request"

def test_overlap_fails_outcome():
    items=[x for x in passing() if x.kind is not ObservationKind.FOOTPRINT_STATE]
    items += [o(ObservationKind.FOOTPRINT_STATE,3.3,ego_x=10.0,ego_y=0.0,ego_yaw_rad=0.0,target_x=13.0,target_y=0.0,target_yaw_rad=0.0,sample_skew_s=.01,separation_m=0.0,overlap=True)]
    items.sort(key=lambda item: item.receipt_monotonic_s)
    result = evaluate_scenario(CONFIG,items)
    assert result.details["failed_event"] == "footprint_outcome"
    assert not failure_is_pending(result)


def test_positive_gap_without_future_opening_is_pending_collection():
    items = [x for x in passing() if x.receipt_monotonic_s <= 3.2]
    result = evaluate_scenario(CONFIG, items)
    assert result.details["failed_event"] == "footprint_outcome"
    assert failure_is_pending(result)


def test_fabricated_footprint_relation_fails_replay_integrity():
    items = passing()
    index = next(i for i, item in enumerate(items) if item.kind is ObservationKind.FOOTPRINT_STATE)
    original = items[index]
    items[index] = o(ObservationKind.FOOTPRINT_STATE, original.receipt_monotonic_s,
        ego_x=10.0, ego_y=0.0, ego_yaw_rad=0.0,
        target_x=17.0, target_y=0.0, target_yaw_rad=0.0,
        sample_skew_s=0.01, separation_m=99.0, overlap=False)
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "footprint_integrity"


def test_release_requires_held_stop_and_diagnostic_expiry_independence():
    no_hold = [x for x in passing() if not (x.kind is ObservationKind.ODOMETRY and x.receipt_monotonic_s == 3.5)]
    assert evaluate_scenario(CONFIG, no_hold).details["failed_event"] == "verified_ego_stop"
    no_latched_guard = [x for x in passing() if not (x.kind is ObservationKind.COORDINATION_STATE and x.receipt_monotonic_s == 3.96)]
    assert evaluate_scenario(CONFIG, no_latched_guard).details["failed_event"] == "diagnostic_release_independence"
    retained = [x for x in no_latched_guard if not (x.kind is ObservationKind.AEB_INTERVENTION and x.receipt_monotonic_s == 3.7)]
    retained.extend([
        o(ObservationKind.DIAGNOSTIC,3.95,source_stamp="3.950000000",node="autonomous_emergency_braking",task="aeb_emergency_stop",level="ERROR"),
        o(ObservationKind.AEB_INTERVENTION,3.95,source_stamp="3.950000000",node="autonomous_emergency_braking",task="aeb_emergency_stop",level="ERROR",message="[AEB]: Emergency Brake",rss_distance_m=8.0,object_distance_m=7.5,object_speed_mps=-2.0),
    ])
    retained.sort(key=lambda item: item.receipt_monotonic_s)
    result = evaluate_scenario(CONFIG, retained)
    assert result.outcome is Outcome.PASS_OBSERVED_CHAIN
    assert result.details["diagnostic_release_relation"] == "release_while_native_diagnostic_retained"


def test_mrm_or_reordered_observation_cannot_pass_nominal_chain():
    contaminated = passing() + [o(ObservationKind.MRM_STATE,4.02,state="MRM_OPERATING",behavior="EMERGENCY_STOP")]
    assert evaluate_scenario(CONFIG, contaminated).details["failed_event"] == "nominal_path_isolation"
    reordered = passing()
    reordered[-1], reordered[-2] = reordered[-2], reordered[-1]
    assert evaluate_scenario(CONFIG, reordered).details["failed_event"] == "observation_order"


def test_baseline_requires_exact_native_aeb_diagnostic_identity():
    items = []
    for item in passing():
        if item.kind is ObservationKind.DIAGNOSTIC and item.payload["level"] == "OK":
            items.append(o(
                ObservationKind.DIAGNOSTIC,
                item.receipt_monotonic_s,
                source_stamp=item.source_stamp,
                node="rogue_aeb",
                task="forged_task",
                level="OK",
            ))
        else:
            items.append(item)
    assert evaluate_scenario(CONFIG, items).details["failed_event"] == "baseline_precondition"


def test_required_artifact_roles_must_resolve_to_distinct_files(tmp_path):
    artifact = tmp_path / "artifact.txt"
    artifact.write_text("one physical file", encoding="utf-8")
    digest = hashlib.sha256(artifact.read_bytes()).hexdigest()
    roles = {
        "observer_raw", "observer_log", "launch_log", "run_metadata", "map_runtime"
    }
    document = {
        "artifacts": {
            role: {"path": artifact.name, "sha256": digest} for role in roles
        }
    }
    validator = runpy.run_path(str(CONFIG_PATH.parents[1] / "scripts" / "validate_scenario_evidence.py"))
    with pytest.raises(validator["ValidationError"], match="distinct"):
        validator["_verify_artifacts"](document, tmp_path)


def test_risk_payload_requires_exact_shape_and_real_booleans():
    assert normalize_risk_payload({
        "rss_distance_m": 8,
        "object_distance_m": 10.5,
        "warning": False,
        "intervention": True,
    }) == {
        "rss_distance_m": 8.0,
        "object_distance_m": 10.5,
        "warning": False,
        "intervention": True,
    }
    with pytest.raises(ValueError, match="exact keys"):
        normalize_risk_payload({
            "rss_distance_m": 8,
            "object_distance_m": 10.5,
            "warning": False,
            "intervention": True,
            "unknown": "discarded",
        })
    for malformed in ("false", 0, 1, None):
        with pytest.raises(ValueError, match="JSON booleans"):
            normalize_risk_payload({
                "rss_distance_m": 8,
                "object_distance_m": 10.5,
                "warning": malformed,
                "intervention": False,
            })


def test_map_runtime_extracted_hashes_must_match_runtime_lock(tmp_path):
    bench_root = CONFIG_PATH.parents[1]
    evidence = json.loads(
        (bench_root / "evidence/009b/scenario-evidence.json").read_text(encoding="utf-8")
    )
    runtime_source = bench_root / evidence["artifacts"]["map_runtime"]["path"]
    runtime = json.loads(runtime_source.read_text(encoding="utf-8"))
    runtime["extracted_sha256"]["lanelet2_map.osm"] = "0" * 64
    runtime_path = tmp_path / "map-runtime.json"
    runtime_path.write_text(json.dumps(runtime), encoding="utf-8")
    (tmp_path / "runtime-lock.yaml").write_bytes(
        (bench_root / "runtime-lock.yaml").read_bytes()
    )
    validator = runpy.run_path(
        str(bench_root / "scripts" / "validate_scenario_evidence.py")
    )
    with pytest.raises(validator["ValidationError"], match="do not match runtime lock"):
        validator["_verify_map_runtime"](
            evidence, {"map_runtime": runtime_path}, tmp_path
        )
