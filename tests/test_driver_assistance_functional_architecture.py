"""Content pins for the driver-assistance functional architecture (phase 6), not semantic validation.

INC-DRIVING-002 phase 6 breaks the candidate driver-assistance system into its functions and allocates each
requirement of phase 5 to the functions that carry it. Method Check holds the DefineFunctionalArchitecture rules
(at least one function; each functional requirement allocated to a function by a native allocation). These pins
hold what review settled on top of them:

- four functions, each an AllocatableFunction, and the functional flow that breaks the system into them, with the
  items they exchange: the front-camera image and the vehicle speed of phase 2 in, the driving command and the
  warning request out, and inside, the assessment of the vehicle ahead, the state of the warning request and the
  record of the candidate identity;
- one command path: the emergency braking is a mode of the one function that commands the vehicle, not a second
  command source, and only that function gives the driving command;
- the warning request first: the command function takes the state of the request and starts an emergency braking
  only after the request has started;
- a driving command the actuation can check: its issue time, a sequence count and a check value
  (REQ-DRIVING-039);
- the allocation of every requirement but REQ-DRIVING-038 and REQ-DRIVING-043, which constrain the exchanges over
  the Eclipse S-CORE path and are carried in phase 8;
- the functions the context elements perform, as functions of their own root, outside the system's scope, and the
  system process that runs the system as one action between them, with the two modes of the warning and the times
  between the warning request, each mode and the start of the emergency braking, which answers the phase 1
  concern driverWarningSequenceConcern. Its participants are the context parts of phase 2 themselves, bound by
  reference;
- the modes and the functions that depend on them, the conceptual interfaces as port definitions with directed
  items typed by functional item definitions of this package, and one view per SAF question, five in all;
- no technology, platform or safety claim in the functions and the new elements, and no vehicle signal
  specification in the package.
"""

from pathlib import Path
import re

import pytest

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
MODEL = DRIVING / "driver_assistance_functional_architecture.sysml"
NEEDS_REQUIREMENTS = DRIVING / "driver_assistance_needs_requirements.sysml"
FRAMING = DRIVING / "driver_assistance_framing.sysml"
GUIDE = ROOT / "docs/guides/driver-assistance-increment.md"
PACKAGE = "DE4SDV_DriverAssistanceFunctionalArchitecture"
FLOW = "DriverAssistanceFunctionalFlow"
FLOW_USAGE = "driverAssistanceFunctionalFlow"
CONCERN = "driverAssistanceFunctionsConcern"
PHASE_1_CONCERN = "driverWarningSequenceConcern"
TREE_VIEW = "driverAssistanceFunctionBreakdownView"
MATRIX_VIEW = "driverAssistanceRequirementFunctionMappingView"

#: Each function of the flow, in breakdown order -> its definition.
FUNCTIONS = {
    "identifyCandidate": "IdentifyCandidate",
    "assessVehicleAhead": "AssessVehicleAhead",
    "requestWarning": "RequestCollisionWarning",
    "commandVehicle": "GiveDrivingCommand",
}

#: The items the functions exchange inside the system; the boundary items are phase 2's.
INTERNAL_ITEMS = {"VehicleAheadAssessment", "WarningRequestState", "CandidateIdentityRecord"}
PHASE_2_ITEMS = ("FrontCameraImage", "VehicleSpeed", "DrivingCommand", "WarningRequest", "CollisionWarning")

#: The flow's own parameters: the phase 2 items crossing the boundary of the system.
FLOW_PARAMETERS = [
    ("in", "frontCameraImage", "FrontCameraImage"),
    ("in", "vehicleSpeed", "VehicleSpeed"),
    ("out", "drivingCommand", "DrivingCommand"),
    ("out", "warningRequest", "WarningRequest"),
]

#: Item flows between the functions (source, target).
FLOWS = {
    ("assessVehicleAhead.assessment", "requestWarning.assessment"),
    ("assessVehicleAhead.assessment", "commandVehicle.assessment"),
    ("requestWarning.warningState", "commandVehicle.warningState"),
    ("identifyCandidate.candidateRecord", "commandVehicle.candidateRecord"),
}
#: The order of one step: the assessment, then the warning request, then the command.
SUCCESSIONS = [("assessVehicleAhead", "requestWarning"), ("requestWarning", "commandVehicle")]

#: Function parameters bound to the flow's own parameters: (function, direction, parameter, flow parameter).
BINDINGS = {
    ("assessVehicleAhead", "in", "frontCameraImage", "frontCameraImage"),
    ("assessVehicleAhead", "in", "vehicleSpeed", "vehicleSpeed"),
    ("commandVehicle", "in", "currentSpeed", "vehicleSpeed"),
    ("requestWarning", "out", "warningRequest", "warningRequest"),
    ("commandVehicle", "out", "drivingCommand", "drivingCommand"),
}

#: Each requirement of phase 5 -> the functions it is allocated to.
ALLOCATED = {
    "reqEmergencyBrakingForImminentCollision": {"assessVehicleAhead", "commandVehicle"},
    "reqImpactSpeedWithinLimit": {"commandVehicle"},
    "reqDetectableDrivingCommand": {"commandVehicle"},
    "reqWithholdWarningRequest": {"assessVehicleAhead", "requestWarning"},
    "reqWithholdEmergencyBraking": {"assessVehicleAhead", "commandVehicle"},
    "reqWarningRequestBeforeEmergencyBraking": {"requestWarning", "commandVehicle"},
    "reqRecordCandidateIdentity": {"identifyCandidate", "commandVehicle"},
}
#: REQ-DRIVING-038 and REQ-DRIVING-043 constrain how the two outputs travel over the Eclipse S-CORE path, not a
#: function: phase 8 carries them.
EXCHANGE_CONSTRAINTS = {"reqDrivingCommandOverSCORE", "reqWarningRequestOverSCORE"}

MODES = ["identifying", "assisting", "warning", "emergencyBraking"]
TRANSITIONS = {("identifying", "assisting"), ("assisting", "warning"), ("warning", "emergencyBraking"),
               ("warning", "assisting"), ("emergencyBraking", "assisting")}

#: The root of the functions the context elements perform, outside the system's functional scope. Not an
#: AllocatableFunction: the increment's functions are the AllocatableFunction actions, and no context function
#: carries a requirement of phase 5. Its own root, not the closed-loop driving one, whose text names that loop.
CONTEXT_FUNCTION_ROOT = "DriverAssistanceContextFunction"

#: Each context function -> its parameters (direction, name, item type), named as the actions of phase 2 name them.
CONTEXT_FUNCTIONS = {
    "CaptureFrontCameraImage": [("out", "frontCameraImage", "FrontCameraImage")],
    "SampleVehicleSpeed": [("out", "vehicleSpeed", "VehicleSpeed")],
    "CarryDrivingCommand": [("in", "drivingCommand", "DrivingCommand"), ("out", "carriedCommand", "DrivingCommand")],
    "CarryWarningRequest": [("in", "warningRequest", "WarningRequest"),
                            ("out", "carriedWarningRequest", "WarningRequest")],
    "ActuateVehicle": [("in", "drivingCommand", "DrivingCommand")],
    "ShowCollisionWarning": [("in", "warningRequest", "WarningRequest"),
                             ("out", "collisionWarning", "CollisionWarning")],
    "SoundCollisionWarning": [("in", "warningRequest", "WarningRequest"),
                              ("out", "collisionWarning", "CollisionWarning")],
    "ReceiveCollisionWarning": [("in", "shownWarning", "CollisionWarning"), ("in", "soundedWarning", "CollisionWarning")],
}

PROCESS = "DriverAssistanceSystemProcess"
PROCESS_USAGE = "driverAssistanceSystemProcess"

#: The one operational context of the increment (phase 2), whose parts the process binds its participants to.
CONTEXT_USAGE = "driverAssistanceOperationalContext"

#: Each participant of the process -> its phase 2 type, the phase 2 context part it is bound to by reference (the
#: process declares no part of its own) and the actions it owns and performs, each a context function of this
#: package (name -> definition). The participant is the swim lane of its functions.
PARTICIPANTS = {
    "vehicle": ("SubjectVehicle", f"{CONTEXT_USAGE}::vehicle",
                {"captureImage": "CaptureFrontCameraImage", "sampleSpeed": "SampleVehicleSpeed",
                 "actuateVehicle": "ActuateVehicle"}),
    "candidateSystem": ("DriverAssistanceSystem", f"{CONTEXT_USAGE}::candidateSystem", {}),
    "scorePath": ("SCORECommandAndWarningPath", f"{CONTEXT_USAGE}::scorePath",
                  {"carryCommand": "CarryDrivingCommand", "carryWarningRequest": "CarryWarningRequest"}),
    "warningPresentation": ("DriverWarningPresentation", f"{CONTEXT_USAGE}::aaosSDVGuest::warningPresentation",
                            {"showWarning": "ShowCollisionWarning", "soundWarning": "SoundCollisionWarning"}),
    "driver": ("Driver", f"{CONTEXT_USAGE}::driver", {"receiveWarning": "ReceiveCollisionWarning"}),
}

#: The items of the process (source, target), each end chained through the participant that owns the action:
#: the exchange says who gives and who takes. The carried warning request goes to both modes of the warning.
PROCESS_FLOWS = {
    ("vehicle.captureImage.frontCameraImage", f"candidateSystem.{FLOW_USAGE}.frontCameraImage"),
    ("vehicle.sampleSpeed.vehicleSpeed", f"candidateSystem.{FLOW_USAGE}.vehicleSpeed"),
    (f"candidateSystem.{FLOW_USAGE}.drivingCommand", "scorePath.carryCommand.drivingCommand"),
    (f"candidateSystem.{FLOW_USAGE}.warningRequest", "scorePath.carryWarningRequest.warningRequest"),
    ("scorePath.carryCommand.carriedCommand", "vehicle.actuateVehicle.drivingCommand"),
    ("scorePath.carryWarningRequest.carriedWarningRequest", "warningPresentation.showWarning.warningRequest"),
    ("scorePath.carryWarningRequest.carriedWarningRequest", "warningPresentation.soundWarning.warningRequest"),
    ("warningPresentation.showWarning.collisionWarning", "driver.receiveWarning.shownWarning"),
    ("warningPresentation.soundWarning.collisionWarning", "driver.receiveWarning.soundedWarning"),
}

#: The functions whose behavior differs by mode (function usage, mode).
MODE_DEPENDENCIES = {
    ("commandVehicle", "identifying"),
    ("commandVehicle", "assisting"),
    ("commandVehicle", "warning"),
    ("commandVehicle", "emergencyBraking"),
    ("requestWarning", "assisting"),
    ("requestWarning", "warning"),
}

#: The functional item definitions of the boundary, each specializing its phase 2 item.
BOUNDARY_ITEM_SPECIALIZATIONS = {
    "FrontCameraImageInput": "FrontCameraImage",
    "VehicleSpeedInput": "VehicleSpeed",
    "DrivingCommandOutput": "DrivingCommand",
    "CollisionWarningRequestOutput": "WarningRequest",
}
#: What each boundary item carries, as ISQ quantities and scalar values, no signal specification.
BOUNDARY_ITEM_ATTRIBUTES = {
    "FrontCameraImageInput": {"captureTime": "ISQ::DurationValue"},
    "VehicleSpeedInput": {"speed": "ISQ::SpeedValue", "sampleTime": "ISQ::DurationValue"},
    "DrivingCommandOutput": {"steeringAngle": "ISQ::AngularMeasureValue", "acceleration": "ISQ::AccelerationValue",
                             "issueTime": "ISQ::DurationValue", "sequenceCount": "Natural", "checkValue": "Natural"},
    "CollisionWarningRequestOutput": {"requested": "Boolean", "issueTime": "ISQ::DurationValue"},
}

#: Each port definition of the boundary -> its one directed item (direction, name, item definition).
BOUNDARY_PORTS = {
    "FrontCameraImageInbound": ("in", "frontCameraImage", "FrontCameraImageInput"),
    "VehicleSpeedInbound": ("in", "vehicleSpeed", "VehicleSpeedInput"),
    "DrivingCommandOutbound": ("out", "drivingCommand", "DrivingCommandOutput"),
    "WarningRequestOutbound": ("out", "warningRequest", "CollisionWarningRequestOutput"),
}

BOUNDARY = "DriverAssistanceFunctionalBoundary"

#: Each port usage of the boundary part -> its port definition.
BOUNDARY_PORT_USAGES = {
    "frontCameraImageIn": "FrontCameraImageInbound",
    "vehicleSpeedIn": "VehicleSpeedInbound",
    "drivingCommandOut": "DrivingCommandOutbound",
    "warningRequestOut": "WarningRequestOutbound",
}

#: How the boundary binds the flow's parameters to the port payloads (direction, parameter, binding).
BOUNDARY_BINDINGS = {
    ("in", "frontCameraImage", "frontCameraImageIn.frontCameraImage"),
    ("in", "vehicleSpeed", "vehicleSpeedIn.vehicleSpeed"),
    ("out", "drivingCommand", "drivingCommandOut.drivingCommand"),
    ("out", "warningRequest", "warningRequestOut.warningRequest"),
}

PROCESS_CONCERN = "driverAssistanceProcessConcern"
STATE_CONCERN = "driverAssistanceModeDependenceConcern"
INTERFACE_CONCERN = "driverAssistanceInterfaceConcern"

#: The Phase 6 concerns, the catalogue concern definition each is typed by, and the parties that hold it.
CATALOGUE_CONCERNS = {
    CONCERN: ("FunctionalBehaviorConcern", {"SystemArchitect", "VerificationEngineer"}),
    PROCESS_CONCERN: ("SystemProcessConcern", {"SystemArchitect", "SystemsEngineer"}),
    STATE_CONCERN: ("SystemStateConcern", {"SystemArchitect", "SoftwareDeveloper"}),
    INTERFACE_CONCERN: ("FunctionalInterfaceConcern", {"SystemsEngineer", "SoftwareDeveloper"}),
}

#: One view per SAF question beyond the breakdown and the matrix: name -> (type or "", render statement,
#: exposures, framed concerns), in the forms the closed-loop driving increment proved with licensed renders: the
#: process an action flow with one level of each participant exposed, the modes a table, the interfaces the tree
#: of the port definitions with their items. The process also answers the phase 1 concern of the warning sequence.
VIEWS = {
    "driverAssistanceSystemProcessView": (
        "ActionFlowView", "",
        [f"{PROCESS}::*"] + [f"{PROCESS}::{participant}::*" for participant in PARTICIPANTS],
        [PROCESS_CONCERN, PHASE_1_CONCERN]),
    "driverAssistanceModeDependenceTableView": (
        "TVD::TableView", "", [f"DriverAssistanceModes::{mode}" for mode in MODES], [STATE_CONCERN]),
    "driverAssistanceFunctionalInterfaceView": (
        "", "render asTreeDiagram;", sorted(BOUNDARY_PORTS), [INTERFACE_CONCERN]),
}
#: The one table, with the row population and the columns it renders.
TABLES = {
    "driverAssistanceModeDependenceTableView": ("filter @ SysML::StateUsage;",
                                                [("Mode", "CT::declaredName"),
                                                 ("DependentFunctions", "CT::documentation")]),
}

#: Every view the package publishes: the breakdown, the matrix and one view per question above.
PUBLISHED_VIEWS = {TREE_VIEW, MATRIX_VIEW, *VIEWS}

#: The catalogue viewpoint definition each view's viewpoint usage is typed by, by the phase 6 concern.
VIEWPOINTS = {
    PROCESS_CONCERN: "SystemProcessViewpoint",
    STATE_CONCERN: "SystemStateViewpoint",
    INTERFACE_CONCERN: "SystemInterfaceDefinitionViewpoint",
}

#: Words that would name a technology, the candidate, a platform or a claim inside a function or a new element.
FORBIDDEN_IN_FUNCTIONS = ("CARLA", "ROS", "DDS", "Zenoh", "SOME/IP", "GPU", "Python", "PyTorch", "Linux",
                          "Android", "S-CORE", "SCORE", "VSS", "VisionPilot", ".cpp", "safe", "certif", "complian",
                          "homolog")

#: Buses, brokers, platforms and runtimes, matched by case so that the word "can" is no bus.
TECHNOLOGY_NAMES = ("CAN", "LIN", "FlexRay", "Ethernet", "gRPC", "KUKSA", "AUTOSAR", "AAOS", "Autoware", "ONNX",
                    "TensorRT", "CUDA", "OpenCV")


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


def _header() -> str:
    return _flat(_raw().split(f"package {PACKAGE}", 1)[0])


def _flow_body() -> str:
    return braced_body(_code(), f"action def {FLOW}")


def _process_body() -> str:
    return braced_body(_code(), f"action def {PROCESS}")


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
    return re.findall(r"\brequirement\s+<'REQ-DRIVING-\d{3}'>\s+(\w+)\s*:\s*(\w+)\s*\{", code)


def _terms() -> str:
    return _flat(NEEDS_REQUIREMENTS.read_text(encoding="utf-8"))


def test_the_charter_names_the_package_after_the_needs_and_requirements():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part driverAssistanceCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    assert names.index(PACKAGE) == names.index("DE4SDV_DriverAssistanceNeedsRequirements") + 1
    assert re.search(rf"(?m)^package\s+{PACKAGE}\s*\{{", _code())


def test_the_four_functions_are_allocatable_functions_and_nothing_else_is():
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
    for item in PHASE_2_ITEMS:
        assert f"private import DE4SDV_DriverAssistanceOperationalContext::{item};" in code, item
    assert re.search(rf"\baction\s+{FLOW_USAGE}\s*:\s*{FLOW}\s*;", code)


def test_the_flow_breaks_the_system_into_the_four_functions():
    direct = _direct(_flow_body())
    assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", direct) == FLOW_PARAMETERS
    assert dict(re.findall(r"\baction\s+(\w+)\s*:\s*(\w+)\s*\{", direct)) == FUNCTIONS
    assert list(dict(re.findall(r"\baction\s+(\w+)\s*:\s*(\w+)\s*\{", direct))) == list(FUNCTIONS), \
        "the breakdown keeps the order of one step"


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


def test_one_command_path_whose_emergency_braking_is_a_mode_of_the_command_function():
    code = _code()
    functions = dict(re.findall(r"\baction\s+def\s+(\w+)\s*:>\s*AllocatableFunction\s*\{([^}]*)\}", code))
    commanders = {name for name, body in functions.items() if re.search(r"\bout\s+\w+\s*:\s*DrivingCommand\b", body)}
    assert commanders == {"GiveDrivingCommand"}, "one function gives the driving command"
    requesters = {name for name, body in functions.items() if re.search(r"\bout\s+\w+\s*:\s*WarningRequest\b", body)}
    assert requesters == {"RequestCollisionWarning"}
    flow = _flow_body()
    for outer in ("drivingCommand", "warningRequest"):
        sources = re.findall(rf"\baction\s+(\w+)\s*:\s*\w+\s*\{{[^}}]*\bout\s+\w+\s*=\s*{FLOW}::{outer}\s*;", flow)
        assert sources == [{"drivingCommand": "commandVehicle", "warningRequest": "requestWarning"}[outer]], outer
    assert "not a second command source" in _header()
    assert "gapNoSeparateEmergencyFunction" in _header(), "the open question stays open"
    doc = _doc("action def GiveDrivingCommand :> AllocatableFunction")
    assert ("It starts the emergency braking, a command for 5.0 m/s² or more, only while a collision is imminent and "
            "only after the warning request has started, and commands at least 5.0 m/s² while the needed deceleration "
            "is at least 5.0 m/s².") in doc
    assert "Until an emergency braking starts, it follows the lane" in doc
    assert "with a deceleration below 5.0 m/s²" in doc
    # the bound is the term of phase 5, not a number of this phase
    assert "a deceleration of at least 5.0 m/s², in its driving command or apart from it" in _terms()


def test_the_warning_request_comes_first():
    """The command function takes the state of the warning request and starts an emergency braking only after it;
    starting the request with the imminence gives the lead of REQ-DRIVING-042 that phase 5 computed for the
    settings."""
    code = _code()
    assert "in warningState : WarningRequestState;" in braced_body(code, "action def GiveDrivingCommand")
    assert "out warningState : WarningRequestState;" in braced_body(code, "action def RequestCollisionWarning")
    assert ("requestWarning.warningState", "commandVehicle.warningState") in FLOWS
    doc = _doc("action def RequestCollisionWarning :> AllocatableFunction")
    assert doc.startswith("Starts the warning request at the boundary of the system when a collision with a "
                          "vehicle ahead becomes imminent, and starts none while no collision is imminent")
    assert "in each setting at a constant approach speed the two are at least 1.11 s apart" in doc
    assert "the collision becomes imminent at least 1.11 s before a needed deceleration of 5.0 m/s²" in _terms()


def test_the_assessment_works_out_the_terms_of_the_requirements():
    doc = _doc("action def AssessVehicleAhead :> AllocatableFunction")
    imminence = "a time to collision of at most 4.0 s and a needed deceleration of at least 1.0 m/s²"
    assert f"whether a collision is imminent: {imminence}." in doc
    assert imminence in _terms(), "the numbers are the term of phase 5"
    for word in ("lane", "closest vehicle ahead", "distance", "closes on it", "time to collision",
                 "needed deceleration"):
        assert word in doc, word
    assessment = _doc("item def VehicleAheadAssessment")
    assert "the time to collision, which has no value while the vehicle does not close on it" in assessment


def test_the_candidate_identity_is_recorded_before_the_first_command():
    code = _code()
    assert "in candidateRecord : CandidateIdentityRecord;" in braced_body(code, "action def GiveDrivingCommand")
    assert re.findall(r"\bout\s+(\w+)\s*:\s*(\w+)\s*;", braced_body(code, "action def IdentifyCandidate")) == [
        ("candidateRecord", "CandidateIdentityRecord")]
    doc = _doc("action def IdentifyCandidate :> AllocatableFunction")
    assert doc.startswith("Before the first driving command of each run, records the candidate identity: ")
    for part in ("the upstream revision", "the difference between the source of the system and that revision",
                 "the SHA-256 of each network file", "of each file of its configuration",
                 "the settings of its launch, verbatim"):
        assert part in doc, part
    assert "It gives none before the candidate identity is recorded." in _doc(
        "action def GiveDrivingCommand :> AllocatableFunction")


def test_the_driving_command_carries_the_parts_by_which_the_actuation_detects_a_failure_of_the_path():
    """REQ-DRIVING-039: the form of the command lets the actuation detect its loss, delay, repetition or
    corruption on the path. Phase 6 names the parts; phase 8 records the realization the analysis reads."""
    code = _code()
    command = braced_body(code, "item def DrivingCommandOutput :> DrivingCommand")
    assert dict(re.findall(r"\battribute\s+(\w+)\s*:\s*([\w:]+)\s*;", command)) == \
        BOUNDARY_ITEM_ATTRIBUTES["DrivingCommandOutput"]
    doc = _doc("item def DrivingCommandOutput :> DrivingCommand")
    for part in ("its issue time in simulation time, by which a delay shows",
                 "a sequence count, one more than that of the command before it, by which a loss or a repetition "
                 "shows", "a check value over the other parts, by which a corruption shows", "REQ-DRIVING-039"):
        assert part in doc, part
    assert ("It gives each command with its issue time, a sequence count and a check value, the form by which the "
            "actuation can detect its loss, delay, repetition or corruption on the path.") in _doc(
        "action def GiveDrivingCommand :> AllocatableFunction")
    actuation = _doc(f"action def ActuateVehicle :> {CONTEXT_FUNCTION_ROOT}")
    assert "rejecting what it detects is the share of the product that holds the path (REQ-MW-006)" in actuation


def test_the_modes_follow_from_the_requirements():
    machine = braced_body(_code(), "state def DriverAssistanceModes")
    assert re.findall(r"\bstate\s+(\w+)\s*[;{]", machine) == MODES
    assert set(re.findall(r"\btransition\s+first\s+(\w+)\s+then\s+(\w+)\s*;", machine)) == TRANSITIONS
    assert len(re.findall(r"\btransition\b", machine)) == len(TRANSITIONS)
    assert "The modes follow from the requirements, not from a term of phase 5." in _doc(
        "state def DriverAssistanceModes")


def test_each_requirement_is_allocated_to_the_functions_decided():
    assert _allocations() == ALLOCATED


def test_every_functional_requirement_is_allocated_and_every_function_carries_one():
    requirements = _requirements()
    assert len(requirements) == 9
    allocated = _allocations()
    functional = [name for name, kind in requirements if kind == "FunctionalRequirementCandidate"]
    assert len(functional) == 5 and all(name in allocated for name in functional)
    assert {name for name, _ in requirements} - set(allocated) == EXCHANGE_CONSTRAINTS
    assert set(allocated) <= {name for name, _ in requirements}
    assert set().union(*allocated.values()) == set(FUNCTIONS)


def test_the_s_core_constraints_are_left_to_the_exchanges_of_phase_8():
    header = _header()
    assert "REQ-DRIVING-038" in header and "REQ-DRIVING-043" in header and "phase 8" in header
    assert not EXCHANGE_CONSTRAINTS & set(_allocations())


def test_the_breakdown_view_shows_the_flow_with_its_four_functions():
    """The view exposes the flow usage only, the form the closed-loop driving increment proved: its compartments
    list the items and the functions. Exposing the functions themselves, the allocation targets, made SysIDE draw
    every allocation of that package as an unconnected node (licensed run 41737744809)."""
    view = braced_body(_code(), f"view {TREE_VIEW}")
    viewpoint = braced_body(view, "viewpoint")
    assert re.search(r"viewpoint\s+\w+\s*:\s*SystemFunctionalBreakdownStructureViewpoint\s*\{", view)
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == [CONCERN]
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", view) == [FLOW_USAGE]
    assert "render asTreeDiagram;" in view


def test_the_matrix_maps_every_requirement_to_its_functions():
    view = braced_body(_code(), f"view {MATRIX_VIEW} : MVD::MatrixView")
    viewpoint = braced_body(view, "viewpoint")
    assert re.search(r"viewpoint\s+\w+\s*:\s*SystemRequirementTraceabilityViewpoint\s*\{", view)
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == [CONCERN]
    rows = braced_body(view, "view :>> rowView")
    columns = braced_body(view, "view :>> columnView")
    cells = braced_body(view, "view :>> cellView")
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", rows) == [name for name, _ in _requirements()]
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
        declared = dict(re.findall(r"\battribute\s+(\w+)\s*:\s*([\w:]+)\s*;", body))
        assert len(re.findall(r"\battribute\b", body)) == len(declared), item
        assert declared == attributes, item
    for scalar in ("Boolean", "Natural"):
        assert f"private import ScalarValues::{scalar};" in code, scalar
    camera = _doc("item def FrontCameraImageInput :> FrontCameraImage")
    assert "the system builds no calibration of its own" in camera
    assert "A request starts when it begins to ask." in _doc("item def CollisionWarningRequestOutput :> WarningRequest")


def test_the_functions_name_no_technology_platform_candidate_or_claim():
    declarations = [f"action def {d} :> AllocatableFunction" for d in FUNCTIONS.values()]
    declarations += [f"action def {FLOW}"] + [f"item def {item}" for item in sorted(INTERNAL_ITEMS)]
    for declaration in declarations:
        doc = _doc(declaration)
        found = [word for word in FORBIDDEN_IN_FUNCTIONS if re.search(rf"\b{re.escape(word)}", doc, re.I)]
        found += [word for word in TECHNOLOGY_NAMES if re.search(rf"\b{re.escape(word)}\b", doc)]
        assert not found, (declaration, found)


def test_the_grids_have_a_title_and_their_axes_named():
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"matrix-{MATRIX_VIEW}"]
    assert metadata.row_label == "requirements (requirement usages)"
    assert metadata.column_label == "system functions (action usages)"
    assert metadata.title and metadata.description


def test_the_context_elements_perform_their_functions_outside_the_system_scope():
    """The context elements act: the vehicle's front camera and motion sensing give the image and the speed, the
    command and warning path carries the two outputs, the warning presentation gives the warning in its two modes,
    the vehicle's actuation applies the command and the driver gets the warning. Those functions are not the
    system's: they are typed by their own root, not by AllocatableFunction."""
    code = _code()
    assert re.search(rf"\baction\s+def\s+{CONTEXT_FUNCTION_ROOT}\s*\{{", code), "the context functions need a root"
    assert not re.search(rf"\baction\s+def\s+{CONTEXT_FUNCTION_ROOT}\s*:>", code), "the root specializes nothing"
    assert "ContextElementFunction" not in code, "not the closed-loop driving root, whose text names that loop"
    for name, parameters in CONTEXT_FUNCTIONS.items():
        body = _direct(braced_body(code, f"action def {name} :> {CONTEXT_FUNCTION_ROOT}"))
        assert re.findall(r"\b(in|out)\s+(\w+)\s*:\s*(\w+)\s*;", body) == parameters, name
    assert "outside the scope of the driver-assistance system" in _doc(f"action def {CONTEXT_FUNCTION_ROOT}")


def test_the_process_binds_its_participants_to_the_context_parts_of_phase_2():
    """SAF System Process: one activity whose participants are the context parts of phase 2 and the system of
    interest, bound by reference, so the increment keeps one context and the process declares no part of its own.
    Each participant owns and performs its functions as the swim lane of its functions; the system's step is the
    one functional flow usage the boundary performs; the exchanges are the process's item flows, chained through
    the participants."""
    code = _code()
    body = _process_body()
    direct = _direct(body)
    assert re.findall(r"\bref\s+part\s+(\w+)\s*:\s*(\w+)\s*=\s*([\w:]+)\s*\{", direct) == [
        (name, typed, bound) for name, (typed, bound, _) in PARTICIPANTS.items()]
    assert not re.search(r"(?<!ref )\bpart\s+\w+", direct), "the process declares no part of its own"
    assert f"private import DE4SDV_DriverAssistanceOperationalContext::{CONTEXT_USAGE};" in code
    assert not re.search(r"\b(action|perform|first)\b", direct), \
        "the process owns no action of its own: each participant performs its functions in its own body"
    for name, (typed, bound, functions) in PARTICIPANTS.items():
        part = braced_body(body, f"ref part {name} : {typed} = {bound}")
        assert re.findall(r"\bperform\s+action\s+(\w+)\s*:\s*(\w+)\s*;", part) == list(functions.items()), name
        if name == "candidateSystem":
            assert re.findall(r"\bperform\s+(\w+)\s*;", part) == [FLOW_USAGE], \
                "the system's step is the flow usage the boundary performs, not a second usage of the flow"
        else:
            assert not re.search(r"\bperform\s+\w+\s*;", part), name
    performed = {definition for _, (_, _, functions) in PARTICIPANTS.items() for definition in functions.values()}
    assert performed == set(CONTEXT_FUNCTIONS), "every context function is performed by one participant"
    assert set(re.findall(r"\bflow\s+from\s+([\w.]+)\s+to\s+([\w.]+)\s*;", body)) == PROCESS_FLOWS
    assert len(re.findall(r"\bflow\s+from\b", body)) == len(PROCESS_FLOWS)
    assert not [flow for flow in PROCESS_FLOWS if flow[0].startswith("driver.")], "nothing flows back from the driver"
    assert not [flow for flow in PROCESS_FLOWS
                if flow[1].startswith("candidateSystem.") and not flow[0].startswith("vehicle.")], \
        "only the image and the speed enter the system"
    assert re.search(rf"\baction\s+{PROCESS_USAGE}\s*:\s*{PROCESS}\s*;", code)
    assert "allocate" not in body, "the process assigns no responsibility"
    doc = _doc(f"action def {PROCESS}")
    for phrase in ("the context parts of phase 2 themselves", "declares no part of its own",
                   "outside the scope of the driver-assistance system", "nothing flows back from the driver"):
        assert phrase in doc, phrase


def test_the_process_states_the_sequence_and_the_times_of_the_warning():
    """driverWarningSequenceConcern of phase 1: the sequence from the warning request to each of the two modes of
    the warning and to the start of the emergency braking, and the time between them, independent of the software.
    The times are those of REQ-DRIVING-042 and of the share phase 5 allots to the path and the AAOS SDV."""
    doc = _doc(f"action def {PROCESS}")
    for phrase in ("the system gives its warning request at its boundary at least 1.0 s of simulation time before "
                   "the start of its emergency braking, which leaves in its driving command (REQ-DRIVING-042)",
                   "the path and the warning presentation start each mode of the warning within 0.2 s of wall-clock "
                   "time after the request",
                   "so that each mode starts at least 0.8 s before the emergency braking while the simulation runs "
                   "no faster than wall-clock time, which is the obligation of System 2",
                   "Phase 8 divides the 0.2 s between the path and the warning presentation."):
        assert phrase in doc, phrase
    terms = _terms()
    assert "Of the 1.0 s, 0.2 s is allotted from the warning request to the start of each mode of the warning" in terms
    assert "each mode is due within 0.2 s of wall-clock time after the request" in terms
    for mode in ("ShowCollisionWarning", "SoundCollisionWarning"):
        assert "within 0.2 s of wall-clock time after the warning request starts at the boundary of the system" in \
            _doc(f"action def {mode} :> {CONTEXT_FUNCTION_ROOT}"), mode
    assert "on the display" in _doc(f"action def ShowCollisionWarning :> {CONTEXT_FUNCTION_ROOT}")
    assert "as a sound" in _doc(f"action def SoundCollisionWarning :> {CONTEXT_FUNCTION_ROOT}")
    code = _code()
    assert f"private import DE4SDV_DriverAssistanceFraming::{PHASE_1_CONCERN};" in code
    concern = _flat(FRAMING.read_text(encoding="utf-8"))
    assert "Answered by the system process of phase 6." in concern


def test_the_modes_name_the_functions_that_depend_on_them():
    """SAF System State: which modes the system has, and which functions depend on them. The dependence is native,
    one dependency per function and mode, and each mode's doc says what the dependent functions do in it."""
    code = _code()
    pairs = set(re.findall(
        rf"\bdependency\s+\w+\s+from\s+{FLOW}::(\w+)\s+to\s+DriverAssistanceModes::(\w+)\s*;", code))
    assert pairs == MODE_DEPENDENCIES
    assert len(re.findall(r"\bdependency\b", code)) == len(MODE_DEPENDENCIES), "no other dependency"
    for function, mode in MODE_DEPENDENCIES:
        assert function in _doc(f"state {mode}"), (function, mode)
    assert "commandVehicle gives no driving command (REQ-DRIVING-044)" in _doc("state identifying")
    assisting = _doc("state assisting")
    assert "requestWarning starts no warning request (REQ-DRIVING-040)" in assisting
    assert "starts no emergency braking (REQ-DRIVING-041)" in assisting
    assert "requestWarning gives the warning request from the start of the imminence" in _doc("state warning")
    braking = _doc("state emergencyBraking")
    assert ("commandVehicle commands a deceleration of at least 5.0 m/s² while the needed deceleration is at least "
            "5.0 m/s² (REQ-DRIVING-036)") in braking


def test_the_system_boundary_carries_typed_functional_ports():
    """SAF System Interface Definition: the system's conceptual interfaces as port definitions with one directed
    item each, typed by a functional item definition of this package that specializes the phase 2 item."""
    code = _code()
    assert re.search(rf"\bpart\s+def\s+{BOUNDARY}\s*:>\s*DriverAssistanceSystem\s*\{{", code)
    specializations = dict(re.findall(r"\bitem\s+def\s+(\w+)\s*:>\s*(\w+)\s*\{", code))
    assert {name: base for name, base in specializations.items()
            if name in BOUNDARY_ITEM_SPECIALIZATIONS} == BOUNDARY_ITEM_SPECIALIZATIONS
    for port, item in BOUNDARY_PORTS.items():
        body = braced_body(code, f"port def {port}")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [item], port
    boundary = braced_body(code, f"part def {BOUNDARY}")
    direct = _direct(boundary)
    assert re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", direct) == list(BOUNDARY_PORT_USAGES.items())
    perform = braced_body(boundary, f"perform {FLOW_USAGE} : {FLOW}")
    assert set(re.findall(r"\b(in|out)\s+item\s+(\w+)\s*=\s*([\w.]+)\s*;", perform)) == BOUNDARY_BINDINGS
    assert not re.search(rf"\bpart\s+\w+\s*:\s*{BOUNDARY}\b", code), "a usage of it would be a second system"
    assert "not a logical element" in _doc(f"part def {BOUNDARY}")
    for typed in ("SCORECommandAndWarningPath", "DriverWarningPresentation"):
        assert f"private import DE4SDV_DriverAssistanceOperationalContext::{typed};" in code, typed
    for typed in ("SubjectVehicle", "Driver"):
        assert f"private import DE4SDV_OperationalContext::{typed};" in code, typed
    assert "private import DE4SDV_DriverAssistanceFraming::DriverAssistanceSystem;" in code


def test_the_package_publishes_exactly_one_view_per_question():
    declared = re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M)
    assert sorted(declared) == sorted(PUBLISHED_VIEWS)
    assert len(declared) == 5


@pytest.mark.parametrize("view_name", sorted(VIEWS), ids=sorted(VIEWS))
def test_each_view_frames_its_concern_and_exposes_its_content(view_name):
    view_type, render, exposes, frames = VIEWS[view_name]
    code = _code()
    header = f"view {view_name}" + (f" : {view_type}" if view_type else "")
    assert re.search(rf"\bview\s+{view_name}\s*" + (rf":\s*{re.escape(view_type)}\s*" if view_type else "") + r"\{",
                     code), header
    view = braced_body(code, header)
    viewpoint = braced_body(view, "viewpoint")
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == frames
    assert re.search(rf"viewpoint\s+\w+\s*:\s*{VIEWPOINTS[frames[0]]}\s*\{{", view), view_name
    assert len(re.findall(r"\bviewpoint\b", view)) == 1
    assert re.findall(r"\bexpose\s+([\w:*]+(?:\[[^\]]*\])?)\s*;", view) == exposes
    if render:
        assert render in view
    else:
        assert "render as" not in view, "the view type selects the kind"


@pytest.mark.parametrize("view_name", sorted(TABLES))
def test_each_table_states_its_rows_and_columns(view_name):
    code = _code()
    filter_, columns = TABLES[view_name]
    view = braced_body(code, f"view {view_name} : TVD::TableView")
    assert filter_ in view
    for label, feature in columns:
        column = braced_body(view, f"view {label} :> columnViews")
        assert f"attribute :>> featureToRender = {feature}" in column, (view_name, label)
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"table-{view_name}"]
    assert metadata.title and metadata.description, view_name


@pytest.mark.parametrize("concern_name", sorted(CATALOGUE_CONCERNS), ids=sorted(CATALOGUE_CONCERNS))
def test_each_phase_6_concern_is_typed_by_the_catalogue_and_held_by_the_party_it_serves(concern_name):
    catalogue, stakeholders = CATALOGUE_CONCERNS[concern_name]
    concern = braced_body(_code(), f"concern {concern_name} : {catalogue}")
    members = re.findall(r"\b(subject|stakeholder)\b", concern)
    assert members and members[0] == "subject"
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == stakeholders
    assert " need " in _doc(f"concern {concern_name} : {catalogue}")


def test_the_package_types_no_vehicle_signal_specification():
    """Owner decision: no vehicle signal specification in phase 6. The typing starts at phase 8, at the port where
    an item enters a software contract; the phase 6 interface items are conceptual."""
    raw = _raw()
    assert "VSS" not in _code(), "no vehicle signal type, import or path in the model code"
    assert "COVESA_VSS" not in raw and "DE4SDV_VSS_Extensions" not in raw
    assert not re.search(r"\bimport\b[^\n]*VSS", raw)
    assert "no vehicle signal specification" in _header().lower()


def test_the_new_elements_name_no_technology_platform_candidate_or_claim():
    declarations = [f"action def {CONTEXT_FUNCTION_ROOT}"]
    declarations += [f"action def {name} :> {CONTEXT_FUNCTION_ROOT}" for name in CONTEXT_FUNCTIONS]
    declarations += [f"action def {PROCESS}", f"part def {BOUNDARY}", "state def DriverAssistanceModes"]
    declarations += [f"state {mode}" for mode in MODES]
    declarations += [f"port def {port}" for port in BOUNDARY_PORTS]
    declarations += [f"item def {item}" for item in BOUNDARY_ITEM_SPECIALIZATIONS]
    declarations += [f"concern {name} : {catalogue}" for name, (catalogue, _) in CATALOGUE_CONCERNS.items()]
    declarations += [f"ref part {name} : {typed} = {bound}" for name, (typed, bound, _) in PARTICIPANTS.items()]
    for declaration in declarations:
        doc = _doc(declaration)
        found = [word for word in FORBIDDEN_IN_FUNCTIONS if re.search(rf"\b{re.escape(word)}", doc, re.I)]
        found += [word for word in TECHNOLOGY_NAMES if re.search(rf"\b{re.escape(word)}\b", doc)]
        assert not found, (declaration, found)


def test_the_guide_has_a_phase_6_section_and_names_phase_7_next():
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.index("## Requirements (Phase 5)") < guide.index("## Functional architecture (Phase 6)") \
        < guide.index("## What the framing already records as open")
    raw_section = guide.split("## Functional architecture (Phase 6)", 1)[1].split("\n## ", 1)[0]
    section = " ".join(raw_section.split())
    assert "](../../textual-notation-of-model/packages/features/driving/driver_assistance_functional_architecture.sysml)" \
        in raw_section
    for name in (*FUNCTIONS, FLOW, PROCESS, "DriverAssistanceModes", BOUNDARY, PHASE_1_CONCERN, *PUBLISHED_VIEWS,
                 "REQ-DRIVING-038", "REQ-DRIVING-043", "REQ-DRIVING-039", "REQ-DRIVING-042",
                 "gapNoSeparateEmergencyFunction"):
        assert f"`{name}`" in section, name
    assert "VisionPilot/" not in raw_section and ".cpp" not in raw_section, "the guide carries no upstream paths"
    assert "tests/test_driver_assistance_functional_architecture.py" in section
    # the guide states the answer to the phase 1 concern with the model's times
    for phrase in ("the warning request at the boundary at least 1.0 s of simulation time before the start of the "
                   "emergency braking (`REQ-DRIVING-042`);",
                   "each mode of the warning within 0.2 s of wall-clock time after the request, the share of the "
                   "S-CORE path and the AAOS SDV, which Phase 8 divides between them;",
                   "so each mode at least 0.8 s before the emergency braking, while the simulation runs no faster "
                   "than wall-clock time, which is the obligation of System 2.",
                   "Rejecting what it detects is the share of the product that holds the path (`REQ-MW-006`), "
                   "which Phase 8 allocates."):
        assert phrase in section, phrase
    flat = " ".join(guide.split())
    assert ("**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 classification, "
            "Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture, Phase 7 logical "
            "architecture and Phase 8 physical and software realization, proposal.**") in flat
    assert ("The next model obligation is **Phase 9**: variability and configuration, which makes the realization a "
            "configured product of the product line; its first gate is `incrementHasConfiguredProduct`.") in flat
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert "tests/test_driver_assistance_functional_architecture.py" in check
