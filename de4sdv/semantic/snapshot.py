"""Validated snapshot path for the deterministic method-conformance engine (Lane D).

Scope boundary (frozen baseline §14, Increment D):

- a snapshot is a rebuildable derived cache of ONE validated API revision; it
  is never a second semantic authority and never changes the evaluator;
- the snapshot serializes the exact semantic inputs the deterministic
  evaluator consumes (the validated graph payload plus the repository
  artifacts the evaluation reads), so a load re-enters the SAME assembly
  (``method_pilot.assemble_pilot_context``) and the SAME ``MethodEvaluator`` —
  there is no ``SnapshotEvaluator`` and no transport-specific evaluation path;
- trust comes from the controlled validated importer/build artifact chain:
  every load is checked against a retained validation record supplied by the
  caller (the validated binding + export identity of the exact privileged
  run) ***and*** an externally trusted canonical content digest supplied
  outside the snapshot. A bundle cannot authorize itself: self-attested
  provenance is rejected, a handle whose digests do not match the retained
  record is rejected, and content that was modified and re-forged to internal
  digest consistency still fails because the externally trusted payload
  binding — which transitively covers the graph, file inventories, scope,
  method, evaluator and completeness sections — no longer matches;
- loads are revision-explicit and fail closed: corrupt, incomplete,
  wrong-bound, or untrusted snapshots raise; there is NO fallback such as
  "invalid snapshot -> load latest API state", and no code path here can
  reach the network, a live API, or a newer revision.

Transport metadata (creation time, validation-run labels) lives in envelopes
outside the canonical payload digest; the canonical conformance payload is
insensitive to snapshot serialization order.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping, Sequence

from .method_evaluator import RevisionIdentity

SCHEMA = "de4sdv-method-snapshot/v1"

#: File-source roles carried by a snapshot. ``candidate`` is the evaluated
#: revision's artifact view; ``tested`` is the declared tested head's view.
ROLE_CANDIDATE = "candidate"
ROLE_TESTED = "tested"
ROLES = (ROLE_CANDIDATE, ROLE_TESTED)

#: Provenance kinds. Only a snapshot whose provenance names the controlled
#: validated importer chain is loadable.
PROVENANCE_VALIDATED = "validated-api-revision"
PROVENANCE_SELF_ATTESTED = "self-attested"

REQUIRED_SECTIONS = (
    "semantic_binding",
    "method_binding",
    "evaluator_binding",
    "scope_binding",
    "graph",
    "file_sources",
    "completeness",
    "integrity",
    "provenance",
)

_HANDLE_FIELDS = (
    "git_commit",
    "sysml_project_id",
    "sysml_commit_id",
    "scope",
    "export_sha256",
    "binding_sha256",
)

_FULL_SHA = re.compile(r"\A[0-9a-f]{40}\Z")
_SHA256 = re.compile(r"\A[0-9a-f]{64}\Z")


# ---------------------------------------------------------------------------
# Errors (fail closed; every refusal names its reasons)
# ---------------------------------------------------------------------------


class SnapshotError(RuntimeError):
    """Base class: the snapshot was refused; no evaluation was performed."""

    def __init__(self, reasons: Sequence[str]) -> None:
        self.reasons = tuple(reasons)
        super().__init__("snapshot refused: " + "; ".join(self.reasons))


class SnapshotValidationError(SnapshotError):
    """Structure, identity, trust, or expectation mismatch."""


class SnapshotIntegrityError(SnapshotError):
    """Payload/element/file digest or decode failure."""


class SnapshotCompletenessError(SnapshotError):
    """Missing required section, empty graph, or insufficient root coverage."""


def _refuse(
    error: type[SnapshotError], path: Path | str, reasons: Iterable[str]
) -> SnapshotError:
    return error([f"{path}: {reason}" for reason in reasons])


# ---------------------------------------------------------------------------
# Canonical digests and payload construction
# ---------------------------------------------------------------------------


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def elements_digest(elements: Sequence[Mapping[str, Any]]) -> str:
    """Order-insensitive digest of the graph payload (MC-12-class transport
    invariance: API enumeration order is not semantic content)."""
    ordered = sorted(elements, key=lambda element: str(element.get("@id") or ""))
    return hashlib.sha256(_canonical_bytes(ordered)).hexdigest()


def file_inventory_digest(files: Mapping[str, bytes]) -> str:
    manifest = {
        path: hashlib.sha256(blob).hexdigest() for path, blob in files.items()
    }
    return hashlib.sha256(_canonical_bytes(manifest)).hexdigest()


def _encode_files(files: Mapping[str, bytes]) -> dict[str, dict[str, Any]]:
    encoded: dict[str, dict[str, Any]] = {}
    for path in sorted(files):
        blob = files[path]
        encoded[path] = {
            "sha256": hashlib.sha256(blob).hexdigest(),
            "content_b64": base64.b64encode(blob).decode("ascii"),
        }
    return encoded


def _decode_files(entries: Mapping[str, Mapping[str, Any]]) -> dict[str, bytes]:
    decoded: dict[str, bytes] = {}
    for path, entry in entries.items():
        blob = base64.b64decode(str(entry.get("content_b64") or ""), validate=True)
        decoded[path] = blob
    return decoded


def _file_source_digest_view(
    file_sources: Mapping[str, Mapping[str, Any]],
) -> dict[str, dict[str, Any]]:
    view: dict[str, dict[str, Any]] = {}
    for role in sorted(file_sources):
        entry = file_sources[role]
        files = _decode_files(entry.get("files") or {})
        view[role] = {
            "revision": str(entry.get("revision") or ""),
            "roots": sorted(str(root) for root in entry.get("roots") or ()),
            "file_count": len(files),
            "total_bytes": sum(len(blob) for blob in files.values()),
            "files_digest": file_inventory_digest(files),
        }
    return view


def payload_digest_of(payload: Mapping[str, Any]) -> str:
    """Digest over the canonical semantic payload (envelope fields excluded)."""
    graph = payload.get("graph") or {}
    view = {
        "schema": payload.get("schema"),
        "semantic_binding": payload.get("semantic_binding"),
        "method_binding": payload.get("method_binding"),
        "evaluator_binding": payload.get("evaluator_binding"),
        "scope_binding": payload.get("scope_binding"),
        "graph": {
            "element_count": graph.get("element_count"),
            "elements_digest": graph.get("elements_digest"),
        },
        "file_sources": _file_source_digest_view(payload.get("file_sources") or {}),
        "completeness": payload.get("completeness"),
        "provenance": payload.get("provenance"),
    }
    return hashlib.sha256(_canonical_bytes(view)).hexdigest()


def finalize_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Recompute all digests from the payload body, in place, and return it.

    Used by builders that compose or adjust a payload in steps; the loader
    always recomputes independently and never trusts these stored values.
    """
    mutable = dict(payload)
    graph = dict(mutable.get("graph") or {})
    elements = graph.get("elements") or []
    graph["element_count"] = len(elements)
    graph["elements_digest"] = elements_digest(elements)
    mutable["graph"] = graph
    integrity = dict(mutable.get("integrity") or {})
    integrity["elements_digest"] = graph["elements_digest"]
    integrity["file_source_digests"] = {
        role: entry["files_digest"]
        for role, entry in _file_source_digest_view(
            mutable.get("file_sources") or {}
        ).items()
    }
    mutable["integrity"] = integrity
    integrity["payload_digest"] = payload_digest_of(mutable)
    return mutable

def build_snapshot_payload(
    *,
    semantic_binding: Mapping[str, Any],
    method_binding: Mapping[str, Any],
    evaluator_binding: Mapping[str, Any],
    scope_binding: Mapping[str, Any],
    elements: Sequence[Mapping[str, Any]],
    file_sources: Mapping[str, Mapping[str, Any]],
    provenance: Mapping[str, Any],
    declared_evaluation_key: str | None = None,
    created_at: str | None = None,
    build_notes: Sequence[str] = (),
) -> dict[str, Any]:
    """Compose one ``de4sdv-method-snapshot/v1`` payload with digests filled.

    ``file_sources`` maps a role (``candidate`` / ``tested``) to
    ``{"revision": <full SHA>, "roots": [prefix, ...], "files": {path: bytes}}``.
    """
    if not elements:
        raise SnapshotCompletenessError(
            ["graph.elements is empty; a snapshot must carry the validated graph payload"]
        )
    if provenance.get("kind") != PROVENANCE_VALIDATED:
        raise SnapshotValidationError(
            [
                "provenance.kind must be "
                f"{PROVENANCE_VALIDATED!r}; a snapshot cannot authorize itself"
            ]
        )
    handle = provenance.get("validation_handle") or {}
    missing_handle = [field for field in _HANDLE_FIELDS if not str(handle.get(field) or "")]
    if missing_handle:
        raise SnapshotValidationError(
            [f"provenance.validation_handle is missing {missing_handle}"]
        )
    unknown_roles = sorted(set(file_sources) - set(ROLES))
    if unknown_roles:
        raise SnapshotValidationError([f"unknown file-source roles {unknown_roles}"])

    encoded_sources: dict[str, dict[str, Any]] = {}
    for role, entry in file_sources.items():
        revision = str(entry.get("revision") or "")
        if not _FULL_SHA.match(revision):
            raise SnapshotValidationError(
                [f"file_sources.{role}.revision must be a full 40-character SHA"]
            )
        raw_files = entry.get("files") or {}
        encoded_sources[role] = {
            "revision": revision,
            "roots": [str(root) for root in entry.get("roots") or ()],
            "files": _encode_files(raw_files),
        }

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "created_at": created_at,
        "semantic_binding": dict(semantic_binding),
        "method_binding": dict(method_binding),
        "evaluator_binding": dict(evaluator_binding),
        "scope_binding": dict(scope_binding),
        "graph": {"element_count": len(elements), "elements": [dict(e) for e in elements]},
        "file_sources": encoded_sources,
        "completeness": {
            "roots": {
                role: sorted(str(root) for root in entry.get("roots") or ())
                for role, entry in file_sources.items()
            },
            "declared_evaluation_key": declared_evaluation_key,
            "build_notes": [str(note) for note in build_notes],
        },
        "integrity": {},
        "provenance": dict(provenance),
    }
    return finalize_payload(payload)


def write_snapshot(payload: Mapping[str, Any], path: Path) -> None:
    path.write_text(json.dumps(payload, indent=1, sort_keys=False), encoding="utf-8")


def read_snapshot(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SnapshotValidationError([f"{path}: unreadable snapshot payload: {error}"])
    if not isinstance(value, dict):
        raise SnapshotValidationError([f"{path}: snapshot payload is not a JSON object"])
    return value


# ---------------------------------------------------------------------------
# Trusted provenance and load-time expectations
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TrustedSnapshotBinding:
    """The retained validation record of the exact privileged run.

    Values are read from the controlled importer artifacts (validated candidate
    binding + export identity) and from the retained snapshot-build record.
    They are supplied out-of-band by the caller; the snapshot must match them,
    never the other way around.

    ``expected_payload_digest`` is the externally trusted canonical payload
    digest of the build output: the loader recomputes the payload digest from
    the snapshot's own contents and refuses unless it equals this externally
    supplied value. It transitively covers every semantic snapshot section
    (graph elements, file inventories, scope/method/evaluator bindings,
    completeness and provenance). The optional per-section digests add
    independently trusted anchors; they never override the payload binding.
    """

    git_commit: str
    sysml_project_id: str
    sysml_commit_id: str
    scope: str
    export_sha256: str
    expected_payload_digest: str
    binding_sha256: str | None = None
    validation_run: str = ""
    expected_elements_digest: str | None = None
    expected_candidate_files_digest: str | None = None
    expected_tested_files_digest: str | None = None


@dataclass(frozen=True)
class SnapshotExpectations:
    """Identity/scope/content expectations the loaded snapshot must satisfy."""

    method_id: str
    contract_id: str
    contract_digest: str
    policy_bundle_id: str
    evaluator_build: str
    scope_id: str
    increment_id: str
    usage_ids: tuple[str, ...]
    profiles: tuple[str, ...]
    declared_tested_head: str | None
    candidate_roots: tuple[str, ...]
    tested_roots: tuple[str, ...]
    expected_evaluation_key: str | None = None


@dataclass(frozen=True)
class LoadedSnapshot:
    """Validated snapshot inputs — the canonical evaluator input, offline."""

    schema: str
    revision: RevisionIdentity
    elements: tuple[Mapping[str, Any], ...]
    sources: Mapping[str, "SnapshotFileSource"]
    provenance: Mapping[str, Any]
    payload_digest: str
    declared_evaluation_key: str | None


class SnapshotFileSource:
    """Read-only :class:`FileSource` over one role's captured file inventory.

    Semantics mirror the live sources (git/directory): ``read_bytes`` returns
    ``None`` for absent paths, ``list_files`` returns ``None`` for absent
    prefixes, and ``exists`` treats a directory prefix with content as present.
    """

    def __init__(self, files: Mapping[str, bytes]) -> None:
        self._files = {str(path): bytes(blob) for path, blob in files.items()}

    def read_bytes(self, relative_path: str) -> bytes | None:
        return self._files.get(relative_path)

    def exists(self, relative_path: str) -> bool:
        if relative_path in self._files:
            return True
        prefix = relative_path.rstrip("/") + "/"
        return any(path.startswith(prefix) for path in self._files)

    def list_files(self, prefix: str) -> list[str] | None:
        normalized = prefix.rstrip("/")
        matches = sorted(
            path
            for path in self._files
            if path == normalized or path.startswith(normalized + "/")
        )
        return matches or None


# ---------------------------------------------------------------------------
# Loading (fail closed, revision-explicit, trust-checked)
# ---------------------------------------------------------------------------


def _require_full_sha(value: str, label: str) -> None:
    if not _FULL_SHA.match(str(value or "")):
        raise ValueError(
            f"{label} must be a full 40-character lowercase SHA, got {value!r}"
        )


def _require_sha256(value: str | None, label: str, *, optional: bool = False) -> None:
    if optional and not value:
        return
    if not _SHA256.match(str(value or "")):
        raise ValueError(
            f"{label} must be a lowercase SHA-256 hex digest, got {value!r}"
        )


def _roots_cover(declared: Sequence[str], required: Sequence[str]) -> list[str]:
    missing: list[str] = []
    for root in required:
        normalized = str(root).rstrip("/")
        if not any(
            normalized == str(candidate).rstrip("/")
            or normalized.startswith(str(candidate).rstrip("/") + "/")
            for candidate in declared
        ):
            missing.append(str(root))
    return missing


def load_snapshot(
    path: Path,
    *,
    trusted: TrustedSnapshotBinding | None,
    expectations: SnapshotExpectations,
) -> LoadedSnapshot:
    """Validate and load one snapshot; every failure refuses (never falls back).

    Verification order: structure -> trusted record -> provenance handle ->
    identity -> expectations (method/evaluator/scope/completeness) -> integrity
    digests -> externally trusted content binding -> file decode. The
    externally trusted expected payload digest is compared against a value
    recomputed from the snapshot's contents and is never read from the
    snapshot itself. Any mismatch raises; no partial load is returned.
    """
    payload = read_snapshot(path)

    # 1. Structure.
    if payload.get("schema") != SCHEMA:
        raise _refuse(
            SnapshotValidationError,
            path,
            [f"schema: {payload.get('schema')!r} is not {SCHEMA!r}"],
        )
    missing_sections = [name for name in REQUIRED_SECTIONS if name not in payload]
    if missing_sections:
        raise _refuse(
            SnapshotCompletenessError,
            path,
            [f"missing required sections: {missing_sections}"],
        )

    # 2. Trusted record.
    if trusted is None:
        raise _refuse(
            SnapshotValidationError,
            path,
            [
                "no trusted validation record supplied; a self-attested snapshot "
                "cannot be loaded (the controlled validated importer chain is the "
                "trust origin)"
            ],
        )
    _require_full_sha(trusted.git_commit, "trusted git_commit")
    _require_sha256(trusted.export_sha256, "trusted export_sha256")
    _require_sha256(trusted.binding_sha256, "trusted binding_sha256", optional=True)
    _require_sha256(
        trusted.expected_payload_digest, "trusted expected_payload_digest"
    )
    _require_sha256(
        trusted.expected_elements_digest,
        "trusted expected_elements_digest",
        optional=True,
    )
    _require_sha256(
        trusted.expected_candidate_files_digest,
        "trusted expected_candidate_files_digest",
        optional=True,
    )
    _require_sha256(
        trusted.expected_tested_files_digest,
        "trusted expected_tested_files_digest",
        optional=True,
    )

    # 3. Provenance kind and handle.
    provenance = payload["provenance"]
    if provenance.get("kind") != PROVENANCE_VALIDATED:
        raise _refuse(
            SnapshotValidationError,
            path,
            [
                f"provenance.kind {provenance.get('kind')!r}: only "
                f"{PROVENANCE_VALIDATED!r} provenance is loadable; a snapshot "
                "cannot authorize itself with self-attested provenance"
            ],
        )
    handle = provenance.get("validation_handle") or {}
    missing_handle = [field for field in _HANDLE_FIELDS if not str(handle.get(field) or "")]
    if missing_handle:
        raise _refuse(
            SnapshotValidationError,
            path,
            [f"provenance.validation_handle is missing {missing_handle}"],
        )

    # 4. Identity: snapshot semantic binding and handle vs the trusted record.
    binding = payload["semantic_binding"]
    identity_reasons: list[str] = []
    for field, expected, observed in (
        ("semantic_binding.git_commit", trusted.git_commit, binding.get("git_commit")),
        ("semantic_binding.sysml_project_id", trusted.sysml_project_id, binding.get("sysml_project_id")),
        ("semantic_binding.sysml_commit_id", trusted.sysml_commit_id, binding.get("sysml_commit_id")),
        ("semantic_binding.scope", trusted.scope, binding.get("scope")),
        ("handle.git_commit", trusted.git_commit, handle.get("git_commit")),
        ("handle.sysml_project_id", trusted.sysml_project_id, handle.get("sysml_project_id")),
        ("handle.sysml_commit_id", trusted.sysml_commit_id, handle.get("sysml_commit_id")),
        ("handle.scope", trusted.scope, handle.get("scope")),
        ("handle.export_sha256", trusted.export_sha256, handle.get("export_sha256")),
    ):
        if str(expected) != str(observed):
            identity_reasons.append(
                f"{field}: retained record requires {expected!r}, snapshot declares {observed!r}"
            )
    if trusted.binding_sha256 and str(handle.get("binding_sha256")) != str(trusted.binding_sha256):
        identity_reasons.append(
            "handle.binding_sha256: retained record requires "
            f"{trusted.binding_sha256!r}, snapshot declares {handle.get('binding_sha256')!r}"
        )
    if not _FULL_SHA.match(str(binding.get("git_commit") or "")):
        identity_reasons.append(
            "semantic_binding.git_commit must be a full 40-character lowercase SHA"
        )
    if identity_reasons:
        raise _refuse(SnapshotValidationError, path, identity_reasons)

    # 5. Expectations: method, evaluator, scope, completeness.
    method = payload["method_binding"]
    evaluator = payload["evaluator_binding"]
    scope = payload["scope_binding"]
    expectation_reasons: list[str] = []
    for field, expected in (
        ("method_id", expectations.method_id),
        ("contract_id", expectations.contract_id),
        ("contract_digest", expectations.contract_digest),
        ("policy_bundle_id", expectations.policy_bundle_id),
    ):
        observed = method.get(field)
        if str(expected) != str(observed):
            expectation_reasons.append(
                f"method_binding.{field}: approved selection requires {expected!r}, "
                f"snapshot declares {observed!r}"
            )
    if str(evaluator.get("build_id")) != str(expectations.evaluator_build):
        expectation_reasons.append(
            f"evaluator_binding.build_id: required {expectations.evaluator_build!r}, "
            f"snapshot declares {evaluator.get('build_id')!r}"
        )
    if str(scope.get("scope_id")) != str(expectations.scope_id):
        expectation_reasons.append(
            f"scope_binding.scope_id: expected {expectations.scope_id!r}, "
            f"snapshot declares {scope.get('scope_id')!r}"
        )
    if str(scope.get("increment_id")) != str(expectations.increment_id):
        expectation_reasons.append(
            f"scope_binding.increment_id: expected {expectations.increment_id!r}, "
            f"snapshot declares {scope.get('increment_id')!r}"
        )
    if sorted(str(item) for item in scope.get("usage_ids") or ()) != sorted(
        expectations.usage_ids
    ):
        expectation_reasons.append(
            "scope_binding.usage_ids: declared usage set differs from the approved scope"
        )
    if tuple(str(item) for item in scope.get("profiles") or ()) != tuple(
        expectations.profiles
    ):
        expectation_reasons.append(
            "scope_binding.profiles: declared profile order/set differs from the approved scope"
        )
    if expectations.declared_tested_head and str(
        scope.get("declared_tested_head") or ""
    ) != str(expectations.declared_tested_head):
        expectation_reasons.append(
            "scope_binding.declared_tested_head: expected "
            f"{expectations.declared_tested_head!r}, snapshot declares "
            f"{scope.get('declared_tested_head')!r}"
        )
    file_sources = payload["file_sources"]
    completeness_reasons: list[str] = []
    missing_roles = [
        role
        for role in ROLES
        if role not in file_sources and role in _expected_roles(expectations)
    ]
    if missing_roles:
        completeness_reasons.append(
            f"file_sources: required roles {missing_roles} are missing from the snapshot"
        )
    if ROLE_CANDIDATE in file_sources:
        declared_roots = file_sources[ROLE_CANDIDATE].get("roots") or []
        uncovered = _roots_cover(declared_roots, expectations.candidate_roots)
        if uncovered:
            completeness_reasons.append(
                f"file_sources.candidate.roots do not cover required roots {uncovered}"
            )
    if ROLE_TESTED in file_sources:
        declared_roots = file_sources[ROLE_TESTED].get("roots") or []
        uncovered = _roots_cover(declared_roots, expectations.tested_roots)
        if uncovered:
            completeness_reasons.append(
                f"file_sources.tested.roots do not cover required roots {uncovered}"
            )
        tested_revision = str(file_sources[ROLE_TESTED].get("revision") or "")
        if expectations.declared_tested_head and tested_revision != str(
            expectations.declared_tested_head
        ):
            expectation_reasons.append(
                "file_sources.tested.revision: declared tested head requires "
                f"{expectations.declared_tested_head!r}, snapshot captured "
                f"{tested_revision!r}"
            )
    if completeness_reasons:
        raise _refuse(SnapshotCompletenessError, path, completeness_reasons)
    if expectation_reasons:
        raise _refuse(SnapshotValidationError, path, expectation_reasons)

    if expectations.expected_evaluation_key is not None and str(
        payload["completeness"].get("declared_evaluation_key") or ""
    ) != expectations.expected_evaluation_key:
        raise _refuse(
            SnapshotIntegrityError,
            path,
            [
                "declared evaluation key does not reproduce: expected "
                f"{expectations.expected_evaluation_key!r}, snapshot declares "
                f"{payload['completeness'].get('declared_evaluation_key')!r}"
            ],
        )

    # 6. Integrity: recompute from the payload body; never trust stored values.
    integrity = payload["integrity"]
    graph = payload["graph"]
    integrity_reasons: list[str] = []
    recomputed_elements = elements_digest(graph.get("elements") or [])
    if str(integrity.get("elements_digest")) != recomputed_elements:
        integrity_reasons.append(
            "elements_digest: stored "
            f"{integrity.get('elements_digest')!r} does not match recomputed "
            f"{recomputed_elements!r}"
        )
    if int(graph.get("element_count") or 0) != len(graph.get("elements") or []):
        integrity_reasons.append(
            "graph.element_count does not match the serialized element payload"
        )
    if not (graph.get("elements") or []):
        integrity_reasons.append("graph.elements is empty")
    # Per-file digests: decode and hash every stored blob BEFORE computing any
    # digest over their content, so undecodable content is reported as such.
    decoded_sources: dict[str, dict[str, bytes]] = {}
    for role, entry in file_sources.items():
        decoded: dict[str, bytes] = {}
        for file_path, file_entry in (entry.get("files") or {}).items():
            try:
                blob = base64.b64decode(
                    str(file_entry.get("content_b64") or ""), validate=True
                )
            except (binascii.Error, ValueError) as error:
                integrity_reasons.append(
                    f"file_sources.{role}.{file_path}: undecodable content ({error})"
                )
                continue
            observed = hashlib.sha256(blob).hexdigest()
            if observed != str(file_entry.get("sha256")):
                integrity_reasons.append(
                    f"file_sources.{role}.{file_path}: content digest mismatch "
                    f"(declared {file_entry.get('sha256')!r}, observed {observed!r})"
                )
                continue
            decoded[file_path] = blob
        decoded_sources[role] = decoded
    recomputed_files: dict[str, dict[str, Any]] = {}
    if not integrity_reasons:
        recomputed_files = _file_source_digest_view(file_sources)
        stored_file_digests = integrity.get("file_source_digests") or {}
        for role, view in recomputed_files.items():
            if str(stored_file_digests.get(role)) != view["files_digest"]:
                integrity_reasons.append(
                    f"file_sources.{role}: files_digest mismatch "
                    f"(stored {stored_file_digests.get(role)!r}, recomputed {view['files_digest']!r})"
                )
    if integrity_reasons:
        raise _refuse(SnapshotIntegrityError, path, integrity_reasons)
    recomputed_payload = payload_digest_of(payload)
    if str(integrity.get("payload_digest")) != recomputed_payload:
        raise _refuse(
            SnapshotIntegrityError,
            path,
            [
                "payload_digest: stored "
                f"{integrity.get('payload_digest')!r} does not match recomputed "
                f"{recomputed_payload!r}"
            ],
        )

    # 6b. Externally trusted content binding. The canonical payload digest —
    # recomputed from the snapshot's own contents — must equal the value
    # supplied OUTSIDE the snapshot by the retained build/evidence process. A
    # bundle cannot authorize its own contents: content modified and re-forged
    # to internal digest consistency still fails here, and the trusted value is
    # never read from the snapshot being validated.
    external_reasons: list[str] = []
    if recomputed_payload != trusted.expected_payload_digest:
        external_reasons.append(
            "expected_payload_digest: externally trusted content binding "
            f"{trusted.expected_payload_digest!r} does not match the snapshot "
            f"contents {recomputed_payload!r}"
        )
    if (
        trusted.expected_elements_digest
        and recomputed_elements != trusted.expected_elements_digest
    ):
        external_reasons.append(
            "expected_elements_digest: externally trusted value "
            f"{trusted.expected_elements_digest!r} does not match the snapshot "
            f"contents {recomputed_elements!r}"
        )
    for label, role in (
        ("expected_candidate_files_digest", ROLE_CANDIDATE),
        ("expected_tested_files_digest", ROLE_TESTED),
    ):
        expected = getattr(trusted, label)
        if not expected:
            continue
        observed = (recomputed_files.get(role) or {}).get("files_digest")
        if observed != expected:
            external_reasons.append(
                f"{label}: externally trusted value {expected!r} does not match "
                f"the snapshot {role} file inventory {observed!r}"
            )
    if external_reasons:
        raise _refuse(SnapshotValidationError, path, external_reasons)

    # 7. Loaded inputs.
    elements = tuple(dict(element) for element in graph.get("elements") or [])
    sources = {
        role: SnapshotFileSource(decoded_sources.get(role, {})) for role in file_sources
    }
    return LoadedSnapshot(
        schema=SCHEMA,
        revision=RevisionIdentity(
            git_commit=str(binding["git_commit"]),
            sysml_project_id=str(binding["sysml_project_id"]),
            sysml_commit_id=str(binding["sysml_commit_id"]),
            scope=str(binding["scope"]),
        ),
        elements=elements,
        sources=sources,
        provenance=provenance,
        payload_digest=str(integrity["payload_digest"]),
        declared_evaluation_key=payload["completeness"].get("declared_evaluation_key"),
    )


def _expected_roles(expectations: SnapshotExpectations) -> tuple[str, ...]:
    roles: list[str] = [ROLE_CANDIDATE]
    if expectations.tested_roots or expectations.declared_tested_head:
        roles.append(ROLE_TESTED)
    return tuple(roles)


# ---------------------------------------------------------------------------
# Availability is a separate operational projection (MC-28)
# ---------------------------------------------------------------------------


def source_availability(
    *,
    source_label: str,
    probe: Callable[[], bool],
    observed_at: str,
) -> dict[str, Any]:
    """Report current source availability WITHOUT touching any evaluated result.

    A historical evaluated payload is never rewritten by later unavailability;
    this projection exists so callers can report retention/availability
    separately from the (reproducible) conformance result.
    """
    diagnostics: list[str] = []
    available = False
    try:
        available = bool(probe())
    except Exception as error:  # noqa: BLE001 - availability must never raise
        diagnostics.append(f"availability probe failed: {error}")
    return {
        "source": source_label,
        "available": available,
        "observed_at": observed_at,
        "affects_historical_result": False,
        "diagnostics": diagnostics,
        "note": (
            "availability is a separate operational projection; it never "
            "rewrites a historical evaluated result"
        ),
    }
