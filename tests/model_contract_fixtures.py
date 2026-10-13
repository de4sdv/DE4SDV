"""Shared fixtures for tests of the model-built kernel contract (O4 Wave C2).

The authored ontology YAML no longer exists. Tests that need the real kernel
contract use :func:`model_contract` (``KernelContract.from_layers`` over this
checkout); tests that need a revision binding use :func:`binding_dict` (a
revision binding v2 carrying the contract's semantic-authority identity);
tests that exercise the runtime over a synthetic API use :func:`model_service`
(the model facade plus the production service assembly). Synthetic
contracts are built with ``KernelContract.from_records``; no copy of any
model or ontology file is used.
"""
from __future__ import annotations

import hashlib
from functools import lru_cache
from pathlib import Path
from typing import Any

from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.sysml_api.revisions import (
    BINDING_SCHEMA,
    SEMANTIC_AUTHORITY_SCHEMA,
    RevisionBinding,
    SemanticAuthorityIdentity,
)

REPO_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def model_contract() -> KernelContract:
    """The model-built kernel contract of this checkout (cached)."""
    return KernelContract.from_layers(REPO_ROOT)


def semantic_authority_dict() -> dict[str, Any]:
    return model_contract().identity.to_dict()


def synthetic_identity(tag: str = "synthetic") -> SemanticAuthorityIdentity:
    """A well-formed, clearly synthetic semantic-authority identity."""
    digest = hashlib.sha256(tag.encode()).hexdigest()
    return SemanticAuthorityIdentity(SEMANTIC_AUTHORITY_SCHEMA, "sai-" + digest[:32],
                                     ((f"synthetic/{tag}.json", "sha256:" + digest),))


def binding_dict(*, git_commit: str = "a" * 40, sysml_project_id: str = "pid",
                 sysml_commit_id: str = "cid", scope: str = "full-model",
                 kernel_bindings: list[dict[str, str]] | tuple = (),
                 semantic_authority: dict[str, Any] | None = None,
                 **extra: Any) -> dict[str, Any]:
    """A revision binding v2 document (defaults: the model contract identity)."""
    value = {
        "schema": BINDING_SCHEMA,
        "git_repository": extra.pop("git_repository", "fixture"),
        "git_commit": git_commit,
        "sysml_project_id": sysml_project_id,
        "sysml_commit_id": sysml_commit_id,
        "import_timestamp": extra.pop("import_timestamp", "2026-10-08T00:00:00Z"),
        "import_tool_version": extra.pop("import_tool_version", "synthetic"),
        "semantic_validation": extra.pop("semantic_validation", "passed"),
        "semantic_authority": semantic_authority or semantic_authority_dict(),
        "scope": scope,
        "kernel_bindings": [dict(item) for item in kernel_bindings],
    }
    value.update(extra)
    return value


def binding(**kwargs: Any) -> RevisionBinding:
    return RevisionBinding.from_dict(binding_dict(**kwargs))


@lru_cache(maxsize=1)
def _facade_parts():
    from de4sdv.semantic import model_authority_runtime as mar

    facade = mar.model_facade(REPO_ROOT)
    return facade._contract, facade._routing, facade.profile, facade._components


def model_facade():
    """A fresh model facade over this checkout (parts cached; no binding)."""
    from de4sdv.semantic import model_authority_runtime as mar

    contract, routing, successor, components = _facade_parts()
    return mar.ModelAuthorityFacade(contract=contract, routing=routing,
                                    successor_contract=successor, components=components)


def model_service(revision_binding: RevisionBinding, repository: Any, *,
                  expected_git_revision: str | None = None, facade: Any = None, **kwargs: Any):
    """The production service assembly over a synthetic repository."""
    from de4sdv.semantic import model_authority_runtime as mar

    return mar.assemble_model_services(
        facade if facade is not None else model_facade(), revision_binding, repository,
        expected_git_revision=expected_git_revision or revision_binding.git_commit, **kwargs)


ADMISSION_MANIFESTS = (
    "de4sdv/semantic/contract-data/class-definition-admission.yaml",
    "de4sdv/semantic/contract-data/kernel-vocabulary-admission.yaml",
)


@lru_cache(maxsize=1)
def _admission_rows() -> dict[str, dict[str, Any]]:
    import yaml

    rows: dict[str, dict[str, Any]] = {}
    for relative in ADMISSION_MANIFESTS:
        for row in yaml.safe_load((REPO_ROOT / relative).read_text(encoding="utf-8"))["admitted"]:
            rows[row["identity"]] = row
    return rows


def admission_row(identity: str) -> dict[str, Any]:
    """The reviewed admission-manifest row of one identity (batch 1 or 2)."""
    return _admission_rows()[identity]


def owned_definition_documentation(source: str, declaration: str) -> str:
    """Require nonempty immediately owned Documentation, not copied prose."""
    from de4sdv.semantic import authority_inventory as inventory

    block, bodyless = inventory.declaration_block(source, declaration)
    if not block or bodyless:
        raise ValueError(f"{declaration}: missing current definition home")
    text = " ".join(inventory._owned_doc_bodies(block))
    if not text.strip():
        raise ValueError(f"{declaration}: empty current model-owned documentation")
    return text


def current_definition(identity: str) -> str:
    """Read current model-owned meaning for synthetic runtime consumers.

    This cleanup retired the live copied-definition oracle. Admission rows locate model
    documentation; neither frozen authored prose nor generated JSON is a
    fallback. This helper is not an expected-output oracle for generators.
    """
    row = admission_row(identity)
    if "declaration" in row:
        locator = row["declaration"]
        source = (REPO_ROOT / locator["file"]).read_text(encoding="utf-8")
        text = owned_definition_documentation(source, locator["declaration"])
    else:
        from de4sdv.semantic.definition_projection_batch2 import _Model, _definition_text

        definition, _ = _definition_text(_Model(REPO_ROOT), row)
        text = definition["documentation"]
    if not text.strip():
        raise ValueError(f"{identity}: empty current model-owned documentation")
    return text


def manifest_held_values(row: dict[str, Any]) -> dict[str, Any]:
    """The contract fields one kernel-vocabulary manifest row holds itself
    (owner decision D9): class pins, or a relation with its mechanics.
    Definition text is excluded; the model owns it."""
    values: dict[str, Any] = {}
    if row["semantic_kind"] == "class":
        grounding = row["grounding"]
        values.update(kernel_mapping=grounding["kernel_mapping"],
                      sub_class_of=grounding["sub_class_of"],
                      disjoint_with=list(grounding["disjoint_with"]))
    elif row["admission_class"] != "successor":
        values["relation"] = dict(row["relation"])
        if "mechanics" in row:
            values["mechanics"] = dict(row["mechanics"])
    return values


__all__ = ["admission_row", "manifest_held_values",
           "current_definition", "owned_definition_documentation", "REPO_ROOT", "binding", "binding_dict", "model_contract",
           "model_facade", "model_service", "semantic_authority_dict", "synthetic_identity"]
