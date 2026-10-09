"""The one canonical semantic-runtime router (O4 Wave C2: model authority only).

Every semantic consumer builds its runtime here. The selector
(``authority``/``DE4SDV_SEMANTIC_AUTHORITY``) must be ``model``
(:func:`authority_selection.require_model_selection`: unset, ``legacy``,
``o3`` and unknown values are refused); the model-authority bundle is then
verified and assembled by :mod:`model_authority_runtime`. There is no other
composition and no fallback.
"""
from __future__ import annotations

from typing import Any

from .authority_selection import AuthoritySelectionError, require_model_selection

_RUNTIME_KEYS = frozenset({
    "api_url", "binding_path", "expected_git_revision", "api_timeout",
    "require_activation_eligible", "production",
    "validation_artifacts", "environ", "root",
})


def build_explicit_semantic_runtime(*, composition: str | None = None, **kwargs: Any) -> tuple[Any, Any]:
    """Shared bootstrap contract for every semantic consumer.

    Returns ``(service, selection)``. ``model_bundle_path``/``model_bundle_id``
    (or the ``DE4SDV_MODEL_AUTHORITY_BUNDLE``/``_ID`` environment) name the
    bundle; any other argument outside the runtime contract is refused.
    """
    if composition is not None:
        raise AuthoritySelectionError(
            f"runtime composition {composition!r} is retired by O4 Wave C2; only the "
            "model authority is assembled")
    require_model_selection(kwargs.pop("authority", None), kwargs.get("environ"))
    bundle_path = kwargs.pop("model_bundle_path", None)
    bundle_id = kwargs.pop("model_bundle_id", None)
    unknown = sorted(set(kwargs) - _RUNTIME_KEYS)
    if unknown:
        raise AuthoritySelectionError(f"unsupported semantic-runtime arguments: {unknown}")
    from . import model_authority_runtime as model

    root = kwargs.pop("root", model.ROOT)
    service = model.build_model_authority_runtime(root, bundle_path, bundle_id, **kwargs)
    return service, service.selection


__all__ = ["build_explicit_semantic_runtime"]
