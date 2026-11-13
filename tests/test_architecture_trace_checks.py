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

import pytest

import de4sdv.semantic.increment_workflow as workflow_reader
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

#: An export snapshot, as the pull-request Method Check evaluates: an API revision binding withholds these checks
#: while allocatedTo has open forward obligations (test_allocation_checks_are_withheld_while_an_obligation_is_open).
REVISION = me.RevisionIdentity("a" * 40, "", "", workflow_reader.EXPORT_SNAPSHOT_SCOPE)
API_BINDING = me.RevisionIdentity("a" * 40, "project", "commit", "full-model")
P0, P6, P7, P8 = ("phase0_incrementFraming", "phase6_functionalArchitecture", "phase7_logicalArchitecture",
                  "phase8_physicalRealization")
P, C = WorkflowParameter, WorkflowCheck
G6, G6_ADVISORY, G6B = ("functionalRequirementAllocatedToFunction", "requirementCarriedByArchitecture",
                        "functionCarriesRequirement")
G6_POPULATION = "incrementHasFunction"
G7, G7B, G8, G8B = ("functionAllocatedToLogicalElement", "logicalElementCarriesFunction",
                    "logicalElementAllocatedToPhysicalElement", "physicalElementCarriesLogicalElement")
VERIFICATION_ONLY = "is carried by no architecture element and is covered by verification only"
NO_VERIFICATION_YET = "is carried by no architecture element and has no verification case yet"
ARCHITECTURE_GATES = (G6, G6_POPULATION, G6_ADVISORY, G6B, G7, G7B, G8, G8B)


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
            C(G6_POPULATION, "populationMember", "functions"),
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


def _evaluate(architecture: Architecture, revision: me.RevisionIdentity = REVISION):
    return evaluate_increment(_view(architecture), architecture.scenario.increment_id, revision=revision)


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


def _diagnostics(note: dict[str, Any], name: str) -> list[str]:
    return next(s.get("diagnostics", []) for s in note["subjects"] if s["name"] == name)


def _verify(a: Architecture, requirement: dict[str, Any]) -> None:
    """A verification case whose objective verifies ``requirement`` (the verifiedBy shape phase 10 reads)."""
    b = a.builder
    case_def = b.definition("VerificationCaseDefinition", "ConstraintVerification", a.scenario.evidence_package)
    b.objective(case_def, "constraintObjective", [requirement])
    b.usage("VerificationCaseUsage", "constraintVerification", a.scenario.evidence_package, [case_def])


def _poison(a: Architecture) -> None:
    """One allocation in an unrelated package whose chain end names a feature no longer in the revision."""
    b = a.builder
    other = b.package("DE4SDV_FixtureUnrelated")
    holder = b.definition("PartDefinition", "Holder", other)
    x = b.usage("PartUsage", "x", other, [holder])
    y = b.usage("PartUsage", "y", holder, membership="FeatureMembership")
    b.allocation("unrelatedUnreadable", other, [x, y], b.usage("PartUsage", "z", other))
    b.remove(y)


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


def test_an_allocation_outside_the_end_pairs_counts_for_none_and_is_a_near_miss() -> None:
    a = _architecture(workflow=False)
    a.builder.allocation("constraintToLogicalA", a.scenario.needs_package, a.constraint, a.logical_a)
    view = _view(a)
    result = check_relation(view, "allocatedTo", a.constraint["@id"])
    assert result.problem == "" and result.hops == ()
    assert result.absent.endswith("constraint0 is allocated to no AllocatableFunction")
    assert result.near_misses == (f"1 allocation(s) between it and {view.label(a.logical_a['@id'])} ground in no "
                                  "allocatedTo end pair and do not count",)


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


def test_a_dependency_from_a_function_to_a_functional_requirement_is_a_near_miss_of_the_blocking_check() -> None:
    """The baseline's own trace shape (a dependency from the function to the requirement) carries the
    requirement for the advisory check (hasRelevantArchitecture), never for allocatedTo: the gap says so."""
    a = _architecture()
    b = a.builder
    requirement0 = a.scenario.requirements[0]
    b.remove(next(e for e in b.elements if e.get("declaredName") == "requirement0ToFnA"))
    b.dependency("functionRelevantToRequirement0", a.scenario.needs_package, a.function_def, requirement0)
    evaluation = _evaluate(a)
    assert _subjects(evaluation, G6)[requirement0["@id"]] == me.VERDICT_FAIL
    assert _subjects(evaluation, G6_ADVISORY)[requirement0["@id"]] == me.VERDICT_PASS
    (gap,) = [g for g in evaluation.gaps()["blocking"] if g["gate"] == G6]
    assert _diagnostics(gap, "requirement0")[1:] == [
        "1 dependency(ies) from allocatableFunctions to it do not count; only an allocation does"]


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


def test_a_perform_usage_names_the_function_it_performs_and_is_no_function_of_its_own() -> None:
    """``perform fixtureFlow.fnA;`` in a logical part: a PerformActionUsage typed like fnA, with an authored
    ReferenceSubsetting to it (the export's shape). It declares no function, so it is not a subject."""
    a = _architecture()
    b = a.builder
    perform = b.usage("PerformActionUsage", "performFnA", a.logical_a, [a.function_def],
                      membership="FeatureMembership")
    b.reference_subsetting(perform, a.fn_a)
    view = _view(a)
    assert perform["@id"] not in scope_closure(view, resolve_increment(view, a.scenario.increment_id))
    assert _subjects(_evaluate(a), G7) == {a.fn_a["@id"]: me.VERDICT_PASS, a.fn_b["@id"]: me.VERDICT_PASS}


def test_conforming_architecture_passes_phases_6_to_8_with_definition_features_as_subjects() -> None:
    a = _architecture()
    evaluation = _evaluate(a)
    assert {p: s for p, s in _exits(evaluation).items() if p in (P6, P7, P8)} == {
        P6: "READY", P7: "READY", P8: "READY"}
    requirement0, requirement1 = a.scenario.requirements
    assert _subjects(evaluation, G6) == {requirement0["@id"]: me.VERDICT_PASS, requirement1["@id"]: me.VERDICT_PASS}
    assert _subjects(evaluation, G6_POPULATION) == {a.fn_a["@id"]: me.VERDICT_PASS, a.fn_b["@id"]: me.VERDICT_PASS}
    # The composite flow usage is no function: only the AllocatableFunction-typed features count.
    assert _subjects(evaluation, G7) == {a.fn_a["@id"]: me.VERDICT_PASS, a.fn_b["@id"]: me.VERDICT_PASS}
    assert _subjects(evaluation, G8) == {a.logical_a["@id"]: me.VERDICT_PASS}
    assert _subjects(evaluation, G8B) == {a.physical_a["@id"]: me.VERDICT_PASS}


def test_a_requirement_carried_by_nothing_is_an_advisory_note_that_says_whether_verification_covers_it() -> None:
    """Covered by verification only when a verification case verifies it (verifiedBy, as phase 10
    reads it); otherwise it has no verification case yet."""
    a = _architecture()
    evaluation = _evaluate(a)
    note = _note(evaluation, G6_ADVISORY)
    assert note is not None and [s["name"] for s in note["subjects"]] == ["constraint0"]
    (diagnostic,) = _diagnostics(note, "constraint0")
    assert diagnostic.endswith(NO_VERIFICATION_YET) and VERIFICATION_ONLY not in diagnostic
    assert _exits(evaluation)[P6] == "READY"  # advisory: never blocks
    _verify(a, a.constraint)
    evaluation = _evaluate(a)
    (diagnostic,) = _diagnostics(_note(evaluation, G6_ADVISORY), "constraint0")
    assert diagnostic.endswith(VERIFICATION_ONLY)
    assert _exits(evaluation)[P6] == "READY"


def test_a_requirement_allocated_to_a_logical_element_is_never_reported_as_carried_by_nothing() -> None:
    a = _architecture()
    a.builder.allocation("constraintToLogicalA", a.scenario.needs_package, a.constraint, a.logical_a)
    evaluation = _evaluate(a)
    (diagnostic,) = _diagnostics(_note(evaluation, G6_ADVISORY), "constraint0")
    assert "carried by no architecture element" not in diagnostic
    assert diagnostic.endswith(
        "constraint0 is allocated to no function and named as relevant by no architecture element "
        f"(hasRelevantArchitecture); its allocation(s) with {_view(a).label(a.logical_a['@id'])} ground in no "
        "allocatedTo end pair")


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


def test_an_unreadable_allocation_anywhere_leaves_absence_unestablished() -> None:
    """Absence is not established while any allocation is unreadable: its ends are unknown, so it may be
    the one that reaches the subject. Each subject without a counting allocation is INDETERMINATE (an
    input problem the author can fix), never a gap; subjects with one still pass."""
    a = _architecture()
    b = a.builder
    requirement0 = a.scenario.requirements[0]
    b.remove(next(e for e in b.elements if e.get("declaredName") == "requirement0ToFnA"))
    assert _subjects(_evaluate(a), G6)[requirement0["@id"]] == me.VERDICT_FAIL
    _poison(a)
    evaluation = _evaluate(a)
    results = {r.subject_id: r for r in evaluation.canonical.results if r.unit_id == G6 and r.subject_id}
    assert results[requirement0["@id"]].verdict is None
    assert results[requirement0["@id"]].missing == ("model-witness:allocatedTo",)
    (diagnostic,) = results[requirement0["@id"]].diagnostics
    assert diagnostic.startswith("1 allocation cannot be read, so absence cannot be established: "
                                 "DE4SDV_FixtureUnrelated::unrelatedUnreadable: ")
    assert results[a.scenario.requirements[1]["@id"]].verdict == me.VERDICT_PASS
    assert _subjects(evaluation, G6_ADVISORY)[a.constraint["@id"]] is None
    step = evaluation.next_obligation()["next"]
    assert (step["gate"], step["kind"]) == (G6, "input-problem")


def _withheld(evaluation) -> dict[str, str]:
    """Phase 6 to 8 gate -> the diagnostic it is withheld with (method side, no verdict); every gate
    when the guard holds."""
    found = {}
    for gate in ARCHITECTURE_GATES:
        unit = evaluation._unit(gate)
        if (unit.verdict, unit.missing) == (None, ("allocation-admission:allocatedTo",)):
            found[gate] = unit.diagnostics[0]
    return found


#: An obligation a row of the admission could list, for the tests of the guard itself.
OPEN_OBLIGATION = "exact-revision traversal evidence (exact-SHA privileged run) before any runtime-queryable claim"


def test_allocation_checks_are_withheld_while_an_obligation_is_open(monkeypatch) -> None:
    """While allocatedTo has open forward obligations, an API revision binding reports every check of
    phases 6 to 8 as method side (nothing to author, exits BLOCKED); an export snapshot evaluates them."""
    monkeypatch.setattr(workflow_reader, "open_forward_obligations", lambda relation: (OPEN_OBLIGATION,))
    a = _architecture()
    api, export = _evaluate(a, API_BINDING), _evaluate(a)
    withheld = _withheld(api)
    assert list(withheld) == list(ARCHITECTURE_GATES)
    assert all("withholds the checks that read native allocations" in d for d in withheld.values())
    assert _withheld(export) == {}
    answer = api.next_obligation()
    assert answer["next"] is None
    assert [blocker["gate"] for blocker in answer["method_side_blockers"]] == [G6, G6_POPULATION, G7, G8]
    assert _exits(api) == {P6: "BLOCKED", P7: "BLOCKED", P8: "BLOCKED"}
    assert _exits(export) == {P6: "READY", P7: "READY", P8: "READY"}


def test_the_allocation_guard_lifts_with_this_checkouts_admission() -> None:
    """The admission lists no open obligation of allocatedTo (an exact-SHA privileged run discharged both;
    test_kernel_vocabulary_projection pins the record), so an API revision binding evaluates every check of
    phases 6 to 8 as the export snapshot does."""
    a = _architecture()
    api, export = _evaluate(a, API_BINDING), _evaluate(a)
    assert _withheld(api) == {}
    for gate in ARCHITECTURE_GATES:
        assert _subjects(api, gate) == _subjects(export, gate), gate
    assert _exits(api) == _exits(export) == {P6: "READY", P7: "READY", P8: "READY"}
    assert api.next_obligation()["method_side_blockers"] == export.next_obligation()["method_side_blockers"] == []


def test_the_admission_lists_no_open_forward_obligation_of_allocated_to() -> None:
    """The guard reads them from this checkout's kernel-vocabulary admission. The successor parity and the
    allocation-end closure of the exact-SHA privileged run discharged both; the row records them under
    discharged_obligations, which the guard does not read."""
    assert workflow_reader.open_forward_obligations("allocatedTo") == ()


@pytest.fixture
def admission_path(tmp_path, monkeypatch):
    """Where the guard reads the kernel-vocabulary admission, under a root the test controls. The
    obligation cache is cleared around the test, so nothing read here outlives it."""
    workflow_reader.open_forward_obligations.cache_clear()
    monkeypatch.setattr(workflow_reader, "ROOT", tmp_path)
    yield tmp_path / workflow_reader.ADMISSION_PATH
    workflow_reader.open_forward_obligations.cache_clear()


def test_an_admission_that_cannot_be_read_leaves_the_obligations_open(admission_path) -> None:
    """Fail closed: a missing or malformed admission counts as one open obligation, so an API revision
    binding still withholds every check of phases 6 to 8."""
    (missing,) = workflow_reader.open_forward_obligations("allocatedTo")
    assert missing.startswith("the kernel-vocabulary admission cannot be read: ")
    admission_path.parent.mkdir(parents=True)
    admission_path.write_text("admitted: [unclosed\n", encoding="utf-8")
    workflow_reader.open_forward_obligations.cache_clear()
    (malformed,) = workflow_reader.open_forward_obligations("allocatedTo")
    assert malformed.startswith("the kernel-vocabulary admission cannot be read: ")
    withheld = _withheld(_evaluate(_architecture(), API_BINDING))
    assert list(withheld) == list(ARCHITECTURE_GATES)
    assert all("allocatedTo: the kernel-vocabulary admission cannot be read" in d for d in withheld.values())


def test_an_admission_without_an_allocated_to_row_leaves_the_obligations_open(admission_path) -> None:
    """Fail closed: an admission that lists no allocatedTo row counts as one open obligation (only a
    row whose obligations are discharged lifts the guard)."""
    admission_path.parent.mkdir(parents=True)
    admission_path.write_text("admitted:\n- identity: hasRelevantArchitecture\n  forward_obligations: []\n",
                              encoding="utf-8")
    assert workflow_reader.open_forward_obligations("hasRelevantArchitecture") == ()
    assert workflow_reader.open_forward_obligations("allocatedTo") == (
        "the kernel-vocabulary admission has no row for allocatedTo",)
    withheld = _withheld(_evaluate(_architecture(), API_BINDING))
    assert list(withheld) == list(ARCHITECTURE_GATES)
    assert all("allocatedTo: the kernel-vocabulary admission has no row for allocatedTo" in d
               for d in withheld.values())


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
    assert {p: s for p, s in _exits(evaluation).items() if p in (P6, P7, P8)} == {
        P6: "BLOCKED", P7: "BLOCKED", P8: "BLOCKED"}
    # Phase 6: no functional requirement (its blocking trace does not apply) and no function.
    assert evaluation._unit(G6).verdict == me.VERDICT_NOT_APPLICABLE
    for gate in (G6_POPULATION, G7):
        (gap,) = [g for g in evaluation.gaps()["blocking"] if g["gate"] == gate]
        assert "POPULATION_POLICY_VIOLATION" in gap["reason_codes"], gate
        assert gap["what_to_author"].startswith("keep at least 1 "), gate
        assert ("in the increment's packages named in the charter's expectedArtifacts, at any depth, and the "
                "elements their allocations name") in gap["what_to_author"], gate
    assert evaluation.next_obligation()["next"]["gate"] == G6_POPULATION


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
    constraint = view.label(a.constraint["@id"])
    carried = check_remedy(view, "carriedByArchitecture", subject=a.constraint["@id"])
    assert carried.declarations == (f"allocation <name> allocate {constraint} to <function>;",)
    (alternative,) = [note for note in carried.notes if note.startswith("Instead of the allocation")]
    assert alternative.endswith(f"dependency <name> from <element> to {constraint};")
    assert f"Leaving {constraint} carried by neither is allowed" in carried.text


def test_a_source_remedy_declares_no_new_source_and_says_none_is_allowed() -> None:
    a = _architecture(workflow=False)
    b = a.builder
    view = _view(a)
    received = check_remedy(view, "receivesAllocation", subject=a.fn_a["@id"])
    function = view.label(a.fn_a["@id"])
    assert received.declarations == (f"allocation <name> allocate <requirement> to {function};",)
    assert f"Leaving {function} without one is allowed" in received.text
    assert "declare no new <requirement> just to close the note" in received.text
    logical_def = next(e for e in b.elements if e.get("declaredName") == "FixtureLogical")
    logical_b = b.usage("PartUsage", "logicalB", a.scenario.needs_package, [logical_def])
    _workflow(a)
    gaps = _evaluate(a).gaps()
    (note,) = [n for n in gaps["advisory"] if n["gate"] == G7B]
    assert _diagnostics(note, "logicalB") == [
        f"{_view(a).label(logical_b['@id'])} receives no allocatedTo allocation from an AllocatableFunction"]
