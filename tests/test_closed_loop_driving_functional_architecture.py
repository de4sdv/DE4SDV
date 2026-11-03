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
- two views of the SAF System Functional Breakdown Structure viewpoint: the breakdown tree and the
  requirement-function matrix, which also answers the degraded-input concern of phase 1;
- no technology, platform or safety claim in the functions.
"""

from pathlib import Path
import re

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

#: Words that would name a technology, a platform or a claim inside a function.
FORBIDDEN_IN_FUNCTIONS = ("CARLA", "ROS", "DDS", "Zenoh", "SOME/IP", "GPU", "Python", "PyTorch", "Linux",
                          "Android", "S-CORE", "safe", "certif", "complian", "homolog")


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
    assert dict(functions) == {name: "AllocatableFunction" for name in FUNCTIONS.values()}
    assert code.count("private import DE4SDV_TraceVocabulary::AllocatableFunction;") == 1
    assert re.search(rf"\baction\s+def\s+{FLOW}\s*\{{", code), "the flow is a composite, not a function"
    assert set(re.findall(r"\bitem\s+def\s+(\w+)", code)) == INTERNAL_ITEMS
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
    assert not re.search(r"\bin\s+\w+\s*:\s*DrivingOperationalState\b", code), "no function takes the published state"
    assert "never waits for a receiver" in _doc("action def PublishOperationalState :> AllocatableFunction")


def test_the_modes_are_those_the_health_of_the_driving_system_names():
    code = _code()
    machine = braced_body(code, "state def ClosedLoopDrivingModes")
    assert re.findall(r"\bstate\s+(\w+)\s*;", machine) == MODES
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


def test_the_breakdown_tree_shows_the_seven_functions():
    view = braced_body(_code(), f"view {TREE_VIEW}")
    viewpoint = braced_body(view, "viewpoint")
    assert re.search(r"viewpoint\s+\w+\s*:\s*SystemFunctionalBreakdownStructureViewpoint\s*\{", view)
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == [CONCERN]
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", view) == [FLOW] + [f"{FLOW}::{f}" for f in FUNCTIONS]
    assert "render asTreeDiagram;" in view


def test_the_matrix_maps_every_requirement_to_its_functions_and_answers_the_degraded_input_concern():
    code = _code()
    assert f"private import DE4SDV_ClosedLoopDrivingFraming::{PHASE_1_CONCERN};" in code
    view = braced_body(code, f"view {MATRIX_VIEW} : MVD::MatrixView")
    viewpoint = braced_body(view, "viewpoint")
    assert re.search(r"viewpoint\s+\w+\s*:\s*SystemFunctionalBreakdownStructureViewpoint\s*\{", view)
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
        assert not found, (declaration, found)


def test_the_matrix_render_has_a_title_and_its_axes_named():
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"matrix-{MATRIX_VIEW}"]
    assert metadata.row_label == "requirements (requirement usages)"
    assert metadata.column_label == "system functions (action usages)"
