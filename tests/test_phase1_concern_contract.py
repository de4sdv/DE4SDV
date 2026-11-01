"""The owner-approved Phase-1 boundary: framing alone is not concern analysis.

The Phase-1 checks come from the live workflow; the surrounding steps and
model content are small synthetic exports, not copies of production models.
These tests establish native structure and canonical identity, not adequacy.
"""
from __future__ import annotations

import pytest

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from increment_model_fixtures import (
    INFINITY, WorkflowCheck, WorkflowParameter, WorkflowStep,
    increment_scenario, increment_workflow, ref,
)
from test_method_answer_coverage import _workflow_steps
from test_revision_index import _traversal

P0 = "phase0_incrementFraming"
P1 = "phase1_concernFraming"
P2 = "phase2_operationalContext"
GATE = "incrementHasNonBoundaryConcern"
CHECK = "nonBoundaryConcernPresent"
BOUNDARY = "IncrementBoundaryConcern"
REVISION = me.RevisionIdentity("b" * 40, "project", "commit", "full-model")


def test_live_phase1_contract_requires_a_non_boundary_concern():
    step = next(step for step in _workflow_steps() if step.phase == P1)
    assert [(check.name, check.check, check.advisory) for check in step.checks] == [
        (GATE, CHECK, False),
        ("concernHasStakeholder", "stakeholderMember", False),
        ("concernFramedByViewpoint", "framedByViewpoint", False),
    ]
    claim = step.checks[0].claim
    assert "specialization" in claim and "coverage" in claim


def _scenario(depth=0):
    scenario = increment_scenario(applicable_phases=(P0, P1, P2))
    builder = scenario.builder
    boundary = builder.kernel_definition(BOUNDARY)
    typed = boundary
    for level in range(depth):
        typed = builder.definition("ConcernDefinition", f"LocalBoundary{level}", scenario.framing, [typed])
    _replace_type(builder, scenario.concern, typed)
    builder.remove(builder.feature_of(scenario.charter, "expectedArtifacts"))
    builder.attribute(scenario.charter, "expectedArtifacts", [scenario.framing["declaredName"]])
    phase1 = next(step for step in _workflow_steps() if step.phase == P1)
    keywords = {"part": "PartUsage", "requirement": "RequirementUsage", "concern": "ConcernUsage"}
    types = {"ProblemStatement": scenario.vocabulary["ProblemStatement"],
             "Stakeholder": scenario.vocabulary["Stakeholder"]}
    parameters = tuple(WorkflowParameter(
        p.name, types[p.type] if p.type else None, keywords[p.keyword], p.direction,
        (p.multiplicity[0], INFINITY if p.multiplicity[1] == "*" else p.multiplicity[1]),
    ) for p in phase1.parameters)
    increment_workflow(builder, [
        WorkflowStep("frameIncrement", P0, (WorkflowParameter("increment", "EngineeringIncrement"),),
                     (WorkflowCheck("framingWitnessPresent", "populationMember", "increment"),)),
        WorkflowStep(phase1.usage, P1, parameters, tuple(
            WorkflowCheck(c.name, c.check, c.about, advisory=c.advisory, doc=c.claim) for c in phase1.checks)),
        WorkflowStep("specifyContext", P2, (WorkflowParameter("context", kind="UseCaseUsage"),),
                     (WorkflowCheck("contextPresent", "populationMember", "context"),)),
    ], charter=scenario.charter)
    return scenario


def _replace_type(builder, usage, definition):
    builder.remove(*[element for element in builder.elements if element.get("@type") == "FeatureTyping"
                     and element.get("owningRelatedElement", {}).get("@id") == usage["@id"]])
    builder.typed(usage, definition)


def _evaluate(scenario):
    builder = scenario.builder
    return evaluate_increment(ModelView(builder.elements, _traversal(builder), sources=builder.sources),
                              scenario.increment_id, revision=REVISION)


def _phase(evaluation, phase=P1):
    return next(block for block in evaluation.status()["phases"] if block["phase"] == phase)


def _add_concern(scenario, *, owner=None, name="operatingConcern", definition=None, frame=True, stakeholder=True):
    builder = scenario.builder
    owner = scenario.framing if owner is None else owner
    definition = definition or builder.definition("ConcernDefinition", "OperatingConcern", owner)
    concern = builder.usage("ConcernUsage", name, owner, [definition])
    if stakeholder:
        role = next(element for element in builder.elements if element.get("declaredName") == "FixtureEngineer")
        builder.stakeholder(concern, "engineer", role)
    if frame:
        viewpoint = next(element for element in builder.elements if element.get("declaredName") == "selectedViewpoint")
        builder.frame(viewpoint, concern)
    return concern


@pytest.mark.parametrize("depth", [0, 1, 2])
def test_boundary_concern_and_its_specializations_cannot_open_phase1(depth):
    evaluation = _evaluate(_scenario(depth))
    block = _phase(evaluation)
    assert _phase(evaluation, P0)["phase_exit"] == "READY"
    assert block["gates"]["concernHasStakeholder"] == "PASS"
    assert block["gates"]["concernFramedByViewpoint"] == "PASS"
    assert block["gates"][GATE] == "FAIL" and block["phase_exit"] == "BLOCKED"
    step = evaluation.next_obligation()["next"]
    assert (step["stage"], step["gate"]) == (P1, GATE)
    assert "concern" in step["what_to_author"].lower() and "specializ" in step["what_to_author"].lower()


def test_boundary_plus_native_non_boundary_concern_opens_only_structural_phase1():
    scenario = _scenario()
    _add_concern(scenario)
    evaluation = _evaluate(scenario)
    block = _phase(evaluation)
    assert block["phase_exit"] == "READY" and set(block["gates"].values()) == {"PASS"}
    assert evaluation.next_obligation()["next"]["stage"] == P2
    assert "no" in evaluation.status()["claim_boundary"] and "adequacy" in evaluation.status()["claim_boundary"]


@pytest.mark.parametrize("missing", ["stakeholder", "frame"])
def test_non_boundary_presence_does_not_bypass_existing_native_checks(missing):
    scenario = _scenario()
    _add_concern(scenario, stakeholder=missing != "stakeholder", frame=missing != "frame")
    block = _phase(_evaluate(scenario))
    assert block["gates"][GATE] == "PASS"
    other = "concernHasStakeholder" if missing == "stakeholder" else "concernFramedByViewpoint"
    assert block["gates"][other] == "FAIL" and block["phase_exit"] == "BLOCKED"


def test_more_boundary_records_are_not_a_substitute_for_another_concern():
    scenario = _scenario()
    for index in range(3):
        _add_concern(scenario, name=f"boundary{index}", definition=scenario.builder.kernel[BOUNDARY])
    assert _phase(_evaluate(scenario))["gates"][GATE] == "FAIL"


@pytest.mark.parametrize("placement", ["outside_scope", "inside_view", "nested_package"])
def test_non_boundary_concerns_count_only_in_the_declared_package_population(placement):
    scenario = _scenario()
    builder = scenario.builder
    if placement == "outside_scope":
        owner = builder.package("UnrelatedScope")
    elif placement == "inside_view":
        owner = next(e for e in builder.elements if e.get("@type") == "ViewUsage")
    else:
        owner = builder.package("NestedAnalysis", scenario.framing)
    _add_concern(scenario, owner=owner)
    assert _phase(_evaluate(scenario))["gates"][GATE] == ("PASS" if placement == "nested_package" else "FAIL")


def test_same_named_unrelated_type_is_not_the_canonical_boundary_type():
    scenario = _scenario()
    foreign = scenario.builder.package("UnrelatedVocabulary")
    homonym = scenario.builder.definition("ConcernDefinition", BOUNDARY, foreign)
    _add_concern(scenario, definition=homonym, name="boundaryByNameOnly")
    assert _phase(_evaluate(scenario))["gates"][GATE] == "PASS"


@pytest.mark.parametrize("corruption", ["missing_binding", "missing_root_with_surviving_homonym"])
def test_missing_canonical_identity_is_method_side_not_non_boundary_evidence(corruption):
    scenario = _scenario()
    builder = scenario.builder
    foreign = builder.package("UnrelatedVocabulary")
    homonym = builder.definition("ConcernDefinition", BOUNDARY, foreign)
    _add_concern(scenario, definition=homonym)
    if corruption == "missing_binding":
        builder.bindings[:] = [b for b in builder.bindings if b["ontology_class"] != BOUNDARY]
    else:
        builder.remove(builder.kernel[BOUNDARY])
    evaluation = _evaluate(scenario)
    assert _phase(evaluation)["phase_exit"] == "BLOCKED"
    entry = next(entry for entry in evaluation.gaps()["blocking"] if entry["gate"] == GATE)
    assert entry["kind"] == "method-side", entry
    assert any(BOUNDARY in marker for marker in entry.get("missing", [])
               + [marker for subject in entry["subjects"] for marker in subject.get("missing", [])])


@pytest.mark.parametrize("known_non_boundary", [False, True])
def test_incomplete_candidate_lineage_is_not_evidence_of_non_boundary_membership(known_non_boundary):
    scenario = _scenario()
    builder = scenario.builder
    missing = builder.definition("ConcernDefinition", "UnavailableGeneral", scenario.framing)
    uncertain = builder.definition("ConcernDefinition", "UnreadableConcernType", scenario.framing, [missing])
    _add_concern(scenario, definition=uncertain, name="uncertainConcern")
    builder.remove(missing)
    if known_non_boundary:
        _add_concern(scenario)
    evaluation = _evaluate(scenario)
    block = _phase(evaluation)
    if known_non_boundary:
        assert block["gates"][GATE] == "PASS"
    else:
        assert block["phase_exit"] == "BLOCKED"
        assert block["gates"][GATE] != "PASS"
        entry = next(entry for entry in evaluation.gaps()["blocking"] if entry["gate"] == GATE)
        assert entry["kind"] == "input-problem", entry
        assert entry["what_to_author"], entry
        step = evaluation.next_obligation()["next"]
        assert (step["stage"], step["gate"]) == (P1, GATE), step


_NARROWING = [("Subsetting", "subsettedFeature"), ("Redefinition", "redefinedFeature"),
              ("ReferenceSubsetting", "referencedFeature")]


def _narrow(builder, concern, target, kind, field, own_type=False):
    if not own_type:
        builder.remove(*[e for e in builder.elements if e.get("@type") == "FeatureTyping"
                         and e.get("owningRelatedElement", {}).get("@id") == concern["@id"]])
    builder.relationship(kind, concern, general=ref(target), specific=ref(concern), **{field: ref(target)})


@pytest.mark.parametrize("kind,field", _NARROWING)
@pytest.mark.parametrize("own_type", [False, True])
def test_narrowing_a_boundary_concern_cannot_erase_its_inherited_type(kind, field, own_type):
    scenario = _scenario(depth=1)
    concern = _add_concern(scenario)
    _narrow(scenario.builder, concern, scenario.concern, kind, field, own_type)
    assert _phase(_evaluate(scenario))["gates"][GATE] == "FAIL"


@pytest.mark.parametrize("kind,field", _NARROWING)
def test_a_known_non_boundary_type_inherited_from_a_narrowed_feature_counts(kind, field):
    scenario = _scenario()
    builder = scenario.builder
    foreign = builder.package("ReusableConcerns")
    base = _add_concern(scenario, owner=foreign)
    concern = _add_concern(scenario, name="localAnalysisConcern")
    _narrow(builder, concern, base, kind, field)
    assert _phase(_evaluate(scenario))["gates"][GATE] == "PASS"


@pytest.mark.parametrize("known_non_boundary", [False, True])
def test_an_unavailable_narrowed_feature_is_not_non_boundary_evidence(known_non_boundary):
    scenario = _scenario()
    builder = scenario.builder
    missing = _add_concern(scenario, owner=builder.package("ReusableConcerns"))
    concern = _add_concern(scenario, name="unreadableNarrowedConcern")
    _narrow(builder, concern, missing, "Subsetting", "subsettedFeature")
    builder.remove(missing)
    if known_non_boundary:
        _add_concern(scenario, name="knownConcern")
    evaluation = _evaluate(scenario)
    if known_non_boundary:
        assert _phase(evaluation)["gates"][GATE] == "PASS"
    else:
        assert _phase(evaluation)["phase_exit"] == "BLOCKED"
        entry = next(entry for entry in evaluation.gaps()["blocking"] if entry["gate"] == GATE)
        assert entry["kind"] == "input-problem", entry
        assert entry["what_to_author"], entry
        step = evaluation.next_obligation()["next"]
        assert (step["stage"], step["gate"]) == (P1, GATE), step


def test_unreadable_direct_typing_keeps_phase1_actionable():
    scenario = _scenario()
    builder = scenario.builder
    missing = builder.definition("ConcernDefinition", "MissingConcernType", scenario.framing)
    concern = _add_concern(scenario, definition=missing, name="unreadableTypedConcern")
    builder.remove(missing)  # removing the definition also removes its typing
    dangling = "00000000-0000-4000-8000-000000000001"
    builder.relationship("FeatureTyping", concern, type=ref(dangling), general=ref(dangling),
                         specific=ref(concern), typedFeature=ref(concern))
    evaluation = _evaluate(scenario)
    entry = next(entry for entry in evaluation.gaps()["blocking"] if entry["gate"] == GATE)
    assert entry["kind"] == "input-problem", entry
    assert entry["what_to_author"], entry
    step = evaluation.next_obligation()["next"]
    assert (step["stage"], step["gate"]) == (P1, GATE), step


def test_an_untyped_concern_counts_as_non_boundary():
    """The owner-approved pin: an untyped concern has an empty lineage and counts."""
    scenario = _scenario()
    builder = scenario.builder
    role = next(element for element in builder.elements if element.get("declaredName") == "FixtureEngineer")
    concern = builder.usage("ConcernUsage", "placeholder", scenario.framing, [])
    builder.stakeholder(concern, "engineer", role)
    viewpoint = next(element for element in builder.elements if element.get("declaredName") == "selectedViewpoint")
    builder.frame(viewpoint, concern)
    block = _phase(_evaluate(scenario))
    assert block["phase_exit"] == "READY"
    assert set(block["gates"].values()) == {"PASS"}


def test_the_new_gate_keeps_the_notes_of_its_authoring_lines():
    from de4sdv.semantic.remedies import check_remedy

    scenario = _scenario()
    view = ModelView(scenario.builder.elements, _traversal(scenario.builder), sources=scenario.builder.sources)
    base = check_remedy(view, "framedByViewpoint")
    extended = check_remedy(view, "nonBoundaryConcernPresent")
    assert set(base.notes) <= set(extended.notes), (base.notes, extended.notes)
    assert any("coverage adequacy" in note for note in extended.notes)

