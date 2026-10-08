"""O4 definition layer — verified pair, fail-closed API closure, real consumers.

Since O4 Wave C2 the definition pair is a layer of the model-built kernel
contract: there is no legacy fallback provider, no explicit migration
selector and no separate runtime. This suite covers verified construction
from the real candidate pair, the fail-closed activation prerequisite (a fresh
exact-revision API closure whose binding carries the model-built semantic
authority), genuine consumption through the real API-binding / kernel-index /
traversal / query consumers of the model-authority service on a synthetic
validated closure, and the executable offline probe (schema v2) over the
real retained artifacts.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from model_contract_fixtures import binding_dict, model_contract, model_service

REPO_ROOT = Path(__file__).resolve().parents[1]

from de4sdv.semantic import model_authority_runtime as mar
from de4sdv.semantic.definition_candidate import load_definition_candidate
from de4sdv.semantic.definition_migration import (
    DefinitionMigrationError,
    load_definition_migration_authority,
    probe_definition_migration,
)
from de4sdv.semantic.kernel_contract import declaration_identity
from de4sdv.semantic.model_contract import O2_CHAIN_IDENTITIES
from de4sdv.semantic.query import SemanticQueryService
from de4sdv.semantic.validation import validate_ontology_bindings
from de4sdv.sysml_api.revisions import RevisionBinding

REVISION = "a" * 40


def _candidate():
    return load_definition_candidate(REPO_ROOT)


def _synthetic_closure() -> tuple[list[dict], list[dict]]:
    """Elements + validated bindings for every admitted identity (offline)."""
    candidate = _candidate()
    elements: list[dict] = []
    bindings: list[dict] = []
    for index, name in enumerate(candidate.identities):
        row = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        declared_name, expected_type = declaration_identity(row["declaration"])
        element_id_value = f"uuid-{index:02d}"
        elements.append(
            {
                "@id": element_id_value,
                "@type": expected_type,
                "declaredName": declared_name,
            }
        )
        bindings.append(
            {
                "ontology_class": name,
                "element_id": element_id_value,
                "source_file": row["source_file"],
                "declaration": row["declaration"],
            }
        )
    return elements, bindings


def _binding_document(tmp_path: Path, bindings: list[dict], **overrides) -> Path:
    document = binding_dict(git_commit=REVISION, sysml_project_id="project-1",
                            sysml_commit_id="commit-1", kernel_bindings=bindings,
                            git_repository="de4sdv/DE4SDV", **overrides)
    path = tmp_path / "binding.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _fake_binding(bindings: list[dict]) -> SimpleNamespace:
    return SimpleNamespace(
        semantic_validation="passed",
        scope="full-model",
        kernel_bindings=tuple(SimpleNamespace(**item) for item in bindings),
    )


class _FakeRepository:
    def __init__(self, elements: list[dict]) -> None:
        self._elements = elements
        self.calls = 0

    def list_elements(self, project_id: str, commit_id: str) -> list[dict]:
        self.calls += 1
        return list(self._elements)


# ---------------------------------------------------------------------------
# verified construction + frozen O2-chain disjointness
# ---------------------------------------------------------------------------


def test_authority_loads_verified_candidate_and_reports_closure_prerequisite():
    authority = load_definition_migration_authority(REPO_ROOT)
    candidate = _candidate()
    assert authority.authority_id == f"definition-candidate:{candidate.source_revision}"
    assert authority.identities == candidate.identities
    assert len(authority.identities) == 22
    assert authority.activation_eligible is False
    assert authority.closure.missing == tuple(sorted(candidate.identities))
    assert authority.closure.mismatched == ()
    reason = authority.activation_blocked_reason()
    assert "fresh exact-revision API closure" in reason
    assert "ingestion" in reason
    # the frozen O2-chain 13 identities are never overlapped
    assert set(authority.identities) & set(O2_CHAIN_IDENTITIES) == set()
    assert len(O2_CHAIN_IDENTITIES) == 13


def test_activation_fails_closed_without_fresh_exact_revision_closure(tmp_path):
    binding = RevisionBinding.load(_binding_document(tmp_path, bindings=[]))
    with pytest.raises(
        DefinitionMigrationError, match="fresh exact-revision API closure"
    ) as excinfo:
        load_definition_migration_authority(
            REPO_ROOT, binding=binding, require_activation_eligible=True,
            expected_git_revision=REVISION,
        )
    assert "22 of 22" in str(excinfo.value)


def test_closure_rejects_binding_disagreeing_with_the_candidate_pair():
    _elements, bindings = _synthetic_closure()
    tampered = [dict(item) for item in bindings]
    tampered[0]["declaration"] = "part def Mutated"
    authority = load_definition_migration_authority(
        REPO_ROOT, binding=_fake_binding(tampered)
    )
    assert authority.activation_eligible is False
    assert authority.closure.mismatched
    assert "disagrees with the candidate" in authority.activation_blocked_reason()


# ---------------------------------------------------------------------------
# genuine consumption through the real consumers (synthetic validated closure)
# ---------------------------------------------------------------------------


def test_migrated_definitions_consumed_by_real_consumers(tmp_path):
    elements, bindings = _synthetic_closure()
    binding = RevisionBinding.load(_binding_document(tmp_path, bindings=bindings))
    authority = load_definition_migration_authority(
        REPO_ROOT, binding=binding, require_activation_eligible=True,
        expected_git_revision=REVISION,
    )
    assert authority.activation_eligible is True
    provider = authority.provider
    fake = _FakeRepository(elements)
    service = model_service(binding, fake, expected_git_revision=REVISION)
    assert isinstance(service, SemanticQueryService)
    assert service.semantic_authority_id == service.contract.authority_id
    # runtime consumer wiring: binder, traversal and impact all receive the
    # model facade whose definition layer serves the verified pair
    assert service.binder.contract is service.contract
    assert service.traversal.contract is service.contract
    assert isinstance(service.impact_service, mar.ModelAuthorityImpactService)
    assert service.impact_service.semantic_authority_id == service.semantic_authority_id

    # API-binding consumer: candidate mapping + ingestion-validated UUID
    bound = service.binder.bind_class("Requirement")
    row = _candidate().row_for("Requirement")["grounding"]["kernel_binding_contract"]
    assert bound.kernel.file == row["source_file"]
    assert bound.kernel.declaration == row["declaration"]
    assert bound.sysml.element_id

    # kernel-index consumer: reverse direction resolves the governed class
    by_id = {element["@id"]: element for element in elements}
    index = service.binder.kernel_bindings
    assert index is not None
    assert index.ontology_class_for(bound.sysml.element_id, by_id) == "Requirement"
    candidate = _candidate()
    for name in candidate.identities:
        mapping = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        assert provider.class_mapping(name).file == mapping["source_file"]
        admitted_bound = service.binder.bind_class(name)
        assert admitted_bound.kernel.file == mapping["source_file"]
        assert admitted_bound.kernel.declaration == mapping["declaration"]
        assert index.ontology_class_for(admitted_bound.sysml.element_id, by_id) == name
        declared_name = declaration_identity(mapping["declaration"])[0]
        inspected = service.inspect_element(declared_name)
        assert inspected["element"]["element_id"] == admitted_bound.sysml.element_id

    # traversal consumer: runs the real strategy through the facade
    source = by_id[bound.sysml.element_id]
    assert service.traversal.traverse("verifiedBy", source, elements) == []

    # query consumer: runs offline against the stubbed repository
    status = service.model_status()
    assert status["current_baseline"] is True
    assert status["element_count"] == len(elements)
    assert status["semantic_authority"]["kind"] == "model"
    assert status["semantic_authority"]["id"] == service.semantic_authority_id

    declared_name = declaration_identity(row["declaration"])[0]
    resolved = service.resolve_element(declared_name)
    assert resolved["element"]["element_id"] == bound.sysml.element_id
    neighbors = service.semantic_neighbors(declared_name, predicates=["verifiedBy"])
    assert neighbors["query"] == "semantic_neighbors"
    assert (
        neighbors["provenance"][2]["source"]
        == f"semantic-authority://{model_contract().identity.id}"
    )

    # validation consumer classifies every admitted identity from the pair
    sources = {item["element_id"]: item["source_file"] for item in bindings}
    report = validate_ontology_bindings(provider, elements, sources)
    assert len(report.entries) == 22
    assert all(entry.status == "mapped" for entry in report.entries)


# ---------------------------------------------------------------------------
# executable offline probe over the real retained candidate artifacts
# ---------------------------------------------------------------------------


def test_probe_reports_real_artifacts_offline():
    report = probe_definition_migration(REPO_ROOT)
    assert report["schema"] == "de4sdv.o4-definition-migration-probe/v2"
    assert report["offline"] is True
    assert report["admitted_count"] == 22
    assert report["o2_chain_overlap"] == []
    assert report["activation_eligible"] is False
    assert "fresh exact-revision API closure" in report["activation_prerequisite"]
    assert report["closure"]["closed"] is False
    assert report["closure"]["missing"] == sorted(report["closure"]["missing"])
    assert len(report["closure"]["missing"]) == 22
    assert report["export"]["provided"] is False
    assert report["semantic_authority"] == model_contract().identity.to_dict()
    records = report["identities"]
    assert [record["identity"] for record in records] == sorted(
        record["identity"] for record in records
    )
    # real parity at this revision: candidate mappings equal the model-built
    # contract's definition layer
    assert all(record["contract_present"] for record in records)
    assert all(record["mapping_equal"] for record in records)
    assert all(record["validated_binding_element_id"] is None for record in records)


def test_probe_export_branch_marks_resolved_without_identity_claim():
    candidate = _candidate()
    elements: list[dict] = []
    sources: dict[str, str] = {}
    for index, name in enumerate(candidate.identities):
        row = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        declared_name, expected_type = declaration_identity(row["declaration"])
        element_id_value = f"exp-{index:02d}"
        elements.append(
            {
                "@id": element_id_value,
                "@type": expected_type,
                "declaredName": declared_name,
            }
        )
        sources[element_id_value] = row["source_file"]
    report = probe_definition_migration(
        REPO_ROOT, export=elements, element_sources=sources
    )
    assert report["export"]["provided"] is True
    assert report["export"]["resolved_count"] == 22
    assert all(record["export_resolved"] for record in report["identities"])


def test_closure_refuses_stale_binding_revision(tmp_path):
    _elements, bindings = _synthetic_closure()
    binding = RevisionBinding.load(_binding_document(tmp_path, bindings=bindings))
    with pytest.raises(DefinitionMigrationError, match="expected Git revision"):
        load_definition_migration_authority(
            REPO_ROOT, binding=binding, require_activation_eligible=True,
            expected_git_revision="b" * 40,
        )


def test_probe_cannot_assert_exact_revision_without_expected_revision(tmp_path):
    from de4sdv.sysml_api.revisions import RevisionBinding

    _elements, bindings = _synthetic_closure()
    report = probe_definition_migration(
        REPO_ROOT,
        binding=RevisionBinding.load(_binding_document(tmp_path, bindings)),
    )
    assert report["activation_eligible"] is False
    assert "expected" in report["activation_prerequisite"]


@pytest.mark.parametrize("defect", ["duplicate", "empty-id"])
def test_closure_refuses_ambiguous_or_empty_binding_identity(tmp_path, defect):
    from de4sdv.sysml_api.revisions import RevisionBinding

    _elements, bindings = _synthetic_closure()
    document = json.loads(_binding_document(tmp_path, bindings).read_text())
    if defect == "duplicate":
        document["kernel_bindings"].append(dict(document["kernel_bindings"][0]))
    else:
        document["kernel_bindings"][0]["element_id"] = "   "
    binding = RevisionBinding.from_dict(document)
    report = probe_definition_migration(REPO_ROOT, binding=binding)
    assert report["closure"]["closed"] is False
    assert report["closure"]["mismatched"]


def test_probe_refuses_foreign_semantic_authority_even_when_revision_and_rows_match(tmp_path):
    from model_contract_fixtures import synthetic_identity

    _elements, bindings = _synthetic_closure()
    document = json.loads(_binding_document(
        tmp_path, bindings, semantic_authority=synthetic_identity("foreign").to_dict()).read_text())
    report = probe_definition_migration(
        REPO_ROOT, binding=RevisionBinding.from_dict(document),
        expected_git_revision=REVISION,
    )
    assert report["activation_eligible"] is False
    assert report["closure"]["authority_matches"] is False
    assert "semantic-authority" in report["activation_prerequisite"]


@pytest.mark.parametrize("content", [None, "[]"])
def test_cli_refuses_missing_or_malformed_binding(tmp_path, content):
    binding_path = tmp_path / "binding.json"
    if content is not None:
        binding_path.write_text(content, encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable, "-B", str(REPO_ROOT / "scripts/probe_definition_migration.py"),
            "--binding", str(binding_path),
        ],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 2
    assert "refused:" in result.stderr
    assert "Traceback" not in result.stderr


def test_probe_reports_closed_closure_when_a_validated_binding_is_supplied(tmp_path):
    _elements, bindings = _synthetic_closure()
    binding_path = _binding_document(tmp_path, bindings=bindings)
    from de4sdv.sysml_api.revisions import RevisionBinding

    report = probe_definition_migration(
        REPO_ROOT, binding=RevisionBinding.load(binding_path),
        expected_git_revision=REVISION,
    )
    assert report["closure"]["closed"] is True
    assert report["activation_eligible"] is True
    assert all(
        record["validated_binding_element_id"] for record in report["identities"]
    )