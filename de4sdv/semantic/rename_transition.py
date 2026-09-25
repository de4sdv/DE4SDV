"""Inert W6 rename-transition scaffolding. Prepares decisions; activates none.

The committed plan (``docs/method-conformance/o4/w6-transition-plan.yaml``) is
preparation only: no identity is renamed, no alias is emitted, no deprecation
interval is active, and no runtime consumer reads this module. Every entry
stays ``authorization: null`` until the owner resolves decision-1 (the five
renames plus alias/deprecation policy) or decision-15 (trace-chain successor
name). Any non-null authorization in the committed plan is refused.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

PLAN_PATH = "docs/method-conformance/o4/w6-transition-plan.yaml"
SCHEMA = "de4sdv.o4-w6-transition-plan/v1"
STATUS = "preparation"
REPO_ROOT = Path(__file__).resolve().parents[2]

_ALLOWED_TOP = {"schema", "status", "note", "entries"}
_ALLOWED_ENTRY = {"identity", "proposed_successor", "authorization"}
_IDENTIFIER = re.compile(r"^[A-Za-z][A-Za-z0-9]*$")
# Proposed *new* names follow the review's lowercase-initial convention.
_SUCCESSOR_PROPOSED = re.compile(r"^[a-z][A-Za-z0-9]*$")
# decision-15 rows: their successor is an existing register identity (or an
# as-yet-undecided name), so those entries validate the successor as an
# identifier only — never as a proposed lowercase name.
_TRACE_IDENTITIES = frozenset({"IncrementTraceabilityShell", "RequiredTraceChain", "TraceLink"})
_AUTHORIZATION_KEYS = {"decision", "record"}
_RECOGNIZED_DECISIONS = {"decision-1", "decision-15"}


class RenameTransitionError(ValueError):
    """Malformed, unauthorized, or activating transition-plan content."""


def _pending_decision(identity: str) -> str:
    return "decision-15" if identity in _TRACE_IDENTITIES else "decision-1"


def validate_plan(document: dict, *, allow_authorized: bool = False) -> dict:
    """Fail-closed validation of a transition plan document.

    Refuses unknown keys anywhere, malformed or duplicate identities,
    non-identifier or non-lowercase proposed successors (decision-15 trace
    entries carry an existing register identity and validate as identifiers
    only), and — unless ``allow_authorized`` is set for synthetic in-memory
    exercises of the schema — any non-null authorization, naming the owner
    decision that is still unresolved. The committed plan is validated with the
    default (authorization must be null); no committed plan can carry an
    authorization record today.
    """
    if not isinstance(document, dict):
        raise RenameTransitionError("plan must be a mapping")
    unknown = sorted(set(document) - _ALLOWED_TOP)
    if unknown:
        raise RenameTransitionError(f"unknown top-level keys: {unknown}")
    if document.get("schema") != SCHEMA:
        raise RenameTransitionError(f"unexpected schema: {document.get('schema')!r}")
    if document.get("status") != STATUS:
        raise RenameTransitionError(
            f"status must be {STATUS!r}; activation is not authorized")
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise RenameTransitionError("entries must be a list")
    seen: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict):
            raise RenameTransitionError("entry must be a mapping")
        unknown = sorted(set(entry) - _ALLOWED_ENTRY)
        if unknown:
            raise RenameTransitionError(f"unknown entry keys: {unknown}")
        missing = sorted(_ALLOWED_ENTRY - set(entry))
        if missing:
            raise RenameTransitionError(f"missing entry keys: {missing}")
        identity = entry["identity"]
        if not isinstance(identity, str) or not _IDENTIFIER.match(identity):
            raise RenameTransitionError(f"invalid identity: {identity!r}")
        if identity in seen:
            raise RenameTransitionError(f"duplicate identity {identity}")
        seen.add(identity)
        successor = entry["proposed_successor"]
        if not isinstance(successor, str) or not _IDENTIFIER.match(successor):
            raise RenameTransitionError(f"{identity}: invalid proposed_successor {successor!r}")
        if identity not in _TRACE_IDENTITIES and not _SUCCESSOR_PROPOSED.match(successor):
            raise RenameTransitionError(
                f"{identity}: proposed_successor {successor!r} must be a lowercase-initial name")
        authorization = entry["authorization"]
        if authorization is None:
            continue
        if not allow_authorized:
            raise RenameTransitionError(
                f"{identity}: authorization refused; owner {_pending_decision(identity)} "
                "is unresolved and the committed plan must stay inert "
                "(authorization: null)")
        if not isinstance(authorization, dict):
            raise RenameTransitionError(f"{identity}: authorization must be a decision record")
        unknown = sorted(set(authorization) - _AUTHORIZATION_KEYS)
        if unknown:
            raise RenameTransitionError(f"{identity}: unknown authorization keys: {unknown}")
        missing = sorted(_AUTHORIZATION_KEYS - set(authorization))
        if missing:
            raise RenameTransitionError(f"{identity}: missing authorization keys: {missing}")
        if authorization["decision"] not in _RECOGNIZED_DECISIONS:
            raise RenameTransitionError(
                f"{identity}: authorization decision {authorization['decision']!r} "
                "is not a recognized owner decision")
        record = authorization["record"]
        if not isinstance(record, str) or not record:
            raise RenameTransitionError(
                f"{identity}: authorization record must be a non-empty reference")
    return document


def load_plan(root: str | Path = REPO_ROOT) -> dict:
    """Load and validate the committed transition plan. Never activates it."""
    path = Path(root) / PLAN_PATH
    if not path.is_file():
        raise RenameTransitionError(f"transition plan missing: {PLAN_PATH}")
    return validate_plan(yaml.safe_load(path.read_text(encoding="utf-8")))


def transition_state(identity: str, plan: dict | None = None) -> str:
    """'pending' until an authorized entry exists; 'decided' otherwise.

    'decided' is not representable by the committed plan (every entry keeps
    ``authorization: null``); it exists so the schema logic can be exercised
    against synthetic in-memory plans validated with ``allow_authorized``.
    """
    document = load_plan() if plan is None else plan
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise RenameTransitionError("entries must be a list")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("identity") == identity:
            return "pending" if entry.get("authorization") is None else "decided"
    raise RenameTransitionError(f"unknown identity: {identity}")


def authorized_entries(document: dict) -> list[dict]:
    """Entries carrying an owner authorization record. Empty for the skeleton."""
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise RenameTransitionError("entries must be a list")
    return [entry for entry in entries
            if isinstance(entry, dict) and entry.get("authorization") is not None]