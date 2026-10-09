"""What the method evaluator takes from its caller, and the rules it adds for increments.

A caller may replace the registered predicates and add selector kinds it
resolves itself (plain name -> function mappings); unknown names are contract
errors before any evaluation. Declared-phase applicability follows the
increment's declared phases. A population that cannot be established is never
an empty population, and a population outside its bounds (at least
``minimum_population``, at most ``maximum_population`` when set) fails with
POPULATION_POLICY_VIOLATION. A contract without a maximum keeps its digest.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from de4sdv.semantic import method_evaluator as me

#: Digest of ``_contract(_spec())`` before population maxima existed.
DIGEST_WITHOUT_MAXIMUM = "fb027ed485d8a76e435ccfd22cdb238f529cbaa84b59df5370fcb51802aacacc"


def _passing(ctx, spec, subject_id) -> me.PredicateOutcome:
    return me.PredicateOutcome(status="satisfied", targets=("t",))


def _spec(**overrides) -> me.ObligationSpec:
    values = dict(
        obligation_id="OB-1", phase="phase5_requirements", subject_selector="scope usages",
        selector_kind=me.SELECTOR_SCOPE_USAGES, applicability="unconditional",
        applicability_kind=me.APPLICABILITY_UNCONDITIONAL, minimum_population=1, permitted_empty=False,
        permitted_empty_disposition=None, predicate="binding-resolution", target_filters=(),
        cardinality=(1, 1), required=True, evaluation_source=me.EVALUATION_SOURCE_MODEL,
        attestation_policy_ref="", claim_boundary="test claim",
    )
    values.update(overrides)
    return me.ObligationSpec(**values)


def _contract(*obligations: me.ObligationSpec) -> me.MethodContract:
    return me.MethodContract(method_id="de4sdv.test", contract_id="TEST", phase="phase5_requirements",
                             obligations=tuple(obligations))


def _context(declared_phases=None) -> me.EvaluationContext:
    return me.EvaluationContext(
        revision=me.RevisionIdentity("a" * 40, "p", "c", "full-model"), elements=(),
        scope=me.DeclaredEvaluationScope("S", "INC-X", ("U1", "U2"), frozenset(), ()),
        declared_phases=declared_phases,
    )


def _evaluate(spec: me.ObligationSpec, subjects=("A",), declared_phases=None) -> me.EvaluationResult:
    contract = _contract(replace(spec, selector_kind="test-subjects", predicate="test-pass"))
    evaluator = me.MethodEvaluator(contract, predicates={"test-pass": _passing},
                                   selectors={"test-subjects": lambda _spec, _ctx: (list(subjects), [])})
    (unit,) = evaluator.evaluate(_context(declared_phases)).units
    return unit


def test_caller_predicates_and_selector_kinds_dispatch_and_unknown_names_fail_closed() -> None:
    seen: list[str] = []

    def record(ctx, spec, subject_id):
        seen.append(subject_id)
        return _passing(ctx, spec, subject_id)

    contract = _contract(_spec(selector_kind="test-everything", predicate="test-record"))
    evaluation = me.MethodEvaluator(
        contract, predicates={"test-record": record},
        selectors={"test-everything": lambda _spec, _ctx: (["X1", "X2"], [])}).evaluate(_context())
    assert seen == ["X1", "X2"] and evaluation.conformance_verdict == me.VERDICT_PASS
    with pytest.raises(me.ContractValidationError, match="unknown predicate"):
        me.MethodEvaluator(contract, selectors={"test-everything": lambda _spec, _ctx: ([], [])})
    with pytest.raises(me.ContractValidationError, match="unsupported subject_selector kind"):
        me.MethodEvaluator(contract, predicates={"test-record": record})


@pytest.mark.parametrize(("declared", "state", "verdict"), [
    (frozenset({"phase5_requirements"}), me.STATE_COMPLETE, me.VERDICT_PASS),
    (frozenset({"phase4_needs"}), me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE),
    (None, me.STATE_INDETERMINATE, None),
])
def test_declared_phase_applicability_follows_the_declared_phases(declared, state, verdict) -> None:
    unit = _evaluate(_spec(applicability="increment declares the step phase",
                           applicability_kind=me.APPLICABILITY_DECLARED_PHASE), declared_phases=declared)
    assert (unit.state, unit.verdict) == (state, verdict)
    if declared is None:
        assert unit.reason_codes == (me.APPLICABILITY_UNRESOLVED,)


@pytest.mark.parametrize(
    ("reason", "state"),
    [(me.INPUT_UNAVAILABLE, me.STATE_INDETERMINATE), (me.SCOPE_RESOLUTION_ERROR, me.STATE_ERROR)],
)
def test_unresolvable_subjects_are_never_an_empty_population(reason, state) -> None:
    def unresolvable(spec, ctx):
        raise me.SubjectResolutionError(reason, diagnostics=("population unknown",), missing=("kernel-binding:Need",))

    contract = _contract(_spec(selector_kind="test-unresolvable", predicate="test-pass"))
    evaluation = me.MethodEvaluator(contract, predicates={"test-pass": _passing},
                                    selectors={"test-unresolvable": unresolvable}).evaluate(_context())
    (unit,) = evaluation.units
    assert unit.state == state and unit.reason_codes == (reason,)


@pytest.mark.parametrize(("spec", "subjects", "observed"), [
    (_spec(maximum_population=1), ["A", "B"], "2 subjects; the population policy allows at most 1"),
    (_spec(minimum_population=2), ["A"], "1 subject; the population policy requires at least 2"),
])
def test_a_population_outside_its_bounds_fails(spec, subjects, observed) -> None:
    unit = _evaluate(spec, subjects)
    assert (unit.state, unit.verdict, unit.reason_codes) == (
        me.STATE_COMPLETE, me.VERDICT_FAIL, (me.POPULATION_POLICY_VIOLATION,))
    assert any(observed in diagnostic for diagnostic in unit.diagnostics)


def test_a_population_within_its_bounds_is_evaluated() -> None:
    assert _evaluate(_spec(maximum_population=2), ["A", "B"]).verdict == me.VERDICT_PASS
    assert _evaluate(_spec(), ["A", "B", "C"]).verdict == me.VERDICT_PASS
    empty = _evaluate(_spec(minimum_population=0, maximum_population=1, permitted_empty=True,
                            permitted_empty_disposition=me.NO_ELIGIBLE_SUBJECTS), [])
    assert empty.verdict == me.VERDICT_NOT_APPLICABLE


@pytest.mark.parametrize(("minimum", "maximum"), [(1, -1), (2, 1), (1, 0)])
def test_inconsistent_population_bounds_are_contract_errors(minimum: int, maximum: int) -> None:
    with pytest.raises(me.ContractValidationError, match="maximum_population"):
        me.validate_contract(_contract(_spec(minimum_population=minimum, maximum_population=maximum)))


def test_a_contract_without_a_maximum_keeps_its_digest() -> None:
    assert _contract(_spec()).digest() == DIGEST_WITHOUT_MAXIMUM
    assert _contract(_spec(maximum_population=3)).digest() != DIGEST_WITHOUT_MAXIMUM
