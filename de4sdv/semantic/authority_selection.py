"""Explicit semantic-authority selection (O4 Wave C2: model authority only).

Production semantic authority is selected EXPLICITLY and never inferred:

    DE4SDV_SEMANTIC_AUTHORITY = model

``model`` is the only accepted value: one closed, activation-eligible
model-authority bundle identified by its path and exact ``mab-`` id
(``DE4SDV_MODEL_AUTHORITY_BUNDLE`` / ``DE4SDV_MODEL_AUTHORITY_BUNDLE_ID``).

- An unset or empty selector is refused (owner decision D6, 2026-10-07): no
  default authority is ever activated implicitly.
- ``legacy`` and ``o3`` are refused: the authored ontology and the O3 bundle
  machinery were retired by O4 Wave C2. Rollback is a redeploy of the
  pre-Wave-C production revision through the normal deploy workflows, not a
  selector change (``docs/method-conformance/o4/model-authority-activation.md``).
- Any other value is refused. There is no fallback and no bundle discovery.
"""
from __future__ import annotations

import os
from typing import Mapping

AUTHORITY_ENV = "DE4SDV_SEMANTIC_AUTHORITY"
MODEL_AUTHORITY = "model"
RETIRED_AUTHORITIES = ("legacy", "o3")
ROLLBACK_PROCEDURE = (
    "docs/method-conformance/o4/model-authority-activation.md (rollback = redeploy "
    "the pre-Wave-C production revision)"
)


class AuthoritySelectionError(ValueError):
    """The explicit semantic-authority selection is invalid (fail closed)."""


def selector_value(authority: str | None, environ: Mapping[str, str] | None = None) -> str:
    env = os.environ if environ is None else environ
    raw = authority if authority is not None else env.get(AUTHORITY_ENV, "")
    return str(raw or "").strip().lower()


def require_model_selection(authority: str | None = None,
                            environ: Mapping[str, str] | None = None) -> str:
    """Return ``model`` or refuse (unset, retired or unknown selector)."""
    value = selector_value(authority, environ)
    if value == MODEL_AUTHORITY:
        return value
    if not value:
        raise AuthoritySelectionError(
            f"{AUTHORITY_ENV} is unset: the semantic authority is never selected "
            f"implicitly; set {AUTHORITY_ENV}=model with the accepted model-authority "
            "bundle (owner decision D6)")
    if value in RETIRED_AUTHORITIES:
        raise AuthoritySelectionError(
            f"{AUTHORITY_ENV}={value!r} is retired by O4 Wave C2 (the authored ontology "
            f"and the O3 bundle path were removed); only 'model' is accepted. Rollback "
            f"is a redeploy, see {ROLLBACK_PROCEDURE}")
    raw = authority if authority is not None else (os.environ if environ is None else environ).get(
        AUTHORITY_ENV, "")
    raise AuthoritySelectionError(
        f"unknown {AUTHORITY_ENV} value {raw!r}: only 'model' is accepted; the semantic "
        "authority is never selected implicitly")


__all__ = ["AUTHORITY_ENV", "AuthoritySelectionError", "MODEL_AUTHORITY", "RETIRED_AUTHORITIES",
           "ROLLBACK_PROCEDURE", "require_model_selection", "selector_value"]
