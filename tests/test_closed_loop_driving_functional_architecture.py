"""Content pins for the closed-loop driving functional architecture (phase 6), not semantic validation.

INC-DRIVING-001 phase 6 breaks the driving system into its functions and allocates each requirement of
phase 5 to the functions that carry it. Method Check holds the DefineFunctionalArchitecture rules (at least
one function; each functional requirement allocated to a function by a native allocation). These pins hold
what review settled on top of them:

- seven functions, each an AllocatableFunction, and the functional flow that breaks the driving system into
  them, with the items they exchange: the inputs and outputs of phase 2 at the boundary, and inside, the
  checkpoint inputs, the input condition, the plan, the mode and the run record;
- one command path: the stop response is a mode of the one function that commands the vehicle, not a second
  command source, and the actuation applies the stop response itself when commands stop arriving;
- observation one way: nothing the publication of the operational state gives flows back into the loop;
- the modes that the health of the driving system names, priming, driving and stopped, with no way out of
  stopped;
- the allocation of every requirement but REQ-DRIVING-014, which constrains the exchanges and is carried in
  phase 8;
- the breakdown tree of the SAF System Functional Breakdown Structure viewpoint and the requirement-function
  matrix of the System Requirement Traceability viewpoint, which also answers the degraded-input concern of
  phase 1;
- the functions the context elements perform in the loop, as functions of their own root, outside the
  system's scope, and the system process that runs the system as one action between them, with the items
  that cross the boundary. Its participants are the context parts of phase 2 themselves, bound by
  reference: the process declares no part of its own, so the increment has one context;
- the modes and the functions that depend on them, the system's functional interfaces as port definitions
  with directed items typed by functional item definitions of this package, and one view per SAF question:
  the process as an action flow, the modes as a table, the boundary as an interconnection, each framed by a
  phase 6 concern typed by that catalogue. The package publishes exactly five views;
- no technology, platform or safety claim in the functions, and no vehicle signal specification in the
  package.
"""

from pathlib import Path
import re

import pytest

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
MODEL = DRIVING / "closed_loop_driving_functional_architecture.sysml"
NEEDS_REQUIREMENTS = DRIVING / "closed_loop_driving_needs_requirements.sysml"
FRAMING = DRIVING / "closed_loop_driving_framing.sysml"
PACKAGE = "DE4SDV_ClosedLoopDrivingFunctionalArchitecture"
FLOW = "ClosedLoopDrivingFunctionalFlow"
FLOW_USAGE = "closedLoopDrivingFunctionalFlow"
CONCERN = "closedLoopDrivingFunctionsConcern"
PHASE_1_CONCERN = "degradedInputBehaviorConcern"
TREE_VIEW = "closedLoopDrivingFunctionBreakdownView"
MATRIX_VIEW = "closedLoopDrivingRequirementFunctionMappingView"

#: Each function of the flow, in breakdown order -> its definition.
FUNCTIONS = {
    "identifyRun": "IdentifyRun",
    "assembleInputs": "AssembleCheckpointInputs",
    "planTrajectory": "PlanTrajectory",
    "superviseLoop": "SuperviseDrivingLoop",
    "commandVehicle": "CommandVehicle",
    "applyCommands": "ApplyCommandsAtActuation",
    "publishState": "PublishOperationalState",
}

#: The items the functions exchange inside the driving system; the boundary items are phase 2's.
INTERNAL_ITEMS = {"CheckpointInputs", "InputCondition", "DrivingPlan", "DrivingMode", "RunRecord"}
PHASE_2_ITEMS = ("CameraImages", "EgoMotionState", "Route", "VehicleMotionCommand", "DrivingOperationalState")

#: The flow's own parameters: the phase 2 items crossing the boundary of the driving system.
FLOW_PARAMETERS = [
    ("in", "cameraImages", "CameraImages"),
    ("in", "egoMotion", "EgoMotionState"),
    ("in", "route", "Route"),
    ("out", "vehicleCommand", "VehicleMotionCommand"),
    ("out", "operationalState", "DrivingOperationalState"),
]

#: Item flows between the functions (source, target).
FLOWS = {
    ("assembleInputs.checkpointInputs", "planTrajectory.checkpointInputs"),
    ("identifyRun.runRecord", "planTrajectory.runRecord"),
    ("assembleInputs.inputCondition", "superviseLoop.inputCondition"),
    ("planTrajectory.plan", "superviseLoop.plan"),
    ("superviseLoop.validPlan", "commandVehicle.validPlan"),
    ("superviseLoop.mode", "commandVehicle.mode"),
    ("commandVehicle.command", "applyCommands.command"),
    ("planTrajectory.plan", "publishState.plan"),
    ("superviseLoop.mode", "publishState.mode"),
}

#: Function parameters bound to the flow's own parameters: (function, direction, parameter, flow parameter).
BINDINGS = {
    ("assembleInputs", "in", "cameraImages", "cameraImages"),
    ("assembleInputs", "in", "egoMotion", "egoMotion"),
    ("assembleInputs", "in", "route", "route"),
    ("commandVehicle", "in", "currentMotion", "egoMotion"),
    ("publishState", "in", "motion", "egoMotion"),
    ("applyCommands", "out", "actuatedCommand", "vehicleCommand"),
    ("publishState", "out", "operationalState", "operationalState"),
}

#: Each requirement of phase 5 -> the functions it is allocated to.
ALLOCATED = {
    "reqPlanEachStep": {"planTrajectory"},
    "reqPlansByCheckpointInference": {"planTrajectory"},
    "reqCameraImagesInCheckpointForm": {"assembleInputs"},
    "reqCameraHistory": {"assembleInputs"},
    "reqProjectionOperators": {"assembleInputs"},
    "reqMapContextRaster": {"assembleInputs"},
    "reqRouteMaskRaster": {"assembleInputs"},
    "reqEgoMotionHistory": {"assembleInputs"},
    "reqHoldUntilHistoriesComplete": {"commandVehicle"},
    "reqHistoriesFromCapturedInputs": {"assembleInputs"},
    "reqCommandsFromNewestValidPlan": {"commandVehicle"},
    "reqCommandsWithinActuationLimits": {"commandVehicle"},
    "reqPlanWithinPlanningPeriod": {"planTrajectory"},
    "reqPublishPlans": {"publishState"},
    "reqPublishVehicleState": {"publishState"},
    "reqPublishHealthPeriodically": {"publishState"},
    "reqPlansIndependentOfObservation": {"publishState"},
    "reqPlanningTimeIndependentOfObservation": {"publishState"},
    "reqStopResponseDeceleration": {"commandVehicle"},
    "reqStopResponseSteeringHeld": {"commandVehicle"},
    "reqStandstillAfterStop": {"commandVehicle"},
    "reqStopOnDegradedCameraImages": {"superviseLoop"},
    "reqStopOnDegradedMotion": {"superviseLoop"},
    "reqStopOnDegradedRoute": {"superviseLoop"},
    "reqStopOnStalePlan": {"superviseLoop"},
    "reqStopOnInvalidPlan": {"superviseLoop"},
    "reqStopOnLostCommands": {"applyCommands"},
    "reqPublishStop": {"publishState"},
    "reqStampInputs": {"assembleInputs"},
    "reqStampPlans": {"planTrajectory"},
    "reqStampCommands": {"commandVehicle", "applyCommands"},
    "reqRecordRunIdentity": {"identifyRun"},
    "reqPlansNameRunRecord": {"planTrajectory"},
    "reqRefuseUnpinnedCheckpoint": {"identifyRun"},
}
#: REQ-DRIVING-014 constrains the exchanges of the plan and the commands, not a function: phase 8 carries it.
EXCHANGE_CONSTRAINT = "reqPlansAndCommandsOverSCORE"

MODES = ["priming", "driving", "stopped"]
TRANSITIONS = {("priming", "driving"), ("priming", "stopped"), ("driving", "stopped")}

#: The root of the functions the context elements perform, outside the system's functional scope. Not an
#: AllocatableFunction: the increment's functions are the AllocatableFunction actions, and no context
#: function carries a requirement of phase 5.
CONTEXT_FUNCTION_ROOT = "ContextElementFunction"

#: Each context function -> its one parameter (direction, name, item type), taken from phase 2.
CONTEXT_FUNCTIONS = {
    "GiveRoute": ("out", "route", "Route"),
    "CaptureCameraImages": ("out", "cameraImages", "CameraImages"),
    "SampleEgoMotion": ("out", "egoMotion", "EgoMotionState"),
    "ApplyMotionCommands": ("in", "command", "VehicleMotionCommand"),
    "PresentDrivingState": ("in", "operationalState", "DrivingOperationalState"),
}

PROCESS = "ClosedLoopDrivingSystemProcess"
PROCESS_USAGE = "closedLoopDrivingSystemProcess"

#: The one operational context of the increment (phase 2), whose parts the process binds its participants to.
CONTEXT_USAGE = "closedLoopDrivingOperationalContext"

#: Each participant of the process, in loop order -> its phase 2 type, the phase 2 context part it is bound
#: to by reference (the process declares no part of its own) and the actions it owns and performs, each a
#: context function of this package (name -> definition). The participant is the swim lane of its function.
PARTICIPANTS = {
    "navigation": ("NavigationSystem", f"{CONTEXT_USAGE}::navigation", {"giveRoute": "GiveRoute"}),
    "vehicle": ("SubjectVehicle", f"{CONTEXT_USAGE}::vehicle",
                {"captureImages": "CaptureCameraImages", "sampleEgoMotion": "SampleEgoMotion",
                 "applyCommands": "ApplyMotionCommands"}),
    "drivingSystem": ("ClosedLoopDrivingSystem", f"{CONTEXT_USAGE}::drivingSystem", {}),
    "stateObserver": ("DrivingStateObserverApplication", f"{CONTEXT_USAGE}::aaosSDVGuest::stateObserver",
                      {"presentState": "PresentDrivingState"}),
}

#: The items that cross the boundary of the system inside the process (source, target), each end chained
#: through the participant that owns the action: the exchange says who gives and who takes.
PROCESS_FLOWS = {
    ("navigation.giveRoute.route", f"drivingSystem.{FLOW_USAGE}.route"),
    ("vehicle.captureImages.cameraImages", f"drivingSystem.{FLOW_USAGE}.cameraImages"),
    ("vehicle.sampleEgoMotion.egoMotion", f"drivingSystem.{FLOW_USAGE}.egoMotion"),
    (f"drivingSystem.{FLOW_USAGE}.vehicleCommand", "vehicle.applyCommands.command"),
    (f"drivingSystem.{FLOW_USAGE}.operationalState", "stateObserver.presentState.operationalState"),
}

#: The functions whose behavior differs by mode (function usage, mode).
MODE_DEPENDENCIES = {
    ("commandVehicle", "priming"),
    ("commandVehicle", "driving"),
    ("commandVehicle", "stopped"),
    ("publishState", "stopped"),
}

#: The functional item definitions of the boundary, each specializing its phase 2 item.
BOUNDARY_ITEM_SPECIALIZATIONS = {
    "CameraImageInput": "CameraImages",
    "EgoMotionInput": "EgoMotionState",
    "RouteInput": "Route",
    "VehicleCommandOutput": "VehicleMotionCommand",
    "OperationalStateOutput": "DrivingOperationalState",
}

#: Each port definition of the boundary -> its one directed item (direction, name, item definition).
BOUNDARY_PORTS = {
    "CameraImagesInbound": ("in", "cameraImages", "CameraImageInput"),
    "EgoMotionInbound": ("in", "egoMotion", "EgoMotionInput"),
    "RouteInbound": ("in", "route", "RouteInput"),
    "VehicleCommandOutbound": ("out", "vehicleCommand", "VehicleCommandOutput"),
    "OperationalStateOutbound": ("out", "operationalState", "OperationalStateOutput"),
}

BOUNDARY = "ClosedLoopDrivingFunctionalBoundary"

#: Each port usage of the boundary part -> its port definition.
BOUNDARY_PORT_USAGES = {
    "cameraImagesIn": "CameraImagesInbound",
    "egoMotionIn": "EgoMotionInbound",
    "routeIn": "RouteInbound",
    "vehicleCommandOut": "VehicleCommandOutbound",
    "operationalStateOut": "OperationalStateOutbound",
}

#: How the boundary binds the flow's parameters to the port payloads (direction, parameter, binding).
BOUNDARY_BINDINGS = {
    ("in", "cameraImages", "cameraImagesIn.cameraImages"),
    ("in", "egoMotion", "egoMotionIn.egoMotion"),
    ("in", "route", "routeIn.route"),
    ("out", "vehicleCommand", "vehicleCommandOut.vehicleCommand"),
    ("out", "operationalState", "operationalStateOut.operationalState"),
}

PROCESS_CONCERN = "closedLoopDrivingProcessConcern"
STATE_CONCERN = "closedLoopDrivingModeDependenceConcern"
INTERFACE_CONCERN = "closedLoopDrivingInterfaceConcern"

#: The Phase 6 concerns and the catalogue concern definition each is typed by.
CATALOGUE_CONCERNS = {
    PROCESS_CONCERN: ("SystemProcessConcern", {"SystemArchitect", "SystemsEngineer"}),
    STATE_CONCERN: ("SystemStateConcern", {"SystemArchitect", "SoftwareDeveloper"}),
    INTERFACE_CONCERN: ("FunctionalInterfaceConcern", {"SystemsEngineer", "SoftwareDeveloper"}),
}

#: One view per SAF question beyond the breakdown and the matrix: name -> (type or "", render statement,
#: exposures, framed concerns). The process is an action flow with its members exposed (SysIDE draws only
#: exposed elements as nodes), the modes a table, the interfaces the tree of the five port definitions with
#: their items (SysIDE's interconnection kind draws usages wired through ports; the boundary definition
#: alone drew nothing, licensed runs 41920933909 and 41923136300). The render forms the owner compared on
#: 2026-11-04 left the model.
VIEWS = {
    "closedLoopDrivingSystemProcessView": (
        "ActionFlowView", "",
        [f"{PROCESS}::*"] + [f"{PROCESS}::{participant}::*" for participant in PARTICIPANTS],
        [PROCESS_CONCERN]),
    "closedLoopDrivingModeDependenceTableView": (
        "TVD::TableView", "",
        ["ClosedLoopDrivingModes::priming", "ClosedLoopDrivingModes::driving", "ClosedLoopDrivingModes::stopped"],
        [STATE_CONCERN, PHASE_1_CONCERN]),
    "closedLoopDrivingFunctionalInterfaceView": (
        "", "render asTreeDiagram;", [port for port in sorted(BOUNDARY_PORTS)], [INTERFACE_CONCERN]),
}
#: The one table, with the row population and the columns it renders.
TABLES = {
    "closedLoopDrivingModeDependenceTableView": ("filter @ SysML::StateUsage;",
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

#: Words that would name a technology, a platform or a claim inside a function.
FORBIDDEN_IN_FUNCTIONS = ("CARLA", "ROS", "DDS", "Zenoh", "SOME/IP", "GPU", "Python", "PyTorch", "Linux",
                          "Android", "S-CORE", "VSS", "safe", "certif", "complian", "homolog")

TECHNOLOGY_NAMES = ("CAN", "LIN", "FlexRay", "Ethernet", "gRPC", "KUKSA", "AUTOSAR", "AAOS", "Autoware")


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


def _flow_body() -> str:
    return braced_body(_code(), f"action def {FLOW}")


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


def test_the_charter_names_the_package_after_the_needs_and_requirements():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part closedLoopDrivingCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1))[-2:] == [
        "DE4SDV_ClosedLoopDrivingNeedsRequirements", PACKAGE]
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", _code())


def test_the_seven_functions_are_allocatable_functions_and_nothing_else_is():
    code = _code()
    functions = re.findall(r"\baction\s+def\s+(\w+)\s*:>\s*([^{;]+?)\s*\{", code)
    assert {name: typed for name, typed in functions if typed == "AllocatableFunction"} == {
        name: "AllocatableFunction" for name in FUNCTIONS.values()}
    assert {name: typed for name, typed in functions if typed != "AllocatableFunction"} == {
        name: CONTEXT_FUNCTION_ROOT for name in CONTEXT_FUNCTIONS}
    assert code.count("private import DE4SDV_TraceVocabulary::AllocatableFunction;") == 1
    assert re.search(rf"\baction\s+def\s+{FLOW}\s*\{{", code), "the flow is a composite, not a function"
    assert set(re.findall(r"\bitem\s+def\s+(\w+)", code)) == INTERNAL_ITEMS | set(BOUNDARY_ITEM_SPECIALIZATIONS)
    for item in PHASE_2_ITEMS:
        assert f"private import DE4SDV_ClosedLoopDrivingOperationalContext::{item};" in code, item
    assert re.search(rf"\baction\s+{FLOW_USAGE}\s*:\s*{FLOW}\s*;", code)


def test_the_flow_breaks_the_driving_system_into_the_seven_functions():
    body = _flow_body()
    direct = _direct(body)
    assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", direct) == FLOW_PARAMETERS
    assert dict(re.findall(r"\baction\s+(\w+)\s*:\s*(\w+)\s*\{", direct)) == FUNCTIONS
    assert list(dict(re.findall(r"\baction\s+(\w+)\s*:\s*(\w+)\s*\{", direct))) == list(FUNCTIONS), \
        "the breakdown keeps the order of one step"


def test_the_functions_exchange_exactly_these_items():
    body = _flow_body()
    assert set(re.findall(r"\bflow\s+from\s+([\w.]+)\s+to\s+([\w.]+)\s*;", body)) == FLOWS
    bound = set()
    for function in FUNCTIONS:
        usage = braced_body(body, f"action {function} : {FUNCTIONS[function]}")
        for direction, parameter, outer in re.findall(rf"\b(in|out)\s+(\w+)\s*=\s*{FLOW}::(\w+)\s*;", usage):
            bound.add((function, direction, parameter, outer))
    assert bound == BINDINGS


def test_one_command_path_whose_stop_response_is_a_mode_and_an_actuation_that_stops_on_its_own():
    code = _code()
    producers = {name for name, body in re.findall(r"\baction\s+def\s+(\w+)\s*:>\s*AllocatableFunction\s*\{([^}]*)\}",
                                                    code) if re.search(r"\bout\s+\w+\s*:\s*VehicleMotionCommand\b", body)}
    assert producers == {"CommandVehicle", "ApplyCommandsAtActuation"}
    into_actuation = {source for source, target in FLOWS if target.startswith("applyCommands.")}
    assert into_actuation == {"commandVehicle.command"}, "no second command source reaches the actuation"
    assert "while stopped, the stop response" in _doc("action def CommandVehicle :> AllocatableFunction")
    assert "applies the stop response there itself" in _doc(
        "action def ApplyCommandsAtActuation :> AllocatableFunction")
    for stop in ("reqStopResponseDeceleration", "reqStopResponseSteeringHeld", "reqStandstillAfterStop"):
        assert _allocations()[stop] == {"commandVehicle"}, stop


def test_observation_is_one_way():
    code = _code()
    assert not [flow for flow in FLOWS if flow[0].startswith("publishState.")]
    assert not re.search(r"\bflow\s+from\s+publishState\.", code)
    functions = [body for body in re.findall(r"action def \w+ :> AllocatableFunction \{[^}]*\}", code)]
    assert not any(re.search(r"\bin\s+\w+\s*:\s*DrivingOperationalState\b", body) for body in functions), \
        "no function of the driving system takes the published state"
    assert not [flow for flow in PROCESS_FLOWS if "presentState" in flow[0]], \
        "the state observer gives nothing back into the process"
    assert "never waits for a receiver" in _doc("action def PublishOperationalState :> AllocatableFunction")


def test_the_modes_are_those_the_health_of_the_driving_system_names():
    code = _code()
    machine = braced_body(code, "state def ClosedLoopDrivingModes")
    assert re.findall(r"\bstate\s+(\w+)\s*[;{]", machine) == MODES
    assert set(re.findall(r"\btransition\s+first\s+(\w+)\s+then\s+(\w+)\s*;", machine)) == TRANSITIONS
    assert len(re.findall(r"\btransition\b", machine)) == len(TRANSITIONS)
    terms = _flat(NEEDS_REQUIREMENTS.read_text(encoding="utf-8"))
    assert "Health: the mode of the driving system (priming, driving or stopped)" in terms
    assert "with no transition out" in _doc("state def ClosedLoopDrivingModes")
    assert "SuperviseDrivingLoop" in _doc("state def ClosedLoopDrivingModes")


def test_each_requirement_is_allocated_to_the_functions_decided():
    assert _allocations() == ALLOCATED


def test_every_functional_requirement_is_allocated_and_every_function_carries_one():
    requirements = _requirements()
    assert len(requirements) == 35
    allocated = _allocations()
    functional = [name for name, kind in requirements if kind == "FunctionalRequirementCandidate"]
    assert len(functional) == 23 and all(name in allocated for name in functional)
    assert {name for name, _ in requirements} - set(allocated) == {EXCHANGE_CONSTRAINT}
    assert set(allocated) <= {name for name, _ in requirements}
    assert set().union(*allocated.values()) == set(FUNCTIONS)


def test_the_s_core_constraint_is_left_to_the_exchanges_of_phase_8():
    header = _flat(_raw().split(f"package {PACKAGE}", 1)[0])
    assert "REQ-DRIVING-014" in header and "phase 8" in header
    assert EXCHANGE_CONSTRAINT not in _allocations()


def test_the_concern_is_held_by_those_who_build_on_the_functions():
    concern = braced_body(_code(), f"concern {CONCERN} : FunctionalBehaviorConcern")
    members = [m for m in re.findall(r"\b(subject|stakeholder)\b", concern)]
    assert members and members[0] == "subject"
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == {"SystemArchitect",
                                                                                  "VerificationEngineer"}
    assert _doc(f"concern {CONCERN} : FunctionalBehaviorConcern").startswith(
        "System architects and verification engineers need")


def test_the_breakdown_view_shows_the_flow_with_its_seven_functions():
    """The view exposes the flow usage only, as AEBS-010's rendered function view does: its compartments list
    the items and the seven functions. Exposing the functions themselves (`Flow::fn`), the allocation targets,
    made SysIDE draw all 35 allocations of this package as unconnected nodes (licensed run 41737744809)."""
    view = braced_body(_code(), f"view {TREE_VIEW}")
    viewpoint = braced_body(view, "viewpoint")
    assert re.search(r"viewpoint\s+\w+\s*:\s*SystemFunctionalBreakdownStructureViewpoint\s*\{", view)
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == [CONCERN]
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", view) == [FLOW_USAGE]
    assert "render asTreeDiagram;" in view


def test_the_matrix_maps_every_requirement_to_its_functions_and_answers_the_degraded_input_concern():
    code = _code()
    assert f"private import DE4SDV_ClosedLoopDrivingFraming::{PHASE_1_CONCERN};" in code
    view = braced_body(code, f"view {MATRIX_VIEW} : MVD::MatrixView")
    viewpoint = braced_body(view, "viewpoint")
    # SAF System Requirement Traceability asks which system function a requirement addresses; the breakdown
    # viewpoint asks which functions there are, which the tree answers
    assert re.search(r"viewpoint\s+\w+\s*:\s*SystemRequirementTraceabilityViewpoint\s*\{", view)
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == [CONCERN, PHASE_1_CONCERN]
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


def test_the_functions_name_no_technology_platform_or_claim():
    declarations = [f"action def {d} :> AllocatableFunction" for d in FUNCTIONS.values()]
    declarations += [f"action def {FLOW}"] + [f"item def {item}" for item in sorted(INTERNAL_ITEMS)]
    for declaration in declarations:
        doc = _doc(declaration)
        found = [word for word in FORBIDDEN_IN_FUNCTIONS if re.search(rf"\b{re.escape(word)}", doc, re.I)]
        # buses, brokers and platforms, matched by case so that the word "can" is no bus
        found += [word for word in TECHNOLOGY_NAMES if re.search(rf"\b{re.escape(word)}\b", doc)]
        assert not found, (declaration, found)


def test_the_matrix_render_has_a_title_and_its_axes_named():
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"matrix-{MATRIX_VIEW}"]
    assert metadata.row_label == "requirements (requirement usages)"
    assert metadata.column_label == "system functions (action usages)"


def _process_body() -> str:
    return braced_body(_code(), f"action def {PROCESS}")


def test_the_context_elements_perform_the_loop_functions_outside_the_system_scope():
    """The context elements act: navigation gives the route, the vehicle's cameras and motion sensing give
    the images and the ego motion, its actuation applies the commands, and the state observer presents the
    published state. Those functions are not the system's: they are typed by their own root, not by
    AllocatableFunction, so Method Check keeps counting the seven functions as the increment's."""
    code = _code()
    assert re.search(rf"\baction\s+def\s+{CONTEXT_FUNCTION_ROOT}\s*\{{", code), "the context functions need a root"
    declared = dict(re.findall(r"\baction\s+def\s+(\w+)\s*:>\s*(\w+)\s*\{", code))
    assert {name: base for name, base in declared.items() if base == CONTEXT_FUNCTION_ROOT} == {
        name: CONTEXT_FUNCTION_ROOT for name in CONTEXT_FUNCTIONS}
    assert not re.search(rf"\baction\s+def\s+{CONTEXT_FUNCTION_ROOT}\s*:>", code), "the root specializes nothing"
    for name, parameter in CONTEXT_FUNCTIONS.items():
        body = _direct(braced_body(code, f"action def {name} :> {CONTEXT_FUNCTION_ROOT}"))
        assert re.findall(r"\b(in|out)\s+(\w+)\s*:\s*(\w+)\s*;", body) == [parameter], name
    assert "outside the scope of the driving system" in _doc(f"action def {CONTEXT_FUNCTION_ROOT}")


def test_the_process_binds_its_participants_to_the_context_parts_of_phase_2():
    """SAF System Process: one activity whose participants are the context parts of phase 2 and the system
    of interest, bound by reference as the story's actors are, so the increment keeps one context and the
    process declares no part of its own. Each participant owns and performs its functions of the loop, as
    the swim lane of its function; the system's step is the one functional flow usage the boundary
    performs, so the system's functional scope is one action of the process; the exchanges across the
    boundary are the process's item flows, chained through the participants, and no allocation leaves the
    requirement-to-function pairs of this package."""
    code = _code()
    body = _process_body()
    direct = _direct(body)
    assert re.findall(r"\bref\s+part\s+(\w+)\s*:\s*(\w+)\s*=\s*([\w:]+)\s*\{", direct) == [
        (name, typed, bound) for name, (typed, bound, _) in PARTICIPANTS.items()]
    assert not re.search(r"(?<!ref )\bpart\s+\w+", direct), "the process declares no part of its own"
    assert f"private import DE4SDV_ClosedLoopDrivingOperationalContext::{CONTEXT_USAGE};" in code
    assert not re.search(r"\b(action|perform|first)\b", direct), \
        "the process owns no action of its own: each participant performs its function in its own body"
    for name, (typed, bound, functions) in PARTICIPANTS.items():
        part = braced_body(body, f"ref part {name} : {typed} = {bound}")
        assert re.findall(r"\bperform\s+action\s+(\w+)\s*:\s*(\w+)\s*;", part) == list(functions.items()), name
        if name == "drivingSystem":
            assert re.findall(r"\bperform\s+(\w+)\s*;", part) == [FLOW_USAGE], \
                "the system's step is the flow usage the boundary performs, not a second usage of the flow"
        else:
            assert not re.search(r"\bperform\s+\w+\s*;", part), name
    performed = {definition for _, (_, _, functions) in PARTICIPANTS.items() for definition in functions.values()}
    assert performed == set(CONTEXT_FUNCTIONS), "every context function is performed by one participant"
    assert set(re.findall(r"\bflow\s+from\s+([\w.]+)\s+to\s+([\w.]+)\s*;", body)) == PROCESS_FLOWS
    assert len(re.findall(r"\bflow\s+from\b", body)) == len(PROCESS_FLOWS)
    assert re.search(rf"\baction\s+{PROCESS_USAGE}\s*:\s*{PROCESS}\s*;", code)
    assert "allocate" not in body, "the process assigns no responsibility"
    doc = _doc(f"action def {PROCESS}")
    assert "the context parts of phase 2 themselves" in doc and "declares no part of its own" in doc
    assert "navigation gives the route" in doc and "outside the scope of the driving system" in doc
    assert "nothing the observation gives flows back" in doc


def test_the_modes_name_the_functions_that_depend_on_them():
    """SAF System State: which modes the system has, and which functions depend on them. The dependence is
    native, one dependency per function and mode, and each mode's doc says what the dependent functions do
    in it. Stopped is the degraded-input response the phase 1 concern asks about."""
    code = _code()
    pairs = set(re.findall(
        rf"\bdependency\s+\w+\s+from\s+{FLOW}::(\w+)\s+to\s+ClosedLoopDrivingModes::(\w+)\s*;", code))
    assert pairs == MODE_DEPENDENCIES
    assert len(re.findall(r"\bdependency\b", code)) == len(MODE_DEPENDENCIES), "no other dependency"
    mode_takers = set()
    for name, function in FUNCTIONS.items():
        if re.search(r"\bin\s+mode\s*:\s*DrivingMode\s*;",
                     braced_body(code, f"action def {function} :> AllocatableFunction")):
            mode_takers.add(name)
    assert mode_takers == {"commandVehicle", "publishState"}
    assert "CommandVehicle holds the vehicle at standstill" in _doc("state priming")
    assert "CommandVehicle commands from the newest valid plan" in _doc("state driving")
    stopped = _doc("state stopped")
    assert "CommandVehicle computes the stop response" in stopped
    assert "PublishOperationalState publishes the stop with its cause" in stopped


def test_the_system_boundary_carries_typed_functional_ports():
    """SAF System Interface Definition: the system's conceptual interfaces as port definitions with one
    directed item each, typed by a functional item definition of this package that specializes the phase 2
    item, on one functional chain. No logical element owns them."""
    code = _code()
    # the boundary is the driving system itself at its interfaces, not a second system
    assert re.search(rf"\bpart\s+def\s+{BOUNDARY}\s*:>\s*ClosedLoopDrivingSystem\s*\{{", code)
    specializations = dict(re.findall(r"\bitem\s+def\s+(\w+)\s*:>\s*(\w+)\s*\{", code))
    assert {name: base for name, base in specializations.items()
            if name in BOUNDARY_ITEM_SPECIALIZATIONS} == BOUNDARY_ITEM_SPECIALIZATIONS
    for port, item in BOUNDARY_PORTS.items():
        body = braced_body(code, f"port def {port}")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [item], port
    boundary = braced_body(code, f"part def {BOUNDARY}")
    direct = _direct(boundary)
    assert re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", direct) == list(BOUNDARY_PORT_USAGES.items())
    perform = braced_body(boundary, f"perform closedLoopDrivingFunctionalFlow : {FLOW}")
    assert set(re.findall(r"\b(in|out)\s+item\s+(\w+)\s*=\s*([\w.]+)\s*;", perform)) == BOUNDARY_BINDINGS
    # the boundary is a definition of the system of interest; a usage of it would be a second system
    assert not re.search(rf"\bpart\s+\w+\s*:\s*{BOUNDARY}\b", code)
    assert "not a logical element" in _doc(f"part def {BOUNDARY}")
    for typed in ("NavigationSystem", "DrivingStateObserverApplication"):
        assert f"private import DE4SDV_ClosedLoopDrivingOperationalContext::{typed};" in code, typed
    assert "private import DE4SDV_OperationalContext::SubjectVehicle;" in code
    assert "private import DE4SDV_ClosedLoopDrivingFraming::ClosedLoopDrivingSystem;" in code
    for name, (base, _, _) in PARTICIPANTS.items():
        assert re.search(rf"\bref\s+part\s+{name}\s*:\s*{base}\b", _process_body()), name


def test_the_package_publishes_exactly_one_view_per_question():
    """Five views: the breakdown tree, the requirement matrix, the process, the modes and the boundary. A
    second form of the same elements is bloat, not a view (review of 2026-11-04)."""
    declared = re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M)
    assert sorted(declared) == sorted(PUBLISHED_VIEWS)
    assert len(declared) == 5


@pytest.mark.parametrize("view_name", sorted(VIEWS), ids=sorted(VIEWS))
def test_each_view_frames_its_concern_and_exposes_its_content(view_name):
    """Each view frames a phase 6 concern from its catalogue type's viewpoint and exposes exactly the content
    of its question. The process exposes its members too: SysIDE draws only exposed elements as nodes, and
    a view typed by a standard view definition carries no render statement (the type selects the kind)."""
    view_type, render, exposes, frames = VIEWS[view_name]
    code = _code()
    header = f"view {view_name}" + (f" : {view_type}" if view_type else "")
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
    assert "need" in _doc(f"concern {concern_name} : {catalogue}")


def test_the_package_types_no_vehicle_signal_specification():
    """Owner decision: no vehicle signal specification in phase 6. The typing starts at phase 8, at the port
    where an item enters a software contract; the phase 6 interface items are conceptual."""
    raw = _raw()
    code = _code()
    assert "VSS" not in code, "no vehicle signal type, import or path in the model code"
    assert "COVESA_VSS" not in raw and "DE4SDV_VSS_Extensions" not in raw
    assert not re.search(r"\bimport\b[^\n]*VSS", raw)
    assert "no vehicle signal specification" in _flat(raw.split(f"package {PACKAGE}", 1)[0]).lower()


def test_the_new_elements_name_no_technology_platform_or_claim():
    declarations = [f"action def {name} :> {CONTEXT_FUNCTION_ROOT}" for name in CONTEXT_FUNCTIONS]
    declarations += [f"action def {PROCESS}", f"part def {BOUNDARY}"]
    declarations += [f"port def {port}" for port in BOUNDARY_PORTS]
    declarations += [f"item def {item}" for item in BOUNDARY_ITEM_SPECIALIZATIONS]
    declarations += [f"concern {name} : {catalogue}" for name, (catalogue, _) in CATALOGUE_CONCERNS.items()]
    for declaration in declarations:
        doc = _doc(declaration)
        found = [word for word in FORBIDDEN_IN_FUNCTIONS if re.search(rf"\b{re.escape(word)}", doc, re.I)]
        # buses, brokers and platforms, matched by case so that the word "can" is no bus
        found += [word for word in TECHNOLOGY_NAMES if re.search(rf"\b{re.escape(word)}\b", doc)]
        assert not found, (declaration, found)
