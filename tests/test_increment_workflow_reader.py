"""The increment workflow, read from the increment's charter and evaluated.

The method is the workflow the increment's charter declares: charter ->
its definition -> ``action workflow : IncrementWorkflow`` -> the workflow
definition -> its step actions (ordered by successions from ``start`` to
``done``) -> their step definitions (``phase``, parameters) -> metadata usages
whose metadata definition declares ``check``. No kernel binding of the
workflow declarations is needed. Every check is evaluated; the step order only
ranks ``next``. Subjects come from the packages the charter declares.
"""

from __future__ import annotations

import re
from pathlib import Path

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView, resolve_increment
from de4sdv.semantic.increment_workflow import (
    UNBOUNDED,
    WORKFLOW_FEATURE,
    read_increment_method,
    read_revision_method,
)
from de4sdv.semantic.method_checks import MethodCheckRegistry
from de4sdv.semantic.model_authority_runtime import model_facade
from de4sdv.semantic.relation_checks import RelationCheckRegistry
from increment_model_fixtures import (
    INFINITY,
    WorkflowCheck,
    WorkflowParameter,
    WorkflowStep,
    attach_workflow,
    increment_scenario,
    increment_workflow,
    install_model_workflow,
    ref,
)
from test_revision_index import _traversal

WORKFLOW_FILE = (Path(__file__).resolve().parents[1]
                 / "textual-notation-of-model/packages/methods/de4sdv/de4sdv_increment_workflow.sysml")
REVISION = me.RevisionIdentity("a" * 40, "project", "commit", "full-model")
P0, P4, P5, P10 = ("phase0_incrementFraming", "phase4_needs", "phase5_requirements", "phase10_vvEvidence")
P = WorkflowParameter
C = WorkflowCheck
ADVISORY = {"requirementSpecifiesFeatureOrCapability", "verificationCaseVerifiesAcceptanceCriterion",
            "verificationCaseHasEvidenceRecordOrStatus"}


def _named(scenario, name: str) -> dict:
    (element,) = [e for e in scenario.builder.elements if e.get("declaredName") == name]
    return element


def _view(scenario) -> ModelView:
    builder = scenario.builder
    return ModelView(builder.elements, _traversal(builder), sources=builder.sources)


def _method(scenario):
    view = _view(scenario)
    return read_increment_method(view, resolve_increment(view, scenario.increment_id),
                                 revision_label=REVISION.git_commit)


def _evaluate(scenario):
    return evaluate_increment(_view(scenario), scenario.increment_id, revision=REVISION)


def _scenario(applicable_phases=(P0, P4, P5, P10), **changes):
    scenario = increment_scenario(applicable_phases=applicable_phases)
    install_model_workflow(scenario, **changes)
    return scenario


def _unit(evaluation, check):
    (unit,) = [u for u in evaluation.canonical.units if u.unit_id == check]
    return unit


def _children(evaluation, check):
    return [r for r in evaluation.canonical.results if r.unit_id == check and r.subject_id]


def _owner(builder, element) -> str | None:
    membership = next((m for m in builder.elements if m["@id"] == element["owningRelationship"]["@id"]), None)
    return membership["owningRelatedElement"]["@id"] if membership else None


def test_the_charter_declares_the_workflow_read_into_one_contract() -> None:
    scenario = _scenario()
    method = _method(scenario)
    assert method.available, method.problems or method.reason
    assert not any(b["ontology_class"] in {"IncrementWorkflow", "MethodCheck"} for b in scenario.builder.bindings)
    obligations = method.contract.obligations
    assert len(obligations) == 28
    assert [o.obligation_id for o in obligations][:2] == ["incrementHasIdentifier", "incrementHasCharter"]
    by_id = {o.obligation_id: o for o in obligations}
    assert by_id["needFramesConcern"].predicate == "framesStakeholderConcern"
    assert {o.obligation_id for o in obligations if not o.required} == ADVISORY
    assert all(o.depends_on == () for o in obligations)  # successions rank, they never gate
    assert by_id["incrementHasCharter"].applicability_kind == me.APPLICABILITY_UNCONDITIONAL
    assert by_id["needFramesConcern"].applicability_kind == me.APPLICABILITY_DECLARED_PHASE
    assert (by_id["incrementHasCharter"].minimum_population, by_id["incrementHasCharter"].maximum_population) == (1, 1)
    assert by_id["needFramesConcern"].maximum_population is None
    assert by_id["requirementHasOneSubject"].cardinality == (1, 1)
    assert by_id["requirementHasVerificationMethod"].cardinality == (1, 1)
    assert by_id["needFramesConcern"].cardinality == (1, UNBOUNDED)
    assert by_id["requirementVerifiedByVerificationCase"].permitted_empty
    assert method.phases == (P0, P4, P5, P10)
    assert method.labels["needFramesConcern"]["check_definition"].endswith("MethodCheck")


def test_the_workflow_is_found_through_a_definition_the_charter_specializes() -> None:
    scenario = increment_scenario()
    builder = scenario.builder
    charter_definition = _named(scenario, "FixtureCharter")
    base = builder.definition("PartDefinition", "CharterBase", scenario.framing)
    builder.specializes(charter_definition, base)
    made = increment_workflow(builder, [WorkflowStep("elaborateNeeds", P4, (
        P("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),), (
        C("needHasStatement", "requireConstraint", "needs"),))])
    feature = builder.new("ActionUsage", name="workflow")
    builder.own(base, feature, kind="FeatureMembership", member_name="workflow")
    builder.typed(feature, made["workflow"])
    method = _method(scenario)
    assert method.available and [o.obligation_id for o in method.contract.obligations] == ["needHasStatement"]


def test_a_charter_without_a_workflow_has_no_executable_method() -> None:
    scenario = increment_scenario()
    increment_workflow(scenario.builder, [WorkflowStep("elaborateNeeds", P4, (
        P("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),), (
        C("needHasStatement", "requireConstraint", "needs"),))])
    method = _method(scenario)
    assert method.contract is None and "declares no workflow feature" in method.reason
    status = _evaluate(scenario).status()
    assert status["reason_codes"] == [me.CONTRACT_UNAVAILABLE]


def test_two_charters_leave_the_method_unavailable() -> None:
    scenario = _scenario()
    builder = scenario.builder
    second = builder.usage("PartUsage", "secondCharter", scenario.framing, [_named(scenario, "FixtureCharter")])
    builder.attribute(second, "increment", scenario.usage, kind="PartUsage")
    method = _method(scenario)
    assert method.contract is None and "2 charter declarations" in method.reason


def test_a_metadata_usage_without_a_check_attribute_is_not_a_check() -> None:
    scenario = _scenario()
    builder = scenario.builder
    note_definition = builder.definition("MetadataDefinition", "ReviewNote", scenario.framing)
    builder.own(note_definition, builder.new("AttributeUsage", name="text"), kind="FeatureMembership",
                member_name="text")
    note = builder.new("MetadataUsage", name="reviewNote")
    builder.own(_named(scenario, "ElaborateNeedsStep"), note, kind="FeatureMembership", member_name="reviewNote")
    builder.typed(note, note_definition)
    method = _method(scenario)
    assert method.available and "reviewNote" not in {o.obligation_id for o in method.contract.obligations}


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


def test_every_check_is_evaluated_and_next_follows_workflow_order() -> None:
    scenario = _scenario()
    builder = scenario.builder
    builder.remove(_named(scenario, "need0ValidationPlanning"))
    builder.remove(builder.feature_of(scenario.charter, "owner"))
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, "needHasValidationScenario").verdict == me.VERDICT_FAIL
    assert _unit(evaluation, "incrementHasOwner").verdict == me.VERDICT_FAIL
    # Open framing and needs checks block nothing: later steps are evaluated.
    assert _unit(evaluation, "requirementDerivesFromNeed").verdict == me.VERDICT_PASS
    assert all(me.NOT_ATTEMPTED not in u.reason_codes for u in evaluation.canonical.units)
    assert evaluation.next_obligation()["next"]["gate"] == "incrementHasOwner"
    assert evaluation.next_obligation(phase=P4)["next"]["gate"] == "needHasValidationScenario"
    assert {entry["gate"] for entry in evaluation.gaps()["blocking"]} == {
        "incrementHasOwner", "needHasValidationScenario"}


def test_subjects_are_the_declared_scope_elements_of_the_parameter_type_or_kind() -> None:
    scenario = _scenario()
    builder = scenario.builder
    undeclared = builder.package("DE4SDV_FixtureOtherEvidence")
    builder.references(undeclared, scenario.usage)
    stray = builder.usage("VerificationCaseUsage", "strayVerification", undeclared,
                          [_named(scenario, "FixtureVerification")])
    evaluation = _evaluate(scenario)
    assert {r.subject_id for r in _children(evaluation, "needFramesConcern")} == {n["@id"] for n in scenario.needs}
    assert [r.subject_id for r in _children(evaluation, "incrementHasFramedConcern")] == [scenario.concern["@id"]]
    cases = [r.subject_id for r in _children(evaluation, "verificationCaseVerifiesRequirement")]
    assert cases == [scenario.cases[0]["@id"]] and stray["@id"] not in cases


def test_framing_always_applies_and_later_steps_need_their_phase_declared() -> None:
    evaluation = _evaluate(_scenario(applicable_phases=(P4,)))
    assert _unit(evaluation, "incrementHasCharter").verdict == me.VERDICT_PASS
    assert _unit(evaluation, "needFramesConcern").verdict == me.VERDICT_PASS
    assert _unit(evaluation, "requirementHasOneSubject").verdict == me.VERDICT_NOT_APPLICABLE


def test_a_population_above_the_parameter_multiplicity_fails() -> None:
    scenario = _scenario()
    builder = scenario.builder
    second = builder.usage("RequirementUsage", "secondProblemStatement", scenario.framing,
                           [scenario.vocabulary["ProblemStatement"]])
    builder.subject(second, scenario.definition, name="increment")
    unit = _unit(_evaluate(scenario), "incrementHasProblemStatement")
    assert (unit.verdict, unit.reason_codes) == (me.VERDICT_FAIL, (me.POPULATION_POLICY_VIOLATION,))
    assert "at most 1" in unit.diagnostics[0]


def test_the_parameter_multiplicity_sets_the_minimum_population() -> None:
    for bounds in ((0, INFINITY), (1, INFINITY)):
        scenario = increment_scenario()
        increment_workflow(scenario.builder, [WorkflowStep("planVerificationAndEvidence", P10, (
            P("verificationCases", None, "VerificationCaseUsage", bounds=bounds),), (
            C("verificationCaseVerifiesRequirement", "verifiesIncrementRequirement", "verificationCases"),))],
            charter=scenario.charter)
        scenario.builder.remove(scenario.cases[0])
        unit = _unit(_evaluate(scenario), "verificationCaseVerifiesRequirement")
        if bounds[0] == 0:
            assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE)
        else:
            assert (unit.verdict, unit.reason_codes) == (me.VERDICT_FAIL, (me.POPULATION_POLICY_VIOLATION,))


def test_an_unknown_check_id_fails_closed() -> None:
    scenario = increment_scenario()
    increment_workflow(scenario.builder, [WorkflowStep("elaborateNeeds", P4, (
        P("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),), (
        C("needSomething", "noSuchCheck", "needs"),))], charter=scenario.charter)
    method = _method(scenario)
    assert method.contract is None and any("noSuchCheck" in problem for problem in method.problems)
    assert _evaluate(scenario).phase_contract()["reason_codes"] == [me.INVALID_CONTRACT]


def test_a_check_about_something_other_than_a_step_parameter_is_invalid() -> None:
    scenario = _scenario()
    annotation = [e for e in scenario.builder.elements if e["@type"] == "Annotation"][0]
    annotation["annotatedElement"] = ref(scenario.needs[0])
    method = _method(scenario)
    assert method.contract is None and any("not a parameter of the step" in p for p in method.problems)


def test_cyclic_successions_are_invalid() -> None:
    scenario = increment_scenario()
    increment_workflow(scenario.builder, [
        WorkflowStep("elaborateNeeds", P4, (P("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),),
                     (C("needHasStatement", "requireConstraint", "needs"),)),
        WorkflowStep("specifyRequirements", P5, (
            P("requirements", "Requirement", "RequirementUsage", bounds=(1, INFINITY)),), (
            C("requirementHasOneSubject", "oneNativeSubject", "requirements"),)),
    ], charter=scenario.charter, successions=[("elaborateNeeds", "specifyRequirements"),
                                              ("specifyRequirements", "elaborateNeeds")])
    method = _method(scenario)
    assert method.contract is None and any("cycle" in problem for problem in method.problems)


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


def _set_verification_method(scenario, value) -> None:
    builder = scenario.builder
    feature = builder.library_feature("verificationMethod")
    holders = [e for e in builder.elements if e.get("name") == "verificationMethod" and e["@type"] == "AttributeUsage"]
    (first,) = [h for h in holders if _owner(builder, h) == scenario.requirements[0]["@id"]]
    builder.remove(first)
    builder.attribute(scenario.requirements[0], "verificationMethod", value, redefines=feature)


def test_one_verification_method_kind_requires_one_standard_kind() -> None:
    for value in ("review", ["test", "analyze"]):
        scenario = _scenario()
        _set_verification_method(scenario, value)
        verdicts = {r.subject_id: r.verdict
                    for r in _children(_evaluate(scenario), "requirementHasVerificationMethod")}
        assert verdicts[scenario.requirements[0]["@id"]] == me.VERDICT_FAIL, value
        assert verdicts[scenario.requirements[1]["@id"]] == me.VERDICT_PASS


def test_framing_checks_name_what_is_missing() -> None:
    scenario = _scenario()
    builder = scenario.builder
    builder.remove(builder.feature_of(scenario.charter, "owner"))
    stray = builder.usage("PartUsage", "strayAssumption", scenario.evidence_package,
                          [scenario.vocabulary["Assumption"]])
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, "incrementHasOwner").verdict == me.VERDICT_FAIL
    # Framing reads the increment's own package: an assumption elsewhere is not counted.
    assert stray["@id"] not in {r.subject_id for r in _children(evaluation, "incrementHasAssumption")}
    assert _unit(evaluation, "incrementHasAssumption").verdict == me.VERDICT_PASS


def test_the_revision_method_is_the_one_workflow_its_charters_declare() -> None:
    scenario = _scenario()
    assert read_revision_method(_view(scenario), revision_label=REVISION.git_commit).available
    other = increment_workflow(scenario.builder, [WorkflowStep("elaborateNeeds", P4, (
        P("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),), (
        C("needHasStatement", "requireConstraint", "needs"),))], package_name="DE4SDV_OtherWorkflow")
    second_definition = scenario.builder.definition("PartDefinition", "OtherCharter", scenario.framing,
                                                    [scenario.vocabulary["IncrementTraceObligations"]])
    second = scenario.builder.usage("PartUsage", "otherCharter", scenario.framing, [second_definition])
    attach_workflow(scenario.builder, second, other["workflow"])
    method = read_revision_method(_view(scenario), revision_label=REVISION.git_commit)
    assert method.contract is None and "2 workflows" in method.reason


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


def test_a_population_failure_says_how_many_elements_of_which_type_to_keep() -> None:
    scenario = _scenario()
    builder = scenario.builder
    second = builder.usage("RequirementUsage", "secondProblemStatement", scenario.framing,
                           [scenario.vocabulary["ProblemStatement"]])
    builder.subject(second, scenario.definition, name="increment")
    evaluation = _evaluate(scenario)
    (entry,) = [g for g in evaluation.gaps()["blocking"] if g["gate"] == "incrementHasProblemStatement"]
    assert entry["kind"] == "violation"
    assert "exactly 1" in entry["what_to_author"] and "ProblemStatement" in entry["what_to_author"]
    assert "the population has 2 subjects" in entry["what_to_author"]


def test_the_model_charter_declares_the_workflow_feature_the_reader_follows() -> None:
    """The model's IncrementCharter owns the workflow feature the reader starts from."""
    text = re.sub(r"/\*.*?\*/", "", WORKFLOW_FILE.read_text(encoding="utf-8"), flags=re.S)
    charter = re.search(r"part def IncrementCharter\b[^{]*\{(.*?)\n  \}", text, re.S)
    assert charter is not None
    assert re.search(rf"\baction\s+{WORKFLOW_FEATURE}\s*:\s*IncrementWorkflow\b", charter.group(1))


def test_framing_counts_only_the_increments_own_package() -> None:
    """Framing checks read the package that owns the increment; later steps read the declared packages."""
    scenario = _scenario()
    builder = scenario.builder
    phase_decision = builder.usage("PartUsage", "phaseDecision", scenario.needs_package,
                                   [scenario.vocabulary["IncrementLifecycleDecision"]])
    evaluation = _evaluate(scenario)
    unit = _unit(evaluation, "incrementHasLifecycleDecision")
    assert unit.verdict == me.VERDICT_PASS, unit.diagnostics
    assert phase_decision["@id"] not in {r.subject_id for r in _children(evaluation, "incrementHasLifecycleDecision")}
    # A need in another declared package is still a subject of the needs step.
    assert {r.subject_id for r in _children(evaluation, "needHasStatement")} == {n["@id"] for n in scenario.needs}


def test_framed_concern_check_needs_one_framed_concern_of_the_own_package() -> None:
    scenario = _scenario()
    builder = scenario.builder
    unframed = builder.usage("ConcernUsage", "unframedConcern", scenario.framing)
    foreign = builder.usage("ConcernUsage", "foreignConcern", scenario.needs_package)
    evaluation = _evaluate(scenario)
    subjects = {r.subject_id for r in _children(evaluation, "incrementHasFramedConcern")}
    assert unframed["@id"] in subjects and foreign["@id"] not in subjects
    assert _unit(evaluation, "incrementHasFramedConcern").verdict == me.VERDICT_PASS
    viewpoint = _named(scenario, "selectedViewpoint")
    builder.remove(*[e for e in builder.elements if e.get("@type") == "FramedConcernMembership"
                     and e.get("owningRelatedElement", {}).get("@id") == viewpoint["@id"]])
    assert _unit(_evaluate(scenario), "incrementHasFramedConcern").verdict == me.VERDICT_FAIL
