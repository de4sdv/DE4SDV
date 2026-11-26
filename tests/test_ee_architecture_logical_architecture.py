"""Content pins for the E/E architecture logical architecture (phase 7), not semantic validation.

INC-EE-001 phase 7 gives the vehicle network an inside: the technology-independent logical elements that realize the
five functions of phase 6, one level below the functional boundary. Method Check holds the DefineLogicalArchitecture
rule (each function allocated to a logical element by a native allocation; advisory, each logical element carries a
function). These pins hold what the design settled on top of it:

- the decomposition subject is the system of interest: EEVehicleNetworkLogicalSystem specializes the functional
  boundary of phase 6, keeps its two ports and owns the three logical elements; its one usage,
  eeVehicleNetworkLogicalSystem, exists for the views (SysIDE draws usages, not definitions), depicts the context's
  vehicleNetwork and is bound to nothing;
- three logical elements for five functions (owner decision of 2026-11-26): the identity recorder carries
  recordNetworkIdentity and has no port, the command carrier carries takeDrivingCommand and carryDrivingCommand, and
  the actuation end carries checkDrivingCommand and applyDrivingCommand;
- each function allocated to its logical element, by untyped native allocations from the definition-nested function
  usages that phase 6 allocated the requirements to;
- the exchanges as connections between typed ports: two delegations from the inherited ports and one exchange, the
  carried driving commands from the command carrier to the actuation end; nothing runs from the actuation end to
  another logical element, nothing into the command carrier from another logical element, and no connection touches
  the identity recorder; the driving command enters by one delegation only, the one input that REQ-EE-002 keeps;
- one view per SAF question of phase 7: the structure as a tree, the function mapping as a matrix, the internal
  exchange as an interconnection, each framed by a phase 7 concern typed by the catalogue;
- no technology, platform, transport or claim in any doc, no vehicle signal specification, and no trace of
  REQ-EE-001 or REQ-EE-003, which phase 8 carries;
- the texts of record of the design whole, and the guide's Phase 7 section block by block.

The structural guards read the code with docs and notes removed, so a doc word cannot trip them, and each reads the
whole file, not one body: the exchange ban, the kinds the package does not hold, and the counts of part usages, port
usages and connects. A skeleton of the package, every declaration at its own depth with the docs left to the texts
of record, pins its code whole; the `//` notes of the file are exactly the two of the system definition.
"""

from itertools import zip_longest
from pathlib import Path
import re

import pytest

from sysml_shapes import braced_body, strip_comments
from test_ee_architecture_framing import APPROVAL
from test_ee_architecture_functional_architecture import (BOUNDARY_PORT_USAGES, CLAUSE_NUMBER, MODE_WORD,
                                                          NETWORK_NAMES, PAST_BEHAVIOR, ROUTE_AND_TECHNOLOGY)
from test_ee_architecture_functional_architecture import FUNCTIONS as PHASE_6_FUNCTIONS

ROOT = Path(__file__).resolve().parents[1]
EE = ROOT / "textual-notation-of-model/packages/features/ee"
MODEL = EE / "ee_architecture_logical_architecture.sysml"
FUNCTIONAL = EE / "ee_architecture_functional_architecture.sysml"
FRAMING = EE / "ee_architecture_framing.sysml"
GUIDE = ROOT / "docs/guides/ee-architecture-increment.md"
MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
PACKAGE = "DE4SDV_EEArchitectureLogicalArchitecture"
FUNCTIONAL_PACKAGE = "DE4SDV_EEArchitectureFunctionalArchitecture"
SYSTEM = "EEVehicleNetworkLogicalSystem"
SYSTEM_USAGE = "eeVehicleNetworkLogicalSystem"
BOUNDARY = "EEVehicleNetworkFunctionalBoundary"
SOI = "EEVehicleNetworkSystem"
FLOW = "EEVehicleNetworkFunctionalFlow"
FLOW_USAGE = "eeVehicleNetworkFunctionalFlow"

#: Each logical element of the system, in the order of the owned parts -> (definition, the functions it carries).
ELEMENTS = {
    "eeIdentityRecorder": ("EEIdentityRecorder", ("recordNetworkIdentity",)),
    "eeCommandCarrier": ("EECommandCarrier", ("takeDrivingCommand", "carryDrivingCommand")),
    "eeActuationEnd": ("EEActuationEnd", ("checkDrivingCommand", "applyDrivingCommand")),
}
#: The five functions of phase 6, in the order of the flow.
FUNCTIONS = tuple(PHASE_6_FUNCTIONS)

#: Each logical element definition -> its ports, in order; the boundary port definitions are those of phase 6.
PORTS = {
    "EEIdentityRecorder": [],
    "EECommandCarrier": [("eeCommandIn", "EEDrivingCommandInbound"),
                         ("eeCarriedCommandOut", "EECarriedCommandOutbound")],
    "EEActuationEnd": [("eeCarriedCommandIn", "EECarriedCommandInbound"), ("eeActuationOut", "EEActuationOutbound")],
}
#: The ports the system inherits from the boundary of phase 6 -> their port definitions.
BOUNDARY_PORTS = dict(BOUNDARY_PORT_USAGES)
#: The inner port definitions of this package -> (direction, item, item type): one item each, one direction.
INTERNAL_PORT_ITEMS = {
    "EECarriedCommandOutbound": ("out", "eeCarriedCommand", "DrivingCommand"),
    "EECarriedCommandInbound": ("in", "eeCarriedCommand", "DrivingCommand"),
}

#: Every connection of the system, in order: the two delegations, then the one exchange between logical
#: elements.
CONNECTIONS = [
    ("eeCommandToCarrierDelegation", "drivingCommandIn", "eeCommandCarrier.eeCommandIn"),
    ("eeActuationFromEndDelegation", "eeActuationEnd.eeActuationOut", "actuationOut"),
    ("eeCommandExchange", "eeCommandCarrier.eeCarriedCommandOut", "eeActuationEnd.eeCarriedCommandIn"),
]
#: The kind of each connection, read from the directions of the port items at its two ends.
CONNECTION_KINDS = {
    "eeCommandToCarrierDelegation": "inbound delegation",
    "eeActuationFromEndDelegation": "outbound delegation",
    "eeCommandExchange": "exchange",
}
#: The three carriage requirements: phase 6 allocated each to carryDrivingCommand alone.
CARRIAGE_REQUIREMENTS = {"REQ-EE-004": "reqDeliverCommandStreamUnchanged",
                         "REQ-EE-005": "reqCarryEachCommandWithin50Ms",
                         "REQ-EE-007": "reqPassDetectionPartsOnAsTaken"}

#: The five allocations, in order -> (name, function, logical element).
ALLOCATIONS = [
    ("eeRecordNetworkIdentityAllocation", "recordNetworkIdentity", "eeIdentityRecorder"),
    ("eeTakeDrivingCommandAllocation", "takeDrivingCommand", "eeCommandCarrier"),
    ("eeCarryDrivingCommandAllocation", "carryDrivingCommand", "eeCommandCarrier"),
    ("eeCheckDrivingCommandAllocation", "checkDrivingCommand", "eeActuationEnd"),
    ("eeApplyDrivingCommandAllocation", "applyDrivingCommand", "eeActuationEnd"),
]

STRUCTURE_VIEW = "eeVehicleNetworkLogicalStructureView"
MATRIX_VIEW = "eeVehicleNetworkFunctionMappingView"
EXCHANGE_VIEW = "eeVehicleNetworkInternalExchangeView"
#: view -> (type or None, render, exposes in order, framed concerns, viewpoint usage)
VIEWS = {
    STRUCTURE_VIEW: (None, "render asTreeDiagram;",
                     [SYSTEM_USAGE] + [f"{SYSTEM_USAGE}::{element}" for element in ELEMENTS],
                     ["eeVehicleNetworkLogicalStructureConcern"], "eeLogicalStructureViewpoint"),
    MATRIX_VIEW: ("MVD::MatrixView", None,
                  [f"{FLOW_USAGE}::{function}" for function in FUNCTIONS]
                  + [f"{SYSTEM}::{element}" for element in ELEMENTS] + [f"{PACKAGE}::*"],
                  ["eeVehicleNetworkFunctionMappingConcern"], "eeFunctionMappingViewpoint"),
    EXCHANGE_VIEW: (None, "render asInterconnectionDiagram;", [SYSTEM_USAGE, f"{SYSTEM_USAGE}::**"],
                    ["eeVehicleNetworkInternalExchangeConcern"], "eeInternalExchangeViewpoint"),
}
VIEWPOINTS = {
    "eeVehicleNetworkLogicalStructureConcern": "SystemStructureDefinitionViewpoint",
    "eeVehicleNetworkFunctionMappingConcern": "SystemFunctionMappingViewpoint",
    "eeVehicleNetworkInternalExchangeConcern": "SystemInternalExchangeViewpoint",
}
#: concern -> (catalogue type, the parties that hold it, in order)
CATALOGUE_CONCERNS = {
    "eeVehicleNetworkLogicalStructureConcern": ("ConceptualStructureConcern", ["SystemArchitect", "SoftwareDeveloper"]),
    "eeVehicleNetworkFunctionMappingConcern": ("ConceptualFunctionMappingConcern",
                                               ["SystemArchitect", "VerificationEngineer"]),
    "eeVehicleNetworkInternalExchangeConcern": ("ConceptualInternalExchangeConcern",
                                                ["SystemsEngineer", "SoftwareDeveloper"]),
}
#: The package's imports, one by one (the set is pinned, not the order).
IMPORTS = [
    "DE4SDV_Stakeholders::*", "DE4SDV_TraceVocabulary::LogicalAllocationElement",
    f"{FUNCTIONAL_PACKAGE}::{BOUNDARY}", f"{FUNCTIONAL_PACKAGE}::{FLOW}", f"{FUNCTIONAL_PACKAGE}::{FLOW_USAGE}",
    f"{FUNCTIONAL_PACKAGE}::EEDrivingCommandInbound", f"{FUNCTIONAL_PACKAGE}::EEActuationOutbound",
    "DE4SDV_DriverAssistanceOperationalContext::DrivingCommand",
    "SAF_Viewpoints::*", "SysideViews::**", "Views::*",
]
#: Every name the package declares, owned ones included (the stakeholder usages keep the catalogue's role names).
DECLARED_NAMES = {
    PACKAGE, "EECarriedCommandOutbound", "EECarriedCommandInbound", "eeCarriedCommand",
    *(d for d, _ in ELEMENTS.values()),
    SYSTEM, *ELEMENTS, *(port for ports in PORTS.values() for port, _ in ports), *(c for c, _, _ in CONNECTIONS),
    SYSTEM_USAGE, *(a for a, _, _ in ALLOCATIONS), *CATALOGUE_CONCERNS, *VIEWS, *(v[4] for v in VIEWS.values()),
}
#: The usage kinds that the name test reads in every other model file, beside every definition kind.
USAGE_KINDS = ("part", "port", "item", "action", "attribute", "state", "requirement", "constraint", "calc",
               "interface", "occurrence", "connection", "allocation", "concern", "view", "viewpoint", "flow",
               "message", "ref", "enum")
#: The two `//` notes of the file, both in the system definition, in order.
NOTES = ["The boundary items, delegated from the inherited ports of phase 6.",
         "The exchange between the logical elements."]

#: The technology words of phase 7 (the design's narrow reading of 2026-11-26), beside the bans of phase 6.
PHASE7_TECH = re.compile(
    r"(?i)\b(?:ECUs?|central\s+computers?|network\s+side|switch(?:es)?|VLANs?|S-?CORE|Eclipse|Zephyr|NXP|QNX|"
    r"Android|hypervisors?|VMs?|virtual\s+machines?|containers?)\b")
#: The model states only the definition chain: no text calls the usage the same system as the context's part.
SAME_SYSTEM = re.compile(r"(?i)\bthe same system\b")
#: After "it" (the usage), "this one" reads as the usage: a text names the definition it means.
THIS_ONE = re.compile(r"(?i)\bthis one\b")
#: Every ban that the docs of the package and the guide's Phase 7 section are held to.
BANS = (ROUTE_AND_TECHNOLOGY, NETWORK_NAMES, MODE_WORD, PAST_BEHAVIOR, CLAUSE_NUMBER, APPROVAL, PHASE7_TECH,
        SAME_SYSTEM, THIS_ONE)

#: The grid script's names for the matrix: title, description, row label, column label.
GRID = ("Vehicle network function-to-logical-element mapping",
        "Maps the five functions of the vehicle network to the three logical elements that carry them.",
        "system functions (action usages)", "logical elements (part usages)")

#: The texts of record of the design, pinned whole: the header, paragraph by paragraph.
HEADER_PARAGRAPHS = [
    "DE4SDV E/E architecture logical architecture.",
    "INC-EE-001, phase 7: the logical architecture of the vehicle network. What technology-independent logical "
    "elements realize the five functions of phase 6?",
    "The decomposition subject is the system of interest itself, one level below the functional boundary of phase 6: "
    "EEVehicleNetworkLogicalSystem specializes EEVehicleNetworkFunctionalBoundary, so it keeps the two boundary "
    "ports and gives the vehicle network an inside of three logical elements. The context elements of phase 2 stay "
    "outside and undivided. Functions stay where phase 6 put them; each is allocated to the logical element that "
    "carries it by a native allocation (allocatedTo), a responsibility assignment, not a realization, deployment or "
    "runtime claim.",
    "Three logical elements for five functions (owner decision of 2026-11-26). Functions share a logical element "
    "when nothing requires them to be separately placeable, and split where a requirement constrains the exchange "
    "between them or demands that one keeps working when the other does not. The command carrier takes each driving "
    "command at the boundary interface and carries it to the actuation end: nothing asks the taking and the carrying "
    "to be placed apart. The actuation end checks each driving command that reaches it and applies each valid one "
    "until the stop response starts. It stands apart from the command carrier: REQ-EE-004, REQ-EE-005 and REQ-EE-007 "
    "constrain the carriage to it, and by REQ-EE-009 the stop response starts there once more than 200 ms of "
    "simulation time pass with no valid driving command reaching it, so it keeps working when the carriage delivers "
    "nothing. The check stays with the application: phase 5 judges a driving command valid as it reaches the end of "
    "its route, and the two functions share REQ-EE-006 and REQ-EE-008. The identity recorder stands alone because "
    "the record covers the software and the configuration of both other logical elements and comes before the first "
    "driving command of each run is taken.",
    "The carried driving commands are the one exchange between logical elements, and the three carriage requirements "
    "constrain it. REQ-EE-002 keeps one input: the boundary delegates the driving command to the command carrier "
    "alone. REQ-EE-010 orders the record before the first driving command; phase 6 holds that order by succession, "
    "with no item, so it crosses no exchange here. REQ-EE-001 and REQ-EE-003 constrain the topology and the routes, "
    "so phase 8 carries them by the elements that it places on the routes. Phase 6 left to phases 7 and 8 which "
    "element checks a driving command: here, the actuation end. Where each element of the routes takes the "
    "simulation time stays with phase 8. Nothing here names a computer, a process, a transport or a signal "
    "catalogue.",
]
#: Each inner port definition -> its doc.
PORT_DOCS = {
    "EECarriedCommandOutbound": (
        "The output port of the carried driving commands: the command carrier gives the actuation end each driving "
        "command that it carries, with each part as the path gave it."),
    "EECarriedCommandInbound": (
        "The input port of the carried driving commands: the actuation end takes each driving command that reaches "
        "it and judges it there by the term valid driving command."),
}
#: Each logical element definition -> its doc.
ELEMENT_DOCS = {
    "EEIdentityRecorder": (
        "Carries the recording of the network identity: before the first driving command of each run is taken, it "
        "records the network identity, whose parts phase 5 names one by one, so that each verdict binds the route, "
        "the commit with its difference, the configuration and the settings that ran. The record covers the software "
        "and the configuration of the command carrier and of the actuation end alike, so it is a responsibility of "
        "its own: phase 8 realizes it, and its order before the first driving command, in the software of the "
        "vehicle network. It exchanges nothing with another logical element: phase 6 orders the record before the "
        "first driving command by succession, with no item."),
    "EECommandCarrier": (
        "Carries the taking and the carriage of the driving commands: it takes each driving command at the boundary "
        "interface as the path that carries it there gives it, at the simulation time at which the path gives it, "
        "and from nowhere else, and carries it to the actuation end once, in its order and with each part as the "
        "path gave it, handing its detection parts on as it received them and computing none of them anew. In a run "
        "without a fault each driving command reaches the actuation end within 50 ms of simulation time after it is "
        "taken; around a fault the carrier goes on carrying each driving command that the fault does not affect. "
        "Nothing asks the taking and the carrying to be placed apart, so they share one logical element. It takes "
        "nothing from another logical element. Phase 8 realizes it on the elements that each route passes, which "
        "REQ-EE-001 and REQ-EE-003 constrain."),
    "EEActuationEnd": (
        "Carries what the vehicle gets from the vehicle network: it decides, by the term valid driving command, "
        "whether each driving command that reaches it is valid, applies each valid one when it reaches it and "
        "nothing in place of an invalid one, and gives the vehicle the steering angle and the acceleration of the "
        "last valid driving command that it applied, and nothing before the first. Once more than 200 ms of "
        "simulation time pass with no valid driving command reaching it, counted from the last one or from the start "
        "of the run when none did, it applies no driving command that reaches it after that, and gives the vehicle "
        "the stop response on the same output, from no later than 300 ms of simulation time after that last valid "
        "driving command or the start of the run until the run ends. The check and the application share REQ-EE-006 "
        "and REQ-EE-008, and phase 5 judges a driving command valid as it reaches the end of its route, so they "
        "share one logical element. It stands apart from the command carrier because it keeps working when the "
        "carriage delivers nothing. It gives nothing to another logical element. Phase 8 realizes it on the last "
        "element that a driving command reaches."),
}
SYSTEM_DOC = (
    "The vehicle network of phase 2, one level inside the functional boundary of phase 6, with its three logical "
    "elements and the exchange between them. The boundary ports are inherited and delegated to the logical elements "
    "that take or provide their items: the driving command goes to the command carrier, and the applied command "
    "leaves from the actuation end. Inside, the carried driving commands go from the command carrier to the "
    "actuation end, the one exchange between logical elements. No exchange runs from the actuation end to another "
    "logical element, nothing runs into the command carrier from another logical element, and the identity recorder "
    "exchanges nothing. This definition names no computer, process, transport or technology. "
    "eeVehicleNetworkLogicalSystem is its usage for the views, which draw usages. It depicts the context's "
    "vehicleNetwork, whose definition EEVehicleNetworkLogicalSystem specializes, and is bound to nothing.")
USAGE_DOC = (
    "The vehicle network as the views draw it: the one usage of the logical definition. It depicts the context's "
    "vehicleNetwork and is bound to nothing.")
#: Each concern -> its doc.
CONCERN_DOCS = {
    "eeVehicleNetworkLogicalStructureConcern": (
        "System architects and software developers need the logical elements of the vehicle network, one level "
        "inside its functional boundary, each with the responsibility it carries and its ports, before phase 8 "
        "allocates each of them to a physical element: which logical elements there are, and why each stands alone."),
    "eeVehicleNetworkFunctionMappingConcern": (
        "System architects and verification engineers need each function of phase 6 allocated to the logical element "
        "that carries it, and each logical element carrying a function: phase 8 allocates each logical element to a "
        "physical element, and phase 10 verifies the requirements that their functions carry."),
    "eeVehicleNetworkInternalExchangeConcern": (
        "Systems engineers and software developers need the exchanges of the vehicle network between its logical "
        "elements, the item each carries and its direction: the carried driving commands, the one exchange between "
        "logical elements, which REQ-EE-004, REQ-EE-005 and REQ-EE-007 constrain and whose lack of a valid driving "
        "command for more than 200 ms of simulation time starts the stop response of REQ-EE-009; and the boundary "
        "items delegated to the logical element that takes or provides them, the driving command by the one input "
        "that REQ-EE-002 keeps. Phase 8 places the exchange on the routes."),
}

#: The guide: its Status line and the next obligation, as phase 7 moves them.
GUIDE_STATUS = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification, "
    "Phase 4 stakeholder needs, Phase 5 requirements, Phase 6 functional architecture and Phase 7 logical "
    "architecture, proposal.**")
#: The paragraph of the next obligation: the go for phase 7 with its date, and phase 8 next.
GUIDE_NEXT_PARAGRAPH = (
    "Use the Method Check of the reviewed pull request to select the next obligation, not the phase number alone. "
    "Phase 3, the capability classification, records no feature-model delta, and review judges it: its one blocking "
    "check has nothing to evaluate, so the Method Check lists Phase 3 as vacuous, with a prompt for review. The "
    "owner decided on 2026-11-18 to carry out Phases 1 to 3 of this increment before the baseline of the "
    "driver-assistance increment, whose driving command it carries. After that baseline, the owner decided on "
    "2026-11-21 to start Phase 4, on 2026-11-22 to go on with Phase 5, on 2026-11-24 to go on with Phase 6 and on "
    "2026-11-25 to go on with Phase 7. The next model obligation is **Phase 8**: the E/E and software realization, "
    "which allocates each logical element to a physical element; its first gate is "
    "`logicalElementAllocatedToPhysicalElement`. The testbed with its readiness probe waits for a further decision "
    "of the owner.")
GUIDE_NEXT = (
    "The next model obligation is **Phase 8**: the E/E and software realization, which allocates each logical "
    "element to a physical element; its first gate is `logicalElementAllocatedToPhysicalElement`.")
#: The blocks of the guide's Phase 7 section, whole and in order: the opening, one list item per logical
#: element, the exchanges and the views.
GUIDE_OPENING = (
    "Phase 7 gives the vehicle network three logical elements in DE4SDV_EEArchitectureLogicalArchitecture. "
    "EEVehicleNetworkLogicalSystem specializes the functional boundary of Phase 6, so it keeps its two ports, and "
    "each of the five functions is allocated to the logical element that carries it. On 2026-11-26 the owner chose "
    "three logical elements for the five functions: functions share a logical element when nothing requires them to "
    "be separately placeable, and split where a requirement constrains the exchange between them or demands that one "
    "keeps working when the other does not.")
GUIDE_ELEMENTS = [
    "eeIdentityRecorder carries recordNetworkIdentity (REQ-EE-010). The record covers the software and the "
    "configuration of both other logical elements and comes before the first driving command of each run is taken, "
    "so it stands alone. It exchanges nothing: Phase 6 orders the record by succession, with no item.",
    "eeCommandCarrier carries takeDrivingCommand and carryDrivingCommand (REQ-EE-002, REQ-EE-004, REQ-EE-005 and "
    "REQ-EE-007). Nothing asks the taking and the carrying to be placed apart.",
    "eeActuationEnd carries checkDrivingCommand and applyDrivingCommand (REQ-EE-006, REQ-EE-008 and REQ-EE-009). It "
    "keeps working when the carriage delivers nothing: by REQ-EE-009 the stop response starts there once more than "
    "200 ms of simulation time pass with no valid driving command reaching it. So it stands apart from the command "
    "carrier. The check stays with the application: Phase 5 judges a driving command valid as it reaches the end of "
    "its route, and both functions share REQ-EE-006 and REQ-EE-008.",
]
GUIDE_EXCHANGES = (
    "The driving command enters by one delegation, to the command carrier, the one input that REQ-EE-002 keeps; the "
    "carried driving commands go from the command carrier to the actuation end, the one exchange between logical "
    "elements, which REQ-EE-004, REQ-EE-005 and REQ-EE-007 constrain; and the applied command leaves from the "
    "actuation end. REQ-EE-001 and REQ-EE-003 constrain the topology and the routes, so Phase 8 carries them by the "
    "elements that it places on the routes. Of the two questions that Phase 6 left open, Phase 7 settles which "
    "element checks a driving command: the actuation end. Where each element of the routes takes the simulation time "
    "stays with Phase 8.")
GUIDE_VIEWS = (
    "Three views show it: the logical structure, the function by logical element matrix and the internal exchange.")
GUIDE_HEADING = "## Logical architecture (Phase 7)"
TEST_FILE = "tests/test_ee_architecture_logical_architecture.py"

#: The package's code, every declaration at its own depth (two spaces a level), as `_skeleton` reads it: generated
#: from the model, never written by hand. A line ending in a backslash continues on the next.
SKELETON = """\
/*…*/
package DE4SDV_EEArchitectureLogicalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::LogicalAllocationElement;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEVehicleNetworkFunctionalBoundary;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEVehicleNetworkFunctionalFlow;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::eeVehicleNetworkFunctionalFlow;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEDrivingCommandInbound;
  private import DE4SDV_EEArchitectureFunctionalArchitecture::EEActuationOutbound;
  private import DE4SDV_DriverAssistanceOperationalContext::DrivingCommand;
  private import SAF_Viewpoints::*;
  private import SysideViews::**;
  private import Views::*;
  /* ─── The ports of the exchange inside the vehicle network ─── */
  port def EECarriedCommandOutbound {
    doc /*…*/
    out item eeCarriedCommand : DrivingCommand;
  port def EECarriedCommandInbound {
    doc /*…*/
    in item eeCarriedCommand : DrivingCommand;
  /* ─── The three logical elements of the vehicle network ─── */
  part def EEIdentityRecorder :> LogicalAllocationElement {
    doc /*…*/
  part def EECommandCarrier :> LogicalAllocationElement {
    doc /*…*/
    port eeCommandIn : EEDrivingCommandInbound;
    port eeCarriedCommandOut : EECarriedCommandOutbound;
  part def EEActuationEnd :> LogicalAllocationElement {
    doc /*…*/
    port eeCarriedCommandIn : EECarriedCommandInbound;
    port eeActuationOut : EEActuationOutbound;
  /* ─── The vehicle network one level inside its boundary ─── */
  part def EEVehicleNetworkLogicalSystem :> EEVehicleNetworkFunctionalBoundary {
    doc /*…*/
    part eeIdentityRecorder : EEIdentityRecorder;
    part eeCommandCarrier : EECommandCarrier;
    part eeActuationEnd : EEActuationEnd;
    connection eeCommandToCarrierDelegation connect drivingCommandIn to eeCommandCarrier.eeCommandIn;
    connection eeActuationFromEndDelegation connect eeActuationEnd.eeActuationOut to actuationOut;
    connection eeCommandExchange connect eeCommandCarrier.eeCarriedCommandOut to eeActuationEnd.eeCarriedCommandIn;
  part eeVehicleNetworkLogicalSystem : EEVehicleNetworkLogicalSystem {
    doc /*…*/
  /* ─── Function-to-logical-element allocations (allocatedTo) ─── */
  allocation eeRecordNetworkIdentityAllocation allocate EEVehicleNetworkFunctionalFlow::recordNetworkIdentity to \
EEVehicleNetworkLogicalSystem::eeIdentityRecorder;
  allocation eeTakeDrivingCommandAllocation allocate EEVehicleNetworkFunctionalFlow::takeDrivingCommand to \
EEVehicleNetworkLogicalSystem::eeCommandCarrier;
  allocation eeCarryDrivingCommandAllocation allocate EEVehicleNetworkFunctionalFlow::carryDrivingCommand to \
EEVehicleNetworkLogicalSystem::eeCommandCarrier;
  allocation eeCheckDrivingCommandAllocation allocate EEVehicleNetworkFunctionalFlow::checkDrivingCommand to \
EEVehicleNetworkLogicalSystem::eeActuationEnd;
  allocation eeApplyDrivingCommandAllocation allocate EEVehicleNetworkFunctionalFlow::applyDrivingCommand to \
EEVehicleNetworkLogicalSystem::eeActuationEnd;
  /* ─── Views ─── */
  concern eeVehicleNetworkLogicalStructureConcern : ConceptualStructureConcern {
    doc /*…*/
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  view eeVehicleNetworkLogicalStructureView {
    viewpoint eeLogicalStructureViewpoint : SystemStructureDefinitionViewpoint {
      frame eeVehicleNetworkLogicalStructureConcern;
    expose eeVehicleNetworkLogicalSystem;
    expose eeVehicleNetworkLogicalSystem::eeIdentityRecorder;
    expose eeVehicleNetworkLogicalSystem::eeCommandCarrier;
    expose eeVehicleNetworkLogicalSystem::eeActuationEnd;
    filter not (@ SysML::AllocationUsage);
    render asTreeDiagram;
  concern eeVehicleNetworkFunctionMappingConcern : ConceptualFunctionMappingConcern {
    doc /*…*/
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  view eeVehicleNetworkFunctionMappingView : MVD::MatrixView {
    viewpoint eeFunctionMappingViewpoint : SystemFunctionMappingViewpoint {
      frame eeVehicleNetworkFunctionMappingConcern;
    view :>> rowView {
      expose eeVehicleNetworkFunctionalFlow::recordNetworkIdentity;
      expose eeVehicleNetworkFunctionalFlow::takeDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::carryDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::checkDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::applyDrivingCommand;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    view :>> columnView {
      expose EEVehicleNetworkLogicalSystem::eeIdentityRecorder;
      expose EEVehicleNetworkLogicalSystem::eeCommandCarrier;
      expose EEVehicleNetworkLogicalSystem::eeActuationEnd;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    view :>> cellView {
      expose DE4SDV_EEArchitectureLogicalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
  concern eeVehicleNetworkInternalExchangeConcern : ConceptualInternalExchangeConcern {
    doc /*…*/
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  view eeVehicleNetworkInternalExchangeView {
    viewpoint eeInternalExchangeViewpoint : SystemInternalExchangeViewpoint {
      frame eeVehicleNetworkInternalExchangeConcern;
    expose eeVehicleNetworkLogicalSystem;
    expose eeVehicleNetworkLogicalSystem::**;
    filter not (@ SysML::AllocationUsage);
    attribute depth = -1;
    attribute showAnnotationRows = false;
    render asInterconnectionDiagram;
"""


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(re.sub(r"//\*.*?\*/", "", _raw(), flags=re.S))


def _flat(text: str) -> str:
    """The text of a doc or comment body, whitespace collapsed; only the `*` that leads a line is dropped."""
    return " ".join(re.sub(r"(?m)^\s*\*(?!/)\s?", "", text).split())


def _doc(declaration: str) -> str:
    """The doc text of the model element whose body follows ``declaration`` in the raw model."""
    assert _raw().count(declaration) == 1, f"{declaration}: one copy in the file, so that no note holds a decoy"
    body = braced_body(_raw(), declaration)
    match = re.match(r"\s*doc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{declaration}: the doc must open the body"
    return _flat(match.group(1))


def _paragraphs(text: str) -> list[str]:
    return [" ".join(re.sub(r"(?m)^\s*\*\s?", "", part).split()) for part in re.split(r"\n\s*\*\s*\n", text)
            if part.strip()]


def _header_paragraphs() -> list[str]:
    head = _raw().split(f"package {PACKAGE}", 1)[0]
    assert head.startswith("/*") and head.rstrip().endswith("*/")
    return _paragraphs(head.strip()[2:-2])


def _header() -> str:
    return " ".join(_header_paragraphs())


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
    rows = re.findall(r"\ballocation\s+(\w+)(?:\s*:\s*([\w:]+))?\s+allocate\s+(\S+)\s+to\s+([^\s;{]+)\s*;", code)
    assert all(not typed for _, typed, _, _ in rows), "allocations are untyped, as in phase 6"
    assert len(rows) == len(re.findall(r"\ballocation\b", code)) == len(re.findall(r"\ballocate\b", code)), \
        "every allocation has the one form"
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


def _skeleton() -> list[str]:
    """The raw model as one line per declaration, the whole declaration up to its own `{` or `;` (whitespace
    collapsed), indented two spaces per brace depth, each body's members after it one level deeper. The `//` and
    `//* */` notes are dropped; the header, each `doc` and each `comment` keep only `/*…*/` (the texts of record pin
    their words); every other `/* */` comment, a section comment, keeps its text."""
    raw = _raw()
    lines: list[str] = []
    pending, depth, at = "", 0, 0

    def emit(text: str) -> None:
        lines.append("  " * depth + " ".join(text.split()))

    while at < len(raw):
        if raw.startswith("//*", at):
            at = raw.index("*/", at + 3) + 2
        elif raw.startswith("//", at):
            end = raw.find("\n", at)
            at = len(raw) if end < 0 else end
        elif raw.startswith("/*", at):
            end = raw.index("*/", at + 2) + 2
            if re.fullmatch(r"\s*(?:doc|comment)\b[\w\s:,]*", pending) or not (lines or pending.strip()):
                emit(pending + " /*…*/")
                pending = ""
            elif pending.strip():
                pending += " /* " + " ".join(raw[at + 2:end - 2].split()) + " */ "
            else:
                emit("/* " + " ".join(raw[at + 2:end - 2].split()) + " */")
            at = end
        elif raw[at] in "\"'":
            end = raw.index(raw[at], at + 1) + 1
            pending += raw[at:end]
            at = end
        elif raw[at] == "{":
            emit(pending + " {")
            pending, depth, at = "", depth + 1, at + 1
        elif raw[at] == ";":
            emit(pending + ";")
            pending, at = "", at + 1
        elif raw[at] == "}":
            if pending.strip():
                emit(pending)
            assert depth > 0, "a } that closes no body"
            pending, depth, at = "", depth - 1, at + 1
        else:
            pending += raw[at]
            at += 1
    if pending.strip():
        emit(pending)
    assert depth == 0, "a body that is never closed"
    return lines


def _guide() -> str:
    return GUIDE.read_text(encoding="utf-8")


def _guide_section(guide: str) -> str:
    return guide.split(GUIDE_HEADING + "\n", 1)[1].split("\n## ", 1)[0]


def test_the_charter_names_the_package_after_the_functional_architecture():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part eeArchitectureCharter : IncrementCharter")
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
    # the package's only part usage is that one; the only usages of the logical elements are the system's three
    # parts
    package = _direct(braced_body(code, f"package {PACKAGE}"))
    assert re.findall(r"\bpart\s+(?!def\b)(\w+)\s*:", package) == [SYSTEM_USAGE]
    roles = "|".join(definition for definition, _ in ELEMENTS.values())
    assert re.findall(rf"\b(\w+)\s*:(?![:>])\s*({roles})\b", code) == [
        (usage, definition) for usage, (definition, _) in ELEMENTS.items()]
    # over the whole file: the three parts and the usage, the four ports of the logical elements, the three
    # connections
    assert re.findall(r"\bpart\s+(?!def\b)(\w+)", code) == [*ELEMENTS, SYSTEM_USAGE]
    assert len(re.findall(r"\bport\s+(?!def\b)\w+", code)) == sum(len(ports) for ports in PORTS.values()) == 4
    assert len(re.findall(r"\bconnect\b", code)) == len(CONNECTIONS) == 3
    assert not re.search(rf"(?<!:):(?!:)\s*(?:{BOUNDARY}|{SOI})\b", code), "no usage of the boundary or the SoI"
    assert not re.search(rf"\b{SOI}\b", code)
    # the boundary ports are inherited, never redeclared
    assert not re.search(r"\bport\b", body)


@pytest.mark.parametrize("definition", sorted(PORTS), ids=sorted(PORTS))
def test_each_element_declares_exactly_its_ports(definition):
    body = braced_body(_code(), f"part def {definition} :> LogicalAllocationElement")
    assert re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", body) == PORTS[definition]
    assert len(re.findall(r"\bport\b", body)) == len(PORTS[definition])
    assert not re.search(r"\b(part|action|perform|exhibit|flow|item|attribute|connection|ref)\b", body), \
        "a logical element carries functions by allocation only, and has ports and nothing else"


def test_the_identity_recorder_has_no_port_and_no_exchange():
    body = braced_body(_code(), "part def EEIdentityRecorder :> LogicalAllocationElement")
    assert body.split() == ["doc"], "a doc and nothing else"
    assert not any("eeIdentityRecorder" in end for _, *ends in _connections() for end in ends)
    assert "eeIdentityRecorder." not in _code(), "no connection end names the identity recorder"


def test_the_inner_ports_carry_the_driving_command_in_one_direction():
    code = _code()
    assert re.findall(r"\bport\s+def\s+(\w+)", code) == list(INTERNAL_PORT_ITEMS)
    for port_def, (direction, item, item_type) in INTERNAL_PORT_ITEMS.items():
        body = braced_body(code, f"port def {port_def}")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [(direction, item, item_type)], \
            port_def
        assert body.split()[0] == "doc" and len(re.findall(r"\b(?:item|attribute|port|ref|in|out)\b", body)) == 2, \
            port_def
    assert not re.search(r"\bitem\s+def\b", code), "the items are phase 2's and phase 6's"
    for port_def in BOUNDARY_PORTS.values():
        assert not re.search(rf"\bport\s+def\s+{port_def}\b", code), "the boundary port definitions are phase 6's"
    # the item is the driving command that every function of the chain takes and gives in phase 6
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    for definition in ("EECarryDrivingCommand", "EECheckDrivingCommand"):
        body = braced_body(functional, f"action def {definition} :> AllocatableFunction")
        assert re.search(r"\b(?:in|out)\s+\w+\s*:\s*DrivingCommand\s*;", body), definition
    boundary = braced_body(functional, f"part def {BOUNDARY} :> {SOI}")
    assert dict(re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", boundary)) == BOUNDARY_PORTS


def test_the_exchanges_are_exactly_these_three_connections():
    connections = _connections()
    assert connections == CONNECTIONS
    body = _system_body()
    assert len(re.findall(r"\bconnect\b", body)) == len(CONNECTIONS)
    assert len(re.findall(r"\bconnection\b", _code())) == len(CONNECTIONS)
    assert not re.search(r"\b(flow|bind|binding|interface|message|succession)\b", _code()), \
        "the file's only exchanges are the system's three connections"
    # every end of a connection names a declared port of its logical element, or an inherited boundary port
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


def test_the_exchanges_run_one_way_and_the_carried_commands_are_the_one_between_elements():
    connections = _connections()
    end, carrier = "eeActuationEnd.", "eeCommandCarrier."
    for name, source, target in connections:
        # nothing the actuation end provides goes to another logical element
        if source.startswith(end):
            assert name == "eeActuationFromEndDelegation" and "." not in target, name
        # nothing goes into the command carrier but the driving command from the boundary
        if target.startswith(carrier):
            assert name == "eeCommandToCarrierDelegation" and "." not in source, name
        assert "eeIdentityRecorder" not in source + target, name
    between = [name for name, source, target in connections if "." in source and "." in target]
    assert between == ["eeCommandExchange"]
    # the driving command enters by one delegation only (REQ-EE-002 keeps one input)
    assert [name for name, source, target in connections if "drivingCommandIn" in (source, target)] == [
        "eeCommandToCarrierDelegation"]
    assert len(re.findall(r"\bdrivingCommandIn\b", _code())) == 1
    # the applied command leaves from the actuation end only
    assert [source for _, source, target in connections if target == "actuationOut"] == [
        "eeActuationEnd.eeActuationOut"]


def test_the_carried_commands_are_the_exchange_that_the_carriage_requirements_constrain():
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    assert re.search(r"\bflow\s+from\s+carryDrivingCommand\.carriedCommand\s+to\s+checkDrivingCommand\."
                     r"carriedCommand\s*;", functional)
    carriers = {function: element for _, function, element in ALLOCATIONS}
    assert (carriers["carryDrivingCommand"], carriers["checkDrivingCommand"]) == (
        "eeCommandCarrier", "eeActuationEnd"), "the carried driving commands cross between two logical elements"
    for identity, requirement in CARRIAGE_REQUIREMENTS.items():
        allocated = set(re.findall(rf"\ballocate\s+{requirement}\s+to\s+{FLOW}::(\w+)\s*;", functional))
        assert allocated == {"carryDrivingCommand"}, (identity, allocated)
    assert ("REQ-EE-004, REQ-EE-005 and REQ-EE-007 constrain the carriage to it" in _header())
    assert "The carried driving commands are the one exchange between logical elements" in _header()


def test_each_function_is_allocated_to_the_element_the_owner_decided():
    rows = _allocations()
    assert rows == [(name, f"{FLOW}::{function}", f"{SYSTEM}::{element}") for name, function, element in ALLOCATIONS]
    # the owner's decision of 2026-11-26: three logical elements for five functions
    carried = {}
    for _, function, element in ALLOCATIONS:
        carried.setdefault(element, []).append(function)
    assert carried == {usage: list(functions) for usage, (_, functions) in ELEMENTS.items()}
    assert carried["eeIdentityRecorder"] == ["recordNetworkIdentity"], "the identity recorder stands alone"
    assert carried["eeCommandCarrier"] == ["takeDrivingCommand", "carryDrivingCommand"]
    assert carried["eeActuationEnd"] == ["checkDrivingCommand", "applyDrivingCommand"], \
        "the check stays with the application"
    # each function goes to one logical element, and each logical element carries a function
    assert sorted(function for _, function, _ in ALLOCATIONS) == sorted(FUNCTIONS)
    assert "Three logical elements for five functions (owner decision of 2026-11-26)." in _header_paragraphs()[3]


def test_the_functions_allocated_are_the_five_of_phase_6():
    functional = strip_comments(FUNCTIONAL.read_text(encoding="utf-8"))
    flow = braced_body(functional, f"action def {FLOW}")
    declared = re.findall(r"^\s*action\s+(\w+)\s*:\s*\w+\s*[{;]", flow, re.M)
    assert declared == list(FUNCTIONS)


@pytest.mark.parametrize("definition", sorted(ELEMENT_DOCS), ids=sorted(ELEMENT_DOCS))
def test_each_element_states_its_text_of_record(definition):
    assert _doc(f"part def {definition} :> LogicalAllocationElement") == ELEMENT_DOCS[definition]


def test_the_system_its_usage_and_its_ports_state_their_texts_of_record():
    assert _doc(f"part def {SYSTEM} :> {BOUNDARY}") == SYSTEM_DOC
    assert _doc(f"part {SYSTEM_USAGE} : {SYSTEM}") == USAGE_DOC
    for port_def, text in PORT_DOCS.items():
        assert _doc(f"port def {port_def}") == text, port_def


def test_the_notes_of_the_file_are_exactly_the_two_of_the_system_definition():
    raw = _raw()
    assert [" ".join(note.split()) for note in re.findall(r"//(?!\*)([^\n]*)", raw)] == NOTES
    assert "//*" not in raw, "no multi-line note"
    system = braced_body(raw, f"part def {SYSTEM} :> {BOUNDARY}")
    assert [" ".join(note.split()) for note in re.findall(r"//([^\n]*)", system)] == NOTES


def test_the_package_publishes_exactly_one_view_per_question():
    declared = re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M)
    assert declared == list(VIEWS)
    assert len(re.findall(r"\bview\s+(?!:>>)\w+", _code())) == len(VIEWS)


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
    assert len(re.findall(r"\bframe\b", view)) == 1
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", view) == exposes
    assert len(re.findall(r"\bexpose\b", view)) == len(exposes)
    if render:
        assert re.findall(r"\brender\s+[^;]+;", view) == [render]
    else:
        assert "render" not in view, "the view type selects the kind"


def test_the_matrix_maps_the_functions_to_the_elements_with_reference_elements():
    view = braced_body(_code(), f"view {MATRIX_VIEW} : MVD::MatrixView")
    rows = braced_body(view, "view :>> rowView")
    columns = braced_body(view, "view :>> columnView")
    cells = braced_body(view, "view :>> cellView")
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", rows) == [f"{FLOW_USAGE}::{function}" for function in FUNCTIONS]
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", columns) == [f"{SYSTEM}::{element}" for element in ELEMENTS]
    for axis in (rows, columns):
        assert re.findall(r"\battribute\s+[^;]+;", axis) == ["attribute :>> includeReferenceElements = true;",
                                                             "attribute :>> representation = Rep::name;"]
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", cells) == [f"{PACKAGE}::*"]
    assert re.findall(r"\battribute\s+[^;]+;", cells) == [
        "attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;"]
    assert not re.search(r"\bfilter\b", view), "the allocations are the cells; no filter of the matrix hides them"
    assert re.findall(r"\bview\s+:>>\s*(\w+)", view) == ["rowView", "columnView", "cellView"]
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
    assert len(re.findall(r"\battribute\b", view)) == 2
    assert "attribute" not in braced_body(_code(), f"view {STRUCTURE_VIEW}")


@pytest.mark.parametrize("concern_name", sorted(CATALOGUE_CONCERNS), ids=sorted(CATALOGUE_CONCERNS))
def test_each_phase_7_concern_is_typed_by_the_catalogue_and_held_by_the_party_it_serves(concern_name):
    catalogue, stakeholders = CATALOGUE_CONCERNS[concern_name]
    concern = braced_body(_code(), f"concern {concern_name} : {catalogue}")
    assert concern.split()[0] == "doc"
    members = re.findall(r"\b(subject|stakeholder|require|assume|attribute|ref)\b", concern)
    assert members == ["subject"] + ["stakeholder"] * len(stakeholders)
    assert re.search(r"\bsubject\s*;", concern)
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern) == stakeholders
    assert _doc(f"concern {concern_name} : {catalogue}") == CONCERN_DOCS[concern_name]
    assert len(re.findall(r"\bconcern\s+\w+\s*:", _code())) == len(CATALOGUE_CONCERNS)


def test_no_doc_of_the_package_and_no_sentence_of_the_guide_section_names_a_technology_or_a_claim():
    # every /* */ block (the header, each doc and each section comment) and every // note of the package
    docs = _docs()
    assert len(docs) >= 18, "the population of the check must not be vacuous"
    prose = re.sub(r"`[^`]*`|\]\([^)]*\)", " ", _guide_section(_guide()))
    for text in docs + [" ".join(prose.split())]:
        found = [ban.search(text).group(0) for ban in BANS if ban.search(text)]
        assert not found, (text[:80], found)


def test_the_package_types_no_signal_and_holds_no_other_kind():
    code = _code()
    assert "VSS" not in _raw() and "COVESA" not in _raw() and "DE4SDV_VSS_Extensions" not in code
    assert not re.search(r":\s*Vehicle_\w+", code), "VSS typing starts at phase 8"
    assert not re.search(r"\b(item\s+def|ref\s+part|ref|perform|exhibit|state|action|dependency|satisfy|refine|"
                         r"alias|attribute\s+def|enum|calc|constraint|requirement|occurrence)\b", code)
    assert not re.search(rf"^\s*part\s+\w+\s*:\s*{SYSTEM}\s*=", code, re.M), "the usage is bound to nothing"
    assert not re.search(r":>>?\s*\w*[Cc]ontext\w*|eeArchitectureOperationalContext|\bvehicleNetwork\b", code), \
        "the usage is bound to no context part"
    # REQ-EE-001 and REQ-EE-003 stay with phase 8; no allocation names a requirement
    assert not re.search(r"\breq[A-Z]\w*", code), "no requirement is allocated or traced here"
    assert "NeedsRequirements" not in code
    assert not re.search(r"[^\x00-\x7f]", code), "the code is ASCII: only docs and comments hold other characters"


def test_the_package_is_exactly_its_skeleton():
    """The whole code of the package, pinned line by line: every declaration at its own depth, whole, in order.
    Because the skeleton pins the code whole, a change to any declaration of the package fails it: a member added,
    removed, moved or reordered at any depth, a changed keyword, name, type, value or binding, a changed section
    comment, a brace that closes no body or a body never closed. Its limit: the header, the docs and the `//` notes
    are pinned by the texts of record and NOTES, which read the one copy of each declaration in the file (a note
    that copies a declaration fails them)."""
    expected = SKELETON.replace("\\\n", "").splitlines()
    actual = _skeleton()
    assert len(expected) >= 100, "the skeleton must not be vacuous"
    for number, (line, pinned) in enumerate(zip_longest(actual, expected), 1):
        assert line == pinned, f"skeleton line {number}: {line!r}, pinned {pinned!r}"


def test_the_package_declares_no_name_that_another_model_package_declares():
    # Two packages may declare the same name, but a lookup by name then finds two model elements, and a check that reads
    # a folder by name sees one increment's declaration as the other's. Both ways: no other model file declares a name
    # of this package, owned ones included, in the forms read here (a definition of any kind, a package or a usage of a
    # kind of USAGE_KINDS, with the plain name directly after the keyword), and no top-level name of another file is
    # declared here. Not read: a short name before a definition's name or an unquoted one before a usage's, a quoted
    # name, an alias, a usage of another kind and a directed feature with no kind keyword.
    kinds = r"(?:package|part def|port def|part|port|item|connection|allocation|concern|view|viewpoint)"
    anywhere = re.compile(rf"\b{kinds}\s+(?:<'[^']*'>\s*)?(\w+)")
    declared = set(anywhere.findall(_code()))
    assert declared == DECLARED_NAMES
    assert len(declared) == 33, "the population of the check must not be vacuous"
    assert all(name.startswith(("ee", "EE")) for name in declared - {PACKAGE}), sorted(
        name for name in declared if not name.startswith(("ee", "EE")))
    # in another file: a package, a definition of any kind, or a usage of one of these kinds (the name is read
    # ahead, so that a kind before a kind, as in `ref part`, still yields the name after the second)
    definitions = re.compile(r"\b\w+\s+def\s+(\w+)")
    usages = re.compile(rf"\b(?:package|{'|'.join(USAGE_KINDS)})\s+(?:<'[^']*'>\s*)?(?=(\w+))")
    top_level = re.compile(rf"(?m)^  (?:\w+\s+def|package|{'|'.join(USAGE_KINDS)})\s+(?:<'[^']*'>\s*)?(\w+)")
    taken: dict[str, list[str]] = {}
    scanned = 0
    for root in MODEL_ROOTS:
        for path in sorted(root.rglob("*.sysml")):
            if path == MODEL:
                continue
            scanned += 1
            code = strip_comments(path.read_text(encoding="utf-8"))
            for name in definitions.findall(code) + usages.findall(code):
                if name in declared:
                    taken.setdefault(name, []).append(path.name)
            for name in top_level.findall(code):
                if name in declared:
                    taken.setdefault(name, []).append(f"{path.name} (top level)")
    assert scanned > 100, "the population of the scan must not be vacuous"
    assert not taken, f"declared in another package too: {taken}"


def test_the_allocation_file_is_governed_with_its_three_endpoint_definitions():
    import test_trace_allocation_completeness as trace

    assert trace.EE_L == MODEL
    assert trace.ALLOCATION_FILES[trace.EE_L] == (
        (trace.EE_L, trace.EE_F), {(trace.FUNCTION, trace.LOGICAL): len(ALLOCATIONS)}, {},
        (trace.FUNCTION, trace.LOGICAL))
    assert trace.GOVERNED[trace.EE_L] == (trace.LOGICAL, {d for d, _ in ELEMENTS.values()})
    assert trace.LINEAGE_FILES.index(trace.EE_L) == trace.LINEAGE_FILES.index(trace.EE_F) + 1
    assert trace.NOT_ENDPOINTS[trace.EE_L] == {SYSTEM}


def test_the_guide_has_a_phase_7_section_and_names_the_next_obligation():
    guide = _guide()
    assert guide.count(GUIDE_HEADING + "\n") == 1
    assert guide.index("## Functional architecture (Phase 6)") < guide.index(GUIDE_HEADING) \
        < guide.index("## What the framing already records as open")
    assert guide.split(GUIDE_HEADING, 1)[0].rstrip().endswith(
        "fits a CAN frame, and the medium of the direct link."), "the section follows the Phase 6 section"
    raw_section = _guide_section(guide)
    blocks = [" ".join(block.split()) for block in re.split(r"\n\s*\n", raw_section.strip())]
    assert blocks == [GUIDE_OPENING, " ".join(f"- {text}" for text in GUIDE_ELEMENTS), GUIDE_EXCHANGES,
                      GUIDE_VIEWS], "every block of the section, whole and in order"
    bullets = re.split(r"\n\s*\n", raw_section.strip())[1]
    items = [" ".join(match[1].split()) for match in re.finditer(r"(?ms)^- (.*?)(?=^- |\Z)", bullets)]
    assert items == list(GUIDE_ELEMENTS), "one item per logical element, in order"
    assert all(line.startswith(("- ", "  ")) for line in bullets.splitlines()), "a two-space hanging indent"
    assert all(len(line) <= 79 for line in raw_section.splitlines()), "the guide wraps at 79"
    flat = " ".join(guide.split())
    assert flat.count(GUIDE_STATUS) == 1
    assert "Phase 5 requirements and Phase 6 functional architecture, proposal.**" not in flat, \
        "the status line moved to phase 7"
    nxt = guide.split("## Next obligation and execution limits\n", 1)[1].split("\n## ", 1)[0]
    assert [" ".join(block.split()) for block in re.split(r"\n\s*\n", nxt.strip())][0] == GUIDE_NEXT_PARAGRAPH
    assert flat.count(GUIDE_NEXT) == 1
    assert "The next model obligation is **Phase 7**" not in flat
    assert flat.count("The next model obligation is") == 1
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert f"tests/test_ee_architecture_functional_architecture.py {TEST_FILE} -q`" in check
