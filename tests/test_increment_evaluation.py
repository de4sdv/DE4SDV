"""One canonical method evaluation per increment and its three projections.

``status`` (per phase), ``gaps`` (unmet blocking checks plus advisory notes)
and ``next`` (the earliest actionable check in workflow order) come from one
canonical evaluation and carry the same evaluation identity. The method is the
workflow the increment's charter declares: in these scenarios, the workflow of
the frozen genuine-export cut, whose outcomes they assert (not the current
model's).
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
    cut_method_builder,
    cut_workflow,
    kernel_qualified_name,
    set_check,
)
from test_revision_index import _traversal

REVISION = me.RevisionIdentity("a" * 40, "project", "commit", "full-model")
P0, P4, P5, P10 = ("phase0_incrementFraming", "phase4_needs", "phase5_requirements", "phase10_vvEvidence")
#: The phases the workflow of the frozen cut gives executable checks.
CHECKED = [P0, P4, P5, "phase6_functionalArchitecture", "phase7_logicalArchitecture",
           "phase8_physicalRealization", P10]


def _scenario(applicable_phases=(P0, P4, P5, P10)):
    scenario = increment_scenario(cut_method_builder(), applicable_phases=applicable_phases)
    scenario.workflow = cut_workflow(scenario)
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


def test_an_increment_not_declared_at_the_revision_is_named_with_a_distinct_reason() -> None:
    """Branch work is invisible to another revision: every answer says the increment isn't declared at
    this revision, names the revision and points to the PR Method Check, instead of an empty reason."""
    evaluation = _evaluate(_scenario(), "INC-EXAMPLE-001")
    answers = (evaluation.status(), evaluation.gaps(), evaluation.next_obligation(), evaluation.phase_contract())
    for answer in answers:
        block = answer["increment"]
        assert (block["id"], block["resolved"], block["resolution"]) == (
            "INC-EXAMPLE-001", False, "not-declared"), answer["query"]
        assert block["message"].startswith(f"INC-EXAMPLE-001 isn't declared at revision {REVISION.git_commit}")
        assert "PR Method Check" in block["message"]
    answer = evaluation.next_obligation()
    assert answer["reason"] == answer["increment"]["message"]
    assert "reason_code" not in answer and "reason_code" not in answer["increment"]  # review R8: one name only
    assert answer["next"]["gate"] == "incrementHasIdentifier"  # a new increment still learns how to declare itself



def test_the_not_declared_message_covers_a_usage_that_lacks_its_short_name() -> None:
    """Review R5: a legacy increment usage exists at the revision without its identifier as short name
    (like incMW002 for INC-MW-002); the message must not suggest only branch work."""
    scenario = _scenario()
    scenario.usage.pop("declaredShortName")
    block = _evaluate(scenario).status()["increment"]
    assert block["resolution"] == "not-declared"
    assert ("An increment usage that exists without that short name, such as a legacy increment, is not found "
            "either; the Method Check report lists such usages.") in block["message"]
    assert "the PR Method Check evaluates the head of a pull request" in block["message"]

def test_a_declared_increment_has_no_such_reason_and_next_always_says_why() -> None:
    complete = _evaluate(_scenario())
    assert (complete.status()["increment"]["resolution"], "message" in complete.status()["increment"]) == (
        "resolved", False)
    assert complete.next_obligation()["reason"] == "every required gate passes or is not applicable"
    scenario = _scenario()
    scenario.builder.remove(scenario.builder.feature_of(scenario.charter, "owner"))
    gappy = _evaluate(scenario).next_obligation()
    assert gappy["next"]["gate"] == "incrementHasOwner"
    assert gappy["reason"] == "the first open blocking check in workflow order (step order, then check order)"
    ambiguous = _scenario()  # declared twice: ambiguous, not undeclared
    ambiguous.builder.usage("PartUsage", "incFixtureCopy", ambiguous.framing, [ambiguous.definition],
                            short=ambiguous.increment_id)
    block = _evaluate(ambiguous).status()["increment"]
    assert (block["resolved"], block["resolution"], "message" in block) == (False, "ambiguous", False)



def test_an_unbound_increment_lineage_resolves_as_lineage_unavailable_not_as_undeclared() -> None:
    scenario = _scenario()
    scenario.builder.bindings[:] = [b for b in scenario.builder.bindings
                                    if b["ontology_class"] != "EngineeringIncrement"]
    block = _evaluate(scenario).status()["increment"]
    assert (block["resolved"], block["resolution"], "message" in block) == (False, "lineage-unavailable", False)

def test_next_none_says_which_declared_phases_no_check_judges() -> None:
    """0 blocking says nothing about a declared phase without executable checks; the reason says so."""
    evaluation = _evaluate(_scenario(applicable_phases=(P0, "phase1_concernFraming", P4, P5, P10)))
    answer = evaluation.next_obligation()
    assert answer["next"] is None
    assert answer["reason"] == ("every required gate passes or is not applicable; no executable checks at this "
                                "revision judge the declared phase phase1_concernFraming")
    assert answer["coverage"]["declared_phases_without_executable_checks"] == ["phase1_concernFraming"]
    (block,) = [b for b in evaluation.status()["phases"] if b["phase"] == "phase1_concernFraming"]
    assert (block["coverage"], block["phase_exit"]) == ("no executable checks at this revision", "BLOCKED")
    assert [output["parameter"] for output in block["outputs"]] == ["stakeholders", "concerns"]


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
    assert advisory == {"needSubjectIsSystemOfInterest": "violation",
                        "requirementSubjectIsSystemOfInterest": "violation",
                        "requirementStatesSuccessCriteria": "violation",
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
                           "verificationCaseHasEvidenceRecordOrStatus"}
    assert checks["verificationCaseVerifiesRequirement"]["applicability_resolution"] == "not_applicable"
    assert "conformance_verdict" not in contract
    assert evaluation.phase_contract()["phases"] == CHECKED



def test_at_least_one_assumption_reads_on_the_population_not_the_cardinality() -> None:
    """T4 finding L2: "owns at least one assumption" showed cardinality [1, 1]. The cardinality counts the
    owning package of each assumption (exactly one); the population counts the assumptions."""
    gates = {gate["obligation_id"]: gate for gate in _evaluate(_scenario()).phase_contract(phase=P0)["gates"]}
    for name in ("incrementHasAssumption", "incrementHasOutOfScopeItem"):
        assert "at least one" in gates[name]["claim_boundary"]
        assert (gates[name]["population"], gates[name]["cardinality"]) == ([1, "*"], [1, 1]), name
    assert gates["incrementHasScope"]["population"] == [1, 1]  # "owns exactly one scope"

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


def test_a_phase_without_checks_still_lists_what_its_step_declares() -> None:
    evaluation = _evaluate(_scenario())
    contract = evaluation.phase_contract(phase="phase1_concernFraming")
    (step,) = contract["steps"]
    assert (step["step"], step["executable_checks"], step["coverage"]) == (
        "frameConcerns", 0, "no executable checks at this revision")
    assert [output["parameter"] for output in step["outputs"]] == ["stakeholders", "concerns"]
    assert step["applicability_resolution"] == "not_applicable"  # the charter declares phases 0, 4, 5 and 10
    assert contract["phases_without_executable_checks"] == ["phase1_concernFraming"]
    whole = evaluation.phase_contract()
    assert len(whole["steps"]) == 13
    assert whole["phases"] == CHECKED



P1 = "phase1_concernFraming"
NO_CHECKS = "no executable checks at this revision"


def _two_step_scenario(*, with_workflow: bool = True):
    """A charter declaring phases 0, 1 and 4 over a workflow with steps for phases 0 and 4 only."""
    scenario = increment_scenario(applicable_phases=(P0, P1, P4))
    if with_workflow:
        increment_workflow(scenario.builder, [
            WorkflowStep("frameIncrement", P0, (WorkflowParameter("increment", "EngineeringIncrement"),), (
                WorkflowCheck("incrementHasIdentifier", "incrementShortName", "increment"),)),
            WorkflowStep("elaborateNeeds", P4, (
                WorkflowParameter("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),), (
                WorkflowCheck("needHasStatement", "requireConstraint", "needs"),)),
        ], charter=scenario.charter)
    return scenario


def _unchecked(block: dict, phase: str) -> None:
    """A declared phase no executable check judges, whether or not the workflow has a step for it."""
    assert (block["phase"], block["coverage"], block["executable_checks"]) == (phase, NO_CHECKS, 0)
    assert (block["assessment_coverage"], block["evaluation_state"], block["conformance_verdict"]) == (
        me.COVERAGE_UNASSESSED, None, None)
    assert block["phase_exit"] == "BLOCKED"


def test_a_declared_phase_without_a_workflow_step_is_reported_too() -> None:
    evaluation = _evaluate(_two_step_scenario())
    status = evaluation.status()
    assert [block["phase"] for block in status["phases"]] == [P0, P1, P4]
    (block,) = [b for b in status["phases"] if b["phase"] == P1]
    _unchecked(block, P1)
    assert (block["step"], block["outputs"]) == (None, [])
    assert status["coverage"]["declared_phases_without_executable_checks"] == [P1]
    assert evaluation.next_obligation()["coverage"]["declared_phases_without_executable_checks"] == [P1]


def test_without_a_workflow_every_declared_phase_is_reported() -> None:
    status = _evaluate(_two_step_scenario(with_workflow=False)).status()
    assert status["executable_contract_available"] is False
    assert status["reason_codes"] == [me.CONTRACT_UNAVAILABLE]
    assert status["coverage"]["declared_phases_without_executable_checks"] == [P0, P1, P4]
    assert [block["phase"] for block in status["phases"]] == [P0, P1, P4]
    for block, phase in zip(status["phases"], (P0, P1, P4)):
        _unchecked(block, phase)
        assert (block["step"], block["outputs"]) == (None, [])


def test_an_unchecked_phase_exit_is_blocked_by_the_method_never_by_a_gap() -> None:
    """Review R2: BLOCKED beside the step's outputs must not read like a gap to author against."""
    evaluation = _evaluate(_scenario(applicable_phases=(P0, P1, P4, P5, P10)))
    (block,) = [b for b in evaluation.status()["phases"] if b["phase"] == P1]
    assert block["reason_codes"] == [me.CONTRACT_UNAVAILABLE]  # an UNASSESSED result names its reason
    for phrase in ("BLOCKED by the method, not by the model", "no gap is open here",
                   "nothing you author opens this exit"):
        assert phrase in block["exit_note"], phrase
    (diagnostic,) = block["readiness"]["diagnostics"]
    assert diagnostic.endswith("its exit stays BLOCKED until the method adds checks; this is not a gap")
    gaps = evaluation.gaps()
    assert P1 not in {gap["phase"] for gap in gaps["blocking"] + gaps["advisory"]}
    assert evaluation.next_obligation()["next"] is None
    (unread,) = [b for b in _evaluate(_two_step_scenario(with_workflow=False)).status()["phases"] if b["phase"] == P1]
    assert unread["reason_codes"] == [me.CONTRACT_UNAVAILABLE] and unread["exit_note"] == block["exit_note"]

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
    from de4sdv.semantic.trace_vocabulary_traversal import SuccessorTraversal

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
    """What to author for a relation is SysML the model already uses; placeholders are only in angle brackets.
    Types and the subject are named by their qualified names (read here from the cut's kernel bindings and
    owning packages), the scenario is declared before the connection that names it."""
    scenario = _scenario()
    builder = scenario.builder
    builder.remove(*[e for e in builder.elements if e.get("declaredName") == "need1ValidationPlanning"])
    (entry,) = [g for g in _evaluate(scenario).gaps()["blocking"] if g["gate"] == "needHasValidationScenario"]
    association, package = kernel_qualified_name(builder, "ValidationPlanningAssociation")
    scenario_type, _package = kernel_qualified_name(builder, "ValidationPlanningScenario")
    lines = [f"part <validationScenario> : {scenario_type};",
             f"connection <name> : {association} connect DE4SDV_FixtureNeedsRequirements::need1 to "
             "<validationScenario>;"]
    assert entry["authoring"]["declarations"] == lines
    assert entry["what_to_author"].endswith(
        f": {' '.join(lines)} Import: private import {package}::*;"), entry["what_to_author"]
    # Without a subject, the member sits in its container (a requirement holds a framed concern).
    assert mc.remedy("frame", _evaluate(scenario).view) == (
        "declare each subject with the concern it frames: requirement <name> { frame <concern>; }")


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


def _success_criteria_scenario(value=None):
    """A synthetic workflow, not the frozen cut's: after the mandatory framing step (which reads
    only the increment's own package), its requirements step declares the advisory
    success-criteria check, and the requirement type owns ``successCriteria``. With a ``value``,
    both requirements set it."""
    scenario = increment_scenario()
    builder = scenario.builder
    requirement_type = scenario.vocabulary["Requirement"]
    feature = builder.new("AttributeUsage", name="successCriteria", source=builder.sources[requirement_type["@id"]])
    builder.own(requirement_type, feature, kind="FeatureMembership", member_name="successCriteria")
    if value is not None:
        for requirement in scenario.requirements:
            builder.attribute(requirement, "successCriteria", value, redefines=feature)
    increment_workflow(builder, [
        WorkflowStep("frameIncrement", P0, (WorkflowParameter("increment", "EngineeringIncrement"),)),
        WorkflowStep("specifyRequirements", P5, (
            WorkflowParameter("requirements", "Requirement", "RequirementUsage", bounds=(1, INFINITY)),), (
            WorkflowCheck("requirementStatesSuccessCriteria", "successCriteriaAttribute", "requirements",
                          advisory=True),)),
    ], charter=scenario.charter)
    return scenario


def test_success_criteria_pass_when_each_requirement_states_them() -> None:
    evaluation = _evaluate(_success_criteria_scenario("The fixture output matches its reference in 20 of 20 runs."))
    assert _state(evaluation, "requirementStatesSuccessCriteria") == me.VERDICT_PASS
    assert evaluation.gaps()["advisory"] == []


def test_missing_success_criteria_are_an_advisory_note_that_says_what_to_author() -> None:
    evaluation = _evaluate(_success_criteria_scenario())
    assert _state(evaluation, "requirementStatesSuccessCriteria") == me.VERDICT_FAIL
    gaps = evaluation.gaps()
    assert gaps["blocking"] == []
    (note,) = gaps["advisory"]
    assert (note["gate"], note["kind"]) == ("requirementStatesSuccessCriteria", "violation")
    assert sorted(subject["name"] for subject in note["subjects"]) == ["requirement0", "requirement1"]
    assert "attribute :>> successCriteria = " in note["what_to_author"]


def test_empty_success_criteria_do_not_count() -> None:
    evaluation = _evaluate(_success_criteria_scenario(""))
    assert _state(evaluation, "requirementStatesSuccessCriteria") == me.VERDICT_FAIL
    (note,) = evaluation.gaps()["advisory"]
    assert sorted(subject["name"] for subject in note["subjects"]) == ["requirement0", "requirement1"]


def test_population_remedies_name_where_the_subjects_belong() -> None:
    scenario = _scenario()
    builder = scenario.builder
    builder.usage("PartUsage", "secondDecision", scenario.framing, [scenario.vocabulary["IncrementLifecycleDecision"]])
    for need in scenario.needs:
        builder.remove(need)
    gaps = {g["gate"]: g for g in _evaluate(scenario).gaps()["blocking"]}
    assert "in the increment's package" in gaps["incrementHasLifecycleDecision"]["what_to_author"]
    assert ("in the increment's packages named in the charter's expectedArtifacts"
            in gaps["needHasStatement"]["what_to_author"])
