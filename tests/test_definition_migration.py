"""O4 definition-migration path — verified, explicitly selected, fail-closed.

TDD suite: verified construction from the real candidate pair; the explicit
selection surface (never implicit); the fail-closed activation prerequisite
(a fresh exact-revision API closure); genuine consumption through the real
API-binding / kernel-index / traversal / query / runtime consumers on a
synthetic validated closure; adversarial independence of the migrated
definition data from the authored contract with the remaining legacy
fallback kept visible; and the executable offline probe over the real
retained candidate artifacts.

The O3 bundle route (authority_selection: legacy | o3) and the frozen 13
identity semantics are asserted untouched — the migration path never
composes with them and never impersonates them.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

from de4sdv.semantic import o3_bundle
from de4sdv.semantic.authority_ids import LEGACY_AUTHORITY_ID
from de4sdv.semantic.authority_selection import (
    AuthoritySelectionError,
    resolve_authority_selection,
)
from de4sdv.semantic.definition_candidate import load_definition_candidate
from de4sdv.semantic.definition_candidate_provider import DefinitionCandidateProvider
from de4sdv.semantic.definition_migration import (
    DefinitionMigrationError,
    MIGRATION_ENV,
    MIGRATION_SELECTED,
    build_definition_migration_runtime,
    load_definition_migration_authority,
    probe_definition_migration,
    resolve_definition_migration_selection,
)
from de4sdv.semantic.kernel_contract import KernelContract, declaration_identity
from de4sdv.semantic.o3_bundle import O3ImpactService
from de4sdv.semantic.query import SemanticQueryService
from de4sdv.semantic.runtime import build_semantic_runtime
from de4sdv.semantic.validation import validate_ontology_bindings

ONTOLOGY = REPO_ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
REVISION = "a" * 40


def _contract() -> KernelContract:
    return KernelContract.load(ONTOLOGY)


def _candidate():
    return load_definition_candidate(REPO_ROOT)


def _provider() -> DefinitionCandidateProvider:
    return DefinitionCandidateProvider(legacy=_contract(), candidate=_candidate())


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


def _binding_document(tmp_path: Path, bindings: list[dict]) -> Path:
    document = {
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": REVISION,
        "sysml_project_id": "project-1",
        "sysml_commit_id": "commit-1",
        "import_timestamp": "2026-09-30T00:00:00Z",
        "import_tool_version": "test",
        "semantic_validation": "passed",
        "scope": "full-model",
        "ontology": _contract().identity.to_dict(),
        "kernel_bindings": bindings,
    }
    path = tmp_path / "binding.json"
    path.write_text(json.dumps(document), encoding="utf-8")
    return path


def _fake_binding(bindings: list[dict]) -> SimpleNamespace:
    return SimpleNamespace(
        semantic_validation="passed",
        scope="full-model",
        kernel_bindings=tuple(SimpleNamespace(**item) for item in bindings),
    )


def _mutated_legacy(
    *, classes: tuple[str, ...] = (), relationships: tuple[str, ...] = ()
) -> KernelContract:
    legacy = _contract()
    mutated_classes = {name: dict(spec) for name, spec in legacy.classes.items()}
    for name in classes:
        entry = dict(mutated_classes[name])
        kernel = dict(entry["kernel"])
        kernel["file"] = "mutated/path.sysml"
        kernel["declaration"] = "part def Mutated"
        entry["kernel"] = kernel
        mutated_classes[name] = entry
    mutated_relationships = {
        name: dict(spec) for name, spec in legacy.relationships.items()
    }
    for name in relationships:
        spec = dict(mutated_relationships[name])
        mapping = dict(spec["sysml_mapping"])
        mapping["strategy"] = "mutated-strategy"
        spec["sysml_mapping"] = mapping
        mutated_relationships[name] = spec
    return KernelContract(
        source=legacy.source,
        identity=legacy.identity,
        governed_directory=legacy.governed_directory,
        exclusions=legacy.exclusions,
        classes=mutated_classes,
        relationships=mutated_relationships,
    )


class _FakeRepository:
    def __init__(self, elements: list[dict]) -> None:
        self._elements = elements
        self.calls = 0

    def list_elements(self, project_id: str, commit_id: str) -> list[dict]:
        self.calls += 1
        return list(self._elements)


# ---------------------------------------------------------------------------
# verified construction + frozen-O3 / production-default preservation
# ---------------------------------------------------------------------------


def test_authority_loads_verified_candidate_and_reports_closure_prerequisite():
    authority = load_definition_migration_authority(REPO_ROOT, contract=_contract())
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
    # frozen O3 13 identity semantics preserved and never overlapped
    assert set(authority.identities) & set(o3_bundle.MIGRATED_IDENTITIES) == set()
    assert len(o3_bundle.MIGRATED_IDENTITIES) == 13
    # the accepted bundle route is untouched: legacy | o3 only
    assert resolve_authority_selection(environ={}).kind == "legacy"
    with pytest.raises(AuthoritySelectionError):
        resolve_authority_selection(authority="o4", environ={})


def test_selection_is_explicit_and_never_implicit(tmp_path):
    assert resolve_definition_migration_selection(environ={}) == "off"
    assert resolve_definition_migration_selection(environ={MIGRATION_ENV: ""}) == "off"
    assert resolve_definition_migration_selection(environ={MIGRATION_ENV: "off"}) == "off"
    assert (
        resolve_definition_migration_selection(environ={MIGRATION_ENV: MIGRATION_SELECTED})
        == MIGRATION_SELECTED
    )
    with pytest.raises(DefinitionMigrationError, match="never selected implicitly"):
        resolve_definition_migration_selection(environ={MIGRATION_ENV: "o4"})
    with pytest.raises(DefinitionMigrationError, match="not selected"):
        build_definition_migration_runtime(
            api_url="http://localhost:1",
            binding_path=tmp_path / "unused.json",
            expected_git_revision=REVISION,
            ontology_path=ONTOLOGY,
            environ={},
        )


def test_activation_fails_closed_without_fresh_exact_revision_closure(tmp_path):
    binding_path = _binding_document(tmp_path, bindings=[])
    with pytest.raises(
        DefinitionMigrationError, match="fresh exact-revision API closure"
    ) as excinfo:
        build_definition_migration_runtime(
            api_url="http://localhost:1",
            binding_path=binding_path,
            expected_git_revision=REVISION,
            ontology_path=ONTOLOGY,
            selection=MIGRATION_SELECTED,
        )
    assert "22 of 22" in str(excinfo.value)
    # production default unchanged: the same binding builds a legacy runtime
    service = build_semantic_runtime(
        api_url="http://localhost:1",
        binding_path=binding_path,
        expected_git_revision=REVISION,
        ontology_path=ONTOLOGY,
    )
    assert service.semantic_authority_id == LEGACY_AUTHORITY_ID


def test_closure_rejects_binding_disagreeing_with_the_candidate_pair():
    _elements, bindings = _synthetic_closure()
    tampered = [dict(item) for item in bindings]
    tampered[0]["declaration"] = "part def Mutated"
    authority = load_definition_migration_authority(
        REPO_ROOT, contract=_contract(), binding=_fake_binding(tampered)
    )
    assert authority.activation_eligible is False
    assert authority.closure.mismatched
    assert "disagrees with the candidate" in authority.activation_blocked_reason()


# ---------------------------------------------------------------------------
# genuine consumption through the real consumers (synthetic validated closure)
# ---------------------------------------------------------------------------


def test_migrated_definitions_consumed_by_real_consumers(tmp_path):
    elements, bindings = _synthetic_closure()
    binding_path = _binding_document(tmp_path, bindings=bindings)
    service, authority = build_definition_migration_runtime(
        api_url="http://localhost:1",
        binding_path=binding_path,
        expected_git_revision=REVISION,
        ontology_path=ONTOLOGY,
        selection=MIGRATION_SELECTED,
    )
    assert authority.activation_eligible is True
    provider = authority.provider
    assert isinstance(service, SemanticQueryService)
    assert service.semantic_authority_id == provider.authority_id
    assert service.contract is provider
    # runtime consumer wiring: binder, traversal and impact all receive the
    # verified provider — the same consumers the production path uses
    assert service.binder.contract is provider
    assert service.traversal.contract is provider
    assert isinstance(service.impact_service, O3ImpactService)
    assert service.impact_service.semantic_authority_id == provider.authority_id

    fake = _FakeRepository(elements)
    service.repository = fake
    service.binder.repository = fake

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
    # Exercise every admitted row through the actual binder, reverse index,
    # and public query surface, not only the provider's mapping dictionary.
    candidate = _candidate()
    for name in candidate.identities:
        mapping = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        admitted_bound = service.binder.bind_class(name)
        assert admitted_bound.kernel.file == mapping["source_file"]
        assert admitted_bound.kernel.declaration == mapping["declaration"]
        assert index.ontology_class_for(admitted_bound.sysml.element_id, by_id) == name
        declared_name = declaration_identity(mapping["declaration"])[0]
        inspected = service.inspect_element(declared_name)
        assert inspected["element"]["element_id"] == admitted_bound.sysml.element_id

    # traversal consumer: runs the real strategy through the provider
    source = by_id[bound.sysml.element_id]
    assert service.traversal.traverse("verifiedBy", source, elements) == []

    # query consumer: runs offline against the stubbed repository
    status = service.model_status()
    assert status["current_baseline"] is True
    assert status["element_count"] == len(elements)
    assert status["semantic_authority"]["kind"] == "definition-candidate"
    assert status["semantic_authority"]["id"] == provider.authority_id

    declared_name = declaration_identity(row["declaration"])[0]
    resolved = service.resolve_element(declared_name)
    assert resolved["element"]["element_id"] == bound.sysml.element_id
    neighbors = service.semantic_neighbors(declared_name, predicates=["verifiedBy"])
    assert neighbors["query"] == "semantic_neighbors"
    assert (
        neighbors["provenance"][2]["source"]
        == f"projection://{provider.authority_id}"
    )


def test_migration_never_composes_with_the_o3_route(tmp_path):
    elements, bindings = _synthetic_closure()
    binding_path = _binding_document(tmp_path, bindings=bindings)
    provider = _provider()
    assert provider.authority_id.startswith("definition-candidate:")
    assert not provider.authority_id.startswith("o3:")
    with pytest.raises(ValueError, match="never both"):
        build_semantic_runtime(
            api_url="http://localhost:1",
            binding_path=binding_path,
            expected_git_revision=REVISION,
            ontology_path=ONTOLOGY,
            semantic_authority={},
            definition_candidate_authority=provider,
        )


# ---------------------------------------------------------------------------
# adversarial independence + visible remaining legacy dependency
# ---------------------------------------------------------------------------


def test_adversarial_legacy_mutation_leaves_migrated_data_untouched():
    candidate = _candidate()
    unadmitted = sorted(set(_contract().classes) - set(candidate.identities))
    assert unadmitted
    target = unadmitted[0]
    mutated = _mutated_legacy(classes=tuple(candidate.identities) + (target,))
    authority = load_definition_migration_authority(REPO_ROOT, contract=mutated)
    provider = authority.provider
    for name in candidate.identities:
        row = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        resolved = provider.class_mapping(name)
        assert resolved.file == row["source_file"], name
        assert resolved.declaration == row["declaration"], name
        assert provider.mapping(name).file == row["source_file"], name

    # every other identity keeps its EXPLICIT fallback: the mutated authored
    # contract is what unadmitted identities still resolve through
    unadmitted = sorted(set(_contract().classes) - set(candidate.identities))
    assert unadmitted
    target = unadmitted[0]
    assert provider.class_mapping(target) == mutated.class_mapping(target)
    assert provider.mapping(target).file == "mutated/path.sysml"

    # validation consumer classifies admitted identities from candidate data
    elements: list[dict] = []
    sources: dict[str, str] = {}
    for index, name in enumerate(candidate.identities):
        row = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        declared_name, expected_type = declaration_identity(row["declaration"])
        element_id_value = f"val-{index:02d}"
        elements.append(
            {
                "@id": element_id_value,
                "@type": expected_type,
                "declaredName": declared_name,
            }
        )
        sources[element_id_value] = row["source_file"]
    report = validate_ontology_bindings(provider, elements, sources)
    admitted = set(candidate.identities)
    admitted_entries = [entry for entry in report.entries if entry.ontology_class in admitted]
    assert len(admitted_entries) == 22
    assert all(entry.status == "mapped" for entry in admitted_entries)
    # the remaining legacy dependency stays visible: an unadmitted class under
    # the mutated contract fails to resolve instead of being silently served
    unadmitted_entry = next(
        entry for entry in report.entries if entry.ontology_class == target
    )
    assert unadmitted_entry.status == "unresolved"


# ---------------------------------------------------------------------------
# executable offline probe over the real retained candidate artifacts
# ---------------------------------------------------------------------------


def test_probe_reports_real_artifacts_offline():
    report = probe_definition_migration(REPO_ROOT)
    assert report["schema"] == "de4sdv.o4-definition-migration-probe/v1"
    assert report["offline"] is True
    assert report["admitted_count"] == 22
    assert report["o3_overlap"] == []
    assert report["activation_eligible"] is False
    assert "fresh exact-revision API closure" in report["activation_prerequisite"]
    assert report["closure"]["closed"] is False
    assert report["closure"]["missing"] == sorted(report["closure"]["missing"])
    assert len(report["closure"]["missing"]) == 22
    assert report["export"]["provided"] is False
    assert report["legacy_only_class_count"] > 0
    records = report["identities"]
    assert [record["identity"] for record in records] == sorted(
        record["identity"] for record in records
    )
    # real parity at this revision: candidate mappings equal the authored
    # ones, but they resolve from the verified candidate artifacts
    assert all(record["legacy_present"] for record in records)
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


def test_runtime_refuses_stale_binding_before_assembly(tmp_path):
    _elements, bindings = _synthetic_closure()
    binding_path = _binding_document(tmp_path, bindings=bindings)
    with pytest.raises(DefinitionMigrationError, match="revision"):
        build_definition_migration_runtime(
            api_url="http://localhost:1",
            binding_path=binding_path,
            expected_git_revision="b" * 40,
            ontology_path=ONTOLOGY,
            selection=MIGRATION_SELECTED,
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


def test_probe_refuses_foreign_ontology_even_when_revision_and_rows_match(tmp_path):
    from de4sdv.sysml_api.revisions import RevisionBinding

    _elements, bindings = _synthetic_closure()
    document = json.loads(_binding_document(tmp_path, bindings).read_text())
    document["ontology"]["sha256"] = "b" * 64
    report = probe_definition_migration(
        REPO_ROOT, binding=RevisionBinding.from_dict(document),
        expected_git_revision=REVISION,
    )
    assert report["activation_eligible"] is False
    assert "ontology" in report["activation_prerequisite"]


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