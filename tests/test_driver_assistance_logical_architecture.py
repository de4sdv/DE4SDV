"""Content pins for the driver-assistance logical architecture (phase 7), not semantic validation.

INC-DRIVING-002 phase 7 gives the candidate driver-assistance system an inside: the technology-independent logical
elements that realize the four functions of phase 6, one level below the functional boundary. Method Check holds the
DefineLogicalArchitecture rule (each function allocated to a logical element by a native allocation; advisory, each
logical element carries a function). These pins hold what review settled on top of it:

- the decomposition subject is the system of interest: DriverAssistanceLogicalSystem specializes the functional
  boundary of phase 6, keeps its four ports and owns the four elements; its one usage,
  driverAssistanceLogicalSystem, exists for the views (SysIDE draws usages, not definitions) and is the same system
  as the context's candidateSystem, not a second one;
- four elements, one per function (owner decision of 2026-11-15): the identity recorder, the vehicle-ahead
  assessor, the warning requester and the driving commander; the driving commander is the one command source, and
  the emergency braking stays a mode of its one function;
- each function allocated to its own element, by untyped native allocations from the definition-nested function
  usages phase 6 allocated the requirements to;
- the exchanges as connections between typed ports: the boundary items delegated from the inherited ports, the
  vehicle speed to two elements, and inside the assessment, the warning state and the candidate record in the order
  of the functional flow; the warning state carries the order of REQ-DRIVING-042 across two elements and the
  candidate record that of REQ-DRIVING-044; nothing runs from the driving commander to another element;
- the gaps that border an element stay open in its doc: the emergency braking (gapNoSeparateEmergencyFunction), the
  warning output (gapWarningOutput) and the camera geometry (gapCameraImageAndGeometry);
- one view per SAF question of phase 7: the structure as a tree, the function mapping as a matrix, the internal
  exchanges as an interconnection, each framed by a phase 7 concern typed by the catalogue;
- no technology, platform, transport or claim in the elements, no vehicle signal specification, and no trace of the
  path requirements, which phase 8 carries.
"""

from pathlib import Path
import re

import pytest

from sysml_shapes import braced_body, strip_comments
from test_driver_assistance_functional_architecture import FORBIDDEN_IN_FUNCTIONS, TECHNOLOGY_NAMES

ROOT = Path(__file__).resolve().parents[1]
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
MODEL = DRIVING / "driver_assistance_logical_architecture.sysml"
FUNCTIONAL = DRIVING / "driver_assistance_functional_architecture.sysml"
FRAMING = DRIVING / "driver_assistance_framing.sysml"
GUIDE = ROOT / "docs/guides/driver-assistance-increment.md"
PACKAGE = "DE4SDV_DriverAssistanceLogicalArchitecture"
FUNCTIONAL_PACKAGE = "DE4SDV_DriverAssistanceFunctionalArchitecture"
SYSTEM = "DriverAssistanceLogicalSystem"
SYSTEM_USAGE = "driverAssistanceLogicalSystem"
BOUNDARY = "DriverAssistanceFunctionalBoundary"
FLOW = "DriverAssistanceFunctionalFlow"
FLOW_USAGE = "driverAssistanceFunctionalFlow"

#: Each logical element of the system, in the order of the functional flow -> (definition, the function it carries).
ELEMENTS = {
    "identityRecorder": ("CandidateIdentityRecorder", "identifyCandidate"),
    "vehicleAheadAssessor": ("VehicleAheadAssessor", "assessVehicleAhead"),
    "warningRequester": ("CollisionWarningRequester", "requestWarning"),
    "drivingCommander": ("DrivingCommander", "commandVehicle"),
}
FUNCTIONS = ("identifyCandidate", "assessVehicleAhead", "requestWarning", "commandVehicle")

#: Each element definition -> its ports; the boundary port definitions are those of phase 6.
PORTS = {
    "CandidateIdentityRecorder": {"candidateRecordOut": "CandidateIdentityRecordOutbound"},
    "VehicleAheadAssessor": {"frontCameraImageIn": "FrontCameraImageInbound", "vehicleSpeedIn": "VehicleSpeedInbound",
                             "assessmentOut": "VehicleAheadAssessmentOutbound"},
    "CollisionWarningRequester": {"assessmentIn": "VehicleAheadAssessmentInbound",
                                  "warningRequestOut": "WarningRequestOutbound",
                                  "warningStateOut": "WarningRequestStateOutbound"},
    "DrivingCommander": {"assessmentIn": "VehicleAheadAssessmentInbound", "vehicleSpeedIn": "VehicleSpeedInbound",
                         "warningStateIn": "WarningRequestStateInbound",
                         "candidateRecordIn": "CandidateIdentityRecordInbound",
                         "drivingCommandOut": "DrivingCommandOutbound"},
}
BOUNDARY_PORTS = ("frontCameraImageIn", "vehicleSpeedIn", "drivingCommandOut", "warningRequestOut")
BOUNDARY_PORT_DEFS = ("FrontCameraImageInbound", "VehicleSpeedInbound", "DrivingCommandOutbound",
                      "WarningRequestOutbound")
INTERNAL_PORT_ITEMS = {
    "VehicleAheadAssessmentOutbound": ("out", "assessment", "VehicleAheadAssessment"),
    "VehicleAheadAssessmentInbound": ("in", "assessment", "VehicleAheadAssessment"),
    "WarningRequestStateOutbound": ("out", "warningState", "WarningRequestState"),
    "WarningRequestStateInbound": ("in", "warningState", "WarningRequestState"),
    "CandidateIdentityRecordOutbound": ("out", "candidateRecord", "CandidateIdentityRecord"),
    "CandidateIdentityRecordInbound": ("in", "candidateRecord", "CandidateIdentityRecord"),
}

#: Every connection of the system as (from end, to end): boundary delegations, then the functional flow.
CONNECTIONS = {
    ("frontCameraImageIn", "vehicleAheadAssessor.frontCameraImageIn"),
    ("vehicleSpeedIn", "vehicleAheadAssessor.vehicleSpeedIn"),
    ("vehicleSpeedIn", "drivingCommander.vehicleSpeedIn"),
    ("drivingCommander.drivingCommandOut", "drivingCommandOut"),
    ("warningRequester.warningRequestOut", "warningRequestOut"),
    ("vehicleAheadAssessor.assessmentOut", "warningRequester.assessmentIn"),
    ("vehicleAheadAssessor.assessmentOut", "drivingCommander.assessmentIn"),
    ("warningRequester.warningStateOut", "drivingCommander.warningStateIn"),
    ("identityRecorder.candidateRecordOut", "drivingCommander.candidateRecordIn"),
}
#: The exchanges across which a requirement states an order -> (the requirement, its name in phase 5).
CONSTRAINED_EXCHANGES = {
    ("warningRequester.warningStateOut", "drivingCommander.warningStateIn"):
        ("REQ-DRIVING-042", "reqWarningRequestBeforeEmergencyBraking"),
    ("identityRecorder.candidateRecordOut", "drivingCommander.candidateRecordIn"):
        ("REQ-DRIVING-044", "reqRecordCandidateIdentity"),
}

STRUCTURE_VIEW = "driverAssistanceLogicalStructureView"
MATRIX_VIEW = "driverAssistanceFunctionMappingView"
EXCHANGE_VIEW = "driverAssistanceInternalExchangeView"
#: view -> (type or None, render, exposes in order, framed concerns)
VIEWS = {
    STRUCTURE_VIEW: (None, "render asTreeDiagram;",
                     [SYSTEM_USAGE] + [f"{SYSTEM_USAGE}::{element}" for element in ELEMENTS],
                     ["driverAssistanceLogicalStructureConcern"]),
    MATRIX_VIEW: ("MVD::MatrixView", None,
                  [f"{FLOW_USAGE}::{function}" for function in FUNCTIONS]
                  + [f"{SYSTEM}::{element}" for element in ELEMENTS] + [f"{PACKAGE}::*"],
                  ["driverAssistanceFunctionMappingConcern"]),
    EXCHANGE_VIEW: (None, "render asInterconnectionDiagram;", [SYSTEM_USAGE, f"{SYSTEM_USAGE}::**"],
                    ["driverAssistanceInternalExchangeConcern"]),
}
VIEWPOINTS = {
    "driverAssistanceLogicalStructureConcern": "SystemStructureDefinitionViewpoint",
    "driverAssistanceFunctionMappingConcern": "SystemFunctionMappingViewpoint",
    "driverAssistanceInternalExchangeConcern": "SystemInternalExchangeViewpoint",
}
#: concern -> (catalogue type, the parties that hold it)
CATALOGUE_CONCERNS = {
    "driverAssistanceLogicalStructureConcern": ("ConceptualStructureConcern", {"SystemArchitect", "SoftwareDeveloper"}),
    "driverAssistanceFunctionMappingConcern": ("ConceptualFunctionMappingConcern",
                                               {"SystemArchitect", "VerificationEngineer"}),
    "driverAssistanceInternalExchangeConcern": ("ConceptualInternalExchangeConcern",
                                                {"SystemsEngineer", "SoftwareDeveloper"}),
}

#: The phase 6 bans, which name the candidate, its path and its platform, plus the deployment words of phase 7.
FORBIDDEN_IN_DOCS = FORBIDDEN_IN_FUNCTIONS + ("container", "hypervisor")


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


def _element_doc(usage: str) -> str:
    return _doc(f"part def {ELEMENTS[usage][0]} :> LogicalAllocationElement")


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
                          "part driverAssistanceCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    assert names.index(PACKAGE) == names.index(FUNCTIONAL_PACKAGE) + 1
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", _code())


def test_the_header_states_the_question_the_decision_and_what_phase_8_carries():
    header = _flat(_raw().split("package ", 1)[0].replace("/*", "").replace("*/", ""))
    for phrase in ("INC-DRIVING-002, phase 7: the logical architecture of the candidate driver-assistance system. "
                   "What technology-independent logical elements realize the four functions of phase 6?",
                   "Four elements, one per function (owner decision of 2026-11-15).",
                   "The context elements of phase 2 stay outside and undivided.",
                   "REQ-DRIVING-038 and REQ-DRIVING-043 constrain how the driving command and the warning request "
                   "travel outside the system; phase 8 carries them by the elements it places on those exchanges.",
                   "Nothing here names a computer, a process, a transport or a signal catalogue."):
        assert phrase in header, phrase


def test_the_four_elements_are_logical_allocation_elements_and_nothing_else_is():
    code = _code()
    declared = re.findall(r"\bpart\s+def\s+(\w+)\s*:>\s*LogicalAllocationElement\s*\{", code)
    assert sorted(declared) == sorted(definition for definition, _ in ELEMENTS.values())
    assert len(declared) == 4
    assert "private import DE4SDV_TraceVocabulary::LogicalAllocationElement;" in code
    for usage in ELEMENTS:
        assert _element_doc(usage).startswith("Carries "), usage


def test_the_system_is_the_boundary_of_phase_6_one_level_inside_and_owns_the_four_elements():
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
    assert "the same system as the context's candidateSystem" in _doc(f"part def {SYSTEM} :> {BOUNDARY}")
    assert "the same system as the context's candidateSystem" in _doc(f"part {SYSTEM_USAGE} : {SYSTEM}")
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
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [(direction, item, item_type)], \
            port_def
        assert f"private import {FUNCTIONAL_PACKAGE}::{item_type};" in code, item_type
    for boundary_port in BOUNDARY_PORT_DEFS:
        assert f"private import {FUNCTIONAL_PACKAGE}::{boundary_port};" in code, boundary_port
        assert not re.search(rf"\bport\s+def\s+{boundary_port}\b", code), "the boundary ports are phase 6's"
    assert len(re.findall(r"\bport\s+def\b", code)) == len(INTERNAL_PORT_ITEMS)
    assert not re.search(r"\bitem\s+def\b", code), "the items are phase 2's and phase 6's"
    # each item is the one the function at the exchange's source gives out in phase 6
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    for function_def, item, item_type in (("IdentifyCandidate", "candidateRecord", "CandidateIdentityRecord"),
                                          ("AssessVehicleAhead", "assessment", "VehicleAheadAssessment"),
                                          ("RequestCollisionWarning", "warningState", "WarningRequestState")):
        body = braced_body(functional, f"action def {function_def} :> AllocatableFunction")
        assert re.search(rf"\bout\s+{item}\s*:\s*{item_type}\s*;", body), function_def


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


def test_one_command_source_and_every_exchange_runs_one_way():
    connections = set(_connections())
    # the driving command leaves from the driving commander only, the warning request from the requester only
    assert {source for source, target in connections if target == "drivingCommandOut"} == \
        {"drivingCommander.drivingCommandOut"}
    assert {source for source, target in connections if target == "warningRequestOut"} == \
        {"warningRequester.warningRequestOut"}
    # nothing the driving commander provides goes to another element, and nothing goes into the identity recorder
    elements = set(ELEMENTS)
    for source, target in connections:
        if source.split(".")[0] == "drivingCommander":
            assert target.split(".")[0] not in elements, (source, target)
        assert not target.startswith("identityRecorder."), (source, target)
    # the assessor takes only the boundary items; the requester only the assessment
    assert {source for source, target in connections if target.startswith("vehicleAheadAssessor.")} == \
        {"frontCameraImageIn", "vehicleSpeedIn"}
    assert {source for source, target in connections if target.startswith("warningRequester.")} == \
        {"vehicleAheadAssessor.assessmentOut"}
    # the vehicle speed reaches the two elements that take it
    assert {target for source, target in connections if source == "vehicleSpeedIn"} == {
        "vehicleAheadAssessor.vehicleSpeedIn", "drivingCommander.vehicleSpeedIn"}


def test_the_constrained_exchanges_carry_the_order_of_their_requirements():
    connections = set(_connections())
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    system = _doc(f"part def {SYSTEM} :> {BOUNDARY}")
    exchange = _doc("concern driverAssistanceInternalExchangeConcern : ConceptualInternalExchangeConcern")
    for (source, target), (identity, requirement) in CONSTRAINED_EXCHANGES.items():
        assert (source, target) in connections
        # phase 6 allocated the requirement to the functions of both ends, so its order crosses this exchange
        ends = {ELEMENTS[source.split(".")[0]][1], ELEMENTS[target.split(".")[0]][1]}
        allocated = set(re.findall(rf"\ballocate\s+{requirement}\s+to\s+{FLOW}::(\w+)\s*;", functional))
        assert allocated == ends, (identity, allocated)
        assert identity in system and identity in exchange, identity
    assert ("The warning state carries the order of REQ-DRIVING-042 across two elements, and the candidate record "
            "that of REQ-DRIVING-044.") in system


def test_each_function_is_allocated_to_its_own_element():
    rows = _allocations()
    assert len(rows) == 4
    expected = {f"{FLOW}::{function}": f"{SYSTEM}::{usage}" for usage, (_, function) in ELEMENTS.items()}
    assert {source: target for _, source, target in rows} == expected
    assert sorted(source for _, source, _ in rows) == sorted(f"{FLOW}::{function}" for function in FUNCTIONS)
    # the owner's decision of 2026-11-15: four elements, one per function, so no two functions share an element
    assert len({target for _, _, target in rows}) == len(FUNCTIONS)
    assert f"private import {FUNCTIONAL_PACKAGE}::{FLOW};" in _code()


def test_the_functions_allocated_are_the_four_of_phase_6():
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    flow = braced_body(functional, f"action def {FLOW}")
    declared = re.findall(r"^\s*action\s+(\w+)\s*:\s*\w+\s*\{", flow, re.M)
    assert declared == list(FUNCTIONS)


def test_each_element_says_why_it_stands_alone_and_keeps_its_gap_open():
    recorder = _element_doc("identityRecorder")
    assert "before the first driving command of each run" in recorder
    assert "phase 8 realizes it beside the software that gives the commands, not inside it" in recorder
    assessor = _element_doc("vehicleAheadAssessor")
    assert "the one producer of the assessment that both decisions take" in assessor
    assert "(gapCameraImageAndGeometry)" in assessor
    requester = _element_doc("warningRequester")
    assert "It is the only source of the warning request." in requester
    assert "(gapWarningOutput)" in requester
    commander = _element_doc("drivingCommander")
    for phrase in ("It is the one command source of the system",
                   "The emergency braking is a mode of this one command function, not an element of its own",
                   "stays open (gapNoSeparateEmergencyFunction)"):
        assert phrase in commander, phrase
    framing = strip_comments(FRAMING.read_text(encoding="utf-8"))
    for gap in ("gapCameraImageAndGeometry", "gapWarningOutput", "gapNoSeparateEmergencyFunction"):
        assert re.search(rf"\bpart\s+{gap}\s*:\s*IncrementGap\b", framing), gap


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
    """SysIDE draws every allocation of the view's package as a node unless filtered (precedent render)."""
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
    declarations += [f"part def {SYSTEM} :> {BOUNDARY}", f"part {SYSTEM_USAGE} : {SYSTEM}"]
    declarations += [f"port def {p}" for p in INTERNAL_PORT_ITEMS]
    declarations += [f"concern {c} : {t}" for c, (t, _) in CATALOGUE_CONCERNS.items()]
    for declaration in declarations:
        doc = _doc(declaration)
        found = [word for word in FORBIDDEN_IN_DOCS if re.search(rf"\b{re.escape(word)}", doc, re.I)]
        found += [word for word in TECHNOLOGY_NAMES if re.search(rf"\b{re.escape(word)}\b", doc)]
        assert not found, (declaration, found)


def test_the_package_types_no_signal_and_adds_no_trace_of_the_path_requirements():
    code = _code()
    assert "COVESA_VSS" not in code and "DE4SDV_VSS_Extensions" not in code
    assert not re.search(r":\s*Vehicle_\w+", code), "VSS typing starts at phase 8"
    assert not re.search(r"\b(ref\s+part|perform|exhibit|state\s+def)\b", code)
    assert not re.search(rf"^\s*part\s+\w+\s*:\s*{SYSTEM}\s*=", code, re.M), "the usage is bound to nothing"
    # REQ-DRIVING-038 and REQ-DRIVING-043 constrain the path outside the system; phase 8 carries them
    assert not re.search(r"\bdependency\b", code)
    assert not re.search(r"\breq[A-Z]\w*", code), "no requirement is allocated or traced here"


def test_the_allocation_file_is_governed_with_its_four_endpoint_definitions():
    import test_trace_allocation_completeness as trace

    assert trace.ALLOCATION_FILES[trace.ASSIST_L] == (
        (trace.ASSIST_L, trace.ASSIST_F), {(trace.FUNCTION, trace.LOGICAL): 4}, {}, (trace.FUNCTION, trace.LOGICAL))
    assert trace.GOVERNED[trace.ASSIST_L] == (trace.LOGICAL, {d for d, _ in ELEMENTS.values()})
    assert trace.ASSIST_L in trace.LINEAGE_FILES
    assert trace.NOT_ENDPOINTS[trace.ASSIST_L] == {SYSTEM}


def test_the_guide_describes_phase_7_and_hands_its_exchanges_to_phase_8():
    guide = GUIDE.read_text(encoding="utf-8")
    flat = " ".join(guide.split())
    # the section sits after phase 6 and before the open points
    order = [guide.index(heading) for heading in ("## Functional architecture (Phase 6)",
                                                  "## Logical architecture (Phase 7)",
                                                  "## What the framing already records as open")]
    assert order == sorted(order)
    section = " ".join(guide.split("## Logical architecture (Phase 7)", 1)[1].split("\n## ", 1)[0].split())
    for phrase in ("(../../textual-notation-of-model/packages/features/driving/driver_assistance_logical_architecture"
                   ".sysml)",
                   "four logical elements, one per function (2026-11-15)",
                   "The warning state carries the order of REQ-DRIVING-042 across two elements, and the candidate "
                   "record that of REQ-DRIVING-044.",
                   "Phase 8 places each exchange on a technology",
                   "Phase 7 shows no timing:",
                   "No state output crosses the boundary:"):
        assert phrase in section, phrase
    assert ("**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 classification, "
            "Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture, Phase 7 logical "
            "architecture, Phase 8 physical and software realization, Phase 9 variability and configuration and the "
            "first slice of Phase 10 verification and evidence, proposal.**") in flat
    assert ("The next model obligation is **Phase 10**: verification and evidence, which judges the configured "
            "product DRIVING-CONFIG-002 in closed loop; its second slice follows the readiness probes and adds the "
            "bench, the runs, the retained records and the statuses.") in flat
    assert "its first gate is `verificationCaseVerifiesRequirement`" not in flat, "phase 10's first slice landed"
    assert "The next model obligation is **Phase 9**" not in flat
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert "tests/test_driver_assistance_logical_architecture.py" in check
