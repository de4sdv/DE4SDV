"""Privileged-run wiring after the release-ceremony retirement (static + argument-spy).

Owner decision 2026-10-11: no model-authority bundle, closure or activation
step. These tests pin the one-job topology, the release evidence over the
export, the CI import rehearsal marked for removal after two releases, the
artifact naming boundary with the deploy/core-evidence consumers, and that
every workflow command line parses against the REAL script parser (the
parser is spied; nothing executes). No network, no dispatch.
"""
from __future__ import annotations

import argparse
import re
import shlex
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml"
JOB = "ingest-and-validate"
REV = "a" * 40
BATTERIES = ("Exercise three production semantic concerns",
             "Validate governed product-line scope through API identity",
             "Exercise read-only semantic MCP tools")
EVIDENCE = "Release evidence over the export"
TESTS = "Run production-ingestion tests"
UPLOAD = "Upload exact-head ingestion evidence"
VALIDATE = "Validate exact-revision checkout"


def _workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _steps():
    return _workflow()["jobs"][JOB]["steps"]


def _names():
    return [s.get("name") for s in _steps()]


def _step(name):
    matches = [s for s in _steps() if s.get("name") == name]
    assert len(matches) == 1, name
    return matches[0]


def _dispatch_inputs():
    workflow = _workflow()
    triggers = workflow.get("on", workflow.get(True))  # PyYAML reads `on:` as True
    return triggers["workflow_dispatch"]["inputs"]


def test_one_job_and_no_ceremony():
    assert list(_workflow()["jobs"]) == [JOB]
    assert set(_dispatch_inputs()) == {"ref"}
    text = WORKFLOW.read_text(encoding="utf-8")
    for retired in ("run_model_authority_bundle", "readback_verification_anchors",
                    "probe_definition_migration", "verify_restored_api_corpus",
                    "verify_reuse_ingestion_run", "measure_requirement_population_delta",
                    "model-authority-evidence", "model-authority-api-db", "pg_dump",
                    "--allow-candidate-bundle", "--model-authority-bundle",
                    "--semantic-authority", "/tmp/o4/", "reuse_ingestion_run"):
        assert retired not in text, retired


def test_release_evidence_runs_over_the_export_after_the_batteries_and_before_the_tests():
    names = _names()
    assert all(names.index(b) < names.index(EVIDENCE) for b in BATTERIES)
    assert names.index("Verify pilot read-back against candidate transaction 1") < names.index(EVIDENCE)
    assert names.index(EVIDENCE) < names.index(TESTS) < names.index(UPLOAD)
    run = re.sub(r"\\\n\s*", " ", _step(EVIDENCE)["run"])
    for argument in ("--export /tmp/de4sdv-full-model-export.json",
                     "--binding /tmp/de4sdv-full-model-binding.json",
                     "--semantic-report /tmp/de4sdv-full-model-semantic-validation.json",
                     "--query-coverage /tmp/de4sdv-full-model-semantic-query-coverage.json",
                     "--scope-validation /tmp/de4sdv-product-line-scope-validation.json",
                     "--mcp-validation /tmp/de4sdv-semantic-mcp-validation.json",
                     "--output /tmp/de4sdv-release-evidence.json"):
        assert argument in run, argument
    assert _step(EVIDENCE).get("continue-on-error") is None  # a failed check fails the run


def test_the_import_rehearsal_is_marked_for_removal_after_two_releases():
    text = WORKFLOW.read_text(encoding="utf-8")
    marker = text.index("# CI import rehearsal")
    note = text[marker:text.index("- name: Build pinned Systems Modeling API service")]
    assert "two releases" in note and "owner decision 2026-10-11" in note


def test_batteries_run_through_the_deployed_runtime_without_selector_flags():
    for name in BATTERIES:
        run = _step(name)["run"]
        assert "--binding /tmp/de4sdv-full-model-binding.json" in run
        assert "bundle" not in run and "authority" not in run


def test_the_upload_keeps_the_deploy_and_core_evidence_contract():
    upload = _step(UPLOAD)
    assert upload["with"]["name"] == "full-model-api-ingestion-${{ github.sha }}"
    paths = upload["with"]["path"].split()
    for required in ("/tmp/de4sdv-full-model-export.json", "/tmp/de4sdv-full-model-binding.json",
                     "/tmp/de4sdv-full-model-semantic-validation.json",
                     "/tmp/de4sdv-full-model-semantic-query-coverage.json",
                     "/tmp/de4sdv-semantic-mcp-validation.json",
                     "/tmp/de4sdv-release-evidence.json",
                     # Method Core Operational Evidence reads candidate transaction 1.
                     "/tmp/de4sdv-candidate-export.json", "/tmp/de4sdv-candidate-binding.json",
                     "/tmp/de4sdv-candidate-export-identity.json"):
        assert required in paths, required
    uploads = [s.get("with", {}).get("name", "") for s in _steps()
               if "upload-artifact" in str(s.get("uses"))]
    assert [n for n in uploads if n.startswith("full-model-api-ingestion-")] == [
        "full-model-api-ingestion-${{ github.sha }}"]


def _validate(tmp_path, requested, dispatch):
    """Run the validate step in a one-commit checkout, GitHub expressions filled in."""
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit",
                    "-q", "--allow-empty", "-m", "c"], cwd=checkout, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout, check=True,
                          capture_output=True, text=True).stdout.strip()
    script = (_step(VALIDATE)["run"]
              .replace("${{ github.event.inputs.ref }}", requested.replace("HEAD", head))
              .replace("${{ github.sha }}", dispatch.replace("HEAD", head)))
    assert "${{" not in script
    return subprocess.run(["bash", "--noprofile", "--norc", "-eo", "pipefail", "-c", script],
                          cwd=checkout, capture_output=True, text=True)


@pytest.mark.parametrize("requested, dispatch, refusal", [
    ("HEAD", "HEAD", None),
    ("", "HEAD", None),
    # A ref input that is not the dispatch tip: the run and its artifact would
    # carry the tip's name over another commit's evidence.
    ("HEAD", "b" * 40, "is not the dispatch revision"),
    ("b" * 40, "HEAD", "does not match checked-out"),
])
def test_the_run_ingests_only_its_dispatch_revision(tmp_path, requested, dispatch, refusal):
    result = _validate(tmp_path, requested, dispatch)
    if refusal is None:
        assert result.returncode == 0, result.stderr
    else:
        assert result.returncode == 1 and refusal in result.stderr, result.stderr


def _commands():
    out = []
    for step in _steps():
        run = step.get("run") or ""
        joined = re.sub(r"\\\n\s*", " ", run)
        for line in joined.splitlines():
            line = line.strip()
            if line.startswith(("python scripts/", "python3 scripts/")):
                line = re.sub(r'"\$\(git rev-parse HEAD\)"', REV, line)
                out.append((step["name"], shlex.split(line)))
    return out


class _Parsed(Exception):
    pass


_SCRIPTS = ("validate_full_model_semantic_queries.py", "validate_product_line_scope_api.py",
            "validate_semantic_mcp.py", "import_sysml_api_baseline.py",
            "check_release_evidence.py")
_COMMANDS = [c for c in _commands() if Path(c[1][1]).name in _SCRIPTS]


def test_every_release_script_is_exercised():
    assert {Path(argv[1]).name for _, argv in _COMMANDS} == set(_SCRIPTS)


@pytest.mark.parametrize("name, argv", _COMMANDS, ids=[c[0] for c in _COMMANDS])
def test_command_lines_parse_with_the_real_parsers(monkeypatch, name, argv):
    import importlib
    import inspect
    import sys

    argv = argv[:argv.index(">")] if ">" in argv else argv
    module = importlib.import_module("scripts." + Path(argv[1]).stem)
    captured = {}
    real = argparse.ArgumentParser.parse_args

    def spy(self, args=None, namespace=None):
        captured["namespace"] = real(self, args, namespace)
        raise _Parsed

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", spy)
    monkeypatch.setattr(sys, "argv", argv[1:])
    with pytest.raises(_Parsed):
        if inspect.signature(module.main).parameters:
            module.main(argv[2:])
        else:
            module.main()
    namespace = vars(captured["namespace"])
    for key in ("git_revision", "source_revision", "expected_git_revision"):
        if key in namespace:
            assert namespace[key] == REV
