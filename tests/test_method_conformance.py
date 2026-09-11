"""Lane C: deterministic evaluator + discovery acceptance matrix.

Covers every C-owned MC case (mc-outcome-owner-matrix.md): MC-01..09,
MC-11..13, MC-15..20, MC-23, MC-26, MC-27, MC-29, MC-31, MC-33..35,
MC-38..40, plus the adversarial set required by the Lane C brief.

In-memory synthetic fixtures only; no real model files are copied. Serializer
shapes mirror the committed contract, the Lane B binding tests, and the real
pilot shapes (feature-membership attribute chains, reference shadows,
metadata subtrees) without embedding real model content.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

from de4sdv.semantic import method_evaluator as me
from de4sdv.semantic import method_pilot as mp

ROOT = Path(__file__).resolve().parents[1]

REV = me.RevisionIdentity(
    git_commit="a" * 40,
    sysml_project_id="proj-1",
    sysml_commit_id="commit-1",
    scope="candidate",
)


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def make_spec(**overrides) -> me.ObligationSpec:
    defaults = dict(
        obligation_id="OB-1",
        phase="phase6_functionalArchitecture",
        subject_selector="scope usages",
        selector_kind=me.SELECTOR_SCOPE_USAGES,
        applicability="(no applicability condition)",
        applicability_kind="unconditional",
        minimum_population=1,
        permitted_empty=False,
        permitted_empty_disposition=None,
        predicate="binding-resolution",
        target_filters=(),
        cardinality=(1, 1),
        required=True,
        evaluation_source="pinned-model-record",
        attestation_policy_ref="",
        claim_boundary="test claim boundary",
    )
    defaults.update(overrides)
    return me.ObligationSpec(**defaults)


def make_contract(obligations=(), **overrides) -> me.MethodContract:
    defaults = dict(
        method_id="de4sdv.test-method",
        contract_id="TEST-CONTRACT",
        phase="phase6_functionalArchitecture",
        obligations=tuple(obligations),
    )
    defaults.update(overrides)
    return me.MethodContract(**defaults)


def make_scope(usage_ids=("U1", "U2"), profiles=("p1", "p2")) -> me.DeclaredEvaluationScope:
    return me.DeclaredEvaluationScope(
        scope_id="PSC-X",
        increment_id="INC-X",
        usage_ids=tuple(usage_ids),
        contribution_ids=frozenset({"PSC-X"}),
        profiles=tuple(profiles),
    )


def make_context(*, elements=(), usage_bindings=None, scope=None, **overrides):
    values = dict(
        revision=REV,
        elements=tuple(elements),
        scope=scope or make_scope(),
        usage_bindings=usage_bindings or {},
        definition_id=None,
        requirement_target_ids=(),
        bench_definition_id=None,
        artifact_source=None,
        bench_root="",
        campaign_manifest=None,
        records={},
        expected_dispositions={},
        registry_scan=None,
        scope_equality={},
        task_entry_prerequisites={},
        pilot_scope_declared=True,
        candidate_missing_inputs=(),
        diagnostics=(),
    )
    values.update(overrides)
    return me.EvaluationContext(**values)


def ok_binding(usage_id: str, **extra) -> dict:
    binding = {
        "element_id": f"elem-{usage_id}",
        "resolution_level": "stable-explicit-id",
        "element_type": "VerificationCaseUsage",
        "subject_members": (),
        "metadata_owners": (),
        "objective_targets": (),
        "expected_kind_values": (),
    }
    binding.update(extra)
    return binding


def manifest(profiles=("p1", "p2"), head="b" * 40) -> dict:
    return {
        "execution_head": head,
        "increment_id": "INC-X",
        "profiles": {
            name: {"path": f"evidence/{name}.json", "run_id": f"run-{name}", "sha256": ""}
            for name in profiles
        },
    }


def evaluate(specs, context, **kwargs):
    evaluator = me.MethodEvaluator(make_contract(specs))
    return evaluator.evaluate(context, **kwargs)


def child(evaluation, unit_id):
    children = [r for r in evaluation.results if r.unit_id == unit_id]
    assert children, f"no child result for {unit_id}"
    return children


def unit(evaluation, unit_id):
    return next(u for u in evaluation.units if u.unit_id == unit_id)


# ---------------------------------------------------------------------------
# MC-01: complete scoped pilot, passing executions -> COMPLETE / PASS
# ---------------------------------------------------------------------------


def test_mc01_complete_pass() -> None:
    spec = make_spec()
    ctx = make_context(usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")})
    evaluation = evaluate([spec], ctx)
    assert evaluation.assessment_coverage == "ASSESSED"
    assert evaluation.evaluation_state == "COMPLETE"
    assert evaluation.conformance_verdict == "PASS"
    assert all(r.verdict == "PASS" and r.reason_codes == () for r in evaluation.results)
    assert evaluation.evaluated_at == ""  # no timestamp inside the canonical payload


# ---------------------------------------------------------------------------
# MC-02: one subject missing required evidence -> FAIL naming subject + relation
# ---------------------------------------------------------------------------


def test_mc02_missing_evidence_fails_with_subject_and_relation() -> None:
    spec = make_spec(
        predicate="verification-subject-membership",
        cardinality=(1, 1),
        target_filters=("element type OverrideMatrixBench specialization",),
    )
    ctx = make_context(
        usage_bindings={
            "U1": ok_binding("U1", subject_members=("member-1",)),
            "U2": ok_binding("U2", subject_members=()),
        },
        bench_definition_id="bench-def",
        elements=tuple(_bench_elements().values()),
    )
    evaluation = evaluate([spec], ctx)
    assert evaluation.conformance_verdict == "FAIL"
    failing = [r for r in evaluation.results if r.verdict == "FAIL"]
    assert len(failing) == 1
    assert failing[0].subject_id == "U2"
    assert failing[0].reason_codes == ("REQUIRED_RELATION_MISSING",)


# ---------------------------------------------------------------------------
# MC-03: several records for one case, none for another -> covered per subject
# ---------------------------------------------------------------------------


def test_mc03_per_subject_coverage_not_global_counts() -> None:
    spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
        cardinality=(1, 1),
    )
    base_manifest = manifest(profiles=("p1",))  # p2 has no entry at all
    ctx = make_context(campaign_manifest=base_manifest, scope=make_scope(profiles=("p1", "p2")))
    evaluation = evaluate([spec], ctx)
    children = {r.subject_id: r for r in evaluation.results}
    # p1: entry present but storage unbound -> INDETERMINATE, never pass; p2: no
    # canonical record -> FAIL with the uncovered subject named.
    assert children["p2"].reason_codes == ("REQUIRED_RELATION_MISSING",)
    assert children["p2"].verdict == "FAIL"
    assert children["p1"].state == "INDETERMINATE"
    # The uncovered case fails at its own subject; no global-count rescue and no
    # pass verdict anywhere in the evaluation.
    assert any(r.verdict == "FAIL" for r in evaluation.results)
    assert all(r.verdict != "PASS" for r in evaluation.results)


def test_mc03_several_paths_for_one_record_still_one_distinct_target() -> None:
    # MC-04 shared shape: duplicate witnesses for the same member count once.
    spec = make_spec(
        predicate="verification-subject-membership",
        cardinality=(1, 1),
        target_filters=("element type OverrideMatrixBench specialization",),
    )
    ctx = make_context(
        usage_bindings={
            "U1": ok_binding("U1", subject_members=("member-1", "member-1")),
        },
        elements=(),
        bench_definition_id="bench-def",
        scope=make_scope(usage_ids=("U1",)),
    )
    evaluation = evaluate([spec], ctx)
    result = evaluation.results[0]
    assert result.verdict == "FAIL"  # no resolvable bench chain in this fixture
    assert result.targets == ()


# ---------------------------------------------------------------------------
# MC-04: duplicate paths to one target count once
# ---------------------------------------------------------------------------


def test_mc04_distinct_targets_counted_once() -> None:
    elements = _bench_elements()
    spec = make_spec(
        predicate="verification-subject-membership",
        cardinality=(1, 1),
        target_filters=("element type OverrideMatrixBench specialization",),
    )
    ctx = make_context(
        usage_bindings={
            "U1": ok_binding("U1", subject_members=("member-1", "member-1")),
        },
        elements=tuple(elements.values()),
        bench_definition_id="bench-def",
        scope=make_scope(usage_ids=("U1",)),
    )
    evaluation = evaluate([spec], ctx)
    result = evaluation.results[0]
    assert result.verdict == "PASS"
    assert result.targets == ("member-1",)  # one distinct target, not two paths


def _bench_elements() -> dict:
    """ReferenceUsage shadow -> Subsetting/Redefinition -> PartUsage typed by
    the bench definition (mirrors the real verifiedBench chain)."""
    return {
        "member-1": {
            "@id": "member-1",
            "@type": "ReferenceUsage",
            "declaredName": "verifiedBench",
            "ownedRelationship": [{"@id": "sub-1"}],
        },
        "bench-part": {
            "@id": "bench-part",
            "@type": "PartUsage",
            "declaredName": "bench",
            "ownedRelationship": [{"@id": "ft-1"}],
        },
        "bench-def": {"@id": "bench-def", "@type": "PartDefinition", "declaredName": "OverrideMatrixBench"},
        "sub-1": {
            "@id": "sub-1",
            "@type": "Subsetting",
            "owningRelatedElement": {"@id": "member-1"},
            "specific": {"@id": "member-1"},
            "subsettedFeature": {"@id": "bench-part"},
        },
        "ft-1": {
            "@id": "ft-1",
            "@type": "FeatureTyping",
            "owningRelatedElement": {"@id": "bench-part"},
            "specific": {"@id": "bench-part"},
            "general": {"@id": "bench-def"},
            "type": {"@id": "bench-def"},
        },
    }


# ---------------------------------------------------------------------------
# MC-05: valid scope, no subjects, non-empty policy -> COMPLETE / FAIL
# ---------------------------------------------------------------------------


def test_mc05_empty_population_with_policy_fails() -> None:
    spec = make_spec(subject_selector="scope usages", selector_kind=me.SELECTOR_SCOPE_USAGES)
    ctx = make_context(scope=make_scope(usage_ids=()), usage_bindings={})
    evaluation = evaluate([spec], ctx)
    result = evaluation.results[0]
    assert result.coverage == "ASSESSED"
    assert result.state == "COMPLETE"
    assert result.verdict == "FAIL"
    assert result.reason_codes == ("POPULATION_POLICY_VIOLATION",)
    assert evaluation.conformance_verdict == "FAIL"


# ---------------------------------------------------------------------------
# MC-06: missing membership / broken selector / wrong type -> no empty pass
# ---------------------------------------------------------------------------


def test_mc06_unresolved_usage_is_error() -> None:
    spec = make_spec()
    ctx = make_context(usage_bindings={"U1": ok_binding("U1")})  # U2 unbound
    evaluation = evaluate([spec], ctx)
    failing = [r for r in evaluation.results if r.subject_id == "U2"][0]
    assert failing.state == "ERROR"
    assert failing.reason_codes == ("SCOPE_RESOLUTION_ERROR",)
    assert evaluation.evaluation_state == "ERROR"
    assert evaluation.conformance_verdict is None


def test_mc06_name_based_resolution_is_not_provenance() -> None:
    spec = make_spec()
    ctx = make_context(
        usage_bindings={
            "U1": ok_binding("U1"),
            "U2": ok_binding("U2", resolution_level="structural-match"),
        }
    )
    evaluation = evaluate([spec], ctx)
    failing = [r for r in evaluation.results if r.subject_id == "U2"][0]
    assert failing.state == "ERROR"
    assert failing.reason_codes == ("SCOPE_RESOLUTION_ERROR",)


def test_mc06_wrong_target_type_is_binding_mismatch() -> None:
    spec = make_spec()
    ctx = make_context(
        usage_bindings={
            "U1": ok_binding("U1"),
            "U2": ok_binding("U2", element_type="RequirementUsage"),
        }
    )
    evaluation = evaluate([spec], ctx)
    failing = [r for r in evaluation.results if r.subject_id == "U2"][0]
    assert failing.state == "ERROR"
    assert failing.reason_codes == ("BINDING_MISMATCH",)


# ---------------------------------------------------------------------------
# MC-07: explicit supported non-applicability / permitted-empty
# ---------------------------------------------------------------------------


def test_mc07_explicit_non_applicability() -> None:
    spec = make_spec(
        applicability="candidate revision declares the INC-X pilot scope",
        applicability_kind="candidate-declares-scope",
    )
    ctx = make_context(pilot_scope_declared=False)
    evaluation = evaluate([spec], ctx)
    result = evaluation.results[0]
    assert result.state == "COMPLETE"
    assert result.verdict == "NOT_APPLICABLE"
    assert result.reason_codes == ("NOT_APPLICABLE_REASON",)
    assert "EXPLICIT_DISPOSITION" in result.diagnostics


def test_mc07_permitted_empty_disposition() -> None:
    spec = make_spec(
        subject_selector="scope usages",
        selector_kind=me.SELECTOR_SCOPE_USAGES,
        permitted_empty=True,
        permitted_empty_disposition="NO_ELIGIBLE_SUBJECTS",
    )
    ctx = make_context(scope=make_scope(usage_ids=()), usage_bindings={})
    evaluation = evaluate([spec], ctx)
    result = evaluation.results[0]
    assert result.verdict == "NOT_APPLICABLE"
    assert "NO_ELIGIBLE_SUBJECTS" in result.diagnostics


# ---------------------------------------------------------------------------
# MC-08: unknown applicability / missing input -> INDETERMINATE, no pass
# ---------------------------------------------------------------------------


def test_mc08_unresolved_applicability_is_indeterminate() -> None:
    spec = make_spec(
        applicability="candidate revision declares the INC-X pilot scope",
        applicability_kind="candidate-declares-scope",
    )
    ctx = make_context(pilot_scope_declared=None, candidate_missing_inputs=("scope record",))
    evaluation = evaluate([spec], ctx)
    result = evaluation.results[0]
    assert result.state == "INDETERMINATE"
    assert result.verdict is None
    assert result.reason_codes == ("APPLICABILITY_UNRESOLVED",)
    assert result.missing == ("scope record",)


def test_mc08_absent_record_storage_is_indeterminate_not_empty() -> None:
    spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    ctx = make_context(
        campaign_manifest=manifest(profiles=("p1",)),
        scope=make_scope(profiles=("p1",)),
        artifact_source=None,  # retained storage not bound
    )
    evaluation = evaluate([spec], ctx)
    result = evaluation.results[0]
    assert result.state == "INDETERMINATE"
    assert result.reason_codes == ("INPUT_UNAVAILABLE",)


# ---------------------------------------------------------------------------
# MC-09 / MC-27: contract errors before normative evaluation
# ---------------------------------------------------------------------------


def test_mc09_duplicate_obligation_ids_rejected() -> None:
    specs = [make_spec(obligation_id="OB-1"), make_spec(obligation_id="OB-1")]
    with pytest.raises(me.ContractValidationError, match="duplicate"):
        me.validate_contract(make_contract(specs))


def test_mc09_unknown_predicate_rejected() -> None:
    with pytest.raises(me.ContractValidationError, match="unknown predicate"):
        me.validate_contract(make_contract([make_spec(predicate="made-up-predicate")]))


def test_mc09_invalid_cardinality_rejected() -> None:
    with pytest.raises(me.ContractValidationError, match="cardinality"):
        me.validate_contract(make_contract([make_spec(cardinality=(3, 1))]))


def test_mc09_unresolved_policy_reference_rejected() -> None:
    with pytest.raises(me.ContractValidationError, match="policy"):
        me.validate_contract(
            make_contract([make_spec(attestation_policy_ref="de4sdv.unknown.policy")])
        )


def test_mc09_unsupported_applicability_form_rejected() -> None:
    with pytest.raises(me.ContractValidationError, match="applicability"):
        me.validate_contract(
            make_contract([make_spec(applicability_kind="free-text-condition")])
        )


def test_mc09_live_delivery_source_rejected_deterministically() -> None:
    with pytest.raises(me.ContractValidationError, match="live-delivery"):
        me.validate_contract(
            make_contract([make_spec(evaluation_source="live-delivery-adapter")])
        )


def test_mc27_blocking_prerequisite_cycle_rejected() -> None:
    specs = [
        make_spec(obligation_id="OB-A", depends_on=("OB-B",)),
        make_spec(obligation_id="OB-B", depends_on=("OB-A",)),
    ]
    with pytest.raises(me.ContractValidationError, match="cycle"):
        me.validate_contract(make_contract(specs))


def test_mc27_non_cyclic_prerequisite_chain_allowed() -> None:
    specs = [
        make_spec(obligation_id="OB-A"),
        make_spec(obligation_id="OB-B", depends_on=("OB-A",)),
    ]
    me.validate_contract(make_contract(specs))  # must not raise


# ---------------------------------------------------------------------------
# MC-11: mismatched identities refuse the evaluation
# ---------------------------------------------------------------------------


def test_mc11_manifest_identity_mismatch_refuses() -> None:
    expected = {
        "git_commit": "a" * 40,
        "sysml_project_id": "proj-1",
        "sysml_commit_id": "commit-1",
        "contract_digest": "d" * 64,
        "evaluator_build": me.EVALUATOR_BUILD_ID,
        "policy_bundle_id": "de4sdv.acceptance.maintainer-decision.v1",
    }
    me.verify_manifest_identity(expected, dict(expected))  # equal -> no raise
    for key in expected:
        diverged = dict(expected)
        diverged[key] = "different"
        with pytest.raises(me.ManifestMismatchError, match=key):
            me.verify_manifest_identity(expected, diverged)


# ---------------------------------------------------------------------------
# MC-12 / MC-13: canonical determinism and identity sensitivity
# ---------------------------------------------------------------------------


def test_mc12_same_semantic_inputs_same_payload_despite_order() -> None:
    spec = make_spec()
    binding = {"U1": ok_binding("U1"), "U2": ok_binding("U2")}
    base = make_context(usage_bindings=binding)
    shuffled_elements = [{"@id": f"e{i}", "@type": "PartUsage"} for i in range(5)]
    reversed_elements = list(reversed(shuffled_elements))
    first = evaluate(
        [spec], make_context(usage_bindings=binding, elements=tuple(shuffled_elements))
    )
    second = evaluate(
        [spec], make_context(usage_bindings=binding, elements=tuple(reversed_elements))
    )
    assert first.evaluation_key == second.evaluation_key
    assert json.dumps(first.increment_status(), sort_keys=True) == json.dumps(
        second.increment_status(), sort_keys=True
    )
    # The base context with no elements produces the same canonical payload for
    # the same semantic inputs as well (enumeration-order independence).
    third = evaluate([spec], base)
    assert third.evaluation_key == first.evaluation_key


def test_mc13_changed_scope_or_config_changes_identity() -> None:
    spec = make_spec()
    ctx = make_context(usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")})
    baseline = evaluate([spec], ctx)
    changed_scope = make_context(
        usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")},
        scope=make_scope(usage_ids=("U1",)),
    )
    assert evaluate([spec], changed_scope).evaluation_key != baseline.evaluation_key
    # Meaningful ordered-collection change (declared profile order).
    reordered = make_context(
        usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")},
        scope=make_scope(profiles=("p2", "p1")),
    )
    assert evaluate([spec], reordered).evaluation_key != baseline.evaluation_key


# ---------------------------------------------------------------------------
# MC-15: accepted evidence recording a failed execution
# ---------------------------------------------------------------------------


def _record_context(tmp_path: Path, *, record_mutator=None, **overrides):
    """Build an evidence-branch context with a digest-consistent record file.

    ``record_mutator`` mutates the record BEFORE it is written, so the file
    digest stays consistent with the manifest entry.
    """
    record = {
        "profile": "p1",
        "evaluation": {"passed": True, "disposition": "expected_disposition"},
        "provenance": {"repository_head": "b" * 40},
    }
    if record_mutator is not None:
        record_mutator(record)
    import hashlib

    workspace = tmp_path / "workspace"
    record_path = workspace / mp.BENCH_ROOT / "evidence" / "p1.json"
    record_path.parent.mkdir(parents=True, exist_ok=True)
    record_path.write_text(json.dumps(record))
    digest = hashlib.sha256(record_path.read_bytes()).hexdigest()
    record_manifest = manifest(profiles=("p1",))
    record_manifest["profiles"]["p1"]["sha256"] = digest
    values = dict(
        campaign_manifest=record_manifest,
        scope=make_scope(profiles=("p1",)),
        records={"p1": record},
        expected_dispositions={"p1": "expected_disposition"},
        artifact_source=mp.DirectoryFileSource(workspace),
        bench_root=mp.BENCH_ROOT,
    )
    values.update(overrides)
    return make_context(**values)


def test_mc15_failed_execution_fails_passing_outcome_obligation(tmp_path: Path) -> None:
    spec = make_spec(
        obligation_id="OB-OUT",
        predicate="execution-outcome",
        subject_selector="canonical records",
        selector_kind=me.SELECTOR_UPSTREAM,
        upstream_obligation_id="OB-REC",
        depends_on=("OB-REC",),
    )
    record_spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    # The record passed but with the wrong disposition literal (a failed
    # observation relative to the pinned expectation).
    ctx = _record_context(
        tmp_path,
        record_mutator=lambda record: record.update(
            {"evaluation": {"passed": True, "disposition": "something_else"}}
        ),
    )
    evaluation = evaluate([record_spec, spec], ctx)
    outcome = unit(evaluation, "OB-OUT")
    assert outcome.verdict == "FAIL"
    assert outcome.reason_codes == ("EXECUTION_FAILED",)


def test_mc15_failed_execution_does_not_block_acceptance_observation(tmp_path: Path) -> None:
    # A failed execution may still be validly accepted as an observation: the
    # acceptance obligation evaluates independently (no cross edges).
    record_spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    outcome_spec = make_spec(
        obligation_id="OB-OUT",
        predicate="execution-outcome",
        subject_selector="canonical records",
        selector_kind=me.SELECTOR_UPSTREAM,
        upstream_obligation_id="OB-REC",
        depends_on=("OB-REC",),
    )
    acceptance_spec = make_spec(
        obligation_id="OB-ACC",
        predicate="acceptance-record-match",
        subject_selector="canonical records",
        selector_kind=me.SELECTOR_UPSTREAM,
        upstream_obligation_id="OB-REC",
        depends_on=("OB-REC",),
        attestation_policy_ref="de4sdv.acceptance.maintainer-decision.v1",
    )
    ctx = _record_context(
        tmp_path,
        record_mutator=lambda record: record.update(
            {"evaluation": {"passed": False, "disposition": "expected_disposition"}}
        ),
        registry_scan=me.RegistryScan(
            path="docs/acceptance-decisions",
            state="scanned-clean",
            decisions=(
                {
                    "decision_id": "DEC-1",
                    "outcome": "accepted",
                    "covered_profiles": ("p1",),
                    "decider": "maintainer",
                },
            ),
        )
    )
    evaluation = evaluate([record_spec, outcome_spec, acceptance_spec], ctx)
    assert unit(evaluation, "OB-OUT").verdict == "FAIL"
    assert unit(evaluation, "OB-ACC").verdict == "PASS"  # acceptance evaluated


# ---------------------------------------------------------------------------
# MC-16: accepted claim without attributable authority
# ---------------------------------------------------------------------------


def test_mc16_accepted_without_decision_never_passes(tmp_path: Path) -> None:
    record_spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    acceptance_spec = make_spec(
        obligation_id="OB-ACC",
        predicate="acceptance-record-match",
        subject_selector="canonical records",
        selector_kind=me.SELECTOR_UPSTREAM,
        upstream_obligation_id="OB-REC",
        depends_on=("OB-REC",),
        attestation_policy_ref="de4sdv.acceptance.maintainer-decision.v1",
    )
    ctx = _record_context(
        tmp_path,
        registry_scan=me.RegistryScan(
            path="docs/acceptance-decisions", state="scanned-clean", decisions=()
        )
    )
    evaluation = evaluate([record_spec, acceptance_spec], ctx)
    outcome = unit(evaluation, "OB-ACC")
    assert outcome.verdict == "FAIL"
    assert outcome.reason_codes == ("ACCEPTANCE_AUTHORITY_MISSING",)


def test_mc16_schema_invalid_registry_record_is_error(tmp_path: Path) -> None:
    record_spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    acceptance_spec = make_spec(
        obligation_id="OB-ACC",
        predicate="acceptance-record-match",
        subject_selector="canonical records",
        selector_kind=me.SELECTOR_UPSTREAM,
        upstream_obligation_id="OB-REC",
        depends_on=("OB-REC",),
        attestation_policy_ref="de4sdv.acceptance.maintainer-decision.v1",
    )
    ctx = _record_context(
        tmp_path,
        registry_scan=me.RegistryScan(
            path="docs/acceptance-decisions",
            state="invalid-record",
            diagnostics=("registry entry 'x.yaml': invalid decision outcome 'maybe'",),
        )
    )
    evaluation = evaluate([record_spec, acceptance_spec], ctx)
    outcome = unit(evaluation, "OB-ACC")
    assert outcome.state == "ERROR"
    assert outcome.reason_codes == ("BINDING_MISMATCH",)


# ---------------------------------------------------------------------------
# MC-17 / MC-18 / MC-19: conservative scope equality
# ---------------------------------------------------------------------------


def test_mc17_scope_mismatch_fails_no_carry_forward(tmp_path: Path) -> None:
    record_spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    equality_spec = make_spec(
        obligation_id="OB-EQ",
        predicate="conservative-scope-equality",
        subject_selector="canonical records",
        selector_kind=me.SELECTOR_UPSTREAM,
        upstream_obligation_id="OB-REC",
        depends_on=("OB-REC",),
    )
    ctx = _record_context(
        tmp_path,
        scope_equality={
            "p1": me.ScopeEqualityComparison(
                status="mismatch",
                compared_fields=("execution_manifest_sha256",),
                mismatched_fields=("execution_manifest_sha256",),
                diagnostics=("input changed since the tested head",),
            )
        }
    )
    evaluation = evaluate([record_spec, equality_spec], ctx)
    outcome = unit(evaluation, "OB-EQ")
    assert outcome.verdict == "FAIL"
    assert outcome.reason_codes == ("EVIDENCE_SCOPE_MISMATCH",)


def test_mc18_unestablishable_boundary_is_indeterminate(tmp_path: Path) -> None:
    record_spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    equality_spec = make_spec(
        obligation_id="OB-EQ",
        predicate="conservative-scope-equality",
        subject_selector="canonical records",
        selector_kind=me.SELECTOR_UPSTREAM,
        upstream_obligation_id="OB-REC",
        depends_on=("OB-REC",),
    )
    ctx = _record_context(
        tmp_path,
        scope_equality={
            "p1": me.ScopeEqualityComparison(
                status="indeterminate",
                compared_fields=(),
                missing_fields=("host_arch",),
            )
        }
    )
    evaluation = evaluate([record_spec, equality_spec], ctx)
    outcome = unit(evaluation, "OB-EQ")
    assert outcome.state == "INDETERMINATE"
    assert outcome.reason_codes == ("INPUT_UNAVAILABLE",)
    assert "host_arch" in outcome.missing


def test_mc18_no_comparison_values_is_indeterminate(tmp_path: Path) -> None:
    record_spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    equality_spec = make_spec(
        obligation_id="OB-EQ",
        predicate="conservative-scope-equality",
        subject_selector="canonical records",
        selector_kind=me.SELECTOR_UPSTREAM,
        upstream_obligation_id="OB-REC",
        depends_on=("OB-REC",),
    )
    ctx = _record_context(tmp_path, scope_equality={})
    evaluation = evaluate([record_spec, equality_spec], ctx)
    assert unit(evaluation, "OB-EQ").state == "INDETERMINATE"


def test_mc19_evidence_committed_after_execution_has_no_self_sha_requirement(tmp_path: Path) -> None:
    # The record was produced at head H; the candidate revision is a LATER
    # commit. Equality is established over scope identity, and nothing demands
    # the evidence commit contain its own hash.
    record_spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    equality_spec = make_spec(
        obligation_id="OB-EQ",
        predicate="conservative-scope-equality",
        subject_selector="canonical records",
        selector_kind=me.SELECTOR_UPSTREAM,
        upstream_obligation_id="OB-REC",
        depends_on=("OB-REC",),
    )
    ctx = _record_context(
        tmp_path,
        scope_equality={
            "p1": me.ScopeEqualityComparison(
                status="equal",
                compared_fields=me_method_scope_fields(),
            )
        }
    )
    evaluation = evaluate([record_spec, equality_spec], ctx)
    assert unit(evaluation, "OB-EQ").verdict == "PASS"
    assert evaluation.evaluation_state == "COMPLETE"


def me_method_scope_fields() -> tuple:
    return (
        "repository_head",
        "override_matrix_sha256",
        "override_execution_manifest_sha256",
        "execution_manifest_sha256",
        "runtime_lock_sha256",
        "inherited_009a.execution_manifest_sha256",
        "inherited_009a.runtime_lock_sha256",
        "image_digest",
        "map_digest",
        "host_arch",
    )


# ---------------------------------------------------------------------------
# MC-20: conflicting acceptance without supersession stays unresolved
# ---------------------------------------------------------------------------


def _decision_file(
    directory: Path,
    decision_id: str,
    outcome: str,
    covered=("p1",),
    supersedes=(),
) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    body = {
        "schema": "de4sdv.acceptance-decision.v1",
        "policy_id": "de4sdv.acceptance.maintainer-decision.v1",
        "decision_id": decision_id,
        "campaign_scope": "INC-X @ " + "b" * 40,
        "covered_profiles": list(covered),
        "outcome": outcome,
        "decider": "maintainer",
        "decision_date": "2026-09-01",
    }
    if supersedes:
        body["supersedes"] = list(supersedes)
    import yaml

    (directory / f"{decision_id}.yaml").write_text(yaml.safe_dump(body, sort_keys=True))


def _acceptance_specs():
    record_spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    acceptance_spec = make_spec(
        obligation_id="OB-ACC",
        predicate="acceptance-record-match",
        subject_selector="canonical records",
        selector_kind=me.SELECTOR_UPSTREAM,
        upstream_obligation_id="OB-REC",
        depends_on=("OB-REC",),
        attestation_policy_ref="de4sdv.acceptance.maintainer-decision.v1",
    )
    return [record_spec, acceptance_spec]


def test_mc20_conflicting_decisions_unresolved_without_timestamp_winner(tmp_path: Path) -> None:
    ctx = _record_context(tmp_path)
    registry = tmp_path / "workspace" / mp.REGISTRY_PATH
    _decision_file(registry, "DEC-A", "accepted")
    _decision_file(registry, "DEC-B", "rejected")
    ctx.registry_scan = mp.scan_acceptance_registry(
        mp.DirectoryFileSource(tmp_path / "workspace")
    )
    evaluation = evaluate(_acceptance_specs(), ctx)
    outcome = unit(evaluation, "OB-ACC")
    assert outcome.state == "INDETERMINATE"
    assert outcome.reason_codes == ("ACCEPTANCE_AUTHORITY_MISSING",)
    assert "DEC-A" in " ".join(outcome.diagnostics)


def test_mc20_supersession_resolves_conflict(tmp_path: Path) -> None:
    ctx = _record_context(tmp_path)
    registry = tmp_path / "workspace" / mp.REGISTRY_PATH
    _decision_file(registry, "DEC-A", "accepted")
    _decision_file(registry, "DEC-B", "rejected", supersedes=("DEC-A",))
    scan = mp.scan_acceptance_registry(mp.DirectoryFileSource(tmp_path / "workspace"))
    assert scan.state == "scanned-clean"
    ctx.registry_scan = scan
    evaluation = evaluate(_acceptance_specs(), ctx)
    assert unit(evaluation, "OB-ACC").verdict == "FAIL"  # superseding rejection wins

    workspace2 = tmp_path / "workspace2"
    ctx2 = _record_context(workspace2)
    registry2 = workspace2 / mp.REGISTRY_PATH
    _decision_file(registry2, "DEC-A", "accepted", supersedes=("DEC-B",))
    _decision_file(registry2, "DEC-B", "rejected")
    ctx2.registry_scan = mp.scan_acceptance_registry(mp.DirectoryFileSource(workspace2))
    evaluation2 = evaluate(_acceptance_specs(), ctx2)
    assert unit(evaluation2, "OB-ACC").verdict == "PASS"


def test_mc20_supersession_cycle_is_error(tmp_path: Path) -> None:
    workspace = tmp_path / "workspace"
    ctx = _record_context(workspace)
    registry = workspace / mp.REGISTRY_PATH
    _decision_file(registry, "DEC-A", "accepted", supersedes=("DEC-B",))
    _decision_file(registry, "DEC-B", "rejected", supersedes=("DEC-A",))
    scan = mp.scan_acceptance_registry(mp.DirectoryFileSource(workspace))
    assert scan.state == "invalid-record"
    assert any("cycle" in d for d in scan.diagnostics)
    ctx.registry_scan = scan
    evaluation = evaluate(_acceptance_specs(), ctx)
    outcome = unit(evaluation, "OB-ACC")
    assert outcome.state == "ERROR"
    assert outcome.reason_codes == ("BINDING_MISMATCH",)


# ---------------------------------------------------------------------------
# MC-23: candidate cannot weaken its own governing rules
# ---------------------------------------------------------------------------


def test_mc23_candidate_closure_divergence_is_a_migration_blocker() -> None:
    approved = make_contract(
        [make_spec(predicate="binding-resolution", cardinality=(1, 1), required=True)]
    )
    weakened = [
        {
            "obligationId": "OB-1",
            "predicate": "binding-resolution",
            "cardinalityMinimum": "1",
            "cardinalityMaximum": "99",  # weakened bounds
            "required": "false",  # weakened requirement
            "attestationPolicyRef": "",
        }
    ]
    mismatches = me.verify_candidate_policy_closure(approved, weakened)
    assert any("cardinalityMaximum" in m for m in mismatches)
    assert any("required" in m for m in mismatches)
    # A faithful encoding produces no mismatches.
    faithful = [
        {
            "obligationId": "OB-1",
            "predicate": "binding-resolution",
            "cardinalityMinimum": "1",
            "cardinalityMaximum": "1",
            "required": "true",
            "attestationPolicyRef": "",
        }
    ]
    assert me.verify_candidate_policy_closure(approved, faithful) == []


def test_mc23_missing_candidate_obligations_block() -> None:
    approved = make_contract([make_spec()])
    mismatches = me.verify_candidate_policy_closure(approved, [])
    assert any("missing approved obligations" in m for m in mismatches)


# ---------------------------------------------------------------------------
# MC-26: memory/claims do not change the result
# ---------------------------------------------------------------------------


def test_mc26_external_claims_do_not_change_results(tmp_path: Path) -> None:
    spec = make_spec(
        obligation_id="OB-REC",
        predicate="external-evidence-reference",
        subject_selector="declared profiles",
        selector_kind=me.SELECTOR_PROFILE_SET,
    )
    base = _record_context(tmp_path)
    claims_dir = tmp_path / "workspace" / "docs" / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    (claims_dir / "evidence-exists.md").write_text(
        "A memory says evidence exists for p1."
    )
    before = evaluate([spec], base)
    # A Hindsight-style claim appears; declared sources are unchanged.
    (claims_dir / "evidence-exists.md").write_text(
        "A memory strongly insists the evidence was accepted."
    )
    after = evaluate([spec], base)
    assert before.evaluation_key == after.evaluation_key
    assert json.dumps(before.increment_status(), sort_keys=True) == json.dumps(
        after.increment_status(), sort_keys=True
    )


# ---------------------------------------------------------------------------
# MC-29: all-not-applicable aggregate vs no executable contract
# ---------------------------------------------------------------------------


def test_mc29_all_not_applicable_aggregate() -> None:
    spec = make_spec(
        applicability="candidate revision declares the INC-X pilot scope",
        applicability_kind="candidate-declares-scope",
    )
    ctx = make_context(pilot_scope_declared=False)
    evaluation = evaluate([spec], ctx)
    assert evaluation.assessment_coverage == "ASSESSED"
    assert evaluation.evaluation_state == "COMPLETE"
    assert evaluation.conformance_verdict == "NOT_APPLICABLE"
    assert evaluation.conformance_verdict != "PASS"


def test_mc29_no_executable_contract_is_unassessed() -> None:
    selection = me.ApprovedMethodSelection(
        method_id="de4sdv.test-method",
        contract_id="TEST",
        policy_bundle_id="",
        source="test",
        contracts={},
    )
    service = me.MethodConformanceService(selection)
    response = service.increment_status("phase10_vvEvidence")
    assert response["assessment_coverage"] == "UNASSESSED"
    assert response["evaluation_state"] is None
    assert response["conformance_verdict"] is None
    assert response["reason_codes"] == ["CONTRACT_UNAVAILABLE"]


# ---------------------------------------------------------------------------
# MC-31: unmerged candidate evaluation, merge not required
# ---------------------------------------------------------------------------


def test_mc31_candidate_revision_evaluated_without_merge() -> None:
    spec = make_spec()
    ctx = make_context(usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")})
    assert ctx.revision.scope == "candidate"
    evaluation = evaluate([spec], ctx)
    assert evaluation.revision_identity["git_commit"] == "a" * 40
    assert evaluation.revision_identity["scope"] == "candidate"
    # The evaluation binds the exact candidate commit in its identity.
    other = make_context(
        usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")},
        revision=me.RevisionIdentity(
            git_commit="b" * 40,
            sysml_project_id="proj-1",
            sysml_commit_id="commit-1",
            scope="candidate",
        ),
    )
    assert evaluate([spec], other).evaluation_key != evaluation.evaluation_key


# ---------------------------------------------------------------------------
# MC-33: non-Phase-10 contract through the same engine (no phase branches)
# ---------------------------------------------------------------------------


def test_mc33_non_phase10_contract_same_engine() -> None:
    spec = make_spec(
        obligation_id="OB-FUNC",
        phase="phase6_functionalArchitecture",
        predicate="binding-resolution",
    )
    ctx = make_context(
        usage_bindings={
            "U1": ok_binding("U1"),
            "U2": ok_binding("U2"),
        }
    )
    evaluation = evaluate([spec], ctx)
    assert evaluation.method_identity["phase"] == "phase6_functionalArchitecture"
    assert evaluation.conformance_verdict == "PASS"
    # The phase literal alters no semantics: the same engine produced both.
    assert evaluation.evaluation_key


def test_mc33_evaluator_source_has_no_phase_branches() -> None:
    evaluator_source = (
        ROOT / "de4sdv" / "semantic" / "method_evaluator.py"
    ).read_text(encoding="utf-8")
    pilot_source = (ROOT / "de4sdv" / "semantic" / "method_pilot.py").read_text(
        encoding="utf-8"
    )
    for source in (evaluator_source, pilot_source):
        assert "phase10" not in source
        assert "phase == " not in source
        assert 'phase =="' not in source


# ---------------------------------------------------------------------------
# MC-34 / MC-35: candidate-independent discovery
# ---------------------------------------------------------------------------


def _pilot_selection() -> me.ApprovedMethodSelection:
    contract = mp.load_approved_contract_from_yaml(
        ROOT / "docs" / "method-conformance" / "pilot-obligations.yaml"
    )
    return me.ApprovedMethodSelection(
        method_id=contract.method_id,
        contract_id=contract.contract_id,
        policy_bundle_id=contract.policy_bundle_id,
        source="docs/method-conformance/pilot-obligations.yaml (approved)",
        contracts={contract.phase: contract},
    )


def test_mc34_phase_without_contract_reports_contract_unavailable() -> None:
    selection = _pilot_selection()
    response = selection.phase_contract("phase11_publication")
    assert response["executable_contract_available"] is False
    assert response["reason_codes"] == ["CONTRACT_UNAVAILABLE"]
    assert response["obligations"] == []
    # Broader exit readiness stays blocked for the unavailable contract.
    service = me.MethodConformanceService(selection)
    status = service.increment_status(
        "phase11_publication",
        None,
        requested_readiness=[me.ReadinessTarget("PHASE_EXIT", "INC-1/phase11")],
    )
    assert status["readiness"][0]["readiness"] == "BLOCKED"
    assert status["readiness"][0]["reason_codes"] == ["CONTRACT_UNAVAILABLE"]


def test_mc35_phase_contract_method_only_provenance() -> None:
    selection = _pilot_selection()
    response = selection.phase_contract("phase10_vvEvidence")
    assert response["executable_contract_available"] is True
    assert len(response["obligations"]) == 11
    # No fabricated candidate binding, no evaluation fields, no verdict.
    serialized = json.dumps(response)
    assert "git_commit" not in serialized
    assert "sysml_project" not in serialized
    for forbidden in (
        "conformance_verdict",
        "evaluation_state",
        "assessment_coverage",
        "readiness",
    ):
        assert forbidden not in response


def test_mc35_candidate_context_never_hides_obligations() -> None:
    selection = _pilot_selection()
    hostile_context = {
        "pilot_scope_declared": None,
        "missing_inputs": ("scope record", "candidate revision"),
    }
    response = selection.phase_contract("phase10_vvEvidence", hostile_context)
    assert len(response["obligations"]) == 11  # nothing disappeared
    unresolved = [
        o
        for o in response["obligations"]
        if o.get("applicability_resolution") == "unresolved"
    ]
    assert unresolved, "unresolved applicability must remain visible"
    assert all("conformance_verdict" not in o for o in response["obligations"])


# ---------------------------------------------------------------------------
# MC-38: illegal result combinations and readiness targets
# ---------------------------------------------------------------------------


def test_mc38_illegal_results_rejected() -> None:
    cases = [
        # PASS with reason codes
        me.EvaluationResult("U", "ASSESSED", "COMPLETE", "PASS", ("INPUT_UNAVAILABLE",)),
        # INDETERMINATE with a verdict
        me.EvaluationResult("U", "ASSESSED", "INDETERMINATE", "FAIL", ("INPUT_UNAVAILABLE",)),
        # UNASSESSED with a verdict
        me.EvaluationResult("U", "UNASSESSED", None, "PASS", ("NOT_ATTEMPTED",)),
        # FAIL with forbidden CONTRACT_UNAVAILABLE
        me.EvaluationResult("U", "ASSESSED", "COMPLETE", "FAIL", ("CONTRACT_UNAVAILABLE",)),
        # ERROR with forbidden INPUT_UNAVAILABLE
        me.EvaluationResult("U", "ASSESSED", "ERROR", None, ("INPUT_UNAVAILABLE",)),
        # UNASSESSED with forbidden STALE_INPUT
        me.EvaluationResult("U", "UNASSESSED", None, None, ("STALE_INPUT",)),
        # INDETERMINATE without required reason content
        me.EvaluationResult("U", "ASSESSED", "INDETERMINATE", None, ()),
        # NOT_APPLICABLE without sub-code diagnostic
        me.EvaluationResult(
            "U", "ASSESSED", "COMPLETE", "NOT_APPLICABLE", ("NOT_APPLICABLE_REASON",)
        ),
    ]
    for result in cases:
        with pytest.raises(me.ResultValidationError):
            result.validate()
    legal = me.EvaluationResult(
        "U", "ASSESSED", "COMPLETE", "NOT_APPLICABLE", ("NOT_APPLICABLE_REASON",),
        ("EXPLICIT_DISPOSITION",),
    )
    legal.validate()


def test_mc38_readiness_always_names_its_target() -> None:
    spec = make_spec()
    ctx = make_context(usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")})
    evaluation = evaluate(
        [spec], ctx, requested_readiness=[me.ReadinessTarget("PHASE_EXIT", "exit-1")]
    )
    for block in evaluation.readiness:
        assert block.target.target_id == "exit-1"
        assert block.as_dict()["readiness_target"]["id"] == "exit-1"
    with pytest.raises(ValueError, match="delivery projection"):
        evaluate([spec], ctx, requested_readiness=[me.ReadinessTarget("PR_MERGE", "pr-1")])


# ---------------------------------------------------------------------------
# MC-39: phase-exit blocked while corrective task entry is ready
# ---------------------------------------------------------------------------


def test_mc39_corrective_task_entry_ready_while_exit_blocked() -> None:
    spec = make_spec()
    ctx = make_context(
        usage_bindings={"U1": ok_binding("U1")},  # U2 missing -> reference error
        task_entry_prerequisites={"corrective-task-1": {"candidate revision": True}},
    )
    evaluation = evaluate(
        [spec],
        ctx,
        requested_readiness=[
            me.ReadinessTarget("PHASE_EXIT", "exit-1"),
            me.ReadinessTarget("TASK_ENTRY", "corrective-task-1"),
        ],
    )
    blocks = {b.target.target_type: b for b in evaluation.readiness}
    assert blocks["PHASE_EXIT"].readiness == "BLOCKED"
    assert blocks["TASK_ENTRY"].readiness == "READY"


# ---------------------------------------------------------------------------
# MC-40: mixed attempted/unassessed children keep all results visible
# ---------------------------------------------------------------------------


def test_mc40_mixed_coverage_preserves_children_and_lists() -> None:
    passing = make_spec(obligation_id="OB-PASS")
    failing = make_spec(obligation_id="OB-FAIL")
    blocked = make_spec(obligation_id="OB-BLOCKED", depends_on=("OB-FAIL",))
    ctx = make_context(
        usage_bindings={
            "U1": ok_binding("U1"),
            "U2": ok_binding("U2", resolution_level="structural-match"),  # reference error
        }
    )
    evaluation = evaluate([passing, failing, blocked], ctx)
    # Aggregate: unassessed children keep coverage unassessed with null state.
    assert evaluation.assessment_coverage == "UNASSESSED"
    assert evaluation.evaluation_state is None
    assert evaluation.conformance_verdict is None
    assert "OB-BLOCKED" in evaluation.unassessed_ids
    # Known child failures stay visible.
    assert "OB-FAIL" in evaluation.errored_ids
    # method_gaps still surfaces the errored child and the not-attempted child.
    gaps = evaluation.method_gaps()
    assert any(r["unit_id"] == "OB-FAIL" for r in gaps["unresolved_inputs"])
    assert any(r["unit_id"] == "OB-BLOCKED" for r in gaps["unassessed"])
    # Phase-exit readiness is blocked for the broader scope.
    evaluation2 = evaluate(
        [passing, failing, blocked],
        ctx,
        requested_readiness=[me.ReadinessTarget("PHASE_EXIT", "exit-1")],
    )
    assert evaluation2.readiness[0].readiness == "BLOCKED"


def test_mc40_prerequisite_failure_marks_dependent_not_attempted() -> None:
    failing = make_spec(obligation_id="OB-FAIL")
    dependent = make_spec(obligation_id="OB-DEP", depends_on=("OB-FAIL",))
    ctx = make_context(
        usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2", element_type="X")}
    )
    evaluation = evaluate([failing, dependent], ctx)
    dependent_unit = unit(evaluation, "OB-DEP")
    assert dependent_unit.coverage == "UNASSESSED"
    assert dependent_unit.reason_codes == ("NOT_ATTEMPTED",)
    assert dependent_unit.verdict is None
    assert any("OB-FAIL" in d for d in dependent_unit.diagnostics)


# ---------------------------------------------------------------------------
# Aggregation precedence: ERROR > INDETERMINATE > COMPLETE
# ---------------------------------------------------------------------------


def test_child_aggregation_precedence() -> None:
    ok = make_spec(obligation_id="OB-OK")
    errored = make_spec(obligation_id="OB-ERR")
    indeterminate = make_spec(obligation_id="OB-IND")
    ctx = make_context(
        usage_bindings={
            "U1": ok_binding("U1"),
            "U2": ok_binding("U2", element_type="bad"),
        }
    )
    # All three subjects error on the same bindings; isolate by scope.
    evaluation = evaluate([ok], make_context(usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")}))
    assert evaluation.evaluation_state == "COMPLETE"
    evaluation_error = evaluate([errored], ctx)
    assert evaluation_error.evaluation_state == "ERROR"
    # Indeterminate wins over complete when no error is present.
    indeterminate_spec = make_spec(
        obligation_id="OB-IND2",
        applicability="scope condition",
        applicability_kind="candidate-declares-scope",
    )
    evaluation_ind = evaluate(
        [indeterminate_spec, ok],
        make_context(
            usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")},
            pilot_scope_declared=None,
        ),
    )
    assert evaluation_ind.evaluation_state == "INDETERMINATE"
    assert evaluation_ind.conformance_verdict is None
    # ERROR outranks INDETERMINATE.
    mixed = evaluate(
        [indeterminate_spec, errored],
        make_context(
            usage_bindings={
                "U1": ok_binding("U1"),
                "U2": ok_binding("U2", element_type="bad"),
            },
            pilot_scope_declared=None,
        ),
    )
    assert mixed.evaluation_state == "ERROR"


# ---------------------------------------------------------------------------
# Target filtering: non-qualifying targets rejected per subject
# ---------------------------------------------------------------------------


def test_target_filtering_rejects_wrong_element_type() -> None:
    spec = make_spec(
        obligation_id="OB-SCOPE",
        predicate="scope-composition",
        target_filters=("element type VerificationCaseUsage",),
        cardinality=(1, 1),
    )
    wrong = {"@id": "elem-U2", "@type": "RequirementUsage", "declaredName": "nope"}
    right = {"@id": "elem-U1", "@type": "VerificationCaseUsage", "declaredName": "ok"}
    ctx = make_context(
        elements=(wrong, right),
        usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")},
    )
    evaluation = evaluate([spec], ctx)
    result = evaluation.results[0]
    # Only elem-U1 qualifies; cardinality [1..1] holds over the filtered set.
    assert result.verdict == "PASS"
    assert result.targets == ("elem-U1",)


# ---------------------------------------------------------------------------
# Projection consistency: one canonical evaluation identity
# ---------------------------------------------------------------------------


def test_projections_share_one_evaluation_identity() -> None:
    contract = mp.load_approved_contract_from_yaml(
        ROOT / "docs" / "method-conformance" / "pilot-obligations.yaml"
    )
    selection = me.ApprovedMethodSelection(
        method_id=contract.method_id,
        contract_id=contract.contract_id,
        policy_bundle_id=contract.policy_bundle_id,
        source="test",
        contracts={contract.phase: contract},
    )
    service = me.MethodConformanceService(selection)
    # A minimal context that evaluates the contract with heavy indeterminacy:
    # the projections must still agree on one identity and one evaluation run.
    ctx = make_context(
        scope=make_scope(
            usage_ids=tuple(mp.PILOT_SCOPE_USAGES),
            profiles=mp.PILOT_PROFILES,
        ),
        pilot_scope_declared=None,
    )
    status = service.increment_status(contract.phase, ctx)
    gaps = service.method_gaps(contract.phase, ctx)
    nxt = service.next_obligation(contract.phase, ctx)
    assert service.evaluation_count == 1
    key = status["evaluation_key"]
    assert gaps["evaluation_key"] == key
    assert nxt["evaluation_key"] == key


# ---------------------------------------------------------------------------
# Pilot decode and witness-path fixtures
# ---------------------------------------------------------------------------


def test_approved_twin_decode_matches_frozen_contract() -> None:
    contract = mp.load_approved_contract_from_yaml(
        ROOT / "docs" / "method-conformance" / "pilot-obligations.yaml"
    )
    assert contract.phase == "phase10_vvEvidence"
    ids = [o.obligation_id for o in contract.obligations]
    assert len(ids) == 11
    assert len(set(ids)) == 11
    by_id = {o.obligation_id: o for o in contract.obligations}
    assert by_id["PC-009D-VC-BINDING"].cardinality == (1, 1)
    assert by_id["PC-009D-SCOPE-POPULATION"].cardinality == (6, 6)
    assert (
        by_id["PC-009D-ACCEPTANCE-AUTHORITY"].attestation_policy_ref
        == "de4sdv.acceptance.maintainer-decision.v1"
    )
    assert by_id["PC-009D-EXECUTION-OUTCOME"].depends_on == ("PC-009D-EXECUTION-RECORD",)


def test_unknown_selector_string_rejected_at_decode() -> None:
    twin = {
        "phase_literal": "phase10_vvEvidence",
        "obligations": [
            {
                "id": "OB-X",
                "subject_selector": "mystery subjects",
                "applicability": "(no applicability condition)",
                "evaluation_source": "pinned-model-record",
                "predicate": "binding-resolution",
                "per_subject_cardinality": [1, 1],
                "subjects": 1,
            }
        ],
    }
    with pytest.raises(ValueError, match="selector"):
        mp.decode_approved_contract(twin)


def test_objective_witness_path_returns_full_inherited_chain() -> None:
    elements = _objective_fixture()
    targets, witnesses, diagnostics = mp._objective_targets(
        elements,
        "usage-1",
        "def-1",
        {"req-1": "EC-009D-01", "req-2": "EC-009D-02", "req-3": "EC-009D-03"},
    )
    assert targets == ("req-1", "req-2", "req-3")
    assert len(witnesses) == 3  # one RequirementVerificationMembership per target
    assert diagnostics == []


def _objective_fixture() -> list[dict]:
    """Usage -> FeatureTyping -> definition -> objective -> RVM shadows."""
    elements: list[dict] = [
        {"@id": "usage-1", "@type": "VerificationCaseUsage", "declaredName": "u"},
        {"@id": "def-1", "@type": "VerificationCaseDefinition", "declaredName": "d"},
        {"@id": "obj-1", "@type": "RequirementUsage", "declaredName": "objective"},
    ]
    elements.append(
        {
            "@id": "ft-1",
            "@type": "FeatureTyping",
            "owningRelatedElement": {"@id": "usage-1"},
            "specific": {"@id": "usage-1"},
            "general": {"@id": "def-1"},
            "type": {"@id": "def-1"},
        }
    )
    elements.append(
        {
            "@id": "om-1",
            "@type": "ObjectiveMembership",
            "owningRelatedElement": {"@id": "def-1"},
            "memberElement": {"@id": "obj-1"},
        }
    )
    for index in (1, 2, 3):
        shadow = f"shadow-{index}"
        elements.append(
            {
                "@id": shadow,
                "@type": "RequirementUsage",
                "name": None,
                "ownedRelationship": [{"@id": f"rvs-{index}"}],
            }
        )
        elements.append(
            {
                "@id": f"rvs-{index}",
                "@type": "ReferenceSubsetting",
                "owningRelatedElement": {"@id": shadow},
                "specific": {"@id": shadow},
                "referencedFeature": {"@id": f"req-{index}"},
                "subsettedFeature": {"@id": f"req-{index}"},
            }
        )
        elements.append(
            {
                "@id": f"rvm-{index}",
                "@type": "RequirementVerificationMembership",
                "owningRelatedElement": {"@id": "obj-1"},
                "memberElement": {"@id": shadow},
            }
        )
        elements.append(
            {"@id": f"req-{index}", "@type": "RequirementUsage", "declaredShortName": f"EC-009D-0{index}"}
        )
    return elements


# ---------------------------------------------------------------------------
# Conservative scope equality mechanics over synthetic trees
# ---------------------------------------------------------------------------


def _write_bench_tree(root: Path) -> None:
    bench = root / mp.BENCH_ROOT
    (bench / "config").mkdir(parents=True)
    (bench / "scripts").mkdir()
    (bench / "src").mkdir()
    (bench / "workspace").mkdir()
    (bench / "runtime-lock.yaml").write_text(
        "container:\n  index_digest: sha256:abc\n  platform: linux/arm64\n"
        "map:\n  sha256: def\n"
        "inherited_009a:\n"
        "  execution_manifest_sha256: inherited-manifest\n"
        "  runtime_lock_sha256: inherited-lock\n"
    )
    (bench / "config" / "scenario-009d-conscious-override-matrix.yaml").write_text("matrix: v1\n")
    for name in (
        "compose.yaml",
        "cyclonedds.xml",
        "config/scenario-009b-moving-vehicle-target.yaml",
        "config/scenario-009d-moving-vehicle-target.yaml",
        "config/aebs-009b.param.yaml",
        "workspace/.gitkeep",
    ):
        path = bench / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("x\n")
    (bench / "scripts" / "run.sh").write_text("echo run\n")
    (bench / "src" / "bench.py").write_text("print('bench')\n")


def _scope_record(record_overrides=None) -> dict:
    provenance = {
        "repository_head": "b" * 40,
        "override_matrix_sha256": __import__("hashlib").sha256(b"matrix: v1\n").hexdigest(),
        "runtime_lock_sha256": "",
        "inherited_009a": {
            "execution_manifest_sha256": "inherited-manifest",
            "runtime_lock_sha256": "inherited-lock",
        },
        "image_digest": "sha256:abc",
        "map_digest": "sha256:def",
        "host_arch": "aarch64",
    }
    record = {"profile": "p1", "provenance": provenance}
    if record_overrides:
        record.update(record_overrides)
    return record


def _scope_equality(tmp_path: Path, mutate=None):
    tested = tmp_path / "tested"
    candidate = tmp_path / "candidate"
    _write_bench_tree(tested)
    _write_bench_tree(candidate)
    # The lock file hash and manifest values only match when the trees are
    # identical; derive the record from the tested tree.
    import hashlib

    lock_blob = (tested / mp.BENCH_ROOT / "runtime-lock.yaml").read_bytes()
    record = _scope_record()
    record["provenance"]["runtime_lock_sha256"] = hashlib.sha256(lock_blob).hexdigest()
    # Compute the tested input map and both manifests.
    tested_source = mp.DirectoryFileSource(tested)
    paths, _ = mp._claimed_input_paths(tested_source)
    input_map = {}
    for relative in paths:
        blob = tested_source.read_bytes(relative)
        if blob is not None:
            input_map[relative.replace(f"{mp.BENCH_ROOT}/", "")] = hashlib.sha256(blob).hexdigest()
    record["provenance"]["execution_manifest_sha256"] = mp.reconstruct_manifest_sha256(input_map)
    record["provenance"]["override_execution_manifest_sha256"] = mp.reconstruct_manifest_sha256(
        input_map, "p1"
    )
    if mutate:
        mutate(tested, candidate, record)
    return mp.compare_scope_equality(
        record=record,
        profile="p1",
        declared_execution_head="b" * 40,
        candidate_source=mp.DirectoryFileSource(candidate),
        tested_source=mp.DirectoryFileSource(tested),
    )


def test_scope_equality_equal_when_trees_match(tmp_path: Path) -> None:
    comparison = _scope_equality(tmp_path)
    assert comparison.status == "equal"
    assert set(mp.SCOPE_EQUALITY_FIELDS) <= set(comparison.compared_fields)


def test_scope_equality_mismatch_on_changed_input(tmp_path: Path) -> None:
    def mutate(tested: Path, candidate: Path, record: dict) -> None:
        (candidate / mp.BENCH_ROOT / "config" / "scenario-009d-moving-vehicle-target.yaml").write_text(
            "changed\n"
        )

    comparison = _scope_equality(tmp_path, mutate)
    assert comparison.status == "mismatch"
    assert "execution_manifest_sha256" in comparison.mismatched_fields
    assert any("scenario-009d-moving-vehicle-target" in d for d in comparison.diagnostics)


def test_scope_equality_mismatch_on_removed_input(tmp_path: Path) -> None:
    def mutate(tested: Path, candidate: Path, record: dict) -> None:
        (candidate / mp.BENCH_ROOT / "scripts" / "run.sh").unlink()

    comparison = _scope_equality(tmp_path, mutate)
    assert comparison.status == "mismatch"


def test_scope_equality_indeterminate_on_missing_record_field(tmp_path: Path) -> None:
    def mutate(tested: Path, candidate: Path, record: dict) -> None:
        del record["provenance"]["host_arch"]

    comparison = _scope_equality(tmp_path, mutate)
    assert comparison.status == "indeterminate"
    assert "host_arch" in comparison.missing_fields


def test_scope_equality_declared_head_field_compared(tmp_path: Path) -> None:
    def mutate(tested: Path, candidate: Path, record: dict) -> None:
        record["provenance"]["repository_head"] = "c" * 40

    comparison = _scope_equality(tmp_path, mutate)
    assert comparison.status == "mismatch"
    assert "repository_head" in comparison.mismatched_fields


# ---------------------------------------------------------------------------
# Declared tested-scope decode (feature-membership attribute chain)
# ---------------------------------------------------------------------------


def _attribute_chain(
    owner: dict, owner_prefix: str, member_name: str, value: str
) -> list[dict]:
    """Membership(memberName) -> attribute -> FeatureValue -> literal.

    The owner element is wired to own its membership, mirroring the real
    serializer shape (owner.ownedRelationship -> FeatureMembership).
    """
    owner_id = owner["@id"]
    membership_id = f"{owner_prefix}-m-{member_name}"
    attribute_id = f"{owner_prefix}-a-{member_name}"
    value_id = f"{owner_prefix}-v-{member_name}"
    owner.setdefault("ownedRelationship", []).append({"@id": membership_id})
    return [
        {
            "@id": membership_id,
            "@type": "FeatureMembership",
            "memberName": member_name,
            "owningRelatedElement": {"@id": owner_id},
            "memberElement": {"@id": attribute_id},
        },
        {
            "@id": attribute_id,
            "@type": "AttributeUsage",
            "ownedRelationship": [{"@id": f"{owner_prefix}-fv-{member_name}"}],
        },
        {
            "@id": f"{owner_prefix}-fv-{member_name}",
            "@type": "FeatureValue",
            "memberElement": {"@id": value_id},
        },
        {"@id": value_id, "@type": "LiteralString", "value": value},
    ]


def test_declared_tested_scope_decode() -> None:
    scope = {"@id": "scope-1", "@type": "ItemUsage", "declaredName": "testedScope"}
    elements = [scope] + _attribute_chain(scope, "scope", "executionHead", "b" * 40) + (
        _attribute_chain(scope, "scope", "profileIdentities", "p1, p2")
    )
    item, profiles, diagnostics = mp.decode_declared_tested_scope(elements)
    assert item is not None
    assert profiles == ("p1", "p2")
    assert diagnostics == []


def test_model_obligation_closure_decode_and_divergence() -> None:
    element = {"@id": "ob-1", "@type": "ItemUsage", "declaredName": "obligationA"}
    elements = (
        [element]
        + _attribute_chain(element, "ob", "obligationId", "OB-1")
        + _attribute_chain(element, "ob", "predicate", "binding-resolution")
        + _attribute_chain(element, "ob", "cardinalityMinimum", "1")
        + _attribute_chain(element, "ob", "cardinalityMaximum", "1")
        + _attribute_chain(element, "ob", "required", "true")
        + _attribute_chain(element, "ob", "attestationPolicyRef", "")
    )
    closure = mp.decode_model_obligation_closure(elements)
    assert closure == [
        {
            "obligationId": "OB-1",
            "predicate": "binding-resolution",
            "cardinalityMinimum": "1",
            "cardinalityMaximum": "1",
            "required": "true",
            "attestationPolicyRef": "",
        }
    ]
    approved = make_contract([make_spec(obligation_id="OB-1")])
    assert me.verify_candidate_policy_closure(approved, closure) == []
    closure[0]["cardinalityMaximum"] = "5"
    assert me.verify_candidate_policy_closure(approved, closure)


# ---------------------------------------------------------------------------
# Readiness: task-entry blocked without established prerequisites (honesty)
# ---------------------------------------------------------------------------


def test_task_entry_missing_prerequisites_blocks() -> None:
    spec = make_spec()
    ctx = make_context(usage_bindings={"U1": ok_binding("U1"), "U2": ok_binding("U2")})
    evaluation = evaluate(
        [spec],
        ctx,
        requested_readiness=[me.ReadinessTarget("TASK_ENTRY", "unknown-task")],
    )
    assert evaluation.readiness[0].readiness == "BLOCKED"
    assert evaluation.readiness[0].reason_codes == ("INPUT_UNAVAILABLE",)


# ---------------------------------------------------------------------------
# Query-service and MCP integration for the four C-owned surfaces
# ---------------------------------------------------------------------------


def _unused() -> Any:
    """Type-checked placeholder for fields the method surfaces never touch."""
    return cast(Any, None)


def _wired_query_service(context):
    from de4sdv.semantic.query import SemanticQueryService

    selection = _pilot_selection()
    service = me.MethodConformanceService(selection)
    return (
        SemanticQueryService(
            repository=_unused(),
            binding=_unused(),
            contract=_unused(),
            binder=_unused(),
            traversal=_unused(),
            impact_service=_unused(),
            expected_git_revision="a" * 40,
            method_conformance=service,
            method_context_provider=lambda: context,
        ),
        service,
        selection,
    )


def _pilot_phase() -> str:
    return "phase10_vvEvidence"


def _bare_context() -> me.EvaluationContext:
    return make_context(
        scope=make_scope(
            usage_ids=tuple(mp.PILOT_SCOPE_USAGES), profiles=mp.PILOT_PROFILES
        ),
        pilot_scope_declared=None,
    )


def test_query_service_method_surfaces_project_one_identity() -> None:
    query, service, _ = _wired_query_service(_bare_context())
    status = query.increment_status(_pilot_phase())
    gaps = query.method_gaps(_pilot_phase())
    nxt = query.next_obligation(_pilot_phase())
    contract_response = query.phase_contract(_pilot_phase())
    assert status["evaluation_key"] == gaps["evaluation_key"] == nxt["evaluation_key"]
    assert service.evaluation_count == 1
    assert contract_response["executable_contract_available"] is True
    assert len(contract_response["obligations"]) == 11


def test_query_service_refuses_unconfigured_method_queries() -> None:
    from de4sdv.semantic.query import SemanticQueryService

    bare = SemanticQueryService(
        repository=_unused(),
        binding=_unused(),
        contract=_unused(),
        binder=_unused(),
        traversal=_unused(),
        impact_service=_unused(),
        expected_git_revision="a" * 40,
    )
    with pytest.raises(RuntimeError, match="not configured"):
        bare.phase_contract(_pilot_phase())
    with pytest.raises(RuntimeError, match="not configured"):
        bare.increment_status(_pilot_phase())


def test_mcp_surface_exposes_c_owned_method_tools() -> None:
    import asyncio

    from de4sdv.semantic.mcp_server import create_mcp_server

    query, _, _ = _wired_query_service(_bare_context())
    server = create_mcp_server(query)
    tools = {tool.name for tool in server._tool_manager.list_tools()}
    assert {
        "phase_contract",
        "increment_status",
        "method_gaps",
        "next_obligation",
        "model_status",
        "resolve_element",
    } <= tools
    response = asyncio.run(
        server._tool_manager.call_tool(
            "phase_contract", {"phase": _pilot_phase()}
        )
    )
    assert response["executable_contract_available"] is True
    assert len(response["obligations"]) == 11
