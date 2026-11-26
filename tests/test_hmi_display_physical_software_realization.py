"""Content pins for the HMI display physical and software realization (phase 8), not semantic validation.

INC-HMI-001 phase 8 places the three logical elements of phase 7 on software, and the paths of the inputs from the
SDV Core VM on the elements that carry them, as REQ-HMI-009 asks. Method Check holds the DefinePhysicalRealization
rule (each logical element allocated to a physical allocation element; advisories, each physical element carries a
logical element, each crossing has a signal mapping with its semantic source). These pins hold what the design
settled on top of it:

- the placement (owner decision of 2026-11-25): the identity recording service and the composition of the display on
  the central computer, the scene drawing app in the IVI VM, the high availability renderer in the SDV Media VM, and
  the vehicle data publisher in the SDV Core VM on the path to the renderer; the presenter carried by the renderer and
  the composition together; no other warning presentation in the IVI VM;
- System 1 only: the central computer is a definition of its own that references the generic layers of the platform
  stack, which phase 9 binds, and nothing here is typed by the bench's guest host or its layers; the guest host
  appears only in sentences that say what stands in for an element of the vehicle;
- the seven connections between the VMs and the central computer, each from an out port to an in port of one item,
  and nothing that leads back;
- eight signal mappings with complete records, the vehicle speed and the distance to the object that the system
  acts on typed by COVESA VSS at the ports, and REQ-HMI-009 carried by a dependency from the physical system;
- three views, each framed by a concern of the Physical domain, two of them the phase 1 concerns of the renderer;
- the texts of record of the design whole, and the guide's Phase 8 section block by block.
"""

from pathlib import Path
import hashlib
import re

import pytest

from sysml_shapes import braced_body, strip_comments
from test_hmi_display_framing import APPROVAL, PAST_BEHAVIOR
from test_hmi_display_functional_architecture import EXCLUDED_WORD_SHA256

ROOT = Path(__file__).resolve().parents[1]
HMI = ROOT / "textual-notation-of-model/packages/features/hmi"
MODEL = HMI / "hmi_display_physical_software_realization.sysml"
LOGICAL = HMI / "hmi_display_logical_architecture.sysml"
NEEDS = HMI / "hmi_display_needs_requirements.sysml"
FRAMING = HMI / "hmi_display_framing.sysml"
ASSIST_P = ROOT / "textual-notation-of-model/packages/features/driving" / \
    "driver_assistance_physical_software_realization.sysml"
GUIDE = ROOT / "docs/guides/hmi-display-increment.md"
MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
PACKAGE = "DE4SDV_HmiDisplayPhysicalSoftwareRealization"
LOGICAL_PACKAGE = "DE4SDV_HmiDisplayLogicalArchitecture"
LOGICAL_SYSTEM = "HmiDisplayLogicalSystem"
SYSTEM = "HmiDisplayPhysicalSystem"
SYSTEM_USAGE = "hmiDisplayPhysicalSystem"
CENTRAL = "HmiDisplayCentralComputer"

#: The four software elements, the only physical allocation elements of the package, in the order of the file.
ELEMENT_DEFINITIONS = ["DisplayIdentityRecordingService", "SceneDrawingApplication", "HighAvailabilityRenderer",
                       "DisplayPlaneComposition"]
#: The other part definitions: the path element, the three VMs, the central computer and the system.
NOT_ELEMENTS = ["RendererVehicleDataPublisher", "HmiDisplaySDVCoreGuest", "HmiDisplayIVIGuest",
                "HmiDisplaySDVMediaGuest", CENTRAL, SYSTEM]

#: Each part definition -> its own ports (name, port definition), in order.
PORTS = {
    "DisplayIdentityRecordingService": [],
    "SceneDrawingApplication": [("sceneMessageIn", "DisplaySceneMessageIn"), ("heartbeatOut", "DrawnSceneHeartbeatOut"),
                                ("iviPlaneOut", "DisplayPlaneOut")],
    "HighAvailabilityRenderer": [("speedSampleIn", "DisplayVehicleSpeedSampleIn"),
                                 ("warningEventIn", "WarningRequestEventIn"), ("sceneTimeIn", "DisplaySceneTimeIn"),
                                 ("heartbeatIn", "DrawnSceneHeartbeatIn"), ("rendererPlaneOut", "DisplayPlaneOut"),
                                 ("chimeOut", "CollisionWarningChimeOut")],
    "DisplayPlaneComposition": [("iviPlaneIn", "DisplayPlaneIn"), ("rendererPlaneIn", "DisplayPlaneIn"),
                                ("displayFrameOut", "ComposedDisplayFrameOut")],
    "RendererVehicleDataPublisher": [("speedSampleIn", "DisplayVehicleSpeedSampleIn"),
                                     ("warningEventIn", "WarningRequestEventIn"),
                                     ("sceneMessageIn", "DisplaySceneMessageIn"),
                                     ("speedSampleOut", "DisplayVehicleSpeedSampleOut"),
                                     ("warningEventOut", "WarningRequestEventOut"),
                                     ("sceneTimeOut", "DisplaySceneTimeOut")],
    "HmiDisplaySDVCoreGuest": [("warningSomeIpIn", "WarningRequestEventIn"),
                               ("speedSampleIn", "DisplayVehicleSpeedSampleIn"),
                               ("sceneMessageIn", "DisplaySceneMessageIn"),
                               ("sceneMessageOut", "DisplaySceneMessageOut"),
                               ("speedSampleOut", "DisplayVehicleSpeedSampleOut"),
                               ("warningEventOut", "WarningRequestEventOut"), ("sceneTimeOut", "DisplaySceneTimeOut")],
    "HmiDisplayIVIGuest": [("sceneMessageIn", "DisplaySceneMessageIn"), ("heartbeatOut", "DrawnSceneHeartbeatOut"),
                           ("iviPlaneOut", "DisplayPlaneOut")],
    "HmiDisplaySDVMediaGuest": [("speedSampleIn", "DisplayVehicleSpeedSampleIn"),
                                ("warningEventIn", "WarningRequestEventIn"), ("sceneTimeIn", "DisplaySceneTimeIn"),
                                ("heartbeatIn", "DrawnSceneHeartbeatIn"), ("rendererPlaneOut", "DisplayPlaneOut"),
                                ("chimeOut", "CollisionWarningChimeOut")],
    CENTRAL: [("iviPlaneIn", "DisplayPlaneIn"), ("rendererPlaneIn", "DisplayPlaneIn"),
              ("displayFrameOut", "ComposedDisplayFrameOut")],
    SYSTEM: [],
}
#: Each container definition -> its owned parts (keyword, name, type), in order.
PARTS = {
    "HmiDisplaySDVCoreGuest": [("part", "os", "AndroidHLOS"), ("part", "sdvMiddleware", "AndroidSDVMiddleware"),
                               ("ref part", "sdvCore", "SDVCoreBoundary"),
                               ("part", "vehicleDataPublisher", "RendererVehicleDataPublisher")],
    "HmiDisplayIVIGuest": [("part", "os", "AndroidHLOS"), ("part", "sdvGateway", "SDVGatewayOnIVIBoundary"),
                           ("part", "sceneDrawingApp", "SceneDrawingApplication")],
    "HmiDisplaySDVMediaGuest": [("ref part", "os", "OSPlatformLayer"),
                                ("part", "highAvailabilityRenderer", "HighAvailabilityRenderer")],
    CENTRAL: [("ref part", "os", "OSPlatformLayer"), ("ref part", "hypervisor", "HypervisorLayer"),
              ("part", "identityRecordingService", "DisplayIdentityRecordingService"),
              ("part", "planeComposition", "DisplayPlaneComposition")],
    SYSTEM: [("part", "centralComputer", CENTRAL), ("part", "hmiSDVCoreGuest", "HmiDisplaySDVCoreGuest"),
             ("part", "hmiIVIGuest", "HmiDisplayIVIGuest"), ("part", "hmiSDVMediaGuest", "HmiDisplaySDVMediaGuest")],
}
#: The binds inside each container, in order.
BINDS = {
    "HmiDisplaySDVCoreGuest": [("sdvCore", "sdvMiddleware"), ("warningSomeIpIn", "sdvCore.someIp.someIpPort"),
                               ("speedSampleIn", "sdvCore.vsidlMiddleware.signalAccessPort"),
                               ("sceneMessageIn", "sdvCore.dataTunnel.topicPublishPort"),
                               ("sceneMessageOut", "sdvCore.dataTunnel.topicSubscribePort"),
                               ("speedSampleOut", "vehicleDataPublisher.speedSampleOut"),
                               ("warningEventOut", "vehicleDataPublisher.warningEventOut"),
                               ("sceneTimeOut", "vehicleDataPublisher.sceneTimeOut")],
    "HmiDisplayIVIGuest": [("sceneMessageIn", "sdvGateway.dataTunnelPort"),
                           ("heartbeatOut", "sceneDrawingApp.heartbeatOut"),
                           ("iviPlaneOut", "sceneDrawingApp.iviPlaneOut")],
    "HmiDisplaySDVMediaGuest": [(port, f"highAvailabilityRenderer.{port}") for port in (
        "speedSampleIn", "warningEventIn", "sceneTimeIn", "heartbeatIn", "rendererPlaneOut", "chimeOut")],
    CENTRAL: [(port, f"planeComposition.{port}") for port in ("iviPlaneIn", "rendererPlaneIn", "displayFrameOut")],
    SYSTEM: [],
}
#: The connections inside each container, in order: (name, source, target).
CONNECTIONS = {
    "HmiDisplaySDVCoreGuest": [
        ("warningTopicPublishedByInterop", "sdvCore.someIp.topicPublishOut", "sdvCore.dataTunnel.topicPublishPort"),
        ("warningTopicToPublisher", "sdvCore.dataTunnel.topicSubscribePort", "vehicleDataPublisher.warningEventIn"),
        ("sceneTopicToPublisher", "sdvCore.dataTunnel.topicSubscribePort", "vehicleDataPublisher.sceneMessageIn"),
        ("speedDataToPublisher", "sdvCore.vsidlMiddleware.signalAccessPort", "vehicleDataPublisher.speedSampleIn")],
    "HmiDisplayIVIGuest": [("sceneThroughSDVGateway", "sdvGateway.clientPort", "sceneDrawingApp.sceneMessageIn")],
    "HmiDisplaySDVMediaGuest": [],
    CENTRAL: [],
    SYSTEM: [
        ("sceneTopicToIVIOverDataTunnel", "hmiSDVCoreGuest.sceneMessageOut", "hmiIVIGuest.sceneMessageIn"),
        ("speedToRendererAcrossVMs", "hmiSDVCoreGuest.speedSampleOut", "hmiSDVMediaGuest.speedSampleIn"),
        ("warningToRendererAcrossVMs", "hmiSDVCoreGuest.warningEventOut", "hmiSDVMediaGuest.warningEventIn"),
        ("sceneTimeToRendererAcrossVMs", "hmiSDVCoreGuest.sceneTimeOut", "hmiSDVMediaGuest.sceneTimeIn"),
        ("drawnSceneHeartbeatToRenderer", "hmiIVIGuest.heartbeatOut", "hmiSDVMediaGuest.heartbeatIn"),
        ("iviPlaneToComposition", "hmiIVIGuest.iviPlaneOut", "centralComputer.iviPlaneIn"),
        ("rendererPlaneToComposition", "hmiSDVMediaGuest.rendererPlaneOut", "centralComputer.rendererPlaneIn")],
}
#: The hypervisor interfaces of the system: each VM's operating system under the central computer's hypervisor.
INTERFACES = [(f"{guest}UnderHypervisor", f"{guest}.os.hypervisorPort", "centralComputer.hypervisor.guestPort")
              for guest in ("hmiSDVCoreGuest", "hmiIVIGuest", "hmiSDVMediaGuest")]

#: The item definitions of the package -> (supertype or None, attributes (name, type)).
ITEMS = {
    "DisplaySceneMessage": ("DisplaySceneInput",
                            [("obstacleDistance", "Vehicle_ADAS_ObstacleDetection_Distance[0..1]")]),
    "DisplayVehicleSpeedSample": ("VehicleSpeed", [("speed", "Vehicle_Speed"), ("sampleTime", "Real")]),
    "DisplaySceneTime": (None, [("captureTime", "Real")]),
    "DrawnSceneHeartbeat": (None, [("sceneCaptureTime", "Real")]),
    "DisplayPlane": (None, []),
    "ComposedDisplayFrame": ("DisplayContentOutput", []),
    "CollisionWarningChime": (None, []),
}
#: The port definitions of the package -> (direction, item, item type): one item each, one direction.
PORT_ITEMS = {
    "DisplaySceneMessageOut": ("out", "sceneMessage", "DisplaySceneMessage"),
    "DisplaySceneMessageIn": ("in", "sceneMessage", "DisplaySceneMessage"),
    "DisplayVehicleSpeedSampleOut": ("out", "speedSample", "DisplayVehicleSpeedSample"),
    "DisplayVehicleSpeedSampleIn": ("in", "speedSample", "DisplayVehicleSpeedSample"),
    "DisplaySceneTimeOut": ("out", "sceneTime", "DisplaySceneTime"),
    "DisplaySceneTimeIn": ("in", "sceneTime", "DisplaySceneTime"),
    "DrawnSceneHeartbeatOut": ("out", "heartbeat", "DrawnSceneHeartbeat"),
    "DrawnSceneHeartbeatIn": ("in", "heartbeat", "DrawnSceneHeartbeat"),
    "DisplayPlaneOut": ("out", "plane", "DisplayPlane"),
    "DisplayPlaneIn": ("in", "plane", "DisplayPlane"),
    "ComposedDisplayFrameOut": ("out", "displayFrame", "ComposedDisplayFrame"),
    "CollisionWarningChimeOut": ("out", "chime", "CollisionWarningChime"),
}
#: The warning request keeps the payload and the port definitions of the driver-assistance realization.
IMPORTED_PORT_DEFS = ("WarningRequestEventIn", "WarningRequestEventOut")

#: The four allocations of the logical elements, in order: (name, logical element, physical element).
ALLOCATIONS = [
    ("recorderToIdentityRecordingService", "displayIdentityRecorder", "centralComputer::identityRecordingService"),
    ("drawerToSceneDrawingApplication", "sceneDrawer", "hmiIVIGuest::sceneDrawingApp"),
    ("presenterToHighAvailabilityRenderer", "displayPresenter", "hmiSDVMediaGuest::highAvailabilityRenderer"),
    ("presenterToPlaneComposition", "displayPresenter", "centralComputer::planeComposition"),
]
#: The eight signal mappings, in order: (allocation, short name, record, logical element, port chain).
MAPPINGS = [
    ("sceneIngressMapping", "MAP-HMI-SCENE", "sceneIngressMappingRecord", "sceneDrawer",
     "hmiIVIGuest.sceneDrawingApp.sceneMessageIn"),
    ("drawnSceneHeartbeatMapping", "MAP-HMI-DRAWN-SCENE-HEARTBEAT", "drawnSceneHeartbeatMappingRecord", "sceneDrawer",
     "hmiIVIGuest.sceneDrawingApp.heartbeatOut"),
    ("iviPlaneMapping", "MAP-HMI-IVI-PLANE", "iviPlaneMappingRecord", "sceneDrawer",
     "hmiIVIGuest.sceneDrawingApp.iviPlaneOut"),
    ("displaySpeedMapping", "MAP-HMI-VEHICLE-SPEED", "displaySpeedMappingRecord", "displayPresenter",
     "hmiSDVMediaGuest.highAvailabilityRenderer.speedSampleIn"),
    ("rendererWarningRequestMapping", "MAP-HMI-WARNING-REQUEST", "rendererWarningRequestMappingRecord",
     "displayPresenter", "hmiSDVMediaGuest.highAvailabilityRenderer.warningEventIn"),
    ("sceneTimeMapping", "MAP-HMI-SCENE-TIME", "sceneTimeMappingRecord", "displayPresenter",
     "hmiSDVMediaGuest.highAvailabilityRenderer.sceneTimeIn"),
    ("warningChimeMapping", "MAP-HMI-WARNING-CHIME", "warningChimeMappingRecord", "displayPresenter",
     "hmiSDVMediaGuest.highAvailabilityRenderer.chimeOut"),
    ("shownContentMapping", "MAP-HMI-SHOWN-CONTENT", "shownContentMappingRecord", "displayPresenter",
     "centralComputer.planeComposition.displayFrameOut"),
]
#: The attributes of each record, in order.
RECORD_ATTRIBUTES = ("semanticSource", "softwareContractArtifact", "softwareContractMessage", "softwareContractField",
                     "dataTypeAndUnit", "timingQualityAndState", "transformationRule", "disposition", "owner",
                     "nextAction", "evidenceOrGap")
#: The comments on the framing's records: name -> the record it is about.
COMMENTS = {
    "phase8RendererIntegrationPlaced": "gapHmiRendererIntegration",
    "phase8RendererCollisionWarningPlaced": "gapHmiRendererCollisionWarning",
    "phase8WarningPresentationSettled": "gapHmiWarningPresentation",
    "phase8SceneOutputHeld": "gapHmiSceneOutput",
    "phase8MemberGuestLayoutUntouched": "gapHmiMemberGuestLayout",
    "phase8RendererReadinessOpen": "asmHmiRendererWithoutGraphicsCard",
}
#: The gaps of the realization: short name -> name.
GAPS = {
    "GAP-HMI-001": "gapHmiRendererJudgesSceneCurrency",
    "GAP-HMI-002": "gapHmiBenchSpeedFeed",
    "GAP-HMI-003": "gapHmiDrawingToleranceUnset",
    "GAP-HMI-004": "gapHmiIdentityMissesPhase8Elements",
}

STRUCTURE_VIEW = "hmiDisplayPhysicalStructureView"
MATRIX_VIEW = "hmiDisplayPhysicalLogicalMappingView"
PATH_VIEW = "hmiDisplayRendererPathView"
#: The path view's exposes after the usage, in order: each part, port and connection that it draws, by name, so
#: that the platform of the SDV Core VM shows by name only and its binds stay.
PATH_VIEW_EXPOSES = (
    "hmiSDVCoreGuest", "hmiSDVCoreGuest::warningSomeIpIn", "hmiSDVCoreGuest::speedSampleIn",
    "hmiSDVCoreGuest::sceneMessageIn", "hmiSDVCoreGuest::sceneMessageOut", "hmiSDVCoreGuest::speedSampleOut",
    "hmiSDVCoreGuest::warningEventOut", "hmiSDVCoreGuest::sceneTimeOut", "hmiSDVCoreGuest::vehicleDataPublisher",
    "hmiSDVCoreGuest::vehicleDataPublisher::speedSampleIn", "hmiSDVCoreGuest::vehicleDataPublisher::warningEventIn",
    "hmiSDVCoreGuest::vehicleDataPublisher::sceneMessageIn", "hmiSDVCoreGuest::vehicleDataPublisher::speedSampleOut",
    "hmiSDVCoreGuest::vehicleDataPublisher::warningEventOut", "hmiSDVCoreGuest::vehicleDataPublisher::sceneTimeOut",
    "hmiIVIGuest", "hmiIVIGuest::sceneMessageIn", "hmiIVIGuest::heartbeatOut", "hmiIVIGuest::iviPlaneOut",
    "hmiIVIGuest::sdvGateway", "hmiIVIGuest::sdvGateway::dataTunnelPort", "hmiIVIGuest::sdvGateway::clientPort",
    "hmiIVIGuest::sceneDrawingApp", "hmiIVIGuest::sceneDrawingApp::sceneMessageIn",
    "hmiIVIGuest::sceneDrawingApp::heartbeatOut", "hmiIVIGuest::sceneDrawingApp::iviPlaneOut",
    "hmiIVIGuest::sceneThroughSDVGateway", "hmiSDVMediaGuest", "hmiSDVMediaGuest::speedSampleIn",
    "hmiSDVMediaGuest::warningEventIn", "hmiSDVMediaGuest::sceneTimeIn", "hmiSDVMediaGuest::heartbeatIn",
    "hmiSDVMediaGuest::rendererPlaneOut", "hmiSDVMediaGuest::chimeOut", "hmiSDVMediaGuest::highAvailabilityRenderer",
    "hmiSDVMediaGuest::highAvailabilityRenderer::speedSampleIn",
    "hmiSDVMediaGuest::highAvailabilityRenderer::warningEventIn",
    "hmiSDVMediaGuest::highAvailabilityRenderer::sceneTimeIn",
    "hmiSDVMediaGuest::highAvailabilityRenderer::heartbeatIn",
    "hmiSDVMediaGuest::highAvailabilityRenderer::rendererPlaneOut",
    "hmiSDVMediaGuest::highAvailabilityRenderer::chimeOut", "centralComputer", "centralComputer::iviPlaneIn",
    "centralComputer::rendererPlaneIn", "centralComputer::displayFrameOut", "centralComputer::planeComposition",
    "centralComputer::planeComposition::iviPlaneIn", "centralComputer::planeComposition::rendererPlaneIn",
    "centralComputer::planeComposition::displayFrameOut", "sceneTopicToIVIOverDataTunnel", "speedToRendererAcrossVMs",
    "warningToRendererAcrossVMs", "sceneTimeToRendererAcrossVMs", "drawnSceneHeartbeatToRenderer",
    "iviPlaneToComposition", "rendererPlaneToComposition")
#: view -> (type or None, render, exposes in order, viewpoint type, framed concerns)
VIEWS = {
    STRUCTURE_VIEW: (None, "render asTreeDiagram;", [SYSTEM_USAGE] + [f"{SYSTEM_USAGE}::{path}" for path in (
        "centralComputer", "centralComputer::os", "centralComputer::hypervisor",
        "centralComputer::identityRecordingService", "centralComputer::planeComposition", "hmiSDVCoreGuest",
        "hmiSDVCoreGuest::os", "hmiSDVCoreGuest::sdvMiddleware", "hmiSDVCoreGuest::sdvCore",
        "hmiSDVCoreGuest::vehicleDataPublisher", "hmiIVIGuest", "hmiIVIGuest::os", "hmiIVIGuest::sdvGateway",
        "hmiIVIGuest::sceneDrawingApp", "hmiSDVMediaGuest", "hmiSDVMediaGuest::os",
        "hmiSDVMediaGuest::highAvailabilityRenderer")],
                     "PhysicalStructureDefinitionViewpoint", ["hmiDisplayPhysicalStructureConcern"]),
    MATRIX_VIEW: ("MVD::MatrixView", None,
                  [f"{LOGICAL_SYSTEM}::{element}" for element in (
                      "displayIdentityRecorder", "sceneDrawer", "displayPresenter")]
                  + [f"{SYSTEM_USAGE}::{target}" for _, _, target in ALLOCATIONS]
                  + [f"{PACKAGE}::*"],
                  "PhysicalLogicalMappingViewpoint", ["hmiDisplayPhysicalAllocationConcern",
                                                      "hmiRendererAllocationConcern"]),
    PATH_VIEW: (None, "render asInterconnectionDiagram;",
                [SYSTEM_USAGE] + [f"{SYSTEM_USAGE}::{path}" for path in PATH_VIEW_EXPOSES],
                "PhysicalInternalExchangeViewpoint", ["hmiRendererPathConcern"]),
}
#: view -> its filters, in order
VIEW_FILTERS = {
    STRUCTURE_VIEW: ["not (@ SysML::AllocationUsage)", "not (@ SysML::BindingConnectorAsUsage)"],
    MATRIX_VIEW: [],
    PATH_VIEW: ["not (@ SysML::AllocationUsage)", "not (@ SysML::InterfaceUsage)"],
}
#: concern -> (catalogue type, the parties that hold it, in order)
CATALOGUE_CONCERNS = {
    "hmiDisplayPhysicalStructureConcern": ("PhysicalStructureConcern", ["SystemArchitect", "SoftwareDeveloper"]),
    "hmiDisplayPhysicalAllocationConcern": ("PhysicalLogicalMappingConcern",
                                            ["SystemArchitect", "VerificationEngineer"]),
}
#: The phase 1 concerns of the Physical domain that this phase's views frame -> their catalogue type.
FRAMING_CONCERNS = {"hmiRendererAllocationConcern": "PhysicalFunctionalMappingConcern",
                    "hmiRendererPathConcern": "PhysicalInternalExchangeConcern"}
#: The grid of the matrix: (title, description, row axis, column axis), pinned whole.
GRID = (
    "HMI display logical-to-physical mapping",
    "Maps the three logical elements of the HMI display to the four software elements that carry them.",
    "logical elements (part usages)",
    "software elements (part usages)",
)

#: Words of an assurance claim that no element doc and no part of the header makes.
CLAIM_WORDS = ("certif", "homolog", "complian", "approv", "production-ready", "production ready", "guarantee",
               "proves that", "proven on", "is met", "are met")
#: The SHA-256 of words that no text of this phase carries: two product names, and two words of a fault report.
BANNED_WORD_SHA256 = {
    "00a6009aac697f11c40fb11836ef5cb762f766b2604b66ad25dfafeba3251497",
    "647d177cca8601046a3cb39e12f55bec5790bfcbc42199dd5fcf063200fac1d0",
    "7358bd4ec877e1b622397ab4f9706b76680348a2886bfc0a675ed0555085d0ea",
    "d5c685f25c91f309b6af96c14cd1dc55139184d1153ae51b18c8593a0d69d8c0",
    "ecb53f367b3541da3a14236d9a091f9bcc7a9903953f36577c2664fdd2a68a55",
    "ed7aa50d187fda240b52d794e3fb9fea08dc8b2c45ba3aeeae7e9c4ea3aefd5a",
}
#: The phrase of a launch that no text of this phase carries, joined here so that this file holds it in no line.
LAUNCH_PHRASE = "launch" + " " + "form"

#: The package's imports, one by one (the set is pinned, not the order).
IMPORTS = [
    "ScalarValues::*",
    "DE4SDV_MethodContext::*",
    "DE4SDV_MethodProcess::SystemToSoftwareSignalMappingCandidate",
    "DE4SDV_MethodProcess::LogicalToSoftwareSignalMappingRecord",
    "DE4SDV_MethodProcess::SignalMappingDisposition",
    "DE4SDV_TraceVocabulary::PhysicalAllocationElement",
    "DE4SDV_SDVPlatformStack::AndroidHLOS",
    "DE4SDV_SDVPlatformStack::AndroidSDVMiddleware",
    "DE4SDV_SDVPlatformStack::OSPlatformLayer",
    "DE4SDV_SDVPlatformStack::OSHypervisorInterface",
    "DE4SDV_SDVPlatformStack::HypervisorLayer",
    "DE4SDV_AAOSSDVMiddlewareBoundary::SDVCoreBoundary",
    "DE4SDV_AAOSSDVMiddlewareBoundary::SDVGatewayOnIVIBoundary",
    "DE4SDV_DriverAssistancePhysicalSoftwareRealization::WarningRequestEventPayload",
    "DE4SDV_DriverAssistancePhysicalSoftwareRealization::WarningRequestEventIn",
    "DE4SDV_DriverAssistancePhysicalSoftwareRealization::WarningRequestEventOut",
    "DE4SDV_HmiDisplayFraming::gapHmiSceneOutput",
    "DE4SDV_HmiDisplayFraming::gapHmiRendererCollisionWarning",
    "DE4SDV_HmiDisplayFraming::gapHmiRendererIntegration",
    "DE4SDV_HmiDisplayFraming::gapHmiWarningPresentation",
    "DE4SDV_HmiDisplayFraming::gapHmiMemberGuestLayout",
    "DE4SDV_HmiDisplayFraming::asmHmiRendererWithoutGraphicsCard",
    "DE4SDV_HmiDisplayFraming::hmiRendererAllocationConcern",
    "DE4SDV_HmiDisplayFraming::hmiRendererPathConcern",
    "DE4SDV_HmiDisplayFunctionalArchitecture::DisplaySceneInput",
    "DE4SDV_DriverAssistanceOperationalContext::VehicleSpeed",
    "DE4SDV_HmiDisplayFunctionalArchitecture::DisplayContentOutput",
    "DE4SDV_HmiDisplayLogicalArchitecture::HmiDisplayLogicalSystem",
    "DE4SDV_HmiDisplayNeedsRequirements::reqRendererSplitAndInputPaths",
    "COVESA_VSS::SignalDefinitions::Vehicle_Speed",
    "COVESA_VSS::SignalDefinitions::Vehicle_ADAS_ObstacleDetection_Distance",
    "DE4SDV_Stakeholders::*",
    "SAF_Viewpoints::*",
    "SysideViews::**",
    "Views::*",
]

#: The texts of record of the design, pinned whole: the header, paragraph by paragraph.
HEADER_PARAGRAPHS = [
    "DE4SDV HMI display physical and software realization.",
    "INC-HMI-001, phase 8: the physical and software realization of the HMI display. What software, hardware and "
    "deployment elements realize the three logical elements of phase 7, and which elements carry each input from the "
    "SDV Core VM to the high availability renderer and to the app that draws the scene, as REQ-HMI-009 asks?",
    "The placement (owner decision of 2026-11-25):",
    "- The identity recorder is a DE4SDV service on the computer that starts the VMs, and that service starts them: "
    "the central computer in the vehicle, the guest host on the bench. Before it starts the IVI and SDV Media VMs, "
    "it records the display identity, every part that the term names. It follows the pattern of the identity "
    "recording application of the driver-assistance increment, which the platform's launcher starts first. The "
    "record is a self-report of System 1; System 2 only reads it into the evidence of a run. - The drawn scene "
    "reaches the screen by composition, the design that Android SDV documents (upstream.md): the renderer's plane "
    "lies over the IVI plane on one display. The app in the IVI VM that draws the scene sends the renderer a "
    "heartbeat with each frame that it draws, carrying the time of the scene in that frame. While that scene is "
    "current by the term current, the renderer keeps the scene area transparent; while it is not, the renderer "
    "covers the area with its placeholder. So the drawn scenes of phase 7 are realized by the heartbeats and by the "
    "composition of the IVI plane under the renderer's plane. - In the display's runs the IVI VM runs no other "
    "warning presentation: the warning presentation of the driver-assistance increment does not run there, so no "
    "element but the renderer draws the vehicle speed or the collision warning. The realization, the runs and the "
    "verdicts of the driver-assistance increment stay as they are. - The vehicle speed follows the vehicle's own "
    "path: an ECU measures it, the vehicle network carries it to the central computer, and the SDV Core VM takes it "
    "in as vehicle data. A DE4SDV publisher in the SDV Core VM gives it, over the platform's messaging, to the "
    "vehicle data of the renderer, which has a speed message. On the bench the simulator stands in for the ECU and "
    "the network and feeds the SDV Core VM. The vehicle-network increment names that path and keeps it out of its "
    "scope (eeSensorDataOutOfScope). - No readiness session runs with this phase. One follows it, at its cost and "
    "with the owner's go each time, so this phase states its readiness questions as gaps.",
    "What follows from the phase 7 elements and the defaults of this phase:",
    "- Topology: four software elements carry the three logical elements. The identity recording service and the "
    "composition of the display are on the central computer, the scene drawing app is in the IVI VM, and the high "
    "availability renderer is in the SDV Media VM. The presenter is carried by the renderer and the composition "
    "together, so the drawn scene reaches the display only through the presenter's side. The central computer runs "
    "three VMs, SDV Core, IVI and SDV Media, under its hypervisor; on the bench the guest host of INC-DRIVING-001 "
    "stands in for it, and no element of the bench is modeled here. - Paths: the inputs reach the display in the SDV "
    "Core VM. The warning request reaches it as the Data Tunnel topic that the SOME/IP interop publishes for the "
    "Eclipse S-CORE path of the driver-assistance increment, the vehicle speed as vehicle data, and the scene as a "
    "Data Tunnel topic that a context stand-in publishes, since the scene's way out of the candidate stays open. The "
    "Data Tunnel carries the scene on to the SDV Gateway on the IVI VM and to the app. The vehicle data publisher "
    "gives the speed, the warning request and the time of each scene to the renderer. - Time: of the display's 0.1 "
    "s, 0.05 s is for the hop from the SDV Core VM to the renderer or to the app, and 0.05 s for the drawing and for "
    "the start of the sound; both are unmeasured and revisited when a readiness probe measures them. The clocks and "
    "the simulator's mode are those of the driver-assistance increment: simulation time is the time that each value "
    "carries from its source, and wall-clock time is the time of the host. - VSS at the ports only: the vehicle "
    "speed as Vehicle.Speed, the distance to the object that the system acts on in the scene as "
    "Vehicle.ADAS.ObstacleDetection.Distance, and the warning request in the payload of the driver-assistance "
    "increment. Apart from that distance, the scene, the time of a scene, the heartbeat, the planes, the frames of "
    "the display and the chime are no vehicle signal, and their records say so. No VSS extension is added. - Looks "
    "of an outdated element (REQ-HMI-006): the "
    "renderer's placeholder covers the scene area, the speed shows no number, and the warning shows one fixed symbol "
    "while it is unavailable. The visual design stays out of scope (hmiHumanFactorsOutOfScope). - The changes to the "
    "projects of the renderer and of the candidate stay gaps; nothing is written to their maintainers.",
    "Alternatives recorded and not selected: - ALT-HMI-RECORDERINCORE-001: the identity recorder inside the SDV Core "
    "VM. A recorder in a VM records no image of the IVI or SDV Media VM before their start, which the record has to "
    "precede. - ALT-HMI-SCENESTREAM-001: the app streams its drawn frames to the renderer, which draws them. The "
    "renderer would draw video, a larger change to it than a time in a heartbeat. - ALT-HMI-SPEEDOVERSCORE-001: the "
    "vehicle speed on the Eclipse S-CORE path beside the warning request. It changes the path of the "
    "driver-assistance increment, and the speed is no output of the candidate.",
    "The IVI and SDV Media VMs with the software of the display, the identity recording service and the composition "
    "on the central computer, and the paths from the SDV Core VM are inside the display. The platform of the SDV "
    "Core VM, where the inputs reach the display, is shared with the Eclipse S-CORE path, which is outside it. The "
    "candidate, the S-CORE path and the simulator stay in the realization of the driver-assistance increment; the "
    "simulator, the capture of the display and of the sound, and the evaluators are System 2. An allocation here is "
    "a responsibility assignment, no deployment, execution or runtime claim; a signal mapping is no interoperability "
    "claim. Nothing in this package claims that a requirement is met, that a case ran or that the bench has shown "
    "anything.",
]

#: The doc of each element, by the declaration whose body it opens.
DOCS = {
    "item def DisplaySceneMessage :> DisplaySceneInput":
        "The scene as the realization types it on the Data Tunnel topic of the SDV Core VM and through the SDV "
        "Gateway into the scene drawing app: the scene of one result pass with its capture time in simulation time. "
        "Its message type is new and stays open until phase 10. A scene is no vehicle signal, except the distance to "
        "the object that the system acts on: COVESA VSS types it at the port as obstacleDistance "
        "(Vehicle_ADAS_ObstacleDetection_Distance, m), the value in m of the inherited actedOnObjectDistance "
        "(MAP-HMI-SCENE).",
    "item def DisplayVehicleSpeedSample :> VehicleSpeed":
        "The vehicle speed as the realization types it from the vehicle data of the SDV Core VM to the speed message "
        "of the renderer's vehicle data. The speed is typed by COVESA VSS at the port (Vehicle_Speed, km/h); the "
        "sample time is the time that its source gives it, on the bench the simulation time of the world snapshot "
        "(MAP-HMI-VEHICLE-SPEED).",
    "item def DisplaySceneTime":
        "The time of a scene that has reached the HMI display, the capture time in simulation time of the camera "
        "image of its result pass, as the vehicle data publisher gives it to the renderer to judge the currency of "
        "the scene. The rest of the scene does not go to the renderer. No vehicle signal (MAP-HMI-SCENE-TIME).",
    "item def DrawnSceneHeartbeat":
        "The heartbeat that the scene drawing app sends the renderer with each frame that it draws, in the place of "
        "the heartbeats of Android SDV's design (upstream.md), carrying the time of the scene in that frame. With "
        "the IVI plane it realizes the drawn scenes of phase 7. No vehicle signal (MAP-HMI-DRAWN-SCENE-HEARTBEAT).",
    "item def DisplayPlane":
        "The frames of one plane of the display: the IVI plane, on which the scene drawing app draws the scene, or "
        "the renderer's plane, which lies over it. Pixels, no vehicle signal (MAP-HMI-IVI-PLANE).",
    "item def ComposedDisplayFrame :> DisplayContentOutput":
        "What the HMI display shows, as the frames of the one display: the renderer's plane composed over the IVI "
        "plane. Pixels, no vehicle signal (MAP-HMI-SHOWN-CONTENT).",
    "item def CollisionWarningChime":
        "The collision warning as a sound: the chime that the renderer gives while the warning request asks for the "
        "warning. A sound, no vehicle signal (MAP-HMI-WARNING-CHIME).",
    "port def DisplaySceneMessageOut":
        "The typed scene leaving an element: from the Data Tunnel of the SDV Core VM to the IVI VM.",
    "port def DisplaySceneMessageIn":
        "The typed scene entering an element: the SDV Core VM, the IVI VM, the publisher or the app.",
    "port def DisplayVehicleSpeedSampleOut":
        "The typed vehicle speed leaving an element: the vehicle data publisher or the SDV Core VM.",
    "port def DisplayVehicleSpeedSampleIn":
        "The typed vehicle speed entering an element: the SDV Core VM, the publisher, the SDV Media VM or the "
        "renderer.",
    "port def DisplaySceneTimeOut":
        "The time of a scene leaving the vehicle data publisher or the SDV Core VM for the renderer.",
    "port def DisplaySceneTimeIn":
        "The time of a scene entering the SDV Media VM or the renderer.",
    "port def DrawnSceneHeartbeatOut":
        "The heartbeat of a drawn frame leaving the scene drawing app or the IVI VM.",
    "port def DrawnSceneHeartbeatIn":
        "The heartbeat of a drawn frame entering the SDV Media VM or the renderer.",
    "port def DisplayPlaneOut":
        "A plane of the display leaving the element that draws it: the scene drawing app or the renderer.",
    "port def DisplayPlaneIn":
        "A plane of the display entering the composition, or the central computer on its way there.",
    "port def ComposedDisplayFrameOut":
        "The frames of the one display leaving the composition for the driver.",
    "port def CollisionWarningChimeOut":
        "The chime of the collision warning leaving the renderer for the driver.",
    "part def DisplayIdentityRecordingService :> PhysicalAllocationElement":
        "Carries the identity recorder of phase 7, beside the software of the scene drawing app and of the renderer "
        "and inside neither VM: a DE4SDV service on the computer that starts the VMs, which starts them (owner "
        "decision of 2026-11-25). In the vehicle that computer is the central computer; on the bench the guest host "
        "stands in for it. In each run, before it starts the IVI and SDV Media VMs, it records the display identity "
        "as the term of the requirements defines it: the SHA-256 of the files of the build of the high availability "
        "renderer, of the files of the build of the scene drawing app, of the image of the IVI VM and of the SDV "
        "Media VM, and of the sound file of the collision warning; the SHA-256 of each configuration file that the "
        "HMI display reads at its start; and the settings of its start, verbatim. Only then does it start the two "
        "VMs, so the record comes before the first frame of the display (REQ-HMI-010). It follows the pattern of the "
        "identity recording application of the driver-assistance increment, which the platform's launcher starts "
        "first. The record is a self-report of System 1, a file of the run that System 2 only reads into the "
        "evidence of the run. It sends nothing to another element of the display, so it has no port. How long the "
        "recording delays the start of the two VMs is not measured. A build item, named here, not claimed.",
    "part def SceneDrawingApplication :> PhysicalAllocationElement":
        "Carries the scene drawer of phase 7: a DE4SDV Android app in the IVI VM, a build item, named here, not "
        "claimed. It subscribes to the topic of the scene through the SDV Gateway and draws each scene that reaches "
        "it, or a newer one, with the object that the system acts on, when the scene has one, as an element of its "
        "own, in the scene area of the display of the IVI VM, the IVI plane. With each frame that it draws, it sends "
        "the renderer a heartbeat that carries the time of the scene in that frame. It takes the place that Android "
        "SDV's design gives DriverUI, the app in the IVI VM whose heartbeats tell the renderer that Android is alive "
        "(upstream.md), for the scene area only. It draws neither the vehicle speed nor the collision warning and "
        "gives no sound (REQ-HMI-009). While it, or Android in the IVI VM, is out, no heartbeat comes, and the "
        "renderer covers the scene area. Of the display's 0.1 s it has 0.05 s, from the arrival of a scene to its "
        "first frame on the display, unmeasured. How a drawn position is read against the scene is not set yet "
        "(gapHmiDrawingToleranceUnset). The look of the scene stays out of scope (hmiHumanFactorsOutOfScope).",
    "part def HighAvailabilityRenderer :> PhysicalAllocationElement":
        "Carries the presenter of phase 7, together with the composition of the display: the high availability "
        "renderer of Android SDV's display safety with its app, in the SDV Media VM, at the commits that the "
        "upstream record names (upstream.md), with DE4SDV changes that its project has not taken "
        "(gapHmiRendererCollisionWarning, gapHmiRendererJudgesSceneCurrency). From its vehicle data it takes the "
        "vehicle speed, each event of the warning request and the time of each scene that reaches the display, which "
        "the vehicle data publisher of the SDV Core VM gives it; from the scene drawing app it takes a heartbeat "
        "with each drawn frame. It judges by the term current whether the scene as drawn, the vehicle speed and the "
        "warning request are current. On its plane, which lies over the IVI plane on the one display, it draws the "
        "vehicle speed to the whole km/h and no number while the speed is outdated; the collision warning while the "
        "warning request asks for it; and one fixed symbol while the warning is unavailable. It keeps the scene area "
        "transparent while the scene as drawn is current and covers it with its placeholder while it is outdated. It "
        "gives the collision warning as a sound, its chime. It takes nothing from the IVI VM but the heartbeats, so "
        "it goes on through each outage in the IVI VM (REQ-HMI-008). Of the display's 0.1 s it has 0.05 s, from the "
        "arrival of a value to the first frame on the display that shows it and to the start of the chime, "
        "unmeasured. The symbols and the chime stay with their design (gapHmiRendererCollisionWarning).",
    "part def DisplayPlaneComposition :> PhysicalAllocationElement":
        "Carries the presenter of phase 7, together with the high availability renderer: the composition of the one "
        "display on the central computer, which puts the renderer's plane over the IVI plane, as Android SDV's "
        "design places them (upstream.md), and gives the frames on the display. It adds nothing of its own and "
        "chooses nothing: of the IVI plane the driver sees what the renderer's plane leaves transparent. The "
        "presenter is allocated to it because the drawn scene reaches the display only through it; carrying no "
        "logical element, it would be a way from the scene drawer to the driver beside the presenter. It is outside "
        "the IVI VM, so it goes on through each outage there. In the vehicle the central computer composes its "
        "display; on the bench the guest host stands in for it, and whether it composes the two planes there is not "
        "observed (gapHmiRendererIntegration).",
    "part def RendererVehicleDataPublisher":
        "The vehicle data publisher of the display: a DE4SDV service in the SDV Core VM, inside the boundary of the "
        "display, a build item named here, not claimed. It carries no logical element: it is a hop of the paths that "
        "bring the presenter its inputs (REQ-HMI-009). It reads the vehicle speed from the vehicle data of the SDV "
        "Core VM and subscribes to the Data Tunnel topics of the warning request and of the scene. Over the "
        "platform's messaging between the VMs it publishes each vehicle speed to the speed message of the renderer's "
        "vehicle data, and each event of the warning request and the time of each scene, which are new to that "
        "vehicle data (gapHmiRendererCollisionWarning, gapHmiRendererJudgesSceneCurrency). It changes no value and "
        "no time. How a producer in the SDV Core VM reaches the renderer's topics is open "
        "(gapHmiRendererIntegration).",
    "part def HmiDisplaySDVCoreGuest":
        "The SDV Core VM of the display's runs, where the inputs reach the HMI display: Android under the hypervisor "
        "of the central computer, with the SDV Core middleware. Its SOME/IP interop receives the warning request "
        "from the Eclipse S-CORE path of the driver-assistance increment, outside the display, and its broker "
        "publishes it as the Data Tunnel topic of that increment. The vehicle speed reaches it as vehicle data: in "
        "the vehicle from the ECU that measures it, over the vehicle network; on the bench from the simulator, which "
        "stands in for both (gapHmiBenchSpeedFeed). The scene reaches it as a Data Tunnel topic that a context "
        "stand-in publishes, since the scene's way out of the candidate is open (gapHmiSceneOutput). The Data Tunnel "
        "carries the scene on to the IVI VM, and the vehicle data publisher of the display gives the speed, the "
        "warning request and the time of each scene to the SDV Media VM. The SDV Core boundary model of "
        "packages/architecture is referenced and bound to the middleware layer; nothing of the platform is built by "
        "DE4SDV.",
    "part def HmiDisplayIVIGuest":
        "The IVI VM of the display's runs, inside the display: Android under the hypervisor of the central computer, "
        "with the SDV Gateway and the scene drawing app. It runs no other warning presentation: the warning "
        "presentation of the driver-assistance increment does not run in the display's runs, so no element of this "
        "VM draws the vehicle speed or the collision warning (owner decision of 2026-11-25, REQ-HMI-009). It is a "
        "definition of its own, not a specialization of that increment's IVI VM, which owns that presentation. The "
        "app subscribes to the topic of the scene through the SDV Gateway. The VM gives the renderer the heartbeats, "
        "and the composition its display, the IVI plane.",
    "part def HmiDisplaySDVMediaGuest":
        "The SDV Media VM, inside the display: a guest of its own under the hypervisor of the central computer, "
        "which Android SDV's documentation also calls the rapid boot VM (upstream.md), with the high availability "
        "renderer. Its operating system is typed by the platform stack's operating-system layer only: no source that "
        "DE4SDV keeps names it. It takes the speed, the warning request and the time of each scene from the SDV Core "
        "VM and the heartbeats from the IVI VM, and gives its plane to the composition and the chime to the driver. "
        "The boundary model of the AAOS SDV middleware leaves this VM out of its scope; this realization models only "
        "what the display needs of it.",
    "part def HmiDisplayCentralComputer":
        "The central computer of the vehicle as the HMI display needs it: the computer that hosts the SDV Core, IVI "
        "and SDV Media VMs under its hypervisor. Beside the VMs it holds two elements of the display: the identity "
        "recording service, which records the display identity and then starts the IVI and SDV Media VMs, and the "
        "composition of the display, to whose ports its own are bound. Its own platform and its hypervisor are typed "
        "by the generic layers of the platform stack only. On the bench the guest host of INC-DRIVING-001 stands in "
        "for it, with the SDV Media VM as a third guest (asmHmiRendererWithoutGraphicsCard); no element of the bench "
        "is modeled here. No E/E realization declares the central computer yet; once one does, this realization "
        "imports it and no longer declares it.",
    "part def HmiDisplayPhysicalSystem":
        "The physical realization of the HMI display in the vehicle: the central computer and its three VMs. Inside "
        "the display are the identity recording service and the composition on the central computer, the IVI VM with "
        "the scene drawing app, the SDV Media VM with the high availability renderer, and the paths from the SDV "
        "Core VM, with the vehicle data publisher in it. The platform of the SDV Core VM, where the inputs reach the "
        "display, is shared with the Eclipse S-CORE path outside it. The candidate, the S-CORE path and the "
        "simulator stay in the realization of the driver-assistance increment, and no part here stands for them or "
        "for an element of the bench. Between the VMs, the scene goes from the SDV Core VM to the IVI VM on the Data "
        "Tunnel; the speed, the warning request and the time of each scene go from the SDV Core VM to the SDV Media "
        "VM over the platform's messaging; and the heartbeats go from the IVI VM to the SDV Media VM. The two planes "
        "go to the composition on the central computer, the renderer's over the IVI plane. Nothing crosses back to "
        "the SDV Core VM or to the IVI VM. It carries REQ-HMI-009 by the elements that it places on those paths.",
    "connection sceneTopicToIVIOverDataTunnel":
        "The scene as the Data Tunnel topic from the SDV Core VM to the SDV Gateway on the IVI VM; its message type "
        "stays open until phase 10.",
    "connection speedToRendererAcrossVMs":
        "The vehicle speed from the vehicle data publisher to the speed message of the renderer's vehicle data, over "
        "the platform's messaging between the VMs.",
    "connection warningToRendererAcrossVMs":
        "Each event of the warning request from the vehicle data publisher to the renderer's vehicle data, over the "
        "platform's messaging between the VMs; new to that vehicle data (gapHmiRendererCollisionWarning).",
    "connection sceneTimeToRendererAcrossVMs":
        "The time of each scene that reaches the display, from the vehicle data publisher to the renderer, over the "
        "platform's messaging between the VMs; new to the renderer's vehicle data "
        "(gapHmiRendererJudgesSceneCurrency).",
    "connection drawnSceneHeartbeatToRenderer":
        "One heartbeat for each frame that the scene drawing app draws, with the time of the scene in it, from the "
        "IVI VM to the renderer: with the IVI plane, the drawn scenes of phase 7.",
    "connection iviPlaneToComposition":
        "The IVI plane, on which the scene drawing app draws the scene, into the composition of the display, under "
        "the renderer's plane: with the heartbeats, the drawn scenes of phase 7.",
    "connection rendererPlaneToComposition":
        "The renderer's plane into the composition of the display, over the IVI plane.",
    "part hmiDisplayPhysicalSystem : HmiDisplayPhysicalSystem":
        "The HMI display as the views draw it: the one usage of the physical definition. It depicts the realization "
        "of the context's hmiDisplay and is bound to nothing.",
    "concern hmiDisplayPhysicalStructureConcern : PhysicalStructureConcern":
        "System architects and software developers need the software and platform elements that realize the HMI "
        "display, as they nest: the central computer with the identity recording service and the composition of the "
        "display, the SDV Core VM with the vehicle data publisher, the IVI VM with the scene drawing app and no "
        "other warning presentation, and the SDV Media VM with the high availability renderer.",
    "concern hmiDisplayPhysicalAllocationConcern : PhysicalLogicalMappingConcern":
        "System architects and verification engineers need each logical element of phase 7 allocated to the software "
        "elements that carry it, and each software element carrying one: the identity recording service, the scene "
        "drawing app, and the high availability renderer and the composition of the display, which carry the "
        "presenter together. An allocation is a responsibility assignment, no deployment or runtime claim.",
    "view hmiDisplayRendererPathView":
        "The paths of the inputs inside the display (hmiRendererPathConcern): the scene from the SDV Core VM over "
        "the Data Tunnel and the SDV Gateway to the scene drawing app in the IVI VM; the vehicle speed, the warning "
        "request and the time of each scene from the vehicle data publisher in the SDV Core VM to the high "
        "availability renderer in the SDV Media VM; the heartbeat of each drawn frame from the app to the renderer, "
        "by which the app tells the renderer that Android is alive; and the two planes into the composition on the "
        "central computer. No other port leads to the renderer, and nothing leads back. Each edge between the VMs and "
        "the central computer is labelled with the ports at its ends, and each port definition carries the one item "
        "that its exchange moves. The platform of the SDV Core VM is listed by name only; where a path enters or "
        "leaves it, its binds and connections are drawn as boxes that name their two ends. The hypervisor interfaces "
        "are drawn in no view of this phase; the structure tree shows the hypervisor and each VM's operating system.",
}
DOC_IDS = [
    "DisplaySceneMessage", "DisplayVehicleSpeedSample", "DisplaySceneTime", "DrawnSceneHeartbeat", "DisplayPlane",
    "ComposedDisplayFrame", "CollisionWarningChime", "DisplaySceneMessageOut", "DisplaySceneMessageIn",
    "DisplayVehicleSpeedSampleOut", "DisplayVehicleSpeedSampleIn", "DisplaySceneTimeOut", "DisplaySceneTimeIn",
    "DrawnSceneHeartbeatOut", "DrawnSceneHeartbeatIn", "DisplayPlaneOut", "DisplayPlaneIn", "ComposedDisplayFrameOut",
    "CollisionWarningChimeOut", "DisplayIdentityRecordingService", "SceneDrawingApplication",
    "HighAvailabilityRenderer", "DisplayPlaneComposition", "RendererVehicleDataPublisher", "HmiDisplaySDVCoreGuest",
    "HmiDisplayIVIGuest", "HmiDisplaySDVMediaGuest", "HmiDisplayCentralComputer", "HmiDisplayPhysicalSystem",
    "sceneTopicToIVIOverDataTunnel", "speedToRendererAcrossVMs", "warningToRendererAcrossVMs",
    "sceneTimeToRendererAcrossVMs", "drawnSceneHeartbeatToRenderer", "iviPlaneToComposition",
    "rendererPlaneToComposition", "hmiDisplayPhysicalSystem", "hmiDisplayPhysicalStructureConcern",
    "hmiDisplayPhysicalAllocationConcern", "hmiDisplayRendererPathView",
]

#: The doc of each mapping record.
RECORD_DOCS = {
    "sceneIngressMappingRecord":
        "The scene from the Data Tunnel topic of the SDV Core VM through the SDV Gateway on the IVI VM into the "
        "scene drawing app. A scene is no vehicle signal, except the distance to the object that the system acts on, "
        "which COVESA VSS types at the port.",
    "drawnSceneHeartbeatMappingRecord":
        "The heartbeat of each drawn frame from the scene drawing app in the IVI VM to the renderer in the SDV Media "
        "VM: with the IVI plane, the drawn scenes of phase 7. No vehicle signal.",
    "iviPlaneMappingRecord":
        "The IVI plane, on which the scene drawing app draws the scene, into the composition of the display under "
        "the renderer's plane: with the heartbeats, the drawn scenes of phase 7. Pixels, no vehicle signal.",
    "displaySpeedMappingRecord":
        "The vehicle speed from the vehicle data of the SDV Core VM through the vehicle data publisher to the speed "
        "message of the renderer's vehicle data. The owning allocation targets the typed port; its item "
        "DisplayVehicleSpeedSample types the speed by COVESA VSS.",
    "rendererWarningRequestMappingRecord":
        "The warning request from the Data Tunnel topic that the SOME/IP interop of the SDV Core VM publishes, "
        "through the vehicle data publisher, to the renderer's vehicle data. The item is the payload of the "
        "driver-assistance increment, unchanged.",
    "sceneTimeMappingRecord":
        "The time of each scene that reaches the display, from the Data Tunnel topic of the scene in the SDV Core VM "
        "through the vehicle data publisher to the renderer, which judges the currency of the scene from it. No "
        "vehicle signal.",
    "warningChimeMappingRecord":
        "The collision warning as a sound, from the renderer to the driver: a chime of the renderer's chime "
        "configuration. A sound, no vehicle signal.",
    "shownContentMappingRecord":
        "What the HMI display shows: the frames of the one display, the renderer's plane composed over the IVI "
        "plane. The looks of an outdated element are those of this phase. Pixels, no vehicle signal.",
}

#: The values of each mapping record, attribute by attribute, as written (strings without their quotes).
RECORD_VALUES = {
    "sceneIngressMappingRecord": {
        "semanticSource":
            "the scene of one result pass of the candidate with the capture time of its camera image in simulation "
            "time: the output that the candidate does not give yet (gapHmiSceneOutput), no vehicle signal, except the "
            "distance to the object that the system acts on, which COVESA VSS types at the port as "
            "Vehicle_ADAS_ObstacleDetection_Distance (Vehicle.ADAS.ObstacleDetection.Distance, m)",
        "softwareContractArtifact":
            "a Data Tunnel topic of the SDV Core VM that a context stand-in publishes, and the subscription of the "
            "scene drawing app to it through the SDV Gateway on the IVI VM, candidate",
        "softwareContractMessage":
            "DisplaySceneMessage, one per result pass; a new message type, open until phase 10, candidate",
        "softwareContractField":
            "the capture time, the lane points, the path, the objects with their levels, and the object that the "
            "system acts on with its distance and the speed of the closest object; not typed in this model yet",
        "dataTypeAndUnit":
            "capture time in simulation seconds; distance in m; speed of the closest object in m/s, negative while "
            "it approaches",
        "timingQualityAndState":
            "one scene per 0.1 s of simulation time; of the display's 0.1 s of wall-clock time, 0.05 s is for the "
            "hop from the SDV Core VM to the app and 0.05 s for the drawing, both unmeasured and revisited when a "
            "readiness probe measures them",
        "transformationRule":
            "none on the path: the capture time reaches the app unchanged, and the app draws the scene as the "
            "candidate gives it",
        "disposition":
            "SignalMappingDisposition::candidate",
        "owner":
            "DE4SDV maintainers",
        "nextAction":
            "settle the scene's way out of the candidate and the message type, then bring the verification cases of "
            "REQ-HMI-001 and REQ-HMI-002 to evidence of record; none is started",
        "evidenceOrGap":
            "no runtime evidence of record; framing gap gapHmiSceneOutput",
    },
    "drawnSceneHeartbeatMappingRecord": {
        "semanticSource":
            "the time of the scene that the scene drawing app has drawn in a frame, sent with that frame in the "
            "place of the heartbeats of Android SDV's design: a liveness message, no vehicle signal",
        "softwareContractArtifact":
            "the heartbeat by which the renderer learns that the app in the IVI VM is alive, extended with the time "
            "of the drawn scene, candidate",
        "softwareContractMessage":
            "DrawnSceneHeartbeat, one per drawn frame, candidate",
        "softwareContractField":
            "sceneCaptureTime, exact; the other fields of the heartbeat are not typed in this model yet",
        "dataTypeAndUnit":
            "sceneCaptureTime in simulation seconds",
        "timingQualityAndState":
            "one heartbeat per drawn frame; none while the app or Android in the IVI VM is out; the renderer judges "
            "the scene as drawn by the term current from the newest heartbeat",
        "transformationRule":
            "sceneCaptureTime = the capture time of the scene that the frame shows, unchanged",
        "disposition":
            "SignalMappingDisposition::candidate",
        "owner":
            "DE4SDV maintainers",
        "nextAction":
            "settle the heartbeat's interface with the renderer, then bring the verification cases of REQ-HMI-006 "
            "and REQ-HMI-008 to evidence of record; none is started",
        "evidenceOrGap":
            "no runtime evidence of record; framing gap gapHmiRendererIntegration and gap "
            "gapHmiRendererJudgesSceneCurrency",
    },
    "iviPlaneMappingRecord": {
        "semanticSource":
            "the frames of the display of the IVI VM, on which the scene drawing app draws the scene in the scene "
            "area: pixels, no vehicle signal",
        "softwareContractArtifact":
            "the display of the IVI VM as a plane of the one display, composed under the renderer's plane on the "
            "central computer, candidate",
        "softwareContractMessage":
            "one frame of the IVI plane for each frame that the display of the IVI VM gives, candidate",
        "softwareContractField":
            "the pixels of the scene area; the rest of the IVI plane lies under the renderer's own drawing",
        "dataTypeAndUnit":
            "pixels; the size and the scale of the scene area are set with the app's drawing",
        "timingQualityAndState":
            "a frame for each drawing of the app; none while the app or Android in the IVI VM is out, when the "
            "renderer covers the scene area",
        "transformationRule":
            "none: the composition puts the renderer's plane over the IVI plane and adds nothing",
        "disposition":
            "SignalMappingDisposition::candidate",
        "owner":
            "DE4SDV maintainers",
        "nextAction":
            "show that the bench composes the two planes, then bring the verification cases of REQ-HMI-001 and "
            "REQ-HMI-006 to evidence of record; none is started",
        "evidenceOrGap":
            "no runtime evidence of record; framing gap gapHmiRendererIntegration (the drawing over the display of "
            "the IVI VM)",
    },
    "displaySpeedMappingRecord": {
        "semanticSource":
            "the speed of the vehicle as vehicle data of the SDV Core VM, typed at the port by COVESA VSS "
            "Vehicle_Speed [km/h]; on the bench the simulator's speed of the ego vehicle stands in for it",
        "softwareContractArtifact":
            "in: the vehicle data of the SDV Core VM, read by the vehicle data publisher, candidate; out: the speed "
            "message of the renderer's vehicle data (upstream.md), published over the platform's messaging between "
            "the VMs, candidate",
        "softwareContractMessage":
            "DisplayVehicleSpeedSample, one per sample of the vehicle data; the renderer's speed message, candidate",
        "softwareContractField":
            "speed, sampleTime, exact; the fields of the renderer's speed message as its vehicle data catalogue "
            "gives them",
        "dataTypeAndUnit":
            "speed : Vehicle_Speed km/h; sampleTime in simulation seconds",
        "timingQualityAndState":
            "one sample per sample of the vehicle data, on the bench one per world snapshot, every 0.05 s of "
            "simulation time; of the display's 0.1 s of wall-clock time, 0.05 s is for the hop from the SDV Core VM "
            "to the renderer and 0.05 s for the drawing, both unmeasured",
        "transformationRule":
            "none on the path; the renderer shows the speed rounded to the whole km/h",
        "disposition":
            "SignalMappingDisposition::candidate",
        "owner":
            "DE4SDV maintainers",
        "nextAction":
            "build the feed of the speed into the SDV Core VM on the bench and the vehicle data publisher, then "
            "bring the verification cases of REQ-HMI-003 to evidence of record; none is started",
        "evidenceOrGap":
            "no runtime evidence of record; gap gapHmiBenchSpeedFeed and framing gap gapHmiRendererIntegration (the "
            "path from the SDV Core VM to the SDV Media VM)",
    },
    "rendererWarningRequestMappingRecord": {
        "semanticSource":
            "the warning request of the candidate, typed at the port by Vehicle_ADAS_AEBS_DriverWarning_IsActive in "
            "the payload of the driver-assistance increment, WarningRequestEventPayload; the issue time is no "
            "vehicle signal",
        "softwareContractArtifact":
            "in: the Data Tunnel topic of the warning request that the driver-assistance increment publishes in the "
            "SDV Core VM, candidate; out: a message of the renderer's vehicle data that its catalogue does not hold "
            "yet, published over the platform's messaging between the VMs, candidate",
        "softwareContractMessage":
            "WarningRequestEventPayload, one event per plan, candidate",
        "softwareContractField":
            "requested, issueTime, exact; the fields of the message in the renderer's vehicle data are not typed in "
            "this model yet",
        "dataTypeAndUnit":
            "requested boolean; issueTime in simulation seconds",
        "timingQualityAndState":
            "one event per plan, every 0.1 s of simulation time; a request starts with the first event that asks "
            "after one that does not. Of the display's 0.1 s of wall-clock time from the start of a request reaching "
            "the SDV Core VM to the start of each mode, 0.05 s is for the hop to the renderer and 0.05 s for the "
            "first frame with the warning and the start of the chime; both are unmeasured and revisited when a "
            "readiness probe measures them",
        "transformationRule":
            "none on the path; the renderer draws the warning and gives the chime while the request asks, and the "
            "symbol that the warning is unavailable while the request is outdated",
        "disposition":
            "SignalMappingDisposition::candidate",
        "owner":
            "DE4SDV maintainers",
        "nextAction":
            "add the warning request, its symbols and the chime to the renderer, then bring the verification cases "
            "of REQ-HMI-004, REQ-HMI-005 and REQ-HMI-007 to evidence of record; none is started",
        "evidenceOrGap":
            "no runtime evidence of record; framing gap gapHmiRendererCollisionWarning",
    },
    "sceneTimeMappingRecord": {
        "semanticSource":
            "the capture time in simulation time of the camera image of the result pass of each scene that reaches "
            "the display: a time, no vehicle signal",
        "softwareContractArtifact":
            "in: the Data Tunnel topic of the scene in the SDV Core VM, candidate; out: a message of the renderer's "
            "vehicle data that its catalogue does not hold yet, published over the platform's messaging between the "
            "VMs, candidate",
        "softwareContractMessage":
            "DisplaySceneTime, one per scene, candidate",
        "softwareContractField":
            "captureTime, exact",
        "dataTypeAndUnit":
            "captureTime in simulation seconds",
        "timingQualityAndState":
            "one per scene, every 0.1 s of simulation time; 0.05 s of wall-clock time for the hop from the SDV Core "
            "VM to the renderer, unmeasured",
        "transformationRule":
            "captureTime = the capture time of the scene, unchanged; the rest of the scene does not go to the renderer",
        "disposition":
            "SignalMappingDisposition::candidate",
        "owner":
            "DE4SDV maintainers",
        "nextAction":
            "add the time of the scene to the renderer's vehicle data, then bring the verification cases of "
            "REQ-HMI-006 to evidence of record; none is started",
        "evidenceOrGap":
            "no runtime evidence of record; gap gapHmiRendererJudgesSceneCurrency",
    },
    "warningChimeMappingRecord": {
        "semanticSource":
            "the collision warning as a sound: a chime, no vehicle signal",
        "softwareContractArtifact":
            "a chime of the renderer's chime configuration, which holds no collision chime yet (upstream.md), and "
            "the sound output of the SDV Media VM, candidate",
        "softwareContractMessage":
            "one chime for as long as the warning request asks, candidate",
        "softwareContractField":
            "the sound file of the collision warning, which the display identity hashes",
        "dataTypeAndUnit":
            "a sound; its design stays open",
        "timingQualityAndState":
            "starts within the presentation time after the start of a request reaches the display: 0.05 s of "
            "wall-clock time for the hop and 0.05 s to the start of the chime, unmeasured",
        "transformationRule":
            "the chime plays while the warning request asks and stops once it asks for none or is outdated",
        "disposition":
            "SignalMappingDisposition::candidate",
        "owner":
            "DE4SDV maintainers",
        "nextAction":
            "design and review the chime, then bring the verification cases of REQ-HMI-004 and REQ-HMI-005 to "
            "evidence of record; none is started",
        "evidenceOrGap":
            "no runtime evidence of record; framing gaps gapHmiRendererCollisionWarning and "
            "gapHmiRendererIntegration (the sound output and its capture)",
    },
    "shownContentMappingRecord": {
        "semanticSource":
            "the frames of the one display: the renderer's plane, with the vehicle speed, the collision warning, the "
            "symbol that the warning is unavailable and the placeholder of the scene area, over the IVI plane with "
            "the drawn scene; pixels, no vehicle signal",
        "softwareContractArtifact":
            "the composition of the display on the central computer, with the renderer's plane over the IVI plane, "
            "candidate",
        "softwareContractMessage":
            "one frame of the display per composition, candidate",
        "softwareContractField":
            "the scene area, the speed, the warning and the symbol that the warning is unavailable, each at a place "
            "that the renderer's design sets",
        "dataTypeAndUnit":
            "pixels; the speed to the whole km/h",
        "timingQualityAndState":
            "each change of what the display shows within the presentation time: 0.05 s of wall-clock time for the "
            "hop and 0.05 s for the drawing and the composition, unmeasured",
        "transformationRule":
            "an outdated scene shows as the renderer's placeholder over the scene area; an outdated speed shows no "
            "number; an unavailable warning shows one fixed symbol; a current element shows as given",
        "disposition":
            "SignalMappingDisposition::candidate",
        "owner":
            "DE4SDV maintainers",
        "nextAction":
            "show that the bench composes the two planes and captures the display, then bring the verification cases "
            "of REQ-HMI-001, REQ-HMI-003, REQ-HMI-006 and REQ-HMI-007 to evidence of record; none is started",
        "evidenceOrGap":
            "no runtime evidence of record; framing gap gapHmiRendererIntegration",
    },
}

#: The text of each comment on a framing record.
COMMENT_TEXTS = {
    "phase8RendererIntegrationPlaced":
        "Placed, not observed: the vehicle data publisher in the SDV Core VM gives the renderer the speed, the "
        "warning request and the time of each scene over the platform's messaging between the VMs; the scene drawing "
        "app in the IVI VM sends it a heartbeat with each drawn frame, which is how it tells the renderer that "
        "Android is alive; the composition of the display on the central computer puts the renderer's plane over the "
        "IVI plane; and the renderer gives the chime. None of this has run on the bench. Which transport carries the "
        "renderer's topics between the VMs, whether the bench composes the two planes, which IVI image runs the app, "
        "and how the sound is captured are readiness questions. One readiness session follows this phase, at its "
        "cost and with the owner's go (owner decision of 2026-11-25).",
    "phase8RendererCollisionWarningPlaced":
        "Placed, not closed: the vehicle data publisher gives the renderer each event of the warning request, a "
        "message that the renderer's vehicle data does not hold yet. The renderer learns that the warning is "
        "unavailable from the age of those events (warningAvailabilityFixedInPhase5) and shows one fixed symbol "
        "then. The symbol of the collision warning, that of the unavailable warning and the chime stay to be "
        "designed and reviewed; they are changes to the renderer's project.",
    "phase8WarningPresentationSettled":
        "Settled for this realization (owner decision of 2026-11-25): in the display's runs the IVI VM runs no other "
        "warning presentation, and the warning presentation of the driver-assistance increment does not run there. "
        "Its realization, its runs and its verdicts stay as they are. Of the display's 0.1 s, 0.05 s is for the hop "
        "from the SDV Core VM to the renderer or to the app and 0.05 s for the drawing and the start of the sound. "
        "Both shares are unmeasured and revisited when a readiness probe measures them "
        "(warningPresentationFixedInPhase5).",
    "phase8SceneOutputHeld":
        "Held open: this realization changes nothing in the candidate (hmiCandidateChangeOutOfScope). A context "
        "stand-in publishes the scene as a Data Tunnel topic in the SDV Core VM, where the scene reaches the "
        "display; what stands in, and how, is decided with the scene's way out of the candidate.",
    "phase8MemberGuestLayoutUntouched":
        "Not settled here: the central computer of this realization runs three VMs, which says nothing of the guest "
        "partition of a member product. That layout is settled outside this increment.",
    "phase8RendererReadinessOpen":
        "Not yet shown: no readiness probe has measured the renderer drawing on the guest host with the SDV Core, "
        "IVI and SDV Media VMs running on it together. The probe runs after this phase, so that it tests the "
        "realization placed here: the heartbeats, the composition and the renderer's judging of the scene by the "
        "term current.",
}

#: The doc of each gap of the realization.
GAP_DOCS = {
    "GAP-HMI-001":
        "The renderer has to judge the scene as drawn by the term current: from the time of the scene in the newest "
        "heartbeat, against the newest time of a value that has reached the display, and from when the newest "
        "heartbeat came. Android SDV's design keeps the scene area transparent while the heartbeats arrive "
        "(upstream.md), whatever scene the app has drawn. The time in the heartbeat and in the renderer's vehicle "
        "data, and the judging by the term current, are changes to the renderer's project. How the renderer learns "
        "when the newest value of each input reached the SDV Core VM, where the values reach the display, is open.",
    "GAP-HMI-002":
        "On the bench the simulator stands in for the ECU that measures the vehicle speed and for the vehicle "
        "network that carries it to the central computer. No element of the bench feeds the simulator's speed into "
        "the vehicle data of the SDV Core VM yet, and which element does is open.",
    "GAP-HMI-003":
        "REQ-HMI-001 reads a frame on the display against the scene within the tolerance of a drawn position that "
        "phase 8 states with the drawing. The scale of the scene area and the drawing of the scene drawing app are "
        "not built, so the tolerance is not set. It is set with the app's drawing, before phase 10.",
    "GAP-HMI-004":
        "The display identity of the requirements names the builds of the renderer and of the scene drawing app and "
        "the images of the IVI and SDV Media VMs. Phase 8 places three more elements inside the display whose builds "
        "it does not name: the vehicle data publisher in the SDV Core VM, and the identity recording service and the "
        "composition on the central computer. Nor does it name the image of the SDV Core VM, whose platform carries "
        "the scene on to the IVI VM and the other inputs to the publisher. A change to one of them records the same "
        "display identity, so REQ-HMI-010 is not met as worded until the term names them, before phase 10.",
}

#: The guide: its Status line, its line in the frame, the next obligation and the check command, as phase 9 moves
#: them.
GUIDE_STATUS = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification, "
    "Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture, Phase 7 logical "
    "architecture, Phase 8 physical and software realization and Phase 9 variability and configuration, "
    "proposal.**")
GUIDE_NEXT = (
    "The next model obligation is **Phase 10**: the verification cases, one or more for each requirement of the "
    "increment; its first gate is `verificationCaseVerifiesRequirement`.")
GUIDE_HEADING = "## Physical and software realization (Phase 8)"
GUIDE_LINK = "../../textual-notation-of-model/packages/features/hmi/hmi_display_physical_software_realization.sysml"
GUIDE_FRAME_LINE = (f"- [SysML physical and software realization]({GUIDE_LINK}): the Phase 8 physical and software "
                    "realization of the HMI display.")
GUIDE_CHECK = (
    "`python -m pytest tests/test_hmi_display_framing.py tests/test_hmi_display_functional_architecture.py "
    "tests/test_hmi_display_logical_architecture.py tests/test_hmi_display_physical_software_realization.py "
    "tests/test_hmi_display_variability_configuration.py -q`")

#: The guide's Phase 8 section, block by block, whole.
GUIDE_BLOCKS = [
    "The [physical and software realization](../../textual-notation-of-model/packages/features/hmi/"
    "hmi_display_physical_software_realization.sysml) answers what software, hardware and deployment elements "
    "realize the three logical elements, and which elements carry each input from the SDV Core VM to the high "
    "availability renderer and to the app that draws the scene. On 2026-11-25 the owner decided the placement:",
    "- The identity recorder is a DE4SDV service on the computer that starts the VMs, and that service starts them: "
    "the central computer in the vehicle, the guest host on the bench. It records the display identity before it "
    "starts the IVI and SDV Media VMs, in the pattern of the identity recording application of the driver-assistance "
    "increment. The record is a self-report of System 1, which System 2 only reads. - The drawn scene reaches the "
    "screen by composition, the design that Android SDV documents: the renderer's plane lies over the IVI plane on "
    "one display. With each frame that it draws, the app in the IVI VM sends the renderer a heartbeat with the time "
    "of the scene in that frame. While that scene is current, the renderer keeps the scene area transparent; while "
    "it is not, the renderer covers the area with its placeholder. - In the display's runs the IVI VM runs no other "
    "warning presentation, so no element but the renderer draws the vehicle speed or the collision warning. The "
    "realization, the runs and the verdicts of the driver-assistance increment stay as they are. - The vehicle speed "
    "follows the vehicle's own path: an ECU measures it, the vehicle network carries it to the central computer, and "
    "the SDV Core VM takes it in as vehicle data. A DE4SDV publisher in the SDV Core VM gives it to the renderer's "
    "vehicle data. On the bench the simulator stands in for the ECU and the network. - No readiness session runs "
    "with this phase. One follows it, at its cost and with the owner's go each time.",
    "Four software elements carry the three logical elements:",
    "- **Identity recording service** (DE4SDV, on the central computer) carries the identity recorder. It has no "
    "port: it sends nothing to another element. - **Scene drawing app** (DE4SDV, in the IVI VM) carries the scene "
    "drawer. It takes the scene through the SDV Gateway, draws it in the scene area of the IVI plane and sends the "
    "heartbeats. It draws neither the speed nor the warning. - **High availability renderer** (Android SDV's, in the "
    "SDV Media VM, with DE4SDV changes) and the **composition of the display** (on the central computer) carry the "
    "presenter together. The renderer judges whether the scene as drawn, the speed and the warning request are "
    "current, draws the speed, the warning and the symbol that the warning is unavailable on its plane, and gives "
    "the chime. The composition puts the renderer's plane over the IVI plane and adds nothing.",
    "The presenter is allocated to both, because the drawn scene reaches the display only through the composition. "
    "Without the presenter, the composition would be a way from the scene drawer to the driver beside the presenter, "
    "and the showing of the drawn scene would split, which Phase 7 rules out. Neither element is in the IVI VM, so "
    "both go on through each outage there. The heartbeats and the IVI plane together realize the drawn scenes of "
    "Phase 7. There are four allocations; an allocation is a responsibility assignment, no deployment or runtime "
    "claim.",
    "The inputs reach the display in the SDV Core VM. The warning request comes as the Data Tunnel topic of the "
    "driver-assistance increment, the speed as vehicle data, and the scene as a Data Tunnel topic that a context "
    "stand-in publishes, since the scene's way out of the candidate stays open. The Data Tunnel carries the scene to "
    "the SDV Gateway on the IVI VM. A DE4SDV vehicle data publisher in the SDV Core VM, which carries no logical "
    "element, gives the renderer the speed, the warning request and the time of each scene. The physical system "
    "carries `reqRendererSplitAndInputPaths` (REQ-HMI-009) by a dependency from its definition. The IVI VM of the "
    "display's runs is a definition of its own, so it holds no other warning presentation. The central computer runs "
    "the three VMs under its hypervisor; on the bench the guest host of INC-DRIVING-001 stands in for it, and no "
    "element of the bench is modeled here.",
    "Of the display's 0.1 s, Phase 8 gives 0.05 s to the hop from the SDV Core VM to the renderer or to the app, and "
    "0.05 s to the drawing and to the start of the sound. Both are unmeasured and revisited when a readiness probe "
    "measures them. An outdated scene shows as the renderer's placeholder over the scene area, an outdated speed as "
    "no number, and an unavailable warning as one fixed symbol; the visual design stays out of scope. The speed is "
    "typed by COVESA VSS at its ports, and so is the distance to the object that the system acts on in the scene "
    "message (`Vehicle.ADAS.ObstacleDetection.Distance`); the warning request keeps the payload of the "
    "driver-assistance increment. Every other item says in its mapping record why it is no vehicle signal. There are "
    "eight mappings.",
    "Four gaps of the realization state what is not settled: the renderer's judging of the scene by the term current "
    "(`gapHmiRendererJudgesSceneCurrency`), the bench's feed of the speed into the SDV Core VM "
    "(`gapHmiBenchSpeedFeed`), the tolerance of a drawn position (`gapHmiDrawingToleranceUnset`), and the display "
    "identity, which does not name the builds of the vehicle data publisher, of the identity recording service and "
    "of the composition, nor the image of the SDV Core VM (`gapHmiIdentityMissesPhase8Elements`). Comments on the "
    "framing's gaps say what this phase placed: the path to the renderer, the heartbeats, the composition and the "
    "chime are placed and not observed on the bench. The changes to the projects of the renderer and of the "
    "candidate stay gaps, and nothing is written to their maintainers.",
    "Three alternatives were not selected: the recorder inside the SDV Core VM, the app streaming its drawn frames "
    "to the renderer, and the speed on the Eclipse S-CORE path.",
    "Three views answer the concerns of this phase: the structure as a tree of the SAF Physical Structure Definition "
    "viewpoint; the mapping as a matrix of logical element by software element of the Physical Logical Mapping "
    "viewpoint, which also frames `hmiRendererAllocationConcern`; and the paths as an interconnection of the "
    "Physical Internal Exchange viewpoint, which frames `hmiRendererPathConcern`. They are listed in "
    "[`VIEWS.md`](../../textual-notation-of-model/packages/features/hmi/VIEWS.md).",
    "`tests/test_hmi_display_physical_software_realization.py` pins the elements, their ports and paths, the "
    "allocations, the mappings, the views and this section.",
]


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(text.replace("*", " ").split())


def _doc(declaration: str) -> str:
    """The doc text of the element whose body follows ``declaration`` in the raw model."""
    assert _raw().count(declaration) == 1, declaration
    body = braced_body(_raw(), declaration)
    match = re.match(r"\s*doc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{declaration}: the doc must open the body"
    return _flat(match.group(1))


def _comment(name: str) -> str:
    match = re.search(rf"\bcomment\s+{name}\s+about\s+\w+\s*/\*(.*?)\*/", _raw(), re.S)
    assert match, name
    return _flat(match.group(1))


def _header_paragraphs() -> list[str]:
    head = _raw().split(f"package {PACKAGE}", 1)[0]
    assert head.startswith("/*") and head.rstrip().endswith("*/")
    lines = [re.sub(r"^\s*\*?\s?", "", line) for line in head.strip()[2:-2].splitlines()]
    return [" ".join(part.split()) for part in "\n".join(lines).split("\n\n") if part.strip()]


def _direct(body: str) -> str:
    """Blank nested bodies, so only the direct members of ``body`` remain visible."""
    out, depth = [], 0
    for char in body:
        if char == "}":
            depth -= 1
        out.append(char if depth == 0 else " ")
        if char == "{":
            depth += 1
    return "".join(out)


def _definition(name: str) -> str:
    header = re.search(rf"\bpart\s+def\s+{name}\b[^{{;]*\{{", _code())
    assert header, name
    return braced_body(_code(), header.group(0)[:-1].rstrip())


def _connections(name: str) -> list[tuple[str, str, str]]:
    return re.findall(r"\bconnection\s+(\w+)\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*[;{]", _direct(_definition(name)))


def _binds(name: str) -> list[tuple[str, str]]:
    return re.findall(r"\bbind\s+([\w.]+)\s*=\s*([\w.]+)\s*;", _direct(_definition(name)))


def _strings_blanked(code: str) -> str:
    return re.sub(r'"[^"\n]*"', '""', code)


def _port_items() -> dict[str, tuple[str, str, str]]:
    """Every port definition this package uses -> its one directed item (direction, name, type)."""
    items = {}
    for path in (MODEL, ASSIST_P):
        code = strip_comments(path.read_text(encoding="utf-8"))
        for name in re.findall(r"\bport\s+def\s+(\w+)\s*\{", code):
            if path == ASSIST_P and name not in IMPORTED_PORT_DEFS:
                continue
            found = re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", braced_body(code, f"port def {name}"))
            assert len(found) == 1, name
            items[name] = found[0]
    return items


def _end_item(container: str, end: str) -> tuple[str, str]:
    """The (direction, item type) at a connection or bind end inside ``container``, read through the definitions."""
    items = _port_items()
    ports = dict(PORTS[container])
    if "." not in end:
        return items[ports[end]][0], items[ports[end]][2]
    part, port = end.split(".")
    definition = {name: typ for _, name, typ in PARTS[container]}[part]
    found = items[dict(PORTS[definition])[port]]
    return found[0], found[2]


def _records() -> dict[str, dict[str, str]]:
    """Each mapping record -> its attribute values as written (a string without its quotes, or the literal)."""
    records = {}
    for _, short, record, _, _ in MAPPINGS:
        body = braced_body(_raw(), f"item <'{short}'> {record} : LogicalToSoftwareSignalMappingRecord")
        body = re.sub(r"doc\s*/\*.*?\*/", "", body, flags=re.S)
        values = re.findall(r'^\s*attribute\s+:>>\s+(\w+)\s*=\s*("(?:[^"\\]|\\.)*"|[\w:]+)\s*;\s*$', body, re.M)
        records[record] = {name: value[1:-1] if value.startswith('"') else value for name, value in values}
    return records


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _guide_section(guide: str) -> str:
    return guide.split(GUIDE_HEADING + "\n", 1)[1].split("\n## ", 1)[0]


# -- the package and its elements ----------------------------------------------------------------------------------


def test_the_charter_names_the_package_after_the_logical_architecture():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part hmiDisplayCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    # phase 9 follows phase 8 in the charter
    assert names.index(PACKAGE) == names.index(LOGICAL_PACKAGE) + 1 == len(names) - 2
    assert names[-1] == "DE4SDV_HmiDisplayVariabilityConfiguration"
    assert names.count(PACKAGE) == 1
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", _code())


def test_the_header_states_its_text_of_record():
    assert _header_paragraphs() == HEADER_PARAGRAPHS


def test_the_header_records_the_placement_decision_with_its_five_bullets_in_order():
    paragraphs = _header_paragraphs()
    index = paragraphs.index("The placement (owner decision of 2026-11-25):")
    bullets = [bullet for bullet in re.split(r"(?:^|\s)- (?=[A-Z])", paragraphs[index + 1]) if bullet]
    assert len(bullets) == 5
    assert [bullet.split(":")[0].split(",")[0][:40] for bullet in bullets] == [
        "The identity recorder is a DE4SDV servic", "The drawn scene reaches the screen by co",
        "In the display's runs the IVI VM runs no", "The vehicle speed follows the vehicle's ",
        "No readiness session runs with this phas"]
    assert "(eeSensorDataOutOfScope)" in bullets[3]
    assert " ".join(paragraphs).count("owner decision of 2026-11-25") == 1


def test_the_package_imports_one_by_one():
    imports = re.findall(r"^\s*private\s+import\s+([\w:*]+)\s*;", _code(), re.M)
    assert sorted(imports) == sorted(IMPORTS), "the imports, each once; their order is free"
    assert len(re.findall(r"\bimport\b", _code())) == len(IMPORTS)
    assert not re.search(r"\bpublic\s+import\b", _code())


def test_the_four_software_elements_are_the_physical_elements_and_nothing_else_is():
    code = _code()
    declared = re.findall(r"\bpart\s+def\s+(\w+)\s*:>\s*PhysicalAllocationElement\s*\{", code)
    assert declared == ELEMENT_DEFINITIONS
    assert len(re.findall(r"\bPhysicalAllocationElement\b", code)) == len(ELEMENT_DEFINITIONS) + 1, \
        "the import and the four"
    assert re.findall(r"\bpart\s+def\s+(\w+)", code) == ELEMENT_DEFINITIONS + NOT_ELEMENTS
    for name in NOT_ELEMENTS:
        assert re.search(rf"\bpart\s+def\s+{name}\s*\{{", code), f"{name} specializes nothing"
    for definition in ELEMENT_DEFINITIONS:
        assert _doc(f"part def {definition} :> PhysicalAllocationElement").startswith("Carries "), definition


@pytest.mark.parametrize("definition", list(PORTS), ids=list(PORTS))
def test_each_definition_declares_exactly_its_ports(definition):
    body = _direct(_definition(definition))
    assert re.findall(r"^\s*port\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M) == PORTS[definition]
    assert len(re.findall(r"\bport\b", body)) == len(PORTS[definition])


@pytest.mark.parametrize("definition", list(PARTS), ids=list(PARTS))
def test_each_container_holds_exactly_its_parts_binds_and_connections(definition):
    body = _direct(_definition(definition))
    parts = re.findall(r"^\s*(ref\s+part|part)\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M)
    assert [(" ".join(kind.split()), name, typ) for kind, name, typ in parts] == PARTS[definition]
    assert len(re.findall(r"\bpart\b", body)) == len(PARTS[definition])
    assert _binds(definition) == BINDS[definition]
    assert len(re.findall(r"\bbind\b", body)) == len(BINDS[definition])
    assert _connections(definition) == CONNECTIONS[definition]
    assert len(re.findall(r"\bconnection\b", body)) == len(CONNECTIONS[definition])


#: The member kinds each body may hold, at any indentation, with the continuation words of its multi-line members.
ALLOWED_PACKAGE = (r"(?:private import|item def|port def|part def|part|allocation|allocate|to|dependency|from|"
                   r"comment|concern|view)")
ALLOWED_CONTAINER = r"(?:doc|port|part|ref part|bind|connection|interface|connect)"


def test_no_body_holds_a_member_kind_that_no_pin_reads():
    package = _direct(braced_body(_code(), f"package {PACKAGE}"))
    heads = re.findall(r"(?m)^[ \t]*(\w+(?:[ \t]+\w+)?)", package)
    assert all(re.match(ALLOWED_PACKAGE + r"\b", h) for h in heads), heads
    assert re.findall(r"(?m)^\s*ref\s+part\b", package) == []
    for name in PARTS:
        body = _direct(_definition(name))
        heads = re.findall(r"(?m)^[ \t]*(\w+(?:[ \t]+\w+)?)", body)
        assert all(re.match(ALLOWED_CONTAINER + r"\b", h) for h in heads), (name, heads)
    assert not re.search(r"\b(?:flow|binding|action|perform|exhibit|succession|message)\b",
                         _strings_blanked(_code()))


def test_the_software_elements_hold_ports_and_nothing_else():
    for definition in ELEMENT_DEFINITIONS + ["RendererVehicleDataPublisher"]:
        body = _definition(definition)
        assert not re.search(r"\b(part|action|perform|flow|item|attribute|connection|bind)\b", body), definition


def test_the_items_and_the_port_definitions_carry_one_item_each_in_one_direction():
    code = _code()
    declared = re.findall(r"\bitem\s+def\s+(\w+)\s*(?::>\s*(\w+)\s*)?\{", code)
    assert [(name, parent or None) for name, parent in declared] == [(n, p) for n, (p, _) in ITEMS.items()]
    for name, (_, attributes) in ITEMS.items():
        body = braced_body(code, f"item def {name}")
        assert re.findall(r"\battribute\s+(\w+)\s*:\s*([\w:]+(?:\[[^\]]*\])?(?:\s+ordered)?)\s*;", body) == \
            attributes, name
        assert len(re.findall(r"\battribute\b", body)) == len(attributes), name
    assert re.findall(r"\bport\s+def\s+(\w+)", code) == list(PORT_ITEMS)
    for port_def, (direction, item, item_type) in PORT_ITEMS.items():
        body = braced_body(code, f"port def {port_def}")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [(direction, item, item_type)], \
            port_def
        assert len(re.findall(r"\bitem\b", body)) == 1, port_def
    used = {port_def for ports in PORTS.values() for _, port_def in ports}
    assert used == set(PORT_ITEMS) | set(IMPORTED_PORT_DEFS), "every port definition is used, and only these"


def test_the_recorder_has_no_port_records_before_the_vms_start_and_names_every_part_of_the_term():
    body = braced_body(_code(), "part def DisplayIdentityRecordingService :> PhysicalAllocationElement")
    assert body.split() == ["doc"], "a doc and nothing else"
    assert re.findall(r"\b(\w+)\s*:(?![:>])\s*DisplayIdentityRecordingService\b", _code()) == [
        "identityRecordingService"]
    assert ("part", "identityRecordingService", "DisplayIdentityRecordingService") in PARTS[CENTRAL]
    doc = _doc("part def DisplayIdentityRecordingService :> PhysicalAllocationElement")
    for phrase in ("before it starts the IVI and SDV Media VMs, it records the display identity",
                   "the files of the build of the high availability renderer", "the build of the scene drawing app",
                   "the image of the IVI VM and of the SDV Media VM", "the sound file of the collision warning",
                   "each configuration file that the HMI display reads at its start",
                   "the settings of its start, verbatim", "Only then does it start the two VMs",
                   "on the bench the guest host stands in for it", "(owner decision of 2026-11-25)"):
        assert phrase in doc, phrase
    term = _flat(re.search(r"- Display identity:(.*?)(?=- Run:)", NEEDS.read_text(encoding="utf-8"), re.S).group(1))
    for part in ("of the build of the high availability renderer", "of the image of the IVI VM and of the SDV Media VM",
                 "of the sound file of the collision warning", "each configuration file that the HMI display reads at "
                 "its start", "the settings of its start, verbatim"):
        assert part in term, part
    assert not any("identityRecordingService" in end for name in PARTS for _, *ends in _connections(name)
                   for end in ends)


def test_the_central_computer_is_its_own_definition_typed_by_the_generic_layers():
    code = _code()
    assert re.search(rf"\bpart\s+def\s+{CENTRAL}\s*\{{", code), "it specializes nothing"
    body = _direct(_definition(CENTRAL))
    # The layers are referenced, as the phase 9 product binds them to the projection's; the stack owns them.
    assert re.search(r"^\s*ref\s+part\s+os\s*:\s*OSPlatformLayer\s*;", body, re.M)
    assert re.search(r"^\s*ref\s+part\s+hypervisor\s*:\s*HypervisorLayer\s*;", body, re.M)
    media = _direct(_definition("HmiDisplaySDVMediaGuest"))
    assert re.search(r"^\s*ref\s+part\s+os\s*:\s*OSPlatformLayer\s*;", media, re.M)
    assert not re.search(r"^\s*part\s+(?:os|hypervisor)\s*:\s*(?:OSPlatformLayer|HypervisorLayer)\s*;", code, re.M)
    assert "private import DE4SDV_SDVPlatformStack::HypervisorLayer;" in code


def test_no_part_is_typed_by_the_bench_host_or_its_layers():
    code = _code()
    assert not re.search(r"\b(?:AAOSGuestHost|KVMHypervisor|LinuxPlatform)\b", code)
    assert "DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization" not in code
    assert not re.search(r":>\s*\w*GuestHost\b", code)


def test_the_system_its_usage_and_its_structure_concern_describe_the_vehicle():
    texts = [_doc(f"part def {SYSTEM}"), _doc(f"part {SYSTEM_USAGE} : {SYSTEM}"),
             _doc("concern hmiDisplayPhysicalStructureConcern : PhysicalStructureConcern")]
    allowed = "no part here stands for them or for an element of the bench"
    assert texts[0].count(allowed) == 1
    for text in texts:
        assert "bench" not in text.replace(allowed, ""), text[:80]
        assert "guest host" not in text, text[:80]
    assert texts[0].startswith("The physical realization of the HMI display in the vehicle: the central computer")


def test_the_guest_host_appears_only_where_it_stands_in_or_is_asked_about():
    # every sentence of a doc or comment that names the guest host says that it stands in for the central computer,
    # or asks what a probe on it has not measured yet
    for text in [_flat(block) for block in re.findall(r"/\*(.*?)\*/", _raw(), re.S)]:
        for sentence in re.split(r"(?<=[.;:])\s+", text):
            if "guest host" in sentence:
                assert ("stands in for it" in sentence or "the guest host on the bench" in sentence
                        or "no readiness probe has measured" in sentence), sentence


# -- the paths -----------------------------------------------------------------------------------------------------


def test_the_physical_system_joins_the_central_computer_and_the_three_vms():
    code = _code()
    body = _direct(_definition(SYSTEM))
    found = re.findall(r"\binterface\s+(\w+)\s*:\s*OSHypervisorInterface\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*;",
                       body)
    assert found == INTERFACES
    assert len(re.findall(r"\binterface\b", _strings_blanked(code))) == len(INTERFACES)
    assert len(re.findall(r"\bconnect\b", code)) == sum(len(c) for c in CONNECTIONS.values()) + len(INTERFACES)
    # one usage of the physical definition, for the views; bound to nothing and adding nothing
    assert re.findall(rf"^\s*part\s+(\w+)\s*:\s*{SYSTEM}\s*[{{;=]", code, re.M) == [SYSTEM_USAGE]
    assert braced_body(code, f"part {SYSTEM_USAGE} : {SYSTEM}").split() == ["doc"]
    package = _direct(braced_body(code, f"package {PACKAGE}"))
    assert re.findall(r"^\s*part\s+(?!def\b)(\w+)\s*:", package, re.M) == [SYSTEM_USAGE]


@pytest.mark.parametrize("container", list(CONNECTIONS), ids=list(CONNECTIONS))
def test_each_connection_and_each_bind_runs_in_the_direction_of_its_port_items(container):
    """A connection goes from an out port to an in port of the same item; a bind delegates one direction."""
    for name, source, target in CONNECTIONS[container]:
        if source.startswith(("sdvCore.", "sdvGateway.")):
            continue  # a port of the platform boundary, typed by the platform's port definitions
        assert _end_item(container, source)[0] == "out", (name, source)
        assert _end_item(container, target)[0] == "in", (name, target)
        assert _end_item(container, source)[1] == _end_item(container, target)[1], name
    for own, inner in BINDS[container]:
        if inner.startswith(("sdvCore", "sdvGateway")) or own == "sdvCore":
            continue
        assert _end_item(container, own) == _end_item(container, inner), (own, inner)


def test_nothing_leads_back_and_the_renderer_takes_four_inputs():
    system = CONNECTIONS[SYSTEM]
    assert not [name for name, _, target in system if target.startswith("hmiSDVCoreGuest.")], "nothing into SDV Core"
    assert not [name for name, source, target in system
                if target.startswith("hmiIVIGuest.") and not source.startswith("hmiSDVCoreGuest.")]
    assert not [name for name, source, _ in system if source.startswith("centralComputer.")]
    into_media = [target.split(".")[1] for _, _, target in system if target.startswith("hmiSDVMediaGuest.")]
    assert into_media == ["speedSampleIn", "warningEventIn", "sceneTimeIn", "heartbeatIn"]
    items = _port_items()
    inputs = [port for port, port_def in PORTS["HighAvailabilityRenderer"] if items[port_def][0] == "in"]
    assert inputs == into_media, "the renderer's only inputs"
    assert [source.split(".")[0] for _, source, target in system if target.startswith("hmiSDVMediaGuest.")] == [
        "hmiSDVCoreGuest", "hmiSDVCoreGuest", "hmiSDVCoreGuest", "hmiIVIGuest"]
    into_central = [(source, target) for _, source, target in system if target.startswith("centralComputer.")]
    assert into_central == [("hmiIVIGuest.iviPlaneOut", "centralComputer.iviPlaneIn"),
                            ("hmiSDVMediaGuest.rendererPlaneOut", "centralComputer.rendererPlaneIn")]


def test_the_ivi_vm_holds_the_gateway_and_the_app_and_no_other_warning_presentation():
    code = _code()
    assert re.search(r"\bpart\s+def\s+HmiDisplayIVIGuest\s*\{", code), "its own definition, no specialization"
    assert not re.search(r"\b(?:CollisionWarningPresentationApplication|DriverAssistanceIVIGuest)\b", code)
    assert [typ for _, _, typ in PARTS["HmiDisplayIVIGuest"]] == ["AndroidHLOS", "SDVGatewayOnIVIBoundary",
                                                                   "SceneDrawingApplication"]
    doc = _doc("part def SceneDrawingApplication :> PhysicalAllocationElement")
    assert "It draws neither the vehicle speed nor the collision warning and gives no sound (REQ-HMI-009)." in doc


def test_the_sdv_core_vm_references_the_platform_boundary_and_holds_the_publisher():
    body = _direct(_definition("HmiDisplaySDVCoreGuest"))
    assert re.search(r"^\s*ref\s+part\s+sdvCore\s*:\s*SDVCoreBoundary\s*;", body, re.M)
    assert re.search(r"^\s*bind\s+sdvCore\s*=\s*sdvMiddleware\s*;", body, re.M)
    assert not re.search(r"(?m)^\s*part\s+\w+\s*:\s*SDVCoreBoundary\b", _code()), "the guest boundary is referenced"
    assert re.findall(r"\b(\w+)\s*:(?![:>])\s*RendererVehicleDataPublisher\b", _code()) == ["vehicleDataPublisher"]


def test_vss_types_the_vehicle_speed_at_its_ports_and_the_warning_keeps_its_payload():
    code = _strings_blanked(_code())
    assert re.findall(r"(?<!:):(?!:)\s*(Vehicle_\w+)", code) == ["Vehicle_ADAS_ObstacleDetection_Distance",
                                                                "Vehicle_Speed"]
    assert "private import COVESA_VSS::SignalDefinitions::Vehicle_Speed;" in code
    assert "private import COVESA_VSS::SignalDefinitions::Vehicle_ADAS_ObstacleDetection_Distance;" in code
    assert "DE4SDV_VSS_Extensions" not in code and "VssSignalMetadata" not in code
    assert not re.search(r"\b(?:item|port)\s+def\s+WarningRequestEvent", code), "imported, never redeclared"
    for name in ("WarningRequestEventPayload", "WarningRequestEventIn", "WarningRequestEventOut"):
        assert f"private import DE4SDV_DriverAssistancePhysicalSoftwareRealization::{name};" in code, name


# -- allocations, mappings and the path requirement ----------------------------------------------------------------


def test_each_logical_element_is_allocated_to_the_software_that_carries_it():
    code = _code()
    rows = re.findall(r"\ballocation\s+(\w+)\s+allocate\s+(\S+)\s+to\s+([^\s;{]+)\s*;", code)
    assert rows == [(name, f"{LOGICAL_SYSTEM}::{logical}", f"{SYSTEM_USAGE}::{physical}")
                    for name, logical, physical in ALLOCATIONS]
    assert len(re.findall(r"\ballocation\b", code)) == len(ALLOCATIONS) + len(MAPPINGS)
    targets = {}
    for _, logical, physical in ALLOCATIONS:
        targets.setdefault(logical, []).append(physical.split("::")[-1])
    assert targets == {"displayIdentityRecorder": ["identityRecordingService"], "sceneDrawer": ["sceneDrawingApp"],
                       "displayPresenter": ["highAvailabilityRenderer", "planeComposition"]}
    logical = strip_comments(LOGICAL.read_text(encoding="utf-8"))
    assert re.findall(r"^\s*part\s+(\w+)\s*:\s*\w+\s*;", braced_body(logical, f"part def {LOGICAL_SYSTEM}"),
                      re.M) == list(targets)


def test_each_crossing_has_one_signal_mapping_with_a_complete_record():
    code = _code()
    found = re.findall(r"\ballocation\s+(\w+)\s*:\s*SystemToSoftwareSignalMappingCandidate\s+allocate\s+(\S+)\s+to\s+"
                       r"([^\s{;]+)\s*\{\s*item\s+<'([A-Z-]+)'>\s+(\w+)\s*:\s*LogicalToSoftwareSignalMappingRecord",
                       code)
    assert found == [(name, f"{LOGICAL_SYSTEM}::{logical}", f"{SYSTEM_USAGE}.{port}", short, record)
                     for name, short, record, logical, port in MAPPINGS]
    assert len(re.findall(r"\bSystemToSoftwareSignalMappingCandidate\b", code)) == len(MAPPINGS) + 1
    records = _records()
    for record, values in records.items():
        assert tuple(values) == RECORD_ATTRIBUTES, record
        assert values["disposition"] == "SignalMappingDisposition::candidate", record
        assert values["owner"] == "DE4SDV maintainers", record
        assert values["semanticSource"].strip() and values["nextAction"].strip(), record
        assert values["nextAction"].endswith("; none is started"), record
        assert values["evidenceOrGap"].startswith("no runtime evidence of record; "), record


@pytest.mark.parametrize("record", [m[2] for m in MAPPINGS], ids=[m[1] for m in MAPPINGS])
def test_each_record_states_its_values_of_record(record):
    assert _records()[record] == RECORD_VALUES[record]
    short = next(m[1] for m in MAPPINGS if m[2] == record)
    assert _doc(f"item <'{short}'> {record} : LogicalToSoftwareSignalMappingRecord") == RECORD_DOCS[record]


def test_every_item_that_is_no_vehicle_signal_says_so_and_the_speed_names_its_vss_type():
    records = _records()
    for _, short, record, _, _ in MAPPINGS:
        source = records[record]["semanticSource"]
        if short == "MAP-HMI-VEHICLE-SPEED":
            assert "COVESA VSS Vehicle_Speed" in source
        elif short == "MAP-HMI-SCENE":
            assert "which COVESA VSS types at the port as Vehicle_ADAS_ObstacleDetection_Distance " in source
            assert "no vehicle signal, except the distance to the object that the system acts on" in source
        elif short == "MAP-HMI-WARNING-REQUEST":
            assert "Vehicle_ADAS_AEBS_DriverWarning_IsActive" in source and "WarningRequestEventPayload" in source
        else:
            assert "no vehicle signal" in source, short


def test_the_time_of_the_display_is_split_and_unmeasured():
    records = _records()
    timed = [short for _, short, record, _, _ in MAPPINGS if "0.05 s" in records[record]["timingQualityAndState"]]
    assert timed == ["MAP-HMI-SCENE", "MAP-HMI-VEHICLE-SPEED", "MAP-HMI-WARNING-REQUEST", "MAP-HMI-SCENE-TIME",
                     "MAP-HMI-WARNING-CHIME", "MAP-HMI-SHOWN-CONTENT"]
    for short in timed:
        record = next(m[2] for m in MAPPINGS if m[1] == short)
        assert "unmeasured" in records[record]["timingQualityAndState"], short
    for definition, phrase in (("SceneDrawingApplication", "Of the display's 0.1 s it has 0.05 s, from the arrival "
                                "of a scene to its first frame on the display, unmeasured."),
                               ("HighAvailabilityRenderer", "Of the display's 0.1 s it has 0.05 s, from the arrival "
                                "of a value to the first frame on the display that shows it and to the start of the "
                                "chime, unmeasured.")):
        assert phrase in _doc(f"part def {definition} :> PhysicalAllocationElement"), definition
    assert "0.05 s is for the hop from the SDV Core VM to the renderer or to the app, and 0.05 s for the drawing" \
        in " ".join(_header_paragraphs())


def test_the_looks_of_an_outdated_element_are_this_phases():
    rule = _records()["shownContentMappingRecord"]["transformationRule"]
    assert rule == ("an outdated scene shows as the renderer's placeholder over the scene area; an outdated speed "
                    "shows no number; an unavailable warning shows one fixed symbol; a current element shows as given")
    doc = _doc("part def HighAvailabilityRenderer :> PhysicalAllocationElement")
    for phrase in ("it draws the vehicle speed to the whole km/h and no number while the speed is outdated",
                   "and one fixed symbol while the warning is unavailable",
                   "covers it with its placeholder while it is outdated"):
        assert phrase in doc, phrase


def test_the_path_requirement_is_carried_by_a_dependency_from_the_physical_system():
    code = _code()
    assert re.findall(r"\bdependency\s+(\w+)\s+from\s+(\w+)\s+to\s+(\w+)\s*;", code) == [
        ("physicalSystemCarriesRendererSplitAndInputPaths", SYSTEM, "reqRendererSplitAndInputPaths")]
    assert len(re.findall(r"\bdependency\b", code)) == 1
    assert "private import DE4SDV_HmiDisplayNeedsRequirements::reqRendererSplitAndInputPaths;" in code
    assert not re.search(r"\ballocate\s+\w*req[A-Z]", code), "no allocation names a requirement"
    assert len(re.findall(r"\breq[A-Z]\w*", code)) == 2, "the import and the dependency"


# -- comments, gaps and texts of record ----------------------------------------------------------------------------


def test_the_comments_record_what_phase_8_placed_on_the_framing_records():
    code = _code()
    declared = dict(re.findall(r"\bcomment\s+(\w+)\s+about\s+(\w+)\s*$", code, re.M))
    assert declared == COMMENTS
    for name in COMMENTS:
        assert _comment(name) == COMMENT_TEXTS[name], name
    for record in COMMENTS.values():
        assert f"private import DE4SDV_HmiDisplayFraming::{record};" in code, record


def test_the_gaps_of_the_realization_are_recorded_with_their_short_names_and_no_disposition():
    code = _code()
    assert dict(re.findall(r"\bpart\s+<'(GAP-HMI-\d{3})'>\s+(\w+)\s*:\s*IncrementGap\s*\{", code)) == GAPS
    assert len(re.findall(r"<'(?:ASM|GAP)-[A-Z]+-\d{3}'>", code)) == len(GAPS)
    for short, name in GAPS.items():
        body = braced_body(code, f"part <'{short}'> {name} : IncrementGap")
        assert body.split() == ["doc"], "open, with no disposition yet"
        assert _doc(f"part <'{short}'> {name} : IncrementGap") == GAP_DOCS[short], short
    assert "private import DE4SDV_MethodContext::*;" in code


def test_the_display_identity_gap_names_what_the_term_misses():
    # The term of phase 5 names the builds of the two drawing elements and the images of the IVI and SDV Media VMs;
    # phase 8 places three more elements inside the display, and the platform of the SDV Core VM carries the inputs
    # on. The gap stays true while the term does not name them.
    doc = _doc("part <'GAP-HMI-004'> gapHmiIdentityMissesPhase8Elements : IncrementGap")
    for phrase in ("the vehicle data publisher in the SDV Core VM",
                   "the identity recording service and the composition on the central computer.",
                   "Nor does it name the image of the SDV Core VM, whose platform carries the scene on to the IVI VM "
                   "and the other inputs to the publisher.",
                   "A change to one of them records the same display identity",
                   "so REQ-HMI-010 is not met as worded until the term names them, before phase 10."):
        assert phrase in doc, phrase
    term = _flat(re.search(r"- Display identity:(.*?)(?=- Run:)", NEEDS.read_text(encoding="utf-8"), re.S).group(1))
    for element in ("publisher", "recording service", "composition", "SDV Core VM"):
        assert element not in term, element
    assert "(`gapHmiIdentityMissesPhase8Elements`)" in " ".join(GUIDE_BLOCKS)


@pytest.mark.parametrize("declaration", list(DOCS), ids=DOC_IDS)
def test_each_element_states_its_text_of_record(declaration):
    assert _doc(declaration) == DOCS[declaration]


def test_every_doc_of_the_package_is_pinned():
    docs = len(re.findall(r"\bdoc\s*/\*", _raw()))
    assert docs == len(DOCS) + len(RECORD_DOCS) + len(GAP_DOCS)


def test_every_plain_comment_is_a_section_heading_that_names_no_bench():
    body = _raw().split(f"package {PACKAGE}", 1)[1]
    blocks = re.findall(r"(\bdoc\s*|\bcomment\s+\w+\s+about\s+\w+\s*)?/\*(.*?)\*/", body, re.S)
    plain = [_flat(text) for lead, text in blocks if not lead]
    assert len(plain) == 11
    assert all(text.startswith("─" * 13 + " ") and "bench" not in text and "guest host" not in text
               for text in plain), plain


def test_the_element_docs_make_no_assurance_claim():
    for declaration in [f"part def {d} :> PhysicalAllocationElement" for d in ELEMENT_DEFINITIONS] + \
            [f"part def {name}" for name in NOT_ELEMENTS]:
        doc = _doc(declaration)
        assert not [word for word in CLAIM_WORDS if word in doc.lower()], declaration
    head = " ".join(_header_paragraphs())
    disclaimer = ("Nothing in this package claims that a requirement is met, that a case ran or that the bench has "
                  "shown anything.")
    assert head.count(disclaimer) == 1
    assert not [word for word in CLAIM_WORDS if word in head.replace(disclaimer, "").lower()]
    assert not re.search(r"\b(realizedBy|deployedTo|validatedBy|constrainedBy|satisfy|verify)\b",
                         _strings_blanked(_code()))


def test_no_text_of_phase_8_quotes_the_owner_or_carries_a_banned_word():
    section = _guide_section(_guide())
    texts = {"model": _raw(), "guide section": section, "this test": Path(__file__).read_text(encoding="utf-8")}
    for label, text in texts.items():
        words = set(re.findall(r"[a-z0-9]+", text.lower()))
        assert len(words) >= 100, label
        digests = {hashlib.sha256(word.encode()).hexdigest() for word in words}
        assert EXCLUDED_WORD_SHA256 not in digests, label
        assert not digests & BANNED_WORD_SHA256, label
        assert LAUNCH_PHRASE not in " ".join(text.split()), label
    for label in ("model", "guide section"):
        flat = _flat(texts[label])
        assert not re.search(r"(?i)\b(?:the owner said|owner's words|in his words|he said)\b", flat), label
        assert not re.search(r"(?i)\b(?:issue|pull request|PR)\s*#?\d+|#\d{2,}", flat), label
    prose = re.sub(r"`[^`]*`|\]\([^)]*\)", " ", section)
    assert '"' not in prose and "\u201c" not in prose and "\u201d" not in prose, "the section quotes nobody"
    for text in [_flat(t) for t in re.findall(r"/\*(.*?)\*/", _raw(), re.S)] + [" ".join(prose.split())]:
        assert not PAST_BEHAVIOR.search(text) and not APPROVAL.search(text), text[:80]


def test_the_package_declares_no_name_that_another_model_package_declares():
    # The platform parts keep the names that the precedent's guests and hosts use for the same parts.
    kinds = r"(?:part def|port def|item def|ref part|part|port|item|concern|view|allocation|connection|interface|" \
            r"dependency|comment)"
    declared = set(re.findall(rf"(?m)^\s*{kinds}\s+(?:<'[^']*'>\s*)?(\w+)", _code()))
    declared -= {"os", "sdvMiddleware", "sdvCore", "sdvGateway", "hypervisor"}
    # the E/E realization of INC-EE-001 may declare it first
    declared -= {"centralComputer"}
    assert len(declared) >= 90, "the population of the check must not be vacuous"
    anywhere = re.compile(rf"\b{kinds}\s+(?:<'[^']*'>\s*)?(\w+)")
    taken: dict[str, list[str]] = {}
    for root in MODEL_ROOTS:
        for path in sorted(root.rglob("*.sysml")):
            if path == MODEL:
                continue
            for name in anywhere.findall(strip_comments(path.read_text(encoding="utf-8"))):
                if name in declared:
                    taken.setdefault(name, []).append(path.name)
    assert not taken, f"declared in another package too: {taken}"


# -- views -----------------------------------------------------------------------------------------------------------


def test_the_package_publishes_exactly_one_view_per_question():
    declared = re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M)
    assert declared == list(VIEWS)


@pytest.mark.parametrize("view_name", list(VIEWS), ids=list(VIEWS))
def test_each_view_frames_its_concerns_and_exposes_its_content(view_name):
    view_type, render, exposes, viewpoint_type, frames = VIEWS[view_name]
    code = _code()
    view = braced_body(code, f"view {view_name}" + (f" : {view_type}" if view_type else ""))
    viewpoint = braced_body(view, "viewpoint")
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == frames
    assert re.search(rf"viewpoint\s+\w+\s*:\s*{viewpoint_type}\s*\{{", view), view_name
    assert len(re.findall(r"\bviewpoint\b", view)) == 1
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", view) == exposes
    assert re.findall(r"\bfilter\s+([^;]+);", view) == VIEW_FILTERS[view_name]
    if render:
        assert render in view
    else:
        assert "render as" not in view, "the view type selects the kind"


def test_the_path_view_takes_the_form_of_the_exchange_views_and_the_tree_sets_nothing():
    path = braced_body(_code(), f"view {PATH_VIEW}")
    assert re.findall(r"\battribute\s+(\w+)\s*=\s*([^;]+);", path) == [("depth", "-1"),
                                                                       ("showAnnotationRows", "false")]
    assert "attribute" not in braced_body(_code(), f"view {STRUCTURE_VIEW}")
    doc = _doc(f"view {PATH_VIEW}")
    for phrase in ("(hmiRendererPathConcern)", "No other port leads to the renderer, and nothing leads back.",
                   "Each edge between the VMs and the central computer is labelled with the ports at its ends,",
                   "The platform of the SDV Core VM is listed by name only;",
                   "its binds and connections are drawn as boxes that name their two ends.",
                   "The hypervisor interfaces are drawn in no view of this phase; the structure tree shows the "
                   "hypervisor and each VM's operating system."):
        assert phrase in doc, phrase
    # The render labels each edge with its end ports, not with the connection name, and draws no interface.
    assert "connection name" not in doc and "structure tree only" not in doc
    # Named exposes only: the platform of the SDV Core VM is not drawn in full, and the binds stay.
    assert "::**" not in path and "::*;" not in path
    assert "BindingConnectorAsUsage" not in path


def test_the_matrix_maps_the_logical_elements_to_the_software_with_reference_elements():
    view = braced_body(_code(), f"view {MATRIX_VIEW} : MVD::MatrixView")
    rows = braced_body(view, "view :>> rowView")
    columns = braced_body(view, "view :>> columnView")
    cells = braced_body(view, "view :>> cellView")
    exposes = VIEWS[MATRIX_VIEW][2]
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", rows) == exposes[:3]
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", columns) == exposes[3:7]
    for axis in (rows, columns):
        assert "attribute :>> includeReferenceElements = true;" in axis
        assert "attribute :>> representation = Rep::name;" in axis
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", cells) == [f"{PACKAGE}::*"]
    assert "attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;" in cells
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"matrix-{MATRIX_VIEW}"]
    assert (metadata.title, metadata.description, metadata.row_label, metadata.column_label) == GRID


@pytest.mark.parametrize("concern_name", list(CATALOGUE_CONCERNS), ids=list(CATALOGUE_CONCERNS))
def test_each_phase_8_concern_is_typed_by_the_catalogue_and_held_by_the_party_it_serves(concern_name):
    catalogue, stakeholders = CATALOGUE_CONCERNS[concern_name]
    concern = braced_body(_code(), f"concern {concern_name} : {catalogue}")
    members = re.findall(r"\b(subject|stakeholder)\b", concern)
    assert members and members[0] == "subject"
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern) == stakeholders
    assert len(re.findall(r"\bconcern\s+\w+\s*:", _code())) == len(CATALOGUE_CONCERNS)


def test_the_phase_1_physical_concerns_are_framed_here_in_their_domain_and_need_no_deviation():
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    code = _code()
    for concern, catalogue in FRAMING_CONCERNS.items():
        assert re.search(rf"\bconcern\s+{concern}\s*:\s*{catalogue}\b", framing), concern
        assert f"private import DE4SDV_HmiDisplayFraming::{concern};" in code, concern
        assert not re.search(rf"\bconcern\s+{concern}\b", code), "framed, never redeclared"
    import test_views_per_phase as views

    assert not [key for key in views.KNOWN_DEVIATIONS if key[0] == "INC-HMI-001"], "the method's own list"


# -- registrations and the guide -----------------------------------------------------------------------------------


def test_the_allocation_file_is_governed_with_its_four_endpoint_definitions():
    import test_trace_allocation_completeness as trace

    assert trace.HMI_P == MODEL
    assert trace.ALLOCATION_FILES[trace.HMI_P] == (
        (trace.HMI_P, trace.HMI_L), {(trace.LOGICAL, trace.PHYSICAL): len(ALLOCATIONS)},
        {"SystemToSoftwareSignalMappingCandidate": len(MAPPINGS)}, (trace.LOGICAL, trace.PHYSICAL))
    assert trace.GOVERNED[trace.HMI_P] == (trace.PHYSICAL, set(ELEMENT_DEFINITIONS))
    assert trace.LINEAGE_FILES.index(trace.HMI_P) == trace.LINEAGE_FILES.index(trace.HMI_L) + 1
    assert trace.NOT_ENDPOINTS[trace.HMI_P] == set(NOT_ELEMENTS)


def test_the_guide_has_a_phase_8_section_and_names_the_next_obligation():
    guide = _guide()
    assert guide.count(GUIDE_HEADING + "\n") == 1
    assert guide.index("## Logical architecture (Phase 7)") < guide.index(GUIDE_HEADING) \
        < guide.index("## What the framing already records as open")
    raw_section = _guide_section(guide)
    assert f"]({GUIDE_LINK})" in raw_section
    blocks = [" ".join(block.split()) for block in re.split(r"\n\s*\n", raw_section.strip())]
    assert blocks == GUIDE_BLOCKS, "every block of the section, whole and in order, as it says"
    assert all(len(line) <= 79 or "](" in line for line in raw_section.splitlines()), "the guide wraps at 79"
    flat = " ".join(guide.split())
    assert flat.count(GUIDE_STATUS) == 1
    assert "and Phase 7 logical architecture, proposal.**" not in flat, "the status line moved to phase 8"
    frame = " ".join(guide.split("## Authoritative frame", 1)[1].split("\n## ", 1)[0].split())
    assert frame.count(GUIDE_FRAME_LINE) == 1, "the frame links the package, as it links each earlier phase"
    nxt = " ".join(guide.split("## Next obligation and execution limits", 1)[1].split("\n## ", 1)[0].split())
    assert nxt.count(GUIDE_NEXT) == 1
    assert "The next model obligation is **Phase 8**" not in flat
    assert flat.count("The next model obligation is") == 1
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert GUIDE_CHECK in check
