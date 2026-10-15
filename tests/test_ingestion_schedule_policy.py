"""Ingestion scheduling policy.

The full-model API ingestion builds a JVM service from source and runs the
complete Syside export + import + semantic validation chain, the batteries
and the release evidence (2.5 to 5 hours per run). It is the expensive backbone
workflow, so it runs only where its result is consumed: on demand via
`workflow_dispatch`, once per release SHA, before a production deployment of
that exact SHA (the deploy workflow verifies the pairing).

It must NOT run per pull request: a modeling PR is covered by fast CI and
Privileged Syside Validation; its content reaches `main` through review, and
the release's dispatch ingests the merged main SHA. Live evidence: 2026-09-02
produced 42 ingestion runs in one day, 27 of them PR-triggered, serializing
into multi-hour wait chains.

It must NOT run on a schedule either: a nightly run would hold the
concurrency group for hours and delay a release dispatch. The schedule
added in #198 (2026-09-03) never ran: the job's `if` from #172 admits only
dispatches, so every scheduled run was skipped.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
INGESTION = (
    ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml"
).read_text(encoding="utf-8")


def test_ingestion_has_no_pull_request_trigger() -> None:
    trigger_block = INGESTION.split("on:", 1)[1].split("permissions:", 1)[0]
    assert "pull_request" not in trigger_block


def test_ingestion_has_no_schedule() -> None:
    trigger_block = INGESTION.split("on:", 1)[1].split("permissions:", 1)[0]
    assert "schedule:" not in trigger_block
    assert "cron:" not in trigger_block


def test_ingestion_is_triggered_only_by_dispatch() -> None:
    workflow = yaml.safe_load(INGESTION)
    triggers = workflow.get("on", workflow.get(True))  # YAML 1.1 reads the key `on` as True
    assert set(triggers) == {"workflow_dispatch"}


def test_ingestion_job_runs_only_on_dispatch() -> None:
    job = yaml.safe_load(INGESTION)["jobs"]["ingest-and-validate"]
    assert job.get("if") == "github.event_name == 'workflow_dispatch'"


def test_ingestion_still_allows_on_demand_dispatch() -> None:
    trigger_block = INGESTION.split("on:", 1)[1].split("permissions:", 1)[0]
    assert "workflow_dispatch" in trigger_block


def test_ingestion_documents_why_it_is_not_per_pr() -> None:
    assert "never per-PR" in INGESTION
    # The documented deploy pairing invariant stays visible.
    assert "deploy workflow refuses any other pairing" in INGESTION
