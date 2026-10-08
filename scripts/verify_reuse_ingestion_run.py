#!/usr/bin/env python3
"""Verify that an earlier ingestion run may feed a model-authority re-run.

Reuse mode of ``.github/workflows/privileged-full-model-api-ingestion.yml``
(``reuse_ingestion_run`` input) skips ``ingest-and-validate`` and runs
``model-authority-evidence`` on the artifacts of an earlier run. Before
anything is downloaded, every precondition is read through the GitHub REST
API and the run is refused unless all hold:

1. the input ``ref`` is an exact lowercase 40-character SHA and the run id is
   numeric and not the current run;
2. the source run belongs to this repository and to this same workflow file,
   was triggered by ``workflow_dispatch``, is completed, and its ``head_sha``
   equals ``ref`` (the source run's artifact names are bound to that SHA);
3. the source run's ``ingest-and-validate`` job concluded ``success``;
4. ``full-model-api-ingestion-<ref>`` and ``model-authority-api-db-<ref>``
   each exist exactly once, are not expired, and originate from ``ref``.

The content binding (export/binding/O3 bundle name the checked-out SHA, the
database dump matches its sha256) is re-checked by the workflow's existing
"Verify inputs are bound to the checked-out revision" step after download.

On success the provenance record (source run, job, artifact ids/digests) is
written next to the model-authority outputs and the two artifact ids are
emitted as step outputs, so the download binds to the verified objects.
Stdlib only: it runs before Python is set up. Exit 0 = eligible; 1 = refused.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

WORKFLOW_FILE = "privileged-full-model-api-ingestion.yml"
INGEST_JOB = "ingest-and-validate"
INGESTION_PREFIX = "full-model-api-ingestion-"
SNAPSHOT_PREFIX = "model-authority-api-db-"
SOURCE_SCHEMA = "de4sdv.o4-model-authority-ingestion-source/v1"
_SHA = re.compile(r"[0-9a-f]{40}")


class ReuseRefused(Exception):
    """A reuse precondition does not hold."""


def _artifact(records: dict[str, Any], name: str, ref: str) -> dict[str, Any]:
    matches = [a for a in records.get("artifacts", []) if a.get("name") == name]
    if len(matches) != 1:
        raise ReuseRefused(f"artifact {name} must exist exactly once in the source run "
                           f"(found {len(matches)})")
    artifact = matches[0]
    if artifact.get("expired") is not False:
        raise ReuseRefused(f"artifact {name} is expired (expired={artifact.get('expired')!r}); "
                           "re-dispatch the full ingestion instead")
    origin = (artifact.get("workflow_run") or {}).get("head_sha")
    if origin != ref:
        raise ReuseRefused(f"artifact {name} origin head_sha {origin!r} != ref {ref}")
    return {key: artifact.get(key)
            for key in ("id", "name", "size_in_bytes", "digest", "created_at", "expires_at")}


def verify_reuse_run(api: Callable[[str], Any], *, repository: str, run_id: str, ref: str,
                     current_run_id: str | None) -> dict[str, Any]:
    """Return the provenance record, or raise :class:`ReuseRefused`."""
    if not _SHA.fullmatch(ref or ""):
        raise ReuseRefused(f"reuse mode requires the ref input to be an exact lowercase "
                           f"40-character SHA (got {ref!r})")
    if not (run_id or "").isdecimal():
        raise ReuseRefused(f"reuse_ingestion_run must be a numeric run id (got {run_id!r})")
    if current_run_id is not None and str(current_run_id) == run_id:
        raise ReuseRefused("reuse_ingestion_run names the current run")

    workflow = api(f"/actions/workflows/{WORKFLOW_FILE}")
    run = api(f"/actions/runs/{run_id}")
    if (run.get("repository") or {}).get("full_name") != repository:
        raise ReuseRefused(f"source run {run_id} is not in repository {repository}")
    if run.get("workflow_id") != workflow.get("id"):
        raise ReuseRefused(f"source run {run_id} is not a run of workflow {WORKFLOW_FILE}")
    if run.get("event") != "workflow_dispatch":
        raise ReuseRefused(f"source run {run_id} event is {run.get('event')!r}, "
                           "not workflow_dispatch")
    if run.get("status") != "completed":
        raise ReuseRefused(f"source run {run_id} status is {run.get('status')!r}, not completed")
    if run.get("head_sha") != ref:
        raise ReuseRefused(f"source run {run_id} head_sha {run.get('head_sha')!r} != ref {ref}; "
                           "its artifacts are not bound to this ref")

    jobs = api(f"/actions/runs/{run_id}/jobs?per_page=100")
    ingest = [j for j in jobs.get("jobs", []) if j.get("name") == INGEST_JOB]
    if len(ingest) != 1 or ingest[0].get("conclusion") != "success":
        state = [j.get("conclusion") for j in ingest]
        raise ReuseRefused(f"source run {run_id} job {INGEST_JOB} did not conclude success "
                           f"(found {state})")

    records = api(f"/actions/runs/{run_id}/artifacts?per_page=100")
    if records.get("total_count") != len(records.get("artifacts", [])):
        raise ReuseRefused(f"source run {run_id} artifact inventory is incomplete")
    ingestion = _artifact(records, INGESTION_PREFIX + ref, ref)
    snapshot = _artifact(records, SNAPSHOT_PREFIX + ref, ref)

    job = ingest[0]
    return {
        "schema": SOURCE_SCHEMA,
        "mode": "reuse",
        "ref": ref,
        "source_run_id": run.get("id"),
        "source_run_attempt": run.get("run_attempt"),
        "source_run_url": run.get("html_url"),
        "source_workflow_id": run.get("workflow_id"),
        "source_ingest_job": {key: job.get(key)
                              for key in ("id", "name", "conclusion", "completed_at")},
        "ingestion_artifact": ingestion,
        "snapshot_artifact": snapshot,
        "reusing_run_id": None if current_run_id is None else str(current_run_id),
        "claim_boundary": (
            "names the earlier ingestion run whose artifacts this model-authority "
            "evidence consumed; content is re-bound to the checked-out revision by "
            "the workflow's input-binding step"
        ),
    }


def _gh_api(repository: str) -> Callable[[str], Any]:
    def api(path: str) -> Any:
        return json.loads(subprocess.check_output(["gh", "api", f"repos/{repository}{path}"]))

    return api


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument("--repository", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--ref", required=True)
    parser.add_argument("--current-run-id")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--github-output", type=Path,
                        default=Path(os.environ["GITHUB_OUTPUT"])
                        if os.environ.get("GITHUB_OUTPUT") else None)
    args = parser.parse_args(argv)
    try:
        record = verify_reuse_run(_gh_api(args.repository), repository=args.repository,
                                  run_id=args.run_id, ref=args.ref,
                                  current_run_id=args.current_run_id)
    except ReuseRefused as exc:
        print(f"::error::reuse_ingestion_run={args.run_id} refused: {exc}")
        return 1
    record["verified_at"] = datetime.now(timezone.utc).isoformat()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if args.github_output is not None:
        with args.github_output.open("a", encoding="utf-8") as handle:
            handle.write(f"ingestion_artifact_id={record['ingestion_artifact']['id']}\n")
            handle.write(f"snapshot_artifact_id={record['snapshot_artifact']['id']}\n")
    print(f"reuse source verified: run {record['source_run_id']} at {args.ref}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
