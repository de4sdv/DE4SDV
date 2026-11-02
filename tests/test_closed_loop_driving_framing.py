"""Content pins for the closed-loop driving increment, not semantic validation."""

from pathlib import Path
import re

from sysml_shapes import braced_body, strip_comments

ROOT = Path(__file__).resolve().parents[1]
MODEL = ROOT / "textual-notation-of-model/packages/features/driving/closed_loop_driving_framing.sysml"
PACKAGE = "DE4SDV_ClosedLoopDrivingFraming"
CONTEXT_PACKAGE = "DE4SDV_ClosedLoopDrivingOperationalContext"
CLASSIFICATION_PACKAGE = "DE4SDV_ClosedLoopDrivingCapabilityClassification"
NEEDS_PACKAGE = "DE4SDV_ClosedLoopDrivingNeedsRequirements"


def test_increment_has_its_own_phase_zero_contract():
    assert MODEL.is_file(), "the owner's closed-loop question needs a framing model"
    code = strip_comments(MODEL.read_text(encoding="utf-8"))
    assert "part def ClosedLoopDrivingIncrement :> EngineeringIncrement" in code
    assert re.search(
        r"part\s+<'INC-DRIVING-001'>\s+closedLoopDrivingIncrement\s*:\s*ClosedLoopDrivingIncrement",
        code,
    )
    problem = braced_body(code, "requirement closedLoopDrivingProblem : ProblemStatement")
    assert "subject closedLoopDrivingSubject : ClosedLoopDrivingIncrement;" in problem
    charter = braced_body(code, "part closedLoopDrivingCharter : IncrementCharter")
    assert "ref part :>> increment = closedLoopDrivingIncrement;" in charter
    assert "ref part :>> systemOfInterest = candidateDrivingSystem;" in charter
    assert 'attribute :>> owner = "Orkun Yilmaz";' in charter
    assert "part closedLoopDrivingScope : IncrementScope" in code
    assert re.search(
        r"dependency\s+scopeToDrivingQuestion\s+from\s+closedLoopDrivingScope\s+to\s+closedLoopDrivingQuestion\s*;",
        code,
    )
    assert re.findall(r'MethodPhase::(\w+)', charter) == [
        "phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
        "phase3_capabilityClassification", "phase4_needs", "phase5_requirements",
        "phase6_functionalArchitecture", "phase7_logicalArchitecture",
        "phase8_physicalRealization", "phase9_variabilityConfiguration",
        "phase10_vvEvidence", "phase11_baseline",
    ]
    artifacts = re.search(r"expectedArtifacts\s*=\s*\((.*?)\);", charter, re.S)
    assert artifacts and re.findall(r'"([^"]+)"', artifacts.group(1)) == [
        PACKAGE, CONTEXT_PACKAGE, CLASSIFICATION_PACKAGE, NEEDS_PACKAGE]
    assert "frame closedLoopDrivingBoundary;" in code
    assert "viewpoint closedLoopDrivingFramingViewpoint : IncrementFramingViewpoint" in code
    assert "expose closedLoopDrivingCharter;" in code


def test_phase_zero_keeps_risks_and_nonclaims_visible():
    raw = MODEL.read_text(encoding="utf-8")
    code = strip_comments(raw)
    expected = {
        "asmEngineeringUse": ("IncrementAssumption", ("System 1", "System 2", "not production-ready")),
        "asmSourceAuthenticity": ("IncrementAssumption", ("pinned checkpoint", "synthetic-input", "not substitutes")),
        "asmCandidateReuse": ("IncrementAssumption", ("reuse candidate", "not trajectory", "not safety")),
        "gapClosedLoopPerformance": ("IncrementGap", ("20 fresh", "24 fps", "inference cadence", "real-time factor", "input-to-actuation age", "unmeasured")),
        "gapModelInputAndFeedback": ("IncrementGap", ("calibration", "history", "acceleration/curvature", "domain shift")),
        "gapTransportAndControl": ("IncrementGap", ("S-CORE", "AAOS", "existing AEBS", "control")),
        "gapProductLineAdmission": ("IncrementGap", ("ADR 0014", "Phase 3", "Phase 9")),
        "gapAdoptionAndRights": ("IncrementGap", ("maintainers", "checkpoint", "before deep adoption")),
        "gapBoundedCloudCampaign": ("IncrementGap", ("authorization", "shutdown", "credit")),
    }
    for name, (kind, phrases) in expected.items():
        declaration = f"part {name} : {kind}"
        assert declaration in code, f"missing framing record: {name}"
        documentation = braced_body(raw, declaration)
        normalized = " ".join(re.sub(r"(?m)^\s*\*\s?", "", documentation).split())
        for phrase in phrases:
            assert phrase in normalized, (name, phrase)
    assert "part closedLoopVerificationEnvironment : System2EngineeringAndAssuranceSystem" in code
    assert "OutOfScopeItem" not in braced_body(code, "part closedLoopDrivingScope : IncrementScope")
    assert not re.search(r"\b(?:verify|satisfy)\s+\w+", code)


def test_framing_view_exposes_scope_and_deferred_scope():
    code = strip_comments(MODEL.read_text(encoding="utf-8"))
    scope_items = set(re.findall(
        r"\bpart\s+(\w+)\s*:\s*(?:InScopeItem|OutOfScopeItem)\b", code
    ))
    assert scope_items, "the scope-coverage assertion must not be vacuous"
    view = braced_body(code, "view closedLoopDrivingFramingView")
    exposed = set(re.findall(r"\bexpose\s+(\w+)\s*;", view))
    required = scope_items | {"closedLoopDrivingBoundary"}
    assert required <= exposed, f"framing view omits boundary content: {sorted(required - exposed)}"


#: Phase 1: one concern per question of the in-scope items, typed by the SAF concern whose question it
#: is, with its native stakeholders (owner decision of 2026-11-02: the needs are held by those they serve, not
#: only by the roles that check them; seven concerns, the occupant's added last). The in-scope item each answers
#: is named in its documentation.
PHASE1_CONCERNS = {
    "drivenAlongTheRouteConcern": ("OperationalCapabilityConcern", "learnedDrivingInScope", {
        "occupant": "VehicleOccupant"}),
    "checkpointCommandAuthorityConcern": ("PhysicalFunctionalMappingConcern", "learnedDrivingInScope", {
        "systemsEngineer": "SystemsEngineer", "verificationEngineer": "VerificationEngineer",
        "reviewer": "OpenSourceReviewer"}),
    "scoreCommandPathConcern": ("PhysicalInternalExchangeConcern", "integrationAndObservationInScope", {
        "systemArchitect": "SystemArchitect", "softwareDeveloper": "SoftwareDeveloper",
        "maintainer": "Maintainer"}),
    "aaosObservationFidelityConcern": ("PhysicalContextExchangeConcern", "integrationAndObservationInScope", {
        "occupant": "VehicleOccupant",
        "verificationEngineer": "VerificationEngineer", "reviewer": "OpenSourceReviewer"}),
    "degradedInputBehaviorConcern": ("FunctionalBehaviorConcern", "feedbackAndTimingInScope", {
        "occupant": "VehicleOccupant", "roadUser": "RoadUser",
        "safetyExpert": "SafetyExpert", "systemArchitect": "SystemArchitect"}),
    "timeDomainHonestyConcern": ("ArgumentationAssuranceConcern", "feedbackAndTimingInScope", {
        "verificationEngineer": "VerificationEngineer", "systemsEngineer": "SystemsEngineer"}),
    "reproducibleClosedLoopEvidenceConcern": ("ArgumentationAssuranceConcern", "closedLoopEvidenceInScope", {
        "verificationEngineer": "VerificationEngineer", "maintainer": "Maintainer",
        "reviewer": "OpenSourceReviewer"}),
}


def test_phase_one_frames_a_concern_for_every_in_scope_question():
    raw = MODEL.read_text(encoding="utf-8")
    code = strip_comments(raw)
    assert "private import SAF_Viewpoints::*;" in code
    assert not re.search(r"\b(?:concern|part) def \w*(?:Concern|Engineer|Expert|Architect|Developer|Maintainer)\b", code), \
        "concern types and stakeholders come from SAF and the kernel, never from the slice"
    viewpoint = braced_body(code, "viewpoint closedLoopDrivingFramingViewpoint : IncrementFramingViewpoint")
    view = braced_body(code, "view closedLoopDrivingFramingView")
    declared = dict(re.findall(r"\bconcern\s+(\w+)\s*:\s*(\w+)\s*\{", code))
    assert set(declared) == set(PHASE1_CONCERNS) | {"closedLoopDrivingBoundary"}
    answered = set()
    for name, (kind, scope_item, stakeholders) in PHASE1_CONCERNS.items():
        assert declared[name] == kind, name
        body = braced_body(code, f"concern {name} : {kind}")
        parameters = [line.strip() for line in body.splitlines() if line.strip() and line.strip() != "doc"]
        assert parameters[0] == "subject;", f"{name}: the subject is the first parameter"
        assert dict(re.findall(r"\bstakeholder\s+(\w+)\s*:\s*(\w+)\s*;", body)) == stakeholders, name
        assert f"frame {name};" in viewpoint, f"{name} is not framed by the framing viewpoint"
        assert f"expose {name};" in view, f"{name} is not shown in the framing view"
        documentation = " ".join(re.sub(r"(?m)^\s*\*\s?", "", braced_body(raw, f"concern {name} : {kind}")).split())
        assert scope_item in documentation, f"{name} does not name the in-scope item it answers"
        answered.add(scope_item)
    in_scope = set(re.findall(r"\bpart\s+(\w+)\s*:\s*InScopeItem\b", code))
    assert answered == in_scope, f"in-scope items without a concern: {sorted(in_scope - answered)}"


def test_the_occupant_holds_the_operational_concern_and_the_two_reuse_concerns():
    # Owner decision of 2026-11-02: a need is held by the party it serves, not only by the roles that check it.
    # The occupant's own expectation of being driven along the chosen route is its own concern, answered by the
    # phase 2 story; the AAOS and degraded-input concerns gain the people the question is answered for.
    raw = MODEL.read_text(encoding="utf-8")
    code = strip_comments(raw)
    assert "private import DE4SDV_Stakeholders::*;" in code, "the occupant and road user come from the kernel"
    assert not re.search(r"\bpart def (?:VehicleOccupant|RoadUser)\b", code), "kernel stakeholders are reused"
    assert "private import SAF_Viewpoints::*;" in code
    assert not re.search(r"\bconcern def OperationalCapabilityConcern\b", code)

    occupant_concern = braced_body(code, "concern drivenAlongTheRouteConcern : OperationalCapabilityConcern")
    lines = [line.strip() for line in occupant_concern.splitlines() if line.strip() and line.strip() != "doc"]
    assert lines[0] == "subject;"
    assert re.findall(r"\bstakeholder\s+\w+\s*:\s*\w+\s*;", occupant_concern) == \
        ["stakeholder occupant : VehicleOccupant;"], "the occupant alone holds the operational concern"
    occupant_doc = " ".join(re.sub(r"(?m)^\s*\*\s?", "", braced_body(
        raw, "concern drivenAlongTheRouteConcern : OperationalCapabilityConcern")).split())
    for phrase in ("learnedDrivingInScope", "operational part", "along the route",
                   "chose on navigation", "not how well", "phase 2"):
        assert phrase in occupant_doc, phrase

    holders = {
        "aaosObservationFidelityConcern": ["stakeholder occupant : VehicleOccupant;",
                                           "stakeholder verificationEngineer : VerificationEngineer;",
                                           "stakeholder reviewer : OpenSourceReviewer;"],
        "degradedInputBehaviorConcern": ["stakeholder occupant : VehicleOccupant;",
                                        "stakeholder roadUser : RoadUser;",
                                        "stakeholder safetyExpert : SafetyExpert;",
                                        "stakeholder systemArchitect : SystemArchitect;"],
    }
    #: Each doc opens with its in-scope item, so the first sentence after it must be the holders' own need:
    #: a check for a leading "Reviewers need" would never fire here.
    holder_need = {
        "aaosObservationFidelityConcern": "AAOS part. The driver, a vehicle occupant, needs",
        "degradedInputBehaviorConcern": "behavior part. Vehicle occupants and road users need",
    }
    for name, expected in holders.items():
        body = braced_body(code, f"concern {name}")
        assert re.findall(r"\bstakeholder\s+\w+\s*:\s*\w+\s*;", body) == expected, name
        documentation = " ".join(re.sub(r"(?m)^\s*\*\s?", "", braced_body(raw, f"concern {name}")).split())
        assert holder_need[name] in documentation, f"{name}: the holder states the need first"
    degraded_doc = " ".join(re.sub(r"(?m)^\s*\*\s?", "",
                                   braced_body(raw, "concern degradedInputBehaviorConcern")).split())
    assert "route" in degraded_doc, "degraded input includes the route becoming invalid, lost or stale"
    assert "road users" in degraded_doc

    viewpoint = braced_body(code, "viewpoint closedLoopDrivingFramingViewpoint : IncrementFramingViewpoint")
    assert "frame drivenAlongTheRouteConcern;" in viewpoint
    assert viewpoint.index("frame drivenAlongTheRouteConcern;") < \
        viewpoint.index("frame checkpointCommandAuthorityConcern;")
    view = braced_body(code, "view closedLoopDrivingFramingView")
    assert "expose drivenAlongTheRouteConcern;" in view

    assert "Reviewers need" not in occupant_doc
    story_model = (ROOT / "textual-notation-of-model/packages/features/driving"
                   "/closed_loop_driving_operational_context.sysml").read_text(encoding="utf-8")
    story = braced_body(strip_comments(story_model),
                        "viewpoint closedLoopDrivingStoryViewpoint : OperationalStoryViewpoint")
    assert re.search(r"\bframe\s+(?:[\w.]+::)?drivenAlongTheRouteConcern\s*;", story), \
        "the phase 2 story answers the occupant's concern"
