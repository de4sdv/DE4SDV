"""O4 definition-candidate runtime seam — explicit, non-default assembly.

Tests: an explicit candidate assembly resolves admitted identities through
the provider while the production default stays byte-unchanged; the explicit
authority paths refuse to combine; the deployment provenance label is correct
for legacy, o3 and candidate authority ids.
"""
from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from de4sdv.semantic.authority_ids import LEGACY_AUTHORITY_ID
from de4sdv.semantic.definition_candidate import (
    DefinitionCandidate,
    load_definition_candidate,
)
from de4sdv.semantic.definition_candidate_provider import DefinitionCandidateProvider
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.runtime import build_semantic_runtime

ONTOLOGY = REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"


def _contract() -> KernelContract:
    return KernelContract.load(ONTOLOGY)


def _candidate() -> DefinitionCandidate:
    return load_definition_candidate(REPO_ROOT)


def _provider() -> DefinitionCandidateProvider:
    return DefinitionCandidateProvider(legacy=_contract(), candidate=_candidate())


def _binding_file(tmp_path: Path) -> Path:
    document = {
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": "a" * 40,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "import_timestamp": "2026-09-27T00:00:00Z",
        "import_tool_version": "test",
        "semantic_validation": "passed",
        "scope": "fixture",
        "ontology": _contract().identity.to_dict(),
    }
    path = tmp_path / "binding.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _assemble(tmp_path: Path, **extra):
    return build_semantic_runtime(
        api_url="http://localhost:1",
        binding_path=_binding_file(tmp_path),
        expected_git_revision="a" * 40,
        ontology_path=ONTOLOGY,
        **extra,
    )


def test_candidate_assembly_resolves_admitted_and_delegates(tmp_path):
    candidate = _candidate()
    provider = DefinitionCandidateProvider(legacy=_contract(), candidate=candidate)
    service = _assemble(tmp_path, definition_candidate_authority=provider)
    assert service.semantic_authority_id == (
        f"definition-candidate:{candidate.source_revision}"
    )
    assert service.contract is provider
    contract_row = candidate.row_for("Requirement")["grounding"][
        "kernel_binding_contract"
    ]
    resolved = service.contract.class_mapping("Requirement")
    assert resolved.file == contract_row["source_file"]
    assert resolved.declaration == contract_row["declaration"]
    legacy = _contract()
    unadmitted = sorted(set(legacy.classes) - set(candidate.identities))[0]
    assert service.contract.class_mapping(unadmitted) == legacy.class_mapping(
        unadmitted
    )
    assert (
        getattr(service.impact_service, "semantic_authority_id")
        == provider.authority_id
    )


def test_default_assembly_remains_legacy(tmp_path):
    service = _assemble(tmp_path)
    assert service.semantic_authority_id == LEGACY_AUTHORITY_ID
    assert isinstance(service.contract, KernelContract)


def test_explicit_authority_paths_cannot_combine(tmp_path):
    with pytest.raises(ValueError, match="never both"):
        _assemble(
            tmp_path,
            semantic_authority={},
            definition_candidate_authority=_provider(),
        )


def test_candidate_authority_requires_non_empty_id(tmp_path):
    with pytest.raises(ValueError, match="authority_id"):
        _assemble(tmp_path, definition_candidate_authority=object())


def test_provenance_labels_by_authority_kind(tmp_path):
    provider = _provider()
    service = _assemble(tmp_path, definition_candidate_authority=provider)
    label = service._semantic_authority()
    assert label["kind"] == "definition-candidate"
    assert label["id"] == provider.authority_id
    assert "migrated_scope" not in label

    legacy_service = _assemble(tmp_path)
    assert legacy_service._semantic_authority() == {
        "id": LEGACY_AUTHORITY_ID,
        "kind": "legacy",
        "note": (
            "authored KernelContract authority (production default; "
            "unchanged behavior)"
        ),
    }

    o3_service = replace(service, semantic_authority_id="o3:bundle-abc")
    assert o3_service._semantic_authority() == {
        "id": "o3:bundle-abc",
        "kind": "o3",
        "migrated_scope": "reviewed-13-identity-subset",
        "note": (
            "explicitly selected O3 authority bundle (Semantic Projection "
            "semantics + API Representation Profile mechanics); every "
            "other identity delegates to the legacy authored "
            "KernelContract; verified against this exact revision and "
            "revision binding at startup"
        ),
    }
