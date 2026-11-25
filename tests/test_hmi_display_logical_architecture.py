"""Content pins for the HMI display logical architecture (phase 7), not semantic validation.

INC-HMI-001 phase 7 gives the HMI display an inside: the technology-independent logical elements that realize the five
functions of phase 6, one level below the functional boundary. Method Check holds the DefineLogicalArchitecture rule
(each function allocated to a logical element by a native allocation; advisory, each logical element carries a
function). These pins hold what the design settled on top of it:

- the decomposition subject is the system of interest: HmiDisplayLogicalSystem specializes the functional boundary of
  phase 6, keeps its five ports and owns the three elements; its one usage, hmiDisplayLogicalSystem, exists for the
  views (SysIDE draws usages, not definitions), depicts the context's hmiDisplay and is bound to nothing;
- three elements for five functions (owner decision of 2026-11-24): the scene drawer carries drawScene alone, the
  presenter carries judgeCurrency, showContent and giveWarning, and the identity recorder carries
  recordDisplayIdentity and has no port;
- each function allocated to its element, by untyped native allocations from the definition-nested function usages
  phase 6 allocated the requirements to;
- the exchanges as connections between typed ports: six delegations from the inherited ports and one exchange, the
  drawn scenes from the scene drawer to the presenter; nothing runs from the presenter to another element, nothing
  into the scene drawer from another element, and nothing touches the identity recorder;
- one view per SAF question of phase 7: the structure as a tree, the function mapping as a matrix, the internal
  exchanges as an interconnection, each framed by a phase 7 concern typed by the catalogue;
- no technology, platform, transport or claim in any doc, no vehicle signal specification, and no trace of
  REQ-HMI-009, which phase 8 carries;
- the texts of record of the design whole, and the guide's Phase 7 section block by block.
"""

from pathlib import Path
import hashlib
import re

import pytest

from sysml_shapes import braced_body, strip_comments
from test_hmi_display_framing import APPROVAL, PAST_BEHAVIOR
from test_hmi_display_functional_architecture import (DESIGN_TECHNOLOGY_WORDS, EXCLUDED_WORD_SHA256,
                                                      FORBIDDEN_IN_FUNCTIONS, TECHNOLOGY_NAMES)

ROOT = Path(__file__).resolve().parents[1]
HMI = ROOT / "textual-notation-of-model/packages/features/hmi"
MODEL = HMI / "hmi_display_logical_architecture.sysml"
FUNCTIONAL = HMI / "hmi_display_functional_architecture.sysml"
FRAMING = HMI / "hmi_display_framing.sysml"
GUIDE = ROOT / "docs/guides/hmi-display-increment.md"
MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
PACKAGE = "DE4SDV_HmiDisplayLogicalArchitecture"
FUNCTIONAL_PACKAGE = "DE4SDV_HmiDisplayFunctionalArchitecture"
SYSTEM = "HmiDisplayLogicalSystem"
SYSTEM_USAGE = "hmiDisplayLogicalSystem"
BOUNDARY = "HmiDisplayFunctionalBoundary"
SOI = "HmiDisplaySystem"
FLOW = "HmiDisplayFunctionalFlow"
FLOW_USAGE = "hmiDisplayFunctionalFlow"

#: Each logical element of the system, in the order of the owned parts -> (definition, the functions it carries).
ELEMENTS = {
    "displayIdentityRecorder": ("DisplayIdentityRecorder", ("recordDisplayIdentity",)),
    "sceneDrawer": ("SceneDrawer", ("drawScene",)),
    "displayPresenter": ("DisplayPresenter", ("judgeCurrency", "showContent", "giveWarning")),
}
#: The five functions of phase 6, in the order of the flow.
FUNCTIONS = ("recordDisplayIdentity", "drawScene", "judgeCurrency", "showContent", "giveWarning")

#: Each element definition -> its ports, in order; the boundary port definitions are those of phase 6.
PORTS = {
    "DisplayIdentityRecorder": [],
    "SceneDrawer": [("sceneIn", "DisplaySceneInbound"), ("drawnSceneOut", "DrawnSceneOutbound")],
    "DisplayPresenter": [("sceneIn", "DisplaySceneInbound"), ("speedIn", "DisplaySpeedInbound"),
                         ("warningRequestIn", "DisplayWarningRequestInbound"), ("drawnSceneIn", "DrawnSceneInbound"),
                         ("contentOut", "DisplayContentOutbound"), ("warningOut", "DisplayWarningOutbound")],
}
#: The ports the system inherits from the boundary of phase 6 -> their port definitions.
BOUNDARY_PORTS = {"sceneIn": "DisplaySceneInbound", "speedIn": "DisplaySpeedInbound",
                  "warningRequestIn": "DisplayWarningRequestInbound", "contentOut": "DisplayContentOutbound",
                  "warningOut": "DisplayWarningOutbound"}
#: The inner port definitions of this package -> (direction, item, item type): one phase 6 item each, one direction.
INTERNAL_PORT_ITEMS = {
    "DrawnSceneOutbound": ("out", "drawnScene", "DrawnScene"),
    "DrawnSceneInbound": ("in", "drawnScene", "DrawnScene"),
}

#: Every connection of the system, in order: the six delegations, then the one exchange between elements.
CONNECTIONS = [
    ("sceneToDrawerDelegation", "sceneIn", "sceneDrawer.sceneIn"),
    ("sceneToPresenterDelegation", "sceneIn", "displayPresenter.sceneIn"),
    ("speedToPresenterDelegation", "speedIn", "displayPresenter.speedIn"),
    ("warningRequestToPresenterDelegation", "warningRequestIn", "displayPresenter.warningRequestIn"),
    ("contentFromPresenterDelegation", "displayPresenter.contentOut", "contentOut"),
    ("warningFromPresenterDelegation", "displayPresenter.warningOut", "warningOut"),
    ("drawnSceneExchange", "sceneDrawer.drawnSceneOut", "displayPresenter.drawnSceneIn"),
]
#: The kind of each connection, read from the directions of the port items at its two ends.
CONNECTION_KINDS = {
    "sceneToDrawerDelegation": "inbound delegation", "sceneToPresenterDelegation": "inbound delegation",
    "speedToPresenterDelegation": "inbound delegation", "warningRequestToPresenterDelegation": "inbound delegation",
    "contentFromPresenterDelegation": "outbound delegation", "warningFromPresenterDelegation": "outbound delegation",
    "drawnSceneExchange": "exchange",
}
#: The two requirements that phase 6 allocated to both ends of the drawn scenes (drawScene and showContent).
DRAWN_SCENE_REQUIREMENTS = {"REQ-HMI-001": "reqShowTheSceneAsGiven", "REQ-HMI-002": "reqMarkTheObjectTheSystemActsOn"}

#: The five allocations, in order -> (name, function, element).
ALLOCATIONS = [
    ("recordDisplayIdentityAllocation", "recordDisplayIdentity", "displayIdentityRecorder"),
    ("drawSceneAllocation", "drawScene", "sceneDrawer"),
    ("judgeCurrencyAllocation", "judgeCurrency", "displayPresenter"),
    ("showContentAllocation", "showContent", "displayPresenter"),
    ("giveWarningAllocation", "giveWarning", "displayPresenter"),
]

STRUCTURE_VIEW = "hmiDisplayLogicalStructureView"
MATRIX_VIEW = "hmiDisplayFunctionMappingView"
EXCHANGE_VIEW = "hmiDisplayInternalExchangeView"
#: view -> (type or None, render, exposes in order, framed concerns, viewpoint usage)
VIEWS = {
    STRUCTURE_VIEW: (None, "render asTreeDiagram;",
                     [SYSTEM_USAGE] + [f"{SYSTEM_USAGE}::{element}" for element in ELEMENTS],
                     ["hmiDisplayLogicalStructureConcern"], "selectedLogicalStructureViewpoint"),
    MATRIX_VIEW: ("MVD::MatrixView", None,
                  [f"{FLOW_USAGE}::{function}" for function in FUNCTIONS]
                  + [f"{SYSTEM}::{element}" for element in ELEMENTS] + [f"{PACKAGE}::*"],
                  ["hmiDisplayFunctionMappingConcern"], "selectedFunctionMappingViewpoint"),
    EXCHANGE_VIEW: (None, "render asInterconnectionDiagram;", [SYSTEM_USAGE, f"{SYSTEM_USAGE}::**"],
                    ["hmiDisplayInternalExchangeConcern"], "selectedInternalExchangeViewpoint"),
}
VIEWPOINTS = {
    "hmiDisplayLogicalStructureConcern": "SystemStructureDefinitionViewpoint",
    "hmiDisplayFunctionMappingConcern": "SystemFunctionMappingViewpoint",
    "hmiDisplayInternalExchangeConcern": "SystemInternalExchangeViewpoint",
}
#: concern -> (catalogue type, the parties that hold it, in order)
CATALOGUE_CONCERNS = {
    "hmiDisplayLogicalStructureConcern": ("ConceptualStructureConcern", ["SystemArchitect", "SoftwareDeveloper"]),
    "hmiDisplayFunctionMappingConcern": ("ConceptualFunctionMappingConcern",
                                         ["SystemArchitect", "VerificationEngineer"]),
    "hmiDisplayInternalExchangeConcern": ("ConceptualInternalExchangeConcern",
                                          ["SystemsEngineer", "SoftwareDeveloper"]),
}
#: The package's imports, one by one (the set is pinned, not the order).
IMPORTS = [
    "DE4SDV_Stakeholders::*", "DE4SDV_TraceVocabulary::LogicalAllocationElement",
    f"{FUNCTIONAL_PACKAGE}::{BOUNDARY}", f"{FUNCTIONAL_PACKAGE}::{FLOW}", f"{FUNCTIONAL_PACKAGE}::{FLOW_USAGE}",
    f"{FUNCTIONAL_PACKAGE}::DrawnScene", *(f"{FUNCTIONAL_PACKAGE}::{p}" for p in (
        "DisplaySceneInbound", "DisplaySpeedInbound", "DisplayWarningRequestInbound", "DisplayContentOutbound",
        "DisplayWarningOutbound")),
    "SAF_Viewpoints::*", "SysideViews::**", "Views::*",
]

#: The phase 6 bans, which name the candidate, its path and its platform, plus the deployment words of phase 7.
FORBIDDEN_IN_DOCS = FORBIDDEN_IN_FUNCTIONS + ("container", "hypervisor")
#: The words the design avoids beside its technology words (D6): no app, virtual machine, guest or instrument.
AVOIDED_WORDS = re.compile(r"(?i)\b(?:apps?|VMs?|guests?|instrument\w*|containers?|hypervisors?)\b")

#: The texts of record of the design, pinned whole: the header, paragraph by paragraph.
HEADER_PARAGRAPHS = [
    "DE4SDV HMI display logical architecture.",
    "INC-HMI-001, phase 7: the logical architecture of the HMI display. What technology-independent logical elements "
    "realize the five functions of phase 6?",
    "The decomposition subject is the system of interest itself, one level below the functional boundary of phase 6: "
    "HmiDisplayLogicalSystem specializes HmiDisplayFunctionalBoundary, so it keeps the five boundary ports and gives "
    "the display an inside of three logical elements. The context elements of phase 2 stay outside and undivided. "
    "Functions stay where phase 6 put them; each is allocated to the element that carries it by a native allocation "
    "(allocatedTo), a responsibility assignment, not a realization, deployment or runtime claim.",
    "Three elements for five functions (owner decision of 2026-11-24). Functions share an element when nothing "
    "requires them to be separately placeable, and split where a requirement constrains the exchange between them or "
    "demands that one keeps working when the other does not. The scene drawer carries the drawing of the scene alone: "
    "REQ-HMI-009 sets the drawing of the scene apart from the drawing of the vehicle speed and the collision warning, "
    "and REQ-HMI-008 asks the speed and the warning to go on through each outage of the drawing of the scene. The "
    "presenter carries the judging of the currency, the showing of the content and the giving of the warning: the "
    "three share the currency verdict, and no requirement asks one of them to go on when another does not. The "
    "identity recorder stands alone because the record covers both other elements and comes before the first frame of "
    "either, so phase 8 realizes it beside their software, not inside either.",
    "The drawn scenes are the one exchange between elements. Phase 6 allocated REQ-HMI-001 and REQ-HMI-002 to the "
    "functions at both of its ends, and their stop leaves the vehicle speed and the warning going, as REQ-HMI-008 "
    "asks. REQ-HMI-009 keeps the paths of the inputs inside the boundary: each element takes its inputs from the "
    "boundary by delegations of its own, and phase 8 carries the requirement by the elements it places on those paths. "
    "REQ-HMI-010 orders the record before the first frame; phase 6 holds that order by succession, with no item, so it "
    "crosses no exchange here. Nothing here names a computer, a process, a transport or a signal catalogue.",
]

#: The doc of each inner port definition.
PORT_DOCS = {
    "DrawnSceneOutbound":
        "The output port of the drawn scenes: the scene drawer gives one for each scene that it draws, and none while "
        "it is out.",
    "DrawnSceneInbound":
        "The input port of the drawn scenes: the presenter takes them, and goes on when they stop.",
}

#: The doc of each element definition: what it carries, and why it stands alone.
ELEMENT_DOCS = {
    "DisplayIdentityRecorder":
        "Carries the recording of the display identity: before the first frame of the HMI display in each run, it "
        "records the display identity, whose parts the requirements name one by one. The record covers the scene "
        "drawer and the presenter alike and comes before the first frame of either, so it is a responsibility of its "
        "own: phase 8 realizes it beside the software of both, not inside either. It exchanges nothing with another "
        "element: phase 6 orders the record before the first frame by succession, with no item.",
    "SceneDrawer":
        "Carries the drawing of the scene: it draws each scene that reaches the HMI display, or a newer one, with the "
        "object that the system acts on, when the scene has one, as an element of its own, and gives each scene that "
        "it draws, with the time of that scene, to the presenter, and none while it, or the environment that hosts it, "
        "is out. It is the only element that draws the scene, and it takes nothing from another element. It stands "
        "alone because REQ-HMI-009 sets the drawing of the scene apart from the drawing of the vehicle speed and the "
        "collision warning, and the other elements go on through each of its outages: phase 8 realizes it on the "
        "software that draws the scene, apart from the presenter.",
    "DisplayPresenter":
        "Carries what the driver gets from the HMI display: it judges the currency of each element and of the warning "
        "request, shows the drawn scene and the vehicle speed, each element as outdated while it is outdated and the "
        "collision warning as unavailable while the warning request is outdated, and gives the collision warning on "
        "the display and as a sound. The three functions share the currency verdict, and no requirement asks one of "
        "them to go on when another does not, so they share one element. It takes the scene only to judge its "
        "currency, and nothing from the scene drawer but the drawn scenes, so it goes on through each outage of the "
        "drawing of the scene. Phase 8 realizes it on the side that draws the vehicle speed and the collision warning, "
        "apart from the scene drawer.",
}

#: The doc of the logical system.
SYSTEM_DOC = (
    "The HMI display of phase 2, one level inside the functional boundary of phase 6: the same system, now with its "
    "three logical elements and the exchanges between them. The boundary ports are inherited and delegated to the "
    "elements that take or provide their items: the scene goes to the scene drawer and to the presenter, the vehicle "
    "speed and the warning request to the presenter, and what the display shows and the collision warning leave from "
    "the presenter. Inside, the drawn scenes go from the scene drawer to the presenter, the one exchange between "
    "elements. No exchange runs from the presenter to another element, nothing runs into the scene drawer from another "
    "element, and the identity recorder exchanges nothing. This definition names no computer, process, transport or "
    "technology. hmiDisplayLogicalSystem is its usage for the views, which draw usages. It depicts the context's "
    "hmiDisplay, whose definition this one specializes, and is bound to nothing.")

#: The doc of its one usage, for the views.
USAGE_DOC = (
    "The HMI display as the views draw it: the one usage of the logical definition. It depicts the context's "
    "hmiDisplay and is bound to nothing.")

#: The doc of each concern of phase 7, naming its holders.
CONCERN_DOCS = {
    "hmiDisplayLogicalStructureConcern":
        "System architects and software developers need the logical elements of the HMI display, one level inside its "
        "functional boundary, each with the responsibility it carries and its ports, before phase 8 places software on "
        "them: which elements there are, and why each stands alone.",
    "hmiDisplayFunctionMappingConcern":
        "System architects and verification engineers need each function of phase 6 allocated to the logical element "
        "that carries it, and each element carrying a function: phase 8 places the elements, and phase 10 verifies "
        "each requirement on the functions of its element.",
    "hmiDisplayInternalExchangeConcern":
        "Systems engineers and software developers need the exchanges between the logical elements of the HMI display, "
        "the item each carries and its direction: the drawn scenes, the one exchange between elements, which carries "
        "REQ-HMI-001 and REQ-HMI-002 across two elements and whose stop leaves the vehicle speed and the warning going "
        "(REQ-HMI-008); and the boundary items delegated to the elements that take or provide them, on paths that "
        "REQ-HMI-009 keeps inside the boundary. Phase 8 places each exchange on a technology.",
}

#: The grid of the matrix: (title, description, row axis, column axis), pinned whole.
GRID = (
    "HMI display function-to-logical-element mapping",
    "Maps the five functions of the HMI display to the three logical elements that carry them.",
    "system functions (action usages)",
    "logical elements (part usages)",
)

#: The guide: its Status line, its line in the frame and the next obligation, as phase 7 moves them.
GUIDE_STATUS = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification, "
    "Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture and Phase 7 logical "
    "architecture, proposal.**")
GUIDE_NEXT = (
    "The next model obligation is **Phase 8**: the physical and software realization, which allocates each logical "
    "element to a physical element; its first gate is `logicalElementAllocatedToPhysicalElement`.")
GUIDE_HEADING = "## Logical architecture (Phase 7)"
GUIDE_LINK = "../../textual-notation-of-model/packages/features/hmi/hmi_display_logical_architecture.sysml"
GUIDE_FRAME_LINE = (f"- [SysML logical architecture]({GUIDE_LINK}): the Phase 7 logical architecture of the HMI "
                    "display.")

#: The guide's Phase 7 section, block by block: the opening, with the link to the package.
GUIDE_OPENING = (
    "The [logical architecture](" + GUIDE_LINK + ") "
    "answers what technology-independent logical elements realize the five functions. The decomposition subject is the "
    "system of interest itself: `HmiDisplayLogicalSystem` specializes the functional boundary of Phase 6, keeps its "
    "five ports and owns the display's inside, one level below the boundary. The context elements of Phase 2 stay "
    "outside and undivided. The package's one usage of the definition, `hmiDisplayLogicalSystem`, exists for the "
    "views, which draw usages; it depicts the context's `hmiDisplay`, whose definition `HmiDisplayLogicalSystem` "
    "specializes, and is bound to nothing.")

#: The owner's decision, with its date and the cut rule.
GUIDE_DECISION = (
    "The owner decided on three logical elements for the five functions (2026-11-24). Functions share an element when "
    "nothing requires them to be separately placeable, and split where a requirement constrains the exchange between "
    "them or demands that one keeps working when the other does not:")

#: One bullet per element, after its name, in order.
GUIDE_ELEMENTS = {
    "Scene drawer":
        "carries `drawScene` alone. REQ-HMI-009 sets the drawing of the scene apart from the drawing of the vehicle "
        "speed and the collision warning, and REQ-HMI-008 asks the speed and the warning to go on through each outage "
        "of the drawing of the scene.",
    "Presenter":
        "carries `judgeCurrency`, `showContent` and `giveWarning`. The three share the currency verdict, and no "
        "requirement asks one of them to go on when another does not. It takes nothing from the scene drawer but the "
        "drawn scenes, so it goes on through each outage of the drawing.",
    "Identity recorder":
        "carries `recordDisplayIdentity`. The record covers both other elements and comes before the first frame of "
        "either, so Phase 8 realizes it beside their software, not inside either.",
}

#: The allocations and the exchanges.
GUIDE_EXCHANGES = (
    "Each function is allocated to its element by a native allocation from the definition-nested function usage Phase "
    "6 allocated the requirements to; the allocation is a responsibility assignment, not a realization, deployment or "
    "runtime claim. The exchanges are connections between typed ports. The boundary items are delegated from the "
    "inherited ports: the scene to the scene drawer and to the presenter, the vehicle speed and the warning request to "
    "the presenter, and what the display shows and the collision warning from the presenter. Inside, the drawn scenes "
    "go from the scene drawer to the presenter, the one exchange between elements. The drawn scenes carry REQ-HMI-001 "
    "and REQ-HMI-002 across two elements, and their stop leaves the vehicle speed and the warning going, as "
    "REQ-HMI-008 asks. Nothing runs from the presenter to another element, and the identity recorder exchanges "
    "nothing. REQ-HMI-009 keeps the paths of the inputs inside the boundary and stays with Phase 8, which carries it "
    "by the elements it places on those paths; Phase 8 places each exchange on a technology. No element, port or "
    "exchange names a computer, a process, a transport or a signal catalogue.")

#: What crosses the boundary, and the deliberate absences with the decision behind each.
GUIDE_BOUNDARY = (
    "What crosses the boundary agrees in three places: the boundary flows of the operational context, the ports of "
    "Phase 6 and the delegations of Phase 7. Nothing goes back to the candidate or to the command and warning path, "
    "and nothing comes from the driver, who only receives. No identity port: Phase 6 orders the record before the "
    "first frame by succession, with no item, so it crosses no exchange. No liveness signal of its own: the drawn "
    "scenes carry an outage of the drawing to the presenter, as Phase 6 decided. Phase 7 shows no timing: Phase 8 "
    "divides the 0.1 s of the display among the elements it places.")

#: The three concerns and the three views.
GUIDE_VIEWS = (
    "Three concerns of this phase are held by the parties they serve: the structure by system architects and software "
    "developers, the function mapping by system architects and verification engineers, and the internal exchanges by "
    "systems engineers and software developers. One view answers each, per the method's list of views per phase: the "
    "structure as a tree of the SAF System Structure Definition viewpoint, the mapping as a matrix of function by "
    "logical element of the System Function Mapping viewpoint, and the exchanges as an interconnection of the System "
    "Internal Exchange viewpoint. The phase publishes three views, listed in "
    "[`VIEWS.md`](../../textual-notation-of-model/packages/features/hmi/VIEWS.md).")

#: The closing paragraph: what the test pins.
GUIDE_CLOSING = (
    "`tests/test_hmi_display_logical_architecture.py` pins the system, the elements and their ports, the exchanges, "
    "the allocations, the views and this section.")


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


def _system_body() -> str:
    return braced_body(_code(), f"part def {SYSTEM} :> {BOUNDARY}")


def _connections() -> list[tuple[str, str, str]]:
    return re.findall(r"\bconnection\s+(\w+)\s+connect\s+([\w.]+)\s+to\s+([\w.]+)\s*;", _system_body())


def _allocations() -> list[tuple[str, str, str]]:
    code = _code()
    rows = re.findall(r"\ballocation\s+(\w+)(?:\s*:\s*(\w+))?\s+allocate\s+(\S+)\s+to\s+([^\s;{]+)\s*;", code)
    assert all(not typed for _, typed, _, _ in rows), "allocations are untyped, as in phase 6"
    assert len(rows) == len(re.findall(r"\ballocat(?:e|ion)\b", code)) / 2, "every allocation has the one form"
    return [(name, source, target) for name, _, source, target in rows]


def _docs() -> list[str]:
    """Every comment and doc text of the package, flattened."""
    return [_flat(text) for text in re.findall(r"/\*(.*?)\*/", _raw(), re.S)] + \
        [_flat(text) for text in re.findall(r"//([^\n]*)", _raw())]


def _port_items() -> dict[str, tuple[str, str, str]]:
    """Every port definition of phase 6 and of this package -> its one directed item (direction, name, type)."""
    items = {}
    for path in (FUNCTIONAL, MODEL):
        code = strip_comments(path.read_text(encoding="utf-8"))
        for name in re.findall(r"\bport\s+def\s+(\w+)\s*\{", code):
            found = re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", braced_body(code, f"port def {name}"))
            assert len(found) == 1, name
            items[name] = found[0]
    return items


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _guide_section(guide: str) -> str:
    return guide.split(GUIDE_HEADING + "\n", 1)[1].split("\n## ", 1)[0]


def test_the_charter_names_the_package_after_the_functional_architecture():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part hmiDisplayCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    assert names.index(PACKAGE) == names.index(FUNCTIONAL_PACKAGE) + 1
    assert names.count(PACKAGE) == 1
    assert re.search(rf"\bpackage\s+{PACKAGE}\s*\{{", _code())


def test_the_header_states_its_text_of_record():
    assert _header_paragraphs() == HEADER_PARAGRAPHS


def test_the_package_imports_one_by_one():
    imports = re.findall(r"^\s*private\s+import\s+([\w:*]+)\s*;", _code(), re.M)
    assert sorted(imports) == sorted(IMPORTS), "the imports, each once; their order is free"
    assert len(re.findall(r"\bimport\b", _code())) == len(IMPORTS)
    assert not re.search(r"\bpublic\s+import\b", _code())


def test_the_three_elements_are_logical_allocation_elements_and_nothing_else_is():
    code = _code()
    declared = re.findall(r"\bpart\s+def\s+(\w+)\s*:>\s*LogicalAllocationElement\s*\{", code)
    assert declared == [definition for definition, _ in ELEMENTS.values()]
    assert len(re.findall(r"\bLogicalAllocationElement\b", code)) == len(ELEMENTS) + 1, "the import and the three"
    assert re.findall(r"\bpart\s+def\s+(\w+)", code) == declared + [SYSTEM]
    for definition, _ in ELEMENTS.values():
        assert _doc(f"part def {definition} :> LogicalAllocationElement").startswith("Carries "), definition


def test_the_system_is_the_boundary_of_phase_6_one_level_inside_and_owns_the_three_elements():
    code = _code()
    # the exact header: the logical system is the system of interest at its phase 6 boundary, not a new one
    assert re.search(rf"\bpart\s+def\s+{SYSTEM}\s*:>\s*{BOUNDARY}\s*\{{", code)
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    assert re.search(rf"\bpart\s+def\s+{BOUNDARY}\s*:>\s*{SOI}\s*\{{", functional), "the chain runs to the SoI"
    body = _direct(_system_body())
    owned = re.findall(r"^\s*part\s+(\w+)\s*:\s*(\w+)\s*;", body, re.M)
    assert owned == [(usage, definition) for usage, (definition, _) in ELEMENTS.items()]
    assert len(re.findall(r"\bpart\b", body)) == len(ELEMENTS)
    # one usage of the logical definition, for the views (SysIDE draws usages); no usage of the boundary or the SoI
    assert re.findall(rf"^\s*part\s+(\w+)\s*:\s*{SYSTEM}\s*[{{;=]", code, re.M) == [SYSTEM_USAGE]
    assert re.findall(rf"\b(\w+)\s*:(?![:>])\s*{SYSTEM}\b", code) == [SYSTEM_USAGE], "nothing else is typed by it"
    # the usage adds nothing to the definition: its body holds its doc and nothing else
    assert braced_body(code, f"part {SYSTEM_USAGE} : {SYSTEM}").split() == ["doc"], "the usage adds nothing"
    # the package's only part usage is that one; the only usages of the elements are the system's three parts
    package = _direct(braced_body(code, f"package {PACKAGE}"))
    assert re.findall(r"\bpart\s+(?!def\b)(\w+)\s*:", package) == [SYSTEM_USAGE]
    roles = "|".join(definition for definition, _ in ELEMENTS.values())
    assert re.findall(rf"\b(\w+)\s*:(?![:>])\s*({roles})\b", code) == [
        (usage, definition) for usage, (definition, _) in ELEMENTS.items()]
    # the seven connections are the system's, and the eight ports are the elements'
    assert len(re.findall(r"\bconnect\b", code)) == len(CONNECTIONS)
    assert len(re.findall(r"\bport\s+(?!def\b)\w+\s*:", code)) == sum(len(ports) for ports in PORTS.values()) == 8
    assert not re.search(rf"(?<!:):(?!:)\s*(?:{BOUNDARY}|{SOI})\b", code), "no usage of the boundary or the SoI"
    assert not re.search(rf"\b{SOI}\b", code)
    # the boundary ports are inherited, never redeclared
    assert not re.search(r"\bport\b", body)


@pytest.mark.parametrize("definition", sorted(PORTS), ids=sorted(PORTS))
def test_each_element_declares_exactly_its_ports(definition):
    body = braced_body(_code(), f"part def {definition} :> LogicalAllocationElement")
    assert re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", body) == PORTS[definition]
    assert len(re.findall(r"\bport\b", body)) == len(PORTS[definition])
    assert not re.search(r"\b(part|action|perform|flow|item|attribute|connection)\b", body), \
        "an element carries functions by allocation only, and has ports and nothing else"


def test_the_identity_recorder_has_no_port_and_no_exchange():
    body = braced_body(_code(), "part def DisplayIdentityRecorder :> LogicalAllocationElement")
    assert body.split() == ["doc"], "a doc and nothing else"
    assert not any("displayIdentityRecorder" in end for _, *ends in _connections() for end in ends)


def test_the_inner_ports_carry_the_drawn_scenes_of_phase_6_in_one_direction():
    code = _code()
    assert re.findall(r"\bport\s+def\s+(\w+)", code) == list(INTERNAL_PORT_ITEMS)
    for port_def, (direction, item, item_type) in INTERNAL_PORT_ITEMS.items():
        body = braced_body(code, f"port def {port_def}")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [(direction, item, item_type)], \
            port_def
        assert len(re.findall(r"\bitem\b", body)) == 1, port_def
    assert not re.search(r"\bitem\s+def\b", code), "the items are phase 2's and phase 6's"
    for port, port_def in BOUNDARY_PORTS.items():
        assert not re.search(rf"\bport\s+def\s+{port_def}\b", code), "the boundary port definitions are phase 6's"
    # the item is the one drawScene gives out and showContent and judgeCurrency take in phase 6
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    assert re.search(r"\bout\s+drawnScene\s*:\s*DrawnScene\s*;",
                     braced_body(functional, "action def DrawScene :> AllocatableFunction"))
    assert re.search(r"\bin\s+drawnScene\s*:\s*DrawnScene\s*;",
                     braced_body(functional, "action def ShowContent :> AllocatableFunction"))
    boundary = braced_body(functional, f"part def {BOUNDARY} :> {SOI}")
    assert dict(re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", boundary)) == BOUNDARY_PORTS


def test_the_exchanges_are_exactly_these_seven_connections():
    connections = _connections()
    assert connections == CONNECTIONS
    body = _system_body()
    assert len(re.findall(r"\bconnect\b", body)) == len(CONNECTIONS)
    assert len(re.findall(r"\bconnection\b", _code())) == len(CONNECTIONS)
    assert not re.search(r"\b(flow|bind|binding|interface|message|succession)\b", _code()), \
        "the file's only exchanges are the system's seven connections"
    # every end of a connection names a declared port of its element, or an inherited boundary port
    for _, *ends in connections:
        for end in ends:
            if "." in end:
                element, port = end.split(".")
                assert port in dict(PORTS[ELEMENTS[element][0]]), end
            else:
                assert end in BOUNDARY_PORTS, end


def test_each_connection_runs_in_the_direction_of_its_port_items():
    items = _port_items()
    for name, source, target in _connections():
        ends = []
        for end in (source, target):
            if "." in end:
                element, port = end.split(".")
                ends.append(("part", items[dict(PORTS[ELEMENTS[element][0]])[port]]))
            else:
                ends.append(("frame", items[BOUNDARY_PORTS[end]]))
        (kind_a, (dir_a, _, type_a)), (kind_b, (dir_b, _, type_b)) = ends
        kind = {("frame", "in", "part", "in"): "inbound delegation",
                ("part", "out", "frame", "out"): "outbound delegation",
                ("part", "out", "part", "in"): "exchange"}.get((kind_a, dir_a, kind_b, dir_b))
        assert kind == CONNECTION_KINDS[name], (name, kind)
        assert type_a == type_b, (name, type_a, type_b)


def test_the_exchanges_run_one_way_and_the_drawn_scenes_are_the_one_between_elements():
    connections = _connections()
    presenter, drawer = "displayPresenter.", "sceneDrawer."
    for name, source, target in connections:
        # nothing the presenter provides goes to another element
        if source.startswith(presenter):
            assert "." not in target, name
        # nothing goes into the scene drawer but the scene from the boundary
        if target.startswith(drawer):
            assert name == "sceneToDrawerDelegation" and "." not in source, name
        assert "displayIdentityRecorder" not in source + target, name
    between = [name for name, source, target in connections if "." in source and "." in target]
    assert between == ["drawnSceneExchange"]
    # what the display shows and the collision warning leave from the presenter only; the scene reaches two elements
    assert {source for _, source, target in connections if target in ("contentOut", "warningOut")} == {
        "displayPresenter.contentOut", "displayPresenter.warningOut"}
    assert [target for _, source, target in connections if source == "sceneIn"] == [
        "sceneDrawer.sceneIn", "displayPresenter.sceneIn"]


def test_the_drawn_scenes_carry_the_two_requirements_phase_6_gave_both_their_ends():
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    assert re.search(r"\bflow\s+from\s+drawScene\.drawnScene\s+to\s+showContent\.drawnScene\s*;", functional)
    carriers = {function: element for _, function, element in ALLOCATIONS}
    ends = {carriers["drawScene"], carriers["showContent"]}
    assert ends == {"sceneDrawer", "displayPresenter"}, "the drawn scenes cross between two elements"
    for identity, requirement in DRAWN_SCENE_REQUIREMENTS.items():
        allocated = set(re.findall(rf"\ballocate\s+{requirement}\s+to\s+{FLOW}::(\w+)\s*;", functional))
        assert allocated == {"drawScene", "showContent"}, (identity, allocated)
    exchange = _doc("concern hmiDisplayInternalExchangeConcern : ConceptualInternalExchangeConcern")
    assert ("the drawn scenes, the one exchange between elements, which carries REQ-HMI-001 and REQ-HMI-002 across "
            "two elements") in exchange
    assert "Phase 6 allocated REQ-HMI-001 and REQ-HMI-002 to the functions at both of its ends" in \
        " ".join(_header_paragraphs())


def test_each_function_is_allocated_to_the_element_the_owner_decided():
    rows = _allocations()
    assert rows == [(name, f"{FLOW}::{function}", f"{SYSTEM}::{element}") for name, function, element in ALLOCATIONS]
    # the owner's decision of 2026-11-24: three elements for five functions
    carried = {}
    for _, function, element in ALLOCATIONS:
        carried.setdefault(element, []).append(function)
    assert carried == {usage: list(functions) for usage, (_, functions) in ELEMENTS.items()}
    assert carried["sceneDrawer"] == ["drawScene"], "the scene drawer carries the drawing of the scene alone"
    assert carried["displayPresenter"] == ["judgeCurrency", "showContent", "giveWarning"]
    assert carried["displayIdentityRecorder"] == ["recordDisplayIdentity"]
    # each function goes to one element, and each element carries a function
    assert sorted(function for _, function, _ in ALLOCATIONS) == sorted(FUNCTIONS)
    assert "(owner decision of 2026-11-24)" in _header_paragraphs()[3]


def test_the_functions_allocated_are_the_five_of_phase_6():
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    flow = braced_body(functional, f"action def {FLOW}")
    declared = re.findall(r"^\s*action\s+(\w+)\s*:\s*\w+\s*\{", flow, re.M)
    assert declared == list(FUNCTIONS)


@pytest.mark.parametrize("definition", sorted(ELEMENT_DOCS), ids=sorted(ELEMENT_DOCS))
def test_each_element_states_its_text_of_record(definition):
    assert _doc(f"part def {definition} :> LogicalAllocationElement") == ELEMENT_DOCS[definition]


def test_the_system_its_usage_and_its_ports_state_their_texts_of_record():
    assert _doc(f"part def {SYSTEM} :> {BOUNDARY}") == SYSTEM_DOC
    assert _doc(f"part {SYSTEM_USAGE} : {SYSTEM}") == USAGE_DOC
    for port_def, text in PORT_DOCS.items():
        assert _doc(f"port def {port_def}") == text, port_def
    for comment in ("The boundary items, delegated from the inherited ports of phase 6.",
                    "The exchange between the elements."):
        assert re.findall(r"//\s*(.*)", braced_body(_raw(), f"part def {SYSTEM} :> {BOUNDARY}")).count(comment) == 1


def test_the_package_publishes_exactly_one_view_per_question():
    declared = re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M)
    assert declared == list(VIEWS)


@pytest.mark.parametrize("view_name", sorted(VIEWS), ids=sorted(VIEWS))
def test_each_view_frames_its_concern_and_exposes_its_content(view_name):
    view_type, render, exposes, frames, viewpoint_usage = VIEWS[view_name]
    code = _code()
    header = rf"\bview\s+{view_name}\s*" + (rf":\s*{re.escape(view_type)}\s*" if view_type else "") + r"\{"
    assert re.search(header, code), view_name
    view = braced_body(code, f"view {view_name}" + (f" : {view_type}" if view_type else ""))
    viewpoint = braced_body(view, f"viewpoint {viewpoint_usage}")
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == frames
    assert re.search(rf"viewpoint\s+{viewpoint_usage}\s*:\s*{VIEWPOINTS[frames[0]]}\s*\{{", view), view_name
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
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", cells) == [f"{PACKAGE}::*"]
    assert "attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;" in cells
    assert not re.search(r"\bfilter\b", view), "the allocations are the cells; no filter of the matrix hides them"
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"matrix-{MATRIX_VIEW}"]
    assert (metadata.title, metadata.description, metadata.row_label, metadata.column_label) == GRID


def test_the_diagrams_draw_the_elements_without_the_allocations():
    """SysIDE draws every allocation of the view's package as a node unless filtered (precedent render)."""
    for view_name in (STRUCTURE_VIEW, EXCHANGE_VIEW):
        view = braced_body(_code(), f"view {view_name}")
        assert re.findall(r"\bfilter\s+([^;]+);", view) == ["not (@ SysML::AllocationUsage)"], view_name
    view = braced_body(_code(), f"view {EXCHANGE_VIEW}")
    assert re.findall(r"\battribute\s+(\w+)\s*=\s*([^;]+);", view) == [("depth", "-1"), ("showAnnotationRows", "false")]
    assert "attribute" not in braced_body(_code(), f"view {STRUCTURE_VIEW}")


@pytest.mark.parametrize("concern_name", sorted(CATALOGUE_CONCERNS), ids=sorted(CATALOGUE_CONCERNS))
def test_each_phase_7_concern_is_typed_by_the_catalogue_and_held_by_the_party_it_serves(concern_name):
    catalogue, stakeholders = CATALOGUE_CONCERNS[concern_name]
    concern = braced_body(_code(), f"concern {concern_name} : {catalogue}")
    members = re.findall(r"\b(subject|stakeholder)\b", concern)
    assert members and members[0] == "subject"
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern) == stakeholders
    assert _doc(f"concern {concern_name} : {catalogue}") == CONCERN_DOCS[concern_name]
    assert len(re.findall(r"\bconcern\s+\w+\s*:", _code())) == len(CATALOGUE_CONCERNS)


def test_no_doc_of_the_package_and_no_sentence_of_the_guide_section_names_a_technology():
    # every /* */ block (each doc and section comment) and every // line of the package
    docs = _docs()
    assert len(docs) >= 17, "the population of the check must not be vacuous"
    for text in docs:
        assert not PAST_BEHAVIOR.search(text) and not APPROVAL.search(text), ("a run or approval claim", text[:80])
    prose = re.sub(r"`[^`]*`|\]\([^)]*\)", " ", _guide_section(_guide()))
    for text in docs + [" ".join(prose.split())]:
        found = [word for word in FORBIDDEN_IN_DOCS if re.search(rf"\b{re.escape(word)}", text, re.I)]
        found += [word for word in TECHNOLOGY_NAMES if re.search(rf"\b{re.escape(word)}\b", text)]
        found += DESIGN_TECHNOLOGY_WORDS.findall(text) + AVOIDED_WORDS.findall(text)
        assert not found, (text[:80], found)


def test_the_package_types_no_signal_and_adds_no_trace_of_req_hmi_009():
    code = _code()
    assert "COVESA_VSS" not in code and "DE4SDV_VSS_Extensions" not in code
    assert not re.search(r":\s*Vehicle_\w+", code), "VSS typing starts at phase 8"
    assert not re.search(r"\b(ref\s+part|perform|exhibit|state\s+def|item\s+def|flow|dependency|satisfy)\b", code)
    assert not re.search(rf"^\s*part\s+\w+\s*:\s*{SYSTEM}\s*=", code, re.M), "the usage is bound to nothing"
    assert not re.search(r":>>?\s*\w*[Cc]ontext\w*|hmiDisplayOperationalContext|\bhmiDisplay\b", code), \
        "the usage is bound to no context part"
    # REQ-HMI-009 stays with phase 8 (phase 6 decision D4); no allocation names a requirement
    assert not re.search(r"\breq[A-Z]\w*", code), "no requirement is allocated or traced here"
    assert "NeedsRequirements" not in code


def test_the_package_declares_no_name_that_another_model_package_declares():
    # Two packages may declare the same name, but a lookup by name then finds two elements, and a check that
    # reads a folder by name sees one increment's element as the other's. The elements' ports repeat the five
    # boundary port names of phase 6, as the precedent's do, and the viewpoint usages keep the names that other
    # logical packages use too; those are left out.
    kinds = r"(?:part def|port def|part|port|concern|view|allocation|connection)"
    declared = set(re.findall(rf"(?m)^(?:  |    ){kinds}\s+(\w+)", _code()))
    declared -= set(BOUNDARY_PORTS)
    assert len(declared) >= 29, "the population of the check must not be vacuous"
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


def test_the_allocation_file_is_governed_with_its_three_endpoint_definitions():
    import test_trace_allocation_completeness as trace

    assert trace.HMI_L == MODEL
    assert trace.ALLOCATION_FILES[trace.HMI_L] == (
        (trace.HMI_L, trace.HMI_F), {(trace.FUNCTION, trace.LOGICAL): len(ALLOCATIONS)}, {},
        (trace.FUNCTION, trace.LOGICAL))
    assert trace.GOVERNED[trace.HMI_L] == (trace.LOGICAL, {d for d, _ in ELEMENTS.values()})
    assert trace.LINEAGE_FILES.index(trace.HMI_L) == trace.LINEAGE_FILES.index(trace.HMI_F) + 1
    assert trace.NOT_ENDPOINTS[trace.HMI_L] == {SYSTEM}


def test_no_text_of_phase_7_carries_the_excluded_word():
    for text in (_raw(), _guide_section(_guide())):
        words = set(re.findall(r"[a-z0-9]+", text.lower()))
        assert len(words) >= 100
        assert EXCLUDED_WORD_SHA256 not in {hashlib.sha256(word.encode()).hexdigest() for word in words}


def test_the_guide_has_a_phase_7_section_and_names_phase_8_next():
    guide = _guide()
    assert guide.count(GUIDE_HEADING + "\n") == 1
    assert guide.index("## Functional architecture (Phase 6)") < guide.index(GUIDE_HEADING) \
        < guide.index("## What the framing already records as open")
    raw_section = _guide_section(guide)
    assert f"]({GUIDE_LINK})" in raw_section
    blocks = [" ".join(block.split()) for block in re.split(r"\n\s*\n", raw_section.strip())]
    assert blocks == [GUIDE_OPENING, GUIDE_DECISION,
                      " ".join(f"- **{name}** {text}" for name, text in GUIDE_ELEMENTS.items()),
                      GUIDE_EXCHANGES, GUIDE_BOUNDARY, GUIDE_VIEWS, GUIDE_CLOSING], \
        "every block of the section, whole and in order, as it says"
    bullets = raw_section.strip().split("\n\n")[2]
    elements = [(match[1], " ".join(match[2].split()))
                for match in re.finditer(r"(?ms)^- \*\*(.+?)\*\* (.*?)(?=^- |\Z)", bullets)]
    assert elements == list(GUIDE_ELEMENTS.items()), "one bullet per element, in order"
    assert all(len(line) <= 79 or "](" in line for line in raw_section.splitlines()), "the guide wraps at 79"
    flat = " ".join(guide.split())
    assert flat.count(GUIDE_STATUS) == 1
    assert "and Phase 6 functional architecture, proposal.**" not in flat, "the status line moved to phase 7"
    frame = " ".join(guide.split("## Authoritative frame", 1)[1].split("\n## ", 1)[0].split())
    assert frame.count(GUIDE_FRAME_LINE) == 1, "the frame links the package, as it links each earlier phase"
    nxt = " ".join(guide.split("## Next obligation and execution limits", 1)[1].split("\n## ", 1)[0].split())
    assert nxt.count(GUIDE_NEXT) == 1
    assert "The next model obligation is **Phase 7**" not in flat
    assert flat.count("The next model obligation is") == 1
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert ("`python -m pytest tests/test_hmi_display_framing.py tests/test_hmi_display_functional_architecture.py "
            "tests/test_hmi_display_logical_architecture.py -q`") in check
