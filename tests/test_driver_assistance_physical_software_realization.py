"""Content pins for the driver-assistance physical/software realization (phase 8), not semantic validation.

INC-DRIVING-002 phase 8 places the four logical elements of phase 7 on software: the candidate, VisionPilot at
014e0e7a, stays one process and becomes an Eclipse S-CORE application through a DE4SDV S-CORE interface module (the
owner's choice of 2026-11-15); the identity recorder is an S-CORE application of its own beside it. Method Check holds
the DefinePhysicalRealization rule (each logical element allocated to a physical element; advisory, each physical
element carries one, each crossing has a signal mapping and each record names its semantic source). These pins hold
what the phase settled on top of it:

- topology: two upstream modules (the perception and fusion, the safety guardian's planner) and three DE4SDV modules
  (camera interface, vehicle interface, warning request publisher) of one process, plus the recording application,
  are the six physical elements; the warning requester and the driving commander share the planner
  (gapNoSeparateEmergencyFunction);
- the S-CORE path and the AAOS SDV stay outside the candidate: the actuation adapter, the gateway processes, the
  guests and the warning presentation are context realizations, typed by no kernel class;
- the actuation adapter rejects a detected failed command and applies nothing in its place, and has no stop response;
- the clock and the three hosts are INC-DRIVING-001's decisions of 2026-11-08 and 2026-11-09, carried over;
- the simulator receives CARLA's Ackermann control, typed by the fields of the 0.9.16 API reference;
- VSS only at the ports: the command, the speed and the warning request; the 0.2 s share of REQ-DRIVING-042 is divided
  0.1 s for the path and 0.1 s for the presentation;
- the two path requirements are carried by a dependency from the publishing definitions;
- one view per SAF question of the phase: the structure as a tree, the logical-to-physical mapping as a matrix, the
  S-CORE path as an interconnection of the S-CORE host, the two phase 1 concerns of the Physical domain framed there.
"""

import re
from pathlib import Path

import pytest

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
MODEL = DRIVING / "driver_assistance_physical_software_realization.sysml"
FRAMING = DRIVING / "driver_assistance_framing.sysml"
EXTENSIONS = ROOT / "textual-notation-of-model/libraries/covesa-vss-sysmlv2/DE4SDV_VSS_Extensions.sysml"
GUIDE = ROOT / "docs/guides/driver-assistance-increment.md"
UPSTREAM = DRIVING / "upstream.md"
PACKAGE = "DE4SDV_DriverAssistancePhysicalSoftwareRealization"
LOGICAL_PACKAGE = "DE4SDV_DriverAssistanceLogicalArchitecture"
LOGICAL_SYSTEM = "DriverAssistanceLogicalSystem"
IDENTITY = "DriverAssistanceSystem"
SYSTEM = "DriverAssistancePhysicalSystem"
SYSTEM_USAGE = "driverAssistancePhysicalSystem"
HOST = "DriverAssistanceSCOREHost"
HOST_USAGE = "driverAssistanceSCOREHost"
SIMULATOR_HOST = "DriverAssistanceSimulatorHost"
#: the guest host is INC-DRIVING-001's definition, imported: it owns Linux and KVM and nothing of either increment
GUEST_HOST = "AAOSGuestHost"
REALIZATION = "DriverAssistanceSoftwareRealization"
APPLICATION = "VisionPilotSCOREApplication"
ADAPTER = "DrivingCommandActuationAdapter"
PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"
SOFTWARE = f"{SYSTEM_USAGE}::scoreHost::assistanceSoftware"
#: the same software realization as a feature chain: a mapping's port target is written through the usage, since the
#: ports are declared on the definitions and a qualified name would resolve to the definition's port
SOFTWARE_CHAIN = f"{SYSTEM_USAGE}.scoreHost.assistanceSoftware"

#: The physical element definitions -> (usage path below the software realization, the logical elements it carries).
ELEMENT_DEFINITIONS = {
    "CandidateIdentityRecordingApplication": ("identityRecording", ("identityRecorder",)),
    "SCORECameraInterface": ("visionPilotApplication::cameraInterface", ("vehicleAheadAssessor",)),
    "VisionPilotPerceptionAndFusion": ("visionPilotApplication::perceptionAndFusion", ("vehicleAheadAssessor",)),
    "VisionPilotSafetyGuardianPlanner": ("visionPilotApplication::safetyGuardianPlanner",
                                         ("warningRequester", "drivingCommander")),
    "SCOREVehicleInterface": ("visionPilotApplication::vehicleInterface", ("drivingCommander",)),
    "SCOREWarningRequestPublisher": ("visionPilotApplication::warningRequestPublisher", ("warningRequester",)),
}
LOGICAL_ELEMENTS = ("identityRecorder", "vehicleAheadAssessor", "warningRequester", "drivingCommander")
#: allocation name -> (logical element, physical usage path below the software realization)
ALLOCATIONS = {
    "recorderToIdentityRecording": ("identityRecorder", "identityRecording"),
    "assessorToCameraInterface": ("vehicleAheadAssessor", "visionPilotApplication::cameraInterface"),
    "assessorToPerceptionAndFusion": ("vehicleAheadAssessor", "visionPilotApplication::perceptionAndFusion"),
    "requesterToSafetyGuardianPlanner": ("warningRequester", "visionPilotApplication::safetyGuardianPlanner"),
    "requesterToWarningRequestPublisher": ("warningRequester", "visionPilotApplication::warningRequestPublisher"),
    "commanderToSafetyGuardianPlanner": ("drivingCommander", "visionPilotApplication::safetyGuardianPlanner"),
    "commanderToVehicleInterface": ("drivingCommander", "visionPilotApplication::vehicleInterface"),
}

#: Each definition -> its ports.
PORTS = {
    "CandidateIdentityRecordingApplication": {"candidateRecordOut": "CandidateRecordEventOut"},
    "SCORECameraInterface": {"frontCameraImageIn": "FrontCameraStreamIn", "imageOut": "FrontCameraStreamOut"},
    "VisionPilotPerceptionAndFusion": {"imageIn": "FrontCameraStreamIn", "assessmentOut": "AssessmentResultOut"},
    "VisionPilotSafetyGuardianPlanner": {"assessmentIn": "AssessmentResultIn", "vehicleSpeedIn": "VehicleSpeedSampleIn",
                                         "planOut": "PlannedCommandOut", "plannedWarningsOut": "PlannedWarningsOut"},
    "SCOREVehicleInterface": {"vehicleSpeedIn": "VehicleSpeedSampleIn", "vehicleSpeedOut": "VehicleSpeedSampleOut",
                              "planIn": "PlannedCommandIn", "candidateRecordIn": "CandidateRecordEventIn",
                              "drivingCommandOut": "DrivingCommandEventOut"},
    "SCOREWarningRequestPublisher": {"plannedWarningsIn": "PlannedWarningsIn",
                                     "warningRequestOut": "WarningRequestEventOut"},
    APPLICATION: {"frontCameraImageIn": "FrontCameraStreamIn", "vehicleSpeedIn": "VehicleSpeedSampleIn",
                  "candidateRecordIn": "CandidateRecordEventIn", "drivingCommandOut": "DrivingCommandEventOut",
                  "warningRequestOut": "WarningRequestEventOut"},
    REALIZATION: {"frontCameraImageIn": "FrontCameraStreamIn", "vehicleSpeedIn": "VehicleSpeedSampleIn",
                  "drivingCommandOut": "DrivingCommandEventOut", "warningRequestOut": "WarningRequestEventOut"},
    ADAPTER: {"drivingCommandIn": "DrivingCommandEventIn", "simulationClockIn": "SimulationClockIn",
              "vehicleSpeedIn": "VehicleSpeedSampleIn", "ackermannControlOut": "AckermannControlOut"},
    "DriverAssistanceSimulationServer": {"frontCameraStreamOut": "FrontCameraStreamOut",
                                         "vehicleSpeedOut": "VehicleSpeedSampleOut",
                                         "simulationClockOut": "SimulationClockOut",
                                         "ackermannControlIn": "AckermannControlIn"},
    HOST: {"frontCameraImageIn": "FrontCameraStreamIn", "vehicleSpeedIn": "VehicleSpeedSampleIn",
           "simulationClockIn": "SimulationClockIn", "adapterVehicleSpeedIn": "VehicleSpeedSampleIn",
           "ackermannControlOut": "AckermannControlOut", "warningRequestOut": "WarningRequestEventOut"},
    SIMULATOR_HOST: {"frontCameraStreamOut": "FrontCameraStreamOut", "vehicleSpeedOut": "VehicleSpeedSampleOut",
                     "simulationClockOut": "SimulationClockOut", "ackermannControlIn": "AckermannControlIn"},
    "DriverAssistanceSDVCoreGuest": {"someIpIn": "WarningRequestEventIn", "topicOut": "DataTunnelPort"},
    "DriverAssistanceIVIGuest": {"topicIn": "DataTunnelPort"},
    "CollisionWarningPresentationApplication": {"warningRequestIn": "WarningRequestEventIn"},
}
GATEWAY_PROCESSES = ("gatewayd", "someipd")
GATEWAY_PORTS = {"warningRequestIn": "WarningRequestEventIn", "warningRequestOut": "WarningRequestEventOut"}
#: port definition -> (direction, item, item type); one pair per item, whatever hop carries it
PORT_ITEMS = {
    "FrontCameraStreamOut": ("out", "frontCameraImage", "FrontCameraImage"),
    "FrontCameraStreamIn": ("in", "frontCameraImage", "FrontCameraImage"),
    "VehicleSpeedSampleOut": ("out", "vehicleSpeed", "VehicleSpeedSamplePayload"),
    "VehicleSpeedSampleIn": ("in", "vehicleSpeed", "VehicleSpeedSamplePayload"),
    "AssessmentResultOut": ("out", "assessment", "VehicleAheadAssessment"),
    "AssessmentResultIn": ("in", "assessment", "VehicleAheadAssessment"),
    "PlannedCommandOut": ("out", "plannedCommand", "DrivingCommand"),
    "PlannedCommandIn": ("in", "plannedCommand", "DrivingCommand"),
    "PlannedWarningsOut": ("out", "plannedWarnings", "PlannedWarnings"),
    "PlannedWarningsIn": ("in", "plannedWarnings", "PlannedWarnings"),
    "DrivingCommandEventOut": ("out", "drivingCommand", "DrivingCommandEventPayload"),
    "DrivingCommandEventIn": ("in", "drivingCommand", "DrivingCommandEventPayload"),
    "WarningRequestEventOut": ("out", "warningRequest", "WarningRequestEventPayload"),
    "WarningRequestEventIn": ("in", "warningRequest", "WarningRequestEventPayload"),
    "CandidateRecordEventOut": ("out", "candidateRecord", "CandidateIdentityRecord"),
    "CandidateRecordEventIn": ("in", "candidateRecord", "CandidateIdentityRecord"),
    "AckermannControlOut": ("out", "ackermannControl", "SimulatorAckermannControl"),
    "AckermannControlIn": ("in", "ackermannControl", "SimulatorAckermannControl"),
}
#: the payloads this phase types, each a realization of a phase 2 item -> (base item, attribute -> type)
PAYLOADS = {
    "VehicleSpeedSamplePayload": ("VehicleSpeed", {"speed": "Vehicle_Speed", "sampleTime": "Real"}),
    "DrivingCommandEventPayload": ("DrivingCommand", {
        "acceleration": "Vehicle_ADAS_Driving_Command_Acceleration",
        "steeringAngle": "Vehicle_ADAS_Driving_Command_SteeringAngle", "issueTime": "Real",
        "sequenceCount": "Natural", "checkValue": "Natural"}),
    "WarningRequestEventPayload": ("WarningRequest", {"requested": "Vehicle_ADAS_AEBS_DriverWarning_IsActive",
                                                      "issueTime": "Real"}),
}
#: the plan's warnings as the planner hands them to the publisher: a phase 8 item, not phase 7's warning state (R7)
PLANNED_WARNINGS = {"forwardCollisionWarning": "Boolean", "emergencyBraking": "Boolean"}
VSS_IMPORTS = {
    "Vehicle_Speed": "COVESA_VSS::SignalDefinitions",
    "Vehicle_ADAS_Driving_Command_Acceleration": "DE4SDV_VSS_Extensions",
    "Vehicle_ADAS_Driving_Command_SteeringAngle": "DE4SDV_VSS_Extensions",
    "Vehicle_ADAS_AEBS_DriverWarning_IsActive": "DE4SDV_VSS_Extensions",
}
#: The fields of carla.VehicleAckermannControl in the Python API reference of CARLA 0.9.16, in its order
ACKERMANN_FIELDS = [("steer", "Real"), ("steerSpeed", "Real"), ("speed", "Real"), ("acceleration", "Real"),
                    ("jerk", "Real")]

APPLICATION_PARTS = [("cameraInterface", "SCORECameraInterface"), ("perceptionAndFusion", "VisionPilotPerceptionAndFusion"),
                     ("safetyGuardianPlanner", "VisionPilotSafetyGuardianPlanner"),
                     ("vehicleInterface", "SCOREVehicleInterface"),
                     ("warningRequestPublisher", "SCOREWarningRequestPublisher")]
#: The delegations of the candidate's process are binds, as the precedent's realization binds its own ports: the
#: S-CORE path view draws them as edges between exposed ports.
APPLICATION_BINDS = {
    ("frontCameraImageIn", "cameraInterface.frontCameraImageIn"),
    ("vehicleSpeedIn", "vehicleInterface.vehicleSpeedIn"),
    ("candidateRecordIn", "vehicleInterface.candidateRecordIn"),
    ("drivingCommandOut", "vehicleInterface.drivingCommandOut"),
    ("warningRequestOut", "warningRequestPublisher.warningRequestOut"),
}
#: The hand-offs of the candidate's process, in the order of the loop.
APPLICATION_CONNECTIONS = {
    "imageHandOff": ("cameraInterface.imageOut", "perceptionAndFusion.imageIn"),
    "assessmentHandOff": ("perceptionAndFusion.assessmentOut", "safetyGuardianPlanner.assessmentIn"),
    "vehicleSpeedHandOff": ("vehicleInterface.vehicleSpeedOut", "safetyGuardianPlanner.vehicleSpeedIn"),
    "plannedCommandHandOff": ("safetyGuardianPlanner.planOut", "vehicleInterface.planIn"),
    "plannedWarningsHandOff": ("safetyGuardianPlanner.plannedWarningsOut",
                               "warningRequestPublisher.plannedWarningsIn"),
}
REALIZATION_BINDS = {
    ("frontCameraImageIn", "visionPilotApplication.frontCameraImageIn"),
    ("vehicleSpeedIn", "visionPilotApplication.vehicleSpeedIn"),
    ("drivingCommandOut", "visionPilotApplication.drivingCommandOut"),
    ("warningRequestOut", "visionPilotApplication.warningRequestOut"),
}
REALIZATION_CONNECTIONS = {
    "candidateRecordOverSCORECommunication": ("identityRecording.candidateRecordOut",
                                              "visionPilotApplication.candidateRecordIn"),
}
HOST_BINDS = {
    ("frontCameraImageIn", "assistanceSoftware.frontCameraImageIn"),
    ("vehicleSpeedIn", "assistanceSoftware.vehicleSpeedIn"),
    ("simulationClockIn", "actuationAdapter.simulationClockIn"),
    ("adapterVehicleSpeedIn", "actuationAdapter.vehicleSpeedIn"),
    ("ackermannControlOut", "actuationAdapter.ackermannControlOut"),
    ("warningRequestOut", "scoreServices.someipd.warningRequestOut"),
}
HOST_CONNECTIONS = {
    "drivingCommandOverSCORECommunication": ("assistanceSoftware.drivingCommandOut", "actuationAdapter.drivingCommandIn"),
    "warningRequestOverSCORECommunication": ("assistanceSoftware.warningRequestOut",
                                             "scoreServices.gatewayd.warningRequestIn"),
    "warningRequestOverGatewayIPC": ("scoreServices.gatewayd.warningRequestOut", "scoreServices.someipd.warningRequestIn"),
}
SIMULATOR_HOST_CONNECTIONS = {
    "frontCameraStreamDelegation": ("carlaServer.frontCameraStreamOut", "frontCameraStreamOut"),
    "vehicleSpeedDelegation": ("carlaServer.vehicleSpeedOut", "vehicleSpeedOut"),
    "simulationClockDelegation": ("carlaServer.simulationClockOut", "simulationClockOut"),
    "ackermannControlDelegation": ("ackermannControlIn", "carlaServer.ackermannControlIn"),
}
SYSTEM_CONNECTIONS = {
    "frontCameraStreamOverBenchNetwork": ("simulatorHost.frontCameraStreamOut", "scoreHost.frontCameraImageIn"),
    "vehicleSpeedOverBenchNetwork": ("simulatorHost.vehicleSpeedOut", "scoreHost.vehicleSpeedIn"),
    "vehicleSpeedToActuationOverBenchNetwork": ("simulatorHost.vehicleSpeedOut", "scoreHost.adapterVehicleSpeedIn"),
    "simulationClockOverBenchNetwork": ("simulatorHost.simulationClockOut", "scoreHost.simulationClockIn"),
    "ackermannControlOverBenchNetwork": ("scoreHost.ackermannControlOut", "simulatorHost.ackermannControlIn"),
    "warningRequestOverSOMEIPAcrossVXLANSegment": ("scoreHost.warningRequestOut", "sdvCoreGuest.someIpIn"),
    "warningRequestTopicOverDataTunnelAcrossVMs": ("sdvCoreGuest.topicOut", "iviGuest.topicIn"),
}
SDV_CORE_GUEST_BINDS = {("sdvCore", "sdvMiddleware"), ("someIpIn", "sdvCore.someIp.someIpPort"),
                        ("topicOut", "sdvCore.dataTunnel.topicSubscribePort")}
SDV_CORE_GUEST_CONNECTIONS = {("sdvCore.someIp.topicPublishOut", "sdvCore.dataTunnel.topicPublishPort")}
IVI_GUEST_BINDS = {("topicIn", "sdvGateway.dataTunnelPort")}
IVI_GUEST_CONNECTIONS = {("sdvGateway.clientPort", "warningPresentation.warningRequestIn")}

#: signal mapping -> (logical element, target port path below the software realization, record short name)
SIGNAL_MAPPINGS = {
    "cameraImageIngressMapping": ("vehicleAheadAssessor", "visionPilotApplication::cameraInterface::frontCameraImageIn",
                                  "MAP-DRIVING-DA-CAMERA-IMAGE"),
    "vehicleSpeedIngressMapping": ("drivingCommander", "visionPilotApplication::vehicleInterface::vehicleSpeedIn",
                                   "MAP-DRIVING-DA-VEHICLE-SPEED"),
    "vehicleAheadAssessmentMapping": ("vehicleAheadAssessor",
                                      "visionPilotApplication::perceptionAndFusion::assessmentOut",
                                      "MAP-DRIVING-DA-ASSESSMENT"),
    "plannedWarningsMapping": ("warningRequester",
                               "visionPilotApplication::safetyGuardianPlanner::plannedWarningsOut",
                               "MAP-DRIVING-DA-PLANNED-WARNINGS"),
    "plannedCommandMapping": ("drivingCommander", "visionPilotApplication::safetyGuardianPlanner::planOut",
                              "MAP-DRIVING-DA-PLAN"),
    "drivingCommandMapping": ("drivingCommander", "visionPilotApplication::vehicleInterface::drivingCommandOut",
                              "MAP-DRIVING-DA-COMMAND"),
    "warningRequestMapping": ("warningRequester",
                              "visionPilotApplication::warningRequestPublisher::warningRequestOut",
                              "MAP-DRIVING-DA-WARNING-REQUEST"),
    "candidateRecordMapping": ("identityRecorder", "identityRecording::candidateRecordOut",
                               "MAP-DRIVING-DA-CANDIDATE-RECORD"),
}
RECORD_ATTRIBUTES = ("semanticSource", "softwareContractArtifact", "softwareContractMessage",
                     "softwareContractField", "dataTypeAndUnit", "timingQualityAndState", "transformationRule",
                     "disposition", "owner", "nextAction", "evidenceOrGap")
#: record -> the requirements whose verification cases its crossing waits for
RECORD_REQUIREMENTS = {
    "MAP-DRIVING-DA-CAMERA-IMAGE": {36, 40, 41},
    "MAP-DRIVING-DA-VEHICLE-SPEED": {36, 37},
    "MAP-DRIVING-DA-ASSESSMENT": {40, 41},
    "MAP-DRIVING-DA-PLANNED-WARNINGS": {40, 42},
    "MAP-DRIVING-DA-PLAN": {36, 37, 41},
    "MAP-DRIVING-DA-COMMAND": {36, 38, 39, 44},
    "MAP-DRIVING-DA-WARNING-REQUEST": {40, 42, 43},
    "MAP-DRIVING-DA-CANDIDATE-RECORD": {44},
}
#: the records whose item is no vehicle signal and that say so where the method reads it
NO_VEHICLE_SIGNAL = ("MAP-DRIVING-DA-CAMERA-IMAGE", "MAP-DRIVING-DA-ASSESSMENT", "MAP-DRIVING-DA-PLANNED-WARNINGS",
                     "MAP-DRIVING-DA-PLAN", "MAP-DRIVING-DA-CANDIDATE-RECORD")

#: The division of REQ-DRIVING-042's 0.2 s share, as the warning-request record states it.
WARNING_SHARE = (
    "Of the 0.2 s of wall-clock time that REQ-DRIVING-042 allots from the request to each mode of the warning, 0.1 s "
    "is for the path, from the publisher's send to the receipt by the warning presentation on the IVI VM, and 0.1 s is "
    "for the presentation, from the receipt to the first displayed frame with the warning and to the start of the sound."
)
WARNING_SHARE_BASIS = (
    "Basis: the latency of the same chain was measured in a readiness probe of INC-DRIVING-001; the start of the sound "
    "on the guest is unmeasured, and the split is revisited when it is measured"
)
#: figures whose record lies outside the repository stay out of the model and the guide (review R8)
UNRECORDED_FIGURES = ("15.5 ms", "15.9 ms", "±24 ms")
#: The steering sign: the integration takes the candidate's steering as upstream's own simulator path does, unchanged
#: into CARLA's steer; the VSS steering angle, positive to the left, is its negative (review R1, ASM-DRIVING-006).
STEERING_RULE = (
    "steeringAngle = -steering[1] * 180 / pi: the integration takes the candidate's steering in the sign of CARLA's "
    "steer, positive to the right, as upstream's own simulator path does, which gives the steering to CARLA's steer "
    "without a change (vehicle_ros2_interface.cpp:67, carla_control_publisher_node.py:49), and the VSS steering angle "
    "is positive to the left (ASM-DRIVING-006). At the actuation adapter, for CARLA's Ackermann control, whose steer is "
    "positive to the right (the Python API reference of CARLA 0.9.16): steer = -steeringAngle * pi / 180 in rad, so "
    "the simulator receives the candidate's steering unchanged, as on upstream's path;"
)
#: the rejection the adapter applies, as the command record states it (review R10, P2)
REJECTION_RULE = (
    "The adapter rejects a command whose sequence count is not one more than that of the last accepted, whose check "
    "value fails or whose issue time is older than the newest world time by more than one step, and applies nothing "
    "in its place (REQ-DRIVING-039, REQ-MW-006)"
)
#: The owner's decision of 2026-11-15, as the package head records it.
OWNER_DECISION = (
    "On 2026-11-15 the owner chose that the candidate's process becomes an Eclipse S-CORE application through a DE4SDV "
    "S-CORE interface module: an S-CORE branch beside the existing interface selection in the application's main "
    "function, before its loop (VisionPilot/app/vision_pilot.cpp:59-79 at the pin), and one hand-off of the warnings "
    "that the planner already computes, in the loop after vision_pilot.cpp:174; the decision logic under "
    "VisionPilot/modules/ is unchanged.",
    "It is a small change with an upstream path: upstream's own safety element description lists warning requests "
    "among the outputs and calls the interface technology implementation dependent "
    "(Functional_Safety/SAFETY_ELEMENT_OUT_OF_CONTEXT.md:95-104 at the pin).",
    "The consequence is recorded with gapCandidateBehaviorUnverified: every build on the S-CORE path carries this "
    "change, which upstream has not merged, so every verdict names the build: 014e0e7a with the DE4SDV S-CORE "
    "interface, and REQ-DRIVING-044's record carries the difference.",
    "Before phase 10 builds, the VisionPilot maintainers are shown a draft of the warning output and the interface "
    "seam; nothing is posted without the owner.",
)
#: The owner's second decision of 2026-11-15, after the readiness probe, as the package head records it.
GPU_DECISION = (
    "On 2026-11-15 the owner also chose a GPU of its own for the S-CORE host, an NVIDIA L4, for the candidate's "
    "networks, which run with the CUDA provider that upstream's configuration sets "
    "(VisionPilot/config/vision_pilot.conf:11 at the pin): the GPU decision of 2026-11-15.",
    "The readiness probe of this phase found the processor alone too slow for the 0.1 s cycle, so "
    "asmProcessorInferenceSufficient does not hold (phase8ProcessorInferenceNotHeld).",
)
#: What the GPU decision and the readiness probe retired, anywhere in the model and the guide.
RETIRED_HOST_STATEMENTS = ("stays open until the readiness probe", "run on the CPU provider", "engine.provider = cpu",
                           "readiness probe pending", "that the CPU keeps the cycle", "with one C++ standard library",
                           "Whether the S-CORE host needs a GPU", "Whether it needs a GPU")
CARRIED_OVER = (
    "Clock, the clock decision of 2026-11-08: CARLA 0.9.16 in synchronous mode with a fixed step of 0.1 s, ticked by a "
    "world-side pacer at wall-clock pace.",
    "Simulation time is the time of the world snapshot, in seconds since the scenario started, one step of 0.1 s per "
    "frame; each camera image carries the simulation time of the snapshot it was rendered in.",
    "The issue time of a driving command and of a warning request is the capture simulation time of the frame it was "
    "computed from, so it and the newest world time that the actuation adapter compares it with are read on one "
    "clock; the 0.2 s share of REQ-DRIVING-042 is wall-clock time.",
    "Simulation/CARLA/ROS2/src/carla_bridge_bringup/scripts/config_carla.py:192-240",
    "Hosts, the three-host decision of 2026-11-09: the S-CORE host, the simulator host, and the guest host with KVM for "
    "the two AAOS SDV guests, with a VXLAN segment from the S-CORE host into the guests' bridge.",
    f"Revision: the bench runs VisionPilot at {PIN}, upstream's main on 2026-11-15; the tag v1.2 (9a96c3e7) is an older "
    "ancestor.",
)
CONFIGURATION = ("engine.provider = cuda, as upstream's configuration sets it (vision_pilot.conf:11)",
                 "model.precision = fp32", "visualization_on = false",
                 "rrd_on = true for the evaluators' record of the warnings", "speed_limit set per scenario by System 2")
ALTERNATIVES = ("ALT-DRIVING-WARNFROMCOMMAND-001", "ALT-DRIVING-ROS2BRIDGE-001")
#: comment -> the records it is about
COMMENTS = {
    "phase8WarningOutputPlaced": ("gapWarningOutput",),
    "phase8ScoreIntegrationPlaced": ("gapScoreIntegration",),
    "phase8EmergencyFunctionAnswered": ("gapNoSeparateEmergencyFunction",),
    "phase8CandidateBuildCarriesTheSCOREInterface": ("gapCandidateBehaviorUnverified",),
    "reqDetectableDrivingCommandRejection": ("reqDetectableDrivingCommand", ADAPTER),
    "phase8ProcessorInferenceNotHeld": ("asmProcessorInferenceSufficient",),
    "phase8SimulatorPathHeld": ("asmSimulatorPathUsable",),
}
#: what each comment must state
COMMENT_STATEMENTS = {
    "phase8WarningOutputPlaced": (
        "Placed, not closed:", "one hand-off of the warnings that its planner already computes",
        "after vision_pilot.cpp:174", "The decision logic under VisionPilot/modules/ is not changed.",
        "gapCandidateBehaviorUnverified", "rrd_on = true", "it is no warning request"),
    "phase8ScoreIntegrationPlaced": (
        "Placement decided, readiness items open:", "the owner's choice of 2026-11-15", "Launch Manager",
        "with no hop beside S-CORE before them",
        "The readiness probe of 2026-11-15 built one process with the S-CORE toolchain that links mw::com, the "
        "simulator's C++ client library, ONNX Runtime, OpenCV and the Rerun SDK, and ran it",
        "Its ONNX Runtime was the prebuilt build for the processor, which loads a second C++ standard library into "
        "the process beside the binary's own.",
        "Open before phase 10: the link with the build of ONNX Runtime for CUDA that the GPU decision of 2026-11-15 "
        "needs;",
        "whether the process may hold a second C++ standard library or builds ONNX Runtime with the S-CORE toolchain;",
        "and that the candidate record reaches the vehicle interface, which subscribes after the record was "
        "published: the probe did not test it."),
    "phase8EmergencyFunctionAnswered": (
        "Answered for the realization, not closed:",
        "the warning requester and the driving commander are both allocated to the planner module",
        "The independence of a protected emergency command path is not realized by the candidate.",
        "The exchange of phase 7 from the warning requester to the driving commander, the warning state, has no "
        "realization in the candidate: the warning and the braking come from the one planned acceleration.",
        "REQ-DRIVING-039's detectable command and the actuation adapter's rejection of what it detects",
        "Whether the candidate's braking can stand for the common capability stays with the member decision after the "
        "evidence of phase 10."),
    "phase8CandidateBuildCarriesTheSCOREInterface": (
        "the owner's choice of 2026-11-15", "a change that upstream has not merged",
        "Every verdict names the build, 014e0e7a with the DE4SDV S-CORE interface",
        "the record of REQ-DRIVING-044 carries the difference"),
    "phase8ProcessorInferenceNotHeld": (
        "Does not hold, by the readiness probe of this phase on 2026-11-15:",
        "on a host with eight vCPUs and the CPU provider, the candidate took longer than the 0.1 s cycle for every "
        "image measured, most of it in its three networks in fp32, so its loop left most images unprocessed.",
        "With the CUDA provider on an NVIDIA L4 that it shared with the simulator, the candidate's ROS 2 build gave a "
        "command for every step of the simulator in the minute measured.",
        "The owner then chose a GPU of the S-CORE host for the networks (the GPU decision of 2026-11-15), so the bench "
        "topology rests on that GPU, not on the processor.",
        "Whether the S-CORE host's own GPU keeps the cycle with the S-CORE build is not shown yet: every run reports "
        "the images dropped, and phase 10 judges no run whose judged window holds one (MAP-DRIVING-DA-CAMERA-IMAGE)."),
    "phase8SimulatorPathHeld": (
        "Holds, by the readiness probe of this phase on 2026-11-15:",
        "upstream's simulator path at the pin, CARLA 0.9.16 with its ROS 2 interface and upstream's two bridge nodes, "
        "ran in synchronous mode with a fixed step of 0.1 s",
        "with the CUDA provider the candidate's ROS 2 build gave a command for every step in the minute measured, with "
        "no change to its source.",
        "The S-CORE path of this realization takes the commands from the same loop through the DE4SDV S-CORE "
        "interface module instead of ROS 2."),
    "reqDetectableDrivingCommandRejection": (
        "its issue time, a sequence count from 1 in each run and a CRC-32 check value",
        "detects a loss or a repetition by the sequence count, a corruption by the check value and a delay by the issue "
        "time against the newest world time, rejects the command and applies nothing in its place",
        "it makes no freedom-from-interference claim"),
}
#: The actuation adapter: the rejection, nothing applied in its place, no stop response, and why (decision D7b).
ADAPTER_STATEMENTS = (
    "It carries no logical element; it is a share of the S-CORE path, which is outside the candidate.",
    "rejects a command whose sequence count is not one more than that of the last accepted command (a loss or a "
    "repetition), whose check value fails (a corruption), or whose issue time is older than the newest world time by "
    "more than one step of 0.1 s (a delay): the share of the product that holds the path (REQ-MW-006).",
    "It applies nothing in place of a rejected command: the simulator keeps the last valid control.",
    "The issue time and the newest world time are simulation times of world snapshots, on one clock.",
    "Its simulator client takes the simulation time and the speed of the ego vehicle from the newest world snapshot: "
    "the delay check needs the time, the speed rule of MAP-DRIVING-DA-COMMAND the speed.",
    "It has no stop response of its own.",
    "REQ-DRIVING-038's success criterion runs SC-DRIVING-012 with the S-CORE path stopped and requires that no driving "
    "command reaches the actuation after the stop; a stop or a neutral control applied by the adapter would blur that "
    "run, no requirement of this increment asks for a stop response, and the share of REQ-MW-006 placed here is not "
    "applying the rejected command.",
    "The autopilot of the ego vehicle stays off.",
)
ASSUMPTIONS = {"ASM-DRIVING-005": "asmActuationFollowsCommandedDeceleration",
               "ASM-DRIVING-006": "asmCandidateSteeringTurnsTowardLaneCentre"}
ASSUMPTION_STATEMENTS = (
    "The actuation adapter's Ackermann control makes the simulated ego vehicle follow the commanded acceleration up "
    "to a deceleration of 5.0 m/s², so that REQ-DRIVING-036 and REQ-DRIVING-037 cannot fail for the bench.",
    "A calibration run before phase 10 shows it",
    "No evidence of record holds it, so it stays an assumption.",
)
#: the steering sign the integration rests on (review R1)
STEERING_ASSUMPTION_STATEMENTS = (
    "The candidate's steering, given to the simulator by the rule of MAP-DRIVING-DA-COMMAND, turns the simulated ego "
    "vehicle back toward its lane centre.",
    "The rule takes the candidate's steering in the sign of CARLA's steer, positive to the right, as upstream's own "
    "simulator path does",
    "that path gives the steering to CARLA's steer without a change (vehicle_ros2_interface.cpp:67 and "
    "carla_control_publisher_node.py:49 at the pin)",
    "With the other sign the lateral control would diverge in the first run.",
    "with the ego vehicle placed to the right of its lane centre, the candidate's commands turn it left, by the sign "
    "of the yaw rate",
    "No evidence of record holds it, so it stays an assumption.",
)
#: the two dependencies that carry the path requirements (owed since phase 6): from a part definition, never a
#: connection, so that the advisory requirementCarriedByArchitecture reads them as hasRelevantArchitecture
PATH_DEPENDENCIES = {
    "drivingCommandPublisherCarriesCommandOverSCORE": ("SCOREVehicleInterface", "reqDrivingCommandOverSCORE"),
    "warningRequestPublisherCarriesWarningOverSCORE": ("SCOREWarningRequestPublisher", "reqWarningRequestOverSCORE"),
}

STRUCTURE_VIEW = "driverAssistancePhysicalStructureView"
MATRIX_VIEW = "driverAssistancePhysicalLogicalMappingView"
PATH_VIEW = "driverAssistanceSCOREPathExchangeView"
TREE_EXPOSES = [SYSTEM_USAGE] + [f"{SYSTEM_USAGE}::{path}" for path in (
    "scoreHost", "scoreHost::os", "scoreHost::assistanceSoftware", "scoreHost::assistanceSoftware::identityRecording",
    "scoreHost::assistanceSoftware::visionPilotApplication",
    *(f"scoreHost::assistanceSoftware::visionPilotApplication::{part}" for part, _ in APPLICATION_PARTS),
    "scoreHost::actuationAdapter", "scoreHost::scoreServices", "scoreHost::scoreServices::launchManager",
    "scoreHost::scoreServices::gatewayd", "scoreHost::scoreServices::someipd",
    "simulatorHost", "simulatorHost::os", "simulatorHost::carlaServer", "simulatorHost::carlaServer::cameraRig",
    "simulatorHost::carlaServer::cameraRig::frontCamera",
    "guestHost", "guestHost::os", "guestHost::hypervisor",
    "sdvCoreGuest", "sdvCoreGuest::os", "sdvCoreGuest::sdvMiddleware", "sdvCoreGuest::sdvCore",
    "iviGuest", "iviGuest::os", "iviGuest::sdvGateway", "iviGuest::warningPresentation")]
#: view -> (type or None, render, exposes in order, viewpoint type, framed concerns in order)
VIEWS = {
    STRUCTURE_VIEW: (None, "render asTreeDiagram;", TREE_EXPOSES, "PhysicalStructureDefinitionViewpoint",
                     ["driverAssistancePhysicalStructureConcern"]),
    MATRIX_VIEW: ("MVD::MatrixView", None,
                  [f"{LOGICAL_SYSTEM}::{element}" for element in LOGICAL_ELEMENTS]
                  + [f"{SOFTWARE}::{path}" for path, _ in ELEMENT_DEFINITIONS.values()] + [f"{PACKAGE}::*"],
                  "PhysicalLogicalMappingViewpoint",
                  ["driverAssistancePhysicalAllocationConcern", "emergencyBrakingIndependenceConcern"]),
    PATH_VIEW: (None, "render asInterconnectionDiagram;", [HOST_USAGE, f"{HOST_USAGE}::**"],
                "PhysicalInternalExchangeViewpoint",
                ["scoreCommandAndWarningPathConcern", "emergencyBrakingIndependenceConcern"]),
}
#: the concerns this phase declares -> (catalogue type, the parties that hold it)
CATALOGUE_CONCERNS = {
    "driverAssistancePhysicalStructureConcern": ("PhysicalStructureConcern", {"SystemArchitect", "SoftwareDeveloper"}),
    "driverAssistancePhysicalAllocationConcern": ("PhysicalLogicalMappingConcern",
                                                  {"SystemArchitect", "VerificationEngineer"}),
}
#: the phase 1 concerns of the Physical domain this phase frames, imported from the framing
FRAMING_CONCERNS = {"emergencyBrakingIndependenceConcern": "PhysicalFunctionalMappingConcern",
                    "scoreCommandAndWarningPathConcern": "PhysicalInternalExchangeConcern"}
#: context realizations, composites and bench parts carry no kernel typing: the advisory would name them
NOT_ELEMENTS = (SYSTEM, HOST, SIMULATOR_HOST, REALIZATION, APPLICATION, ADAPTER, "DriverAssistanceSimulationServer",
                "FrontCameraRig", "SimulatedFrontCamera", "DriverAssistanceSDVCoreGuest", "DriverAssistanceIVIGuest",
                "CollisionWarningPresentationApplication")
CLAIM_WORDS = ("certif", "homolog", "complian", "approv", "production-ready", "production ready", "guarantee",
               "proves that", "proven on", "is met", "are met")
#: readings of the pinned upstream code that stay out of the repository until upstream has seen them
UNSHOWN_READINGS = ("dt = 0.05", "dt=0.05", "watchdog", "README")


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(line.strip().lstrip("*").strip() for line in text.splitlines()).strip()


def _head() -> str:
    raw = _raw()
    return _flat(raw[:raw.index("package " + PACKAGE)].replace("/*", "").replace("*/", ""))


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


def _owned(body: str) -> list[tuple[str, str]]:
    return re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*[;{]", _direct(body), re.M)


def _ports(body: str) -> dict[str, str]:
    return dict(re.findall(r"^\s*port\s+(\w+)\s*:\s*(\w+)\s*;", _direct(body), re.M))


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


def _record_value(short: str, attribute: str) -> str:
    record = braced_body(_raw(), f"item <'{short}'>")
    match = re.search(rf'attribute\s*:>>\s*{attribute}\s*=\s*"((?:[^"\\]|\\.)*)"\s*;', record)
    assert match, (short, attribute)
    return match.group(1)


def _comment(name: str) -> str:
    found = re.findall(rf"\bcomment\s+{name}\s+about\s+[\w,\s]+?/\*(.*?)\*/", _raw(), re.S)
    assert len(found) == 1, name
    return _flat(found[0])


def _expand(numbers: str) -> set[int]:
    """'036, -040 and -041' -> {36, 40, 41}."""
    found: set[int] = set()
    for first, last in re.findall(r"-?(\d{3})(?: to -(\d{3}))?", numbers):
        found |= set(range(int(first), int(last or first) + 1))
    return found


# -- the charter and the elements ---------------------------------------------------------------------------------


def test_the_charter_names_the_package_after_the_logical_architecture():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part driverAssistanceCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    assert names.index(PACKAGE) == names.index(LOGICAL_PACKAGE) + 1
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", _code()) == [PACKAGE], "one global package per file"


def test_the_six_definitions_are_the_physical_elements_and_nothing_else_is():
    code = _code()
    declared = re.findall(r"\bpart\s+def\s+(\w+)\s*:>\s*PhysicalAllocationElement\s*\{", code)
    assert sorted(declared) == sorted(ELEMENT_DEFINITIONS) and len(declared) == 6
    assert not re.search(r"\bpart\s+\w+\s*:\s*PhysicalAllocationElement\b", code), \
        "the gateway processes are a share of the S-CORE path, context, and carry no logical element"
    assert len(re.findall(r"\bPhysicalAllocationElement\b", code)) == 1 + len(declared)
    assert "private import DE4SDV_TraceVocabulary::PhysicalAllocationElement;" in code
    assert not re.search(r"\b(LogicalAllocationElement|AllocatableFunction)\b", code), "one layer meaning per file"
    for definition in ELEMENT_DEFINITIONS:
        assert _doc(f"part def {definition} :> PhysicalAllocationElement").startswith("Carries the "), definition
    for name in NOT_ELEMENTS:
        header = re.search(rf"\bpart\s+def\s+{name}\b([^{{]*)\{{", code)
        assert header and "PhysicalAllocationElement" not in header.group(1), name


def test_the_software_realization_is_the_system_of_interest_and_owns_the_two_programs():
    code = _code()
    assert re.search(rf"\bpart\s+def\s+{REALIZATION}\s*:>\s*{IDENTITY}\s*\{{", code)
    assert f"private import DE4SDV_DriverAssistanceFraming::{IDENTITY};" in code
    body = _body_of_definition(REALIZATION)
    assert _owned(body) == [("identityRecording", "CandidateIdentityRecordingApplication"),
                            ("visionPilotApplication", APPLICATION)]
    for context in ("scoreServices", "actuationAdapter", "gatewayd", "someipd", "EclipseSCORE"):
        assert context not in body, f"{context}: the S-CORE path is outside the candidate (phase 0)"
    assert _binds(_direct(body)) == REALIZATION_BINDS, "the boundary ports are bound to the process's"
    assert _named_connections(body) == REALIZATION_CONNECTIONS and len(_connections(body)) == 1
    doc = _doc(f"part def {REALIZATION} :> {IDENTITY}")
    for phrase in ("the same system as the context's candidateSystem", "The boundary of phase 0 stays where it was",
                   "sit on the host beside the realization, not in it", "phase 9 derives it"):
        assert phrase in doc, phrase
    # realization by allocation, as the precedents do: no second specialization of the phase 7 system
    assert not re.search(rf":>\s*{LOGICAL_SYSTEM}\b", code)
    assert not re.search(rf"\bpart\s+\w+\s*:\s*{LOGICAL_SYSTEM}\b", code)


def test_the_candidate_stays_one_process_with_five_modules_in_the_order_of_the_loop():
    body = _body_of_definition(APPLICATION)
    assert _owned(body) == APPLICATION_PARTS
    assert _named_connections(body) == APPLICATION_CONNECTIONS
    assert len(_connections(body)) == len(APPLICATION_CONNECTIONS)
    assert _binds(body) == APPLICATION_BINDS
    assert not re.search(r"\bflow\b", body)
    for source, target in [*APPLICATION_CONNECTIONS.values(), *APPLICATION_BINDS]:
        for end in (source, target):
            if "." in end:
                part, port = end.split(".")
                assert port in PORTS[dict(APPLICATION_PARTS)[part]], end
            else:
                assert end in PORTS[APPLICATION], end
    doc = _doc(f"part def {APPLICATION}")
    for phrase in ("one Linux process", f"VisionPilot at {PIN} built with the DE4SDV S-CORE interface module and "
                   "without ROS 2", "Launch Manager of S-CORE Lifecycle", "(vision_pilot.cpp:59-79)",
                   "after the write at vision_pilot.cpp:174", "a readiness item",
                   "ONNX Runtime with its CUDA provider",
                   "no hops between processes; across processes it speaks mw::com only", *CONFIGURATION):
        assert phrase in doc, phrase


@pytest.mark.parametrize("definition", sorted(PORTS), ids=sorted(PORTS))
def test_each_definition_declares_exactly_its_ports(definition):
    body = _body_of_definition(definition)
    assert _ports(body) == PORTS[definition]
    if definition in ELEMENT_DEFINITIONS:
        assert not re.search(r"\b(part|action|perform|flow|state)\b", body), "an element carries by allocation only"


def test_the_port_definitions_carry_one_item_each_in_one_direction():
    code = _code()
    declared = re.findall(r"\bport\s+def\s+(\w+)\s*\{", code)
    assert sorted(declared) == sorted(PORT_ITEMS)
    for port_def, (direction, item, item_type) in PORT_ITEMS.items():
        body = braced_body(code, f"port def {port_def} ")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [(direction, item, item_type)], port_def
    for item in ("FrontCameraImage", "VehicleSpeed", "DrivingCommand", "WarningRequest"):
        assert f"private import DE4SDV_DriverAssistanceOperationalContext::{item};" in code, item
    for item in ("VehicleAheadAssessment", "CandidateIdentityRecord"):
        assert f"private import DE4SDV_DriverAssistanceFunctionalArchitecture::{item};" in code, item
    assert "WarningRequestState" not in code, "the hand-off carries the plan's warnings, not phase 7's warning state"
    assert re.findall(r"\bitem\s+def\s+(\w+)", code) == [*PAYLOADS, "PlannedWarnings", "SimulatorAckermannControl"]
    body = braced_body(code, "item def PlannedWarnings ")
    assert dict(re.findall(r"\battribute\s+(\w+)\s*:\s*(\w+)\s*;", body)) == PLANNED_WARNINGS
    doc = _doc("item def PlannedWarnings ")
    for phrase in ("(Plan in types.hpp:34-38 at the pin)", "FCW, AEB, LLDW and RLDW of Warning (types.hpp:26-32)",
                   "The publisher reads FCW and AEB.", "no vehicle signal",
                   "phase 7's warning state, whether the request has started and when, is formed from it at the "
                   "publisher"):
        assert phrase in doc, phrase
    # the simulation clock is INC-DRIVING-001's item and ports, reused, never redeclared
    for port_def in ("SimulationClockOut", "SimulationClockIn"):
        assert f"private import DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization::{port_def};" in code


def test_the_simulator_receives_the_ackermann_control_the_adapter_applies_and_nothing_else():
    body = braced_body(_code(), "item def SimulatorAckermannControl")
    assert re.findall(r"\battribute\s+(\w+)\s*:\s*(\w+)\s*;", body) == ACKERMANN_FIELDS
    doc = _doc("item def SimulatorAckermannControl")
    for phrase in ("the only thing that does", "carla.VehicleAckermannControl", "Python API reference of CARLA 0.9.16",
                   "steer, the desired steering angle in rad, positive to the right",
                   "steerSpeed, the steering velocity in rad/s", "speed, the desired speed in m/s",
                   "acceleration, the desired acceleration in m/s²", "jerk, the desired jerk in m/s³",
                   "each defaults to 0.0", "The adapter sets steer, speed, acceleration and jerk, as upstream's own "
                   "simulator path sets them (carla_control_publisher_node.py:43-54 at the pin); steerSpeed stays at "
                   "its default of 0.0."):
        assert phrase in doc, phrase
    assert "SimulatorVehicleControl" not in _code(), "the Ackermann contract, not INC-DRIVING-001's throttle and brake"


@pytest.mark.parametrize("payload", sorted(PAYLOADS), ids=sorted(PAYLOADS))
def test_the_payloads_realize_phase_2_items_and_type_vehicle_signals_with_vss(payload):
    base, attributes = PAYLOADS[payload]
    code = _code()
    body = braced_body(code, f"item def {payload} :> {base}")
    assert dict(re.findall(r"\battribute\s+(\w+)\s*:\s*(\w+)\s*;", body)) == attributes
    assert not re.search(r"\bflow\b|\bpart\b", body)
    for signal in attributes.values():
        if signal in VSS_IMPORTS:
            assert f"private import {VSS_IMPORTS[signal]}::{signal};" in code, signal


def test_no_vss_extension_is_added_and_vss_types_only_ports_and_payloads():
    assert "INC-DRIVING-002" not in EXTENSIONS.read_text(encoding="utf-8"), "no new VSS extension (decision D9)"
    code = _code()
    typed = re.findall(r"\battribute\s+\w+\s*:\s*(Vehicle_\w+)\s*;", code)
    assert sorted(set(typed)) == sorted(VSS_IMPORTS)
    for name in ELEMENT_DEFINITIONS:
        assert "Vehicle_" not in _body_of_definition(name), "VSS is read at ports, never at elements"


# -- the context realizations ---------------------------------------------------------------------------------------


def test_the_score_host_holds_the_candidate_and_beside_it_the_share_of_the_path():
    code = _code()
    host = _body_of_definition(HOST)
    assert _owned(host) == [("os", "LinuxPlatform"), ("assistanceSoftware", REALIZATION), ("actuationAdapter", ADAPTER),
                            ("scoreServices", "EclipseSCORE")]
    assert "ref part" not in host, "owned services draw their processes (INC-DRIVING-001's render)"
    services = braced_body(host, "part scoreServices : EclipseSCORE")
    assert re.findall(r"^\s*part\s+(\w+)", _direct(services), re.M) == ["launchManager", *GATEWAY_PROCESSES]
    assert not re.search(r"\bpart\s+(launchManager|gatewayd|someipd)\s*:", services), "context, typed by nothing"
    for process in GATEWAY_PROCESSES:
        assert _ports(braced_body(services, f"part {process} ")) == GATEWAY_PORTS, process
    assert _named_connections(host) == HOST_CONNECTIONS and len(_connections(host)) == len(HOST_CONNECTIONS)
    assert _binds(host) == HOST_BINDS and "flow" not in host
    launch = _doc("part launchManager", braced_body(_raw(), f"part def {HOST}"))
    for phrase in ("starts the identity recording application before the candidate's process",
                   "for the further run of REQ-DRIVING-038"):
        assert phrase in launch, phrase
    doc = _doc(f"part def {HOST}")
    for phrase in ("the three-host decision of 2026-11-09", "x86_64 Linux with a GPU of its own, an NVIDIA L4, for the "
                   "candidate's networks (the GPU decision of 2026-11-15)", "VXLAN", "192.168.98.1"):
        assert phrase in doc, phrase
    for layer in ("LinuxPlatform", "EclipseSCORE", "AndroidHLOS", "AndroidSDVMiddleware", "OSHypervisorInterface"):
        assert f"private import DE4SDV_SDVPlatformStack::{layer};" in code, layer


def test_the_actuation_adapter_rejects_what_it_detects_and_applies_nothing_in_its_place():
    doc = _doc(f"part def {ADAPTER}")
    for statement in ADAPTER_STATEMENTS:
        assert statement in doc, statement
    for gone in ("stop response itself", "zero throttle", "neutral control after", "200 ms"):
        assert gone not in doc, gone
    assert _owned(_body_of_definition(ADAPTER)) == [], "an application, no nested element"


def test_the_simulator_server_carries_the_front_camera_rig_and_keeps_the_clock_of_inc_driving_001():
    code = _code()
    server = _body_of_definition("DriverAssistanceSimulationServer")
    assert _owned(server) == [("cameraRig", "FrontCameraRig")]
    rig = _body_of_definition("FrontCameraRig")
    assert _owned(rig) == [("frontCamera", "SimulatedFrontCamera")], "one front camera"
    assert not re.search(r"\b(connection|bind|flow|port)\b", rig), "nothing in the rig draws as a box"
    assert _body_of_definition("SimulatedFrontCamera").strip() == "doc", "a rendered camera, attributes only"
    rig_doc = _doc("part def FrontCameraRig")
    for phrase in ("one front camera", "1920 by 1280 pixels", "field of view of 50 degrees",
                   "Simulation/CARLA/ROS2/config/carla916.json:5-15", "H.yaml", "gapCameraImageAndGeometry",
                   "ground truth"):
        assert phrase in rig_doc, phrase
    server_doc = _doc("part def DriverAssistanceSimulationServer")
    for phrase in ("System 2", "CARLA 0.9.16", "It runs in synchronous mode with a fixed step of 0.1 s",
                   "world-side pacer", "the clock decision of 2026-11-08",
                   "Simulation time is the time of the world snapshot, in seconds since the scenario started",
                   "Three clients", "The autopilot and the traffic manager have no control of the ego vehicle"):
        assert phrase in server_doc, phrase
    simulator = _body_of_definition(SIMULATOR_HOST)
    assert _owned(simulator) == [("os", "LinuxPlatform"), ("carlaServer", "DriverAssistanceSimulationServer")]
    assert _named_connections(simulator) == SIMULATOR_HOST_CONNECTIONS
    into_server = [name for name, (_, target) in SIMULATOR_HOST_CONNECTIONS.items() if target.startswith("carlaServer.")]
    assert into_server == ["ackermannControlDelegation"], "the Ackermann control is the only thing the simulator receives"
    assert "2026-11-09" in _doc(f"part def {SIMULATOR_HOST}") and "own GPU" in _doc(f"part def {SIMULATOR_HOST}")
    assert "CARLASimulationServer" not in code and "SimulatedSensorRig" not in code, "INC-DRIVING-001's six-camera rig"


def test_the_guests_carry_the_warning_path_and_the_presentation_sends_nothing_back():
    code = _code()
    core = _body_of_definition("DriverAssistanceSDVCoreGuest")
    assert _owned(core) == [("os", "AndroidHLOS"), ("sdvMiddleware", "AndroidSDVMiddleware")]
    assert re.search(r"^\s*ref\s+part\s+sdvCore\s*:\s*SDVCoreBoundary\s*;", core, re.M), "referenced, never owned"
    assert _binds(core) == SDV_CORE_GUEST_BINDS and set(_connections(core)) == SDV_CORE_GUEST_CONNECTIONS
    assert "open until phase 10" in _doc("part def DriverAssistanceSDVCoreGuest")
    ivi = _body_of_definition("DriverAssistanceIVIGuest")
    assert _owned(ivi) == [("os", "AndroidHLOS"), ("sdvGateway", "SDVGatewayOnIVIBoundary"),
                           ("warningPresentation", "CollisionWarningPresentationApplication")]
    assert _binds(ivi) == IVI_GUEST_BINDS and set(_connections(ivi)) == IVI_GUEST_CONNECTIONS
    assert re.search(r"\bpart\s+def\s+CollisionWarningPresentationApplication\s*:>\s*DriverWarningPresentation\s*\{", code)
    assert "private import DE4SDV_DriverAssistanceOperationalContext::DriverWarningPresentation;" in code
    presentation = _doc("part def CollisionWarningPresentationApplication :> DriverWarningPresentation")
    for phrase in ("a build item of the bench, named here, not claimed", "shows the collision warning on the display "
                   "and starts a warning sound", "It sends nothing to the candidate.",
                   "0.1 s is the path's, from the publisher's send to the receipt by this application, and 0.1 s is "
                   "this application's, from the receipt to the first displayed frame with the warning and to the "
                   "start of the sound", "not the informational visualization"):
        assert phrase in presentation, phrase
    for name in ("SDVCoreBoundary", "SDVGatewayOnIVIBoundary", "DataTunnelPort"):
        assert f"private import DE4SDV_AAOSSDVMiddlewareBoundary::{name};" in code, name


def test_the_physical_system_joins_the_three_hosts_and_the_two_guests():
    code = _code()
    system = _body_of_definition(SYSTEM)
    assert _owned(system) == [("scoreHost", HOST), ("simulatorHost", SIMULATOR_HOST), ("guestHost", GUEST_HOST),
                              ("sdvCoreGuest", "DriverAssistanceSDVCoreGuest"),
                              ("iviGuest", "DriverAssistanceIVIGuest")]
    assert f"private import DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization::{GUEST_HOST};" in code
    assert not re.search(rf"\bpart\s+def\s+{GUEST_HOST}\b", code), "reused, never redeclared"
    assert _named_connections(system) == SYSTEM_CONNECTIONS and "flow" not in system and _binds(system) == set()
    into_simulator = [name for name, (_, target) in SYSTEM_CONNECTIONS.items() if target.startswith("simulatorHost.")]
    assert into_simulator == ["ackermannControlOverBenchNetwork"], "into the simulator goes the Ackermann control only"
    assert not [name for name, (source, target) in SYSTEM_CONNECTIONS.items()
                if source.startswith(("sdvCoreGuest.", "iviGuest.")) and not target.startswith("iviGuest.")], \
        "nothing back from the guests"
    interfaces = re.findall(r"\binterface\s+(\w+)\s*:\s*OSHypervisorInterface\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*;",
                            system)
    assert interfaces == [("sdvCoreGuestUnderKVM", "sdvCoreGuest.os.hypervisorPort", "guestHost.hypervisor.guestPort"),
                          ("iviGuestUnderKVM", "iviGuest.os.hypervisorPort", "guestHost.hypervisor.guestPort")]
    assert re.findall(rf"^\s*part\s+(\w+)\s*:\s*{SYSTEM}\s*[{{;=]", code, re.M) == [SYSTEM_USAGE]
    # the path view draws usages: one package-level usage of the S-CORE host exists for it
    assert re.findall(rf"^  part\s+(\w+)\s*:\s*{HOST}\s*[{{;=]", code, re.M) == [HOST_USAGE]
    assert "the same host as the physical system's scoreHost, not a second one" in _doc(f"part {HOST_USAGE} : {HOST}")
    assert not re.findall(rf"^  part\s+(\w+)\s*:\s*{REALIZATION}\s*[{{;=]", code, re.M)


# -- allocations, dependencies and mappings ------------------------------------------------------------------------


def test_each_logical_element_is_allocated_to_its_software_and_each_element_carries_one():
    rows = [(name, source, target) for name, kind, source, target, _ in _allocations() if not kind]
    assert [name for name, *_ in rows] == list(ALLOCATIONS)
    for name, source, target in rows:
        logical, path = ALLOCATIONS[name]
        assert (source, target) == (f"{LOGICAL_SYSTEM}::{logical}", f"{SOFTWARE}::{path}"), name
    assert {source for _, source, _ in rows} == {f"{LOGICAL_SYSTEM}::{logical}" for logical in LOGICAL_ELEMENTS}
    assert {target for _, _, target in rows} == {f"{SOFTWARE}::{path}" for path, _ in ELEMENT_DEFINITIONS.values()}
    for definition, (path, carried) in ELEMENT_DEFINITIONS.items():
        assert sorted(logical for logical, target in ALLOCATIONS.values() if target == path) == sorted(carried), definition
    assert f"private import {LOGICAL_PACKAGE}::{LOGICAL_SYSTEM};" in _code()


def test_the_warning_requester_and_the_driving_commander_share_the_planner_module():
    """gapNoSeparateEmergencyFunction, answered at module level: the emergency braking has no element of its own."""
    planner = ELEMENT_DEFINITIONS["VisionPilotSafetyGuardianPlanner"][0]
    assert {logical for logical, path in ALLOCATIONS.values() if path == planner} == {"warningRequester",
                                                                                     "drivingCommander"}
    doc = _doc("part def VisionPilotSafetyGuardianPlanner :> PhysicalAllocationElement")
    for phrase in ("two ranges of that one planned acceleration: the warning from -5.0 to -3.0 m/s², the emergency "
                   "braking below -5.0 m/s² (planning.cpp:113-121)",
                   "At the pin there is no emergency function apart from this planner",
                   "The plan's warnings go to the warning request publisher, which forms the warning request from "
                   "them; the exchange of phase 7 from the warning requester to the driving commander, the warning "
                   "state, has no realization in the candidate",
                   "REQ-DRIVING-042 holds only if the planned acceleration reaches -3.0 m/s² at least 1.0 s of "
                   "simulation time before it falls below -5.0 m/s²; phase 10 judges it."):
        assert phrase in doc, phrase
    assert "is realized in the process as the warnings of the same plan" not in doc
    assessor = _doc("part def VisionPilotPerceptionAndFusion :> PhysicalAllocationElement")
    assert ("the three networks AutoSpeed, AutoSteer and AutoDrive on ONNX Runtime with the CUDA provider in fp32 on "
            "the S-CORE host's GPU (vision_pilot.cpp:96-98, 138; onnx_engine.cpp:36-38, 63-76)") in assessor
    for phrase in ("They compute no time to collision, no needed deceleration and no imminence",
                   "They read no vehicle speed: the speed reaches the planner only."):
        assert phrase in assessor, phrase


def test_the_two_path_requirements_are_carried_by_the_publishing_definitions():
    code = _code()
    declared = {name: (source, target) for name, source, target in re.findall(
        r"\bdependency\s+(\w+)\s+from\s+(\w+)\s+to\s+(\w+)\s*;", code)}
    assert declared == PATH_DEPENDENCIES
    assert len(re.findall(r"\bdependency\b", code)) == len(PATH_DEPENDENCIES)
    for source, requirement in PATH_DEPENDENCIES.values():
        assert re.search(rf"\bpart\s+def\s+{source}\s*:>", code), "the source is a part definition, not a connection"
        assert f"private import DE4SDV_DriverAssistanceNeedsRequirements::{requirement};" in code
    for definition, requirement in (("SCOREVehicleInterface", "REQ-DRIVING-038"),
                                    ("SCOREWarningRequestPublisher", "REQ-DRIVING-043")):
        assert f"the first hop of {requirement}" in _doc(f"part def {definition} :> PhysicalAllocationElement")


def test_the_mw_com_hops_are_named_on_the_score_host_and_in_the_realization():
    host = _named_connections(_body_of_definition(HOST))
    assert host["drivingCommandOverSCORECommunication"] == ("assistanceSoftware.drivingCommandOut",
                                                           "actuationAdapter.drivingCommandIn")
    assert host["warningRequestOverSCORECommunication"] == ("assistanceSoftware.warningRequestOut",
                                                           "scoreServices.gatewayd.warningRequestIn")
    into_adapter = [name for name, (_, target) in host.items() if target.startswith("actuationAdapter.")]
    assert into_adapter == ["drivingCommandOverSCORECommunication"], \
        "the driving command reaches the actuation adapter on the mw::com event only"
    bound = _binds(_body_of_definition(HOST))
    assert [inner for outer, inner in bound if outer == "ackermannControlOut"] == ["actuationAdapter.ackermannControlOut"], \
        "the adapter alone writes the simulator's control"


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
        assert records == [(short, f"{name}Record")], name
        record = braced_body(raw, f"item <'{short}'> {records[0][1]} : LogicalToSoftwareSignalMappingRecord")
        assert re.match(r"\s*doc\s*/\*", record), short
        stated = dict(re.findall(r'attribute\s*:>>\s*(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|SignalMappingDisposition::\w+)\s*;',
                                 record))
        assert tuple(stated) == RECORD_ATTRIBUTES, (short, tuple(stated))
        for attribute, value in stated.items():
            assert len(value) > 12 and not re.search(r"\b(TBD|TBC|TODO)\b|<[^']", value), (short, attribute)
        assert stated["disposition"] == "SignalMappingDisposition::candidate", short
        assert stated["owner"] == '"DE4SDV maintainers"', short
        assert stated["nextAction"].count("to evidence of record; none is started") == 1, short
    for name in ("SystemToSoftwareSignalMappingCandidate", "LogicalToSoftwareSignalMappingRecord",
                 "SignalMappingDisposition"):
        assert f"private import DE4SDV_MethodProcess::{name};" in _code(), name
    # each element that realizes a logical element and has a directed port has a mapping for each element it carries
    mapped = {(logical, path.rsplit("::", 1)[0]) for logical, path, _ in SIGNAL_MAPPINGS.values()}
    assert mapped == set(ALLOCATIONS.values())


def test_what_is_left_in_each_record_is_the_evidence_of_cases_that_are_not_started():
    assert list(RECORD_REQUIREMENTS) == [short for _, _, short in SIGNAL_MAPPINGS.values()]
    for short, requirements in RECORD_REQUIREMENTS.items():
        action = _record_value(short, "nextAction")
        left = re.search(r"bring the verification cases of REQ-DRIVING-(.+?) to evidence of record; none is started",
                         action)
        assert left, (short, action)
        assert _expand(left.group(1)) == requirements, (short, left.group(1))


def test_the_records_say_what_each_item_is_and_where_the_vss_typing_is():
    for short in NO_VEHICLE_SIGNAL:
        assert "no vehicle signal" in _record_value(short, "semanticSource"), short
    speed = _record_value("MAP-DRIVING-DA-VEHICLE-SPEED", "semanticSource")
    assert "Vehicle_Speed [km/h]" in speed
    rule = _record_value("MAP-DRIVING-DA-VEHICLE-SPEED", "transformationRule")
    for phrase in ("speed = |velocity| * 3.6 as the VSS km/h value", "speed / 3.6 in m/s",
                   "the speed reaches the planner only, not the perception"):
        assert phrase in rule, phrase
    command = _record_value("MAP-DRIVING-DA-COMMAND", "semanticSource")
    assert "Vehicle_ADAS_Driving_Command_Acceleration [m/s^2]" in command
    assert "Vehicle_ADAS_Driving_Command_SteeringAngle [degrees]" in command
    assert "REQ-DRIVING-038" in _record_value("MAP-DRIVING-DA-COMMAND", "softwareContractArtifact")
    warning = _record_value("MAP-DRIVING-DA-WARNING-REQUEST", "semanticSource")
    assert warning.startswith("the warning request of the candidate, typed at the port by "
                              "Vehicle_ADAS_AEBS_DriverWarning_IsActive")
    artifact = _record_value("MAP-DRIVING-DA-WARNING-REQUEST", "softwareContractArtifact")
    for hop in ("mw::com", "gatewayd", "someipd", "SOME/IP", "VXLAN", "Data Tunnel", "SDV Gateway",
                "REQ-DRIVING-043"):
        assert hop in artifact, hop
    assert "open until phase 10" in _record_value("MAP-DRIVING-DA-WARNING-REQUEST", "softwareContractMessage")
    assessment = _record_value("MAP-DRIVING-DA-ASSESSMENT", "transformationRule")
    assert ("the candidate computes no time to collision, no needed deceleration and no imminence, so the assessment of "
            "phase 6 is realized in part, and phase 10 judges the imminence from the simulator's ground truth") \
        in assessment
    record = _record_value("MAP-DRIVING-DA-CANDIDATE-RECORD", "softwareContractField")
    for phrase in ("vision_pilot.conf", "H.yaml", "the DE4SDV interface configuration", "the mw::com manifest",
                   "the network files", "the working directory"):
        assert phrase in record, phrase
    assert "never empty (gapCandidateBehaviorUnverified)" in _record_value("MAP-DRIVING-DA-CANDIDATE-RECORD",
                                                                          "transformationRule")


def test_the_warning_request_record_divides_the_share_of_the_path_and_the_presentation():
    timing = _flat(_record_value("MAP-DRIVING-DA-WARNING-REQUEST", "timingQualityAndState"))
    assert WARNING_SHARE in timing
    assert timing.endswith(WARNING_SHARE_BASIS)
    for figure in UNRECORDED_FIGURES:
        assert figure not in _raw() and figure not in GUIDE.read_text(encoding="utf-8"), figure


def test_a_warning_is_requested_for_the_forward_collision_warning_and_for_the_emergency_braking():
    """Both ranges of the one planned acceleration request the warning, so a plan that goes straight to the
    emergency braking still requests one. The rule is stated three times, and each copy is pinned."""
    rule = _record_value("MAP-DRIVING-DA-WARNING-REQUEST", "transformationRule")
    assert rule.startswith("requested = the plan's warnings hold FCW or AEB; issueTime = the capture simulation time "
                           "of the frame the plan was computed from; ")
    publisher = _doc("part def SCOREWarningRequestPublisher")
    assert "requested is true while the plan holds a forward-collision warning or an emergency braking" in publisher
    assert ("the issue time is the capture simulation time of the frame the plan was computed from, which the "
            "interface module keeps from the camera interface for the pass") in publisher
    assert _record_value("MAP-DRIVING-DA-PLANNED-WARNINGS", "softwareContractField").endswith(
        "the publisher reads FCW and AEB")
    assert _record_value("MAP-DRIVING-DA-PLANNED-WARNINGS", "transformationRule").startswith(
        "FCW for a planned acceleration from -5.0 to -3.0 m/s², AEB below -5.0 m/s² (planning.cpp:113-121)")


def test_the_command_record_places_the_detectable_form_the_rejection_and_the_steering_sign():
    unit = _record_value("MAP-DRIVING-DA-COMMAND", "dataTypeAndUnit")
    for phrase in ("steeringAngle float degrees, positive to the left", "issueTime in simulation seconds",
                   "sequenceCount an unsigned 32-bit count from 1 in each run",
                   "checkValue the CRC-32 over the other fields"):
        assert phrase in unit, phrase
    # the sign of the VSS steering angle is the extension's, read from the extension (review R10, P4)
    extension = braced_body(EXTENSIONS.read_text(encoding="utf-8"),
                            "@VssSignalMetadata about Vehicle_ADAS_Driving_Command_SteeringAngle")
    assert "Positive = degrees to the left." in extension
    timing = _record_value("MAP-DRIVING-DA-COMMAND", "timingQualityAndState")
    assert timing == ("one command per plan; none before the candidate record has arrived (REQ-DRIVING-044); the "
                      "issue time is the capture simulation time of the frame the command was computed from")
    rule = _record_value("MAP-DRIVING-DA-COMMAND", "transformationRule")
    assert rule.startswith("acceleration unchanged; " + STEERING_RULE)
    assert "steeringAngle = steering[1]" not in rule and "lateral_" not in _raw(), "the sign follows upstream's path"
    for phrase in ("speed = max(0, v + 2 * acceleration) with v the speed of the ego vehicle in the newest world "
                   "snapshot", "acceleration unchanged and jerk = 10.0",
                   "(carla_control_publisher_node.py:44-53); steerSpeed stays at its default of 0.0"):
        assert phrase in rule, phrase
    assert rule.endswith(REJECTION_RULE)
    # the second copy of the sign, in the plan record (each copy is pinned)
    assert _record_value("MAP-DRIVING-DA-PLAN", "dataTypeAndUnit") == (
        "acceleration float m/s², negative decelerates; steering a tyre angle in rad, taken in the sign of CARLA's "
        "steer, positive to the right, as upstream's own simulator path takes it (ASM-DRIVING-006)")
    assert _record_value("MAP-DRIVING-DA-COMMAND", "nextAction").startswith(
        "run the calibrations of ASM-DRIVING-005 and ASM-DRIVING-006")


def test_the_capture_time_travels_inside_the_interface_module_and_dropped_images_are_counted():
    """Review R2, R3 and R4: the frame reaches the loop without a time, so the interface module keeps it; the
    candidate's fusion takes two processed frames as 0.1 s apart, so each dropped image is counted and a run with one
    in its judged window is not judged; the issue time and the world time are read on one clock."""
    camera = _doc("part def SCORECameraInterface :> PhysicalAllocationElement")
    for phrase in ("drops older images and counts each image it drops, as upstream's own camera interface counts its "
                   "dropped frames",
                   "The frame goes to the loop without a time (camera_interface.hpp:18): the module keeps its capture "
                   "time, the simulation time of the world snapshot the image was rendered in, and the vehicle "
                   "interface and the warning request publisher, modules of the same interface, read it in the same "
                   "pass of the loop."):
        assert phrase in camera, phrase
    vehicle = _doc("part def SCOREVehicleInterface :> PhysicalAllocationElement")
    assert ("adds the issue time, the capture simulation time of the frame the command was computed from, which the "
            "interface module keeps from the camera interface for the pass,") in vehicle
    timing = _record_value("MAP-DRIVING-DA-CAMERA-IMAGE", "timingQualityAndState")
    assert timing == ("one image per 0.1 s of simulation time; the camera interface hands on the newest image, drops "
                      "older ones and counts each image it drops; the candidate's fusion takes two processed frames "
                      "as 0.1 s apart, its nominal step, since no step is passed to it (longitudinal_fusion.hpp:40, "
                      "inference.cpp:206-207), so every run reports the images dropped, and phase 10 judges no run "
                      "whose judged window holds a dropped image; the capture time is the simulation time of the "
                      "world snapshot the image was rendered in")
    field = _record_value("MAP-DRIVING-DA-CAMERA-IMAGE", "softwareContractField")
    assert field.endswith("out: the image to the loop, candidate, and its capture time to the vehicle interface and "
                          "the warning request publisher inside the interface module, candidate")
    assert "frame index" not in _raw() and "frame index" not in GUIDE.read_text(encoding="utf-8")


def test_the_texts_place_the_seam_the_hashes_and_the_record_delivery_as_the_pinned_code_does():
    """Review R5, R13 and R11: the interface selection runs once in the main function, the record hashes what the
    process reads for its configuration, and the delivery of the record to a later subscriber is a readiness item."""
    assert "main loop (VisionPilot/app/vision_pilot.cpp:59-79" not in _head()
    application = _doc(f"part def {APPLICATION}")
    assert ("Its main function takes the S-CORE branch beside the existing interface selection before the loop "
            "(vision_pilot.cpp:59-79), and its loop hands the plan's warnings to the warning request publisher after "
            "the write at vision_pilot.cpp:174.") in application
    hashed = "the SHA-256 of each configuration, calibration, manifest and network file that the candidate's process reads"
    recorder = _doc("part def CandidateIdentityRecordingApplication :> PhysicalAllocationElement")
    assert hashed in recorder and "opens" not in recorder
    assert hashed in _record_value("MAP-DRIVING-DA-CANDIDATE-RECORD", "softwareContractField")
    assert _record_value("MAP-DRIVING-DA-CANDIDATE-RECORD", "timingQualityAndState").endswith(
        "the record has to reach the vehicle interface, which subscribes after it was published; how mw::com "
        "delivers it is a readiness item (phase8ScoreIntegrationPlaced)")


# -- what the package records --------------------------------------------------------------------------------------


def test_the_package_head_records_the_owner_decision_of_2026_11_15():
    head = _head()
    for statement in OWNER_DECISION:
        assert statement in head, statement
    for statement in CARRIED_OVER:
        assert statement in head, statement
    for statement in GPU_DECISION:
        assert statement in head, statement
    assert head.index(GPU_DECISION[0]) < head.index("Carried over from the dated decisions of INC-DRIVING-001"), \
        "a decision of this phase, not one carried over"
    for alternative in ALTERNATIVES:
        assert alternative in head, alternative
    assert ("the simulator receives the candidate's steering unchanged and the planned acceleration, as on that path. "
            "That the vehicle follows the commanded deceleration is ASM-DRIVING-005, and that the candidate's steering "
            "turns it toward its lane centre is ASM-DRIVING-006.") in head
    for phrase in ("An allocation here is a responsibility assignment, no deployment, execution or runtime claim; a "
                   "signal mapping is no interoperability claim",
                   "Nothing in this package claims a requirement met or a case run."):
        assert phrase in head, phrase


def test_the_gpu_decision_retires_the_processor_statements():
    """The readiness probe and the GPU decision of 2026-11-15 settle what phase 8 left open: no text keeps it open."""
    model = _flat(_raw())
    guide = " ".join(GUIDE.read_text(encoding="utf-8").split())
    for statement in RETIRED_HOST_STATEMENTS:
        assert statement not in model and statement not in guide, statement


def test_the_comments_record_what_phase_8_settled_on_the_framing_records():
    code = _code()
    declared = {name: tuple(part.strip() for part in about.split(",")) for name, about in re.findall(
        r"\bcomment\s+(\w+)\s+about\s+([\w,\s]+?)\s*(?=$|\n)", code, re.M)}
    assert declared == COMMENTS
    for name, statements in COMMENT_STATEMENTS.items():
        text = _comment(name)
        for statement in statements:
            assert statement in text, (name, statement)
    for gap in ("gapNoSeparateEmergencyFunction", "gapWarningOutput", "gapCandidateBehaviorUnverified",
                "gapScoreIntegration"):
        assert f"private import DE4SDV_DriverAssistanceFraming::{gap};" in code, gap
    for assumption in ("asmProcessorInferenceSufficient", "asmSimulatorPathUsable"):
        assert f"private import DE4SDV_DriverAssistanceFraming::{assumption};" in code, assumption
    assert "private import DE4SDV_DriverAssistanceNeedsRequirements::reqDetectableDrivingCommand;" in code


def test_the_assumption_of_the_realization_is_recorded_with_its_short_name_and_no_gap_is_added():
    code = _code()
    assert dict(re.findall(r"\bpart\s+<'(ASM-DRIVING-\d{3})'>\s+(\w+)\s*:\s*IncrementAssumption\s*\{", code)) == ASSUMPTIONS
    assert not re.search(r"<'GAP-DRIVING-\d{3}'>", code), "the open points stay with the framing's records"
    assert len(re.findall(r"<'(?:ASM|GAP)-[A-Z]+-\d{3}'>", code)) == 2
    doc = _doc("part <'ASM-DRIVING-005'> asmActuationFollowsCommandedDeceleration : IncrementAssumption")
    for statement in ASSUMPTION_STATEMENTS:
        assert statement in doc, statement
    steering = _doc("part <'ASM-DRIVING-006'> asmCandidateSteeringTurnsTowardLaneCentre : IncrementAssumption")
    for statement in STEERING_ASSUMPTION_STATEMENTS:
        assert statement in steering, statement
    assert "private import DE4SDV_MethodContext::*;" in code


def test_the_slice_names_no_upstream_thread_and_no_reading_the_maintainers_have_not_seen():
    raw = _raw()
    flat = _flat(raw)
    assert not re.search(r"(?i)\b(?:issue|pull request|PR)\s*#?\d+|#\d{2,}", flat), "no upstream issue or PR number"
    assert not re.search(r"(?i)\bpull requests?\b", flat)
    for reading in UNSHOWN_READINGS:
        assert reading not in raw, reading
    assert not re.search(r"(?i)\b(?:the owner said|owner's words|in his words)\b", flat), "decisions, never quotes"
    assert not re.search(r"(?i)\b(?:clause|paragraph|annex)\s+\d", flat), "regulation titles, not clause numbers"


def test_the_element_docs_make_no_assurance_claim():
    declarations = [f"part def {d} :> PhysicalAllocationElement" for d in ELEMENT_DEFINITIONS]
    declarations += [f"part def {name}" for name in NOT_ELEMENTS]
    for declaration in declarations:
        doc = _doc(declaration)
        found = [word for word in CLAIM_WORDS if word in doc.lower()]
        assert not found, (declaration, found)
    assert not [word for word in CLAIM_WORDS if word in _head().lower()]
    assert not re.search(r"\b(realizedBy|deployedTo|validatedBy|constrainedBy|satisfy|verify)\b",
                         re.sub(r'"(?:[^"\\]|\\.)*"', '""', _code()))


# -- views ---------------------------------------------------------------------------------------------------------


def test_the_package_publishes_exactly_one_view_per_question():
    declared = re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M)
    assert sorted(declared) == sorted(VIEWS) and len(declared) == 3


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
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", view) == exposes
    if render:
        assert render in view
        assert "filter not (@ SysML::AllocationUsage);" in view, "SysIDE draws the package's allocations otherwise"
    else:
        assert "render as" not in view, "the view type selects the kind"


def test_the_tree_and_the_path_view_take_the_forms_the_precedent_rendered():
    code = _code()
    tree = braced_body(code, f"view {STRUCTURE_VIEW}")
    assert "filter not (@ SysML::BindingConnectorAsUsage);" in tree, "a bind draws as a box with two ends in a tree"
    path = braced_body(code, f"view {PATH_VIEW}")
    assert "attribute depth = -1;" in path and "attribute showAnnotationRows = false;" in path
    assert "BindingConnectorAsUsage" not in path, "the host's and the process's binds draw as edges between exposed ports"
    doc = _doc(f"view {PATH_VIEW}")
    for phrase in ("scoreCommandAndWarningPathConcern", "emergencyBrakingIndependenceConcern",
                   "the only element that writes the simulator's Ackermann control",
                   "the emergency braking leaves in the one driving command",
                   "not by a function-by-software matrix", "The guests are drawn in the structure tree only."):
        assert phrase in doc, phrase


def test_the_matrix_maps_the_logical_elements_to_the_software_with_reference_elements():
    view = braced_body(_code(), f"view {MATRIX_VIEW} : MVD::MatrixView")
    rows = braced_body(view, "view :>> rowView")
    columns = braced_body(view, "view :>> columnView")
    cells = braced_body(view, "view :>> cellView")
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", rows) == [f"{LOGICAL_SYSTEM}::{element}" for element in LOGICAL_ELEMENTS]
    assert len(re.findall(r"\bexpose\s+([\w:]+)\s*;", columns)) == 6
    for axis in (rows, columns):
        assert "attribute :>> includeReferenceElements = true;" in axis
        assert "attribute :>> representation = Rep::name;" in axis
    assert f"expose {PACKAGE}::*;" in cells
    assert "attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;" in cells
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"matrix-{MATRIX_VIEW}"]
    assert metadata.title and "four logical elements" in metadata.description and "six software elements" in \
        metadata.description


@pytest.mark.parametrize("concern_name", sorted(CATALOGUE_CONCERNS), ids=sorted(CATALOGUE_CONCERNS))
def test_each_phase_8_concern_is_typed_by_the_catalogue_and_held_by_the_party_it_serves(concern_name):
    catalogue, stakeholders = CATALOGUE_CONCERNS[concern_name]
    concern = braced_body(_code(), f"concern {concern_name} : {catalogue}")
    members = re.findall(r"\b(subject|stakeholder)\b", concern)
    assert members and members[0] == "subject"
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == stakeholders
    assert "need" in _doc(f"concern {concern_name} : {catalogue}")


def test_the_phase_1_physical_concerns_are_framed_here_in_their_domain_and_need_no_deviation():
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    code = _code()
    for concern, catalogue in FRAMING_CONCERNS.items():
        assert re.search(rf"\bconcern\s+{concern}\s*:\s*{catalogue}\b", framing), concern
        assert f"private import DE4SDV_DriverAssistanceFraming::{concern};" in code, concern
        assert not re.search(rf"\bconcern\s+{concern}\b", code), "framed, never redeclared"
    import test_views_per_phase as views

    assert not [key for key in views.KNOWN_DEVIATIONS if key[0] == "INC-DRIVING-002"], "the method's own list"


# -- registrations -------------------------------------------------------------------------------------------------


def test_the_allocation_file_is_governed_with_its_six_endpoint_definitions():
    import test_trace_allocation_completeness as trace

    assert trace.ASSIST_P == MODEL
    assert trace.ALLOCATION_FILES[trace.ASSIST_P] == (
        (trace.ASSIST_P, trace.ASSIST_L), {(trace.LOGICAL, trace.PHYSICAL): 7},
        {"SystemToSoftwareSignalMappingCandidate": 8}, (trace.LOGICAL, trace.PHYSICAL))
    assert trace.GOVERNED[trace.ASSIST_P] == (trace.PHYSICAL, set(ELEMENT_DEFINITIONS))
    assert trace.ASSIST_P in trace.LINEAGE_FILES
    assert trace.NOT_ENDPOINTS[trace.ASSIST_P] == set(NOT_ELEMENTS)


def test_the_guide_describes_phase_8_and_names_the_next_work():
    guide = GUIDE.read_text(encoding="utf-8")
    flat = " ".join(guide.split())
    order = [guide.index(heading) for heading in ("## Logical architecture (Phase 7)",
                                                  "## Physical and software realization (Phase 8)",
                                                  "## What the framing already records as open")]
    assert order == sorted(order)
    section = " ".join(guide.split("## Physical and software realization (Phase 8)", 1)[1].split("\n## ", 1)[0].split())
    for phrase in ("(../../textual-notation-of-model/packages/features/driving/"
                   "driver_assistance_physical_software_realization.sysml)",
                   "On 2026-11-15 the owner chose that the candidate's process becomes an Eclipse S-CORE application "
                   "through a DE4SDV S-CORE interface module",
                   "every verdict names the build, 014e0e7a with the DE4SDV S-CORE interface",
                   "the warning requester and the driving commander share the planner module",
                   "applies nothing in place of a rejected command", "no stop response",
                   "0.1 s for the path and 0.1 s for the presentation", "`ASM-DRIVING-005`",
                   "`reqDrivingCommandOverSCORE`", "`reqWarningRequestOverSCORE`",
                   "gives the simulator the candidate's steering unchanged, as that path does",
                   "so the vehicle interface writes the negative of the candidate's steering, which the integration "
                   "takes in the sign of CARLA's steer, positive to the right",
                   "`ASM-DRIVING-006`", "counts the images it drops",
                   "an S-CORE branch beside the existing interface selection in the application's main function, "
                   "before its loop",
                   "hashes every configuration, calibration, manifest and network file the candidate's process reads",
                   "CARLA 0.9.16 in synchronous mode with a fixed step of 0.1 s, paced at wall-clock speed",
                   "2026-11-08", "2026-11-09",
                   "On 2026-11-15 the owner also chose a GPU of its own for the S-CORE host, an NVIDIA L4, for the "
                   "candidate's networks",
                   "the readiness probe of Phase 8 found the processor alone too slow for the 0.1 s cycle",
                   "tests/test_driver_assistance_physical_software_realization.py"):
        assert phrase in section, phrase
    assert "VisionPilot/" not in section and ".cpp" not in section, "the guide carries no upstream paths"
    assert "like the VSS steering angle" not in section and "changes its sign" not in section, "review R1"
    assert ("**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 classification, "
            "Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture, Phase 7 logical "
            "architecture and Phase 8 physical and software realization, proposal.**") in flat
    assert ("The next model obligation is **Phase 9**: variability and configuration, which makes the realization a "
            "configured product of the product line; its first gate is `incrementHasConfiguredProduct`.") in flat
    assert "The next model obligation is **Phase 8**" not in flat
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert "tests/test_driver_assistance_physical_software_realization.py" in check


def test_the_upstream_record_names_what_phase_8_read_at_the_pin():
    record = UPSTREAM.read_text(encoding="utf-8")
    section = record.split("\n## VisionPilot\n", 1)[1].split("\n## ", 1)[0]
    text = " ".join(section.split())
    assert ("Read for the physical and software realization of INC-DRIVING-002 on 2026-11-15, at the same commit, "
            "which phase 8 takes for the bench with the DE4SDV S-CORE interface module") in text
    for path in ("VisionPilot/modules/safety_guardian/fusion/include/fusion/longitudinal_fusion.hpp",
                 "VisionPilot/modules/models/src/inference.cpp",
                 "VisionPilot/modules/sensing/camera_interface/include/camera_interface/camera_interface.hpp",
                 "VisionPilot/modules/middleware_interfaces/ros2_interface/vehicle_ros2_interface/src/"
                 "vehicle_ros2_interface.cpp",
                 "VisionPilot/modules/common/include/common/types.hpp",
                 "VisionPilot/modules/config/src/vision_pilot_config.cpp",
                 "VisionPilot/modules/engine/src/onnx_engine.cpp",
                 "Simulation/CARLA/ROS2/src/carla_bridge_bringup/scripts/config_carla.py",
                 "Simulation/CARLA/ROS2/config/carla916.json",
                 "Simulation/CARLA/ROS2/src/carla_control_publisher/carla_control_publisher/"
                 "carla_control_publisher_node.py"):
        assert f"https://github.com/autowarefoundation/vision_pilot/blob/{PIN}/{path}" in section, path
    assert f"https://github.com/autowarefoundation/vision_pilot/blob/{PIN}/VisionPilot/config/vision_pilot.conf#L11-L17" \
        in section, "the provider and the precision of the configuration that upstream ships"
    assert ("https://github.com/carla-simulator/carla/blob/0.9.16/Docs/python_api.md#carlavehicleackermanncontrol"
            in section), "the API reference of the simulator's Ackermann control, at the release the bench runs"
    assert ("https://github.com/carla-simulator/carla/blob/0.9.16/LibCarla/source/carla/ros2/subscribers/"
            "AckermannControlSubscriber.cpp") in section
    assert "lateral_planning.cpp" not in section and "lateral_fusion.hpp" not in section, "the model cites neither"
    for phrase in ("lines 13 to 18 give the closest object in the path with its distance and its velocity, negative "
                   "while it approaches, and line 40 a nominal step of 0.10 s",
                   "lines 152 to 154 keep the previous and the current processed frame, and lines 206 and 207 update "
                   "the fusion without a step", "line 18 returns the newest image alone",
                   "lines 64 to 68 publish the steering that the loop writes as it is",
                   "line 49 gives the steering to the Ackermann control's steering angle without a change",
                   "line 12 sets the control's steer to the message's steering angle",
                   "run the simulator in synchronous mode with a fixed step of 0.1 s",
                   "lines 32 to 46 create the session for the configured provider, cpu, cuda or tensorrt, and refuse "
                   "any other; lines 63 to 76 create the CUDA session, with ONNX Runtime's CUDA execution provider on "
                   "the configured device",
                   "line 11 sets the provider to cuda and line 17 the precision to fp32",
                   "steer in rad, positive to the right, steer_speed in rad/s, speed in m/s, acceleration in m/s² and "
                   "jerk in m/s³, each with a default of 0.0"):
        assert phrase in text, phrase


def test_every_upstream_file_the_model_cites_by_line_is_in_the_upstream_record():
    """Review R9, generalized: each file that the model cites by line is read in upstream.md, by its file name."""
    record = UPSTREAM.read_text(encoding="utf-8")
    cited = sorted(set(re.findall(r"([\w./-]+\.(?:cpp|hpp|py|json|md)):\d", _raw())))
    assert len(cited) >= 12, cited
    assert not [path for path in cited if path.rsplit("/", 1)[-1] not in record]
