"""Generic predicate and subject-selector registries of the method evaluator.

Predicates and selector kinds are registered behaviour, not strings the
evaluator core recognises: an obligation's predicate dispatches through the
registry, its target-filter text decodes against the predicate's closed
filter vocabulary into typed target filters at contract validation, and its
selector kind resolves subjects through the selector registry. Unknown names,
kinds or filter texts are contract errors before any evaluation.
"""

from __future__ import annotations

import inspect

import pytest

from de4sdv.semantic import method_evaluator as me


def _spec(**overrides) -> me.ObligationSpec:
    values = dict(
        obligation_id="OB-1",
        phase="phase5_requirements",
        subject_selector="scope usages",
        selector_kind=me.SELECTOR_SCOPE_USAGES,
        applicability="unconditional",
        applicability_kind=me.APPLICABILITY_UNCONDITIONAL,
        minimum_population=1,
        permitted_empty=False,
        permitted_empty_disposition=None,
        predicate="binding-resolution",
        target_filters=(),
        cardinality=(1, 1),
        required=True,
        evaluation_source=me.EVALUATION_SOURCE_MODEL,
        attestation_policy_ref="",
        claim_boundary="test claim",
    )
    values.update(overrides)
    return me.ObligationSpec(**values)


def _contract(*obligations: me.ObligationSpec) -> me.MethodContract:
    return me.MethodContract(
        method_id="de4sdv.test", contract_id="TEST", phase="phase5_requirements",
        obligations=tuple(obligations),
    )


def _context(usage_ids=("U1", "U2")) -> me.EvaluationContext:
    return me.EvaluationContext(
        revision=me.RevisionIdentity("a" * 40, "p", "c", "full-model"),
        elements=(),
        scope=me.DeclaredEvaluationScope("S", "INC-X", tuple(usage_ids), frozenset(), ()),
    )


def test_default_registry_holds_the_existing_predicates() -> None:
    assert me.DEFAULT_PREDICATES.names() == frozenset(
        {
            "binding-resolution",
            "scope-composition",
            "verification-subject-membership",
            "verifiedBy-reverse-witness",
            "verification-method-metadata",
            "external-evidence-reference",
            "execution-outcome",
            "conservative-scope-equality",
            "acceptance-record-match",
        }
    )
    # The legacy name->function view stays available and read-only.
    assert set(me.PREDICATES) == me.DEFAULT_PREDICATES.names()
    with pytest.raises(TypeError):
        me.PREDICATES["new"] = lambda *args: None  # type: ignore[index]


@pytest.mark.parametrize(
    ("predicate", "text", "kind", "argument"),
    [
        ("scope-composition", "element type VerificationCaseUsage", me.FILTER_ELEMENT_TYPE, "VerificationCaseUsage"),
        ("scope-composition", "profile identity equality (pinned set, exact)", me.FILTER_PROFILE_SET_EQUALITY, ""),
        ("verification-subject-membership", "element type OverrideMatrixBench specialization", me.FILTER_BENCH_SPECIALIZATION, "OverrideMatrixBench"),
        ("verifiedBy-reverse-witness", "full-witness-path", me.FILTER_FULL_WITNESS_PATH, ""),
        ("verification-method-metadata", "per-action kind", me.FILTER_PER_ACTION_KIND, ""),
    ],
)
def test_filter_text_decodes_to_a_typed_target_filter(predicate, text, kind, argument) -> None:
    spec = _spec(predicate=predicate, target_filters=(text,))
    (decoded,) = me.DEFAULT_PREDICATES.filters(spec)
    assert (decoded.kind, decoded.argument, decoded.text) == (kind, argument, text)


def test_filter_text_outside_the_predicate_vocabulary_is_a_contract_error() -> None:
    spec = _spec(predicate="scope-composition", target_filters=("element type PartUsage",))
    with pytest.raises(me.ContractValidationError, match="unsupported target filter"):
        me.validate_contract(_contract(spec))


def test_filter_text_of_another_predicate_is_a_contract_error() -> None:
    # A known filter text is still unsupported for a predicate whose
    # vocabulary does not contain it: vocabularies are per predicate.
    spec = _spec(predicate="binding-resolution", target_filters=("per-action kind",))
    with pytest.raises(me.ContractValidationError, match="unsupported target filter"):
        me.validate_contract(_contract(spec))


def test_evaluator_carries_decoded_filters_without_changing_the_contract_digest() -> None:
    spec = _spec(predicate="scope-composition", target_filters=("element type VerificationCaseUsage",))
    contract = _contract(spec)
    evaluator = me.MethodEvaluator(contract)
    decoded = evaluator.contract.by_id("OB-1")
    assert decoded.filters == me.DEFAULT_PREDICATES.filters(spec)
    assert evaluator.contract.digest() == contract.digest()


def test_predicate_dispatch_goes_through_the_injected_registry() -> None:
    calls: list[str] = []

    def always(ctx, spec, subject_id):
        calls.append(subject_id)
        return me.PredicateOutcome(status="satisfied", targets=(f"t-{subject_id}",))

    registry = me.DEFAULT_PREDICATES.with_definitions(
        me.PredicateDefinition(name="test-always", evaluate=always)
    )
    contract = _contract(_spec(predicate="test-always"))
    evaluation = me.MethodEvaluator(contract, predicates=registry).evaluate(_context())
    assert calls == ["U1", "U2"]
    assert evaluation.conformance_verdict == me.VERDICT_PASS
    # Extending a registry never mutates the default registry.
    assert "test-always" not in me.DEFAULT_PREDICATES.names()
    with pytest.raises(me.ContractValidationError, match="unknown predicate"):
        me.MethodEvaluator(contract)


def test_registering_a_duplicate_predicate_name_is_refused() -> None:
    with pytest.raises(ValueError, match="already registered"):
        me.DEFAULT_PREDICATES.with_definitions(
            me.PredicateDefinition(name="scope-composition", evaluate=lambda *a: None)
        )


def test_selector_kind_resolves_through_the_injected_selector_registry() -> None:
    def everything(spec, ctx):
        return ["X1", "X2", "X3"], []

    selectors = me.DEFAULT_SELECTORS.with_definitions(
        me.SelectorDefinition(kind="test-everything", resolve=everything)
    )
    seen: list[str] = []

    def record(ctx, spec, subject_id):
        seen.append(subject_id)
        return me.PredicateOutcome(status="satisfied", targets=("t",))

    predicates = me.DEFAULT_PREDICATES.with_definitions(
        me.PredicateDefinition(name="test-record", evaluate=record)
    )
    contract = _contract(_spec(selector_kind="test-everything", predicate="test-record"))
    me.MethodEvaluator(contract, predicates=predicates, selectors=selectors).evaluate(_context())
    assert seen == ["X1", "X2", "X3"]
    with pytest.raises(me.ContractValidationError, match="unsupported subject_selector kind"):
        me.MethodEvaluator(contract, predicates=predicates)


def test_evaluator_core_does_not_match_pilot_filter_text() -> None:
    # The pilot filter texts live only in the pilot filter vocabularies; the
    # predicates and the target-eligibility filter read typed filters.
    pilot_texts = (
        "element type VerificationCaseUsage",
        "element type OverrideMatrixBench specialization",
        "profile identity equality (pinned set, exact)",
        "full-witness-path",
        "per-action kind",
    )
    for function in (
        me._eligible_target_ids,
        me._predicate_scope_composition,
        me._predicate_subject_membership,
        me._predicate_objective_contracts,
        me._predicate_method_metadata,
        me.MethodEvaluator._subjects,
    ):
        source = inspect.getsource(function)
        for text in pilot_texts:
            assert text not in source, (function.__name__, text)


def _declared_phase_spec() -> me.ObligationSpec:
    return _spec(
        applicability="increment declares the gate phase",
        applicability_kind=me.APPLICABILITY_DECLARED_PHASE,
        predicate="test-pass",
    )


def _pass_registry() -> me.PredicateRegistry:
    return me.DEFAULT_PREDICATES.with_definitions(
        me.PredicateDefinition(
            name="test-pass",
            evaluate=lambda ctx, spec, subject: me.PredicateOutcome(status="satisfied", targets=("t",)),
        )
    )


def _evaluate_declared(declared):
    ctx = _context()
    ctx.declared_phases = declared
    return me.MethodEvaluator(_contract(_declared_phase_spec()), predicates=_pass_registry()).evaluate(ctx)


def test_declared_phase_applicability_evaluates_declared_phases() -> None:
    evaluation = _evaluate_declared(frozenset({"phase5_requirements"}))
    assert evaluation.conformance_verdict == me.VERDICT_PASS


def test_undeclared_phase_is_explicitly_not_applicable() -> None:
    evaluation = _evaluate_declared(frozenset({"phase4_needs"}))
    (unit,) = evaluation.units
    assert (unit.state, unit.verdict) == (me.STATE_COMPLETE, me.VERDICT_NOT_APPLICABLE)
    assert me.EXPLICIT_DISPOSITION in evaluation.results[0].diagnostics


def test_unknown_declared_phases_leave_applicability_unresolved() -> None:
    evaluation = _evaluate_declared(None)
    (unit,) = evaluation.units
    assert (unit.state, unit.verdict) == (me.STATE_INDETERMINATE, None)
    assert unit.reason_codes == (me.APPLICABILITY_UNRESOLVED,)


@pytest.mark.parametrize(
    ("reason", "state"),
    [(me.INPUT_UNAVAILABLE, me.STATE_INDETERMINATE), (me.SCOPE_RESOLUTION_ERROR, me.STATE_ERROR)],
)
def test_unresolvable_subjects_are_never_an_empty_population(reason, state) -> None:
    def unresolvable(spec, ctx):
        raise me.SubjectResolutionError(reason, diagnostics=("population unknown",),
                                        missing=("kernel-binding:Need",))

    selectors = me.DEFAULT_SELECTORS.with_definitions(
        me.SelectorDefinition(kind="test-unresolvable", resolve=unresolvable)
    )
    contract = _contract(_spec(selector_kind="test-unresolvable", predicate="test-pass"))
    evaluation = me.MethodEvaluator(contract, predicates=_pass_registry(), selectors=selectors).evaluate(
        _context()
    )
    (unit,) = evaluation.units
    assert unit.state == state
    assert unit.reason_codes == (reason,)
    assert me.POPULATION_POLICY_VIOLATION not in unit.reason_codes
