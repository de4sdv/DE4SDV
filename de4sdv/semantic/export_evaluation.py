"""Evaluate an increment offline, over a full-model JSON export.

The same evaluation the semantic service runs over the API runs over an
export of the same revision: the same model-built contract (from this
checkout), the same production traversal, the same gates, the same
predicates. Two input modes, both read-only and offline:

- **export plus validated revision binding** (the existing offline path of
  the pilot runner): the binding must be a revision binding v2 for the
  export's exact Git commit and carry this checkout's semantic authority;
  its ingestion-validated kernel bindings and SysML project/commit identity
  are used, so the evaluation key equals the API evaluation of that
  revision;
- **export alone** (an export snapshot, for example of a pull-request head):
  kernel identity is validated from the export by the same validator the
  ingestion uses; the revision identity is the Git commit with scope
  ``export-snapshot`` and no SysML API identity.

Any identity mismatch refuses the evaluation; nothing falls back to another
revision or to names.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping

from de4sdv.sysml_api.baseline import BaselineExportBundle
from de4sdv.sysml_api.revisions import KernelElementBinding, RevisionBinding

from .increment_evaluation import IncrementEvaluation, evaluate_increment
from .increment_scope import ModelView
from .method_evaluator import RevisionIdentity
from .method_pilot import establish_candidate_identity

ROOT = Path(__file__).resolve().parents[2]
EXPORT_SNAPSHOT_SCOPE = "export-snapshot"


class ExportEvaluationRefused(RuntimeError):
    """The export or binding cannot be evaluated as one exact revision."""


@dataclass(frozen=True)
class ExportSnapshot:
    """One export, its revision identity and its kernel bindings."""

    elements: list[dict[str, Any]]
    sources: Mapping[str, str]
    revision: RevisionIdentity
    kernel_bindings: tuple[KernelElementBinding, ...]
    identity_mode: str
    export_sha256: str


def _contract(root: Path) -> Any:
    from .model_contract import build_model_contract

    return build_model_contract(root)


def load_export_snapshot(
    export_path: Path, binding_path: Path | None = None, *, root: Path = ROOT
) -> ExportSnapshot:
    """Load and identity-check one export (and its binding, when given)."""
    raw = Path(export_path).read_bytes()
    export = json.loads(raw)
    try:
        bundle = BaselineExportBundle.from_dict(export)
    except ValueError as error:
        raise ExportEvaluationRefused(f"export refused: {error}") from error
    elements = list(export["elements"])
    sources = dict(bundle.element_sources)
    digest = hashlib.sha256(raw).hexdigest()
    contract = _contract(root)
    if binding_path is not None:
        document = json.loads(Path(binding_path).read_text(encoding="utf-8"))
        try:
            binding = RevisionBinding.from_dict(document)
        except ValueError as error:
            raise ExportEvaluationRefused(f"revision binding refused: {error}") from error
        identity, diagnostics = establish_candidate_identity(binding=document, export=export)
        if identity is None:
            raise ExportEvaluationRefused("; ".join(diagnostics))
        if binding.semantic_authority != contract.identity:
            raise ExportEvaluationRefused(
                f"revision binding carries semantic authority {binding.semantic_authority.id}; "
                f"this checkout builds {contract.identity.id}"
            )
        return ExportSnapshot(
            elements=elements, sources=sources, export_sha256=digest,
            revision=RevisionIdentity(binding.git_commit, binding.sysml_project_id,
                                      binding.sysml_commit_id, binding.scope),
            kernel_bindings=tuple(binding.kernel_bindings),
            identity_mode="validated-revision-binding",
        )
    from .validation import validate_ontology_bindings

    report = validate_ontology_bindings(contract, elements, sources)
    # Same rule as the ingestion importer: a class whose binding resolved to
    # exactly one element carries that element, its file and declaration.
    kernel = tuple(
        KernelElementBinding(
            ontology_class=entry.ontology_class,
            element_id=entry.element_ids[0],
            source_file=entry.mapping["file"],
            declaration=entry.mapping["declaration"],
        )
        for entry in report.entries
        if entry.status == "mapped" and len(entry.element_ids) == 1
    )
    git_commit = str(export.get("git_commit") or "")
    return ExportSnapshot(
        elements=elements, sources=sources, export_sha256=digest,
        revision=RevisionIdentity(git_commit, "", "", EXPORT_SNAPSHOT_SCOPE),
        kernel_bindings=kernel,
        identity_mode="export-validated-kernel-bindings",
    )


def export_view(snapshot: ExportSnapshot, *, root: Path = ROOT) -> ModelView:
    """The production traversal over the export (unverified facade of this checkout)."""
    from .model_authority_runtime import ModelAuthorityTraversal, model_facade
    from .relationship_successor import route_successor_bindings

    facade = model_facade(Path(root))
    index, _routes = route_successor_bindings(
        facade.profile, SimpleNamespace(kernel_bindings=snapshot.kernel_bindings)
    )
    traversal = ModelAuthorityTraversal(facade, kernel_bindings=index)
    return ModelView(snapshot.elements, traversal, sources=snapshot.sources)


def evaluate_export(
    export_path: Path,
    increment_id: str,
    *,
    binding_path: Path | None = None,
    root: Path = ROOT,
) -> tuple[ExportSnapshot, IncrementEvaluation]:
    """Load one export and evaluate one increment against its method gates."""
    snapshot = load_export_snapshot(export_path, binding_path, root=root)
    view = export_view(snapshot, root=root)
    return snapshot, evaluate_increment(view, increment_id, revision=snapshot.revision)
