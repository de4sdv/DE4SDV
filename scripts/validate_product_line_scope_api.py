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

from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.sysml_api.baseline import BaselineExportBundle, BaselineManifest
from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.product_line_scope import validate_scope_elements
from de4sdv.sysml_api.repository import SysMLRepository, element_id
from de4sdv.sysml_api.revisions import RevisionBinding


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def selected_contract_identity(
    *,
    api_url: str,
    binding_path: Path,
    git_commit: str,
    authority: str | None = None,
    bundle_path: "str | Path | None" = None,
    bundle_id: str | None = None,
    model_bundle_path: "str | Path | None" = None,
    model_bundle_id: str | None = None,
):
    """Ontology compatibility identity of the SELECTED semantic authority.

    The default (legacy) keeps the authored contract load unchanged. An
    explicit ``o3`` or ``model`` selection builds that runtime through the
    entry seam (fail closed, no fallback) and takes the contract identity the
    runtime actually serves, so the scope check binds the same authority the
    production surfaces would answer from.
    """
    value = str(authority or "legacy").strip().lower()
    if value == "legacy":
        return KernelContract.load(
            ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
        ).identity
    from de4sdv.semantic import entry_authority

    runtime, _ = entry_authority.build_entry_semantic_runtime(
        api_url=api_url,
        binding_path=binding_path,
        expected_git_revision=git_commit,
        ontology_path=ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml",
        authority=value,
        bundle_path=bundle_path,
        bundle_id=bundle_id,
        model_bundle_path=model_bundle_path,
        model_bundle_id=model_bundle_id,
        environ={},
    )
    return runtime.contract.identity


def validate_api_scope(
    *,
    api_url: str,
    binding_path: Path,
    export_path: Path,
    authority: str | None = None,
    bundle_path: "str | Path | None" = None,
    bundle_id: str | None = None,
    model_bundle_path: "str | Path | None" = None,
    model_bundle_id: str | None = None,
) -> dict[str, Any]:
    git_commit = _git_head()
    binding = RevisionBinding.load(binding_path)
    binding.require_current(git_commit)

    binding.require_ontology(selected_contract_identity(
        api_url=api_url, binding_path=binding_path, git_commit=git_commit,
        authority=authority, bundle_path=bundle_path, bundle_id=bundle_id,
        model_bundle_path=model_bundle_path, model_bundle_id=model_bundle_id,
    ))

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
            "ontology": binding.ontology.to_dict(),
        },
        "api_element_count": len(elements),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--semantic-authority", default="legacy",
                        help="legacy (default), o3 or model")
    parser.add_argument("--o3-authority-bundle")
    parser.add_argument("--o3-authority-bundle-id")
    parser.add_argument("--model-authority-bundle")
    parser.add_argument("--model-authority-bundle-id")
    args = parser.parse_args()

    report = validate_api_scope(
        api_url=args.api_url,
        binding_path=args.binding,
        export_path=args.export,
        authority=args.semantic_authority,
        bundle_path=args.o3_authority_bundle,
        bundle_id=args.o3_authority_bundle_id,
        model_bundle_path=args.model_authority_bundle,
        model_bundle_id=args.model_authority_bundle_id,
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
