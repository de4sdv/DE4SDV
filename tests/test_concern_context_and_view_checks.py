"""The checks of phases 1, 2, 3 and 11, over a synthetic increment in the export's shapes.

- Phase 1 (``frameConcerns``, about the concerns): each concern has a native
  stakeholder member (``stakeholderMember``), and a viewpoint of a view in a
  package of the increment frames it (``framedByViewpoint``).
- Phase 2 (``specifyOperationalContext``, about the operational context): the
  increment has exactly one SystemContext usage (``populationMember``); it
  redefines its ``systemOfInterest`` with the system of interest the charter
  declares (``contextSystemOfInterest``); each use case of the increment binds
  its subject to that system of interest (``storySubjectBound``) and each actor
  to a part of the context around it (``storyActorsBound``).
- Phase 3 (``classifyCapabilities``, about the product-line characteristics):
  each one is a feature candidate or deferred product-line scope
  (``featureDeltaOnly``); a common-capability record is no feature-model delta.
- Phase 11 (``publishIncrement``, about the views): each view has a viewpoint
  that frames a concern (``viewpointFramesConcern``) and exposes model content,
  itself or through a view it owns (``exposesModelContent``).

The binding shapes are those of the genuine export (INC-MW-011's stories): a
subject or actor parameter owns a FeatureValue whose FeatureReferenceExpression
names the bound usage through a Membership. The scenarios declare a synthetic
workflow with these checks; the frozen genuine cut's workflow is evaluated in
``test_genuine_export_evaluation.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.method_checks import NAMED_CHECKS, use_case_parameters
from de4sdv.sysml_api.qualified_names import QualifiedNameIndex
from increment_model_fixtures import (
    INFINITY,
    ModelBuilder,
    WorkflowCheck,
    WorkflowParameter,
    WORKFLOW_SOURCE,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
    ref,
)
from test_remedies import _problems
from test_revision_index import _traversal

#: The checks read no allocation, so an API revision binding evaluates them (nothing is withheld).
REVISION = me.RevisionIdentity("a" * 40, "project", "commit", "full-model")
P0, P1, P2, P3, P11 = ("phase0_incrementFraming", "phase1_concernFraming", "phase2_operationalContext",
                       "phase3_capabilityClassification", "phase11_publication")
P, C = WorkflowParameter, WorkflowCheck
STAKEHOLDER, FRAMED = "concernHasStakeholder", "concernFramedByViewpoint"
CONTEXT, CONTEXT_SYSTEM, SUBJECT_BOUND, ACTORS_BOUND = (
    "incrementHasOperationalContext", "operationalContextHoldsSystemOfInterest",
    "storyBindsSubjectToSystemOfInterest", "storyBindsActorsToContextParts")
DELTA = "characteristicIsFeatureDelta"
VIEW_FRAMES, VIEW_EXPOSES = "publishedViewFramesConcern", "publishedViewExposesContent"
GATES = (STAKEHOLDER, FRAMED, CONTEXT, CONTEXT_SYSTEM, SUBJECT_BOUND, ACTORS_BOUND, DELTA, VIEW_FRAMES, VIEW_EXPOSES)
CONTEXT_PACKAGE, CLASSIFICATION_PACKAGE = "DE4SDV_FixtureOperationalContext", "DE4SDV_FixtureClassification"


@dataclass
class Story:
    """Handles to a synthetic increment with an operational context, a story, a classification and views."""

    scenario: Any
    context_package: dict[str, Any]
    classification: dict[str, Any]
    system_context: dict[str, Any]
    kernel_system: dict[str, Any]
    system_def: dict[str, Any]
    context: dict[str, Any]
    context_system: dict[str, Any]
    host: dict[str, Any]
    provider: dict[str, Any]
    driver: dict[str, Any]
    use_case: dict[str, Any]
    subject: dict[str, Any]
    actors: dict[str, dict[str, Any]]
    context_view: dict[str, Any]
    context_concern: dict[str, Any]
    feature: dict[str, Any]
    roots: dict[str, dict[str, Any]]

    @property
    def builder(self):
        return self.scenario.builder


def _bind(builder, feature: dict[str, Any], target: dict[str, Any]) -> None:
    """``<feature> = <target>``: a FeatureValue whose FeatureReferenceExpression names the target."""
    builder.own(feature, builder.value_expression(feature, target), kind="FeatureValue")


def _redefines(builder, feature: dict[str, Any], target: dict[str, Any], *, implied: bool = False) -> None:
    """``:>> target``; ``implied`` is the Redefinition the serializer writes for a parameter the language
    rule makes redefine its definition's parameter (``isImplied``)."""
    builder.relationship("Redefinition", feature, general=ref(target), specific=ref(feature),
                         subsettedFeature=ref(target), subsettingFeature=ref(feature),
                         redefinedFeature=ref(target), redefiningFeature=ref(feature),
                         **({"isImplied": True} if implied else {}))


def _parameter(builder, use_case: dict[str, Any], membership: str, kind: str, name: str,
               typed_by: dict[str, Any] | None = None, bound: dict[str, Any] | None = None) -> dict[str, Any]:
    """A use case's subject or actor parameter (direction in), typed and bound as the export has them."""
    parameter = builder.new(kind, name=name, source=builder.sources[use_case["@id"]], direction="in")
    builder.own(use_case, parameter, kind=membership, member_name=name)
    if typed_by is not None:
        builder.typed(parameter, typed_by)
    if bound is not None:
        _bind(builder, parameter, bound)
    return parameter


def _expose(builder, view: dict[str, Any], package: dict[str, Any]) -> None:
    """``expose <package>::*;``: the NamespaceExpose of the export."""
    builder.relationship("NamespaceExpose", view, importedNamespace=ref(package))


def _view_framing(builder, owner: dict[str, Any], name: str, concern: dict[str, Any]) -> dict[str, Any]:
    view = builder.usage("ViewUsage", name, owner)
    viewpoint = builder.usage("ViewpointUsage", "selectedViewpoint", view, membership="FeatureMembership")
    builder.frame(viewpoint, concern)
    return view


def _story(*, phases=(P0, P1, P2, P3, P11), workflow: bool = True) -> Story:
    """A conforming increment: the charter references ``fixtureSystem`` as its system of interest; the
    context package owns ``fixtureContext : SystemContext`` whose ``fixtureSystemPart :>> systemOfInterest``
    is typed by its definition, with ``host.provider`` and ``driver`` around it, and the story
    ``fixtureStory`` binding its subject to that part and its actors to the context parts; a concern of the
    package framed by a viewpoint of the package's view, which exposes the package; the classification
    package's feature candidate; the framing view exposes the framing package."""
    # Kernel definitions in a package per kernel file, as the export owns them: remedies name them qualified.
    scenario = increment_scenario(ModelBuilder(label="phase-checks", kernel_packages=True), applicable_phases=phases)
    b = scenario.builder
    roots = {cls: b.kernel_definition(cls) for cls in (
        "ProductLineCharacteristic", "Feature", "CommonCapability", "DeferredProductLineScope", "Stakeholder")}
    for kind in ("Feature", "CommonCapability", "DeferredProductLineScope"):
        b.specializes(roots[kind], roots["ProductLineCharacteristic"])
    kernel_package = b.package("DE4SDV_FixtureMethodKernel")
    system_context = b.definition("PartDefinition", "SystemContext", kernel_package)
    for name in ("actors", "systemOfInterest"):
        b.usage("PartUsage", name, system_context, membership="FeatureMembership")
    kernel_system = b.feature_of(system_context, "systemOfInterest")

    system_def = b.definition("PartDefinition", "FixtureSystem", scenario.framing)
    system = b.usage("PartUsage", "fixtureSystem", scenario.framing, [system_def])
    b.attribute(scenario.charter, "systemOfInterest", system, kind="PartUsage")
    b.remove(b.feature_of(scenario.charter, "expectedArtifacts"))
    b.attribute(scenario.charter, "expectedArtifacts", [
        "DE4SDV_FixtureFraming", "DE4SDV_FixtureNeedsRequirements", "DE4SDV_FixtureVerificationEvidence",
        CONTEXT_PACKAGE, CLASSIFICATION_PACKAGE])
    (framing_view,) = [e for e in b.elements if e.get("declaredName") == "fixtureFramingView"]
    _expose(b, framing_view, scenario.framing)

    package = b.package(CONTEXT_PACKAGE)
    host_def = b.definition("PartDefinition", "FixtureHost", package)
    provider_def = b.definition("PartDefinition", "FixtureProvider", package)
    driver_def = b.definition("PartDefinition", "FixtureDriver", package)
    context = b.usage("PartUsage", "fixtureContext", package, [system_context])
    context_system = b.usage("PartUsage", "fixtureSystemPart", context, [system_def], membership="FeatureMembership")
    _redefines(b, context_system, kernel_system)
    host = b.usage("PartUsage", "host", context, [host_def], membership="FeatureMembership")
    provider = b.usage("PartUsage", "provider", host, [provider_def], membership="FeatureMembership")
    driver = b.usage("PartUsage", "driver", context, [driver_def], membership="FeatureMembership")
    use_case = b.usage("UseCaseUsage", "fixtureStory", package)
    subject = _parameter(b, use_case, "SubjectMembership", "ReferenceUsage", "subj", system_def, context_system)
    actors = {"provider": _parameter(b, use_case, "ActorMembership", "PartUsage", "provider", provider_def, provider),
              "driver": _parameter(b, use_case, "ActorMembership", "PartUsage", "driver", driver_def, driver)}
    concern_def = b.definition("ConcernDefinition", "FixtureContextConcern", package)
    concern = b.usage("ConcernUsage", "fixtureContextConcern", package, [concern_def])
    b.stakeholder(concern, "engineer", b.definition("PartDefinition", "FixtureReviewer", package,
                                                    [roots["Stakeholder"]]))
    context_view = _view_framing(b, package, "fixtureContextView", concern)
    _expose(b, context_view, package)

    classification = b.package(CLASSIFICATION_PACKAGE)
    feature = b.usage("PartUsage", "fixtureFeature", classification, [roots["Feature"]])
    story = Story(scenario, package, classification, system_context, kernel_system, system_def, context,
                  context_system, host, provider, driver, use_case, subject, actors, context_view, concern, feature,
                  roots)
    if workflow:
        _workflow(story)
    return story


def _workflow(story: Story) -> None:
    increment_workflow(story.builder, [
        WorkflowStep("frameIncrement", P0, (P("increment", "EngineeringIncrement"),)),
        WorkflowStep("frameConcerns", P1, (P("concerns", None, "ConcernUsage", bounds=(1, INFINITY)),), (
            C(STAKEHOLDER, "stakeholderMember", "concerns"), C(FRAMED, "framedByViewpoint", "concerns"))),
        WorkflowStep("specifyOperationalContext", P2, (P("operationalContext", story.system_context, "PartUsage"),), (
            C(CONTEXT, "populationMember", "operationalContext"),
            C(CONTEXT_SYSTEM, "contextSystemOfInterest", "operationalContext"),
            C(SUBJECT_BOUND, "storySubjectBound", "operationalContext"),
            C(ACTORS_BOUND, "storyActorsBound", "operationalContext"))),
        WorkflowStep("classifyCapabilities", P3, (
            P("characteristics", "ProductLineCharacteristic", "PartUsage", bounds=(0, INFINITY)),), (
            C(DELTA, "featureDeltaOnly", "characteristics"),)),
        WorkflowStep("publishIncrement", P11, (P("publishedViews", None, "ViewUsage", bounds=(1, INFINITY)),), (
            C(VIEW_FRAMES, "viewpointFramesConcern", "publishedViews"),
            C(VIEW_EXPOSES, "exposesModelContent", "publishedViews"))),
    ], charter=story.scenario.charter)


def _view(story: Story) -> ModelView:
    builder = story.builder
    return ModelView(builder.elements, _traversal(builder), sources=builder.sources)


def _evaluate(story: Story, revision: me.RevisionIdentity = REVISION):
    return evaluate_increment(_view(story), story.scenario.increment_id, revision=revision)


def _unit(evaluation, gate: str) -> me.EvaluationResult:
    (unit,) = [u for u in evaluation.canonical.units if u.unit_id == gate]
    return unit


def _verdicts(evaluation, gate: str) -> dict[str, str | None]:
    """Subject name -> verdict of one gate."""
    names = evaluation.view.index
    return {names.name_of(r.subject_id): r.verdict for r in evaluation.canonical.results
            if r.unit_id == gate and r.subject_id}


def _diagnostics(evaluation, gate: str) -> list[str]:
    return [d for r in evaluation.canonical.results if r.unit_id == gate for d in r.diagnostics]


def _blocking(evaluation, gate: str) -> dict[str, Any]:
    (entry,) = [e for e in evaluation.gaps()["blocking"] if e["gate"] == gate]
    return entry


def _authorable(entry: dict[str, Any], story: Story) -> list[str]:
    """Why a gap's remedy is not authorable SysML (empty: it is), by the remedy tests' accepted forms."""
    return _problems(entry, QualifiedNameIndex(story.builder.elements), "DE4SDV_FixtureFraming")


def _owner(builder, element: dict[str, Any]) -> str | None:
    by_id = {e["@id"]: e for e in builder.elements}
    membership = by_id.get((element.get("owningRelationship") or {}).get("@id"), {})
    return (membership.get("owningRelatedElement") or {}).get("@id")


def _element(story: Story, name: str) -> dict[str, Any]:
    (found,) = [e for e in story.builder.elements if e.get("declaredName") == name]
    return found


# -- pass --------------------------------------------------------------------


@pytest.mark.parametrize("revision", [REVISION, me.RevisionIdentity("a" * 40, "", "", "export-snapshot")])
def test_a_conforming_increment_passes_every_check_of_phases_1_2_3_and_11(revision) -> None:
    evaluation = _evaluate(_story(), revision)
    for gate in GATES:
        unit = _unit(evaluation, gate)
        assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_PASS), (gate, unit.diagnostics)
    exits = {p["phase"]: p["phase_exit"] for p in evaluation.status()["phases"]}
    assert {phase: exits[phase] for phase in (P1, P2, P3, P11)} == dict.fromkeys((P1, P2, P3, P11), "READY")
    assert evaluation.gaps()["blocking"] == [] and evaluation.gaps()["advisory"] == []


def test_every_check_is_blocking_and_reads_the_population_its_parameter_declares() -> None:
    contract = _evaluate(_story()).phase_contract()
    gates = {g["obligation_id"]: g for g in contract["gates"]}
    assert all(gates[gate]["required"] for gate in GATES)
    assert {gate: gates[gate]["population"] for gate in GATES} == {
        STAKEHOLDER: [1, "*"], FRAMED: [1, "*"], CONTEXT: [1, 1], CONTEXT_SYSTEM: [1, 1], SUBJECT_BOUND: [1, 1],
        ACTORS_BOUND: [1, 1], DELTA: [0, "*"], VIEW_FRAMES: [1, "*"], VIEW_EXPOSES: [1, "*"]}
    # Only the synthetic framing step, which declares no check here, is without one.
    assert contract["phases_without_executable_checks"] == [P0]


def test_a_phase_the_charter_does_not_declare_is_not_applicable_never_passed() -> None:
    evaluation = _evaluate(_story(phases=(P0,)))
    for gate in GATES:
        unit = _unit(evaluation, gate)
        assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE), gate


# -- phase 1: concerns -------------------------------------------------------------


def test_a_concern_without_a_stakeholder_member_fails() -> None:
    story = _story()
    story.builder.remove(story.builder.feature_of(story.context_concern, "engineer"))
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, STAKEHOLDER)["fixtureContextConcern"] == me.VERDICT_FAIL
    assert _verdicts(evaluation, STAKEHOLDER)["fixtureConcern"] == me.VERDICT_PASS
    entry = _blocking(evaluation, STAKEHOLDER)
    assert "has no native stakeholder member" in " ".join(entry["subjects"][0]["diagnostics"])
    assert _authorable(entry, story) == []


def test_a_concern_no_viewpoint_frames_fails_and_a_need_s_frame_does_not_count() -> None:
    """The fixture's needs frame its framing concern too (a FramedConcernMembership owned by a need): only a
    viewpoint's frame counts (rule 3), so removing the viewpoint's frame fails the concern."""
    story = _story()
    b = story.builder
    (framing_view,) = [e for e in b.elements if e.get("declaredName") == "fixtureFramingView"]
    viewpoint = b.feature_of(framing_view, "selectedViewpoint")
    b.remove(b.feature_of(viewpoint, "fixtureConcern"))
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, FRAMED) == {"fixtureConcern": me.VERDICT_FAIL, "fixtureContextConcern": me.VERDICT_PASS}
    diagnostics = _diagnostics(evaluation, FRAMED)
    assert any("frames it but is no viewpoint" in d for d in diagnostics), diagnostics
    assert _authorable(_blocking(evaluation, FRAMED), story) == []


def test_a_viewpoint_outside_the_increment_s_packages_does_not_frame_its_concern() -> None:
    story = _story()
    b = story.builder
    b.remove(story.context_view)
    elsewhere = b.package("DE4SDV_FixtureUnnamedPackage")
    _view_framing(b, elsewhere, "elsewhereView", story.context_concern)
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, FRAMED)["fixtureContextConcern"] == me.VERDICT_FAIL
    assert any("elsewhereView::selectedViewpoint frames it but is no viewpoint of a view of the increment" in d
               for d in _diagnostics(evaluation, FRAMED))


def test_a_view_owned_by_a_part_is_no_view_of_the_increment_in_either_phase() -> None:
    """Review R3: phases 1 and 11 count the same views, those the increment's packages own. A view that a
    part owns frames no concern for phase 1 and is no phase-11 subject."""
    story = _story()
    b = story.builder
    b.remove(story.context_view)
    nested = b.usage("ViewUsage", "hostView", story.host, membership="FeatureMembership")
    viewpoint = b.usage("ViewpointUsage", "selectedViewpoint", nested, membership="FeatureMembership")
    b.frame(viewpoint, story.context_concern)
    _expose(b, nested, story.context_package)
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, FRAMED)["fixtureContextConcern"] == me.VERDICT_FAIL
    assert any("hostView::selectedViewpoint frames it but is no viewpoint of a view of the increment" in d
               for d in _diagnostics(evaluation, FRAMED))
    for gate in (VIEW_FRAMES, VIEW_EXPOSES):
        assert "hostView" not in _verdicts(evaluation, gate), gate


def test_a_viewpoint_inherits_the_frames_of_its_viewpoint_definition_in_both_phases() -> None:
    """Review R4: ``viewpoint vp : VD;`` where ``viewpoint def VD { frame c; }``: the usage frames ``c``."""
    story = _story()
    b = story.builder
    viewpoint = b.feature_of(story.context_view, "selectedViewpoint")
    b.remove(b.feature_of(viewpoint, "fixtureContextConcern"))
    definition = b.definition("ViewpointDefinition", "FixtureContextViewpointDef", story.context_package)
    b.frame(definition, story.context_concern)
    b.typed(viewpoint, definition)
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, FRAMED)["fixtureContextConcern"] == me.VERDICT_PASS
    assert _verdicts(evaluation, VIEW_FRAMES)["fixtureContextView"] == me.VERDICT_PASS


def test_a_viewpoint_definition_s_frame_counts_only_through_a_viewpoint_typed_by_it() -> None:
    """Review R4: the diagnostic names the viewpoint definition as such, never "no viewpoint"."""
    story = _story()
    b = story.builder
    viewpoint = b.feature_of(story.context_view, "selectedViewpoint")
    b.remove(b.feature_of(viewpoint, "fixtureContextConcern"))
    definition = b.definition("ViewpointDefinition", "FixtureContextViewpointDef", story.context_package)
    b.frame(definition, story.context_concern)
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, FRAMED)["fixtureContextConcern"] == me.VERDICT_FAIL
    diagnostics = _diagnostics(evaluation, FRAMED)
    assert any(f"the viewpoint definition {CONTEXT_PACKAGE}::FixtureContextViewpointDef frames it, but no viewpoint "
               "of a view of the increment is typed by it" in d for d in diagnostics), diagnostics
    assert not any("FixtureContextViewpointDef frames it but is no viewpoint" in d for d in diagnostics)


def test_no_concern_in_the_increment_fails_the_population_of_phase_1() -> None:
    story = _story()
    b = story.builder
    b.remove(story.scenario.concern, story.context_concern)
    unit = _unit(_evaluate(story), STAKEHOLDER)
    assert (unit.verdict, me.POPULATION_POLICY_VIOLATION in unit.reason_codes) == (me.VERDICT_FAIL, True)


# -- phase 2: the operational context and the story -------------------------------------


def test_an_increment_without_an_operational_context_fails_every_context_gate_on_population() -> None:
    story = _story()
    story.builder.remove(story.context)
    evaluation = _evaluate(story)
    for gate in (CONTEXT, CONTEXT_SYSTEM, SUBJECT_BOUND, ACTORS_BOUND):
        unit = _unit(evaluation, gate)
        assert unit.verdict == me.VERDICT_FAIL and me.POPULATION_POLICY_VIOLATION in unit.reason_codes, gate
    entry = _blocking(evaluation, CONTEXT)
    assert "keep exactly 1 SystemContext" in entry["what_to_author"]
    assert _authorable(entry, story) == []
    assert _authorable(_blocking(evaluation, CONTEXT_SYSTEM), story) == []


def test_two_operational_contexts_fail_the_population_of_exactly_one() -> None:
    story = _story()
    story.builder.usage("PartUsage", "secondContext", story.context_package, [story.system_context])
    unit = _unit(_evaluate(story), CONTEXT)
    assert unit.verdict == me.VERDICT_FAIL and me.POPULATION_POLICY_VIOLATION in unit.reason_codes


def test_a_context_that_keeps_the_inherited_system_of_interest_fails() -> None:
    story = _story()
    b = story.builder
    (redefinition,) = [r for r in b.elements if r.get("@type") == "Redefinition"
                       and r.get("redefiningFeature", {}).get("@id") == story.context_system["@id"]]
    b.remove(redefinition)
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, CONTEXT_SYSTEM) == {"fixtureContext": me.VERDICT_FAIL}
    assert any("does not redefine its systemOfInterest" in d for d in _diagnostics(evaluation, CONTEXT_SYSTEM))
    assert _verdicts(evaluation, SUBJECT_BOUND) == {"fixtureContext": me.VERDICT_FAIL}
    entry = _blocking(evaluation, CONTEXT_SYSTEM)
    assert ":>> systemOfInterest;" in entry["what_to_author"]
    assert _authorable(entry, story) == []


def test_a_context_whose_system_of_interest_is_another_system_fails() -> None:
    story = _story()
    b = story.builder
    other = b.definition("PartDefinition", "OtherSystem", story.context_package)
    (typing,) = [r for r in b.elements if r.get("@type") == "FeatureTyping"
                 and r.get("typedFeature", {}).get("@id") == story.context_system["@id"]]
    typing["type"] = typing["general"] = ref(other)
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, CONTEXT_SYSTEM) == {"fixtureContext": me.VERDICT_FAIL}
    assert any("is not the system of interest the charter declares" in d
               for d in _diagnostics(evaluation, CONTEXT_SYSTEM))


def test_a_context_system_of_interest_bound_to_the_declared_usage_passes() -> None:
    """``part :>> systemOfInterest = fixtureSystem;``: an untyped redefinition bound to the declared usage."""
    story = _story()
    b = story.builder
    (typing,) = [r for r in b.elements if r.get("@type") == "FeatureTyping"
                 and r.get("typedFeature", {}).get("@id") == story.context_system["@id"]]
    b.remove(typing)
    _bind(b, story.context_system, _element(story, "fixtureSystem"))
    unit = _unit(_evaluate(story), CONTEXT_SYSTEM)
    assert unit.verdict == me.VERDICT_PASS, unit.diagnostics


def test_a_charter_without_a_system_of_interest_leaves_the_context_gate_indeterminate_never_passed() -> None:
    story = _story()
    story.builder.remove(story.builder.feature_of(story.scenario.charter, "systemOfInterest"))
    unit = _unit(_evaluate(story), CONTEXT_SYSTEM)
    assert (unit.state, unit.verdict) == (me.STATE_INDETERMINATE, None)
    assert me.INPUT_UNAVAILABLE in unit.reason_codes


def test_an_unbound_story_subject_fails_and_names_the_use_case() -> None:
    """The shape INC-AEBS-010 had before its phase-2 revision: ``subject instrumentedMember;``, no value."""
    story = _story()
    b = story.builder
    (value,) = [r for r in b.elements if r.get("@type") == "FeatureValue"
                and r.get("owningRelatedElement", {}).get("@id") == story.subject["@id"]]
    b.remove(value)
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, SUBJECT_BOUND) == {"fixtureContext": me.VERDICT_FAIL}
    assert any("fixtureStory binds its subject" in d and "to no usage" in d
               for d in _diagnostics(evaluation, SUBJECT_BOUND))
    entry = _blocking(evaluation, SUBJECT_BOUND)
    assert f"replace the subject of {CONTEXT_PACKAGE}::fixtureStory with: subject <subjectName> = " \
           f"{CONTEXT_PACKAGE}::fixtureContext::fixtureSystemPart;" in entry["what_to_author"]
    assert _authorable(entry, story) == []


def test_a_story_subject_bound_to_another_part_fails() -> None:
    story = _story()
    b = story.builder
    (value,) = [r for r in b.elements if r.get("@type") == "FeatureValue"
                and r.get("owningRelatedElement", {}).get("@id") == story.subject["@id"]]
    b.remove(value)
    _bind(b, story.subject, story.driver)
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, SUBJECT_BOUND) == {"fixtureContext": me.VERDICT_FAIL}
    assert any("not to the system of interest" in d for d in _diagnostics(evaluation, SUBJECT_BOUND))


def test_a_subject_its_definition_binds_counts_for_the_use_case() -> None:
    """A use case has one subject: its own, else its definition's (with that definition's binding)."""
    story = _story()
    b = story.builder
    b.remove(story.subject)
    definition = b.definition("UseCaseDefinition", "FixtureStoryDefinition", story.context_package)
    _parameter(b, definition, "SubjectMembership", "ReferenceUsage", "subj", story.system_def, story.context_system)
    b.typed(story.use_case, definition)
    assert _unit(_evaluate(story), SUBJECT_BOUND).verdict == me.VERDICT_PASS


def test_a_use_case_without_a_subject_fails() -> None:
    story = _story()
    story.builder.remove(story.subject)
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, SUBJECT_BOUND) == {"fixtureContext": me.VERDICT_FAIL}
    assert any("fixtureStory declares no subject" in d for d in _diagnostics(evaluation, SUBJECT_BOUND))


def test_an_increment_without_a_use_case_has_no_story_to_bind_not_a_pass() -> None:
    story = _story()
    story.builder.remove(story.use_case)
    evaluation = _evaluate(story)
    for gate in (SUBJECT_BOUND, ACTORS_BOUND):
        unit = _unit(evaluation, gate)
        assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE), gate
        assert any("own no use case at any depth" in d for d in _diagnostics(evaluation, gate)), gate


def test_a_story_the_context_owns_is_the_story_and_its_unbound_parameters_fail() -> None:
    """Review R2: the story is every use case the packages own at any depth. A use case the context owns,
    with an unbound subject and an unbound actor, fails both story checks; it is never "no use case"."""
    story = _story()
    b = story.builder
    b.remove(story.use_case)
    nested = b.usage("UseCaseUsage", "contextStory", story.context, membership="FeatureMembership")
    _parameter(b, nested, "SubjectMembership", "ReferenceUsage", "subj", story.system_def)
    _parameter(b, nested, "ActorMembership", "PartUsage", "driver")
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, SUBJECT_BOUND) == {"fixtureContext": me.VERDICT_FAIL}
    assert _verdicts(evaluation, ACTORS_BOUND) == {"fixtureContext": me.VERDICT_FAIL}
    assert any("contextStory binds its subject" in d and "to no usage" in d
               for d in _diagnostics(evaluation, SUBJECT_BOUND))
    assert any("contextStory: actor driver is bound to no usage" in d for d in _diagnostics(evaluation, ACTORS_BOUND))
    (phase,) = [p for p in evaluation.status()["phases"] if p["phase"] == P2]
    assert phase["phase_exit"] == "BLOCKED"
    for gate in (SUBJECT_BOUND, ACTORS_BOUND):
        assert _authorable(_blocking(evaluation, gate), story) == []


def test_an_include_use_case_is_no_use_case_of_the_story() -> None:
    """``include use case <other>;`` in the story references another use case: it binds nothing itself."""
    story = _story()
    b = story.builder
    other = b.usage("UseCaseUsage", "otherStory", b.package("DE4SDV_FixtureOtherStories"))
    included = b.usage("IncludeUseCaseUsage", "otherStory", story.use_case, membership="FeatureMembership")
    b.reference_subsetting(included, other)
    evaluation = _evaluate(story)
    for gate in (SUBJECT_BOUND, ACTORS_BOUND):
        assert _unit(evaluation, gate).verdict == me.VERDICT_PASS, gate


@pytest.mark.parametrize("where", ["package part", "the system of interest", "inside the system of interest",
                                   "the kernel's actors slot", "unbound"])
def test_an_actor_not_bound_to_a_part_around_the_system_of_interest_fails(where) -> None:
    """The shape INC-AEBS-010 had before its phase-2 revision binds its actors to package parts: no part of an
    operational context."""
    story = _story()
    b = story.builder
    actor = story.actors["driver"]
    (value,) = [r for r in b.elements if r.get("@type") == "FeatureValue"
                and r.get("owningRelatedElement", {}).get("@id") == actor["@id"]]
    b.remove(value)
    if where == "package part":
        _bind(b, actor, b.usage("PartUsage", "packageDriver", story.context_package))
    elif where == "the system of interest":
        _bind(b, actor, story.context_system)
    elif where == "inside the system of interest":
        _bind(b, actor, b.usage("PartUsage", "inner", story.context_system, membership="FeatureMembership"))
    elif where == "the kernel's actors slot":  # review R1: ``actor driver = fixtureContext::actors;``
        _bind(b, actor, b.feature_of(story.system_context, "actors"))
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, ACTORS_BOUND) == {"fixtureContext": me.VERDICT_FAIL}
    assert any("actor driver" in d for d in _diagnostics(evaluation, ACTORS_BOUND))
    entry = _blocking(evaluation, ACTORS_BOUND)
    assert f"in the existing {CONTEXT_PACKAGE}::fixtureStory: actor driver = <contextPart>;" in entry["what_to_author"]
    assert _authorable(entry, story) == []


def test_an_actor_bound_to_a_part_of_the_context_s_own_definition_passes() -> None:
    """Review R1, the other side: a part the context's own definition declares is a part of the context. Only
    the definition that first declares systemOfInterest (the kernel's SystemContext) owns no context part."""
    story = _story()
    b = story.builder
    definition = b.definition("PartDefinition", "FixtureContextDefinition", story.context_package)
    b.specializes(definition, story.system_context)
    assistant = b.usage("PartUsage", "assistant", definition, membership="FeatureMembership")
    b.typed(story.context, definition)
    actor = story.actors["driver"]
    (value,) = [r for r in b.elements if r.get("@type") == "FeatureValue"
                and r.get("owningRelatedElement", {}).get("@id") == actor["@id"]]
    b.remove(value)
    _bind(b, actor, assistant)
    assert _unit(_evaluate(story), ACTORS_BOUND).verdict == me.VERDICT_PASS


def test_an_inherited_actor_no_own_actor_redefines_is_unbound_and_fails() -> None:
    story = _story()
    b = story.builder
    definition = b.definition("UseCaseDefinition", "FixtureStoryDefinition", story.context_package)
    _parameter(b, definition, "ActorMembership", "PartUsage", "reviewer")
    b.typed(story.use_case, definition)
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, ACTORS_BOUND) == {"fixtureContext": me.VERDICT_FAIL}
    assert any("actor reviewer is bound to no usage" in d for d in _diagnostics(evaluation, ACTORS_BOUND))


@pytest.mark.parametrize("implied", [False, True], ids=["declared", "implied"])
def test_an_own_actor_that_redefines_the_inherited_one_replaces_it(implied: bool) -> None:
    """Declared (``actor :>> driver = ...;``) or by the language rule (``actor driver = ...;`` in a use
    case whose definition declares ``actor driver``): the export writes the second as an implied
    Redefinition, the shape of INC-AEBS-010's story."""
    story = _story()
    b = story.builder
    definition = b.definition("UseCaseDefinition", "FixtureStoryDefinition", story.context_package)
    inherited = _parameter(b, definition, "ActorMembership", "PartUsage", "driver")
    b.typed(story.use_case, definition)
    _redefines(b, story.actors["driver"], inherited, implied=implied)
    evaluation = _evaluate(story)
    assert _unit(evaluation, ACTORS_BOUND).verdict == me.VERDICT_PASS
    assert inherited["@id"] not in use_case_parameters(evaluation.view, story.use_case["@id"], "ActorMembership")


def test_a_story_without_actors_has_none_to_bind_not_a_pass() -> None:
    story = _story()
    story.builder.remove(*story.actors.values())
    unit = _unit(_evaluate(story), ACTORS_BOUND)
    assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE)


# -- phase 3: the feature-model delta -------------------------------------------------


def test_a_common_capability_record_is_no_feature_model_delta() -> None:
    story = _story()
    story.builder.usage("PartUsage", "aebsRemainsCommon", story.classification, [story.roots["CommonCapability"]])
    evaluation = _evaluate(story)
    assert _verdicts(evaluation, DELTA) == {"fixtureFeature": me.VERDICT_PASS, "aebsRemainsCommon": me.VERDICT_FAIL}
    entry = _blocking(evaluation, DELTA)
    assert "core elements are common by default and get no record" in entry["subjects"][0]["diagnostics"][0]
    assert entry["what_to_author"].startswith(f"remove {CLASSIFICATION_PACKAGE}::aebsRemainsCommon")
    assert _authorable(entry, story) == []


def test_deferred_product_line_scope_is_allowed_and_another_characteristic_is_not() -> None:
    story = _story()
    b = story.builder
    b.usage("PartUsage", "deferredVariability", story.classification, [story.roots["DeferredProductLineScope"]])
    choice = b.definition("PartDefinition", "FixtureVariantChoice", story.classification,
                          [story.roots["ProductLineCharacteristic"]])
    b.usage("PartUsage", "variantChoice", story.classification, [choice])
    assert _verdicts(_evaluate(story), DELTA) == {
        "fixtureFeature": me.VERDICT_PASS, "deferredVariability": me.VERDICT_PASS, "variantChoice": me.VERDICT_FAIL}


def test_an_increment_that_adds_no_variability_records_nothing_and_is_not_applicable() -> None:
    story = _story()
    story.builder.remove(story.feature)
    unit = _unit(_evaluate(story), DELTA)
    assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE)


def test_an_unbound_feature_class_is_method_side_never_a_gap() -> None:
    story = _story()
    b = story.builder
    b.bindings[:] = [binding for binding in b.bindings if binding["ontology_class"] != "Feature"]
    evaluation = _evaluate(story)
    unit = _unit(evaluation, DELTA)
    assert unit.state == me.STATE_INDETERMINATE and me.INPUT_UNAVAILABLE in unit.reason_codes
    assert any(gate["gate"] == DELTA for gate in evaluation.next_obligation()["method_side_blockers"])


# -- phase 11: the views -----------------------------------------------------------


def test_a_view_without_a_viewpoint_or_whose_viewpoint_frames_nothing_fails() -> None:
    story = _story()
    b = story.builder
    bare = b.usage("ViewUsage", "bareView", story.context_package)
    _expose(b, bare, story.context_package)
    silent = b.usage("ViewUsage", "silentView", story.context_package)
    b.usage("ViewpointUsage", "selectedViewpoint", silent, membership="FeatureMembership")
    _expose(b, silent, story.context_package)
    evaluation = _evaluate(story)
    verdicts = _verdicts(evaluation, VIEW_FRAMES)
    assert (verdicts["bareView"], verdicts["silentView"], verdicts["fixtureContextView"]) == (
        me.VERDICT_FAIL, me.VERDICT_FAIL, me.VERDICT_PASS)
    diagnostics = _diagnostics(evaluation, VIEW_FRAMES)
    assert any("bareView has no viewpoint" in d for d in diagnostics)
    assert any("frames no concern" in d for d in diagnostics)
    assert _authorable(_blocking(evaluation, VIEW_FRAMES), story) == []


def test_a_view_that_exposes_nothing_fails_and_one_exposing_through_its_owned_views_passes() -> None:
    """A table or matrix view exposes through its row and column views (``view :>> rowView { expose ...;
    }``), as the functional and logical mapping views of both live increments do."""
    story = _story()
    b = story.builder
    empty = _view_framing(b, story.context_package, "emptyView", story.context_concern)
    matrix = _view_framing(b, story.context_package, "matrixView", story.context_concern)
    row = b.usage("ViewUsage", "rowView", matrix, membership="FeatureMembership")
    b.relationship("MembershipExpose", row, importedMembership=ref(story.context["owningRelationship"]["@id"]))
    evaluation = _evaluate(story)
    verdicts = _verdicts(evaluation, VIEW_EXPOSES)
    assert (verdicts["emptyView"], verdicts["matrixView"]) == (me.VERDICT_FAIL, me.VERDICT_PASS)
    (matrix_result,) = [r for r in evaluation.canonical.results if r.unit_id == VIEW_EXPOSES
                        and r.subject_id == matrix["@id"]]
    assert matrix_result.targets == (story.context["@id"],)
    assert empty["@id"] in {r.subject_id for r in evaluation.canonical.results
                            if r.unit_id == VIEW_EXPOSES and r.verdict == me.VERDICT_FAIL}
    assert _authorable(_blocking(evaluation, VIEW_EXPOSES), story) == []


def test_a_declared_publication_without_views_fails_on_population() -> None:
    """Review R3: ``publishedViews[1..*]``. A declared phase 11 with no view of the increment is no empty
    publication that passes: both checks fail on population and the exit is BLOCKED (MC-05)."""
    story = _story()
    b = story.builder
    packages = {story.scenario.framing["@id"], story.context_package["@id"]}
    b.remove(*[e for e in b.elements if e.get("@type") == "ViewUsage"
               and b.sources.get(e["@id"]) != WORKFLOW_SOURCE and _owner(b, e) in packages])
    evaluation = _evaluate(story)
    for gate in (VIEW_FRAMES, VIEW_EXPOSES):
        unit = _unit(evaluation, gate)
        assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_FAIL), gate
        assert me.POPULATION_POLICY_VIOLATION in unit.reason_codes, gate
        assert _authorable(_blocking(evaluation, gate), story) == []
    (phase,) = [p for p in evaluation.status()["phases"] if p["phase"] == P11]
    assert phase["phase_exit"] == "BLOCKED"


# -- the registry ----------------------------------------------------------------------


def test_the_new_checks_are_registered_named_checks_and_read_no_method_field() -> None:
    """Each check is a function of the view, the increment and one subject (no selector, filter or phase)."""
    for check in ("framedByViewpoint", "contextSystemOfInterest", "storySubjectBound", "storyActorsBound",
                  "featureDeltaOnly", "viewpointFramesConcern", "exposesModelContent"):
        function = NAMED_CHECKS[check]
        assert function.__code__.co_varnames[:3] == ("view", "increment", "subject_id"), check
