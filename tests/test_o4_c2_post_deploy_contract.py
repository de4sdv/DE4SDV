"""Post-deploy contract of the O4 Wave C2 deployment (independent review R1/R3).

R1: the first C2 deploy must pass its own mandatory post-deploy check. The
status document written by ``deploy.write_status`` carries
``baseline.semantic_authority`` (C2); a pre-C2 rollback revision (``ff0311b``)
writes ``baseline.ontology``. ``verify_public_api.check_status_payload``
accepts exactly one of the two, each validated with a strict shape.

The tests run the REAL ``deploy.write_status`` output through the verifier,
and a document in the exact pre-C2 shape (synthetic values, the field set
``ff0311b``'s ``write_status`` produces).
"""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / "deployment" / "scripts"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(f"c2_{name}", SCRIPTS / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


deploy = _load("deploy")
verify_api = _load("verify_public_api")


def _c2_status_document(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    from test_public_deployment import _evidence_bundle

    bundle_dir, _meta = _evidence_bundle(tmp_path / "bundle")
    evidence = deploy.validate_bundle(bundle_dir)
    monkeypatch.setattr(deploy, "STATUS_DIR", tmp_path / "status")
    deployment = {
        "sysml_project_id": "deploy-project",
        "sysml_commit_id": "deploy-commit",
        "element_count": 5,
        "kernel_binding_summary": {"mapped": 30, "unresolved": 0, "ambiguous": 0},
    }
    path = deploy.write_status(evidence, deployment)
    return json.loads(path.read_text(encoding="utf-8"))


def _pre_c2_status_document() -> dict[str, Any]:
    """The field set ff0311b's deploy.write_status publishes (synthetic values)."""
    return {
        "service": "DE4SDV Experimental Read-Only Systems Modeling API",
        "status": "experimental",
        "read_only": True,
        "api_implementation": {
            "repository": "https://github.com/Systems-Modeling/SysML-v2-API-Services",
            "revision": "0af711b1",
        },
        "baseline": {
            "git_commit": "f" * 40,
            "sysml_project_id": "deploy-project",
            "sysml_commit_id": "deploy-commit",
            "ontology": {
                "path": "synthetic/pre-c2-authored-ontology.yaml",
                "sha256": "d" * 64,
            },
            "export_sha256": "e" * 64,
            "element_count": 5,
            "ontology_summary": {"mapped": 30, "unresolved": 0, "ambiguous": 0},
        },
        "deployed_at_utc": "2026-10-07T00:00:00Z",
    }


def test_real_c2_write_status_output_passes_the_mandatory_check(tmp_path, monkeypatch):
    document = _c2_status_document(tmp_path, monkeypatch)
    assert "semantic_authority" in document["baseline"]
    assert "ontology" not in document["baseline"]
    verify_api.check_status_payload(document)


def test_pre_c2_rollback_status_document_passes_the_mandatory_check():
    verify_api.check_status_payload(_pre_c2_status_document())


def test_status_document_without_any_authority_identity_is_refused(tmp_path, monkeypatch):
    document = _c2_status_document(tmp_path, monkeypatch)
    del document["baseline"]["semantic_authority"]
    with pytest.raises(verify_api.VerificationError, match="semantic_authority.*ontology"):
        verify_api.check_status_payload(document)


def test_status_document_with_both_identities_is_refused(tmp_path, monkeypatch):
    document = _c2_status_document(tmp_path, monkeypatch)
    document["baseline"]["ontology"] = _pre_c2_status_document()["baseline"]["ontology"]
    with pytest.raises(verify_api.VerificationError, match="exactly one"):
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
    document = _c2_status_document(tmp_path, monkeypatch)
    mutate(document["baseline"]["semantic_authority"])
    with pytest.raises(verify_api.VerificationError, match="semantic_authority"):
        verify_api.check_status_payload(document)


@pytest.mark.parametrize("mutate", [
    lambda o: o.update(sha256="D" * 64),
    lambda o: o.update(sha256="d" * 63),
    lambda o: o.update(path=""),
    lambda o: o.update(extra="x"),
    lambda o: o.pop("path"),
])
def test_malformed_pre_c2_ontology_identity_is_refused(mutate):
    document = _pre_c2_status_document()
    mutate(document["baseline"]["ontology"])
    with pytest.raises(verify_api.VerificationError, match="ontology"):
        verify_api.check_status_payload(document)


def test_check_status_document_delegates_to_the_payload_check(monkeypatch):
    """The fetching wrapper runs exactly the payload check (no second contract)."""
    document = copy.deepcopy(_pre_c2_status_document())
    monkeypatch.setattr(verify_api, "fetch_json", lambda url: document)
    assert verify_api.check_status_document("https://example.invalid") is document
    del document["baseline"]["ontology"]
    with pytest.raises(verify_api.VerificationError):
        verify_api.check_status_document("https://example.invalid")


# ---------------------------------------------------------------------------
# R3: an unset or stale selector must not deploy green.
#
# /ask-status.json .semantic_authority is checked after the API deploy
# (verify_public_api.check_ask_semantic_authority, against the operator's
# declared expectation), by the Ask verifier (served authority must equal the
# accepted mab: id) and by the monitor (invalid alerts).

MAB = "mab-" + "1" * 32
OTHER_MAB = "mab-" + "2" * 32


def _model_block(bundle_id: str = MAB, *, served: bool = True) -> dict[str, Any]:
    block = {
        "kind": "model",
        "authority_id": "mab:" + bundle_id,
        "bundle_id": bundle_id,
        "bundle_path": "/run/de4sdv/model/de4sdv-model-authority-bundle.json",
    }
    if served:
        block["semantic_authority_id"] = block["authority_id"]
    else:
        block["state"] = "requested"
    return block


_INVALID_UNSET = {
    "kind": "invalid",
    "error": "DE4SDV_SEMANTIC_AUTHORITY is unset; the only accepted value is model",
    "note": "semantic authority selector is invalid; semantic answers are refused",
}


def test_model_authority_ids_use_the_runtime_formula():
    from de4sdv.semantic.entry_authority import model_authority_id

    import semantic_authority_check as sac

    assert _model_block()["authority_id"] == model_authority_id(MAB)
    assert sac.model_authority_id(MAB) == model_authority_id(MAB)


def test_post_deploy_accepts_the_declared_model_bundle(tmp_path, monkeypatch):
    status = _c2_status_document(tmp_path, monkeypatch)
    for served in (True, False):  # before re-closing, the runtime is only requested
        result = verify_api.check_ask_semantic_authority(
            {"semantic_authority": _model_block(served=served)},
            expected=MAB, status_doc=status,
        )
        assert result["kind"] == "model" and result["bundle_id"] == MAB


@pytest.mark.parametrize("block, message", [
    (_INVALID_UNSET, "invalid"),
    ({"kind": "invalid", "error": "retired value legacy"}, "invalid"),
    (_model_block(OTHER_MAB), "bundle"),
    ({**_model_block(), "authority_id": "mab:" + "3" * 32}, "authority_id"),
    ({**_model_block(), "semantic_authority_id": "mab:" + "3" * 32}, "serves"),
    ({"kind": "legacy", "authority_id": "legacy"}, "kind"),
])
def test_post_deploy_fails_an_unset_stale_or_mismatched_selector(
    tmp_path, monkeypatch, block, message,
):
    status = _c2_status_document(tmp_path, monkeypatch)
    with pytest.raises(verify_api.VerificationError, match=message):
        verify_api.check_ask_semantic_authority(
            {"semantic_authority": block}, expected=MAB, status_doc=status,
        )


def test_post_deploy_refuses_a_missing_authority_block(tmp_path, monkeypatch):
    status = _c2_status_document(tmp_path, monkeypatch)
    with pytest.raises(verify_api.VerificationError, match="semantic_authority"):
        verify_api.check_ask_semantic_authority({}, expected=MAB, status_doc=status)


def test_post_deploy_refuses_a_non_model_expectation_on_a_c2_revision(tmp_path, monkeypatch):
    status = _c2_status_document(tmp_path, monkeypatch)
    with pytest.raises(verify_api.VerificationError, match="pre-C2"):
        verify_api.check_ask_semantic_authority(
            {"semantic_authority": {"kind": "legacy", "authority_id": "legacy"}},
            expected="legacy", status_doc=status,
        )


@pytest.mark.parametrize("expected", ["", "model", "mab-XYZ", "o3", "o3:", "sai-" + "1" * 32])
def test_post_deploy_refuses_a_malformed_expectation(tmp_path, monkeypatch, expected):
    status = _c2_status_document(tmp_path, monkeypatch)
    with pytest.raises(verify_api.VerificationError, match="expected semantic authority"):
        verify_api.check_ask_semantic_authority(
            {"semantic_authority": _model_block()}, expected=expected, status_doc=status,
        )


def test_pre_c2_rollback_declares_the_authority_that_revision_serves():
    status = _pre_c2_status_document()
    legacy = {"kind": "legacy", "authority_id": "legacy"}
    o3 = {"kind": "o3", "authority_id": "o3:abc", "bundle_id": "o3b-abc"}
    verify_api.check_ask_semantic_authority(
        {"semantic_authority": legacy}, expected="legacy", status_doc=status)
    verify_api.check_ask_semantic_authority(
        {"semantic_authority": o3}, expected="o3:o3b-abc", status_doc=status)
    verify_api.check_ask_semantic_authority(
        {"semantic_authority": _model_block()}, expected=MAB, status_doc=status)
    # a stale C2 environment left in place for the rollback is caught
    with pytest.raises(verify_api.VerificationError, match="kind"):
        verify_api.check_ask_semantic_authority(
            {"semantic_authority": _model_block(OTHER_MAB)}, expected="legacy",
            status_doc=status)
    with pytest.raises(verify_api.VerificationError, match="bundle"):
        verify_api.check_ask_semantic_authority(
            {"semantic_authority": o3}, expected="o3:o3b-other", status_doc=status)
    with pytest.raises(verify_api.VerificationError, match="invalid"):
        verify_api.check_ask_semantic_authority(
            {"semantic_authority": _INVALID_UNSET}, expected="legacy", status_doc=status)


def test_verify_public_api_cli_requires_the_expected_authority():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_public_api.py"),
         "--base-url", "https://example.invalid"],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "--expected-semantic-authority" in result.stderr


def test_deploy_workflow_passes_the_declared_authority_to_the_mandatory_check():
    workflow = (REPO / ".github" / "workflows" / "deploy-public-sysml-api.yml").read_text(
        encoding="utf-8")
    assert "expected_semantic_authority:" in workflow
    step = workflow[workflow.index("Post-deploy public verification (mandatory)"):]
    step = step[: step.index("- name:", 10)]
    assert '--expected-semantic-authority "$EXPECTED_SEMANTIC_AUTHORITY"' in step
    assert "inputs.expected_semantic_authority" in workflow


# --- Ask verifier: the served authority must be the accepted bundle ---------

verify_ask = _load("verify_public_ask")


@pytest.mark.parametrize("block, message", [
    (_INVALID_UNSET, "invalid"),
    (_model_block(OTHER_MAB), "bundle"),
    (_model_block(served=False), "serves"),  # requested but not served
    ({"kind": "legacy", "authority_id": "legacy"}, "kind"),
])
def test_ask_verifier_requires_the_served_accepted_bundle(block, message):
    with pytest.raises(verify_ask.VerificationError, match=message):
        verify_ask.check_semantic_authority(
            {"semantic_authority": block}, expected_bundle_id=MAB)


def test_ask_verifier_accepts_the_served_accepted_bundle():
    result = verify_ask.check_semantic_authority(
        {"semantic_authority": _model_block()}, expected_bundle_id=MAB)
    assert result["semantic_authority_id"] == "mab:" + MAB


def test_ask_verifier_cli_requires_the_expected_bundle_id():
    import subprocess
    import sys

    result = subprocess.run(
        [sys.executable, str(SCRIPTS / "verify_public_ask.py"),
         "--application-sha", "a" * 40],
        capture_output=True, text=True,
    )
    assert result.returncode == 2
    assert "--expected-model-authority-bundle-id" in result.stderr


def test_ask_deploy_workflow_passes_the_accepted_bundle_id():
    workflow = (REPO / ".github" / "workflows" / "deploy-public-ask-viewer.yml").read_text(
        encoding="utf-8")
    assert "model_authority_bundle_id:" in workflow
    assert '--expected-model-authority-bundle-id "$MODEL_AUTHORITY_BUNDLE_ID"' in workflow


# --- Monitor: invalid alerts ------------------------------------------------

monitor = _load("monitor_public_ask")


def _ask_status(block: dict[str, Any] | None) -> dict[str, Any]:
    status = {
        "application_git_commit": "a" * 40,
        "model_git_commit": "b" * 40,
        "semantic_warmup": {"status": "ready"},
    }
    if block is not None:
        status["semantic_authority"] = block
    return status


def _patched_monitor(monkeypatch, ask_status):
    def fake_get(url):
        if url.endswith("/ask-status.json"):
            return ask_status
        return {"baseline": {"git_commit": "b" * 40}}

    monkeypatch.setattr(monitor, "_get_json", fake_get)
    return monitor.monitor_public_ask(ask_url="https://ask.invalid",
                                      model_status_url="https://api.invalid/s.json")


@pytest.mark.parametrize("block, message", [
    (_INVALID_UNSET, "invalid"),
    (None, "semantic_authority"),
    ({**_model_block(), "semantic_authority_id": "mab:" + "3" * 32}, "serves"),
])
def test_monitor_alerts_on_an_invalid_or_inconsistent_authority(monkeypatch, block, message):
    with pytest.raises(monitor.MonitorError, match=message):
        _patched_monitor(monkeypatch, _ask_status(block))


@pytest.mark.parametrize("block", [
    _model_block(),
    {"kind": "legacy", "authority_id": "legacy"},  # pre-C2 production is not an alert
])
def test_monitor_reports_the_served_authority(monkeypatch, block):
    result = _patched_monitor(monkeypatch, _ask_status(block))
    assert result["status"] == "healthy"
    assert result["semantic_authority_kind"] == block["kind"]


def test_pre_c2_rollback_with_a_model_expectation_requires_the_served_bundle():
    """F3: a pre-C2 revision is deployed with its bundle already closed at
    its own binding, so a model expectation must be SERVED there. ff0311b left
    with a request it cannot serve (for example the C2 mab- id) reports the
    request but no served id, and fails the post-deploy verification."""
    status = _pre_c2_status_document()
    with pytest.raises(verify_api.VerificationError, match="serves"):
        verify_api.check_ask_semantic_authority(
            {"semantic_authority": _model_block(served=False)}, expected=MAB,
            status_doc=status)
    verify_api.check_ask_semantic_authority(
        {"semantic_authority": _model_block(served=True)}, expected=MAB, status_doc=status)
