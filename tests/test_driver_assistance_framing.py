"""Content pins for the framing of the driver-assistance increment, not semantic validation.

The framing of INC-DRIVING-002 is Phase 0 only. These tests hold its structure to the
method's Phase 0 shape, pin each decided statement by its own phrase, and hold the guide
and the upstream record to the model. They read the model text; they do not parse SysML.

What they do not hold: a sentence that no pin names can change inside a doc of the model
or inside the upstream record, and a report of a run in words that the scan for past
behavior does not list passes. Those are for the review of the text.
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
UPSTREAM_RECORD = DRIVING / "driver-assistance-upstream.md"
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
    "noReactionInScope":
        "Two scenarios in which neither a warning nor braking is due, taken from the false-reaction scenarios of "
        "the regulation.",
    "vehicleTargetCriteriaInScope":
        "Criteria for a vehicle target derived from UNECE R152, each with what a simulation cannot show.",
    "scoreCommandPathInScope":
        "The candidate's commands reach the simulated vehicle through Eclipse S-CORE; no bypass.",
    "verdictEvidenceInScope":
        "A pass or a fail for each requirement and scenario, bound to the candidate revision that ran.",
}
#: out-of-scope item -> the statement it makes
OUT_OF_SCOPE = {
    "pedestrianAndBicycleTargetsOutOfScope": "Pedestrian and bicycle targets.",
    "cruiseAndLaneKeepingQualityOutOfScope":
        "How well the candidate holds speed, distance and lane. These functions run; no case judges them.",
    "driverInteractionOutOfScope": "Driver monitoring, driver override and deactivation.",
    "warningPresentationOutOfScope":
        "Presentation of the warning to a driver, and the modes of that warning. The increment judges the warning "
        "request at the system boundary and the time of that request. The product line requires a collision "
        "warning to the driver; this increment answers that requirement in part only.",
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
                      "Their results for the first application are not evidence for this one."),
    "asmSimulatedConfigurationStandsIn": (
        "stand in for the vehicle, the surface and the test target that the source regulation prescribes",
        "A verdict holds for that simulated configuration only."),
}
#: gap -> the phrase that states what is open
GAPS = {
    "gapVehicleTargetCriteria": "None exists for a vehicle target.",
    "gapNoSeparateEmergencyFunction": "It has no emergency function apart from that planner.",
    "gapWarningOutput": "That interface carries no warning.",
    "gapCandidateBehaviorUnverified": "No closed-loop result of the application exists on the DE4SDV bench.",
    "gapScoreIntegration": "no binding to Eclipse S-CORE communication and no S-CORE supervision",
    "gapCameraImageAndGeometry": "The simulator's images are not images of that dataset.",
    "gapCandidateAdmission": "This increment admits no member and changes no scope decision.",
    "gapUpstreamContactAndRights": "The upstream maintainers are not yet involved.",
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
                   "request the warning and command the braking that the product line requires for a vehicle "
                   "target",
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
                   "The Eclipse S-CORE command path that carries the driving command to the actuation is platform "
                   "content of System 1. It is outside this boundary, and it is not an enabling system.",
                   "The candidate is a proposed application system, not a member product",
                   "this increment admits no member to the governed product-line scope"):
        assert phrase in system, phrase
    environment = _doc("part driverAssistanceVerificationEnvironment : System2EngineeringAndAssuranceSystem")
    for phrase in ("CARLA renders the camera image and moves the vehicle and the targets.",
                   "Cloud hosts, the scenario runner, the evaluators and the recordings enable engineering and "
                   "verification. They are not vehicle features and not contents of the candidate System 1 "
                   "boundary.",
                   "it serves as an instrument. The increment does not judge it as a warning to the driver."):
        assert phrase in environment, phrase


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
    for phrase in ("The warning request and the braking of the candidate for a vehicle target ahead in its lane",
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
                   "The warnings go to the application's own display and to its own data log, each only when it "
                   "is switched on.",
                   "is an output that the application does not have",
                   "without a change to the application's decision logic, is open"):
        assert phrase in warning, phrase
    unverified = _doc("part gapCandidateBehaviorUnverified : IncrementGap")
    for phrase in ("lists what the project's own open changes report: an error in the speed planner and "
                   "closed-loop cases that fail",
                   "None of these changes starts from the inspected revision, and DE4SDV has run neither that "
                   "revision nor the changes.",
                   "is a different candidate, and its verdicts are reported apart"):
        assert phrase in unverified, phrase
    # the framing states nothing of its own about a defect of the inspected revision, and forecasts no result
    for phrase in ("inspected revision still has", "likely first result"):
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
    assert "(../../textual-notation-of-model/packages/features/driving/driver-assistance-upstream.md)" in visionpilot
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
                   "../../textual-notation-of-model/packages/features/driving/driver-assistance-upstream.md"):
        assert f"]({target})" in guide, target
    flat = _flat(guide)
    for phrase in ("No implementation, run, result, product-line admission or compliance is claimed.",
                   "The additions are named from the requirements that fail and from the gaps of this increment; "
                   "the increment builds none of them.",
                   "It is no statement about compliance or type approval.",
                   "Starting this increment launches no compute and authorizes no spend.",
                   "The framing's boundary concern does not open Phase 1."):
        assert phrase in flat, phrase
    boundaries = _flat(guide.split("## Boundaries", 1)[1].split("\n## ", 1)[0])
    for phrase in ("The candidate driver-assistance system is a proposed **System 1** subject.",
                   "is platform content of **System 1**: it is outside the candidate's boundary, and it is not an "
                   "enabler.",
                   "CARLA, the cloud hosts, the scenario runner, the evaluators and the recordings are **System 2** "
                   "enablers, not vehicle features.",
                   "it serves as an instrument. The increment does not judge it as a warning to the driver."):
        assert phrase in boundaries, phrase
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


def test_the_upstream_record_pins_what_the_framing_read():
    record = UPSTREAM_RECORD.read_text(encoding="utf-8")
    flat = _flat(record)
    pinned = re.findall(r"github\.com/autowarefoundation/vision_pilot/(?:blob|tree)/([^/)\s]+)", record)
    assert len(pinned) == 14 and set(pinned) == {PIN}, "every file link of the record is at the inspected commit"
    assert f"commit `{PIN}`" in flat
    network = re.findall(r"github\.com/autowarefoundation/auto_speed([^)\s]*)", record)
    assert network == [f"/tree/{AUTOSPEED_PIN}"], "the record links the network's repository at one commit"
    assert f"commit `{AUTOSPEED_PIN}`" in flat
    # what the model's gaps rest on is in the record, in the record's own words
    for phrase in ("Its release tag `v1.2` is commit `9a96c3e771f9e79e91b6ccfcbf2ce860530024c8`, an ancestor of the "
                   "inspected commit.",
                   "The code has no emergency function apart from that planner.",
                   "It carries no warning.",
                   "each only when the application configuration switches it on",
                   "The draft lists warning requests among the outputs of the element.",
                   "The inspected commit holds no binding to Eclipse S-CORE communication and no S-CORE supervision.",
                   "This repository holds no reproduction of their results.",
                   "None of the three starts from the inspected commit.",
                   "Pull requests 427 and 423 branch from the default branch as it was on 2026-09-11.",
                   "The inspected commit holds none of the 123 commits that led to that state",
                   "Pull request 448 branches from the default branch as it was on 2026-10-09.",
                   "for the application's vehicle at 9.4 m/s, a stopped object ahead and a 20 m gap, an "
                   "acceleration of +1.48 m/s² before the change and −3.62 m/s² after it",
                   "runs the loop step of the application, bound to Python and with the pull request's own "
                   "correction of a sign in the lateral control",
                   "the vehicle that cuts in is hit, the pedestrian that steps out is hit and never braked for, "
                   "and the straight junction passes",
                   "Its description lists no warning among their contents.",
                   "says that the AutoSpeed 2.0 network is trained on the OpenLane dataset",
                   "DE4SDV has not checked that the weights in the application's repository are the ones that this "
                   "README describes.",
                   "DE4SDV has built and run nothing of this upstream project.",
                   "The clauses for a vehicle target are not yet anchored there."):
        assert phrase in flat, phrase
    # the record states what the open changes say, and nothing of DE4SDV's own about a defect of the inspected commit
    assert "takes the relative speed in the same way" not in flat
    body, contact = record.split("## Upstream contact", 1)
    assert _flat(contact).startswith("None. DE4SDV has posted nothing in this project")
    # outside that section the record tells of no exchange with the project
    exchange = re.compile(
        r"(?i)\bDE4SDV (?:has )?(?:confirmed|agreed|asked|contacted|told|informed|reported|discussed|posted|opened|"
        r"sent)\b|\b(?:maintainers?|authors?|project) (?:has |have )?(?:confirmed|agreed|answered|replied|approved|"
        r"endorsed)\b|\bwith its author\b")
    assert not exchange.findall(_flat(body)), exchange.findall(_flat(body))
    index = INDEX.read_text(encoding="utf-8")
    assert "(textual-notation-of-model/packages/features/driving/driver-assistance-upstream.md)" in index
    assert "(https://github.com/autowarefoundation/vision_pilot)" in index
