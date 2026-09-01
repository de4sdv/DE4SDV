#!/usr/bin/env python3
"""Validated deployment of the DE4SDV full-model baseline.

Deployment model (ADR 0013, corrected by human review of PR #176):

    validated privileged Syside export for Git SHA X
        -> exact DE4SDV checkout at Git SHA X
        -> THIS deployment's fresh Systems Modeling API repository
        -> the existing DE4SDV validated import path (scripts/import_sysml_api_baseline.py)
        -> deployment-specific Project/Commit UUIDs (the deployment API
           repository generates its own identities; the privileged CI run's
           ephemeral UUIDs are NOT reused)
        -> deployment-specific RevisionBinding + ontology/API validation
        -> public deployment-status tuple

Fail-closed stages:

1.  Bundle validation: the privileged evidence files must exist, agree on one
    Git SHA, be `passed`/`full-model` with a clean ontology summary, carry the
    semantic authority ontology identity, and the export bytes must hash to
    the digest recorded in the privileged semantic report.
2.  Exact Git checkout: the deployment repository HEAD must equal the bundle
    Git SHA and be clean (no stale files; the workflow creates a detached
    checkout at the exact SHA).
3.  Import: the exact validated export is imported into this deployment's
    API repository through the existing DE4SDV importer (no second parser).
    The importer fails closed on any lost element UUID or internal
    reference; ontology mappings must resolve with 0 unresolved and
    0 ambiguous; only then is a deployment-specific binding written.
4.  Cross-check: the deployment import must preserve the immutable evidence
    the privileged run pinned (element count, internal reference count,
    export digest, ontology identity, source-document count). Project/commit
    UUIDs are intentionally deployment-specific and are NOT compared against
    the privileged run's ephemeral UUIDs.
5.  Status + proxy: only after all of the above succeed is
    deployment-status.json written and the public proxy started.

Availability guarantee (honest wording): this is a single-host compose
stack without a blue/green switch. Bringing up postgres/API before the
import validation completes, and restarting the stack during redeploy,
causes a service interruption on that host. A failed deployment leaves the
stack in a well-defined state (new API containers + validated-or-empty DB,
proxy running only when a previous deployment validated); it does NOT
guarantee the previously served version stays untouched.

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

DEPLOY_DIR = Path(os.environ.get("DEPLOY_DIR", "/srv/de4sdv"))
STATUS_DIR = DEPLOY_DIR / "status"
REQUIRED_FILES = (
    "de4sdv-full-model-export.json",
    "de4sdv-full-model-binding.json",
    "de4sdv-full-model-semantic-validation.json",
    "de4sdv-full-model-semantic-query-coverage.json",
    "de4sdv-semantic-mcp-validation.json",
)
API_IMPLEMENTATION_REVISION = "0af711b14bbcea7b240bb0a3a65817ae68302092"


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
    """Validate the privileged evidence; deployment UUIDs are not required here."""
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

    ontology_report = report.get("ontology") or {}
    require(
        ontology_report.get("passed") is True,
        "semantic validation report did not pass",
    )
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
        and mcp_revision.get("ontology") == ontology,
        "MCP validation Git/ontology identity differs from the binding",
    )

    return {
        "git_commit": binding["git_commit"],
        "ontology": ontology,
        "export_path": export,
        "export_sha256": actual_digest,
        "expected_element_count": report.get("element_count"),
        "expected_internal_reference_count": report.get("internal_reference_count"),
        "expected_source_document_count": report.get("source_document_count"),
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


def compose(*args: str, repo: Path) -> None:
    env = dict(os.environ)
    env["DEPLOY_DIR"] = str(DEPLOY_DIR)
    subprocess.run(
        [
            "docker",
            "compose",
            "-f",
            str(repo / "deployment" / "compose.yaml"),
            "--env-file",
            str(DEPLOY_DIR / "sysml2-api.env"),
            *args,
        ],
        cwd=repo,
        env=env,
        check=True,
    )


def stop_public_proxy(repo: Path) -> None:
    """Stop the public proxy BEFORE any import/mutation touches the stack.

    Redeploy failure mode being prevented: while postgres/API are rebuilt
    and the import runs, a still-running Caddy could serve a partially
    imported project while deployment-status.json still describes the
    previous baseline. The proxy only comes back after the new status file
    is published (see main's ordered sequence).
    """
    compose("stop", "caddy", repo=repo)


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


def wait_for_api(timeout_s: int = 240) -> None:
    """Poll the internal API until it answers /projects."""
    base_url = api_base_url_from_docker()
    deadline = time.monotonic() + timeout_s
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            with urlrequest.urlopen(f"{base_url}/projects", timeout=10) as response:
                if response.status == 200:
                    return
        except (URLError, TimeoutError) as exc:
            last_error = str(exc)
        time.sleep(5)
    raise DeployError(f"API did not become ready: {last_error}")


def import_baseline(repo: Path, evidence: dict[str, Any]) -> dict[str, Any]:
    """Run the existing DE4SDV validated import against this deployment's API.

    Reuses scripts/import_sysml_api_baseline.py (the privileged import path):
    it fails closed on lost element UUIDs / internal references, requires a
    clean ontology binding summary, and writes a deployment-specific
    full-model binding with the deployment repository's own Project/Commit
    UUIDs. A fresh empty API database is the expected first-deployment state.
    """
    api_url = api_base_url_from_docker()
    wait_for_api()
    artifacts = DEPLOY_DIR / "artifacts" / "current"
    binding_path = artifacts / "de4sdv-full-model-binding.json"
    report_path = artifacts / "de4sdv-full-model-semantic-validation.json"
    import_cmd = [
        sys.executable,
        "scripts/import_sysml_api_baseline.py",
        "--api-url",
        api_url,
        "--export",
        str(evidence["export_path"]),
        "--binding",
        str(binding_path),
        "--report",
        str(report_path),
        "--project-name",
        f"DE4SDV public API {evidence['git_commit'][:12]}",
        "--git-repository",
        "de4sdv/DE4SDV",
    ]
    subprocess.run(import_cmd, cwd=repo, check=True)
    binding = load_json(binding_path)
    deployment_report = load_json(report_path)

    require(
        binding.get("git_commit") == evidence["git_commit"],
        "deployment binding Git SHA differs from the bundle Git SHA",
    )
    require(
        binding.get("scope") == "full-model"
        and binding.get("semantic_validation") == "passed",
        "deployment binding is not a passed full-model binding",
    )
    require(
        binding.get("ontology") == evidence["ontology"],
        "deployment binding ontology identity differs from the privileged identity",
    )
    deployment_summary = (deployment_report.get("ontology") or {}).get("summary") or {}
    require(
        deployment_summary.get("unresolved") == 0
        and deployment_summary.get("ambiguous") == 0,
        f"deployment ontology summary is not clean: {deployment_summary}",
    )
    require(
        deployment_report.get("source_export_sha256") == evidence["export_sha256"],
        "deployment import consumed different export bytes than the validated bundle",
    )

    # Immutable evidence from the privileged run must hold for the deployment
    # import too. Project/commit UUIDs are deployment-specific by design and
    # are deliberately NOT compared with the privileged run's ephemeral IDs.
    require(
        evidence["expected_element_count"] is None
        or deployment_report.get("element_count") == evidence["expected_element_count"],
        "deployment element count differs from the privileged report",
    )
    require(
        evidence["expected_internal_reference_count"] is None
        or deployment_report.get("internal_reference_count")
        == evidence["expected_internal_reference_count"],
        "deployment internal reference count differs from the privileged report",
    )
    require(
        evidence["expected_source_document_count"] is None
        or deployment_report.get("source_document_count")
        == evidence["expected_source_document_count"],
        "deployment source document count differs from the privileged report",
    )

    return {
        "sysml_project_id": binding["sysml_project_id"],
        "sysml_commit_id": binding["sysml_commit_id"],
        "element_count": deployment_report.get("element_count"),
        "ontology_summary": deployment_summary,
    }


def write_status(
    evidence: dict[str, Any], deployment: dict[str, Any]
) -> Path:
    STATUS_DIR.mkdir(parents=True, exist_ok=True)
    status = {
        "service": "DE4SDV Experimental Read-Only Systems Modeling API",
        "status": "experimental",
        "read_only": True,
        "api_implementation": {
            "repository": "https://github.com/Systems-Modeling/SysML-v2-API-Services",
            "revision": API_IMPLEMENTATION_REVISION,
        },
        "baseline": {
            "git_commit": evidence["git_commit"],
            # Deployment-specific API identities generated by THIS deployment's
            # repository during the validated import (not the privileged CI
            # run's ephemeral UUIDs).
            "sysml_project_id": deployment["sysml_project_id"],
            "sysml_commit_id": deployment["sysml_commit_id"],
            "ontology": evidence["ontology"],
            "export_sha256": evidence["export_sha256"],
            "element_count": deployment["element_count"],
            "ontology_summary": deployment["ontology_summary"],
        },
        "deployed_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    target = STATUS_DIR / "deployment-status.json"
    tmp = target.with_suffix(".tmp")
    tmp.write_text(json.dumps(status, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(tmp, target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle-dir", type=Path, required=True)
    parser.add_argument("--repo", type=Path, default=DEPLOY_DIR / "DE4SDV")
    args = parser.parse_args()

    try:
        evidence = validate_bundle(args.bundle_dir)
        print(f"bundle valid for Git {evidence['git_commit'][:12]}")

        validate_repo_head(args.repo, evidence["git_commit"])
        print("exact Git checkout verified at the bundle SHA")

        # Fail-closed redeploy sequence: the public proxy is stopped FIRST
        # and only started again after the new deployment-status.json has
        # been published. If any stage below fails, Caddy stays down and no
        # partially validated baseline is publicly reachable.
        stop_public_proxy(args.repo)
        print("public proxy stopped for the import window")

        compose("up", "-d", "--build", "postgres", "sysml2-api", repo=args.repo)
        print("API repository is up; importing the validated export")
        deployment = import_baseline(args.repo, evidence)
        print(
            "deployment import validated: project "
            f"{deployment['sysml_project_id']} commit {deployment['sysml_commit_id']}"
        )

        status_path = write_status(evidence, deployment)
        print(f"deployment-status written to {status_path}")

        compose("up", "-d", "caddy", repo=args.repo)
        print("public proxy is up; deployment complete")
        return 0
    except (DeployError, subprocess.CalledProcessError) as exc:
        print(f"DEPLOYMENT REFUSED: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
