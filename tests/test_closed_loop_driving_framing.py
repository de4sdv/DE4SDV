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
FUNCTIONAL_PACKAGE = "DE4SDV_ClosedLoopDrivingFunctionalArchitecture"
LOGICAL_PACKAGE = "DE4SDV_ClosedLoopDrivingLogicalArchitecture"
PHYSICAL_PACKAGE = "DE4SDV_ClosedLoopDrivingPhysicalSoftwareRealization"
VARIABILITY_PACKAGE = "DE4SDV_ClosedLoopDrivingVariabilityConfiguration"
EVIDENCE_PACKAGE = "DE4SDV_ClosedLoopDrivingVerificationEvidence"


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
        PACKAGE, CONTEXT_PACKAGE, CLASSIFICATION_PACKAGE, NEEDS_PACKAGE, FUNCTIONAL_PACKAGE, LOGICAL_PACKAGE,
        PHYSICAL_PACKAGE, VARIABILITY_PACKAGE, EVIDENCE_PACKAGE]
    assert "frame closedLoopDrivingBoundary;" in code
    assert "viewpoint closedLoopDrivingFramingViewpoint : IncrementFramingViewpoint" in code
    assert "expose closedLoopDrivingCharter;" in code


def test_phase_zero_keeps_risks_and_nonclaims_visible():
    raw = MODEL.read_text(encoding="utf-8")
    code = strip_comments(raw)
    expected = {
        "asmEngineeringUse": ("IncrementAssumption", ("System 1", "System 2", "not production-ready")),
        "asmSourceAuthenticity": ("IncrementAssumption", ("pinned checkpoint", "synthetic-input", "not substitutes",
                                                          "one bounded deviation (owner decision of 2026-11-09)",
                                                          "GAP-DRIVING-010 records the deviation")),
        "asmCandidateReuse": ("IncrementAssumption", ("reuse candidate", "not trajectory", "not safety")),
        "gapClosedLoopPerformance": ("IncrementGap", ("20 fresh", "24 fps", "inference cadence", "real-time factor", "input-to-actuation age", "unmeasured")),
        "gapModelInputAndFeedback": ("IncrementGap", ("calibration", "history", "acceleration/curvature", "domain shift",
                                                      "read through the bounded deviation of asmSourceAuthenticity")),
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


# -- phase 11: the baseline decision ------------------------------------------------------------------------------

DRIVING = MODEL.parent
GUIDE = ROOT / "docs/guides/closed-loop-driving-increment.md"
BASELINE = "part closedLoopDrivingBaselineDecision : IncrementBaselineDecision"
#: The disposition the baseline decision gives each gap record of the increment: the six framing gaps by name, the
#: others by short name. An accepted gap stays open as a known limit; a deferred one moves to a later increment.
GAP_DISPOSITIONS = {
    "gapClosedLoopPerformance": "accepted",
    "gapModelInputAndFeedback": "accepted",
    "gapTransportAndControl": "deferred",
    "gapProductLineAdmission": "deferred",
    "gapAdoptionAndRights": "deferred",
    "gapBoundedCloudCampaign": "deferred",
    "GAP-DRIVING-001": "deferred",
    "GAP-DRIVING-003": "deferred",
    "GAP-DRIVING-006": "deferred",
    "GAP-DRIVING-007": "deferred",
    "GAP-DRIVING-009": "deferred",
    "GAP-DRIVING-010": "accepted",
    "GAP-DRIVING-011": "accepted",
    "GAP-DRIVING-012": "accepted",
    "GAP-DRIVING-013": "accepted",
}
#: What the baseline decision states, in its order: what it accepts, what it does not, the gaps under their
#: dispositions, and the claims it does not make. The figures are those of the recorded runs, which are not in the
#: repository; the bench's verdicts on them are drafts.
BASELINE_STATEMENTS = (
    "BL-DRIVING-001-P11.",
    "The baseline of INC-DRIVING-001 accepts the closed-loop driving integration as built: the model of phases "
    "0 to 10 and the bench that implements it.",
    "The pinned AutoE2E checkpoint plans inside an Eclipse S-CORE FEO agent, its commands reach the simulated "
    "vehicle through the actuation adapter alone, and plan, vehicle state and health reach the observer on the "
    "IVI VM of AAOS SDV as a typed message.",
    "This answers the framing decision (closedLoopDrivingDecision): the integration is retained, on the drafts "
    "named below and not on evidence of record.",
    "It accepts no evidence.",
    "The increment closes without evidence records: the owner ended its runs on 2026-11-11, the recorded runs "
    "were made on the bench's branches before the merge, and the merged bench has not run.",
    "Every verification case and every requirement keeps NotStarted.",
    "The verdicts of the bench's evaluators are drafts: in the three closed-loop runs after the corrections of "
    "GAP-DRIVING-012, 12 of the 23 cases those runs judge pass in all three, VC-DRIVING-001 fails in two, and "
    "VC-DRIVING-002, -005, -011, -012, -016 and -033 are inconclusive in all three for evidence the runs did "
    "not record.",
    "Twelve cases have no pass and no fail in any recorded run: those six and VC-DRIVING-035, inconclusive "
    "wherever they were judged; VC-DRIVING-014, -024 and -028, whose faults no run injected; and VC-DRIVING-018 "
    "and -019, whose runs were not made.",
    "Accepted as known limits, still open in this baseline: the bounded deviation of the motion history "
    "(GAP-DRIVING-010), the route from which the checkpoint takes no turn (GAP-DRIVING-011), the lane it does "
    "not keep (GAP-DRIVING-012), the planning period kept with almost no margin (GAP-DRIVING-013), the "
    "performance limits of gapClosedLoopPerformance and the input and feedback limits of "
    "gapModelInputAndFeedback.",
    "Deferred to a later increment: FEO outside the pinned S-CORE baseline (GAP-DRIVING-001), the unproven "
    "parity of the planner stack (GAP-DRIVING-003), the evidence of record for the typed topic "
    "(GAP-DRIVING-006), the three-host bench on the merged tree (GAP-DRIVING-007), the environment's identity "
    "in the evidence record (GAP-DRIVING-009), the runs gapTransportAndControl still asks for, the member "
    "decision of gapProductLineAdmission, the clearances of gapAdoptionAndRights and the campaign of "
    "gapBoundedCloudCampaign.",
    "No gap is withdrawn.",
    "No driving-quality, real-time, safety, certification, compliance, homologation or membership claim follows "
    "from this baseline, and no acceptance of evidence.",
    "The bench is engineering equipment, and its sensors and vehicle dynamics are simulated.",
)
#: What each framing gap says at the baseline: what the increment answered and what stays open.
FRAMING_GAP_BASELINE_STATEMENTS = {
    "gapClosedLoopPerformance": (
        "At the baseline decision: the planning period is measured on the bench host, and GAP-DRIVING-013 "
        "states the runs and their margin.",
        "The rendered frame rate and the capture rate of the simulator are not judged: no requirement and no "
        "verification case carries the 20 rendered frames per second or the 24 fps capture target.",
        "Nothing measured is real-time operation on target hardware or a performance promise "
        "(counterClaimNoRealTimeOnTarget).",
        "Accepted as a known limit; the gap stays open.",
    ),
    "gapModelInputAndFeedback": (
        "At the baseline decision: the conversions between the simulator and the checkpoint are realized where "
        "phase 8 placed them (phase8ConversionPlacement) and ran in the closed loop.",
        "The runs found two errors of the bench, one in the control conversion and one in the actuation "
        "conversion, and both were corrected (GAP-DRIVING-012).",
        "What this gap warned of holds: with matching interfaces the pinned checkpoint needs the bounded "
        "deviation of its motion history (GAP-DRIVING-010), takes no turn from the route (GAP-DRIVING-011) and "
        "keeps no lane (GAP-DRIVING-012).",
        "The degraded-input cases cover the faults they inject and no other (counterClaimBoundedFaults).",
        "Accepted as a known limit; the gap stays open.",
    ),
    "gapTransportAndControl": (
        "At the baseline decision: the design this gap asks for exists.",
        "S-CORE is on the functional path (phase8TransportSettled), the observer on the IVI VM consumed the "
        "typed plan, vehicle state and health in two runs (GAP-DRIVING-006), and REQ-DRIVING-020 to "
        "REQ-DRIVING-029 define the stop response.",
        "The evidence it asks for is incomplete: no recorded run has judged that plans and commands pass over "
        "S-CORE (VC-DRIVING-014), the stop on lost commands (VC-DRIVING-028), or that planning is independent "
        "of the observation (VC-DRIVING-018 and VC-DRIVING-019).",
        "Deferred to a later increment with those runs.",
    ),
    "gapProductLineAdmission": (
        "At the baseline decision: phase 3 classified the capability and named the owner scope decisions "
        "(memberDecisionScopeInputs), and phase 9 gave DRIVING-CONFIG-001, a valid configuration that is not "
        "admitted.",
        "The member decision that amends ADR 0014 has not been made, and this baseline admits no member product "
        "(counterClaimNoMembership).",
        "Deferred to a later increment.",
    ),
    "gapAdoptionAndRights": (
        "At the baseline decision: DE4SDV posted in the upstream repositories on 2026-11-11 (upstream.md of "
        "this folder, Upstream contact).",
        "No adoption approval and no rights clearance exists, and the checkpoint's terms stay unresolved "
        "(counterClaimCheckpointRightsAndTransfer).",
        "Deferred to a later increment.",
    ),
    "gapBoundedCloudCampaign": (
        "At the baseline decision: the owner authorized the campaign and its runs were made.",
        "The owner ended the runs of this increment on 2026-11-11 and keeps the remaining allowance for a later "
        "increment; the machines are stopped, not deleted.",
        "Deferred with that allowance: a further paid run needs the same conditions.",
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
    for path in sorted(DRIVING.glob("*.sysml")):
        code = strip_comments(path.read_text(encoding="utf-8"))
        for short, name in re.findall(r"\bpart\s+(?:<'([^']+)'>\s+)?(\w+)\s*:\s*IncrementGap\s*\{", code):
            declaration = f"part <'{short}'> {name} : IncrementGap" if short else f"part {name} : IncrementGap"
            assert (short or name) not in records, short or name
            records[short or name] = braced_body(code, declaration)
    return records


def test_the_increment_has_one_baseline_decision_beside_its_framing_decision():
    codes = {path.name: strip_comments(path.read_text(encoding="utf-8")) for path in sorted(DRIVING.glob("*.sysml"))}
    declared = [(name, found) for name, code in codes.items()
                for found in re.findall(r"\bpart\s+(\w+)\s*:\s*(?:\w+::)?IncrementBaselineDecision\b", code)]
    assert declared == [(MODEL.name, "closedLoopDrivingBaselineDecision")], "exactly one, in the framing package"
    code = codes[MODEL.name]
    body = braced_body(code, BASELINE)
    assert re.findall(r"\battribute\s*:>>\s*disposition\s*=\s*LifecycleDisposition::(\w+)\s*;", body) == ["accepted"]
    assert "private import DE4SDV_MethodContext::*;" in code
    assert not re.search(r"\bpart def \w*(?:Baseline|Lifecycle)Decision\b", code), "the type comes from the kernel"
    # the framing decision of phase 0 names the decision the increment supports; it is no baseline decision
    assert "disposition" not in braced_body(code, "part closedLoopDrivingDecision : IncrementLifecycleDecision")
    exposed = re.findall(r"\bexpose\s+(\w+)\s*;", braced_body(code, "view closedLoopDrivingFramingView"))
    assert exposed.index("closedLoopDrivingBaselineDecision") == exposed.index("closedLoopDrivingDecision") + 1, \
        "the framing view shows the baseline decision beside the framing decision"


def test_the_baseline_decision_states_what_it_accepts_and_what_it_does_not():
    raw = MODEL.read_text(encoding="utf-8")
    assert BASELINE in strip_comments(raw), "the increment has no baseline decision"
    doc = _flat_body(raw, BASELINE)
    assert doc.startswith("doc /* BL-DRIVING-001-P11. The baseline of INC-DRIVING-001 accepts"), doc[:80]
    _in_order(BASELINE_STATEMENTS, doc, "baseline")
    for claim in ("is verified", "are verified", "is proven", "meets REQ-", "certified", "evidence of record exists"):
        assert claim not in doc, claim


def test_every_gap_of_the_increment_states_the_disposition_the_baseline_gives_it():
    stated = {key: re.findall(r"\battribute\s*:>>\s*disposition\s*=\s*LifecycleDisposition::(\w+)\s*;", body)
              for key, body in _gap_records().items()}
    assert stated == {key: [disposition] for key, disposition in GAP_DISPOSITIONS.items()}


def test_the_baseline_decision_names_every_gap_under_its_disposition():
    raw = MODEL.read_text(encoding="utf-8")
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
    raw = MODEL.read_text(encoding="utf-8")
    closing = {"accepted": "Accepted as a known limit; the gap stays open.", "deferred": "Deferred"}
    assert set(FRAMING_GAP_BASELINE_STATEMENTS) == {key for key in GAP_DISPOSITIONS if not key.startswith("GAP-")}
    for name, statements in FRAMING_GAP_BASELINE_STATEMENTS.items():
        doc = _flat_body(raw, f"part {name} : IncrementGap")
        assert statements[0].startswith("At the baseline decision: "), name
        assert statements[-1].startswith(closing[GAP_DISPOSITIONS[name]]), (name, statements[-1])
        _in_order(statements, doc, name)
        assert doc.count("At the baseline decision: ") == 1, name
        assert doc.index(statements[0]) > 150, f"{name}: the framing text stays first"


def test_the_guide_describes_the_baseline_and_what_it_defers():
    guide = GUIDE.read_text(encoding="utf-8")
    assert "## Baseline (Phase 11)" in guide, "the guide has no baseline section"
    assert guide.index("## Verification and evidence (Phase 10)") < guide.index("## Baseline (Phase 11)") \
        < guide.index("## Next obligation and execution limits")
    section = " ".join(guide.split("## Baseline (Phase 11)")[1].split("\n## ")[0].split())
    for text in ("`closedLoopDrivingBaselineDecision` (BL-DRIVING-001-P11)", "each of the 15 gap records",
                 "**Accepted: the integration as built.**", "**No evidence is accepted.**",
                 "the merged bench has not run", "Every case is Not started and every requirement keeps NotStarted",
                 "12 of the 23 cases", "VC-DRIVING-001 fails in two", "Twelve cases have no pass and no fail",
                 "**Withdrawn.** None.", "implementation/closed-loop-driving-bench/README.md#known-limits"):
        assert text in section, text

    def named(bullet: str) -> set[str]:
        numbers = set(re.findall(r"-(0\d\d)\b", bullet))
        for first, last in re.findall(r"GAP-DRIVING-(\d{3}) to GAP-DRIVING-(\d{3})", bullet):
            numbers |= {f"{number:03d}" for number in range(int(first), int(last) + 1)}
        return {f"GAP-DRIVING-{number}" for number in numbers} | set(re.findall(r"`(gap\w+)`", bullet))

    bullets = dict(re.findall(r"- \*\*([^*]+)\*\* (.*?)(?= - \*\*| The bench's own)", section))
    assert len(GAP_DISPOSITIONS) == 15
    for title, disposition in (("Known limits: accepted, still open.", "accepted"),
                               ("Deferred to a later increment.", "deferred")):
        expected = {key for key, value in GAP_DISPOSITIONS.items() if value == disposition}
        assert named(bullets[title]) == expected, title
    flat = " ".join(guide.split())
    assert "**Status: baselined (Phase 11).**" in flat and "physical/software realization, proposal" not in flat
    assert "The increment ended at its baseline decision." in flat and "The next work is" not in flat
    assert "(../../implementation/closed-loop-driving-bench/README.md)" in guide, "the guide links the bench"
