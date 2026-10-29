"""The executable checks of phases 9 and 12, and the phase-0 count that a baseline decision leaves alone.

Phase 9 (``DefineVariabilityAndConfiguration``): the increment declares at least one configured product
(``configuredProducts[1..*] : ProductLineConfiguredProduct``), and exactly one feature configuration
configures each, by the derivation rule of ``configuredBy``. A configuration configures a configured
product when one of its effective part usages, its own or inherited and not redefined, is typed by the
part definition of that configuration's product-model projection. The derivation of the configurations
and of their generated part definitions, by validated identity, is the member-product derivation's
(``applies_to_member_product.configuration_projections``), tested on serializer graphs in
``test_applies_to_member_product``. Here it is given to the view, so these tests judge how the check reads
the configured product: its own and inherited usages, a redefinition, a specialization that adds System 2
instrumentation, and none or two configurations.

Phase 12 (``DecideBaselineAndNextSlice``): exactly one baseline decision, typed by
``IncrementBaselineDecision``, states its disposition, and each open gap states the disposition that the
baseline decision gives it. A disposition is a literal of the kernel's ``LifecycleDisposition``.

Phase 0: a baseline decision specializes the lifecycle decision but is never the framing decision, so the
framing count excludes its lineage by typing, wherever it is declared (owner decision of 2026-10-29).
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Any

import pytest

from de4sdv.semantic import increment_workflow as workflow_reader, method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView
from de4sdv.semantic.method_checks import NAMED_CHECKS, effective_part_usages
from de4sdv.sysml_api.qualified_names import QualifiedNameIndex
from increment_model_fixtures import (
    INFINITY,
    ModelBuilder,
    WorkflowCheck,
    WorkflowParameter,
    WorkflowStep,
    increment_scenario,
    increment_workflow,
)
from test_remedies import _problems
from test_revision_index import _traversal

REVISION = me.RevisionIdentity("a" * 40, "project", "commit", "full-model")
P0, P9, P12 = "phase0_incrementFraming", "phase9_variabilityConfiguration", "phase12_baselineNextSlice"
P = WorkflowParameter
C = WorkflowCheck
FRAMING_DECISION = "incrementHasLifecycleDecision"
HAS_PRODUCT, CONFIGURED_BY = "incrementHasConfiguredProduct", "configuredProductConfiguredByOneConfiguration"
HAS_BASELINE, BASELINE_DISPOSITION = "incrementHasBaselineDecision", "baselineDecisionStatesDisposition"
GAP_DISPOSITION = "openGapStatesDisposition"
GATES = (HAS_PRODUCT, CONFIGURED_BY, HAS_BASELINE, BASELINE_DISPOSITION, GAP_DISPOSITION)
PRODUCT_PACKAGE, BASELINE_PACKAGE = "DE4SDV_FixtureVariabilityConfiguration", "DE4SDV_FixtureBaseline"
MEMO = ("configuration-part-definitions",)
DISPOSITIONS = ("accepted", "deferred", "invalidated")


@dataclass
class Increment:
    scenario: Any
    builder: ModelBuilder
    product_package: dict[str, Any]
    baseline_package: dict[str, Any]
    product_def: dict[str, Any]
    product: dict[str, Any]
    platform_stack: dict[str, Any]
    projection: dict[str, Any]
    configuration: dict[str, Any]
    baseline: dict[str, Any]
    gap: dict[str, Any]
    literals: dict[str, dict[str, Any]]
    roots: dict[str, dict[str, Any]]

    @property
    def projections(self) -> dict[str, tuple[str, ...]]:
        """Generated part definition -> configurations: what the derivation would give this corpus."""
        return {self.projection["@id"]: (self.configuration["@id"],)}


def _increment(*, phases=(P0, P9, P12)) -> Increment:
    """A conforming increment. ``FixtureConfiguredProduct :> ProductLineConfiguredProduct`` composes the
    generated projection ``FixtureProjection`` of ``fixtureConfiguration`` (its ``platformStack``) and a
    realization part; ``configuredProduct`` is its usage. ``baselineDecision : IncrementBaselineDecision``
    and the gap ``fixtureGap`` state their dispositions. The framing package keeps its framing decision."""
    scenario = increment_scenario(ModelBuilder(label="phase-9-12", kernel_packages=True), applicable_phases=phases)
    b = scenario.builder
    roots = {cls: b.kernel_definition(cls) for cls in (
        "ConfiguredProduct", "IncrementBaselineDecision", "IncrementLifecycleDecision", "Gap")}
    b.specializes(roots["IncrementBaselineDecision"], roots["IncrementLifecycleDecision"])
    literals = b.enumeration("LifecycleDisposition", DISPOSITIONS)
    b.remove(b.feature_of(scenario.charter, "expectedArtifacts"))
    b.attribute(scenario.charter, "expectedArtifacts", [
        "DE4SDV_FixtureFraming", "DE4SDV_FixtureNeedsRequirements", "DE4SDV_FixtureVerificationEvidence",
        PRODUCT_PACKAGE, BASELINE_PACKAGE])
    models = b.package("DE4SDV_FixtureProductModels")
    projection = b.definition("PartDefinition", "FixtureProjection", models)
    configuration = b.usage("PartUsage", "fixtureConfiguration", b.package("DE4SDV_FixtureFeatureConfigurations"))
    package = b.package(PRODUCT_PACKAGE)
    layer = b.definition("PartDefinition", "FixtureIntegrationLayer", package)
    product_def = b.definition("PartDefinition", "FixtureConfiguredProduct", package, [roots["ConfiguredProduct"]])
    platform_stack = b.usage("PartUsage", "platformStack", product_def, [projection], membership="FeatureMembership")
    b.usage("PartUsage", "integrationLayer", product_def, [layer], membership="FeatureMembership")
    product = b.usage("PartUsage", "configuredProduct", package, [product_def])
    baselines = b.package(BASELINE_PACKAGE)
    baseline = b.usage("PartUsage", "baselineDecision", baselines, [roots["IncrementBaselineDecision"]])
    b.attribute(baseline, "disposition", literals["accepted"])
    gap = b.usage("PartUsage", "fixtureGap", baselines, [roots["Gap"]])
    b.attribute(gap, "disposition", literals["deferred"])
    increment_workflow(b, [
        WorkflowStep("frameIncrement", P0, (P("lifecycleDecision", "IncrementLifecycleDecision", "PartUsage"),), (
            C(FRAMING_DECISION, "ownedByIncrementPackage", "lifecycleDecision"),)),
        WorkflowStep("defineVariabilityAndConfiguration", P9, (
            P("configuredProducts", "ConfiguredProduct", "PartUsage", bounds=(1, INFINITY)),), (
            C(HAS_PRODUCT, "populationMember", "configuredProducts"),
            C(CONFIGURED_BY, "configuredByOneConfiguration", "configuredProducts"))),
        WorkflowStep("decideBaselineAndNextSlice", P12, (
            P("baselineDecision", "IncrementBaselineDecision", "PartUsage"),
            P("openGaps", "Gap", "PartUsage", bounds=(0, INFINITY))), (
            C(HAS_BASELINE, "populationMember", "baselineDecision"),
            C(BASELINE_DISPOSITION, "dispositionStated", "baselineDecision"),
            C(GAP_DISPOSITION, "dispositionStated", "openGaps"))),
    ], charter=scenario.charter)
    return Increment(scenario, b, package, baselines, product_def, product, platform_stack, projection,
                     configuration, baseline, gap, literals, roots)


def _view(increment: Increment, *, projections: dict[str, tuple[str, ...]] | None = None,
          problem: str | None = None, export: bool = True) -> ModelView:
    """The evaluated view. An export's view carries the source documents and the external references; the
    configurations of its feature models are given (``projections``, or the increment's own). Over the API
    the view has neither, and nothing is given."""
    b = increment.builder
    if not export:
        return ModelView(b.elements, _traversal(b))
    view = ModelView(b.elements, _traversal(b), sources=b.sources, external_references=())
    given = increment.projections if projections is None else projections
    view.index.memo(MEMO, lambda: (MappingProxyType(given), problem))
    return view


def _evaluate(increment: Increment, **options: Any):
    return evaluate_increment(_view(increment, **options), increment.scenario.increment_id, revision=REVISION)


def _unit(evaluation, gate: str) -> me.EvaluationResult:
    (unit,) = [u for u in evaluation.canonical.units if u.unit_id == gate]
    return unit


def _verdicts(evaluation, gate: str) -> dict[str, str | None]:
    names = evaluation.view.index
    return {names.name_of(r.subject_id): r.verdict for r in evaluation.canonical.results
            if r.unit_id == gate and r.subject_id}


def _diagnostics(evaluation, gate: str) -> list[str]:
    return [d for r in evaluation.canonical.results if r.unit_id == gate for d in r.diagnostics]


def _blocking(evaluation, gate: str) -> dict[str, Any]:
    (entry,) = [e for e in evaluation.gaps()["blocking"] if e["gate"] == gate]
    return entry


def _authorable(entry: dict[str, Any], increment: Increment) -> list[str]:
    return _problems(entry, QualifiedNameIndex(increment.builder.elements), "DE4SDV_FixtureFraming")


def _phase(evaluation, phase: str) -> dict[str, Any]:
    (block,) = [b for b in evaluation.status()["phases"] if b["phase"] == phase]
    return block


def _population_failure(unit: me.EvaluationResult) -> bool:
    return unit.verdict == me.VERDICT_FAIL and me.POPULATION_POLICY_VIOLATION in unit.reason_codes


# -- pass ------------------------------------------------------------------------------


def test_a_conforming_increment_passes_every_check_of_phases_9_and_12() -> None:
    evaluation = _evaluate(_increment())
    for gate in (FRAMING_DECISION, *GATES):
        unit = _unit(evaluation, gate)
        assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_PASS), (gate, unit.diagnostics)
    assert {p: _phase(evaluation, p)["phase_exit"] for p in (P0, P9, P12)} == dict.fromkeys((P0, P9, P12), "READY")
    (result,) = [r for r in evaluation.canonical.results if r.unit_id == CONFIGURED_BY and r.subject_id]
    increment = _increment()
    assert evaluation.view.index.name_of(result.targets[0]) == "fixtureConfiguration"
    assert increment.configuration["declaredName"] == "fixtureConfiguration"


def test_every_check_is_blocking_and_reads_the_population_its_parameter_declares() -> None:
    contract = _evaluate(_increment()).phase_contract()
    gates = {g["obligation_id"]: g for g in contract["gates"]}
    assert all(gates[gate]["required"] for gate in GATES)
    assert {gate: gates[gate]["population"] for gate in GATES} == {
        HAS_PRODUCT: [1, "*"], CONFIGURED_BY: [1, "*"], HAS_BASELINE: [1, 1], BASELINE_DISPOSITION: [1, 1],
        GAP_DISPOSITION: [0, "*"]}


def test_a_phase_the_charter_does_not_declare_is_not_applicable_never_passed() -> None:
    evaluation = _evaluate(_increment(phases=(P0,)))
    for gate in GATES:
        unit = _unit(evaluation, gate)
        assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE), gate


def test_the_new_checks_are_registered_named_checks() -> None:
    for check in ("configuredByOneConfiguration", "dispositionStated"):
        assert check in NAMED_CHECKS


# -- phase 9: the configured product ---------------------------------------------------------


def test_a_specialization_that_adds_instrumentation_is_configured_through_what_it_inherits() -> None:
    """The INC-AEBS-010 shape: a test article specializes the configured member, owns only its System 2
    instrumentation, and inherits the platform stack. It is a configured product of its own increment."""
    increment = _increment()
    b = increment.builder
    b.remove(increment.product)
    article_def = b.definition("PartDefinition", "FixtureTestArticle", increment.product_package)
    b.specializes(article_def, increment.product_def)
    b.usage("PartUsage", "visualizationChain", article_def, membership="FeatureMembership")
    b.usage("PartUsage", "testArticle", increment.product_package, [article_def])
    evaluation = _evaluate(increment)
    assert _verdicts(evaluation, CONFIGURED_BY) == {"testArticle": me.VERDICT_PASS}
    (article,) = [e for e in b.elements if e.get("declaredName") == "testArticle"]
    names = [evaluation.view.index.name_of(u) for u in effective_part_usages(evaluation.view, article["@id"])]
    assert names == ["visualizationChain", "platformStack", "integrationLayer"]


def test_a_product_that_composes_no_projection_is_configured_by_no_configuration() -> None:
    increment = _increment()
    increment.builder.remove(increment.platform_stack)
    evaluation = _evaluate(increment)
    assert _verdicts(evaluation, CONFIGURED_BY) == {"configuredProduct": me.VERDICT_FAIL}
    assert any("configured by no feature configuration" in d for d in _diagnostics(evaluation, CONFIGURED_BY))
    assert _phase(evaluation, P9)["phase_exit"] == "BLOCKED"
    assert _authorable(_blocking(evaluation, CONFIGURED_BY), increment) == []


def test_an_inherited_projection_part_that_a_usage_redefines_no_longer_counts() -> None:
    """``part :>> platformStack : <other>;`` replaces the inherited usage: the redefined one is no effective
    usage, and the redefining one is typed by no projection."""
    increment = _increment()
    b = increment.builder
    b.remove(increment.product)
    article_def = b.definition("PartDefinition", "FixtureTestArticle", increment.product_package)
    b.specializes(article_def, increment.product_def)
    other = b.definition("PartDefinition", "FixtureOtherStack", increment.product_package)
    redefining = b.usage("PartUsage", "platformStack", article_def, [other], membership="FeatureMembership")
    b.relationship("Redefinition", redefining, redefinedFeature={"@id": increment.platform_stack["@id"]},
                   redefiningFeature={"@id": redefining["@id"]})
    b.usage("PartUsage", "testArticle", increment.product_package, [article_def])
    evaluation = _evaluate(increment)
    assert _verdicts(evaluation, CONFIGURED_BY) == {"testArticle": me.VERDICT_FAIL}


def test_two_configurations_configuring_one_product_fail() -> None:
    increment = _increment()
    b = increment.builder
    second = b.definition("PartDefinition", "FixtureSecondProjection", increment.product_package)
    b.usage("PartUsage", "secondStack", increment.product_def, [second], membership="FeatureMembership")
    other = b.usage("PartUsage", "otherConfiguration", increment.product_package)
    projections = {**increment.projections, second["@id"]: (other["@id"],)}
    evaluation = _evaluate(increment, projections=projections)
    assert _verdicts(evaluation, CONFIGURED_BY) == {"configuredProduct": me.VERDICT_FAIL}
    assert any("configured by 2 feature configurations" in d for d in _diagnostics(evaluation, CONFIGURED_BY))
    assert _authorable(_blocking(evaluation, CONFIGURED_BY), increment) == []


def test_a_configuration_may_configure_several_products() -> None:
    increment = _increment()
    increment.builder.usage("PartUsage", "secondProduct", increment.product_package, [increment.product_def])
    evaluation = _evaluate(increment)
    assert _verdicts(evaluation, CONFIGURED_BY) == {"configuredProduct": me.VERDICT_PASS,
                                                    "secondProduct": me.VERDICT_PASS}


def test_an_increment_without_a_configured_product_fails_on_population() -> None:
    increment = _increment()
    increment.builder.remove(increment.product)
    evaluation = _evaluate(increment)
    for gate in (HAS_PRODUCT, CONFIGURED_BY):
        assert _population_failure(_unit(evaluation, gate)), gate
        assert _authorable(_blocking(evaluation, gate), increment) == []
    assert _phase(evaluation, P9)["phase_exit"] == "BLOCKED"


def test_a_part_typed_by_a_homonym_of_the_projection_is_no_configuration() -> None:
    """Identity, never a name: the derivation binds the generated part definition by identity, so a part
    typed by another definition with the projection's name is typed by no projection."""
    increment = _increment()
    b = increment.builder
    b.remove(increment.platform_stack)
    homonym = b.definition("PartDefinition", "FixtureProjection", increment.product_package)
    b.usage("PartUsage", "platformStack", increment.product_def, [homonym], membership="FeatureMembership")
    evaluation = _evaluate(increment)
    assert _verdicts(evaluation, CONFIGURED_BY) == {"configuredProduct": me.VERDICT_FAIL}


def test_over_the_api_the_configurations_cannot_be_derived_and_the_check_is_indeterminate() -> None:
    """The derivation reads the source documents and the external references of an export; the API view
    has neither. The check is INDETERMINATE there, never a pass."""
    evaluation = _evaluate(_increment(), export=False)
    unit = _unit(evaluation, CONFIGURED_BY)
    assert (unit.state, unit.verdict) == (me.STATE_INDETERMINATE, None)
    assert me.INPUT_UNAVAILABLE in unit.reason_codes
    assert _phase(evaluation, P9)["phase_exit"] == "BLOCKED"


def test_a_refused_derivation_leaves_the_check_indeterminate() -> None:
    evaluation = _evaluate(_increment(), problem="the feature configurations cannot be read: a shape")
    unit = _unit(evaluation, CONFIGURED_BY)
    assert (unit.state, unit.verdict) == (me.STATE_INDETERMINATE, None)
    assert any("cannot be read" in d for d in _diagnostics(evaluation, CONFIGURED_BY))


def test_without_the_pleml_library_the_real_derivation_reads_no_configuration_and_never_passes() -> None:
    """The real derivation on a corpus without PLEML: it refuses or finds no configuration, never a pass."""
    increment = _increment()
    b = increment.builder
    view = ModelView(b.elements, _traversal(b), sources=b.sources, external_references=())
    evaluation = evaluate_increment(view, increment.scenario.increment_id, revision=REVISION)
    assert _unit(evaluation, CONFIGURED_BY).verdict != me.VERDICT_PASS


# -- phase 12: the baseline decision and the open gaps ------------------------------------------


def test_an_increment_without_a_baseline_decision_fails_on_population() -> None:
    """INC-MW-011 declares phase 12 and has authored no baseline decision yet."""
    increment = _increment()
    increment.builder.remove(increment.baseline)
    evaluation = _evaluate(increment)
    for gate in (HAS_BASELINE, BASELINE_DISPOSITION):
        assert _population_failure(_unit(evaluation, gate)), gate
        assert _authorable(_blocking(evaluation, gate), increment) == []
    assert _phase(evaluation, P12)["phase_exit"] == "BLOCKED"


def test_two_baseline_decisions_fail_on_population() -> None:
    increment = _increment()
    b = increment.builder
    second = b.usage("PartUsage", "secondBaseline", increment.baseline_package,
                     [increment.roots["IncrementBaselineDecision"]])
    b.attribute(second, "disposition", increment.literals["deferred"])
    assert _population_failure(_unit(_evaluate(increment), HAS_BASELINE))


@pytest.mark.parametrize("value", ["none", "another enumeration"])
def test_a_baseline_decision_without_a_lifecycle_disposition_fails(value: str) -> None:
    increment = _increment()
    b = increment.builder
    b.remove(b.feature_of(increment.baseline, "disposition"))
    if value == "another enumeration":
        other = b.definition("EnumerationDefinition", "FixtureOutcome", increment.baseline_package)
        literal = b.usage("EnumerationUsage", "accepted", other, membership="VariantMembership")
        b.attribute(increment.baseline, "disposition", literal)
    evaluation = _evaluate(increment)
    assert _verdicts(evaluation, BASELINE_DISPOSITION) == {"baselineDecision": me.VERDICT_FAIL}
    assert any("states no disposition" in d for d in _diagnostics(evaluation, BASELINE_DISPOSITION))
    entry = _blocking(evaluation, BASELINE_DISPOSITION)
    assert "attribute :>> disposition = <disposition>;" in entry["what_to_author"]
    assert _authorable(entry, increment) == []


def test_each_literal_of_the_lifecycle_disposition_states_a_disposition() -> None:
    for literal in DISPOSITIONS:
        increment = _increment()
        b = increment.builder
        b.remove(b.feature_of(increment.gap, "disposition"))
        b.attribute(increment.gap, "disposition", increment.literals[literal])
        assert _verdicts(_evaluate(increment), GAP_DISPOSITION) == {"fixtureGap": me.VERDICT_PASS}, literal


def test_an_open_gap_without_its_disposition_fails_and_is_named() -> None:
    """A gap has no disposition before phase 12; the record of a resolved gap leaves the model, so a resolved
    gap whose record stays (INC-MW-011's GAP-MW-032) counts as open and fails the same way."""
    increment = _increment()
    b = increment.builder
    b.remove(b.feature_of(increment.gap, "disposition"))
    resolved = b.usage("PartUsage", "resolvedGap", increment.baseline_package, [increment.roots["Gap"]])
    evaluation = _evaluate(increment)
    assert _verdicts(evaluation, GAP_DISPOSITION) == {"fixtureGap": me.VERDICT_FAIL, "resolvedGap": me.VERDICT_FAIL}
    assert resolved["declaredName"] == "resolvedGap"
    entry = _blocking(evaluation, GAP_DISPOSITION)
    assert len(entry["subjects"]) == 2
    assert _authorable(entry, increment) == []


def test_an_increment_without_gaps_has_no_open_gap_to_dispose_of_not_a_pass() -> None:
    increment = _increment()
    increment.builder.remove(increment.gap)
    unit = _unit(_evaluate(increment), GAP_DISPOSITION)
    assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE)


def test_a_baseline_short_name_or_a_homonym_never_makes_a_baseline_decision() -> None:
    """The typing identifies the baseline decision, never a name: a ``BL-`` short name on a framing decision,
    or a local definition named IncrementBaselineDecision, is no baseline decision."""
    increment = _increment()
    b = increment.builder
    b.remove(increment.baseline)
    homonym = b.definition("PartDefinition", "IncrementBaselineDecision", increment.baseline_package)
    b.usage("PartUsage", "localBaseline", increment.baseline_package, [homonym], short="BL-FIXTURE-001")
    b.usage("PartUsage", "namedBaseline", increment.baseline_package,
            [increment.roots["IncrementLifecycleDecision"]], short="BL-FIXTURE-002")
    assert _population_failure(_unit(_evaluate(increment), HAS_BASELINE))


def test_an_unbound_lifecycle_disposition_is_method_side_never_a_gap() -> None:
    increment = _increment()
    b = increment.builder
    b.bindings[:] = [binding for binding in b.bindings if binding["ontology_class"] != "LifecycleDisposition"]
    evaluation = _evaluate(increment)
    assert _unit(evaluation, BASELINE_DISPOSITION).verdict != me.VERDICT_PASS
    assert BASELINE_DISPOSITION not in {gap["gate"] for gap in evaluation.gaps()["blocking"]
                                        if gap.get("kind") == "violation"}


# -- phase 0: the framing decision count leaves the baseline decision alone -----------------------


def _framing_baseline(increment: Increment) -> dict[str, Any]:
    """A baseline decision in the framing package, next to the framing decision."""
    b = increment.builder
    baseline = b.usage("PartUsage", "framingPackageBaseline", increment.scenario.framing,
                       [increment.roots["IncrementBaselineDecision"]])
    b.attribute(baseline, "disposition", increment.literals["accepted"])
    return baseline


def test_a_framing_decision_and_a_baseline_decision_in_the_framing_package_pass_phase_0() -> None:
    increment = _increment()
    increment.builder.remove(increment.baseline)
    _framing_baseline(increment)
    evaluation = _evaluate(increment)
    assert _unit(evaluation, FRAMING_DECISION).verdict == me.VERDICT_PASS
    assert _unit(evaluation, HAS_BASELINE).verdict == me.VERDICT_PASS  # phase 12 counts it, wherever it is


def test_a_baseline_decision_alone_fails_the_framing_decision_count() -> None:
    increment = _increment()
    b = increment.builder
    (framing,) = [e for e in b.elements if e.get("declaredName") == "fixtureDecision"]
    b.remove(framing)
    _framing_baseline(increment)
    assert _population_failure(_unit(_evaluate(increment), FRAMING_DECISION))


def test_two_framing_decisions_fail_the_framing_decision_count() -> None:
    increment = _increment()
    increment.builder.usage("PartUsage", "secondFramingDecision", increment.scenario.framing,
                            [increment.roots["IncrementLifecycleDecision"]])
    assert _population_failure(_unit(_evaluate(increment), FRAMING_DECISION))


def test_without_the_structural_exclusion_the_baseline_decision_would_break_phase_0(monkeypatch) -> None:
    """The mutant of the exclusion: the framing count then sees two lifecycle decisions."""
    monkeypatch.setattr(workflow_reader, "EXCLUDED_LINEAGES", MappingProxyType({}))
    increment = _increment()
    _framing_baseline(increment)
    assert _population_failure(_unit(_evaluate(increment), FRAMING_DECISION))
