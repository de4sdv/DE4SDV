"""Build-time W6 approval reconciliation; never runtime semantic authority.

The v2 plan records accepted semantic directions without activating aliases,
consumers or production authority. It resolves every required decision against
the repository's scoped owner record. Historical v1 preparation documents remain
valid as historical inputs; synthetic v1 authorization is not owner approval.
Successor runtime meaning comes from its versioned model-derived contract, not
this governance wording or the historical review's advisory rename proposals.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml

PLAN_PATH = "docs/method-conformance/o4/w6-transition-plan.yaml"
SCHEMA = "de4sdv.o4-w6-transition-plan/v1"
STATUS = "preparation"
APPROVED_SCHEMA = "de4sdv.o4-w6-transition-plan/v2"
APPROVALS_PATH = "docs/method-conformance/o4/approved-semantic-decisions.yaml"
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
_AUTHORIZATION_KEYS = {"decisions", "record"}
_REQUIRED_DECISIONS = {
    "realizedBy": {"decision-1"},
    "specifiesFunction": {"decision-1"},
    "validatedBy": {"decision-1"},
    "deployedTo": {"decision-1"},
    "constrainedBy": {"decision-1", "decision-2"},
    # The shell inherits these prerequisites from its proposed merge target,
    # not from its own (empty) register gate_decisions.
    "IncrementTraceabilityShell": {"decision-8", "decision-15"},
    "RequiredTraceChain": {"decision-8", "decision-15"},
    "TraceLink": {"decision-8", "decision-15"},
}

# Governance treatment locks, not runtime mappings or semantic authority.
_APPROVED_TREATMENTS = {
    "realizedBy": ("retire-name", "allocatedTo"),
    "specifiesFunction": ("retain-weaker-dependency", None),
    "validatedBy": ("rename-planning-association", "hasValidationScenario"),
    "constrainedBy": ("rename-provenance", "hasRegulatorySource"),
    "deployedTo": ("retire-name", "allocatedTo"),
    "IncrementTraceabilityShell": ("redesign-trace", None),
    "RequiredTraceChain": ("redesign-trace", None),
    "TraceLink": ("redesign-trace", None),
}
_APPROVED_TOPICS = {
    "topic1": {"decision-1"}, "topic2": {"decision-2"},
    "topic3": {"decision-3"}, "topic4": {"decision-4"},
    "topic5": {"decision-8", "decision-15"}, "topic6": {"decision-11"},
}
_APPROVAL_FLAGS = {
    "runtime_authority", "production_activation", "whole_consumer_retirement",
    "ple_adoption", "upstream_contact",
}


class RenameTransitionError(ValueError):
    """Malformed, unsupported, or activating transition-plan content."""


def _fields(value, expected: set[str], label: str) -> None:
    if not isinstance(value, dict) or set(value) != expected:
        raise RenameTransitionError(f"{label}: fields must be exactly {sorted(expected)}")


def _decision_set(value, label: str) -> set[str]:
    if (not isinstance(value, list) or not value
            or not all(isinstance(item, str) for item in value)
            or len(value) != len(set(value))):
        raise RenameTransitionError(f"{label}: decisions must be unique nonempty strings")
    return set(value)


def _load_approvals(root: Path) -> dict:
    path = root / APPROVALS_PATH
    try:
        document = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    except (OSError, yaml.YAMLError) as exc:
        raise RenameTransitionError(f"cannot load scoped owner record: {APPROVALS_PATH}") from exc
    _fields(document, {"schema", "inspection_basis", "scope", "note", "topics"}
            | _APPROVAL_FLAGS, "owner record")
    if (document["schema"] != "de4sdv.owner-semantic-approvals/v1"
            or document["scope"] != "reviewed-semantic-direction-only"
            or any(document[key] is not False for key in _APPROVAL_FLAGS)):
        raise RenameTransitionError("owner record cannot authorize activation, retirement or adoption")
    if (not isinstance(document["inspection_basis"], str)
            or not re.fullmatch(r"[0-9a-f]{40}", document["inspection_basis"])):
        raise RenameTransitionError("owner record requires an exact inspection revision")
    topics = document["topics"]
    _fields(topics, set(_APPROVED_TOPICS), "owner topics")
    for identity, required in _APPROVED_TOPICS.items():
        topic = topics[identity]
        _fields(topic, {"decisions", "accepted_at", "approval", "disposition"}, identity)
        if _decision_set(topic["decisions"], identity) != required:
            raise RenameTransitionError(f"{identity}: owner decisions differ from the reviewed scope")
        for key in ("accepted_at", "approval", "disposition"):
            if not isinstance(topic[key], str) or not topic[key].strip():
                raise RenameTransitionError(f"{identity}: {key} must be nonempty")
    return document


def _validate_approved_plan(document: dict, root: Path) -> dict:
    _fields(document, {"schema", "status", "note", "entries", "approval_record",
            "runtime_activation", "automatic_aliases"}, "approved plan")
    if (document["status"] != "approved-implementation"
            or document["runtime_activation"] is not False
            or document["automatic_aliases"] is not False
            or document["approval_record"] != APPROVALS_PATH):
        raise RenameTransitionError("approved plan cannot activate authority or automatic aliases")
    approvals = _load_approvals(root)
    entries = document["entries"]
    if not isinstance(entries, list):
        raise RenameTransitionError("approved entries must be a list")
    seen: set[str] = set()
    for entry in entries:
        _fields(entry, {"identity", "disposition", "successor", "authorization"}, "approved entry")
        identity = entry["identity"]
        if not isinstance(identity, str) or identity not in _APPROVED_TREATMENTS:
            raise RenameTransitionError(f"unsupported approved identity: {identity!r}")
        if identity in seen:
            raise RenameTransitionError(f"duplicate identity {identity}")
        seen.add(identity)
        disposition, successor = _APPROVED_TREATMENTS[identity]
        if (entry["disposition"], entry["successor"]) != (disposition, successor):
            raise RenameTransitionError(f"{identity}: superseded or unreviewed treatment")
        authorization = entry["authorization"]
        _fields(authorization, _AUTHORIZATION_KEYS, f"{identity} authorization")
        required = _REQUIRED_DECISIONS[identity]
        if _decision_set(authorization["decisions"], identity) != required:
            raise RenameTransitionError(f"{identity}: incomplete applicable decisions")
        reference = authorization["record"]
        prefix = APPROVALS_PATH + "#"
        if not isinstance(reference, str) or not reference.startswith(prefix):
            raise RenameTransitionError(f"{identity}: foreign owner record")
        fragments = reference[len(prefix):].split("+")
        if len(fragments) != len(set(fragments)):
            raise RenameTransitionError(f"{identity}: duplicate approval fragments")
        resolved: set[str] = set()
        for fragment in fragments:
            topic = approvals["topics"].get(fragment)
            if topic is None:
                raise RenameTransitionError(f"{identity}: unknown approval fragment {fragment!r}")
            resolved.update(topic["decisions"])
        if resolved != required:
            raise RenameTransitionError(f"{identity}: approval record does not resolve all applicable decisions")
    if seen != set(_APPROVED_TREATMENTS):
        raise RenameTransitionError("approved plan must account for every governed transition identity")
    return document


def _pending_decision(identity: str) -> str:
    if identity not in _REQUIRED_DECISIONS:
        raise RenameTransitionError(f"unknown transition identity: {identity}")
    return ", ".join(sorted(_REQUIRED_DECISIONS[identity]))


def validate_plan(document: dict, *, allow_authorized: bool = False,
                  root: str | Path = REPO_ROOT) -> dict:
    """Fail-closed validation of a transition plan document.

    Refuses unknown keys anywhere, malformed or duplicate identities,
    non-identifier or non-lowercase proposed successors (decision-15 trace
    entries carry an existing register identity and validate as identifiers
    only), and — unless ``allow_authorized`` is set for synthetic in-memory
    exercises of the historical v1 schema — any non-null authorization.
    Version 2 resolves approvals against the scoped repository owner record
    regardless of allow_authorized; that flag cannot bypass v2 checks.
    """
    if not isinstance(document, dict):
        raise RenameTransitionError("plan must be a mapping")
    if document.get("schema") == APPROVED_SCHEMA:
        return _validate_approved_plan(document, Path(root))
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
        if identity not in _REQUIRED_DECISIONS:
            raise RenameTransitionError(f"unsupported transition identity: {identity}")
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
                f"{identity}: authorization refused in historical v1; {_pending_decision(identity)} "
                "requires the scoped approval record in v2; v1 stays inert "
                "(authorization: null)")
        if not isinstance(authorization, dict):
            raise RenameTransitionError(f"{identity}: authorization must be a decision record")
        unknown = sorted(set(authorization) - _AUTHORIZATION_KEYS)
        if unknown:
            raise RenameTransitionError(f"{identity}: unknown authorization keys: {unknown}")
        missing = sorted(_AUTHORIZATION_KEYS - set(authorization))
        if missing:
            raise RenameTransitionError(f"{identity}: missing authorization keys: {missing}")
        decisions = authorization["decisions"]
        _pending_decision(identity)  # Unknown identities have no authorization rule.
        if (not isinstance(decisions, list)
                or not all(isinstance(value, str) for value in decisions)
                or len(decisions) != len(set(decisions))
                or set(decisions) != _REQUIRED_DECISIONS[identity]):
            raise RenameTransitionError(
                f"{identity}: authorization decisions must cover exactly "
                f"{_pending_decision(identity)}")
        record = authorization["record"]
        if not isinstance(record, str) or not record:
            raise RenameTransitionError(
                f"{identity}: authorization record must be a non-empty reference")
    return document


class _UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            try:
                if key in keys:
                    raise RenameTransitionError(f"duplicate YAML key: {key}")
                keys.add(key)
            except TypeError as exc:
                raise RenameTransitionError("YAML mapping keys must be scalar") from exc
        return super().construct_mapping(node, deep=deep)


def load_plan(root: str | Path = REPO_ROOT) -> dict:
    """Load and validate the committed transition plan. Never activates it."""
    path = Path(root) / PLAN_PATH
    if not path.is_file():
        raise RenameTransitionError(f"transition plan missing: {PLAN_PATH}")
    return validate_plan(yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader), root=root)


def transition_state(identity: str, plan: dict | None = None, *,
                     root: str | Path = REPO_ROOT) -> str:
    """v2 'approved' is direction-only; v1 'decided' remains synthetic."""
    document = load_plan(root) if plan is None else validate_plan(plan, allow_authorized=True, root=root)
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise RenameTransitionError("entries must be a list")
    for entry in entries:
        if isinstance(entry, dict) and entry.get("identity") == identity:
            if document["schema"] == APPROVED_SCHEMA:
                return "approved"
            return "pending" if entry.get("authorization") is None else "decided"
    raise RenameTransitionError(f"unknown identity: {identity}")


def authorized_entries(document: dict, *, root: str | Path = REPO_ROOT) -> list[dict]:
    """Direction-only v2 approvals or synthetic v1 schema entries; never activation."""
    validate_plan(document, allow_authorized=True, root=root)
    entries = document.get("entries")
    if not isinstance(entries, list):
        raise RenameTransitionError("entries must be a list")
    return [entry for entry in entries
            if isinstance(entry, dict) and entry.get("authorization") is not None]