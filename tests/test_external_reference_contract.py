"""External evidence-reference contract: fail-closed validation, no claim inflation."""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]


def _reference(**overrides):
    record = {
        "artifact_identity": "retained://middleware/run-2026-09-19T21-00Z",
        "digest": "A" * 64,
        "run": "run-34630102233",
        "tested_scope": ["INC-MW-010", "bench/mw-e014"],
    }
    record.update(overrides)
    return record


def _manifest(**overrides):
    manifest = {
        "baseline_identity": "baseline://mw-010/phase-12",
        "manifest_digest": {"algorithm": "sha256", "value": "b" * 64},
        "entries": ["retained://middleware/run-2026-09-19T21-00Z"],
    }
    manifest.update(overrides)
    return manifest


def test_valid_reference_normalizes_and_never_implies_pass():
    from de4sdv.semantic.external_reference_contract import validate_evidence_reference

    normalized = validate_evidence_reference(_reference())
    assert normalized["digest"] == {"algorithm": "sha256", "value": "a" * 64}
    assert normalized["implies_pass"] is False
    assert normalized["implies_acceptance"] is False


def test_missing_or_malformed_fields_fail_closed():
    from de4sdv.semantic.external_reference_contract import (
        EvidenceReferenceError, validate_evidence_reference,
    )

    for record in (
        _reference(artifact_identity=""),
        _reference(digest="not-a-digest"),
        _reference(run=""),
        _reference(tested_scope=[]),
        _reference(tested_scope=["ok", 7]),
        {},
    ):
        with pytest.raises(EvidenceReferenceError):
            validate_evidence_reference(record)


def test_baseline_inclusion_is_explicit_and_never_approves():
    from de4sdv.semantic.external_reference_contract import baseline_inclusion

    result = baseline_inclusion(_reference(), _manifest())
    assert result["included"] is True
    assert result["implies_approval"] is False
    assert result["implies_pass"] is False


def test_baseline_missing_entry_is_not_included_but_still_no_claim():
    from de4sdv.semantic.external_reference_contract import baseline_inclusion

    result = baseline_inclusion(_reference(artifact_identity="retained://other"), _manifest())
    assert result["included"] is False
    assert result["implies_approval"] is False


def test_baseline_manifest_requires_identity_and_entries():
    from de4sdv.semantic.external_reference_contract import (
        EvidenceReferenceError, validate_baseline_manifest,
    )

    with pytest.raises(EvidenceReferenceError):
        validate_baseline_manifest(_manifest(baseline_identity=""))
    with pytest.raises(EvidenceReferenceError):
        validate_baseline_manifest(_manifest(entries=[]))


def test_association_state_contains_no_verdict_fields():
    from de4sdv.semantic.external_reference_contract import association_state

    state = association_state(_reference())
    assert state["external_reference_validated"] is True
    assert state["implies_pass"] is False
    assert state["implies_acceptance"] is False
    forbidden = {"verdict", "passed", "accepted", "approval", "status"}
    assert not (forbidden & set(state))


def test_contract_never_fetches_content_and_stays_read_only():
    import inspect

    from de4sdv.semantic import external_reference_contract as module

    source = inspect.getsource(module)
    for banned in ("requests", "urllib", "http", "subprocess", "open("):
        assert banned not in source, f"contract must stay offline/read-only: {banned}"