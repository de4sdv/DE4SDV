"""Regression tests: the deployment must recreate the ask-viewer for the
deployed revision and fail closed when the application SHA is missing.

Motivation (2026-09-08 incident): deploy.py never recreated the ask-viewer
container, so after a model-changing deploy the container kept serving a
startup-cached site and grounding index from the PREVIOUS revision — every
ask was refused and warmup crashed the worker mid-request. The compose file
now requires DE4SDV_APP_GIT_SHA and deploy.py recreates + health-checks the
service before the public proxy returns.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
COMPOSE = REPO / "deployment" / "compose.yaml"
DEPLOY_PY = REPO / "deployment" / "scripts" / "deploy.py"


def test_compose_requires_app_git_sha_for_ask_viewer() -> None:
    source = COMPOSE.read_text(encoding="utf-8")
    assert "DE4SDV_APP_GIT_SHA" in source
    # The required-variable form (":?...") fails composition when the SHA
    # is absent, instead of silently starting with an empty identity.
    assert "${DE4SDV_APP_GIT_SHA:?" in source


def test_deploy_py_recreates_and_health_checks_ask_viewer() -> None:
    source = DEPLOY_PY.read_text(encoding="utf-8")
    tree = ast.parse(source)
    functions = {
        node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    }
    assert "recreate_ask_viewer" in functions
    assert "wait_for_ask_viewer" in functions
    # The recreate must pass the deployed SHA and the credentials env file,
    # and the ordered sequence must run it before caddy comes back.
    assert 'env["DE4SDV_APP_GIT_SHA"] = git_commit' in source
    assert "DE4SDV_ASK_ENV_FILE" in source
    recreate_at = source.index("recreate_ask_viewer(args.repo")
    caddy_at = source.index('compose("up", "-d", "caddy"')
    assert recreate_at < caddy_at, "ask-viewer must be recreated before the proxy returns"
    assert "wait_for_ask_viewer()" in source
