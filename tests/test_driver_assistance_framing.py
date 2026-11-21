"""Content pins for the framing of the driver-assistance increment, not semantic validation.

The framing of INC-DRIVING-002 holds Phase 0, the Phase 1 concerns and the baseline decision of
Phase 11. These tests hold its structure to the method's Phase 0, Phase 1 and Phase 11 shapes,
pin each decided statement by its own phrase, and hold the guide and the VisionPilot section of the
folder's upstream record to the model. They read the model text; they do not parse SysML.

What they do not hold: a sentence that no pin names can change inside a doc of the model
or inside that section, and a report of a run in words that the scan for past behavior
does not list passes. Those are for the review of the text.
"""

from __future__ import annotations

import json
import math
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
DRIVING = ROOT / "textual-notation-of-model/packages/features/driving"
MODEL = DRIVING / "driver_assistance_framing.sysml"
UPSTREAM_RECORD = DRIVING / "upstream.md"
#: the separate record of the first heads of this increment; the folder keeps one upstream record
FORMER_RECORD = DRIVING / "driver-assistance-upstream.md"
GUIDE = ROOT / "docs/guides/driver-assistance-increment.md"
INDEX = ROOT / "UPSTREAM.md"
GLOSSARY = ROOT / "docs/terminology/glossary.md"
AEBS_REQUIREMENTS = ROOT / "textual-notation-of-model/packages/features/aebs/aebs_needs_requirements.sysml"
PACKAGE = "DE4SDV_DriverAssistanceFraming"
IDENTITY = "INC-DRIVING-002"
PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"
AUTOSPEED_PIN = "b62e55b93ba728787cb1152347463030443634c4"

DOC = re.compile(r"\bdoc\s*/\*(.*?)\*/", re.DOTALL)
#: a usage declared at package level (two spaces of indent), with an optional short name
PACKAGE_USAGE = re.compile(r"(?m)^  (part|requirement|concern)\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*(\w+)")

#: in-scope item -> the statement it makes
IN_SCOPE = {
    "vehicleTargetResponseInScope":
        "The warning request and the braking for a stationary and for a slower moving vehicle target ahead.",
    "driverWarningInScope":
        "The collision warning that the AAOS SDV gives the driver in two modes, on its display and as a sound: "
        "whether each mode is given, and when, relative to the warning request and to the start of the emergency "
        "braking.",
    "noReactionInScope":
        "Two scenarios in which neither a warning nor braking is due, taken from the false-reaction scenarios of "
        "the regulation.",
    "vehicleTargetCriteriaInScope":
        "Criteria for a vehicle target derived from UNECE R152, each with what a simulation cannot show.",
    "scoreCommandPathInScope":
        "The candidate's commands reach the simulated vehicle, and its warning request reaches the AAOS SDV, through "
        "Eclipse S-CORE; no bypass.",
    "verdictEvidenceInScope":
        "A pass or a fail for each requirement and scenario, bound to the candidate revision that ran.",
}
#: out-of-scope item -> the statement it makes
OUT_OF_SCOPE = {
    "pedestrianAndBicycleTargetsOutOfScope": "Pedestrian and bicycle targets.",
    "cruiseAndLaneKeepingQualityOutOfScope":
        "How well the candidate holds speed, distance and lane. These functions run; no case judges them.",
    "laneDepartureFunctionsOutOfScope":
        "The candidate's lane-departure warning and lane-departure avoidance. They come with the application; no case "
        "judges them.",
    "speedAssistanceOutOfScope":
        "The candidate's intelligent speed assistance, which its documentation bases on speed-limit map data. No run "
        "of this increment gives it map data, and no case judges it.",
    "handsFreeModeOutOfScope":
        "The candidate's hands-free mode as a product function: driving one lane of a highway without the driver's "
        "hands. The candidate drives the vehicle in the runs, but no case judges the mode.",
    "driverInteractionOutOfScope": "Driver monitoring, driver override and deactivation.",
    "furtherWarningProvisionsOutOfScope":
        "The haptic mode of the collision warning, the regulation's further rules on the warning signals (their "
        "description, the failure and unavailability signals, their check at ignition and their visibility in "
        "daylight), and whether a driver perceives the warning. The regulation asks for the warning in at least two "
        "modes; this increment judges two, the warning on the display and the sound, by whether and when each is "
        "given. The product line's requirement of a collision warning to the driver is answered that far and no "
        "further.",
    "existingAEBSOutOfScope": "Changing the Autoware-based AEBS or reusing its evidence for this candidate.",
    "candidateTuningOutOfScope":
        "Training the candidate's networks, or tuning the candidate or a scenario until a case passes.",
    "onRoadOperationOutOfScope":
        "On-road operation, production readiness, safety approval, compliance, type approval or certification.",
}
#: assumption -> the phrase that states its premise, and a further statement that the framing decided
ASSUMPTIONS = {
    "asmSimulatorPathUsable": ("works with the simulator release of the driving bench",
                               "can be taken from it without a change to its decision logic"),
    "asmProcessorInferenceSufficient": ("run on a processor alone, without a graphics card",
                                        "fast enough for its control cycle in closed loop"),
    "asmBenchReuse": ("can carry a second application",
                      "the path to the AAOS SDV display of the closed-loop driving increment",
                      "Their results for the first application are not evidence for this one.",
                      "That increment built its path to the display to show the driving state, with no deadline for "
                      "its delivery; whether the path carries a warning in time is for a readiness probe or Phase 7 "
                      "to show."),
    "asmSimulatedConfigurationStandsIn": (
        "stand in for the vehicle, the surface and the test target that the source regulation prescribes",
        "A verdict holds for that simulated configuration only."),
}
#: gap -> the phrase that states what is open
GAPS = {
    "gapVehicleTargetCriteria": "None exists for a vehicle target.",
    "gapNoSeparateEmergencyFunction": "It has no emergency function apart from that planner.",
    "gapWarningOutput": "That interface carries no warning.",
    "gapCandidateBehaviorUnverified": "No closed-loop result of the application exists on the DE4SDV bench",
    "gapScoreIntegration": "no binding to Eclipse S-CORE communication and no S-CORE supervision",
    "gapCameraImageAndGeometry": "The simulator's images are not images of that dataset.",
    "gapDeclaredOperatingConditions":
        "The two scenarios in which no reaction is due lie outside the declared conditions",
    "gapCandidateAdmission": "This increment admits no member and changes no scope decision.",
    "gapUpstreamContactAndRights": "The upstream maintainers are not yet involved.",
    "gapDriverHmiInProductLine": "that revision of the governed scope is made outside this increment.",
}
#: gap -> the label of its open point in the guide
OPEN_POINTS = {
    "gapVehicleTargetCriteria": "No criteria for a vehicle target",
    "gapNoSeparateEmergencyFunction": "No emergency function apart from the speed planner",
    "gapWarningOutput": "No warning output",
    "gapCandidateBehaviorUnverified": "No result on the DE4SDV bench",
    "gapScoreIntegration": "No Eclipse S-CORE binding",
    "gapCameraImageAndGeometry": "Simulated images",
    "gapDeclaredOperatingConditions": "Two scenarios outside the declared conditions",
    "gapCandidateAdmission": "No admission",
    "gapUpstreamContactAndRights": "No upstream contact and no rights clearance",
    "gapDriverHmiInProductLine": "The HMI display's place in the product line",
}
#: Phase 1: concern -> (its SAF or DE4SDV concern definition, the in-scope items its doc names first, its native
#: stakeholders in order, the sentences that state its question, and the views that answer it as (phase, viewpoint
#: definition) pairs, read from the doc's answer). One concern per question; a concern is held by the parties whose
#: interest it states, not only by the roles that check it.
PHASE1_CONCERNS = {
    "vehicleTargetResponseConcern": (
        "OperationalCapabilityConcern", ("vehicleTargetResponseInScope", "noReactionInScope"),
        [("occupant", "VehicleOccupant"), ("roadUser", "RoadUser")],
        ("Vehicle occupants and road users need the vehicle to warn its driver and to brake when a collision with a "
         "stationary or a slower moving vehicle ahead in its lane is imminent, and to do neither when no collision "
         "is imminent.",
         "It states what they expect, not how well the candidate meets it: no safety or on-road claim follows from "
         "it."),
        ((2, "OperationalStoryViewpoint"),)),
    "emergencyBrakingIndependenceConcern": (
        "PhysicalFunctionalMappingConcern", ("vehicleTargetResponseInScope",),
        [("safetyExpert", "SafetyExpert"), ("productLineEngineer", "ProductLineEngineer")],
        ("Safety experts and product-line engineers need to see which software element of the candidate realizes "
         "the emergency braking, whether it is a function apart from the speed planner "
         "(gapNoSeparateEmergencyFunction), and how its braking command keeps the independence of the protected "
         "emergency command path that the product line holds as common content.",
         "Whether the candidate's braking can stand for the common capability turns on it, and so does the lifecycle "
         "decision."),
        ((8, "PhysicalLogicalMappingViewpoint"), (8, "PhysicalInternalExchangeViewpoint"))),
    "driverWarningSequenceConcern": (
        "SystemProcessConcern", ("driverWarningInScope",),
        [("occupant", "VehicleOccupant"), ("safetyExpert", "SafetyExpert")],
        ("The driver, a vehicle occupant, needs a warning of an imminent collision on the display and as a sound.",
         "Safety experts need to see the sequence from the candidate's warning request to each of the two modes of "
         "the warning and to the start of the emergency braking, and the time between them, independent of the "
         "software that realizes it.",
         "Whether a driver perceives the warning is out of scope."),
        ((6, "SystemProcessViewpoint"),)),
    "scoreCommandAndWarningPathConcern": (
        "PhysicalInternalExchangeConcern", ("scoreCommandPathInScope",),
        [("systemsEngineer", "SystemsEngineer"), ("productLineEngineer", "ProductLineEngineer")],
        ("Systems engineers and product-line engineers need to see the driving command pass from the candidate "
         "through Eclipse S-CORE elements to the actuation, and the warning request through S-CORE to the AAOS SDV, "
         "with no exchange beside S-CORE, and the boundary interface by which each leaves the candidate.",
         "(gapWarningOutput, gapScoreIntegration)",
         "The candidate's boundary stays as phase 0 draws it: the path is an internal exchange of the realization "
         "that holds the candidate, the S-CORE path and the AAOS SDV, which phases 6 to 8 decide."),
        ((8, "PhysicalInternalExchangeViewpoint"),)),
    "vehicleTargetCriteriaConcern": (
        "RegulatoryScopeWithoutComplianceClaimConcern", ("vehicleTargetCriteriaInScope",),
        [("complianceEngineer", "ComplianceEngineer"), ("verificationEngineer", "VerificationEngineer")],
        ("Compliance engineers and verification engineers need each criterion for a vehicle target traced to the "
         "provision of UNECE R152 it is derived from, with the product-line requirement it judges, whose obligation "
         "it is, and what a simulation cannot show of it (gapVehicleTargetCriteria).",
         "A criterion met in simulation holds for the simulated configuration only "
         "(asmSimulatedConfigurationStandsIn) and is no statement about compliance or type approval."),
        ((5, "SystemRequirementDefinitionViewpoint"),)),
    "candidateVerdictConcern": (
        "ArgumentationAssuranceConcern", ("verdictEvidenceInScope",),
        [("productLineEngineer", "ProductLineEngineer"), ("verificationEngineer", "VerificationEngineer")],
        ("Product-line engineers and verification engineers need the lifecycle decision to rest on a pass or a fail "
         "for each requirement and scenario, each bound to the candidate revision that ran and to the simulated "
         "configuration.",
         "A build that carries a change that upstream has not merged is a different candidate, with its verdicts "
         "reported apart (gapCandidateBehaviorUnverified), and a fail stays a recorded result.",
         "A fail that a mismatch of the simulated camera image or of the camera calibration may explain stays a "
         "fail, and names gapCameraImageAndGeometry."),
        ((10, "ArgumentationAssuranceViewpoint"),)),
}
#: the SAF or DE4SDV catalogue file that declares each definition a Phase 1 concern is typed by
CATALOGUES = {
    "SAF_Viewpoints": ROOT / "textual-notation-of-model/packages/methods/saf/SAF_Viewpoints.sysml",
    "DE4SDV_MethodViewpoints":
        ROOT / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_method_concerns_and_viewpoints.sysml",
}
#: a past form of what a candidate does in a run: a framing reports no run
PAST_BEHAVIOR = re.compile(r"(?i)\b(?:braked|warned|stopped|collided|avoided|detected|passed|failed)\b")
#: an affirmative claim of approval or admission
APPROVAL = re.compile(r"(?i)\b(?:compliant|complies|certified|homologated|type-approved|admitted)\b")
#: the words by which a concern's doc names a view that answers it -> the viewpoint definition of that view
VIEW_PHRASES = {
    "operational story": "OperationalStoryViewpoint",
    "requirement definition table": "SystemRequirementDefinitionViewpoint",
    "system process": "SystemProcessViewpoint",
    "physical-logical mapping": "PhysicalLogicalMappingViewpoint",
    "view of the claimed path": "PhysicalInternalExchangeViewpoint",
    "argumentation assurance view": "ArgumentationAssuranceViewpoint",
}
#: a sentence of a concern's doc that says by which views the concern is answered
ANSWER_SENTENCE = re.compile(r"[^.]*\banswered\b[^.]*\.", re.I)


def _raw() -> str:
    return MODEL.read_text(encoding="utf-8")


def _code() -> str:
    return strip_comments(_raw())


def _doc(declaration: str) -> str:
    """The first doc of the declaration's body, without comment leaders and line breaks."""
    match = DOC.search(braced_body(_raw(), declaration))
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
    assert "part def DriverAssistanceIncrement :> EngineeringIncrement;" in code
    assert re.search(
        rf"part\s+<'{IDENTITY}'>\s+driverAssistanceIncrement\s*:\s*DriverAssistanceIncrement\b", code)
    problem = braced_body(code, "requirement driverAssistanceProblem : ProblemStatement")
    assert "subject driverAssistanceSubject : DriverAssistanceIncrement;" in problem
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", problem) == [
        "ProductLineEngineer", "SystemsEngineer", "SafetyExpert", "VerificationEngineer", "ComplianceEngineer"]
    assert len(_declared("IncrementEngineeringQuestion")) == 1
    assert len(_declared("IncrementLifecycleDecision")) == 1
    assert _declared("IncrementScope") == {"driverAssistanceScope"}, "exactly one scope"
    assert re.search(
        r"dependency\s+scopeToDriverAssistanceQuestion\s+from\s+driverAssistanceScope\s+to\s+"
        r"driverAssistanceQuestion\s*;", code)
    assert re.search(
        r"dependency\s+driverAssistanceQuestionToProblem\s+from\s+driverAssistanceQuestion\s+to\s+"
        r"driverAssistanceProblem\s*;", code)

    charter = braced_body(code, "part driverAssistanceCharter : IncrementCharter")
    assert "ref part :>> increment = driverAssistanceIncrement;" in charter
    assert "ref part :>> systemOfInterest = candidateDriverAssistanceSystem;" in charter
    assert 'attribute :>> owner = "Orkun Yilmaz";' in charter
    assert re.findall(r"MethodPhase::(\w+)", charter) == [
        "phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
        "phase3_capabilityClassification", "phase4_needs", "phase5_requirements",
        "phase6_functionalArchitecture", "phase7_logicalArchitecture",
        "phase8_physicalRealization", "phase9_variabilityConfiguration",
        "phase10_vvEvidence", "phase11_baseline",
    ]
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1)) == [
        PACKAGE, "DE4SDV_DriverAssistanceOperationalContext", "DE4SDV_DriverAssistanceCapabilityClassification",
        "DE4SDV_DriverAssistanceNeedsRequirements", "DE4SDV_DriverAssistanceFunctionalArchitecture",
        "DE4SDV_DriverAssistanceLogicalArchitecture", "DE4SDV_DriverAssistancePhysicalSoftwareRealization",
        "DE4SDV_DriverAssistanceVariabilityConfiguration", "DE4SDV_DriverAssistanceVerificationEvidence",
    ], "the charter names only the packages that hold content today"
    evidence = re.search(r"expectedReviewEvidence\s*=\s*\((.*?)\);", charter, re.S)
    assert evidence and re.findall(r'"([^"]+)"', evidence.group(1)) == [
        "owner confirmation of the engineering question and the scope",
        "independent review of the System 1 and System 2 boundary and the nonclaims",
        "repository, smoke and focused regression checks on the reviewed changes",
        "exact-head licensed SysML validation and Syside-generated framing view",
    ]

    assert "part candidateDriverAssistanceSystem : DriverAssistanceSystem;" in code
    assert "part driverAssistanceVerificationEnvironment : System2EngineeringAndAssuranceSystem" in code


def test_the_question_the_decision_and_the_boundary_say_what_was_agreed():
    increment = _doc(f"part <'{IDENTITY}'> driverAssistanceIncrement : DriverAssistanceIncrement")
    for phrase in ("VisionPilot of the Autoware Foundation is the application that the owner named.",
                   "The increment judges the candidate's warning request and braking for a vehicle target, and the "
                   "collision warning that the AAOS SDV then gives the driver on its display and as a sound.",
                   "It does not change the Autoware-based AEBS.",
                   "This package holds Phase 0, the Phase 1 concerns and the baseline decision of Phase 11."):
        assert phrase in increment, phrase
    problem = _doc("requirement driverAssistanceProblem : ProblemStatement")
    for phrase in ("The product line holds AEBS for a vehicle target as common content",
                   "to detect an imminent forward collision with a vehicle target, to warn the driver and to "
                   "command emergency braking",
                   "DE4SDV does not know whether its warning and braking meet those requirements",
                   "the model holds no regulation-derived criteria for a vehicle target"):
        assert phrase in problem, phrase
    question = _doc("part driverAssistanceQuestion : IncrementEngineeringQuestion")
    for phrase in ("with its commands on the Eclipse S-CORE command path",
                   "request the collision warning and command the braking that the product line requires for a "
                   "vehicle target, with the warning shown on the AAOS SDV display and sounded,",
                   "criteria derived from UNECE R152 judge its closed-loop behavior in simulation",
                   "A verdict for each requirement and scenario answers this.",
                   "A recording of a run that looks right does not."):
        assert phrase in question, phrase
    assert question.count("?") == 1, "an increment answers one engineering question"
    decision = _doc("part driverAssistanceDecision : IncrementLifecycleDecision")
    for phrase in ("whose own warning and braking stand for the common capability",
                   "a candidate that needs named additions from the platform, or not at all",
                   "executed cases with a pass or a fail for each requirement of the increment",
                   "The additions are named from the requirements that fail and from the gaps of this increment; "
                   "the increment builds none of them.",
                   "A fail is a result to record.",
                   "no reason to change a scenario or a criterion until the candidate passes"):
        assert phrase in decision, phrase
    system = _doc("part def DriverAssistanceSystem")
    # the three sentences that state the boundary are pinned whole: one more item inside is a change of the boundary
    for phrase in ("Candidate System 1 boundary. In: the front-camera image and the vehicle speed. Inside: "
                   "perception of the lane and of the closest object in the path, speed and steering planning, "
                   "and the warning and braking decision. Out: the driving command and the warning request.",
                   "Two parts of System 1 are outside this boundary, and neither is an enabling system: the Eclipse "
                   "S-CORE path that carries the driving command to the actuation and the warning request to the "
                   "AAOS SDV, and the AAOS SDV, which gives the driver the collision warning on its display and as a "
                   "sound.",
                   "The candidate is a proposed application system, not a member product",
                   "this increment admits no member to the governed product-line scope"):
        assert phrase in system, phrase
    environment = _doc("part driverAssistanceVerificationEnvironment : System2EngineeringAndAssuranceSystem")
    for phrase in ("CARLA renders the camera image and moves the vehicle and the targets.",
                   "Cloud hosts, the scenario runner, the evaluators, the capture of the display and of the sound, "
                   "and the recordings enable engineering and verification. They are not vehicle features and not "
                   "contents of the candidate System 1 boundary.",
                   "The capture observes the AAOS SDV and is no part of it."):
        assert phrase in environment, phrase
    # the display's place in the product line is an open point of its own, not a statement of the boundary
    assert "optional" not in system
    # the owner's decisions of 2026-11-13: the display shows the warning as part of the system, not as an instrument,
    # and the warning is given in two modes
    assert "instrument" not in _flat(_raw())


def test_the_candidate_definition_declares_nothing_and_system_2_is_one_part_beside_it():
    code = _code()
    assert braced_body(code, "part def DriverAssistanceSystem").split() == ["doc"], \
        "phase 0 states the candidate boundary in words; its parts and ports follow in phases 2 and 3"
    assert _declared("System2EngineeringAndAssuranceSystem") == {"driverAssistanceVerificationEnvironment"}
    assert re.search(r"(?m)^  part driverAssistanceVerificationEnvironment : System2EngineeringAndAssuranceSystem\b",
                     code), "the enabling system is a part of the package, not of the candidate"
    assert _declared("DriverAssistanceSystem") == {"candidateDriverAssistanceSystem"}


def test_scope_items_are_the_agreed_closed_sets():
    code = _code()
    assert _declared("InScopeItem") == set(IN_SCOPE)
    assert _declared("OutOfScopeItem") == set(OUT_OF_SCOPE)
    for name, statement in IN_SCOPE.items():
        assert _doc(f"part {name} : InScopeItem") == statement, name
    for name, statement in OUT_OF_SCOPE.items():
        assert _doc(f"part {name} : OutOfScopeItem") == statement, name
    scope_body = braced_body(code, "part driverAssistanceScope : IncrementScope")
    assert "InScopeItem" not in scope_body and "OutOfScopeItem" not in scope_body, \
        "scope items are package-level parts: a nested item is not in the scope gate's population"
    scope = _doc("part driverAssistanceScope : IncrementScope")
    for phrase in ("The warning request and the braking of the candidate for a vehicle target ahead in its lane, and "
                   "the collision warning that the AAOS SDV then gives the driver on its display and as a sound,",
                   "in closed loop with a rendered camera image",
                   "for one configuration and with at most ten requirements",
                   "a stationary target, a slower moving target, and two in which no reaction is due",
                   "Implementation is not part of this framing slice."):
        assert phrase in scope, phrase
    # the requirements that the scope names as the source of the increment's own are requirements of the AEBS model
    named = re.findall(r"REQ-AEBS-\d{3}", scope)
    assert named == ["REQ-AEBS-002", "REQ-AEBS-003", "REQ-AEBS-008", "REQ-AEBS-012"]
    aebs = AEBS_REQUIREMENTS.read_text(encoding="utf-8")
    statements = {
        "REQ-AEBS-002": "providing a collision warning to the driver",
        "REQ-AEBS-003": "commanding emergency braking",
        "REQ-AEBS-008": "shall not issue an AEBS collision warning",
        "REQ-AEBS-012": "shall not command AEBS emergency braking",
    }
    for identity in named:
        declared = re.findall(rf"requirement\s+(\w+)\s*:\s*\w+\s*\{{\s*doc\s*/\*\s*{identity}\b", aebs)
        assert len(declared) == 1, f"{identity} is one requirement of the AEBS model: {declared}"
        assert statements[identity] in _flat(braced_body(aebs, f"requirement {declared[0]} :")), identity


def test_assumptions_are_premises_and_gaps_are_open_points():
    code = _code()
    assert _declared("IncrementAssumption") == set(ASSUMPTIONS)
    assert _declared("IncrementGap") == set(GAPS)
    for name, phrases in ASSUMPTIONS.items():
        for phrase in phrases:
            assert phrase in _doc(f"part {name} : IncrementAssumption"), (name, phrase)
    for name, phrase in GAPS.items():
        assert phrase in _doc(f"part {name} : IncrementGap"), name
    assert len(re.findall(r"\battribute\s*:>>\s*disposition\b", code)) == len(GAPS) + 1, \
        "each gap and the baseline decision state one disposition, the one the baseline decision of phase 11 gives"
    # the two premises that a readiness probe discharges say so
    for name in ("asmSimulatorPathUsable", "asmProcessorInferenceSufficient"):
        assert "readiness probe" in _doc(f"part {name} : IncrementAssumption"), name
    criteria = _doc("part gapVehicleTargetCriteria : IncrementGap")
    for phrase in ("cover the pedestrian and the bicycle target",
                   "its detection criteria for a vehicle target, the timing, modality and observability of its "
                   "collision warning, the activation conditions and the braking demand profile of its emergency "
                   "braking, and its non-activation and false-reaction constraints",
                   "It defers the promotion of quantified thresholds into System 1 obligations.",
                   "gives their parameters as guidance, not as a test",
                   "It also has to state whose obligation each criterion is."):
        assert phrase in criteria, phrase
    emergency = _doc("part gapNoSeparateEmergencyFunction : IncrementGap")
    for phrase in ("At the inspected revision",
                   "Whether the candidate's braking can stand for the common capability, or the platform has to "
                   "add an independent function, is open. The lifecycle decision turns on it.",
                   "The product line also holds the independence of the protected emergency command path as "
                   "common content."):
        assert phrase in emergency, phrase
    warning = _doc("part gapWarningOutput : IncrementGap")
    for phrase in ("At the inspected revision",
                   "writes its steering and its acceleration to its vehicle interface",
                   "The warnings go to the application's own visualization and to its own data log, each only "
                   "when it is switched on.",
                   "A warning request at the system boundary, which the AAOS SDV needs, is an output that the "
                   "application does not have.",
                   "Whether it can be added without a change to the application's decision logic is open.",
                   "The data log can give the evaluators a record of the warnings, not the warning for the driver."):
        assert phrase in warning, phrase
    assert "How its driving command, its warning request and its state enter the S-CORE path without a bypass is " \
           "open." in _doc("part gapScoreIntegration : IncrementGap")
    hmi = _doc("part gapDriverHmiInProductLine : IncrementGap")
    for phrase in ("The feature model holds the HMI display as an optional feature that requires the AAOS SDV guest, "
                   "and neither governed member selects it, while the product line requires every member product to "
                   "warn the driver.",
                   "The owner decided on 2026-11-13 that every member product has an HMI display, realized "
                   "according to the member's integration mode;",
                   "assumes that the HMI of the S-CORE-integrated member is the visualization of the AEBS "
                   "visualization increment, an informational display and not the AEBS driver warning.",
                   "The AEBS visualization increment keeps that visualization in System 2, out of every System 1 "
                   "feature configuration.",
                   "Here the display is System 1 content that gives the collision warning, so it is not that "
                   "visualization.",
                   "Phase 3 classifies the candidate's display and sound against the scope as it then stands."):
        assert phrase in hmi, phrase
    unverified = _doc("part gapCandidateBehaviorUnverified : IncrementGap")
    for phrase in ("No closed-loop result of the application exists on the DE4SDV bench, and DE4SDV has run "
                   "neither the inspected revision nor a change to it.",
                   "is a different candidate, and its verdicts are reported apart"):
        assert phrase in unverified, phrase
    # the framing states nothing of its own about a defect of the inspected revision, restates no open change of the
    # project, and forecasts no result
    for phrase in ("still has", "relative speed", "wrong sign", "open changes", "likely first result"):
        assert phrase not in _flat(_raw()), phrase
    admission = _doc("part gapCandidateAdmission : IncrementGap")
    for phrase in ("The governed scope holds two planned reference members.",
                   "and the independence of the protected emergency command path",
                   "does not fit that content"):
        assert phrase in admission, phrase
    rights = _doc("part gapUpstreamContactAndRights : IncrementGap")
    for phrase in ("show them a result about their project before it is published",
                   "No upstream contact, endorsement or rights clearance is asserted."):
        assert phrase in rights, phrase


def test_the_declared_operating_conditions_place_the_four_scenarios():
    gap = _doc("part gapDeclaredOperatingConditions : IncrementGap")
    for phrase in ("The candidate's documentation declares its hands-free mode only for highways and motorways with "
                   "clearly marked lane lines, in fair weather and visibility, at up to 70 mph (about 113 km/h) and "
                   "away from construction zones and roadwork, with a human driver supervising it at all times.",
                   "Supervision by a driver falls under driver monitoring, which is out of scope "
                   "(driverInteractionOutOfScope); the road, the weather and the speed place each scenario.",
                   "The scenarios with a stationary and with a slower moving vehicle target ahead in the lane run on a "
                   "highway-type road in fair weather, inside these conditions.",
                   "The two scenarios in which no reaction is due lie outside the declared conditions: a tight curve "
                   "with guard pipes and a turn at a corner are no highway situations.",
                   "Both come from the regulation's false-reaction scenarios and stay in the scope.",
                   "Phase 10 reports the runs outside the declared conditions apart from the runs inside them."):
        assert phrase in gap, phrase
    assert "driverInteractionOutOfScope" in OUT_OF_SCOPE
    # the conditions are the project's own declaration, read at the inspected commit
    section = _record_section(UPSTREAM_RECORD.read_text(encoding="utf-8"), "VisionPilot")
    assert (f"[Documentation index](https://github.com/autowarefoundation/vision_pilot/blob/{PIN}"
            "/github-io/docs-index.md)") in section
    flat = _flat(section)
    for phrase in ("Read for an amendment of the framing and the operational context of INC-DRIVING-002 on "
                   "2026-11-15, at the same commit:",
                   "it lists the application's driver-assistance functions, among them an intelligent speed assist "
                   "that uses speed-limit map data and a single-lane hands-free highway autopilot.",
                   "It declares the hands-free mode only for highways and motorways with clearly marked lane lines, in "
                   "fair weather and visibility, at up to 70 mph and away from construction zones and roadwork, with "
                   "a human driver supervising it at all times."):
        assert phrase in flat, phrase


def test_the_framing_view_frames_the_boundary_and_exposes_every_usage():
    code = _code()
    boundary = braced_body(code, "concern driverAssistanceBoundary : IncrementBoundaryConcern")
    lines = [line.strip() for line in boundary.splitlines() if line.strip()]
    assert lines[0] == "subject increment : DriverAssistanceIncrement;"
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", boundary) == ["SystemsEngineer", "VerificationEngineer"]
    assert dict(re.findall(r"\bconcern\s+(\w+)\s*:\s*(\w+)\s*\{", code)) == {
        "driverAssistanceBoundary": "IncrementBoundaryConcern",
        **{name: spec[0] for name, spec in PHASE1_CONCERNS.items()}}, \
        "the boundary concern of Phase 0 and the concerns of Phase 1, no other"

    view = braced_body(code, "view driverAssistanceFramingView")
    viewpoint = braced_body(view, "viewpoint driverAssistanceFramingViewpoint : IncrementFramingViewpoint")
    frames = re.findall(r"\bframe\s+(\w+)\s*;", viewpoint)
    assert frames[0] == "driverAssistanceBoundary" and sorted(frames[1:]) == sorted(PHASE1_CONCERNS) \
        and len(frames) == len(set(frames)), "the one framing viewpoint frames every concern of the increment once"
    assert len(re.findall(r"\bview\s+\w+\s*\{", code)) == 1, "phases 0 and 1 share one view"
    assert "render asTreeDiagram;" in view
    exposed = re.findall(r"\bexpose\s+(\w+)\s*;", view)
    assert len(exposed) == len(set(exposed)), "an element is exposed once"

    usages = {name for _kind, name, _type in PACKAGE_USAGE.findall(code)}
    kinds = {kind for _kind, _name, kind in PACKAGE_USAGE.findall(code)}
    assert len(usages) >= 30, "the population of the exposure check must not be vacuous"
    assert {"InScopeItem", "OutOfScopeItem", "IncrementAssumption", "IncrementGap", "IncrementCharter",
            "IncrementScope", "ProblemStatement", "IncrementBoundaryConcern"} <= kinds
    assert set(exposed) == usages | {"DriverAssistanceIncrement"}, \
        f"not exposed: {sorted(usages - set(exposed))}; exposed and not declared: {sorted(set(exposed) - usages)}"


def test_the_framing_claims_no_verification_no_admission_and_no_compliance():
    raw = _raw()
    code = _code()
    # raw source: a claim hidden in a comment is still a claim a reader sees
    assert not re.search(r"\b(?:verify|satisfy)\s+\w+", code)
    assert not re.search(r"\bverification\b", code)
    assert "ProductLineMemberProduct" not in raw, "the candidate is not typed as a member product"
    assert not re.search(r"(?i)\b(?:compliant|complies|certified|homologated|type-approved)\b", raw)
    header = raw.split("package", 1)[0]
    for phrase in ("Phase 0 framing, the Phase 1 concerns and the baseline decision of Phase 11",
                   "no implementation", "no runtime result",
                   "no product-line",
                   "no compliance"):
        assert phrase in _flat(header.replace("*", "")), phrase
    for word in ("compliance", "type approval", "certification", "production readiness"):
        assert word in OUT_OF_SCOPE["onRoadOperationOutOfScope"], word


def test_no_text_of_the_framing_reports_a_run_an_approval_or_an_admission():
    visionpilot = _row(GLOSSARY, "VisionPilot |")
    criterion = _row(GLOSSARY, "Regulation-derived criterion |")
    index_row = _row(INDEX, "[VisionPilot]")
    texts = {
        MODEL.name: _raw(),
        GUIDE.name: GUIDE.read_text(encoding="utf-8"),
        "upstream record, VisionPilot": _record_section(UPSTREAM_RECORD.read_text(encoding="utf-8"), "VisionPilot"),
        "glossary row VisionPilot": visionpilot,
        "glossary row Regulation-derived criterion": criterion,
        "index row": index_row,
    }
    for name, text in texts.items():
        assert not PAST_BEHAVIOR.findall(text), f"{name} reports behavior in a run: {PAST_BEHAVIOR.findall(text)}"
        assert not APPROVAL.findall(text), f"{name}: {APPROVAL.findall(text)}"
    # each of these texts says what the candidate is not, in its own sentence
    assert "In DE4SDV a candidate application under evaluation, not a member product." in visionpilot
    assert "the closest object in its path and commands steering and acceleration" in visionpilot
    assert "(../../textual-notation-of-model/packages/features/driving/upstream.md#visionpilot)" in visionpilot
    assert "with the result pass, fail or inconclusive" in criterion
    assert "Meeting it is not a statement of compliance, type approval or certification." in criterion
    assert "Candidate application of the driver-assistance increment." in index_row
    assert "It is read for the framing. No bench builds or runs it." in index_row


def test_the_identity_is_declared_once_and_its_subject_is_registered():
    declarations = []
    for root in MODEL_ROOTS:
        for path in root.rglob("*.sysml"):
            if f"<'{IDENTITY}'>" in path.read_text(encoding="utf-8"):
                declarations.append(path.relative_to(ROOT).as_posix())
    assert declarations == [MODEL.relative_to(ROOT).as_posix()]
    assert _raw().count(f"<'{IDENTITY}'>") == 1
    assert IDENTITY.split("-")[1] in check_naming.REGISTERED_SUBJECTS
    assert check_naming.check_identifier_tokens_in_text(
        _raw(), display_path=MODEL.name, suffix=".sysml") == []


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
    assert "**Status: baselined (Phase 11).**" in _flat(guide)
    quoted = _flat(" ".join(line[1:].strip() for line in guide.splitlines() if line.startswith(">")))
    assert quoted == _doc("part driverAssistanceQuestion : IncrementEngineeringQuestion"), \
        "the guide quotes the model's engineering question word for word"
    rows = [[cell.strip() for cell in line.strip().strip("|").split("|")]
            for line in guide.split("## What the increment judges", 1)[1].split("\n\n", 2)[1].splitlines()]
    assert rows[0] == ["In scope", "Out of scope"]
    cells_in = [row[0] for row in rows[2:] if row[0]]
    cells_out = [row[1] for row in rows[2:] if row[1]]
    assert cells_in == list(IN_SCOPE.values()), "the table's in-scope column is the model's in-scope items"
    assert cells_out == list(OUT_OF_SCOPE.values()), "the table's out-of-scope column is the model's items"
    for target in ("../../textual-notation-of-model/packages/features/driving/driver_assistance_framing.sysml",
                   "../../textual-notation-of-model/packages/features/driving/VIEWS.md",
                   "../../textual-notation-of-model/packages/features/driving/upstream.md#visionpilot",
                   "../../textual-notation-of-model/packages/features/driving/upstream.md"
                   "#questions-requiring-upstream-engagement",
                   "../../methodologies/sysmod-sysmlv2/pilots/aebs-regulatory-source.yaml"):
        assert f"]({target})" in guide, target
    flat = _flat(guide)
    for phrase in ("No product-line admission, safety, compliance or type-approval claim follows;",
                   "The additions are named from the requirements that fail and from the gaps of this increment; "
                   "the increment builds none of them.",
                   "It is no statement about compliance or type approval.",
                   "Starting this increment launches no compute and authorizes no spend.",
                   "The increment ended at its baseline decision.",
                   "the clauses for a vehicle target are not yet anchored there."):
        assert phrase in flat, phrase
    boundaries = _flat(guide.split("## Boundaries", 1)[1].split("\n## ", 1)[0])
    for phrase in ("The candidate driver-assistance system is a proposed **System 1** subject.",
                   "Two parts of **System 1** are outside its boundary, and neither is an enabler: the Eclipse S-CORE "
                   "path that carries its driving command to the actuation and its warning request to the AAOS SDV, "
                   "and the AAOS SDV, which gives the driver the collision warning on its display and as a sound.",
                   "CARLA, the cloud hosts, the scenario runner, the evaluators, the capture of the display and of the "
                   "sound, and the recordings are **System 2** enablers, not vehicle features.",
                   "The capture observes the AAOS SDV and is no part of it."):
        assert phrase in boundaries, phrase
    assert boundaries.count("**System 1**") == 2 and boundaries.count("**System 2**") == 1
    assert "instrument" not in flat, "the display shows the warning as part of the system"


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


def test_the_upstream_record_pins_what_the_framing_read():
    # The folder keeps one upstream record. Its VisionPilot section holds what this framing read: the inspected
    # commit, the licence, and the files that the gaps rest on; and the one file the classification (phase 3) read. It restates no pull request of the project and no
    # reading of DE4SDV's own; the questions for the maintainers and the contact stand in the record's shared sections.
    assert not FORMER_RECORD.exists(), "one upstream record for the folder"
    record = UPSTREAM_RECORD.read_text(encoding="utf-8")
    assert record.startswith("# Driving: upstream provenance\n")
    intro = _flat(record.split("\n## ", 1)[0])
    assert ("The VisionPilot section and the statements about VisionPilot belong to INC-DRIVING-002; the rest of the "
            "record belongs to INC-DRIVING-001.") in intro, "the record says whose each statement is"
    section = _record_section(record, "VisionPilot")
    pinned = re.findall(r"github\.com/autowarefoundation/vision_pilot/(?:blob|tree)/([^/)\s]+)", record)
    assert len(pinned) == 33 and set(pinned) == {PIN}, "every file link of the record is at the inspected commit"
    assert len(re.findall(r"github\.com/autowarefoundation/vision_pilot/(?:blob|tree)/", section)) == 33, \
        "the files of the project are linked in its section only"
    network = re.findall(r"github\.com/autowarefoundation/auto_speed([^)\s]*)", record)
    assert network == [f"/tree/{AUTOSPEED_PIN}"], "the record links the network's repository at one commit"
    text = _link_text(section)
    for phrase in ("Read for the framing of INC-DRIVING-002 on 2026-11-13: Autoware Foundation VisionPilot, "
                   f"commit `{PIN}` of the branch `main`, with an Apache-2.0 licence file.",
                   "Which revision a bench runs is a decision of phase 8.",
                   "Application loop: one process that reads the camera image and the vehicle speed and writes a "
                   "steering and an acceleration command.",
                   "Closed-loop simulator path: CARLA 0.9.16 over ROS 2.",
                   "Its release tag `v1.2` is commit `9a96c3e771f9e79e91b6ccfcbf2ce860530024c8`, an ancestor of the "
                   "inspected commit.",
                   "DE4SDV has built and run nothing of this project, and vendors nothing of it.",
                   "The code has no emergency function apart from that planner.",
                   "it carries no warning. The warnings go to the application's visualization and to its data log, "
                   "each only when the application configuration switches it on. In the inspected commit that file "
                   "switches the visualization on and the data log off.",
                   "it lists warning requests among the outputs of the element.",
                   "the commit holds no binding to Eclipse S-CORE communication and no S-CORE supervision.",
                   f"(commit `{AUTOSPEED_PIN}`, Apache-2.0 licence file), says that the AutoSpeed 2.0 network is "
                   "trained on the OpenLane dataset.",
                   "DE4SDV has not checked that the weights in the application's repository are the ones that this "
                   "README describes, and has not read the terms of the weights or of that dataset."):
        assert phrase in text, phrase
    assert not re.search(r"(?i)\bpull requests?\b", text), "the section restates no pull request of the project"
    # A reading of DE4SDV's own about the pinned code, or a reply of the project, is in no part of the record. What
    # DE4SDV sent stands in the closed-loop increment's contact text, so its own exchanges are looked for where this
    # increment writes: the VisionPilot section and its questions.
    for phrase in ("still has", "relative speed", "wrong sign"):
        assert phrase not in _flat(record), phrase
    reply = re.compile(r"(?i)\b(?:maintainers?|authors?|project) (?:has |have )?(?:confirmed|agreed|answered|replied|"
                       r"approved|endorsed)\b|\bwith its author\b")
    assert not reply.findall(_flat(record)), reply.findall(_flat(record))
    exchange = re.compile(r"(?i)\bDE4SDV (?:has )?(?:confirmed|agreed|asked|contacted|told|informed|reported|discussed|"
                          r"posted|opened|sent)\b")
    questions = _record_section(record, "Questions requiring upstream engagement")
    assert questions.count("\nVisionPilot:\n") == 1
    asks = questions.split("\nVisionPilot:\n", 1)[1]
    for part in (text, _flat(asks)):
        assert not exchange.findall(part), exchange.findall(part)
    assert len(re.findall(r"(?m)^- ", asks)) == 5, "five questions for the maintainers of the project"
    for phrase in ("Which revision and which configuration does the project support for a closed-loop run in the "
                   "simulator?",
                   "Is an output of the warnings planned apart from the visualization and the data log?",
                   "permit the intended use and the publication of results?"):
        assert phrase in _flat(asks), phrase
    contact = _flat(_record_section(record, "Upstream contact"))
    about = [sentence for sentence in re.split(r"(?<=\.) ", contact) if re.search(r"(?i)vision.?pilot", sentence)]
    assert about == ["In the VisionPilot repository DE4SDV has posted nothing."], about
    index_row = _row(INDEX, "[VisionPilot]")
    assert "[Driving upstream record](textual-notation-of-model/packages/features/driving/upstream.md)" in index_row
    assert "(https://github.com/autowarefoundation/vision_pilot)" in index_row


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
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", DOC.search(braced_body(_raw(), f"concern {name} : {kind}")).group(1))
                    .split())


def test_phase_one_frames_one_concern_for_each_question_of_the_scope():
    code = _code()
    assert "private import SAF_Viewpoints::*;" in code, "the SAF concern definitions come from the catalogue"
    assert not re.search(r"\b(?:concern|viewpoint|part) def\b(?! (?:DriverAssistanceIncrement|DriverAssistanceSystem)\b)",
                         code), "concern types and stakeholders come from the catalogues and the kernel, never the slice"
    catalogues = {name: path.read_text(encoding="utf-8") for name, path in CATALOGUES.items()}
    answered = set()
    for name, (kind, items, holders, sentences, answer) in PHASE1_CONCERNS.items():
        assert sum(bool(re.search(rf"\bconcern def {kind}\b", text)) for text in catalogues.values()) == 1, \
            f"{name}: {kind} is a concern definition of exactly one catalogue"
        body = braced_body(code, f"concern {name} : {kind}")
        parameters = [line.strip() for line in body.splitlines() if line.strip() and line.strip() != "doc"]
        assert parameters[0] == "subject;", f"{name}: the subject is the first parameter"
        assert re.findall(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;", body) == holders, name
        doc = _concern_doc(name, kind)
        lead = ", ".join(items[:-1]) + (" and " if len(items) > 1 else "") + items[-1]
        assert doc.startswith(lead), f"{name}: the doc opens with the in-scope items it answers: {doc[:80]}"
        for sentence in sentences:
            assert sentence in doc, (name, sentence)
        assert _answers(doc) == set(answer), (name, sorted(_answers(doc)))
        answered.update(items)
    in_scope = _declared("InScopeItem")
    assert answered == in_scope, f"in-scope items without a concern: {sorted(in_scope - answered)}"


def test_every_stakeholder_of_the_problem_holds_a_phase_one_concern_and_the_beneficiaries_hold_their_own():
    # The concerns' holders are the parties whose interest each states: the five roles of the problem statement and
    # the people the warning and the braking serve. The occupant and the road user hold the operational concern alone.
    problem = braced_body(_code(), "requirement driverAssistanceProblem : ProblemStatement")
    roles = set(re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", problem))
    held = {role for _kind, _items, holders, *_rest in PHASE1_CONCERNS.values() for _name, role in holders}
    assert roles <= held, f"problem stakeholders that hold no Phase 1 concern: {sorted(roles - held)}"
    assert held - roles == {"VehicleOccupant", "RoadUser"}, sorted(held - roles)
    assert "private import DE4SDV_Stakeholders::*;" in _code()
    operational = _concern_doc("vehicleTargetResponseConcern", "OperationalCapabilityConcern")
    assert "Reviewers need" not in operational and "engineers" not in operational


def test_the_phase_one_concerns_claim_no_result_and_name_no_unread_record():
    names = set(re.findall(r"\bpart\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*(?:IncrementGap|IncrementAssumption|InScopeItem)\b",
                           _code()))
    for name, (kind, *_rest) in PHASE1_CONCERNS.items():
        doc = _concern_doc(name, kind)
        named = set(re.findall(r"\b((?:gap|asm)[A-Z]\w+|\w+InScope)\b", doc))
        assert named <= names, f"{name} names a record the framing does not declare: {sorted(named - names)}"
        assert not PAST_BEHAVIOR.findall(doc) and not APPROVAL.findall(doc), name
        assert not re.search(r"\b\d+(?:\.\d+)?\s*(?:s|m|km/h|m/s)\b", doc), f"{name}: a criterion value is phase 5's"


def test_the_guide_lists_the_phase_one_concerns_with_their_holders():
    guide = GUIDE.read_text(encoding="utf-8")
    assert guide.index("## What the increment judges") < guide.index("## Concerns (Phase 1)") \
        < guide.index("## What the framing already records as open")
    section = _flat(guide.split("## Concerns (Phase 1)", 1)[1].split("\n## ", 1)[0])
    bullets = re.findall(r"- \*\*[^*]+\*\* `(\w+)`", section)
    model_order = re.findall(r"\bconcern\s+(\w+)\s*:", _code())
    assert model_order[0] == "driverAssistanceBoundary" and sorted(model_order[1:]) == sorted(PHASE1_CONCERNS)
    assert bullets == model_order[1:], "one bullet for each Phase 1 concern, in the model's order"
    for phrase in ("The framing viewpoint frames all six until those views exist.",
                   "They do not judge whether the stakeholder, risk and viewpoint coverage is adequate; review does."):
        assert phrase in section, phrase


def test_each_phase_one_concern_is_answered_by_a_view_of_its_phase_in_its_saf_domain():
    # The views that answer a concern are views the method lists for their phase. A concern typed by an SAF
    # definition is answered in the SAF domain of that definition: rule 15's domain advisory reads that property
    # once the views exist. The DE4SDV-typed concern is outside rule 15; its phase is still checked.
    listed = _canonical_list()
    domains = _domains(SAF_FILE.read_text(encoding="utf-8"))
    for name, (kind, _items, _holders, _sentences, answers) in PHASE1_CONCERNS.items():
        assert answers, f"{name} names no view that answers it"
        for phase, viewpoint in answers:
            assert viewpoint in listed[phase], f"{name}: {viewpoint} is not a view the method lists for phase {phase}"
            if kind in domains:
                assert domains[viewpoint] == domains[kind], \
                    f"{name}: {kind} is in the {domains[kind]} domain, {viewpoint} in {domains[viewpoint]}"


# -- phase 11: the baseline decision ------------------------------------------------------------------------------

BASELINE = "part driverAssistanceBaselineDecision : IncrementBaselineDecision"
#: the slice files of this increment; the driving folder holds INC-DRIVING-001's files too
SLICES = sorted(DRIVING.glob("driver_assistance_*.sysml"))
#: The disposition the baseline decision gives each gap record of the increment: the ten framing gaps by name, the
#: gap of phase 10 by short name. An accepted gap stays open as a known limit; a deferred one moves to a later
#: increment. gapCandidateBehaviorUnverified stays accepted because the judged session S1 is evidence of record;
#: gapCameraImageAndGeometry is deferred because S1 does not show what explains the fails; GAP-DRIVING-014 stays
#: deferred with the text that the second slice of phase 10 gives it (the decisions of 2026-11-21).
GAP_DISPOSITIONS = {
    "gapVehicleTargetCriteria": "deferred",
    "gapNoSeparateEmergencyFunction": "deferred",
    "gapWarningOutput": "deferred",
    "gapCandidateBehaviorUnverified": "accepted",
    "gapScoreIntegration": "deferred",
    "gapCameraImageAndGeometry": "deferred",
    "gapDeclaredOperatingConditions": "accepted",
    "gapCandidateAdmission": "deferred",
    "gapUpstreamContactAndRights": "deferred",
    "gapDriverHmiInProductLine": "deferred",
    "GAP-DRIVING-014": "deferred",
}
#: The evidence directory of the judged session S1. The verdicts, the statuses and the figures of the baseline and of
#: the gaps are written by hand; these tests derive each of them from its file here, so that a refresh that changes
#: a verdict file fails the hand texts that restate it (review Q3 and Q7 of 2026-11-21).
EVIDENCE = ROOT / "implementation" / "driver-assistance-bench" / "evidence" / "s1-20261121T014447Z"
VERIFICATION = DRIVING / "driver_assistance_verification_evidence.sysml"


def _evidence(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def _case_verdicts() -> dict[str, str]:
    """The verdict of each case of S1: the eight evaluated cases from verdicts.json, and VC-DRIVING-039 from the
    outcome of the desk analysis (analysis_039.generator.json), mapped as MapAssistanceEvidenceOutcomeToVerdict of
    the phase 10 slice maps it."""
    found = {vc: case["verdict"] for vc, case in _evidence("verdicts.json")["cases"].items()}
    calc = " ".join(VERIFICATION.read_text(encoding="utf-8").split("calc def MapAssistanceEvidenceOutcomeToVerdict",
                                                                    1)[1].split("}", 1)[0].split())
    mapped = dict(re.findall(r"outcome == AssistanceEvidenceOutcome::(\w+)\? VerdictKind::(\w+)", calc))
    other = re.search(r"else VerdictKind::(\w+);", calc)
    assert mapped and other, "the slice's calc def has no readable map"
    found["VC-DRIVING-039"] = mapped.get(_evidence("analysis_039.generator.json")["outcome"], other.group(1))
    assert sorted(found) == [f"VC-DRIVING-0{n}" for n in range(36, 45)], sorted(found)
    return {vc: found[vc] for vc in sorted(found)}


def _case_runs(vc: str) -> list[dict]:
    return _evidence("verdicts.json")["cases"][vc]["measured"]["runs"]


#: the judged runs of S1: those to which VC-DRIVING-036 gives a pass or a fail; the runs of SC-DRIVING-014 and
#: SC-DRIVING-015 have no judged-run term, and VC-DRIVING-036 does not read them
JUDGED = [e["run"] for e in _case_runs("VC-DRIVING-036") if e["outcome"] != "inconclusiveMissingEvidence"]
JUDGED_012 = [run for run in JUDGED if run.startswith("012_")]
#: the impact speed that VC-DRIVING-037 measured in each judged run of SC-DRIVING-012, km/h to one decimal
IMPACTS = [f"{e['measured']['impactKmh']:.1f}" for e in _case_runs("VC-DRIVING-037") if e["run"] in JUDGED_012]
IMPACT_LIST = ", ".join(IMPACTS[:-1]) + " and " + IMPACTS[-1]
#: why 012_20_r2 is not judged, as VC-DRIVING-036 records it
CENTER_LINE = re.search(r"center line ([0-9.]+) m from the target's \(limit ([0-9.]+) m\)", " ".join(
    " ".join(e["missing"]) for e in _case_runs("VC-DRIVING-036") if e["run"] == "012_20_r2")).groups()
#: the end of the judged run of SC-DRIVING-013 and of the second runs, and the stop instant of the stop run, as the
#: refresh writes them into drop_counts.json from the session tree
_COUNTS = _evidence("drop_counts.json")
RUN_END_013 = _COUNTS["013_30_r1"]["runEnd"]
B1_TICKS = sorted({_COUNTS[run]["runEnd"]["ticks"] for run in ("013_30_r2", "013_60_r2")})
STOP_WINDOW = _COUNTS["stop"]["wholeRunWindow"]
STOP_INSTANT = _COUNTS["stop"].get("stopInstant") or {}


def _kmh(value) -> str:
    return f"{value:.1f}" if isinstance(value, (int, float)) else str(value)


def _s(value, digits: int) -> str:
    return f"{value:.{digits}f}" if isinstance(value, (int, float)) else str(value)


#: the words of the judged runs in the texts (review Q8 of 2026-11-21): of the 14 runs, those that VC-DRIVING-036
#: judges, and the runs of SC-DRIVING-014 and SC-DRIVING-015, which have no judged-run term
JUDGED_RUNS_PHRASE = (f"the 14 runs of SC-DRIVING-012 to SC-DRIVING-015 ({len(JUDGED)} of them judged runs; "
                      "SC-DRIVING-014 and SC-DRIVING-015 have no judged-run term)")
#: the stop clause of VC-DRIVING-038, from the stop run's whole-run window and its stop instant (review Q1)
STOP_CLAUSE = (f"{STOP_WINDOW['dropped']} dropped camera images fall inside its judged window, from "
               f"{STOP_WINDOW['firstTickSimS']:.3f} s to {STOP_WINDOW['lastTickSimS']:.3f} s of simulation time, and "
               f"the stop came at about {_s(STOP_INSTANT.get('simS'), 2)} s, so "
               f"{_s(STOP_INSTANT.get('ticksAfterStopS'), 2)} s of ticks follow it")
#: Every place of the draft that waits for the verdicts of the judged session S1 or for phase 10b. Finishing the
#: baseline replaced each one in the model and the guide; none remains.
PLACEHOLDERS = ()
#: The texts that replaced the 13 places of the draft, in the draft's order: the framing decision's answer, the
#: evidence, the verdicts, the verdicts that read the runs outside the declared conditions, the additions,
#: GAP-DRIVING-014, and one place in each of seven framing gaps (S1, the decisions of 2026-11-21).
FILLS = (
    # 0 the framing decision's answer
    "as a candidate that needs the additions named below before it can be the AEBS of a member product, by the "
    "decision of 2026-11-21",
    # 1 the evidence
    "by the decision of 2026-11-21, the judged session S1, session 20261121T014447Z at bench commit 508649ba, run on "
    f"2026-11-21 on the three hosts with {JUDGED_RUNS_PHRASE} and the run that stops the path, and its records, on the "
    "condition that the bench files that ran are byte-identical to those that the second slice of phase 10 merges, "
    "the check that the evidence README of that slice states",
    # 2 the verdicts
    "VC-DRIVING-036, VC-DRIVING-037 and VC-DRIVING-042 a fail of the pinned candidate on this bench in simulation: in "
    "each of the five judged runs of SC-DRIVING-012 the candidate started no warning request and commanded no "
    f"deceleration stronger than 0.46 m/s², and the contact with the stationary target came at {IMPACT_LIST} km/h, "
    "the impact speeds that VC-DRIVING-037 measured; the second run at 20 km/h is not judged, its center line "
    f"{CENTER_LINE[0]} m from the target's against a limit of {CENTER_LINE[1]} m. Of SC-DRIVING-013, the first run "
    "at 30 km/h is judged and meets the three criteria, since no collision became imminent and the candidate slowed "
    "below the target's speed: at the run's last tick the vehicle drove at "
    f"{_kmh(RUN_END_013.get('egoSpeedAtLastTickKmh'))} km/h and the target at "
    f"{_kmh(RUN_END_013.get('targetSpeedAtLastTickKmh'))} km/h; the second run at 30 km/h and both runs at 60 "
    "km/h have no functional part and are not judged. VC-DRIVING-038, VC-DRIVING-040, VC-DRIVING-041, VC-DRIVING-043 "
    "and VC-DRIVING-044 inconclusive: each of the 14 runs and the run that stops the path drops 23 or 24 camera "
    "images in the first 5 s after its first image, "
    "and by the rule of phase 8 no run whose judged window holds a dropped image is judged; for these cases the "
    "window is the whole run. Read with "
    "that rule set aside, for diagnosis only and as no verdict, VC-DRIVING-038 and VC-DRIVING-044 meet their "
    "criteria in all 14 runs, and VC-DRIVING-040, VC-DRIVING-041 and VC-DRIVING-043 in the runs of SC-DRIVING-012 and "
    "SC-DRIVING-013. VC-DRIVING-039 a pass, by a desk analysis of the realization in an independent agent session, "
    "within its bounds: a loss of a driving command shows only when a later command arrives, a delay of up to 0.1 s "
    "of simulation time goes unseen, and the second slice of phase 10 corrects the realization's sentence about later "
    "valid commands to what the check value catches",
    # 3 the verdicts that read the runs of SC-DRIVING-014 and SC-DRIVING-015
    "no run of either gives a verdict, since VC-DRIVING-038, VC-DRIVING-040, VC-DRIVING-041 and VC-DRIVING-044, the "
    "cases that read them, judge over the whole run and are inconclusive by the rule on dropped images",
    # 4 the additions
    "by the decision of 2026-11-21, a warning and an emergency braking for a stationary vehicle ahead in its lane, "
    "a camera path that keeps every image from a run's first image on, so that the criteria over every run can be "
    "judged, except those of VC-DRIVING-040 and VC-DRIVING-041 on the runs of SC-DRIVING-014 and SC-DRIVING-015, "
    "which also need the fix of the case evaluators that GAP-DRIVING-014 names as B3, and for the stop clauses of "
    "VC-DRIVING-038 and VC-DRIVING-043 a judged window that ends at the stop "
    "instant or a camera input that stops with the candidate, since after the stop the interface drops the images "
    "that the candidate no longer takes",
    # 5 what GAP-DRIVING-014 holds after the second slice of phase 10
    "the readiness items that S1 leaves open: the candidate's cycle on the GPU of the S-CORE host, on which each of "
    "the 14 runs of SC-DRIVING-012 to SC-DRIVING-015 drops 23 or 24 camera images in the first 5 s after its first "
    "image and up to 2 more inside the run, with no "
    "cause shown, what S1 does not show of the start of the sound on the IVI guest, the showing of the results to the "
    "VisionPilot maintainers, the bench item B1 for the next session, the end of the second runs of "
    f"SC-DRIVING-013 after {' or '.join(str(t) for t in B1_TICKS)} ticks at the speed of the target, and the bench "
    "item B3, the case evaluators' reading of the guidance of SC-DRIVING-014 and SC-DRIVING-015 one level above "
    "where the setting record holds it",
    # 6 gapNoSeparateEmergencyFunction
    "VC-DRIVING-036 and VC-DRIVING-037 a fail, since in the five judged runs of SC-DRIVING-012 the candidate "
    "commanded no deceleration stronger than 0.46 m/s² before the contact with the stationary target, VC-DRIVING-042 "
    "a fail, since in the same runs the candidate started no warning request, and VC-DRIVING-041 inconclusive by the "
    "rule on dropped images",
    # 7 gapWarningOutput
    "VC-DRIVING-042 a fail, since in the five judged runs of SC-DRIVING-012 the candidate started no warning request, "
    "and VC-DRIVING-040 and VC-DRIVING-043 inconclusive by the rule on dropped images",
    # 8 gapCandidateBehaviorUnverified
    "the judged session S1 of 2026-11-21 gives the first closed-loop results of record of the candidate on the "
    "DE4SDV bench",
    # 9 gapScoreIntegration
    "VC-DRIVING-038 and VC-DRIVING-043, each inconclusive by the rule on dropped images. The stop clause of "
    f"VC-DRIVING-038 is inconclusive by the same rule: {STOP_CLAUSE}",
    # 10 gapCameraImageAndGeometry
    "S1 does not show whether the detection of the target at the distances that the criteria need, or the "
    "calibration, explains the fails of VC-DRIVING-036, VC-DRIVING-037 and VC-DRIVING-042",
    # 11 gapDeclaredOperatingConditions
    "no run of SC-DRIVING-014 or SC-DRIVING-015 gives a verdict, since the cases that read them judge over the whole "
    "run and are inconclusive by the rule on dropped images",
    # 12 gapUpstreamContactAndRights
    "at the baseline the maintainers have not seen the results or the draft, and nothing is posted to them before "
    "the owner approves its exact text",
)
#: The verdict of each case in the judged session S1, as the baseline and the guide's table state it: derived from
#: the verdict files of the evidence directory, never typed here (review Q7 of 2026-11-21)
VERDICTS = _case_verdicts()
#: What the baseline decision states, in its order: what it accepts, the evidence and the verdicts, the gaps under
#: their dispositions, and the claims it does not make.
BASELINE_STATEMENTS = (
    "BL-DRIVING-002-P11.",
    "The baseline of INC-DRIVING-002 accepts the driver-assistance integration as built: the model of phases 0 to 10 "
    "and the bench that implements it.",
    "VisionPilot at 014e0e7a, built with the DE4SDV S-CORE interface and the visualization recorder, runs as an "
    "Eclipse S-CORE application that the Launch Manager starts and supervises; the bench carries its driving command "
    "to the simulated vehicle in CARLA 1.0 through the actuation adapter, and its warning request to the AAOS SDV "
    "guests, on the Eclipse S-CORE path.",
    f"This answers the framing decision (driverAssistanceDecision): the candidate goes forward {FILLS[0]}.",
    f"The evidence it accepts: {FILLS[1]}.",
    f"The verdicts, one for each case: {FILLS[2]}.",
    "The runs of SC-DRIVING-014 and SC-DRIVING-015 lie outside the candidate's declared operating conditions and are "
    f"reported apart: {FILLS[3]}.",
    "A fail is a recorded result: no scenario, criterion or setting is changed for it (counterClaimNoTuningToPass).",
    "The additions named from the requirements that fail and from the gaps of this increment: "
    f"{FILLS[4]}; the increment builds none of them.",
    "Accepted as known limits, still open in this baseline: the verdicts of a build with changes that upstream has "
    "not merged (gapCandidateBehaviorUnverified), and the runs outside the declared operating conditions "
    "(gapDeclaredOperatingConditions).",
    "Deferred to a later increment: the product line's criteria for a vehicle target (gapVehicleTargetCriteria), the "
    "member decision on the braking that leaves in the one driving command (gapNoSeparateEmergencyFunction), the "
    "upstream take-up of the warning hand-off (gapWarningOutput) and of the S-CORE interface module "
    "(gapScoreIntegration), whether the rendered camera images or the calibration of the simulated camera explain "
    "the fails (gapCameraImageAndGeometry), the member decision that amends ADR 0014 (gapCandidateAdmission), the upstream contact "
    "and the rights clearance (gapUpstreamContactAndRights), the display in the governed scope and the acoustic "
    f"warning (gapDriverHmiInProductLine), and {FILLS[5]} (GAP-DRIVING-014).",
    "No gap is withdrawn.",
    "No safety, on-road, compliance, type-approval, certification, homologation or membership claim follows from "
    "this baseline, and nothing about UNECE R152: a criterion met in simulation holds for the simulated "
    "configuration only (asmSimulatedConfigurationStandsIn).",
    "The bench is engineering equipment, and its camera images, vehicle dynamics and targets are simulated.",
)
#: What each framing gap says at the baseline: what the increment answered and what stays open.
FRAMING_GAP_BASELINE_STATEMENTS = {
    "gapVehicleTargetCriteria": (
        "At the baseline decision: phase 5 derived the criteria for a vehicle target with their provenance and the "
        "owner of each (vehicleTargetCriteriaFixedInPhase5), and the cases of phase 10 read them.",
        "The AEBS model still records its criteria for a vehicle target as undefined, and no verdict covers what a "
        "simulation cannot show of a criterion.",
        "Deferred to a later increment: taking the criteria into the obligations of the product line.",
    ),
    "gapNoSeparateEmergencyFunction": (
        "At the baseline decision: the realization answers the gap for this candidate "
        "(phase8EmergencyFunctionAnswered): the warning and the emergency braking come from the one planned "
        "acceleration and leave in the one driving command, and the candidate realizes no independent protected "
        "emergency command path (counterClaimNoIndependentEmergencyPath).",
        f"The cases that judge that braking: {FILLS[6]}.",
        "Deferred to a later increment: whether the candidate's braking can stand for the common capability is for "
        "the member decision.",
    ),
    "gapWarningOutput": (
        "At the baseline decision: the warning request leaves the candidate through the hand-off that phase 8 "
        "placed (phase8WarningOutputPlaced), a change that upstream has not merged.",
        f"The cases that judge the warning request: {FILLS[7]}.",
        "The inspected revision has no warning output of its own; whether upstream takes the hand-off is open until "
        "its maintainers have seen the draft (gapUpstreamContactAndRights).",
        "Deferred to a later increment.",
    ),
    "gapCandidateBehaviorUnverified": (
        f"At the baseline decision: {FILLS[8]}.",
        "Every verdict is of the build 014e0e7a with the DE4SDV S-CORE interface and the visualization recorder, "
        "changes that upstream has not merged (phase8CandidateBuildCarriesTheSCOREInterface, "
        "phase8VisualizationRecorderPlaced, counterClaimBuildWithUnmergedChanges); the inspected revision without "
        "them has run on no DE4SDV bench.",
        "Accepted as a known limit; the gap stays open.",
    ),
    "gapScoreIntegration": (
        "At the baseline decision: the candidate's process is an Eclipse S-CORE application through the DE4SDV "
        "S-CORE interface module, which the Launch Manager starts and supervises (phase8ScoreIntegrationPlaced), and "
        "its driving command and its warning request enter the S-CORE path at the boundary of the process.",
        "The readiness items that phase 8 left open went on as GAP-DRIVING-014.",
        f"The cases that judge the path: {FILLS[9]}.",
        "The module is a change that upstream has not merged, and the inspected revision has no S-CORE binding of "
        "its own.",
        "Deferred to a later increment: its take-up upstream.",
    ),
    "gapCameraImageAndGeometry": (
        "At the baseline decision: the cases read the candidate on rendered camera images, with the calibration of "
        "the simulated camera.",
        f"A fail that a mismatch of the image or of the calibration may explain stays a fail: {FILLS[10]}.",
        "A verdict holds for the rendered images only (counterClaimRenderedCameraImages).",
        "Deferred to a later increment: which of the two explains the fails, if either.",
    ),
    "gapDeclaredOperatingConditions": (
        "At the baseline decision: the runs of SC-DRIVING-014 and SC-DRIVING-015, outside the declared conditions, "
        "are reported apart from the runs of SC-DRIVING-012 and SC-DRIVING-013 "
        "(counterClaimOutsideDeclaredConditions).",
        f"Reported apart: {FILLS[11]}.",
        "Accepted as a known limit; the gap stays open.",
    ),
    "gapCandidateAdmission": (
        "At the baseline decision: phase 3 classified the candidate and named the scope decisions "
        "(memberDecisionScopeInputs), and phase 9 gave DRIVING-CONFIG-002, a valid configuration that no member "
        "decision has taken in.",
        "This baseline admits no member product (counterClaimNoMemberProduct), and the member decision that amends "
        "ADR 0014 has not been made.",
        "Deferred to a later increment.",
    ),
    "gapUpstreamContactAndRights": (
        "At the baseline decision: by the upstream contact decision of 2026-11-18 the VisionPilot maintainers are "
        "shown the draft of the warning output and the interface seam, with the results, after the scenarios of "
        f"phase 10 have run in CARLA: {FILLS[12]}.",
        "No endorsement and no rights clearance exists, and the terms of the network weights and of their data are "
        "not read (counterClaimNoUpstreamEndorsementOrRights).",
        "Deferred to a later increment.",
    ),
    "gapDriverHmiInProductLine": (
        "At the baseline decision: phase 3 classified the display and the sound (driverHmiClassification).",
        "The governed scope takes in the display as common content with the scope pull request of ADR 0026, outside "
        "this increment, and whether the acoustic warning becomes common content of the driver warning is for the "
        "member decision.",
        "Deferred to a later increment.",
    ),
}


def _flat_body(raw: str, declaration: str) -> str:
    return " ".join(re.sub(r"(?m)^\s*\*\s?", "", braced_body(raw, declaration)).split())


def _in_order(statements, text: str, what: str) -> None:
    position = -1
    for statement in statements:
        assert statement in text, (what, statement)
        assert text.index(statement) > position, (what, "out of order", statement)
        position = text.index(statement)


def _gap_records() -> dict[str, str]:
    """Every IncrementGap part of the increment's packages, by short name or else by name, with its body."""
    records = {}
    for path in SLICES:
        code = strip_comments(path.read_text(encoding="utf-8"))
        for short, name in re.findall(r"\bpart\s+(?:<'([^']+)'>\s+)?(\w+)\s*:\s*IncrementGap\s*\{", code):
            declaration = f"part <'{short}'> {name} : IncrementGap" if short else f"part {name} : IncrementGap"
            assert (short or name) not in records, short or name
            records[short or name] = braced_body(code, declaration)
    return records


def test_the_increment_has_one_baseline_decision_beside_its_framing_decision():
    codes = {path.name: strip_comments(path.read_text(encoding="utf-8")) for path in SLICES}
    assert len(codes) == 9, "the nine packages of the charter"
    declared = [(name, found) for name, code in codes.items()
                for found in re.findall(r"\bpart\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*(?:\w+::)?IncrementBaselineDecision\b",
                                        code)]
    assert declared == [(MODEL.name, "driverAssistanceBaselineDecision")], "exactly one, in the framing package"
    code = codes[MODEL.name]
    body = braced_body(code, BASELINE)
    assert re.findall(r"\battribute\s*:>>\s*disposition\s*=\s*LifecycleDisposition::(\w+)\s*;", body) == ["accepted"]
    assert "private import DE4SDV_MethodContext::*;" in code
    assert not re.search(r"\bpart def \w*(?:Baseline|Lifecycle)Decision\b", code), "the type comes from the kernel"
    # the framing decision of phase 0 names the decision the increment supports; it is no baseline decision
    assert "disposition" not in braced_body(code, "part driverAssistanceDecision : IncrementLifecycleDecision")
    exposed = re.findall(r"\bexpose\s+(\w+)\s*;", braced_body(code, "view driverAssistanceFramingView"))
    assert exposed.index("driverAssistanceBaselineDecision") == exposed.index("driverAssistanceDecision") + 1, \
        "the framing view shows the baseline decision beside the framing decision"


def test_the_baseline_decision_states_what_it_accepts_and_what_it_does_not():
    raw = _raw()
    assert BASELINE in strip_comments(raw), "the increment has no baseline decision"
    doc = _flat_body(raw, BASELINE)
    assert doc.startswith("doc /* BL-DRIVING-002-P11. The baseline of INC-DRIVING-002 accepts"), doc[:80]
    _in_order(BASELINE_STATEMENTS, doc, "baseline")
    for claim in ("is verified", "are verified", "is proven", "meets REQ-", "certified", "evidence of record exists",
                  "compliant", "type-approved"):
        assert claim not in doc, claim


def test_every_gap_of_the_increment_states_the_disposition_the_baseline_gives_it():
    stated = {key: re.findall(r"\battribute\s*:>>\s*disposition\s*=\s*LifecycleDisposition::(\w+)\s*;", body)
              for key, body in _gap_records().items()}
    assert stated == {key: [disposition] for key, disposition in GAP_DISPOSITIONS.items()}


def test_the_baseline_decision_names_every_gap_under_its_disposition():
    raw = _raw()
    assert BASELINE in strip_comments(raw), "the increment has no baseline decision"
    doc = _flat_body(raw, BASELINE)
    heads = {"accepted": "Accepted as known limits, still open in this baseline:",
             "deferred": "Deferred to a later increment:"}
    lists = {}
    for disposition, head in heads.items():
        found = [statement for statement in BASELINE_STATEMENTS if statement.startswith(head)]
        assert len(found) == 1 and doc.count(head) == 1 and found[0] in doc, head
        lists[disposition] = found[0]
    assert set(GAP_DISPOSITIONS.values()) == set(heads) and "No gap is withdrawn." in BASELINE_STATEMENTS
    for key, disposition in GAP_DISPOSITIONS.items():
        named = [where for where, statement in lists.items() if re.search(rf"\b{re.escape(key)}\b", statement)]
        assert named == [disposition], (key, disposition, named)


def test_each_framing_gap_says_what_the_increment_answered_and_what_stays_open():
    raw = _raw()
    closing = {"accepted": "Accepted as a known limit; the gap stays open.", "deferred": "Deferred"}
    assert set(FRAMING_GAP_BASELINE_STATEMENTS) == {key for key in GAP_DISPOSITIONS if not key.startswith("GAP-")}
    for name, statements in FRAMING_GAP_BASELINE_STATEMENTS.items():
        doc = _flat_body(raw, f"part {name} : IncrementGap")
        assert statements[0].startswith("At the baseline decision: "), name
        assert statements[-1].startswith(closing[GAP_DISPOSITIONS[name]]), (name, statements[-1])
        _in_order(statements, doc, name)
        assert doc.count("At the baseline decision: ") == 1, name
        assert doc.index(statements[0]) > 150, f"{name}: the framing text stays first"
        # the framing text before the baseline paragraph is the one that the open points of the guide quote
        assert GAPS[name] in doc[:doc.index(statements[0])], name


def test_the_guide_describes_the_baseline_and_what_it_defers():
    guide = GUIDE.read_text(encoding="utf-8")
    assert "## Baseline (Phase 11)" in guide, "the guide has no baseline section"
    assert guide.index("## Verification and evidence (Phase 10)") < guide.index("## Baseline (Phase 11)") \
        < guide.index("## What the framing already records as open") \
        < guide.index("## Next obligation and execution limits")
    section = _flat(guide.split("## Baseline (Phase 11)")[1].split("\n## ")[0])
    for text in ("`driverAssistanceBaselineDecision` (BL-DRIVING-002-P11)",
                 f"each of the {len(GAP_DISPOSITIONS)} gap records",
                 "**Accepted: the integration as built.**", "**Evidence and verdicts.**",
                 f"**Evidence and verdicts.** {FILLS[1][0].upper()}{FILLS[1][1:]}.",
                 f"The framing decision asked how the candidate goes forward; the baseline answers: {FILLS[0]}.",
                 f"The additions named from the requirements that fail and from the gaps: {FILLS[4]}; the increment "
                 "builds none of them.", f"GAP-DRIVING-014: {FILLS[5]}.", "**Withdrawn.** None."):
        assert text in section, text
    # one row for each case, with the verdict of the baseline
    raw_section = guide.split("## Baseline (Phase 11)")[1].split("\n## ")[0]
    rows = dict(re.findall(r"(?m)^\| (VC-DRIVING-\d{3}) \| (\w+) \|", raw_section))
    assert rows == VERDICTS, rows

    def named(bullet: str) -> set[str]:
        return set(re.findall(r"\bGAP-DRIVING-\d{3}\b", bullet)) | set(re.findall(r"`(gap\w+)`", bullet))

    bullets = dict(re.findall(r"- \*\*([^*]+)\*\* (.*?)(?= - \*\*|$)", section))
    for title, disposition in (("Known limits: accepted, still open.", "accepted"),
                               ("Deferred to a later increment.", "deferred")):
        expected = {key for key, value in GAP_DISPOSITIONS.items() if value == disposition}
        assert named(bullets[title]) == expected, title
    flat = _flat(guide)
    assert "**Status: baselined (Phase 11).**" in flat
    tally = {verdict: list(VERDICTS.values()).count(verdict) for verdict in ("fail", "inconclusive", "pass")}
    words = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five", 6: "six", 7: "seven", 8: "eight", 9: "nine"}
    assert ("The baseline accepts the model of phases 0 to 10 and the bench as built, and as evidence the judged "
            f"session S1 of 2026-11-21 at bench commit 508649ba: {words[tally['fail']]} cases are a fail, "
            f"{words[tally['inconclusive']]} are inconclusive and {words[tally['pass']]} is a pass.") in flat
    assert "first slice of Phase 10 verification and evidence, proposal" not in flat
    assert "The increment ended at its baseline decision." in flat and "The next model obligation is" not in flat


def test_no_place_of_the_baseline_waits_for_the_judged_session():
    """The draft of phase 11 waited for the verdicts of S1 and for phase 10b in marked texts. Finishing the baseline
    replaced them all, in the model and the guide, and emptied PLACEHOLDERS."""
    marked = re.compile(r"<(?:S1|10b): [^>]*>")
    found = []
    for path in SLICES:
        found += marked.findall(_flat(re.sub(r"(?m)^\s*\*\s?", "", path.read_text(encoding="utf-8"))))
    in_guide = marked.findall(_flat(GUIDE.read_text(encoding="utf-8")))
    assert PLACEHOLDERS == () and len(FILLS) == 13
    assert found == [], found
    assert in_guide == [], in_guide


def test_the_baseline_states_one_verdict_for_each_case():
    doc = _flat_body(_raw(), BASELINE)
    verdicts = doc.split("The verdicts, one for each case: ", 1)[1].split(" The runs of SC-DRIVING-014", 1)[0]
    words = {"fail": "a fail", "inconclusive": "inconclusive", "pass": "a pass"}
    for case, verdict in VERDICTS.items():
        assert case in verdicts, case
    for verdict, word in words.items():
        cases = [case for case, value in VERDICTS.items() if value == verdict]
        listed = ", ".join(cases[:-1]) + (" and " if len(cases) > 1 else "") + cases[-1]
        assert f"{listed} {word}" in verdicts, (verdict, listed)


#: the drop counts of the evidence directory, which the baseline's figures of the dropped images restate
DROP_COUNTS = ROOT / "implementation" / "driver-assistance-bench" / "evidence" / "s1-20261121T014447Z" / "drop_counts.json"
#: the 14 runs of SC-DRIVING-012 to SC-DRIVING-015 in S1, by their label in the drop counts
JUDGED_RUN_LABELS = ("012_20_r1", "012_20_r2", "012_42_r1", "012_42_r2", "012_60_r1", "012_60_r2", "013_30_r1",
                     "013_30_r2", "013_60_r1", "013_60_r2", "014_30_r1", "014_30_r2", "015_40_r1", "015_40_r2")


def test_the_baseline_states_where_the_images_drop_and_no_rate():
    """The correction of 2026-11-21: the baseline, the gaps and the guide state where the images drop, as
    drop_counts.json places them, never a rate, and claim no cause; the addition keeps every image from a run's first
    image on."""
    assert DROP_COUNTS.is_file(), "the evidence directory has no drop_counts.json"
    counts = json.loads(DROP_COUNTS.read_text(encoding="utf-8"))
    judged = [counts[label] for label in JUDGED_RUN_LABELS]
    start = " or ".join(str(n) for n in sorted({c["droppedInFirst5s"] for c in judged}))
    inside = max(len(c["wholeRunWindow"]["isolatedDropsS"]) for c in judged)
    # the five inconclusive cases read the 14 runs and the run that stops the path; the steering calibration run
    # (34 in its first 5 s) is read by none of them, so no sentence says "every run" (review P1 of 2026-11-21)
    read = " or ".join(str(n) for n in sorted({c["droppedInFirst5s"] for c in judged + [counts["stop"]]}))
    assert counts["calib_steer"]["droppedInFirst5s"] not in {c["droppedInFirst5s"] for c in judged}
    assert (f"each of the 14 runs and the run that stops the path drops {read} camera images in the first 5 s after "
            "its first image") in FILLS[2]
    gpu = (f"on which each of the 14 runs of SC-DRIVING-012 to SC-DRIVING-015 drops {start} camera images in the "
           f"first 5 s after its first image and up to {inside} more inside the run, with no cause shown")
    assert gpu in FILLS[5]
    # the stop clauses: after the stop the interface drops the images that the candidate no longer takes, so
    # a camera path that keeps every image does not make them judgeable (review P3 of 2026-11-21)
    assert counts["stop"]["droppedAtStreamEnd"] > 0 and counts["stop"]["lastImageSimS"] < counts["stop"][
        "wholeRunWindow"]["lastTickSimS"], "the stop run's image stream ends, with drops, before its last world tick"
    stop_clauses = ("for the stop clauses of VC-DRIVING-038 and VC-DRIVING-043 a judged window that ends at the stop "
                    "instant or a camera input that stops with the candidate, since after the stop the interface "
                    "drops the images that the candidate no longer takes")
    assert "a camera path that keeps every image from a run's first image on" in FILLS[4]
    assert stop_clauses in FILLS[4]
    texts = {"framing": _flat(re.sub(r"(?m)^\s*\*\s?", "", _raw())), "guide": _flat(GUIDE.read_text(encoding="utf-8"))}
    for where, text in texts.items():
        for retired in ("in 20", "one camera image in", "1 image in", "keeps every image, so that",
                        "every run drops", "Every run drops"):
            assert retired not in text, (where, retired)
    guide = texts["guide"]
    assert (f"Each of the 14 runs and the run that stops the path drops {read} camera images in the first 5 s after "
            "its first image, and for the five inconclusive cases the judged window is the whole run.") in guide
    assert gpu in guide
    assert stop_clauses in guide
    # the guide's verdict table states the commanded deceleration, never "no braking" (the correction of 2026-11-21);
    # over the five judged runs the bound is 0.46 m/s² (test_the_five_judged_runs_of_sc_driving_012_...)
    assert ("| VC-DRIVING-036 | fail | In the five judged runs of SC-DRIVING-012 the candidate commands no "
            "deceleration stronger than 0.46 m/s²; the contact comes at ") in GUIDE.read_text(encoding="utf-8")


#: the rows of the guide's verdict table that state figures, each figure from the evidence directory: the impact
#: speeds that VC-DRIVING-037 measured (review Q9) and the stop clause from the stop instant of path_stop.json
#: (review Q1 of 2026-11-21)
GUIDE_ROWS = (
    "| VC-DRIVING-036 | fail | In the five judged runs of SC-DRIVING-012 the candidate commands no deceleration "
    f"stronger than 0.46 m/s²; the contact comes at {IMPACT_LIST} km/h. |",
    f"| VC-DRIVING-037 | fail | The same runs: the impact speeds are {IMPACT_LIST} km/h. |",
    "| VC-DRIVING-038 | inconclusive | No run is judged by the rule on dropped images. Its stop clause is "
    f"inconclusive by the same rule: {STOP_CLAUSE.replace(' camera images', ' images').replace(' of simulation time', '')}. |",
)
#: readings that the records do not bear out (review Q1, Q2, Q8, Q9 and Q10 of 2026-11-21)
RETIRED_READINGS = ("meet their entry conditions", "the stop came at about 2871", "at the approach speed (",
                    "the contact comes at the approach speed", "the speed at the contact is the approach speed",
                    "settled at the target's speed", "every run of S1 drops", "which ends at the stop,",
                    "so that the criteria over every run can be judged, and")


def test_the_figures_of_the_baseline_come_from_the_evidence_directory():
    """Review Q1, Q5, Q8, Q9 and Q10 of 2026-11-21: the stop came at the stop instant of path_stop.json, not at the
    last dropped image; six runs are judged; the contact speeds are stated, not called the approach speed; the
    judged run of SC-DRIVING-013 ends slower than the target; and VC-DRIVING-042 fails for its own reason."""
    assert "simS" in STOP_INSTANT, "drop_counts.json states no stop instant of the run that stops the path"
    assert STOP_INSTANT["file"] == "score/out/path_stop_stop/path_stop.json"
    assert STOP_INSTANT["simS"] < _COUNTS["stop"]["lastImageSimS"] - 0.5, "the stop comes before the last image"
    assert JUDGED == ["012_20_r1", "012_42_r1", "012_42_r2", "012_60_r1", "012_60_r2", "013_30_r1"], JUDGED
    assert not any(e["run"].startswith(("014_", "015_")) for e in _case_runs("VC-DRIVING-036")), \
        "the runs of SC-DRIVING-014 and SC-DRIVING-015 have no judged-run term"
    assert len(JUDGED_012) == 5 and len(IMPACTS) == 5
    approach = {e["run"]: e["measured"]["approachKmh"] for e in _case_runs("VC-DRIVING-037") if e["run"] in JUDGED_012}
    assert min(approach.values()) < 21.0 and float(IMPACTS[0]) < 20.0, \
        "19.7 km/h lies below the band of 20 to 22 km/h: no text calls the contact speeds the approach speed"
    assert "egoSpeedAtLastTickKmh" in RUN_END_013, "drop_counts.json states no speed at the run's last tick"
    assert RUN_END_013["egoSpeedAtLastTickKmh"] < RUN_END_013["targetSpeedAtLastTickKmh"] - 1.0, RUN_END_013
    # the bound of the five judged runs and the bound of the desk analysis, each from its file
    strongest = max(_evidence("commanded_deceleration.json")["runs"][run]["strongestDecelerationMps2"]
                    for run in JUDGED_012)
    assert math.ceil(round(strongest, 9) * 100) / 100 == 0.46, strongest
    assert "no deceleration stronger than 0.46 m/s²" in FILLS[2] and "0.46 m/s²" in FILLS[6]
    assert "0.1 s of simulation time" in _evidence("analysis_039.generator.json")["claimBoundary"]
    assert "a delay of up to 0.1 s of simulation time goes unseen" in FILLS[2]
    starts = {e["run"]: e["measured"].get("warningStarts") for e in _case_runs("VC-DRIVING-042")
              if e["run"] in JUDGED_012}
    assert starts == {run: 0 for run in JUDGED_012}, "VC-DRIVING-042 fails since no judged run starts a warning"
    framing = _flat(re.sub(r"(?m)^\s*\*\s?", "", _raw()))
    guide = _flat(GUIDE.read_text(encoding="utf-8"))
    for row in GUIDE_ROWS:
        assert row in GUIDE.read_text(encoding="utf-8"), row
    # no sentence gives VC-DRIVING-042 the deceleration bound as its reason (review Q5)
    for text in (framing, guide):
        assert "VC-DRIVING-036, VC-DRIVING-037 and VC-DRIVING-042 a fail, since" not in text
    readme = _flat((EVIDENCE / "README.md").read_text(encoding="utf-8"))
    for where, text in (("framing", framing), ("guide", guide), ("README", readme)):
        for retired in RETIRED_READINGS:
            assert retired not in text, (where, retired)


def test_no_text_counts_the_14_runs_as_judged_runs():
    """The wording rule of 2026-11-21, as review Q8 corrected it: of the 14 runs of SC-DRIVING-012 to SC-DRIVING-015
    six are judged runs, and SC-DRIVING-014 and SC-DRIVING-015 have no judged-run term, so no text calls the 14 judged
    runs and none says that 10 of them meet their entry conditions."""
    readme = ROOT / "implementation" / "driver-assistance-bench" / "evidence" / "s1-20261121T014447Z" / "README.md"
    texts = {path.name: _flat(re.sub(r"(?m)^\s*\*\s?", "", path.read_text(encoding="utf-8"))) for path in SLICES}
    texts["guide"] = _flat(GUIDE.read_text(encoding="utf-8"))
    texts["README"] = _flat(readme.read_text(encoding="utf-8"))
    for where, text in texts.items():
        for retired in ("14 judged runs", "fourteen judged runs", "Each judged run drops", "in each judged run (",
                        "(10 of them meet their entry conditions)", "meet their entry conditions"):
            assert retired not in text, (where, retired)
    assert JUDGED_RUNS_PHRASE in texts[MODEL.name]
    assert texts["guide"].count(JUDGED_RUNS_PHRASE) == 2, "the evidence of phase 10 and the baseline"
    assert JUDGED_RUNS_PHRASE.split("the 14 runs of SC-DRIVING-012 to SC-DRIVING-015 ")[1] in texts["README"]
