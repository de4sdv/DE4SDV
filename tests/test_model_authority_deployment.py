"""Deployment wiring of the deployed runtime: no selector, no bundle (synthetic)."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from deployment.ask_viewer import entrypoint
from deployment.ask_viewer.entrypoint import RuntimeContractError, validate_runtime_contract

ROOT = Path(__file__).resolve().parents[1]


def _git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], check=True,
                          capture_output=True, text=True).stdout.strip()


def _commit(repo, message):
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _write(repo, relative, text):
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


MODEL_INPUTS = (
    "de4sdv/semantic/contract-data/frozen-records/semantic-projection-v1.json",
    "de4sdv/semantic/contract-data/frozen-records/api-representation-profile-v1.json",
    "de4sdv/semantic/contract-data/native-grounding-projection.json",
    "de4sdv/semantic/contract-data/class-definition-projection.json",
    "de4sdv/semantic/contract-data/class-definition-profile.json",
    "de4sdv/semantic/contract-data/class-definition-admission.yaml",
    "de4sdv/semantic/contract-data/kernel-vocabulary-projection.json",
    "de4sdv/semantic/contract-data/kernel-vocabulary-profile.json",
    "de4sdv/semantic/contract-data/kernel-vocabulary-admission.yaml",
    "de4sdv/semantic/contract-data/trace-vocabulary-contract.json",
    "de4sdv/semantic/contract-data/ontology-identity-register.json",
    "de4sdv/semantic/contract-data/kernel-internal-declarations.yaml",
)


@pytest.fixture
def runtime_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    _write(repo, "textual-notation-of-model/model.sysml", "package Model;\n")
    for relative in MODEL_INPUTS:
        _write(repo, relative, "{}\n")
    _write(repo, "docs/references/model-authority-runtime.md", "# doc\n")
    model_revision = _commit(repo, "model")
    binding = tmp_path / "binding.json"
    binding.write_text(json.dumps({"git_commit": model_revision}), encoding="utf-8")
    return repo, binding


def _env(revision):
    return {"NOUS_API_KEY": "k", "DE4SDV_APP_GIT_SHA": revision}


def test_every_governed_path_matches_a_tracked_file():
    """A governed path that matches nothing makes the drift gate pass vacuously."""
    for pathspec in entrypoint._GOVERNED_MODEL_PATHS:
        tracked = _git(ROOT, "ls-files", "--", pathspec)
        assert tracked, f"governed path matches no tracked file: {pathspec}"


def test_deleted_authored_yaml_is_no_longer_a_governed_path():
    assert not any("de4sdv-basic-ontology" in path for path in entrypoint._GOVERNED_MODEL_PATHS)
    assert "textual-notation-of-model" in entrypoint._GOVERNED_MODEL_PATHS
    assert "de4sdv/semantic/contract-data/ontology-identity-register.json" in entrypoint._GOVERNED_MODEL_PATHS


@pytest.mark.parametrize("relative", MODEL_INPUTS)
def test_projection_profile_admission_drift_refuses_code_only_start(runtime_repo, relative):
    repo, binding = runtime_repo
    _write(repo, relative, '{"changed": true}\n')
    revision = _commit(repo, f"change {relative}")
    with pytest.raises(RuntimeContractError, match="drift"):
        validate_runtime_contract(repo, binding, _env(revision))


def test_new_projection_file_is_governed(runtime_repo):
    # A projection/profile pair added to the contract data is governed.
    repo, binding = runtime_repo
    _write(repo, "de4sdv/semantic/contract-data/new-vocabulary-projection.json", "{}\n")
    revision = _commit(repo, "new projection")
    with pytest.raises(RuntimeContractError, match="drift"):
        validate_runtime_contract(repo, binding, _env(revision))


def test_documentation_only_change_still_starts(runtime_repo):
    repo, binding = runtime_repo
    _write(repo, "docs/references/model-authority-runtime.md", "# doc v2\n")
    _write(repo, "docs/method-evaluation/result-algebra.md", "# algebra\n")
    _write(repo, "de4sdv/semantic/contract-data/README.md", "# contract data\n")
    revision = _commit(repo, "docs only")
    contract = validate_runtime_contract(repo, binding, _env(revision))
    assert contract.application_revision == revision


# -- compose ---------------------------------------------------------------------


def _ask_viewer():
    compose = yaml.safe_load((ROOT / "deployment/compose.yaml").read_text(encoding="utf-8"))
    return compose["services"]["ask-viewer"]


def test_compose_passes_no_selector_and_no_bundle():
    environment = _ask_viewer()["environment"]
    for retired in ("DE4SDV_SEMANTIC_AUTHORITY", "DE4SDV_MODEL_AUTHORITY_BUNDLE",
                    "DE4SDV_MODEL_AUTHORITY_BUNDLE_ID", "DE4SDV_ONTOLOGY_PATH"):
        assert retired not in environment, retired
    assert not any(key.startswith("DE4SDV_O3_") for key in environment)
    # The runtime contract: the deployed commit, the binding and the API.
    assert environment["DE4SDV_APP_GIT_SHA"].startswith("${DE4SDV_APP_GIT_SHA:?")
    assert environment["DE4SDV_REVISION_BINDING"] == "/run/de4sdv/de4sdv-full-model-binding.json"
    assert environment["DE4SDV_SYSML_API_URL"] == "http://sysml2-api:9000"


def test_compose_mounts_only_the_checkout_and_the_binding_read_only():
    volumes = _ask_viewer()["volumes"]
    assert "${DEPLOY_SOURCE_DIR:-/srv/de4sdv/DE4SDV}:/srv/de4sdv/DE4SDV:ro" in volumes
    assert ("${DEPLOY_DIR}/artifacts/current/de4sdv-full-model-binding.json:"
            "/run/de4sdv/de4sdv-full-model-binding.json:ro") in volumes
    assert not any("/run/de4sdv/model" in volume or "/run/de4sdv/o3" in volume
                   for volume in volumes)


def test_deploy_readme_documents_the_runtime_contract_release_and_rollback():
    text = (ROOT / "deployment/README.md").read_text(encoding="utf-8")
    for needle in ("## Runtime contract", "startup check", "served model", "## Release",
                   "## Rollback", "063c4fb1f2763a366874118f3b78d9841e0d11b4", "sysml-api-production",
                   "release-2026-10-11"):
        assert needle in text, needle
    assert "model-authority-activation.md" not in text
