"""Fail-closed entry point for the public Ask-model viewer."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping


_FULL_SHA = re.compile(r"^[0-9a-f]{40}$")
_GOVERNED_MODEL_PATHS = (
    "textual-notation-of-model",
    "model-based-product-line-engineering/product-models",
    "approach/framework/ontology/de4sdv-basic-ontology.yaml",
)


class RuntimeContractError(RuntimeError):
    """The deployed application cannot safely serve the bound model."""


@dataclass(frozen=True)
class RuntimeContract:
    application_revision: str
    model_revision: str


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-c", f"safe.directory={repo}", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        timeout=30,
    )


def validate_runtime_contract(
    repo: Path,
    binding_path: Path,
    environ: Mapping[str, str],
) -> RuntimeContract:
    """Validate application identity and model compatibility before startup."""
    if not environ.get("NOUS_API_KEY", "").strip():
        raise RuntimeContractError("NOUS_API_KEY is required")

    application_revision = environ.get("DE4SDV_APP_GIT_SHA", "").strip()
    if not _FULL_SHA.fullmatch(application_revision):
        raise RuntimeContractError("DE4SDV_APP_GIT_SHA must be a full Git SHA")

    try:
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeContractError("revision binding is unreadable") from exc
    if not isinstance(binding, dict):
        raise RuntimeContractError("revision binding must be a JSON object")
    model_revision = str(binding.get("git_commit") or "").strip()
    if not _FULL_SHA.fullmatch(model_revision):
        raise RuntimeContractError("revision binding has no full git_commit")

    head = _git(repo, "rev-parse", "HEAD")
    if head.returncode != 0 or head.stdout.strip() != application_revision:
        raise RuntimeContractError(
            "checkout HEAD does not match DE4SDV_APP_GIT_SHA"
        )

    ancestry = _git(
        repo, "merge-base", "--is-ancestor",
        model_revision, application_revision,
    )
    if ancestry.returncode != 0:
        raise RuntimeContractError(
            "bound model revision is not an ancestor of the application"
        )

    drift = _git(
        repo, "diff", "--quiet", model_revision, application_revision,
        "--", *_GOVERNED_MODEL_PATHS,
    )
    if drift.returncode != 0:
        raise RuntimeContractError(
            "model or ontology drift exists after the bound revision"
        )

    return RuntimeContract(application_revision, model_revision)


def main() -> int:
    repo = Path(os.environ.get("DE4SDV_REPO_ROOT", "/srv/de4sdv/DE4SDV"))
    binding_path = Path(os.environ.get(
        "DE4SDV_REVISION_BINDING",
        "/run/de4sdv/de4sdv-full-model-binding.json",
    ))
    try:
        contract = validate_runtime_contract(repo, binding_path, os.environ)
    except RuntimeContractError as exc:
        print(f"Ask-model startup refused: {exc}", file=sys.stderr)
        return 2

    os.environ["DE4SDV_EXPECTED_GIT_SHA"] = contract.model_revision
    os.execv(
        sys.executable,
        [
            sys.executable,
            "-m", "tools.sysml_html_viewer.serve",
            "--repo", str(repo),
            "--out", "/var/cache/de4sdv-viewer/site",
            "--host", "0.0.0.0",
            "--port", "8787",
            "--no-prs",
            "--production",
        ],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
