"""One canonical method evaluation per increment and its three projections.

``status`` (per phase), ``gaps`` (unmet blocking gates plus advisory notes)
and ``next`` (the first actionable gate, ranked by gate prerequisites) come
from one canonical evaluation and carry the same evaluation identity. The
synthetic method below exercises every gate predicate form; it is test data,
not a copy of the model's method gates.
"""

from __future__ import annotations

import pytest

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from increment_model_fixtures import GateSpec, increment_scenario, method_gates
from test_revision_index import _traversal

REVISION = me.RevisionIdentity("a" * 40, "project", "commit", "full-model")
P0, P4, P5, P10 = ("phase0_incrementFraming", "phase4_needs", "phase5_requirements", "phase10_vvEvidence")
UNCONDITIONAL = "unconditional"


def _gate(name, phase, selector, predicate, target_filter="", **kwargs) -> GateSpec:
    return GateSpec(name=name, phase=phase, selector=selector, predicate=predicate,
                    target_filter=target_filter, **kwargs)


def synthetic_method() -> list[GateSpec]:
    framing = dict(applicability=UNCONDITIONAL)
    later = dict(prerequisites=("phases",))
    advisory = dict(required=False, minimum_population=0, permitted_empty=True,
                    disposition="noEligibleSubjects", prerequisites=("phases",))
    return [
        _gate("identity", P0, "incrementIdentifier", "increment-identity",
              "EngineeringIncrement lineage; declared short name equals the increment identifier",
              maximum=1, **framing),
        _gate("charter", P0, "increment", "increment-charter-declaration",
              "IncrementCharter lineage; increment reference resolves to the increment usage",
              maximum=1, prerequisites=("identity",), **framing),
        _gate("problem", P0, "increment", "increment-problem-statement",
              "ProblemStatement lineage; owned by the increment package; native subject typed by the "
              "increment definition", maximum=1, prerequisites=("identity",), **framing),
        _gate("question", P0, "increment", "package-typed-member", "IncrementEngineeringQuestion lineage",
              maximum=1, prerequisites=("identity",), **framing),
        _gate("assumption", P0, "increment", "package-typed-member", "IncrementAssumption lineage",
              prerequisites=("identity",), **framing),
        _gate("scope", P0, "increment", "package-typed-member", "IncrementScope lineage",
              maximum=1, prerequisites=("identity",), **framing),
        _gate("stakeholder", P0, "increment", "problem-statement-stakeholder", "Stakeholder lineage",
              prerequisites=("problem",), **framing),
        _gate("framing", P0, "increment", "package-view-framed-concern",
              "ConcernUsage owned by the increment package; framed by a viewpoint of a view owned by the "
              "same package", prerequisites=("identity",), **framing),
        _gate("owner", P0, "increment", "charter-attribute-value", "IncrementCharter owner; non-empty String",
              maximum=1, prerequisites=("charter",), **framing),
        _gate("phases", P0, "increment", "charter-attribute-value",
              "IncrementCharter applicablePhases; MethodPhase literal", prerequisites=("charter",), **framing),
        _gate("needStatement", P4, "incrementNeeds", "required-constraint",
              "require constraint; framed concerns excluded", **later),
        _gate("needStakeholder", P4, "incrementNeeds", "stakeholder-membership", "Stakeholder lineage", **later),
        _gate("needSource", P4, "incrementNeeds", "requirement-attribute-value",
              "ODE4HERA source; non-empty String", maximum=1, **later),
        _gate("needValidation", P4, "incrementNeeds", "hasValidationScenario",
              "ValidationPlanningScenario lineage; through a ValidationPlanningAssociation connection", **later),
        _gate("needFrames", P4, "incrementNeeds", "framed-concern-membership",
              "ConcernUsage with at least one native stakeholder member", **later),
        _gate("derives", P5, "incrementRequirements", "derivesRequirementFromNeed",
              "StakeholderNeedCandidate lineage; through a DerivesFromNeed connection only; plain "
              "dependencies excluded", **later),
        _gate("oneSubject", P5, "incrementRequirements", "subject-membership", maximum=1, **later),
        _gate("method", P5, "incrementRequirements", "requirement-attribute-value",
              "ODE4HERA verificationMethod; one of inspect, demo, test, analyze", maximum=1, **later),
        _gate("featureTrace", P5, "incrementRequirements", "specifiesFeatureOrCommonCapability",
              "ProductLineFeatureCandidate or CommonProductLineCapability lineage", **advisory),
        _gate("caseVerifies", P10, "incrementVerificationCases", "verifies",
              "requirement usage in the increment requirements population", **later),
        _gate("requirementVerified", P10, "incrementRequirements", "verifiedBy", "VerificationCaseUsage",
              minimum_population=0, permitted_empty=True, disposition="noEligibleSubjects", **later),
        _gate("acceptance", P10, "incrementVerificationCases", "verifies", "AcceptanceCriterion lineage",
              **advisory),
        _gate("evidence", P10, "incrementVerificationCases", "evidence-record-or-status",
              "evidence record referencing the verification case, or an evidence status of the case",
              **advisory),
    ]


def _scenario(**kwargs):
    scenario = increment_scenario(**kwargs)
    scenario.builder.kernel_definition("AcceptanceCriterion")
    method_gates(scenario.builder, synthetic_method())
    return scenario


def _evaluate(scenario, increment_id=None):
    builder = scenario.builder
    view = ModelView(builder.elements, _traversal(builder), sources=builder.sources)
    return evaluate_increment(view, increment_id or scenario.increment_id, revision=REVISION)


def _state(evaluation, gate):
    (unit,) = [u for u in evaluation.canonical.units if u.unit_id == gate]
    return unit.verdict or unit.state or unit.coverage


def _phase(status, phase):
    (block,) = [b for b in status["phases"] if b["phase"] == phase]
    return block


def test_complete_increment_passes_every_authorable_gate() -> None:
    evaluation = _evaluate(_scenario())
    states = {u.unit_id: (u.verdict or u.state) for u in evaluation.canonical.units}
    blocking_failures = {gate: state for gate, state in states.items()
                         if state not in {me.VERDICT_PASS, me.VERDICT_NOT_APPLICABLE}
                         and gate not in {"scope", "featureTrace", "acceptance", "evidence"}}
    assert blocking_failures == {}
    assert states["scope"] == me.STATE_INDETERMINATE  # IncrementScope has no kernel identity
    status = evaluation.status()
    assert [b["phase"] for b in status["phases"]] == [P0, P4, P5, P10]
    assert _phase(status, P0)["phase_exit"] == "BLOCKED"
    for phase in (P4, P5, P10):
        assert _phase(status, phase)["phase_exit"] == "READY", phase
    nxt = evaluation.next_obligation()
    assert nxt["next"] is None
    assert [b["gate"] for b in nxt["method_side_blockers"]] == ["scope"]


def test_projections_share_one_evaluation_identity() -> None:
    evaluation = _evaluate(_scenario())
    keys = {
        evaluation.status()["evaluation_key"],
        evaluation.gaps()["evaluation_key"],
        evaluation.next_obligation()["evaluation_key"],
        evaluation.status(phase=P4)["evaluation_key"],
        evaluation.gaps(phase=P10)["evaluation_key"],
        evaluation.next_obligation(phase=P5)["evaluation_key"],
    }
    assert keys == {evaluation.evaluation_key}


def test_missing_identifier_blocks_everything_and_says_what_to_author() -> None:
    scenario = _scenario()
    scenario.usage.pop("declaredShortName")
    evaluation = _evaluate(scenario)
    assert _state(evaluation, "identity") == me.VERDICT_FAIL
    assert _state(evaluation, "needStakeholder") == me.COVERAGE_UNASSESSED
    step = evaluation.next_obligation()["next"]
    assert (step["stage"], step["gate"], step["kind"]) == (P0, "identity", "violation")
    assert "INC-FIXTURE-001" in step["what_to_author"]
    assert _phase(evaluation.status(), P4)["phase_exit"] == "BLOCKED"


def test_next_ranks_by_gate_prerequisites_before_phase() -> None:
    scenario = _scenario()
    b = scenario.builder
    owner_feature = b.feature_of(scenario.charter, "owner")
    b.remove(owner_feature)
    need = scenario.needs[1]
    stakeholder = [e for e in b.elements if e.get("@type") == "StakeholderMembership"
                   and e.get("owningRelatedElement", {}).get("@id") == need["@id"]]
    b.remove(*stakeholder)
    evaluation = _evaluate(scenario)
    assert _state(evaluation, "owner") == me.VERDICT_FAIL
    assert _state(evaluation, "needStakeholder") == me.VERDICT_FAIL
    step = evaluation.next_obligation()["next"]
    # owner (identity -> charter -> owner) is shallower than needStakeholder
    # (identity -> charter -> phases -> needStakeholder).
    assert (step["stage"], step["gate"]) == (P0, "owner")
    queue = evaluation.next_obligation()["stage_queue"]
    assert [entry["phase"] for entry in queue] == [P0, P4]
    assert evaluation.next_obligation(phase=P4)["next"]["gate"] == "needStakeholder"


def test_next_prefers_the_earlier_phase_at_equal_depth() -> None:
    scenario = _scenario()
    b = scenario.builder
    need = scenario.needs[0]
    b.remove(*[e for e in b.elements if e.get("@type") == "StakeholderMembership"
               and e.get("owningRelatedElement", {}).get("@id") == need["@id"]])
    method_value = b.feature_of(scenario.requirements[0], "verificationMethod")
    b.remove(method_value)
    evaluation = _evaluate(scenario)
    assert _state(evaluation, "method") == me.VERDICT_FAIL
    step = evaluation.next_obligation()["next"]
    assert (step["stage"], step["gate"]) == (P4, "needStakeholder")
    subjects = [s["name"] for s in step["subjects"]]
    assert subjects == ["need0"]


def test_failing_subjects_are_reported_with_where_to_author() -> None:
    scenario = _scenario()
    b = scenario.builder
    b.remove(*[e for e in b.elements if e.get("@type") == "ConnectionUsage"
               and e.get("declaredName") == "requirement1DerivedFromNeed1"])
    evaluation = _evaluate(scenario)
    gaps = evaluation.gaps()
    (entry,) = [g for g in gaps["blocking"] if g["gate"] == "derives"]
    assert entry["kind"] == "violation"
    assert [s["name"] for s in entry["subjects"]] == ["requirement1"]
    subject_id = entry["subjects"][0]["element_id"]
    assert gaps["presentation"]["element_sources"][subject_id].endswith(".sysml")
    assert entry["where"]["packages"] == ["DE4SDV_FixtureNeedsRequirements"]
    assert "DerivesFromNeed" in entry["what_to_author"]


def test_unplanned_validation_and_unverified_requirement_fail() -> None:
    scenario = _scenario()
    b = scenario.builder
    b.remove(*[e for e in b.elements if e.get("declaredName") == "need1ValidationPlanning"])
    case_def = next(e for e in b.elements if e.get("declaredName") == "FixtureVerification")
    objective = next(e for e in b.elements if e.get("declaredName") == "fixtureObjective")
    verifications = [e for e in b.elements if e.get("@type") == "RequirementVerificationMembership"
                     and e.get("owningRelatedElement", {}).get("@id") == objective["@id"]]
    b.remove(verifications[1])
    assert case_def
    evaluation = _evaluate(scenario)
    assert _state(evaluation, "needValidation") == me.VERDICT_FAIL
    assert _state(evaluation, "requirementVerified") == me.VERDICT_FAIL
    assert _state(evaluation, "caseVerifies") == me.VERDICT_PASS


def test_verification_method_outside_the_standard_kinds_fails() -> None:
    scenario = _scenario()
    b = scenario.builder
    literal = next(e for e in b.elements if e.get("@type") == "LiteralString" and e.get("value") == "test")
    literal["value"] = "simulation"
    evaluation = _evaluate(scenario)
    assert _state(evaluation, "method") == me.VERDICT_FAIL
    (entry,) = [g for g in evaluation.gaps()["blocking"] if g["gate"] == "method"]
    assert "inspect, demo, test, analyze" in " ".join(entry["subjects"][0]["diagnostics"])


def test_undeclared_phase_is_not_applicable_not_passed() -> None:
    evaluation = _evaluate(_scenario(applicable_phases=(P0, P4, P5)))
    assert _state(evaluation, "caseVerifies") == me.VERDICT_NOT_APPLICABLE
    block = _phase(evaluation.status(), P10)
    assert block["applicability"] == "not declared"
    assert block["conformance_verdict"] == me.VERDICT_NOT_APPLICABLE


def test_advisory_gates_never_block_and_are_reported_as_notes() -> None:
    evaluation = _evaluate(_scenario())
    gaps = evaluation.gaps()
    advisory = {entry["gate"]: entry["kind"] for entry in gaps["advisory"]}
    assert advisory == {"featureTrace": "method-side", "acceptance": "violation", "evidence": "method-side"}
    assert all(entry["gate"] not in advisory for entry in gaps["blocking"])


def test_a_model_without_gates_reports_no_executable_contract() -> None:
    scenario = increment_scenario()
    evaluation = _evaluate(scenario)
    status = evaluation.status()
    assert status["executable_contract_available"] is False
    assert (status["assessment_coverage"], status["evaluation_state"], status["conformance_verdict"]) == (
        me.COVERAGE_UNASSESSED, None, None)
    assert status["reason_codes"] == [me.CONTRACT_UNAVAILABLE]
    assert evaluation.next_obligation()["next"] is None
    assert evaluation.gaps()["blocking"] == []


def test_invalid_gates_are_an_evaluation_error() -> None:
    scenario = increment_scenario()
    method_gates(scenario.builder, [GateSpec(name="broken", phase=P4, selector="incrementNeeds",
                                             predicate="no-such-predicate")])
    status = _evaluate(scenario).status()
    assert (status["assessment_coverage"], status["evaluation_state"]) == (me.COVERAGE_ASSESSED, me.STATE_ERROR)
    assert status["reason_codes"] == [me.INVALID_CONTRACT]
    assert any("no-such-predicate" in problem for problem in status["method"]["problems"])


def test_phase_contract_lists_gates_with_increment_applicability_and_no_verdict() -> None:
    evaluation = _evaluate(_scenario(applicable_phases=(P0, P4, P5)))
    contract = evaluation.phase_contract(phase=P10)
    assert contract["executable_contract_available"] is True
    gates = {gate["obligation_id"]: gate for gate in contract["gates"]}
    assert set(gates) == {"caseVerifies", "requirementVerified", "acceptance", "evidence"}
    assert gates["caseVerifies"]["applicability_resolution"] == "not_applicable"
    assert gates["caseVerifies"]["prerequisites"] == ["phases"]
    assert "conformance_verdict" not in contract
    assert evaluation.phase_contract()["phases"] == [P0, P4, P5, P10]


@pytest.mark.parametrize("increment_id", ["INC-FIXTURE-001"])
def test_status_names_the_resolved_increment(increment_id: str) -> None:
    scenario = _scenario()
    status = _evaluate(scenario, increment_id).status()
    assert status["increment"]["id"] == increment_id
    assert status["increment"]["usage"]["qualified_name"] == "DE4SDV_FixtureFraming::incFixture"
    assert status["increment"]["declared_phases"] == [P0, P4, P5, P10]


def test_a_phase_without_gates_is_unassessed_never_a_pass() -> None:
    evaluation = _evaluate(_scenario())
    status = evaluation.status(phase="phase1_concernFraming")
    assert status["phases"] == []
    assert (status["assessment_coverage"], status["evaluation_state"], status["conformance_verdict"]) == (
        me.COVERAGE_UNASSESSED, None, None)
    assert status["reason_codes"] == [me.CONTRACT_UNAVAILABLE]
    assert evaluation.next_obligation(phase="phase1_concernFraming")["next"] is None
    contract = evaluation.phase_contract(phase="phase1_concernFraming")
    assert contract["executable_contract_available"] is False
    assert contract["reason_codes"] == [me.CONTRACT_UNAVAILABLE]


def test_an_empty_required_inventory_cannot_open_a_phase_exit() -> None:
    scenario = increment_scenario()
    scenario.builder.kernel_definition("AcceptanceCriterion")
    only_advisory = [g for g in synthetic_method() if g.phase != P10 or not g.required]
    method_gates(scenario.builder, only_advisory)
    evaluation = _evaluate(scenario)
    block = _phase(evaluation.status(), P10)
    assert (block["assessment_coverage"], block["evaluation_state"], block["conformance_verdict"]) == (
        me.COVERAGE_UNASSESSED, None, None)
    assert block["phase_exit"] == "BLOCKED"
    assert block["readiness"]["reason_codes"] == [me.CONTRACT_UNAVAILABLE]


def test_unreadable_governed_witnesses_stay_indeterminate_for_every_subject(monkeypatch) -> None:
    """The traversal de-duplicates its unsupported records; each subject's own
    unreadable witness must still be reported as an input problem, not a FAIL."""
    from de4sdv.semantic.relationship_successor import SuccessorTraversal

    def unreadable(self, predicate, source, elements):
        if predicate == "derivesRequirementFromNeed":
            self.unavailable(predicate, "native connection endpoint is absent")
            return []
        return original(self, predicate, source, elements)

    original = SuccessorTraversal.traverse
    monkeypatch.setattr(SuccessorTraversal, "traverse", unreadable)
    evaluation = _evaluate(_scenario())
    children = [r for r in evaluation.canonical.results if r.unit_id == "derives"]
    assert len(children) == 2
    assert {(c.state, c.verdict) for c in children} == {(me.STATE_INDETERMINATE, None)}
    (entry,) = [g for g in evaluation.gaps()["blocking"] if g["gate"] == "derives"]
    assert entry["kind"] == "input-problem"
