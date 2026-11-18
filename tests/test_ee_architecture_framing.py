"""Content pins for the framing of the E/E architecture increment, not semantic validation.

The framing of INC-EE-001 holds Phase 0 and the Phase 1 concerns. These tests hold its structure to
the method's Phase 0 and Phase 1 shapes, pin each decided statement by its own phrase, hold the
requirements and the records that the framing names to their text in the model, and hold the guide,
the folder's upstream record and the rows that name the increment elsewhere to the model. They read
the model text; they do not parse SysML.

What they do not hold: a sentence that no pin names can change inside a doc of the model or inside
the record, and a report of a run in words that the scan for past behavior does not list passes.
Those are for the review of the text.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from sysml_shapes import braced_body, strip_comments
from test_saf_domains import SAF_FILE, _domains
from test_views_per_phase import _canonical_list

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import check_naming  # noqa: E402

MODEL_ROOTS = (ROOT / "textual-notation-of-model", ROOT / "model-based-product-line-engineering")
PACKAGES = ROOT / "textual-notation-of-model/packages"
FEATURES = PACKAGES / "features"
EE = FEATURES / "ee"
MODEL = EE / "ee_architecture_framing.sysml"
UPSTREAM_RECORD = EE / "upstream.md"
CLOSED_LOOP_REQUIREMENTS = FEATURES / "driving/closed_loop_driving_needs_requirements.sysml"
DRIVER_ASSISTANCE_REQUIREMENTS = FEATURES / "driving/driver_assistance_needs_requirements.sysml"
MIDDLEWARE_REQUIREMENTS = FEATURES / "middleware/middleware_requirements.sysml"
MIDDLEWARE_NEEDS = FEATURES / "middleware/middleware_stakeholder_needs.sysml"
MIDDLEWARE_SCORE_FRAMING = FEATURES / "middleware/middleware_score_framing.sysml"
MIDDLEWARE_SCORE_REQUIREMENTS = FEATURES / "middleware/middleware_score_needs_requirements.sysml"
DRIVER_ASSISTANCE_REALIZATION = FEATURES / "driving/driver_assistance_physical_software_realization.sysml"
CLOSED_LOOP_REALIZATION = FEATURES / "driving/closed_loop_driving_physical_software_realization.sysml"
AEBS_SIMULATION_DEPLOYMENT = FEATURES / "aebs/aebs_simulation_deployment.sysml"
PRODUCT_LINE = ROOT / "model-based-product-line-engineering"
AEBS_REALIZATION = FEATURES / "aebs/aebs_physical_software_realization.sysml"
PLATFORM_STACK = PACKAGES / "architecture/sdv_platform_stack.sysml"
MIDDLEWARE_BOUNDARY = PACKAGES / "architecture/aaos_sdv_middleware_boundary.sysml"
EXECUTION_ENVIRONMENTS = PACKAGES / "architecture/execution_environments.sysml"
FEATURE_MODELS = ROOT / "model-based-product-line-engineering/feature-models"
GUIDE = ROOT / "docs/guides/ee-architecture-increment.md"
GLOSSARY = ROOT / "docs/terminology/glossary.md"
NAMING = ROOT / "docs/naming/naming-conventions.md"
PACKAGE = "DE4SDV_EEArchitectureFraming"
IDENTITY = "INC-EE-001"

DOC = re.compile(r"\bdoc\s*/\*(.*?)\*/", re.DOTALL)
#: a usage declared at package level (two spaces of indent), with an optional short name
PACKAGE_USAGE = re.compile(r"(?m)^  (part|requirement|concern)\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*(\w+)")

#: in-scope item -> the statement it makes
IN_SCOPE = {
    "eeTopologyInScope":
        "One topology of the vehicle network: one central computer, two zone controllers, one Ethernet backbone "
        "between them, a CAN bus at the edge of each zone, and a direct link from the central computer to the "
        "actuation ECU that passes no zone controller.",
    "eeCommandFlowInScope":
        "The driving command of the driver-assistance increment, down from its source on the central computer to "
        "an actuation ECU on CAN.",
    "eeCommandRouteInScope":
        "Two routes of the driving command to the actuation ECU: through the Ethernet backbone and a zone "
        "controller, and over the direct link.",
    "eeNetworkFaultsInScope":
        "Faults of the vehicle network on the route of the command: one link of that route that goes down, and a "
        "command that is lost, delayed, repeated or corrupted on its way.",
    "eeVerdictEvidenceInScope":
        "A pass or a fail for each requirement of the increment on each route, on a virtual vehicle, from the "
        "replay of a recorded command stream, bound to the route, the topology, the configuration and the revision "
        "that ran.",
}
#: out-of-scope item -> the statement it makes
OUT_OF_SCOPE = {
    "eeTimingOutOfScope":
        "Claims on the timing of the vehicle network, such as latency and jitter budgets, and time "
        "synchronisation between its nodes.",
    "eeTrafficShapingOutOfScope": "Traffic shaping, and the behavior of the command under competing load on the "
                                  "network.",
    "eeDiagnosticsUpdateOutOfScope": "Diagnostics and software update of the ECUs through the zone controllers.",
    "eeSecurityOutOfScope": "Security hardening: segmentation, authenticated messages and link protection.",
    "eeRedundancyOutOfScope": "Redundancy, the operation of the vehicle after the loss of a whole zone, and power "
                              "modes such as sleep and wake.",
    "eeVariabilityOutOfScope": "A second topology, and any variability of the E/E architecture in the product "
                               "line.",
    "eeSensorDataOutOfScope": "Sensor data, such as the vehicle speed, up from an ECU on CAN to the central "
                              "computer.",
    "eeClosedLoopOutOfScope": "Closed loop with a driving simulator through the vehicle network.",
    "eeHardwareEffectsOutOfScope":
        "Effects of hardware: the physical layer, bit timing on CAN and the timing of microcontrollers.",
    "eeSafetyClaimOutOfScope":
        "Any safety argument, including freedom from interference, and any compliance, type approval or "
        "certification claim.",
}
#: assumption -> the phrases that state its premise and what the framing decided with it
ASSUMPTIONS = {
    "asmEECommandFromDrivingBaseline": (
        "The form and the cadence of the driving command are those that the driver-assistance increment, "
        "INC-DRIVING-002, fixes at its baseline.",
        "Until that baseline, both can change."),
    "asmEESoftwareTestbedStandsIn": (
        "A software testbed stands for the vehicle network in function.",
        "It gives no hardware timing:",
        "A verdict holds for that testbed only."),
    "asmEEScoreCommandSource": (
        "The driving command enters the vehicle network from the Eclipse S-CORE path of the existing increments on "
        "the central computer.",
        "A readiness probe tests this first.",
        "If it does not hold, the owner decides how the increment goes on."),
}
#: gap -> the phrase that states what is open
GAPS = {
    "gapEESafetyPathArchitecture": "Whether a verdict on them bears on that choice is open",
    "gapEEZoneRouteInVehicles": "Whether vehicles carry a driving command through a zone controller is open",
    "gapEEActuationEnd": "keeps the detection end to end, is open",
    "gapEEBrakeHandoff": "Whether a result of this increment meets that obligation for the AEBS is open",
    "gapEEStackAndNetworkBoundary": "How the vehicle network of this increment relates to them is open",
    "gapEENetworkInProductLine": "The governed product-line scope has no element for the vehicle network.",
    "gapEEBenchPlatform": "The testbed that stands for the vehicle network in this increment is not chosen",
    "gapEERecordedCommandStream": "Which recording gives that stream",
}
#: gap -> the label of its open point in the guide
OPEN_POINTS = {
    "gapEESafetyPathArchitecture": "The safety-path architecture",
    "gapEEZoneRouteInVehicles": "The zone route in vehicles",
    "gapEEActuationEnd": "The actuation end",
    "gapEEBrakeHandoff": "The hand-off to the brake ECU",
    "gapEEStackAndNetworkBoundary": "The platform stack and the network boundary",
    "gapEENetworkInProductLine": "The vehicle network's place in the product line",
    "gapEEBenchPlatform": "No bench for the vehicle network",
    "gapEERecordedCommandStream": "The recorded command stream",
}
#: requirement identity -> (file, element, the statement the framing relies on)
CITED_REQUIREMENTS = {
    "REQ-DRIVING-039": (DRIVER_ASSISTANCE_REQUIREMENTS, "reqDetectableDrivingCommand",
                        "in a form that lets the actuation detect its loss, delay, repetition or corruption on the "
                        "Eclipse S-CORE path."),
    "REQ-DRIVING-028": (CLOSED_LOOP_REQUIREMENTS, "reqStopOnLostCommands",
                        "When no valid command has reached the actuation of the vehicle for 200 ms of simulation "
                        "time, the driving system shall apply the stop response at the actuation."),
    "REQ-MW-006": (MIDDLEWARE_REQUIREMENTS, "reqIsolateSafetyPath",
                   "shall prevent a failure of the non-safety middleware integration path from causing an "
                   "uncontrolled emergency intervention command"),
}
#: a past form of what a system does in a run: a framing reports no run
PAST_BEHAVIOR = re.compile(r"(?i)\b(?:braked|stopped|rejected|detected|routed|forwarded|passed|failed|"
                           r"dropped|recovered|crashed|hung|delivered)\b")
#: an affirmative claim of approval or admission
APPROVAL = re.compile(r"(?i)\b(?:compliant|complies|certified|homologated|type-approved|admitted)\b")
#: glossary row -> the sentence that bounds it
#: Phase 1: concern -> (its SAF concern definition, the in-scope items its doc names first, its native stakeholders
#: in order, the sentences that state its question, and the views that answer it as (phase, viewpoint definition)
#: pairs, read from the doc's answer). One concern per question; a concern is held by the parties whose interest it
#: states, not only by the roles that check it.
PHASE1_CONCERNS = {
    "eeVehicleCommandConcern": (
        "OperationalCapabilityConcern", ("eeCommandFlowInScope", "eeNetworkFaultsInScope"),
        [("occupant", "VehicleOccupant"), ("roadUser", "RoadUser")],
        ("Vehicle occupants and road users need the vehicle to act on the driving command that its central computer "
         "gives across the vehicle network, whichever route the command takes, and to act on no command that a fault "
         "of the network has made invalid on its way.",
         "It states what they expect, not how well the network meets it: no safety, timing or performance claim for "
         "a vehicle network follows from it."),
        ((2, "OperationalStoryViewpoint"),)),
    "eeTopologyStructureConcern": (
        "PhysicalStructureConcern", ("eeTopologyInScope",),
        [("systemArchitect", "SystemArchitect"), ("productLineEngineer", "ProductLineEngineer")],
        ("System architects and product-line engineers need to see which elements make up the one topology of the "
         "vehicle network and in which role each is used: the network side of the central computer, the Ethernet "
         "backbone, the two zone controllers as gateways between the backbone and CAN, the CAN bus of each zone, the "
         "direct link that passes no zone controller, and the actuation ECU on CAN.",
         "The lifecycle decision is whether the product line admits this topology as its reference vehicle "
         "network.",
         "How it relates to the platform stack and to the vehicle network boundary of the AAOS SDV middleware is open "
         "for phases 2 and 3 (gapEEStackAndNetworkBoundary)."),
        ((8, "PhysicalStructureDefinitionViewpoint"),)),
    "eeCommandItemConcern": (
        "PhysicalLogicalItemMappingConcern", ("eeCommandFlowInScope",),
        [("systemsEngineer", "SystemsEngineer"), ("safetyExpert", "SafetyExpert")],
        ("Systems engineers and safety experts need to see which exchange item of the vehicle network carries the "
         "driving command on each part of its way, on the Ethernet backbone, through a zone controller and on CAN, "
         "and whether each keeps the parts of the command by which the actuation detects its loss, delay, "
         "repetition or corruption, including where a zone controller repacks it from Ethernet to CAN "
         "(gapEEActuationEnd).",
         "The form and the cadence of the command are those that the driver-assistance increment fixes at its "
         "baseline (asmEECommandFromDrivingBaseline)."),
        ((8, "PhysicalInternalExchangeViewpoint"),)),
    "eeCommandRouteExchangeConcern": (
        "PhysicalInternalExchangeConcern", ("eeCommandRouteInScope",),
        [("systemArchitect", "SystemArchitect"), ("systemsEngineer", "SystemsEngineer")],
        ("System architects and systems engineers need to see, on each of the two routes, which elements of the "
         "vehicle network exchange the driving command on its way from the network side of the central computer to "
         "the actuation ECU, through the Ethernet backbone and a zone controller or over the direct link, and the "
         "boundary interface by which the command enters the network from the Eclipse S-CORE path "
         "(asmEEScoreCommandSource).",
         "This increment takes neither route as given (gapEEZoneRouteInVehicles), and phases 6 to 8 decide the "
         "medium of the direct link."),
        ((8, "PhysicalInternalExchangeViewpoint"),)),
    "eeNetworkFaultResponseConcern": (
        "SystemProcessConcern", ("eeNetworkFaultsInScope",),
        [("safetyExpert", "SafetyExpert"), ("systemsEngineer", "SystemsEngineer")],
        ("Safety experts and systems engineers need to see the sequence from each fault of the vehicle network on the "
         "route of the command, a link of that route that goes down and a command that is lost, delayed, repeated or "
         "corrupted, to its detection at the actuation and to the response that follows there, independent of the "
         "elements that realize it.",
         "A time limit on a response counts on the clock of the virtual vehicle.",
         "No safety argument follows from it."),
        ((6, "SystemProcessViewpoint"),)),
    "eeRouteVerdictConcern": (
        "ArgumentationAssuranceConcern", ("eeVerdictEvidenceInScope",),
        [("productLineEngineer", "ProductLineEngineer"), ("verificationEngineer", "VerificationEngineer")],
        ("Product-line engineers and verification engineers need the lifecycle decision to rest on a pass or a fail "
         "for each requirement of the increment on each route, each bound to the route, the topology, the "
         "configuration and the revision that ran, from the replay of a recorded command stream whose binding to the "
         "revision that made it is open (gapEERecordedCommandStream).",
         "A verdict holds for the software testbed only (asmEESoftwareTestbedStandsIn) and is no timing claim for a "
         "vehicle network, and a fail stays a recorded result."),
        ((10, "ArgumentationAssuranceViewpoint"),)),
}
#: Phase 1 concern -> (the label of its bullet in the guide, the nonclaim or boundary sentences the bullet keeps).
#: The bullet's SAF definition and holders are read from the model's concern, not from this table.
GUIDE_CONCERNS = {
    "eeVehicleCommandConcern": ("The driving command, operational part",
                                ("No safety, timing or performance claim for a vehicle network follows from it.",)),
    "eeTopologyStructureConcern": ("The topology",
                                   ("The lifecycle decision is whether the product line admits this topology as "
                                    "its reference vehicle network.",)),
    "eeCommandItemConcern": ("The command on the network",
                             ("whether each keeps the parts of the command by which the actuation detects its "
                              "loss, delay, repetition or corruption.",
                              "The form of the command is the one that the driver-assistance increment fixes at "
                              "its baseline.")),
    "eeCommandRouteExchangeConcern": ("The two routes", ("Neither route is taken as given.",)),
    "eeNetworkFaultResponseConcern": ("Faults of the network", ()),
    "eeRouteVerdictConcern": ("Verdicts",
                              ("A verdict holds for the software testbed only and is no timing claim for a "
                               "vehicle network.",)),
}
#: the words by which a concern's doc names a view that answers it -> the viewpoint definition of that view
VIEW_PHRASES = {
    "operational story": "OperationalStoryViewpoint",
    "system process": "SystemProcessViewpoint",
    "physical structure definition": "PhysicalStructureDefinitionViewpoint",
    "view of the claimed path": "PhysicalInternalExchangeViewpoint",
    "argumentation assurance view": "ArgumentationAssuranceViewpoint",
}
#: a sentence of a concern's doc that says by which views the concern is answered
ANSWER_SENTENCE = re.compile(r"[^.]*\banswered\b[^.]*\.", re.I)
#: the owner's decision of 2026-11-18 on the phases before the baseline of INC-DRIVING-002, in the model's words
PHASES_BEFORE_BASELINE = (
    "The owner decided on 2026-11-17 to start this increment and to frame it now, and on 2026-11-18 to carry out "
    "Phases 1 to 3 of this increment before the baseline of the driver-assistance increment, INC-DRIVING-002, whose "
    "driving command it carries.",
    "Phase 4 onward and the testbed with its readiness probe wait for that baseline and for a further decision of "
    "the owner.")
GLOSSARY_ROWS = {
    "E/E architecture |": "The product line has no reference E/E architecture;",
    "Central computer |": "reaches sensors and actuators through the vehicle network.",
    "Zone controller |": "a gateway between the Ethernet backbone and the buses of its zone, such as CAN or LIN,",
    "CAN |": "it is a bus at the edge of a zone, between a zone controller and the ECUs of its zone.",
}


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _doc(declaration: str, source: str | None = None) -> str:
    """The first doc of the declaration's body, without comment leaders and line breaks."""
    match = DOC.search(braced_body(_raw() if source is None else source, declaration))
    assert match, f"{declaration} has no doc"
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", match.group(1)).split())


def _declared(kind: str) -> set[str]:
    """The parts of the kind, with or without a short name."""
    return set(re.findall(rf"\bpart\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*{kind}\b", _code()))


def _row(path: Path, first_cell: str) -> str:
    """The one table row of the file whose first cell starts with the text."""
    rows = [line for line in path.read_text(encoding="utf-8").splitlines() if line.startswith(f"| {first_cell}")]
    assert len(rows) == 1, f"{path.name}: {len(rows)} rows start with {first_cell!r}"
    return rows[0]


def _flat(text: str) -> str:
    return " ".join(text.split())


def _link_text(markdown: str) -> str:
    """The text of a Markdown passage with each link reduced to its words, without line breaks."""
    return _flat(re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", markdown))


def _record_section(record: str, heading: str) -> str:
    """The text of the one second-level section of the record with the heading."""
    assert record.count(f"\n## {heading}\n") == 1, heading
    return record.split(f"\n## {heading}\n", 1)[1].split("\n## ", 1)[0]


def test_increment_declares_the_phase_zero_shape():
    assert MODEL.is_file(), "the increment needs a framing model"
    code = _code()
    assert re.findall(r"(?m)^package\s+(\w+)\s*\{", code) == [PACKAGE], "one global package per file"
    assert "part def EEArchitectureIncrement :> EngineeringIncrement;" in code
    assert re.search(rf"part\s+<'{IDENTITY}'>\s+eeArchitectureIncrement\s*:\s*EEArchitectureIncrement\b", code)
    problem = braced_body(code, "requirement eeArchitectureProblem : ProblemStatement")
    assert "subject eeArchitectureSubject : EEArchitectureIncrement;" in problem
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", problem) == [
        "SystemArchitect", "SystemsEngineer", "SafetyExpert", "ProductLineEngineer", "VerificationEngineer"]
    assert _declared("IncrementEngineeringQuestion") == {"eeArchitectureQuestion"}
    assert _declared("IncrementLifecycleDecision") == {"eeArchitectureDecision"}
    assert _declared("IncrementScope") == {"eeArchitectureScope"}, "exactly one scope"
    assert re.search(
        r"dependency\s+scopeToEEArchitectureQuestion\s+from\s+eeArchitectureScope\s+to\s+eeArchitectureQuestion\s*;",
        code)
    assert re.search(
        r"dependency\s+eeArchitectureQuestionToProblem\s+from\s+eeArchitectureQuestion\s+to\s+eeArchitectureProblem"
        r"\s*;", code)

    charter = braced_body(code, "part eeArchitectureCharter : IncrementCharter")
    assert "ref part :>> increment = eeArchitectureIncrement;" in charter
    assert "ref part :>> systemOfInterest = eeVehicleNetworkSystem;" in charter
    assert 'attribute :>> owner = "Orkun Yilmaz";' in charter
    assert re.findall(r"MethodPhase::(\w+)", charter) == [
        "phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
        "phase3_capabilityClassification", "phase4_needs", "phase5_requirements",
        "phase6_functionalArchitecture", "phase7_logicalArchitecture",
        "phase8_physicalRealization", "phase9_variabilityConfiguration",
        "phase10_vvEvidence", "phase11_baseline",
    ]
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1)) == [PACKAGE], \
        "the charter names only the package that holds content today"
    evidence = re.search(r"expectedReviewEvidence\s*=\s*\((.*?)\);", charter, re.S)
    assert evidence and re.findall(r'"([^"]+)"', evidence.group(1)) == [
        "owner confirmation of the engineering question and the scope",
        "independent review of the System 1 and System 2 boundary and the nonclaims",
        "repository, smoke and focused regression checks on the reviewed changes",
        "exact-head licensed SysML validation and Syside-generated framing view",
    ]
    assert "part eeVehicleNetworkSystem : EEVehicleNetworkSystem;" in code
    assert "part eeVerificationEnvironment : System2EngineeringAndAssuranceSystem" in code


def test_the_question_the_decision_and_the_boundary_say_what_was_agreed():
    increment = _doc(f"part <'{IDENTITY}'> eeArchitectureIncrement : EEArchitectureIncrement")
    for phrase in ("Owner-requested increment on the electrical/electronic (E/E) architecture of the product line: "
                   "the vehicle network between the central computer and the actuators.",
                   *PHASES_BEFORE_BASELINE,
                   "This framing changes neither the platform stack, the governed product-line scope nor another "
                   "increment.",
                   "This package holds Phase 0 and the Phase 1 concerns."):
        assert phrase in increment, phrase
    assert "Its later phases depend on" not in increment, \
        "the decision of 2026-11-18 narrows what waits for the baseline"
    problem = _doc("requirement eeArchitectureProblem : ProblemStatement")
    for phrase in ("The model describes one SoC as the compute of a member product and names the vehicle network "
                   "only as a boundary.",
                   "The platform stack describes one SoC with a main side and an optional guest side, and keeps "
                   "abstract its hardware layer, which names SoC, MCU, sensors and actuators.",
                   "The boundary model of the AAOS SDV middleware gives the vehicle network two Ethernet ports; its "
                   "text names a VLAN-capable switch, an optional DMZ, a telematics control unit and legacy ECUs, "
                   "and models none of them, nor any zone, bus or route.",
                   "The hand-off from the vehicle interface to the brake ECU is a recorded open obligation of the "
                   "AEBS realization.",
                   "In the benches the actuation is a simulator or a simulator client on a bench host, not an ECU; "
                   "in the driving benches it is an actuation adapter on the host that runs Eclipse S-CORE.",
                   "Nothing in the model says how a command reaches an actuator across a vehicle network, or what "
                   "happens when that network fails."):
        assert phrase in problem, phrase
    question = _doc("part eeArchitectureQuestion : IncrementEngineeringQuestion")
    for phrase in ("When the actuation is an ECU on a CAN bus at the edge of a zonal vehicle network, does the path "
                   "of the driving command keep, across that network, the properties that the model asks of the "
                   "command paths of earlier increments,",
                   "on each of two routes: through the Ethernet backbone and a zone controller, and over a direct "
                   "link from the central computer?",
                   "a command whose loss, delay, repetition or corruption the actuation can detect, which "
                   "REQ-DRIVING-039 asks on the Eclipse S-CORE path;",
                   "a stop response when no valid command has reached the actuation for 200 ms of simulation time, "
                   "which REQ-DRIVING-028 asks of the closed-loop driving system;",
                   "no uncontrolled emergency intervention command from a failure of the non-safety middleware "
                   "integration path, which REQ-MW-006 asks of each member product.",
                   "For the driving command, the driver-assistance increment places a share of that requirement at "
                   "the actuation: to apply no command that the actuation rejects.",
                   "The model asks none of these properties of a vehicle network.",
                   "Phase 5 derives the requirements of this increment from them.",
                   "A verdict for each requirement of the increment on each route, on a virtual vehicle, answers "
                   "this.",
                   "A run in which commands arrive does not."):
        assert phrase in question, phrase
    assert question.count("?") == 1, "an increment answers one engineering question"
    assert not re.search(r"(?i)\balready\b|\bstill\b", question), \
        "the question does not say that the model asks these properties of this path today"
    decision = _doc("part eeArchitectureDecision : IncrementLifecycleDecision")
    for phrase in ("whether the product line admits this zonal vehicle network, with the route that the driving "
                   "command takes, as its reference vehicle network, from which later topologies vary, admits it "
                   "with named changes, or does not admit it.",
                   "executed cases with a pass or a fail for each requirement of the increment on each route.",
                   "A fail is a result to record.",
                   "no reason to change a scenario or a criterion until the network passes"):
        assert phrase in decision, phrase
    system = _doc("part def EEVehicleNetworkSystem")
    # the sentences that state the boundary are pinned whole: one more item inside is a change of the boundary
    for phrase in ("Candidate System 1 boundary. In: the driving command of the driver-assistance increment, which "
                   "its source on the central computer gives. Inside: the vehicle network of one topology, with the "
                   "network side of the central computer, one Ethernet backbone, two zone controllers that act as "
                   "gateways between the backbone and CAN, a CAN bus in each zone, and a direct link from the "
                   "central computer to the actuation ECU that passes no zone controller, as the other route; and "
                   "an actuation ECU on CAN that receives the command and acts on it. Out: the command that the "
                   "actuation ECU applies.",
                   "Phases 6 to 8 decide the realization, with the medium of the direct link.",
                   "Two parts of System 1 are outside this boundary, and neither is an enabling system: the source "
                   "of the driving command on the central computer, and the Eclipse S-CORE path that carries the "
                   "command to the vehicle network.",
                   "this increment admits no member to the governed product-line scope."):
        assert phrase in system, phrase
    environment = _doc("part eeVerificationEnvironment : System2EngineeringAndAssuranceSystem")
    for phrase in ("A software testbed stands for the vehicle network:",
                   "replays a recorded stream of driving commands into the Eclipse S-CORE path on the central "
                   "computer,",
                   "takes links down and makes commands get lost, delayed, repeated or corrupted, models the "
                   "vehicle that the actuation ECU drives, and records what reaches each node.",
                   "The testbed with its model of the vehicle is the virtual vehicle of this increment.",
                   "They are not vehicle features and not contents of the System 1 boundary.",
                   "The testbed is chosen after a readiness probe; this framing selects none."):
        assert phrase in environment, phrase
    assert "one host" not in environment, "the framing selects no testbed, so it fixes no count of hosts"
    boundary = _doc("concern eeArchitectureBoundary : IncrementBoundaryConcern")
    for phrase in ("need the framing proposal kept distinct from realized, tested or accepted scope",
                   "the verdicts of Phase 10, which hold what reaches the actuation against what the requirements "
                   "ask, kept distinct from a run of the network that only looks right"):
        assert phrase in boundary, phrase


def test_the_requirements_that_the_framing_names_say_what_it_relies_on():
    question = _doc("part eeArchitectureQuestion : IncrementEngineeringQuestion")
    named = re.findall(r"REQ-[A-Z]+-\d{3}", question)
    assert named == list(CITED_REQUIREMENTS), "the question names the three requirements, in this order"
    for identity, (path, element, statement) in CITED_REQUIREMENTS.items():
        text = path.read_text(encoding="utf-8")
        body = _flat(braced_body(text, f"requirement {element} :")) if identity == "REQ-MW-006" else _flat(
            braced_body(text, f"requirement <'{identity}'> {element} :"))
        assert statement in body, identity
        if identity == "REQ-MW-006":
            assert "REQ-MW-006" in body and "GAP-MW-029" in body
    # what the question says about who is asked: the subject of each requirement
    closed_loop = CLOSED_LOOP_REQUIREMENTS.read_text(encoding="utf-8")
    assert "subject drivingSystem :> DE4SDV_ClosedLoopDrivingFraming::candidateDrivingSystem;" in braced_body(
        closed_loop, "requirement <'REQ-DRIVING-028'> reqStopOnLostCommands :")
    middleware = braced_body(MIDDLEWARE_REQUIREMENTS.read_text(encoding="utf-8"), "requirement reqIsolateSafetyPath :")
    assert "subject memberProduct : ProductLineMemberProduct;" in middleware
    # the share of REQ-MW-006 that the question names for the driving command
    detectable = _flat(braced_body(DRIVER_ASSISTANCE_REQUIREMENTS.read_text(encoding="utf-8"),
                                   "requirement <'REQ-DRIVING-039'> reqDetectableDrivingCommand :"))
    assert "rejecting what the actuation detects is the share of the product that holds the path, under REQ-MW-006" \
        in detectable
    assert "the share of REQ-MW-006 placed here is not applying the rejected command" in _flat(
        DRIVER_ASSISTANCE_REALIZATION.read_text(encoding="utf-8").replace("*", ""))
    assert "Each SDV product-line member product shall prevent" in _flat(middleware)
    assert "deferred to INC-MW-005" in _flat(MIDDLEWARE_NEEDS.read_text(encoding="utf-8").replace("*", ""))
    assert "GAP-MW-029: The isolation criteria and failure-containment expectations" in _flat(
        MIDDLEWARE_NEEDS.read_text(encoding="utf-8").replace("*", ""))


def test_the_system_definition_declares_nothing_and_system_2_is_one_part_beside_it():
    code = _code()
    assert braced_body(code, "part def EEVehicleNetworkSystem").split() == ["doc"], \
        "phase 0 states the boundary in words; its parts and ports follow in phases 2 and 3"
    assert _declared("System2EngineeringAndAssuranceSystem") == {"eeVerificationEnvironment"}
    assert re.search(r"(?m)^  part eeVerificationEnvironment : System2EngineeringAndAssuranceSystem\b", code), \
        "the enabling system is a part of the package, not of the vehicle network"
    assert _declared("EEVehicleNetworkSystem") == {"eeVehicleNetworkSystem"}


def test_scope_items_are_the_agreed_closed_sets():
    code = _code()
    assert _declared("InScopeItem") == set(IN_SCOPE)
    assert _declared("OutOfScopeItem") == set(OUT_OF_SCOPE)
    for name, statement in IN_SCOPE.items():
        assert _doc(f"part {name} : InScopeItem") == statement, name
    for name, statement in OUT_OF_SCOPE.items():
        assert _doc(f"part {name} : OutOfScopeItem") == statement, name
    scope_body = braced_body(code, "part eeArchitectureScope : IncrementScope")
    assert "InScopeItem" not in scope_body and "OutOfScopeItem" not in scope_body, \
        "scope items are package-level parts: a nested item is not in the scope gate's population"
    scope = _doc("part eeArchitectureScope : IncrementScope")
    for phrase in ("Whether the path of the driving command keeps, across a zonal vehicle network, the properties "
                   "that the model asks of the command paths of earlier increments, on each of two routes:",
                   "one topology that holds both routes, with one central computer, two zone controllers and one "
                   "Ethernet backbone,",
                   "one flow, the driving command down to the actuation ECU,",
                   "for one configuration and with at most ten requirements",
                   "Phase 5 derives those requirements from the needs of Phase 4 and from REQ-DRIVING-028, "
                   "REQ-DRIVING-039 and REQ-MW-006.",
                   "The evidence comes from the replay of a recorded command stream on a virtual vehicle, in Phase "
                   "10 of this same increment.",
                   "A time limit of a requirement counts on the clock of the virtual vehicle, and a verdict on it "
                   "is no timing claim for a vehicle network.",
                   "A readiness probe comes before the architecture rests on what it tests.",
                   "Implementation is not part of this framing slice."):
        assert phrase in scope, phrase
    # the owner decided on 2026-11-18 that the increment carries the driving command only; the speed is out of scope
    carried = {"the scope": scope, "the System 1 boundary": _doc("part def EEVehicleNetworkSystem")}
    carried.update({name: _doc(f"part {name} : InScopeItem") for name in IN_SCOPE})
    assert not [name for name, text in carried.items() if re.search(r"(?i)\bspeeds?\b", text)], \
        "the increment carries no vehicle speed"


def test_assumptions_are_premises_and_gaps_are_open_points():
    code = _code()
    assert _declared("IncrementAssumption") == set(ASSUMPTIONS)
    assert _declared("IncrementGap") == set(GAPS)
    for name, phrases in ASSUMPTIONS.items():
        for phrase in phrases:
            assert phrase in _doc(f"part {name} : IncrementAssumption"), (name, phrase)
    for name, phrase in GAPS.items():
        assert phrase in _doc(f"part {name} : IncrementGap"), name
    assert "disposition" not in code, "a gap has no disposition before the baseline decision of phase 11"
    assert _doc("part asmEECommandFromDrivingBaseline : IncrementAssumption") == " ".join(
        ASSUMPTIONS["asmEECommandFromDrivingBaseline"]), "the assumption is the premise only, no plan of phases"
    assert _doc("part asmEEScoreCommandSource : IncrementAssumption") == " ".join(
        ASSUMPTIONS["asmEEScoreCommandSource"]), "the premise, the probe that tests it and the owner's fallback"
    route = _doc("part gapEEZoneRouteInVehicles : IncrementGap")
    for phrase in ("The public sources in the folder's upstream record describe zone controllers as gateways or "
                   "aggregators of input and output between the central computer and the sensors and actuators of "
                   "their zone.",
                   "None of them shows a production vehicle whose brake command takes a route through a zone "
                   "controller: one plans braking among the systems on the Ethernet backbone of a central "
                   "architecture for 2028, one places the brake actuators apart from the zone controllers, and one "
                   "says that the move of chassis control into the zones may need more time.",
                   "So this increment judges that route and a direct link from the central computer, and takes "
                   "neither as given."):
        assert phrase in route, phrase
    assert not re.search(r"(?i)\bunverified\b|\bassum", route), "what the sources leave open is a gap, not a premise"

    safety = _doc("part gapEESafetyPathArchitecture : IncrementGap")
    for phrase in ("REQ-MW-006 asks each member product to keep a failure of the non-safety middleware integration "
                   "path from causing an uncontrolled emergency intervention command, by a middleware partition "
                   "with a safety certification or by a direct vehicle-command path, and leaves that choice and its "
                   "containment criteria open per GAP-MW-029.",
                   "That direct path keeps the AEBS emergency intervention command around the middleware, from the "
                   "AEB node to the vehicle command gate on the Linux host (ASM-MW-003, ASM-MW-028, REQ-MW-017).",
                   "It is not one of the routes that this increment judges, and this increment does not carry that "
                   "AEBS command.",
                   "The routes that this increment judges lie after the middleware.",
                   "The containment criteria stay open, and this increment makes no freedom-from-interference "
                   "claim."):
        assert phrase in safety, phrase
    assert not re.search(r"(?i)\bsettle", safety), "this increment does not claim to settle the choice of REQ-MW-006"
    assert "network route" not in safety, \
        "the model does not say whether the hop after the vehicle command gate crosses a vehicle network"
    score_requirements = MIDDLEWARE_SCORE_REQUIREMENTS.read_text(encoding="utf-8")
    no_emergency = _flat(braced_body(score_requirements, "requirement <'REQ-MW-017'> reqNoEmergencyCommandOnMiddleware :"))
    assert "The middleware integration layer shall carry no AEBS emergency intervention command." in no_emergency
    assert "refines the direct vehicle-command path option of REQ-MW-006" in no_emergency
    assert "The command keeps its direct path from the AEB node to the vehicle command gate on the Linux host." in \
        no_emergency
    boundary_text = _flat(MIDDLEWARE_BOUNDARY.read_text(encoding="utf-8").replace("*", ""))
    assert "ASM-MW-003" in boundary_text and "does NOT go through the adapter or the middleware." in boundary_text
    assert "(AEB node -> emergency intervention request -> vehicle command gate -> brake actuation)" in boundary_text
    assert "ASM-MW-028: The AEBS emergency intervention command path stays inside the Linux host" in _flat(
        MIDDLEWARE_SCORE_FRAMING.read_text(encoding="utf-8").replace("*", ""))

    actuation = _doc("part gapEEActuationEnd : IncrementGap")
    for phrase in ("In the driving benches the actuation end is an actuation adapter on the host that runs Eclipse "
                   "S-CORE.",
                   "The adapter of the closed-loop driving increment applies the stop response of REQ-DRIVING-028.",
                   "The adapter of the driver-assistance increment rejects a command whose sequence count, check "
                   "value or issue time fails, and has no stop response.",
                   "It turns an accepted command into the simulator's control by a rule that takes the speed of the "
                   "ego vehicle from the newest world snapshot (MAP-DRIVING-DA-COMMAND).",
                   "This increment puts the actuation in an ECU on CAN.",
                   "Which element then holds each of these duties,",
                   "where the actuation end takes a vehicle speed if its conversion of the command needs one,",
                   "whether the driving command with its issue time, sequence count and check value fits a CAN "
                   "frame,",
                   "whether a zone controller that repacks the command from Ethernet to CAN keeps the detection end "
                   "to end, is open.",
                   "This framing changes neither adapter."):
        assert phrase in actuation, phrase
    assistance = _flat(DRIVER_ASSISTANCE_REALIZATION.read_text(encoding="utf-8").replace("*", ""))
    for phrase in ("It has no stop response of its own.",
                   "no requirement of this increment asks for a stop response",
                   # the three fields the gap names, in the adapter's order (the adapter counting decision of
                   # 2026-11-18)
                   "The adapter checks the check value first, then the sequence count, then the issue time.",
                   "A command whose check value fails is rejected (a corruption)",
                   # the speed at the actuation end that the gap names
                   "An accepted command becomes the simulator's Ackermann control by the rule of "
                   "MAP-DRIVING-DA-COMMAND. Its simulator client takes the simulation time and the speed of the ego "
                   "vehicle from the newest world snapshot"):
        assert phrase in assistance, phrase
    payload = braced_body(strip_comments(DRIVER_ASSISTANCE_REALIZATION.read_text(encoding="utf-8")),
                          "item def DrivingCommandEventPayload :> DrivingCommand")
    assert re.findall(r"\battribute\s+(\w+)\s*:", payload) == [
        "acceleration", "steeringAngle", "issueTime", "sequenceCount", "checkValue"]
    assert "REQ-DRIVING-028 counts its 200 ms on this clock at the actuation adapter." in _flat(
        CLOSED_LOOP_REALIZATION.read_text(encoding="utf-8").replace("*", ""))

    handoff = _doc("part gapEEBrakeHandoff : IncrementGap")
    for phrase in ("records the hand-off from the vehicle interface to the brake ECU and actuator as an open "
                   "integration obligation, and deferred the boundary of the brake ECU and actuator to "
                   "INC-AEBS-008.",
                   "INC-AEBS-008, the AEBS simulation deployment, uses a vehicle-dynamics test double and makes no "
                   "brake ECU or actuator claim, so the obligation stays open.",
                   "This increment carries the driving command of the driver-assistance increment to an actuation "
                   "ECU on CAN, not an AEBS command.",
                   "Whether a result of this increment meets that obligation for the AEBS is open, and this "
                   "increment does not decide it."):
        assert phrase in handoff, phrase
    aebs = _flat(AEBS_REALIZATION.read_text(encoding="utf-8").replace("*", ""))
    assert "Required brake-controller and physical actuator boundary; deferred to INC-AEBS-008." in aebs
    assert "It is an integration obligation for a later member-product realization" in aebs
    deployment = _flat(AEBS_SIMULATION_DEPLOYMENT.read_text(encoding="utf-8").replace("*", ""))
    assert "INC-AEBS-008 simulation-only deployment" in deployment
    assert "It is a vehicle-dynamics test double, not a brake ECU, actuator, vehicle interface, or HardwareLayer " \
           "member." in deployment

    stack = _doc("part gapEEStackAndNetworkBoundary : IncrementGap")
    for phrase in ("The platform stack describes one SoC and keeps its hardware layer abstract,",
                   "the execution-environment shared asset and its feature model describe one vehicle compute "
                   "target, with an NXP and Zephyr candidate,",
                   "VehicleNetworkBoundary of the AAOS SDV middleware boundary holds two Ethernet ports and no "
                   "part.",
                   "This framing changes none of them."):
        assert phrase in stack, phrase
    environments = _flat(EXECUTION_ENVIRONMENTS.read_text(encoding="utf-8").replace("*", ""))
    assert "Reusable execution-environment shared asset" in environments
    assert "Configurable System 1 vehicle compute target." in environments
    vehicle_targets = (FEATURE_MODELS / "vehicle_execution_environments.sysml").read_text(encoding="utf-8")
    assert "<'F-VEHICLE-COMPUTE-NXP-CANDIDATE'>" in vehicle_targets and "<'F-VEHICLE-OS-ZEPHYR-CANDIDATE'>" in \
        vehicle_targets
    platform = _flat(PLATFORM_STACK.read_text(encoding="utf-8").replace("*", ""))
    assert "One SoC has a main side and an optional guest side." in platform
    assert "Physical compute hardware: SoC, MCU, sensors, actuators." in platform
    assert "This layer is deliberately abstract; concrete hardware modeling is out of scope" in platform
    network = braced_body(strip_comments(MIDDLEWARE_BOUNDARY.read_text(encoding="utf-8")),
                          "part def VehicleNetworkBoundary")
    assert re.findall(r"\bport\s+\w+\s*:\s*(\w+)\s*;", network) == ["EthernetTransport", "EthernetTransport"]
    assert not re.search(r"\bpart\b", network), "the boundary declares no part"
    for phrase in ("VLAN-capable Ethernet switch", "Optional DMZ", "Telematics control unit (TCU)", "legacy ECUs"):
        assert phrase in boundary_text, phrase
    product_line = _doc("part gapEENetworkInProductLine : IncrementGap")
    for phrase in ("This increment admits no member and changes no scope decision.",
                   "Phase 3 classifies the vehicle network against the scope as it then stands."):
        assert phrase in product_line, phrase
    # no model of the product line holds an element for a vehicle network, a zone, a bus or an ECU
    swept = sorted(PRODUCT_LINE.rglob("*.sysml"))
    assert len(swept) >= 10, "the sweep must cover the scoping, the feature models and the product models"
    for path in swept:
        assert not re.search(r"(?i)\b(?:vehicle ?network|zonal|zone|CAN bus|ethernet|ECUs?\b|gateway|backbone)",
                             path.read_text(encoding="utf-8")), path.relative_to(ROOT).as_posix()
    bench = _doc("part gapEEBenchPlatform : IncrementGap")
    for phrase in ("No bench of the repository runs a vehicle network with zone controllers, a backbone or CAN; the "
                   "driving benches carry the vehicle control and the speed between hosts over a bench network.",
                   "Its readiness probe, its cost, its host and whether it runs on one host are open."):
        assert phrase in bench, phrase
    stream = _doc("part gapEERecordedCommandStream : IncrementGap")
    assert "in the form that the driver-assistance increment fixes" in stream
    assert "how the stream is bound to the revision that made it, is open." in stream


def test_the_framing_view_frames_the_boundary_and_exposes_every_usage():
    code = _code()
    boundary = braced_body(code, "concern eeArchitectureBoundary : IncrementBoundaryConcern")
    lines = [line.strip() for line in boundary.splitlines() if line.strip()]
    assert lines[0] == "subject increment : EEArchitectureIncrement;"
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", boundary) == ["SystemsEngineer", "VerificationEngineer"]
    assert dict(re.findall(r"\bconcern\s+(\w+)\s*:\s*(\w+)\s*\{", code)) == {
        "eeArchitectureBoundary": "IncrementBoundaryConcern",
        **{name: spec[0] for name, spec in PHASE1_CONCERNS.items()}}, \
        "the boundary concern of Phase 0 and the concerns of Phase 1, no other"

    view = braced_body(code, "view eeArchitectureFramingView")
    viewpoint = braced_body(view, "viewpoint eeArchitectureFramingViewpoint : IncrementFramingViewpoint")
    frames = re.findall(r"\bframe\s+(\w+)\s*;", viewpoint)
    assert frames[0] == "eeArchitectureBoundary" and sorted(frames[1:]) == sorted(PHASE1_CONCERNS) \
        and len(frames) == len(set(frames)), "the one framing viewpoint frames every concern of the increment once"
    assert "render asTreeDiagram;" in view
    exposed = re.findall(r"\bexpose\s+(\w+)\s*;", view)
    assert len(exposed) == len(set(exposed)), "an element is exposed once"

    usages = {name for _kind, name, _type in PACKAGE_USAGE.findall(code)}
    kinds = {kind for _kind, _name, kind in PACKAGE_USAGE.findall(code)}
    assert len(usages) >= 30, "the population of the exposure check must not be vacuous"
    assert {"InScopeItem", "OutOfScopeItem", "IncrementAssumption", "IncrementGap", "IncrementCharter",
            "IncrementScope", "ProblemStatement", "IncrementBoundaryConcern"} <= kinds
    assert set(PHASE1_CONCERNS) <= set(exposed), "the framing view shows every Phase 1 concern"
    assert set(exposed) == usages | {"EEArchitectureIncrement"}, \
        f"not exposed: {sorted(usages - set(exposed))}; exposed and not declared: {sorted(set(exposed) - usages)}"


def test_the_framing_claims_no_verification_no_admission_and_no_compliance():
    raw = _raw()
    code = _code()
    assert not re.search(r"\b(?:verify|satisfy)\s+\w+", code)
    assert not re.search(r"\bverification\b", code)
    assert "ProductLineMemberProduct" not in raw, "the vehicle network is not typed as a member product"
    # raw source: a claim hidden in a comment is still a claim a reader sees
    assert not APPROVAL.search(raw)
    header = raw.split("package", 1)[0]
    for phrase in ("Phase 0 framing and the Phase 1 concerns only", "no implementation", "no runtime result",
                   "no product-line", "no compliance"):
        assert phrase in _flat(header.replace("*", "")), phrase
    for word in ("compliance", "type approval", "certification", "safety argument", "freedom from interference"):
        assert word in OUT_OF_SCOPE["eeSafetyClaimOutOfScope"], word
    # a framing states what holds, not a moment: such a word is stale after the next merge
    dated = re.findall(r"(?i)\b(?:already|still|yet|today|currently|settled?)\b", raw)
    assert not dated, f"the model text is bound to a moment or names a settlement: {dated}"


def test_no_text_of_the_framing_reports_a_run_an_approval_or_an_admission():
    texts = {
        MODEL.name: _raw(),
        GUIDE.name: GUIDE.read_text(encoding="utf-8"),
        "upstream record": UPSTREAM_RECORD.read_text(encoding="utf-8"),
    }
    for first_cell in GLOSSARY_ROWS:
        texts[f"glossary row {first_cell}"] = _row(GLOSSARY, first_cell)
    for name, text in texts.items():
        assert not PAST_BEHAVIOR.findall(text), f"{name} reports behavior in a run: {PAST_BEHAVIOR.findall(text)}"
        assert not APPROVAL.findall(text), f"{name}: {APPROVAL.findall(text)}"
    for first_cell, sentence in GLOSSARY_ROWS.items():
        assert sentence in texts[f"glossary row {first_cell}"], first_cell
    assert "(../guides/ee-architecture-increment.md)" in texts["glossary row E/E architecture |"]
    assert "In a zonal E/E architecture the vehicle network joins" in texts["glossary row E/E architecture |"], \
        "the row describes a zonal architecture as one kind, not as every E/E architecture"
    assert "(../../textual-notation-of-model/packages/features/ee/upstream.md#zone-controller-route)" in \
        texts["glossary row Zone controller |"]


def test_the_identity_is_declared_once_and_its_subject_is_registered():
    declarations = []
    for root in MODEL_ROOTS:
        for path in root.rglob("*.sysml"):
            if f"<'{IDENTITY}'>" in path.read_text(encoding="utf-8"):
                declarations.append(path.relative_to(ROOT).as_posix())
    assert declarations == [MODEL.relative_to(ROOT).as_posix()]
    assert _raw().count(f"<'{IDENTITY}'>") == 1
    assert IDENTITY.split("-")[1] in check_naming.REGISTERED_SUBJECTS
    naming_row = _row(NAMING, "`EE` |")
    for phrase in ("| E/E architecture |",
                   "The vehicle network between the central computer and the actuators",
                   "Registration allocates identities, not product-line admission or production readiness."):
        assert phrase in naming_row, phrase
    assert check_naming.check_identifier_tokens_in_text(_raw(), display_path=MODEL.name, suffix=".sysml") == []


def test_the_package_declares_no_name_that_another_model_package_declares():
    # Two packages may declare the same name, but a lookup by name then finds two elements, and a check that
    # reads a folder by name sees one increment's element as the other's.
    kinds = r"(?:part def|part|requirement def|requirement|concern def|concern|view def|view|dependency)"
    declared = set(re.findall(rf"(?m)^  {kinds}\s+(?:<'[^']*'>\s*)?(\w+)", _code()))
    assert len(declared) >= 35, "the population of the check must not be vacuous"
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


def test_the_guide_states_the_models_question_and_scope_and_no_more():
    guide = GUIDE.read_text(encoding="utf-8")
    assert "**Status: Phase 0 framing and Phase 1 concerns, proposal.**" in guide
    quoted = _flat(" ".join(line[1:].strip() for line in guide.splitlines() if line.startswith(">")))
    assert quoted == _doc("part eeArchitectureQuestion : IncrementEngineeringQuestion"), \
        "the guide quotes the model's engineering question word for word"
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in guide.split("## What the increment judges", 1)[1].split("\n\n", 2)[1].splitlines()]
    assert rows[0] == ["In scope", "Out of scope"]
    cells_in = [row[0] for row in rows[2:] if row[0]]
    cells_out = [row[1] for row in rows[2:] if row[1]]
    assert cells_in == list(IN_SCOPE.values()), "the table's in-scope column is the model's in-scope items"
    assert cells_out == list(OUT_OF_SCOPE.values()), "the table's out-of-scope column is the model's items"
    for target in ("../../textual-notation-of-model/packages/features/ee/ee_architecture_framing.sysml",
                   "../../textual-notation-of-model/packages/features/ee/VIEWS.md",
                   "../../textual-notation-of-model/packages/features/ee/upstream.md",
                   "../../textual-notation-of-model/packages/features/ee/upstream.md#zone-controller-route",
                   "driver-assistance-increment.md",
                   "closed-loop-driving-increment.md",
                   "../../textual-notation-of-model/packages/features/middleware/middleware_requirements.sysml"):
        assert f"]({target})" in guide, target
    first = guide.split("\n## ", 1)[0]
    assert "electrical/electronic (E/E) architecture" in _flat(first), "the guide spells the term out on first use"
    intro = _flat(first.split("\n\n", 2)[1])
    assert intro == (
        "The model of the product line describes one SoC as the compute of a member product. The platform stack "
        "describes that SoC with a main side and an optional guest side, and the model names the vehicle network "
        "only as a boundary. It does not say how a driving command leaves that computer and reaches an actuator "
        "across a vehicle network, nor what happens when that network fails. This increment frames a first part of "
        "the electrical/electronic (E/E) architecture of the product line, its vehicle network: one central "
        "computer, two zone controllers, an Ethernet backbone and CAN at the edge. It asks whether the path of a "
        "driving command keeps, across that network, the properties that the model asks of the command paths of "
        "earlier increments. It judges two routes: through a zone controller, and over a direct link."), \
        "the guide's opening says what the model's problem statement and question say, and no more"
    assert "The framing's boundary concern does not open Phase 1." not in _flat(guide) and \
        "**Phase 1 concern framing**" not in guide and "The later phases of this increment depend on" not in \
        _flat(guide), "Phase 1 is framed: the guide names the next obligation and what waits for the baseline"
    assert not re.search(r"(?i)\balready requires\b|\bunder the platform stack\b", guide), \
        "the guide claims neither that the model asks these properties of this path nor a new layering"
    flat = _flat(guide)
    for phrase in ("No implementation, run, result, product-line admission or compliance is claimed.",
                   "It takes the driving command as that increment fixes it and changes none of its criteria or "
                   "verdicts.",
                   "A fail is a result to record.",
                   "Starting this increment launches no compute and authorizes no spend.",
                   "The next model obligation is **Phase 2**, the operational context: exactly one context holding "
                   "the vehicle network, with a story whose use cases bind it and the context actors.",
                   "The owner decided on 2026-11-18 to carry out Phases 1 to 3 of this increment before the "
                   "baseline of the driver-assistance increment, whose driving command it carries.",
                   "Phase 4 onward and the testbed with its readiness probe wait for that baseline and for a "
                   "further decision of the owner.",
                   "open gaps and Phase 1 concerns.",
                   "None of them asks these properties of a vehicle network; Phase 5 of this increment derives its "
                   "own requirements from them."):
        assert phrase in flat, phrase
    decision = _doc("part eeArchitectureDecision : IncrementLifecycleDecision")
    assert decision.startswith("Decide whether the product line admits ")
    assert "The increment supports one decision: " + decision[len("Decide "):] in flat, \
        "the guide states the model's lifecycle decision word for word"
    boundaries = _flat(guide.split("## Boundaries", 1)[1].split("\n## ", 1)[0])
    for phrase in ("The vehicle network of one topology is a proposed **System 1** subject",
                   "Two parts of **System 1** are outside its boundary, and neither is an enabler: the source of "
                   "the driving command on the central computer, and the Eclipse S-CORE path that carries the "
                   "command to the vehicle network.",
                   "are **System 2** enablers, not vehicle features.",
                   "The testbed with its model of the vehicle is the virtual vehicle of this increment.",
                   "It is no safety argument: whether a verdict of this increment bears on the choice of the "
                   "safety-path architecture is open, and the containment criteria and any "
                   "freedom-from-interference claim stay open."):
        assert phrase in boundaries, phrase
    assert not re.search(r"(?i)\bsettle|\binform the choice", boundaries), \
        "the guide claims no more for the safety path than the model's gap"
    assert not re.search(r"(?i)\bspeeds?\b", boundaries), "the guide's System 1 subject carries no vehicle speed"
    assert boundaries.count("**System 1**") == 2 and boundaries.count("**System 2**") == 1


def test_the_guide_lists_each_gap_as_an_open_point_in_the_models_own_words():
    order = re.findall(r"\bpart\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*IncrementGap\b", _code())
    assert order == list(OPEN_POINTS) == list(GAPS), "one open point for each gap, in the model's order"
    guide = GUIDE.read_text(encoding="utf-8")
    open_points = guide.split("## What the framing already records as open", 1)[1].split("\n## ", 1)[0]
    bullets = re.findall(r"(?ms)^- \*\*(.+?)\*\*\s+\(`(\w+)`\)\.\s+(.*?)(?=^- \*\*|\n\n)", open_points)
    assert len(re.findall(r"(?m)^- ", open_points)) == len(bullets), "every bullet has a label and names its gap"
    assert [(name, label) for label, name, _body in bullets] == list(OPEN_POINTS.items())
    for _label, name, body in bullets:
        assert len(body.split()) >= 8, f"{name}: an open point says what is open"
        assert _flat(body) in _doc(f"part {name} : IncrementGap"), \
            f"{name}: the open point is not a passage of the gap's own text"


def test_the_upstream_record_holds_the_sources_of_the_route_gap():
    record = UPSTREAM_RECORD.read_text(encoding="utf-8")
    assert record.startswith("# E/E architecture: upstream provenance\n")
    assert [line[3:] for line in record.splitlines() if line.startswith("## ")] == [
        "Zone controller route", "Command source", "Upstream contact"]
    intro = _flat(record.split("\n## ", 1)[0])
    for phrase in ("read for its gap on the zone controller route.",
                   "No upstream implementation is vendored.",
                   "For this increment DE4SDV has built and run nothing."):
        assert phrase in intro, phrase
    route = _record_section(record, "Zone controller route")
    links = re.findall(r"\]\((https://[^)\s]+)\)", route)
    assert links == [
        "https://www.aumovio.com/en/solutions/vehicle-e-e-architectures/server-zone-architecture/"
        "zone-control-units.html",
        "https://www.ti.com/lit/pdf/spry345",
        "https://standards.ieee.org/wp-content/uploads/import/documents/other/eipatd-presentations/2021/d1-15.pdf",
        "https://engineering.gm.com/home.detail.html/Pages/news/us/en/engineering/2026/jul/"
        "0722-ethernet-backbone-reshapes-vehicle-architecture.html",
    ], "the four public sources read on the day of the framing"
    text = _link_text(route)
    assert "the gap `gapEEZoneRouteInVehicles` of the framing model" in text
    entries = [_flat(entry) for entry in re.split(r"(?m)^- ", route)[1:]]
    assert len(entries) == 4, "one entry for each source"
    #: source -> what the entry says the source is, what it quotes, and what it supports or weighs against
    expected = (
        ("a supplier's product page.",
         "\"Local gateway within a physical zone with Ethernet backbone connection to vehicle server (HPC)\"",
         "lists suspension, a chassis function, among the real-time functions that such units run.",
         "\"Ability to host critical x-Domain real-time functions\"",
         "\"safety levels up to ASIL C and in future ASIL D\"",
         "Does not support: a brake command on that route."),
        ("revision C (the document carries a copyright of 2024).",
         "a zonal module has peripherals such as CAN FD or LIN to reach smart sensors and actuators.",
         "It gives powertrain and chassis control stricter latency targets than audio,",
         "\"Transitioning of ADAS or power train and chassis control into the zone architecture may need more "
         "time.\"",
         "Supports: the topology of the increment.",
         "Weighs against: chassis commands on a zone route at the time of the paper."),
        ("slides of an IEEE Standards Association event of November 2021.",
         "\"Currently ALL wheel speed sensors connect DIRECTLY to the ABS/ESP ECU\"",
         "\"Brake Actuators separate from the Zone Controllers\"",
         "Supports: wheel speed pulses on a zone route as a concept, not as practice in vehicles.",
         "Weighs against: the brake command on a zone route."),
        ("a blog post of July 2026.",
         "\"use the network backbone to connect that I/O to compute resources.\"",
         "The post states a plan for a centralized architecture in 2028, first on the Cadillac ESCALADE IQ, not a "
         "vehicle in production.",
         "\"systems including propulsion, steering, braking, infotainment, and safety\"",
         "It does not say whether the brake command passes through a zone controller.",
         "Supports: a central computer that reaches the input and output of its zones over the backbone, and "
         "braking on the backbone as a plan."),
    )
    for entry, phrases in zip(entries, expected):
        for phrase in phrases:
            assert phrase in _link_text(entry), phrase
    closing = _flat(route.rsplit("\n\n", 1)[1])
    assert closing == ("No source read shows a production vehicle whose brake command passes through a zone "
                       "controller. The framing therefore takes that route as a candidate beside a direct link and "
                       "judges both.")
    source = _record_section(record, "Command source")
    assert "(../driving/upstream.md)" in source
    assert "This increment reads no further upstream code for it." in _flat(source)
    contact = _flat(_record_section(record, "Upstream contact"))
    assert contact.startswith("DE4SDV has contacted no author of these sources and no upstream project about this "
                              "increment.")
    exchange = re.compile(r"(?i)\bDE4SDV (?:has )?(?:confirmed|agreed|asked|told|informed|reported|"
                          r"discussed|opened|sent)\b")
    assert not exchange.findall(_flat(record)), exchange.findall(_flat(record))


def _answers(doc: str) -> set[tuple[int, str]]:
    """The (phase, viewpoint definition) pairs that the answer sentences of a concern's doc name."""
    phrases = "|".join(re.escape(phrase) for phrase in VIEW_PHRASES)
    found = set()
    for sentence in ANSWER_SENTENCE.findall(doc):
        pairs = re.findall(rf"\b({phrases}) (?:of|in) phase (\d+)\b", sentence)
        assert pairs, f"an answer that names no view of the method: {sentence.strip()}"
        found.update((int(phase), VIEW_PHRASES[phrase]) for phrase, phase in pairs)
    return found


def _concern_doc(name: str, kind: str) -> str:
    return _doc(f"concern {name} : {kind}")


def test_phase_one_frames_one_concern_for_each_question_of_the_scope():
    code = _code()
    assert "private import SAF_Viewpoints::*;" in code, "the SAF concern definitions come from the catalogue"
    assert not re.search(r"\b(?:concern|viewpoint) def\b", code), \
        "concern types come from the catalogue, never the slice"
    assert re.findall(r"\bpart def (\w+)", code) == ["EEArchitectureIncrement", "EEVehicleNetworkSystem"], \
        "stakeholder roles come from the kernel, never the slice"
    catalogue = SAF_FILE.read_text(encoding="utf-8")
    answered = set()
    for name, (kind, items, holders, sentences, answer) in PHASE1_CONCERNS.items():
        assert len(re.findall(rf"\bconcern def {kind}\b", catalogue)) == 1, \
            f"{name}: {kind} is an SAF concern definition"
        body = braced_body(code, f"concern {name} : {kind}")
        parameters = [line.strip() for line in body.splitlines() if line.strip() and line.strip() != "doc"]
        assert parameters[0] == "subject;", f"{name}: the subject is the first parameter"
        assert re.findall(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;", body) == holders, name
        doc = _concern_doc(name, kind)
        lead = ", ".join(items[:-1]) + (" and " if len(items) > 1 else "") + items[-1]
        lead += ", operational part." if kind == "OperationalCapabilityConcern" else "."
        assert doc.startswith(lead), f"{name}: the doc opens with the in-scope items it answers: {doc[:80]}"
        for sentence in sentences:
            assert sentence in doc, (name, sentence)
        rest = ANSWER_SENTENCE.sub("", doc[len(lead):])
        assert rest.split() == " ".join(sentences).split(), \
            f"{name}: the doc holds only its pinned sentences and its answer"
        assert doc.index(sentences[0]) == len(lead) + 1, f"{name}: the holders' need follows the in-scope items"
        assert _answers(doc) == set(answer), (name, sorted(_answers(doc)))
        answered.update(items)
    in_scope = _declared("InScopeItem")
    assert answered == in_scope, f"in-scope items without a concern: {sorted(in_scope - answered)}"
    # incrementHasNonBoundaryConcern: an SAF definition specializes its domain root, not the boundary concern
    outside = [name for name, (kind, *_rest) in PHASE1_CONCERNS.items()
               if re.search(rf"\bconcern def {kind} :> \w+DomainConcern\s*\{{", catalogue)]
    assert outside == list(PHASE1_CONCERNS), "each Phase 1 concern lies outside the boundary-concern lineage"


def test_every_stakeholder_of_the_problem_holds_a_phase_one_concern_and_the_beneficiaries_hold_their_own():
    # The concerns' holders are the parties whose interest each states: the five roles of the problem statement and
    # the people the vehicle carries and meets. The occupant and the road user hold the operational concern alone.
    code = _code()
    problem = braced_body(code, "requirement eeArchitectureProblem : ProblemStatement")
    roles = set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", problem))
    # the holders as the model declares them, not as this file lists them
    declared = {name: set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;",
                                     braced_body(code, f"concern {name} : {kind}")))
                for name, (kind, *_rest) in PHASE1_CONCERNS.items()}
    held = set().union(*declared.values())
    assert roles <= held, f"problem stakeholders that hold no Phase 1 concern: {sorted(roles - held)}"
    assert held - roles == {"VehicleOccupant", "RoadUser"}, sorted(held - roles)
    beneficiaries = [name for name, holders in declared.items() if {"VehicleOccupant", "RoadUser"} & holders]
    assert beneficiaries == ["eeVehicleCommandConcern"]
    assert declared["eeVehicleCommandConcern"] == {"VehicleOccupant", "RoadUser"}, \
        "the occupants and the road users hold the operational concern alone"
    assert PHASE1_CONCERNS["eeVehicleCommandConcern"][0] == "OperationalCapabilityConcern"
    operational = _concern_doc("eeVehicleCommandConcern", "OperationalCapabilityConcern")
    assert "Reviewers need" not in operational and "engineers" not in operational
    # within the charter: what the occupants and road users expect, with no claim the scope leaves out
    assert not re.search(r"(?i)\b(?:latency|jitter|safe|safely|safer|compliance|reliab\w*|performs?)\b", operational)


def test_the_phase_one_concerns_claim_no_result_and_name_no_unread_record():
    names = set(re.findall(r"\bpart\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*(?:IncrementGap|IncrementAssumption|InScopeItem)\b",
                           _code()))
    for name, (kind, *_rest) in PHASE1_CONCERNS.items():
        doc = _concern_doc(name, kind)
        named = set(re.findall(r"\b((?:gap|asm)[A-Z]\w+|\w+InScope)\b", doc))
        assert named <= names, f"{name} names a record the framing does not declare: {sorted(named - names)}"
        assert not PAST_BEHAVIOR.findall(doc) and not APPROVAL.findall(doc), name
        assert not re.search(r"\b\d+(?:\.\d+)?\s*(?:s|ms|m|km/h|m/s)\b", doc), f"{name}: a criterion value is phase 5's"
        assert not re.search(r"(?i)\b(?:latency|jitter|freedom from interference)\b", doc), \
            f"{name}: the timing of the network and a safety argument are out of scope"
        assert not re.search(r"(?i)\b(?:issue time|sequence count|check value)s?\b", doc), \
            "the form of the command is INC-DRIVING-002's until its baseline"


def _words(name: str) -> str:
    """The words of a CamelCase name, in lower case."""
    return " ".join(re.findall(r"[A-Z][a-z]*", name)).lower()


def _definition_and_holders(name: str) -> str:
    """'Definition; holders.' of a Phase 1 concern, read from its typing and its stakeholder lines in the model.

    Hyphens are spaces here: the guide may write a compound such as product-line with a hyphen.
    """
    code = _code()
    kind = re.search(rf"\bconcern {name}\s*:\s*(\w+)\s*\{{", code).group(1)
    roles = re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", braced_body(code, f"concern {name} : {kind}"))
    definition = _words(kind.removesuffix("Concern")).capitalize()
    return f"{definition}; " + " and ".join(_words(role) + "s" for role in roles) + "."


def test_the_guide_lists_the_phase_one_concerns_with_their_holders():
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.index("## What the increment judges") < guide.index("## Concerns (Phase 1)") \
        < guide.index("## What the framing already records as open")
    section = guide.split("## Concerns (Phase 1)", 1)[1].split("\n## ", 1)[0]
    bullets = re.findall(r"(?ms)^- \*\*([^*]+):\*\* `(\w+)`\.\s+(.*?)(?=^- \*\*|\n\n)", section)
    assert len(re.findall(r"(?m)^- ", section)) == len(bullets), "every bullet has a label and names its concern"
    model_order = re.findall(r"\bconcern\s+(\w+)\s*:", _code())
    assert model_order[0] == "eeArchitectureBoundary" and sorted(model_order[1:]) == sorted(PHASE1_CONCERNS)
    assert [name for _label, name, _body in bullets] == model_order[1:], \
        "one bullet for each Phase 1 concern, in the model's order"
    for label, name, body in bullets:
        expected_label, kept = GUIDE_CONCERNS[name]
        assert label == expected_label, (name, label)
        kind_and_holders = _definition_and_holders(name)
        assert kind_and_holders in _flat(body).replace("-", " "), (name, kind_and_holders)
        for sentence in kept:
            assert sentence in _flat(body), (name, sentence)
        phases = sorted({phase for phase, _viewpoint in PHASE1_CONCERNS[name][4]})
        assert re.search(rf"\bAnswered (?:by|in) [^.]*\bPhase {phases[0]}\b", _flat(body)), \
            f"{name}: the bullet names the phase that answers the concern"
    flat = _flat(section)
    assert not re.search(r"(?i)\b(?:issue time|sequence count|check value)s?\b", flat), \
        "the guide's Phase 1 list names no field of the command: its form is INC-DRIVING-002's until its baseline"
    for phrase in ("held by the parties whose interest it states.",
                   "The vehicle occupants and the road users hold their own concern beside the engineering roles.",
                   "The framing viewpoint frames all six until those views exist.",
                   "They do not judge whether the stakeholder, risk and viewpoint coverage is adequate; review does."):
        assert phrase in flat, phrase


def test_each_phase_one_concern_is_answered_by_a_view_of_its_phase_in_its_saf_domain():
    # The views that answer a concern are views the method lists for their phase, in the SAF domain of the
    # concern's definition: rule 15's domain advisory reads that property once the views exist.
    listed = _canonical_list()
    domains = _domains(SAF_FILE.read_text(encoding="utf-8"))
    for name, (kind, _items, _holders, _sentences, answers) in PHASE1_CONCERNS.items():
        assert answers, f"{name} names no view that answers it"
        for phase, viewpoint in answers:
            assert viewpoint in listed[phase], f"{name}: {viewpoint} is not a view the method lists for phase {phase}"
            assert domains[viewpoint] == domains[kind], \
                f"{name}: {kind} is in the {domains[kind]} domain, {viewpoint} in {domains[viewpoint]}"
