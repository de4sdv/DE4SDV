"""The architecture trace checks of phases 6 to 8, over a synthetic increment in the export's shapes.

``allocatedTo`` is read from the ends of native allocations, typed or not: an
allocation counts for the one end pair (requirement to function, function to
logical element, logical element to physical element) its two ends ground in
through the validated kernel bindings, and a feature-chain end (``a.b``) reads
as its last chaining feature. ``receivesAllocation`` reads the same
allocations from their target end, and ``carriedByArchitecture`` accepts an
allocation to a function or a ``hasRelevantArchitecture`` dependency. A step
parameter typed by a function, logical or physical element class counts the
charter's packages at any depth and the elements the increment's own
allocations name. The scenarios declare a synthetic workflow with these checks, so
each test controls the parameters it reads; the genuine-shape evaluation of the
same checks is in ``test_genuine_export_evaluation.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.increment_evaluation import evaluate_increment
from de4sdv.semantic.increment_scope import ModelView, resolve_increment, scope_closure
from de4sdv.semantic.method_checks import increment_content_outside_scope
from de4sdv.semantic.relation_checks import chained_feature, check_relation, relation_checks
from de4sdv.semantic.remedies import check_remedy
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
P0, P6, P7, P8 = ("phase0_incrementFraming", "phase6_functionalArchitecture", "phase7_logicalArchitecture",
                  "phase8_physicalRealization")
P, C = WorkflowParameter, WorkflowCheck
G6, G6_ADVISORY, G6B = ("functionalRequirementAllocatedToFunction", "requirementCarriedByArchitecture",
                        "functionCarriesRequirement")
G7, G7B, G8, G8B = ("functionAllocatedToLogicalElement", "logicalElementCarriesFunction",
                    "logicalElementAllocatedToPhysicalElement", "physicalElementCarriesLogicalElement")
VERIFICATION_ONLY = "is carried by no architecture element and is covered by verification only"


@dataclass
class Architecture:
    """Handles to a synthetic increment with a functional, logical and physical slice."""

    scenario: Any
    functional: dict[str, Any]
    constraint: dict[str, Any]
    function_def: dict[str, Any]
    flow: dict[str, Any]
    fn_a: dict[str, Any]
    fn_b: dict[str, Any]
    system: dict[str, Any]
    logical_a: dict[str, Any]
    physical_a: dict[str, Any]
    roots: dict[str, dict[str, Any]]

    @property
    def builder(self):
        return self.scenario.builder


def _architecture(*, workflow: bool = True) -> Architecture:
    """Requirements requirement0/1 (functional) and constraint0 (not functional) in the needs package, with
    a functional flow definition owning fnA and fnB, a logical system definition owning logicalA, a
    physical part physicalA, and the allocations requirement0 -> FixtureFlow::fnA, requirement1 ->
    fixtureFlow.fnB, fixtureFlow.fnA -> fixtureSystem.logicalA, FixtureFlow::fnB -> logicalA and logicalA
    -> physicalA. The charter declares phases 0 and 6 to 8."""
    scenario = increment_scenario(applicable_phases=(P0, P6, P7, P8))
    b = scenario.builder
    roots = {cls: b.kernel_definition(cls) for cls in ("Function", "LogicalElement", "PhysicalElement",
                                                        "MemberProduct", "Requirement")}
    package = scenario.needs_package
    functional = b.definition("RequirementDefinition", "FixtureFunctionalRequirement", package,
                              [roots["Requirement"]])
    (requirement_def,) = [e for e in b.elements if e.get("declaredName") == "FixtureRequirement"]
    b.specializes(requirement_def, functional)
    constraint_def = b.definition("RequirementDefinition", "FixtureConstraint", package, [roots["Requirement"]])
    constraint = b.usage("RequirementUsage", "constraint0", package, [constraint_def])
    function_def = b.definition("ActionDefinition", "FixtureFunction", package, [roots["Function"]])
    flow_def = b.definition("ActionDefinition", "FixtureFlow", package)
    fn_a = b.usage("ActionUsage", "fnA", flow_def, [function_def], membership="FeatureMembership")
    fn_b = b.usage("ActionUsage", "fnB", flow_def, [function_def], membership="FeatureMembership")
    flow = b.usage("ActionUsage", "fixtureFlow", package, [flow_def])
    logical_def = b.definition("PartDefinition", "FixtureLogical", package, [roots["LogicalElement"]])
    system_def = b.definition("PartDefinition", "FixtureSystem", package)
    logical_a = b.usage("PartUsage", "logicalA", system_def, [logical_def], membership="FeatureMembership")
    system = b.usage("PartUsage", "fixtureSystem", package, [system_def])
    physical_def = b.definition("PartDefinition", "FixturePhysical", package, [roots["PhysicalElement"]])
    physical_a = b.usage("PartUsage", "physicalA", package, [physical_def])
    requirement0, requirement1 = scenario.requirements
    b.allocation("requirement0ToFnA", package, requirement0, fn_a)
    b.allocation("requirement1ToFnB", package, requirement1, [flow, fn_b])
    b.allocation("fnAToLogicalA", package, [flow, fn_a], [system, logical_a])
    b.allocation("fnBToLogicalA", package, fn_b, logical_a)
    b.allocation("logicalAToPhysicalA", package, logical_a, physical_a)
    architecture = Architecture(scenario, functional, constraint, function_def, flow, fn_a, fn_b, system,
                                logical_a, physical_a, roots)
    if workflow:
        _workflow(architecture)
    return architecture


def _workflow(architecture: Architecture) -> None:
    increment_workflow(architecture.builder, [
        WorkflowStep("frameIncrement", P0, (P("increment", "EngineeringIncrement"),)),
        WorkflowStep("defineFunctionalArchitecture", P6, (
            P("requirements", "Requirement", "RequirementUsage", "in", (0, INFINITY)),
            P("functionalRequirements", architecture.functional, "RequirementUsage", "in", (0, INFINITY)),
            P("functions", "Function", "ActionUsage", "out", (1, INFINITY))), (
            C(G6, "allocatedTo", "functionalRequirements"),
            C(G6_ADVISORY, "carriedByArchitecture", "requirements", advisory=True),
            C(G6B, "receivesAllocation", "functions", advisory=True))),
        WorkflowStep("defineLogicalArchitecture", P7, (
            P("functions", "Function", "ActionUsage", "in", (1, INFINITY)),
            P("logicalElements", "LogicalElement", "PartUsage", "out", (1, INFINITY))), (
            C(G7, "allocatedTo", "functions"),
            C(G7B, "receivesAllocation", "logicalElements", advisory=True))),
        WorkflowStep("definePhysicalRealization", P8, (
            P("logicalElements", "LogicalElement", "PartUsage", "in", (1, INFINITY)),
            P("physicalElements", "PhysicalElement", "PartUsage", "out", (1, INFINITY))), (
            C(G8, "allocatedTo", "logicalElements"),
            C(G8B, "receivesAllocation", "physicalElements", advisory=True))),
    ], charter=architecture.scenario.charter)


def _view(architecture: Architecture) -> ModelView:
    builder = architecture.builder
    return ModelView(builder.elements, _traversal(builder), sources=builder.sources)


def _evaluate(architecture: Architecture):
    return evaluate_increment(_view(architecture), architecture.scenario.increment_id, revision=REVISION)


def _subjects(evaluation, gate: str) -> dict[str, str]:
    """Subject element -> verdict of one gate."""
    return {r.subject_id: r.verdict for r in evaluation.canonical.results if r.unit_id == gate and r.subject_id}


def _exits(evaluation) -> dict[str, str]:
    return {phase["phase"]: phase["phase_exit"]["status"] if isinstance(phase["phase_exit"], dict)
            else phase["phase_exit"] for phase in evaluation.status()["phases"] if phase.get("gates")}


def _note(evaluation, gate: str) -> dict[str, Any] | None:
    return next((note for note in evaluation.gaps()["advisory"] if note["gate"] == gate), None)


def _ids(*elements: dict[str, Any]) -> list[str]:
    return [element["@id"] for element in elements]


# -- the relation ----------------------------------------------------------


def test_allocated_to_is_read_from_native_allocations_not_the_successor_traversal() -> None:
    architecture = _architecture(workflow=False)
    assert relation_checks(_view(architecture))["allocatedTo"].__name__ == "allocation_allocatedTo"


def test_each_allocation_reaches_the_target_of_its_end_pair_through_direct_and_chained_ends() -> None:
    a = _architecture(workflow=False)
    view = _view(a)
    requirement0, requirement1 = a.scenario.requirements
    reached = {name: check_relation(view, "allocatedTo", element["@id"]).targets
               for name, element in (("requirement0", requirement0), ("requirement1", requirement1),
                                     ("fnA", a.fn_a), ("fnB", a.fn_b), ("logicalA", a.logical_a))}
    assert reached == {"requirement0": _ids(a.fn_a), "requirement1": _ids(a.fn_b), "fnA": _ids(a.logical_a),
                       "fnB": _ids(a.logical_a), "logicalA": _ids(a.physical_a)}


def test_a_feature_chain_reads_as_its_last_chaining_feature() -> None:
    a = _architecture(workflow=False)
    view = _view(a)
    chains = [e for e in a.builder.elements if e.get("@type") == "Feature"
              and view.index.owned_relationships(e["@id"], "FeatureChaining")]
    assert sorted(chained_feature(view, chain["@id"]) for chain in chains) == sorted(
        _ids(a.fn_b, a.fn_a, a.logical_a))
    assert chained_feature(view, a.fn_a["@id"]) == a.fn_a["@id"]


def test_an_allocation_outside_the_end_pairs_counts_for_none() -> None:
    a = _architecture(workflow=False)
    a.builder.allocation("constraintToLogicalA", a.scenario.needs_package, a.constraint, a.logical_a)
    result = check_relation(_view(a), "allocatedTo", a.constraint["@id"])
    assert result.problem == "" and result.hops == ()
    assert result.absent.endswith("constraint0 is allocated to no AllocatableFunction")


def test_an_end_grounding_in_two_layer_classes_is_unreadable_never_counted() -> None:
    a = _architecture(workflow=False)
    b = a.builder
    both = b.definition("PartDefinition", "LogicalAndPhysical", a.scenario.needs_package,
                        [a.roots["LogicalElement"], a.roots["PhysicalElement"]])
    holder = b.usage("PartUsage", "ambiguous", a.scenario.needs_package, [both])
    lone = b.usage("ActionUsage", "fnLone", a.scenario.needs_package, [a.function_def])
    b.allocation("fnLoneToAmbiguous", a.scenario.needs_package, lone, holder)
    result = check_relation(_view(a), "allocatedTo", lone["@id"])
    assert result.hops == () and result.problem == "model-witness:allocatedTo" and not result.method_side
    assert "grounds in more than one of" in result.reason


def test_plain_dependencies_to_functions_are_near_misses_never_witnesses() -> None:
    a = _architecture(workflow=False)
    a.builder.dependency("constraintTracedToFnA", a.scenario.needs_package, a.constraint, a.fn_a)
    result = check_relation(_view(a), "allocatedTo", a.constraint["@id"])
    assert result.hops == ()
    assert result.near_misses == (
        "1 plain dependency(ies) to allocatableFunctions do not count; only an allocation does",)


# -- the subjects ----------------------------------------------------------


def test_the_scope_closure_holds_definition_features_but_no_parameters_or_connector_ends() -> None:
    a = _architecture()
    view = _view(a)
    closure = set(scope_closure(view, resolve_increment(view, a.scenario.increment_id)))
    assert set(_ids(a.fn_a, a.fn_b, a.logical_a, a.physical_a, a.flow, a.constraint)) <= closure
    ends = {e["@id"] for e in a.builder.elements if e.get("@type") == "Feature"}
    subjects = {e["@id"] for e in a.builder.elements if e.get("@type") == "ReferenceUsage"
                and e.get("declaredName") == "increment"}
    assert not closure & ends and not closure & subjects


def test_conforming_architecture_passes_phases_6_to_8_with_definition_features_as_subjects() -> None:
    a = _architecture()
    evaluation = _evaluate(a)
    assert {p: s for p, s in _exits(evaluation).items() if p in (P6, P7, P8)} == {
        P6: "READY", P7: "READY", P8: "READY"}
    requirement0, requirement1 = a.scenario.requirements
    assert _subjects(evaluation, G6) == {requirement0["@id"]: me.VERDICT_PASS, requirement1["@id"]: me.VERDICT_PASS}
    # The composite flow usage is no function: only the AllocatableFunction-typed features count.
    assert _subjects(evaluation, G7) == {a.fn_a["@id"]: me.VERDICT_PASS, a.fn_b["@id"]: me.VERDICT_PASS}
    assert _subjects(evaluation, G8) == {a.logical_a["@id"]: me.VERDICT_PASS}
    assert _subjects(evaluation, G8B) == {a.physical_a["@id"]: me.VERDICT_PASS}


def test_a_requirement_carried_by_nothing_is_an_advisory_note_covered_by_verification_only() -> None:
    a = _architecture()
    evaluation = _evaluate(a)
    note = _note(evaluation, G6_ADVISORY)
    assert note is not None and [s["name"] for s in note["subjects"]] == ["constraint0"]
    assert any(VERIFICATION_ONLY in d for s in note["subjects"] for d in s.get("diagnostics", []))
    assert _exits(evaluation)[P6] == "READY"  # advisory: never blocks


def test_an_allocation_or_a_relevant_architecture_dependency_carries_a_requirement() -> None:
    allocated = _architecture()
    allocated.builder.allocation("constraintToFnA", allocated.scenario.needs_package, allocated.constraint,
                                 allocated.fn_a)
    assert _note(_evaluate(allocated), G6_ADVISORY) is None
    relevant = _architecture()
    relevant.builder.dependency("functionRelevantToConstraint", relevant.scenario.needs_package,
                                relevant.function_def, relevant.constraint)
    assert check_relation(_view(relevant), "hasRelevantArchitecture", relevant.constraint["@id"]).targets == [
        relevant.function_def["@id"]]
    assert _note(_evaluate(relevant), G6_ADVISORY) is None


def test_an_unallocated_functional_requirement_blocks_phase_6() -> None:
    a = _architecture()
    a.builder.remove(next(e for e in a.builder.elements if e.get("declaredName") == "requirement0ToFnA"))
    evaluation = _evaluate(a)
    assert _exits(evaluation)[P6] == "BLOCKED"
    (gap,) = [g for g in evaluation.gaps()["blocking"] if g["gate"] == G6]
    assert [s["name"] for s in gap["subjects"]] == ["requirement0"]
    assert "allocation <name> allocate" in gap["what_to_author"]


def test_a_function_reused_through_an_own_allocation_is_a_subject_and_its_baseline_chain_is_read() -> None:
    a = _architecture()
    b = a.builder
    baseline = b.package("DE4SDV_FixtureBaseline")
    base_def = b.definition("ActionDefinition", "BaselineFunction", baseline, [a.roots["Function"]])
    base_fn = b.usage("ActionUsage", "baselineFunction", baseline, [base_def])
    b.allocation("constraintToBaseline", a.scenario.needs_package, a.constraint, base_fn)
    evaluation = _evaluate(a)
    assert _subjects(evaluation, G7)[base_fn["@id"]] == me.VERDICT_FAIL  # reused, with no logical element
    assert _exits(evaluation)[P7] == "BLOCKED"
    base_logical_def = b.definition("PartDefinition", "BaselineLogical", baseline, [a.roots["LogicalElement"]])
    base_logical = b.usage("PartUsage", "baselineLogical", baseline, [base_logical_def])
    b.allocation("baselineToLogical", baseline, base_fn, base_logical)
    evaluation = _evaluate(a)
    assert _subjects(evaluation, G7)[base_fn["@id"]] == me.VERDICT_PASS
    # One hop only: the baseline's own allocation names no element of this increment.
    assert base_logical["@id"] not in _subjects(evaluation, G8)


def test_a_declared_phase_without_architecture_elements_blocks_on_an_empty_population() -> None:
    scenario = increment_scenario(applicable_phases=(P0, P6, P7, P8))
    b = scenario.builder
    for cls in ("Function", "LogicalElement", "PhysicalElement", "MemberProduct"):
        b.kernel_definition(cls)
    functional = b.definition("RequirementDefinition", "FixtureFunctionalRequirement", scenario.needs_package,
                              [b.kernel_definition("Requirement")])
    architecture = Architecture(scenario, functional, {}, {}, {}, {}, {}, {}, {}, {}, {})
    _workflow(architecture)
    evaluation = _evaluate(architecture)
    assert _exits(evaluation)[P7] == "BLOCKED" and _exits(evaluation)[P8] == "BLOCKED"
    (gap,) = [g for g in evaluation.gaps()["blocking"] if g["gate"] == G7]
    assert gap["what_to_author"].startswith("keep at least 1 ")
    assert ("in the increment's packages named in the charter's expectedArtifacts, at any depth, and the "
            "elements their allocations name") in gap["what_to_author"]


def test_an_allocation_from_increment_content_outside_the_charter_packages_is_reported() -> None:
    a = _architecture(workflow=False)
    b = a.builder
    elsewhere = b.package("DE4SDV_FixtureElsewhere")
    b.allocation("constraintAllocatedElsewhere", elsewhere, a.constraint, a.fn_a)
    view = _view(a)
    outside = increment_content_outside_scope(view, resolve_increment(view, a.scenario.increment_id))
    assert list(outside) == [elsewhere["@id"]]
    assert list(outside[elsewhere["@id"]].values()) == [f"allocates {view.label(a.constraint['@id'])}"]


def test_the_remedy_writes_the_end_pair_of_the_subject_class() -> None:
    a = _architecture(workflow=False)
    view = _view(a)
    function = check_remedy(view, "allocatedTo", subject=a.fn_a["@id"])
    assert any(line.startswith("part <logicalElement> : ") for line in function.declarations), function.text
    assert f"allocation <name> allocate {view.label(a.fn_a['@id'])} to <logicalElement>;" in function.declarations
    requirement = check_remedy(view, "allocatedTo", subject=a.constraint["@id"])
    assert any(line.startswith("action <function> : ") for line in requirement.declarations), requirement.text
    carried = check_remedy(view, "carriedByArchitecture", subject=a.constraint["@id"])
    assert carried.declarations[-1] == f"dependency <name> from <architecture element> to {view.label(a.constraint['@id'])};"
