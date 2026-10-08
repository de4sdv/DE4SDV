"""Shared check of the public Ask viewer's served semantic authority.

``/ask-status.json`` reports ``.semantic_authority``. Since O4 Wave C2 the
only accepted authority is ``model`` with an exact ``mab-`` bundle id; an
unset or retired selector reports ``kind == "invalid"`` and the viewer
refuses every semantic answer. These checks make that state fail a
deployment run and alert the monitor instead of passing green.

Used by ``verify_public_api.py`` (post-deploy, against the operator's
declared expectation), ``verify_public_ask.py`` (the served authority must be
the accepted bundle) and ``monitor_public_ask.py`` (``invalid`` alerts).
Procedure: docs/method-conformance/o4/model-authority-activation.md.
"""
from __future__ import annotations

import re
from typing import Any

MODEL_BUNDLE_ID = re.compile(r"mab-(?:[0-9a-f]{32}|[0-9a-f]{64})")


class AuthorityCheckError(RuntimeError):
    """The served semantic authority is not the declared one."""


def model_authority_id(bundle_id: str) -> str:
    """The runtime's served id for a model bundle: ``mab:<bundle id>``
    (``mab:mab-<hex>``, de4sdv.semantic.entry_authority.model_authority_id)."""
    return f"mab:{bundle_id}"


def authority_block(ask_status: Any) -> dict[str, Any]:
    """The ``.semantic_authority`` block; ``invalid`` always refuses."""
    block = ask_status.get("semantic_authority") if isinstance(ask_status, dict) else None
    if not isinstance(block, dict):
        raise AuthorityCheckError("/ask-status.json carries no semantic_authority block")
    if block.get("kind") == "invalid":
        raise AuthorityCheckError(
            "semantic authority is invalid; every semantic answer is refused: "
            f"{block.get('error') or 'no reason given'}"
        )
    return block


def check_served_consistency(block: dict[str, Any]) -> None:
    """A built model runtime must serve exactly the requested bundle."""
    served = block.get("semantic_authority_id")
    if block.get("kind") == "model" and served and served != block.get("authority_id"):
        raise AuthorityCheckError(
            f"runtime serves {served!r} but the requested authority is "
            f"{block.get('authority_id')!r}"
        )


def parse_expectation(expected: str) -> tuple[str, str | None]:
    """``mab-<hex>`` -> model; ``legacy`` or ``o3:<bundle id>`` (pre-C2 only)."""
    value = (expected or "").strip()
    if MODEL_BUNDLE_ID.fullmatch(value):
        return "model", value
    if value == "legacy":
        return "legacy", None
    if value.startswith("o3:") and value[3:]:
        return "o3", value[3:]
    raise AuthorityCheckError(
        f"expected semantic authority must be mab-<32|64 hex>, legacy or "
        f"o3:<bundle id>, got {expected!r}"
    )


def check_expected_authority(
    ask_status: Any, *, expected: str, pre_c2: bool, require_served: bool,
) -> dict[str, Any]:
    """Require the served authority to be exactly the declared expectation.

    ``legacy`` and ``o3`` exist only on pre-C2 revisions (a rollback);
    ``require_served`` additionally requires the built runtime's
    ``semantic_authority_id`` (not only the requested selection).
    """
    expected_kind, expected_id = parse_expectation(expected)
    if expected_kind != "model" and not pre_c2:
        raise AuthorityCheckError(
            f"expected authority {expected!r} exists only on a pre-C2 revision; "
            "a C2 revision serves model only"
        )
    block = authority_block(ask_status)
    kind = block.get("kind")
    if kind != expected_kind:
        raise AuthorityCheckError(
            f"semantic authority kind is {kind!r}, expected {expected_kind!r} "
            "(stale or unset selector in the compose substitution environment)"
        )
    if expected_id is not None and block.get("bundle_id") != expected_id:
        raise AuthorityCheckError(
            f"semantic authority bundle is {block.get('bundle_id')!r}, expected "
            f"{expected_id!r} (stale DE4SDV_MODEL_AUTHORITY_BUNDLE_ID?)"
        )
    if expected_kind == "model":
        assert expected_id is not None
        if block.get("authority_id") != model_authority_id(expected_id):
            raise AuthorityCheckError(
                f"semantic authority authority_id is {block.get('authority_id')!r}, "
                f"expected {model_authority_id(expected_id)!r}"
            )
        check_served_consistency(block)
        if require_served and block.get("semantic_authority_id") != model_authority_id(expected_id):
            raise AuthorityCheckError(
                "the model runtime is not built: it serves "
                f"{block.get('semantic_authority_id')!r}, expected "
                f"{model_authority_id(expected_id)!r}"
            )
    return block
