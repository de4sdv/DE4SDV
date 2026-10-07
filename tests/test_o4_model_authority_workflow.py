"""O4 Wave B privileged-run wiring (static + argument-spy; no network, no dispatch).

The model-authority steps run in a separate job of the privileged ingestion
workflow. These tests pin the job topology, the exact-revision inputs, the
artifact naming boundary with the deploy/core-evidence consumers, the
gate/measurement exit policy, and that every workflow command line parses
against the REAL script parser (the parser is spied; nothing executes).
"""
from __future__ import annotations

import argparse
import re
import shlex
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml"
JOB = "model-authority-evidence"
REV = "a" * 40


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _job(name=JOB):
    return _workflow()["jobs"][name]


def _step(name, job=JOB):
    matches = [s for s in _job(job)["steps"] if s.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def _names(job=JOB):
    return [s.get("name") for s in _job(job)["steps"]]


READBACK = "Decision-13 read-back of the implied verification anchors (restored same-run API snapshot)"
DELTA = "Measure the Wave A Requirement-population delta"
BUNDLE = "Build candidate model-authority bundle"
COVERAGE = "Model-projection coverage report against the candidate bundle"
COMPARE = "Same-revision model vs O3 vs legacy runtime equivalence"
CLOSE = "Close the model-authority bundle (activation eligibility)"
UPLOAD = "Upload model-authority evidence"


def test_separate_job_after_ingestion_keeps_both_budgets():
    job = _job()
    assert job["needs"] == "ingest-and-validate"
    assert "needs.ingest-and-validate.result == 'success'" in job["if"]
    assert "workflow_dispatch" in job["if"]
    assert job["timeout-minutes"] <= 360
    assert _job("ingest-and-validate")["timeout-minutes"] <= 360
    # The ingestion job gains only the snapshot + upload (no model steps).
    ingest = _names("ingest-and-validate")
    for name in (READBACK, DELTA, BUNDLE, COMPARE, CLOSE):
        assert name not in ingest


def test_model_job_does_not_turn_the_ingestion_run_red():
    # deploy-public-sysml-api / method-core evidence require a successful run.
    assert _job()["continue-on-error"] is True


def test_model_job_needs_no_licence_secret():
    text = yaml.safe_dump(_job())
    assert "secrets." not in text


def test_snapshot_artifact_never_matches_the_ingestion_artifact_prefix():
    ingest = _job("ingest-and-validate")["steps"]
    names = [s.get("with", {}).get("name", "") for s in ingest if "upload-artifact" in str(s.get("uses"))]
    names += [s.get("with", {}).get("name", "") for s in _job()["steps"]
              if "upload-artifact" in str(s.get("uses"))]
    prefixed = [n for n in names if n.startswith("full-model-api-ingestion-")]
    assert prefixed == ["full-model-api-ingestion-${{ github.sha }}"]


def test_snapshot_is_taken_after_the_o3_comparison():
    ingest = _names("ingest-and-validate")
    assert ingest.index("Run same-revision O3 runtime equivalence comparison") < ingest.index(
        "Snapshot API database for the model-authority job")


def test_restored_inputs_are_revision_checked_before_use():
    names = _names()
    assert names.index("Verify inputs are bound to the checked-out revision") < names.index(
        "Restore API database snapshot") < names.index(READBACK)
    run = _step("Verify inputs are bound to the checked-out revision")["run"]
    assert "sha256sum -c" in run
    for path in ("de4sdv-full-model-export.json", "de4sdv-full-model-binding.json",
                 "o3/de4sdv-o3-candidate-bundle.json"):
        assert path in run


def test_step_order_and_gate_policy():
    names = _names()
    order = [READBACK, DELTA, BUNDLE, COVERAGE, COMPARE, CLOSE, UPLOAD]
    assert [names.index(n) for n in order] == sorted(names.index(n) for n in order)
    assert _step(READBACK).get("if") is None  # never skipped
    for name in (DELTA, BUNDLE, COVERAGE, COMPARE, CLOSE):
        assert _step(name)["if"] == "${{ !cancelled() }}"
    assert _step(UPLOAD)["if"] == "always()"
    # The delta tolerates ONLY exit 2 (measured difference); errors still fail.
    delta = _step(DELTA)["run"]
    assert 'if [ "$rc" = "2" ]' in delta and 'exit "$rc"' in delta
    for name in (READBACK, COMPARE, CLOSE):
        assert "set +e" not in _step(name)["run"]


def _commands(job=JOB):
    out = []
    for step in _job(job)["steps"]:
        run = step.get("run") or ""
        joined = re.sub(r"\\\n\s*", " ", run)
        for line in joined.splitlines():
            line = line.strip()
            if line.startswith("python scripts/"):
                line = re.sub(r'"\$\(git rev-parse HEAD\)"', REV, line)
                line = re.sub(r'"\$\(python -c [^"]*\)"', "o3b-" + "b" * 32, line)
                out.append((step["name"], shlex.split(line)))
    return out


class _Parsed(Exception):
    pass


@pytest.mark.parametrize("name, argv", _commands(), ids=[c[0] for c in _commands()])
def test_workflow_command_lines_parse_with_the_real_parsers(monkeypatch, name, argv):
    import importlib

    script = argv[1]
    if not (ROOT / script).is_file():
        # B2's coverage CLI lands in the integrated PR; this guard is removed
        # by the controller's integration check (it must then parse too).
        pytest.skip(f"{script} is provided by a sibling implementer")
    module = importlib.import_module("scripts." + Path(script).stem)
    captured = {}
    real = argparse.ArgumentParser.parse_args

    def spy(self, args=None, namespace=None):
        captured["namespace"] = real(self, args, namespace)
        raise _Parsed

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", spy)
    with pytest.raises(_Parsed):
        module.main(argv[2:])
    namespace = vars(captured["namespace"])
    for key in ("git_revision", "source_revision"):
        if key in namespace:
            assert namespace[key] == REV


def test_every_model_output_is_uploaded_and_close_reads_produced_files():
    produced = set()
    for _, argv in _commands():
        for flag in ("--output", "--json"):
            if flag in argv:
                produced.add(argv[argv.index(flag) + 1])
    produced |= {"/tmp/o4/de4sdv-model-authority-candidate-bundle.json",
                 "/tmp/o4/de4sdv-model-authority-equivalence-report.json"}
    close = dict(zip(*[iter(next(a for n, a in _commands() if n == CLOSE)[3:])] * 2))
    from_job1 = {"/tmp/de4sdv-full-model-binding.json",
                 "/tmp/o4/de4sdv-o4-definition-migration-probe.json"}
    for flag in ("--model", "--coverage", "--equivalence", "--readback"):
        assert close[flag] in produced, flag
    for flag in ("--binding", "--definition-probe"):
        assert close[flag] in from_job1
    ingest_upload = _step("Upload exact-head ingestion evidence", "ingest-and-validate")
    for path in from_job1:
        assert path in ingest_upload["with"]["path"]
    uploaded = _step(UPLOAD)["with"]["path"]
    from scripts import run_model_authority_bundle as cli

    for path in produced | {f"/tmp/o4/{cli.CLOSED_BUNDLE}", f"/tmp/o4/{cli.ATTESTATION}",
                            f"/tmp/o4/{cli.ELIGIBILITY}"}:
        assert path in uploaded, path


SNAPSHOT = "Snapshot API database for the model-authority job"
SNAPSHOT_UPLOAD = "Upload API database snapshot for the model-authority job"
SNAPSHOT_DOWNLOAD = "Download same-run API database snapshot"
SNAPSHOT_REQUIRED = "Require the same-run API database snapshot"


def test_snapshot_steps_are_off_the_ingestion_critical_path():
    """R4: a snapshot/upload failure never fails ingest-and-validate; scheduled runs skip it."""
    for name in (SNAPSHOT, SNAPSHOT_UPLOAD):
        step = _step(name, "ingest-and-validate")
        assert step["if"] == "github.event_name == 'workflow_dispatch'", name
        assert step["continue-on-error"] is True, name


def test_missing_snapshot_fails_the_model_job_clearly():
    names = _names()
    download = _step(SNAPSHOT_DOWNLOAD)
    assert download["continue-on-error"] is True
    required = _step(SNAPSHOT_REQUIRED)
    assert names.index(SNAPSHOT_DOWNLOAD) < names.index(SNAPSHOT_REQUIRED) < names.index(
        "Verify inputs are bound to the checked-out revision")
    assert required.get("if") is None and required.get("continue-on-error") is None
    run = required["run"]
    assert "::error" in run and "model-authority-api-db-" in run and "exit 1" in run
    for path in ("/tmp/o4-db/sysml2.dump", "/tmp/o4-db/sysml2.dump.sha256"):
        assert path in run
