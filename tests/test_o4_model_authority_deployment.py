"""Deployment wiring for the model-authority selector, O4 Wave C2 (synthetic)."""
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
    "docs/method-conformance/o2/semantic-projection-v1.json",
    "docs/method-conformance/o2/api-representation-profile-v1.json",
    "docs/method-conformance/o2/o21-admission.yaml",
    "docs/method-conformance/o2plus/semantic-projection-o2plus.json",
    "docs/method-conformance/o4/definition-projection.json",
    "docs/method-conformance/o4/definition-profile.json",
    "docs/method-conformance/o4/definition-admission.yaml",
    "docs/method-conformance/o4/vocabulary-carriers-projection.json",
    "docs/method-conformance/o4/vocabulary-carriers-profile.json",
    "docs/method-conformance/o4/vocabulary-carriers.yaml",
    "docs/method-conformance/o4/o4-execution-register.json",
    "docs/method-conformance/o4/kernel-internal-declarations.yaml",
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
    _write(repo, "docs/method-conformance/o4/model-authority-activation.md", "# doc\n")
    model_revision = _commit(repo, "model")
    binding = tmp_path / "binding.json"
    binding.write_text(json.dumps({"git_commit": model_revision}), encoding="utf-8")
    return repo, binding


def _env(revision):
    return {"NOUS_API_KEY": "k", "DE4SDV_APP_GIT_SHA": revision}


def test_deleted_authored_yaml_is_no_longer_a_governed_path():
    assert not any("de4sdv-basic-ontology" in path for path in entrypoint._GOVERNED_MODEL_PATHS)
    assert "textual-notation-of-model" in entrypoint._GOVERNED_MODEL_PATHS
    assert "docs/method-conformance/o4/o4-execution-register.json" in entrypoint._GOVERNED_MODEL_PATHS


@pytest.mark.parametrize("relative", MODEL_INPUTS)
def test_projection_profile_admission_drift_refuses_code_only_start(runtime_repo, relative):
    repo, binding = runtime_repo
    _write(repo, relative, '{"changed": true}\n')
    revision = _commit(repo, f"change {relative}")
    with pytest.raises(RuntimeContractError, match="drift"):
        validate_runtime_contract(repo, binding, _env(revision))


def test_new_batch_projection_file_is_governed(runtime_repo):
    # Admission batch 2 may add a projection/profile pair under o4/.
    repo, binding = runtime_repo
    _write(repo, "docs/method-conformance/o4/definition-batch2-projection.json", "{}\n")
    revision = _commit(repo, "batch 2 projection")
    with pytest.raises(RuntimeContractError, match="drift"):
        validate_runtime_contract(repo, binding, _env(revision))


def test_documentation_only_change_still_starts(runtime_repo):
    repo, binding = runtime_repo
    _write(repo, "docs/method-conformance/o4/model-authority-activation.md", "# doc v2\n")
    _write(repo, "docs/method-conformance/o2/o2-1-design.md", "# design\n")
    revision = _commit(repo, "docs only")
    contract = validate_runtime_contract(repo, binding, _env(revision))
    assert contract.application_revision == revision


# -- compose ---------------------------------------------------------------------


def _ask_viewer():
    compose = yaml.safe_load((ROOT / "deployment/compose.yaml").read_text(encoding="utf-8"))
    return compose["services"]["ask-viewer"]


def test_compose_passes_model_selection_through_substitution_environment():
    environment = _ask_viewer()["environment"]
    # D6: no default; an empty selector is refused by the runtime.
    assert environment["DE4SDV_SEMANTIC_AUTHORITY"] == "${DE4SDV_SEMANTIC_AUTHORITY:-}"
    assert environment["DE4SDV_MODEL_AUTHORITY_BUNDLE"] == (
        "${DE4SDV_MODEL_AUTHORITY_BUNDLE:-/run/de4sdv/model/de4sdv-model-authority-bundle.json}"
    )
    assert environment["DE4SDV_MODEL_AUTHORITY_BUNDLE_ID"] == "${DE4SDV_MODEL_AUTHORITY_BUNDLE_ID:-}"
    # The O3 rollback selector is retired (rollback = redeploy).
    assert not any(key.startswith("DE4SDV_O3_") for key in environment)
    assert "DE4SDV_ONTOLOGY_PATH" not in environment


def test_empty_compose_selector_is_refused_at_runtime():
    from de4sdv.semantic.authority_selection import AuthoritySelectionError, require_model_selection

    with pytest.raises(AuthoritySelectionError, match="is unset"):
        require_model_selection(None, {"DE4SDV_SEMANTIC_AUTHORITY": ""})


def test_compose_mounts_model_artifacts_read_only_outside_checkout():
    volumes = _ask_viewer()["volumes"]
    assert "${DEPLOY_DIR}/artifacts/model:/run/de4sdv/model:ro" in volumes
    assert not any("/run/de4sdv/o3" in volume for volume in volumes)


def test_activation_document_names_owner_gates_and_rollback():
    text = (ROOT / "docs/method-conformance/o4/model-authority-activation.md").read_text(
        encoding="utf-8")
    for needle in (
        "DE4SDV_SEMANTIC_AUTHORITY=model",
        "DE4SDV_MODEL_AUTHORITY_BUNDLE_ID=mab-",
        "sysml-api-production",
        "rollback", "redeploy", "ff0311b",
        "activation_eligible",
    ):
        assert needle in text, needle
    assert "three batteries" in text.lower() or "3 batteries" in text.lower()
    # Wave C2: the selector rollback to o3/legacy no longer exists.
    for retired in ("DE4SDV_SEMANTIC_AUTHORITY=o3", "DE4SDV_SEMANTIC_AUTHORITY=legacy"):
        assert retired not in text, retired


def test_deploy_readme_points_to_model_activation_procedure():
    text = (ROOT / "deployment/README.md").read_text(encoding="utf-8")
    assert "model-authority-activation.md" in text
    assert "artifacts/model" in text
