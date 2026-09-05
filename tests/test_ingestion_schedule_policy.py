"""Ingestion scheduling policy.

The full-model API ingestion builds a JVM service from source and runs the
complete Syside export + import + semantic validation chain. It is the
expensive backbone workflow, so it must run where its results are consumed:

- nightly on `main` (scheduled): keeps a fresh deployable artifact and a
  daily semantic health signal;
- on demand via `workflow_dispatch` before a production deployment for the
  exact SHA being deployed (the deploy workflow verifies the pairing).

It must NOT run per pull request: a modeling PR is covered by fast CI and
Privileged Syside Validation; its content reaches `main` through review, and
the nightly (or pre-deploy dispatch) ingestion re-verifies the merged main
SHA. Live evidence: 2026-09-02 produced 13 ingestion runs in one day, mostly
PR-triggered, serializing into multi-hour wait chains.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INGESTION = (
    ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml"
).read_text(encoding="utf-8")


def test_ingestion_has_no_pull_request_trigger() -> None:
    trigger_block = INGESTION.split("on:", 1)[1].split("permissions:", 1)[0]
    assert "pull_request" not in trigger_block


def test_ingestion_runs_nightly_on_a_schedule() -> None:
    trigger_block = INGESTION.split("on:", 1)[1].split("permissions:", 1)[0]
    assert "schedule:" in trigger_block
    assert "cron:" in trigger_block
    # Exactly one nightly schedule entry.
    assert trigger_block.count("cron:") == 1


def test_ingestion_still_allows_on_demand_dispatch() -> None:
    trigger_block = INGESTION.split("on:", 1)[1].split("permissions:", 1)[0]
    assert "workflow_dispatch" in trigger_block


def test_ingestion_documents_why_it_is_not_per_pr() -> None:
    assert "never per-PR" in INGESTION
    # The documented deploy pairing invariant stays visible.
    assert "deploy workflow refuses any other pairing" in INGESTION
