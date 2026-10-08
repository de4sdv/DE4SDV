"""Reuse-mode preconditions for the model-authority-evidence job.

A transport spy stands in for the GitHub REST API; no network is opened and
nothing is dispatched. Each precondition is planted as a violation and must
be refused with a ``::error::`` naming it.
"""
from __future__ import annotations

import copy
import json

import pytest

from scripts import verify_reuse_ingestion_run as reuse

REPO = "de4sdv/DE4SDV"
REF = "f" * 40
RUN = "37677500924"
WORKFLOW_ID = 4242


def fixture():
    return {
        "/actions/workflows/privileged-full-model-api-ingestion.yml": {"id": WORKFLOW_ID},
        f"/actions/runs/{RUN}": {
            "id": int(RUN), "workflow_id": WORKFLOW_ID, "event": "workflow_dispatch",
            "head_sha": REF, "status": "completed", "conclusion": "success",
            "run_attempt": 1, "html_url": f"https://github.com/{REPO}/actions/runs/{RUN}",
            "repository": {"full_name": REPO},
        },
        f"/actions/runs/{RUN}/jobs?per_page=100": {
            "total_count": 2,
            "jobs": [
                {"id": 1, "name": "ingest-and-validate", "status": "completed",
                 "conclusion": "success", "completed_at": "2026-10-08T00:12:00Z"},
                {"id": 2, "name": "model-authority-evidence", "status": "completed",
                 "conclusion": "failure"},
            ],
        },
        f"/actions/runs/{RUN}/artifacts?per_page=100": {
            "total_count": 3,
            "artifacts": [
                {"id": 11, "name": f"full-model-api-ingestion-{REF}", "expired": False,
                 "size_in_bytes": 10, "expires_at": "2026-10-21T00:00:00Z",
                 "digest": "sha256:aa", "workflow_run": {"id": int(RUN), "head_sha": REF}},
                {"id": 12, "name": f"model-authority-api-db-{REF}", "expired": False,
                 "size_in_bytes": 20, "expires_at": "2026-10-10T00:00:00Z",
                 "digest": "sha256:bb", "workflow_run": {"id": int(RUN), "head_sha": REF}},
                {"id": 13, "name": f"model-authority-evidence-{REF}", "expired": False,
                 "workflow_run": {"id": int(RUN), "head_sha": REF}},
            ],
        },
    }


class Spy:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def __call__(self, path):
        self.calls.append(path)
        if path not in self.responses:
            raise AssertionError(f"unexpected API read {path}")
        return copy.deepcopy(self.responses[path])


def verify(responses, *, ref=REF, run_id=RUN, current="99"):
    return reuse.verify_reuse_run(Spy(responses), repository=REPO, run_id=run_id, ref=ref,
                                  current_run_id=current)


def test_eligible_source_run_passes_and_records_provenance():
    spy = Spy(fixture())
    record = reuse.verify_reuse_run(spy, repository=REPO, run_id=RUN, ref=REF,
                                    current_run_id="99")
    assert record["source_run_id"] == int(RUN)
    assert record["ref"] == REF
    assert record["ingestion_artifact"]["id"] == 11
    assert record["snapshot_artifact"]["id"] == 12
    assert record["source_ingest_job"]["conclusion"] == "success"
    assert record["reusing_run_id"] == "99"
    # Read-only GETs only, all through the API.
    assert all(path.startswith("/actions/") for path in spy.calls)


def _planted(mutate):
    responses = fixture()
    mutate(responses)
    return responses


RUN_PATH = f"/actions/runs/{RUN}"
JOBS_PATH = f"/actions/runs/{RUN}/jobs?per_page=100"
ARTS_PATH = f"/actions/runs/{RUN}/artifacts?per_page=100"

PLANTS = {
    "other-workflow": (lambda r: r[RUN_PATH].update(workflow_id=7), "workflow"),
    "scheduled-event": (lambda r: r[RUN_PATH].update(event="schedule"), "workflow_dispatch"),
    "other-repository": (lambda r: r[RUN_PATH].update(repository={"full_name": "x/y"}),
                         "repository"),
    "head-differs-from-ref": (lambda r: r[RUN_PATH].update(head_sha="e" * 40), "head_sha"),
    "run-not-completed": (lambda r: r[RUN_PATH].update(status="in_progress"), "completed"),
    "ingest-failed": (lambda r: r[JOBS_PATH]["jobs"][0].update(conclusion="failure"),
                      "ingest-and-validate"),
    "ingest-skipped": (lambda r: r[JOBS_PATH]["jobs"][0].update(conclusion="skipped"),
                       "ingest-and-validate"),
    "ingest-missing": (lambda r: r[JOBS_PATH].update(jobs=r[JOBS_PATH]["jobs"][1:],
                                                     total_count=1), "ingest-and-validate"),
    "ingestion-artifact-expired": (lambda r: r[ARTS_PATH]["artifacts"][0].update(expired=True),
                                   "full-model-api-ingestion-"),
    "snapshot-expired": (lambda r: r[ARTS_PATH]["artifacts"][1].update(expired=True),
                         "model-authority-api-db-"),
    "snapshot-missing": (lambda r: r[ARTS_PATH].update(
        artifacts=[a for a in r[ARTS_PATH]["artifacts"] if "api-db" not in a["name"]],
        total_count=2), "model-authority-api-db-"),
    "inventory-truncated": (lambda r: r[ARTS_PATH].update(total_count=500), "inventory"),
    "artifact-origin-differs": (
        lambda r: r[ARTS_PATH]["artifacts"][0]["workflow_run"].update(head_sha="e" * 40),
        "origin"),
}


@pytest.mark.parametrize("plant", sorted(PLANTS))
def test_each_violated_precondition_is_refused(plant):
    mutate, needle = PLANTS[plant]
    with pytest.raises(reuse.ReuseRefused) as refused:
        verify(_planted(mutate))
    assert needle in str(refused.value), str(refused.value)


@pytest.mark.parametrize("ref", ["", "FFFF" + "f" * 36, "f" * 39, "main"])
def test_reuse_requires_an_exact_ref_input(ref):
    with pytest.raises(reuse.ReuseRefused, match="ref"):
        verify(fixture(), ref=ref)


@pytest.mark.parametrize("run_id", ["", "abc", "-1", "1 2"])
def test_reuse_requires_a_numeric_run_id(run_id):
    with pytest.raises(reuse.ReuseRefused, match="run id"):
        verify(fixture(), run_id=run_id)


def test_reusing_the_current_run_is_refused():
    with pytest.raises(reuse.ReuseRefused, match="current run"):
        verify(fixture(), current=RUN)


def test_cli_writes_provenance_and_step_outputs(tmp_path, monkeypatch):
    monkeypatch.setattr(reuse, "_gh_api", lambda repository: Spy(fixture()))
    out = tmp_path / "o4" / "source.json"
    github_output = tmp_path / "gh-output"
    rc = reuse.main(["--repository", REPO, "--run-id", RUN, "--ref", REF,
                     "--current-run-id", "99", "--output", str(out),
                     "--github-output", str(github_output)])
    assert rc == 0
    record = json.loads(out.read_text(encoding="utf-8"))
    assert record["source_run_id"] == int(RUN) and record["mode"] == "reuse"
    lines = github_output.read_text(encoding="utf-8").splitlines()
    assert "ingestion_artifact_id=11" in lines and "snapshot_artifact_id=12" in lines


def test_cli_refusal_is_an_error_annotation_and_writes_nothing(tmp_path, monkeypatch, capsys):
    bad = _planted(PLANTS["ingest-failed"][0])
    monkeypatch.setattr(reuse, "_gh_api", lambda repository: Spy(bad))
    out = tmp_path / "source.json"
    rc = reuse.main(["--repository", REPO, "--run-id", RUN, "--ref", REF,
                     "--current-run-id", "99", "--output", str(out)])
    assert rc == 1
    assert "::error::" in capsys.readouterr().out
    assert not out.exists()
