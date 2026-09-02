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
        # Direct (non-proxied) importer calls must present the allow-listed
        # Host header, or Play's AllowedHostsFilter returns 400 for every
        # request (deploy-host bridge IP is not in the allow list).
        assert "--api-host-header" in cmd
        assert cmd[cmd.index("--api-host-header") + 1] == deploy.api_host_header()
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


def test_workflow_run_metadata_fixture_rejects_wrong_run_and_accepts_real_shape() -> None:
    """Focused fixture using the ACTUAL GitHub Actions workflow-run metadata
    shape: 'path' is '.github/workflows/<file>' (no leading slash, no
    repository prefix) and 'repository' is a nested OBJECT whose 'full_name'
    is 'owner/repo'. The verifier must require exact workflow-path equality,
    check repository.full_name against the expected repository, and fail
    closed on missing repository/full_name."""
    wf = (REPO / ".github" / "workflows" / "deploy-public-sysml-api.yml").read_text(
        encoding="utf-8"
    )
    assert "path != expected_path" in wf
    assert "f\".github/workflows/{os.environ['PRIVILEGED_WORKFLOW_FILE']}\"" in wf
    # the old endswith form must be gone (it rejected the real response)
    assert "path.endswith(" not in wf
    # repository must be treated as an object with full_name
    assert "not isinstance(repository, dict)" in wf
    assert 'repository.get("full_name")' in wf
    # the old string-shape check must be gone
    assert 'meta.get("repository", "").lower()' not in wf

    # ---- Reproduce the exact verifier logic against real-shape metadata ----
    def run_verifier(meta: dict, expected_repo: str = "de4sdv/DE4SDV") -> list[str]:
        sha = "a" * 40
        expected_path = ".github/workflows/privileged-full-model-api-ingestion.yml"
        problems = []
        if meta.get("head_sha") != sha:
            problems.append(f"head_sha {meta.get('head_sha')} != requested {sha}")
        if meta.get("conclusion") != "success":
            problems.append(f"conclusion is {meta.get('conclusion')}, not success")
        path = (meta.get("path") or "")
        if path != expected_path:
            problems.append(f"workflow path {path!r} != {expected_path!r}")
        repository = meta.get("repository")
        if not isinstance(repository, dict):
            problems.append(f"repository is not an object: {repository!r}")
        else:
            full_name = repository.get("full_name")
            if not isinstance(full_name, str) or not full_name:
                problems.append("repository.full_name is missing")
            elif full_name.lower() != expected_repo.lower():
                problems.append(
                    f"repository.full_name {full_name!r} != {expected_repo!r}"
                )
        return problems

    # Real GitHub workflow-run response shape (repository is a nested object):
    real_meta = {
        "id": 1234567890,
        "head_sha": "a" * 40,
        "conclusion": "success",
        "path": ".github/workflows/privileged-full-model-api-ingestion.yml",
        "repository": {
            "id": 900000000,
            "name": "DE4SDV",
            "full_name": "de4sdv/DE4SDV",
            "private": False,
        },
    }
    assert run_verifier(real_meta) == []

    # Negative: repository object missing entirely.
    missing_repo = {k: v for k, v in real_meta.items() if k != "repository"}
    assert any("repository is not an object" in p for p in run_verifier(missing_repo))
    # repository as a plain string (the old wrong assumption) must also fail.
    assert any(
        "repository is not an object" in p
        for p in run_verifier(dict(real_meta, repository="de4sdv/DE4SDV"))
    )
    # Negative: full_name missing.
    assert any(
        "full_name is missing" in p
        for p in run_verifier(dict(real_meta, repository={"id": 1, "name": "DE4SDV"}))
    )
    # Negative: wrong full_name.
    assert any(
        "repository.full_name" in p
        for p in run_verifier(dict(real_meta, repository={"full_name": "attacker/DE4SDV"}))
    )
    # Negative: wrong workflow path must still be rejected.
    assert any(
        "workflow path" in p
        for p in run_verifier(dict(real_meta, path=".github/workflows/ci.yml"))
    )
    # Negative: wrong head_sha must still be rejected.
    assert any(
        "head_sha" in p for p in run_verifier(dict(real_meta, head_sha="b" * 40))
    )


def test_workflow_permissions_are_read_only_minimum() -> None:
    wf = (REPO / ".github" / "workflows" / "deploy-public-sysml-api.yml").read_text(
        encoding="utf-8"
    )
    assert "permissions:" in wf
    assert "  contents: read" in wf
    assert "  actions: read" in wf
    assert "write" not in wf


def test_workflow_defines_deploy_sha_once_at_job_level() -> None:
    wf = (REPO / ".github" / "workflows" / "deploy-public-sysml-api.yml").read_text(
        encoding="utf-8"
    )
    # One definition from the input at job level...
    assert "DEPLOY_SHA: ${{ inputs.git_sha }}" in wf
    # ...and no GITHUB_ENV round-trip for the SHA.
    assert 'echo "DEPLOY_SHA=' not in wf


def test_workflow_requires_out_of_band_host_key_verification() -> None:
    wf = (REPO / ".github" / "workflows" / "deploy-public-sysml-api.yml").read_text(
        encoding="utf-8"
    )
    assert "DEPLOY_SSH_KNOWN_HOSTS" in wf
    assert "StrictHostKeyChecking=yes" in wf
    # ssh-keyscan must never be USED dynamically: the only allowed mention is
    # in comments stating it is not trusted.
    code_lines = [
        line
        for line in wf.splitlines()
        if "ssh-keyscan" in line and not line.strip().startswith("#")
    ]
    assert code_lines == [], f"ssh-keyscan used in executable code: {code_lines}"


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
    # HTTP/3 is not exposed: no UDP port publishing (finding 7).
    assert "443:443/udp" not in compose_text
    assert '"80:80"' in compose_text and '"443:443"' in compose_text


def test_caddyfile_documents_actual_rate_limit_behavior(caddyfile_text: str) -> None:
    # 50 events / 10 s window / per remote host — and no invented burst claim.
    assert "events 50" in caddyfile_text
    assert "window 10s" in caddyfile_text
    assert "key {remote_host}" in caddyfile_text
    # 'burst' may only appear inside a comment explaining that no burst
    # parameter exists; never as configuration.
    config_lines = [
        line
        for line in caddyfile_text.splitlines()
        if "burst" in line.lower() and not line.strip().startswith("#")
    ]
    assert config_lines == [], f"burst configured: {config_lines}"


def test_caddy_image_and_compose_provenance_use_actual_pin() -> None:
    dockerfile = (DEPLOYMENT / "caddy" / "Dockerfile").read_text(encoding="utf-8")
    compose_text = (DEPLOYMENT / "compose.yaml").read_text(encoding="utf-8")
    actual_pin = "b8d8c9a9d99ee352d675cbbe416ec2b489fc8cab"
    assert actual_pin in dockerfile
    # The stale 5625512f pin may appear ONLY in the documented pin-note
    # explaining why the newer commits are not used; never in the LABEL.
    label_line = [ln for ln in dockerfile.splitlines() if "image.description" in ln][0]
    assert "5625512f" not in label_line
    assert "5625512f" not in compose_text
    assert "b8d8c9a9" in compose_text


def test_deploy_stops_public_proxy_before_import() -> None:
    import ast

    source = (DEPLOYMENT / "scripts" / "deploy.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    main_fn = next(
        n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef) and n.name == "main"
    )
    calls = [
        (n.lineno, n.func.id if isinstance(n.func, ast.Name) else getattr(n.func, "attr", "?"))
        for n in ast.walk(main_fn)
        if isinstance(n, ast.Call)
    ]
    order = [
        name
        for _line, name in calls
        if name in {"stop_public_proxy", "import_baseline", "write_status", "compose"}
    ]
    # stop_public_proxy must precede import_baseline; write_status must
    # precede the final compose(caddy up). Proven from the AST call order.
    assert "stop_public_proxy" in order
    assert order.index("stop_public_proxy") < order.index("import_baseline")
    assert order.index("import_baseline") < order.index("write_status")
    assert source.index("stop_public_proxy(args.repo)") < source.index(
        'compose("up", "-d", "caddy"'
    )
    assert source.index("write_status(evidence, deployment)") < source.index(
        'compose("up", "-d", "caddy"'
    )


def test_provision_script_installs_full_host_dependency_set() -> None:
    prov = (DEPLOYMENT / "scripts" / "provision-server.sh").read_text(encoding="utf-8")
    for pkg in ("git", "python3", "python3-venv", "curl", "ca-certificates", "openssl", "ufw"):
        assert pkg in prov, pkg
    # dedicated venv with the pinned importer dependency, not system python
    assert 'python3 -m venv "$VENV_DIR"' in prov
    assert "PyYAML==6.0.2" in prov
    assert '"$VENV_DIR/bin/pip" check' in prov
    # sanity check refuses partial provisioning
    assert "Dependency sanity check" in prov
    assert "all host dependencies present" in prov


def test_workflow_uses_dedicated_venv_python_for_deploy() -> None:
    wf = (REPO / ".github" / "workflows" / "deploy-public-sysml-api.yml").read_text(
        encoding="utf-8"
    )
    assert "/srv/de4sdv/venv/bin/python deployment/scripts/deploy.py" in wf
    assert "sudo DEPLOY_DIR=/srv/de4sdv python3 deployment/scripts/deploy.py" not in wf


# ------------------------------------------------- direct-call Host header


def test_wait_for_api_sends_allow_listed_host_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The readiness probe bypasses Caddy and must present the accepted Host.

    Regression: probing the container by bridge IP sent ``Host: <ip>:9000``,
    which Play's AllowedHostsFilter rejects with 400, so every deploy run
    timed out with "API did not become ready: HTTP Error 400".
    """
    captured: dict[str, Any] = {}

    class FakeResponse:
        status = 200

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    def fake_urlopen(request, timeout=None):
        captured["url"] = request.full_url
        captured["headers"] = {k.lower(): v for k, v in request.header_items()}
        return FakeResponse()

    monkeypatch.setattr(deploy, "api_base_url_from_docker", lambda: "http://172.18.0.5:9000")
    monkeypatch.setattr(deploy.urlrequest, "urlopen", fake_urlopen)

    deploy.wait_for_api(timeout_s=5)

    assert captured["url"] == "http://172.18.0.5:9000/projects"
    assert captured["headers"]["host"] == deploy.api_host_header()
    # The accepted value must be the compose service name, not an address.
    assert deploy.api_host_header() == "sysml2-api:9000"


def test_importer_threads_host_header_into_api_client() -> None:
    """``--api-host-header`` reaches ApiClient.default_headers; absent flag = no Host override."""
    import inspect

    from de4sdv.sysml_api.client import ApiClient

    spec = importlib.util.spec_from_file_location(
        "import_sysml_api_baseline", REPO / "scripts" / "import_sysml_api_baseline.py"
    )
    assert spec is not None and spec.loader is not None
    importer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(importer)

    signature = inspect.signature(importer.run_import)
    assert "api_host_header" in signature.parameters
    assert signature.parameters["api_host_header"].default is None

    # ApiClient maps default_headers into every request (the mechanism used).
    client = ApiClient("http://172.18.0.5:9000", default_headers={"Host": "sysml2-api:9000"})
    request_headers = {"Accept": "application/json", **client.default_headers}
    assert request_headers["Host"] == "sysml2-api:9000"
    # No flag -> empty default_headers -> urllib auto-Host (unchanged behavior).
    assert ApiClient("http://host:9000").default_headers == {}
