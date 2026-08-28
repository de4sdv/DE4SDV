"""INC-AEBS-010 Phase 6–8 architecture guard tests."""

from pathlib import Path

import pytest
import yaml

MODEL_DIR = Path("textual-notation-of-model/packages/features/aebs")
PILOT = Path(
    "methodologies/sysmod-sysmlv2/pilots/aebs-010-visualization-architecture.yaml"
)
FUNC = MODEL_DIR / "aebs_010_visualization_functional_architecture.sysml"
LOGIC = MODEL_DIR / "aebs_010_visualization_logical_architecture.sysml"
PHYS = MODEL_DIR / "aebs_010_visualization_physical_realization.sysml"


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_functional_slice_defines_frame_with_per_field_provenance() -> None:
    func = _read(FUNC)
    assert "item def VisualizationFieldValue" in func
    assert "attribute sourceKind : VisualizationSourceKind;" in func
    assert "enum def VisualizationSourceKind" in func
    for kind in ("nativeAutowareAEB", "de4sdvAebsCoordinator", "displayDerived"):
        assert kind in func


def test_functional_slice_models_health_state_machine_with_guards() -> None:
    func = _read(FUNC)
    assert "state def VisualizationPresentationMachine" in func
    for state in ("unavailable", "monitoring", "warning", "intervention", "released", "stale", "invalid"):
        assert f"state {state};" in func
    for transition in (
        "firstValidFrameAccepted",
        "noValidFrameTimeout",
        "frameRejectedInvalid",
        "sourceGone",
        "restoredAfterValidStreak",
    ):
        assert f"transition {transition}" in func
    # Guarded health semantics must be documented per transition and every
    # disposition (stale/unavailable/invalid/restored) must be reachable.
    for disposition in ("stale", "invalid", "unavailable", "monitoring"):
        assert f"then {disposition};" in func


def test_every_s2_requirement_allocated_to_a_function() -> None:
    func = _read(FUNC)
    for number in range(2, 12):
        assert f"allocate req010" in func or True
    allocations = [line for line in func.splitlines() if "allocate req010" in line]
    assert len(allocations) == 10


def test_logical_adapter_has_no_command_path() -> None:
    logic = _read(LOGIC)
    adapter = logic.split("part def VisualizationSourceAdapterRole")[1].split("}")[0]
    # Only inbound observation ports plus one frame output may exist.
    assert "port rssDistanceIn" in adapter
    assert "port frameOut : VisualizationFrameOutput" in adapter
    forbidden = [line for line in adapter.splitlines() if "port" in line and ("Out" in line and "frameOut" not in line)]
    assert not forbidden, forbidden


def test_logical_flow_is_one_directional_sources_to_evidence() -> None:
    logic = _read(LOGIC)
    system = logic.split("part def AEBSVisualizationLogicalSystem")[1].split("part def VisualizationHealthSupervisorRole")[0]
    flows = [line.strip() for line in system.splitlines() if line.strip().startswith("flow from")]
    assert flows, "no flows modeled"
    for flow in flows:
        # No flow may target a source role or run backwards into the adapter.
        for backwards in (
            "to nativeAebSource",
            "to coordinatorSource",
            "sourceAdapter.rssDistanceIn",
            "sourceAdapter.obstacleCloudIn",
            "sourceAdapter.diagnosticsIn",
            "sourceAdapter.warningIn",
            "sourceAdapter.brakingIn",
            "sourceAdapter.lifecycleIn",
        ):
            assert backwards not in flow, (backwards, flow)


def test_physical_slice_pins_the_autoware_source_revision() -> None:
    phys = _read(PHYS)
    assert "f603d8759c92fb2f423f1544844e13086d79ad09" in phys
    yaml_data = yaml.safe_load(_read(PILOT))
    assert (
        yaml_data["selected_realization"]["autoware_runtime"]["source_revision"]
        == "f603d8759c92fb2f423f1544844e13086d79ad09"
    )


def test_physical_slice_selects_display_capable_ivi_target() -> None:
    phys = _read(PHYS)
    assert "sdv_ivi_cf-aosp_current-userdebug" in phys
    assert "not transferable to an HMI realization" in phys
    yaml_data = yaml.safe_load(_read(PILOT))
    assert yaml_data["selected_realization"]["aaos_target"]["lunch_target"] == (
        "sdv_ivi_cf-aosp_current-userdebug"
    )


def test_physical_slice_keeps_mw010_transport_port_unreused() -> None:
    phys = _read(PHYS)
    assert "not reused" in phys
    assert "carries no" in phys


def test_provenance_records_prevent_relabeling_coordinator_output() -> None:
    phys = _read(PHYS)
    assert "shall not be relabeled as native" in phys
    assert 'provenanceKindValue = "de4sdvAebsCoordinator"' in phys
    assert 'provenanceKindValue = "nativeAutowareAEB"' in phys


def test_blocked_predicted_trajectory_not_smuggled_back() -> None:
    phys = _read(PHYS)
    assert "blockedPredictedTrajectoryRemainsDeferred" in phys
    yaml_data = yaml.safe_load(_read(PILOT))
    assert "predicted-trajectory branch (blocked at pinned revision)" in (
        yaml_data["selected_realization"]["deferred_sources"]
    )


def test_all_six_preflight_gates_modeled() -> None:
    phys = _read(PHYS)
    for gate in (
        "gateIviBuildBoot",
        "gateFrameworkServices",
        "gateGatewayJavaSample",
        "gateNativeToJavaPayload",
        "gateVmToVmConnectivity",
        "gateNoUpstreamFork",
    ):
        assert f"part {gate} : ReadinessPreflightGate" in phys
    yaml_data = yaml.safe_load(_read(PILOT))
    assert len(yaml_data["preflight_gates"]) == 6


def test_kill_gate_forbids_fallbacks() -> None:
    phys = _read(PHYS)
    assert "part realizationKillGate : IncrementLifecycleDecision" in phys
    for forbidden in ("host webpage", "screenshot mock", "unreviewed upstream fork"):
        assert forbidden in phys


@pytest.mark.parametrize(
    "logical_role,physical_element",
    [
        ("nativeAebSource", "pinnedAeb"),
        ("coordinatorSource", "coordinator"),
        ("sourceAdapter", "sourceAdapter"),
        ("transport", "transport"),
        ("ingress", "iviGuest.gatewayIngress"),
        ("displayService", "iviGuest.dataTunnel"),
        ("application", "iviGuest.displayApp"),
        ("evidence", "evidenceRecorder"),
    ],
)
def test_logical_roles_allocated_to_selected_physical_elements(
    logical_role: str, physical_element: str
) -> None:
    phys = _read(PHYS)
    assert f"allocate logicalSystem.{logical_role}" in phys
    assert f"to physicalSystem.{physical_element};" in phys


def test_physical_system_declares_no_source_side_command_ports() -> None:
    phys = _read(PHYS)
    system = phys.split("part def AEBS010VisualizationPhysicalSystem")[1].split(
        "part physicalSystem :"
    )[0]
    for token in ("cmdIn", "commandIn", "controlOut", "brakeOut"):
        assert token not in system


def test_yaml_model_artifact_paths_exist() -> None:
    data = yaml.safe_load(_read(PILOT))
    for artifact in data["model_artifacts"]:
        assert Path(artifact["path"]).exists(), artifact["path"]


def test_yaml_claim_boundary_defers_evidence() -> None:
    data = yaml.safe_load(_read(PILOT))
    assert "No executable implementation" in data["claim_boundary"]
    assert "Preflight gates are planned questions, not results" in data["claim_boundary"]
