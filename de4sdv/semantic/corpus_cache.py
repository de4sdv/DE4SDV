"""Exact-revision element-corpus snapshot reused across process restarts.

One snapshot per validated API revision and semantic authority, stored
outside the repository (default ``~/.cache/de4sdv/semantic-snapshots``;
``DE4SDV_SEMANTIC_SNAPSHOT_DIR`` selects another directory). It turns the
cold start of a semantic MCP server (the full element listing of the bound
revision, several minutes over the public API) into a local file load after
the first run on a machine.

A snapshot is a derived read cache, never a second semantic authority:

- it is consulted only after the runtime's revision gates pass (exact
  expected Git SHA and semantic authority, ``_require_valid_revision``) and
  only when its recorded identity matches the running runtime exactly;
- the identity binds the API endpoint (as a SHA-256 digest; credentials never
  enter the file), the Git commit, the SysML project/commit ids, a canonical
  digest of the revision binding (its ingestion-validated kernel bindings
  included), the binding's semantic-authority identity, the runtime's
  semantic authority id and the snapshot format;
- any doubt (checksum mismatch, identity drift, older format, malformed,
  truncated, duplicate or missing element UUIDs) is a miss that falls back
  to the exact API load; a snapshot is never partially adopted;
- writes are atomic (unique temporary file, ``os.replace``) with a checksum
  sidecar, and installing the lazy hook performs no I/O, so protocol
  handshakes never wait for the corpus.

Salvaged from draft PR #284 (identity contract moved from the retired
authored-ontology identity to the model-built semantic authority).
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

#: v4: semantic-authority-bound identity (model-built contract). Older
#: snapshots are a miss by construction, never reinterpreted.
CORPUS_SNAPSHOT_FORMAT = 4


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


def _directory(directory: Path | str | None) -> Path:
    return snapshot_directory() if directory is None else Path(directory)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _endpoint_digest(service: Any) -> str:
    """SHA-256 of the API base URL: binds the endpoint without exposing credentials."""
    client = getattr(getattr(service, "repository", None), "client", None)
    base_url = str(getattr(client, "base_url", "") or "")
    return hashlib.sha256(base_url.encode("utf-8")).hexdigest()


def _binding_digest(service: Any) -> str:
    """Canonical digest of the revision binding (kernel bindings included)."""
    binding = service.binding
    payload = binding.to_dict() if callable(getattr(binding, "to_dict", None)) else {
        key: str(getattr(binding, key, "") or "")
        for key in ("git_repository", "git_commit", "sysml_project_id", "sysml_commit_id")
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _semantic_authority(service: Any) -> dict[str, Any]:
    identity = getattr(service.binding, "semantic_authority", None)
    to_dict = getattr(identity, "to_dict", None)
    return to_dict() if callable(to_dict) else {}


def corpus_identity(service: Any) -> dict[str, Any]:
    """The exact identity a snapshot must carry to be loadable."""
    binding = service.binding
    return {
        "format": CORPUS_SNAPSHOT_FORMAT,
        "api_endpoint_digest": _endpoint_digest(service),
        "git_commit": str(binding.git_commit),
        "sysml_project_id": str(binding.sysml_project_id),
        "sysml_commit_id": str(binding.sysml_commit_id),
        "binding_digest": _binding_digest(service),
        "semantic_authority": _semantic_authority(service),
        "semantic_authority_id": str(getattr(service, "semantic_authority_id", "") or ""),
    }


def corpus_snapshot_path(service: Any, *, directory: Path | str | None = None) -> Path:
    """Snapshot file of one exact revision and runtime semantic authority."""
    authority = str(getattr(service, "semantic_authority_id", "") or "unknown")
    component = hashlib.sha256(authority.encode("utf-8")).hexdigest()[:12]
    return _directory(directory) / f"{service.binding.sysml_commit_id}.{component}.json"


def write_corpus_snapshot(service: Any, elements: object, *, directory: Path | str | None = None) -> Path:
    """Atomically write a snapshot and its checksum sidecar (validated corpus)."""
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
        sidecar_tmp.write_text(hashlib.sha256(main_tmp.read_bytes()).hexdigest(), encoding="utf-8")
        os.replace(sidecar_tmp, sidecar)
        os.replace(main_tmp, path)
    finally:
        for leftover in (main_tmp, sidecar_tmp):
            try:
                leftover.unlink(missing_ok=True)
            except OSError:
                pass
    return path


def load_corpus_snapshot(service: Any, *, directory: Path | str | None = None) -> list[dict[str, Any]] | None:
    """The checksum- and identity-verified snapshot corpus, or None (any doubt)."""
    path = corpus_snapshot_path(service, directory=directory)
    try:
        raw = path.read_bytes()
        expected = path.with_suffix(".json.sha256").read_text(encoding="utf-8").strip()
        if hashlib.sha256(raw).hexdigest() != expected:
            return None
        data = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            return None
        for key, value in corpus_identity(service).items():
            if data.get(key) != value:
                return None
        try:
            validated = validated_element_corpus(data.get("elements"))
        except ValueError:
            return None
        if data.get("element_count") != len(validated):
            return None
        return validated
    except (OSError, ValueError):
        return None


def _bound_revision(service: Any, project_id: str, commit_id: str) -> bool:
    binding = service.binding
    return (str(project_id), str(commit_id)) == (str(binding.sysml_project_id), str(binding.sysml_commit_id))


def install_corpus_snapshot(service: Any, *, directory: Path | str | None = None) -> bool:
    """Install the lazy snapshot-first corpus hook on the service's repository.

    Nothing is read or written at install time. The first listing of the
    bound revision tries the identity-bound snapshot after the revision
    gates pass; a miss performs the exact API load and writes the result
    back best-effort. Only the bound revision is ever served or written.
    Returns False (and installs nothing) when the service has no repository
    supporting the hook.
    """
    repository = getattr(service, "repository", None)
    if repository is None or not hasattr(repository, "install_corpus_source"):
        return False

    def source(project_id: str, commit_id: str):
        if not _bound_revision(service, project_id, commit_id):
            return None
        service._require_valid_revision()  # gates before any snapshot I/O
        try:
            return load_corpus_snapshot(service, directory=directory)
        except OSError:
            return None

    def sink(project_id: str, commit_id: str, elements) -> None:
        if not _bound_revision(service, project_id, commit_id):
            return
        try:
            service._require_valid_revision()
        except RevisionMismatchError:
            return
        try:
            write_corpus_snapshot(service, elements, directory=directory)
        except (OSError, ValueError):
            pass

    repository.install_corpus_source(source, sink=sink)
    return True
