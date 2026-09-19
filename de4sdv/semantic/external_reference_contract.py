"""External evidence-reference contract: fail-closed validation of supplied records.

Prepared machinery for the reviewed external-boundary rows ``EvidenceArtifact``,
``hasEvidence`` and ``capturedInBaseline``. The governed semantics are the
reviewed definitions: an evidence reference carries explicit artifact
identity, digest, run and tested scope; a baseline inclusion is explicit
membership in an identified immutable manifest. The contract validates
SUPPLIED records only:

* no network fetch, no content mirroring, no artifact byte claims;
* association, validity and inclusion never imply a pass, a verdict, or an
  acceptance — those flags are machine-locked ``False`` in every output;
* malformed, incomplete or foreign-shaped records fail closed.

Read-only; never imported by the runtime; grants no authority.
"""
from __future__ import annotations

import re
from typing import Any

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class EvidenceReferenceError(ValueError):
    """A supplied evidence reference or baseline manifest violates the contract."""


def _require_text(mapping: dict[str, Any], key: str, context: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise EvidenceReferenceError(f"{context}: {key} must be a non-empty string")
    return value


def normalize_digest(value: Any, context: str) -> dict[str, str]:
    """Normalize a digest to {algorithm: sha256, value: lowercase hex64}."""
    if isinstance(value, str):
        candidate = value.strip().lower()
        if not _SHA256.match(candidate):
            raise EvidenceReferenceError(f"{context}: digest must be a sha256 hex string")
        return {"algorithm": "sha256", "value": candidate}
    if isinstance(value, dict) and value.get("algorithm") == "sha256":
        candidate = str(value.get("value", "")).strip().lower()
        if not _SHA256.match(candidate):
            raise EvidenceReferenceError(f"{context}: digest.value must be a sha256 hex string")
        return {"algorithm": "sha256", "value": candidate}
    raise EvidenceReferenceError(
        f"{context}: digest must be a sha256 hex string or {{algorithm: sha256, value}}"
    )


def validate_evidence_reference(record: dict[str, Any]) -> dict[str, Any]:
    """Validate one supplied evidence reference; returns a normalized record."""
    if not isinstance(record, dict):
        raise EvidenceReferenceError("evidence reference must be a mapping")
    artifact_identity = _require_text(record, "artifact_identity", "reference")
    digest = normalize_digest(record.get("digest"), "reference")
    run = _require_text(record, "run", "reference")
    scope = record.get("tested_scope")
    if not isinstance(scope, list) or not scope or not all(
        isinstance(item, str) and item.strip() for item in scope
    ):
        raise EvidenceReferenceError(
            "reference: tested_scope must be a non-empty list of scope references"
        )
    return {
        "artifact_identity": artifact_identity,
        "digest": digest,
        "run": run,
        "tested_scope": sorted(item.strip() for item in scope),
        # Machine-locked: a validated reference implies nothing further.
        "implies_pass": False,
        "implies_acceptance": False,
    }


def validate_baseline_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    """Validate one supplied baseline manifest (identity + immutable entries)."""
    if not isinstance(manifest, dict):
        raise EvidenceReferenceError("baseline manifest must be a mapping")
    identity = _require_text(manifest, "baseline_identity", "baseline")
    digest = normalize_digest(manifest.get("manifest_digest"), "baseline")
    entries = manifest.get("entries")
    if not isinstance(entries, list) or not entries or not all(
        isinstance(item, str) and item.strip() for item in entries
    ):
        raise EvidenceReferenceError(
            "baseline: entries must be a non-empty list of artifact identities"
        )
    return {
        "baseline_identity": identity,
        "manifest_digest": digest,
        "entries": sorted(item.strip() for item in entries),
    }


def baseline_inclusion(reference: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    """Explicit baseline inclusion of a validated reference — never approval."""
    normalized_reference = validate_evidence_reference(reference)
    normalized_manifest = validate_baseline_manifest(manifest)
    included = normalized_reference["artifact_identity"] in set(normalized_manifest["entries"])
    return {
        "artifact_identity": normalized_reference["artifact_identity"],
        "baseline_identity": normalized_manifest["baseline_identity"],
        "included": included,
        # Machine-locked: inclusion does not approve evidence.
        "implies_approval": False,
        "implies_pass": False,
    }


def association_state(reference: dict[str, Any]) -> dict[str, Any]:
    """The only state an association may expose from a supplied reference."""
    normalized = validate_evidence_reference(reference)
    return {
        "external_reference_validated": True,
        "artifact_identity": normalized["artifact_identity"],
        "run": normalized["run"],
        "implies_pass": False,
        "implies_acceptance": False,
    }