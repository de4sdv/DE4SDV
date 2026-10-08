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
                "path": "approach/framework/ontology/de4sdv-basic-ontology.yaml",
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
