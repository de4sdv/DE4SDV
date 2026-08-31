#!/usr/bin/env python3
"""Import and semantically validate an official full-model SysML JSON export."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from de4sdv.semantic.kernel_contract import KernelContract
from de4sdv.semantic.validation import validate_ontology_bindings
from de4sdv.sysml_api.baseline import BaselineExportBundle, BaselineManifest
from de4sdv.sysml_api.client import ApiClient
from de4sdv.sysml_api.ingestion import import_baseline
from de4sdv.sysml_api.repository import SysMLRepository
from de4sdv.sysml_api.revisions import RevisionBinding


def _git_head() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_import(
    *,
    api_url: str,
    export_path: Path,
    binding_path: Path,
    report_path: Path,
    project_name: str | None,
    git_repository: str,
) -> dict[str, object]:
    head = _git_head()
    bundle = BaselineExportBundle.load(export_path)
    if bundle.git_commit != head:
        raise RuntimeError(
            f"baseline export is stale: artifact={bundle.git_commit}, checked-out HEAD={head}"
        )
    bundle.require_current_sources(BaselineManifest.discover(ROOT))
    client = ApiClient(api_url, timeout=600.0)
    imported = import_baseline(
        client,
        bundle,
        project_name=project_name or f"DE4SDV full baseline {head[:12]}",
    )
    repository = SysMLRepository(client)
    elements = repository.list_elements(imported.project_id, imported.commit_id)
    contract = KernelContract.load(
        ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml"
    )
    ontology = validate_ontology_bindings(contract, elements, bundle.element_sources)
    report = {
        "schema": "de4sdv-full-model-semantic-validation/v1",
        "git_commit": head,
        "sysml_project_id": imported.project_id,
        "sysml_commit_id": imported.commit_id,
        "source_export_sha256": hashlib.sha256(export_path.read_bytes()).hexdigest(),
        "source_document_count": len(set(bundle.element_sources.values())),
        "element_count": imported.element_count,
        "internal_reference_count": imported.internal_reference_count,
        "external_reference_count": len(bundle.external_references),
        "source_manifest": list(bundle.source_manifest),
        "external_references": list(bundle.external_references),
        "ontology": ontology.to_dict(),
    }
    _write_json(report_path, report)
    if not ontology.passed:
        raise RuntimeError(
            "ontology/API binding validation failed closed: "
            f"{ontology.summary}; report={report_path}"
        )
    binding = RevisionBinding(
        git_repository=git_repository,
        git_commit=head,
        sysml_project_id=imported.project_id,
        sysml_commit_id=imported.commit_id,
        import_timestamp=datetime.now(timezone.utc).isoformat(),
        import_tool_version="de4sdv-full-model-import/1+official-syside-json",
        semantic_validation="passed",
        scope="full-model",
    )
    _write_json(binding_path, binding.to_dict())
    return {
        "binding": binding.to_dict(),
        "semantic_report": str(report_path),
        "ontology_summary": ontology.summary,
        "element_count": imported.element_count,
        "internal_reference_count": imported.internal_reference_count,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--binding", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--project-name")
    parser.add_argument("--git-repository", default="de4sdv/DE4SDV")
    args = parser.parse_args()
    result = run_import(
        api_url=args.api_url,
        export_path=args.export,
        binding_path=args.binding,
        report_path=args.report,
        project_name=args.project_name,
        git_repository=args.git_repository,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
