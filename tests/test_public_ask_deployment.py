import json
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
import yaml

from deployment.ask_viewer.entrypoint import (
    RuntimeContractError,
    validate_runtime_contract,
)
from deployment.scripts.monitor_public_ask import monitor_public_ask
from deployment.scripts.verify_public_ask import verify_public_ask


def _git(repo, *args):
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _commit(repo, message):
    _git(repo, "add", ".")
    _git(repo, "commit", "-m", message)
    return _git(repo, "rev-parse", "HEAD")


def _runtime_repo(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "test@example.invalid")
    _git(repo, "config", "user.name", "Test")
    model = repo / "textual-notation-of-model" / "model.sysml"
    model.parent.mkdir()
    model.write_text("package Model;\n", encoding="utf-8")
    ontology = (
        repo / "approach" / "framework" / "ontology"
        / "de4sdv-basic-ontology.yaml"
    )
    ontology.parent.mkdir(parents=True)
    ontology.write_text("classes: {}\n", encoding="utf-8")
    model_revision = _commit(repo, "model")
    code = repo / "tools" / "viewer.py"
    code.parent.mkdir()
    code.write_text("VERSION = 1\n", encoding="utf-8")
    application_revision = _commit(repo, "viewer")
    binding = tmp_path / "binding.json"
    binding.write_text(
        json.dumps({"git_commit": model_revision}), encoding="utf-8"
    )
    return repo, binding, model_revision, application_revision


def test_runtime_contract_accepts_code_only_revision_after_model_binding(tmp_path):
    repo, binding, model_revision, application_revision = _runtime_repo(tmp_path)
    contract = validate_runtime_contract(
        repo,
        binding,
        {
            "NOUS_API_KEY": "test-key",
            "DE4SDV_APP_GIT_SHA": application_revision,
        },
    )
    assert contract.application_revision == application_revision
    assert contract.model_revision == model_revision


def test_runtime_contract_accepts_the_host_owned_read_only_mount(tmp_path,
                                                                monkeypatch):
    repo, binding, model_revision, application_revision = _runtime_repo(tmp_path)
    monkeypatch.setenv("GIT_TEST_ASSUME_DIFFERENT_OWNER", "1")
    contract = validate_runtime_contract(
        repo,
        binding,
        {
            "NOUS_API_KEY": "test-key",
            "DE4SDV_APP_GIT_SHA": application_revision,
        },
    )
    assert contract.model_revision == model_revision


def test_runtime_contract_rejects_model_drift_after_bound_revision(tmp_path):
    repo, binding, _, _ = _runtime_repo(tmp_path)
    model = repo / "textual-notation-of-model" / "model.sysml"
    model.write_text("package ChangedModel;\n", encoding="utf-8")
    changed_revision = _commit(repo, "change model")

    with pytest.raises(RuntimeContractError, match="model or ontology drift"):
        validate_runtime_contract(
            repo,
            binding,
            {
                "NOUS_API_KEY": "test-key",
                "DE4SDV_APP_GIT_SHA": changed_revision,
            },
        )


def test_runtime_contract_rejects_missing_llm_key(tmp_path):
    repo, binding, _, application_revision = _runtime_repo(tmp_path)
    with pytest.raises(RuntimeContractError, match="NOUS_API_KEY"):
        validate_runtime_contract(
            repo,
            binding,
            {"DE4SDV_APP_GIT_SHA": application_revision},
        )


def test_ask_viewer_container_is_pinned_non_root_and_minimal():
    dockerfile = (
        Path("deployment/ask_viewer/Dockerfile").read_text(encoding="utf-8")
    )
    assert (
        "FROM python:3.12.11-slim-bookworm@sha256:"
        "519591d6871b7bc437060736b9f7456b8731f1499a57e22e6c285135ae657bf7"
    ) in dockerfile
    assert "PyYAML==6.0.2" in dockerfile
    assert "USER 10001:10001" in dockerfile
    assert "WORKDIR /srv/de4sdv/DE4SDV" in dockerfile
    assert "ENTRYPOINT" in dockerfile


def test_compose_keeps_ask_viewer_internal_and_mounts_identity_read_only():
    compose = yaml.safe_load(
        Path("deployment/compose.yaml").read_text(encoding="utf-8")
    )
    service = compose["services"]["ask-viewer"]
    assert "ask-viewer" not in compose["services"]["caddy"]["depends_on"]
    assert "ports" not in service
    assert service["expose"] == ["8787"]
    assert service["read_only"] is True
    assert service["cap_drop"] == ["ALL"]
    assert service["security_opt"] == ["no-new-privileges:true"]
    assert service["env_file"] == ["${DE4SDV_ASK_ENV_FILE:-/dev/null}"]
    mounts = service["volumes"]
    assert any("/srv/de4sdv/DE4SDV:ro" in mount for mount in mounts)
    assert any("de4sdv-full-model-binding.json:ro" in mount for mount in mounts)
    assert any("ask_viewer_cache:/var/cache/de4sdv-viewer" in mount
               for mount in mounts)
    environment = service["environment"]
    assert "NOUS_API_KEY" not in environment
    assert "DE4SDV_APP_GIT_SHA" not in environment
    assert environment["NOUS_ASK_SEMANTIC"] == "1"
    assert environment["DE4SDV_SYSML_API_URL"] == "http://sysml2-api:9000"
    assert environment["DE4SDV_ASK_ALLOWED_ORIGIN"] == \
        "https://viewer.de4sdv.org"
    assert environment["NOUS_MAX_CONCURRENT_REQUESTS"] == "1"
    assert environment["NOUS_MAX_TOKENS"] == "1000"
    assert environment["GIT_CONFIG_COUNT"] == "1"
    assert environment["GIT_CONFIG_KEY_0"] == "safe.directory"
    assert environment["GIT_CONFIG_VALUE_0"] == "/srv/de4sdv/DE4SDV"
    assert "ask_viewer_cache" in compose["volumes"]
    assert service["logging"]["driver"] == "json-file"
    assert service["logging"]["options"] == {
        "max-size": "10m", "max-file": "5"
    }
    assert compose["services"]["caddy"]["logging"] == service["logging"]


def test_caddy_applies_global_and_per_ip_ask_quotas_and_method_allowlist():
    caddyfile = Path("deployment/caddy/Caddyfile").read_text(encoding="utf-8")
    assert "viewer.de4sdv.org" in caddyfile
    assert "ask.de4sdv.org" not in caddyfile
    assert "zone ask_global" in caddyfile
    assert "key ask-global" in caddyfile
    assert "events 60" in caddyfile
    assert "window 1h" in caddyfile
    assert "zone ask_daily" in caddyfile
    assert "events 120" in caddyfile
    assert "window 24h" in caddyfile
    assert "zone ask_per_ip" in caddyfile
    assert "key {remote_host}" in caddyfile
    assert "events 3" in caddyfile
    assert "window 1m" in caddyfile
    assert "@ask_post method POST" in caddyfile
    assert "@read method GET HEAD" in caddyfile
    assert "@ask_internal path /_ask_warmup" in caddyfile
    assert "respond @ask_internal 404" in caddyfile
    assert "response_header_timeout 180s" in caddyfile
    assert "reverse_proxy ask-viewer:8787" in caddyfile
    assert "rewrite * /DE4SDV{uri}" in caddyfile
    assert "reverse_proxy https://de4sdv.github.io" in caddyfile
    assert "POST /ask is handled above and never reaches this fallback" in caddyfile
    assert "respond 405" in caddyfile
    assert "output stdout" in caddyfile
    assert "format json" in caddyfile


def test_public_ask_workflow_is_exact_sha_gated_and_does_not_ingest():
    workflow = Path(
        ".github/workflows/deploy-public-ask-viewer.yml"
    ).read_text(encoding="utf-8")
    assert "environment: sysml-api-production" in workflow
    assert "DEPLOY_SHA: ${{ inputs.git_sha }}" in workflow
    assert "git bundle verify" in workflow
    assert "transferred Git bundle checksum mismatch" in workflow
    assert "not on origin/main" in workflow
    assert "NOUS_API_KEY: ${{ secrets.NOUS_API_KEY }}" in workflow
    assert 'DEPLOY_DIR=/srv/de4sdv' in workflow
    assert 'DE4SDV_ASK_ENV_FILE="$DEPLOY_DIR/ask-viewer.env"' in workflow
    assert 'status.get("status") or "unknown"' in workflow
    assert "ready) ready=true" in workflow
    # The remote script is streamed to `bash -s` over SSH. Compose attaches
    # stdin even with exec -T/run -T and would otherwise consume every line
    # after the warmup probe or validation command while returning success.
    assert workflow.count("</dev/null") >= 2
    assert "exec -T ask-viewer python -c '" in workflow
    assert "' </dev/null)" in workflow
    assert "--adapter caddyfile </dev/null" in workflow
    assert "caddy validate" in workflow
    assert "--live-query" in workflow
    assert "if: failure()" in workflow
    assert "Remove runner secret material" in workflow
    assert "if: always()" in workflow
    assert "sysand sync" not in workflow
    assert "privileged-full-model" not in workflow
    assert "https://viewer.de4sdv.org" in workflow
    assert "ask.de4sdv.org" not in workflow


def test_public_ask_material_has_one_reader_hostname():
    paths = [
        "deployment/compose.yaml",
        "deployment/scripts/verify_public_ask.py",
        "deployment/scripts/monitor_public_ask.py",
        "deployment/README.md",
        "docs/architecture-decisions/0016-publish-bounded-public-ask-viewer.md",
        "docs/guides/model-viewer.md",
    ]
    for path in paths:
        text = Path(path).read_text(encoding="utf-8")
        assert "ask.de4sdv.org" not in text, path
        assert "viewer.de4sdv.org" in text, path


def test_pages_workflow_remains_a_native_engineering_mirror():
    workflow = Path(".github/workflows/deploy-viewer.yml").read_text(
        encoding="utf-8"
    )
    assert "native GitHub Pages URL" in workflow
    assert "viewer.de4sdv.org" not in workflow


def test_public_ask_monitor_is_non_paid_and_schedule_safe():
    workflow = Path(
        ".github/workflows/monitor-public-ask-viewer.yml"
    ).read_text(encoding="utf-8")
    script = Path(
        "deployment/scripts/monitor_public_ask.py"
    ).read_text(encoding="utf-8")
    assert "schedule:" in workflow
    assert "workflow_dispatch:" in workflow
    assert "monitor_public_ask.py" in workflow
    assert "NOUS_API_KEY" not in workflow
    assert 'method="POST"' not in script
    assert "/ask-status.json" in script
    assert "semantic warmup is not ready" in script


def test_public_verifier_checks_identity_policy_and_live_grounding():
    app_sha = "a" * 40
    model_sha = "b" * 40
    seen = {"live": False}
    expected_origin = ""

    class Handler(BaseHTTPRequestHandler):
        def _json(self, status, payload):
            body = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/ask-status.json":
                self._json(200, {
                    "application_git_commit": app_sha,
                    "model_git_commit": model_sha,
                    "semantic_warmup": {"status": "ready"},
                })
            elif self.path == "/deployment-status.json":
                self._json(200, {"baseline": {"git_commit": model_sha}})
            elif self.path == "/assets/viewer.js":
                body = b"function renderAskAnswer() {}"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
            else:
                body = b"<script>window.__DE4SDV_VIEWER_SERVER__=true;</script>"
                self.send_response(200)
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        def do_POST(self):
            length = int(self.headers.get("Content-Length") or 0)
            payload = json.loads(self.rfile.read(length))
            if self.headers.get("Origin") != expected_origin:
                self._json(403, {"error": "origin is not allowed"})
            elif payload["element"] == "missing":
                self._json(404, {"error": "not found"})
            else:
                seen["live"] = True
                self._json(200, {
                    "answer": "Grounded answer",
                    "method_context_source": "api:snapshot",
                })

        def do_BREW(self):
            self.send_response(405)
            self.end_headers()

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    expected_origin = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        result = verify_public_ask(
            expected_origin,
            application_sha=app_sha,
            model_sha=model_sha,
            live_query=True,
            tls_attempts=1,
        )
        assert result["application_git_commit"] == app_sha
        assert result["model_git_commit"] == model_sha
        assert result["live_query"] == "passed"
        assert seen["live"] is True
        monitored = monitor_public_ask(
            ask_url=expected_origin,
            model_status_url=f"{expected_origin}/deployment-status.json",
        )
        assert monitored == {
            "status": "healthy",
            "application_git_commit": app_sha,
            "model_git_commit": model_sha,
        }
    finally:
        server.shutdown()
        server.server_close()


def test_public_verifier_retries_tls_readiness_before_giving_up():
    """A just-restarted Caddy may refuse TLS before its first certificate is
    ready; the verifier must retry only that boundary, then fail fast on
    real errors."""
    import ssl

    app_sha = "c" * 40
    model_sha = "d" * 40
    state = {"requests": 0}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["requests"] += 1
            if state["requests"] < 3:
                # terminate the connection like an unready TLS endpoint
                self.connection.setsockopt(
                    __import__("socket").SOL_SOCKET,
                    __import__("socket").SO_LINGER,
                    __import__("struct").pack("ii", 1, 0),
                )
                self.connection.close()
                return
            self.send_response(200)
            self.send_header("Content-Length", "2")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, format, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        with pytest.raises(Exception) as excinfo:
            verify_public_ask(
                base,
                application_sha=app_sha,
                model_sha=model_sha,
                tls_attempts=2,
            )
        assert "TLS endpoint not ready" in str(excinfo.value)
    finally:
        server.shutdown()
        server.server_close()
    assert state["requests"] == 2  # retried, did not fail on attempt 1
