"""Content pins for the closed-loop driving physical/software realization (phase 8), not semantic validation.

INC-DRIVING-001 phase 8 places the six logical elements of phase 7 on software: three Eclipse S-CORE programs on
one Linux host, with the S-CORE SOME/IP gateway carrying the operational state to the AAOS SDV guests. Method
Check holds the DefinePhysicalRealization rule (each logical element allocated to a physical element; advisory,
each physical element carries one and each crossing has a signal mapping). These pins hold what the owner
settled on top of it (decisions of 2026-11-06):

- topology A: the loop is one FEO agent (a fixed-execution-order application of four activities, each a
  physical element: condition the inputs, infer the plan, supervise the loop, command the vehicle), beside an
  actuation adapter and a state publisher, each an S-CORE application; the two gateway processes carry the
  publication across the hypervisor;
- the planner is C++ on an exported form of the pinned AutoE2E checkpoint (an inference engine, not the
  training framework), its parity with the reference a gap until phase 10 measures it;
- S-CORE pinned at v0.10.0 (reference_integration ca2a5f03); FEO at v1.0.5 (313b3d84), outside that
  baseline, recorded as a gap; KUKSA stays unselected (ALT-MW-KUKSA-001);
- the simulator runs in asynchronous real-time mode; simulation time comes with each measurement and from the
  world snapshot at the actuation adapter, wall-clock time from the host;
- the operational state reaches AAOS SDV as a typed Data Tunnel topic over the proven gateway chain
  (decision 4); ego motion is typed by COVESA VSS, the commands by two DE4SDV VSS extension candidates
  (decision 5);
- the exchanges REQ-DRIVING-014 constrains cross processes only over S-CORE communication; inside the agent
  they are FEO topics, a reading recorded as a gap for the owner;
- one view per SAF question: the structure as a tree, the logical-to-physical mapping as a matrix, the
  S-CORE path as an interconnection of the software realization, the observation path as an interconnection
  of the physical system with its context, each framed by a concern of the Physical domain.
"""

from pathlib import Path
import re

import pytest

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
MODEL = DRIVING / "closed_loop_driving_physical_software_realization.sysml"
LOGICAL = DRIVING / "closed_loop_driving_logical_architecture.sysml"
FRAMING = DRIVING / "closed_loop_driving_framing.sysml"
EXTENSIONS = ROOT / "textual-notation-of-model/libraries/covesa-vss-sysmlv2/DE4SDV_VSS_Extensions.sysml"
GUIDE = ROOT / "docs/guides/closed-loop-driving-increment.md"
PACKAGE = "DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization"
LOGICAL_PACKAGE = "DE4SDV_ClosedLoopDrivingLogicalArchitecture"
LOGICAL_SYSTEM = "ClosedLoopDrivingLogicalSystem"
IDENTITY = "ClosedLoopDrivingSystem"
SYSTEM = "ClosedLoopDrivingPhysicalSystem"
SYSTEM_USAGE = "closedLoopDrivingPhysicalSystem"
HOST = "ClosedLoopDrivingLinuxHost"
REALIZATION = "ClosedLoopDrivingSoftwareRealization"
AGENT = "DrivingAgentApplication"
SOFTWARE = f"{SYSTEM_USAGE}::linuxHost::drivingSoftware"
#: the same software realization as a feature chain: a mapping's port target is written through the usage, since
#: the ports are declared on the definitions and a qualified name would resolve to the definition's port
SOFTWARE_CHAIN = f"{SYSTEM_USAGE}.linuxHost.drivingSoftware"

#: The physical element definitions, in the order of the loop -> (usage path below the software realization,
#: the logical element each carries).
ELEMENT_DEFINITIONS = {
    "InputConditioningActivity": ("drivingAgent::conditionInputs", "inputConditioner"),
    "PlanInferenceActivity": ("drivingAgent::inferPlan", "planner"),
    "LoopSupervisionActivity": ("drivingAgent::superviseLoop", "loopSupervisor"),
    "VehicleCommandActivity": ("drivingAgent::commandVehicle", "vehicleCommander"),
    "ActuationAdapterApplication": ("actuationAdapter", "actuationGateway"),
    "OperationalStatePublisherApplication": ("statePublisherApplication", "statePublisher"),
}
#: The two gateway processes: usages typed by the kernel class directly, as INC-MW-011 declares them.
GATEWAY_PROCESSES = ("gatewayd", "someipd")
LOGICAL_ELEMENTS = ("inputConditioner", "planner", "loopSupervisor", "vehicleCommander", "actuationGateway",
                    "statePublisher")
#: logical element -> the physical usage paths (below the software realization) it is allocated to
ALLOCATIONS = {
    "inputConditioner": ["drivingAgent::conditionInputs"],
    "planner": ["drivingAgent::inferPlan"],
    "loopSupervisor": ["drivingAgent::superviseLoop"],
    "vehicleCommander": ["drivingAgent::commandVehicle"],
    "actuationGateway": ["actuationAdapter"],
    "statePublisher": ["statePublisherApplication", "scoreServices::gatewayd", "scoreServices::someipd"],
}

#: Each element definition -> its ports.
PORTS = {
    "InputConditioningActivity": {"cameraImagesIn": "CameraStreamIn", "egoMotionIn": "EgoMotionStreamIn",
                                  "routeIn": "RouteIn", "checkpointInputsOut": "CheckpointInputsOut",
                                  "inputConditionOut": "InputConditionOut",
                                  "egoMotionSampleOut": "EgoMotionSampleOut"},
    "PlanInferenceActivity": {"checkpointInputsIn": "CheckpointInputsIn", "planOut": "DrivingPlanOut",
                              "planEventOut": "DrivingPlanOut"},
    "LoopSupervisionActivity": {"inputConditionIn": "InputConditionIn", "planIn": "DrivingPlanIn",
                                "validPlanOut": "DrivingPlanOut", "modeOut": "DrivingModeOut",
                                "modeEventOut": "DrivingModeOut"},
    "VehicleCommandActivity": {"validPlanIn": "DrivingPlanIn", "modeIn": "DrivingModeIn",
                               "egoMotionSampleIn": "EgoMotionSampleIn", "commandOut": "MotionCommandOut"},
    "ActuationAdapterApplication": {"commandIn": "MotionCommandIn", "simulationClockIn": "SimulationClockIn",
                                    "vehicleControlOut": "VehicleControlOut"},
    "OperationalStatePublisherApplication": {"planIn": "DrivingPlanIn", "modeIn": "DrivingModeIn",
                                             "egoMotionSampleIn": "EgoMotionSampleIn",
                                             "operationalStateOut": "OperationalStateOut"},
    AGENT: {"cameraImagesIn": "CameraStreamIn", "egoMotionIn": "EgoMotionStreamIn", "routeIn": "RouteIn",
            "egoMotionSampleOut": "EgoMotionSampleOut", "planEventOut": "DrivingPlanOut",
            "modeEventOut": "DrivingModeOut", "commandOut": "MotionCommandOut"},
    REALIZATION: {"cameraImagesIn": "CameraStreamIn", "egoMotionIn": "EgoMotionStreamIn", "routeIn": "RouteIn",
                  "simulationClockIn": "SimulationClockIn", "vehicleControlOut": "VehicleControlOut",
                  "operationalStateOut": "OperationalStateOut"},
    "CARLASimulationServer": {"cameraStreamOut": "CameraStreamOut", "egoMotionOut": "EgoMotionStreamOut",
                              "simulationClockOut": "SimulationClockOut", "vehicleControlIn": "VehicleControlIn"},
    "ScenarioRouteProvider": {"routeOut": "RouteOut"},
}
GATEWAY_PORTS = {"operationalStateIn": "OperationalStateIn", "operationalStateOut": "OperationalStateOut"}
#: port definition -> (direction, item, item type); one pair per item, whatever hop carries it
PORT_ITEMS = {
    "CameraStreamOut": ("out", "cameraImages", "CameraImages"),
    "CameraStreamIn": ("in", "cameraImages", "CameraImages"),
    "EgoMotionStreamOut": ("out", "egoMotion", "EgoMotionState"),
    "EgoMotionStreamIn": ("in", "egoMotion", "EgoMotionState"),
    "RouteOut": ("out", "route", "Route"),
    "RouteIn": ("in", "route", "Route"),
    "SimulationClockOut": ("out", "simulationClock", "SimulationClock"),
    "SimulationClockIn": ("in", "simulationClock", "SimulationClock"),
    "CheckpointInputsOut": ("out", "checkpointInputs", "CheckpointInputs"),
    "CheckpointInputsIn": ("in", "checkpointInputs", "CheckpointInputs"),
    "InputConditionOut": ("out", "inputCondition", "InputCondition"),
    "InputConditionIn": ("in", "inputCondition", "InputCondition"),
    "DrivingPlanOut": ("out", "plan", "DrivingPlan"),
    "DrivingPlanIn": ("in", "plan", "DrivingPlan"),
    "DrivingModeOut": ("out", "mode", "DrivingMode"),
    "DrivingModeIn": ("in", "mode", "DrivingMode"),
    "EgoMotionSampleOut": ("out", "egoMotionSample", "EgoMotionSamplePayload"),
    "EgoMotionSampleIn": ("in", "egoMotionSample", "EgoMotionSamplePayload"),
    "MotionCommandOut": ("out", "command", "VehicleMotionCommandPayload"),
    "MotionCommandIn": ("in", "command", "VehicleMotionCommandPayload"),
    "VehicleControlOut": ("out", "vehicleControl", "SimulatorVehicleControl"),
    "VehicleControlIn": ("in", "vehicleControl", "SimulatorVehicleControl"),
    "OperationalStateOut": ("out", "operationalState", "DrivingOperationalState"),
    "OperationalStateIn": ("in", "operationalState", "DrivingOperationalState"),
}
#: the payloads this phase types, each a realization of a phase 2 item -> (base item, VSS-typed attributes)
PAYLOADS = {
    "EgoMotionSamplePayload": ("EgoMotionState", {
        "speed": "Vehicle_Speed", "longitudinalAcceleration": "Vehicle_Acceleration_Longitudinal",
        "lateralAcceleration": "Vehicle_Acceleration_Lateral", "yawRate": "Vehicle_AngularVelocity_Yaw"}),
    "VehicleMotionCommandPayload": ("VehicleMotionCommand", {
        "acceleration": "Vehicle_ADAS_Driving_Command_Acceleration",
        "steeringAngle": "Vehicle_ADAS_Driving_Command_SteeringAngle"}),
}
#: the DE4SDV VSS extension candidates this phase adds (local; proposing them upstream needs the owner's word)
EXTENSIONS_ADDED = {
    "Vehicle_ADAS_Driving_Command_Acceleration": ("Vehicle.ADAS.Driving.Command.Acceleration",
                                                   "SI::metrePerSecondSquared"),
    "Vehicle_ADAS_Driving_Command_SteeringAngle": ("Vehicle.ADAS.Driving.Command.SteeringAngle", "SI::degree"),
}

#: The connections of the agent: boundary delegations, then the FEO topics in the order of the loop.
AGENT_CONNECTIONS = {
    ("cameraImagesIn", "conditionInputs.cameraImagesIn"),
    ("egoMotionIn", "conditionInputs.egoMotionIn"),
    ("routeIn", "conditionInputs.routeIn"),
    ("conditionInputs.egoMotionSampleOut", "egoMotionSampleOut"),
    ("inferPlan.planEventOut", "planEventOut"),
    ("superviseLoop.modeEventOut", "modeEventOut"),
    ("commandVehicle.commandOut", "commandOut"),
    ("conditionInputs.checkpointInputsOut", "inferPlan.checkpointInputsIn"),
    ("conditionInputs.inputConditionOut", "superviseLoop.inputConditionIn"),
    ("conditionInputs.egoMotionSampleOut", "commandVehicle.egoMotionSampleIn"),
    ("inferPlan.planOut", "superviseLoop.planIn"),
    ("superviseLoop.validPlanOut", "commandVehicle.validPlanIn"),
    ("superviseLoop.modeOut", "commandVehicle.modeIn"),
}
#: The connections of the software realization: boundary delegations, then the hops between processes.
REALIZATION_CONNECTIONS = {
    ("cameraImagesIn", "drivingAgent.cameraImagesIn"),
    ("egoMotionIn", "drivingAgent.egoMotionIn"),
    ("routeIn", "drivingAgent.routeIn"),
    ("simulationClockIn", "actuationAdapter.simulationClockIn"),
    ("actuationAdapter.vehicleControlOut", "vehicleControlOut"),
    ("scoreServices.someipd.operationalStateOut", "operationalStateOut"),
    ("drivingAgent.commandOut", "actuationAdapter.commandIn"),
    ("drivingAgent.planEventOut", "statePublisherApplication.planIn"),
    ("drivingAgent.modeEventOut", "statePublisherApplication.modeIn"),
    ("drivingAgent.egoMotionSampleOut", "statePublisherApplication.egoMotionSampleIn"),
    ("statePublisherApplication.operationalStateOut", "scoreServices.gatewayd.operationalStateIn"),
    ("scoreServices.gatewayd.operationalStateOut", "scoreServices.someipd.operationalStateIn"),
}
#: The hops over S-CORE communication (mw::com), named so in the connection: the ones REQ-DRIVING-014
#: constrains between processes, and the observation hops beside them.
SCORE_COMMUNICATION_HOPS = {
    "commandOverSCORECommunication": ("drivingAgent.commandOut", "actuationAdapter.commandIn"),
    "planEventOverSCORECommunication": ("drivingAgent.planEventOut", "statePublisherApplication.planIn"),
    "modeEventOverSCORECommunication": ("drivingAgent.modeEventOut", "statePublisherApplication.modeIn"),
    "egoMotionSampleOverSCORECommunication": ("drivingAgent.egoMotionSampleOut",
                                              "statePublisherApplication.egoMotionSampleIn"),
    "operationalStateOverSCORECommunication": ("statePublisherApplication.operationalStateOut",
                                               "scoreServices.gatewayd.operationalStateIn"),
}
#: host flow -> (item, source, target): each exchange with the context realizations is a flow of its item, so the
#: context exchange view labels what crosses; into the simulator goes the vehicle control and nothing else
#: the item is the end ports' (typed), so the flow declares none (the MW-008 adapter boundary form, which renders)
HOST_FLOWS = {
    "cameraStreamOverHostLoopback": ("", "carlaServer.cameraStreamOut.cameraImages",
                                     "drivingSoftware.cameraImagesIn.cameraImages"),
    "egoMotionOverHostLoopback": ("", "carlaServer.egoMotionOut.egoMotion", "drivingSoftware.egoMotionIn.egoMotion"),
    "simulationClockOverHostLoopback": ("", "carlaServer.simulationClockOut.simulationClock",
                                        "drivingSoftware.simulationClockIn.simulationClock"),
    "routeFromScenario": ("", "routeProvider.routeOut.route", "drivingSoftware.routeIn.route"),
    "vehicleControlOverHostLoopback": ("", "drivingSoftware.vehicleControlOut.vehicleControl",
                                       "carlaServer.vehicleControlIn.vehicleControl"),
}
#: the delegation to the host's own port stays a connection: a flow into an out item fails direction conformance
HOST_CONNECTIONS = [("drivingSoftware.operationalStateOut", "operationalStateOut")]
#: the two hops are unnamed flows (the AEBS deployment's form); the Data Tunnel's port item is untyped, so that
#: flow declares the payload
SYSTEM_FLOWS = [
    ("", "linuxHost.operationalStateOut.operationalState", "sdvCoreGuest.someIpIn.operationalState"),
    ("DrivingOperationalState", "sdvCoreGuest.topicOut.topicData", "hmiGuest.topicIn.topicData"),
]
SDV_CORE_GUEST_CONNECTIONS = {
    ("someIpIn", "sdvCore.someIp.someIpPort"),
    ("sdvCore.someIp.topicPublishOut", "sdvCore.dataTunnel.topicPublishPort"),
    ("sdvCore.dataTunnel.topicSubscribePort", "topicOut"),
}
HMI_GUEST_CONNECTIONS = {
    ("topicIn", "sdvGateway.dataTunnelPort"),
    ("sdvGateway.clientPort", "stateObserver.operationalStateIn"),
}

#: signal mapping -> (logical element, target port path below the software realization, record short name)
SIGNAL_MAPPINGS = {
    "cameraImagesIngressMapping": ("inputConditioner", "drivingAgent::conditionInputs::cameraImagesIn",
                                   "MAP-DRIVING-CAMERA-IMAGES"),
    "egoMotionSampleMapping": ("inputConditioner", "drivingAgent::conditionInputs::egoMotionSampleOut",
                               "MAP-DRIVING-EGO-MOTION"),
    "routeIngressMapping": ("inputConditioner", "drivingAgent::conditionInputs::routeIn", "MAP-DRIVING-ROUTE"),
    "planMapping": ("planner", "drivingAgent::inferPlan::planEventOut", "MAP-DRIVING-PLAN"),
    "modeMapping": ("loopSupervisor", "drivingAgent::superviseLoop::modeEventOut", "MAP-DRIVING-MODE"),
    "commandMapping": ("vehicleCommander", "drivingAgent::commandVehicle::commandOut", "MAP-DRIVING-COMMAND"),
    "vehicleControlMapping": ("actuationGateway", "actuationAdapter::vehicleControlOut",
                              "MAP-DRIVING-VEHICLE-CONTROL"),
    "operationalStateMapping": ("statePublisher", "scoreServices::someipd::operationalStateOut",
                                "MAP-DRIVING-OPERATIONAL-STATE"),
}
RECORD_ATTRIBUTES = ("semanticSource", "softwareContractArtifact", "softwareContractMessage",
                     "softwareContractField", "dataTypeAndUnit", "timingQualityAndState", "transformationRule",
                     "disposition", "owner", "nextAction", "evidenceOrGap")

ASSUMPTIONS = {
    "ASM-DRIVING-001": "asmFixedOrderCycleCarriesTheLoop",
    "ASM-DRIVING-002": "asmExportedModelStandsForTheCheckpoint",
    "ASM-DRIVING-003": "asmSimulatorClientsInsideSCOREApplications",
}
GAPS = {
    "GAP-DRIVING-001": "gapFEOOutsideReleasedBaseline",
    "GAP-DRIVING-002": "gapSOMEIPGatewayAgainstCommunication060",
    "GAP-DRIVING-003": "gapModelExportAndParityUnproven",
    "GAP-DRIVING-004": "gapSimulatorClientBuildUnproven",
    "GAP-DRIVING-005": "gapActuationStopUnobservable",
    "GAP-DRIVING-006": "gapTypedOperationalStateTopicUnproven",
    "GAP-DRIVING-007": "gapGPUAndKVMHostUnprovisioned",
}
#: what each gap must name
GAP_MENTIONS = {
    "GAP-DRIVING-001": ("v1.0.5", "313b3d84", "known_good"),
    "GAP-DRIVING-002": ("d9eac670", "0.6.0"),
    "GAP-DRIVING-003": ("ONNX", "parity", "REQ-DRIVING-035"),
    "GAP-DRIVING-004": ("libcarla", "12.2"),
    "GAP-DRIVING-005": ("REQ-DRIVING-028", "REQ-DRIVING-029", "publishState", "2026-11-06", "follow-up"),
    "GAP-DRIVING-006": ("VSIDL", "GAP-MW-038"),
    "GAP-DRIVING-007": ("GPU", "KVM", "gapBoundedCloudCampaign"),
}
PINS = ("313b3d849c17881d3a11b6bf62aa2afab6565ef0", "ca2a5f03724780be3cebf3d80e0c9c0c6fa64eb2",
        "d9eac670b7534352749da3d30f52aebf5129f168", "cb50764b8250a3c44ee5b79b87ba02c5a83b0c91", "v0.10.0",
        "v1.0.5", "0.6.0", "ALT-MW-KUKSA-001")
ALTERNATIVES = ("ALT-DRIVING-PLAINAPPS-001", "ALT-DRIVING-SIMBRIDGE-001", "ALT-DRIVING-LIBTORCH-001",
                "ALT-DRIVING-FEOMWCOM-001")

STRUCTURE_VIEW = "closedLoopDrivingPhysicalStructureView"
MATRIX_VIEW = "closedLoopDrivingPhysicalLogicalMappingView"
PATH_VIEW = "closedLoopDrivingSCOREPathExchangeView"
CONTEXT_VIEW = "closedLoopDrivingPhysicalContextExchangeView"
TREE_EXPOSES = [SYSTEM_USAGE] + [f"{SYSTEM_USAGE}::{path}" for path in (
    "linuxHost", "linuxHost::os", "linuxHost::hypervisor", "linuxHost::drivingSoftware",
    "linuxHost::drivingSoftware::drivingAgent", "linuxHost::drivingSoftware::drivingAgent::conditionInputs",
    "linuxHost::drivingSoftware::drivingAgent::inferPlan", "linuxHost::drivingSoftware::drivingAgent::superviseLoop",
    "linuxHost::drivingSoftware::drivingAgent::commandVehicle", "linuxHost::drivingSoftware::actuationAdapter",
    "linuxHost::drivingSoftware::statePublisherApplication", "linuxHost::drivingSoftware::scoreServices",
    "linuxHost::drivingSoftware::scoreServices::launchManager", "linuxHost::drivingSoftware::scoreServices::gatewayd",
    "linuxHost::drivingSoftware::scoreServices::someipd", "linuxHost::carlaServer", "linuxHost::routeProvider",
    "sdvCoreGuest", "sdvCoreGuest::os", "sdvCoreGuest::sdvMiddleware", "sdvCoreGuest::sdvCore", "hmiGuest",
    "hmiGuest::os", "hmiGuest::sdvGateway",
    "hmiGuest::stateObserver")]
#: view -> (type or None, render, exposes in order, viewpoint type, framed concerns in order)
VIEWS = {
    STRUCTURE_VIEW: (None, "render asTreeDiagram;", TREE_EXPOSES, "PhysicalStructureDefinitionViewpoint",
                     ["closedLoopDrivingPhysicalStructureConcern"]),
    MATRIX_VIEW: ("MVD::MatrixView", None,
                  [f"{LOGICAL_SYSTEM}::{element}" for element in LOGICAL_ELEMENTS]
                  + [f"{SOFTWARE}::{path}" for path, _ in ELEMENT_DEFINITIONS.values()]
                  + [f"{SOFTWARE}::scoreServices::{process}" for process in GATEWAY_PROCESSES] + [f"{PACKAGE}::*"],
                  "PhysicalLogicalMappingViewpoint", ["closedLoopDrivingPhysicalAllocationConcern"]),
    PATH_VIEW: (None, "render asInterconnectionDiagram;", ["closedLoopDrivingSoftware", "closedLoopDrivingSoftware::**"],
                "PhysicalInternalExchangeViewpoint", ["scoreCommandPathConcern", "checkpointCommandAuthorityConcern"]),
    CONTEXT_VIEW: (None, "render asInterconnectionDiagram;",
                   [SYSTEM_USAGE] + [f"{SYSTEM_USAGE}::{member}" for member in (
                       "linuxHost", "linuxHost::*[istype SysML::PortUsage]",
                       "linuxHost::drivingSoftware", "linuxHost::drivingSoftware::*[istype SysML::PortUsage]",
                       "linuxHost::carlaServer", "linuxHost::carlaServer::*[istype SysML::PortUsage]",
                       "linuxHost::routeProvider", "linuxHost::routeProvider::*[istype SysML::PortUsage]",
                       "linuxHost::*[istype SysML::FlowUsage]",
                       "sdvCoreGuest", "sdvCoreGuest::*[istype SysML::PortUsage]",
                       "hmiGuest", "hmiGuest::*[istype SysML::PortUsage]",
                       "*[istype SysML::FlowUsage]")],
                   "PhysicalContextExchangeViewpoint",
                   ["aaosObservationFidelityConcern", "checkpointCommandAuthorityConcern"]),
}
#: the concerns this phase declares -> (catalogue type, the parties that hold it)
CATALOGUE_CONCERNS = {
    "closedLoopDrivingPhysicalStructureConcern": ("PhysicalStructureConcern", {"SystemArchitect", "SoftwareDeveloper"}),
    "closedLoopDrivingPhysicalAllocationConcern": ("PhysicalLogicalMappingConcern",
                                                   {"SystemArchitect", "VerificationEngineer", "OpenSourceReviewer"}),
}
#: the phase 1 concerns of the Physical domain this phase frames, imported from the framing
FRAMING_CONCERNS = ("scoreCommandPathConcern", "checkpointCommandAuthorityConcern", "aaosObservationFidelityConcern")
#: context realizations and platform parts carry no kernel typing: the advisory would name them
NOT_ELEMENTS = ("CARLASimulationServer", "ScenarioRouteProvider", "AAOSSDVCoreGuest", "AAOSIVIGuest", HOST, SYSTEM,
                REALIZATION, AGENT)
CLAIM_WORDS = ("certif", "homolog", "complian", "production-ready", "production ready", "guarantee", "proves that",
               "proven on")


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(line.strip().lstrip("*").strip() for line in text.splitlines()).strip()


def _doc(declaration: str, source: str | None = None) -> str:
    body = braced_body(source if source is not None else _raw(), declaration)
    match = re.match(r"\s*doc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{declaration}: the doc must open the body"
    return _flat(match.group(1))


def _direct(body: str) -> str:
    """Blank nested bodies, keeping their braces, so only direct members remain visible."""
    out, depth = [], 0
    for char in body:
        if char == "}":
            depth -= 1
        out.append(char if depth == 0 else " ")
        if char == "{":
            depth += 1
    assert depth == 0, "unbalanced body"
    return "".join(out)


def _connections(body: str) -> list[tuple[str, str]]:
    return re.findall(r"\bconnection\s+\w+\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*;", body)


def _flows(body: str) -> dict[str, tuple[str, str, str]]:
    """name -> (declared item or '', source, target) of every named flow, with or without an `of <Item>` payload."""
    return {name: (item, source, target) for name, item, source, target in re.findall(
        r"\bflow\s+(\w+)\s+(?:of\s+(\w+)\s+)?from\s+([\w.]+)\s+to\s+([\w.]+)\s*;", body)}


def _unnamed_flows(body: str) -> list[tuple[str, str, str]]:
    """(declared item or '', source, target) of every unnamed flow (the AEBS deployment's rendering form)."""
    return re.findall(r"\bflow\s+(?:of\s+(\w+)\s+)?from\s+([\w.]+)\s+to\s+([\w.]+)\s*[;{]", body)


def _allocations() -> list[tuple[str, str, str, str, str]]:
    """(name, definition or '', source, target, body or '') of every allocation usage."""
    code = re.sub(r'"(?:[^"\\]|\\.)*"', '""', _code())
    rows = []
    for match in re.finditer(r"\ballocation\s+(\w+)(?:\s*:\s*(\w+))?\s+allocate\s+(\S+)\s+to\s+([^\s;{]+)\s*([;{])",
                             code):
        body = braced_body(code, match.group(0)[:-1].rstrip()) if match.group(5) == "{" else ""
        rows.append((match.group(1), match.group(2) or "", match.group(3), match.group(4), body))
    assert len(rows) == len(re.findall(r"\ballocate\b", code)), "unrecognized allocation form"
    return rows


def _body_of_definition(name: str) -> str:
    return braced_body(_code(), f"part def {name}")


def test_the_charter_names_the_package_after_the_logical_architecture():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part closedLoopDrivingCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    assert names.index(PACKAGE) == names.index(LOGICAL_PACKAGE) + 1 == len(names) - 1
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", _code())


def test_the_six_definitions_and_the_two_gateway_processes_are_the_physical_elements_and_nothing_else_is():
    code = _code()
    declared = re.findall(r"\bpart\s+def\s+(\w+)\s*:>\s*PhysicalAllocationElement\s*\{", code)
    assert sorted(declared) == sorted(ELEMENT_DEFINITIONS)
    assert len(declared) == 6
    typed = re.findall(r"\bpart\s+(\w+)\s*:\s*PhysicalAllocationElement\s*\{", code)
    assert typed == list(GATEWAY_PROCESSES)
    assert len(re.findall(r"\bPhysicalAllocationElement\b", code)) == 1 + len(declared) + len(typed)
    assert "private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;" in code
    assert not re.search(r"\b(LogicalAllocationElement|AllocatableFunction)\b", code), "one layer meaning per file"
    for definition in ELEMENT_DEFINITIONS:
        assert "Carries" in _doc(f"part def {definition} :> PhysicalAllocationElement"), definition
    for name in NOT_ELEMENTS:
        header = re.search(rf"\bpart\s+def\s+{name}\b([^{{]*)\{{", code)
        assert header and "PhysicalAllocationElement" not in header.group(1), name


def test_the_software_realization_is_the_system_of_interest_and_owns_the_three_programs():
    code = _code()
    assert re.search(rf"\bpart\s+def\s+{REALIZATION}\s*:>\s*{IDENTITY}\s*\{{", code)
    assert f"private import DE4SDV_ClosedLoopDrivingFraming::{IDENTITY};" in code
    body = braced_body(code, f"part def {REALIZATION} :> {IDENTITY}")
    owned = re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M)
    assert owned == [("drivingAgent", AGENT), ("actuationAdapter", "ActuationAdapterApplication"),
                     ("statePublisherApplication", "OperationalStatePublisherApplication")]
    assert re.search(r"^\s*part\s+scoreServices\s*:\s*EclipseSCORE\s*\{", body, re.M), "owned with the programs, one instance"
    assert "ref part" not in body and "bind" not in body, "a reference bound to a host part drew no processes (run 42212398480)"
    services = braced_body(body, "part scoreServices : EclipseSCORE")
    assert re.findall(r"^\s*part\s+(\w+)", services, re.M) == ["launchManager", *GATEWAY_PROCESSES]
    for process in GATEWAY_PROCESSES:
        assert dict(re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", braced_body(services, f"part {process} : PhysicalAllocationElement"))) == GATEWAY_PORTS
    assert not re.search(r"\blaunchManager\s*:", services), "the launch manager carries no logical element"
    assert "the same system as the context's drivingSystem" in _doc(f"part def {REALIZATION} :> {IDENTITY}")
    # no second specialization of the phase 7 system: realization by allocation, as INC-MW-011 does
    assert not re.search(rf":>\s*{LOGICAL_SYSTEM}\b", code)
    assert not re.search(r"\bpart\s+\w+\s*:\s*ClosedLoopDrivingLogicalSystem\b", code)


def test_the_agent_runs_the_four_activities_in_the_order_of_the_loop():
    body = _body_of_definition(AGENT)
    owned = re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M)
    assert owned == [("conditionInputs", "InputConditioningActivity"), ("inferPlan", "PlanInferenceActivity"),
                     ("superviseLoop", "LoopSupervisionActivity"), ("commandVehicle", "VehicleCommandActivity")]
    doc = _doc(f"part def {AGENT}")
    for word in ("FEO", "fixed", "activit", "one Linux process", "v1.0.5"):
        assert word in doc, word
    connections = _connections(body)
    assert set(connections) == AGENT_CONNECTIONS and len(connections) == len(AGENT_CONNECTIONS)
    assert not re.search(r"\bflow\b", body)
    for source, target in connections:
        for end in (source, target):
            if "." in end:
                part, port = end.split(".")
                assert port in PORTS[dict(owned)[part]], end
            else:
                assert end in PORTS[AGENT], end


@pytest.mark.parametrize("definition", sorted(PORTS), ids=sorted(PORTS))
def test_each_definition_declares_exactly_its_ports(definition):
    header = f"part def {definition}"
    body = braced_body(_code(), header)
    assert dict(re.findall(r"^\s*port\s+(\w+)\s*:\s*(\w+)\s*;", _direct(body), re.M)) == PORTS[definition]
    if definition in ELEMENT_DEFINITIONS:
        assert not re.search(r"\b(part|action|perform|flow|state)\b", body), "an element carries by allocation only"


def test_the_port_definitions_carry_one_item_each_in_one_direction():
    code = _code()
    declared = re.findall(r"\bport\s+def\s+(\w+)\s*\{", code)
    assert sorted(declared) == sorted(PORT_ITEMS)
    for port_def, (direction, item, item_type) in PORT_ITEMS.items():
        body = braced_body(code, f"port def {port_def}")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [(direction, item, item_type)], port_def
    for item in ("CameraImages", "EgoMotionState", "Route", "VehicleMotionCommand", "DrivingOperationalState",
                 "NavigationSystem", "DrivingStateObserverApplication"):
        assert f"private import DE4SDV_ClosedLoopDrivingOperationalContext::{item};" in code, item
    for item in ("CheckpointInputs", "InputCondition", "DrivingPlan", "DrivingMode"):
        assert f"private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::{item};" in code, item
    assert re.findall(r"\bitem\s+def\s+(\w+)", code) == ["SimulationClock", *PAYLOADS, "SimulatorVehicleControl"]


def test_the_simulator_receives_the_three_control_fields_the_adapter_sets_and_nothing_else():
    body = braced_body(_code(), "item def SimulatorVehicleControl")
    assert re.findall(r"\battribute\s+(\w+)\s*:\s*(\w+)\s*;", body) == [("throttle", "Real"), ("steer", "Real"),
                                                                            ("brake", "Real")]
    doc = _doc("item def SimulatorVehicleControl")
    for phrase in ("the only thing", "VehicleControl", "[0, 1]", "[-1, 1]", "API reference", "pinned in phase 10",
                   "REQ-DRIVING-012", "Hand brake, reverse, manual gear shift and gear stay at their defaults"):
        assert phrase in doc, phrase


@pytest.mark.parametrize("payload", sorted(PAYLOADS), ids=sorted(PAYLOADS))
def test_the_payloads_realize_phase_2_items_and_type_vehicle_signals_with_vss(payload):
    base, attributes = PAYLOADS[payload]
    code = _code()
    body = braced_body(code, f"item def {payload} :> {base}")
    typed = dict(re.findall(r"\battribute\s+(\w+)\s*:\s*(\w+)\s*;", body))
    for name, signal in attributes.items():
        assert typed[name] == signal, (payload, name)
    assert not re.search(r"\bflow\b|\bpart\b", body)
    for signal in attributes.values():
        library = "DE4SDV_VSS_Extensions" if signal in EXTENSIONS_ADDED else "COVESA_VSS::SignalDefinitions"
        assert f"private import {library}::{signal};" in code, signal


def test_the_extension_candidates_are_declared_with_their_metadata_and_stay_local():
    source = EXTENSIONS.read_text(encoding="utf-8")
    for signal, (path, unit) in EXTENSIONS_ADDED.items():
        assert f"attribute def {signal} :> Real;" in source, signal
        metadata = braced_body(source, f"@VssSignalMetadata about {signal}")
        assert f'path = "{path}";' in metadata
        assert 'kind = "actuator";' in metadata
        assert 'datatype = "float";' in metadata
        assert "INC-DRIVING-001" in metadata and "not present in the generated COVESA VSS snapshot" in metadata
        quantity = braced_body(source, f"@VssQuantityMetadata about {signal}")
        assert f'unitReference = "{unit}";' in quantity
    assert "not proposed upstream" in source or "needs the owner" in source


def test_the_realization_connects_the_programs_over_score_communication_and_delegates_its_boundary():
    body = braced_body(_code(), f"part def {REALIZATION} :> {IDENTITY}")
    connections = _connections(body)
    assert set(connections) == REALIZATION_CONNECTIONS and len(connections) == len(REALIZATION_CONNECTIONS)
    named = dict(re.findall(r"\bconnection\s+(\w+)\s+connect\s+([\w.]+\s+to\s+[\w.]+)\s*;", body))
    for name, (source, target) in SCORE_COMMUNICATION_HOPS.items():
        assert named[name] == f"{source} to {target}", name
    assert "bind" not in body, "the host binds its S-CORE services to the reference"
    # nothing runs from the actuation adapter or the publisher back into the agent (phase 7's one-way rule)
    for source, target in connections:
        if source.startswith(("actuationAdapter.", "statePublisherApplication.", "scoreServices.")):
            assert not target.startswith("drivingAgent."), (source, target)


def test_the_host_owns_the_platform_the_software_and_the_context_realizations():
    code = _code()
    body = _body_of_definition(HOST)
    owned = re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M)
    assert owned == [("os", "LinuxPlatform"), ("hypervisor", "KVMHypervisor"), ("drivingSoftware", REALIZATION),
                     ("carlaServer", "CARLASimulationServer"), ("routeProvider", "ScenarioRouteProvider")]
    assert "bind" not in body and "scoreServices" not in body, "the realization owns the S-CORE services"
    assert _connections(body) == HOST_CONNECTIONS, "the exchanges are flows of their items; the delegation a connection"
    assert _flows(body) == HOST_FLOWS
    assert len(re.findall(r"\bflow\b", body)) == len(HOST_FLOWS)
    into_simulator = [name for name, (_, _, target) in HOST_FLOWS.items() if target.startswith("carlaServer.")]
    assert into_simulator == ["vehicleControlOverHostLoopback"], "the vehicle control is the only thing the simulator receives"
    assert dict(re.findall(r"^\s*port\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M)) == {"operationalStateOut": "OperationalStateOut"}
    for layer in ("LinuxPlatform", "KVMHypervisor", "EclipseSCORE", "AndroidHLOS", "AndroidSDVMiddleware",
                  "OSHypervisorInterface"):
        assert f"private import DE4SDV_SDVPlatformStack::{layer};" in code, layer
    # the navigation of phase 2 is realized on the host, not on the AAOS guest: the context-role decision holds
    assert re.search(r"\bpart\s+def\s+ScenarioRouteProvider\s*:>\s*NavigationSystem\s*\{", code)
    route_doc = _doc("part def ScenarioRouteProvider :> NavigationSystem")
    assert "System 2" in route_doc and "2026-11-02" in route_doc
    carla_doc = _doc("part def CARLASimulationServer")
    assert "System 2" in carla_doc and "asynchronous" in carla_doc


def test_the_guests_carry_the_observation_path_and_the_system_crosses_the_hypervisor_twice():
    code = _code()
    core = _body_of_definition("AAOSSDVCoreGuest")
    assert re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", core, re.M) == [("os", "AndroidHLOS"),
                                                                        ("sdvMiddleware", "AndroidSDVMiddleware")]
    # the SDV Core boundary model is referenced, never owned: the platform stack owns the guest (2026-10-25)
    assert re.search(r"^\s*ref\s+part\s+sdvCore\s*:\s*SDVCoreBoundary\s*;", core, re.M)
    assert "bind sdvCore = sdvMiddleware;" in core
    assert set(_connections(core)) == SDV_CORE_GUEST_CONNECTIONS
    assert dict(re.findall(r"^\s*port\s+(\w+)\s*:\s*(\w+)\s*;", core, re.M)) == {"someIpIn": "OperationalStateIn",
                                                                                 "topicOut": "DataTunnelPort"}
    hmi = _body_of_definition("AAOSIVIGuest")
    assert re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*[;{]", hmi, re.M) == [
        ("os", "AndroidHLOS"), ("sdvGateway", "SDVGatewayOnIVIBoundary"), ("stateObserver", "DrivingStateObserverApplication")]
    assert set(_connections(hmi)) == HMI_GUEST_CONNECTIONS
    observer = braced_body(hmi, "part stateObserver : DrivingStateObserverApplication")
    assert dict(re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", observer)) == {"operationalStateIn": "OperationalStateIn"}
    # what the observer presents (owner decision 2026-11-06): the operational state only, under two clocks
    observer_doc = _doc("part stateObserver : DrivingStateObserverApplication", braced_body(_raw(), "part def AAOSIVIGuest"))
    for phrase in ("2026-11-06", "the run record it names", "the cause of a stop", "the run identity",
                   "No camera images, no commands, no route; nothing back", "two clocks side by side",
                   "simulation time of the newest input", "wall-clock time of the publication", "phase 10 evidence"):
        assert phrase in observer_doc, phrase
    system = _body_of_definition(SYSTEM)
    assert re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", system, re.M) == [
        ("linuxHost", HOST), ("sdvCoreGuest", "AAOSSDVCoreGuest"), ("hmiGuest", "AAOSIVIGuest")]
    assert _connections(system) == [] and _flows(system) == {} and _unnamed_flows(system) == SYSTEM_FLOWS
    interfaces = re.findall(r"\binterface\s+(\w+)\s*:\s*OSHypervisorInterface\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*;", system)
    assert interfaces == [("sdvCoreGuestUnderKVM", "sdvCoreGuest.os.hypervisorPort", "linuxHost.hypervisor.guestPort"),
                          ("hmiGuestUnderKVM", "hmiGuest.os.hypervisorPort", "linuxHost.hypervisor.guestPort")]
    for name in ("SDVCoreBoundary", "SDVGatewayOnIVIBoundary", "DataTunnelPort"):
        assert f"private import DE4SDV_AAOSSDVMiddlewareBoundary::{name};" in code, name
    assert re.findall(rf"^\s*part\s+(\w+)\s*:\s*{SYSTEM}\s*[{{;=]", code, re.M) == [SYSTEM_USAGE]
    # the path view draws usages: one package-level usage of the realization exists for it (phase 7's form)
    assert re.findall(rf"^  part\s+(\w+)\s*:\s*{REALIZATION}\s*[{{;=]", code, re.M) == ["closedLoopDrivingSoftware"]
    assert "the same" in _doc(f"part closedLoopDrivingSoftware : {REALIZATION}")


def test_each_logical_element_is_allocated_to_its_software_and_each_element_carries_one():
    rows = [(name, source, target) for name, kind, source, target, _ in _allocations() if not kind]
    assert len(rows) == 8
    expected = {(f"{LOGICAL_SYSTEM}::{logical}", f"{SOFTWARE}::{path}")
                for logical, paths in ALLOCATIONS.items() for path in paths}
    assert {(source, target) for _, source, target in rows} == expected
    assert {source for _, source, _ in rows} == {f"{LOGICAL_SYSTEM}::{logical}" for logical in LOGICAL_ELEMENTS}
    targets = {target for _, _, target in rows}
    assert targets == {f"{SOFTWARE}::{path}" for path, _ in ELEMENT_DEFINITIONS.values()} | {
        f"{SOFTWARE}::scoreServices::{process}" for process in GATEWAY_PROCESSES}
    assert f"private import {LOGICAL_PACKAGE}::{LOGICAL_SYSTEM};" in _code()
    # the owner's picks, each pinned by the allocation that records it
    assert ALLOCATIONS["planner"] == ["drivingAgent::inferPlan"], "the planner is an activity of the agent"
    assert ALLOCATIONS["actuationGateway"] == ["actuationAdapter"], "a process of its own, so REQ-DRIVING-028 survives the agent"
    assert "drivingAgent" not in " ".join(ALLOCATIONS["statePublisher"]), "observation is off the agent"


def test_each_crossing_has_one_signal_mapping_with_a_complete_record():
    mappings = [(name, source, target, body) for name, kind, source, target, body in _allocations()
                if kind == "SystemToSoftwareSignalMappingCandidate"]
    assert [name for name, *_ in mappings] == list(SIGNAL_MAPPINGS)
    raw = _raw()
    for name, source, target, body in mappings:
        logical, path, short = SIGNAL_MAPPINGS[name]
        assert source == f"{LOGICAL_SYSTEM}::{logical}", name
        assert target == f"{SOFTWARE_CHAIN}.{path.replace('::', '.')}", name
        assert "::" not in target, "a chain through the realizing usage, not a qualified name"
        records = re.findall(r"\bitem\s+<'([^']+)'>\s+(\w+)\s*:\s*LogicalToSoftwareSignalMappingRecord\s*\{", body)
        assert records == [(short, f"{name[:-len('Mapping')]}MappingRecord")], name
        record = braced_body(raw, f"item <'{short}'> {records[0][1]} : LogicalToSoftwareSignalMappingRecord")
        assert re.match(r"\s*doc\s*/\*", record), short
        stated = dict(re.findall(r'attribute\s*:>>\s*(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|SignalMappingDisposition::\w+)\s*;', record))
        assert tuple(stated) == RECORD_ATTRIBUTES, (short, tuple(stated))
        for attribute, value in stated.items():
            assert len(value) > 12 and not re.search(r"\b(TBD|TBC|TODO)\b|<[^']", value), (short, attribute)
        assert stated["disposition"] == "SignalMappingDisposition::candidate", short
        assert stated["owner"] == '"DE4SDV maintainers"', short
        assert stated["nextAction"].startswith('"phase 10'), short
    assert "private import DE4SDV_MethodProcess::SystemToSoftwareSignalMappingCandidate;" in _code()
    assert "private import DE4SDV_MethodProcess::LogicalToSoftwareSignalMappingRecord;" in _code()
    assert "private import DE4SDV_MethodProcess::SignalMappingDisposition;" in _code()


def test_the_records_say_what_each_item_is_and_where_the_vss_typing_is():
    raw = _raw()
    def record(short):
        return braced_body(raw, f"item <'{short}'>")
    assert "no vehicle signal" in record("MAP-DRIVING-CAMERA-IMAGES") or "not a vehicle signal" in record("MAP-DRIVING-CAMERA-IMAGES")
    assert "Vehicle_Speed" in record("MAP-DRIVING-EGO-MOTION") and "km/h" in record("MAP-DRIVING-EGO-MOTION")
    assert "curvature" in record("MAP-DRIVING-EGO-MOTION"), "the fourth history input is derived, not a VSS signal"
    assert "Vehicle_ADAS_Driving_Command_Acceleration" in record("MAP-DRIVING-COMMAND")
    assert "REQ-DRIVING-014" in record("MAP-DRIVING-COMMAND")
    assert "VehicleControl" in record("MAP-DRIVING-VEHICLE-CONTROL") and "REQ-DRIVING-028" in record("MAP-DRIVING-VEHICLE-CONTROL")
    state = record("MAP-DRIVING-OPERATIONAL-STATE")
    for hop in ("gatewayd", "someipd", "SOME/IP", "Data Tunnel", "VSIDL", "REQ-DRIVING-017"):
        assert hop in state, hop
    assert "ONNX" in record("MAP-DRIVING-PLAN") or "exported" in record("MAP-DRIVING-PLAN")


def test_the_assumptions_and_gaps_of_the_realization_are_recorded_with_short_names():
    code = _code()
    assert dict(re.findall(r"\bpart\s+<'(ASM-DRIVING-\d{3})'>\s+(\w+)\s*:\s*IncrementAssumption\s*\{", code)) == ASSUMPTIONS
    assert dict(re.findall(r"\bpart\s+<'(GAP-DRIVING-\d{3})'>\s+(\w+)\s*:\s*IncrementGap\s*\{", code)) == GAPS
    assert "private import DE4SDV_MethodContext::*;" in code
    raw = _raw()
    for short, name in {**ASSUMPTIONS, **GAPS}.items():
        kind = "IncrementAssumption" if short.startswith("ASM") else "IncrementGap"
        doc = _doc(f"part <'{short}'> {name} : {kind}")
        assert len(doc) > 120, short
        for word in GAP_MENTIONS.get(short, ()):
            assert word in doc, (short, word)
    for short in GAPS:
        body = braced_body(code, f"part <'{short}'>")
        assert "attribute :>> disposition = LifecycleDisposition::" in body, short


def test_the_package_records_the_pins_the_alternatives_and_what_phase_8_settled():
    raw = _raw()
    head = raw[:raw.index("package " + PACKAGE)]
    for pin in PINS:
        assert pin in raw, pin
    for alternative in ALTERNATIVES:
        assert alternative in head, alternative
    assert "KUKSA" in head
    comments = re.findall(r"\bcomment\s+(\w+)\s+about\s+(\w+)", _code())
    assert sorted(comments) == sorted([("phase8TransportSettled", "gapTransportAndControl"),
                                       ("phase8ConversionPlacement", "gapModelInputAndFeedback"),
                                       ("reqPlansAndCommandsOverSCOREReading", "reqPlansAndCommandsOverSCORE")])
    for gap in ("gapTransportAndControl", "gapModelInputAndFeedback"):
        assert f"private import DE4SDV_ClosedLoopDrivingFraming::{gap};" in _code(), gap
    # the owner's reading of REQ-DRIVING-014 (2026-11-06) closed the in-process-hops question: no gap carries it
    assert "private import DE4SDV_ClosedLoopDrivingNeedsRequirements::reqPlansAndCommandsOverSCORE;" in _code()
    assert re.search(r"\bcomment\s+reqPlansAndCommandsOverSCOREReading\s+about\s+reqPlansAndCommandsOverSCORE,\s*"
                     + AGENT + r"\b", _code())
    reading = _flat(re.search(r"comment reqPlansAndCommandsOverSCOREReading[^/]*/\*(.*?)\*/", _raw(), re.S).group(1))
    for phrase in ("2026-11-06", "hops between processes", "mw::com", "no hops between processes",
                   "REQ-DRIVING-014 does not constrain them", "The placement stands", "logs them as FEO topics"):
        assert phrase in reading, phrase
    assert "GAP-DRIVING-008" not in _raw() and "gapInProcessHopsUnderREQ014" not in _raw()
    for concern in FRAMING_CONCERNS:
        assert f"private import DE4SDV_ClosedLoopDrivingFraming::{concern};" in _code(), concern


def test_the_package_publishes_exactly_one_view_per_question():
    declared = re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M)
    assert sorted(declared) == sorted(VIEWS)
    assert len(declared) == 4


@pytest.mark.parametrize("view_name", sorted(VIEWS), ids=sorted(VIEWS))
def test_each_view_frames_its_concerns_and_exposes_its_content(view_name):
    view_type, render, exposes, viewpoint_type, frames = VIEWS[view_name]
    code = _code()
    header = rf"\bview\s+{view_name}\s*" + (rf":\s*{re.escape(view_type)}\s*" if view_type else "") + r"\{"
    assert re.search(header, code), view_name
    view = braced_body(code, f"view {view_name}" + (f" : {view_type}" if view_type else ""))
    viewpoint = braced_body(view, "viewpoint")
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == frames
    assert re.search(rf"viewpoint\s+\w+\s*:\s*{viewpoint_type}\s*\{{", view), view_name
    assert len(re.findall(r"\bviewpoint\b", view)) == 1
    assert re.findall(r"\bexpose\s+([\w:*]+(?:\[[^\]]*\])?)\s*;", view) == exposes
    if render:
        assert render in view
        if view_name != CONTEXT_VIEW:
            assert "filter not (@ SysML::AllocationUsage);" in view, "SysIDE draws the package's allocations otherwise"
    else:
        assert "render as" not in view, "the view type selects the kind"


def test_the_interconnection_views_draw_the_path_and_the_context_at_their_depths():
    code = _code()
    path = braced_body(code, f"view {PATH_VIEW}")
    assert "attribute depth = -1;" in path and "attribute showAnnotationRows = false;" in path
    context = braced_body(code, f"view {CONTEXT_VIEW}")
    # depth 1 drew one box with a parts compartment and no hop (run 42212398480); a wildcard over the usages drew
    # the parts without their definition-declared ports and no hop (run 42214648709): each element is named
    assert "attribute depth = -1;" in context and "attribute maxCompartmentEntries = 0;" in context
    assert "attribute showAnnotationRows = false;" in context
    # a connection with one exposed end drew as a box with two ends (run 42215689738: the delegations inside the
    # host and the guests); the exchanges the view draws are flows; the delegations are filtered by exact type
    # (`@`, subtype-inclusive, took the flows with them: run 42247403125), the hypervisor interfaces by theirs
    assert "filter not (hastype SysML::ConnectionUsage);" in context
    assert len(re.findall(r"\bfilter\b", context)) == 1, "the AEBS form: allocations and interfaces with no exposed end are not drawn"
    tree = braced_body(code, f"view {STRUCTURE_VIEW}")
    assert "filter not (@ SysML::BindingConnectorAsUsage);" in tree, "the guest's bind drew as a box with two ends"
    assert "FlowUsage" not in tree, "filtering the flows did not remove their ends from the parts' compartments (run 42248991235)"


def test_the_matrix_maps_the_logical_elements_to_the_software_with_reference_elements():
    view = braced_body(_code(), f"view {MATRIX_VIEW} : MVD::MatrixView")
    rows = braced_body(view, "view :>> rowView")
    columns = braced_body(view, "view :>> columnView")
    cells = braced_body(view, "view :>> cellView")
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", rows) == [f"{LOGICAL_SYSTEM}::{element}" for element in LOGICAL_ELEMENTS]
    assert len(re.findall(r"\bexpose\s+([\w:]+)\s*;", columns)) == 8
    for axis in (rows, columns):
        assert "attribute :>> includeReferenceElements = true;" in axis
        assert "attribute :>> representation = Rep::name;" in axis
    assert f"expose {PACKAGE}::*;" in cells
    assert "attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;" in cells
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"matrix-{MATRIX_VIEW}"]
    assert metadata.title and "eight" in metadata.description, MATRIX_VIEW


@pytest.mark.parametrize("concern_name", sorted(CATALOGUE_CONCERNS), ids=sorted(CATALOGUE_CONCERNS))
def test_each_phase_8_concern_is_typed_by_the_catalogue_and_held_by_the_party_it_serves(concern_name):
    catalogue, stakeholders = CATALOGUE_CONCERNS[concern_name]
    concern = braced_body(_code(), f"concern {concern_name} : {catalogue}")
    members = re.findall(r"\b(subject|stakeholder)\b", concern)
    assert members and members[0] == "subject"
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == stakeholders
    assert "need" in _doc(f"concern {concern_name} : {catalogue}")


def test_the_phase_1_physical_concerns_are_framed_here_in_their_domain_and_the_list_deviation_is_pinned():
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    for concern, catalogue in (("scoreCommandPathConcern", "PhysicalInternalExchangeConcern"),
                               ("checkpointCommandAuthorityConcern", "PhysicalFunctionalMappingConcern"),
                               ("aaosObservationFidelityConcern", "PhysicalContextExchangeConcern")):
        assert re.search(rf"\bconcern\s+{concern}\s*:\s*{catalogue}\b", framing), concern
    assert not re.search(r"\bconcern\s+(scoreCommandPathConcern|checkpointCommandAuthorityConcern|aaosObservationFidelityConcern)\b", _code()), \
        "framed, never redeclared"
    import test_views_per_phase as views

    assert views.KNOWN_DEVIATIONS[("INC-DRIVING-001", CONTEXT_VIEW)] == ((8,), "PhysicalContextExchangeViewpoint")
    assert "PhysicalContextExchangeViewpoint" not in views.CANONICAL[8], "pinned as a deviation until the method lists it"


def test_the_element_docs_make_no_assurance_claim():
    declarations = [f"part def {d} :> PhysicalAllocationElement" for d in ELEMENT_DEFINITIONS]
    declarations += [f"part def {AGENT}", f"part def {REALIZATION} :> {IDENTITY}", f"part def {HOST}", f"part def {SYSTEM}"]
    for declaration in declarations:
        doc = _doc(declaration)
        found = [word for word in CLAIM_WORDS if word in doc.lower()]
        assert not found, (declaration, found)
    assert not re.search(r"\b(realizedBy|deployedTo|validatedBy|constrainedBy)\b", re.sub(r'"(?:[^"\\]|\\.)*"', '""', _code()))


def test_the_allocation_file_is_governed_with_its_six_endpoint_definitions():
    import test_trace_allocation_completeness as trace

    assert trace.ALLOCATION_FILES[trace.DRIVING_P] == (
        (trace.DRIVING_P, trace.DRIVING_L), {(trace.LOGICAL, trace.PHYSICAL): 8},
        {"SystemToSoftwareSignalMappingCandidate": 8}, (trace.LOGICAL, trace.PHYSICAL))
    assert trace.GOVERNED[trace.DRIVING_P] == (trace.PHYSICAL, set(ELEMENT_DEFINITIONS))
    assert trace.DRIVING_P in trace.LINEAGE_FILES
    assert trace.NOT_ENDPOINTS[trace.DRIVING_P] == {SYSTEM, HOST, REALIZATION, AGENT, "CARLASimulationServer",
                                                    "ScenarioRouteProvider", "AAOSSDVCoreGuest", "AAOSIVIGuest"}


def test_the_guide_describes_phase_8_and_names_phase_9_as_the_next_work():
    guide = GUIDE.read_text(encoding="utf-8")
    assert "## Physical and software realization (Phase 8)" in guide
    assert "closed_loop_driving_physical_software_realization.sysml" in guide
    flat = " ".join(guide.split())
    for word in ("FEO", "actuation adapter", "state publisher", "gatewayd", "ONNX", "v0.10.0", "v1.0.5",
                 "GAP-DRIVING-005", "reqPlansAndCommandsOverSCOREReading", "KUKSA", "two clocks side by side",
                 "simulated sensor rig", "the vehicle control and nothing else", "2026-11-06"):
        assert word in flat, word
    assert "GAP-DRIVING-008" not in guide
    assert "The next work is **Phase 9**" in guide
    assert "The next work is **Phase 8**" not in guide
    assert "tests/test_closed_loop_driving_physical_software_realization.py" in guide
