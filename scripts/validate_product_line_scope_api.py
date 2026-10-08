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
from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.product_line_scope import validate_scope_elements
from de4sdv.sysml_api.repository import SysMLRepository, element_id
from de4sdv.sysml_api.revisions import RevisionBinding


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def selected_runtime(
    *,
    api_url: str,
    binding_path: Path,
    git_commit: str,
    authority: str | None = None,
    model_bundle_path: "str | Path | None" = None,
    model_bundle_id: str | None = None,
    allow_candidate_bundle: bool = False,
):
    """The model-authority runtime the scope check binds (fail closed).

    Built through the entry seam, so the scope check binds the same
    authority the production surfaces answer from. ``allow_candidate_bundle``
    serves an unclosed candidate bundle (privileged evidence steps only).
    """
    from de4sdv.semantic import entry_authority

    kwargs = {"require_activation_eligible": False} if allow_candidate_bundle else {}
    return entry_authority.build_entry_semantic_runtime(
        api_url=api_url,
        binding_path=binding_path,
        expected_git_revision=git_commit,
        authority=authority,
        model_bundle_path=model_bundle_path,
        model_bundle_id=model_bundle_id,
        environ={},
        **kwargs,
    )


def validate_api_scope(
    *,
    api_url: str,
    binding_path: Path,
    export_path: Path,
    authority: str | None = None,
    model_bundle_path: "str | Path | None" = None,
    model_bundle_id: str | None = None,
    allow_candidate_bundle: bool = False,
) -> dict[str, Any]:
    git_commit = _git_head()
    binding = RevisionBinding.load(binding_path)
    binding.require_current(git_commit)

    runtime, selection = selected_runtime(
        api_url=api_url, binding_path=binding_path, git_commit=git_commit,
        authority=authority, model_bundle_path=model_bundle_path,
        model_bundle_id=model_bundle_id, allow_candidate_bundle=allow_candidate_bundle,
    )
    binding.require_semantic_authority(runtime.contract.identity)

    bundle = BaselineExportBundle.load(export_path)
    if bundle.git_commit != git_commit:
        raise RuntimeError(
            f"scope export Git revision {bundle.git_commit} does not match {git_commit}"
        )
    bundle.require_current_sources(BaselineManifest.discover(ROOT))

    repository = SysMLRepository(ApiClient(api_url, timeout=600.0))
    elements = repository.list_elements(
        binding.sysml_project_id,
        binding.sysml_commit_id,
    )
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
        "model_authority": selection.provenance(),
        "api_element_count": len(elements),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--semantic-authority",
                        help="model (the only accepted value; default DE4SDV_SEMANTIC_AUTHORITY)")
    parser.add_argument("--model-authority-bundle")
    parser.add_argument("--model-authority-bundle-id")
    parser.add_argument("--allow-candidate-bundle", action="store_true",
                        help="serve an unclosed candidate bundle (privileged evidence steps only)")
    args = parser.parse_args()

    report = validate_api_scope(
        api_url=args.api_url,
        binding_path=args.binding,
        export_path=args.export,
        authority=args.semantic_authority,
        model_bundle_path=args.model_authority_bundle,
        model_bundle_id=args.model_authority_bundle_id,
        allow_candidate_bundle=args.allow_candidate_bundle,
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
