"""Content pins for the HMI display functional architecture (phase 6), not semantic validation.

INC-HMI-001 phase 6 breaks the HMI display into its functions and allocates the requirements of phase 5 to the
functions that carry them. Method Check holds the DefineFunctionalArchitecture rules (at least one function; each
functional requirement allocated to a function by a native allocation). These pins hold what review settled on top
of them, the decisions of the design of 2026-11-24:

- five functions, each an AllocatableFunction, and the functional flow that breaks the display into them, with the
  items they exchange: the scene, the vehicle speed and the warning request of phase 2 in, what the display shows
  and the collision warning out, and inside, the record of the display identity, the drawn scenes and the currency
  of the content;
- the drawing of the scene stands apart: judgeCurrency and showContent take nothing from drawScene but the drawn
  scenes, and giveWarning takes nothing from it at all, so an outage of the drawing or of the environment that
  hosts it is an event inside the display that the drawn scenes carry (no detection function of its own);
- the allocation of every requirement but REQ-HMI-009, which constrains which elements draw what and the paths of
  their inputs, not a function, and which phase 8 carries; REQ-HMI-004 and REQ-HMI-005, the asking and its start,
  go to judgeCurrency and giveWarning, since both depend on the currency judgement, and REQ-HMI-002 goes to
  showContent as well as to drawScene, since the mark reaches the display as the scene does; seventeen
  allocations in all;
- the functions the context elements of phase 2 perform, as functions of their own root, outside the display's
  scope, and the system process that runs the display as one action between them, with the times from the start of
  a request to each mode of the warning; its participants are the parts of the one context of phase 2, bound by
  reference, and the context holds no other presentation of the warning;
- the states of each element and of the collision warning, called states and not modes, since phase 5 defines a
  mode as a form of the warning, and the functions that depend on them;
- the conceptual interfaces as port definitions with directed items typed by item definitions of this package that
  specialize the items of phase 2, the speed and the request through the items of the driver-assistance increment,
  adding no attribute; one view per SAF question, five in all;
- no function waits on the drawing of the scene: every exchange is a plain flow, and the only successions put the
  record of the display identity first;
- no technology, platform or claim in the docs of the package, and no vehicle signal specification in it; the
  process view hides doc rows, so the view index notes where its times are, and the lane docs carry them;
- the guide's Phase 6 section, every block whole and in order, as its closing paragraph says.
"""

from pathlib import Path
import hashlib
import re

import pytest

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
HMI = ROOT / "textual-notation-of-model/packages/features/hmi"
MODEL = HMI / "hmi_display_functional_architecture.sysml"
NEEDS_REQUIREMENTS = HMI / "hmi_display_needs_requirements.sysml"
FRAMING = HMI / "hmi_display_framing.sysml"
OPERATIONAL_CONTEXT = HMI / "hmi_display_operational_context.sysml"
DRIVING_FUNCTIONS = ROOT / "textual-notation-of-model/packages/features/driving" / \
    "driver_assistance_functional_architecture.sysml"
GUIDE = ROOT / "docs/guides/hmi-display-increment.md"
MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
PACKAGE = "DE4SDV_HmiDisplayFunctionalArchitecture"
FLOW = "HmiDisplayFunctionalFlow"
FLOW_USAGE = "hmiDisplayFunctionalFlow"
CONCERN = "hmiDisplayFunctionsConcern"
TREE_VIEW = "hmiDisplayFunctionBreakdownView"
MATRIX_VIEW = "hmiDisplayRequirementFunctionMatrixView"
PROCESS_VIEW = "hmiDisplaySystemProcessView"
TABLE_VIEW = "hmiDisplayStateTableView"
INTERFACE_VIEW = "hmiDisplayFunctionalInterfaceView"

#: Each function of the flow, in breakdown order -> its definition.
FUNCTIONS = {
    "recordDisplayIdentity": "RecordDisplayIdentity",
    "drawScene": "DrawScene",
    "judgeCurrency": "JudgeCurrency",
    "showContent": "ShowContent",
    "giveWarning": "GiveCollisionWarning",
}

#: The items the functions exchange inside the display; the boundary items are phase 2's.
INTERNAL_ITEMS = {"DisplayIdentityRecord", "DrawnScene", "ContentCurrency"}

#: Each function definition -> its parameters (direction, name, item type), in order.
FUNCTION_PARAMETERS = {
    "RecordDisplayIdentity": [("out", "identityRecord", "DisplayIdentityRecord")],
    "DrawScene": [("in", "perceivedScene", "PerceivedScene"), ("out", "drawnScene", "DrawnScene")],
    "JudgeCurrency": [("in", "perceivedScene", "PerceivedScene"), ("in", "vehicleSpeed", "VehicleSpeed"),
                      ("in", "warningRequest", "WarningRequest"), ("in", "drawnScene", "DrawnScene"),
                      ("out", "contentCurrency", "ContentCurrency")],
    "ShowContent": [("in", "drawnScene", "DrawnScene"), ("in", "vehicleSpeed", "VehicleSpeed"),
                    ("in", "contentCurrency", "ContentCurrency"), ("out", "shownContent", "HmiDisplayContent")],
    "GiveCollisionWarning": [("in", "warningRequest", "WarningRequest"), ("in", "contentCurrency", "ContentCurrency"),
                             ("out", "collisionWarning", "CollisionWarning")],
}

#: The flow's own parameters: the phase 2 items crossing the boundary of the display.
FLOW_PARAMETERS = [
    ("in", "perceivedScene", "PerceivedScene"),
    ("in", "vehicleSpeed", "VehicleSpeed"),
    ("in", "warningRequest", "WarningRequest"),
    ("out", "shownContent", "HmiDisplayContent"),
    ("out", "collisionWarning", "CollisionWarning"),
]

#: Item flows between the functions (source, target): the drawn scenes and the currency, nothing else.
FLOWS = {
    ("drawScene.drawnScene", "judgeCurrency.drawnScene"),
    ("drawScene.drawnScene", "showContent.drawnScene"),
    ("judgeCurrency.contentCurrency", "showContent.contentCurrency"),
    ("judgeCurrency.contentCurrency", "giveWarning.contentCurrency"),
}
#: The display identity is recorded before the display gives its first frame.
SUCCESSIONS = [("recordDisplayIdentity", "drawScene"), ("recordDisplayIdentity", "showContent"),
               ("recordDisplayIdentity", "giveWarning")]

#: Function parameters bound to the flow's own parameters: (function, direction, parameter, flow parameter).
BINDINGS = {
    ("drawScene", "in", "perceivedScene", "perceivedScene"),
    ("judgeCurrency", "in", "perceivedScene", "perceivedScene"),
    ("judgeCurrency", "in", "vehicleSpeed", "vehicleSpeed"),
    ("judgeCurrency", "in", "warningRequest", "warningRequest"),
    ("showContent", "in", "vehicleSpeed", "vehicleSpeed"),
    ("giveWarning", "in", "warningRequest", "warningRequest"),
    ("showContent", "out", "shownContent", "shownContent"),
    ("giveWarning", "out", "collisionWarning", "collisionWarning"),
}

#: Each requirement of phase 5 -> the functions it is allocated to: seventeen allocations in all.
ALLOCATION_COUNT = 17
ALLOCATED = {
    "reqShowTheSceneAsGiven": {"drawScene", "showContent"},
    "reqMarkTheObjectTheSystemActsOn": {"drawScene", "showContent"},
    "reqShowTheVehicleSpeed": {"showContent"},
    "reqCollisionWarningWhileRequested": {"judgeCurrency", "giveWarning"},
    "reqStartEachWarningModeWithinLimit": {"judgeCurrency", "giveWarning"},
    "reqShowOutdatedElementsAsOutdated": {"judgeCurrency", "showContent"},
    "reqShowWarningUnavailableWhileRequestOutdated": {"judgeCurrency", "showContent"},
    "reqSpeedAndWarningThroughOutages": {"judgeCurrency", "showContent", "giveWarning"},
    "reqRecordDisplayIdentity": {"recordDisplayIdentity"},
}
#: REQ-HMI-009 constrains which elements draw what and the paths of their inputs, not a function: phase 8 carries it.
LEFT_TO_PHASE_8 = "reqRendererSplitAndInputPaths"

#: The states of each element and of the collision warning: state definition -> its states, in order.
STATES = {
    "ElementCurrency": ["outdated", "current"],
    "CollisionWarningStates": ["unavailable", "notAsking", "asking"],
}
#: Each transition (state definition, source, target) -> the comment that states its meaning.
TRANSITIONS = {
    ("ElementCurrency", "outdated", "current"): "a current value is shown",
    ("ElementCurrency", "current", "outdated"):
        "the value shown is no longer current, the drawing of the scene being out included",
    ("CollisionWarningStates", "unavailable", "notAsking"): "a current event that asks for none",
    ("CollisionWarningStates", "unavailable", "asking"): "a current event that asks: the start of a request",
    ("CollisionWarningStates", "notAsking", "asking"): "the start of a request",
    ("CollisionWarningStates", "asking", "notAsking"): "a current event that asks for none",
    ("CollisionWarningStates", "asking", "unavailable"): "the warning request becomes outdated",
    ("CollisionWarningStates", "notAsking", "unavailable"): "the warning request becomes outdated",
}
#: The functions whose behavior differs by state (function usage, state definition, state).
STATE_DEPENDENCIES = {
    ("showContent", "ElementCurrency", "outdated"),
    ("showContent", "ElementCurrency", "current"),
    ("showContent", "CollisionWarningStates", "unavailable"),
    ("giveWarning", "CollisionWarningStates", "unavailable"),
    ("giveWarning", "CollisionWarningStates", "notAsking"),
    ("giveWarning", "CollisionWarningStates", "asking"),
}

#: The root of the functions the context elements perform, outside the display's functional scope. Not an
#: AllocatableFunction: no context function carries a requirement of phase 5.
CONTEXT_FUNCTION_ROOT = "HmiDisplayContextFunction"

#: Each context function -> its parameters (direction, name, item type).
CONTEXT_FUNCTIONS = {
    "GiveSceneAndWarningRequest": [("out", "perceivedScene", "PerceivedScene"),
                                   ("out", "warningRequest", "WarningRequest")],
    "CarryWarningRequestToDisplay": [("in", "warningRequest", "WarningRequest"),
                                     ("out", "carriedWarningRequest", "WarningRequest")],
    "GiveVehicleSpeed": [("out", "vehicleSpeed", "VehicleSpeed")],
    "SuperviseWithTheDisplay": [("in", "shownContent", "HmiDisplayContent"),
                                ("in", "collisionWarning", "CollisionWarning")],
}

PROCESS = "HmiDisplaySystemProcess"
PROCESS_USAGE = "hmiDisplaySystemProcess"

#: The one operational context of the increment (phase 2), whose parts the process binds its participants to.
CONTEXT_USAGE = "hmiDisplayOperationalContext"

#: Each participant of the process, in order -> its phase 2 type, the phase 2 context part it is bound to by
#: reference, and the actions it owns and performs (name -> definition). The display performs its flow usage.
PARTICIPANTS = {
    "candidate": ("DriverAssistanceSystem", f"{CONTEXT_USAGE}::candidate",
                  {"giveSceneAndRequest": "GiveSceneAndWarningRequest"}),
    "scorePath": ("SCORECommandAndWarningPath", f"{CONTEXT_USAGE}::scorePath",
                  {"carryRequest": "CarryWarningRequestToDisplay"}),
    "vehicle": ("SubjectVehicle", f"{CONTEXT_USAGE}::vehicle", {"giveSpeed": "GiveVehicleSpeed"}),
    "hmiDisplay": ("HmiDisplaySystem", f"{CONTEXT_USAGE}::hmiDisplay", {}),
    "driver": ("Driver", f"{CONTEXT_USAGE}::driver", {"supervise": "SuperviseWithTheDisplay"}),
}

#: The items of the process (source, target), each end chained through the participant that owns the action.
PROCESS_FLOWS = {
    ("candidate.giveSceneAndRequest.perceivedScene", f"hmiDisplay.{FLOW_USAGE}.perceivedScene"),
    ("candidate.giveSceneAndRequest.warningRequest", "scorePath.carryRequest.warningRequest"),
    ("scorePath.carryRequest.carriedWarningRequest", f"hmiDisplay.{FLOW_USAGE}.warningRequest"),
    ("vehicle.giveSpeed.vehicleSpeed", f"hmiDisplay.{FLOW_USAGE}.vehicleSpeed"),
    (f"hmiDisplay.{FLOW_USAGE}.shownContent", "driver.supervise.shownContent"),
    (f"hmiDisplay.{FLOW_USAGE}.collisionWarning", "driver.supervise.collisionWarning"),
}

#: The functional item definitions of the boundary -> the item each specializes: the item of phase 2, or, for the
#: vehicle speed and the warning request, the item that the driver-assistance increment defines for it.
BOUNDARY_ITEM_SPECIALIZATIONS = {
    "DisplaySceneInput": "PerceivedScene",
    "DisplayVehicleSpeedInput": "VehicleSpeedInput",
    "DisplayWarningRequestInput": "CollisionWarningRequestOutput",
    "DisplayContentOutput": "HmiDisplayContent",
    "DisplayWarningOutput": "CollisionWarning",
}
#: What each boundary item adds, as ISQ quantities and scalar values (multiplicity included), no signal
#: specification. The two driver-assistance items carry their quantities already, so the display adds none.
BOUNDARY_ITEM_ATTRIBUTES = {
    "DisplaySceneInput": {"captureTime": "ISQ::DurationValue", "actedOnObjectDistance": "ISQ::LengthValue[0..1]",
                          "actedOnObjectSpeed": "ISQ::SpeedValue[0..1]"},
    "DisplayVehicleSpeedInput": {},
    "DisplayWarningRequestInput": {},
    "DisplayContentOutput": {"shownSpeed": "ISQ::SpeedValue[0..1]", "sceneOutdated": "Boolean",
                             "speedOutdated": "Boolean", "warningUnavailable": "Boolean"},
    "DisplayWarningOutput": {"onDisplay": "Boolean", "asSound": "Boolean"},
}
#: The two driver-assistance items the display reuses, and their quantities, defined once in that increment.
DRIVING_ITEMS = {
    "VehicleSpeedInput": ("VehicleSpeed", {"speed": "ISQ::SpeedValue", "sampleTime": "ISQ::DurationValue"}),
    "CollisionWarningRequestOutput": ("WarningRequest", {"requested": "Boolean", "issueTime": "ISQ::DurationValue"}),
}

#: Each port definition of the boundary -> its one directed item (direction, name, item definition).
BOUNDARY_PORTS = {
    "DisplaySceneInbound": ("in", "perceivedScene", "DisplaySceneInput"),
    "DisplaySpeedInbound": ("in", "vehicleSpeed", "DisplayVehicleSpeedInput"),
    "DisplayWarningRequestInbound": ("in", "warningRequest", "DisplayWarningRequestInput"),
    "DisplayContentOutbound": ("out", "shownContent", "DisplayContentOutput"),
    "DisplayWarningOutbound": ("out", "collisionWarning", "DisplayWarningOutput"),
}

BOUNDARY = "HmiDisplayFunctionalBoundary"

#: Each port usage of the boundary part -> its port definition.
BOUNDARY_PORT_USAGES = {
    "sceneIn": "DisplaySceneInbound",
    "speedIn": "DisplaySpeedInbound",
    "warningRequestIn": "DisplayWarningRequestInbound",
    "contentOut": "DisplayContentOutbound",
    "warningOut": "DisplayWarningOutbound",
}

#: How the boundary binds the flow's parameters to the port payloads (direction, parameter, binding), in order.
BOUNDARY_BINDINGS = [
    ("in", "perceivedScene", "sceneIn.perceivedScene"),
    ("in", "vehicleSpeed", "speedIn.vehicleSpeed"),
    ("in", "warningRequest", "warningRequestIn.warningRequest"),
    ("out", "shownContent", "contentOut.shownContent"),
    ("out", "collisionWarning", "warningOut.collisionWarning"),
]

INTERFACE_CONCERN = "hmiDisplayInterfaceConcern"

#: The phase 6 concerns, the catalogue concern definition each is typed by, and the parties that hold it.
CATALOGUE_CONCERNS = {
    CONCERN: ("FunctionalBehaviorConcern", {"SystemArchitect", "VerificationEngineer"}),
    INTERFACE_CONCERN: ("FunctionalInterfaceConcern", {"SystemsEngineer", "SoftwareDeveloper"}),
}

#: The phase 1 concerns that a phase 6 view answers ("Answered by the system process / state of phase 6").
PHASE_1_PROCESS_CONCERNS = ["hmiDisplayInputsConcern", "hmiWarningSequenceConcern", "hmiAndroidOutageConcern"]
PHASE_1_STATE_CONCERN = "hmiContentCurrencyConcern"

#: One view per SAF question beyond the breakdown and the matrix: name -> (type or "", render statement, viewpoint,
#: exposures, framed concerns), in the forms of the driver-assistance increment's phase 6.
VIEWS = {
    PROCESS_VIEW: ("ActionFlowView", "", "SystemProcessViewpoint",
                   [f"{PROCESS}::*"] + [f"{PROCESS}::{participant}::*" for participant in PARTICIPANTS],
                   PHASE_1_PROCESS_CONCERNS),
    TABLE_VIEW: ("TVD::TableView", "", "SystemStateViewpoint",
                 [f"{state_def}::{state}" for state_def, states in STATES.items() for state in states],
                 [PHASE_1_STATE_CONCERN]),
    INTERFACE_VIEW: ("", "render asTreeDiagram;", "SystemInterfaceDefinitionViewpoint", sorted(BOUNDARY_PORTS),
                     [INTERFACE_CONCERN]),
}
#: The one table, with the row population and the columns it renders: State, not Mode (D5).
TABLE_COLUMNS = [("State", "CT::declaredName"), ("DependentFunctions", "CT::documentation")]

#: Every view the package publishes: the breakdown, the matrix and one view per question above.
PUBLISHED_VIEWS = {TREE_VIEW, MATRIX_VIEW, *VIEWS}

#: Words that would name a technology, the candidate, a platform or a claim inside a function or a new element.
FORBIDDEN_IN_FUNCTIONS = ("CARLA", "ROS", "DDS", "Zenoh", "SOME/IP", "GPU", "Python", "PyTorch", "Linux",
                          "Android", "S-CORE", "SCORE", "VSS", "VisionPilot", ".cpp", "safe", "certif", "complian",
                          "homolog")
#: Buses, brokers, platforms and runtimes, matched by case so that the word "can" is no bus.
TECHNOLOGY_NAMES = ("CAN", "LIN", "FlexRay", "Ethernet", "gRPC", "KUKSA", "AUTOSAR", "AAOS", "Autoware", "ONNX",
                    "TensorRT", "CUDA", "OpenCV")
#: The technology words of the design (D6), none of them in any doc of the package or in the guide's Phase 6 prose:
#: the outage is an outage of the drawing of the scene or of the environment that hosts it.
DESIGN_TECHNOLOGY_WORDS = re.compile(
    r"(?i)\b(?:Android|IVI|SDV\s+Media|SDV\s+Core|renderers?|HAR|DriverUI|VisionPilot|S-CORE|AAOS|VSS|"
    r"heartbeats?)\b")
#: "Mode" keeps its phase 5 meaning, a form of the warning: no state definition and no column is a mode (D5).
MODE_WORD = re.compile(r"(?i)modes?")

#: The SHA-256 of the excluded word, as the requirements test of phase 5 holds it.
EXCLUDED_WORD_SHA256 = "647d177cca8601046a3cb39e12f55bec5790bfcbc42199dd5fcf063200fac1d0"

#: The texts of record of the design, pinned whole.
HEADER_PARAGRAPHS = [
    "DE4SDV HMI display functional architecture.",
    "INC-HMI-001, phase 6: the functions of the HMI display and the requirements of phase 5 each carries. Five "
    "functions record the display identity, draw the scene, judge the currency of what the display shows, show the "
    "content and give the collision warning. Every requirement but REQ-HMI-009 is allocated to a function. "
    "REQ-HMI-009 constrains which elements draw the scene, the vehicle speed and the warning, and the paths that "
    "bring them their inputs, not what a function does: phase 8 carries it by the elements that it places, and the "
    "inspection of the realization that phase 8 records verifies it. An allocation assigns responsibility only "
    "(allocatedTo); it asserts no satisfaction. No logical element, platform, transport or technology is chosen, and "
    "no safety claim is made.",
    "The drawing of the scene stands apart from the other functions: they take nothing from it but the scenes that "
    "it has drawn, and the function that gives the warning takes nothing from it at all. An outage of the drawing of "
    "the scene or of the environment that hosts it is therefore an event inside the HMI display that stops the drawn "
    "scenes and leaves the vehicle speed and the warning going: judgeCurrency finds the scene outdated by the term "
    "current, and showContent shows it as outdated until the drawing gives a current scene again.",
    "The display in operation is a process, not a second architecture: the candidate gives the scene and the "
    "warning request, the command and warning path carries the warning request to the display, the vehicle gives "
    "its speed, and the driver supervises the system with what the display shows and gets the collision warning. "
    "Those are functions of the context elements, outside the scope of the display, and HmiDisplaySystemProcess "
    "runs the display as one action between them, with the times from the start of a request to each mode of the "
    "warning. Its participants are the parts of the one operational context of phase 2, bound by reference. The "
    "functions whose behavior differs by state depend on the states of ElementCurrency and CollisionWarningStates, "
    "and the conceptual interfaces of the display are the ports of HmiDisplayFunctionalBoundary, whose items "
    "specialize the items of phase 2. No vehicle signal specification is imported or used anywhere in this package: "
    "the interface items are conceptual, their quantities are ISQ quantity values, and the signal typing of an "
    "interface starts in phase 8. The functions state what the display has to do, not what any element does at an "
    "inspected revision; phase 8 maps them to its software.",
]
#: The header sentence that leaves REQ-HMI-009 to phase 8 (D4).
REQ_009_SENTENCE = (
    "REQ-HMI-009 constrains which elements draw the scene, the vehicle speed and the warning, and the paths that "
    "bring them their inputs, not what a function does: phase 8 carries it by the elements that it places, and the "
    "inspection of the realization that phase 8 records verifies it.")

FUNCTION_DOCS = {
    "RecordDisplayIdentity":
        "Records the display identity of the HMI display before its first frame on the display in each run, so that "
        "each verdict binds the display that ran.",
    "DrawScene":
        "Draws each scene that reaches the HMI display, or a newer one, as the driver-assistance system gives it, "
        "with the object that the system acts on, when the scene has one, as an element of its own with its "
        "distance to the whole metre and the speed of the closest object to the whole km/h. It gives each scene "
        "that it draws with the time of that scene, and none while it, or the environment that hosts it, is out.",
    "JudgeCurrency":
        "Judges, by the term current, whether each element, the scene as drawn and the vehicle speed, and the "
        "warning request is current or outdated. It judges from the times of the values that reach the HMI display, "
        "from when the newest value of each input reached it, and, for the scene, from the drawn scenes, which stop "
        "while the drawing of the scene or the environment that hosts it is out. It takes nothing else from the "
        "drawing of the scene, so it goes on through each such outage.",
    "ShowContent":
        "Shows on the HMI display, within the presentation time, the drawn scene and the vehicle speed to the whole "
        "km/h. It shows each element as outdated while, and only while, it is outdated, the scene included while its "
        "drawing is out. It shows that the collision warning is unavailable while, and only while, the warning "
        "request is outdated. It takes nothing from the drawing of the scene but the drawn scenes, so it goes on "
        "through each outage of that drawing or of the environment that hosts it.",
    "GiveCollisionWarning":
        "Gives the collision warning on the HMI display and as a sound while, and only while, the warning request "
        "asks for it. Each mode starts within 0.1 s of wall-clock time after the start of a request reaches the "
        "display, and follows each change of the asking within the presentation time. It takes nothing from the "
        "drawing of the scene, so it goes on through each outage of that drawing or of the environment that hosts "
        "it.",
}

ITEM_DOCS = {
    "DisplayIdentityRecord":
        "The record of the display identity of one run, made before the first frame of the HMI display on the "
        "display in that run.",
    "DrawnScene":
        "A scene as the drawing of the scene shows it, with the time of that scene. The drawing gives one for each "
        "scene that it draws, and none while it, or the environment that hosts it, is out.",
    "ContentCurrency":
        "Whether each element, the scene as drawn and the vehicle speed, and the warning request is current or "
        "outdated by the term current, as judgeCurrency judges it.",
}

CONTEXT_ROOT_DOC = (
    "A behavior of a context element of phase 2 while the HMI display operates. It is outside the scope of the HMI "
    "display: the display does not provide it and no requirement of phase 5 is allocated to it.")
CONTEXT_DOCS = {
    "GiveSceneAndWarningRequest":
        "The candidate: gives the scene of each result pass with its time, and the warning request of each plan with "
        "its issue time, as the driver-assistance increment defines the request, both every 0.1 s of simulation "
        "time. At the inspected revision it gives no scene at its boundary (gapHmiSceneOutput).",
    "CarryWarningRequestToDisplay":
        "The command and warning path: carries the warning request to the boundary of the HMI display, with no "
        "exchange beside it.",
    "GiveVehicleSpeed":
        "The vehicle: gives its speed with each world snapshot, every step of 0.05 s of simulation time, with its "
        "sample time. Which element of System 1 brings it to the display is for the architecture phases.",
    "SuperviseWithTheDisplay":
        "The driver: supervises the driver-assistance system with what the HMI display shows, and gets the "
        "collision warning on the display and as a sound; nothing flows back to the display.",
}

FLOW_DOC = (
    "The HMI display broken into its functions, and the items they exchange. The scene and the warning request come "
    "from the candidate, the warning request over the command and warning path, and the vehicle speed from the "
    "vehicle. What the display shows and the collision warning go to the driver. Only the content of showContent "
    "leaves as what the display shows, and only the warning of giveWarning as the collision warning. The display "
    "identity is recorded before the display gives its first frame.")

PARTICIPANT_DOCS = {
    "candidate": "The candidate of phase 2: gives the scene with its time and the warning request with its issue "
                 "time, every 0.1 s of simulation time. At the inspected revision it gives no scene at its boundary "
                 "(gapHmiSceneOutput).",
    "scorePath": "The command and warning path of phase 2: carries the warning request to the HMI display, with no "
                 "exchange beside it. Of the 0.2 s of wall-clock time that the driver-assistance increment allots "
                 "from the warning request at the boundary of the candidate to each mode of the warning, 0.1 s lies "
                 "before the boundary of the display, on this path, and the architecture phases of both increments "
                 "place it.",
    "vehicle": "The vehicle of phase 2: gives its speed with each world snapshot, every step of 0.05 s of simulation "
               "time.",
    "hmiDisplay": "The system of interest of phase 2: it performs its whole functional flow, the one usage its "
                  "functional boundary performs, and starts each mode of the warning within 0.1 s of wall-clock time "
                  "after the start of a request reaches it; phase 8 divides that 0.1 s among its elements. An outage "
                  "of the drawing of the scene or of the environment that hosts it is an event inside the display: "
                  "the drawn scenes stop, judgeCurrency finds the scene outdated by the term current, and "
                  "showContent shows it as outdated within the limits of that term and the presentation time from "
                  "the last scene drawn. Through the outage the display goes on showing the vehicle speed, giving "
                  "the warning while the request asks for it, and showing the warning as unavailable while the "
                  "request is outdated.",
    "driver": "The driver of phase 2: supervises the system with what the HMI display shows and gets the collision "
              "warning; nothing flows back to the display.",
}

#: The process view hides doc rows (the convention form), so the view index notes where its times are.
PROCESS_VIEW_NOTE = (
    "SysIDE draws the lanes of the process and the flows between them but prints no doc in this form: the times of "
    "the warning sequence and the sequence of an outage are in the docs of `HmiDisplaySystemProcess` and of its "
    "lanes.")
#: What the lane docs, the only docs that a doc-row form of the process view prints, carry of the times and of
#: the outage: participant -> phrases of its doc.
LANE_FACTS = {
    "candidate": ("every 0.1 s of simulation time", "gives no scene at its boundary (gapHmiSceneOutput)"),
    "scorePath": ("Of the 0.2 s of wall-clock time", "0.1 s lies before the boundary of the display, on this "
                  "path"),
    "vehicle": ("every step of 0.05 s",),
    "hmiDisplay": ("within 0.1 s of wall-clock time", "An outage of the drawing of the scene",
                   "Through the outage the display goes on showing the vehicle speed"),
}

PROCESS_PARAGRAPHS = [
    "One run of the HMI display in operation, as a process. The participants are the context parts of phase 2 "
    "themselves and the system of interest, bound by reference: the process declares no part of its own, so the "
    "increment has one context. Each participant owns and performs its functions, as the swim lane of its functions: "
    "the candidate gives the scene and the warning request, the command and warning path carries the warning request "
    "to the display, and the vehicle gives its speed. The display records its identity, draws the scene, judges the "
    "currency of what it shows, shows the content and gives the warning, as one action of the process. The driver "
    "supervises the system with what the display shows and gets the collision warning. The functions of the context "
    "elements are outside the scope of the HMI display; its functional scope is the one functional flow usage it "
    "performs. The items that cross its boundary are the flows of the process, each chained through the participant "
    "that gives and the one that takes, and nothing flows back from the driver.",
    "The sequence and its times: the candidate gives the scene and the warning request every 0.1 s of simulation "
    "time, and the vehicle gives its speed with each world snapshot, every step of 0.05 s. The driver-assistance "
    "increment allots 0.2 s of wall-clock time from the warning request at the boundary of the candidate to each "
    "mode of the warning. The display starts each mode within 0.1 s of wall-clock time after the start of a request "
    "reaches it, and the other 0.1 s lies before its boundary, on the path, which the architecture phases of both "
    "increments place. Phase 8 divides the 0.1 s of the display among its elements. An outage of the drawing of the "
    "scene or of the environment that hosts it is an event inside the display: the drawn scenes stop, and the scene "
    "shows as outdated within the limits of the term current and the presentation time from the last scene drawn, "
    "while the vehicle speed and the warning go on. Once the drawing gives a current scene again, the scene shows as "
    "current. No transport, display or sound technology is fixed here.",
]

STATE_DEF_DOCS = {
    "ElementCurrency":
        "The state of each element of the HMI display, the scene as drawn and the vehicle speed, by the term current. "
        "Each element is in one of them on its own, and is outdated from the start of each run until its first "
        "current value.",
    "CollisionWarningStates":
        "The state of the collision warning at the HMI display, by the warning request. It is unavailable from the "
        "start of each run until the first current event of the request.",
}
STATE_DOCS = {
    "outdated":
        "The element shows no current value: its value came late or never, no value of its input has reached the "
        "display yet, or, for the scene, the drawing of the scene or the environment that hosts it is out and the "
        "scene shown is no longer current. showContent shows the element as outdated (REQ-HMI-006).",
    "current":
        "The element shows a current value: showContent shows the scene as drawn and the vehicle speed to the whole "
        "km/h (REQ-HMI-001, REQ-HMI-003).",
    "unavailable":
        "The warning request is outdated: giveWarning gives no collision warning, and showContent shows that the "
        "warning is unavailable (REQ-HMI-007), through each outage of the drawing of the scene as well (REQ-HMI-008).",
    "notAsking": "The warning request is current and asks for no collision warning: giveWarning gives none.",
    "asking":
        "The warning request asks: giveWarning gives the collision warning on the display and as a sound, each mode "
        "starting within 0.1 s of wall-clock time after the start of a request reaches the display (REQ-HMI-004, "
        "REQ-HMI-005), through each outage of the drawing of the scene as well (REQ-HMI-008).",
}

BOUNDARY_ITEM_DOCS = {
    "DisplaySceneInput":
        "The scene as it reaches the HMI display at its input, with its time, the capture time in simulation time of "
        "the camera image of its result pass. When the scene has an object that the system acts on, it also carries "
        "that object's distance and the speed of the closest object that the fusion gives. The rest of the scene "
        "travels with it.",
    "DisplayVehicleSpeedInput":
        "The vehicle speed as it reaches the HMI display: the speed of each world snapshot, the same speed that the "
        "driver-assistance system takes at its input, with its sample time in simulation time.",
    "DisplayWarningRequestInput":
        "The warning request as it reaches the HMI display: the request that the driver-assistance system gives at "
        "its boundary, whether it asks for the collision warning, with its issue time in simulation time.",
    "DisplayContentOutput":
        "What the HMI display shows: the drawn scene, the vehicle speed to the whole km/h, whether each element is "
        "shown as outdated, and whether the collision warning is shown as unavailable. How each looks is for phase 8.",
    "DisplayWarningOutput":
        "The collision warning as the HMI display gives it, in its two modes: on the display and as a sound.",
}
PORT_DOCS = {
    "DisplaySceneInbound": "The input port of the scene: the candidate gives it.",
    "DisplaySpeedInbound": "The input port of the vehicle speed: the vehicle gives it.",
    "DisplayWarningRequestInbound":
        "The input port of the warning request: the command and warning path brings it from the candidate.",
    "DisplayContentOutbound": "The output port of what the display shows: the driver sees it.",
    "DisplayWarningOutbound":
        "The output port of the collision warning, on the display and as a sound: the driver gets it.",
}
BOUNDARY_DOC = (
    "The HMI display at its functional boundary, the one place its conceptual interfaces are stated: three input "
    "ports and two output ports, each with one directed item typed by an item definition of this package that "
    "specializes the item of phase 2, or the item that the driver-assistance increment defines for it. It performs "
    "the functional flow and binds its inputs and outputs to the ports. It is not a logical element: neither it nor "
    "its ports names a computer, a process, a transport or a technology.")
CONCERN_DOCS = {
    CONCERN:
        "System architects and verification engineers need the functions of the HMI display and each requirement of "
        "phase 5 mapped to the functions that carry it: phase 7 gives the functions to logical elements, and phase "
        "10 verifies each requirement on its functions.",
    INTERFACE_CONCERN:
        "Systems engineers and software developers need the conceptual interfaces of the HMI display before phase 7 "
        "allocates the functions and phase 8 places software on them: the port of the functional chain for each item "
        "that crosses its boundary, and the direction of that item. Signal typing at a software contract belongs to "
        "phase 8.",
}

#: The guide: its Status line and the next obligation, as phase 8 moved them.
GUIDE_STATUS = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification, "
    "Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture, Phase 7 logical "
    "architecture, Phase 8 physical and software realization and Phase 9 variability and configuration, "
    "proposal.**")
GUIDE_STATUS_PHASE_5 = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification, "
    "Phase 4 stakeholder needs and Phase 5 requirements, proposal.**")
GUIDE_NEXT = (
    "The next model obligation is **Phase 10**: the verification cases, one or more for each requirement of the "
    "increment; its first gate is `verificationCaseVerifiesRequirement`.")
GUIDE_HEADING = "## Functional architecture (Phase 6)"
GUIDE_LINK = "../../textual-notation-of-model/packages/features/hmi/hmi_display_functional_architecture.sysml"
GUIDE_FRAME_LINE = (f"- [SysML functional architecture]({GUIDE_LINK}): the Phase 6 functional architecture of the HMI "
                    "display.")
#: The guide's bullet of each function, after its name, pinned whole, in order.
GUIDE_FUNCTION_BULLETS = {
    "recordDisplayIdentity": "records the display identity before the first frame on the display in each run;",
    "drawScene":
        "draws each scene that reaches the display, with the object that the system acts on as an element of its "
        "own, and gives each scene that it draws with the time of that scene;",
    "judgeCurrency":
        "judges, by the term current, whether each element and the warning request are current or outdated;",
    "showContent":
        "shows the drawn scene and the vehicle speed, each element as outdated while, and only while, it is "
        "outdated, and that the collision warning is unavailable while, and only while, the warning request is "
        "outdated;",
    "giveWarning":
        "gives the collision warning on the display and as a sound while, and only while, the warning request "
        "asks for it.",
}
#: The guide's sentence of the outage: no separate function detects it, judgeCurrency finds it (R9).
GUIDE_OUTAGE_SENTENCE = (
    "The drawn scenes are the exchange that carries the outage inside the display, so no separate function "
    "detects it: `judgeCurrency` finds it from the drawn scenes.")
#: The guide's four decisions, title -> text, pinned whole, in order.
GUIDE_DECISIONS = {
    "The drawing of the scene stands apart.":
        "`judgeCurrency` and `showContent` take nothing from `drawScene` but the drawn scenes, and `giveWarning` "
        "takes nothing from it at all. An outage of the drawing of the scene or of the environment that hosts it is "
        "an event inside the display: the drawn scenes stop, `judgeCurrency` finds the scene outdated by the term "
        "current, and `showContent` shows it as outdated until the drawing gives a current scene again, while the "
        "vehicle speed and the warning go on. " + GUIDE_OUTAGE_SENTENCE + " Phase 8 maps that exchange to the "
        "realization.",
    "The share of the display in the time.":
        "Each mode of the warning starts within 0.1 s of wall-clock time after the start of a request reaches the "
        "display (`REQ-HMI-005`). The driver-assistance increment allots 0.2 s of wall-clock time from the warning "
        "request at the boundary of the candidate to each mode, and the other 0.1 s lies before the boundary of the "
        "display, on the path, which the architecture phases of both increments place. Phase 8 divides the 0.1 s "
        "of the display among its elements.",
    "States, not modes.":
        "Phase 5 calls a form of the warning, on the display or as a sound, a mode, so the conditions of the "
        "display are states: `ElementCurrency`, outdated or current for each element on its own, and "
        "`CollisionWarningStates`, unavailable, not asking or asking. `showContent` and `giveWarning` depend on the "
        "states in which their behavior differs.",
    "`REQ-HMI-009` is left to Phase 8.":
        "It constrains which elements draw the scene, the vehicle speed and the warning, and the paths that bring "
        "them their inputs, not what a function does. Phase 8 carries it by the elements that it places, and the "
        "inspection of the realization that Phase 8 records verifies it.",
}
#: The guide's paragraph of the allocations: their count and the functions of REQ-HMI-004 and REQ-HMI-005.
GUIDE_ALLOCATION_PARAGRAPH = (
    "Each of the other nine requirements is allocated (`allocatedTo`) to the functions that carry it, seventeen "
    "allocations in all, and each function carries at least one. `REQ-HMI-004` and the performance requirement "
    "`REQ-HMI-005` go to `judgeCurrency` and `giveWarning`, since the asking and its start depend on the currency "
    "judgement. An allocation assigns responsibility only; it claims no satisfaction.")
#: The guide's paragraph of the process: the period of the candidate and the step of the vehicle.
GUIDE_PROCESS_PARAGRAPH = (
    "The display in operation is the process `HmiDisplaySystemProcess`. Its participants are the parts of the "
    "operational context of Phase 2, each the swim lane of its functions: the candidate gives the scene and the "
    "warning request every 0.1 s of simulation time, the command and warning path carries the warning request to "
    "the display, the vehicle gives its speed with each world snapshot, every step of 0.05 s, and the driver "
    "supervises the system with what the display shows and gets the collision warning. The display performs its "
    "functional flow as one action. The context of Phase 2 holds no other presentation of the warning beside the "
    "display; whether a build of this display replaces the presentation of the warning in the driver-assistance "
    "increment stays open.")
#: The guide's opening paragraph of the section.
GUIDE_OPENING_PARAGRAPH = (
    "The [functional "
    "architecture](../../textual-notation-of-model/packages/features/hmi/hmi_display_functional_architecture.sysml) "
    "breaks the HMI display down into five functions:")
#: The guide's paragraph of the flow, after the function bullets.
GUIDE_FLOW_PARAGRAPH = (
    "They are `AllocatableFunction` actions of the functional flow `HmiDisplayFunctionalFlow`. The flow takes the "
    "scene, the vehicle speed and the warning request in, and gives what the display shows and the collision warning "
    "out. Inside, the functions exchange the drawn scenes and the currency of the content, and the display identity is "
    "recorded before the display gives its first frame. The functions state what the display has to do, not what any "
    "element does at an inspected revision; Phase 8 maps them to its software.")
#: The line that introduces the four decisions.
GUIDE_DECISIONS_INTRO = (
    "Four decisions shape the functional architecture:")
#: The guide's paragraph of the conceptual interfaces: the five ports and their items.
GUIDE_INTERFACE_PARAGRAPH = (
    "The conceptual interfaces are the five ports of `HmiDisplayFunctionalBoundary`, the display at its boundary: the "
    "scene, the vehicle speed and the warning request in, each with its time, and what the display shows and the "
    "collision warning out. The items of the vehicle speed and of the warning request specialize the items that the "
    "driver-assistance increment defines at its own boundary and add nothing to them, so each quantity is defined "
    "once. The items carry ISQ quantities; no vehicle signal specification is used, and the signal typing starts at "
    "Phase 8.")
#: The line that introduces the five views.
GUIDE_VIEWS_INTRO = (
    "Five views publish the architecture, one per SAF question:")
#: The guide's closing paragraph: what the test pins and what review judges.
GUIDE_CLOSING_PARAGRAPH = (
    "`tests/test_hmi_display_functional_architecture.py` pins the functions, their flows and allocations, the process "
    "with its times, the states, the interfaces, the five views and this section. The Phase 6 gates check that a "
    "function exists and that each functional requirement is allocated to one; review judges whether they are the "
    "right ones.")
#: The guide's five view bullets, whole and in order; the process view's says where its times are.
GUIDE_VIEW_BULLETS = [
    ("the breakdown `hmiDisplayFunctionBreakdownView`, which lists the items and the five functions of the flow but "
     "draws no item flows, and frames `hmiDisplayFunctionsConcern`;"),
    ("the matrix `hmiDisplayRequirementFunctionMatrixView`, with the ten requirements in rows, `REQ-HMI-009` an empty "
     "one, and the functions in columns, which frames `hmiDisplayFunctionsConcern` as well;"),
    ("the process `hmiDisplaySystemProcessView`, with its participants as swim lanes and the items that cross the "
     "boundary, which answers the Phase 1 concerns `hmiDisplayInputsConcern`, `hmiWarningSequenceConcern` and "
     "`hmiAndroidOutageConcern`; it prints no doc, so the times of the warning sequence and the sequence of an outage "
     "are in the docs of the process and of its lanes;"),
    ("the table `hmiDisplayStateTableView` of the states and what the functions that depend on them do in each, which "
     "answers the Phase 1 concern `hmiContentCurrencyConcern`;"),
    ("the tree `hmiDisplayFunctionalInterfaceView` of the five port definitions, each with its directed item, which "
     "frames `hmiDisplayInterfaceConcern`."),
]
#: The two grids of the phase: key -> (title, description, row axis, column axis), pinned whole.
GRIDS = {
    f"matrix-{MATRIX_VIEW}": (
        "HMI display requirement-function mapping",
        "Maps the requirements of the HMI display to the system functions that carry them.",
        "requirements (requirement usages)", "system functions (action usages)"),
    f"table-{TABLE_VIEW}": (
        "HMI display states",
        "The states of each element of the HMI display and of the collision warning, and the functions whose "
        "behavior differs in each.",
        "states (state usages)", ""),
}
#: What the guide's Phase 6 section states of each decision of the design, word for word.
GUIDE_PHRASES = (
    "`judgeCurrency` and `showContent` take nothing from `drawScene` but the drawn scenes, and `giveWarning` takes "
    "nothing from it at all.",
    "An outage of the drawing of the scene or of the environment that hosts it is an event inside the display",
    "Each mode of the warning starts within 0.1 s of wall-clock time after the start of a request reaches the "
    "display (`REQ-HMI-005`).",
    "the other 0.1 s lies before the boundary of the display, on the path, which the architecture phases of both "
    "increments place.",
    "Phase 8 divides the 0.1 s of the display among its elements.",
    "Phase 5 calls a form of the warning, on the display or as a sound, a mode, so the conditions of the display "
    "are states:",
    "It constrains which elements draw the scene, the vehicle speed and the warning, and the paths that bring them "
    "their inputs, not what a function does.",
    "The context of Phase 2 holds no other presentation of the warning beside the display",
)


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(text.replace("*", " ").split())


def _doc(declaration: str) -> str:
    """The doc text of the element whose body follows ``declaration`` in the raw model."""
    body = braced_body(_raw(), declaration)
    match = re.match(r"\s*doc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{declaration}: the doc must open the body"
    return _flat(match.group(1))


def _header_paragraphs() -> list[str]:
    head = _raw().split(f"package {PACKAGE}", 1)[0]
    assert head.startswith("/*") and head.rstrip().endswith("*/")
    lines = [re.sub(r"^\s*\*?\s?", "", line) for line in head.strip()[2:-2].splitlines()]
    return [" ".join(part.split()) for part in "\n".join(lines).split("\n\n") if part.strip()]


def _header() -> str:
    return " ".join(_header_paragraphs())


def _flow_body() -> str:
    return braced_body(_code(), f"action def {FLOW}")


def _process_body() -> str:
    return braced_body(_code(), f"action def {PROCESS}")


def _process_paragraphs() -> list[str]:
    """The paragraphs of the doc of the process, read from the raw model."""
    raw = braced_body(_raw(), f"action def {PROCESS}")
    match = re.match(r"\s*doc\s*/\*(.*?)\*/", raw, re.S)
    assert match, "the doc must open the body of the process"
    return [" ".join(re.sub(r"(?m)^\s*\*\s?", "", part).split())
            for part in re.split(r"\n\s*\*\s*\n", match.group(1)) if part.strip()]


def _process_flows() -> set[tuple[str, str]]:
    """The flows of the process (source, target), read from the model."""
    return set(re.findall(r"\bflow\s+from\s+([\w.]+)\s+to\s+([\w.]+)\s*;", _process_body()))


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


def _allocations() -> dict[str, set[str]]:
    code = _code()
    rows = re.findall(rf"\ballocation\s+(\w+)\s+allocate\s+(\w+)\s+to\s+{FLOW}::(\w+)\s*;", code)
    assert len(rows) == len(re.findall(r"\ballocate\b", code)), "every allocation has the one untyped form"
    assert len({name for name, _, _ in rows}) == len(rows), "allocation names are unique"
    allocated: dict[str, set[str]] = {}
    for _, requirement, function in rows:
        allocated.setdefault(requirement, set()).add(function)
    return allocated


def _requirements() -> list[tuple[str, str]]:
    """(name, definition) of each requirement of phase 5, in declaration order."""
    code = strip_comments(NEEDS_REQUIREMENTS.read_text(encoding="utf-8"))
    return re.findall(r"\brequirement\s+<'REQ-HMI-\d{3}'>\s+(\w+)\s*:\s*(\w+)\s*\{", code)


def _docs() -> list[str]:
    """Every comment and doc text of the package, flattened."""
    return [_flat(text) for text in re.findall(r"/\*(.*?)\*/", _raw(), re.S)] + \
        [_flat(text) for text in re.findall(r"//([^\n]*)", _raw())]


def _number_word(number: int) -> str:
    return {14: "fourteen", 15: "fifteen", 16: "sixteen", 17: "seventeen", 18: "eighteen"}[number]


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _guide_section(guide: str) -> str:
    return guide.split(GUIDE_HEADING + "\n", 1)[1].split("\n## ", 1)[0]


def _attributes(body: str) -> dict[str, str]:
    declared = dict(re.findall(r"\battribute\s+(\w+)\s*:\s*([\w:]+(?:\[[^\]]*\])?)\s*;", body))
    assert len(re.findall(r"\battribute\b", body)) == len(declared)
    return declared


def test_the_charter_names_the_package_after_the_needs_and_requirements():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part hmiDisplayCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    assert names.index(PACKAGE) == names.index("DE4SDV_HmiDisplayNeedsRequirements") + 1
    assert names.count(PACKAGE) == 1
    assert re.search(rf"(?m)^package\s+{PACKAGE}\s*\{{", _code())
    assert len(re.findall(r"(?m)^package\s+\w+", _code())) == 1


def test_the_five_functions_are_allocatable_functions_and_nothing_else_is():
    code = _code()
    functions = re.findall(r"\baction\s+def\s+(\w+)\s*:>\s*([^{;]+?)\s*\{", code)
    assert {name: typed for name, typed in functions if typed == "AllocatableFunction"} == {
        name: "AllocatableFunction" for name in FUNCTIONS.values()}
    assert {name: typed for name, typed in functions if typed != "AllocatableFunction"} == {
        name: CONTEXT_FUNCTION_ROOT for name in CONTEXT_FUNCTIONS}
    assert code.count("private import DE4SDV_TraceVocabulary::AllocatableFunction;") == 1
    assert not re.search(r"\bdef\s+AllocatableFunction\b", code), "no local homonym of the kernel name"
    assert re.search(rf"\baction\s+def\s+{FLOW}\s*\{{", code), "the flow is a composite, not a function"
    assert set(re.findall(r"\bitem\s+def\s+(\w+)", code)) == INTERNAL_ITEMS | set(BOUNDARY_ITEM_SPECIALIZATIONS)
    for item in ("PerceivedScene", "HmiDisplayContent"):
        assert f"private import DE4SDV_HmiDisplayOperationalContext::{item};" in code, item
    for item in ("VehicleSpeed", "WarningRequest", "CollisionWarning"):
        assert f"private import DE4SDV_DriverAssistanceOperationalContext::{item};" in code, item
    assert re.search(rf"\baction\s+{FLOW_USAGE}\s*:\s*{FLOW}\s*;", code)
    for name, parameters in FUNCTION_PARAMETERS.items():
        body = _direct(braced_body(code, f"action def {name} :> AllocatableFunction"))
        assert re.findall(r"\b(in|out)\s+(\w+)\s*:\s*(\w+)\s*;", body) == parameters, name


def test_the_flow_breaks_the_display_into_the_five_functions():
    direct = _direct(_flow_body())
    assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", direct) == FLOW_PARAMETERS
    assert list(re.findall(r"\baction\s+(\w+)\s*:\s*(\w+)\s*\{", direct)) == list(FUNCTIONS.items()), \
        "the breakdown keeps the order of the functions"


def test_the_functions_exchange_exactly_these_items_in_this_order():
    body = _flow_body()
    assert set(re.findall(r"\bflow\s+from\s+([\w.]+)\s+to\s+([\w.]+)\s*;", body)) == FLOWS
    assert len(re.findall(r"\bflow\s+from\b", body)) == len(FLOWS)
    assert re.findall(r"\bfirst\s+(\w+)\s+then\s+(\w+)\s*;", body) == SUCCESSIONS
    bound = set()
    for function, definition in FUNCTIONS.items():
        usage = braced_body(body, f"action {function} : {definition}")
        for direction, parameter, outer in re.findall(rf"\b(in|out)\s+(\w+)\s*=\s*{FLOW}::(\w+)\s*;", usage):
            bound.add((function, direction, parameter, outer))
    assert bound == BINDINGS
    assert FLOW_DOC == _doc(f"action def {FLOW}")


def test_the_drawing_of_the_scene_stands_apart():
    """D3: the drawn scenes are the one exchange with the drawing. judgeCurrency and showContent take nothing else
    from drawScene, giveWarning takes nothing from it, and no separate function detects an outage."""
    body = _flow_body()
    assert len(re.findall(r"\bdrawScene\b", body)) == 4, \
        "drawScene appears only as its usage, its succession and its two flows"
    assert not re.search(r"\b(?:message|bind|connect|connection|interface)\b", body), \
        "the functions exchange nothing but plain flows"
    flows = re.findall(r"\bflow\s+from\s+([\w.]+)\s+to\s+([\w.]+)\s*;", body)
    from_drawing = [(source, target) for source, target in flows if source.startswith("drawScene.")]
    assert from_drawing and all(source == "drawScene.drawnScene" for source, _ in from_drawing)
    assert {target.split(".")[0] for _, target in from_drawing} == {"judgeCurrency", "showContent"}
    assert not [flow for flow in flows if flow[1].startswith("giveWarning.") and "drawScene" in flow[0]], \
        "no flow from drawScene to giveWarning"
    assert not [flow for flow in flows if flow[1].startswith("drawScene.")], "nothing flows into the drawing"
    code = _code()
    assert "DrawnScene" not in braced_body(code, "action def GiveCollisionWarning"), "giveWarning takes no drawn scene"
    assert "drawnScene" not in braced_body(body, "action giveWarning : GiveCollisionWarning")
    assert set(re.findall(r"\bdef\s+(\w+)\s*:>\s*AllocatableFunction", code)) == set(FUNCTIONS.values()), \
        "no detection function of its own"
    header = _header()
    assert ("The drawing of the scene stands apart from the other functions: they take nothing from it but the "
            "scenes that it has drawn, and the function that gives the warning takes nothing from it at all.") in header
    for function, phrase in (("JudgeCurrency", "It takes nothing else from the drawing of the scene, so it goes on "
                                               "through each such outage."),
                             ("ShowContent", "It takes nothing from the drawing of the scene but the drawn scenes, so "
                                             "it goes on through each outage of that drawing or of the environment "
                                             "that hosts it."),
                             ("GiveCollisionWarning", "It takes nothing from the drawing of the scene, so it goes on "
                                                      "through each outage of that drawing or of the environment that "
                                                      "hosts it.")):
        assert phrase in _doc(f"action def {function} :> AllocatableFunction"), function


def test_no_function_waits_on_the_drawing_of_the_scene():
    """Every exchange of the flow is a plain flow, which can start when its payload is there; a succession flow
    from drawScene would make a function wait for the drawing to end. The only successions record the display
    identity first."""
    body = _flow_body()
    plain = re.findall(r"(?m)^\s*flow\s+from\s+([\w.]+)\s+to\s+([\w.]+)\s*;\s*$", body)
    assert set(plain) == FLOWS and len(plain) == len(FLOWS)
    assert len(re.findall(r"\bflow\b", body)) == len(FLOWS), "every flow is a plain `flow from <a>.<x> to <b>.<y>;`"
    assert not re.search(r"\bsuccession\b", body), "no succession, and no succession flow"
    assert re.findall(r"(?m)^\s*first\s+(\w+)\s+then\s+(\w+)\s*;\s*$", body) == SUCCESSIONS
    assert len(re.findall(r"\bthen\b", body)) == len(SUCCESSIONS) == 3
    assert all(source == "recordDisplayIdentity" for source, _ in SUCCESSIONS)


@pytest.mark.parametrize("definition", sorted(FUNCTION_DOCS))
def test_each_function_states_its_text_of_record(definition):
    doc = _doc(f"action def {definition} :> AllocatableFunction")
    assert doc == FUNCTION_DOCS[definition]
    assert not re.search(r"\bREQ-", doc), "a function doc names no requirement"


def test_the_content_and_the_warning_follow_their_input_while_and_only_while():
    assert ("It shows each element as outdated while, and only while, it is outdated" in
            _doc("action def ShowContent :> AllocatableFunction"))
    assert ("It shows that the collision warning is unavailable while, and only while, the warning request is "
            "outdated." in _doc("action def ShowContent :> AllocatableFunction"))
    assert ("Gives the collision warning on the HMI display and as a sound while, and only while, the warning "
            "request asks for it." in _doc("action def GiveCollisionWarning :> AllocatableFunction"))


def test_one_function_gives_each_output():
    code = _code()
    functions = dict(re.findall(r"\baction\s+def\s+(\w+)\s*:>\s*AllocatableFunction\s*\{([^}]*)\}", code))
    for item, giver in (("HmiDisplayContent", "ShowContent"), ("CollisionWarning", "GiveCollisionWarning"),
                        ("DrawnScene", "DrawScene"), ("ContentCurrency", "JudgeCurrency"),
                        ("DisplayIdentityRecord", "RecordDisplayIdentity")):
        givers = {name for name, body in functions.items() if re.search(rf"\bout\s+\w+\s*:\s*{item}\b", body)}
        assert givers == {giver}, item
    flow = _flow_body()
    for outer, function in (("shownContent", "showContent"), ("collisionWarning", "giveWarning")):
        sources = re.findall(rf"\baction\s+(\w+)\s*:\s*\w+\s*\{{[^}}]*\bout\s+\w+\s*=\s*{FLOW}::{outer}\s*;", flow)
        assert sources == [function], outer


def test_the_display_identity_is_recorded_before_the_first_frame():
    successions = re.findall(r"\bfirst\s+(\w+)\s+then\s+(\w+)\s*;", _flow_body())
    assert {source for source, _ in successions} == {"recordDisplayIdentity"}
    assert {target for _, target in successions} == {"drawScene", "showContent", "giveWarning"}, \
        "each function that gives a frame or the warning comes after the record"
    assert "The display identity is recorded before the display gives its first frame." in _doc(f"action def {FLOW}")
    assert _doc("item def DisplayIdentityRecord") == ITEM_DOCS["DisplayIdentityRecord"]


def test_the_states_follow_from_the_requirements():
    code = _code()
    assert re.findall(r"\bstate\s+def\s+(\w+)", code) == list(STATES)
    raw = _raw()
    for state_def, states in STATES.items():
        machine = braced_body(code, f"state def {state_def}")
        assert re.findall(r"\bstate\s+(\w+)\s*[;{]", machine) == states, state_def
        pairs = re.findall(r"\btransition\s+first\s+(\w+)\s+then\s+(\w+)\s*;", machine)
        expected = [(source, target) for (owner, source, target) in TRANSITIONS if owner == state_def]
        assert sorted(pairs) == sorted(expected), state_def
        assert len(re.findall(r"\btransition\b", machine)) == len(expected)
        raw_machine = braced_body(raw, f"state def {state_def}")
        for (owner, source, target), why in TRANSITIONS.items():
            if owner == state_def:
                assert re.search(rf"\btransition\s+first\s+{source}\s+then\s+{target};\s*//\s*{re.escape(why)}\n",
                                 raw_machine), (source, target)
        assert _doc(f"state def {state_def}") == STATE_DEF_DOCS[state_def]
        for state in states:
            assert _doc(f"state {state}") == STATE_DOCS[state], state


def test_no_state_is_a_mode():
    """D5: phase 5 defines a mode as one of the two forms of the warning; the conditions of the display are states."""
    code = _code()
    for name in re.findall(r"\bstate\s+(?:def\s+)?(\w+)", code):
        assert not MODE_WORD.search(name), name
    table = braced_body(code, f"view {TABLE_VIEW} : TVD::TableView")
    columns = re.findall(r"\bview\s+(\w+)\s*:>\s*columnViews", table)
    assert columns == [column for column, _ in TABLE_COLUMNS]
    assert not [column for column in columns if MODE_WORD.search(column)]
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"table-{TABLE_VIEW}"]
    for text in (metadata.title, metadata.description, metadata.row_label, metadata.column_label):
        assert not MODE_WORD.search(text or ""), text
    terms = _flat(NEEDS_REQUIREMENTS.read_text(encoding="utf-8"))
    assert "Mode: one of the two forms of the collision warning" in terms


def test_each_requirement_is_allocated_to_the_functions_decided():
    assert _allocations() == ALLOCATED
    assert sum(len(functions) for functions in _allocations().values()) == ALLOCATION_COUNT


def test_every_functional_requirement_is_allocated_and_every_function_carries_one():
    requirements = _requirements()
    assert len(requirements) == 10
    allocated = _allocations()
    functional = [name for name, kind in requirements if kind == "FunctionalRequirementCandidate"]
    assert len(functional) == 8 and all(name in allocated for name in functional)
    assert {name for name, _ in requirements} - set(allocated) == {LEFT_TO_PHASE_8}
    assert set(allocated) <= {name for name, _ in requirements}
    assert set().union(*allocated.values()) == set(FUNCTIONS)
    assert allocated["reqStartEachWarningModeWithinLimit"] == {"judgeCurrency", "giveWarning"}, \
        "the performance limit binds the currency judgement and giveWarning"
    assert allocated["reqCollisionWarningWhileRequested"] == {"judgeCurrency", "giveWarning"}, \
        "the asking depends on the currency judgement"


def test_req_hmi_009_is_left_to_the_realization_of_phase_8():
    """D4: REQ-HMI-009 constrains which elements draw what and the paths of their inputs; its criteria inspect the
    realization that phase 8 records, and phase 8 owes the dependency from the elements it places."""
    assert REQ_009_SENTENCE in _header()
    assert LEFT_TO_PHASE_8 not in _allocations()
    code = _code()
    assert not re.search(rf"\b(?:allocate|dependency)\b[^;]*\b{LEFT_TO_PHASE_8}\b", code), \
        "phase 6 carries REQ-HMI-009 neither by an allocation nor by a dependency"
    assert "Met when the inspection of the realization that phase 8 records" in _flat(
        NEEDS_REQUIREMENTS.read_text(encoding="utf-8"))


def test_the_breakdown_view_shows_the_flow_with_its_five_functions():
    view = braced_body(_code(), f"view {TREE_VIEW}")
    viewpoint = braced_body(view, "viewpoint")
    assert re.search(r"viewpoint\s+\w+\s*:\s*SystemFunctionalBreakdownStructureViewpoint\s*\{", view)
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == [CONCERN]
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", view) == [FLOW_USAGE]
    assert "render asTreeDiagram;" in view
    from scripts.generate_view_index import KNOWN_PRESENTATION_NOTES

    note = KNOWN_PRESENTATION_NOTES[TREE_VIEW]
    assert f"SysIDE lists the items and the five functions of `{FLOW_USAGE}` but does not draw the flows" in note
    assert f"`{FLOW}`" in note and f"`{MATRIX_VIEW}`" in note


def test_the_matrix_maps_every_requirement_to_its_functions():
    view = braced_body(_code(), f"view {MATRIX_VIEW} : MVD::MatrixView")
    viewpoint = braced_body(view, "viewpoint")
    assert re.search(r"viewpoint\s+\w+\s*:\s*SystemRequirementTraceabilityViewpoint\s*\{", view)
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == [CONCERN]
    rows = braced_body(view, "view :>> rowView")
    columns = braced_body(view, "view :>> columnView")
    cells = braced_body(view, "view :>> cellView")
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", rows) == [name for name, _ in _requirements()], \
        "all ten requirements, REQ-HMI-009 an empty row"
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", columns) == [f"{FLOW_USAGE}::{f}" for f in FUNCTIONS]
    for axis in (rows, columns):
        assert "attribute :>> includeReferenceElements = true;" in axis
        assert "attribute :>> representation = Rep::name;" in axis
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", cells) == [f"{PACKAGE}::*"]
    assert "MatrixTraceabilityDirection::row2col" in cells


def test_the_boundary_items_carry_isq_quantities_and_no_signal_specification():
    code = _code()
    assert "private import ISQ::*;" not in code and "COVESA_VSS" not in code
    for item, attributes in BOUNDARY_ITEM_ATTRIBUTES.items():
        body = braced_body(code, f"item def {item} :> {BOUNDARY_ITEM_SPECIALIZATIONS[item]}")
        assert _attributes(body) == attributes, item
        assert not re.search(r"\b(?:item|part|ref)\b", _direct(body)), item
    assert "private import ScalarValues::Boolean;" in code
    for item, doc in BOUNDARY_ITEM_DOCS.items():
        assert _doc(f"item def {item} :> {BOUNDARY_ITEM_SPECIALIZATIONS[item]}") == doc, item


def test_the_speed_and_the_request_reuse_the_items_of_the_driver_assistance_increment():
    """D7: the display's port items specialize the phase 6 items of the driver-assistance increment and add no
    attribute, so the quantities of the vehicle speed and of the warning request are defined once."""
    code = _code()
    for item in DRIVING_ITEMS:
        assert f"private import DE4SDV_DriverAssistanceFunctionalArchitecture::{item};" in code, item
        assert not re.search(rf"\bdef\s+{item}\b", code), f"{item} is defined once, in the driver-assistance increment"
    assert code.count("private import DE4SDV_DriverAssistanceFunctionalArchitecture::") == len(DRIVING_ITEMS), \
        "one by one, never the whole package"
    driving = strip_comments(DRIVING_FUNCTIONS.read_text(encoding="utf-8"))
    for item, (base, attributes) in DRIVING_ITEMS.items():
        assert _attributes(braced_body(driving, f"item def {item} :> {base}")) == attributes, item
    for item in ("DisplayVehicleSpeedInput", "DisplayWarningRequestInput"):
        body = braced_body(code, f"item def {item} :> {BOUNDARY_ITEM_SPECIALIZATIONS[item]}")
        assert not re.search(r"\b(?:attribute|item|part|ref)\b", body), f"{item} adds nothing"


def test_the_functions_name_no_technology_platform_candidate_or_claim():
    declarations = [f"action def {d} :> AllocatableFunction" for d in FUNCTIONS.values()]
    declarations += [f"action def {FLOW}"] + [f"item def {item}" for item in sorted(INTERNAL_ITEMS)]
    for declaration in declarations:
        doc = _doc(declaration)
        found = [word for word in FORBIDDEN_IN_FUNCTIONS if re.search(rf"\b{re.escape(word)}", doc, re.I)]
        found += [word for word in TECHNOLOGY_NAMES if re.search(rf"\b{re.escape(word)}\b", doc)]
        assert not found, (declaration, found)


def test_no_doc_of_the_package_names_a_technology_of_the_design():
    """D6: the docs of the package name no technology; the phase 2 references keep their names in the code."""
    docs = _docs()
    assert len(docs) >= 40, "the population of the check must not be vacuous"
    for text in docs:
        assert not DESIGN_TECHNOLOGY_WORDS.search(text), (DESIGN_TECHNOLOGY_WORDS.search(text), text[:80])
    outage = "an outage of the drawing of the scene or of the environment that hosts it"
    assert outage in _header().lower() and outage in " ".join(_process_paragraphs()).lower()


def test_the_grids_have_a_title_and_their_axes_named():
    from scripts.render_grid_csv import GRID_METADATA

    for key, expected in GRIDS.items():
        grid = GRID_METADATA[key]
        assert (grid.title, grid.description, grid.row_label, grid.column_label) == expected, key


def test_the_context_elements_perform_their_functions_outside_the_display_scope():
    code = _code()
    assert re.search(rf"\baction\s+def\s+{CONTEXT_FUNCTION_ROOT}\s*\{{", code), "the context functions need a root"
    assert not re.search(rf"\baction\s+def\s+{CONTEXT_FUNCTION_ROOT}\s*:>", code), "the root specializes nothing"
    for root in ("ContextElementFunction", "DriverAssistanceContextFunction"):
        assert root not in code, f"not {root}, whose text names another system"
    for name, parameters in CONTEXT_FUNCTIONS.items():
        body = _direct(braced_body(code, f"action def {name} :> {CONTEXT_FUNCTION_ROOT}"))
        assert re.findall(r"\b(in|out)\s+(\w+)\s*:\s*(\w+)\s*;", body) == parameters, name
        assert _doc(f"action def {name} :> {CONTEXT_FUNCTION_ROOT}") == CONTEXT_DOCS[name], name
    assert _doc(f"action def {CONTEXT_FUNCTION_ROOT}") == CONTEXT_ROOT_DOC
    for item, doc in ITEM_DOCS.items():
        assert _doc(f"item def {item}") == doc, item


def test_the_process_binds_its_participants_to_the_context_parts_of_phase_2():
    """SAF System Process: one activity whose participants are the context parts of phase 2 and the system of
    interest, bound by reference, so the increment keeps one context. Each reference resolves: the part exists in
    the context of phase 2, with the participant's type."""
    code = _code()
    body = _process_body()
    direct = _direct(body)
    assert re.findall(r"\bref\s+part\s+(\w+)\s*:\s*(\w+)\s*=\s*([\w:]+)\s*\{", direct) == [
        (name, typed, bound) for name, (typed, bound, _) in PARTICIPANTS.items()]
    assert not re.search(r"(?<!ref )\bpart\s+\w+", direct), "the process declares no part of its own"
    assert f"private import DE4SDV_HmiDisplayOperationalContext::{CONTEXT_USAGE};" in code
    context = _direct(braced_body(strip_comments(OPERATIONAL_CONTEXT.read_text(encoding="utf-8")),
                                  f"part {CONTEXT_USAGE} : SystemContext"))
    parts = dict(re.findall(r"\bpart\s+(\w+)\s*:\s*(\w+)", context))
    assert set(parts) == set(PARTICIPANTS), "one participant for each part of the context of phase 2"
    for name, (typed, bound, _) in PARTICIPANTS.items():
        assert parts[bound.split("::")[-1]] == typed, name
    assert not re.search(r"\b(action|perform|first)\b", direct), \
        "the process owns no action of its own: each participant performs its functions in its own body"
    for name, (typed, bound, functions) in PARTICIPANTS.items():
        part = braced_body(body, f"ref part {name} : {typed} = {bound}")
        assert re.findall(r"\bperform\s+action\s+(\w+)\s*:\s*(\w+)\s*;", part) == list(functions.items()), name
        if name == "hmiDisplay":
            assert re.findall(r"\bperform\s+(\w+)\s*;", part) == [FLOW_USAGE], \
                "the display's step is the flow usage the boundary performs, not a second usage of the flow"
        else:
            assert not re.search(r"\bperform\s+\w+\s*;", part), name
        assert _doc(f"ref part {name} : {typed} = {bound}") == PARTICIPANT_DOCS[name], name
    performed = {definition for _, (_, _, functions) in PARTICIPANTS.items() for definition in functions.values()}
    assert performed == set(CONTEXT_FUNCTIONS), "every context function is performed by one participant"
    assert set(re.findall(r"\bflow\s+from\s+([\w.]+)\s+to\s+([\w.]+)\s*;", body)) == PROCESS_FLOWS
    assert len(re.findall(r"\bflow\s+from\b", body)) == len(PROCESS_FLOWS)
    assert not [flow for flow in PROCESS_FLOWS if flow[0].startswith("driver.")], "nothing flows back from the driver"
    assert {flow[0].split(".")[0] for flow in PROCESS_FLOWS if flow[1].startswith("hmiDisplay.")} == {
        "candidate", "scorePath", "vehicle"}, "the scene, the request and the speed enter the display"
    assert re.search(rf"\baction\s+{PROCESS_USAGE}\s*:\s*{PROCESS}\s*;", code)
    assert "allocate" not in body, "the process assigns no responsibility"


def test_the_context_holds_no_other_presentation_of_the_warning():
    """D1: the display is the one presenter of the warning in the process, as the context of phase 2 draws it."""
    givers = [flow for flow in _process_flows() if flow[1].startswith("driver.")]
    assert givers, "the driver takes what the display gives"
    assert {flow[0].split(".")[0] for flow in givers} == {"hmiDisplay"}
    assert "Presentation" not in _code()
    assert "The context of Phase 2 holds no other presentation of the warning beside the display" in \
        " ".join(_guide_section(_guide()).split())


def test_the_process_states_the_sequence_and_the_times_of_the_warning():
    """hmiWarningSequenceConcern and hmiAndroidOutageConcern of phase 1: the sequence from the request to each mode
    and its times, the share of the display (REQ-HMI-005, D2), and the outage as an event inside the display (D3)."""
    assert _process_paragraphs() == PROCESS_PARAGRAPHS
    terms = _flat(NEEDS_REQUIREMENTS.read_text(encoding="utf-8"))
    assert ("When the start of a request reaches the HMI display, the HMI display shall start each mode of the "
            "collision warning within 0.1 s of wall-clock time.") in terms
    code = _code()
    for concern in [*PHASE_1_PROCESS_CONCERNS, PHASE_1_STATE_CONCERN]:
        assert f"private import DE4SDV_HmiDisplayFraming::{concern};" in code, concern
    framing = _flat(FRAMING.read_text(encoding="utf-8"))
    assert framing.count("Answered by the system process of phase 6.") == 3
    assert framing.count("Answered by the system state of phase 6.") == 1


def test_the_states_name_the_functions_that_depend_on_them():
    """SAF System State: which states the display has, and which functions depend on them. The dependence is
    native, one dependency per function and state, and each state's doc says what the dependent functions do."""
    code = _code()
    pairs = set(re.findall(rf"\bdependency\s+(\w+)\s+from\s+{FLOW}::(\w+)\s+to\s+(\w+)::(\w+)\s*;", code))
    assert {(function, state_def, state) for _, function, state_def, state in pairs} == STATE_DEPENDENCIES
    for name, function, _, state in pairs:
        assert name == f"{function}DependsOn{state[0].upper()}{state[1:]}State", name
    assert len(re.findall(r"\bdependency\b", code)) == len(STATE_DEPENDENCIES), "no other dependency"
    for function, _, state in STATE_DEPENDENCIES:
        assert function in _doc(f"state {state}"), (function, state)


def test_the_display_boundary_carries_typed_functional_ports():
    """SAF System Interface Definition: the display's conceptual interfaces as port definitions with one directed
    item each, typed by a functional item definition of this package."""
    code = _code()
    assert re.search(rf"\bpart\s+def\s+{BOUNDARY}\s*:>\s*HmiDisplaySystem\s*\{{", code)
    specializations = dict(re.findall(r"\bitem\s+def\s+(\w+)\s*:>\s*(\w+)\s*\{", code))
    assert specializations == BOUNDARY_ITEM_SPECIALIZATIONS
    for port, item in BOUNDARY_PORTS.items():
        body = braced_body(code, f"port def {port}")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [item], port
        assert _doc(f"port def {port}") == PORT_DOCS[port], port
    assert set(re.findall(r"\bport\s+def\s+(\w+)", code)) == set(BOUNDARY_PORTS)
    boundary = braced_body(code, f"part def {BOUNDARY}")
    direct = _direct(boundary)
    assert re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", direct) == list(BOUNDARY_PORT_USAGES.items())
    perform = braced_body(boundary, f"perform {FLOW_USAGE} : {FLOW}")
    assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*=\s*([\w.]+)\s*;", perform) == BOUNDARY_BINDINGS
    assert not re.search(rf"\bpart\s+\w+\s*:\s*{BOUNDARY}\b", code), "a usage of it would be a second system"
    assert _doc(f"part def {BOUNDARY}") == BOUNDARY_DOC
    for typed in ("SubjectVehicle", "Driver"):
        assert f"private import DE4SDV_OperationalContext::{typed};" in code, typed
    assert "private import DE4SDV_DriverAssistanceOperationalContext::SCORECommandAndWarningPath;" in code
    assert "private import DE4SDV_DriverAssistanceFraming::DriverAssistanceSystem;" in code
    assert "private import DE4SDV_HmiDisplayFraming::HmiDisplaySystem;" in code


def test_the_package_imports_one_by_one():
    code = _code()
    wildcards = re.findall(r"\bimport\s+([\w:]+)::\*\*?;", code)
    assert sorted(wildcards) == sorted(["DE4SDV_Stakeholders", "DE4SDV_HmiDisplayNeedsRequirements", "SAF_Viewpoints",
                                        "StandardViewDefinitions", "SysideViews", "Views"]), \
        "no feature package by wildcard but the needs and requirements"


def test_the_package_publishes_exactly_one_view_per_question():
    declared = re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M)
    assert sorted(declared) == sorted(PUBLISHED_VIEWS)
    assert len(declared) == 5


@pytest.mark.parametrize("view_name", sorted(VIEWS), ids=sorted(VIEWS))
def test_each_view_frames_its_concern_and_exposes_its_content(view_name):
    view_type, render, viewpoint_def, exposes, frames = VIEWS[view_name]
    code = _code()
    header = f"view {view_name}" + (f" : {view_type}" if view_type else "")
    assert re.search(rf"\bview\s+{view_name}\s*" + (rf":\s*{re.escape(view_type)}\s*" if view_type else "") + r"\{",
                     code), header
    view = braced_body(code, header)
    viewpoint = braced_body(view, "viewpoint")
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == frames
    assert re.search(rf"viewpoint\s+\w+\s*:\s*{viewpoint_def}\s*\{{", view), view_name
    assert len(re.findall(r"\bviewpoint\b", view)) == 1
    assert re.findall(r"\bexpose\s+([\w:*]+(?:\[[^\]]*\])?)\s*;", view) == exposes
    if render:
        assert render in view
    else:
        assert "render as" not in view, "the view type selects the kind"
    if view_name in (PROCESS_VIEW, INTERFACE_VIEW):
        assert "attribute showAnnotationRows = false;" in view
    if view_name == PROCESS_VIEW:
        assert "attribute maxCompartmentEntries = 0;" in view


def test_the_process_view_notes_where_its_times_are():
    """R1: the process view frames the warning sequence and the outage, but its convention form (doc rows hidden)
    prints no doc. The view index says where the times and the outage are, and the lane docs, the docs that a
    doc-row form prints, carry them."""
    view = braced_body(_code(), f"view {PROCESS_VIEW} : ActionFlowView")
    assert "attribute showAnnotationRows = false;" in view, "the convention form"
    from scripts.generate_view_index import KNOWN_PRESENTATION_NOTES

    assert KNOWN_PRESENTATION_NOTES[PROCESS_VIEW] == PROCESS_VIEW_NOTE
    assert sorted(LANE_FACTS) == sorted(set(PARTICIPANTS) - {"driver"})
    for name, phrases in LANE_FACTS.items():
        typed, bound, _ = PARTICIPANTS[name]
        doc = _doc(f"ref part {name} : {typed} = {bound}")
        for phrase in phrases:
            assert phrase in doc, (name, phrase)
    times = " ".join(_process_paragraphs())
    for phrase in ("allots 0.2 s of wall-clock time", "every step of 0.05 s", "An outage of the drawing"):
        assert phrase in times, phrase


def test_the_table_states_its_rows_and_columns():
    view = braced_body(_code(), f"view {TABLE_VIEW} : TVD::TableView")
    assert "filter @ SysML::StateUsage;" in view
    for label, feature in TABLE_COLUMNS:
        column = braced_body(view, f"view {label} :> columnViews")
        assert f"attribute :>> featureToRender = {feature}" in column, label


@pytest.mark.parametrize("concern_name", sorted(CATALOGUE_CONCERNS), ids=sorted(CATALOGUE_CONCERNS))
def test_each_phase_6_concern_is_typed_by_the_catalogue_and_held_by_the_party_it_serves(concern_name):
    catalogue, stakeholders = CATALOGUE_CONCERNS[concern_name]
    concern = braced_body(_code(), f"concern {concern_name} : {catalogue}")
    members = re.findall(r"\b(subject|stakeholder)\b", concern)
    assert members and members[0] == "subject"
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == stakeholders
    assert _doc(f"concern {concern_name} : {catalogue}") == CONCERN_DOCS[concern_name]
    assert set(re.findall(r"\bconcern\s+(\w+)\s*:", _code())) == set(CATALOGUE_CONCERNS)


def test_the_package_types_no_vehicle_signal_specification():
    """Owner decision: no vehicle signal specification in phase 6. The typing starts at phase 8."""
    raw = _raw()
    assert "VSS" not in raw, "no vehicle signal type, import, path or word"
    assert "COVESA_VSS" not in raw and "DE4SDV_VSS_Extensions" not in raw
    assert not re.search(r"\bimport\b[^\n]*VSS", raw)
    assert "no vehicle signal specification" in _header().lower()


def test_the_header_states_its_text_of_record():
    assert _header_paragraphs() == HEADER_PARAGRAPHS


def test_the_package_declares_no_name_that_another_model_package_declares():
    # Two packages may declare the same name, but a lookup by name then finds two elements, and a check that
    # reads a folder by name sees one increment's element as the other's.
    kinds = (r"(?:part def|item def|action def|state def|port def|part|item|action|state|port|concern|view|"
             r"dependency|allocation|comment)")
    declared = set(re.findall(rf"(?m)^  {kinds}\s+(\w+)", _code()))
    assert len(declared) >= 55, "the population of the check must not be vacuous"
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


def test_no_text_of_phase_6_carries_the_excluded_word():
    for text in (_raw(), _guide_section(_guide())):
        words = set(re.findall(r"[a-z0-9]+", text.lower()))
        assert len(words) >= 100
        assert EXCLUDED_WORD_SHA256 not in {hashlib.sha256(word.encode()).hexdigest() for word in words}


def test_the_guide_has_a_phase_6_section_and_names_the_next_obligation():
    guide = _guide()
    assert guide.count(GUIDE_HEADING + "\n") == 1
    assert guide.index("## Requirements (Phase 5)") < guide.index(GUIDE_HEADING) \
        < guide.index("## What the framing already records as open")
    raw_section = _guide_section(guide)
    section = " ".join(raw_section.split())
    assert f"]({GUIDE_LINK})" in raw_section
    for name in (*FUNCTIONS, FLOW, PROCESS, *STATES, BOUNDARY, *PHASE_1_PROCESS_CONCERNS, PHASE_1_STATE_CONCERN,
                 CONCERN, INTERFACE_CONCERN, *PUBLISHED_VIEWS, "REQ-HMI-009", "REQ-HMI-005"):
        assert f"`{name}`" in section, name
    for phrase in GUIDE_PHRASES:
        assert phrase in section, phrase
    functions = [(match[1], " ".join(match[2].split()))
                 for match in re.finditer(r"(?ms)^- \*\*`(\w+)`\*\* (.*?)(?=^- |^\s*$)", raw_section)]
    assert functions == list(GUIDE_FUNCTION_BULLETS.items()), "the function bullets, whole, in order"
    assert list(GUIDE_FUNCTION_BULLETS) == list(FUNCTIONS)
    decisions = [(match[1], " ".join(match[2].split()))
                 for match in re.finditer(r"(?ms)^- \*\*(?!`\w+`\*\*)(.+?)\*\* (.*?)(?=^- |^\s*$)", raw_section)]
    assert decisions == list(GUIDE_DECISIONS.items()), "the four decisions, whole, in order"
    assert section.count(GUIDE_OUTAGE_SENTENCE) == 1
    blocks = [" ".join(block.split()) for block in re.split(r"\n\s*\n", raw_section.strip())]
    assert blocks.count(GUIDE_ALLOCATION_PARAGRAPH) == 1, "the allocation paragraph, whole"
    assert blocks.count(GUIDE_PROCESS_PARAGRAPH) == 1, "the process paragraph, whole"
    views = [" ".join(match.split())
             for match in re.findall(r"(?ms)^- (the (?:breakdown|matrix|process|table|tree) .*?)(?=^- |^\s*$)",
                                     raw_section)]
    assert views == GUIDE_VIEW_BULLETS, "the five view bullets, whole, in order"
    assert blocks == [GUIDE_OPENING_PARAGRAPH,
                      " ".join(f"- **`{name}`** {text}" for name, text in GUIDE_FUNCTION_BULLETS.items()),
                      GUIDE_FLOW_PARAGRAPH, GUIDE_DECISIONS_INTRO,
                      " ".join(f"- **{name}** {text}" for name, text in GUIDE_DECISIONS.items()),
                      GUIDE_ALLOCATION_PARAGRAPH, GUIDE_PROCESS_PARAGRAPH, GUIDE_INTERFACE_PARAGRAPH,
                      GUIDE_VIEWS_INTRO, " ".join(f"- {bullet}" for bullet in GUIDE_VIEW_BULLETS),
                      GUIDE_CLOSING_PARAGRAPH], "every block of the section, whole and in order, as it says"
    assert f"{_number_word(ALLOCATION_COUNT)} allocations in all" in GUIDE_ALLOCATION_PARAGRAPH
    assert "VisionPilot/" not in raw_section and ".cpp" not in raw_section, "the guide carries no upstream paths"
    prose = re.sub(r"`[^`]*`|\]\([^)]*\)", " ", raw_section)
    assert not DESIGN_TECHNOLOGY_WORDS.search(prose), DESIGN_TECHNOLOGY_WORDS.search(prose)
    assert "tests/test_hmi_display_functional_architecture.py" in section
    assert all(len(line) <= 79 or "](" in line for line in raw_section.splitlines()), "the guide wraps at 79"
    flat = " ".join(guide.split())
    assert flat.count(GUIDE_STATUS) == 1 and GUIDE_STATUS_PHASE_5 not in flat
    frame = " ".join(guide.split("## Authoritative frame", 1)[1].split("\n## ", 1)[0].split())
    assert frame.count(GUIDE_FRAME_LINE) == 1, "the frame links the package, as it links each earlier phase"
    nxt = " ".join(guide.split("## Next obligation and execution limits", 1)[1].split("\n## ", 1)[0].split())
    assert nxt.count(GUIDE_NEXT) == 1
    assert "The next model obligation is **Phase 6**" not in flat
    assert "The next model obligation is **Phase 7**" not in flat
    assert "The next model obligation is **Phase 8**" not in flat
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert "tests/test_hmi_display_functional_architecture.py" in check
