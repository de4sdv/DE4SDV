"""Entry-point authority seam for the O4 Wave B model-authority selector.

Production surfaces select semantic authority explicitly:

    DE4SDV_SEMANTIC_AUTHORITY = legacy | o3 | model     (default: legacy)

``legacy`` and ``o3`` are resolved by the frozen O3 machinery
(``authority_selection`` is a member of the O3 runtime build, so it is not
edited: its behavior — and therefore the O3 rollback path — stays
byte-identical). The one canonical router is
``composition_construction.build_explicit_semantic_runtime``; this module
resolves and identity-checks a ``model`` request around it and delegates every
other value unchanged:

    DE4SDV_MODEL_AUTHORITY_BUNDLE    = <path to the model-authority bundle JSON>
    DE4SDV_MODEL_AUTHORITY_BUNDLE_ID = mab-<hex>

A ``model`` request is bundle-id-bound and fails closed: a missing path or
id, a malformed id, a missing file, a refusal by the model-authority runtime,
or any identity mismatch between the requested id and the served runtime
refuses startup. There is no fallback from a requested model authority to
O3 or legacy; rollback is an explicit selector change (``=o3`` with a fresh
O3 bundle at the same revision, legacy second).

The router imports the model-authority runtime only for a model selection,
so legacy/O3 startup never depends on it.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping

from .authority_selection import AUTHORITY_ENV, AuthoritySelectionError

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
    "ontology_path",
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
    """Resolved model-authority selection (same duck type as O3 selection)."""

    bundle_id: str
    bundle_path: Path
    status: dict[str, Any] = field(default_factory=dict)
    kind: str = MODEL_AUTHORITY

    @property
    def is_o3(self) -> bool:
        return False

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
            "residual": list(self.status.get("residual") or []),
            "rollback": str(self.status.get("rollback") or ""),
        }


def _selector_value(authority: str | None, env: Mapping[str, str]) -> str:
    raw = authority if authority is not None else env.get(AUTHORITY_ENV, "")
    return str(raw or "").strip().lower()


def resolve_model_request(
    *,
    authority: str | None = None,
    bundle_path: "str | Path | None" = None,
    bundle_id: str | None = None,
    environ: Mapping[str, str] | None = None,
) -> ModelAuthorityRequest | None:
    """Return the model request, or ``None`` for any non-model selector.

    Explicit arguments (CLI flags) win over the environment, exactly as in
    the O3 resolver. Non-model values are left to that resolver untouched.
    """
    env = os.environ if environ is None else environ
    if _selector_value(authority, env) != MODEL_AUTHORITY:
        return None
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
            "substituted; O3 and legacy are never used as a fallback)"
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

    Construction goes through the one canonical router,
    ``composition_construction.build_explicit_semantic_runtime``; this seam
    only resolves the request up front and cross-checks the served identity.
    Activation eligibility is required unless the caller explicitly passes
    ``require_activation_eligible=False`` (the privileged candidate compare).
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
    composition: str | None = None,
    authority: str | None = None,
    model_bundle_path: "str | Path | None" = None,
    model_bundle_id: str | None = None,
    environ: Mapping[str, str] | None = None,
    **kwargs: Any,
) -> tuple[Any, Any]:
    """One construction call for every entry point.

    ``model`` is resolved and identity-checked here, then built by the same
    canonical router as every other selector, which receives legacy/o3/
    composition requests unchanged.
    """
    request = resolve_model_request(
        authority=authority,
        bundle_path=model_bundle_path,
        bundle_id=model_bundle_id,
        environ=environ,
    )
    if request is None:
        delegated: dict[str, Any] = dict(kwargs)
        if composition is not None:
            delegated["composition"] = composition
        if authority is not None:
            delegated["authority"] = authority
        if environ is not None:
            delegated["environ"] = environ
        return _delegate(**delegated)
    if composition is not None:
        raise ModelAuthoritySelectionError(
            "explicit runtime composition is a non-production O3 sidecar and "
            "cannot be combined with model authority"
        )
    runtime_kwargs = {key: kwargs[key] for key in RUNTIME_CONTRACT_KEYS if key in kwargs}
    return build_model_runtime(request, **runtime_kwargs)


def entry_authority_status(environ: Mapping[str, str] | None = None) -> dict[str, Any]:
    """Requested-authority provenance without building any runtime."""
    env = os.environ if environ is None else environ
    try:
        request = resolve_model_request(environ=env)
        if request is not None:
            return {
                "kind": MODEL_AUTHORITY,
                "authority_id": model_authority_id(request.bundle_id),
                "bundle_id": request.bundle_id,
                "bundle_path": str(request.bundle_path),
                "state": "requested",
            }
        from .authority_selection import resolve_authority_selection

        return resolve_authority_selection(environ=env).provenance()
    except Exception as exc:  # noqa: BLE001 — status must survive
        return {
            "kind": "invalid",
            "error": str(exc),
            "note": (
                "semantic authority selector is invalid; semantic answers are "
                "refused (no fallback to another authority)"
            ),
        }
