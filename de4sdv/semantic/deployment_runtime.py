"""Deployed semantic runtime: four inputs and one startup check.

The production surfaces (the Ask viewer and the semantic MCP server) start
from exactly four things:

1. a clean checkout of the deployed commit;
2. the deployment's revision binding (``de4sdv.revision-binding/v2``) with
   its ingestion-validated kernel bindings (ADR 0011) and the served-model
   record the importer wrote after the full-payload read-back;
3. the deployed SysML v2 API;
4. one startup check, :func:`verify_startup`.

The startup check refuses unless:

- **right commit:** the checkout HEAD is the application revision, the
  binding is bound to the expected model revision (validation passed, scope
  ``full-model``), and the application revision descends from it;
- **clean tree:** ``git status --porcelain`` is empty;
- **same semantic authority:** the ``sai-`` identity recomputed from the
  checkout (:func:`build_model_contract`) equals the binding's;
- **served model = validated export:** the binding records the served model
  (:class:`~de4sdv.sysml_api.served_model.ServedModel`), and no corpus is
  adopted unless its content digest is exactly that record's. This last part
  runs when the corpus loads, from the API or from a snapshot: a refused
  snapshot is a miss, a refused API corpus raises
  :class:`~de4sdv.sysml_api.errors.ServedModelMismatchError` on every call.
  When the binding also records the export documents
  (:class:`~de4sdv.sysml_api.export_documents.ExportDocuments`, the source
  documents and the external references of the same export), the corpus must
  hold exactly the elements they list. The method view reads them; a binding
  without them still starts, and the checks that need them stay method side.

Every refusal is loud and nothing falls back: the Ask viewer serves no
semantic answers and the MCP server does not start. There is no bundle, no
closure, no activation step and no authority selector (owner decision
2026-10-11, release ceremony retired). Rollback is a redeploy of the previous
release.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from de4sdv.sysml_api.errors import RevisionMismatchError, ServedModelMismatchError
from de4sdv.sysml_api.revisions import RevisionBinding
from de4sdv.sysml_api.served_model import element_digests, digest_of_element_digests

from .kernel_contract import KernelContract
from .model_authority_runtime import (
    MODEL_AUTHORITY,
    ModelAuthorityQueryService,
    assemble_model_services,
    model_facade,
)
from .model_contract import build_model_contract

ROOT = Path(__file__).resolve().parents[2]
_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
ROLLBACK = "redeploy the previous release"


class StartupCheckError(ValueError):
    """The deployed runtime refuses to start (fail closed)."""


def _refuse(message: str) -> StartupCheckError:
    return StartupCheckError(f"startup check refused: {message}")


def _git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}
    return subprocess.run(["git", "-c", f"safe.directory={root}", "-C", str(root), *args],
                          capture_output=True, text=True, timeout=120, env=env)


@dataclass(frozen=True)
class StartupCheck:
    """What the startup check verified (the runtime is built from it)."""

    root: Path
    head: str
    application_revision: str
    expected_git_revision: str
    binding: RevisionBinding
    binding_sha256: str
    contract: KernelContract

    def report(self) -> dict[str, Any]:
        served = self.binding.served_model
        assert served is not None  # verify_startup refuses a binding without it
        return {
            "kind": MODEL_AUTHORITY,
            "startup_check": "passed",
            "semantic_authority": self.contract.identity.id,
            "application_git_commit": self.head,
            "git_commit": self.binding.git_commit,
            "sysml_project_id": self.binding.sysml_project_id,
            "sysml_commit_id": self.binding.sysml_commit_id,
            "binding_sha256": self.binding_sha256,
            "served_model": served.content_sha256,
            "source_export_sha256": served.source_export_sha256,
            "export_documents": (None if self.binding.export_documents is None
                                 else self.binding.export_documents.content_sha256),
            "element_count": served.element_count,
            "refused": sorted(self.contract.refused),
            "rollback": ROLLBACK,
        }


def _require_sha(value: str, label: str) -> str:
    if not _FULL_SHA.fullmatch(str(value or "")):
        raise _refuse(f"{label} must be a full 40-character lowercase Git SHA, got {value!r}")
    return value


def _check_checkout(root: Path, application_revision: str) -> str:
    head = _git(root, "rev-parse", "HEAD")
    if head.returncode != 0:
        raise _refuse(f"wrong commit: {root} is not a Git checkout ({head.stderr.strip()})")
    actual = head.stdout.strip()
    if actual != application_revision:
        raise _refuse(f"wrong commit: checkout HEAD {actual} is not the application "
                      f"revision {application_revision}")
    status = _git(root, "status", "--porcelain")
    if status.returncode != 0:
        raise _refuse(f"dirty tree: git status failed in {root} ({status.stderr.strip()})")
    changed = [line for line in status.stdout.splitlines() if line.strip()]
    if changed:
        raise _refuse(f"dirty tree: {len(changed)} changed or untracked path(s) in {root}: "
                      + "; ".join(changed[:5]))
    return actual


def _load_binding(binding_path: Path) -> tuple[RevisionBinding, str]:
    try:
        raw = Path(binding_path).read_bytes()
        document = json.loads(raw)
        if not isinstance(document, dict):
            raise ValueError("revision binding must be a JSON object")
        binding = RevisionBinding.from_dict(document)
    except (OSError, ValueError) as exc:
        raise _refuse(f"revision binding {binding_path} is unusable: {exc}") from exc
    return binding, "sha256:" + hashlib.sha256(raw).hexdigest()


def verify_startup(root: "str | Path" = ROOT, *, binding_path: "str | Path",
                   expected_git_revision: str,
                   application_revision: str | None = None) -> StartupCheck:
    """The one startup check (fail closed; see the module docstring)."""
    root = Path(root).resolve()
    expected = _require_sha(expected_git_revision, "expected model revision")
    application = _require_sha(application_revision or expected, "application revision")
    head = _check_checkout(root, application)
    binding, binding_sha256 = _load_binding(Path(binding_path))
    try:
        binding.require_current(expected)
    except RevisionMismatchError as exc:
        raise _refuse(f"wrong commit: the deployment binding is not a validated binding "
                      f"of {expected}: {exc}") from exc
    if binding.scope != "full-model":
        raise _refuse(f"the deployment binding scope is {binding.scope!r}, not full-model")
    if application != expected:
        ancestry = _git(root, "merge-base", "--is-ancestor", expected, application)
        if ancestry.returncode != 0:
            raise _refuse(f"wrong commit: the model revision {expected} is not an ancestor "
                          f"of the application revision {application}")
    if binding.served_model is None:
        raise _refuse("the deployment binding records no served model; re-import the "
                      "validated export with this revision's importer")
    contract = build_model_contract(root)
    if contract.identity != binding.semantic_authority:
        raise _refuse(f"wrong semantic authority: the checkout builds {contract.identity.id}, "
                      f"the deployment binding records {binding.semantic_authority.id}")
    return StartupCheck(root=root, head=head, application_revision=application,
                        expected_git_revision=expected, binding=binding,
                        binding_sha256=binding_sha256, contract=contract)


class DeployedQueryService(ModelAuthorityQueryService):
    """The production query service: answers only from the validated export."""

    #: Set by :func:`build_deployment_runtime`.
    startup: StartupCheck | None = None
    #: ``pending`` until a corpus loads, then ``passed`` or ``failed: <why>``.
    _served_model_check: str = "pending"
    #: The one corpus object verified against the served-model record.
    _verified_corpus: list[Any] | None = None
    #: A refused API corpus: re-raised on every call without re-reading the
    #: API (recovery is a process restart, like a failed warm-up).
    _refusal: str | None = None

    def _served_model_problem(self, elements: list[Any]) -> str | None:
        served = self.binding.served_model
        if served is None:
            return "the deployment binding records no served model"
        try:
            digests = element_digests(elements)
        except ValueError as exc:
            return f"the corpus is malformed: {exc}"
        actual = digest_of_element_digests(digests)
        if actual != served.content_sha256 or len(digests) != served.element_count:
            return (f"the corpus holds {len(digests)} elements with content {actual}; the "
                    f"deployment binding records {served.element_count} elements with "
                    f"{served.content_sha256} (export sha256 {served.source_export_sha256})")
        documents = self.binding.export_documents
        if documents is not None:
            return documents.problem_for(elements)
        return None

    def verify_corpus(self, elements: list[Any]) -> None:
        """Refuse any corpus that is not the validated export (memoized by object)."""
        if self._verified_corpus is not None and elements is self._verified_corpus:
            return
        problem = self._served_model_problem(elements)
        if problem is not None:
            raise ServedModelMismatchError(
                f"served model differs from the validated export: {problem}")
        self._verified_corpus = elements
        self._served_model_check = "passed"

    def corpus_matches(self, elements: list[Any]) -> bool:
        """True when ``elements`` is the validated export (snapshot adoption)."""
        try:
            self.verify_corpus(elements)
        except ServedModelMismatchError:
            return False
        return True

    def _guard(self, project_id: str, commit_id: str, elements: list[Any]) -> None:
        if (str(project_id), str(commit_id)) != (str(self.binding.sysml_project_id),
                                                   str(self.binding.sysml_commit_id)):
            raise ServedModelMismatchError(
                f"only the bound revision {self.binding.sysml_project_id}/"
                f"{self.binding.sysml_commit_id} is served, not {project_id}/{commit_id}")
        self.verify_corpus(elements)

    def _elements(self) -> list[dict[str, Any]]:
        if self._refusal is not None:
            raise ServedModelMismatchError(self._refusal)
        try:
            elements = super()._elements()
            self.verify_corpus(elements)
        except ServedModelMismatchError as exc:
            # The repository's snapshot path treats a refusal as a miss, so a
            # refusal that reaches here is the API corpus itself.
            self._refusal = str(exc)
            self._served_model_check = f"failed: {exc}"
            raise
        return elements

    def authority_status(self) -> dict[str, Any]:
        """The served semantic authority (``/ask-status.json`` and MCP stderr)."""
        report = self.startup.report() if self.startup is not None else {"kind": MODEL_AUTHORITY}
        return {**report, "semantic_authority_id": self.semantic_authority_id,
                "served_model_check": self._served_model_check}


def build_deployment_runtime(root: "str | Path" = ROOT, *, api_url: str,
                             binding_path: "str | Path", expected_git_revision: str,
                             application_revision: str | None = None,
                             api_timeout: float = 600.0,
                             repository: Any = None) -> DeployedQueryService:
    """Run the startup check, then assemble the production services.

    ``repository`` replaces the API transport (tests and the release evidence
    over the export); production passes ``api_url`` only. Every failure
    raises before the API is read.
    """
    check = verify_startup(root, binding_path=binding_path,
                           expected_git_revision=expected_git_revision,
                           application_revision=application_revision)
    if repository is None:
        from de4sdv.sysml_api import client, repository as repository_module

        repository = repository_module.SysMLRepository(client.ApiClient(api_url, timeout=api_timeout))
    facade = model_facade(check.root, contract=check.contract)
    service = assemble_model_services(facade, check.binding, repository,
                                      expected_git_revision=check.expected_git_revision,
                                      service_class=DeployedQueryService)
    service.startup = check
    repository.install_corpus_guard(service._guard)
    return service


__all__ = ["DeployedQueryService", "ROLLBACK", "StartupCheck", "StartupCheckError",
           "build_deployment_runtime", "verify_startup"]
