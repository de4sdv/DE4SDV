"""Focused tests for the PR #176 deployment hardening.

Covers the human-review blockers that can be tested without a live host:

- privileged bundle validation (BLOCKER 1 / 6 defense in depth);
- export digest mismatch rejection;
- ontology identity mismatch rejection;
- Git HEAD mismatch / dirty checkout rejection (BLOCKER 2);
- fresh-server import path: deployment-specific project/commit identities
  are accepted and the privileged CI UUIDs are NOT required (BLOCKER 1);
- immutable evidence cross-checks (element/reference counts);
- Caddyfile strict method allowlist (BLOCKER 4);
- Caddyfile status-directory mapping (BLOCKER 5);
- Caddyfile / Caddy binary availability for validation (BLOCKER 3).

The scripts are imported from deployment/scripts as modules.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[1]
DEPLOYMENT = REPO / "deployment"


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, DEPLOYMENT / "scripts" / f"{name}.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


deploy = _load("deploy")


def _evidence_bundle(tmp_path: Path) -> tuple[Path, dict[str, Any]]:
    """Build a synthetic-but-consistent privileged bundle.

    Mirrors the real artifact shape produced by the privileged workflow:
    same keys, sane counts, one Git SHA, one ontology identity.
    """
    tmp_path.mkdir(parents=True, exist_ok=True)
    git_sha = "a" * 40
    ontology = {
        "path": "approach/framework/ontology/de4sdv-basic-ontology.yaml",
        "sha256": "b" * 64,
    }
    export = {
        "git_commit": git_sha,
        "elements": [{"@id": f"e{i}", "@type": "PartUsage"} for i in range(5)],
    }
    export_path = tmp_path / "de4sdv-full-model-export.json"
    export_path.write_text(json.dumps(export), encoding="utf-8")
    export_digest = deploy.sha256_file(export_path)

    report = {
        "schema": "de4sdv-full-model-semantic-validation/v1",
        "git_commit": git_sha,
        "sysml_project_id": "ci-project",
        "sysml_commit_id": "ci-commit",
        "source_export_sha256": export_digest,
        "source_document_count": 59,
        "element_count": 56745,
        "internal_reference_count": 189930,
        "ontology": {
            "passed": True,
            "summary": {"mapped": 30, "native": 16, "external": 4, "unresolved": 0, "ambiguous": 0},
        },
        "ontology_identity": ontology,
    }
    binding = {
        "git_repository": "de4sdv/DE4SDV",
        "git_commit": git_sha,
        "sysml_project_id": "ci-project",
        "sysml_commit_id": "ci-commit",
        "import_timestamp": "2026-09-01T00:00:00Z",
        "import_tool_version": "de4sdv-full-model-import/1+official-syside-json",
        "semantic_validation": "passed",
        "ontology": ontology,
        "scope": "full-model",
    }
    mcp = {
        "read_only": True,
        "tool_count": 7,
        "revision": {
            "git_commit": git_sha,
            "ontology": ontology,
            "scope": "full-model",
        },
    }
    coverage = {"schema": "de4sdv-full-model-semantic-query-coverage/v1"}
    for name, payload in (
        ("de4sdv-full-model-semantic-validation.json", report),
        ("de4sdv-full-model-binding.json", binding),
        ("de4sdv-semantic-mcp-validation.json", mcp),
        ("de4sdv-full-model-semantic-query-coverage.json", coverage),
    ):
        (tmp_path / name).write_text(json.dumps(payload), encoding="utf-8")
    return tmp_path, {"git_sha": git_sha, "ontology": ontology, "export_digest": export_digest}


# ---------------------------------------------------------------- blockers 1/6


def test_bundle_validation_accepts_consistent_privileged_artifact(tmp_path: Path) -> None:
    bundle_dir, facts = _evidence_bundle(tmp_path)
    evidence = deploy.validate_bundle(bundle_dir)
    assert evidence["git_commit"] == facts["git_sha"]
    assert evidence["export_sha256"] == facts["export_digest"]
    assert evidence["expected_element_count"] == 56745


def test_bundle_rejects_export_digest_mismatch(tmp_path: Path) -> None:
    bundle_dir, _facts = _evidence_bundle(tmp_path)
    export = bundle_dir / "de4sdv-full-model-export.json"
    data = json.loads(export.read_text())
    data["elements"] = data["elements"] + [{"@id": "extra", "@type": "PartUsage"}]
    export.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(deploy.DeployError, match="export digest mismatch"):
        deploy.validate_bundle(bundle_dir)


def test_bundle_rejects_ontology_identity_mismatch(tmp_path: Path) -> None:
    bundle_dir, _facts = _evidence_bundle(tmp_path)
    report = json.loads(
        (bundle_dir / "de4sdv-full-model-semantic-validation.json").read_text()
    )
    report["ontology_identity"] = {
        "path": "other.yaml",
        "sha256": "c" * 64,
    }
    (bundle_dir / "de4sdv-full-model-semantic-validation.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    with pytest.raises(deploy.DeployError, match="ontology identity"):
        deploy.validate_bundle(bundle_dir)


def test_bundle_rejects_unclean_ontology_summary(tmp_path: Path) -> None:
    bundle_dir, _facts = _evidence_bundle(tmp_path)
    report = json.loads(
        (bundle_dir / "de4sdv-full-model-semantic-validation.json").read_text()
    )
    report["ontology"]["summary"]["unresolved"] = 2
    (bundle_dir / "de4sdv-full-model-semantic-validation.json").write_text(
        json.dumps(report), encoding="utf-8"
    )
    with pytest.raises(deploy.DeployError, match="not clean"):
        deploy.validate_bundle(bundle_dir)


# ------------------------------------------------------------------- blocker 2


def _init_repo(path: Path) -> str:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.email", "t@example.org"], cwd=path, check=True)
    subprocess.run(["git", "config", "user.name", "t"], cwd=path, check=True)
    (path / "deployment").mkdir(exist_ok=True)
    (path / "deployment" / "marker.txt").write_text("v1", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
    subprocess.run(["git", "commit", "-qm", "v1"], cwd=path, check=True)
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=path, text=True
    ).strip()


def test_repo_head_mismatch_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    head = _init_repo(repo)
    other_sha = "b" * 40
    with pytest.raises(deploy.DeployError, match="HEAD"):
        deploy.validate_repo_head(repo, other_sha)
    # sanity: matching head passes
    deploy.validate_repo_head(repo, head)


def test_dirty_repo_is_rejected(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    head = _init_repo(repo)
    (repo / "deployment" / "stale.txt").write_text("leftover", encoding="utf-8")
    with pytest.raises(deploy.DeployError, match="dirty"):
        deploy.validate_repo_head(repo, head)


# ------------------------------------------------------------------- blocker 1
# Fresh-server import behavior: the deployment must NOT require the
# privileged run's project/commit UUIDs; deployment-specific identities are
# generated by the deployment repository. We test the acceptance logic by
# exercising import_baseline()'s validation core via a monkeypatched
# subprocess.run (importer invocation) so no live API is needed.


def test_import_accepts_deployment_specific_identities(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_dir, facts = _evidence_bundle(tmp_path / "bundle")
    evidence = deploy.validate_bundle(bundle_dir)

    repo = tmp_path / "repo"
    _init_repo(repo)

    class Result:
        def check(self) -> None:  # pragma: no cover - subprocess.run never sees this
            raise AssertionError

    def fake_run(cmd, **_kwargs):
        # The importer must be invoked from the repo with the exact export.
        assert "scripts/import_sysml_api_baseline.py" in " ".join(cmd)
        assert str(evidence["export_path"]) in " ".join(cmd)
        # Simulate the deployment API repository generating its OWN identities.
        binding = {
            "git_commit": facts["git_sha"],
            "sysml_project_id": "deployment-project",
            "sysml_commit_id": "deployment-commit",
            "semantic_validation": "passed",
            "scope": "full-model",
            "ontology": facts["ontology"],
        }
        report = {
            "source_export_sha256": facts["export_digest"],
            "element_count": 56745,
            "internal_reference_count": 189930,
            "source_document_count": 59,
            "ontology": {
                "passed": True,
                "summary": {"mapped": 30, "native": 16, "external": 4, "unresolved": 0, "ambiguous": 0},
            },
        }
        artifacts = tmp_path / "artifacts" / "current"
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "de4sdv-full-model-binding.json").write_text(json.dumps(binding))
        (artifacts / "de4sdv-full-model-semantic-validation.json").write_text(json.dumps(report))
        return Result()

    monkeypatch.setattr(deploy.subprocess, "run", fake_run)
    monkeypatch.setattr(deploy, "wait_for_api", lambda *_a, **_k: None)
    monkeypatch.setattr(
        deploy, "api_base_url_from_docker", lambda: "http://127.0.0.1:1"
    )
    monkeypatch.setattr(deploy, "DEPLOY_DIR", tmp_path)

    deployment = deploy.import_baseline(repo, evidence)
    # Deployment-specific identities, NOT the privileged run's ci-project/ci-commit.
    assert deployment["sysml_project_id"] == "deployment-project"
    assert deployment["sysml_commit_id"] == "deployment-commit"


def test_import_rejects_count_drift_vs_privileged_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    bundle_dir, facts = _evidence_bundle(tmp_path / "bundle")
    evidence = deploy.validate_bundle(bundle_dir)
    repo = tmp_path / "repo"
    _init_repo(repo)

    def fake_run(cmd, **_kwargs):
        binding = {
            "git_commit": facts["git_sha"],
            "sysml_project_id": "deployment-project",
            "sysml_commit_id": "deployment-commit",
            "semantic_validation": "passed",
            "scope": "full-model",
            "ontology": facts["ontology"],
        }
        report = {
            "source_export_sha256": facts["export_digest"],
            "element_count": 56744,  # drift!
            "internal_reference_count": 189930,
            "source_document_count": 59,
            "ontology": {"passed": True, "summary": {"unresolved": 0, "ambiguous": 0}},
        }
        artifacts = tmp_path / "artifacts" / "current"
        artifacts.mkdir(parents=True, exist_ok=True)
        (artifacts / "de4sdv-full-model-binding.json").write_text(json.dumps(binding))
        (artifacts / "de4sdv-full-model-semantic-validation.json").write_text(json.dumps(report))
        return type("R", (), {})()

    monkeypatch.setattr(deploy.subprocess, "run", fake_run)
    monkeypatch.setattr(deploy, "wait_for_api", lambda *_a, **_k: None)
    monkeypatch.setattr(deploy, "api_base_url_from_docker", lambda: "http://127.0.0.1:1")
    monkeypatch.setattr(deploy, "DEPLOY_DIR", tmp_path)

    with pytest.raises(deploy.DeployError, match="element count"):
        deploy.import_baseline(repo, evidence)


# ------------------------------------------------- blockers 3/4/5 (Caddyfile)


@pytest.fixture(scope="module")
def caddyfile_text() -> str:
    return (DEPLOYMENT / "caddy" / "Caddyfile").read_text(encoding="utf-8")


def test_caddyfile_method_allowlist_is_positive(caddyfile_text: str) -> None:
    # Exactly one allow matcher listing only the permitted verbs...
    assert "@allowed_methods method GET HEAD OPTIONS" in caddyfile_text
    # ...and a negated matcher rejecting everything else...
    assert "@rejected_methods not method GET HEAD OPTIONS" in caddyfile_text
    assert "respond @rejected_methods 405" in caddyfile_text
    # ...no old deny-list must remain.
    assert "@mutations" not in caddyfile_text


def test_caddyfile_status_directory_mapping(caddyfile_text: str) -> None:
    assert "root * /srv/de4sdv-status" in caddyfile_text
    compose_text = (DEPLOYMENT / "compose.yaml").read_text(encoding="utf-8")
    assert "${DEPLOY_DIR}/status:/srv/de4sdv-status:ro" in compose_text
    # The repository's static status dir must NOT be mounted into caddy.
    assert "deployment/status:/srv" not in compose_text


def test_caddyfile_rate_limit_module_declared_in_image() -> None:
    dockerfile = (DEPLOYMENT / "caddy" / "Dockerfile").read_text(encoding="utf-8")
    assert "caddy-ratelimit@" in dockerfile
    assert "xcaddy build" in dockerfile
    assert "caddy list-modules | grep -q 'rate_limit'" in dockerfile


def _caddy_image_available() -> bool:
    result = subprocess.run(
        ["docker", "image", "inspect", "de4sdv/caddy-ratelimit:2.8.4"],
        capture_output=True,
    )
    return result.returncode == 0


@pytest.mark.skipif(
    not shutil.which("docker") or not _caddy_image_available(),
    reason="de4sdv/caddy-ratelimit:2.8.4 image not built on this host",
)
def test_caddyfile_validates_with_real_binary(tmp_path: Path) -> None:
    caddyfile = DEPLOYMENT / "caddy" / "Caddyfile"
    result = subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{caddyfile}:/etc/caddy/Caddyfile:ro",
            "-e",
            "ACME_EMAIL=probe@example.org",
            "-e",
            "XDG_CONFIG_HOME=/tmp",
            "--entrypoint",
            "caddy",
            "de4sdv/caddy-ratelimit:2.8.4",
            "validate",
            "--config",
            "/etc/caddy/Caddyfile",
            "--adapter",
            "caddyfile",
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Valid configuration" in result.stdout


# ------------------------------------------------------- blocker 6 (workflow)


def test_workflow_verifies_explicit_run_metadata() -> None:
    wf = (REPO / ".github" / "workflows" / "deploy-public-sysml-api.yml").read_text(
        encoding="utf-8"
    )
    # Explicit run-id path must independently verify workflow file, success,
    # and head SHA equality.
    assert 'meta.get("head_sha") != sha' in wf
    assert 'meta.get("conclusion") != "success"' in wf
    assert "PRIVILEGED_WORKFLOW_FILE" in wf
    # Ambiguous auto-detection must refuse.
    assert "AMBIG:" in wf
    # Verification is mandatory: no skip input remains.
    assert "skip_verification" not in wf


def test_workflow_uses_real_git_checkout() -> None:
    wf = (REPO / ".github" / "workflows" / "deploy-public-sysml-api.yml").read_text(
        encoding="utf-8"
    )
    assert "checkout --detach --force" in wf
    assert "reset --hard" in wf
    assert "clean -ffd" in wf
    # The old fake-checkout must be gone.
    assert "git init -q" not in wf
    assert "--exclude=.git" not in wf


def test_compose_publishes_only_proxy_ports() -> None:
    compose_text = (DEPLOYMENT / "compose.yaml").read_text(encoding="utf-8")
    ports_sections = compose_text.count("ports:")
    assert ports_sections == 1  # caddy only
    assert '"9000:9000"' not in compose_text
    assert '"5432:5432"' not in compose_text
    assert "network_mode: host" not in compose_text
