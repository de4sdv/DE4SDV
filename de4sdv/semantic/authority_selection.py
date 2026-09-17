"""Explicit semantic-authority selection for the production surfaces (O3).

Production semantic authority is selected EXPLICITLY and never inferred:

    DE4SDV_SEMANTIC_AUTHORITY = legacy | o3          (default: legacy)

- ``legacy`` — the authored ``KernelContract`` path; query semantics are
  unchanged from the pre-O3 production behavior (only the provenance block
  reports the authority explicitly). This is the default: an unset (or
  empty) selector never activates anything.
- ``o3`` — exactly ONE accepted closed O3 authority bundle, identified by
  BOTH its deployment path and its exact bundle id:

      DE4SDV_O3_AUTHORITY_BUNDLE    = <path to the closed bundle JSON>
      DE4SDV_O3_AUTHORITY_BUNDLE_ID = o3b-<32 hex>

  The bundle is verified at STARTUP by the runtime assembly seam: schema,
  recomputed bundle id, exact Git revision, runtime build identity,
  Projection/Profile chain identities and digests, the exact validated
  revision binding (digest, SysML project/commit, ontology compatibility
  identity), the structured API closure attestation, the required validation
  evidence records, the VerificationCase grounding result, and the
  recomputed activation eligibility.

There is NO automatic "latest bundle" selection: a directory is never
scanned, a bundle is never discovered, and an incomplete or invalid O3
request is never resolved by guesswork. There is NO fallback from a
requested O3 bundle to legacy authority: any selection or verification
failure refuses the O3 runtime (fail closed) instead of silently serving
legacy answers.

The O3 authority bundle selected here is a DEPLOYMENT input, not a
governed-model content change: activation and rollback are selector
changes, and the selected authority id drives the provenance and the
authority-keyed cache/snapshot identities so answers computed under one
authority are never reused under the other.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from .authority_ids import LEGACY_AUTHORITY_ID
from .o3_bundle import O3_BUNDLE_SCHEMA, o3_authority_id

AUTHORITY_ENV = "DE4SDV_SEMANTIC_AUTHORITY"
BUNDLE_PATH_ENV = "DE4SDV_O3_AUTHORITY_BUNDLE"
BUNDLE_ID_ENV = "DE4SDV_O3_AUTHORITY_BUNDLE_ID"

#: Explicit selector values. Anything else fails closed.
LEGACY_AUTHORITY = "legacy"
O3_AUTHORITY = "o3"


class AuthoritySelectionError(ValueError):
    """The explicit semantic-authority selection is invalid (fail closed)."""


@dataclass(frozen=True)
class AuthoritySelection:
    """One resolved authority selection.

    ``bundle_document`` is the parsed, schema/id/state-checked closed bundle
    for an O3 selection; the deep verification (digests, revision binding,
    closure attestation, activation eligibility) runs inside the runtime
    assembly seam and refuses startup on any mismatch.
    """

    kind: str
    bundle_id: str | None = None
    bundle_path: Path | None = None
    bundle_document: dict[str, Any] | None = None

    @property
    def is_o3(self) -> bool:
        return self.kind == O3_AUTHORITY

    def provenance(self) -> dict[str, Any]:
        """Deployment provenance block (which authority, which bundle)."""
        if self.kind != O3_AUTHORITY:
            return {"kind": LEGACY_AUTHORITY, "authority_id": LEGACY_AUTHORITY_ID}
        document = self.bundle_document or {}
        return {
            "kind": O3_AUTHORITY,
            "authority_id": o3_authority_id(str(self.bundle_id)),
            "bundle_id": str(self.bundle_id),
            "bundle_path": str(self.bundle_path),
            "git_revision": str(document.get("git_revision") or ""),
            "migrated_scope": "reviewed-13-identity-subset",
        }


def resolve_authority_selection(
    *,
    authority: str | None = None,
    bundle_path: "str | Path | None" = None,
    bundle_id: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> AuthoritySelection:
    """Resolve the explicit authority selection (fail closed).

    Explicit arguments (CLI flags) win over the environment. The default —
    an unset or empty selector — is legacy authority. Any other value than
    ``legacy`` / ``o3`` is refused: typos and unknown selectors never
    degrade into an implicit choice.
    """
    env = os.environ if environ is None else environ
    raw = authority if authority is not None else env.get(AUTHORITY_ENV, "")
    value = str(raw or "").strip().lower()
    if value in ("", LEGACY_AUTHORITY):
        return AuthoritySelection(kind=LEGACY_AUTHORITY)
    if value != O3_AUTHORITY:
        raise AuthoritySelectionError(
            f"unknown {AUTHORITY_ENV} value {raw!r}: expected "
            f"{LEGACY_AUTHORITY!r} or {O3_AUTHORITY!r}; the semantic "
            "authority is never selected implicitly (no latest-bundle "
            "discovery, no silent legacy fallback)"
        )

    requested_path = (
        bundle_path if bundle_path is not None else env.get(BUNDLE_PATH_ENV, "")
    )
    requested_id = (
        bundle_id if bundle_id is not None else env.get(BUNDLE_ID_ENV, "")
    )
    if not str(requested_path or "").strip():
        raise AuthoritySelectionError(
            f"{AUTHORITY_ENV}=o3 requires {BUNDLE_PATH_ENV} (path to the "
            "accepted closed O3 authority bundle JSON)"
        )
    if not str(requested_id or "").strip():
        raise AuthoritySelectionError(
            f"{AUTHORITY_ENV}=o3 requires {BUNDLE_ID_ENV} (the exact "
            "accepted bundle id); an accepted O3 authority is always "
            "bundle-id-bound"
        )
    path = Path(str(requested_path))
    if not path.is_file():
        raise AuthoritySelectionError(
            f"O3 authority bundle not found: {path} (no other bundle is "
            "substituted, and legacy authority is never used as a fallback)"
        )
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise AuthoritySelectionError(
            f"O3 authority bundle is not readable JSON: {path}: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise AuthoritySelectionError(
            f"O3 authority bundle must be a JSON object: {path}"
        )
    if document.get("schema") != O3_BUNDLE_SCHEMA:
        raise AuthoritySelectionError(
            f"O3 authority bundle schema mismatch in {path}: "
            f"{document.get('schema')!r} != {O3_BUNDLE_SCHEMA!r}"
        )
    if document.get("state") != "closed":
        raise AuthoritySelectionError(
            f"O3 authority bundle {path} is not closed (state="
            f"{document.get('state')!r}): only a bundle carrying the "
            "exact-revision API closure attestation can be selected for "
            "production"
        )
    loaded_id = str(document.get("bundle_id") or "")
    if not loaded_id:
        raise AuthoritySelectionError(
            f"O3 authority bundle {path} carries no bundle_id"
        )
    if loaded_id != str(requested_id).strip():
        raise AuthoritySelectionError(
            f"requested bundle id {str(requested_id).strip()!r} does not "
            f"equal the bundle document id {loaded_id!r}; selection is "
            "bundle-id-bound"
        )
    return AuthoritySelection(
        kind=O3_AUTHORITY,
        bundle_id=loaded_id,
        bundle_path=path,
        bundle_document=document,
    )


def build_selected_semantic_runtime(
    *,
    api_url: str,
    binding_path: Path,
    expected_git_revision: str,
    ontology_path: Path,
    api_timeout: float = 600.0,
    method_conformance: Any = None,
    method_context_provider: Any = None,
    authority: str | None = None,
    bundle_path: "str | Path | None" = None,
    bundle_id: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> "tuple[Any, AuthoritySelection]":
    """Assemble the production semantic runtime under the selected authority.

    One call site for every production surface: resolve the explicit
    selection (explicit arguments, e.g. CLI flags, win over the
    environment), then build the runtime through the existing assembly
    seam. For an O3 selection the bundle must additionally be ACTIVATION
    ELIGIBLE (grounding EQUIVALENT and every required validation exactly
    passed); any verification failure raises instead of degrading to
    legacy.

    Returns ``(service, selection)``.
    """
    selection = resolve_authority_selection(
        authority=authority,
        bundle_path=bundle_path,
        bundle_id=bundle_id,
        environ=environ,
    )
    from .runtime import build_semantic_runtime

    service = build_semantic_runtime(
        api_url=api_url,
        binding_path=binding_path,
        expected_git_revision=expected_git_revision,
        ontology_path=ontology_path,
        api_timeout=api_timeout,
        method_conformance=method_conformance,
        method_context_provider=method_context_provider,
        semantic_authority=selection.bundle_document,
        require_activation_eligible=selection.is_o3,
    )
    return service, selection