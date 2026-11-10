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
#: the two hosts the bench added beside the S-CORE host (owner decision of 2026-11-09: three hosts)
SIMULATOR_HOST = "ClosedLoopDrivingSimulatorHost"
GUEST_HOST = "AAOSGuestHost"
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
                                    "vehicleControlOut": "VehicleControlOut",
                                    "actuationStateOut": "ActuationStateOut"},
    "OperationalStatePublisherApplication": {"planIn": "DrivingPlanIn", "modeIn": "DrivingModeIn",
                                             "egoMotionSampleIn": "EgoMotionSampleIn",
                                             "actuationStateIn": "ActuationStateIn",
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
    "ActuationStateOut": ("out", "actuationState", "ActuationState"),
    "ActuationStateIn": ("in", "actuationState", "ActuationState"),
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
#: the realization's boundary ports are bound to the programs' ports: a bind is not drawn in an interconnection
#: view, where a delegation connection with an unexposed end drew as a box with two ends (run 42215689738)
REALIZATION_BINDS = {
    ("cameraImagesIn", "drivingAgent.cameraImagesIn"),
    ("egoMotionIn", "drivingAgent.egoMotionIn"),
    ("routeIn", "drivingAgent.routeIn"),
    ("simulationClockIn", "actuationAdapter.simulationClockIn"),
    ("vehicleControlOut", "actuationAdapter.vehicleControlOut"),
    ("operationalStateOut", "scoreServices.someipd.operationalStateOut"),
}
REALIZATION_CONNECTIONS = {
    ("drivingAgent.commandOut", "actuationAdapter.commandIn"),
    ("drivingAgent.planEventOut", "statePublisherApplication.planIn"),
    ("drivingAgent.modeEventOut", "statePublisherApplication.modeIn"),
    ("drivingAgent.egoMotionSampleOut", "statePublisherApplication.egoMotionSampleIn"),
    ("actuationAdapter.actuationStateOut", "statePublisherApplication.actuationStateIn"),
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
    "actuationStateOverSCORECommunication": ("actuationAdapter.actuationStateOut",
                                             "statePublisherApplication.actuationStateIn"),
    "operationalStateOverSCORECommunication": ("statePublisherApplication.operationalStateOut",
                                               "scoreServices.gatewayd.operationalStateIn"),
}
#: The three hosts of the bench (owner decision of 2026-11-09). Each host hands its exchanges to its own ports with
#: named connections, drawn as edges between exposed ports; flows between these ports were not drawn in six licensed
#: runs (42247403125 to 42253633791); each port definition carries the one item its exchange moves, and into the
#: simulator goes the vehicle control and nothing else.
HOST_PORTS = {"cameraImagesIn": "CameraStreamIn", "egoMotionIn": "EgoMotionStreamIn",
              "simulationClockIn": "SimulationClockIn", "vehicleControlOut": "VehicleControlOut",
              "operationalStateOut": "OperationalStateOut"}
HOST_CONNECTIONS = {
    "cameraImagesDelegation": ("cameraImagesIn", "drivingSoftware.cameraImagesIn"),
    "egoMotionDelegation": ("egoMotionIn", "drivingSoftware.egoMotionIn"),
    "simulationClockDelegation": ("simulationClockIn", "drivingSoftware.simulationClockIn"),
    "routeFromScenario": ("routeProvider.routeOut", "drivingSoftware.routeIn"),
    "vehicleControlDelegation": ("drivingSoftware.vehicleControlOut", "vehicleControlOut"),
    "operationalStateDelegation": ("drivingSoftware.operationalStateOut", "operationalStateOut"),
}
SIMULATOR_HOST_PORTS = {"cameraStreamOut": "CameraStreamOut", "egoMotionOut": "EgoMotionStreamOut",
                        "simulationClockOut": "SimulationClockOut", "vehicleControlIn": "VehicleControlIn"}
SIMULATOR_HOST_CONNECTIONS = {
    "cameraStreamDelegation": ("carlaServer.cameraStreamOut", "cameraStreamOut"),
    "egoMotionDelegation": ("carlaServer.egoMotionOut", "egoMotionOut"),
    "simulationClockDelegation": ("carlaServer.simulationClockOut", "simulationClockOut"),
    "vehicleControlDelegation": ("vehicleControlIn", "carlaServer.vehicleControlIn"),
}
#: system exchange -> (source, target): the simulator's exchanges cross the bench network between the simulator host
#: and the S-CORE host; the operational state crosses the VXLAN segment into the SDV Core VM, then the VMs
SYSTEM_CONNECTIONS = {
    "cameraStreamOverBenchNetwork": ("simulatorHost.cameraStreamOut", "linuxHost.cameraImagesIn"),
    "egoMotionOverBenchNetwork": ("simulatorHost.egoMotionOut", "linuxHost.egoMotionIn"),
    "simulationClockOverBenchNetwork": ("simulatorHost.simulationClockOut", "linuxHost.simulationClockIn"),
    "vehicleControlOverBenchNetwork": ("linuxHost.vehicleControlOut", "simulatorHost.vehicleControlIn"),
    "operationalStateOverSOMEIPAcrossVXLANSegment": ("linuxHost.operationalStateOut", "sdvCoreGuest.someIpIn"),
    "operationalStateTopicOverDataTunnelAcrossVMs": ("sdvCoreGuest.topicOut", "hmiGuest.topicIn"),
}
SDV_CORE_GUEST_BINDS = {("sdvCore", "sdvMiddleware"), ("someIpIn", "sdvCore.someIp.someIpPort"),
                        ("topicOut", "sdvCore.dataTunnel.topicSubscribePort")}
SDV_CORE_GUEST_CONNECTIONS = {("sdvCore.someIp.topicPublishOut", "sdvCore.dataTunnel.topicPublishPort")}
HMI_GUEST_BINDS = {("topicIn", "sdvGateway.dataTunnelPort")}
HMI_GUEST_CONNECTIONS = {("sdvGateway.clientPort", "stateObserver.operationalStateIn")}

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
    "actuationStateMapping": ("actuationGateway", "actuationAdapter::actuationStateOut",
                              "MAP-DRIVING-ACTUATION-STATE"),
    "operationalStateMapping": ("statePublisher", "scoreServices::someipd::operationalStateOut",
                                "MAP-DRIVING-OPERATIONAL-STATE"),
}
RECORD_ATTRIBUTES = ("semanticSource", "softwareContractArtifact", "softwareContractMessage",
                     "softwareContractField", "dataTypeAndUnit", "timingQualityAndState", "transformationRule",
                     "disposition", "owner", "nextAction", "evidenceOrGap")

ASSUMPTIONS = {
    "ASM-DRIVING-001": "asmFixedOrderCycleCarriesTheLoop",
    "ASM-DRIVING-002": "asmPlannerStackStandsForTheCheckpoint",
    "ASM-DRIVING-003": "asmSimulatorClientsInsideSCOREApplications",
    "ASM-DRIVING-004": "asmSimulatedSensorsStandForTheVehicles",
}
GAPS = {
    "GAP-DRIVING-001": "gapFEOOutsideReleasedBaseline",
    "GAP-DRIVING-003": "gapPlannerStackParityUnproven",
    "GAP-DRIVING-006": "gapTypedOperationalStateTopicUnproven",
    "GAP-DRIVING-007": "gapThreeHostBenchUnjoined",
    "GAP-DRIVING-010": "gapClosedLoopHistoryFeedback",
    "GAP-DRIVING-011": "gapRouteChoosesNoBranch",
    "GAP-DRIVING-012": "gapPlansKeepNoLane",
    "GAP-DRIVING-013": "gapPlanningPeriodNarrowlyMissed",
}
#: retired by the amendment of 2026-11-09 on the readiness probes' evidence: the records left the model
RETIRED = {
    "GAP-DRIVING-002": "gapSOMEIPGatewayAgainstCommunication060",
    "GAP-DRIVING-004": "gapSimulatorClientBuildUnproven",
}
#: renamed by the same amendment: the old names are gone
RENAMED_AWAY = ("asmExportedModelStandsForTheCheckpoint", "gapModelExportAndParityUnproven",
                "gapGPUAndKVMHostUnprovisioned")
#: what each gap must name
GAP_MENTIONS = {
    "GAP-DRIVING-001": ("v1.0.5", "313b3d84", "known_good", "event trigger", "single_version_override", "Rust"),
    "GAP-DRIVING-003": ("PyTorch", "parity", "tolerance", "REQ-DRIVING-035", "ONNX"),
    "GAP-DRIVING-006": ("VSIDL", "GAP-MW-038"),
    "GAP-DRIVING-007": ("GPU", "KVM", "gapBoundedCloudCampaign", "three hosts", "VXLAN"),
    "GAP-DRIVING-010": ("asmSourceAuthenticity", "owner decision of 2026-11-09", "experiment/closed-loop/RESULTS.md",
                        "readiness probe", "REQ-DRIVING-008", "yaw rate and curvature as zero",
                        "Revisit when upstream publishes"),
    "GAP-DRIVING-011": ("owner decision of 2026-11-10", "takes no turn from the route", "REQ-DRIVING-008",
                        "no branch choice", "Revisit when upstream publishes"),
    "GAP-DRIVING-012": ("owner decision of 2026-11-10", "does not keep the vehicle in its lane", "REQ-DRIVING-008",
                        "GAP-DRIVING-010", "SC-DRIVING-005", "Revisit when upstream publishes"),
    "GAP-DRIVING-013": ("owner decision of 2026-11-10", "REQ-DRIVING-013 is narrowly not met", "99.2 %", "99.0 %",
                        "gapClosedLoopPerformance", "The limit stays at 100 ms", "Revisit with a faster host"),
    "ASM-DRIVING-001": ("event trigger", "newest frame", "Rust", "REQ-DRIVING-013"),
    "ASM-DRIVING-002": ("PyTorch", "rounding", "REQ-DRIVING-033", "tolerance"),
    "ASM-DRIVING-003": ("pacer", "bench network", "synchronous mode"),
    "ASM-DRIVING-004": ("rendered", "ground truth", "noise", "latency", "camera", "motion", "1920"),
}
#: The route decision of 2026-11-10 (GAP-DRIVING-011), as the gap states it: what was measured on the pinned
#: checkpoint, what upstream's code and evaluation say about the route, what it means for the scenario's route, and
#: when to revisit. The scenario's route itself is bench configuration and stays out of the model.
ROUTE_GAP_STATEMENTS = (
    "Open, and accepted as a known limit (owner decision of 2026-11-10): the pinned checkpoint takes no turn from "
    "the route.",
    "Given the same camera images, map and motion history, swapping a route that turns hard left for the same route "
    "mirrored to a hard right changes the planned heading at 6.4 s by at most 0.02 degrees, where a turn at a "
    "junction needs about 60.",
    "This holds with the motion history as REQ-DRIVING-008 gives it (yaw rate and curvature zero) and with the "
    "recorded history, with a route corridor drawn road-wide as in the checkpoint's training data, with a "
    "destination marker 40 m along the route, and with the cameras blanked and no map, where the route is the only "
    "navigation input (0.01 degrees).",
    "Upstream's other released checkpoint (kitscenes-epoch-5) moves its planned heading by at most 1.5 degrees for "
    "the corridor and by 4 degrees for a route that ends 40 m ahead in a destination marker.",
    "Upstream's route-reconstruction head reads the navigation encoder's route contribution, not the fused camera "
    "and navigation features the planner sees (Model/model_components/reactive_e2e.py), so its training teaches "
    "encoding the route, not driving along it;",
    "upstream's own evaluation (Academic_Paper/AutoE2E_Route_Conditioned/paper_en.md) states that its "
    "route-reconstruction score is not evidence that the policy drove along the route, and lists route-determined "
    "branch choice as a hypothesis still to be tested.",
    "So the route enters the plans but does not choose the branch at a junction.",
    "The scenario's route therefore needs no branch choice: every junction on it is passed straight on (CARLA's "
    "route planner gives only lane-follow and straight road options), and the evidence claims no route following "
    "at junctions.",
    "Revisit when upstream publishes a checkpoint whose plans take the turn from the route.",
)
#: The deadline decision of 2026-11-10 (GAP-DRIVING-013), as the gap states it: the runs on the bench, why the margin
#: is small, what stays and when to revisit. The numbers are the evaluator's for the 60 s window of REQ-DRIVING-013 and
#: the runs' timing records: three runs on the straight route, one of them after the bench's steering correction, which
#: does not touch the plan times.
DEADLINE_GAP_STATEMENTS = (
    "Open, and accepted as a known limit (owner decision of 2026-11-10): REQ-DRIVING-013 is narrowly not met.",
    "In three runs of the closed-loop scenario on a straight route (2026-11-10), 595, 585 and 588 of the 600 plans of "
    "the 60 s window were produced within 100 ms after their newest camera image was available (99.2 %, 97.5 % and "
    "98.0 %), and in each run two consecutive plans missed it; the latest plan was 1.7, 7.7 and 3.1 ms late.",
    "In an earlier run (2026-11-09), with the vehicle standing after a contact for about three quarters of the "
    "window, 594 of 600 were in time (99.0 %) and no two consecutive plans missed, which meets the criterion at its "
    "limit.",
    "The margin is small by construction: the checkpoint's inference alone takes about 90 ms, and in the three runs a "
    "plan took 95.9 to 96.3 ms at the median and 99.9 to 101.6 ms at the 99th percentile, so a delay of a few "
    "milliseconds anywhere in the step makes a miss.",
    "The limit stays at 100 ms, the planning period, and the miss is accepted instead of the hold or redirect that "
    "gapClosedLoopPerformance names.",
    "Revisit with a faster host, or with a faster engine for the checkpoint, which changes its numbers and needs its "
    "own parity evidence.",
)
#: The lane decision of 2026-11-10 (GAP-DRIVING-012), as the gap states it: what the runs on a straight route showed,
#: before and after the bench's steering correction, what the readiness probe showed, which other bench-side causes were
#: checked, why no history setting keeps the lane, and what the evidence and the review of NEED-DRIVING-001 take from
#: it. The numbers are the runs' own records: the plans, the vehicle's poses and the adapter's applied commands.
LANE_GAP_STATEMENTS = (
    "Open, and accepted as a known limit (owner decision of 2026-11-10): the pinned checkpoint does not keep the "
    "vehicle in its lane.",
    "In runs of the closed-loop scenario on a straight route (2026-11-10), with the motion history as REQ-DRIVING-008 "
    "gives it, the plans leaned to one side from the first plan that moved the vehicle, with the vehicle aligned in its "
    "lane, and never steered back.",
    "Until a correction that day, the bench applied every steering command at twice its angle: its actuation adapter "
    "scaled the steer by the 35 degree command limit instead of by the vehicle's maximum steering angle of 70 degrees, "
    "as MAP-DRIVING-VEHICLE-CONTROL states.",
    "In two runs before the correction the vehicle turned at 1.9 times the commanded rate and was in the next lane "
    "11.5 and 11.6 s after the first plan; of 375 and 405 plans made with the vehicle more than 0.3 m to that side of "
    "the route, 3 and 2 pointed back toward it.",
    "In the run after the correction the vehicle turned at 0.95 times the commanded rate and was in the next lane "
    "14.7 s after the first plan, and the plans still leaned and did not correct: until the vehicle first crossed a "
    "lane marking, their heading 10 m ahead was 1.7 degrees off the vehicle's at the median (2.2 in both runs before), "
    "and of 434 plans made with the vehicle more than 0.3 m to that side, 2 pointed back.",
    "In the readiness probe, with the yaw history also given as zero, the vehicle drifted to the other side in the "
    "same way (GAP-DRIVING-010).",
    "Other bench-side causes were checked: the camera's principal point is 0.08 degrees off centre, the motion history "
    "carries only speed and acceleration, and the drift went to opposite sides on the bench and in the readiness probe, "
    "which makes a fixed error of the camera rig unlikely.",
    "With its own yaw history the checkpoint turns its plans off the lane within seconds (GAP-DRIVING-010); without "
    "it, as here, the plans do not correct a drift. So neither setting keeps the vehicle in its lane.",
    "The evidence therefore claims no lane keeping and no driving along the route, and the review of NEED-DRIVING-001 "
    "(SC-DRIVING-005) names this limit.",
    "Revisit when upstream publishes a checkpoint that keeps its lane in a closed loop.",
)
#: GAP-DRIVING-010 keeps the junction it observed and what the history mask means for the plans; since the route
#: decision of 2026-11-10 the junction is a limit of its own (GAP-DRIVING-011), not a consequence of the mask.
HISTORY_GAP_STATEMENTS = (
    "In the readiness probe the plans then no longer turned off the lane within seconds: the vehicle stayed in its "
    "lane for the 12 s to the first junction, though it drifted steadily to one side without steering back, and "
    "drove straight on at that junction where the route turned.",
    "The plans are therefore not what the checkpoint makes on the full history it was trained with.",
    "That the route does not steer the vehicle at junctions is a separate limit, independent of the history "
    "(GAP-DRIVING-011).",
)
NUMBER_WORDS = {4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight"}
PINS = ("313b3d849c17881d3a11b6bf62aa2afab6565ef0", "ca2a5f03724780be3cebf3d80e0c9c0c6fa64eb2",
        "d9eac670b7534352749da3d30f52aebf5129f168", "cb50764b8250a3c44ee5b79b87ba02c5a83b0c91", "v0.10.0",
        "v1.0.5", "0.6.0", "ALT-MW-KUKSA-001", "torch 2.7.1", "triton 3.3.1", "9.26.0.51")
ALTERNATIVES = ("ALT-DRIVING-PLAINAPPS-001", "ALT-DRIVING-SIMBRIDGE-001", "ALT-DRIVING-LIBTORCH-001",
                "ALT-DRIVING-FEOMWCOM-001", "ALT-DRIVING-ONNXENGINE-001", "ALT-DRIVING-FEOGATE-001",
                "ALT-DRIVING-LOCKSTEP-001")
#: the owner's decisions of 2026-11-07 to 2026-11-09 the package's head records, from the readiness probes P1 to P4
#: (a probe is evidence for an amendment, never a result of the increment)
AMENDMENT_PHRASES = (
    "2026-11-07", "2026-11-08", "2026-11-09", "readiness probes", "never a result of the increment",
    "Rust", "C++ libraries", "event trigger", "newest frame", "single_version_override", "as root",
    "PyTorch", "in the agent's process", "TensorRT", "torch 2.7.1", "triton 3.3.1", "9.26.0.51",
    "synchronous mode", "pacer", "frame index", "NVENC", "warm-up lap", "nothing retimed",
    "separate real-time recordings", "three hosts", "bench network", "VXLAN", "no redirect",
    # the eight operating rules of decision 5
    "pinned code", "parity check", "capture-safe preprocessing", "no recompilation after the warm-up",
    "64 entries", "capture times from the frame index", "never on the planner's card",
    "one warm-up lap of the route with every camera, the recording view included, in the same simulator session "
    "before any judged or recorded run",
)

STRUCTURE_VIEW = "closedLoopDrivingPhysicalStructureView"
MATRIX_VIEW = "closedLoopDrivingPhysicalLogicalMappingView"
PATH_VIEW = "closedLoopDrivingSCOREPathExchangeView"
CONTEXT_VIEW = "closedLoopDrivingPhysicalContextExchangeView"
TREE_EXPOSES = [SYSTEM_USAGE] + [f"{SYSTEM_USAGE}::{path}" for path in (
    "linuxHost", "linuxHost::os", "linuxHost::drivingSoftware",
    "linuxHost::drivingSoftware::drivingAgent", "linuxHost::drivingSoftware::drivingAgent::conditionInputs",
    "linuxHost::drivingSoftware::drivingAgent::inferPlan", "linuxHost::drivingSoftware::drivingAgent::superviseLoop",
    "linuxHost::drivingSoftware::drivingAgent::commandVehicle", "linuxHost::drivingSoftware::actuationAdapter",
    "linuxHost::drivingSoftware::statePublisherApplication", "linuxHost::drivingSoftware::scoreServices",
    "linuxHost::drivingSoftware::scoreServices::launchManager", "linuxHost::drivingSoftware::scoreServices::gatewayd",
    "linuxHost::drivingSoftware::scoreServices::someipd", "linuxHost::routeProvider",
    "simulatorHost", "simulatorHost::os", "simulatorHost::carlaServer", "simulatorHost::carlaServer::sensorRig",
    *(f"simulatorHost::carlaServer::sensorRig::{camera}Camera" for camera in (
        "front", "frontLeft", "frontRight", "rearLeft", "rear", "rearRight")),
    "simulatorHost::carlaServer::sensorRig::egoMotionSource",
    "guestHost", "guestHost::os", "guestHost::hypervisor",
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
                       "linuxHost", *(f"linuxHost::{port}" for port in HOST_PORTS), "linuxHost::drivingSoftware",
                       *(f"linuxHost::drivingSoftware::{port}" for port in (
                           "cameraImagesIn", "egoMotionIn", "routeIn", "simulationClockIn", "vehicleControlOut",
                           "operationalStateOut")),
                       "linuxHost::routeProvider", "linuxHost::routeProvider::routeOut",
                       *(f"linuxHost::{name}" for name in HOST_CONNECTIONS),
                       "simulatorHost", *(f"simulatorHost::{port}" for port in SIMULATOR_HOST_PORTS),
                       "simulatorHost::carlaServer",
                       *(f"simulatorHost::carlaServer::{port}" for port in (
                           "cameraStreamOut", "egoMotionOut", "simulationClockOut", "vehicleControlIn")),
                       *(f"simulatorHost::{name}" for name in SIMULATOR_HOST_CONNECTIONS),
                       "sdvCoreGuest", "sdvCoreGuest::someIpIn", "sdvCoreGuest::topicOut", "hmiGuest", "hmiGuest::topicIn",
                       *SYSTEM_CONNECTIONS)],
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
                SIMULATOR_HOST, GUEST_HOST,
                REALIZATION, AGENT, "SimulatedSensorRig", "SimulatedCamera", "SimulatedEgoMotionSource")
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
    return re.findall(r"\bconnection\s+\w+\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*[;{]", body)


def _named_connections(body: str) -> dict[str, tuple[str, str]]:
    return {name: (source, target) for name, source, target in re.findall(
        r"\bconnection\s+(\w+)\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*[;{]", body)}


def _binds(body: str) -> set[tuple[str, str]]:
    return set(re.findall(r"\bbind\s+([\w.]+)\s*=\s*([\w.]+)\s*;", body))


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
    assert names.index(PACKAGE) == names.index(LOGICAL_PACKAGE) + 1 == len(names) - 3
    assert names[-2:] == ["DE4SDV_ClosedLoopDrivingVariabilityConfiguration",
                          "DE4SDV_ClosedLoopDrivingVerificationEvidence"], "phases 9 and 10 follow phase 8 in the charter"
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
    assert "ref part" not in body, "a reference bound to a host part drew no processes (run 42212398480)"
    assert not re.search(r"\bbind\s+scoreServices\b", body), "the services are owned, not bound to the host's"
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
    connections = _connections(_direct(body))
    assert set(connections) == REALIZATION_CONNECTIONS and len(connections) == len(REALIZATION_CONNECTIONS)
    named = dict(re.findall(r"\bconnection\s+(\w+)\s+connect\s+([\w.]+\s+to\s+[\w.]+)\s*;", body))
    for name, (source, target) in SCORE_COMMUNICATION_HOPS.items():
        assert named[name] == f"{source} to {target}", name
    assert _binds(_direct(body)) == REALIZATION_BINDS, "the boundary ports are bound, not connected"
    # nothing runs from the actuation adapter or the publisher back into the agent (phase 7's one-way rule)
    for source, target in connections:
        if source.startswith(("actuationAdapter.", "statePublisherApplication.", "scoreServices.")):
            assert not target.startswith("drivingAgent."), (source, target)


def test_the_simulator_server_carries_the_sensor_rig_the_checkpoint_profile_shapes():
    """The owner's sensing decision of 2026-11-06: the loop uses the simulation's sensors, described on the bench."""
    code = _code()
    assert "part sensorRig : SimulatedSensorRig;" in braced_body(code, "part def CARLASimulationServer")
    rig = braced_body(code, "part def SimulatedSensorRig")
    cameras = re.findall(r"\bpart\s+(\w+)\s*:\s*SimulatedCamera\s*\{\s*attribute\s+:>>\s+position\s*=\s*CameraPosition::(\w+);\s*\}", rig)
    assert cameras == [(f"{p}Camera", p) for p in ("front", "frontLeft", "frontRight", "rearLeft", "rear", "rearRight")], \
        "six cameras, one per position of REQ-DRIVING-003, in its order"
    assert "part egoMotionSource : SimulatedEgoMotionSource;" in rig
    assert not re.search(r"\b(connection|bind|flow|port)\b", rig), "nothing in the rig draws as a box in the context view"
    assert "attribute position : CameraPosition;" in braced_body(code, "part def SimulatedCamera")
    assert "private import DE4SDV_ClosedLoopDrivingFunctionalArchitecture::CameraPosition;" in code
    rig_doc = _doc("part def SimulatedSensorRig")
    for word in ("cb50764b", "configs/calibration", "camera_slots.py", "intrinsic", "camera-to-reference",
                 "principal point", "REQ-DRIVING-005", "phase 10", "curvature rule"):
        assert word in rig_doc, word
    assert "nuPlan" in rig_doc and "KITScenes" in rig_doc, "the two released profiles; the pin picks one"
    assert not re.search(r"\b\d{3,4}\s*(px|pixels|mm|°)", rig_doc), "no profile number before the checkpoint is pinned"
    motion_doc = _doc("part def SimulatedEgoMotionSource")
    for word in ("ground truth", "ASM-DRIVING-004", "vehicle state", "REQ-DRIVING-030"):
        assert word in motion_doc, word
    assert "detection" in rig_doc and "DE4SDV_VehicleSensingBoundary" in rig_doc, \
        "the product line's camera is a detection camera: it does not type these"
    assert re.search(r"\bdependency\s+\w+\s+from\s+SimulatedSensorRig\s+to\s+VehicleSensingAssembly\s*;", code)
    assert "private import DE4SDV_VehicleSensingBoundary::VehicleSensingAssembly;" in code
    server_doc = _doc("part def CARLASimulationServer")
    assert "sensor rig" in server_doc or "sensorRig" in server_doc


def _owned(body: str) -> list[tuple[str, str]]:
    return re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M)


def _ports(body: str) -> dict[str, str]:
    return dict(re.findall(r"^\s*port\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M))


def test_the_three_hosts_own_their_platform_layers_the_software_and_the_context_realizations():
    """Owner decision of 2026-11-09: three hosts. The S-CORE host nests no VM and renders nothing; the simulator
    renders on its own card; the guest host carries KVM and nothing of the driving system."""
    code = _code()
    host = _body_of_definition(HOST)
    assert _owned(host) == [("os", "LinuxPlatform"), ("drivingSoftware", REALIZATION),
                            ("routeProvider", "ScenarioRouteProvider")]
    assert "scoreServices" not in host, "the realization owns the S-CORE services"
    assert "hypervisor" not in host and "carlaServer" not in host
    assert _named_connections(host) == HOST_CONNECTIONS and len(_connections(host)) == len(HOST_CONNECTIONS)
    assert _ports(host) == HOST_PORTS
    simulator = _body_of_definition(SIMULATOR_HOST)
    assert _owned(simulator) == [("os", "LinuxPlatform"), ("carlaServer", "CARLASimulationServer")]
    assert (_named_connections(simulator) == SIMULATOR_HOST_CONNECTIONS
            and len(_connections(simulator)) == len(SIMULATOR_HOST_CONNECTIONS))
    assert _ports(simulator) == SIMULATOR_HOST_PORTS
    into_server = [name for name, (_, target) in SIMULATOR_HOST_CONNECTIONS.items() if target.startswith("carlaServer.")]
    assert into_server == ["vehicleControlDelegation"], "the vehicle control is the only thing the simulator receives"
    guest_host = _body_of_definition(GUEST_HOST)
    assert _owned(guest_host) == [("os", "LinuxPlatform"), ("hypervisor", "KVMHypervisor")]
    assert _ports(guest_host) == {} and not _connections(guest_host)
    for body in (host, simulator, guest_host):
        assert _binds(body) == set(), "both ends of each delegation are exposed, so a connection draws as an edge"
        assert "flow" not in body, "flows between these ports were not drawn (six licensed runs)"
    for layer in ("LinuxPlatform", "KVMHypervisor", "EclipseSCORE", "AndroidHLOS", "AndroidSDVMiddleware",
                  "OSHypervisorInterface"):
        assert f"private import DE4SDV_SDVPlatformStack::{layer};" in code, layer
    # the navigation of phase 2 is realized on the S-CORE host, not on the AAOS guest: the context-role decision holds
    assert re.search(r"\bpart\s+def\s+ScenarioRouteProvider\s*:>\s*NavigationSystem\s*\{", code)
    route_doc = _doc("part def ScenarioRouteProvider :> NavigationSystem")
    assert "System 2" in route_doc and "2026-11-02" in route_doc
    carla_doc = _doc("part def CARLASimulationServer")
    for phrase in ("System 2", "synchronous mode", "pacer", "no element of the loop ticks the world",
                   "never waits for a plan", "decision 3"):
        assert phrase in carla_doc, phrase
    for definition, phrases in ((HOST, ("2026-11-09", "S-CORE host", "RTX PRO 6000", "nests no VM")),
                                (SIMULATOR_HOST, ("2026-11-09", "its own GPU", "NVENC", "warm-up lap", "bench network")),
                                (GUEST_HOST, ("2026-11-09", "KVM", "VXLAN", "192.168.98.1"))):
        doc = _doc(f"part def {definition}")
        for phrase in phrases:
            assert phrase in doc, (definition, phrase)


def test_the_guests_carry_the_observation_path_and_the_state_crosses_the_vxlan_segment_and_the_vms():
    code = _code()
    core = _body_of_definition("AAOSSDVCoreGuest")
    assert re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", core, re.M) == [("os", "AndroidHLOS"),
                                                                        ("sdvMiddleware", "AndroidSDVMiddleware")]
    # the SDV Core boundary model is referenced, never owned: the platform stack owns the guest (2026-10-25)
    assert re.search(r"^\s*ref\s+part\s+sdvCore\s*:\s*SDVCoreBoundary\s*;", core, re.M)
    assert _binds(core) == SDV_CORE_GUEST_BINDS
    assert set(_connections(core)) == SDV_CORE_GUEST_CONNECTIONS
    assert dict(re.findall(r"^\s*port\s+(\w+)\s*:\s*(\w+)\s*;", core, re.M)) == {"someIpIn": "OperationalStateIn",
                                                                                 "topicOut": "DataTunnelPort"}
    hmi = _body_of_definition("AAOSIVIGuest")
    assert re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*[;{]", hmi, re.M) == [
        ("os", "AndroidHLOS"), ("sdvGateway", "SDVGatewayOnIVIBoundary"), ("stateObserver", "DrivingStateObserverApplication")]
    assert set(_connections(hmi)) == HMI_GUEST_CONNECTIONS and _binds(hmi) == HMI_GUEST_BINDS
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
        ("linuxHost", HOST), ("simulatorHost", SIMULATOR_HOST), ("guestHost", GUEST_HOST),
        ("sdvCoreGuest", "AAOSSDVCoreGuest"), ("hmiGuest", "AAOSIVIGuest")]
    assert _named_connections(system) == SYSTEM_CONNECTIONS and "flow" not in system and _binds(system) == set()
    into_simulator = [name for name, (_, target) in SYSTEM_CONNECTIONS.items() if target.startswith("simulatorHost.")]
    assert into_simulator == ["vehicleControlOverBenchNetwork"], "into the simulator goes the vehicle control and nothing else"
    assert not [name for name, (source, target) in SYSTEM_CONNECTIONS.items()
                if source.startswith(("sdvCoreGuest.", "hmiGuest.")) and not target.startswith("hmiGuest.")], "nothing back"
    interfaces = re.findall(r"\binterface\s+(\w+)\s*:\s*OSHypervisorInterface\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*;", system)
    assert interfaces == [("sdvCoreGuestUnderKVM", "sdvCoreGuest.os.hypervisorPort", "guestHost.hypervisor.guestPort"),
                          ("hmiGuestUnderKVM", "hmiGuest.os.hypervisorPort", "guestHost.hypervisor.guestPort")]
    vxlan_doc = _flat(re.search(r"connection operationalStateOverSOMEIPAcrossVXLANSegment[^{]*\{\s*doc\s*/\*(.*?)\*/",
                                _raw(), re.S).group(1))
    for phrase in ("VXLAN", "someipd", "guest images unchanged"):
        assert phrase in vxlan_doc, phrase
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
    actuation = record("MAP-DRIVING-ACTUATION-STATE")
    semantic_source = re.search(r'semanticSource = "([^"]*)"', actuation).group(1)
    assert semantic_source.endswith("a system state, no vehicle signal"), "what the actuation state is, said where the method reads it"
    assert "REQ-DRIVING-028" in semantic_source and "REQ-DRIVING-029" in actuation
    assert "GAP-DRIVING-005" not in _code(), "retired by the amendment the owner decided on 2026-11-06"
    assert "curvature" in record("MAP-DRIVING-EGO-MOTION"), "the fourth history input is given as zero, not a VSS signal"
    assert "Vehicle_ADAS_Driving_Command_Acceleration" in record("MAP-DRIVING-COMMAND")
    assert "REQ-DRIVING-014" in record("MAP-DRIVING-COMMAND")
    assert "VehicleControl" in record("MAP-DRIVING-VEHICLE-CONTROL") and "REQ-DRIVING-028" in record("MAP-DRIVING-VEHICLE-CONTROL")
    state = record("MAP-DRIVING-OPERATIONAL-STATE")
    for hop in ("gatewayd", "someipd", "SOME/IP", "Data Tunnel", "VSIDL", "REQ-DRIVING-017"):
        assert hop in state, hop
    assert "PyTorch" in record("MAP-DRIVING-PLAN") and "ONNX" not in record("MAP-DRIVING-PLAN")


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
    # retired and renamed on the amendment of 2026-11-09: no record, no reference left in the code
    for short, name in RETIRED.items():
        assert short not in code and name not in raw, short
    for name in RENAMED_AWAY:
        assert name not in raw, name


def test_the_input_activity_gives_the_checkpoint_yaw_rate_and_curvature_as_zero():
    # The history-mask decision of 2026-11-09 (GAP-DRIVING-010): no text of the realization may still say the
    # agent derives the curvature history the checkpoint takes.
    raw = _raw()
    for gone in ("derives\n     * the curvature from yaw rate and speed", "derives the curvature from yaw rate and speed",
                 "yawRate * pi / 180", "curvature = yawRate_rad / speed_mps",
                 "The curvature history the checkpoint takes is derived", "The\n       * curvature history is derived."):
        assert gone not in raw, gone
    assert "gives the checkpoint the history's yaw rate and curvature as zero" in _flat(raw)
    gap = braced_body(_code(), "part <'GAP-DRIVING-010'>")
    assert "attribute :>> disposition = LifecycleDisposition::accepted;" in gap, "a known limit the baseline keeps visible"


def test_the_history_gap_hands_the_junction_to_the_route_gap():
    # The route decision of 2026-11-10: the checkpoint takes no turn from the route with the zeroed history or with
    # the recorded one (GAP-DRIVING-011), so GAP-DRIVING-010 no longer reads the missed turn as a consequence of the
    # history mask.
    doc = _doc("part <'GAP-DRIVING-010'> gapClosedLoopHistoryFeedback : IncrementGap")
    for statement in HISTORY_GAP_STATEMENTS:
        assert statement in doc, statement
    for gone in ("the route does not yet steer", "trained with, and the route"):
        assert gone not in doc, gone


def test_the_history_gap_claims_no_lane_keeping_the_readiness_probe_did_not_show():
    # The readiness probe's own record: with yaw rate and curvature zero the vehicle stayed in its lane for 12 s while
    # drifting steadily to one side, with no correction back, and its speed went to zero and back every 4 to 5 s.
    # It did not keep its lane, and it made no single stop at a traffic light.
    doc = _doc("part <'GAP-DRIVING-010'> gapClosedLoopHistoryFeedback : IncrementGap")
    assert "drifted steadily to one side without steering back" in doc
    for gone in ("kept its lane", "keeps its lane", "traffic light", "stopped and restarted"):
        assert gone not in doc, gone


def test_each_upstream_source_a_gap_cites_is_listed_in_the_provenance_record():
    # upstream.md holds the provenance of what the model takes from upstream: a gap that cites an upstream file at
    # the pin names it there too (GAP-DRIVING-010 its closed-loop results, GAP-DRIVING-011 the model code and the
    # evaluation it reads).
    provenance = (DRIVING / "upstream.md").read_text(encoding="utf-8")
    pin = "cb50764b8250a3c44ee5b79b87ba02c5a83b0c91"
    assert pin in PINS, "the AutoE2E pin the package records"
    cited = set()
    for short, name in GAPS.items():
        doc = _doc(f"part <'{short}'> {name} : IncrementGap")
        cited |= set(re.findall(r"\(([A-Za-z_]+(?:/[A-Za-z0-9_.-]+)+\.(?:py|md))\)", doc))
    assert {"experiment/closed-loop/RESULTS.md", "Model/model_components/reactive_e2e.py",
            "Academic_Paper/AutoE2E_Route_Conditioned/paper_en.md"} <= cited, cited
    for path in sorted(cited):
        assert f"/{pin}/{path})" in provenance, path


def test_the_route_gap_records_that_the_checkpoint_takes_no_turn_from_the_route():
    # The route decision of 2026-11-10 (GAP-DRIVING-011): the scenario's route needs no branch choice, and the model
    # records the limit as one gap, accepted, right after the history gap.
    raw = _raw()
    following = re.findall(r"\bpart\s+<'([A-Z]+-DRIVING-\d{3})'>", raw[raw.index("part <'GAP-DRIVING-010'>"):])
    assert following[:2] == ["GAP-DRIVING-010", "GAP-DRIVING-011"], following
    gap = braced_body(_code(), "part <'GAP-DRIVING-011'>")
    assert "attribute :>> disposition = LifecycleDisposition::accepted;" in gap, "a known limit the baseline keeps visible"
    doc = _doc("part <'GAP-DRIVING-011'> gapRouteChoosesNoBranch : IncrementGap")
    for statement in ROUTE_GAP_STATEMENTS:
        assert statement in doc, statement
    # the route the bench drives is bench configuration: the gap names no map, route or spawn point of it
    assert not re.search(r"\bTown\d|\bspawn", doc, re.I), doc
    assert not [word for word in CLAIM_WORDS if word in doc.lower()]


def test_the_lane_gap_records_that_the_checkpoint_keeps_no_lane():
    # The lane decision of 2026-11-10 (GAP-DRIVING-012): a measured negative result, accepted, right after the route
    # gap. The run's route and spawn point are bench configuration and stay out of the model.
    raw = _raw()
    following = re.findall(r"\bpart\s+<'([A-Z]+-DRIVING-\d{3})'>", raw[raw.index("part <'GAP-DRIVING-010'>"):])
    assert following[:3] == ["GAP-DRIVING-010", "GAP-DRIVING-011", "GAP-DRIVING-012"], following
    gap = braced_body(_code(), "part <'GAP-DRIVING-012'>")
    assert "attribute :>> disposition = LifecycleDisposition::accepted;" in gap, "a known limit the baseline keeps visible"
    doc = _doc("part <'GAP-DRIVING-012'> gapPlansKeepNoLane : IncrementGap")
    for statement in LANE_GAP_STATEMENTS:
        assert statement in doc, statement
    assert not re.search(r"\bTown\d|\bspawn", doc, re.I), doc
    assert not [word for word in CLAIM_WORDS if word in doc.lower()]
    for gone in ("kept its lane", "the vehicle keeps its lane", "lane keeping works", "about 2 degrees at 10 m ahead",
                 "The vehicle was in the next lane after about 11 s.", "Bench-side causes were checked:",
                 "opposite sides in the two runs"):
        assert gone not in doc, gone


def test_the_deadline_gap_records_that_req_013_is_narrowly_not_met():
    # The deadline decision of 2026-11-10 (GAP-DRIVING-013): REQ-DRIVING-013 recorded as narrowly not met with its
    # measured margin, accepted, right after the lane gap. The limit itself does not move.
    raw = _raw()
    following = re.findall(r"\bpart\s+<'([A-Z]+-DRIVING-\d{3})'>", raw[raw.index("part <'GAP-DRIVING-010'>"):])
    assert following[:4] == ["GAP-DRIVING-010", "GAP-DRIVING-011", "GAP-DRIVING-012", "GAP-DRIVING-013"], following
    gap = braced_body(_code(), "part <'GAP-DRIVING-013'>")
    assert "attribute :>> disposition = LifecycleDisposition::accepted;" in gap, "a known limit the baseline keeps visible"
    doc = _doc("part <'GAP-DRIVING-013'> gapPlanningPeriodNarrowlyMissed : IncrementGap")
    for statement in DEADLINE_GAP_STATEMENTS:
        assert statement in doc, statement
    assert not re.search(r"\bTown\d|\bspawn", doc, re.I), doc
    assert not [word for word in CLAIM_WORDS if word in doc.lower()]
    for gone in ("REQ-DRIVING-013 is met", "meets REQ-DRIVING-013", "lower-precision", "no plan was more than 2 ms late",
                 "In the run of the closed-loop scenario on a straight route"):
        assert gone not in doc, gone
    # the probe's statement in the package head stays, with the verification outcome next to it
    head = _flat(raw[:raw.index("package " + PACKAGE)])
    assert ("met REQ-DRIVING-013's budget in the probe at wall-clock pace, so the increment needed no redirect then: "
            "the charter's hold/redirect condition was not met in the probe. The verification runs later missed the "
            "budget narrowly, and the owner accepted the miss (GAP-DRIVING-013).") in head
    assert "the charter's hold/redirect condition is not met." not in head


def test_the_ego_motion_mapping_says_the_history_is_worked_out_from_the_poses():
    # The owner decision of 2026-11-10 on VC-DRIVING-008: the checkpoint's history takes speed and acceleration from
    # the vehicle's poses the source's way, not speed / 3.6 of the published sample; the record lists the transform
    # among the fields it reads.
    record = braced_body(_raw(), "item <'MAP-DRIVING-EGO-MOTION'>")
    def value(name):
        return re.search(rf'{name} = "([^"]*)"', record).group(1)
    assert value("semanticSource").startswith(
        "the motion state of the ego vehicle as the simulator reports it (its transform, velocity and acceleration "
        "vectors, angular velocity)")
    assert value("softwareContractMessage").startswith(
        "in: transform, velocity, acceleration and angular velocity of the ego vehicle per world snapshot, candidate;")
    assert value("softwareContractField").startswith(
        "in: the transform's world matrix, velocity.x/y, acceleration.x/y, angular_velocity.z, snapshot timestamp,")
    assert value("dataTypeAndUnit").startswith("in: float32 m (the transform), m/s, m/s^2, deg/s, simulation seconds;")
    rule = value("transformationRule")
    assert rule.startswith("speed = |velocity| * 3.6 as the VSS km/h value; the checkpoint's history takes speed and "
                           "acceleration worked out the source's way from the transforms, moved to the origin of the "
                           "camera rig, of the 66 steps that end at the step (REQ-DRIVING-008),")
    assert "the checkpoint input takes speed / 3.6" not in record
    assert ("and its speed and acceleration worked out from the vehicle's poses, not from the sample "
            "(REQ-DRIVING-008)") in _flat(record)


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


def test_the_amendment_records_the_owner_decisions_of_the_readiness_probes():
    raw = _raw()
    head = _flat(raw[:raw.index("package " + PACKAGE)])
    for phrase in AMENDMENT_PHRASES:
        assert phrase in head, phrase
    assert "Python stays in System 2" not in raw, "the planner runs PyTorch in the agent's process (decision 4)"
    assert "TensorRT on the NVIDIA host" not in raw and "over the ONNX export" not in raw
    agent = _doc(f"part def {AGENT}")
    for phrase in ("Rust", "C++ libraries", "event trigger", "newest frame", "skipped"):
        assert phrase in agent, phrase
    inference = _doc("part def PlanInferenceActivity :> PhysicalAllocationElement")
    for phrase in ("PyTorch", "REQ-DRIVING-035", "REQ-DRIVING-033", "cuDNN", "capture-safe preprocessing"):
        assert phrase in inference, phrase
    assert "ONNX" not in inference and "TensorRT" not in inference
    conditioning = _doc("part def InputConditioningActivity :> PhysicalAllocationElement")
    assert "frame index" in conditioning and "100 ms" in conditioning
    launch = _doc("part launchManager", braced_body(raw, "part scoreServices : EclipseSCORE"))
    for phrase in ("as root", "/tmp/mw_com_lola", "LmControlService"):
        assert phrase in launch, phrase


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
        assert "filter not (@ SysML::AllocationUsage);" in view, "SysIDE draws the package's allocations otherwise (run 42253633791: eight boxes)"
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
    assert "filter not (@ SysML::InterfaceUsage);" in context, "the hypervisor interfaces span levels"
    assert "filter not (@ SysML::BindingConnectorAsUsage);" in context, "nine binds drew as boxes with two ends (run 42255511098)"
    assert "ConnectionUsage" not in context, "the exchanges are connections"
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
    declarations += [f"part def {AGENT}", f"part def {REALIZATION} :> {IDENTITY}", f"part def {HOST}", f"part def {SYSTEM}",
                     f"part def {SIMULATOR_HOST}", f"part def {GUEST_HOST}"]
    for declaration in declarations:
        doc = _doc(declaration)
        found = [word for word in CLAIM_WORDS if word in doc.lower()]
        assert not found, (declaration, found)
    assert not re.search(r"\b(realizedBy|deployedTo|validatedBy|constrainedBy)\b", re.sub(r'"(?:[^"\\]|\\.)*"', '""', _code()))


def test_the_allocation_file_is_governed_with_its_six_endpoint_definitions():
    import test_trace_allocation_completeness as trace

    assert trace.ALLOCATION_FILES[trace.DRIVING_P] == (
        (trace.DRIVING_P, trace.DRIVING_L), {(trace.LOGICAL, trace.PHYSICAL): 8},
        {"SystemToSoftwareSignalMappingCandidate": 9}, (trace.LOGICAL, trace.PHYSICAL))
    assert trace.GOVERNED[trace.DRIVING_P] == (trace.PHYSICAL, set(ELEMENT_DEFINITIONS))
    assert trace.DRIVING_P in trace.LINEAGE_FILES
    assert trace.NOT_ENDPOINTS[trace.DRIVING_P] == {SYSTEM, HOST, REALIZATION, AGENT, "CARLASimulationServer",
                                                    "ScenarioRouteProvider", "AAOSSDVCoreGuest", "AAOSIVIGuest",
                                                    SIMULATOR_HOST, GUEST_HOST}


def test_the_guide_describes_phase_8_and_names_the_next_work():
    guide = GUIDE.read_text(encoding="utf-8")
    assert "## Physical and software realization (Phase 8)" in guide
    assert "closed_loop_driving_physical_software_realization.sysml" in guide
    flat = " ".join(guide.split())
    for word in ("FEO", "actuation adapter", "state publisher", "gatewayd", "ONNX", "v0.10.0", "v1.0.5",
                 "GAP-DRIVING-005", "reqPlansAndCommandsOverSCOREReading", "KUKSA", "two clocks side by side",
                 "simulated sensor rig", "the vehicle control and nothing else", "2026-11-06",
                 "actuation state", "MAP-DRIVING-ACTUATION-STATE", "ASM-DRIVING-004",
                 "rig profile", "ground truth", "ISQ", "CameraPosition", "three hosts", "readiness probes",
                 "2026-11-09", "PyTorch", "event trigger", "VXLAN", "NVENC", "warm-up lap"):
        assert word in flat, word
    # the count follows the gap records of the realization, GAP-DRIVING-010 to GAP-DRIVING-013 included
    count = f"{NUMBER_WORDS[len(ASSUMPTIONS)].capitalize()} assumptions and {NUMBER_WORDS[len(GAPS)]} gaps"
    assert count in flat, count
    assert "Four of the gaps, GAP-DRIVING-010 to GAP-DRIVING-013, are accepted as known limits" in flat
    assert "Three of the gaps, GAP-DRIVING-010, GAP-DRIVING-011 and GAP-DRIVING-012" not in flat, "GAP-DRIVING-013 too"
    assert "GAP-DRIVING-008" not in guide and "Three assumptions and seven gaps" not in flat
    assert "Four assumptions and four gaps" not in flat, "GAP-DRIVING-010 to GAP-DRIVING-012 count too"
    assert "Two of the gaps, GAP-DRIVING-010 and GAP-DRIVING-011" not in flat, "GAP-DRIVING-012 is accepted too"
    assert "follow-up PR carries the amendment" not in flat, "the amendment landed"
    assert "The next work is **Phase 8**" not in guide and "The next work is **Phase 9**" not in guide
    assert re.search(r"The next work is (\*\*Phase 1[01]\*\*|the \*\*second slice of Phase 10\*\*)", guide), "phases 8 and 9 landed"
    assert "tests/test_closed_loop_driving_physical_software_realization.py" in guide


def test_the_guide_explains_the_route_gap_right_after_the_history_gap():
    # The route decision of 2026-11-10 for contributors: what was measured, what it means for the scenario's route,
    # and what would close the gap, in the paragraph after the one on GAP-DRIVING-010.
    paragraphs = [" ".join(paragraph.split()) for paragraph in GUIDE.read_text(encoding="utf-8").split("\n\n")]
    history = next(index for index, paragraph in enumerate(paragraphs) if "that GAP-DRIVING-010 records" in paragraph)
    route = paragraphs[history + 1]
    for phrase in ("GAP-DRIVING-011 records a separate limit", "owner's decision of 2026-11-10",
                   "the pinned checkpoint takes no turn from the route", "at most 0.02 degrees", "about 60",
                   "REQ-DRIVING-008", "the cameras blanked and no map", "the scenario's route needs no branch choice",
                   "every junction on it is passed straight on", "only lane-follow and straight road options",
                   "Keep it so when you change the route", "the evidence claims no route following at junctions",
                   "a checkpoint whose plans take the turn from the route"):
        assert phrase in route, phrase


def test_the_guide_records_the_deadline_gap_with_the_probe_that_met_the_budget():
    # The deadline decision of 2026-11-10 for contributors, where the guide says what the readiness probe found: the
    # probe met the budget, the verification runs missed it narrowly, and the limit stays.
    flat = " ".join(GUIDE.read_text(encoding="utf-8").split())
    probe = ("With the simulator on its own card the planner met REQ-DRIVING-013's budget at wall-clock pace in the "
             "probe, so the increment needed no redirect.")
    assert probe in flat
    after = flat[flat.index(probe):]
    for phrase in ("**GAP-DRIVING-013**, accepted on the owner's decision of 2026-11-10, records that REQ-DRIVING-013 "
                   "is narrowly not met.", "In three runs on the straight route 97.5 to 99.2 % of the plans came in "
                   "time", "two in a row missed", "the latest by 7.7 ms", "99.0 %", "standing for most of the window",
                   "about 90 ms of the 100", "The limit stays at 100 ms."):
        assert phrase in after[:900], phrase
    assert "so the increment needs no redirect." not in flat
    assert "none by more than 2 ms" not in flat, "a later run's latest plan was 7.7 ms late"


def test_the_guide_says_the_history_is_worked_out_from_the_positions():
    # The owner decision of 2026-11-10 on VC-DRIVING-008, in the requirement summary and the Phase 6 description.
    flat = " ".join(GUIDE.read_text(encoding="utf-8").split())
    assert ("64 motion samples 100 ms apart before the step, worked out from the vehicle's positions, with yaw rate "
            "and curvature given as zero (008)") in flat
    assert ("each with its sample time, and the vehicle's position at each, from which the checkpoint's history is "
            "worked out the source's way (REQ-DRIVING-008).") in flat


def test_the_guide_explains_the_lane_gap_right_after_the_route_gap():
    # The lane decision of 2026-11-10 for contributors: what the straight-route run showed, why no history setting
    # keeps the lane, what the review and the evidence take from it, and what would close the gap.
    paragraphs = [" ".join(paragraph.split()) for paragraph in GUIDE.read_text(encoding="utf-8").split("\n\n")]
    route = next(index for index, paragraph in enumerate(paragraphs) if "GAP-DRIVING-011 records a separate limit" in paragraph)
    lane = paragraphs[route + 1]
    for phrase in ("GAP-DRIVING-012 records a third limit", "owner's decision of 2026-11-10",
                   "the pinned checkpoint does not keep the vehicle in its lane", "about 2 degrees", "twice its angle",
                   "the 35 degree command limit", "the vehicle's 70 degree maximum", "about 11 s", "about 15 s",
                   "434 plans", "2 pointed back", "REQ-DRIVING-008", "GAP-DRIVING-010", "so no setting keeps the lane",
                   "SC-DRIVING-005", "claims neither lane keeping nor driving along the route",
                   "a checkpoint that keeps its lane in a closed loop"):
        assert phrase in lane, phrase
    assert "of 375 plans" not in lane, "the numbers after the steering correction"
