"""Population bounds of an obligation: at least a minimum, at most a maximum.

An obligation states how many subjects its population may have: at least
``minimum_population`` and, when set, at most ``maximum_population`` (for
example a method step parameter ``[1]``: exactly one). A population outside
these bounds fails with POPULATION_POLICY_VIOLATION and is never evaluated as
a pass. An empty population with a permitted-empty disposition stays not
applicable. A contract without a maximum keeps its digest.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from de4sdv.semantic import method_evaluator as me
from test_method_predicate_registry import _context, _contract, _spec

#: Digest of ``_contract(_spec())`` before population maxima existed.
DIGEST_WITHOUT_MAXIMUM = "fb027ed485d8a76e435ccfd22cdb238f529cbaa84b59df5370fcb51802aacacc"


def _evaluate(spec: me.ObligationSpec, subjects: list[str]) -> me.CanonicalEvaluation:
    selectors = me.DEFAULT_SELECTORS.with_definitions(
        me.SelectorDefinition(kind="test-subjects", resolve=lambda _spec, _ctx: (list(subjects), [])))
    predicates = me.DEFAULT_PREDICATES.with_definitions(me.PredicateDefinition(
        name="test-pass",
        evaluate=lambda ctx, obligation, subject: me.PredicateOutcome(status="satisfied", targets=("t",))))
    contract = _contract(replace(spec, selector_kind="test-subjects", predicate="test-pass"))
    return me.MethodEvaluator(contract, predicates=predicates, selectors=selectors).evaluate(_context())


def _unit(evaluation: me.CanonicalEvaluation) -> me.EvaluationResult:
    (unit,) = evaluation.units
    return unit


def test_a_population_above_the_maximum_fails() -> None:
    unit = _unit(_evaluate(_spec(maximum_population=1), ["A", "B"]))
    assert (unit.coverage, unit.state, unit.verdict) == (
        me.COVERAGE_ASSESSED, me.STATE_COMPLETE, me.VERDICT_FAIL)
    assert unit.reason_codes == (me.POPULATION_POLICY_VIOLATION,)
    assert any("2 subjects" in diagnostic and "at most 1" in diagnostic for diagnostic in unit.diagnostics)


def test_a_non_empty_population_below_the_minimum_fails() -> None:
    unit = _unit(_evaluate(_spec(minimum_population=2), ["A"]))
    assert (unit.state, unit.verdict, unit.reason_codes) == (
        me.STATE_COMPLETE, me.VERDICT_FAIL, (me.POPULATION_POLICY_VIOLATION,))
    assert any("1 subject" in diagnostic and "at least 2" in diagnostic for diagnostic in unit.diagnostics)


def test_a_population_within_the_bounds_is_evaluated() -> None:
    evaluation = _evaluate(_spec(minimum_population=1, maximum_population=2), ["A", "B"])
    assert evaluation.conformance_verdict == me.VERDICT_PASS


def test_without_a_maximum_any_population_size_is_evaluated() -> None:
    assert _evaluate(_spec(), ["A", "B", "C"]).conformance_verdict == me.VERDICT_PASS


def test_an_empty_permitted_population_stays_not_applicable_under_a_maximum() -> None:
    spec = _spec(minimum_population=0, maximum_population=1, permitted_empty=True,
                 permitted_empty_disposition=me.NO_ELIGIBLE_SUBJECTS)
    unit = _unit(_evaluate(spec, []))
    assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE)


@pytest.mark.parametrize(("minimum", "maximum"), [(1, -1), (2, 1), (1, 0)])
def test_inconsistent_population_bounds_are_contract_errors(minimum: int, maximum: int) -> None:
    with pytest.raises(me.ContractValidationError, match="maximum_population"):
        me.validate_contract(_contract(_spec(minimum_population=minimum, maximum_population=maximum)))


def test_a_contract_without_a_maximum_keeps_its_digest() -> None:
    assert _contract(_spec()).digest() == DIGEST_WITHOUT_MAXIMUM
    assert _contract(_spec(maximum_population=3)).digest() != DIGEST_WITHOUT_MAXIMUM
