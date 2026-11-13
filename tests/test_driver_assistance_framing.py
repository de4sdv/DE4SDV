"""Content pins for the framing of the driver-assistance increment, not semantic validation.

The framing of INC-DRIVING-002 is Phase 0 only. These tests hold its structure to the
method's Phase 0 shape, pin each decided statement by its own phrase, and hold the guide
and the VisionPilot section of the folder's upstream record to the model. They read the
model text; they do not parse SysML.

What they do not hold: a sentence that no pin names can change inside a doc of the model
or inside that section, and a report of a run in words that the scan for past behavior
does not list passes. Those are for the review of the text.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

from sysml_shapes import braced_body, strip_comments

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
    "gapCandidateAdmission": "No admission",
    "gapUpstreamContactAndRights": "No upstream contact and no rights clearance",
    "gapDriverHmiInProductLine": "The HMI display's place in the product line",
}
#: a past form of what a candidate does in a run: a framing reports no run
PAST_BEHAVIOR = re.compile(r"(?i)\b(?:braked|warned|stopped|collided|avoided|detected|passed|failed)\b")
#: an affirmative claim of approval or admission
APPROVAL = re.compile(r"(?i)\b(?:compliant|complies|certified|homologated|type-approved|admitted)\b")


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
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1)) == [PACKAGE], \
        "the charter names only the package that holds content today"
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
                   "This package holds only Phase 0."):
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
    assert "disposition" not in code, "a gap has no disposition before the baseline decision of phase 11"
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


def test_the_framing_view_frames_the_boundary_and_exposes_every_usage():
    code = _code()
    boundary = braced_body(code, "concern driverAssistanceBoundary : IncrementBoundaryConcern")
    lines = [line.strip() for line in boundary.splitlines() if line.strip()]
    assert lines[0] == "subject increment : DriverAssistanceIncrement;"
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*(\w+)\s*;", boundary) == ["SystemsEngineer", "VerificationEngineer"]
    assert dict(re.findall(r"\bconcern\s+(\w+)\s*:\s*(\w+)\s*\{", code)) == {
        "driverAssistanceBoundary": "IncrementBoundaryConcern"}, "Phase 0 frames the boundary concern only"

    view = braced_body(code, "view driverAssistanceFramingView")
    viewpoint = braced_body(view, "viewpoint driverAssistanceFramingViewpoint : IncrementFramingViewpoint")
    assert re.findall(r"\bframe\s+(\w+)\s*;", viewpoint) == ["driverAssistanceBoundary"]
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
    for phrase in ("Phase 0 framing only", "no implementation", "no runtime result", "no product-line",
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
    assert "**Status: Phase 0 framing proposal.**" in guide
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
    for phrase in ("No implementation, run, result, product-line admission or compliance is claimed.",
                   "The additions are named from the requirements that fail and from the gaps of this increment; "
                   "the increment builds none of them.",
                   "It is no statement about compliance or type approval.",
                   "Starting this increment launches no compute and authorizes no spend.",
                   "The framing's boundary concern does not open Phase 1.",
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
    # commit, the licence, and the files that the gaps rest on. It restates no pull request of the project and no
    # reading of DE4SDV's own; the questions for the maintainers and the contact stand in the record's shared sections.
    assert not FORMER_RECORD.exists(), "one upstream record for the folder"
    record = UPSTREAM_RECORD.read_text(encoding="utf-8")
    assert record.startswith("# Driving: upstream provenance\n")
    intro = _flat(record.split("\n## ", 1)[0])
    assert ("The VisionPilot section and the statements about VisionPilot belong to INC-DRIVING-002; the rest of the "
            "record belongs to INC-DRIVING-001.") in intro, "the record says whose each statement is"
    section = _record_section(record, "VisionPilot")
    pinned = re.findall(r"github\.com/autowarefoundation/vision_pilot/(?:blob|tree)/([^/)\s]+)", record)
    assert len(pinned) == 11 and set(pinned) == {PIN}, "every file link of the record is at the inspected commit"
    assert len(re.findall(r"github\.com/autowarefoundation/vision_pilot/(?:blob|tree)/", section)) == 11, \
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
