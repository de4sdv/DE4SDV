"""Content pins for the E/E architecture requirements (INC-EE-001, phase 5), not semantic validation.

Phase 5 derives the requirements of the vehicle network, the system of interest the charter declares, from the
three needs of phase 4 and from REQ-DRIVING-028, REQ-DRIVING-039 and REQ-MW-006. The SpecifyRequirements rules of
the increment workflow are checked by Method Check; these pins hold what review settled on top of them:

- the requirement set itself, each with its need, its kind and its verification method, within the charter's
  scope cap of at most ten requirements;
- each statement, source, rationale and success criteria whole, as review settled them;
- requirement-writing rules: one obligation per statement (one `shall`, at most 60 words), the positive form, the
  vehicle network as the subject of each, and the terms the statements use defined once in the package, exactly
  these terms;
- each time limit in simulation time, on the clock of the virtual vehicle, with no timing claim for a vehicle
  network;
- the two comments that record what phase 5 fixes of gapEEActuationEnd and what the criteria ask of System 2;
- the phase 4 comment on the input contract replaced by the requirements and their rationales;
- one requirement definition table, the one view the method names for phase 5, framing the requirement trace
  concern;
- the guide's phase 5 section, its bullets, its decisions and the next obligation, phase 6;
- no claim the charter excludes, and no feature link before phase 9.

The tests read the model text; they do not parse SysML. They state their own constants.
"""

from __future__ import annotations

import re
from pathlib import Path

from sysml_shapes import braced_body, short_name_declarations, strip_comments

ROOT = Path(__file__).resolve().parents[1]
NOTATION = ROOT / "textual-notation-of-model"
EE = NOTATION / "packages/features/ee"
MODEL = EE / "ee_architecture_needs_requirements.sysml"
GUIDE = ROOT / "docs/guides/ee-architecture-increment.md"
MODEL_ROOTS = (NOTATION, ROOT / "model-based-product-line-engineering")
SUBJECT_LINE = "subject vehicleNetwork :> DE4SDV_EEArchitectureFraming::eeVehicleNetworkSystem;"

#: the needs of phase 4 -> their short names
NEED_SHORT = {
    "needDrivingCommandReachesActuationOnEachRoute": "NEED-EE-001",
    "needNoInvalidCommandApplied": "NEED-EE-002",
    "needRunsIdentifyRouteAndNetwork": "NEED-EE-003",
}

F = "FunctionalRequirementCandidate"
R = "RequirementCandidate"

#: The charter's scope: at most ten requirements.
SCOPE_CAP = 10

#: requirement -> (short name, the need it derives from, its definition, its verification method)
REQUIREMENTS = {
    "reqBothRoutesInOneTopology": ("REQ-EE-001", "needDrivingCommandReachesActuationOnEachRoute", R, "inspect"),
    "reqCommandsOnlyFromSCOREPath": ("REQ-EE-002", "needDrivingCommandReachesActuationOnEachRoute", R, "test"),
    "reqCommandsOnlyOnTheirRoute": ("REQ-EE-003", "needDrivingCommandReachesActuationOnEachRoute", R, "test"),
    "reqDeliverCommandStreamUnchanged": ("REQ-EE-004", "needDrivingCommandReachesActuationOnEachRoute", F, "test"),
    "reqCarryEachCommandWithin50Ms": ("REQ-EE-005", "needDrivingCommandReachesActuationOnEachRoute", R, "test"),
    "reqApplyEachValidCommand": ("REQ-EE-006", "needDrivingCommandReachesActuationOnEachRoute", F, "test"),
    "reqPassDetectionPartsOnAsTaken": ("REQ-EE-007", "needNoInvalidCommandApplied", R, "analyze"),
    "reqGiveOnlyLastValidCommand": ("REQ-EE-008", "needNoInvalidCommandApplied", F, "test"),
    "reqStopResponseAfter200Ms": ("REQ-EE-009", "needNoInvalidCommandApplied", F, "test"),
    "reqRecordNetworkIdentity": ("REQ-EE-010", "needRunsIdentifyRouteAndNetwork", F, "test"),
}
#: requirement -> the kind word its rationale opens with (functional: none)
KIND_WORDS = {
    "reqBothRoutesInOneTopology": "design constraint",
    "reqCommandsOnlyFromSCOREPath": "design constraint",
    "reqCommandsOnlyOnTheirRoute": "design constraint",
    "reqDeliverCommandStreamUnchanged": "functional",
    "reqCarryEachCommandWithin50Ms": "performance",
    "reqApplyEachValidCommand": "functional",
    "reqPassDetectionPartsOnAsTaken": "design constraint",
    "reqGiveOnlyLastValidCommand": "functional",
    "reqStopResponseAfter200Ms": "functional",
    "reqRecordNetworkIdentity": "functional",
}
#: requirement -> its statement, pinned whole
STATEMENTS = {
    "reqBothRoutesInOneTopology": (
        'The vehicle network shall hold the route through a zone controller and the direct route in '
        'one topology.'),
    "reqCommandsOnlyFromSCOREPath": 'The vehicle network shall take driving commands only from the Eclipse S-CORE path.',
    "reqCommandsOnlyOnTheirRoute": (
        'The vehicle network shall carry the driving commands of each run only through the elements of '
        'the route of the run.'),
    "reqDeliverCommandStreamUnchanged": (
        'In each run, the vehicle network shall deliver to the actuation ECU each driving command that '
        'no fault affects, once, in its order and with each part unchanged.'),
    "reqCarryEachCommandWithin50Ms": (
        'In each run without a fault, the vehicle network shall carry each driving command from the '
        'boundary interface to the actuation ECU within 50 ms of simulation time after taking it.'),
    "reqApplyEachValidCommand": (
        'Until the stop response starts, the vehicle network shall apply each valid driving command at '
        'the actuation ECU.'),
    "reqPassDetectionPartsOnAsTaken": (
        'The vehicle network shall pass the detection parts of each driving command on to the '
        'actuation ECU at each element as the element received them, without computing any of them '
        'anew.'),
    "reqGiveOnlyLastValidCommand": (
        'Until the stop response starts, the vehicle network shall give the vehicle at the actuation '
        'ECU only the steering angle and the acceleration of the last valid driving command that it '
        'applied.'),
    "reqStopResponseAfter200Ms": (
        'The vehicle network shall start the stop response at the actuation ECU once more than 200 ms '
        'of simulation time pass with no valid driving command reaching the actuation ECU.'),
    "reqRecordNetworkIdentity": (
        'The vehicle network shall record its network identity before it takes the first driving '
        'command of each run.'),
}
#: requirement -> its source, pinned whole
SOURCES = {
    "reqBothRoutesInOneTopology": (
        'NEED-EE-001; eeTopologyStructureConcern; eeCommandRouteExchangeConcern; scope item '
        'eeTopologyInScope; gap gapEEZoneRouteInVehicles'),
    "reqCommandsOnlyFromSCOREPath": 'NEED-EE-001; assumption asmEEScoreCommandSource; eeCommandRouteExchangeConcern',
    "reqCommandsOnlyOnTheirRoute": (
        'NEED-EE-001; eeCommandRouteExchangeConcern; scope item eeCommandRouteInScope; scenarios '
        'SC-EE-001 to SC-EE-004'),
    "reqDeliverCommandStreamUnchanged": (
        'NEED-EE-001; eeVehicleCommandConcern; assumption asmEECommandFromDrivingBaseline; scenarios '
        'SC-EE-001 to SC-EE-004'),
    "reqCarryEachCommandWithin50Ms": (
        'NEED-EE-001; eeVehicleCommandConcern; assumption asmEECommandFromDrivingBaseline; scenarios '
        'SC-EE-001 and SC-EE-002'),
    "reqApplyEachValidCommand": 'NEED-EE-001; eeVehicleCommandConcern; scenarios SC-EE-001 to SC-EE-004',
    "reqPassDetectionPartsOnAsTaken": 'NEED-EE-002; eeCommandItemConcern; REQ-DRIVING-039; gap gapEEActuationEnd',
    "reqGiveOnlyLastValidCommand": (
        'NEED-EE-002; REQ-MW-006; REQ-DRIVING-039; eeNetworkFaultResponseConcern; gap '
        'gapEEActuationEnd; scenario SC-EE-003'),
    "reqStopResponseAfter200Ms": (
        'NEED-EE-002; REQ-DRIVING-028; eeNetworkFaultResponseConcern; gap gapEEActuationEnd; scenarios '
        'SC-EE-003 and SC-EE-004'),
    "reqRecordNetworkIdentity": (
        'NEED-EE-003; eeRouteVerdictConcern; scope item eeVerdictEvidenceInScope; scenarios SC-EE-001 '
        'to SC-EE-004'),
}
#: requirement -> its rationale, pinned whole
RATIONALES = {
    "reqBothRoutesInOneTopology": (
        'This is a design constraint on the structure of the vehicle network. The lifecycle decision '
        'is whether the product line admits one zonal vehicle network as its reference vehicle '
        'network, from a verdict for each requirement on each route, so both routes run in the same '
        'topology: verdicts from two topologies would judge two networks. The increment takes neither '
        'route as given (gapEEZoneRouteInVehicles). Phases 6 to 8 decide the realization of each '
        'element and the medium of the direct link, and how the topology relates to the platform stack '
        'and to the vehicle network boundary of the AAOS SDV middleware stays open '
        '(gapEEStackAndNetworkBoundary).'),
    "reqCommandsOnlyFromSCOREPath": (
        'This is a design constraint on the input of the vehicle network. The driving command enters '
        'the vehicle network from the Eclipse S-CORE path of the existing increments on the central '
        'computer (asmEEScoreCommandSource), the only path over which REQ-DRIVING-038 lets the '
        'driver-assistance system give it, and a readiness probe is to test this first. A command that '
        'reaches the actuation ECU by another way, such as one given straight to the CAN bus of its '
        'zone, would let the vehicle act while the routes carry nothing, so the criteria hold that '
        'each command that reaches the actuation ECU was taken at the boundary interface. The '
        'statement names the Eclipse S-CORE path, so phase 9 links it to the feature eclipseSCORE.'),
    "reqCommandsOnlyOnTheirRoute": (
        'This is a design constraint on the way of the command. A verdict holds for the route that '
        'ran: a command of a run on the direct route that also passes a zone controller, or one of a '
        'run through a zone controller that also takes the direct link, would give that verdict to a '
        'route that did not carry the command alone. Which elements realize each route is decided in '
        'phases 6 to 8, with the medium of the direct link.'),
    "reqDeliverCommandStreamUnchanged": (
        'The vehicle can act on a driving command only if the command reaches the actuation ECU as the '
        'vehicle network took it. The actuation ECU takes a command for valid only when its check '
        'value holds and its sequence count is one more than the reference count, so a command lost, '
        'repeated, put out of order or changed on its way is rejected, and a lost or changed one costs '
        'the command after it as well. The form of the command is the one that the driver-assistance '
        'increment fixes at its baseline (asmEECommandFromDrivingBaseline). Whether it fits a CAN '
        'frame is open (gapEEActuationEnd); however the elements pack it, each part arrives as it was '
        'taken. In a run with a fault, of SC-EE-003 or SC-EE-004, it holds for each command that no '
        'fault affects, so the vehicle network keeps carrying the stream around the fault; REQ-EE-008 '
        'and REQ-EE-009 state what the actuation ECU does with what reaches it.'),
    "reqCarryEachCommandWithin50Ms": (
        'This is a performance requirement on the carriage of the command. The actuation ECU takes a '
        'command for valid only when its issue time is no more than 100 ms of simulation time older '
        'than its arrival, the delay limit of the actuation adapter of the driver-assistance '
        'increment. The vehicle network gets half of that limit, from the boundary interface to the '
        'actuation ECU; the other half is the share of the path that carries the command to the '
        'boundary interface, which a judged run keeps. At its baseline the source gives at most one '
        'driving command each 100 ms of simulation time: one image of the front camera each 100 ms, '
        'one plan per frame with a result and one command per plan. A command carried within 50 ms '
        'reaches the actuation ECU before the next one is given, so the vehicle network carries the '
        'commands at the cadence at which they come. A run with a fault, of SC-EE-003 or SC-EE-004, is '
        'outside this requirement. The limit counts on the clock of the virtual vehicle and makes no '
        'timing claim for a vehicle network (asmEESoftwareTestbedStandsIn).'),
    "reqApplyEachValidCommand": (
        'The vehicle acts on a driving command only when the actuation ECU applies it, at the '
        'simulation time at which it arrives. After a repetition the actuation ECU applies the next '
        'valid driving command; a loss, a corruption, the delay of the run set or a link that goes '
        'down leaves it more than 200 ms without one, so the stop response starts (REQ-EE-009) and no '
        'later command is applied. A valid command that arrives more than 200 ms after the last one '
        'comes when the stop response is due, so the criteria leave it out even while the start of the '
        'response is within its tolerance. The stop response holds until the run ends, as the '
        'standstill of REQ-DRIVING-022 does.'),
    "reqPassDetectionPartsOnAsTaken": (
        'This is a design constraint on the exchange items of the vehicle network. REQ-DRIVING-039 '
        'makes the driving command detectable by its form: its issue time shows a delay, its sequence '
        'count a loss or a repetition, and its check value a corruption. That detection holds from the '
        'boundary interface to the actuation ECU only if no element computes a detection part anew: a '
        'zone controller that repacks the command from Ethernet to CAN with a new check value, issue '
        'time or sequence count would hide from the actuation ECU a fault that came before it. A '
        'record shows a detection part that changes at an element in a run with a fault, but no test '
        'can tell a new check value over unchanged parts from the one taken, so the requirement is '
        'verified by analysis of the realization and of the records. How a zone controller repacks the '
        'command, and whether the command fits a CAN frame, are decided in phases 6 to 8 '
        '(gapEEActuationEnd). The analysis rests on the realization that phase 8 records and makes no '
        'freedom-from-interference claim.'),
    "reqGiveOnlyLastValidCommand": (
        'The driver-assistance increment places at its actuation end the share of REQ-MW-006 that is '
        'not applying a command that the actuation rejects, and this increment puts the actuation in '
        'the actuation ECU, so the vehicle network holds that share: a command that a fault has made '
        'invalid on its way no longer stands for what its source gave. A fault shows at the actuation '
        'ECU in the sequence count for a loss or a repetition, in the check value for a corruption, '
        'and in the issue time against the simulation time at its arrival for a delay, by the rules of '
        'the actuation adapter of the driver-assistance increment (the adapter counting decision of '
        '2026-11-18), with the arrival time set here in place of the newest world time of that '
        'adapter. The arrival time counts on the clock of the virtual vehicle, which the testbed gives '
        'every element, so judging the age of a command needs no newest world time at the actuation '
        'ECU, whose inputs stay open (gapEEActuationEnd). Nothing is applied in place of an invalid '
        'command, so the vehicle keeps the last valid one; an invalid command, a neutral control in '
        'place of one, or a value that no command carried each breaks this requirement. A repetition '
        'costs that one command; the delay of the run set costs the delayed command and those that it '
        'holds behind it, and the stop response follows (REQ-EE-009); a loss or a corruption costs the '
        'lost or corrupted command and the next one, which reveals the gap. A corruption that the '
        'check value misses is judged by its sequence count and its issue time alone and can make the '
        'actuation ECU reject later valid commands as repetitions: the bound of the check value (the '
        'check-value bound decision of 2026-11-21 of that increment). Which element detects and '
        'rejects is decided in phases 6 to 8 (gapEEActuationEnd). The requirement carries no safety '
        'claim and no claim of freedom from interference.'),
    "reqStopResponseAfter200Ms": (
        'This is the share of the vehicle network in the stop response that REQ-DRIVING-028 of '
        'INC-DRIVING-001 asks and SC-EE-004 takes for a link that goes down. The adapter of the '
        'driver-assistance increment has no stop response, and the actuation ECU is the last element '
        'that a command reaches, so it gives the response itself because it can no longer be told to. '
        'The 200 ms of simulation time and the 300 ms of the criteria are those of REQ-DRIVING-028, '
        'whose rationale counts a command every 100 ms, so that two missed commands mean that the path '
        'has stopped; the source of this increment gives at most one each 100 ms. Set here: a command '
        'that reaches the actuation ECU exactly 200 ms after the last valid one still counts, and the '
        'stop response starts only after that. Set here too: with the rules of the actuation adapter '
        'of the driver-assistance increment kept, one lost or corrupted command costs two, so it '
        'leaves the actuation ECU 300 ms without a valid command and starts the stop response, '
        'although REQ-DRIVING-028 reads two missed commands as a stopped path. Set here too: a run '
        'ends 100 ms of simulation time after the path gives its last driving command, more than the '
        '50 ms share of the vehicle network, so that the last command can reach the actuation ECU '
        'within the run, and less than the 200 ms after which the stop response starts, so that a run '
        'without a fault ends without it. A repetition costs only its copy. A delay that only just '
        'makes a command late would leave exactly 200 ms without a valid one, where the outcome would '
        'depend on the clock of the testbed, so the run set delays the command by 300 ms; with the '
        'commands that it holds behind it, that leaves more than 200 ms without a valid one on every '
        'clock, and the stop response follows. The stop response gives the deceleration of '
        'REQ-DRIVING-020 with the steering of REQ-DRIVING-021 until the run ends, which holds the '
        'vehicle at standstill as REQ-DRIVING-022 does, so that it needs no vehicle speed at the '
        'actuation ECU, whose inputs stay open (gapEEActuationEnd). With no valid command applied, '
        'there is no steering angle to hold, so the stop response gives 0° of steering. The response '
        'is shown on the virtual vehicle and carries no safety claim; its time limit counts on the '
        'clock of the virtual vehicle and makes no timing claim for a vehicle network.'),
    "reqRecordNetworkIdentity": (
        'A verdict holds only for the route, the topology and the revision of the vehicle network that '
        'ran, and another engineer can rerun a run only from what it names. The commit names the '
        'revision, and the recorded difference tells a build with a change that the commit lacks apart '
        'from it, as the candidate identity of REQ-DRIVING-044 does; the SHA-256 of each file of the '
        'configuration and the settings read from outside a file pin what the vehicle network read, '
        'because a run can read what the commit does not fix, and the files that set the topology pin '
        'it. The recorded command stream, its binding to the revision that made it and the testbed '
        'belong to System 2 and are bound there (gapEERecordedCommandStream, '
        'asmEESoftwareTestbedStandsIn), so the record covers only what the vehicle network itself '
        'runs. Phase 8 names the files of the configuration (gapEEBenchPlatform).'),
}
#: requirement -> its criteria, pinned whole
CRITERIA = {
    "reqBothRoutesInOneTopology": (
        'Met when the inspection of the realization that phase 8 records, and of the configuration of '
        'each run of the run set, shows one topology that holds both routes: one central computer, two '
        'zone controllers, one Ethernet backbone between them, a CAN bus in each zone and a direct '
        'link from the central computer to the actuation ECU that passes no zone controller.'),
    "reqCommandsOnlyFromSCOREPath": (
        'Met when the run set is judged and, in each of its runs, each driving command that reaches '
        'the actuation ECU is one that the vehicle network took from the Eclipse S-CORE path at its '
        'boundary interface.'),
    "reqCommandsOnlyOnTheirRoute": (
        'Met when the run set is judged and, in each of its runs, the records show each driving '
        'command forwarded only by the elements of the route of the run: on the route through a zone '
        'controller, the network side of the central computer, the Ethernet backbone, the zone '
        'controller of the zone of the actuation ECU and the CAN bus of that zone; on the direct '
        'route, the network side of the central computer and the direct link.'),
    "reqDeliverCommandStreamUnchanged": (
        'Met when the run set is judged and, in each of its runs, the driving commands that reach the '
        'actuation ECU, apart from those that the fault of the run affects, are the command stream '
        'without those, each once and in its order, with each part equal to the part that the path '
        'gave to the boundary interface.'),
    "reqCarryEachCommandWithin50Ms": (
        'Met when the run set is judged and, in each of its runs without a fault, each driving command '
        'reaches the actuation ECU no more than 50 ms of simulation time after the vehicle network '
        'took it.'),
    "reqApplyEachValidCommand": (
        'Met when the run set is judged and, in each of its runs, the actuation ECU applies each valid '
        'driving command that reaches it before the stop response starts and no more than 200 ms of '
        'simulation time after the last valid driving command before it reached the actuation ECU, or '
        'after the run started when it is the first, at the simulation time at which it reaches it.'),
    "reqPassDetectionPartsOnAsTaken": (
        'Met when the run set is judged and the analysis of the realization that phase 8 records, and '
        'of the records of the runs of SC-EE-003 of the run set, shows, for each element of each '
        'route, that the element passes on the issue time, the sequence count and the check value of '
        'each driving command as it received them and computes none of them anew.'),
    "reqGiveOnlyLastValidCommand": (
        'Met when the run set is judged and, in each of its runs, what the actuation ECU gives the '
        'vehicle before the stop response starts is the steering angle and the acceleration of the '
        'last valid driving command that it applied, and nothing before it applies the first.'),
    "reqStopResponseAfter200Ms": (
        'Met when the run set is judged and, in each of its runs in which more than 200 ms of '
        'simulation time pass with no valid driving command reaching the actuation ECU, the actuation '
        'ECU gives the vehicle the stop response, with its deceleration and its steering angle, from '
        'later than 200 ms and no later than 300 ms of simulation time after the last valid driving '
        'command reached it, or after the run started when none did, until the run ends, and applies '
        'no driving command that reaches it after those 200 ms; and when no run of the run set holds a '
        'start of the stop response at another time.'),
    "reqRecordNetworkIdentity": (
        'Met when each run of the run set has the record before the vehicle network takes its first '
        'driving command; when its route is the route that the records show the commands of the run '
        'passing; when the named files are the files of the configuration that phase 8 names; and when '
        'another engineer who checks out the named commit, applies the recorded difference and hashes '
        'the named files obtains the recorded values.'),
}

#: the intro sentence of the terms comment
TERMS_INTRO = 'Terms of the requirements of the vehicle network below, which the needs above use in the same sense.'
#: Every term the requirements use in a sense of their own, in its order, with its definition, pinned whole.
TERM_DEFINITIONS = {
    "Vehicle network": (
        'the system of interest that the charter declares: the network side of the central computer, '
        'the Ethernet backbone, the two zone controllers, the CAN bus of each zone, the direct link '
        'and the actuation ECU.'),
    "Element": (
        'a node or a link of the vehicle network: the network side of the central computer, a zone '
        'controller or the actuation ECU, or the Ethernet backbone, a CAN bus or the direct link.'),
    "Topology": (
        'the arrangement of the elements that the scope of the increment fixes: one central computer, '
        'two zone controllers that act as gateways between the Ethernet backbone and CAN, the Ethernet '
        'backbone between the central computer and the zone controllers, a CAN bus in each zone, and a '
        'direct link from the central computer to the actuation ECU that passes no zone controller.'),
    "Route": (
        'the way of a driving command from the boundary interface to the actuation ECU. The route '
        'through a zone controller passes the network side of the central computer, the Ethernet '
        'backbone, the zone controller of the zone of the actuation ECU and the CAN bus of that zone; '
        'the direct route passes the network side of the central computer and the direct link. The '
        'elements of a route are those that it passes and the actuation ECU.'),
    "Boundary interface": (
        'the interface on the central computer at which the vehicle network takes each driving command '
        'from the path that carries it there.'),
    "Take": (
        'receive a driving command at the boundary interface, at the simulation time at which the path '
        'that carries it there gives it.'),
    "Actuation ECU": (
        'the ECU on the CAN bus of one zone, at the end of both routes, that applies the driving '
        'commands to the vehicle.'),
    "Vehicle": 'the vehicle that the actuation ECU drives, which the virtual vehicle of the increment models.',
    "Driving command": (
        'a steering and acceleration command in the form that the driver-assistance increment, '
        'INC-DRIVING-002, fixes at its baseline, with five parts: a steering angle in degrees, '
        'positive to the left; an acceleration in m/s², negative when it decelerates; an issue time in '
        'seconds of simulation time; a sequence count, an unsigned 32-bit count from 1 in each run; '
        'and a check value, the CRC-32 over the other parts. The check value holds when it equals the '
        'CRC-32 over the other parts as they reach the actuation ECU.'),
    "Detection parts": (
        'the issue time, the sequence count and the check value of a driving command, which show a '
        'delay, a loss or a repetition, and a corruption.'),
    "Command stream": (
        'the driving commands that the path gives to the boundary interface in a run, in the order in '
        'which it gives them.'),
    "Run": (
        'one execution of the vehicle network on one route of one scenario, from the first driving '
        'command that the path gives to the boundary interface until 100 ms of simulation time after '
        'the last one that it gives there.'),
    "Fault": (
        'a disturbance of one link of the route of a run, made from outside the vehicle network, that '
        'makes a driving command lost, held on the link so that it reaches the actuation ECU more than '
        '100 ms of simulation time after its issue time, repeated, or changed in a part, that is a '
        'loss, a delay, a repetition or a corruption, or that takes the link down for the rest of the '
        'run. A fault affects the driving command that it loses, holds, repeats or changes, each '
        'driving command on the link when the link goes down, and each one given to the link while it '
        'is down; it affects no other command, so a command that a delay holds behind the held one is '
        'unaffected, even when it arrives too late to be valid. A defect of an element is no fault; '
        'the requirements hold with it in every run.'),
    "Judged run": (
        'a run in which the path that carries the driving commands to the boundary interface gives '
        'each of them there no more than 50 ms of simulation time after its issue time.'),
    "Run set": (
        'for each route, a run without a fault, of SC-EE-001 on the route through a zone controller or '
        'of SC-EE-002 on the direct route; a run of SC-EE-003 for each of a loss, a delay, a '
        'repetition and a corruption on each link of the route, the delay holding the command on the '
        'link for 300 ms of simulation time; and a run of SC-EE-004 for each link of the route. The '
        'run set is judged when each of its runs is a judged run.'),
    "Simulation time": (
        'the time on the clock of the virtual vehicle, the testbed with its model of the vehicle, in '
        'seconds; the issue time of each driving command counts on it.'),
    "Reference count": (
        'the highest sequence count among the driving commands that reached the actuation ECU earlier '
        'in the run with a check value that holds; it is 0 at the start of each run.'),
    "Valid driving command": (
        'a driving command that reaches the actuation ECU with a check value that holds, a sequence '
        'count one more than the reference count, and an issue time that is a finite number no more '
        'than 100 ms of simulation time before the simulation time at which it reaches the actuation '
        'ECU. A corruption that leaves the check value holding is judged by its sequence count and its '
        'issue time alone: the bound of the check value.'),
    "Apply": (
        'give the vehicle, at the simulation time at which a driving command reaches the actuation '
        'ECU, its steering angle and its acceleration, and hold them as the output of the actuation '
        'ECU until it gives others.'),
    "Stop response": (
        'from its start until the run ends, the actuation ECU gives the vehicle a deceleration of 4 '
        'm/s², within the tolerance of REQ-DRIVING-020, and the steering angle of the last valid '
        'driving command that it applied, or 0° when it applied none. It is the share of the vehicle '
        'network in the response that REQ-DRIVING-028 of INC-DRIVING-001 asks when the commands stop, '
        'after REQ-DRIVING-020 to REQ-DRIVING-022; the deceleration until the run ends and the 0° are '
        'set here.'),
    "Configuration": (
        'every file that sets the topology, the route of a run or the software of an element of the '
        'vehicle network.'),
    "Network identity": (
        'the route of the run; the commit of the DE4SDV repository from which the software of the '
        'vehicle network was built and its configuration taken, and the difference between the source '
        'that was built and that commit; the SHA-256 of each file of the configuration; and each '
        'setting that the vehicle network reads from outside a file, as read.'),
}

#: comment name -> (the elements it is about, its text), pinned whole
GAP_COMMENTS = {
    "actuationEndFixedInPhase5": (
        ('DE4SDV_EEArchitectureFraming::gapEEActuationEnd',),
        (
            'What phase 5 fixes of this gap, and what stays open. Fixed: a driving command is valid at '
            'the actuation ECU by the rules of the actuation adapter of the driver-assistance '
            'increment, by its check value, by its sequence count against the reference count and by '
            'its issue time against the simulation time at its arrival, which is set here in place of '
            'the newest world time of that adapter (the term valid driving command); the vehicle '
            'network applies each valid driving command (REQ-EE-006), gives the vehicle only the last '
            'valid one that it applied (REQ-EE-008) and starts the stop response once more than 200 ms '
            'of simulation time pass without a valid driving command (REQ-EE-009); no element computes '
            'a detection part anew, so the detection holds from the boundary interface to the '
            'actuation ECU through a zone controller that repacks the command (REQ-EE-007); and the '
            'actuation ECU gives the vehicle the steering angle and the acceleration of a command as '
            'they arrive (the term apply), so it needs no vehicle speed. Open, for phases 6 to 8: '
            'which element holds each of these duties other than giving the stop response, which the '
            'actuation ECU gives, where it takes the simulation time, how a zone controller repacks '
            'the command and whether the command with its detection parts fits a CAN frame. Neither '
            'adapter of the driving benches changes.')),
    "testbedObligationsOfPhase5": (
        ('DE4SDV_EEArchitectureFraming::gapEEBenchPlatform', 'DE4SDV_EEArchitectureFraming::gapEERecordedCommandStream'),
        (
            'What the criteria of phase 5 ask of System 2, whose testbed is not chosen yet: each is an '
            'obligation of the verification environment and none a criterion of the vehicle network. '
            'The testbed gives every element the one clock of the virtual vehicle, which counts the '
            'simulation time of the recorded run so that the issue time of each driving command counts '
            'on it, and the records name the step at which each element reads it. The replay gives a '
            'recorded run from its first driving command, whose sequence count is 1, to the Eclipse '
            'S-CORE path on the central computer, each command at the simulation time of its issue '
            'time, one each 100 ms of simulation time with none missing. The path gives each command '
            'to the boundary interface no more than 50 ms of simulation time after its issue time; a '
            'run in which it misses this is reported with what it missed, gets no verdict and is run '
            'again, and both runs are reported. The fault injection makes the one fault that a run of '
            'the run set names, on its link, after the first valid driving command and at least 500 ms '
            'of simulation time before the run ends, so that the stop response starts within the run '
            'and a command that a delay holds reaches the actuation ECU, with those held behind it, '
            'before the run ends; a delay holds the delayed command on its link for 300 ms of '
            'simulation time and keeps the order of the commands, and the records name its size. The '
            'replay and the fault injection give no element of the vehicle network a driving command '
            'other than through the Eclipse S-CORE path. The records hold, with its simulation time, '
            'each driving command where the vehicle network takes it, at each element that it passes '
            'and where it reaches the actuation ECU, identified by the sequence count that the vehicle '
            'network took, and what the actuation ECU gives the vehicle. The vehicle model takes the '
            'steering angle and the acceleration that the actuation ECU gives it, keeps a vehicle at '
            'standstill under a deceleration, and gets its control only from the actuation ECU. Open: '
            'the testbed, its readiness probe, its cost and its host (gapEEBenchPlatform), and which '
            'recording gives the stream and how the stream is bound to the revision that made it '
            '(gapEERecordedCommandStream).')),
}

#: the header paragraph of phase 5, pinned whole
HEADER_PARAGRAPH = (
    'Phase 5: the requirements derived from these needs, each with one subject, the vehicle network, '
    'one verification method and its success criteria. They derive from the needs and from '
    'REQ-DRIVING-028, REQ-DRIVING-039 and REQ-MW-006, and the scope of the increment caps them at ten. '
    'From the driver-assistance increment, the terms take the form of the driving command and the '
    'rules by which its actuation adapter takes a command for valid, and REQ-EE-005 derives the '
    'cadence from its realization; from INC-DRIVING-001, they take the stop response and its limits of '
    '200 ms and 300 ms of simulation time. Set here, each with its reason in a rationale: the share of '
    'the vehicle network in the delay limit; the arrival time at the actuation ECU in place of the '
    'newest world time of that adapter; the start of the stop response once more than 200 ms pass, and '
    'no earlier; its deceleration until the run ends and its steering of 0° before any valid command; '
    'the run set, with its delay of 300 ms; and the end of each run 100 ms after the path gives its '
    'last command. Keeping the rules of that adapter makes one lost or corrupted command start the '
    'stop response, which REQ-DRIVING-028 reads as a stopped path only after two missed commands. Each '
    'time limit counts on the clock of the virtual vehicle. The comment on gapEEActuationEnd gives '
    'what phase 5 fixes of that gap and what stays open, and the comment on gapEEBenchPlatform and '
    'gapEERecordedCommandStream gives what the criteria ask of System 2. Rule 5 of the increment '
    'workflow makes a requirement core when its subject has no link and it has none of its own. No '
    'requirement carries a link at this revision, so all ten read as core. REQ-EE-002 names the '
    'Eclipse S-CORE path and so depends on the feature eclipseSCORE beyond its subject; phase 9 links '
    'it. Phase 3 records no feature candidate for the vehicle network and leaves open whether the '
    'governed scope takes it as common content, so phase 9 decides on a link of its system of interest.')
#: the header sentence that phase 5 replaces
HEADER_OLD = 'Phase 5 adds to this package the requirements derived from these needs.'

CONCERN = "eeArchitectureRequirementTraceConcern"
CONCERN_DOC = (
    'Verification engineers and open-source reviewers need each requirement of the vehicle network '
    'traced to the need it derives from, with its source, its rationale, its verification method and '
    'its success criteria, to judge whether the requirements answer the needs and can be verified. No '
    'concern of the framing names this table: eeRouteVerdictConcern asks a verdict for each '
    'requirement on each route, and the table gives those requirements.')
CONCERN_HOLDERS = [('reviewer', 'OpenSourceReviewer'), ('verificationEngineer', 'VerificationEngineer')]
#: Owner decision of 2026-11-04 (the workflow's views per phase): phase 5 has one table, typed by
#: SystemRequirementDefinitionViewpoint.
VIEW = "eeArchitectureRequirementsView"
VIEWPOINT_USAGE = "selectedRequirementDefinitionViewpoint"
VIEWPOINT = "SystemRequirementDefinitionViewpoint"
MAX_ROW_HEIGHT = 500
#: the columns in order: (name, what it renders, its width or None)
COLUMNS = [
    ('ID', 'CT::reqId', None),
    ('Requirement', 'CT::declaredName', None),
    ('Statement', 'constraintLanguage', 360),
    ('Source', 'source', None),
    ('Rationale', 'rationale', 420),
    ('Method', 'verificationMethod', None),
    ('Criteria', 'successCriteria', 360),
]
TERMS_COMMENT = "termsOfTheVehicleNetworkRequirements"

GUIDE_STATUS_OLD = (
    '**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability '
    'classification and Phase 4 stakeholder needs, proposal.**')
GUIDE_STATUS_NEW = (
    '**Status: Phase 0 framing, Phase 1 concerns, Phase 2 operational context, Phase 3 capability '
    'classification, Phase 4 stakeholder needs and Phase 5 requirements, proposal.**')
GUIDE_NEXT_OLD = (
    'After that baseline, the owner decided on 2026-11-21 to start Phase 4. The next model obligation '
    'is **Phase 5**, the requirements. The testbed with its readiness probe waits for a further '
    'decision of the owner.')
GUIDE_NEXT_NEW = (
    'After that baseline, the owner decided on 2026-11-21 to start Phase 4 and on 2026-11-22 to go on '
    'with Phase 5. The next model obligation is **Phase 6**, the functional architecture. The testbed '
    'with its readiness probe waits for a further decision of the owner.')
GUIDE_HEADING = "## Requirements (Phase 5)"
#: the paragraphs of the guide's Phase 5 section, in order; BULLETS and DECISIONS stand for the two lists
GUIDE_PARAGRAPHS = (
    (
        'The '
        '[requirements](../../textual-notation-of-model/packages/features/ee/ee_architecture_needs_requirements.sysml) '
        'state what the vehicle network shall do and how each is verified. Each has one subject, the '
        'vehicle network, derives from one need, and has one verification method and its success '
        'criteria. They derive from the Phase 4 needs and from REQ-DRIVING-028, REQ-DRIVING-039 and '
        'REQ-MW-006, and the scope caps them at ten. A time limit counts on the clock of the virtual '
        'vehicle and makes no timing claim for a vehicle network.'),
    'BULLETS',
    'The Phase 5 decisions, each with its reason in the rationale of the requirement that it shapes:',
    'DECISIONS',
    (
        'A comment about `gapEEActuationEnd` records what Phase 5 fixes of that gap and what stays '
        'open, and a comment about `gapEEBenchPlatform` and `gapEERecordedCommandStream` records what '
        'the criteria ask of the testbed. `tests/test_ee_architecture_requirements.py` pins the '
        'requirements, their derivations, the terms, the two comments and the table. The Phase 5 gates '
        'check that each requirement has a statement, one subject, a derivation from a need and one '
        'verification method. Review judges whether the requirements are the right ones.'),
)
#: requirement -> the guide's Phase 5 bullet, pinned whole
GUIDE_BULLETS = {
    "REQ-EE-001": 'both routes in one topology. From `NEED-EE-001`, by inspection; a design constraint.',
    "REQ-EE-002": (
        'driving commands only from the Eclipse S-CORE path. From `NEED-EE-001`, by test; a design '
        'constraint.'),
    "REQ-EE-003": (
        'the commands of a run only through the elements of its route. From `NEED-EE-001`, by test; a '
        'design constraint.'),
    "REQ-EE-004": (
        'in each run, the delivery to the actuation ECU of each command that no fault affects, once, '
        'in its order and unchanged. From `NEED-EE-001`, by test; functional.'),
    "REQ-EE-005": (
        'in a run without a fault, each command carried from the boundary interface to the actuation '
        'ECU within 50 ms of simulation time. From `NEED-EE-001`, by test; a performance requirement.'),
    "REQ-EE-006": (
        'each valid command applied until the stop response starts. From `NEED-EE-001`, by test; '
        'functional.'),
    "REQ-EE-007": (
        'each element passes on the issue time, the sequence count and the check value as it received '
        'them, computing none anew. From `NEED-EE-002`, by analysis; a design constraint.'),
    "REQ-EE-008": (
        'until the stop response, the vehicle gets only the last valid command applied. From '
        '`NEED-EE-002`, by test; functional.'),
    "REQ-EE-009": (
        'the stop response once more than 200 ms of simulation time pass without a valid command. From '
        '`NEED-EE-002`, by test; functional.'),
    "REQ-EE-010": (
        'the network identity recorded before the first command of each run. From `NEED-EE-003`, by '
        'test; functional.'),
}
#: the Phase 5 decisions that the guide lists, in order, pinned whole
GUIDE_DECISIONS = (
    (
        'A valid driving command is one that the actuation adapter of the driver-assistance increment '
        'would accept: its check value holds, its sequence count is one more than the reference count, '
        'and its issue time is no more than 100 ms of simulation time old, measured at its arrival in '
        'place of the newest world time of that adapter.'),
    (
        'One lost or corrupted command costs two, so at one command each 100 ms it leaves the '
        'actuation ECU 300 ms without a valid command and the stop response follows, although '
        'REQ-DRIVING-028 takes two missed commands as the sign of a path that gives no more commands. '
        'Accepting the command after a gap would put the span at exactly 200 ms, where the outcome '
        'would depend on the clock of the testbed. A delay that only just makes a command late would '
        'put the span at exactly 200 ms under either rule, so the run set delays the command by 300 '
        'ms, after which the stop response follows on every clock.'),
    (
        'The stop response starts once more than 200 ms of simulation time pass without a valid '
        'command, so a command that arrives exactly at 200 ms still counts.'),
    (
        'The vehicle network gets 50 ms of simulation time from the boundary interface to the '
        'actuation ECU, half of the delay limit; a run is judged only when the path to the boundary '
        'interface keeps the other half.'),
    (
        'The cadence is at most one command each 100 ms of simulation time, from the baseline: one '
        'image of the front camera each 100 ms, one plan per frame with a result and one command per '
        'plan. A command carried within 50 ms arrives before the next, so the cadence needs no '
        'requirement of its own.'),
    (
        'The stop response gives a deceleration of 4 m/s² with the steering held until the run ends, '
        'and 0° of steering before any valid command, so the actuation ECU needs no vehicle speed; the '
        'vehicle model is to keep the vehicle at standstill under it.'),
    (
        'The detection parts are verified by analysis of the realization and of the records of the '
        'fault runs: a test cannot tell a new check value over unchanged parts from the one taken.'),
    (
        'The run set names every run that the criteria judge: on each route, a run without a fault, a '
        'run for each of the four command faults on each link, with the delay holding the command for '
        '300 ms, and a run for each link that goes down. Each run ends 100 ms after the path gives its '
        'last command, so that the last command can arrive and a run without a fault ends without the '
        'stop response.'),
    (
        'The four concerns that are reviewer questions get requirements: the topology and the elements '
        'of each route in `REQ-EE-001` and `REQ-EE-003`, the exchange items in `REQ-EE-007`, and the '
        'sequence from a fault to its response in `REQ-EE-008` and `REQ-EE-009`.'),
    (
        '`REQ-EE-002` names the Eclipse S-CORE path, so Phase 9 links it to the feature '
        '`eclipseSCORE`; the other requirements carry no link of their own.'),
)

#: the inflected forms that a statement may use in place of a term, beyond the head and its plural
TERM_INFLECTIONS = {"Take": ("takes", "taking", "taken"), "Apply": ("applies", "applied", "applying")}
#: requirement -> exactly the defined terms its statement uses (as the rule checks of phase 5 list them)
STATEMENT_TERMS = {
    "REQ-EE-001": ["Vehicle network", "Route", "Topology"],
    "REQ-EE-002": ["Vehicle network", "Driving command", "Take"],
    "REQ-EE-003": ["Vehicle network", "Driving command", "Run", "Element", "Route"],
    "REQ-EE-004": ["Run", "Vehicle network", "Actuation ECU", "Driving command", "Fault"],
    "REQ-EE-005": ["Run", "Fault", "Vehicle network", "Driving command", "Boundary interface", "Actuation ECU",
                   "Simulation time", "Take"],
    "REQ-EE-006": ["Stop response", "Vehicle network", "Apply", "Valid driving command", "Actuation ECU"],
    "REQ-EE-007": ["Vehicle network", "Detection parts", "Driving command", "Actuation ECU", "Element"],
    "REQ-EE-008": ["Stop response", "Vehicle network", "Vehicle", "Actuation ECU", "Valid driving command", "Apply"],
    "REQ-EE-009": ["Vehicle network", "Stop response", "Actuation ECU", "Simulation time", "Valid driving command"],
    "REQ-EE-010": ["Vehicle network", "Network identity", "Driving command", "Run", "Take"],
}
#: the requirements whose statements set a time limit
TIMED_REQUIREMENTS = ["REQ-EE-005", "REQ-EE-009"]
#: kind word -> how the rationale of a requirement that is not functional opens
KIND_OPENING = {"design constraint": "This is a design constraint", "performance": "This is a performance requirement"}
#: kind word -> how the guide's bullet names the kind
GUIDE_KIND = {"design constraint": "a design constraint", "performance": "a performance requirement",
              "functional": "functional"}
#: verification method -> how the guide's bullet names it
GUIDE_METHOD = {"inspect": "by inspection", "test": "by test", "analyze": "by analysis"}

#: Claims the charter excludes.
EXCLUDED = re.compile(r"(?i)certif\w*|homologat\w*|complian\w*|type approval|on-road|production-ready|member product")
#: Wording that belongs to the review of the answer, carried by a statement of none.
STATEMENT_REVIEW_WORDING = re.compile(r"(?i)\b(?:autopilot|replay\w*|overlay\w*)\b")
#: a positive safety claim; "no safety claim" is the non-claim
SAFETY_CLAIM = re.compile(r"(?i)(?<!no )\bsaf(?:e|ety|ely)\b")
#: a positive timing claim; "no timing claim" is the non-claim
TIMING_CLAIM = re.compile(r"(?i)(?<!no )\b(?:timing|latency|jitter|in time|real[- ]time|deadline)\b")
#: a clause or section number of an external source: the repository names its source records only
CLAUSE_NUMBER = re.compile(r"(?i)\b(?:annex|paragraph|clause|appendix|section)\s+\d|§\s*\d|\b\d+(?:\.\d+){2,}\b")
#: a time limit with its unit
TIMED = re.compile(r"\b\d+(?:\.\d+)?\s*(?:ms|s)\b")
#: Phase 0 to 2 text that said the baseline of INC-DRIVING-002 fixes the cadence, and the hold of Phase 4
OLD_TEXTS = (
    "Until that baseline, both can change.", "Phase 4 onward", "form and the cadence", "form and cadence",
    "its form and its cadence", "The next model obligation is **Phase 4**",
)
#: the non-claim sentence of the header
HEADER_NON_CLAIM = ("No safety, timing, on-road or production-readiness claim is made, and no member product is "
                    "claimed.")

REQUIREMENT_PATTERN = re.compile(
    r"\brequirement\s+<'(REQ-EE-[^']+)'>\s+(\w+)\s*:\s*(FunctionalRequirementCandidate|RequirementCandidate)\b")


def _raw() -> str:
    assert MODEL.is_file(), "phase 5 of INC-EE-001 adds its requirements to the needs model"
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _flat(text: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", text).split())


def _short(name: str) -> str:
    return REQUIREMENTS[name][0]


def _requirement(name: str) -> str:
    short, _need, kind, _method = REQUIREMENTS[name]
    return braced_body(_raw(), f"requirement <'{short}'> {name} : {kind}")


def _attribute(body: str, attribute: str) -> str:
    match = re.search(rf'\battribute\s+:>>\s+{attribute}\s*=\s*"([^"]*)"\s*;', body)
    assert match, f"missing {attribute}"
    return match.group(1)


def _statement(body: str) -> str:
    match = re.search(r'\brequire\s+constraint\s+statement\s*\{\s*language\s+"English"\s*/\*(.*?)\*/\s*\}', body, re.S)
    assert match, "missing the English require constraint statement"
    return _flat(match.group(1))


def _texts(name: str) -> dict[str, str]:
    body = _requirement(name)
    return {"statement": _statement(body), "source": _attribute(body, "source"),
            "rationale": _attribute(body, "rationale"), "criteria": _attribute(body, "successCriteria")}


def _terms_comment() -> str:
    matches = re.findall(rf"\bcomment\s+{TERMS_COMMENT}\s*/\*(.*?)\*/", _raw(), re.S)
    assert len(matches) == 1, "one comment defines the terms of the requirements"
    return matches[0]


def test_the_requirements_are_exactly_the_ten_of_phase_5_in_order():
    declared = REQUIREMENT_PATTERN.findall(_code())
    assert declared == [(short, name, kind) for name, (short, _need, kind, _method) in REQUIREMENTS.items()]
    assert len(declared) <= SCOPE_CAP, "the charter's scope cap: at most ten requirements"
    assert [short for short, _name, _kind in declared] == [f"REQ-EE-{n:03d}" for n in range(1, len(declared) + 1)], \
        "REQ-EE-001 onward, without a gap, in order"


def test_each_requirement_has_its_subject_one_statement_and_its_attributes():
    # SpecifyRequirements: requirementHasStatement, requirementHasOneSubject, requirementHasVerificationMethod,
    # and the advisories requirementSubjectIsSystemOfInterest and requirementStatesSuccessCriteria.
    for name, (_short, _need, _kind, method) in REQUIREMENTS.items():
        body = _requirement(name)
        code = strip_comments(body)
        subjects = re.findall(r"(?m)^\s*(subject\b[^\n]*)$", code)
        assert subjects == [SUBJECT_LINE], (name, subjects)
        statements = re.findall(r'\brequire\s+constraint\s+statement\s*\{\s*language\s+"English"\s*/\*', body)
        assert len(statements) == 1, (name, "one English statement")
        assert len(re.findall(r"\brequire\b", code)) == 1, (name, "one require constraint")
        assert _attribute(body, "verificationMethod") == method, name
        assert _attribute(body, "successCriteria").startswith("Met when"), name
        assert body.count("attribute :>> verificationStatus = VVStatus::NotStarted;") == 1, name
        assert len(re.findall(r"\bverificationStatus\b", code)) == 1, name


def test_each_text_of_the_requirements_is_pinned_whole():
    for name in REQUIREMENTS:
        texts = _texts(name)
        assert texts["statement"] == STATEMENTS[name], (name, "statement")
        assert texts["source"] == SOURCES[name], (name, "source")
        assert texts["rationale"] == RATIONALES[name], (name, "rationale")
        assert texts["criteria"] == CRITERIA[name], (name, "criteria")


def test_each_statement_holds_one_obligation_in_the_positive_form():
    for name in REQUIREMENTS:
        statement = _statement(_requirement(name))
        assert statement.count(" shall ") == 1, (name, "one obligation per statement")
        assert len(statement.split()) <= 60, (name, len(statement.split()))
        assert not re.search(r"\bnot\b", statement), (name, "the positive form")
        assert "n't" not in statement, (name, "the positive form")
        assert not STATEMENT_REVIEW_WORDING.findall(statement), (name, STATEMENT_REVIEW_WORDING.findall(statement))
        assert re.search(r"(?i)(?:^|, )the vehicle network$", statement.split(" shall ", 1)[0]), \
            (name, "the vehicle network is the subject of the statement")


def test_each_source_leads_with_its_need_and_wraps_in_its_column():
    for name, (_short, need, _kind, _method) in REQUIREMENTS.items():
        source = _attribute(_requirement(name), "source")
        assert source.startswith(NEED_SHORT[need] + ";"), (name, source)
        longest = max(source.split(), key=len)
        assert len(longest) <= 40, (name, longest)
        assert not re.search(r"\bconcern\s+\w+", source), (name, "a model-wide test reads 'concern <name>'")


def test_rationales_and_criteria_wrap_in_their_columns():
    for name in REQUIREMENTS:
        texts = _texts(name)
        for field in ("rationale", "criteria"):
            longest = max(texts[field].split(), key=len)
            assert len(longest) <= 40, (name, field, longest)


def test_no_requirement_text_makes_an_excluded_claim():
    for name in REQUIREMENTS:
        texts = _texts(name)
        for field in ("statement", "rationale", "criteria"):
            text = texts[field]
            for pattern in (EXCLUDED, SAFETY_CLAIM, TIMING_CLAIM):
                assert not pattern.findall(text), (name, field, pattern.findall(text))
            for old in OLD_TEXTS:
                assert old not in text, (name, field, old)
    raw = _raw()
    assert not CLAUSE_NUMBER.findall(raw), CLAUSE_NUMBER.findall(raw)


def test_each_timed_requirement_names_its_time_domain_and_its_non_claim():
    timed = []
    for name in REQUIREMENTS:
        texts = _texts(name)
        if TIMED.search(texts["statement"]):
            timed.append(_short(name))
            assert "simulation time" in texts["statement"], name
            assert "clock of the virtual vehicle" in texts["rationale"], name
            assert "no timing claim for a vehicle network" in texts["rationale"], name
    assert timed == TIMED_REQUIREMENTS


def test_each_kind_opens_its_rationale():
    for name, (_short, _need, kind, _method) in REQUIREMENTS.items():
        rationale = _attribute(_requirement(name), "rationale")
        if kind == R:
            assert rationale.startswith(KIND_OPENING[KIND_WORDS[name]]), (name, KIND_WORDS[name])
        else:
            assert KIND_WORDS[name] == "functional", name
            assert not rationale.startswith(tuple(KIND_OPENING.values())), name


def test_each_requirement_derives_from_its_need_through_derives_from_need_only():
    # requirementDerivesFromNeed counts DerivesFromNeed only; a plain dependency to a need does not count
    # and is not declared.
    code = _code()
    derivations = re.findall(
        r"\bconnection\s+(\w+)\s*:\s*DerivesFromNeed\s+connect\s+(\w+)\s+to\s+(\w+)\s*;", code)
    assert len(derivations) == 10
    expected = [(f"{name[3].lower()}{name[4:]}Derivation", need, name)
                for name, (_short, need, _kind, _method) in REQUIREMENTS.items()]
    assert derivations == expected
    assert {need for _derivation, need, _name in derivations} == set(NEED_SHORT), "every need of phase 4 has one"
    plain = re.findall(r"\bdependency\s+\w+\s+from\s+(\w+)\s+to\s+([\w:]+)\s*;", code)
    assert not [pair for pair in plain if pair[0] in REQUIREMENTS and pair[1].split("::")[-1] in NEED_SHORT]


def test_the_terms_are_defined_once_and_exactly():
    comment = _terms_comment()
    text = _flat(comment)
    assert text.startswith(TERMS_INTRO), "the terms open with their intro"
    heads = tuple(re.findall(r"(?m)^\s*\*\s+- ([^:\n]+):", comment))
    assert heads == tuple(TERM_DEFINITIONS), heads
    for head, definition in TERM_DEFINITIONS.items():
        assert f"- {head}: {definition}" in text, head


def _used_terms(text: str) -> set[str]:
    """The defined terms that a text uses: each occurrence of a head, its plural or a listed inflection, read as the
    longest defined term that covers it, so that "the vehicle network" uses Vehicle network and never Vehicle."""
    low = text.lower()
    found = []
    for head in TERM_DEFINITIONS:
        for form in (head.lower(), head.lower() + "s") + TERM_INFLECTIONS.get(head, ()):
            found += [(m.start(), m.end(), head) for m in re.finditer(rf"\b{re.escape(form)}\b", low)]
    taken, used = [], set()
    for start, end, head in sorted(found, key=lambda item: item[0] - item[1]):
        if all(end <= first or start >= last for first, last in taken):
            taken.append((start, end))
            used.add(head)
    return used


def test_each_statement_uses_defined_terms():
    by_short = {short: name for name, (short, _need, _kind, _method) in REQUIREMENTS.items()}
    assert sorted(STATEMENT_TERMS) == sorted(by_short)
    for short, heads in STATEMENT_TERMS.items():
        assert set(heads) <= set(TERM_DEFINITIONS), (short, sorted(set(heads) - set(TERM_DEFINITIONS)))
        # the list is exact: each listed term is used, and each defined term that the statement uses is listed
        assert _used_terms(_statement(_requirement(by_short[short]))) == set(heads), short


def test_the_gap_comments_record_what_phase_5_fixes_and_asks():
    raw = _raw()
    for name, (targets, text) in GAP_COMMENTS.items():
        declaration = f"comment {name} about {', '.join(targets)}"
        assert raw.count(declaration) == 1, declaration
        assert len(re.findall(rf"\bcomment\s+{name}\b", raw)) == 1, name
        match = re.search(rf"{re.escape(declaration)}\s*/\*(.*?)\*/", raw, re.S)
        assert match, declaration
        assert _flat(match.group(1)) == text, name


def test_the_header_states_phase_5():
    header = _raw().split("\npackage ", 1)[0]
    paragraphs = [_flat(part) for part in re.split(r"\n\s*\*\s*\n", header)]
    assert HEADER_PARAGRAPH in paragraphs, "the header paragraph of phase 5, pinned whole"
    assert HEADER_OLD not in _flat(header)
    assert HEADER_NON_CLAIM in _flat(header), "the header keeps its non-claims"


def test_the_phase_4_contract_comment_is_now_stated_in_the_rationales():
    # Phase 4 kept the input contract as a comment about NEED-EE-001 for phase 5. Phase 5 states it in the
    # requirements and their rationales, so the comment no longer earns its place.
    assert "commandFormContract" not in _raw()


def test_no_feature_link_before_phase_9():
    # Phase 3 records no feature candidate for the vehicle network; phase 9 decides on a link.
    raw = _raw()
    assert "DE4SDV_SDVProductLineFeatureModel" not in raw
    assert not re.search(r"\bimport\s+DE4SDV_ProductLine", raw)
    assert "#FeatureBinding" not in raw
    # rule 5 reads a dependency of a requirement on a feature, a variant or its definition as a link: no client of any
    # dependency is one of the ten, by declared name, qualified name or short name, in any place of the client list
    names = "|".join(REQUIREMENTS)
    shorts = "|".join(re.escape(short) for short, _need, _kind, _method in REQUIREMENTS.values())
    client = re.compile(rf"(?:^|[\s,:])(?:'?(?:{names})'?|'(?:{shorts})')(?![\w'])")
    for dependency in re.findall(r"\bdependency\b[^;{]*", _code()):
        clients = re.search(r"\bfrom\b(.*?)\bto\b", dependency, re.S)
        assert not (clients and client.search(clients.group(1))), f"a requirement has a dependency: {dependency}"


def _columns(body: str) -> list[str]:
    return re.findall(r"\bview\s+(\w+)\s*:>\s*columnViews\s*\{", body)


def _column(body: str, column: str) -> str:
    return braced_body(body, f"view {column} :> columnViews")


def test_one_table_defines_each_requirement_with_its_verification_and_frames_the_trace_concern():
    code = _code()
    assert re.findall(r"\bconcern\s+(\w+)\s*:\s*RequirementTraceConcern\b", code) == [CONCERN]
    concern = braced_body(code, f"concern {CONCERN} : RequirementTraceConcern")
    assert len(re.findall(r"\bsubject\s*;", concern)) == 1
    holders = sorted(re.findall(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;", concern))
    assert holders == CONCERN_HOLDERS
    rest = re.sub(r"\bstakeholder\s+\w+\s*:\s*\w+\s*;|\bsubject\s*;|\bdoc\b", "", concern)
    assert not rest.strip(), ("the concern holds its doc, its subject and its stakeholders, nothing else", rest)
    raw_concern = braced_body(_raw(), f"concern {CONCERN} : RequirementTraceConcern")
    doc = re.search(r"\bdoc\s*/\*(.*?)\*/", raw_concern, re.S)
    assert doc and _flat(doc.group(1)) == CONCERN_DOC

    framing = []
    for view, kind in re.findall(r"\bview\s+(\w+)\s*:\s*([\w:]+)\s*\{", code):
        if re.search(rf"\bframe\s+{CONCERN}\s*;", braced_body(code, f"view {view} : {kind}")):
            framing.append((view, kind))
    assert framing == [(VIEW, "TVD::TableView")], "one table for phase 5, not two forms of the same requirements"
    body = braced_body(code, f"view {VIEW} : TVD::TableView")
    assert re.search(rf"\bviewpoint\s+{VIEWPOINT_USAGE}\s*:\s*{VIEWPOINT}\s*\{{\s*frame\s+{CONCERN}\s*;\s*\}}", body)
    assert re.findall(r"\bexpose\s+([^;]+);", body) == list(REQUIREMENTS)
    assert "filter @ SysML::RequirementUsage;" in body
    assert "attribute :>> includeReferenceElements = true;" in body
    assert f"attribute :>> maxRowHeight = {MAX_ROW_HEIGHT};" in body
    assert _columns(body) == [column for column, _render, _width in COLUMNS]
    for column, render, width in COLUMNS:
        text = _column(body, column)
        if render.startswith("CT::"):
            assert re.search(rf"featureToRender\s*=\s*{re.escape(render)}\s*;", text), column
        elif render == "constraintLanguage":
            assert re.search(r'CT::constraintLanguage\s*\{\s*attribute\s+constraintName\s*=\s*"statement"\s*;', text)
            assert re.search(r"attribute\s+constraintType\s*=\s*CL::ConT::required\s*;", text)
            assert re.search(r'attribute\s+constraintLanguage\s*=\s*"English"\s*;', text)
        else:
            assert re.search(rf'CT::attributeValue\s*\{{\s*attribute\s+attributeName\s*=\s*"{render}"\s*;\s*\}}',
                             text), column
        widths = re.findall(r"attribute\s+:>>\s+columnWidth\s*=\s*(\d+)\s*;", text)
        assert widths == ([str(width)] if width else []), (column, widths)


def test_each_identity_and_declared_name_is_declared_once_in_the_model():
    declared = short_name_declarations(r"REQ-EE-\d{3}", MODEL_ROOTS)
    assert sorted(declared) == sorted(short for short, _need, _kind, _method in REQUIREMENTS.values())
    for short, paths in declared.items():
        assert paths == [MODEL], (short, paths)
    names = [*REQUIREMENTS, *(f"{name[3].lower()}{name[4:]}Derivation" for name in REQUIREMENTS), TERMS_COMMENT,
             *GAP_COMMENTS, CONCERN, VIEW]
    counts = dict.fromkeys(names, 0)
    pattern = re.compile(r"\b(?:requirement|connection|comment|concern|view|part|attribute|item|action|dependency|"
                         r"port|interface|allocation|constraint|state|use\s+case|verification|analysis|viewpoint|"
                         r"rendering|occurrence|calc|enum|package)(?:\s+|(?=<))(?:def\b\s*)?(?:<'[^']*'>\s*)?(?!def\b)'?(\w+)\b")
    for path in sorted(path for root in MODEL_ROOTS for path in root.rglob("*.sysml")):
        for name in pattern.findall(strip_comments(path.read_text(encoding="utf-8"))):
            if name in counts:
                counts[name] += 1
    assert counts == dict.fromkeys(names, 1), {name: count for name, count in counts.items() if count != 1}


def _guide_section(guide: str) -> str:
    return guide.split(GUIDE_HEADING, 1)[1].split("\n## ", 1)[0]


def test_the_guide_states_phase_5_and_the_next_obligation():
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.count(GUIDE_HEADING + "\n") == 1
    assert guide.index("## Stakeholder needs (Phase 4)") < guide.index(GUIDE_HEADING) \
        < guide.index("## What the framing already records as open")
    raw_section = _guide_section(guide)
    section = " ".join(raw_section.split())
    for paragraph in GUIDE_PARAGRAPHS:
        if paragraph not in ("BULLETS", "DECISIONS"):
            assert paragraph in section, paragraph
    bullets = [(match[1], " ".join(match[2].split()))
               for match in re.finditer(r"(?ms)^- `(REQ-EE-\d{3})`:(.*?)(?=^- `|^\s*$)", raw_section)]
    assert bullets == list(GUIDE_BULLETS.items()), "the guide's Phase 5 bullets, pinned whole, in order"
    decisions = [(match[1], " ".join(match[2].split()))
                 for match in re.finditer(r"(?ms)^(\d+)\. (.*?)(?=^\d+\. |^\s*$)", raw_section)]
    assert decisions == [(str(n), text) for n, text in enumerate(GUIDE_DECISIONS, 1)], \
        "the decisions, in order"
    for name, (short, _need, _kind, method) in REQUIREMENTS.items():
        bullet = GUIDE_BULLETS[short]
        assert f"From `{NEED_SHORT[REQUIREMENTS[name][1]]}`, {GUIDE_METHOD[method]}; " in bullet, (short, method)
        assert bullet.endswith(f"; {GUIDE_KIND[KIND_WORDS[name]]}."), (short, KIND_WORDS[name])
    assert not CLAUSE_NUMBER.findall(raw_section), CLAUSE_NUMBER.findall(raw_section)
    flat = " ".join(guide.split())
    assert GUIDE_STATUS_NEW in flat and GUIDE_STATUS_OLD not in flat
    assert GUIDE_NEXT_NEW in flat and GUIDE_NEXT_OLD not in flat
    assert guide.endswith("\n") and not guide.endswith("\n\n"), "the guide ends with exactly one newline"


def test_the_guide_check_section_runs_the_phase_5_test():
    guide = GUIDE.read_text(encoding="utf-8")
    section = guide.split("## Check the framing change", 1)[1].split("\n## ", 1)[0]
    assert "tests/test_ee_architecture_requirements.py" in " ".join(section.split())
