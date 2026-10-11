#!/usr/bin/env python3
"""Validate the governed AEBS product-line scope on an exact API revision."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.sysml_api.baseline import BaselineExportBundle, BaselineManifest
from de4sdv.sysml_api.product_line_scope import validate_scope_elements
from de4sdv.sysml_api.repository import element_id
from de4sdv.sysml_api.revisions import RevisionBinding


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def selected_runtime(*, api_url: str, binding_path: Path, git_commit: str):
    """The deployed runtime the scope check binds (fail closed).

    The production construction: the startup check (exact commit, clean
    tree, ``sai-`` identity, served-model record), then the deployed
    services, whose corpus is refused unless it is the validated export.
    """
    from de4sdv.semantic.deployment_runtime import build_deployment_runtime

    return build_deployment_runtime(
        ROOT, api_url=api_url, binding_path=binding_path, expected_git_revision=git_commit,
    )


def validate_api_scope(
    *,
    api_url: str,
    binding_path: Path,
    export_path: Path,
) -> dict[str, Any]:
    git_commit = _git_head()
    binding = RevisionBinding.load(binding_path)
    binding.require_current(git_commit)

    runtime = selected_runtime(api_url=api_url, binding_path=binding_path,
                               git_commit=git_commit)

    bundle = BaselineExportBundle.load(export_path)
    if bundle.git_commit != git_commit:
        raise RuntimeError(
            f"scope export Git revision {bundle.git_commit} does not match {git_commit}"
        )
    bundle.require_current_sources(BaselineManifest.discover(ROOT))

    # The runtime's corpus: listed once from the API and accepted only when
    # its content is the validated export the binding records.
    elements = runtime._elements()
    api_ids = {identifier for item in elements if (identifier := element_id(item))}
    export_ids = set(bundle.elements)
    if api_ids != export_ids:
        raise RuntimeError(
            "scope API/export identity mismatch: "
            f"missing={sorted(export_ids - api_ids)}, "
            f"unexpected={sorted(api_ids - export_ids)}"
        )

    scope = validate_scope_elements(elements, bundle.element_sources)
    return {
        **scope,
        "revision": {
            "scope": binding.scope,
            "git_commit": binding.git_commit,
            "sysml_project_id": binding.sysml_project_id,
            "sysml_commit_id": binding.sysml_commit_id,
            "semantic_authority": binding.semantic_authority.to_dict(),
        },
        "model_authority": runtime.authority_status(),
        "api_element_count": len(elements),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    report = validate_api_scope(
        api_url=args.api_url,
        binding_path=args.binding,
        export_path=args.export,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "binding_stage": report["binding_stage"],
                "planned_reference_member_count": len(
                    report["planned_reference_members"]
                ),
                "revision": report["revision"],
                "output": str(args.output),
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
