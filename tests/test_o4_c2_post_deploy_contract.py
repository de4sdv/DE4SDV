"""Post-deploy contract after the release-ceremony retirement (owner decision 2026-10-11).

A deploy is green only when the public Ask viewer serves the deployment: its
startup check passed, it serves the ``sai-`` semantic authority and the served
model that the deployment's own status document records, and its corpus
passed the served-model check. Nothing is declared by an operator; there is
no bundle id. A revision from before the retirement is refused before any
host change and is rolled back from the rollback tag instead.

The tests run the REAL ``deploy.write_status`` output through the verifier.
"""
from __future__ import annotations

import copy
import importlib.util
import json
import subprocess
from pathlib import Path
from typing import Any

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "deployment" / "scripts"
API_WORKFLOW = REPO / ".github" / "workflows" / "deploy-public-sysml-api.yml"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"post_deploy_{name}", SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


deploy = _load("deploy")
verify_api = _load("verify_public_api")


def _status_document(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from test_public_deployment import _evidence_bundle

    bundle_dir, meta = _evidence_bundle(tmp_path / "bundle")
    evidence = deploy.validate_bundle(bundle_dir)
    monkeypatch.setattr(deploy, "STATUS_DIR", tmp_path / "status")
    deployment = {
        "sysml_project_id": "deploy-project",
        "sysml_commit_id": "deploy-commit",
        "element_count": 5,
        "kernel_binding_summary": {"mapped": 30, "unresolved": 0, "ambiguous": 0},
        "served_model": meta["served_model"],
    }
    path = deploy.write_status(evidence, deployment)
    return json.loads(path.read_text(encoding="utf-8"))


def _block(document: dict[str, Any], **changes) -> dict[str, Any]:
    baseline = document["baseline"]
    block = {"kind": "model", "startup_check": "passed",
             "semantic_authority": baseline["semantic_authority"]["id"],
             "semantic_authority_id": baseline["semantic_authority"]["id"],
             "served_model": baseline["served_model"]["content_sha256"],
             "served_model_check": "passed"}
    block.update(changes)
    return block


# -- the status document the deploy writes ------------------------------------------


def test_real_write_status_output_passes_the_mandatory_check(tmp_path, monkeypatch):
    document = _status_document(tmp_path, monkeypatch)
    assert {"semantic_authority", "served_model"} <= set(document["baseline"])
    verify_api.check_status_payload(document)


@pytest.mark.parametrize("field", ["semantic_authority", "served_model", "git_commit"])
def test_a_status_document_missing_its_identity_is_refused(tmp_path, monkeypatch, field):
    document = _status_document(tmp_path, monkeypatch)
    del document["baseline"][field]
    with pytest.raises(verify_api.VerificationError, match=field):
        verify_api.check_status_payload(document)


@pytest.mark.parametrize("mutate", [
    lambda a: a.update(id="sai-short"),
    lambda a: a.update(id="xyz-" + "b" * 32),
    lambda a: a.update(schema="de4sdv.semantic-authority/v0"),
    lambda a: a.update(layers=[]),
    lambda a: a.update(extra="x"),
    lambda a: a.pop("layers"),
])
def test_malformed_semantic_authority_is_refused(tmp_path, monkeypatch, mutate):
    document = _status_document(tmp_path, monkeypatch)
    mutate(document["baseline"]["semantic_authority"])
    with pytest.raises(verify_api.VerificationError, match="semantic_authority"):
        verify_api.check_status_payload(document)


def test_malformed_served_model_is_refused(tmp_path, monkeypatch):
    document = _status_document(tmp_path, monkeypatch)
    document["baseline"]["served_model"]["content_sha256"] = "not-a-digest"
    with pytest.raises(verify_api.VerificationError, match="served_model"):
        verify_api.check_status_payload(document)


def test_a_pre_retirement_status_document_is_not_this_verifier_s_to_pass(tmp_path, monkeypatch):
    """063c4fb1's deploy wrote no served model; its own verifier checks it."""
    document = _status_document(tmp_path, monkeypatch)
    document["baseline"]["served_model"] = None
    with pytest.raises(verify_api.VerificationError, match="predates the release-ceremony retirement"):
        verify_api.check_status_payload(document)


def test_check_status_document_delegates_to_the_payload_check(tmp_path, monkeypatch):
    document = copy.deepcopy(_status_document(tmp_path, monkeypatch))
    monkeypatch.setattr(verify_api, "fetch_json", lambda url: document)
    assert verify_api.check_status_document("https://example.invalid") is document
    del document["baseline"]["served_model"]
    with pytest.raises(verify_api.VerificationError):
        verify_api.check_status_document("https://example.invalid")


# -- the Ask viewer must serve the deployment --------------------------------------


def test_the_served_deployment_passes(tmp_path, monkeypatch):
    document = _status_document(tmp_path, monkeypatch)
    block = verify_api.check_ask_semantic_authority(
        {"semantic_authority": _block(document)}, status_doc=document)
    assert block["served_model_check"] == "passed"


@pytest.mark.parametrize("changes,match", [
    ({"kind": "invalid", "error": "startup check refused: dirty tree"}, "refused to start"),
    ({"kind": "legacy"}, "kind is 'legacy'"),
    ({"semantic_authority_id": None, "state": "starting"}, "not built"),
    ({"semantic_authority": "sai-" + "9" * 32}, "serves semantic authority"),
    ({"served_model": "sha256:" + "9" * 64}, "served model"),
    ({"served_model_check": "failed: the corpus holds 1 elements"}, "served-model check failed"),
])
def test_a_viewer_that_does_not_serve_the_deployment_fails(tmp_path, monkeypatch, changes, match):
    document = _status_document(tmp_path, monkeypatch)
    with pytest.raises(verify_api.VerificationError, match=match):
        verify_api.check_ask_semantic_authority(
            {"semantic_authority": _block(document, **changes)}, status_doc=document)


def test_a_missing_authority_block_fails(tmp_path, monkeypatch):
    document = _status_document(tmp_path, monkeypatch)
    with pytest.raises(verify_api.VerificationError, match="no semantic_authority block"):
        verify_api.check_ask_semantic_authority({}, status_doc=document)


def test_the_wait_returns_when_the_warm_up_is_ready(tmp_path, monkeypatch):
    document = _status_document(tmp_path, monkeypatch)
    observations = iter([
        {"semantic_authority": {"kind": "model", "state": "starting"},
         "semantic_warmup": {"status": "warming"}},
        {"semantic_authority": _block(document, served_model_check="pending"),
         "semantic_warmup": {"status": "warming"}},
        {"semantic_authority": _block(document), "semantic_warmup": {"status": "ready"}},
    ])
    monkeypatch.setattr(verify_api, "fetch_ask_status", lambda url: next(observations))
    monkeypatch.setattr(verify_api.time, "sleep", lambda seconds: None)
    block = verify_api.wait_for_ask_semantic_runtime(
        "https://ask.invalid", document, ready=True, timeout_seconds=60)
    assert block["served_model_check"] == "passed"


def test_the_wait_fails_at_once_on_a_failed_served_model_check(tmp_path, monkeypatch):
    document = _status_document(tmp_path, monkeypatch)
    observed = {"semantic_authority": _block(document, served_model_check="failed: drift"),
                "semantic_warmup": {"status": "error"}}
    calls = []
    monkeypatch.setattr(verify_api, "fetch_ask_status", lambda url: calls.append(1) or observed)
    with pytest.raises(verify_api.VerificationError, match="served-model check failed"):
        verify_api.wait_for_ask_semantic_runtime(
            "https://ask.invalid", document, ready=True, timeout_seconds=600)
    assert calls == [1]


def test_the_wait_names_a_warm_up_that_never_finishes(tmp_path, monkeypatch):
    document = _status_document(tmp_path, monkeypatch)
    observed = {"semantic_authority": _block(document, served_model_check="pending"),
                "semantic_warmup": {"status": "warming"}}
    monkeypatch.setattr(verify_api, "fetch_ask_status", lambda url: observed)
    monkeypatch.setattr(verify_api.time, "sleep", lambda seconds: None)
    with pytest.raises(verify_api.VerificationError, match="warm-up not ready"):
        verify_api.wait_for_ask_semantic_runtime(
            "https://ask.invalid", document, ready=True, timeout_seconds=0)


# -- no declared authority anywhere -------------------------------------------------


def _verify_api_main(argv):
    import sys

    saved = sys.argv
    sys.argv = ["verify_public_api.py", *argv]
    try:
        return verify_api.main()
    finally:
        sys.argv = saved


def test_the_verifiers_take_no_declared_authority():
    with pytest.raises(SystemExit):
        _verify_api_main(["--expected-semantic-authority", "mab-" + "1" * 32])
    ask = _load("verify_public_ask")
    with pytest.raises(SystemExit):
        ask.main(["--application-sha", "a" * 40,
                  "--expected-model-authority-bundle-id", "mab-" + "1" * 32])


def test_the_api_deploy_workflow_declares_no_authority():
    workflow = yaml.safe_load(API_WORKFLOW.read_text(encoding="utf-8"))
    triggers = workflow.get("on", workflow.get(True))
    assert set(triggers["workflow_dispatch"]["inputs"]) == {"git_sha", "artifact_run_id"}
    text = API_WORKFLOW.read_text(encoding="utf-8")
    assert "expected_semantic_authority" not in text and "EXPECTED_SEMANTIC_AUTHORITY" not in text
    assert "verify_public_api.py --json /tmp/verify.json\n" in text


def _guard_script() -> str:
    workflow = yaml.safe_load(API_WORKFLOW.read_text(encoding="utf-8"))
    step = next(s for s in workflow["jobs"]["deploy"]["steps"]
                if s.get("name") == "Validate deployment ref (fail closed on PR heads)")
    run = step["run"]
    return run[run.index("# A revision from before the release-ceremony retirement"):]


@pytest.mark.parametrize("pre_retirement,refused", [(True, True), (False, False)])
def test_the_api_deploy_refuses_a_pre_retirement_revision_before_any_host_change(
        tmp_path, pre_retirement, refused):
    repo = tmp_path / "repo"
    (repo / "deployment").mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    compose = "services:\n  ask-viewer:\n    environment:\n"
    if pre_retirement:
        compose += "      DE4SDV_MODEL_AUTHORITY_BUNDLE_ID: ${DE4SDV_MODEL_AUTHORITY_BUNDLE_ID:-}\n"
    (repo / "deployment" / "compose.yaml").write_text(compose)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t",
                    "commit", "-qm", "c"], check=True)
    sha = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], check=True,
                         capture_output=True, text=True).stdout.strip()
    result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", _guard_script()], cwd=repo,
                            env={"DEPLOY_SHA": sha, "PATH": "/usr/bin:/bin"},
                            capture_output=True, text=True)
    assert (result.returncode != 0) is refused, result.stdout + result.stderr
    if refused:
        assert "predates the release-ceremony retirement" in result.stderr
        assert "rollback tag" in result.stderr
