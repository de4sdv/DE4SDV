#!/usr/bin/env python3
"""Fail-fast proof that a restored API database serves the export corpus.

The privileged ``model-authority-evidence`` job restores a ``pg_dump`` of the
ingestion job's API database and serves it with the pinned SysML v2 API
build. Before any evidence step reads that API, this proof establishes that
the restore actually survived API startup:

1. the binding's SysML project and commit exist in the queried API;
2. the element count read through the API (the shared
   ``SysMLRepository.list_elements`` read path) equals the export's element
   count, and the semantic report's ``element_count`` when supplied;
3. the live element id set equals the export element id set.

Regression anchor: run 37677500924 served 0 of 84429 elements because the
pinned build's ``hibernate.hbm2ddl.auto=create-drop`` recreated the schema at
startup and wiped the restored data. The empty-corpus failure names that
cause.

Claim boundary: the queried API instance serves the same element id set as
the export at the binding's project/commit. No semantic, verification or
activation claim. Exit 0 = proved; 2 = refused (report written either way).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

PROOF_SCHEMA = "de4sdv.o4-restored-api-corpus-proof/v1"

SCHEMA_WIPE_HINT = (
    "the restored database did not survive API startup; check that the pinned "
    "build's conf/META-INF/persistence.xml was patched from "
    "hibernate.hbm2ddl.auto=create-drop to update (create-drop recreates the "
    "schema at startup and wipes the pg_restore'd data)"
)


def prove_restored_corpus(
    repository,
    binding,
    export: dict[str, Any],
    semantic_report: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate the restore proof over the supplied transport (pure)."""
    project, commit = str(binding.sysml_project_id), str(binding.sysml_commit_id)
    export_elements = [e for e in (export.get("elements") or []) if isinstance(e, dict)]
    export_count = len(export_elements)
    report_count = (
        int(semantic_report.get("element_count", -1)) if semantic_report is not None else None
    )
    failures: list[str] = []
    live_count: int | None = None

    if report_count is not None and report_count != export_count:
        failures.append(
            f"semantic report element_count {report_count} != export element count "
            f"{export_count}; the inputs disagree before the API is read"
        )
    reachable = True
    try:
        repository.get_project(project)
    except Exception as exc:  # noqa: BLE001 — any read failure is a refusal
        reachable = False
        failures.append(
            f"binding project {project} is not readable from the restored API ({exc}); "
            + SCHEMA_WIPE_HINT
        )
    if reachable:
        try:
            repository.get_commit(project, commit)
        except Exception as exc:  # noqa: BLE001
            reachable = False
            failures.append(
                f"binding commit {commit} of project {project} is not readable from the "
                f"restored API ({exc}); " + SCHEMA_WIPE_HINT
            )
    if reachable:
        try:
            live = repository.list_elements(project, commit)
        except Exception as exc:  # noqa: BLE001
            failures.append(f"element listing of {project}/{commit} failed: {exc}")
        else:
            live_count = len(live)
            if live_count == 0 and export_count:
                failures.append(
                    f"restored API serves 0 of {export_count} export elements; "
                    + SCHEMA_WIPE_HINT
                )
            elif live_count != export_count:
                failures.append(
                    f"restored API serves {live_count} elements; the export has "
                    f"{export_count}"
                )
            live_ids = {str(e.get("@id")) for e in live if isinstance(e, dict)}
            export_ids = {str(e.get("@id")) for e in export_elements}
            if live_count and live_ids != export_ids:
                failures.append(
                    "restored element id set differs from the export element id set: "
                    f"missing={len(export_ids - live_ids)} "
                    f"unexpected={len(live_ids - export_ids)}"
                )

    return {
        "schema": PROOF_SCHEMA,
        "git_revision": str(export.get("git_commit")),
        "binding_git_commit": str(binding.git_commit),
        "sysml_project_id": project,
        "sysml_commit_id": commit,
        "export_element_count": export_count,
        "semantic_report_element_count": report_count,
        "live_element_count": live_count,
        "failures": failures,
        "passed": not failures,
        "claim_boundary": (
            "the queried API instance serves the export's element id set at the "
            "binding's SysML project/commit; no semantic, verification or "
            "activation claim"
        ),
    }


def _load_binding(path: Path):
    from de4sdv.sysml_api.revisions import RevisionBinding

    return RevisionBinding.load(path)


def _repository(api_url: str):
    from de4sdv.sysml_api.client import ApiClient
    from de4sdv.sysml_api.repository import SysMLRepository

    return SysMLRepository(ApiClient(api_url, timeout=1800.0))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--binding", required=True, type=Path)
    parser.add_argument("--export", required=True, type=Path)
    parser.add_argument("--semantic-report", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args(argv)
    binding = _load_binding(args.binding)
    export_bytes = args.export.read_bytes()
    export = json.loads(export_bytes)
    semantic_report = (
        json.loads(args.semantic_report.read_text(encoding="utf-8"))
        if args.semantic_report else None
    )
    report = prove_restored_corpus(_repository(args.api_url), binding, export, semantic_report)
    report["export_sha256"] = "sha256:" + hashlib.sha256(export_bytes).hexdigest()
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if report["passed"]:
        print(
            f"restored API corpus proved: {report['live_element_count']} elements at "
            f"{report['sysml_project_id']}/{report['sysml_commit_id']}"
        )
        return 0
    for failure in report["failures"]:
        print(f"::error::restored API corpus proof refused: {failure}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
