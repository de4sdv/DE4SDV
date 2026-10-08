"""The increment workflow read from the model and evaluated against an increment.

The method is ``action def IncrementWorkflow`` (DE4SDV_IncrementWorkflow): step
actions chained from ``start`` to ``done``, each typed by a step definition
with a ``phase``, parameters (direction, multiplicity, usually a type) and
``MethodCheck`` metadata about a parameter (``check`` id, optional ``minimum``
and ``advisory``). The synthetic workflow below mirrors the model's steps,
parameters and checks; check ids resolve in the method-check registry and an
unknown id fails closed.
"""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.gate_reader import UNBOUNDED, read_method_gates
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.method_checks import MethodCheckRegistry
from de4sdv.semantic.model_authority_runtime import model_facade
from de4sdv.semantic.relation_checks import RelationCheckRegistry
from increment_model_fixtures import (
    INFINITY,
    WorkflowCheck,
    WorkflowParameter,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
    method_gates,
    ref,
)
from test_increment_evaluation import P0, P4, P5, P10, REVISION, synthetic_method
from test_revision_index import _traversal

WORKFLOW_FILE = (Path(__file__).resolve().parents[1]
                 / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_increment_workflow.sysml")
P = WorkflowParameter
C = WorkflowCheck


def _named(scenario, name: str) -> dict:
    (element,) = [e for e in scenario.builder.elements if e.get("declaredName") == name]
    return element


def _framing_types(scenario) -> tuple[dict, dict]:
    """Scope and out-of-scope declarations of the synthetic increment."""
    builder, framing = scenario.builder, scenario.framing
    scope = builder.definition("PartDefinition", "IncrementScope", framing)
    out_of_scope = builder.definition("PartDefinition", "OutOfScopeItem", framing)
    builder.usage("PartUsage", "fixtureScope", framing, [scope])
    builder.usage("PartUsage", "fixtureOutOfScopeItem", framing, [out_of_scope])
    return scope, out_of_scope


def _steps(scenario, **changes) -> list[WorkflowStep]:
    """The model's workflow steps (checked steps in full, the others with their parameters)."""
    scope, out_of_scope = _framing_types(scenario)
    steps = [
        WorkflowStep("frameIncrement", P0, (
            P("increment", "EngineeringIncrement"), P("charter", "IncrementTraceObligations"),
            P("problemStatement", "ProblemStatement", "RequirementUsage"),
            P("engineeringQuestion", "IncrementEngineeringQuestion"),
            P("lifecycleDecision", "IncrementLifecycleDecision"),
            P("assumptions", "Assumption", bounds=(1, INFINITY)), P("scope", scope),
            P("outOfScopeItems", out_of_scope, bounds=(1, INFINITY)),
            P("framedConcerns", None, "ConcernUsage", bounds=(1, INFINITY)),
        ), (
            C("incrementHasIdentifier", "incrementShortName", "increment"),
            C("incrementHasCharter", "charterReferencesIncrement", "charter"),
            C("incrementHasProblemStatement", "problemStatementSubject", "problemStatement"),
            C("incrementHasEngineeringQuestion", "ownedByIncrementPackage", "engineeringQuestion"),
            C("incrementHasLifecycleDecision", "ownedByIncrementPackage", "lifecycleDecision"),
            C("incrementHasAssumption", "ownedByIncrementPackage", "assumptions"),
            C("incrementHasStakeholder", "stakeholderMember", "problemStatement"),
            C("incrementHasFramedConcern", "framedByIncrementView", "framedConcerns"),
            C("incrementHasScope", "ownedByIncrementPackage", "scope"),
            C("incrementHasOutOfScopeItem", "ownedByIncrementPackage", "outOfScopeItems"),
            C("incrementHasOwner", "charterOwner", "charter"),
            C("incrementDeclaresApplicablePhases", "charterApplicablePhases", "charter"),
            C("incrementDeclaresExpectedArtifacts", "charterExpectedArtifacts", "charter"),
            C("incrementDeclaresExpectedReviewEvidence", "charterExpectedReviewEvidence", "charter"),
        )),
        WorkflowStep("frameConcerns", "phase1_concernFraming", (
            P("problemStatement", "ProblemStatement", "RequirementUsage", "in"),
            P("concerns", None, "ConcernUsage", bounds=(1, INFINITY)),
        )),
        WorkflowStep("elaborateNeeds", P4, (
            P("problemStatement", "ProblemStatement", "RequirementUsage", "in"),
            P("concerns", None, "ConcernUsage", "in", (0, INFINITY)),
            P("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),
        ), (
            C("needHasStatement", "requireConstraint", "needs"),
            C("needHasStakeholder", "stakeholderMember", "needs"),
            C("needHasSource", "sourceAttribute", "needs"),
            C("needHasRationale", "rationaleAttribute", "needs"),
            C("needHasValidationScenario", "hasValidationScenario", "needs"),
            C("needFramesConcern", "framesStakeholderConcern", "needs"),
        )),
        WorkflowStep("specifyRequirements", P5, (
            P("needs", "Need", "RequirementUsage", "in", (0, INFINITY)),
            P("requirements", "Requirement", "RequirementUsage", bounds=(1, INFINITY)),
        ), (
            C("requirementDerivesFromNeed", "derivesRequirementFromNeed", "requirements"),
            C("requirementHasOneSubject", "oneNativeSubject", "requirements"),
            C("requirementHasVerificationMethod", "oneVerificationMethodKind", "requirements"),
            C("requirementSpecifiesFeatureOrCapability", "specifiesFeatureOrCommonCapability", "requirements",
              advisory=True),
        )),
        WorkflowStep("defineFunctionalArchitecture", "phase6_functionalArchitecture", (
            P("requirements", "Requirement", "RequirementUsage", "in", (0, INFINITY)),
            P("functions", None, "ActionUsage", bounds=(1, INFINITY)),
        )),
        WorkflowStep("planVerificationAndEvidence", P10, (
            P("requirements", "Requirement", "RequirementUsage", "in", (0, INFINITY)),
            P("verificationCases", None, "VerificationCaseUsage", bounds=(1, INFINITY)),
        ), (
            C("verificationCaseVerifiesRequirement", "verifiesIncrementRequirement", "verificationCases"),
            C("requirementVerifiedByVerificationCase", "verifiedBy", "requirements"),
            C("verificationCaseVerifiesAcceptanceCriterion", "verifiesAcceptanceCriterion", "verificationCases",
              advisory=True),
            C("verificationCaseHasEvidenceRecordOrStatus", "evidenceRecordOrStatus", "verificationCases",
              advisory=True),
        )),
    ]
    return [replace(step, **changes.get(step.name, {})) for step in steps]


def _view(scenario) -> ModelView:
    builder = scenario.builder
    return ModelView(builder.elements, _traversal(builder), sources=builder.sources)


def _gates(scenario):
    return read_method_gates(_view(scenario), revision_label=REVISION.git_commit)


def _evaluate(scenario):
    return evaluate_increment(_view(scenario), scenario.increment_id, revision=REVISION)


def _scenario(applicable_phases=(P0, P4, P5, P10), **changes):
    scenario = increment_scenario(applicable_phases=applicable_phases)
    scenario.builder.kernel_definition("AcceptanceCriterion")
    increment_workflow(scenario.builder, _steps(scenario, **changes))
    return scenario


def _unit(evaluation, gate):
    (unit,) = [u for u in evaluation.canonical.units if u.unit_id == gate]
    return unit


def _children(evaluation, gate):
    return [r for r in evaluation.canonical.results if r.unit_id == gate and r.subject_id]


ADVISORY = {"requirementSpecifiesFeatureOrCapability", "verificationCaseVerifiesAcceptanceCriterion",
            "verificationCaseHasEvidenceRecordOrStatus"}


def test_the_workflow_reads_every_check_into_one_contract_in_step_order() -> None:
    scenario = _scenario()
    gates = _gates(scenario)
    assert gates.available and gates.representation == "increment-workflow", gates.problems
    obligations = gates.contract.obligations
    assert len(obligations) == 28
    assert [o.obligation_id for o in obligations][:2] == ["incrementHasIdentifier", "incrementHasCharter"]
    assert [o.obligation_id for o in obligations][-1] == "verificationCaseHasEvidenceRecordOrStatus"
    by_id = {o.obligation_id: o for o in obligations}
    assert by_id["needFramesConcern"].predicate == "framesStakeholderConcern"
    assert {o.obligation_id for o in obligations if not o.required} == ADVISORY
    # Framing always applies; later steps apply when the charter declares their phase.
    assert by_id["incrementHasCharter"].applicability_kind == me.APPLICABILITY_UNCONDITIONAL
    assert by_id["needFramesConcern"].applicability_kind == me.APPLICABILITY_DECLARED_PHASE
    assert by_id["requirementHasOneSubject"].cardinality == (1, 1)
    assert by_id["needFramesConcern"].cardinality == (1, UNBOUNDED)
    # A check about an in parameter [0..*] permits an empty population.
    assert by_id["requirementVerifiedByVerificationCase"].permitted_empty
    assert gates.phases == (P0, P4, P5, P10)
    assert gates.labels["requirementVerifiedByVerificationCase"]["direction"] == "in"


def test_a_complete_increment_passes_every_blocking_check() -> None:
    evaluation = _evaluate(_scenario())
    for unit in evaluation.canonical.units:
        if unit.unit_id in ADVISORY:
            continue
        assert (unit.coverage, unit.state, unit.verdict) == (
            me.COVERAGE_ASSESSED, me.STATE_COMPLETE, me.VERDICT_PASS), (unit.unit_id, unit.diagnostics)
    assert _unit(evaluation, "verificationCaseVerifiesAcceptanceCriterion").verdict == me.VERDICT_FAIL
    assert _unit(evaluation, "verificationCaseHasEvidenceRecordOrStatus").state == me.STATE_INDETERMINATE
    assert [block["phase_exit"] for block in evaluation.status()["phases"]] == ["READY"] * 4
    assert evaluation.next_obligation()["next"] is None


def test_subjects_conform_to_the_parameter_type_or_usage_kind() -> None:
    scenario = _scenario()
    builder = scenario.builder
    other = builder.definition("PartDefinition", "OtherIncrement", scenario.needs_package,
                               [scenario.vocabulary["EngineeringIncrement"]])
    stranger = builder.usage("RequirementUsage", "strangerNeed", scenario.needs_package,
                             [_named(scenario, "FixtureNeed")])
    builder.subject(stranger, other, name="increment")
    evaluation = _evaluate(scenario)
    assert {r.subject_id for r in _children(evaluation, "needFramesConcern")} == {n["@id"] for n in scenario.needs}
    assert [r.subject_id for r in _children(evaluation, "incrementHasFramedConcern")] == [scenario.concern["@id"]]
    assert [r.subject_id for r in _children(evaluation, "verificationCaseVerifiesRequirement")] == [
        scenario.cases[0]["@id"]]


def test_framing_always_applies_and_later_steps_need_their_phase_declared() -> None:
    evaluation = _evaluate(_scenario(applicable_phases=(P4,)))
    assert _unit(evaluation, "incrementHasCharter").verdict == me.VERDICT_PASS
    assert _unit(evaluation, "needFramesConcern").verdict == me.VERDICT_PASS
    assert _unit(evaluation, "requirementHasOneSubject").verdict == me.VERDICT_NOT_APPLICABLE


def test_open_steps_leave_their_successors_not_attempted() -> None:
    scenario = _scenario()
    scenario.builder.remove(_named(scenario, "need0ValidationPlanning"))
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, "needHasValidationScenario").verdict == me.VERDICT_FAIL
    assert me.NOT_ATTEMPTED in _unit(evaluation, "requirementDerivesFromNeed").reason_codes
    gates = evaluation.gate_set.contract.obligations
    (derives,) = [o for o in gates if o.obligation_id == "requirementDerivesFromNeed"]
    assert "needFramesConcern" in derives.depends_on and "incrementHasCharter" not in derives.depends_on
    (statement,) = [o for o in gates if o.obligation_id == "needHasStatement"]
    assert "incrementHasCharter" in statement.depends_on  # steps without checks are passed over
    assert evaluation.next_obligation()["next"]["gate"] == "needHasValidationScenario"


def test_an_unknown_check_id_fails_closed() -> None:
    scenario = increment_scenario()
    increment_workflow(scenario.builder, [WorkflowStep("elaborateNeeds", P4, (
        P("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),), (
        C("needSomething", "noSuchCheck", "needs"),))])
    gates = _gates(scenario)
    assert gates.contract is None and any("noSuchCheck" in problem for problem in gates.problems)
    assert _evaluate(scenario).phase_contract()["reason_codes"] == [me.INVALID_CONTRACT]


def test_a_check_about_something_other_than_a_step_parameter_is_invalid() -> None:
    scenario = _scenario()
    annotation = [e for e in scenario.builder.elements if e["@type"] == "Annotation"][0]
    annotation["annotatedElement"] = ref(scenario.needs[0])
    gates = _gates(scenario)
    assert gates.contract is None
    assert any("not a parameter of the step" in problem for problem in gates.problems)


def test_cyclic_successions_are_invalid() -> None:
    scenario = increment_scenario()
    increment_workflow(scenario.builder, _steps(scenario), successions=[
        ("frameIncrement", "elaborateNeeds"), ("elaborateNeeds", "frameIncrement")])
    gates = _gates(scenario)
    assert gates.contract is None and any("cycle" in problem for problem in gates.problems)


def test_minimum_raises_the_number_of_targets_each_subject_needs() -> None:
    evaluation = _evaluate(_scenario(specifyRequirements={"checks": (
        C("requirementDerivesFromNeed", "derivesRequirementFromNeed", "requirements", minimum=2),)}))
    assert _unit(evaluation, "requirementDerivesFromNeed").verdict == me.VERDICT_FAIL


def test_one_native_subject_rejects_a_second_subject() -> None:
    scenario = _scenario()
    scenario.builder.subject(scenario.requirements[0], scenario.definition, name="secondSubject")
    verdicts = {r.subject_id: r.verdict for r in _children(_evaluate(scenario), "requirementHasOneSubject")}
    assert verdicts == {scenario.requirements[0]["@id"]: me.VERDICT_FAIL,
                        scenario.requirements[1]["@id"]: me.VERDICT_PASS}


def _owner(builder, element) -> str | None:
    membership = next((m for m in builder.elements if m["@id"] == element["owningRelationship"]["@id"]), None)
    return membership["owningRelatedElement"]["@id"] if membership else None


def test_one_verification_method_kind_requires_one_standard_kind() -> None:
    scenario = _scenario()
    builder = scenario.builder
    feature = builder.library_feature("verificationMethod")
    holders = [e for e in builder.elements if e.get("name") == "verificationMethod" and e["@type"] == "AttributeUsage"]
    (first,) = [h for h in holders if _owner(builder, h) == scenario.requirements[0]["@id"]]
    builder.remove(first)
    builder.attribute(scenario.requirements[0], "verificationMethod", "review", redefines=feature)
    verdicts = {r.subject_id: r.verdict for r in _children(_evaluate(scenario), "requirementHasVerificationMethod")}
    assert verdicts[scenario.requirements[0]["@id"]] == me.VERDICT_FAIL
    assert verdicts[scenario.requirements[1]["@id"]] == me.VERDICT_PASS


def test_framing_checks_name_what_is_missing() -> None:
    scenario = _scenario()
    builder = scenario.builder
    builder.remove(*[e for e in builder.elements if e["@type"] == "AttributeUsage" and e.get("name") == "owner"
                     and _owner(builder, e) == scenario.charter["@id"]])
    stray = builder.usage("PartUsage", "strayAssumption", scenario.evidence_package,
                          [scenario.vocabulary["Assumption"]])
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, "incrementHasOwner").verdict == me.VERDICT_FAIL
    verdicts = {r.subject_id: r.verdict for r in _children(evaluation, "incrementHasAssumption")}
    assert verdicts[stray["@id"]] == me.VERDICT_FAIL


def test_the_parameter_multiplicity_sets_the_minimum_population() -> None:
    for bounds in ((0, INFINITY), (1, INFINITY)):
        scenario = increment_scenario()
        increment_workflow(scenario.builder, [WorkflowStep("planVerificationAndEvidence", P10, (
            P("verificationCases", None, "VerificationCaseUsage", bounds=bounds),), (
            C("verificationCaseVerifiesRequirement", "verifiesIncrementRequirement", "verificationCases"),))])
        scenario.builder.remove(scenario.cases[0])
        unit = _unit(_evaluate(scenario), "verificationCaseVerifiesRequirement")
        if bounds[0] == 0:
            assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE)
        else:
            assert (unit.verdict, unit.reason_codes) == (me.VERDICT_FAIL, (me.POPULATION_POLICY_VIOLATION,))


def test_without_a_workflow_binding_the_method_gates_are_read() -> None:
    scenario = increment_scenario()
    scenario.builder.kernel_definition("AcceptanceCriterion")
    method_gates(scenario.builder, synthetic_method())
    increment_workflow(scenario.builder, _steps(scenario), bind=False)
    gates = _gates(scenario)
    assert gates.available and gates.representation == "method-gates"


def test_a_workflow_without_method_check_identity_is_unavailable() -> None:
    scenario = _scenario()
    scenario.builder.bindings[:] = [b for b in scenario.builder.bindings if b["ontology_class"] != "MethodCheck"]
    gates = _gates(scenario)
    assert gates.contract is None and "MethodCheck" in gates.reason
    assert _evaluate(scenario).status()["reason_codes"] == [me.CONTRACT_UNAVAILABLE]


def test_the_contract_projection_names_step_parameter_and_subject_type() -> None:
    contract = _evaluate(_scenario()).phase_contract(P4)
    record = contract["gates"][-1]
    assert (record["obligation_id"], record["step"], record["parameter"], record["check"]) == (
        "needFramesConcern", "elaborateNeeds", "needs", "framesStakeholderConcern")
    assert record["subject_type"].endswith("StakeholderNeedCandidate")
    assert record["what_satisfies"].startswith("frame a stakeholder concern")


def test_every_check_the_model_declares_is_supported() -> None:
    """Every check id in the model's workflow resolves in the engine's registry."""
    text = re.sub(r"/\*.*?\*/", "", WORKFLOW_FILE.read_text(encoding="utf-8"), flags=re.S)
    used = set(re.findall(r':>>\s*check\s*=\s*"([^"]+)"', text))
    registry = MethodCheckRegistry.for_relations(RelationCheckRegistry.for_contract(model_facade()).names())
    assert used and used <= set(registry.names()), used - set(registry.names())
