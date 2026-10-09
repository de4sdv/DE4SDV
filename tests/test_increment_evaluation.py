"""One canonical method evaluation per increment and its three projections.

``status`` (per phase), ``gaps`` (unmet blocking checks plus advisory notes)
and ``next`` (the earliest actionable check in workflow order) come from one
canonical evaluation and carry the same evaluation identity. The method is the
workflow the increment's charter declares; the synthetic workflow mirrors the
model's steps and checks.
"""

from __future__ import annotations

import pytest

from de4sdv.semantic import method_checks as mc
from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from increment_model_fixtures import (
    INFINITY,
    WorkflowCheck,
    WorkflowParameter,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
    method_builder,
    model_workflow,
    set_check,
)
from test_revision_index import _traversal

REVISION = me.RevisionIdentity("a" * 40, "project", "commit", "full-model")
P0, P4, P5, P10 = ("phase0_incrementFraming", "phase4_needs", "phase5_requirements", "phase10_vvEvidence")


def _scenario(applicable_phases=(P0, P4, P5, P10)):
    scenario = increment_scenario(method_builder(), applicable_phases=applicable_phases)
    scenario.workflow = model_workflow(scenario)
    return scenario


def _evaluate(scenario, increment_id=None):
    builder = scenario.builder
    view = ModelView(builder.elements, _traversal(builder), sources=builder.sources)
    return evaluate_increment(view, increment_id or scenario.increment_id, revision=REVISION)


def _state(evaluation, check):
    (unit,) = [u for u in evaluation.canonical.units if u.unit_id == check]
    return unit.verdict or unit.state or unit.coverage


def _phase(status, phase):
    (block,) = [b for b in status["phases"] if b["phase"] == phase]
    return block


def _remove_stakeholders(scenario, owner) -> None:
    builder = scenario.builder
    builder.remove(*[e for e in builder.elements if e.get("@type") == "StakeholderMembership"
                     and e.get("owningRelatedElement", {}).get("@id") == owner["@id"]])


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


def test_an_unidentified_increment_is_told_to_declare_its_identifier() -> None:
    """A new increment: the revision's workflow still applies, and framing says what to author first."""
    scenario = _scenario()
    scenario.usage.pop("declaredShortName")
    evaluation = _evaluate(scenario)
    status = evaluation.status()
    assert status["increment"]["resolved"] is False
    assert any("short name" in d for d in status["increment"]["diagnostics"])
    step = evaluation.next_obligation()["next"]
    assert (step["gate"], step["kind"]) == ("incrementHasIdentifier", "input-problem")
    assert step["what_to_author"].startswith("declare the increment usage with its identifier")


def test_next_takes_the_earliest_open_check_in_workflow_order() -> None:
    scenario = _scenario()
    builder = scenario.builder
    builder.remove(builder.feature_of(scenario.charter, "owner"))
    _remove_stakeholders(scenario, scenario.needs[1])
    evaluation = _evaluate(scenario)
    assert _state(evaluation, "incrementHasOwner") == me.VERDICT_FAIL
    assert _state(evaluation, "needHasStakeholder") == me.VERDICT_FAIL
    step = evaluation.next_obligation()["next"]
    assert (step["stage"], step["gate"]) == (P0, "incrementHasOwner")
    queue = evaluation.next_obligation()["stage_queue"]
    assert [entry["phase"] for entry in queue] == [P0, P4]
    assert evaluation.next_obligation(phase=P4)["next"]["gate"] == "needHasStakeholder"


def test_next_names_the_failing_subjects_of_the_earliest_check() -> None:
    scenario = _scenario()
    _remove_stakeholders(scenario, scenario.needs[0])
    scenario.builder.remove(scenario.builder.feature_of(scenario.requirements[0], "verificationMethod"))
    evaluation = _evaluate(scenario)
    assert _state(evaluation, "requirementHasVerificationMethod") == me.VERDICT_FAIL
    step = evaluation.next_obligation()["next"]
    assert (step["stage"], step["gate"]) == (P4, "needHasStakeholder")
    assert [s["name"] for s in step["subjects"]] == ["need0"]


def test_failing_subjects_are_reported_with_where_to_author() -> None:
    scenario = _scenario()
    builder = scenario.builder
    builder.remove(*[e for e in builder.elements if e.get("@type") == "ConnectionUsage"
                     and e.get("declaredName") == "requirement1DerivedFromNeed1"])
    gaps = _evaluate(scenario).gaps()
    (entry,) = [g for g in gaps["blocking"] if g["gate"] == "requirementDerivesFromNeed"]
    assert entry["kind"] == "violation"
    assert [s["name"] for s in entry["subjects"]] == ["requirement1"]
    subject_id = entry["subjects"][0]["element_id"]
    assert gaps["presentation"]["element_sources"][subject_id].endswith(".sysml")
    assert entry["where"]["packages"] == ["DE4SDV_FixtureNeedsRequirements"]
    assert "DerivesFromNeed" in entry["what_to_author"]


def test_unplanned_validation_and_unverified_requirement_fail() -> None:
    scenario = _scenario()
    builder = scenario.builder
    builder.remove(*[e for e in builder.elements if e.get("declaredName") == "need1ValidationPlanning"])
    objective = next(e for e in builder.elements if e.get("declaredName") == "fixtureObjective")
    verifications = [e for e in builder.elements if e.get("@type") == "RequirementVerificationMembership"
                     and e.get("owningRelatedElement", {}).get("@id") == objective["@id"]]
    builder.remove(verifications[1])
    evaluation = _evaluate(scenario)
    assert _state(evaluation, "needHasValidationScenario") == me.VERDICT_FAIL
    assert _state(evaluation, "requirementVerifiedByVerificationCase") == me.VERDICT_FAIL
    assert _state(evaluation, "verificationCaseVerifiesRequirement") == me.VERDICT_PASS


def test_verification_method_outside_the_standard_kinds_fails() -> None:
    scenario = _scenario()
    literal = next(e for e in scenario.builder.elements
                   if e.get("@type") == "LiteralString" and e.get("value") == "test")
    literal["value"] = "simulation"
    evaluation = _evaluate(scenario)
    assert _state(evaluation, "requirementHasVerificationMethod") == me.VERDICT_FAIL
    (entry,) = [g for g in evaluation.gaps()["blocking"] if g["gate"] == "requirementHasVerificationMethod"]
    assert "inspect, analyze, demo, test" in " ".join(entry["subjects"][0]["diagnostics"])


def test_undeclared_phase_is_not_applicable_not_passed() -> None:
    evaluation = _evaluate(_scenario(applicable_phases=(P0, P4, P5)))
    assert _state(evaluation, "verificationCaseVerifiesRequirement") == me.VERDICT_NOT_APPLICABLE
    block = _phase(evaluation.status(), P10)
    assert block["applicability"] == "not declared"
    assert block["conformance_verdict"] == me.VERDICT_NOT_APPLICABLE


def test_advisory_checks_never_block_and_are_reported_as_notes() -> None:
    gaps = _evaluate(_scenario()).gaps()
    advisory = {entry["gate"]: entry["kind"] for entry in gaps["advisory"]}
    assert advisory == {"requirementSpecifiesFeatureOrCapability": "method-side",
                        "verificationCaseVerifiesAcceptanceCriterion": "violation",
                        "verificationCaseHasEvidenceRecordOrStatus": "method-side"}
    assert all(entry["gate"] not in advisory for entry in gaps["blocking"])


def test_a_model_without_a_workflow_reports_no_executable_contract() -> None:
    evaluation = _evaluate(increment_scenario())
    status = evaluation.status()
    assert status["executable_contract_available"] is False
    assert (status["assessment_coverage"], status["evaluation_state"], status["conformance_verdict"]) == (
        me.COVERAGE_UNASSESSED, None, None)
    assert status["reason_codes"] == [me.CONTRACT_UNAVAILABLE]
    assert evaluation.next_obligation()["next"] is None
    assert evaluation.gaps()["blocking"] == []


def test_an_invalid_workflow_is_an_evaluation_error() -> None:
    scenario = increment_scenario()
    increment_workflow(scenario.builder, [WorkflowStep("elaborateNeeds", P4, (
        WorkflowParameter("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),), (
        WorkflowCheck("broken", "noSuchCheck", "needs"),))], charter=scenario.charter)
    status = _evaluate(scenario).status()
    assert (status["assessment_coverage"], status["evaluation_state"]) == (me.COVERAGE_ASSESSED, me.STATE_ERROR)
    assert status["reason_codes"] == [me.INVALID_CONTRACT]
    assert any("noSuchCheck" in problem for problem in status["method"]["problems"])


def test_phase_contract_lists_checks_with_increment_applicability_and_no_verdict() -> None:
    evaluation = _evaluate(_scenario(applicable_phases=(P0, P4, P5)))
    contract = evaluation.phase_contract(phase=P10)
    assert contract["executable_contract_available"] is True
    checks = {check["obligation_id"]: check for check in contract["gates"]}
    assert set(checks) == {"verificationCaseVerifiesRequirement", "requirementVerifiedByVerificationCase",
                           "verificationCaseVerifiesAcceptanceCriterion", "verificationCaseHasEvidenceRecordOrStatus"}
    assert checks["verificationCaseVerifiesRequirement"]["applicability_resolution"] == "not_applicable"
    assert "conformance_verdict" not in contract
    assert evaluation.phase_contract()["phases"] == [P0, P4, P5, P10]


@pytest.mark.parametrize("increment_id", ["INC-FIXTURE-001"])
def test_status_names_the_resolved_increment_and_its_scope(increment_id: str) -> None:
    status = _evaluate(_scenario(), increment_id).status()
    assert status["increment"]["id"] == increment_id
    assert status["increment"]["usage"]["qualified_name"] == "DE4SDV_FixtureFraming::incFixture"
    assert status["increment"]["declared_phases"] == [P0, P4, P5, P10]
    assert status["increment"]["scope"]["packages"] == [
        "DE4SDV_FixtureFraming", "DE4SDV_FixtureNeedsRequirements", "DE4SDV_FixtureVerificationEvidence"]


def test_a_phase_without_checks_is_unassessed_never_a_pass() -> None:
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
    scenario = _scenario()
    for check in ("verificationCaseVerifiesRequirement", "requirementVerifiedByVerificationCase"):
        set_check(scenario, scenario.workflow, check, advisory=True)
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
    children = [r for r in evaluation.canonical.results if r.unit_id == "requirementDerivesFromNeed"]
    assert len(children) == 2
    assert {(c.state, c.verdict) for c in children} == {(me.STATE_INDETERMINATE, None)}
    (entry,) = [g for g in evaluation.gaps()["blocking"] if g["gate"] == "requirementDerivesFromNeed"]
    assert entry["kind"] == "input-problem"


def test_relation_remedies_are_member_text_the_model_uses() -> None:
    """What to author for a relation is SysML the model already uses; placeholders are only in angle brackets."""
    scenario = _scenario()
    builder = scenario.builder
    builder.remove(*[e for e in builder.elements if e.get("declaredName") == "need1ValidationPlanning"])
    (entry,) = [g for g in _evaluate(scenario).gaps()["blocking"] if g["gate"] == "needHasValidationScenario"]
    assert entry["what_to_author"].endswith(
        ": connection <name> : ValidationPlanningAssociation connect need1 to <scenario>;"), entry["what_to_author"]
    assert mc.remedy("frame", _evaluate(scenario).view) == "add to each subject: frame <concern>;"


def test_an_unresolved_declared_artifact_leaves_the_later_steps_input_unavailable() -> None:
    scenario = _scenario()
    builder = scenario.builder
    extra = builder.package("DE4SDV_FixtureExtraRequirements")
    builder.usage("RequirementUsage", "unverifiedRequirement", extra,
                  [next(e for e in builder.elements if e.get("declaredName") == "FixtureRequirement")])
    builder.remove(builder.feature_of(scenario.charter, "expectedArtifacts"))
    builder.attribute(scenario.charter, "expectedArtifacts", [
        "DE4SDV_FixtureFraming", "DE4SDV_FixtureNeedsRequirements", "DE4SDV_FixtureVerificationEvidence",
        "DE4SDV_FixtureExtraRequirement"])
    evaluation = _evaluate(scenario)
    assert _state(evaluation, "incrementDeclaresExpectedArtifacts") == me.VERDICT_FAIL
    for check in ("needHasStatement", "requirementDerivesFromNeed", "verificationCaseVerifiesRequirement"):
        assert _state(evaluation, check) == me.STATE_INDETERMINATE, check
    assert evaluation.next_obligation()["next"]["gate"] == "incrementDeclaresExpectedArtifacts"


def test_next_names_authorable_failures_next_to_method_side_subjects() -> None:
    scenario = _scenario()
    builder = scenario.builder
    builder.remove(*[e for e in builder.elements if e.get("declaredName") == "need1ValidationPlanning"])
    builder.bindings[:] = [b for b in builder.bindings if b["ontology_class"] != "ValidationPlanningScenario"]
    step = _evaluate(scenario).next_obligation()["next"]
    assert (step["gate"], step["kind"]) == ("needHasValidationScenario", "violation")
    assert [s["name"] for s in step["subjects"]] == ["need1"]
    assert [s["name"] for s in step["method_side_subjects"]] == ["need0"]


def test_a_library_attribute_counts_only_through_the_subjects_own_lineage() -> None:
    scenario = _scenario()
    builder = scenario.builder
    holder = builder.definition("PartDefinition", "LogRecord", builder.package("SomeOtherLibrary"))
    foreign = builder.new("AttributeUsage", name="source")
    builder.own(holder, foreign, kind="FeatureMembership", member_name="source")
    for need in scenario.needs:
        builder.remove(builder.feature_of(need, "source"))
        builder.attribute(need, "source", "x", redefines=foreign)
    assert _state(_evaluate(scenario), "needHasSource") == me.VERDICT_FAIL


def test_population_remedies_name_where_the_subjects_belong() -> None:
    scenario = _scenario()
    builder = scenario.builder
    builder.usage("PartUsage", "secondDecision", scenario.framing, [scenario.vocabulary["IncrementLifecycleDecision"]])
    for need in scenario.needs:
        builder.remove(need)
    gaps = {g["gate"]: g for g in _evaluate(scenario).gaps()["blocking"]}
    assert "in the increment's package" in gaps["incrementHasLifecycleDecision"]["what_to_author"]
    assert "in the increment's declared packages" in gaps["needHasStatement"]["what_to_author"]
