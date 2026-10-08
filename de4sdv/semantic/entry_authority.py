"""Entry-point authority seam (O4 Wave C2: model authority only).

Production surfaces select semantic authority explicitly:

    DE4SDV_SEMANTIC_AUTHORITY = model
    DE4SDV_MODEL_AUTHORITY_BUNDLE    = <path to the model-authority bundle JSON>
    DE4SDV_MODEL_AUTHORITY_BUNDLE_ID = mab-<hex>

The request is bundle-id-bound and fails closed: an unset, retired
(``legacy``/``o3``) or unknown selector, a missing path or id, a malformed
id, a missing file, a refusal by the model-authority runtime, or any identity
mismatch between the requested id and the served runtime refuses startup.
Rollback is a redeploy of the pre-Wave-C production revision, never a
selector change. The one canonical router is
``composition_construction.build_explicit_semantic_runtime``.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .authority_selection import AUTHORITY_ENV, AuthoritySelectionError, require_model_selection

ROOT = Path(__file__).resolve().parents[2]

MODEL_AUTHORITY = "model"
MODEL_BUNDLE_PATH_ENV = "DE4SDV_MODEL_AUTHORITY_BUNDLE"
MODEL_BUNDLE_ID_ENV = "DE4SDV_MODEL_AUTHORITY_BUNDLE_ID"

#: Literal model-authority bundle id token (32 or 64 lowercase hex digits).
MAB_ID_PATTERN = re.compile(r"mab-(?:[0-9a-f]{32}|[0-9a-f]{64})")

#: Runtime-contract keyword arguments an entry point may forward to the
#: model-authority runtime through the canonical router.
RUNTIME_CONTRACT_KEYS = (
    "api_url",
    "binding_path",
    "expected_git_revision",
    "api_timeout",
    "method_conformance",
    "method_context_provider",
    "require_activation_eligible",
)


class ModelAuthoritySelectionError(AuthoritySelectionError):
    """The explicit model-authority selection is invalid (fail closed)."""


def model_authority_id(bundle_id: str) -> str:
    """Service/cache authority id for one model-authority bundle."""
    return f"mab:{bundle_id}"


def is_model_bundle_id(value: object) -> bool:
    return isinstance(value, str) and MAB_ID_PATTERN.fullmatch(value) is not None


@dataclass(frozen=True)
class ModelAuthorityRequest:
    bundle_path: Path
    bundle_id: str


@dataclass(frozen=True)
class ModelAuthoritySelection:
    """Resolved and identity-checked model-authority selection."""

    bundle_id: str
    bundle_path: Path
    status: dict[str, Any] = field(default_factory=dict)
    kind: str = MODEL_AUTHORITY

    @property
    def is_model(self) -> bool:
        return True

    def provenance(self) -> dict[str, Any]:
        return {
            "kind": MODEL_AUTHORITY,
            "authority_id": model_authority_id(self.bundle_id),
            "bundle_id": self.bundle_id,
            "bundle_path": str(self.bundle_path),
            "source_revision": str(self.status.get("source_revision") or ""),
            "semantic_authority": str(self.status.get("semantic_authority") or ""),
            "refused": list(self.status.get("refused") or []),
            "rollback": str(self.status.get("rollback") or ""),
        }


def resolve_model_request(
    *,
    authority: str | None = None,
    bundle_path: "str | Path | None" = None,
    bundle_id: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> ModelAuthorityRequest:
    """Resolve the model request (fail closed on any other selector).

    Explicit arguments (CLI flags) win over the environment.
    """
    env = os.environ if environ is None else environ
    try:
        require_model_selection(authority, env)
    except AuthoritySelectionError as exc:
        raise ModelAuthoritySelectionError(str(exc)) from exc
    raw_path = bundle_path if bundle_path is not None else env.get(MODEL_BUNDLE_PATH_ENV, "")
    raw_id = bundle_id if bundle_id is not None else env.get(MODEL_BUNDLE_ID_ENV, "")
    if not str(raw_path or "").strip():
        raise ModelAuthoritySelectionError(
            f"{AUTHORITY_ENV}=model requires {MODEL_BUNDLE_PATH_ENV} (path to the "
            "accepted model-authority bundle JSON)"
        )
    if not str(raw_id or "").strip():
        raise ModelAuthoritySelectionError(
            f"{AUTHORITY_ENV}=model requires {MODEL_BUNDLE_ID_ENV} (the exact "
            "accepted mab- bundle id); model authority is always bundle-id-bound"
        )
    if not is_model_bundle_id(raw_id):
        raise ModelAuthoritySelectionError(
            f"{MODEL_BUNDLE_ID_ENV} must be a literal mab-<32 or 64 lowercase hex> "
            f"token, got {raw_id!r}"
        )
    path = Path(str(raw_path))
    if not path.is_file():
        raise ModelAuthoritySelectionError(
            f"model-authority bundle not found: {path} (no other bundle is "
            "substituted and no other authority exists)"
        )
    return ModelAuthorityRequest(bundle_path=path, bundle_id=str(raw_id))


def require_model_identity(service: Any, request: ModelAuthorityRequest) -> dict[str, Any]:
    """Cross-check the served runtime against the requested bundle id."""
    try:
        status = dict(service.authority_status())
    except Exception as exc:  # noqa: BLE001 — any status failure refuses
        raise ModelAuthoritySelectionError(
            f"model-authority runtime did not report its authority status: {exc}"
        ) from exc
    if status.get("authority") != MODEL_AUTHORITY:
        raise ModelAuthoritySelectionError(
            f"model-authority runtime reports authority {status.get('authority')!r}, "
            "expected 'model'"
        )
    if status.get("bundle_id") != request.bundle_id:
        raise ModelAuthoritySelectionError(
            f"model-authority runtime serves bundle {status.get('bundle_id')!r}, "
            f"requested {request.bundle_id!r}; selection is bundle-id-bound"
        )
    served = str(getattr(service, "semantic_authority_id", "") or "")
    if served != model_authority_id(request.bundle_id):
        raise ModelAuthoritySelectionError(
            f"model-authority runtime semantic_authority_id {served!r} != "
            f"{model_authority_id(request.bundle_id)!r}; cache/snapshot identities "
            "must be keyed by the mab: id"
        )
    return status


def build_model_runtime(request: ModelAuthorityRequest, **runtime_kwargs: Any):
    """Build and identity-check the model-authority runtime (fail closed).

    Activation eligibility is required unless the caller explicitly passes
    ``require_activation_eligible=False`` (privileged evidence steps only).
    """
    unknown = sorted(set(runtime_kwargs) - set(RUNTIME_CONTRACT_KEYS))
    if unknown:
        raise ModelAuthoritySelectionError(
            f"unsupported model-authority runtime arguments: {unknown}"
        )
    try:
        service, _ = _delegate(
            authority=MODEL_AUTHORITY,
            model_bundle_path=request.bundle_path,
            model_bundle_id=request.bundle_id,
            environ={},
            **runtime_kwargs,
        )
    except ModelAuthoritySelectionError:
        raise
    except AuthoritySelectionError as exc:  # includes ModelAuthorityRefused
        raise ModelAuthoritySelectionError(
            f"model-authority runtime refused: {exc}"
        ) from exc
    status = require_model_identity(service, request)
    return service, ModelAuthoritySelection(
        bundle_id=request.bundle_id, bundle_path=request.bundle_path, status=status
    )


def _delegate(**kwargs: Any):
    from .composition_construction import build_explicit_semantic_runtime

    return build_explicit_semantic_runtime(**kwargs)


def build_entry_semantic_runtime(
    *,
    authority: str | None = None,
    model_bundle_path: "str | Path | None" = None,
    model_bundle_id: str | None = None,
    environ: Mapping[str, str] | None = None,
    **kwargs: Any,
) -> tuple[Any, Any]:
    """One construction call for every entry point (model authority only)."""
    request = resolve_model_request(
        authority=authority,
        bundle_path=model_bundle_path,
        bundle_id=model_bundle_id,
        environ=environ,
    )
    unknown = sorted(set(kwargs) - set(RUNTIME_CONTRACT_KEYS))
    if unknown:
        raise ModelAuthoritySelectionError(
            f"unsupported entry-point runtime arguments: {unknown}"
        )
    return build_model_runtime(request, **kwargs)


def entry_authority_status(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Requested-authority provenance without building any runtime."""
    env = os.environ if environ is None else environ
    try:
        request = resolve_model_request(environ=env)
        return {
            "kind": MODEL_AUTHORITY,
            "authority_id": model_authority_id(request.bundle_id),
            "bundle_id": request.bundle_id,
            "bundle_path": str(request.bundle_path),
            "state": "requested",
        }
    except Exception as exc:  # noqa: BLE001 — status must survive
        return {
            "kind": "invalid",
            "error": str(exc),
            "note": (
                "semantic authority selector is invalid; semantic answers are "
                "refused (no fallback to another authority)"
            ),
        }
