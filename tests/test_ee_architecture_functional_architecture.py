"""Content pins for the E/E architecture functional architecture (phase 6), not semantic validation.

INC-EE-001 phase 6 breaks the vehicle network into its functions and allocates the requirements of phase 5 to the
functions that carry them. Method Check holds the DefineFunctionalArchitecture rules (at least one function; each
functional requirement allocated to a function by a native allocation). These pins hold what the design of
2026-11-24 settled on top of them:

- five functions, each an AllocatableFunction, and the functional flow that breaks the vehicle network into them:
  the driving command of phase 2 in, what the actuation ECU gives the vehicle out, and inside, the record of the
  network identity and the command as it is taken, carried and checked; three plain flows and one succession, and
  nothing flows from or into the record of the network identity;
- the functions do not depend on the route: no doc of the package names an element of a route, a transport or a
  technology;
- the stop response is a state of applyDrivingCommand, given at the actuation ECU on the same output as the applied
  command, not a second source of commands; the function that checks a command stands apart from the one that
  applies it, since phase 5 leaves open which element checks;
- eight requirements allocated to the functions, ten allocations in all; REQ-EE-001 and REQ-EE-003 constrain the
  structure that realizes the functions, and phases 7 and 8 carry them;
- the functions the context elements of phase 2 perform, under a root of their own outside the network's scope, and
  the system process that runs the network as one action between them, with the sequence from a fault to the stop
  response; its participants are the parts of the one context of phase 2, bound by reference;
- the three states of the actuation ECU in a run, called states and not modes (the increment's texts use "mode" for
  power modes and for Integration Mode), three transitions and none out of the stop response, and the one function
  that depends on them;
- the conceptual interfaces as two port definitions with directed items: the input specializes the item of the
  driver-assistance increment and adds no attribute, the output specializes the driving command of phase 2 and
  carries the steering angle and the acceleration only; no vehicle signal specification;
- five views, one per SAF question of the phase, each framing its concern; the process view frames the phase 1
  concern of the fault response and hides doc rows, so the view index notes where its sequence is;
- the guide's Phase 6 section, its status line and its next obligation, Phase 7.

The guards added after the review of 2026-11-25 read the code with docs and `//` notes removed, so a doc word cannot
trip them: every directed feature of a function is one of its parameters, the state machine is not parallel and owns
no action, the package has no satisfy and no refine, the matrix filters nothing, the table has the one state filter,
and the process view sets its two attributes only. After the closure check, each view sets exactly its settings and
filters, and a skeleton of the package, every declaration at its own depth with the docs left to the texts of
record, pins its code whole.
"""

from itertools import zip_longest
from pathlib import Path
import re

import pytest

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
EE = ROOT / "textual-notation-of-model/packages/features/ee"
MODEL = EE / "ee_architecture_functional_architecture.sysml"
NEEDS_REQUIREMENTS = EE / "ee_architecture_needs_requirements.sysml"
FRAMING = EE / "ee_architecture_framing.sysml"
OPERATIONAL_CONTEXT = EE / "ee_architecture_operational_context.sysml"
DRIVING_FUNCTIONS = ROOT / "textual-notation-of-model/packages/features/driving" / \
    "driver_assistance_functional_architecture.sysml"
GUIDE = ROOT / "docs/guides/ee-architecture-increment.md"
MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
PACKAGE = "DE4SDV_EEArchitectureFunctionalArchitecture"
FLOW = "EEVehicleNetworkFunctionalFlow"
FLOW_USAGE = "eeVehicleNetworkFunctionalFlow"
CONCERN = "eeVehicleNetworkFunctionsConcern"
INTERFACE_CONCERN = "eeVehicleNetworkInterfaceConcern"
STATES_CONCERN = "eeActuationStatesConcern"
#: The phase 1 concern that names the system process of phase 6 as its answer.
PHASE_1_PROCESS_CONCERN = "eeNetworkFaultResponseConcern"
TREE_VIEW = "eeVehicleNetworkFunctionBreakdownView"
MATRIX_VIEW = "eeVehicleNetworkRequirementFunctionMatrixView"
PROCESS_VIEW = "eeVehicleNetworkSystemProcessView"
TABLE_VIEW = "eeVehicleNetworkStateTableView"
INTERFACE_VIEW = "eeVehicleNetworkFunctionalInterfaceView"

#: Each function of the flow, in breakdown order -> its definition.
FUNCTIONS = {
    "recordNetworkIdentity": "EERecordNetworkIdentity",
    "takeDrivingCommand": "EETakeDrivingCommand",
    "carryDrivingCommand": "EECarryDrivingCommand",
    "checkDrivingCommand": "EECheckDrivingCommand",
    "applyDrivingCommand": "EEApplyDrivingCommand",
}

#: The item the functions exchange inside the network; the boundary items are phase 2's.
INTERNAL_ITEMS = {"EENetworkIdentityRecord"}

#: Each function definition -> its parameters (direction, name, item type), in order.
FUNCTION_PARAMETERS = {
    "EERecordNetworkIdentity": [("out", "identityRecord", "EENetworkIdentityRecord")],
    "EETakeDrivingCommand": [("in", "drivingCommand", "DrivingCommand"), ("out", "takenCommand", "DrivingCommand")],
    "EECarryDrivingCommand": [("in", "takenCommand", "DrivingCommand"), ("out", "carriedCommand", "DrivingCommand")],
    "EECheckDrivingCommand": [("in", "carriedCommand", "DrivingCommand"), ("out", "validCommand", "DrivingCommand")],
    "EEApplyDrivingCommand": [("in", "validCommand", "DrivingCommand"), ("out", "appliedCommand", "DrivingCommand")],
}

#: The flow's own parameters: the phase 2 items crossing the boundary of the network.
FLOW_PARAMETERS = [("in", "drivingCommand", "DrivingCommand"), ("out", "appliedCommand", "DrivingCommand")]

#: Item flows between the functions (source, target), in order: the command as taken, carried and checked.
FLOWS = [
    ("takeDrivingCommand.takenCommand", "carryDrivingCommand.takenCommand"),
    ("carryDrivingCommand.carriedCommand", "checkDrivingCommand.carriedCommand"),
    ("checkDrivingCommand.validCommand", "applyDrivingCommand.validCommand"),
]
#: The network identity is recorded before the network takes the first driving command of each run.
SUCCESSIONS = [("recordNetworkIdentity", "takeDrivingCommand")]

#: Function parameters bound to the flow's own parameters: (function, direction, parameter, flow parameter).
BINDINGS = {
    ("takeDrivingCommand", "in", "drivingCommand", "drivingCommand"),
    ("applyDrivingCommand", "out", "appliedCommand", "appliedCommand"),
}

#: Each allocation -> (requirement of phase 5, function): ten allocations, untyped, to the def-nested usages.
ALLOCATIONS = {
    "eeNetworkIdentityResponsibility": ("reqRecordNetworkIdentity", "recordNetworkIdentity"),
    "eeTakeOnlyFromSCOREPathResponsibility": ("reqCommandsOnlyFromSCOREPath", "takeDrivingCommand"),
    "eeCarryStreamUnchangedResponsibility": ("reqDeliverCommandStreamUnchanged", "carryDrivingCommand"),
    "eeCarriageTimeResponsibility": ("reqCarryEachCommandWithin50Ms", "carryDrivingCommand"),
    "eeDetectionPartsResponsibility": ("reqPassDetectionPartsOnAsTaken", "carryDrivingCommand"),
    "eeCheckValidCommandResponsibility": ("reqApplyEachValidCommand", "checkDrivingCommand"),
    "eeApplyValidCommandResponsibility": ("reqApplyEachValidCommand", "applyDrivingCommand"),
    "eeCheckLastValidCommandResponsibility": ("reqGiveOnlyLastValidCommand", "checkDrivingCommand"),
    "eeGiveLastValidCommandResponsibility": ("reqGiveOnlyLastValidCommand", "applyDrivingCommand"),
    "eeStopResponseResponsibility": ("reqStopResponseAfter200Ms", "applyDrivingCommand"),
}
ALLOCATION_COUNT = 10
#: Each requirement of phase 5 -> the functions it is allocated to.
ALLOCATED = {
    "reqCommandsOnlyFromSCOREPath": {"takeDrivingCommand"},
    "reqDeliverCommandStreamUnchanged": {"carryDrivingCommand"},
    "reqCarryEachCommandWithin50Ms": {"carryDrivingCommand"},
    "reqApplyEachValidCommand": {"checkDrivingCommand", "applyDrivingCommand"},
    "reqPassDetectionPartsOnAsTaken": {"carryDrivingCommand"},
    "reqGiveOnlyLastValidCommand": {"checkDrivingCommand", "applyDrivingCommand"},
    "reqStopResponseAfter200Ms": {"applyDrivingCommand"},
    "reqRecordNetworkIdentity": {"recordNetworkIdentity"},
}
#: REQ-EE-001 and REQ-EE-003 constrain the structure that realizes the functions: phases 7 and 8 carry them.
LEFT_TO_PHASES_7_AND_8 = {"reqBothRoutesInOneTopology": "REQ-EE-001", "reqCommandsOnlyOnTheirRoute": "REQ-EE-003"}
#: The group comment of each set of allocations, in order -> its text of record.
ALLOCATION_GROUPS = {
    "eeIdentityAllocations": (
        "recordNetworkIdentity carries REQ-EE-010: the record is made before the vehicle network takes the first "
        "driving command of each run."),
    "eeInputAllocations": (
        "takeDrivingCommand carries REQ-EE-002, a design constraint on the input of the vehicle network: it takes "
        "driving commands at the boundary interface from the Eclipse S-CORE path and from nowhere else."),
    "eeCarriageAllocations": (
        "carryDrivingCommand carries REQ-EE-004; REQ-EE-005, a performance requirement on the carriage; and "
        "REQ-EE-007, a design constraint on the detection parts that the carriage hands on, whose analysis rests on "
        "the realization that phase 8 records."),
    "eeActuationAllocations": (
        "checkDrivingCommand and applyDrivingCommand share REQ-EE-006 and REQ-EE-008: the check decides which commands "
        "are valid, and the application applies them and gives the vehicle only the last valid one. "
        "applyDrivingCommand alone carries REQ-EE-009, the stop response at the actuation ECU."),
}
#: The allocations each group comment introduces, in order.
GROUPED = {
    "eeIdentityAllocations": ["eeNetworkIdentityResponsibility"],
    "eeInputAllocations": ["eeTakeOnlyFromSCOREPathResponsibility"],
    "eeCarriageAllocations": ["eeCarryStreamUnchangedResponsibility", "eeCarriageTimeResponsibility",
                              "eeDetectionPartsResponsibility"],
    "eeActuationAllocations": ["eeCheckValidCommandResponsibility", "eeApplyValidCommandResponsibility",
                               "eeCheckLastValidCommandResponsibility", "eeGiveLastValidCommandResponsibility",
                               "eeStopResponseResponsibility"],
}

#: The states of the actuation ECU in a run, in order.
STATE_DEF = "EEActuationStates"
STATES = ["noValidCommandYet", "applyingValidCommands", "givingStopResponse"]
#: Each transition (source, target) -> the comment that states its meaning; none leaves givingStopResponse.
TRANSITIONS = {
    ("noValidCommandYet", "applyingValidCommands"):
        "the first valid driving command reaches the actuation ECU within 200 ms of simulation time after the start "
        "of the run",
    ("noValidCommandYet", "givingStopResponse"):
        "more than 200 ms of simulation time pass after the start of the run with no valid driving command reaching "
        "the actuation ECU",
    ("applyingValidCommands", "givingStopResponse"):
        "more than 200 ms of simulation time pass after the last valid driving command with no other reaching the "
        "actuation ECU",
}
#: The function whose behavior differs by state: (function usage, state); no other function depends on a state.
STATE_DEPENDENCIES = {
    ("applyDrivingCommand", "noValidCommandYet"),
    ("applyDrivingCommand", "applyingValidCommands"),
    ("applyDrivingCommand", "givingStopResponse"),
}

#: The root of the functions the context elements perform, outside the network's functional scope. Not an
#: AllocatableFunction: no context function carries a requirement of phase 5.
CONTEXT_FUNCTION_ROOT = "EEContextFunction"
#: Each context function -> its parameters (direction, name, item type), and the action of the operational flow
#: of phase 2 it follows, whose parameters it keeps.
CONTEXT_FUNCTIONS = {
    "EEGiveDrivingCommand": ([("out", "drivingCommand", "DrivingCommand")], "giveDrivingCommand"),
    "EECarryCommandOverSCORE": ([("in", "drivingCommand", "DrivingCommand"),
                                 ("out", "carriedCommand", "DrivingCommand")], "carryCommandOverSCORE"),
    "EEMoveVehicle": ([("in", "appliedCommand", "DrivingCommand")], "moveVehicle"),
}

PROCESS = "EEVehicleNetworkSystemProcess"
PROCESS_USAGE = "eeVehicleNetworkSystemProcess"
#: The one operational context of the increment (phase 2), whose parts the process binds its participants to.
CONTEXT_USAGE = "eeArchitectureOperationalContext"
#: Each participant of the process, in order -> its phase 2 type, the phase 2 context part it is bound to by
#: reference, and the actions it owns and performs (name -> definition). The network performs its flow usage.
PARTICIPANTS = {
    "commandSource": ("DrivingCommandSource", f"{CONTEXT_USAGE}::commandSource",
                      {"giveCommands": "EEGiveDrivingCommand"}),
    "scorePath": ("SCORECommandAndWarningPath", f"{CONTEXT_USAGE}::scorePath",
                  {"handOverCommands": "EECarryCommandOverSCORE"}),
    "vehicleNetwork": ("EEVehicleNetworkSystem", f"{CONTEXT_USAGE}::vehicleNetwork", {}),
    "vehicle": ("SubjectVehicle", f"{CONTEXT_USAGE}::vehicle", {"moveByActuation": "EEMoveVehicle"}),
}
#: The items of the process (source, target), in order, each end chained through the participant that owns it.
PROCESS_FLOWS = [
    ("commandSource.giveCommands.drivingCommand", "scorePath.handOverCommands.drivingCommand"),
    ("scorePath.handOverCommands.carriedCommand", f"vehicleNetwork.{FLOW_USAGE}.drivingCommand"),
    (f"vehicleNetwork.{FLOW_USAGE}.appliedCommand", "vehicle.moveByActuation.appliedCommand"),
]

#: The functional item definitions of the boundary -> the item each specializes.
BOUNDARY_ITEM_SPECIALIZATIONS = {"EEDrivingCommandInput": "DrivingCommandOutput", "EEActuationOutput": "DrivingCommand"}
#: What each boundary item adds, as ISQ quantity values. The input adds none: the driver-assistance increment
#: defines its quantities once.
BOUNDARY_ITEM_ATTRIBUTES = {
    "EEDrivingCommandInput": {},
    "EEActuationOutput": {"steeringAngle": "ISQ::AngularMeasureValue", "acceleration": "ISQ::AccelerationValue"},
}
#: The item of the driver-assistance increment the input reuses, and its quantities, defined once there.
DRIVING_ITEM = ("DrivingCommandOutput", "DrivingCommand", {
    "steeringAngle": "ISQ::AngularMeasureValue", "acceleration": "ISQ::AccelerationValue",
    "issueTime": "ISQ::DurationValue", "sequenceCount": "Natural", "checkValue": "Natural"})
#: Each port definition of the boundary -> its one directed item (direction, name, item definition).
BOUNDARY_PORTS = {
    "EEDrivingCommandInbound": ("in", "drivingCommand", "EEDrivingCommandInput"),
    "EEActuationOutbound": ("out", "appliedCommand", "EEActuationOutput"),
}
BOUNDARY = "EEVehicleNetworkFunctionalBoundary"
#: Each port usage of the boundary part -> its port definition.
BOUNDARY_PORT_USAGES = {"drivingCommandIn": "EEDrivingCommandInbound", "actuationOut": "EEActuationOutbound"}
#: How the boundary binds the flow's parameters to the port payloads (direction, parameter, binding), in order.
BOUNDARY_BINDINGS = [("in", "drivingCommand", "drivingCommandIn.drivingCommand"),
                     ("out", "appliedCommand", "actuationOut.appliedCommand")]

#: The phase 6 concerns, the catalogue concern definition each is typed by, and the parties that hold it.
CATALOGUE_CONCERNS = {
    CONCERN: ("FunctionalBehaviorConcern", {"SystemArchitect", "VerificationEngineer"}),
    INTERFACE_CONCERN: ("FunctionalInterfaceConcern", {"SystemsEngineer", "SoftwareDeveloper"}),
    STATES_CONCERN: ("SystemStateConcern", {"SafetyExpert", "SystemsEngineer"}),
}

#: Each view -> (type or "", render statement or "", viewpoint, exposures in order, framed concerns).
VIEWS = {
    TREE_VIEW: ("", "render asTreeDiagram;", "SystemFunctionalBreakdownStructureViewpoint", [FLOW_USAGE], [CONCERN]),
    PROCESS_VIEW: ("ActionFlowView", "", "SystemProcessViewpoint",
                   [f"{PROCESS}::*"] + [f"{PROCESS}::{participant}::*" for participant in PARTICIPANTS],
                   [PHASE_1_PROCESS_CONCERN]),
    TABLE_VIEW: ("TVD::TableView", "", "SystemStateViewpoint", [f"{STATE_DEF}::{state}" for state in STATES],
                 [STATES_CONCERN]),
    INTERFACE_VIEW: ("", "render asTreeDiagram;", "SystemInterfaceDefinitionViewpoint", sorted(BOUNDARY_PORTS),
                     [INTERFACE_CONCERN]),
}
#: Every view the package publishes: the four above and the matrix.
PUBLISHED_VIEWS = {MATRIX_VIEW, *VIEWS}
#: The table's columns: State, not Mode.
TABLE_COLUMNS = [("State", "CT::declaredName"), ("DependentFunctions", "CT::documentation")]
#: The two grids of the phase: key -> (title, description, row axis, column axis), pinned whole.
GRIDS = {
    f"matrix-{MATRIX_VIEW}": (
        "Vehicle network requirements by function",
        (
            "Each requirement of phase 5 and the functions of the vehicle network that carry it; no function carries "
            "REQ-EE-001 or REQ-EE-003 in this phase."),
        "requirements (requirement usages)", "system functions (action usages)"),
    f"table-{TABLE_VIEW}": (
        "Vehicle network states",
        (
            "The states of the actuation ECU in a run, by the valid driving commands that reach it, and the function "
            "whose behavior differs in each."),
        "states (state usages)", ""),
}
#: The note of the view index on the breakdown, in the form of the earlier increments.
TREE_VIEW_NOTE = (
    "SysIDE lists the items and the five functions of `eeVehicleNetworkFunctionalFlow` but does not draw the flows "
    "between them. The flows are modeled in the source, in the action definition `EEVehicleNetworkFunctionalFlow`, "
    "and the requirements each function carries are in `eeVehicleNetworkRequirementFunctionMatrixView`.")
#: The process view hides doc rows (the convention form), so the view index notes where its sequence is.
PROCESS_VIEW_NOTE = (
    "The diagram draws the four lanes, the action of the vehicle network and the three flows between them. The "
    "sequence from a fault to the stop response, and its times, are in the documentation of "
    "EEVehicleNetworkSystemProcess, whose rows the diagram hides.")

#: The decided usage names nested in the package, new on main like its top-level names.
NESTED_NAMES = {*FUNCTIONS, *STATES, "giveCommands", "handOverCommands", "moveByActuation",
                "eeFunctionBreakdownViewpoint", "eeRequirementFunctionViewpoint", "eeSystemProcessViewpoint",
                "eeStateTableViewpoint", "eeFunctionalInterfaceViewpoint"}

#: Words that would name an element of a route, a transport or a technology in a doc of the package.
ROUTE_AND_TECHNOLOGY = re.compile(
    r"(?i)\b(?:zone\s+controllers?|direct\s+link|backbone|gateways?|frames?|bus|ROS|DDS|Zenoh|SOME/IP|gRPC|KUKSA|"
    r"AUTOSAR|AAOS|VSS|VisionPilot|CARLA|Python|Linux)\b")
#: Buses and networks, matched by case so that the word "can" is no bus.
NETWORK_NAMES = re.compile(r"\b(?:CAN|LIN|FlexRay|Ethernet)\b")
#: The increment's texts use "mode" for power modes and for Integration Mode: the package does not use it.
MODE_WORD = re.compile(r"(?i)\bmodes?\b")
#: A past form of what a system does in a run, as the framing test reads the guide.
PAST_BEHAVIOR = re.compile(r"(?i)\b(?:braked|stopped|rejected|detected|routed|forwarded|passed|failed|"
                           r"dropped|recovered|crashed|hung|delivered)\b")
#: A clause or section number of a source.
CLAUSE_NUMBER = re.compile(r"(?i)\b(?:clause|section|§)\s*\d")

#: The texts of record of the design, pinned whole.
HEADER_PARAGRAPHS = [
    "DE4SDV E/E architecture functional architecture.",
    "INC-EE-001, phase 6: the functions of the vehicle network and the requirements of phase 5 each carries. Five "
    "functions record the network identity, take the driving command at the boundary interface, carry it to the "
    "actuation ECU, check it, apply it at the actuation ECU, and give the stop response when no valid driving command "
    "reaches the actuation ECU for more than 200 ms of simulation time. Eight requirements are allocated to the "
    "functions. The two left constrain the structure that realizes the functions, not what a function does: REQ-EE-001 "
    "holds both routes in one topology, and REQ-EE-003 keeps the commands of a run on the elements of its route. "
    "Phases 7 and 8 carry them by the elements that they place; the inspection of the realization that phase 8 "
    "records, and of the configuration of each run, verifies REQ-EE-001, and the records of the runs verify "
    "REQ-EE-003. An allocation assigns responsibility only (allocatedTo); it asserts no satisfaction. No logical "
    "element, element of a route, transport or technology is chosen, and no safety claim is made.",
    "The functions do not depend on the route: a run takes one route, and which elements carry a command on it is for "
    "the architecture phases. The stop response is given at the actuation ECU, the last element that a command "
    "reaches, by the function that applies the valid driving commands, on the same output: it is a state of that "
    "function, not a second source of commands. Which element checks a command, and where each element takes the "
    "simulation time, are left to phases 7 and 8; every time here counts on the one clock of the virtual vehicle that "
    "the testbed gives every element.",
    "The vehicle network in operation is a process, not a second architecture: the command source gives the driving "
    "command, the Eclipse S-CORE path hands it to the vehicle network at the boundary interface, and the vehicle moves "
    "by what the actuation ECU gives it. Those are functions of the context elements, outside the scope of the vehicle "
    "network, and EEVehicleNetworkSystemProcess runs the network as one action between them, with the sequence from a "
    "fault to the stop response. Its participants are the parts of the one operational context of phase 2, bound by "
    "reference. The function whose behavior differs by state depends on the states of EEActuationStates, and the "
    "conceptual interfaces of the network are the ports of EEVehicleNetworkFunctionalBoundary, whose items specialize "
    "the driving command of phase 2 and the item that the driver-assistance increment defines for it. No vehicle "
    "signal specification is imported or used anywhere in this package: the interface items are conceptual, their "
    "quantities are ISQ quantity values, and the signal typing of an interface starts in phase 8.",
]
#: The header sentence that leaves REQ-EE-001 and REQ-EE-003 to phases 7 and 8.
LEFT_SENTENCES = (
    "The two left constrain the structure that realizes the functions, not what a function does: REQ-EE-001 holds "
    "both routes in one topology, and REQ-EE-003 keeps the commands of a run on the elements of its route.",
    "Phases 7 and 8 carry them by the elements that they place; the inspection of the realization that phase 8 "
    "records, and of the configuration of each run, verifies REQ-EE-001, and the records of the runs verify "
    "REQ-EE-003.")

FUNCTION_DOCS = {
    "EERecordNetworkIdentity": (
        "Records the network identity of the vehicle network before it takes the first driving command of each run, so "
        "that each verdict binds the route, the commit with its difference, the configuration and the settings that "
        "ran."),
    "EETakeDrivingCommand": (
        "Takes each driving command at the boundary interface as the Eclipse S-CORE path gives it there, at the "
        "simulation time at which the path gives it, and takes driving commands from nowhere else."),
    "EECarryDrivingCommand": (
        "Carries each driving command taken at the boundary interface to the actuation ECU, once, in its order and "
        "with each part as the path gave it, and hands its detection parts on as it received them, computing none of "
        "them anew. In a run without a fault each command reaches the actuation ECU within 50 ms of simulation time "
        "after it is taken. Around a fault it goes on carrying each command that the fault does not affect."),
    "EECheckDrivingCommand": (
        "Decides, by the term valid driving command, whether each driving command that reaches the actuation ECU is "
        "valid: its check value, its sequence count against the reference count, and its issue time against the "
        "simulation time at which it reaches the actuation ECU. It passes each valid command on to be applied, and "
        "nothing in place of an invalid one."),
    "EEApplyDrivingCommand": (
        "Applies each valid driving command at the actuation ECU when it reaches it, and gives the vehicle the "
        "steering angle and the acceleration of the last valid command that it applied, and nothing before the first. "
        "Once more than 200 ms of simulation time pass with no valid driving command reaching the actuation ECU, "
        "counted from the last one or from the start of the run when none did, it applies no driving command that "
        "reaches it after that, and gives the vehicle the stop response on the same output, from no later than 300 ms "
        "of simulation time after that last valid command or the start of the run until the run ends."),
}
ITEM_DOCS = {"EENetworkIdentityRecord": (
    "The record of the network identity of one run, by the term network identity, made before the vehicle network "
    "takes the first driving command of the run.")}
CONTEXT_ROOT_DOC = (
    "A behavior of a context element of phase 2 while the vehicle network operates. It is outside the scope of the "
    "vehicle network: the network does not provide it and no requirement of phase 5 is allocated to it.")
CONTEXT_DOCS = {
    "EEGiveDrivingCommand": (
        "The command source: gives each driving command, in this increment the command of the driver-assistance "
        "candidate with its detection parts."),
    "EECarryCommandOverSCORE": (
        "The Eclipse S-CORE path: hands each driving command to the vehicle network at the boundary interface, with no "
        "exchange beside it."),
    "EEMoveVehicle": (
        "The vehicle: steering, acceleration and brakes move it by what the actuation ECU gives it; nothing flows back "
        "to the vehicle network."),
}
FLOW_DOC = (
    "The vehicle network broken into its functions, and the items they exchange. The driving command comes from the "
    "Eclipse S-CORE path at the boundary interface, and what the actuation ECU gives goes to the vehicle: the steering "
    "angle and the acceleration of the last valid driving command, or the stop response. Only what applyDrivingCommand "
    "gives leaves the network. The network identity is recorded before the network takes the first driving command of "
    "each run.")
PARTICIPANT_DOCS = {
    "commandSource": (
        "The command source of phase 2: gives each driving command."),
    "scorePath": (
        "The Eclipse S-CORE path of phase 2: hands each driving command to the vehicle network at the boundary "
        "interface, with no exchange beside it."),
    "vehicleNetwork": (
        "The system of interest of phase 2: it performs its whole functional flow, the one usage its functional "
        "boundary performs. Around a fault it goes on carrying each driving command that the fault does not affect, "
        "and at the actuation ECU it applies only the valid ones, so the vehicle keeps the steering angle and the "
        "acceleration of the last valid command. Once more than 200 ms of simulation time pass with no valid driving "
        "command reaching the actuation ECU, it applies no driving command that reaches the actuation ECU after that "
        "and gives the vehicle the stop response there, from no later than 300 ms of simulation time after the last "
        "valid command, or after the start of the run when none reached the actuation ECU, until the run ends."),
    "vehicle": (
        "The vehicle of phase 2: steering, acceleration and brakes move it by what the actuation ECU gives it; nothing "
        "flows back."),
}
PROCESS_PARAGRAPHS = [
    "One run of the vehicle network in operation, as a process. The participants are the context parts of phase 2 "
    "themselves and the system of interest, bound by reference: the process declares no part of its own, so the "
    "increment has one context. Each participant owns and performs its functions, as the swim lane of its functions: "
    "the command source gives each driving command, and the Eclipse S-CORE path hands it to the vehicle network at the "
    "boundary interface. The vehicle network records its network identity, takes the command, carries it to the "
    "actuation ECU, checks it, and applies it at the actuation ECU, as one action of the process. The vehicle moves by "
    "what the actuation ECU gives it and sends nothing back. The functions of the context elements are outside the "
    "scope of the vehicle network; its functional scope is the one functional flow usage it performs. The items that "
    "cross its boundary are the flows of the process, each chained through the participant that gives and the one that "
    "takes.",
    "The sequence from a fault to the response: a fault, made from outside the vehicle network, loses a driving "
    "command on the route of the run, holds it so that it reaches the actuation ECU more than 100 ms of simulation "
    "time after its issue time, repeats it or corrupts it, or takes a link of that route down for the rest of the run. "
    "The carriage goes on with each command that the fault does not affect. The check decides by the term valid "
    "driving command which of the commands that reach the actuation ECU are valid, and nothing is applied in place of "
    "an invalid one, so the vehicle keeps the steering angle and the acceleration of the last valid command. Once more "
    "than 200 ms of simulation time pass with no valid driving command reaching the actuation ECU, the actuation ECU "
    "applies no driving command that reaches it after that and gives the vehicle the stop response itself: a "
    "deceleration of 4 m/s², within the tolerance of REQ-DRIVING-020, with the steering angle of the last valid "
    "driving command that it applied, or 0° when it applied none, from no later than 300 ms after the last valid "
    "command, or after the start of the run when none reached it, until the run ends. In SC-EE-004 a link of the route "
    "goes down, so no valid command reaches the actuation ECU after it, and the vehicle gets the stop response, as "
    "phase 2 states for that scenario. Every time counts on the one clock of the virtual vehicle that the testbed "
    "gives every element. No element, transport or technology is fixed here.",
]
STATE_DEF_DOC = (
    "The states of the actuation ECU in a run, by the valid driving commands that reach it. It has no valid command "
    "from the start of each run until the first one reaches it, and once it gives the stop response it gives it until "
    "the run ends.")
STATE_DOCS = {
    "noValidCommandYet": (
        "No valid driving command has reached the actuation ECU in this run: applyDrivingCommand gives the vehicle "
        "nothing (REQ-EE-008)."),
    "applyingValidCommands": (
        "applyDrivingCommand applies each valid driving command that reaches the actuation ECU and gives the vehicle "
        "the steering angle and the acceleration of the last one that it applied (REQ-EE-006, REQ-EE-008). An invalid "
        "command changes nothing."),
    "givingStopResponse": (
        "Entered once more than 200 ms of simulation time pass with no valid driving command reaching the actuation "
        "ECU. From then on applyDrivingCommand applies no driving command that reaches the actuation ECU. Until the "
        "stop response starts, it gives the vehicle the steering angle and the acceleration of the last valid driving "
        "command that it applied, or nothing when it applied none (REQ-EE-008). From no later than 300 ms of "
        "simulation time after the last valid command, or after the start of the run when none reached the actuation "
        "ECU, until the run ends, it gives the vehicle the stop response: a deceleration of 4 m/s², within the "
        "tolerance of REQ-DRIVING-020, with the steering angle of that last valid driving command, or 0° when it "
        "applied none (REQ-EE-009)."),
}
BOUNDARY_ITEM_DOCS = {
    "EEDrivingCommandInput": (
        "The driving command as it reaches the boundary interface of the vehicle network: the command that the "
        "driver-assistance system gives at its boundary, its steering angle and its acceleration with its detection "
        "parts."),
    "EEActuationOutput": (
        "What the actuation ECU gives the vehicle: the steering angle and the acceleration of the last valid driving "
        "command that it applied, or, during the stop response, the steering angle of the stop response and its "
        "deceleration as an acceleration below zero. It carries no detection part."),
}
PORT_DOCS = {
    "EEDrivingCommandInbound": (
        "The input port of the driving command at the boundary interface: the Eclipse S-CORE path gives it there."),
    "EEActuationOutbound": (
        "The output port of what the actuation ECU gives the vehicle: the vehicle takes it."),
}
BOUNDARY_DOC = (
    "The vehicle network as a functional boundary: one input port and one output port, each with the item of one "
    "exchange of phase 2, typed by an item definition of this package that specializes the driving command of phase 2 "
    "or the item that the driver-assistance increment defines for it. It performs the functional flow of the network.")
CONCERN_DOCS = {
    CONCERN: (
        "System architects and verification engineers need the functions of the vehicle network and each requirement "
        "of phase 5 mapped to the functions that carry it: phase 7 gives the functions to logical elements, and phase "
        "10 verifies each requirement on its functions."),
    INTERFACE_CONCERN: (
        "Systems engineers and software developers need the conceptual interfaces of the vehicle network before phase "
        "7 allocates its functions and phase 8 places elements and software on them: the port at its boundary for each "
        "item that crosses it, the direction of that item, and the item that the port's item specializes. Signal "
        "typing at a software contract belongs to phase 8."),
    STATES_CONCERN: (
        "Safety experts and systems engineers need the states of the actuation ECU in a run, by the valid driving "
        "commands that reach it, and the function whose behavior differs in each: before the first valid command, "
        "while it applies valid commands, and once more than 200 ms of simulation time pass without a valid driving "
        "command, until the run ends."),
}

#: The guide: its Status line and the next obligation, which phase 6 moves.
GUIDE_STATUS = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification, "
    "Phase 4 stakeholder needs, Phase 5 requirements and Phase 6 functional architecture, proposal.**")
GUIDE_STATUS_PHASE_5 = (
    "**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability classification, "
    "Phase 4 stakeholder needs and Phase 5 requirements, proposal.**")
#: The paragraph of the next obligation: the go for phase 6 with its date, and phase 7 next.
GUIDE_NEXT_PARAGRAPH = (
    "Use the Method Check of the reviewed pull request to select the next obligation, not the phase number alone. "
    "Phase 3, the capability classification, records no feature-model delta, and review judges it: its one blocking "
    "check has nothing to evaluate, so the Method Check lists Phase 3 as vacuous, with a prompt for review. The owner "
    "decided on 2026-11-18 to carry out Phases 1 to 3 of this increment before the baseline of the driver-assistance "
    "increment, whose driving command it carries. After that baseline, the owner decided on 2026-11-21 to start "
    "Phase 4, on 2026-11-22 to go on with Phase 5 and on 2026-11-24 to go on with Phase 6. The next model obligation "
    "is **Phase 7**, the logical architecture. The testbed with its readiness probe waits for a further decision of "
    "the owner.")
GUIDE_NEXT = "The next model obligation is **Phase 7**, the logical architecture."
GUIDE_HEADING = "## Functional architecture (Phase 6)"
#: The paragraphs of the guide's Phase 6 section, whole and in order.
GUIDE_PARAGRAPHS = [
    "Phase 6 breaks the vehicle network into five functions in DE4SDV_EEArchitectureFunctionalArchitecture: "
    "recordNetworkIdentity, takeDrivingCommand, carryDrivingCommand, checkDrivingCommand and applyDrivingCommand. "
    "Eight of the ten requirements of Phase 5 are allocated to them. takeDrivingCommand carries REQ-EE-002; "
    "carryDrivingCommand carries REQ-EE-004, REQ-EE-005 and REQ-EE-007; checkDrivingCommand and applyDrivingCommand "
    "share REQ-EE-006 and REQ-EE-008; applyDrivingCommand carries REQ-EE-009; and recordNetworkIdentity carries "
    "REQ-EE-010. REQ-EE-001 and REQ-EE-003 constrain the structure that realizes the functions, so Phases 7 and 8 "
    "carry them by the elements that they place.",
    "The functions do not depend on the route. The stop response is a state of applyDrivingCommand and leaves on the "
    "same output as the applied command, as the operational context of Phase 2 says: the actuation ECU gives it "
    "itself, as INC-DRIVING-001 does at its own actuation. checkDrivingCommand stands apart from the application "
    "because Phase 5 leaves open which element detects and rejects a command; Phase 7 gives each function to a logical "
    "element.",
    "EEVehicleNetworkSystemProcess runs the network between the parts of the Phase 2 context: the command source, the "
    "Eclipse S-CORE path and the vehicle, bound by reference. Its documentation holds the sequence from a fault to the "
    "stop response, which answers eeNetworkFaultResponseConcern. EEActuationStates holds the three states of the "
    "actuation ECU in a run. The boundary has one input port, whose item specializes the driving command of the "
    "driver-assistance increment, and one output port, which carries only the steering angle and the acceleration.",
    "Five views show it: the function breakdown, the requirement by function matrix, the system process, the state "
    "table and the functional interfaces. Left open for Phases 7 and 8: which element checks a command and where each "
    "element takes the simulation time. Left to Phase 8, which chooses the technology: how a zone controller repacks "
    "the command, whether the command fits a CAN frame, and the medium of the direct link.",
]

#: The package's code, every declaration at its own depth (two spaces a level), as `_skeleton` reads it: generated
#: from the model, never written by hand. A line ending in a backslash continues on the next.
SKELETON = """\
/*…*/
package DE4SDV_EEArchitectureFunctionalArchitecture {
  private import DE4SDV_Stakeholders::*;
  private import DE4SDV_TraceVocabulary::AllocatableFunction;
  private import DE4SDV_EEArchitectureFraming::EEVehicleNetworkSystem;
  private import DE4SDV_EEArchitectureFraming::eeNetworkFaultResponseConcern;
  private import DE4SDV_EEArchitectureOperationalContext::DrivingCommandSource;
  private import DE4SDV_EEArchitectureOperationalContext::eeArchitectureOperationalContext;
  private import DE4SDV_DriverAssistanceOperationalContext::DrivingCommand;
  private import DE4SDV_DriverAssistanceOperationalContext::SCORECommandAndWarningPath;
  private import DE4SDV_OperationalContext::SubjectVehicle;
  private import DE4SDV_DriverAssistanceFunctionalArchitecture::DrivingCommandOutput;
  private import DE4SDV_EEArchitectureNeedsRequirements::*;
  private import SAF_Viewpoints::*;
  private import StandardViewDefinitions::*;
  private import SysideViews::**;
  private import Views::*;
  /* The item the functions exchange inside the vehicle network */
  item def EENetworkIdentityRecord {
    doc /*…*/
  /* The functions of the context elements of phase 2 */
  action def EEContextFunction {
    doc /*…*/
  action def EEGiveDrivingCommand :> EEContextFunction {
    doc /*…*/
    out drivingCommand : DrivingCommand;
  action def EECarryCommandOverSCORE :> EEContextFunction {
    doc /*…*/
    in drivingCommand : DrivingCommand;
    out carriedCommand : DrivingCommand;
  action def EEMoveVehicle :> EEContextFunction {
    doc /*…*/
    in appliedCommand : DrivingCommand;
  /* Functions */
  action def EERecordNetworkIdentity :> AllocatableFunction {
    doc /*…*/
    out identityRecord : EENetworkIdentityRecord;
  action def EETakeDrivingCommand :> AllocatableFunction {
    doc /*…*/
    in drivingCommand : DrivingCommand;
    out takenCommand : DrivingCommand;
  action def EECarryDrivingCommand :> AllocatableFunction {
    doc /*…*/
    in takenCommand : DrivingCommand;
    out carriedCommand : DrivingCommand;
  action def EECheckDrivingCommand :> AllocatableFunction {
    doc /*…*/
    in carriedCommand : DrivingCommand;
    out validCommand : DrivingCommand;
  action def EEApplyDrivingCommand :> AllocatableFunction {
    doc /*…*/
    in validCommand : DrivingCommand;
    out appliedCommand : DrivingCommand;
  /* The functional breakdown of the vehicle network */
  action def EEVehicleNetworkFunctionalFlow {
    doc /*…*/
    in item drivingCommand : DrivingCommand;
    out item appliedCommand : DrivingCommand;
    action recordNetworkIdentity : EERecordNetworkIdentity {
      out identityRecord;
    action takeDrivingCommand : EETakeDrivingCommand {
      in drivingCommand = EEVehicleNetworkFunctionalFlow::drivingCommand;
      out takenCommand;
    first recordNetworkIdentity then takeDrivingCommand;
    action carryDrivingCommand : EECarryDrivingCommand {
      in takenCommand;
      out carriedCommand;
    flow from takeDrivingCommand.takenCommand to carryDrivingCommand.takenCommand;
    action checkDrivingCommand : EECheckDrivingCommand {
      in carriedCommand;
      out validCommand;
    flow from carryDrivingCommand.carriedCommand to checkDrivingCommand.carriedCommand;
    action applyDrivingCommand : EEApplyDrivingCommand {
      in validCommand;
      out appliedCommand = EEVehicleNetworkFunctionalFlow::appliedCommand;
    flow from checkDrivingCommand.validCommand to applyDrivingCommand.validCommand;
  action eeVehicleNetworkFunctionalFlow : EEVehicleNetworkFunctionalFlow;
  /* The system process: the vehicle network between the context elements */
  action def EEVehicleNetworkSystemProcess {
    doc /*…*/
    ref part commandSource : DrivingCommandSource = eeArchitectureOperationalContext::commandSource {
      doc /*…*/
      perform action giveCommands : EEGiveDrivingCommand;
    ref part scorePath : SCORECommandAndWarningPath = eeArchitectureOperationalContext::scorePath {
      doc /*…*/
      perform action handOverCommands : EECarryCommandOverSCORE;
    ref part vehicleNetwork : EEVehicleNetworkSystem = eeArchitectureOperationalContext::vehicleNetwork {
      doc /*…*/
      perform eeVehicleNetworkFunctionalFlow;
    ref part vehicle : SubjectVehicle = eeArchitectureOperationalContext::vehicle {
      doc /*…*/
      perform action moveByActuation : EEMoveVehicle;
    flow from commandSource.giveCommands.drivingCommand to scorePath.handOverCommands.drivingCommand;
    flow from scorePath.handOverCommands.carriedCommand to \
vehicleNetwork.eeVehicleNetworkFunctionalFlow.drivingCommand;
    flow from vehicleNetwork.eeVehicleNetworkFunctionalFlow.appliedCommand to \
vehicle.moveByActuation.appliedCommand;
  action eeVehicleNetworkSystemProcess : EEVehicleNetworkSystemProcess;
  /* States */
  state def EEActuationStates {
    doc /*…*/
    state noValidCommandYet {
      doc /*…*/
    state applyingValidCommands {
      doc /*…*/
    state givingStopResponse {
      doc /*…*/
    transition first noValidCommandYet then applyingValidCommands;
    transition first noValidCommandYet then givingStopResponse;
    transition first applyingValidCommands then givingStopResponse;
  /* The function whose behavior differs by state depends on it */
  dependency eeApplyDrivingCommandDependsOnNoValidCommandYetState from \
EEVehicleNetworkFunctionalFlow::applyDrivingCommand to EEActuationStates::noValidCommandYet;
  dependency eeApplyDrivingCommandDependsOnApplyingValidCommandsState from \
EEVehicleNetworkFunctionalFlow::applyDrivingCommand to EEActuationStates::applyingValidCommands;
  dependency eeApplyDrivingCommandDependsOnGivingStopResponseState from \
EEVehicleNetworkFunctionalFlow::applyDrivingCommand to EEActuationStates::givingStopResponse;
  /* The conceptual interfaces of the vehicle network */
  item def EEDrivingCommandInput :> DrivingCommandOutput {
    doc /*…*/
  item def EEActuationOutput :> DrivingCommand {
    doc /*…*/
    attribute steeringAngle : ISQ::AngularMeasureValue;
    attribute acceleration : ISQ::AccelerationValue;
  port def EEDrivingCommandInbound {
    doc /*…*/
    in item drivingCommand : EEDrivingCommandInput;
  port def EEActuationOutbound {
    doc /*…*/
    out item appliedCommand : EEActuationOutput;
  part def EEVehicleNetworkFunctionalBoundary :> EEVehicleNetworkSystem {
    doc /*…*/
    port drivingCommandIn : EEDrivingCommandInbound;
    port actuationOut : EEActuationOutbound;
    perform eeVehicleNetworkFunctionalFlow : EEVehicleNetworkFunctionalFlow {
      in item drivingCommand = drivingCommandIn.drivingCommand;
      out item appliedCommand = actuationOut.appliedCommand;
  /* Requirement-to-function allocations (allocatedTo) */
  comment eeIdentityAllocations /*…*/
  allocation eeNetworkIdentityResponsibility allocate reqRecordNetworkIdentity to \
EEVehicleNetworkFunctionalFlow::recordNetworkIdentity;
  comment eeInputAllocations /*…*/
  allocation eeTakeOnlyFromSCOREPathResponsibility allocate reqCommandsOnlyFromSCOREPath to \
EEVehicleNetworkFunctionalFlow::takeDrivingCommand;
  comment eeCarriageAllocations /*…*/
  allocation eeCarryStreamUnchangedResponsibility allocate reqDeliverCommandStreamUnchanged to \
EEVehicleNetworkFunctionalFlow::carryDrivingCommand;
  allocation eeCarriageTimeResponsibility allocate reqCarryEachCommandWithin50Ms to \
EEVehicleNetworkFunctionalFlow::carryDrivingCommand;
  allocation eeDetectionPartsResponsibility allocate reqPassDetectionPartsOnAsTaken to \
EEVehicleNetworkFunctionalFlow::carryDrivingCommand;
  comment eeActuationAllocations /*…*/
  allocation eeCheckValidCommandResponsibility allocate reqApplyEachValidCommand to \
EEVehicleNetworkFunctionalFlow::checkDrivingCommand;
  allocation eeApplyValidCommandResponsibility allocate reqApplyEachValidCommand to \
EEVehicleNetworkFunctionalFlow::applyDrivingCommand;
  allocation eeCheckLastValidCommandResponsibility allocate reqGiveOnlyLastValidCommand to \
EEVehicleNetworkFunctionalFlow::checkDrivingCommand;
  allocation eeGiveLastValidCommandResponsibility allocate reqGiveOnlyLastValidCommand to \
EEVehicleNetworkFunctionalFlow::applyDrivingCommand;
  allocation eeStopResponseResponsibility allocate reqStopResponseAfter200Ms to \
EEVehicleNetworkFunctionalFlow::applyDrivingCommand;
  /* Views */
  concern eeVehicleNetworkFunctionsConcern : FunctionalBehaviorConcern {
    doc /*…*/
    subject;
    stakeholder systemArchitect : SystemArchitect;
    stakeholder verificationEngineer : VerificationEngineer;
  view eeVehicleNetworkFunctionBreakdownView {
    viewpoint eeFunctionBreakdownViewpoint : SystemFunctionalBreakdownStructureViewpoint {
      frame eeVehicleNetworkFunctionsConcern;
    expose eeVehicleNetworkFunctionalFlow;
    render asTreeDiagram;
  view eeVehicleNetworkRequirementFunctionMatrixView : MVD::MatrixView {
    viewpoint eeRequirementFunctionViewpoint : SystemRequirementTraceabilityViewpoint {
      frame eeVehicleNetworkFunctionsConcern;
    view :>> rowView {
      expose reqBothRoutesInOneTopology;
      expose reqCommandsOnlyFromSCOREPath;
      expose reqCommandsOnlyOnTheirRoute;
      expose reqDeliverCommandStreamUnchanged;
      expose reqCarryEachCommandWithin50Ms;
      expose reqApplyEachValidCommand;
      expose reqPassDetectionPartsOnAsTaken;
      expose reqGiveOnlyLastValidCommand;
      expose reqStopResponseAfter200Ms;
      expose reqRecordNetworkIdentity;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    view :>> columnView {
      expose eeVehicleNetworkFunctionalFlow::recordNetworkIdentity;
      expose eeVehicleNetworkFunctionalFlow::takeDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::carryDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::checkDrivingCommand;
      expose eeVehicleNetworkFunctionalFlow::applyDrivingCommand;
      attribute :>> includeReferenceElements = true;
      attribute :>> representation = Rep::name;
    view :>> cellView {
      expose DE4SDV_EEArchitectureFunctionalArchitecture::*;
      attribute :>> direction = SysideViews::MatrixTraceabilityDirection::row2col;
  /* The vehicle network in operation as a process: the sequence from a fault to the stop response */
  view eeVehicleNetworkSystemProcessView : ActionFlowView {
    viewpoint eeSystemProcessViewpoint : SystemProcessViewpoint {
      frame eeNetworkFaultResponseConcern;
    expose EEVehicleNetworkSystemProcess::*;
    expose EEVehicleNetworkSystemProcess::commandSource::*;
    expose EEVehicleNetworkSystemProcess::scorePath::*;
    expose EEVehicleNetworkSystemProcess::vehicleNetwork::*;
    expose EEVehicleNetworkSystemProcess::vehicle::*;
    attribute showAnnotationRows = false;
    attribute maxCompartmentEntries = 0;
  /* The states, and the function that depends on them */
  concern eeActuationStatesConcern : SystemStateConcern {
    doc /*…*/
    subject;
    stakeholder safetyExpert : SafetyExpert;
    stakeholder systemsEngineer : SystemsEngineer;
  view eeVehicleNetworkStateTableView : TVD::TableView {
    viewpoint eeStateTableViewpoint : SystemStateViewpoint {
      frame eeActuationStatesConcern;
    expose EEActuationStates::noValidCommandYet;
    expose EEActuationStates::applyingValidCommands;
    expose EEActuationStates::givingStopResponse;
    filter @ SysML::StateUsage;
    attribute :>> maxRowHeight = 300;
    view State :> columnViews {
      attribute :>> featureToRender = CT::declaredName;
    view DependentFunctions :> columnViews {
      attribute :>> featureToRender = CT::documentation;
      attribute :>> columnWidth = 360;
  /* The conceptual interfaces of the vehicle network */
  concern eeVehicleNetworkInterfaceConcern : FunctionalInterfaceConcern {
    doc /*…*/
    subject;
    stakeholder systemsEngineer : SystemsEngineer;
    stakeholder softwareDeveloper : SoftwareDeveloper;
  view eeVehicleNetworkFunctionalInterfaceView {
    viewpoint eeFunctionalInterfaceViewpoint : SystemInterfaceDefinitionViewpoint {
      frame eeVehicleNetworkInterfaceConcern;
    expose EEActuationOutbound;
    expose EEDrivingCommandInbound;
    attribute showAnnotationRows = false;
    render asTreeDiagram;
"""


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(re.sub(r"//\*.*?\*/", "", _raw(), flags=re.S))


def _flat(text: str) -> str:
    """The text of a doc or comment body, whitespace collapsed; only the `*` that leads a line is dropped."""
    return " ".join(re.sub(r"(?m)^\s*\*(?!/)\s?", "", text).split())


def _doc(declaration: str) -> str:
    """The doc text of the element whose body follows ``declaration`` in the raw model."""
    assert _raw().count(declaration) == 1, f"{declaration}: one copy in the file, so that no note holds a decoy"
    body = braced_body(_raw(), declaration)
    match = re.match(r"\s*doc\s*/\*(.*?)\*/", body, re.S)
    assert match, f"{declaration}: the doc must open the body"
    return _flat(match.group(1))


def _comment(name: str) -> str:
    """The text of the named comment."""
    match = re.search(rf"(?m)^  comment\s+{name}\s*/\*(.*?)\*/", _raw(), re.S)
    assert match, name
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


def _flow_body() -> str:
    return braced_body(_code(), f"action def {FLOW}")


def _process_body() -> str:
    return braced_body(_code(), f"action def {PROCESS}")


def _process_paragraphs() -> list[str]:
    assert _raw().count(f"action def {PROCESS}") == 1, \
        "one copy of the process in the file, so that no note holds a decoy"
    raw = braced_body(_raw(), f"action def {PROCESS}")
    match = re.match(r"\s*doc\s*/\*(.*?)\*/", raw, re.S)
    assert match, "the doc must open the body of the process"
    return _paragraphs(match.group(1))


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


def _allocation_rows() -> list[tuple[str, str, str]]:
    code = _code()
    rows = re.findall(rf"\ballocation\s+(\w+)\s+allocate\s+(\w+)\s+to\s+{FLOW}::(\w+)\s*;", code)
    assert len(rows) == len(re.findall(r"\ballocate\b", code)), "every allocation has the one untyped form"
    assert len(rows) == len(re.findall(r"\ballocation\b", code)), "every allocation usage has that form"
    return rows


def _allocations() -> dict[str, set[str]]:
    allocated: dict[str, set[str]] = {}
    for _, requirement, function in _allocation_rows():
        allocated.setdefault(requirement, set()).add(function)
    return allocated


def _requirements() -> list[tuple[str, str, str]]:
    """(short name, name, definition) of each requirement of phase 5, in declaration order."""
    code = strip_comments(NEEDS_REQUIREMENTS.read_text(encoding="utf-8"))
    return re.findall(r"\brequirement\s+<'(REQ-EE-\d{3})'>\s+(\w+)\s*:\s*(\w+)\s*\{", code)


def _docs() -> list[str]:
    """Every comment and doc text of the package, flattened."""
    return [_flat(text) for text in re.findall(r"/\*(.*?)\*/", _raw(), re.S)] + \
        [_flat(text) for text in re.findall(r"//([^\n]*)", _raw())]


def _transitions(machine: str) -> dict[tuple[str, str], str]:
    """Each transition of the raw state machine -> its comment, the continuation lines of the comment joined."""
    found = {}
    for match in re.finditer(r"(?m)^\s*transition\s+first\s+(\w+)\s+then\s+(\w+);[ \t]*//(.*)\n((?:[ \t]+//.*\n)*)",
                             machine):
        lines = [match[3]] + re.findall(r"//(.*)", match[4])
        found[(match[1], match[2])] = " ".join(" ".join(lines).split())
    return found


def _attributes(body: str) -> dict[str, str]:
    declared = dict(re.findall(r"\battribute\s+(\w+)\s*:\s*([\w:]+(?:\[[^\]]*\])?)\s*;", body))
    assert len(re.findall(r"\battribute\b", body)) == len(declared)
    return declared


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


def test_the_charter_names_the_package_after_the_needs_and_requirements():
    charter = braced_body(strip_comments(FRAMING.read_text(encoding="utf-8")),
                          "part eeArchitectureCharter : IncrementCharter")
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts
    names = re.findall(r'"([^"]+)"', artifacts.group(1))
    assert names[-1] == PACKAGE and names.index(PACKAGE) == names.index("DE4SDV_EEArchitectureNeedsRequirements") + 1
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
    assert re.search(rf"\baction\s+{FLOW_USAGE}\s*:\s*{FLOW}\s*;", code)
    for name, parameters in FUNCTION_PARAMETERS.items():
        body = _direct(braced_body(code, f"action def {name} :> AllocatableFunction"))
        assert re.findall(r"\b(in|out)\s+(\w+)\s*:\s*(\w+)\s*;", body) == parameters, name


def test_every_directed_feature_of_a_function_is_one_of_its_parameters():
    """No second output of a function, no time input of the check: every directed feature (in, out, inout, of any
    kind) of each function and context function, read in the code, is one of its pinned parameters, and each owns
    its doc and its parameters only, so no nested action brings an output of its own."""
    code = _code()
    bases = {**{name: "AllocatableFunction" for name in FUNCTION_PARAMETERS},
             **{name: CONTEXT_FUNCTION_ROOT for name in CONTEXT_FUNCTIONS}}
    pinned = {**FUNCTION_PARAMETERS, **{name: parameters for name, (parameters, _) in CONTEXT_FUNCTIONS.items()}}
    assert len(bases) == len(FUNCTIONS) + len(CONTEXT_FUNCTIONS) == 8
    for name, base in bases.items():
        body = _direct(braced_body(code, f"action def {name} :> {base}"))
        assert len(re.findall(r"\b(?:in|out|inout)\b", body)) == len(pinned[name]), \
            f"{name}: no other directed feature"
        rest = re.sub(r"\b(?:in|out)\s+\w+\s*:\s*\w+\s*;", "", braced_body(code, f"action def {name} :> {base}"))
        assert rest.split() == ["doc"], f"{name}: owns its doc and its parameters only"


def test_the_flow_breaks_the_network_into_the_five_functions():
    direct = _direct(_flow_body())
    assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", direct) == FLOW_PARAMETERS
    assert len(re.findall(r"\b(?:in|out|inout)\b", direct)) == len(FLOW_PARAMETERS), \
        "the flow has one input and one output"
    assert list(re.findall(r"\baction\s+(\w+)\s*:\s*(\w+)\s*\{", direct)) == list(FUNCTIONS.items()), \
        "the breakdown keeps the order of the functions"
    assert FLOW_DOC == _doc(f"action def {FLOW}")


def test_the_functions_exchange_exactly_three_plain_flows_and_one_succession():
    """Every exchange is a whole-line `flow from <a>.<x> to <b>.<y>;`, in the order of the command; no other kind of
    exchange, no succession flow, and the one succession records the network identity first."""
    body = _flow_body()
    assert re.findall(r"(?m)^\s*flow\s+from\s+([\w.]+)\s+to\s+([\w.]+)\s*;\s*$", body) == FLOWS
    assert len(re.findall(r"\bflow\b", body)) == len(FLOWS), "no other flow"
    assert not re.search(r"\b(?:succession|message|bind|connect|connection|interface|allocate)\b", body), \
        "the functions exchange nothing but plain flows"
    assert re.findall(r"(?m)^\s*first\s+(\w+)\s+then\s+(\w+)\s*;\s*$", body) == SUCCESSIONS
    assert len(re.findall(r"\b(?:first|then)\b", body)) == 2 * len(SUCCESSIONS)
    bound = set()
    for function, definition in FUNCTIONS.items():
        usage = braced_body(body, f"action {function} : {definition}")
        for direction, parameter, outer in re.findall(rf"\b(in|out)\s+(\w+)\s*=\s*{FLOW}::(\w+)\s*;", usage):
            bound.add((function, direction, parameter, outer))
    assert bound == BINDINGS
    assert len(re.findall(rf"\b{FLOW}::", body)) == len(BINDINGS)


def test_the_network_identity_is_recorded_before_the_first_command_and_exchanges_nothing():
    body = _flow_body()
    assert len(re.findall(r"\brecordNetworkIdentity\b", body)) == 2, \
        "recordNetworkIdentity appears only as its usage and its succession"
    assert not [flow for flow in FLOWS if "recordNetworkIdentity" in " ".join(flow)]
    assert "The network identity is recorded before the network takes the first driving command of each run." \
        in _doc(f"action def {FLOW}")
    assert _doc("item def EENetworkIdentityRecord") == ITEM_DOCS["EENetworkIdentityRecord"]


@pytest.mark.parametrize("definition", sorted(FUNCTION_DOCS))
def test_each_function_states_its_text_of_record(definition):
    doc = _doc(f"action def {definition} :> AllocatableFunction")
    assert doc == FUNCTION_DOCS[definition]
    assert not re.search(r"\bREQ-", doc), "a function doc names no requirement"


def test_the_stop_response_leaves_on_the_one_output_of_the_application():
    """The stop response is a state of applyDrivingCommand, not a second source of commands: the flow has one
    output, which only applyDrivingCommand gives, and no function but it gives an applied command."""
    code = _code()
    flow = _flow_body()
    assert re.findall(r"\bout\s+item\s+(\w+)", _direct(flow)) == ["appliedCommand"]
    sources = re.findall(rf"\baction\s+(\w+)\s*:\s*\w+\s*\{{[^}}]*\bout\s+\w+\s*=\s*{FLOW}::appliedCommand\s*;", flow)
    assert sources == ["applyDrivingCommand"]
    givers = [name for name in FUNCTIONS.values()
              if re.search(r"\bout\s+appliedCommand\b", braced_body(code, f"action def {name} :> AllocatableFunction"))]
    assert givers == ["EEApplyDrivingCommand"]
    assert "gives the vehicle the stop response on the same output" in FUNCTION_DOCS["EEApplyDrivingCommand"]
    assert ("it is a state of that function, not a second source of commands." in _header())


def test_the_states_of_the_actuation_ecu():
    code = _code()
    assert re.findall(r"\bstate\s+def\s+(\w+)", code) == [STATE_DEF]
    machine = braced_body(code, f"state def {STATE_DEF}")
    assert re.findall(r"\bstate\s+(\w+)\s*[;{]", machine) == STATES
    pairs = re.findall(r"\btransition\s+first\s+(\w+)\s+then\s+(\w+)\s*;", machine)
    assert pairs == list(TRANSITIONS), "exactly these three transitions, in this order"
    assert len(re.findall(r"\btransition\b", machine)) == len(TRANSITIONS)
    assert not [pair for pair in pairs if pair[0] == "givingStopResponse"], \
        "the stop response holds until the run ends"
    assert _transitions(braced_body(_raw(), f"state def {STATE_DEF}")) == TRANSITIONS
    assert _doc(f"state def {STATE_DEF}") == STATE_DEF_DOC
    for state in STATES:
        assert _doc(f"state {state}") == STATE_DOCS[state], state


def test_the_state_machine_is_not_parallel_and_owns_no_action():
    """One state at a time, and the states own no behavior: applyDrivingCommand depends on them and is the one source
    of what the vehicle gets. Read in the code, so a doc word cannot trip it; each state owns its doc only, and no
    usage of the state def elsewhere in the package adds behavior to it."""
    code = _code()
    assert re.search(rf"\bstate\s+def\s+{STATE_DEF}\s*\{{", code), "not a parallel state"
    machine = braced_body(code, f"state def {STATE_DEF}")
    assert not re.search(r"\b(?:entry|do|exit|accept|perform|action|calc|parallel)\b", machine), \
        "the states own no action: applyDrivingCommand depends on them"
    for state in STATES:
        assert braced_body(machine, f"state {state}").split() == ["doc"], f"{state} owns its doc only"
    assert not re.search(r"\b(?:entry|do|exit|accept|calc|parallel|exhibit)\b", code), "no state behavior anywhere"
    assert re.findall(r"\bstate\s+(?!def\b)(\w+)", code) == STATES, "no usage of the state def"


def test_no_text_of_the_package_uses_the_word_mode():
    """The increment's texts use "mode" for power modes and for Integration Mode: the conditions are states."""
    assert not MODE_WORD.search(_raw()), MODE_WORD.search(_raw())
    table = braced_body(_code(), f"view {TABLE_VIEW} : TVD::TableView")
    assert re.findall(r"\bview\s+(\w+)\s*:>\s*columnViews", table) == [column for column, _ in TABLE_COLUMNS]
    from scripts.render_grid_csv import GRID_METADATA

    metadata = GRID_METADATA[f"table-{TABLE_VIEW}"]
    for text in (metadata.title, metadata.description, metadata.row_label, metadata.column_label):
        assert not MODE_WORD.search(text or ""), text
    assert not MODE_WORD.search(_guide_section(_guide()))


def test_the_state_dependences_name_the_one_function_that_depends_on_them():
    code = _code()
    rows = re.findall(rf"\bdependency\s+(\w+)\s+from\s+{FLOW}::(\w+)\s+to\s+{STATE_DEF}::(\w+)\s*;", code)
    assert {(function, state) for _, function, state in rows} == STATE_DEPENDENCIES
    for name, function, state in rows:
        assert name == f"ee{function[0].upper()}{function[1:]}DependsOn{state[0].upper()}{state[1:]}State", name
    assert len(re.findall(r"\bdependency\b", code)) == len(STATE_DEPENDENCIES), "no other dependency"
    for function, state in STATE_DEPENDENCIES:
        assert function in _doc(f"state {state}"), (function, state)


def test_each_requirement_is_allocated_to_the_functions_decided():
    rows = _allocation_rows()
    assert {name: (requirement, function) for name, requirement, function in rows} == ALLOCATIONS
    assert len(rows) == ALLOCATION_COUNT
    assert _allocations() == ALLOCATED
    assert sum(len(functions) for functions in _allocations().values()) == ALLOCATION_COUNT


def test_every_functional_requirement_is_allocated_and_every_function_carries_one():
    requirements = _requirements()
    assert len(requirements) == 10
    allocated = _allocations()
    functional = [name for _, name, kind in requirements if kind == "FunctionalRequirementCandidate"]
    assert len(functional) == 5 and all(name in allocated for name in functional)
    assert {name for _, name, _ in requirements} - set(allocated) == set(LEFT_TO_PHASES_7_AND_8)
    assert set(allocated) <= {name for _, name, _ in requirements}
    assert set().union(*allocated.values()) == set(FUNCTIONS), "every function carries a requirement"


def test_req_ee_001_and_req_ee_003_are_left_to_phases_7_and_8():
    """They constrain the structure that realizes the functions; the header states it and the phases that carry
    them, and phase 6 carries them by neither an allocation nor a dependency."""
    for sentence in LEFT_SENTENCES:
        assert sentence in _header(), sentence
    code = _code()
    for name, short in LEFT_TO_PHASES_7_AND_8.items():
        assert name not in _allocations(), short
        assert not re.search(rf"\b(?:allocate|dependency|satisfy|refine)\b[^;]*\b{name}\b", code), short
        assert (short, name) in {(s, n) for s, n, _ in _requirements()}


def test_the_package_asserts_no_satisfaction_and_no_refinement():
    """An allocation assigns responsibility only: phase 6 asserts no satisfaction, so the code has no satisfy and no
    refine, a doc word aside."""
    assert not re.search(r"\b(?:satisfy|refine)\b", _code()), "phase 6 asserts no satisfaction"


@pytest.mark.parametrize("group", list(ALLOCATION_GROUPS))
def test_each_group_of_allocations_states_its_text_of_record(group):
    assert _comment(group) == ALLOCATION_GROUPS[group]
    raw = _raw()
    names = re.findall(r"(?m)^  comment\s+(\w+)|^  allocation\s+(\w+)", raw)
    order = [comment or allocation for comment, allocation in names]
    start = order.index(group)
    following = order[start + 1:]
    end = next((n for n, name in enumerate(following) if name in ALLOCATION_GROUPS), len(following))
    assert following[:end] == GROUPED[group], group
    assert [name for name in order if name in ALLOCATION_GROUPS] == list(ALLOCATION_GROUPS)


def test_the_breakdown_view_shows_the_flow_with_its_five_functions():
    from scripts.generate_view_index import KNOWN_PRESENTATION_NOTES

    assert KNOWN_PRESENTATION_NOTES[TREE_VIEW] == TREE_VIEW_NOTE


def test_the_matrix_maps_every_requirement_to_its_functions():
    view = braced_body(_code(), f"view {MATRIX_VIEW} : MVD::MatrixView")
    viewpoint = braced_body(view, "viewpoint")
    assert re.search(r"viewpoint\s+\w+\s*:\s*SystemRequirementTraceabilityViewpoint\s*\{", view)
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == [CONCERN]
    rows = braced_body(view, "view :>> rowView")
    columns = braced_body(view, "view :>> columnView")
    cells = braced_body(view, "view :>> cellView")
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", rows) == [name for _, name, _ in _requirements()], \
        "all ten requirements, REQ-EE-001 and REQ-EE-003 empty rows"
    assert re.findall(r"\bexpose\s+([\w:]+)\s*;", columns) == [f"{FLOW_USAGE}::{f}" for f in FUNCTIONS]
    for axis in (rows, columns):
        assert "attribute :>> includeReferenceElements = true;" in axis
        assert "attribute :>> representation = Rep::name;" in axis
    assert re.findall(r"\bexpose\s+([\w:*]+)\s*;", cells) == [f"{PACKAGE}::*"]
    assert "MatrixTraceabilityDirection::row2col" in cells


def test_the_matrix_filters_nothing():
    """A filter in any axis of the matrix would empty its rows, columns or cells."""
    view = braced_body(_code(), f"view {MATRIX_VIEW} : MVD::MatrixView")
    assert not re.search(r"\bfilter\b", view)


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
        assert re.findall(r"\brender\s+\w+\s*;", view) == [render]
    else:
        assert "render as" not in view, "the view type selects the kind"
    if view_name in (PROCESS_VIEW, INTERFACE_VIEW):
        assert "attribute showAnnotationRows = false;" in view
    if view_name == PROCESS_VIEW:
        assert "attribute maxCompartmentEntries = 0;" in view


def test_the_package_publishes_exactly_one_view_per_question():
    declared = re.findall(r"^\s*view\s+(\w+)\s*(?::\s*(?!>)[\w:]+)?\s*\{", _code(), re.M)
    assert sorted(declared) == sorted(PUBLISHED_VIEWS)
    assert len(declared) == 5


def test_the_process_view_notes_where_the_sequence_from_a_fault_is():
    """The process view frames the fault response of phase 1, but its convention form (doc rows hidden) prints no
    doc: the view index says where the sequence and its times are."""
    view = braced_body(_code(), f"view {PROCESS_VIEW} : ActionFlowView")
    assert "attribute showAnnotationRows = false;" in view, "the convention form"
    from scripts.generate_view_index import KNOWN_PRESENTATION_NOTES

    assert KNOWN_PRESENTATION_NOTES[PROCESS_VIEW] == PROCESS_VIEW_NOTE
    framing = _flat(FRAMING.read_text(encoding="utf-8"))
    assert framing.count("Answered by the system process of phase 6.") == 1
    assert f"private import DE4SDV_EEArchitectureFraming::{PHASE_1_PROCESS_CONCERN};" in _code()


def test_the_table_states_its_rows_and_columns():
    view = braced_body(_code(), f"view {TABLE_VIEW} : TVD::TableView")
    assert "filter @ SysML::StateUsage;" in view
    for label, feature in TABLE_COLUMNS:
        column = braced_body(view, f"view {label} :> columnViews")
        assert f"attribute :>> featureToRender = {feature}" in column, label


def test_the_table_has_exactly_the_state_filter():
    """A second filter would empty the table."""
    view = braced_body(_code(), f"view {TABLE_VIEW} : TVD::TableView")
    assert re.findall(r"\bfilter\b[^;]*;", view) == ["filter @ SysML::StateUsage;"]


def test_the_process_view_sets_exactly_its_two_attributes():
    """The doc rows hidden and the compartments closed, and nothing else: a depth would draw the functions twice."""
    view = braced_body(_code(), f"view {PROCESS_VIEW} : ActionFlowView")
    assert re.findall(r"\battribute\s+(?::>>\s*)?(\w+)\s*=", _direct(view)) == [
        "showAnnotationRows", "maxCompartmentEntries"]
    assert len(re.findall(r"\battribute\b", view)) == 2


#: Every setting (`name =`, with or without the attribute keyword, at any depth) and every filter of each view, in
#: order: a depth, a filter or another setting changes a render.
VIEW_SETTINGS = {
    TREE_VIEW: ([], []),
    MATRIX_VIEW: (["includeReferenceElements", "representation", "includeReferenceElements", "representation",
                   "direction"], []),
    PROCESS_VIEW: (["showAnnotationRows", "maxCompartmentEntries"], []),
    TABLE_VIEW: (["maxRowHeight", "featureToRender", "featureToRender", "columnWidth"],
                 ["filter @ SysML::StateUsage;"]),
    INTERFACE_VIEW: (["showAnnotationRows"], []),
}


@pytest.mark.parametrize("view_name", sorted(VIEW_SETTINGS), ids=sorted(VIEW_SETTINGS))
def test_each_view_sets_exactly_its_settings_and_filters(view_name):
    view_type = "MVD::MatrixView" if view_name == MATRIX_VIEW else VIEWS[view_name][0]  # VIEWS lacks the matrix
    view = braced_body(_code(), f"view {view_name}" + (f" : {view_type}" if view_type else ""))
    settings, filters = VIEW_SETTINGS[view_name]
    assert re.findall(r"(\w+)\s*=", view) == settings, view_name
    assert re.findall(r"\bfilter\b[^;]*;", view) == filters, view_name


def test_the_grids_have_a_title_and_their_axes_named():
    from scripts.render_grid_csv import GRID_METADATA

    for key, expected in GRIDS.items():
        grid = GRID_METADATA[key]
        assert (grid.title, grid.description, grid.row_label, grid.column_label) == expected, key


def test_the_context_elements_perform_their_functions_outside_the_network_scope():
    code = _code()
    assert re.search(rf"\baction\s+def\s+{CONTEXT_FUNCTION_ROOT}\s*\{{", code), "the context functions need a root"
    assert not re.search(rf"\baction\s+def\s+{CONTEXT_FUNCTION_ROOT}\s*:>", code), "the root specializes nothing"
    operation = braced_body(strip_comments(OPERATIONAL_CONTEXT.read_text(encoding="utf-8")),
                            "action def VehicleNetworkCommandOperation")
    for name, (parameters, phase_2_action) in CONTEXT_FUNCTIONS.items():
        body = _direct(braced_body(code, f"action def {name} :> {CONTEXT_FUNCTION_ROOT}"))
        assert re.findall(r"\b(in|out)\s+(\w+)\s*:\s*(\w+)\s*;", body) == parameters, name
        phase_2 = braced_body(operation, f"action {phase_2_action}")
        assert re.findall(r"\b(in|out)\s+(\w+)\s*:\s*(\w+)\s*;", phase_2) == parameters, (name, phase_2_action)
        assert _doc(f"action def {name} :> {CONTEXT_FUNCTION_ROOT}") == CONTEXT_DOCS[name], name
    assert _doc(f"action def {CONTEXT_FUNCTION_ROOT}") == CONTEXT_ROOT_DOC


def test_the_process_binds_its_participants_to_the_context_parts_of_phase_2():
    """SAF System Process: one activity whose participants are the context parts of phase 2 and the system of
    interest, bound by reference, so the increment keeps one context."""
    code = _code()
    body = _process_body()
    direct = _direct(body)
    assert re.findall(r"\bref\s+part\s+(\w+)\s*:\s*(\w+)\s*=\s*([\w:]+)\s*\{", direct) == [
        (name, typed, bound) for name, (typed, bound, _) in PARTICIPANTS.items()]
    assert not re.search(r"(?<!ref )\bpart\s+\w+", direct), "the process declares no part of its own"
    assert f"private import DE4SDV_EEArchitectureOperationalContext::{CONTEXT_USAGE};" in code
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
        if name == "vehicleNetwork":
            assert re.findall(r"\bperform\s+(\w+)\s*;", part) == [FLOW_USAGE], \
                "the network's step is the flow usage the boundary performs, not a second usage of the flow"
        else:
            assert not re.search(r"\bperform\s+\w+\s*;", part), name
        assert _doc(f"ref part {name} : {typed} = {bound}") == PARTICIPANT_DOCS[name], name
    performed = {definition for _, (_, _, functions) in PARTICIPANTS.items() for definition in functions.values()}
    assert performed == set(CONTEXT_FUNCTIONS), "every context function is performed by one participant"
    assert re.findall(r"(?m)^\s*flow\s+from\s+([\w.]+)\s+to\s+([\w.]+)\s*;\s*$", body) == PROCESS_FLOWS
    assert len(re.findall(r"\bflow\b", body)) == len(PROCESS_FLOWS)
    assert not [flow for flow in PROCESS_FLOWS if flow[0].startswith("vehicle.")], "nothing flows back"
    assert re.search(rf"\baction\s+{PROCESS_USAGE}\s*:\s*{PROCESS}\s*;", code)
    assert "allocate" not in body, "the process assigns no responsibility"


def test_the_process_states_the_sequence_from_a_fault_to_the_stop_response():
    assert _process_paragraphs() == PROCESS_PARAGRAPHS
    assert "Answered by the system process of phase 6." in _flat(
        braced_body(FRAMING.read_text(encoding="utf-8"), f"concern {PHASE_1_PROCESS_CONCERN} : SystemProcessConcern"))


def test_the_input_reuses_the_item_of_the_driver_assistance_increment_and_adds_no_attribute():
    code = _code()
    item, base, attributes = DRIVING_ITEM
    assert code.count("private import DE4SDV_DriverAssistanceFunctionalArchitecture::") == 1
    assert f"private import DE4SDV_DriverAssistanceFunctionalArchitecture::{item};" in code
    assert not re.search(rf"\bdef\s+{item}\b", code), f"{item} is defined once, in the driver-assistance increment"
    driving = strip_comments(DRIVING_FUNCTIONS.read_text(encoding="utf-8"))
    assert _attributes(braced_body(driving, f"item def {item} :> {base}")) == attributes
    body = braced_body(code, "item def EEDrivingCommandInput :> DrivingCommandOutput")
    assert not re.search(r"\b(?:attribute|item|part|ref)\b", body), "no attribute added"


def test_the_output_carries_the_steering_angle_and_the_acceleration_only():
    code = _code()
    assert "private import ISQ::*;" not in code
    for item, attributes in BOUNDARY_ITEM_ATTRIBUTES.items():
        body = braced_body(code, f"item def {item} :> {BOUNDARY_ITEM_SPECIALIZATIONS[item]}")
        assert _attributes(body) == attributes, item
        assert not re.search(r"\b(?:item|part|ref)\b", _direct(body)), item
        assert _doc(f"item def {item} :> {BOUNDARY_ITEM_SPECIALIZATIONS[item]}") == BOUNDARY_ITEM_DOCS[item], item
    assert "It carries no detection part." in BOUNDARY_ITEM_DOCS["EEActuationOutput"]


def test_the_network_boundary_carries_typed_functional_ports():
    """SAF System Interface Definition: the conceptual interfaces as port definitions with one directed item each,
    typed by a functional item definition of this package."""
    code = _code()
    assert re.search(rf"\bpart\s+def\s+{BOUNDARY}\s*:>\s*EEVehicleNetworkSystem\s*\{{", code)
    specializations = dict(re.findall(r"\bitem\s+def\s+(\w+)\s*:>\s*(\w+)\s*\{", code))
    assert specializations == BOUNDARY_ITEM_SPECIALIZATIONS
    for port, item in BOUNDARY_PORTS.items():
        body = braced_body(code, f"port def {port}")
        assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*:\s*(\w+)\s*;", body) == [item], port
        assert len(re.findall(r"\b(?:in|out|inout)\b", body)) == 1, f"{port}: one directed feature"
        assert _doc(f"port def {port}") == PORT_DOCS[port], port
    assert re.findall(r"\bport\s+def\s+(\w+)", code) == list(BOUNDARY_PORTS)
    boundary = braced_body(code, f"part def {BOUNDARY}")
    assert re.findall(r"\bport\s+(\w+)\s*:\s*(\w+)\s*;", _direct(boundary)) == list(BOUNDARY_PORT_USAGES.items())
    perform = braced_body(boundary, f"perform {FLOW_USAGE} : {FLOW}")
    assert re.findall(r"\b(in|out)\s+item\s+(\w+)\s*=\s*([\w.]+)\s*;", perform) == BOUNDARY_BINDINGS
    assert not re.search(rf"\bpart\s+\w+\s*:\s*{BOUNDARY}\b", code), "a usage of it would be a second system"
    assert _doc(f"part def {BOUNDARY}") == BOUNDARY_DOC


def test_the_package_imports_one_by_one():
    imports = re.findall(r"(?m)^  private import ([\w:*]+);", _code())
    assert imports == [
        "DE4SDV_Stakeholders::*", "DE4SDV_TraceVocabulary::AllocatableFunction",
        "DE4SDV_EEArchitectureFraming::EEVehicleNetworkSystem",
        f"DE4SDV_EEArchitectureFraming::{PHASE_1_PROCESS_CONCERN}",
        "DE4SDV_EEArchitectureOperationalContext::DrivingCommandSource",
        f"DE4SDV_EEArchitectureOperationalContext::{CONTEXT_USAGE}",
        "DE4SDV_DriverAssistanceOperationalContext::DrivingCommand",
        "DE4SDV_DriverAssistanceOperationalContext::SCORECommandAndWarningPath",
        "DE4SDV_OperationalContext::SubjectVehicle",
        "DE4SDV_DriverAssistanceFunctionalArchitecture::DrivingCommandOutput",
        "DE4SDV_EEArchitectureNeedsRequirements::*", "SAF_Viewpoints::*", "StandardViewDefinitions::*",
        "SysideViews::**", "Views::*"], "no feature package by wildcard but the needs and requirements"
    assert len(re.findall(r"\bimport\b", _code())) == len(imports)


@pytest.mark.parametrize("concern_name", sorted(CATALOGUE_CONCERNS), ids=sorted(CATALOGUE_CONCERNS))
def test_each_phase_6_concern_is_typed_by_the_catalogue_and_held_by_the_party_it_serves(concern_name):
    catalogue, stakeholders = CATALOGUE_CONCERNS[concern_name]
    concern = braced_body(_code(), f"concern {concern_name} : {catalogue}")
    members = re.findall(r"\b(subject|stakeholder)\b", concern)
    assert members and members[0] == "subject"
    assert set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", concern)) == stakeholders
    assert len(re.findall(r"\bstakeholder\b", concern)) == len(stakeholders)
    assert _doc(f"concern {concern_name} : {catalogue}") == CONCERN_DOCS[concern_name]
    assert set(re.findall(r"\bconcern\s+(\w+)\s*:", _code())) == set(CATALOGUE_CONCERNS)


def test_the_package_types_no_vehicle_signal_specification():
    """No vehicle signal specification in phase 6: the typing starts at phase 8."""
    raw = _raw()
    assert "VSS" not in raw, "no vehicle signal type, import, path or word"
    assert "COVESA" not in raw and "DE4SDV_VSS_Extensions" not in raw
    assert "No vehicle signal specification is imported or used anywhere in this package" in _header()


def test_no_doc_of_the_package_names_an_element_of_a_route_or_a_technology():
    """The functions do not depend on the route: which elements carry a command is for phases 7 and 8."""
    docs = _docs()
    assert len(docs) >= 35, "the population of the check must not be vacuous"
    for text in docs:
        assert not ROUTE_AND_TECHNOLOGY.search(text), (ROUTE_AND_TECHNOLOGY.search(text), text[:80])
        assert not NETWORK_NAMES.search(text), (NETWORK_NAMES.search(text), text[:80])
    assert "The functions do not depend on the route: a run takes one route" in _header()


def test_the_header_states_its_text_of_record():
    assert _header_paragraphs() == HEADER_PARAGRAPHS


def test_the_package_is_exactly_its_skeleton():
    """The whole code of the package, pinned line by line: every declaration at its own depth, whole, in order.
    Because the skeleton pins the code whole, a change to any declaration of the package fails it: a member added,
    removed, moved or reordered at any depth, a changed keyword, name, type, value or binding, a changed section
    comment, a brace that closes no body or a body never closed. Its limit: the header, the docs and the named comments
    are pinned by the texts of record, which read the one copy of each declaration in the file (a note that copies a
    declaration fails them), and the `//` notes of the transitions by TRANSITIONS, not by the skeleton."""
    expected = SKELETON.splitlines()
    actual = _skeleton()
    assert len(expected) >= 200, "the skeleton must not be vacuous"
    assert not re.search(r"[^\x00-\x7f]", _code()), \
        "the code is ASCII: only docs, comments and notes hold other characters"
    for number, (line, pinned) in enumerate(zip_longest(actual, expected), 1):
        assert line == pinned, f"skeleton line {number}: {line!r}, pinned {pinned!r}"


def test_the_package_declares_no_name_that_another_model_package_declares():
    # Two packages may declare the same name, but a lookup by name then finds two elements, and a check that
    # reads a folder by name sees one increment's element as the other's. Both ways: no top-level or decided
    # nested name of this package is declared elsewhere, and no top-level name of another file is declared here.
    kinds = (r"(?:part def|item def|action def|state def|port def|part|item|action|state|port|concern|view|"
             r"dependency|allocation|comment)")
    raw_code = re.sub(r"/\*.*?\*/|//[^\n]*", "", _raw().split(f"package {PACKAGE}", 1)[1], flags=re.S)
    declared = set(re.findall(rf"(?m)^  {kinds}\s+(\w+)", _raw()))
    assert len(declared) >= 45, "the population of the check must not be vacuous"
    assert all(name.startswith(("ee", "EE")) for name in declared), sorted(
        name for name in declared if not name.startswith(("ee", "EE")))
    anywhere = re.compile(rf"\b(?:{kinds}|viewpoint)\s+(?:<'[^']*'>\s*)?(\w+)")
    here = set(anywhere.findall(raw_code))
    assert NESTED_NAMES <= here
    taken: dict[str, list[str]] = {}
    for root in MODEL_ROOTS:
        for path in sorted(root.rglob("*.sysml")):
            if path == MODEL:
                continue
            code = strip_comments(path.read_text(encoding="utf-8"))
            for name in anywhere.findall(code):
                if name in declared | NESTED_NAMES:
                    taken.setdefault(name, []).append(path.name)
            for name in re.findall(rf"(?m)^  {kinds}\s+(\w+)", code):
                if name in here:
                    taken.setdefault(name, []).append(f"{path.name} (top level)")
    assert not taken, f"declared in another package too: {taken}"


def test_the_guide_has_a_phase_6_section_and_names_phase_7_next():
    guide = _guide()
    assert guide.count(GUIDE_HEADING + "\n") == 1
    assert guide.index("## Requirements (Phase 5)") < guide.index(GUIDE_HEADING) \
        < guide.index("## What the framing already records as open")
    raw_section = _guide_section(guide)
    blocks = [" ".join(block.split()) for block in re.split(r"\n\s*\n", raw_section.strip())]
    assert blocks == GUIDE_PARAGRAPHS, "every paragraph of the section, whole and in order"
    assert all(len(line) <= 79 for line in raw_section.splitlines()), "the guide wraps at 79"
    assert not PAST_BEHAVIOR.search(raw_section) and not CLAUSE_NUMBER.search(raw_section)
    flat = " ".join(guide.split())
    assert flat.count(GUIDE_STATUS) == 1 and GUIDE_STATUS_PHASE_5 not in flat
    nxt = guide.split("## Next obligation and execution limits\n", 1)[1].split("\n## ", 1)[0]
    assert [" ".join(block.split()) for block in re.split(r"\n\s*\n", nxt.strip())][0] == GUIDE_NEXT_PARAGRAPH
    assert flat.count(GUIDE_NEXT) == 1
    assert "The next model obligation is **Phase 6**" not in flat
    check = " ".join(guide.split("## Check the framing change", 1)[1].split())
    assert "tests/test_ee_architecture_functional_architecture.py" in check
