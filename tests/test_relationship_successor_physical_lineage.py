"""Lexical endpoint lineage only; privileged validation/API readback remain pending."""
from pathlib import Path
import re

import pytest
from sysml_shapes import strip_comments

ROOT = Path(__file__).resolve().parents[1]
MODEL_DIR = ROOT / "textual-notation-of-model/packages/features/aebs"
PHYSICAL = MODEL_DIR / "aebs_physical_software_realization.sysml"
SIMULATION = MODEL_DIR / "aebs_simulation_deployment.sysml"
IMPORT = "private import DE4SDV_RelationshipSuccessor::PhysicalAllocationElement;"
ENDPOINTS = (
    (PHYSICAL, "VehicleTargetAEBSPhysicalSoftwareBoundary", "aebNode", "AutowareAutonomousEmergencyBrakingNode"),
    (SIMULATION, "AEBSystem1CandidateDeployment", "aeb", "DeployedAEBNode"),
    (SIMULATION, "AEBSystem1CandidateDeployment", "aggregator", "DiagnosticGraphAggregatorNode"),
    (SIMULATION, "AEBSystem1CandidateDeployment", "commandModeToOperationModeAvailabilityConverter", "CommandModeToOperationModeAvailabilityConverterNode"),
    (SIMULATION, "AEBSystem1CandidateDeployment", "mrmHandler", "MrmHandlerNode"),
    (SIMULATION, "AEBSystem1CandidateDeployment", "emergencyStopOperator", "EmergencyStopOperatorNode"),
    (SIMULATION, "AEBSystem1CandidateDeployment", "legacyVehicleCommandGate", "LegacyVehicleCommandGateNode"),
)


def declaration(code, kind, name):
    """Locate exactly one bounded header and its own body (if present)."""
    matches = list(re.finditer(rf"\b{re.escape(kind)}\s+{re.escape(name)}\b([^{{;]*)([{{;])", code))
    assert len(matches) == 1, (kind, name, "missing/ambiguous declaration")
    match = matches[0]
    if match[2] == ";":
        return match[1].strip(), ""
    depth = 1
    for index in range(match.end(), len(code)):
        depth += (code[index] == "{") - (code[index] == "}")
        if depth == 0:
            return match[1].strip(), code[match.end():index]
    raise AssertionError(f"unclosed {kind} {name}")


def direct_body(body):
    """Blank nested bodies, so descendants cannot satisfy an owner assertion."""
    depth = 0
    output = []
    for char in body:
        if char == "{":
            depth += 1
        output.append(char if depth == 0 else " ")
        if char == "}":
            depth -= 1
    assert depth == 0
    return "".join(output)


def assert_endpoint(code, owner, usage, definition):
    _, body = declaration(code, "part def", owner)
    assert re.search(rf"\bpart\s+{re.escape(usage)}\s*:\s*{re.escape(definition)}\s*;", direct_body(body))
    header, _ = declaration(code, "part def", definition)
    assert header == ":> PhysicalAllocationElement", (definition, header)
    assert IMPORT in code
    assert not re.search(r"\bpart\s+def\s+PhysicalAllocationElement\b", code)


@pytest.mark.parametrize("path,owner,usage,definition", ENDPOINTS, ids=[row[2] for row in ENDPOINTS])
def test_existing_allocation_endpoint_definition_has_exact_imported_lineage(path, owner, usage, definition):
    assert_endpoint(strip_comments(path.read_text(encoding="utf-8")), owner, usage, definition)


# Freeze the existing native population, including deliberately non-component
# item mappings. Endpoint typing must not create or silently upgrade a relation.
LOGICAL = "DE4SDV_AEBSLogicalArchitecture::system"
S1 = "deployment.candidateVehicleSystem1"
PHYSICAL_ALLOCATIONS = (
    ("stateAcquisitionPartial", "PartialLogicalToPhysicalSoftwareRealization", f"{LOGICAL}::stateAcquisition", "physicalSoftware.aebNode"),
    ("egoPathPredictionPartial", "PartialLogicalToPhysicalSoftwareRealization", f"{LOGICAL}::egoPathPrediction", "physicalSoftware.aebNode"),
    ("targetProcessingAvailable", "AvailableLogicalToPhysicalSoftwareRealization", f"{LOGICAL}::targetProcessing", "physicalSoftware.aebNode"),
    ("collisionRiskEvaluationAvailable", "AvailableLogicalToPhysicalSoftwareRealization", f"{LOGICAL}::collisionRiskEvaluation", "physicalSoftware.aebNode"),
    ("interventionDecisionPartial", "PartialLogicalToPhysicalSoftwareRealization", f"{LOGICAL}::interventionDecision", "physicalSoftware.aebNode"),
    ("healthSupervisionPartial", "PartialLogicalToPhysicalSoftwareRealization", f"{LOGICAL}::healthSupervision", "physicalSoftware.aebNode"),
    ("evidenceRecordingPartial", "PartialLogicalToPhysicalSoftwareRealization", f"{LOGICAL}::evidenceRecording", "physicalSoftware.aebNode"),
)
SIMULATION_COMPONENT_ALLOCATIONS = (
    ("stateAcquisitionToAEB", "SimulationLogicalToPhysicalRealization", f"{LOGICAL}.stateAcquisition", f"{S1}.aeb"),
    ("interventionDecisionToAEB", "SimulationLogicalToPhysicalRealization", f"{LOGICAL}.interventionDecision", f"{S1}.aeb"),
    ("emergencyCoordinationToAggregator", "SimulationLogicalToPhysicalRealization", f"{LOGICAL}.emergencyCoordination", f"{S1}.aggregator"),
    ("emergencyCoordinationToAvailabilityConverter", "SimulationLogicalToPhysicalRealization", f"{LOGICAL}.emergencyCoordination", f"{S1}.commandModeToOperationModeAvailabilityConverter"),
    ("emergencyCoordinationToMrmHandler", "SimulationLogicalToPhysicalRealization", f"{LOGICAL}.emergencyCoordination", f"{S1}.mrmHandler"),
    ("emergencyCoordinationToOperator", "SimulationLogicalToPhysicalRealization", f"{LOGICAL}.emergencyCoordination", f"{S1}.emergencyStopOperator"),
    ("emergencyCoordinationToLegacyVehicleGate", "SimulationLogicalToPhysicalRealization", f"{LOGICAL}.emergencyCoordination", f"{S1}.legacyVehicleCommandGate"),
)
SIMULATION_ITEM_ALLOCATIONS = (
    ("emergencyRequestToOperateMrm", "LogicalToPhysicalItemRealization", f"{LOGICAL}.emergencyInterventionRequestOut.emergencyInterventionRequest", f"{S1}.mrmHandler.operateMrmOut.request"),
    ("emergencyRequestToLegacyGateControl", "LogicalToPhysicalItemRealization", f"{LOGICAL}.emergencyInterventionRequestOut.emergencyInterventionRequest", f"{S1}.legacyVehicleCommandGate.emergencyControlCommandIn.command"),
    ("vehicleMotionToVelocityFeedback", "LogicalToPhysicalItemRealization", f"{LOGICAL}.vehicleMotionObservationIn.vehicleMotionState", f"{S1}.velocityFeedbackIn.velocity"),
    ("vehicleMotionToKinematicFeedback", "LogicalToPhysicalItemRealization", f"{LOGICAL}.vehicleMotionObservationIn.vehicleMotionState", f"{S1}.kinematicStateIn.odometry"),
)


def allocations(code):
    rows = re.findall(r"\ballocation\s+(\w+)\s*:\s*(\w+)\s+allocate\s+(\S+)\s+to\s+([^\s;]+)\s*;", code)
    assert len(rows) == len(re.findall(r"\ballocate\b", code)), "unrecognized allocation"
    return tuple(rows)


@pytest.mark.parametrize("path,expected", (
    (PHYSICAL, PHYSICAL_ALLOCATIONS),
    (SIMULATION, SIMULATION_COMPONENT_ALLOCATIONS + SIMULATION_ITEM_ALLOCATIONS),
), ids=("software-seven", "deployment-seven-plus-four-items"))
def test_exact_native_allocation_population_and_coverage_types_are_unchanged(path, expected):
    assert allocations(strip_comments(path.read_text(encoding="utf-8"))) == expected


@pytest.mark.parametrize("path", (PHYSICAL, SIMULATION), ids=("software", "deployment"))
def test_only_actual_component_endpoint_definitions_gain_physical_lineage(path):
    code = strip_comments(path.read_text(encoding="utf-8"))
    actual = re.findall(r"\bpart\s+def\s+(\w+)\s*:>\s*PhysicalAllocationElement\b", code)
    assert sorted(actual) == sorted(row[3] for row in ENDPOINTS if row[0] == path)
    assert code.count(IMPORT) == 1


def test_existing_root_usages_reach_the_actual_system1_endpoint_owners():
    code = strip_comments(SIMULATION.read_text(encoding="utf-8"))
    assert re.search(r"\bpart\s+deployment\s*:\s*AEBTwoSystemSimulationDeployment\s*;", code)
    _, deployment = declaration(code, "part def", "AEBTwoSystemSimulationDeployment")
    assert "part candidateVehicleSystem1 : AEBSystem1CandidateDeployment;" in direct_body(deployment)
    code = strip_comments(PHYSICAL.read_text(encoding="utf-8"))
    assert re.search(r"\bpart\s+physicalSoftware\s*:\s*VehicleTargetAEBSPhysicalSoftwareBoundary\s*;", code)


@pytest.mark.parametrize("usage,definition", (
    ("stateAcquisition", "StateAcquisitionAndNormalization"),
    ("egoPathPrediction", "EgoPathPrediction"),
    ("targetProcessing", "TargetProcessing"),
    ("collisionRiskEvaluation", "CollisionRiskEvaluation"),
    ("interventionDecision", "InterventionDecisionAndArbitration"),
    ("healthSupervision", "HealthAndDegradationSupervision"),
    ("evidenceRecording", "EvidenceRecording"),
    ("emergencyCoordination", "EmergencyInterventionCoordination"),
))
def test_existing_component_allocation_sources_retain_logical_lineage(usage, definition):
    code = strip_comments((MODEL_DIR / "aebs_logical_architecture.sysml").read_text(encoding="utf-8"))
    assert "private import DE4SDV_RelationshipSuccessor::*;" in code
    assert re.search(r"\bpart\s+system\s*:\s*VehicleTargetAEBSSystem\s*;", code)
    _, system = declaration(code, "part def", "VehicleTargetAEBSSystem")
    assert re.search(rf"\bpart\s+{usage}\s*:\s*{definition}\s*;", direct_body(system))
    header, _ = declaration(code, "part def", definition)
    assert header == ":> LogicalAllocationElement"


def test_missing_realization_and_blocked_contribution_records_are_preserved():
    code = strip_comments(PHYSICAL.read_text(encoding="utf-8"))
    expected = {
        "MissingPhysicalRealizationRecord": {"driverWarningRealizationGap", "healthCoverageGap", "evidenceCoverageGap"},
        "BlockedPhysicalRealizationBranchRecord": {"predictedTrajectoryBranchBlocked"},
        "PhysicalSourceContributionRecord": {"emergencyDiagnosticContribution"},
    }
    for definition, names in expected.items():
        assert set(re.findall(rf"\bpart\s+(\w+)\s*:\s*{definition}\b", code)) == names
    for name, source, reference, target in (
        ("driverWarningRealizationGap", "warningManagement", "requiredPhysicalRole", "requiredWarningProvider"),
        ("healthCoverageGap", "healthSupervision", "requiredPhysicalRole", "requiredHealthSupervisor"),
        ("evidenceCoverageGap", "evidenceRecording", "requiredPhysicalRole", "requiredEvidenceService"),
        ("predictedTrajectoryBranchBlocked", "egoPathPrediction", "physicalCandidate", "physicalSoftware.aebNode"),
    ):
        _, body = declaration(code, "part", name)
        assert f"ref part systemRole = {LOGICAL}::{source};" in direct_body(body)
        assert f"ref part {reference} = {target};" in direct_body(body)
    _, contribution = declaration(code, "part", "emergencyDiagnosticContribution")
    assert f"ref part conceptualConcern = {LOGICAL}::emergencyCoordination;" in direct_body(contribution)
    assert "ref part physicalSource = physicalSoftware.aebNode;" in direct_body(contribution)


@pytest.mark.parametrize("definition", (
    "AEBReadinessInputs", "ScenarioController", "PlannedAEBScenarioHarness",
    "PlannedAEBScenarioAssets", "SimplePlanningSimulatorTestDouble",
    "SimulationEvidenceCollector", "AEBSystem2SimulationAssets",
    "DeferredControlCommandGateAlternative",
))
def test_system2_and_deferred_alternatives_are_not_physical_successor_endpoints(definition):
    header, _ = declaration(strip_comments(SIMULATION.read_text(encoding="utf-8")), "part def", definition)
    assert header == ""


@pytest.mark.parametrize("definition", (
    "RequiredROS2ApplicationRuntimeBoundary", "RequiredDriverWarningProviderBoundary",
    "RequiredDiagnosticFailureBridgeBoundary", "RequiredEmergencyMRMHandlerBoundary",
    "RequiredVehicleCommandGateBoundary", "RequiredVehicleInterfaceBoundary",
    "RequiredBrakeECUAndActuatorBoundary", "RequiredHealthSupervisorBoundary",
    "RequiredEvidenceServiceBoundary",
))
def test_required_external_boundaries_are_not_promoted_to_implemented_lineage(definition):
    code = strip_comments(PHYSICAL.read_text(encoding="utf-8"))
    header, _ = declaration(code, "part def", definition)
    assert header == ""
    _, software = declaration(code, "part def", "VehicleTargetAEBSPhysicalSoftwareBoundary")
    assert not re.search(rf"\bpart\s+\w+\s*:\s*{definition}\b", direct_body(software))


@pytest.mark.parametrize("path", (PHYSICAL, SIMULATION), ids=("software", "deployment"))
def test_item_and_port_schemas_do_not_inherit_component_endpoint_lineage(path):
    code = strip_comments(path.read_text(encoding="utf-8"))
    forbidden = {row[3] for row in ENDPOINTS} | {"PhysicalAllocationElement", "PhysicalElement"}
    for kind, name in re.findall(r"\b(item|port)\s+def\s+(\w+)", code):
        header, _ = declaration(code, f"{kind} def", name)
        assert not set(re.findall(r"\w+", header)) & forbidden, (kind, name, header)
    for usage, definition in re.findall(r"\bitem\s+(\w+)\s*:\s*(\w+)", code):
        assert definition not in forbidden, (usage, definition)


def test_realized_system2_composite_does_not_instantiate_planned_scenario_assets():
    code = strip_comments(SIMULATION.read_text(encoding="utf-8"))
    _, body = declaration(code, "part def", "AEBSystem2SimulationAssets")
    assert re.findall(r"\bpart\s+(\w+)\s*:\s*(\w+)\s*;", direct_body(body)) == [
        ("readinessInputs", "AEBReadinessInputs"),
        ("simulator", "SimplePlanningSimulatorTestDouble"),
        ("evidenceCollector", "SimulationEvidenceCollector"),
    ]


@pytest.mark.parametrize("mutation", (
    "missing-import", "wrong-base", "comment-only-definition", "wrong-owner-usage",
    "nested-owner-usage", "semicolon-definition-borrows-body",
))
def test_lineage_guard_rejects_synthetic_false_closure(mutation):
    code = f"""{IMPORT}
    part def Node :> PhysicalAllocationElement {{ port retained; }}
    part def Owner {{ part endpoint : Node; }}
    """
    if mutation == "missing-import":
        code = code.replace(IMPORT, "")
    elif mutation == "wrong-base":
        code = code.replace(":> PhysicalAllocationElement", ":> Other")
    elif mutation == "comment-only-definition":
        code = code.replace("part def Node :> PhysicalAllocationElement { port retained; }", "/* part def Node :> PhysicalAllocationElement { port retained; } */")
    elif mutation == "wrong-owner-usage":
        code = code.replace("part def Owner", "part def Unrelated") + "part def Owner;"
    elif mutation == "nested-owner-usage":
        code = code.replace("part def Owner { part endpoint : Node; }", "part def Owner { part def Nested { part endpoint : Node; } }")
    elif mutation == "semicolon-definition-borrows-body":
        code = code.replace("part def Owner { part endpoint : Node; }", "part def Owner; part def Next { part endpoint : Node; }")
    with pytest.raises(AssertionError):
        assert_endpoint(strip_comments(code), "Owner", "endpoint", "Node")
