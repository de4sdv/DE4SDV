"""Committed-candidate production path (frozen baseline Section 12).

Implements the V1 candidate path: selected full Git commit -> isolated
checkout -> export only committed content -> record exact identity ->
isolated candidate import/read-back -> candidate revision binding.

Boundaries:
- dirty working trees are outside V1: uncommitted content never leaks into
  an export, and an explicit dirty-tree evaluation request is refused;
- concurrent candidates never overwrite one another's identities;
- candidate production never changes the published accepted-baseline
  pointer and never implies review approval;
- a candidate binding is emitted only after semantic validation passed.
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from de4sdv.sysml_api.revisions import OntologyIdentity, RevisionBinding

_FULL_SHA_LEN = 40


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True
    ).strip()


def _is_dirty(repo: Path) -> bool:
    status = _git(repo, "status", "--porcelain")
    return bool(status.strip())


@dataclass(frozen=True)
class ExportIdentity:
    git_commit: str
    tree_was_dirty: bool
    """True when the working tree had uncommitted changes at export time.

    This records the tree state, NOT whether dirty content was excluded:
    exclusion is structural (blobs are read from the selected commit), so
    dirty content cannot leak regardless of this flag.
    """
    tool_identity: str

    def __getitem__(self, key: str) -> Any:
        try:
            return getattr(self, key)
        except AttributeError as exc:  # pragma: no cover - defensive
            raise KeyError(key) from exc


def prepare_isolated_checkout(
    repository: Path, git_commit: str, worktree_path: Path
) -> Path:
    """Create an isolated clean worktree at the exact selected commit.

    The worktree is the export source for candidate production: Syside runs
    against THIS checkout, so uncommitted content in the originating
    repository cannot leak (frozen baseline Section 12 step 1). The caller
    owns worktree_path cleanup.
    """
    if len(git_commit) != _FULL_SHA_LEN:
        raise ValueError("selected commit must be a full 40-character SHA")
    try:
        resolved = _git(repository, "rev-parse", f"{git_commit}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"commit {git_commit} does not resolve in this repository"
        ) from exc
    if resolved != git_commit:
        raise ValueError(f"commit {git_commit} does not resolve in this repository")
    if worktree_path.exists():
        raise ValueError(f"worktree path already exists: {worktree_path}")
    subprocess.run(
        [
            "git", "-C", str(repository), "worktree", "add",
            "--detach", str(worktree_path), git_commit,
        ],
        check=True,
        capture_output=True,
    )
    head = _git(worktree_path, "rev-parse", "HEAD")
    if head != git_commit:
        raise RuntimeError(
            f"isolated checkout HEAD {head} does not match selected {git_commit}"
        )
    if _is_dirty(worktree_path):
        raise RuntimeError("isolated checkout is dirty; this is a setup defect")
    return worktree_path


def export_selected_commit(
    repository: Path, git_commit: str, *, allow_dirty: bool = False
) -> tuple[dict[str, list[dict[str, Any]]], ExportIdentity]:
    """Export ONLY the selected commit's tracked content.

    Reads committed blobs straight from the Git object database for the
    requested full SHA, so uncommitted working-tree edits and untracked
    files cannot leak into the export (MC-36). An explicit dirty-tree
    evaluation request is refused as unsupported in V1.
    """
    if len(git_commit) != _FULL_SHA_LEN:
        raise ValueError("selected commit must be a full 40-character SHA")
    try:
        resolved = _git(repository, "rev-parse", f"{git_commit}^{{commit}}")
    except subprocess.CalledProcessError as exc:
        raise ValueError(
            f"commit {git_commit} does not resolve in this repository"
        ) from exc
    if resolved != git_commit:
        raise ValueError(f"commit {git_commit} does not resolve in this repository")

    dirty = _is_dirty(repository)
    if allow_dirty:
        raise RuntimeError(
            "dirty working tree evaluation is refused in V1: only committed "
            "revisions are evaluated; commit or stash the working tree first"
        )
    # Export BOTH validated model roots (textual-notation-of-model and
    # model-based-product-line-engineering/product-models — AGENTS.md model
    # roots) by reading committed blobs from the object database.
    tracked = _git(
        repository,
        "ls-tree",
        "-r",
        "--name-only",
        "-z",
        git_commit,
        "--",
        "textual-notation-of-model",
        "model-based-product-line-engineering/product-models",
    )
    source_docs: dict[str, list[dict[str, Any]]] = {}
    for entry in tracked.split("\0"):
        if not entry:
            continue
        blob = subprocess.check_output(
            ["git", "-C", str(repository), "show", f"{git_commit}:{entry}"]
        )
        source_docs[entry] = [{"_committed_source": blob.decode("utf-8", "replace")}]
    identity = ExportIdentity(
        git_commit=git_commit,
        tree_was_dirty=dirty,
        tool_identity="git-object-read/v1",
    )
    return source_docs, identity


@dataclass(frozen=True)
class CandidateRecord:
    git_commit: str
    sysml_project_id: str
    sysml_commit_id: str
    scope: str


class CandidateRegistry:
    """Isolated candidate identities plus the published accepted-baseline pointer.

    MC-37: candidate records never overwrite each other, and candidate
    production never mutates the published accepted-baseline selection.
    """

    def __init__(self) -> None:
        self._candidates: dict[str, CandidateRecord] = {}
        self._published: CandidateRecord | None = None

    def register_candidate(
        self, *, git_commit: str, project_id: str, commit_id: str
    ) -> CandidateRecord:
        existing = self._candidates.get(git_commit)
        if existing is not None:
            if (
                existing.sysml_project_id != project_id
                or existing.sysml_commit_id != commit_id
            ):
                raise ValueError(
                    f"candidate for {git_commit} already registered with a "
                    "different project/commit identity; concurrent candidates "
                    "must not overwrite each other"
                )
            return existing
        record = CandidateRecord(
            git_commit=git_commit,
            sysml_project_id=project_id,
            sysml_commit_id=commit_id,
            scope="candidate",
        )
        self._candidates[git_commit] = record
        return record

    def get_candidate(self, git_commit: str) -> CandidateRecord:
        return self._candidates[git_commit]

    def set_published_accepted_baseline(
        self, *, git_commit: str, project_id: str, commit_id: str
    ) -> None:
        self._published = CandidateRecord(
            git_commit=git_commit,
            sysml_project_id=project_id,
            sysml_commit_id=commit_id,
            scope="published-accepted",
        )

    def published_accepted_baseline(self) -> CandidateRecord | None:
        return self._published

    def emit_binding(
        self,
        *,
        git_commit: str,
        project_id: str,
        commit_id: str,
        semantic_validation: str,
        git_repository: str,
        import_timestamp: str,
        import_tool_version: str,
        ontology_path: str = "",
        ontology_sha256: str = "",
    ) -> RevisionBinding:
        """Emit a candidate revision binding only after validation passed.

        Provenance is real, not placeholder: repository identity, import
        timestamp, and tool version are required, as is the ontology
        contract identity validated during the candidate's import. The
        emitted binding round-trips through RevisionBinding.from_dict and
        carries the same authority tuple as a full-model binding (scope
        differs, authority does not).
        """
        if semantic_validation != "passed":
            raise RuntimeError(
                "candidate binding emission refused: semantic validation "
                f"has not passed (status {semantic_validation!r})"
            )
        missing = [
            name
            for name, value in (
                ("git_repository", git_repository),
                ("import_timestamp", import_timestamp),
                ("import_tool_version", import_tool_version),
                ("ontology_path", ontology_path),
                ("ontology_sha256", ontology_sha256),
            )
            if not value
        ]
        if missing:
            raise RuntimeError(
                "candidate binding emission refused: required provenance "
                f"missing: {sorted(missing)}"
            )
        record = self.register_candidate(
            git_commit=git_commit, project_id=project_id, commit_id=commit_id
        )
        return RevisionBinding(
            git_repository=git_repository,
            git_commit=git_commit,
            sysml_project_id=record.sysml_project_id,
            sysml_commit_id=record.sysml_commit_id,
            import_timestamp=import_timestamp,
            import_tool_version=import_tool_version,
            semantic_validation=semantic_validation,
            ontology=OntologyIdentity(
                path=ontology_path, sha256=ontology_sha256
            ),
            scope="candidate",
        )
