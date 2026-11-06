"""Content pins for the closed-loop driving logical architecture (phase 7), not semantic validation.

INC-DRIVING-001 phase 7 gives the driving system an inside: the technology-independent logical elements that
realize the seven functions of phase 6, one level below the functional boundary. Method Check holds the
DefineLogicalArchitecture rule (each function allocated to a logical element by a native allocation; advisory,
each logical element carries a function). These pins hold what review settled on top of it:

- the decomposition subject is the system of interest: ClosedLoopDrivingLogicalSystem specializes the
  functional boundary of phase 6, keeps its five ports and owns the six elements; its one usage,
  closedLoopDrivingLogicalSystem, exists for the views (SysIDE draws usages, not definitions) and is the
  same system as the context's drivingSystem, not a second one;
- six elements, not seven (owner decision of 2026-11-06): run identity and planning share the planner, since
  the identity check is on the checkpoint the planner loads; the vehicle commander and the actuation gateway
  are separate, since the stop response of REQ-DRIVING-028 must survive the command path failing; the state
  publisher is separate, since observation is one way;
- each function allocated to exactly one element and each element carrying at least one, by untyped native
  allocations from the definition-nested function usages phase 6 allocated to;
- the exchanges as connections between typed ports: the boundary items delegated from the inherited ports,
  the ego motion to three elements, and inside the plan, the valid plan, the mode and the command in the
  order of the loop; nothing runs from the state publisher or the actuation gateway back into the loop;
- one view per SAF question of phase 7: the structure as a tree, the function mapping as a matrix, the
  internal exchanges as an interconnection, each framed by a phase 7 concern typed by the catalogue;
- no technology, platform, transport or claim in the elements, and no vehicle signal specification.
"""

from pathlib import Path
import re

import pytest

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
MODEL = DRIVING / "closed_loop_driving_logical_architecture.sysml"
FUNCTIONAL = DRIVING / "closed_loop_driving_functional_architecture.sysml"
FRAMING = DRIVING / "closed_loop_driving_framing.sysml"
GUIDE = ROOT / "docs/guides/closed-loop-driving-increment.md"
PACKAGE = "DE4SDV_ClosedLoopDrivingLogicalArchitecture"
FUNCTIONAL_PACKAGE = "DE4SDV_ClosedLoopDrivingFunctionalArchitecture"
SYSTEM = "ClosedLoopDrivingLogicalSystem"
SYSTEM_USAGE = "closedLoopDrivingLogicalSystem"
BOUNDARY = "ClosedLoopDrivingFunctionalBoundary"
FLOW = "ClosedLoopDrivingFunctionalFlow"
FLOW_USAGE = "closedLoopDrivingFunctionalFlow"

#: Each logical element of the system, in the order of the loop -> (definition, the functions it carries).
ELEMENTS = {
    "inputConditioner": ("InputConditioner", {"assembleInputs"}),
    "planner": ("TrajectoryPlanner", {"identifyRun", "planTrajectory"}),
    "loopSupervisor": ("LoopSupervisor", {"superviseLoop"}),
    "vehicleCommander": ("VehicleCommander", {"commandVehicle"}),
    "actuationGateway": ("ActuationGateway", {"applyCommands"}),
    "statePublisher": ("OperationalStatePublisher", {"publishState"}),
}
FUNCTIONS = ("identifyRun", "assembleInputs", "planTrajectory", "superviseLoop", "commandVehicle",
             "applyCommands", "publishState")

#: Each element definition -> its ports; the boundary port definitions are those of phase 6.
PORTS = {
    "InputConditioner": {"cameraImagesIn": "CameraImagesInbound", "egoMotionIn": "EgoMotionInbound",
                         "routeIn": "RouteInbound", "checkpointInputsOut": "CheckpointInputsOutbound",
                         "inputConditionOut": "InputConditionOutbound"},
    "TrajectoryPlanner": {"checkpointInputsIn": "CheckpointInputsInbound", "planOut": "DrivingPlanOutbound"},
    "LoopSupervisor": {"inputConditionIn": "InputConditionInbound", "planIn": "DrivingPlanInbound",
                       "validPlanOut": "DrivingPlanOutbound", "modeOut": "DrivingModeOutbound"},
    "VehicleCommander": {"validPlanIn": "DrivingPlanInbound", "modeIn": "DrivingModeInbound",
                         "egoMotionIn": "EgoMotionInbound", "commandOut": "MotionCommandOutbound"},
    "ActuationGateway": {"commandIn": "MotionCommandInbound", "vehicleCommandOut": "VehicleCommandOutbound",
                         "actuationStateOut": "ActuationStateOutbound"},
    "OperationalStatePublisher": {"planIn": "DrivingPlanInbound", "egoMotionIn": "EgoMotionInbound",
                                  "modeIn": "DrivingModeInbound", "actuationStateIn": "ActuationStateInbound",
                                  "operationalStateOut": "OperationalStateOutbound"},
}
BOUNDARY_PORTS = ("cameraImagesIn", "egoMotionIn", "routeIn", "vehicleCommandOut", "operationalStateOut")
INTERNAL_PORT_ITEMS = {
    "CheckpointInputsOutbound": ("out", "checkpointInputs", "CheckpointInputs"),
    "CheckpointInputsInbound": ("in", "checkpointInputs", "CheckpointInputs"),
    "InputConditionOutbound": ("out", "inputCondition", "InputCondition"),
    "InputConditionInbound": ("in", "inputCondition", "InputCondition"),
    "DrivingPlanOutbound": ("out", "plan", "DrivingPlan"),
    "DrivingPlanInbound": ("in", "plan", "DrivingPlan"),
    "DrivingModeOutbound": ("out", "mode", "DrivingMode"),
    "DrivingModeInbound": ("in", "mode", "DrivingMode"),
    "MotionCommandOutbound": ("out", "command", "VehicleMotionCommand"),
    "MotionCommandInbound": ("in", "command", "VehicleMotionCommand"),
    "ActuationStateOutbound": ("out", "actuationState", "ActuationState"),
    "ActuationStateInbound": ("in", "actuationState", "ActuationState"),
}

#: Every connection of the system as (from end, to end): boundary delegations, then the loop.
CONNECTIONS = {
    ("cameraImagesIn", "inputConditioner.cameraImagesIn"),
    ("egoMotionIn", "inputConditioner.egoMotionIn"),
    ("egoMotionIn", "vehicleCommander.egoMotionIn"),
    ("egoMotionIn", "statePublisher.egoMotionIn"),
    ("routeIn", "inputConditioner.routeIn"),
    ("actuationGateway.vehicleCommandOut", "vehicleCommandOut"),
    ("statePublisher.operationalStateOut", "operationalStateOut"),
    ("inputConditioner.checkpointInputsOut", "planner.checkpointInputsIn"),
    ("inputConditioner.inputConditionOut", "loopSupervisor.inputConditionIn"),
    ("planner.planOut", "loopSupervisor.planIn"),
    ("planner.planOut", "statePublisher.planIn"),
    ("loopSupervisor.validPlanOut", "vehicleCommander.validPlanIn"),
    ("loopSupervisor.modeOut", "vehicleCommander.modeIn"),
    ("loopSupervisor.modeOut", "statePublisher.modeIn"),
    ("vehicleCommander.commandOut", "actuationGateway.commandIn"),
    ("actuationGateway.actuationStateOut", "statePublisher.actuationStateIn"),
}
#: The exchanges a requirement constrains: the plan to the supervisor, the valid plan on and the command
#: (REQ-DRIVING-014), and the actuation state to the publisher, which REQ-DRIVING-029 times from the stop the
#: actuation applies itself (GAP-DRIVING-005, amended on the owner's decision of 2026-11-06).
CONSTRAINED_EXCHANGES = {
    ("planner.planOut", "loopSupervisor.planIn"),
    ("loopSupervisor.validPlanOut", "vehicleCommander.validPlanIn"),
    ("vehicleCommander.commandOut", "actuationGateway.commandIn"),
    ("actuationGateway.actuationStateOut", "statePublisher.actuationStateIn"),
}

STRUCTURE_VIEW = "closedLoopDrivingLogicalStructureView"
MATRIX_VIEW = "closedLoopDrivingFunctionMappingView"
EXCHANGE_VIEW = "closedLoopDrivingInternalExchangeView"
#: view -> (type or None, render, exposes in order, framed concerns)
VIEWS = {
    STRUCTURE_VIEW: (None, "render asTreeDiagram;",
                     [SYSTEM_USAGE] + [f"{SYSTEM_USAGE}::{element}" for element in ELEMENTS],
                     ["closedLoopDrivingLogicalStructureConcern"]),
    MATRIX_VIEW: ("MVD::MatrixView", None,
                  [f"{FLOW_USAGE}::{function}" for function in FUNCTIONS]
                  + [f"{SYSTEM}::{element}" for element in ELEMENTS] + [f"{PACKAGE}::*"],
                  ["closedLoopDrivingFunctionMappingConcern"]),
    EXCHANGE_VIEW: (None, "render asInterconnectionDiagram;", [SYSTEM_USAGE, f"{SYSTEM_USAGE}::**"],
                    ["closedLoopDrivingInternalExchangeConcern"]),
}
VIEWPOINTS = {
    "closedLoopDrivingLogicalStructureConcern": "SystemStructureDefinitionViewpoint",
    "closedLoopDrivingFunctionMappingConcern": "SystemFunctionMappingViewpoint",
    "closedLoopDrivingInternalExchangeConcern": "SystemInternalExchangeViewpoint",
}
#: concern -> (catalogue type, the parties that hold it)
CATALOGUE_CONCERNS = {
    "closedLoopDrivingLogicalStructureConcern": ("ConceptualStructureConcern", {"SystemArchitect", "SoftwareDeveloper"}),
    "closedLoopDrivingFunctionMappingConcern": ("ConceptualFunctionMappingConcern",
                                                {"SystemArchitect", "VerificationEngineer"}),
    "closedLoopDrivingInternalExchangeConcern": ("ConceptualInternalExchangeConcern",
                                                 {"SystemsEngineer", "SoftwareDeveloper"}),
}

FORBIDDEN_IN_DOCS = ("CARLA", "ROS", "DDS", "Zenoh", "SOME/IP", "GPU", "Python", "PyTorch", "Linux", "Android",
                     "S-CORE", "VSS", "safe", "certif", "complian", "homolog", "container", "hypervisor")
TECHNOLOGY_NAMES = ("CAN", "LIN", "FlexRay", "Ethernet", "gRPC", "KUKSA", "AUTOSAR", "AAOS", "Autoware")


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(line.strip().lstrip("*").strip() for line in text.splitlines()).strip()


def _doc(declaration: str) -> str:
    body = braced_body(_raw(), declaration)
    match = re.match(r"\s*doc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{declaration}: the doc must open the body"
    return _flat(match.group(1))


def _system_body() -> str:
    return braced_body(_code(), f"part def {SYSTEM} :> {BOUNDARY}")


def _connections() -> list[tuple[str, str]]:
    return re.findall(r"\bconnection\s+\w+\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*;", _system_body())


def _allocations() -> list[tuple[str, str, str]]:
    rows = re.findall(r"\ballocation\s+(\w+)(?:\s*:\s*(\w+))?\s+allocate\s+(\S+)\s+to\s+([^\s;{]+)\s*;", _code())
    assert all(not typed for _, typed, _, _ in rows), "allocations are untyped, as in phase 6"
    return [(name, source, target) for name, _, source, target in rows]


def test_the_charter_names_the_package_after_the_functional_architecture():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part closedLoopDrivingCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    assert names.index(PACKAGE) == names.index(FUNCTIONAL_PACKAGE) + 1
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", _code())


def test_the_six_elements_are_logical_allocation_elements_and_nothing_else_is():
    code = _code()
    declared = re.findall(r"\bpart\s+def\s+(\w+)\s*:>\s*LogicalAllocationElement\s*\{", code)
    assert sorted(declared) == sorted(definition for definition, _ in ELEMENTS.values())
    assert len(declared) == 6
    assert "private import DE4SDV_TraceVocabulary::LogicalAllocationElement;" in code
    for definition, _ in ELEMENTS.values():
        assert "Carries" in _doc(f"part def {definition} :> LogicalAllocationElement"), definition


def test_the_system_is_the_boundary_of_phase_6_one_level_inside_and_owns_the_six_elements():
    code = _code()
    # the exact header: the logical system is the system of interest at its phase 6 boundary, not a new one
    assert re.search(rf"\bpart\s+def\s+{SYSTEM}\s*:>\s*{BOUNDARY}\s*\{{", code)
    assert f"private import {FUNCTIONAL_PACKAGE}::{BOUNDARY};" in code
    body = _system_body()
    owned = re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M)
    assert owned == [(usage, definition) for usage, (definition, _) in ELEMENTS.items()]
    # one usage of the logical definition, for the views (SysIDE draws usages); no usage of the boundary
    assert re.findall(rf"^\s*part\s+(\w+)\s*:\s*{SYSTEM}\s*[{{;=]", code, re.M) == [SYSTEM_USAGE]
    assert not re.search(rf"\bpart\s+\w+\s*:\s*{BOUNDARY}\b", code)
    assert "the same system as the context's drivingSystem" in _doc(f"part def {SYSTEM} :> {BOUNDARY}")
    assert "the same system as the context's drivingSystem" in _doc(f"part {SYSTEM_USAGE} : {SYSTEM}")
    # the boundary ports are inherited, never redeclared
    assert not re.search(r"^\s*port\s+\w+\s*:", body, re.M)


@pytest.mark.parametrize("definition", sorted(PORTS), ids=sorted(PORTS))
def test_each_element_declares_exactly_its_ports(definition):
    body = braced_body(_code(), f"part def {definition} :> LogicalAllocationElement")
    assert dict(re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", body)) == PORTS[definition]
    assert not re.search(r"\b(part|action|perform|flow)\b", body), "an element carries functions by allocation only"


def test_the_internal_ports_carry_the_items_of_phase_6_in_one_direction():
    code = _code()
    for port_def, (direction, item, item_type) in INTERNAL_PORT_ITEMS.items():
        body = braced_body(code, f"port def {port_def}")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [(direction, item, item_type)], port_def
    for boundary_port in ("CameraImagesInbound", "EgoMotionInbound", "RouteInbound", "VehicleCommandOutbound",
                          "OperationalStateOutbound"):
        assert f"private import {FUNCTIONAL_PACKAGE}::{boundary_port};" in code, boundary_port
        assert not re.search(rf"\bport\s+def\s+{boundary_port}\b", code), "the boundary ports are phase 6's"
    for item in ("CheckpointInputs", "InputCondition", "DrivingPlan", "DrivingMode"):
        assert f"private import {FUNCTIONAL_PACKAGE}::{item};" in code, item
    assert "private import DE4SDV_ClosedLoopDrivingOperationalContext::VehicleMotionCommand;" in code
    assert not re.search(r"\bitem\s+def\b", code), "the items are phase 2's and phase 6's"


def test_the_exchanges_are_exactly_these_connections():
    connections = _connections()
    assert set(connections) == CONNECTIONS
    assert len(connections) == len(CONNECTIONS)
    assert len(re.findall(r"\bconnect\b", _system_body())) == len(CONNECTIONS)
    assert not re.search(r"\bflow\b", _system_body()), "exchanges between parts are connections"
    # every end of a connection names a declared port of its element, or an inherited boundary port
    for end in {end for pair in connections for end in pair}:
        if "." in end:
            element, port = end.split(".")
            assert port in PORTS[ELEMENTS[element][0]], end
        else:
            assert end in BOUNDARY_PORTS, end


def test_the_constrained_exchanges_cross_element_boundaries_and_nothing_flows_back():
    connections = set(_connections())
    assert CONSTRAINED_EXCHANGES <= connections
    for source, target in connections:
        if source.startswith("statePublisher."):
            assert "." not in target, (source, target, "only to the boundary, never back into the loop")
        if source.startswith("actuationGateway."):
            assert "." not in target or target.startswith("statePublisher."), \
                (source, target, "to the boundary or to the publisher, which is off the loop; never back into it")
    publisher_sources = {source for source, target in connections if target.startswith("statePublisher.")}
    assert publisher_sources == {"egoMotionIn", "planner.planOut", "loopSupervisor.modeOut",
                                 "actuationGateway.actuationStateOut"}, "both stop deciders reach the publisher"
    for element in ("ActuationGateway", "OperationalStatePublisher"):
        doc = _doc(f"part def {element} :> LogicalAllocationElement")
        assert "actuation state" in doc and "cause" in doc, element
    # the ego motion reaches the three elements that take it
    assert {target for source, target in connections if source == "egoMotionIn"} == {
        "inputConditioner.egoMotionIn", "vehicleCommander.egoMotionIn", "statePublisher.egoMotionIn"}


def test_each_function_is_allocated_to_its_element_once_and_each_element_carries_one():
    rows = _allocations()
    assert len(rows) == 7
    expected = {f"{FLOW}::{function}": f"{SYSTEM}::{usage}"
                for usage, (_, functions) in ELEMENTS.items() for function in functions}
    assert {source: target for _, source, target in rows} == expected
    assert sorted(source for _, source, _ in rows) == sorted(f"{FLOW}::{function}" for function in FUNCTIONS)
    assert {target for _, _, target in rows} == {f"{SYSTEM}::{usage}" for usage in ELEMENTS}
    assert f"private import {FUNCTIONAL_PACKAGE}::{FLOW};" in _code()
    # the owner's decisions, each pinned by the allocation that records it
    assert expected[f"{FLOW}::identifyRun"] == expected[f"{FLOW}::planTrajectory"] == f"{SYSTEM}::planner"
    assert expected[f"{FLOW}::commandVehicle"] != expected[f"{FLOW}::applyCommands"]
    assert expected[f"{FLOW}::publishState"] not in {expected[f"{FLOW}::{f}"] for f in FUNCTIONS if f != "publishState"}


def test_the_functions_allocated_are_the_seven_of_phase_6():
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    flow = braced_body(functional, f"action def {FLOW}")
    declared = re.findall(r"^\s*action\s+(\w+)\s*:\s*\w+\s*\{", flow, re.M)
    assert sorted(declared) == sorted(FUNCTIONS)


def test_the_package_publishes_exactly_one_view_per_question():
    declared = re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M)
    assert sorted(declared) == sorted(VIEWS)
    assert len(declared) == 3


@pytest.mark.parametrize("view_name", sorted(VIEWS), ids=sorted(VIEWS))
def test_each_view_frames_its_concern_and_exposes_its_content(view_name):
    view_type, render, exposes, frames = VIEWS[view_name]
    code = _code()
    header = rf"\bview\s+{view_name}\s*" + (rf":\s*{re.escape(view_type)}\s*" if view_type else "") + r"\{"
    assert re.search(header, code), view_name
    view = braced_body(code, f"view {view_name}" + (f" : {view_type}" if view_type else ""))
    viewpoint = braced_body(view, "viewpoint")
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == frames
    assert re.search(rf"viewpoint\s+\w+\s*:\s*{VIEWPOINTS[frames[0]]}\s*\{{", view), view_name
    assert len(re.findall(r"\bviewpoint\b", view)) == 1
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", view) == exposes
    if render:
        assert render in view
    else:
        assert "render as" not in view, "the view type selects the kind"


def test_the_matrix_maps_the_functions_to_the_elements_with_reference_elements():
    view = braced_body(_code(), f"view {MATRIX_VIEW} : MVD::MatrixView")
    rows = braced_body(view, "view :>> rowView")
    columns = braced_body(view, "view :>> columnView")
    cells = braced_body(view, "view :>> cellView")
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", rows) == [f"{FLOW_USAGE}::{function}" for function in FUNCTIONS]
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", columns) == [f"{SYSTEM}::{element}" for element in ELEMENTS]
    for axis in (rows, columns):
        assert "attribute :>> includeReferenceElements = true;" in axis
        assert "attribute :>> representation = Rep::name;" in axis
    assert f"expose {PACKAGE}::*;" in cells
    assert "attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;" in cells
    assert f"private import {FUNCTIONAL_PACKAGE}::{FLOW_USAGE};" in _code()
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"matrix-{MATRIX_VIEW}"]
    assert metadata.title and metadata.description, MATRIX_VIEW


def test_the_diagrams_draw_the_elements_without_the_allocations():
    """SysIDE draws every allocation of the view's package as a node unless filtered (render of dd91667d)."""
    for view_name in (STRUCTURE_VIEW, EXCHANGE_VIEW):
        assert "filter not (@ SysML::AllocationUsage);" in braced_body(_code(), f"view {view_name}"), view_name
    view = braced_body(_code(), f"view {EXCHANGE_VIEW}")
    assert "attribute depth = -1;" in view
    assert "attribute showAnnotationRows = false;" in view


@pytest.mark.parametrize("concern_name", sorted(CATALOGUE_CONCERNS), ids=sorted(CATALOGUE_CONCERNS))
def test_each_phase_7_concern_is_typed_by_the_catalogue_and_held_by_the_party_it_serves(concern_name):
    catalogue, stakeholders = CATALOGUE_CONCERNS[concern_name]
    concern = braced_body(_code(), f"concern {concern_name} : {catalogue}")
    members = re.findall(r"\b(subject|stakeholder)\b", concern)
    assert members and members[0] == "subject"
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == stakeholders
    assert "need" in _doc(f"concern {concern_name} : {catalogue}")


def test_the_elements_name_no_technology_platform_transport_or_claim():
    declarations = [f"part def {d} :> LogicalAllocationElement" for d, _ in ELEMENTS.values()]
    declarations += [f"part def {SYSTEM} :> {BOUNDARY}"] + [f"port def {p}" for p in INTERNAL_PORT_ITEMS]
    declarations += [f"concern {c} : {t}" for c, (t, _) in CATALOGUE_CONCERNS.items()]
    for declaration in declarations:
        doc = _doc(declaration)
        found = [word for word in FORBIDDEN_IN_DOCS if re.search(rf"\b{re.escape(word)}", doc, re.I)]
        found += [word for word in TECHNOLOGY_NAMES if re.search(rf"\b{re.escape(word)}\b", doc)]
        assert not found, (declaration, found)


def test_the_package_types_no_vehicle_signal_specification():
    code = _code()
    assert "COVESA_VSS" not in code and "DE4SDV_VSS_Extensions" not in code
    assert not re.search(r":\s*Vehicle_\w+", code), "VSS typing starts at phase 8"
    assert not re.search(r"\b(ref\s+part|perform|exhibit|state\s+def)\b", code)
    assert not re.search(rf"^\s*part\s+\w+\s*:\s*{SYSTEM}\s*=", code, re.M), "the usage is bound to nothing"


def test_the_allocation_file_is_governed_with_its_six_endpoint_definitions():
    import test_trace_allocation_completeness as trace

    assert trace.ALLOCATION_FILES[trace.DRIVING_L] == (
        (trace.DRIVING_L, trace.DRIVING_F), {(trace.FUNCTION, trace.LOGICAL): 7}, {},
        (trace.FUNCTION, trace.LOGICAL))
    assert trace.GOVERNED[trace.DRIVING_L] == (trace.LOGICAL, {d for d, _ in ELEMENTS.values()})
    assert trace.DRIVING_L in trace.LINEAGE_FILES
    assert trace.NOT_ENDPOINTS[trace.DRIVING_L] == {SYSTEM}


def test_the_guide_describes_phase_7_and_hands_its_exchanges_to_phase_8():
    guide = GUIDE.read_text(encoding="utf-8")
    assert "## Logical architecture (Phase 7)" in guide
    assert "closed_loop_driving_logical_architecture.sysml" in guide
    assert "six logical elements" in guide
    assert "Phase 8 places them on a" in guide, "the exchanges REQ-DRIVING-014 constrains are placed by phase 8"
    assert "tests/test_closed_loop_driving_logical_architecture.py" in guide
