"""Content pins for the framing of the driver-assistance increment, not semantic validation.

The framing of INC-DRIVING-002 is Phase 0 only. These tests hold its structure to the
method's Phase 0 shape, pin each decided statement by its own phrase, and hold the guide
and the upstream record to the model. They read the model text; they do not parse SysML.
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
PACKAGE = "DE4SDV_DriverAssistanceFraming"
IDENTITY = "INC-DRIVING-002"
PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"

DOC = re.compile(r"\bdoc\s*/\*(.*?)\*/", re.DOTALL)
#: a usage declared at package level (two spaces of indent), with an optional short name
PACKAGE_USAGE = re.compile(r"(?m)^  (part|requirement|concern)\s+(?:<'[^']*'>\s*)?(\w+)\s*:\s*(\w+)")

#: in-scope item -> the statement it makes
IN_SCOPE = {
    "vehicleTargetResponseInScope":
        "Warning and braking for a stationary and for a slower moving vehicle target ahead.",
    "noReactionInScope": "Two scenarios in which neither a warning nor braking is due.",
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
        "Presentation of the warning to a driver. The increment judges the warning request at the system "
        "boundary.",
    "existingAEBSOutOfScope": "Changing the Autoware-based AEBS or reusing its evidence for this candidate.",
    "candidateTuningOutOfScope":
        "Training the candidate's networks, or tuning the candidate or a scenario until a case passes.",
    "onRoadOperationOutOfScope":
        "On-road operation, production readiness, safety approval, compliance, type approval or certification.",
}
#: assumption -> the phrase that states its premise
ASSUMPTIONS = {
    "asmSimulatorPathUsable": "works with the simulator release of the driving bench",
    "asmProcessorInferenceSufficient": "run on a processor alone, without a graphics card",
    "asmBenchReuse": "Their results for the first application are not evidence for this one.",
    "asmSimulatedConfigurationStandsIn": "A verdict holds for that simulated configuration only.",
}
#: gap -> the phrase that states what is open
GAPS = {
    "gapVehicleTargetCriteria": "None exists for a vehicle target.",
    "gapNoSeparateEmergencyFunction": "It has no emergency function apart from that planner.",
    "gapWarningOutput": "That interface carries no warning.",
    "gapCandidateBehaviorUnverified": "No closed-loop result of the application exists on the DE4SDV bench.",
    "gapScoreIntegration": "no binding to Eclipse S-CORE communication and no S-CORE supervision",
    "gapCameraImageAndGeometry": "The simulator's images differ from them.",
    "gapCandidateAdmission": "This increment admits no member and changes no scope decision.",
    "gapUpstreamContactAndRights": "The upstream maintainers are not yet involved.",
}


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
    return set(re.findall(rf"\bpart\s+(\w+)\s*:\s*{kind}\b", _code()))


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
                   "DE4SDV does not know whether its warning and braking meet those requirements",
                   "the model holds no regulation-derived criteria for a vehicle target"):
        assert phrase in problem, phrase
    question = _doc("part driverAssistanceQuestion : IncrementEngineeringQuestion")
    for phrase in ("with its commands on the Eclipse S-CORE path of the driving bench",
                   "meet the product line's requirements to warn of and to brake for a vehicle target",
                   "criteria derived from UNECE R152 judge its closed-loop behavior in simulation",
                   "Where it does not, what does the platform have to add?",
                   "A verdict for each requirement and scenario answers this.",
                   "A recording of a run that looks right does not."):
        assert phrase in question, phrase
    decision = _doc("part driverAssistanceDecision : IncrementLifecycleDecision")
    for phrase in ("whose own warning and braking stand for the common capability",
                   "a candidate that needs named additions from the platform, or not at all",
                   "executed cases with a pass or a fail for each requirement of the increment",
                   "A fail is a result to record.",
                   "no reason to change a scenario or a criterion until the candidate passes"):
        assert phrase in decision, phrase
    system = _doc("part def DriverAssistanceSystem")
    for phrase in ("In: the front-camera image and the vehicle speed.",
                   "Out: the driving command and the warning request.",
                   "not a member product",
                   "this increment admits no member to the governed product-line scope"):
        assert phrase in system, phrase
    environment = _doc("part driverAssistanceVerificationEnvironment : System2EngineeringAndAssuranceSystem")
    for phrase in ("They are not vehicle features",
                   "is an instrument here, not a driver warning function"):
        assert phrase in environment, phrase


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
    for phrase in ("for a vehicle target ahead in its lane",
                   "in closed loop with a rendered camera image",
                   "for one configuration and with at most ten requirements",
                   "a stationary target, a slower moving target, and two in which no reaction is due",
                   "Implementation is not part of this framing slice."):
        assert phrase in scope, phrase


def test_assumptions_are_premises_and_gaps_are_open_points():
    code = _code()
    assert _declared("IncrementAssumption") == set(ASSUMPTIONS)
    assert _declared("IncrementGap") == set(GAPS)
    for name, phrase in ASSUMPTIONS.items():
        assert phrase in _doc(f"part {name} : IncrementAssumption"), name
    for name, phrase in GAPS.items():
        assert phrase in _doc(f"part {name} : IncrementGap"), name
    assert "disposition" not in code, "a gap has no disposition before the baseline decision of phase 11"
    # the two premises that a readiness probe discharges say so
    for name in ("asmSimulatorPathUsable", "asmProcessorInferenceSufficient"):
        assert "readiness probe" in _doc(f"part {name} : IncrementAssumption"), name
    criteria = _doc("part gapVehicleTargetCriteria : IncrementGap")
    for phrase in ("cover the pedestrian and the bicycle target",
                   "it defers the promotion of quantified thresholds into System 1 obligations",
                   "It also has to state whose obligation each criterion is."):
        assert phrase in criteria, phrase
    emergency = _doc("part gapNoSeparateEmergencyFunction : IncrementGap")
    for phrase in ("At the inspected revision",
                   "The product line holds a protected emergency command path as common content.",
                   "The lifecycle decision turns on it."):
        assert phrase in emergency, phrase
    warning = _doc("part gapWarningOutput : IncrementGap")
    for phrase in ("At the inspected revision",
                   "writes its steering and its acceleration to its vehicle interface",
                   "The warnings go to the application's own display and to its own data log.",
                   "is an output that the application does not have",
                   "without a change to the application's decision logic, is open"):
        assert phrase in warning, phrase
    unverified = _doc("part gapCandidateBehaviorUnverified : IncrementGap")
    for phrase in ("an error in the speed planner, which the inspected revision still has",
                   "A fail is a likely first result.",
                   "is a different candidate, and its verdicts are reported apart"):
        assert phrase in unverified, phrase
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
    open_points = guide.split("## What the framing already records as open", 1)[1].split("\n## ", 1)[0]
    assert len(re.findall(r"(?m)^- \*\*", open_points)) == len(GAPS), \
        "the guide lists one open point for each gap of the model"
    for phrase in ("No implementation, run, result, product-line admission or compliance is claimed.",
                   "It is no statement about compliance or type approval.",
                   "Starting this increment launches no compute and authorizes no spend.",
                   "The framing's boundary concern does not open Phase 1."):
        assert phrase in flat, phrase


def test_the_upstream_record_pins_what_the_framing_read():
    record = UPSTREAM_RECORD.read_text(encoding="utf-8")
    flat = _flat(record)
    pinned = re.findall(r"github\.com/autowarefoundation/vision_pilot/(?:blob|tree)/([^/)\s]+)", record)
    assert len(pinned) == 13 and set(pinned) == {PIN}, "every file link of the record is at the inspected commit"
    assert f"commit `{PIN}`" in flat
    # what the model's gaps rest on is in the record, in the record's own words
    for phrase in ("The code has no emergency function apart from that planner.",
                   "It carries no warning.",
                   "The inspected commit holds no binding to Eclipse S-CORE communication and no S-CORE supervision.",
                   "DE4SDV has reproduced none of their results.",
                   "None of the three starts from the inspected commit",
                   "The speed planner of the inspected commit takes the relative speed in the same way.",
                   "says that it is trained on the OpenLane dataset",
                   "DE4SDV has built and run nothing of this upstream project.",
                   "The clauses for a vehicle target are not yet anchored there."):
        assert phrase in flat, phrase
    contact = record.split("## Upstream contact", 1)[1]
    assert _flat(contact).startswith("None. DE4SDV has posted nothing in this project")
    index = INDEX.read_text(encoding="utf-8")
    assert "(textual-notation-of-model/packages/features/driving/driver-assistance-upstream.md)" in index
    assert "(https://github.com/autowarefoundation/vision_pilot)" in index
