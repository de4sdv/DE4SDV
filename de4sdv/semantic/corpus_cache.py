"""Persistent exact-revision element-corpus cache shared by Ask and MCP.

One snapshot per validated API revision: the element corpus of the bound
SysML project/commit, stored outside the repository (default
``~/.cache/de4sdv/semantic-snapshots``, deployment-selected through
``DE4SDV_SEMANTIC_SNAPSHOT_DIR``).

A snapshot is a derived read cache, never a second semantic authority:

- it is only ever consulted AFTER the runtime's revision gates pass
  (``SemanticQueryService._require_valid_revision``: exact expected Git SHA
  and ontology contract identity) and only when its recorded identity
  matches the running runtime EXACTLY;
- any doubt — checksum mismatch, identity drift, old format, malformed or
  truncated payload, missing/duplicate element UUIDs, partial cache — is a
  MISS that falls back to the exact API load; a snapshot is never accepted
  as governing authority and never partially adopted;
- the identity binds the API endpoint (as a SHA-256 digest; credentials
  never enter the file), the exact Git commit and SysML project/commit ids,
  a canonical digest of the revision binding (which includes the
  ingestion-validated kernel bindings), the ontology identity, the explicit
  semantic authority id, and the snapshot format version (bumped when the
  identity contract changes, so old snapshots are ignored, never
  reinterpreted).

Writes are atomic (unique temp file + ``os.replace``) with a checksum
sidecar; a single process performs at most one retrieval per revision
(the shared repository memoizes and serializes the first load); the
optional lazy hook (:func:`install_corpus_snapshot`) is installed on the
shared repository so server handshakes never block on the cold load.

This module is distinct from ``de4sdv.semantic.snapshot`` (the Lane D
method-conformance snapshot): different scope, different trust model.
"""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from de4sdv.sysml_api.errors import RevisionMismatchError
from de4sdv.sysml_api.repository import validated_element_corpus

#: v3: endpoint/binding/ontology-bound identity — v2 snapshots (and anything
#: older) are a miss by construction, never reinterpreted.
CORPUS_SNAPSHOT_FORMAT = 3


def snapshot_directory() -> Path:
    """Deployment-selected snapshot directory (created on demand)."""
    directory = Path(
        os.environ.get(
            "DE4SDV_SEMANTIC_SNAPSHOT_DIR",
            str(Path.home() / ".cache" / "de4sdv" / "semantic-snapshots"),
        )
    )
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def _resolve_directory(directory: Path | str | None) -> Path:
    if directory is None:
        return snapshot_directory()
    return Path(directory)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _endpoint_digest(service) -> str:
    """SHA-256 of the API base URL — a digest only, never the URL itself.

    The URL may carry credentials (userinfo); the digest binds the endpoint
    identity without exposing them in the snapshot.
    """
    repository = getattr(service, "repository", None)
    client = getattr(repository, "client", None)
    base_url = str(getattr(client, "base_url", "") or "")
    return hashlib.sha256(base_url.encode("utf-8")).hexdigest()


def _binding_digest(service) -> str:
    """Canonical digest of the revision binding (kernel bindings included)."""
    binding = getattr(service, "binding", None)
    to_dict = getattr(binding, "to_dict", None)
    if callable(to_dict):
        payload: object = to_dict()
    else:
        payload = {
            field: str(getattr(binding, field, "") or "")
            for field in (
                "git_repository",
                "git_commit",
                "sysml_project_id",
                "sysml_commit_id",
            )
        }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _ontology_identity(service) -> dict[str, str]:
    binding = getattr(service, "binding", None)
    ontology = getattr(binding, "ontology", None)
    to_dict = getattr(ontology, "to_dict", None)
    value = to_dict() if callable(to_dict) else None
    if isinstance(value, dict):
        return {
            "path": str(value.get("path") or ""),
            "sha256": str(value.get("sha256") or ""),
        }
    return {"path": "", "sha256": ""}


def corpus_identity(service) -> dict[str, Any]:
    """The exact identity a snapshot must match to be loadable."""
    binding = service.binding
    return {
        "format": CORPUS_SNAPSHOT_FORMAT,
        "api_endpoint_digest": _endpoint_digest(service),
        "git_commit": str(binding.git_commit),
        "sysml_project_id": str(binding.sysml_project_id),
        "sysml_commit_id": str(binding.sysml_commit_id),
        "binding_digest": _binding_digest(service),
        "ontology": _ontology_identity(service),
        "semantic_authority_id": str(
            getattr(service, "semantic_authority_id", "") or ""
        ),
    }


def authority_component(service) -> str:
    """Stable filename component for the explicit semantic authority id."""
    authority = str(getattr(service, "semantic_authority_id", "") or "unknown")
    return hashlib.sha256(authority.encode("utf-8")).hexdigest()[:12]


def corpus_snapshot_path(
    service, *, directory: Path | str | None = None
) -> Path:
    """Snapshot file for one exact revision + semantic authority."""
    return _resolve_directory(directory) / (
        f"{service.binding.sysml_commit_id}.{authority_component(service)}.json"
    )


def write_corpus_snapshot(
    service,
    elements: object,
    *,
    directory: Path | str | None = None,
) -> Path:
    """Atomically write a snapshot + checksum sidecar (validated payload).

    Concurrency-safe: unique temp names per writer, ``os.replace`` for the
    final swap. A malformed corpus is refused (``ValueError``) before any
    file is touched.
    """
    validated = validated_element_corpus(elements)
    path = corpus_snapshot_path(service, directory=directory)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        **corpus_identity(service),
        "element_count": len(validated),
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "elements": validated,
    }
    token = f"{os.getpid()}.{uuid.uuid4().hex[:8]}"
    main_tmp = path.with_name(f"{path.name}.tmp.{token}")
    sidecar = path.with_suffix(".json.sha256")
    sidecar_tmp = sidecar.with_name(f"{sidecar.name}.tmp.{token}")
    try:
        main_tmp.write_text(json.dumps(payload), encoding="utf-8")
        digest = hashlib.sha256(main_tmp.read_bytes()).hexdigest()
        sidecar_tmp.write_text(digest, encoding="utf-8")
        os.replace(sidecar_tmp, sidecar)
        os.replace(main_tmp, path)  # atomic on POSIX
    finally:
        for leftover in (main_tmp, sidecar_tmp):
            try:
                leftover.unlink(missing_ok=True)
            except OSError:
                pass
    return path


def load_corpus_snapshot(
    service, *, directory: Path | str | None = None
) -> list[dict[str, Any]] | None:
    """Checksum- and identity-verified snapshot, or None (any doubt = miss)."""
    path = corpus_snapshot_path(service, directory=directory)
    try:
        raw = path.read_bytes()
        expected_digest = path.with_suffix(".json.sha256").read_text(
            encoding="utf-8"
        ).strip()
        if hashlib.sha256(raw).hexdigest() != expected_digest:
            return None
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return None
        for key, value in corpus_identity(service).items():
            if data.get(key) != value:
                return None
        elements = data.get("elements")
        if not isinstance(elements, list):
            return None
        try:
            validated = validated_element_corpus(elements)
        except ValueError:
            return None
        if data.get("element_count") != len(validated):
            return None
        return validated
    except (OSError, ValueError):
        return None


def hydrate_service_caches(service, elements: object) -> None:
    """Adopt a validated corpus into the shared repository + service cache.

    The repository is the single choke point every consumer reads through
    (service queries, impact service, ontology binder), so hydrating it —
    through the explicit validated ``SysMLRepository.adopt_elements``
    method — is what removes the refetch after a snapshot hit. The method
    refuses to displace a listing already loaded from the authoritative API
    in this process; in that case the repository's own listing is served.
    """
    validated = validated_element_corpus(elements)
    binding = service.binding
    project_id = str(binding.sysml_project_id)
    commit_id = str(binding.sysml_commit_id)
    repository = getattr(service, "repository", None)
    adopted = False
    if repository is not None and hasattr(repository, "adopt_elements"):
        adopted = bool(repository.adopt_elements(project_id, commit_id, validated))
    if adopted or repository is None:
        service._element_cache = validated
    else:
        service._element_cache = repository.list_elements(project_id, commit_id)


def load_elements_with_snapshot(
    service, *, directory: Path | str | None = None
) -> list[dict[str, Any]]:
    """Binding checks FIRST, then snapshot, then the exact API load.

    A snapshot is never trusted without the runtime contract passing; a
    corrupted, stale, or malformed snapshot is ignored (the network load
    overwrites it). On a snapshot hit BOTH the shared repository and the
    service cache are hydrated; on a miss the exact API load runs and its
    result is written back best-effort.
    """
    service._require_valid_revision()
    if service._element_cache is not None:
        return service._element_cache
    snapshot = load_corpus_snapshot(service, directory=directory)
    if snapshot is not None:
        hydrate_service_caches(service, snapshot)
        if service._element_cache is not None:
            return service._element_cache
        return snapshot
    elements = service._elements()  # exact API load (binding enforced)
    try:
        write_corpus_snapshot(service, elements, directory=directory)
    except (OSError, ValueError):
        pass  # snapshot is an optimization, never a correctness gate
    return elements


def _requested_revision_matches_binding(
    service, project_id: str, commit_id: str
) -> bool:
    """True only for the exact (project, commit) this service is bound to.

    A snapshot is bound to one exact revision: it must never be served for,
    nor written from, a different requested revision. A different revision
    is always a miss that falls through to the exact API load.
    """
    binding = service.binding
    return (
        str(project_id),
        str(commit_id),
    ) == (
        str(binding.sysml_project_id),
        str(binding.sysml_commit_id),
    )


def install_corpus_snapshot(
    service, *, directory: Path | str | None = None
) -> None:
    """Install the lazy snapshot-first corpus hook on the shared repository.

    Nothing is read or written at install time: protocol handshakes never
    block on the cold load. The first element listing of the bound revision
    tries the identity-bound snapshot; on any doubt the repository performs
    the exact API load and the result is written back best-effort. Only the
    bound revision is ever served from the snapshot — a request for any
    other (project, commit) is a miss, never reinterpretation — and the
    runtime's revision gates (``_require_valid_revision``) run BEFORE any
    source/cache IO and before the sink write, so a stale runtime fails
    closed instead of serving or writing cached data.
    """
    repository = getattr(service, "repository", None)
    if repository is None or not hasattr(repository, "install_corpus_source"):
        raise ValueError(
            "service repository does not support the corpus snapshot hook"
        )

    def _prefetch(project_id: str, commit_id: str):
        if not _requested_revision_matches_binding(service, project_id, commit_id):
            # The bound snapshot must never be returned for another revision.
            return None
        # Revision gates BEFORE any snapshot IO: a stale runtime fails
        # closed instead of serving cached data.
        service._require_valid_revision()
        try:
            return load_corpus_snapshot(service, directory=directory)
        except OSError:
            return None

    def _save(project_id: str, commit_id: str, elements) -> None:
        if not _requested_revision_matches_binding(service, project_id, commit_id):
            # Another revision's corpus must never be written as the bound one.
            return
        try:
            # Revision gates BEFORE the write; the sink is best-effort, so a
            # stale runtime skips the write instead of failing the query.
            service._require_valid_revision()
        except RevisionMismatchError:
            return
        try:
            write_corpus_snapshot(service, elements, directory=directory)
        except (OSError, ValueError):
            pass

    repository.install_corpus_source(_prefetch, sink=_save)
