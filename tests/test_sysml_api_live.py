"""Opt-in live SysML API contract and AEBS impact integration tests."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from de4sdv.semantic.api_binding import OntologyApiBinder
from de4sdv.semantic.impact import ImpactService
from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.traversal import SemanticTraversal
from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.repository import SysMLRepository
from de4sdv.sysml_api.revisions import RevisionBinding
from scripts import query_model_impact as text_backend

ROOT = Path(__file__).resolve().parents[1]
BINDING_ENV = "DE4SDV_SYSML_API_BINDING"
API_URL_ENV = "DE4SDV_SYSML_API_URL"


def live_service() -> tuple[SysMLRepository, RevisionBinding, ImpactService]:
    binding_path = os.environ.get(BINDING_ENV)
    if not binding_path:
        pytest.skip(f"set {BINDING_ENV} to run live API tests")
    binding = RevisionBinding.load(Path(binding_path))
    repository = SysMLRepository(
        ApiClient(os.environ.get(API_URL_ENV, "http://127.0.0.1:9000"))
    )
    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    service = ImpactService(
        repository=repository,
        binding=binding,
        contract=contract,
        binder=OntologyApiBinder(
            contract,
            repository,
            project_id=binding.sysml_project_id,
            commit_id=binding.sysml_commit_id,
        ),
        traversal=SemanticTraversal(contract),
    )
    return repository, binding, service


def test_live_api_revision_and_elements_are_dereferenceable() -> None:
    repository, binding, _service = live_service()

    project = repository.get_project(binding.sysml_project_id)
    commit = repository.get_commit(
        binding.sysml_project_id, binding.sysml_commit_id
    )
    elements = repository.list_elements(
        binding.sysml_project_id, binding.sysml_commit_id
    )
    capabilities = repository.check_capabilities(
        binding.sysml_project_id, binding.sysml_commit_id
    )

    assert project["@id"] == binding.sysml_project_id
    assert commit["@id"] == binding.sysml_commit_id
    assert len(elements) == 11
    assert {"RequirementDefinition", "RequirementUsage", "VerificationCaseUsage", "Dependency"} <= set(
        capabilities["semantic_types"]
    )


def test_live_api_aebs_impact_matches_supported_text_backend_paths() -> None:
    _repository, binding, service = live_service()

    result = service.impact(
        "reqCommandEmergencyBraking", git_revision=binding.git_commit
    )
    text_report = text_backend.query_impact("reqCommandEmergencyBraking")

    assert result["root"]["element_id"]
    assert result["revision"]["sysml_project_id"] == binding.sysml_project_id
    assert result["revision"]["sysml_commit_id"] == binding.sysml_commit_id
    assert {
        node["declared_name"]
        for node in result["nodes"]
        if node["category"] == "evidence"
    } == {edge.source for edge in text_report.edges}
    assert {
        node["declared_name"]
        for node in result["nodes"]
        if node["category"] == "verification"
    } == {edge.verification_usage for edge in text_report.edges}
    assert {
        node["declared_name"]
        for node in result["nodes"]
        if node["category"] == "product-line"
    } == {"memberProduct"}
    assert any(gap["category"] == "architecture" for gap in result["gaps"])
    assert all(edge["api_object_id"] for edge in result["edges"])


def test_live_api_compact_cli_surface_returns_structured_subgraph() -> None:
    binding_path = os.environ.get(BINDING_ENV)
    if not binding_path:
        pytest.skip(f"set {BINDING_ENV} to run live API tests")

    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/query_model_impact.py"),
            "--backend",
            "api",
            "--api-url",
            os.environ.get(API_URL_ENV, "http://127.0.0.1:9000"),
            "--binding",
            binding_path,
            "--json",
            "reqCommandEmergencyBraking",
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["query"] == "impact"
    assert result["root"]["element_id"]
    assert len(result["nodes"]) == 7
    assert len(result["edges"]) == 7
