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


def test_deploy_workflow_exports_app_git_sha_in_every_remote_block() -> None:
    """Live evidence 2026-09-09 (run 34392701140): the activation step's
    remote script never exported DE4SDV_APP_GIT_SHA, so compose refused to
    interpolate services.ask-viewer.environment and the deploy rolled back.
    Every heredoc remote block that invokes docker compose must export the
    variable (compose interpolates the whole file for ANY subcommand)."""
    workflow = (
        REPO / ".github/workflows/deploy-public-ask-viewer.yml"
    ).read_text(encoding="utf-8")
    blocks: list[list[str]] = []
    current: list[str] | None = None
    for line in workflow.splitlines():
        if "<<'REMOTE'" in line:
            current = []
            continue
        if current is not None:
            if line.strip() == "REMOTE":
                blocks.append(current)
                current = None
                continue
            current.append(line[10:] if line.startswith("          ") else line)
    compose_blocks = [
        " ".join(b) for b in blocks if "docker compose" in " ".join(b)
    ]
    assert compose_blocks, "no remote docker compose block found"
    for index, block in enumerate(compose_blocks, 1):
        assert "export DE4SDV_APP_GIT_SHA=" in block, (
            f"remote compose block {index} does not export "
            "DE4SDV_APP_GIT_SHA; compose interpolation of the required "
            "variable will fail closed"
        )


def test_deploy_workflow_sets_canonical_origin_on_host_checkout() -> None:
    """Live evidence 2026-09-09 (run 34395255931): the deployed checkout is
    cloned from a local Git bundle, which carries no 'origin' remote, so
    server-side resolution of the GitHub origin (DE4SDV Guide source
    links) returned empty and answers shipped unpinned references. The
    activation step must set the canonical public URL after cloning."""
    workflow = (
        REPO / ".github/workflows/deploy-public-ask-viewer.yml"
    ).read_text(encoding="utf-8")
    assert (
        'git -C "$NEXT_DIR" remote add origin '
        "https://github.com/de4sdv/DE4SDV.git"
    ) in workflow
    # the canonical URL, never a credential-bearing or SSH form
    assert "git@github.com" not in workflow
