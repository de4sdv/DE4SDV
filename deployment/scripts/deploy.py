#!/usr/bin/env python3
"""Validate a privileged full-model artifact bundle and deploy it.

Fail-closed at every stage (ADR 0013):

1.  The bundle must contain the four privileged evidence files plus the
    exact export, all for one Git SHA.
2.  The deployment host's Git revision must equal the bundle Git SHA.
3.  The semantic validation report must be passed with zero unresolved and
    zero ambiguous ontology classes.
4.  The binding must be synchronized full-model scope with the ontology
    path/SHA-256 identity (PR #174 semantic authority tuple).
5.  The export digest must match the digest recorded in the semantic report.
6.  The database must contain an API project/commit pair equal to the
    binding tuple before the proxy is pointed at it.

On success it writes /srv/de4sdv/status/deployment-status.json and
restarts the stack. On any mismatch it exits nonzero WITHOUT touching the
running service.

Usage (on the deployment host, as root):
  python3 deploy.py --bundle-dir /srv/de4sdv/artifacts/incoming \
                    --repo /srv/de4sdv/DE4SDV
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any
from urllib import request as urlrequest
from urllib.error import URLError

STATUS_DIR = Path("/srv/de4sdv/status")
COMPOSE_DIR_RELPATH = "deployment"
REQUIRED_FILES = (
    "de4sdv-full-model-export.json",
    "de4sdv-full-model-binding.json",
    "de4sdv-full-model-semantic-validation.json",
    "de4sdv-full-model-semantic-query-coverage.json",
    "de4sdv-semantic-mcp-validation.json",
)


class DeployError(RuntimeError):
    """Fail-closed deployment guard."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise DeployError(message)


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(value, dict), f"{path.name} is not a JSON object")
    return value


def git_head(repo: Path) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repo, text=True
    ).strip()


def validate_bundle(bundle_dir: Path) -> dict[str, Any]:
    for name in REQUIRED_FILES:
        path = bundle_dir / name
        require(path.is_file(), f"bundle missing {name}")

    export = bundle_dir / "de4sdv-full-model-export.json"
    binding = load_json(bundle_dir / "de4sdv-full-model-binding.json")
    report = load_json(bundle_dir / "de4sdv-full-model-semantic-validation.json")
    mcp = load_json(bundle_dir / "de4sdv-semantic-mcp-validation.json")

    require(
        binding.get("semantic_validation") == "passed",
        "binding semantic_validation is not passed",
    )
    require(binding.get("scope") == "full-model", "binding scope is not full-model")

    ontology = binding.get("ontology")
    require(isinstance(ontology, dict), "binding carries no ontology identity")
    require(
        set(ontology) == {"path", "sha256"},
        "ontology identity must be exactly path+sha256",
    )
    require(
        isinstance(ontology.get("sha256"), str)
        and len(ontology["sha256"]) == 64
        and all(c in "0123456789abcdef" for c in ontology["sha256"]),
        "ontology sha256 is not a lowercase SHA-256 digest",
    )

    require(
        report.get("ontology", {}).get("passed") is True,
        "semantic validation report did not pass",
    )
    ontology_report = report.get("ontology") or {}
    summary = ontology_report.get("summary") or {}
    require(
        summary.get("unresolved") == 0 and summary.get("ambiguous") == 0,
        f"ontology summary is not clean: {summary}",
    )
    require(
        report.get("ontology_identity") == ontology,
        "report ontology identity differs from binding ontology identity",
    )
    require(
        report.get("git_commit") == binding.get("git_commit"),
        "report Git SHA differs from binding Git SHA",
    )

    recorded_digest = report.get("source_export_sha256")
    actual_digest = sha256_file(export)
    require(
        recorded_digest == actual_digest,
        f"export digest mismatch: report={recorded_digest} actual={actual_digest}",
    )

    require(
        mcp.get("read_only") is True and mcp.get("tool_count") == 7,
        "MCP validation artifact does not describe a clean seven-tool read-only run",
    )
    mcp_revision = mcp.get("revision", {})
    require(
        mcp_revision.get("git_commit") == binding["git_commit"]
        and mcp_revision.get("sysml_project_id") == binding["sysml_project_id"]
        and mcp_revision.get("sysml_commit_id") == binding["sysml_commit_id"]
        and mcp_revision.get("ontology") == ontology,
        "MCP validation revision tuple differs from the binding tuple",
    )

    return {
        "git_commit": binding["git_commit"],
        "sysml_project_id": binding["sysml_project_id"],
        "sysml_commit_id": binding["sysml_commit_id"],
        "ontology": ontology,
        "export_sha256": actual_digest,
        "element_count": report.get("element_count"),
        "ontology_summary": summary,
    }


def validate_repo_head(repo: Path, git_commit: str) -> None:
    require(repo.is_dir() and (repo / ".git").is_dir(), "deployment repo missing")
    head = git_head(repo)
    require(head == git_commit, f"repo HEAD {head} != bundle Git SHA {git_commit}")
    dirty = subprocess.run(
        ["git", "status", "--porcelain"], cwd=repo, text=True, capture_output=True
    ).stdout.strip()
    require(not dirty, f"deployment repo is dirty:\n{dirty}")


def api_base_url_from_docker() -> str:
    """Resolve the API container's internal IP from the host.

    deploy.py runs on the deployment host, where the compose service name
    `sysml2-api` is not resolvable; only containers share that DNS. The
    compose network's bridge IPs are reachable from the host but not from
    the Internet (no published ports), so probing the container IP directly
    preserves the exposure boundary. Fails closed if the container is not
    running or has no address.
    """
    try:
        output = subprocess.check_output(
            [
                "docker",
                "inspect",
                "-f",
                "{{range .NetworkSettings.Networks}}{{.IPAddress}} {{end}}",
                "sysml2-api",
            ],
            text=True,
        ).split()
    except subprocess.CalledProcessError:
        output = []
    require(bool(output), "sysml2-api container not found or has no network address")
    return f"http://{output[0]}:9000"


def wait_for_api(timeout_s: int = 240) -> dict[str, Any]:
    """Poll the internal API until it answers /projects."""
    base_url = api_base_url_from_docker()
    deadline = time.monotonic() + timeout_s
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            with urlrequest.urlopen(f"{base_url}/projects", timeout=10) as response:
                if response.status == 200:
                    projects = json.loads(response.read().decode("utf-8"))
                    return {"projects": projects}
        except (URLError, TimeoutError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        time.sleep(5)
    raise DeployError(f"API did not become ready: {last_error}")


def validate_imported_model(tuple_: dict[str, Any]) -> None:
    """Prove the DB actually serves the bound project/commit before exposing it."""
    base_url = api_base_url_from_docker()
    payload = wait_for_api()
    projects = payload["projects"]
    require(isinstance(projects, list), "/projects did not return a list")
    matching = [
        project
        for project in projects
        if isinstance(project, dict)
        and project.get("@id") == tuple_["sysml_project_id"]
    ]
    require(len(matching) == 1, "bound project not found in the API")

    commit_url = (
        f"{base_url}/projects/"
        f"{tuple_['sysml_project_id']}/commits/{tuple_['sysml_commit_id']}"
    )
    with urlrequest.urlopen(commit_url, timeout=10) as response:
        commit = json.loads(response.read().decode("utf-8"))
    require(
        commit.get("@id") == tuple_["sysml_commit_id"],
        "bound commit not found in the API",
    )


def write_status(tuple_: dict[str, Any]) -> Path:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    status = {
        "service": "DE4SDV Experimental Read-Only Systems Modeling API",
        "status": "experimental",
        "read_only": True,
        "api_implementation": {
            "repository": "https://github.com/Systems-Modeling/SysML-v2-API-Services",
            "revision": "0af711b14bbcea7b240bb0a3a65817ae68302092",
        },
        "baseline": {
            "git_commit": tuple_["git_commit"],
            "sysml_project_id": tuple_["sysml_project_id"],
            "sysml_commit_id": tuple_["sysml_commit_id"],
            "ontology": tuple_["ontology"],
            "export_sha256": tuple_["export_sha256"],
            "element_count": tuple_["element_count"],
            "ontology_summary": tuple_["ontology_summary"],
        },
        "deployed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    target = STATUS_DIR / "deployment-status.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return target


def compose(*args: str, cwd: Path) -> None:
    env = dict(os.environ)
    env["DEPLOY_DIR"] = "/srv/de4sdv"
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(cwd / "deployment" / "compose.yaml"),
            "--env-file",
            "/srv/de4sdv/sysml2-api.env",
            *args,
        ],
        cwd=cwd,
        env=env,
        check=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=Path("/srv/de4sdv/DE4SDV"))
    args = parser.parse_args()

    try:
        tuple_ = validate_bundle(args.bundle_dir)
        print(f"bundle valid for Git {tuple_['git_commit'][:12]}")

        validate_repo_head(args.repo, tuple_["git_commit"])
        print("deployment repo HEAD matches bundle")

        compose("up", "-d", "--build", "postgres", "sysml2-api", cwd=args.repo)
        print("stack is up; validating imported model before exposing the proxy")
        validate_imported_model(tuple_)
        print("bound project/commit verified inside the API")

        compose("up", "-d", "caddy", cwd=args.repo)
        status_path = write_status(tuple_)
        print(f"deployment-status written to {status_path}")
        print("deployment complete")
        return 0
    except (DeployError, subprocess.CalledProcessError) as exc:
        print(f"DEPLOYMENT REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
