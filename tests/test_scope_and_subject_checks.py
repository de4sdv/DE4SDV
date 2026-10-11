"""The scope the checks evaluate and the subject rule, as method checks.

``charterExpectedArtifactsCoverContent`` (advisory, about the charter): a
package that holds increment content but is missing from the charter's
``expectedArtifacts``, the only scope the checks evaluate, is reported, never
silently ignored. ``subjectIsSystemOfInterest`` (advisory, about needs and
requirements): the subject is the system of interest the charter references
in ``systemOfInterest``, never the increment. ``requirementHasStatement``
reuses the needs' ``requireConstraint`` check. The scenarios declare a
synthetic workflow with these checks: the frozen genuine-export cut's
workflow predates them.
"""

from __future__ import annotations

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView, resolve_increment
from increment_model_fixtures import (
    INFINITY,
    WorkflowCheck,
    WorkflowParameter,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
)
from test_revision_index import _traversal

REVISION = me.RevisionIdentity("a" * 40, "project", "commit", "full-model")
P0, P4, P5 = ("phase0_incrementFraming", "phase4_needs", "phase5_requirements")
P, C = WorkflowParameter, WorkflowCheck
COVERAGE, NEED_SUBJECT, REQUIREMENT_SUBJECT, STATEMENT = (
    "expectedArtifactsCoverIncrementContent", "needSubjectIsSystemOfInterest",
    "requirementSubjectIsSystemOfInterest", "requirementHasStatement")


def _view(scenario) -> ModelView:
    builder = scenario.builder
    return ModelView(builder.elements, _traversal(builder), sources=builder.sources)


def _evaluate(scenario):
    return evaluate_increment(_view(scenario), scenario.increment_id, revision=REVISION)


def _unit(evaluation, check):
    (unit,) = [u for u in evaluation.canonical.units if u.unit_id == check]
    return unit


def _children(evaluation, check):
    return {r.subject_id: r for r in evaluation.canonical.results if r.unit_id == check and r.subject_id}


def _note(evaluation, check):
    (note,) = [n for n in evaluation.gaps()["advisory"] if n["gate"] == check]
    return note


def _scenario():
    """A complete increment whose charter declares a workflow with the coverage, statement and subject checks."""
    scenario = increment_scenario()
    increment_workflow(scenario.builder, [
        WorkflowStep("frameIncrement", P0, (
            P("increment", "EngineeringIncrement"), P("charter", "IncrementTraceObligations")), (
            C(COVERAGE, "charterExpectedArtifactsCoverContent", "charter", advisory=True),)),
        WorkflowStep("elaborateNeeds", P4, (P("needs", "Need", "RequirementUsage", bounds=(1, INFINITY)),), (
            C(NEED_SUBJECT, "subjectIsSystemOfInterest", "needs", advisory=True),)),
        WorkflowStep("specifyRequirements", P5, (
            P("requirements", "Requirement", "RequirementUsage", bounds=(1, INFINITY)),), (
            C(STATEMENT, "requireConstraint", "requirements"),
            C(REQUIREMENT_SUBJECT, "subjectIsSystemOfInterest", "requirements", advisory=True),)),
    ], charter=scenario.charter)
    return scenario


def _declare_system_of_interest(scenario, *, by_type: bool = False):
    """``part fixtureSystem : FixtureSystem`` in the framing package, referenced (or typed) by the charter."""
    b = scenario.builder
    system_def = b.definition("PartDefinition", "FixtureSystem", scenario.framing)
    system = b.usage("PartUsage", "fixtureSystem", scenario.framing, [system_def])
    if by_type:  # ref part :>> systemOfInterest : FixtureSystem;
        feature = b.new("PartUsage", name="systemOfInterest", declared=False, source=b.sources[scenario.charter["@id"]])
        b.own(scenario.charter, feature, kind="FeatureMembership", member_name="systemOfInterest")
        b.typed(feature, system_def)
    else:  # ref part :>> systemOfInterest = fixtureSystem;
        b.attribute(scenario.charter, "systemOfInterest", system, kind="PartUsage")
    return system_def, system


def _replace_subjects(scenario, *, narrowing=None, typed_by=None):
    """Replace the fixture's increment-typed subjects of every need and requirement."""
    b = scenario.builder
    for element in (*scenario.needs, *scenario.requirements):
        b.remove(b.feature_of(element, "increment"))
        if narrowing is not None:
            b.subject_narrowing(element, narrowing, name="system")
        elif typed_by is not None:
            b.subject(element, typed_by, name="system")


def _conforming_scenario():
    """The scenario with the system of interest declared and taken as subject by every need and requirement."""
    scenario = _scenario()
    _, system = _declare_system_of_interest(scenario)
    _replace_subjects(scenario, narrowing=system)
    return scenario


# -- resolution ------------------------------------------------------------


def test_the_scope_resolves_the_declared_system_of_interest_and_its_types() -> None:
    scenario = _scenario()
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert scope.system_of_interest == () and scope.system_of_interest_types == ()
    system_def, system = _declare_system_of_interest(scenario)
    scope = resolve_increment(_view(scenario), scenario.increment_id)
    assert scope.system_of_interest == (system["@id"],)
    assert scope.system_of_interest_types == (system_def["@id"],)


def test_the_contract_names_the_scope_as_the_packages_the_charter_names() -> None:
    contract = _evaluate(_conforming_scenario()).phase_contract()
    scopes = {gate["obligation_id"]: gate["scope"] for gate in contract["gates"]}
    assert scopes[COVERAGE] == "increment package"
    assert scopes[STATEMENT] == "packages named in the charter's expectedArtifacts"


# -- pass ------------------------------------------------------------------


def test_a_conforming_increment_passes_every_new_check() -> None:
    scenario = _conforming_scenario()
    evaluation = _evaluate(scenario)
    for check in (COVERAGE, STATEMENT, NEED_SUBJECT, REQUIREMENT_SUBJECT):
        unit = _unit(evaluation, check)
        assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_PASS), (check, unit.diagnostics)
    assert evaluation.gaps()["blocking"] == [] and evaluation.gaps()["advisory"] == []
    (charter_result,) = _children(evaluation, COVERAGE).values()
    assert set(charter_result.targets) == {
        scenario.framing["@id"], scenario.needs_package["@id"], scenario.evidence_package["@id"]}


def test_a_subject_typed_by_the_system_of_interest_type_or_a_specialization_matches() -> None:
    for specialize in (False, True):
        scenario = _scenario()
        system_def, _ = _declare_system_of_interest(scenario)
        subject_type = system_def
        if specialize:
            subject_type = scenario.builder.definition("PartDefinition", "FixtureSystemRealization",
                                                       scenario.framing, [system_def])
        _replace_subjects(scenario, typed_by=subject_type)
        evaluation = _evaluate(scenario)
        assert _unit(evaluation, NEED_SUBJECT).verdict == me.VERDICT_PASS, specialize
        assert _unit(evaluation, REQUIREMENT_SUBJECT).verdict == me.VERDICT_PASS, specialize


def test_the_charter_may_declare_the_system_of_interest_by_type() -> None:
    scenario = _scenario()
    system_def, _ = _declare_system_of_interest(scenario, by_type=True)
    _replace_subjects(scenario, typed_by=system_def)
    assert _unit(_evaluate(scenario), REQUIREMENT_SUBJECT).verdict == me.VERDICT_PASS


# -- the subject is the increment ------------------------------------------


def test_a_subject_typed_by_the_increment_is_reported_whatever_the_charter_declares() -> None:
    scenario = _scenario()  # the fixture's needs and requirements take the increment as subject
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, NEED_SUBJECT).verdict == me.VERDICT_FAIL
    assert _unit(evaluation, REQUIREMENT_SUBJECT).verdict == me.VERDICT_FAIL
    assert evaluation.gaps()["blocking"] == []
    assert evaluation.next_obligation()["next"] is None  # advisory: never blocks
    note = _note(evaluation, NEED_SUBJECT)
    assert note["kind"] == "violation"
    assert sorted(subject["name"] for subject in note["subjects"]) == ["need0", "need1"]
    assert "takes the increment as its subject" in note["subjects"][0]["diagnostics"][0]
    assert "ref part :>> systemOfInterest" in _note(evaluation, REQUIREMENT_SUBJECT)["what_to_author"]
    # Declaring the system of interest does not excuse an increment-typed subject.
    _declare_system_of_interest(scenario)
    assert _unit(_evaluate(scenario), REQUIREMENT_SUBJECT).verdict == me.VERDICT_FAIL


def test_a_subject_narrowing_the_increment_usage_is_the_increment() -> None:
    scenario = _scenario()
    _declare_system_of_interest(scenario)
    _replace_subjects(scenario, narrowing=scenario.usage)
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, NEED_SUBJECT).verdict == me.VERDICT_FAIL
    assert _unit(evaluation, REQUIREMENT_SUBJECT).verdict == me.VERDICT_FAIL


# -- the subject is something else -----------------------------------------


def test_a_subject_that_is_neither_the_increment_nor_the_system_of_interest_is_reported() -> None:
    scenario = _scenario()
    _declare_system_of_interest(scenario)
    other = scenario.builder.definition("PartDefinition", "OtherSystem", scenario.framing)
    _replace_subjects(scenario, typed_by=other)
    child = _children(_evaluate(scenario), REQUIREMENT_SUBJECT)[scenario.requirements[0]["@id"]]
    assert child.verdict == me.VERDICT_FAIL
    assert "is not the declared system of interest" in child.diagnostics[0]
    assert "fixtureSystem" in child.diagnostics[0]


def test_without_a_declared_system_of_interest_a_non_increment_subject_is_an_open_input() -> None:
    scenario = _scenario()
    other = scenario.builder.definition("PartDefinition", "VehicleUpdateClient", scenario.framing)
    _replace_subjects(scenario, typed_by=other)
    evaluation = _evaluate(scenario)
    unit = _unit(evaluation, REQUIREMENT_SUBJECT)
    assert (unit.state, unit.verdict) == (me.STATE_INDETERMINATE, None)
    note = _note(evaluation, REQUIREMENT_SUBJECT)
    assert note["kind"] == "input-problem"
    assert "declares no systemOfInterest" in note["subjects"][0]["diagnostics"][0]
    assert "ref part :>> systemOfInterest" in note["what_to_author"]
    assert evaluation.gaps()["blocking"] == [] and evaluation.next_obligation()["next"] is None


def test_a_need_without_a_subject_is_reported() -> None:
    scenario = _scenario()
    _declare_system_of_interest(scenario)
    scenario.builder.remove(scenario.builder.feature_of(scenario.needs[0], "increment"))
    child = _children(_evaluate(scenario), NEED_SUBJECT)[scenario.needs[0]["@id"]]
    assert child.verdict == me.VERDICT_FAIL and "declares no subject" in child.diagnostics[0]


# -- requirementHasStatement -----------------------------------------------


def test_requirement_has_statement_reuses_the_require_constraint_check() -> None:
    scenario = _conforming_scenario()
    b = scenario.builder
    b.remove(*[e for e in b.elements if e.get("@type") == "RequirementConstraintMembership"
               and e.get("owningRelatedElement", {}).get("@id") == scenario.requirements[1]["@id"]])
    evaluation = _evaluate(scenario)
    verdicts = {subject: result.verdict for subject, result in _children(evaluation, STATEMENT).items()}
    assert verdicts == {scenario.requirements[0]["@id"]: me.VERDICT_PASS,
                        scenario.requirements[1]["@id"]: me.VERDICT_FAIL}
    (entry,) = [g for g in evaluation.gaps()["blocking"] if g["gate"] == STATEMENT]
    assert entry["kind"] == "violation" and "require constraint statement" in entry["what_to_author"]
    assert evaluation.next_obligation(phase=P5)["next"]["gate"] == STATEMENT


def test_an_assumption_constraint_is_not_a_requirement_statement() -> None:
    scenario = _conforming_scenario()
    b = scenario.builder
    (membership,) = [e for e in b.elements if e.get("@type") == "RequirementConstraintMembership"
                     and e.get("owningRelatedElement", {}).get("@id") == scenario.requirements[0]["@id"]]
    membership["kind"] = "assumption"
    child = _children(_evaluate(scenario), STATEMENT)[scenario.requirements[0]["@id"]]
    assert child.verdict == me.VERDICT_FAIL


# -- charterExpectedArtifactsCoverContent -----------------------------------


def test_a_requirement_deriving_from_an_increment_need_in_an_unnamed_package_is_reported() -> None:
    scenario = _conforming_scenario()
    b = scenario.builder
    extra = b.package("DE4SDV_FixtureExtraRequirements")
    requirement_def = next(e for e in b.elements if e.get("declaredName") == "FixtureRequirement")
    stray = b.usage("RequirementUsage", "strayRequirement", extra, [requirement_def])
    b.connection("strayDerivedFromNeed0", extra, scenario.vocabulary["DerivesFromNeed"],
                 [("need", scenario.needs[0]), ("derivedRequirement", stray)])
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, COVERAGE).verdict == me.VERDICT_FAIL
    gaps = evaluation.gaps()
    assert gaps["blocking"] == []
    (note,) = gaps["advisory"]
    assert (note["gate"], note["kind"]) == (COVERAGE, "violation")
    (subject,) = note["subjects"]
    assert subject["name"] == "fixtureCharter"
    diagnostics = " ".join(subject["diagnostics"])
    assert "DE4SDV_FixtureExtraRequirements" in diagnostics and "strayRequirement" in diagnostics
    assert "never evaluate" in diagnostics
    assert "expectedArtifacts" in note["what_to_author"]
    # Unnamed means unevaluated: the stray requirement is no subject of the requirements step.
    assert stray["@id"] not in _children(evaluation, STATEMENT)


def test_a_verification_case_verifying_an_increment_requirement_in_an_unnamed_package_is_reported() -> None:
    scenario = _conforming_scenario()
    b = scenario.builder
    extra = b.package("DE4SDV_FixtureOtherEvidence")
    case_def = next(e for e in b.elements if e.get("declaredName") == "FixtureVerification")
    b.usage("VerificationCaseUsage", "strayVerification", extra, [case_def])  # inherits the verifying objective
    (charter_result,) = _children(_evaluate(scenario), COVERAGE).values()
    assert charter_result.verdict == me.VERDICT_FAIL
    assert "strayVerification (verifies" in " ".join(charter_result.diagnostics)


def test_a_requirement_verified_by_an_in_scope_case_in_an_unnamed_package_is_reported() -> None:
    """The named evidence package's case verifies requirements that live in a package the charter dropped."""
    scenario = _conforming_scenario()
    b = scenario.builder
    b.remove(b.feature_of(scenario.charter, "expectedArtifacts"))
    b.attribute(scenario.charter, "expectedArtifacts", ["DE4SDV_FixtureFraming", "DE4SDV_FixtureVerificationEvidence"])
    evaluation = _evaluate(scenario)
    assert _unit(evaluation, COVERAGE).verdict == me.VERDICT_FAIL
    (charter_result,) = _children(evaluation, COVERAGE).values()
    diagnostics = " ".join(charter_result.diagnostics)
    assert "DE4SDV_FixtureNeedsRequirements" in diagnostics
    # The verifying objective is owned by the case definition, so either it or its usage is named.
    assert "DE4SDV_FixtureNeedsRequirements::requirement0 (verified by DE4SDV_FixtureVerificationEvidence::" in diagnostics
    assert _note(evaluation, COVERAGE)["kind"] == "violation"


def test_a_package_that_only_references_the_increment_usage_is_reported() -> None:
    scenario = _conforming_scenario()
    b = scenario.builder
    extra = b.package("DE4SDV_FixtureNotes")
    b.references(extra, scenario.usage)
    (charter_result,) = _children(_evaluate(scenario), COVERAGE).values()
    assert charter_result.verdict == me.VERDICT_FAIL
    diagnostics = " ".join(charter_result.diagnostics)
    assert "DE4SDV_FixtureNotes" in diagnostics and "references the increment" in diagnostics


def test_the_increments_own_package_must_be_named() -> None:
    scenario = _conforming_scenario()
    b = scenario.builder
    b.remove(b.feature_of(scenario.charter, "expectedArtifacts"))
    b.attribute(scenario.charter, "expectedArtifacts",
                ["DE4SDV_FixtureNeedsRequirements", "DE4SDV_FixtureVerificationEvidence"])
    (charter_result,) = _children(_evaluate(scenario), COVERAGE).values()
    assert charter_result.verdict == me.VERDICT_FAIL
    diagnostics = " ".join(charter_result.diagnostics)
    assert "DE4SDV_FixtureFraming" in diagnostics and "declares the increment" in diagnostics


def test_an_unresolved_scope_is_an_open_input_not_a_coverage_violation() -> None:
    scenario = _conforming_scenario()
    b = scenario.builder
    b.remove(b.feature_of(scenario.charter, "expectedArtifacts"))
    b.attribute(scenario.charter, "expectedArtifacts", ["DE4SDV_FixtureFraming", "DE4SDV_FixtureMissing"])
    evaluation = _evaluate(scenario)
    unit = _unit(evaluation, COVERAGE)
    assert (unit.state, unit.verdict) == (me.STATE_INDETERMINATE, None)
    assert _note(evaluation, COVERAGE)["kind"] == "input-problem"
