"""Reading method gates from the model.

Gates are MethodContractObligation-lineage usages (validated kernel identity)
whose subject selector is a typed increment selector. Their attributes decode
into one method contract spanning the gate phases; prerequisites become
blocking dependencies. Other model obligations (for example a pilot's
phase-10 obligations) are not increment gates and are only listed.
"""

from __future__ import annotations

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic.gate_reader import read_method_gates
from de4sdv.semantic.increment_scope import ModelView
from increment_model_fixtures import (
    INFINITY,
    GateSpec,
    ModelBuilder,
    increment_scenario,
    method_gates,
)
from test_revision_index import _traversal

IDENTITY = GateSpec(
    name="incrementHasIdentifier", phase="phase0_incrementFraming", selector="incrementIdentifier",
    predicate="increment-identity",
    target_filter="EngineeringIncrement lineage; declared short name equals the increment identifier",
    maximum=1, applicability="unconditional",
)
CHARTER = GateSpec(
    name="incrementHasCharter", phase="phase0_incrementFraming", selector="increment",
    predicate="increment-charter-declaration",
    target_filter="IncrementCharter lineage; increment reference resolves to the increment usage",
    maximum=1, applicability="unconditional", prerequisites=("incrementHasIdentifier",),
)
NEED_STAKEHOLDER = GateSpec(
    name="needHasStakeholder", phase="phase4_needs", selector="incrementNeeds",
    predicate="stakeholder-membership", target_filter="Stakeholder lineage",
    prerequisites=("incrementHasCharter",),
)
ADVISORY = GateSpec(
    name="verificationCaseVerifiesAcceptanceCriterion", phase="phase10_vvEvidence",
    selector="incrementVerificationCases", predicate="verifies",
    target_filter="AcceptanceCriterion lineage", required=False, minimum_population=0,
    permitted_empty=True, disposition="noEligibleSubjects", prerequisites=("incrementHasCharter",),
)


def _view(builder: ModelBuilder) -> ModelView:
    return ModelView(builder.elements, _traversal(builder), sources=builder.sources)


def test_gates_decode_into_one_contract_across_phases() -> None:
    scenario = increment_scenario()
    method_gates(scenario.builder, [IDENTITY, CHARTER, NEED_STAKEHOLDER, ADVISORY])
    gates = read_method_gates(_view(scenario.builder), revision_label="a" * 40)
    assert gates.problems == ()
    contract = gates.contract
    assert contract is not None
    assert gates.phases == ("phase0_incrementFraming", "phase4_needs", "phase10_vvEvidence")
    identity = contract.by_id("incrementHasIdentifier")
    assert identity.phase == "phase0_incrementFraming"
    assert identity.subject_selector == "incrementIdentifier"
    assert identity.selector_kind == "incrementIdentifier"
    assert identity.applicability_kind == me.APPLICABILITY_UNCONDITIONAL
    assert identity.cardinality == (1, 1)
    assert identity.required is True and identity.minimum_population == 1
    assert identity.evaluation_source == me.EVALUATION_SOURCE_MODEL
    assert identity.target_filters == (IDENTITY.target_filter,)
    stakeholder = contract.by_id("needHasStakeholder")
    assert stakeholder.applicability_kind == me.APPLICABILITY_DECLARED_PHASE
    assert stakeholder.cardinality == (1, me_unbounded())
    assert stakeholder.depends_on == ("incrementHasCharter",)
    advisory = contract.by_id("verificationCaseVerifiesAcceptanceCriterion")
    assert advisory.required is False
    assert advisory.permitted_empty is True
    assert advisory.permitted_empty_disposition == me.NO_ELIGIBLE_SUBJECTS
    assert set(gates.gate_elements) == {g.name for g in (IDENTITY, CHARTER, NEED_STAKEHOLDER, ADVISORY)}


def me_unbounded() -> int:
    from de4sdv.semantic.gate_reader import UNBOUNDED

    return UNBOUNDED


def test_obligations_with_other_selectors_are_not_increment_gates() -> None:
    scenario = increment_scenario()
    pilot_like = GateSpec(
        name="pilotObligation", phase="phase10_vvEvidence", selector="the declared pilot scope itself",
        predicate="scope-composition", target_filter="element type VerificationCaseUsage",
        applicability="(no applicability condition)",
    )
    method_gates(scenario.builder, [IDENTITY, pilot_like])
    gates = read_method_gates(_view(scenario.builder), revision_label="a" * 40)
    assert gates.problems == ()
    assert [o.obligation_id for o in gates.contract.obligations] == ["incrementHasIdentifier"]
    assert gates.other_obligations == ("pilotObligation",)


def test_a_model_without_gates_has_no_executable_method() -> None:
    scenario = increment_scenario()
    gates = read_method_gates(_view(scenario.builder), revision_label="a" * 40)
    assert gates.contract is None
    assert gates.problems == ()
    assert gates.available is False
    assert "declares no method gates" in gates.reason


def test_an_unknown_predicate_makes_the_method_invalid() -> None:
    scenario = increment_scenario()
    broken = GateSpec(name="brokenGate", phase="phase4_needs", selector="incrementNeeds",
                      predicate="no-such-predicate", prerequisites=("incrementHasIdentifier",))
    method_gates(scenario.builder, [IDENTITY, broken])
    gates = read_method_gates(_view(scenario.builder), revision_label="a" * 40)
    assert gates.contract is None
    assert any("unknown predicate 'no-such-predicate'" in problem for problem in gates.problems)


def test_an_unknown_applicability_or_filter_is_a_method_problem() -> None:
    scenario = increment_scenario()
    odd = GateSpec(name="oddGate", phase="phase4_needs", selector="incrementNeeds",
                   predicate="stakeholder-membership", target_filter="Stakeholder lineage",
                   applicability="whenever it seems right")
    unknown_filter = GateSpec(name="filterGate", phase="phase4_needs", selector="incrementNeeds",
                              predicate="stakeholder-membership", target_filter="Stakeholder-ish things")
    method_gates(scenario.builder, [odd, unknown_filter])
    gates = read_method_gates(_view(scenario.builder), revision_label="a" * 40)
    assert gates.contract is None
    joined = " ".join(gates.problems)
    assert "oddGate" in joined and "applicability" in joined
    assert "filterGate" in joined and "unsupported target filter" in joined


def test_gate_order_does_not_depend_on_corpus_order() -> None:
    first = increment_scenario()
    method_gates(first.builder, [ADVISORY, NEED_STAKEHOLDER, CHARTER, IDENTITY])
    reversed_builder = ModelBuilder(label="Fixture")
    reversed_builder.elements = list(reversed(first.builder.elements))
    reversed_builder.sources = first.builder.sources
    reversed_builder.bindings = first.builder.bindings
    one = read_method_gates(_view(first.builder), revision_label="a" * 40)
    two = read_method_gates(_view(reversed_builder), revision_label="a" * 40)
    assert one.contract.digest() == two.contract.digest()
    assert [o.obligation_id for o in one.contract.obligations] == [
        o.obligation_id for o in two.contract.obligations
    ]
    assert INFINITY is not None
