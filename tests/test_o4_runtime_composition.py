"""Synthetic exact-binding tests; no privileged closure/activation claim."""
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
import mcp.client.stdio  # noqa: F401 — bind stderr during collection

from de4sdv.semantic import authority_selection as selection
from de4sdv.semantic import o3_bundle as ob
from de4sdv.semantic.definition_candidate import load_definition_candidate
from de4sdv.semantic.kernel_contract import KernelContract, declaration_identity
from de4sdv.sysml_api.revisions import RevisionBinding

ROOT = Path(__file__).resolve().parents[1]
ONTOLOGY = ROOT / ob.ONTOLOGY_PATH
REVISION = "a" * 40


def inputs(tmp_path, grounding="EQUIVALENT"):
    candidate = load_definition_candidate(ROOT)
    contract = KernelContract.load(ONTOLOGY)
    bindings = []
    elements = []
    for index, name in enumerate(candidate.identities):
        row = candidate.row_for(name)["grounding"]["kernel_binding_contract"]
        declared, metaclass = declaration_identity(row["declaration"])
        bindings.append(dict(ontology_class=name, element_id=f"uuid-{index}", **row))
        elements.append({"@id": f"uuid-{index}", "@type": metaclass, "declaredName": declared})
    document = dict(git_repository="de4sdv/DE4SDV", git_commit=REVISION,
                    sysml_project_id="pid", sysml_commit_id="cid",
                    import_timestamp="2026-09-30T00:00:00Z", import_tool_version="fixture",
                    semantic_validation="passed", scope="full-model",
                    ontology=contract.identity.to_dict(), kernel_bindings=bindings)
    binding_path = tmp_path / "binding.json"
    binding_path.write_text(json.dumps(document))
    bundle = ob.build_candidate_bundle(ROOT, git_revision=REVISION)
    validations = {}
    for name in ob.REQUIRED_VALIDATIONS:
        evidence = tmp_path / f"{name}.json"
        evidence.write_text(json.dumps({"synthetic": True, "validation": name}))
        validations[name] = dict(status="passed", artifact=name, path=str(evidence),
                                 sha256=ob.sha256_file(evidence))
    closure = ob.build_closure_attestation(
        bundle, binding=RevisionBinding.load(binding_path),
        binding_sha256="sha256:" + hashlib.sha256(binding_path.read_bytes()).hexdigest(),
        element_count=len(elements), export_identity_sha256=None,
        validations=validations, verification_case_grounding={"result": grounding},
        generated_at="1970-01-01T00:00:00+00:00")
    bundle = ob.close_bundle(bundle, closure)
    bundle_path = tmp_path / "bundle.json"
    bundle_path.write_text(json.dumps(bundle))
    return binding_path, bundle_path, bundle, elements


def build(binding, bundle_path, bundle, **kwargs):
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime
    return build_explicit_semantic_runtime(
        api_url="http://127.0.0.1:1", binding_path=binding,
        expected_git_revision=REVISION, ontology_path=ONTOLOGY,
        authority="o3", bundle_path=bundle_path, bundle_id=bundle["bundle_id"],
        environ={}, composition="o3+definitions", **kwargs)


def test_verified_constructor_routes_disjoint_sets(tmp_path):
    binding, path, bundle, elements = inputs(tmp_path)
    service, selected = build(binding, path, bundle)
    assert selected.provenance()["kind"] == "o3+definitions"
    assert selected.provenance()["activation_blocked"] is True
    assert service.semantic_authority_id.startswith("o4-composite:")
    candidate = load_definition_candidate(ROOT)
    for name in candidate.identities:
        assert service.contract.class_mapping(name).declaration == candidate.row_for(name)["grounding"]["kernel_binding_contract"]["declaration"]
    assert len(ob.MIGRATED_IDENTITIES) == 13
    assert not set(candidate.identities) & set(ob.MIGRATED_IDENTITIES)
    assert service.contract.relationship_mapping("hasSubject") == KernelContract.load(ONTOLOGY).relationship_mapping("hasSubject")
    assert "hasStakeholder" not in selected.migrated_identities
    assert service.binder.contract is service.contract
    assert service.traversal.contract is service.contract
    assert service.impact_service.contract is service.contract


def test_real_impact_cli_selects_composition(tmp_path, monkeypatch, capfd):
    from scripts import query_model_impact as cli
    from de4sdv.sysml_api.repository import SysMLRepository
    binding, path, bundle, elements = inputs(tmp_path)
    monkeypatch.setattr(SysMLRepository, "list_elements", lambda self, *a, **k: elements)
    monkeypatch.setattr(SysMLRepository, "get_element", lambda self, *a, **k: elements[0])
    result = cli.main([elements[0]["@id"], "--backend", "api", "--json",
        "--binding", str(binding), "--git-revision", REVISION,
        "--semantic-authority", "o3", "--o3-authority-bundle", str(path),
        "--o3-authority-bundle-id", bundle["bundle_id"],
        "--runtime-composition", "o3+definitions"])
    assert result == 0
    report = json.loads(capfd.readouterr().out)
    assert report["root"]["element_id"] == elements[0]["@id"]
    assert "o4-composite:" in json.dumps(report["provenance"])


def test_identity_covers_both_components(tmp_path):
    from dataclasses import replace
    from de4sdv.semantic.runtime_composition import composition_identity
    candidate = load_definition_candidate(ROOT)
    args: dict[str, Any] = dict(bundle_id="o3b-" + "a" * 32, candidate=candidate,
                binding_digest="sha256:" + "b" * 64,
                implementation_manifest={"schema": "fixture", "id": "fixture", "files": {"fixture": "c" * 64}})
    original = composition_identity(**args)
    assert original != composition_identity(**dict(args, bundle_id="o3b-" + "d" * 32))
    changed = replace(candidate, source_revision="e" * 40)
    assert original != composition_identity(**dict(args, candidate=changed))
    changed = replace(candidate, bound_inputs={"fixture": "sha256:" + "f" * 64})
    assert original != composition_identity(**dict(args, candidate=changed))


def test_legacy_mutations_cannot_change_migrated_answers(tmp_path, monkeypatch):
    from tests.test_definition_migration import _mutated_legacy
    binding, path, bundle, elements = inputs(tmp_path)
    before, _ = build(binding, path, bundle)
    candidate = load_definition_candidate(ROOT)
    name = candidate.identities[0]
    fallback = next(n for n, spec in before.contract.classes.items()
                    if n not in candidate.identities and n not in ob.MIGRATED_IDENTITIES
                    and "file" in spec.get("kernel", {}))
    legacy = _mutated_legacy(classes=(name, fallback), relationships=("hasSubject",))
    monkeypatch.setattr(KernelContract, "load", lambda *a, **k: legacy)
    after, _ = build(binding, path, bundle)
    assert after.contract.mapping(name) == before.contract.mapping(name)
    assert after.contract.relationship_mapping("hasSubject") == before.contract.relationship_mapping("hasSubject")
    assert after.contract.mapping(fallback) != before.contract.mapping(fallback)


def test_changed_external_provider_refuses_before_cache_identity(tmp_path, monkeypatch):
    """Execute changed provider bytes, not a made-up mapping or cache result."""
    import importlib.util
    import sys
    from de4sdv.semantic import definition_migration as migration
    from de4sdv.semantic import definition_candidate_provider as provider

    binding, path, bundle, elements = inputs(tmp_path)
    source = Path(provider.__file__).read_text()
    needle = "return self._admitted_mappings[ontology_class]"
    assert source.count(needle) == 2
    changed = tmp_path / "changed_provider.py"
    changed.write_text(source.replace(
        needle, "return KernelFileMapping('synthetic-changed.sysml', 'part def SyntheticChanged')",
    ))
    name = "de4sdv.semantic._changed_composition_provider"
    spec = importlib.util.spec_from_file_location(name, changed)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    monkeypatch.setattr(migration, "DefinitionCandidateProvider", module.DefinitionCandidateProvider)
    with pytest.raises(ValueError, match="implementation source"):
        build(binding, path, bundle)


@pytest.mark.parametrize("dependency", (
    "de4sdv/semantic/composition_construction.py",
    "de4sdv/semantic/runtime_composition.py",
    "de4sdv/semantic/definition_candidate.py",
    "de4sdv/semantic/definition_migration.py",
    "de4sdv/semantic/definition_candidate_provider.py",
    "de4sdv/sysml_api/client.py",
    "de4sdv/sysml_api/repository.py",
    "de4sdv/semantic/model_edges.py",
    "de4sdv/semantic/relationships.py",
))
def test_every_implementation_dependency_digest_invalidates_cache(tmp_path, dependency):
    from tools.sysml_html_viewer import ask_model_semantic as viewer
    from de4sdv.semantic.composition_construction import SIDECAR_FILES
    from de4sdv.semantic.runtime_composition import composition_identity

    binding, path, bundle, elements = inputs(tmp_path)
    service, selected = build(binding, path, bundle)
    manifest = selected.provenance()["implementation_manifest"]
    assert len(SIDECAR_FILES) == 9
    assert set(manifest["files"]) == set(SIDECAR_FILES)
    for name, digest in manifest["files"].items():
        assert digest == "sha256:" + hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
    assert manifest["id"] == "o4-runtime-" + hashlib.sha256(json.dumps(
        manifest["files"], sort_keys=True, separators=(",", ":"),
    ).encode()).hexdigest()
    args: dict[str, Any] = dict(bundle_id=bundle["bundle_id"],
        candidate=load_definition_candidate(ROOT),
        binding_digest="sha256:" + hashlib.sha256(binding.read_bytes()).hexdigest(),
        implementation_manifest=manifest)
    assert composition_identity(**args) == service.semantic_authority_id
    assert viewer._snapshot_identity(service)["semantic_authority_id"] == service.semantic_authority_id
    before = viewer._snapshot_path(service)
    changed = dict(manifest, files=dict(manifest["files"], **{dependency: "sha256:" + "0" * 64}))
    changed_id = composition_identity(**dict(args, implementation_manifest=changed))
    assert changed_id != service.semantic_authority_id
    service.semantic_authority_id = changed_id
    assert viewer._snapshot_path(service) != before


def test_live_query_module_cannot_import_bootstrap_verifiers():
    import ast
    from de4sdv.semantic import runtime_composition
    tree = ast.parse(Path(runtime_composition.__file__).read_text())
    forbidden = {"composition_construction", "definition_candidate", "definition_migration",
                 "definition_candidate_provider", "authority_inventory", "definition_projection"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            assert all(alias.name.rsplit(".", 1)[-1] not in forbidden for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            assert (node.module or "").rsplit(".", 1)[-1] not in forbidden
            assert all(alias.name not in forbidden for alias in node.names)


def test_incomplete_closure_and_bad_selection_refuse(tmp_path):
    from de4sdv.semantic.composition_construction import build_explicit_semantic_runtime
    binding, path, bundle, elements = inputs(tmp_path)
    with pytest.raises(ValueError, match="unknown explicit"):
        build_explicit_semantic_runtime(composition="typo")
    with pytest.raises(ValueError, match="explicit authority"):
        build_explicit_semantic_runtime(composition="o3+definitions")
    doc = json.loads(binding.read_text())
    doc["kernel_bindings"].pop()
    binding.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        build(binding, path, bundle)


def test_ineligible_comparison_never_activates(tmp_path):
    from de4sdv.semantic.composition_construction import build_composed_semantic_runtime
    binding, path, bundle, elements = inputs(tmp_path, grounding="NOT_YET_COMPARABLE")
    service, selected = build(binding, path, bundle)
    assert selected.provenance()["o3_activation_blocked"] is True
    with pytest.raises(ValueError, match="activation"):
        build_composed_semantic_runtime(api_url="http://127.0.0.1:1", binding_path=binding,
            expected_git_revision=REVISION, ontology_path=ONTOLOGY,
            semantic_authority=bundle, require_activation_eligible=True)


def test_real_viewer_constructor_and_cache_isolation(tmp_path, monkeypatch):
    from tools.sysml_html_viewer import ask_model_semantic as viewer
    binding, path, bundle, elements = inputs(tmp_path)
    monkeypatch.setattr(viewer, "_SEMANTIC_RUNTIME", None)
    monkeypatch.setattr(viewer, "_SEMANTIC_ERROR", None)
    monkeypatch.setattr(viewer, "_AUTHORITY_SELECTION", None)
    monkeypatch.setenv("DE4SDV_REVISION_BINDING", str(binding))
    monkeypatch.setenv("DE4SDV_EXPECTED_GIT_SHA", REVISION)
    service = viewer._runtime(composition="o3+definitions", bundle_path=path, bundle_id=bundle["bundle_id"])
    assert viewer.semantic_authority_status()["kind"] == "o3+definitions"
    assert viewer._snapshot_identity(service)["semantic_authority_id"] == service.semantic_authority_id
    legacy, _ = selection.build_selected_semantic_runtime(api_url="http://127.0.0.1:1",
        binding_path=binding, expected_git_revision=REVISION, ontology_path=ONTOLOGY, environ={})
    assert viewer._snapshot_path(service) != viewer._snapshot_path(legacy)


def test_real_mcp_cli_composes_before_transport(tmp_path, monkeypatch):
    from scripts import semantic_mcp_server as cli
    binding, path, bundle, elements = inputs(tmp_path)
    created = []
    original = cli.create_mcp_server
    def create(service):
        server = original(service)
        monkeypatch.setattr(server, "run", lambda **kwargs: created.append(service))
        return server
    monkeypatch.setattr(cli, "create_mcp_server", create)
    monkeypatch.setattr("sys.argv", ["semantic_mcp_server.py", "--api-url", "http://127.0.0.1:1",
        "--binding", str(binding), "--expected-git-revision", REVISION,
        "--semantic-authority", "o3", "--o3-authority-bundle", str(path),
        "--o3-authority-bundle-id", bundle["bundle_id"], "--runtime-composition", "o3+definitions"])
    assert cli.main() == 0
    assert created[0].semantic_authority_id.startswith("o4-composite:")


def test_admitted_classes_through_binder_and_public_inspection(tmp_path, monkeypatch):
    from de4sdv.sysml_api.repository import SysMLRepository
    binding, path, bundle, elements = inputs(tmp_path)
    monkeypatch.setattr(SysMLRepository, "list_elements", lambda self, *a, **k: elements)
    monkeypatch.setattr(SysMLRepository, "get_element", lambda self, pid, cid, eid: next(e for e in elements if e["@id"] == eid))
    service, selected = build(binding, path, bundle)
    for index, name in enumerate(load_definition_candidate(ROOT).identities):
        assert service.binder.bind_class(name).sysml.element_id == f"uuid-{index}"
        assert name in json.dumps(service.inspect_element(f"uuid-{index}"))
