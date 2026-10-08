"""The increment workflow (provisional representation) evaluated against an increment.

The method is ``action def IncrementWorkflow``: step actions ordered by
successions, each typed by a step definition with a ``phase`` attribute, a
typed ``out`` parameter with a multiplicity and ``MethodCheck`` metadata
``about`` that output (``check`` id, optional ``minimum`` and ``advisory``).
Check ids resolve in the method-check registry; an unknown id fails closed.
Subjects are the increment's elements of the output's type.
"""

from __future__ import annotations

from dataclasses import replace

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.gate_reader import UNBOUNDED, read_method_gates
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from increment_model_fixtures import (
    INFINITY,
    WorkflowCheck,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
    method_gates,
    ref,
)
from test_increment_evaluation import P4, P5, P10, REVISION, synthetic_method
from test_revision_index import _traversal


def _named(scenario, name: str) -> dict:
    (element,) = [e for e in scenario.builder.elements if e.get("declaredName") == name]
    return element


def _steps(scenario, **changes) -> list[WorkflowStep]:
    steps = [
        WorkflowStep("needs", P4, "needs", "Need", checks=(
            WorkflowCheck("needFramesConcern", "needFramesConcern"),
            WorkflowCheck("needHasValidationScenario", "hasValidationScenario"),
        )),
        WorkflowStep("requirements", P5, "requirements", "Requirement", checks=(
            WorkflowCheck("requirementDerivesFromNeed", "derivesRequirementFromNeed"),
            WorkflowCheck("requirementHasOneSubject", "requirementHasOneSubject"),
            WorkflowCheck("requirementHasVerificationMethod", "hasVerificationMethod"),
            WorkflowCheck("requirementVerifiedByVerificationCase", "verifiedByVerificationCase"),
        )),
        WorkflowStep("verification", P10, "cases", _named(scenario, "FixtureVerification"), checks=(
            WorkflowCheck("verificationCaseVerifiesRequirement", "verify"),
            WorkflowCheck("verificationCaseHasEvidence", "hasEvidence", advisory=True),
        )),
    ]
    return [replace(step, **changes.get(step.name, {})) for step in steps]


def _view(scenario) -> ModelView:
    builder = scenario.builder
    return ModelView(builder.elements, _traversal(builder), sources=builder.sources)


def _evaluate(scenario):
    return evaluate_increment(_view(scenario), scenario.increment_id, revision=REVISION)


def _workflow_scenario(**changes):
    scenario = increment_scenario()
    increment_workflow(scenario.builder, _steps(scenario, **changes))
    return scenario


def _unit(evaluation, gate):
    (unit,) = [u for u in evaluation.canonical.units if u.unit_id == gate]
    return unit


def _children(evaluation, gate):
    return [r for r in evaluation.canonical.results if r.unit_id == gate and r.subject_id]


def test_the_workflow_reads_into_one_contract_in_step_order() -> None:
    scenario = _workflow_scenario()
    gates = read_method_gates(_view(scenario), revision_label=REVISION.git_commit)
    assert gates.available and gates.representation == "increment-workflow"
    obligations = gates.contract.obligations
    assert [o.obligation_id for o in obligations] == [
        "needFramesConcern", "needHasValidationScenario", "requirementDerivesFromNeed",
        "requirementHasOneSubject", "requirementHasVerificationMethod",
        "requirementVerifiedByVerificationCase", "verificationCaseVerifiesRequirement",
        "verificationCaseHasEvidence"]
    by_id = {o.obligation_id: o for o in obligations}
    assert by_id["needFramesConcern"].phase == P4 and by_id["needFramesConcern"].predicate == "needFramesConcern"
    assert by_id["requirementDerivesFromNeed"].predicate == "derivesRequirementFromNeed"
    assert by_id["needFramesConcern"].cardinality == (1, UNBOUNDED)
    assert by_id["requirementHasOneSubject"].cardinality == (1, 1)
    assert by_id["needFramesConcern"].required and not by_id["verificationCaseHasEvidence"].required
    assert by_id["needFramesConcern"].target_filters == ()
    assert gates.phases == (P4, P5, P10)
    assert gates.labels["needFramesConcern"]["step"] == "needs"
    assert gates.labels["needFramesConcern"]["output"] == "needs"


def test_a_complete_increment_passes_every_blocking_check() -> None:
    evaluation = _evaluate(_workflow_scenario())
    assert evaluation.gate_set.representation == "increment-workflow"
    for unit in evaluation.canonical.units:
        if unit.unit_id == "verificationCaseHasEvidence":
            assert unit.state == me.STATE_INDETERMINATE  # external evidence: method side
            continue
        assert (unit.coverage, unit.state, unit.verdict) == (
            me.COVERAGE_ASSESSED, me.STATE_COMPLETE, me.VERDICT_PASS), unit.unit_id
    status = evaluation.status()
    assert [block["phase_exit"] for block in status["phases"]] == ["READY", "READY", "READY"]
    assert evaluation.next_obligation()["next"] is None


def test_subjects_are_the_increment_elements_of_the_output_type() -> None:
    scenario = _workflow_scenario()
    builder = scenario.builder
    # A need of another increment: same type, outside this increment's scope.
    other_increment = builder.definition("PartDefinition", "OtherIncrement", scenario.needs_package,
                                         [scenario.vocabulary["EngineeringIncrement"]])
    stranger = builder.usage("RequirementUsage", "strangerNeed", scenario.needs_package,
                             [_named(scenario, "FixtureNeed")])
    builder.subject(stranger, other_increment, name="increment")
    evaluation = _evaluate(scenario)
    subjects = {r.subject_id for r in _children(evaluation, "needFramesConcern")}
    assert subjects == {need["@id"] for need in scenario.needs}
    requirement_subjects = {r.subject_id for r in _children(evaluation, "requirementHasOneSubject")}
    assert requirement_subjects == {requirement["@id"] for requirement in scenario.requirements}


def test_an_unknown_check_id_fails_closed() -> None:
    scenario = _workflow_scenario(needs={"checks": (WorkflowCheck("needSomething", "noSuchCheck"),)})
    gates = read_method_gates(_view(scenario), revision_label=REVISION.git_commit)
    assert gates.contract is None
    assert any("noSuchCheck" in problem for problem in gates.problems)
    contract = _evaluate(scenario).phase_contract()
    assert contract["reason_codes"] == [me.INVALID_CONTRACT]


def test_minimum_raises_the_number_of_targets_each_subject_needs() -> None:
    scenario = _workflow_scenario(requirements={"checks": (
        WorkflowCheck("requirementDerivesFromNeed", "derivesRequirementFromNeed", minimum=2),)})
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, "requirementDerivesFromNeed").verdict == me.VERDICT_FAIL
    assert all("outside the declared cardinality [2.." in r.diagnostics[0]
               for r in _children(evaluation, "requirementDerivesFromNeed"))


def test_an_advisory_check_never_blocks_the_phase_exit() -> None:
    scenario = _workflow_scenario(needs={"checks": (
        WorkflowCheck("needFramesConcern", "needFramesConcern"),
        WorkflowCheck("needDerivesSomething", "derivesRequirementFromNeed", advisory=True),
    )})
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, "needDerivesSomething").verdict == me.VERDICT_FAIL
    (needs,) = [block for block in evaluation.status()["phases"] if block["phase"] == P4]
    assert needs["phase_exit"] == "READY"
    assert "needDerivesSomething" in [note["gate"] for note in evaluation.gaps()["advisory"]]


def test_successions_order_the_steps_and_open_steps_block_their_successors() -> None:
    scenario = increment_scenario()
    steps = _steps(scenario)
    # Declared in reverse; the successions alone give the method order.
    increment_workflow(scenario.builder, list(reversed(steps)),
                       successions=[("needs", "requirements"), ("requirements", "verification")])
    gates = read_method_gates(_view(scenario), revision_label=REVISION.git_commit)
    assert [o.phase for o in gates.contract.obligations][0] == P4
    by_id = {o.obligation_id: o for o in gates.contract.obligations}
    assert set(by_id["requirementDerivesFromNeed"].depends_on) == {"needFramesConcern", "needHasValidationScenario"}
    assert set(by_id["verificationCaseVerifiesRequirement"].depends_on) == {
        "requirementDerivesFromNeed", "requirementHasOneSubject", "requirementHasVerificationMethod",
        "requirementVerifiedByVerificationCase"}
    assert by_id["needFramesConcern"].depends_on == ()
    scenario.builder.remove(_named(scenario, "need0ValidationPlanning"))
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, "needHasValidationScenario").verdict == me.VERDICT_FAIL
    assert me.NOT_ATTEMPTED in _unit(evaluation, "requirementDerivesFromNeed").reason_codes
    assert evaluation.next_obligation()["next"]["gate"] == "needHasValidationScenario"


def test_requirement_has_one_subject_rejects_a_second_subject() -> None:
    scenario = _workflow_scenario()
    scenario.builder.subject(scenario.requirements[0], scenario.definition, name="secondSubject")
    evaluation = _evaluate(scenario)
    verdicts = {r.subject_id: r.verdict for r in _children(evaluation, "requirementHasOneSubject")}
    assert verdicts[scenario.requirements[0]["@id"]] == me.VERDICT_FAIL
    assert verdicts[scenario.requirements[1]["@id"]] == me.VERDICT_PASS


def test_has_verification_method_requires_a_standard_kind() -> None:
    scenario = _workflow_scenario()
    builder = scenario.builder
    builder.remove(*[e for e in builder.elements if e.get("name") == "verificationMethod"
                     and e.get("owningRelationship") and e["@type"] == "AttributeUsage"
                     and builder.elements and _owner(builder, e) == scenario.requirements[0]["@id"]])
    builder.attribute(scenario.requirements[0], "verificationMethod", "review",
                      redefines=builder.library_feature("verificationMethod"))
    evaluation = _evaluate(scenario)
    verdicts = {r.subject_id: r.verdict for r in _children(evaluation, "requirementHasVerificationMethod")}
    assert verdicts[scenario.requirements[0]["@id"]] == me.VERDICT_FAIL
    assert verdicts[scenario.requirements[1]["@id"]] == me.VERDICT_PASS


def _owner(builder, element) -> str | None:
    membership = next((m for m in builder.elements if m["@id"] == element["owningRelationship"]["@id"]), None)
    return membership["owningRelatedElement"]["@id"] if membership else None


def test_the_output_multiplicity_sets_the_minimum_population() -> None:
    # One step only, so no succession prerequisite is involved.
    for bounds in ((0, INFINITY), (1, INFINITY)):
        scenario = increment_scenario()
        (verification,) = [step for step in _steps(scenario) if step.name == "verification"]
        increment_workflow(scenario.builder, [replace(verification, bounds=bounds)])
        scenario.builder.remove(scenario.cases[0])
        unit = _unit(_evaluate(scenario), "verificationCaseVerifiesRequirement")
        if bounds[0] == 0:
            assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE)
        else:
            assert unit.verdict not in (me.VERDICT_PASS, me.VERDICT_NOT_APPLICABLE)


def test_a_check_about_something_other_than_a_step_output_is_invalid() -> None:
    scenario = _workflow_scenario()
    made = [e for e in scenario.builder.elements if e["@type"] == "Annotation"]
    made[0]["annotatedElement"] = ref(scenario.needs[0])
    gates = read_method_gates(_view(scenario), revision_label=REVISION.git_commit)
    assert gates.contract is None
    assert any("not an output parameter" in problem for problem in gates.problems)


def test_cyclic_successions_are_invalid() -> None:
    scenario = increment_scenario()
    increment_workflow(scenario.builder, _steps(scenario),
                       successions=[("needs", "requirements"), ("requirements", "needs")])
    gates = read_method_gates(_view(scenario), revision_label=REVISION.git_commit)
    assert gates.contract is None
    assert any("cycle" in problem for problem in gates.problems)


def test_without_a_workflow_binding_the_method_gates_are_read() -> None:
    scenario = increment_scenario()
    scenario.builder.kernel_definition("AcceptanceCriterion")
    method_gates(scenario.builder, synthetic_method())
    increment_workflow(scenario.builder, _steps(scenario), bind=False)
    gates = read_method_gates(_view(scenario), revision_label=REVISION.git_commit)
    assert gates.available and gates.representation == "method-gates"


def test_a_workflow_without_method_check_identity_is_unavailable() -> None:
    scenario = _workflow_scenario()
    scenario.builder.bindings[:] = [b for b in scenario.builder.bindings if b["ontology_class"] != "MethodCheck"]
    gates = read_method_gates(_view(scenario), revision_label=REVISION.git_commit)
    assert gates.contract is None and "MethodCheck" in gates.reason
    status = _evaluate(scenario).status()
    assert status["reason_codes"] == [me.CONTRACT_UNAVAILABLE]


def test_the_contract_projection_names_step_output_and_subject_type() -> None:
    contract = _evaluate(_workflow_scenario()).phase_contract(P4)
    (record, _second) = contract["gates"]
    assert (record["step"], record["output"], record["check"]) == ("needs", "needs", "needFramesConcern")
    assert record["subject_type"].endswith("StakeholderNeedCandidate")
    assert record["what_satisfies"].startswith("frame a stakeholder concern")
