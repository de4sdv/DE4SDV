"""Privileged-run wiring after the release-ceremony retirement (static + argument-spy).

Owner decision 2026-10-11: no model-authority bundle, closure or activation
step. These tests pin the one-job topology, the release evidence over the
export, the CI import rehearsal marked for removal after two releases, the
artifact naming boundary with the deploy/core-evidence consumers, and that
every workflow command line parses against the REAL script parser (the
parser is spied; nothing executes), and that the checkout the runtime's
startup check reads is the dispatch revision and stays clean. No network,
no dispatch.
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
PARITY = "Exercise production semantic concerns and the successor parity"
BATTERIES = (PARITY,
             "Validate governed product-line scope through API identity",
             "Exercise read-only semantic MCP tools")
EVIDENCE = "Release evidence over the export"
TESTS = "Run production-ingestion tests"
UPLOAD = "Upload exact-head ingestion evidence"
VALIDATE = "Validate exact-revision checkout"
GUARDS = ("Refuse a dirty checkout before the import",
          "Refuse a dirty checkout before the candidate imports")


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


def test_the_successor_parity_compares_the_imported_api_revision_with_the_imported_export():
    """The allocatedTo forward obligations: the parity runs over the API revision this run imported
    and the export it imported, before the release evidence reads its report, and a failure fails the
    run (no continue-on-error), so no deploy takes the run's evidence."""
    names = _names()
    assert names.index("Import and validate exact API revision") < names.index(PARITY) < names.index(EVIDENCE)
    run = re.sub(r"\\\n\s*", " ", _step(PARITY)["run"])
    for argument in ("python scripts/validate_full_model_semantic_queries.py",
                     "--api-url http://127.0.0.1:9000",
                     "--export /tmp/de4sdv-full-model-export.json",
                     "--output /tmp/de4sdv-full-model-semantic-query-coverage.json"):
        assert argument in run, argument
    assert _step(PARITY).get("continue-on-error") is None


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


def _starts_a_background_process(run):
    """A lone ``&`` outside a comment (not ``&&``, ``2>&1``, ``&>`` or ``|&``)."""
    for line in run.splitlines():
        code = re.split(r"(?:^|\s)#", line, maxsplit=1)[0]
        if re.search(r"(?<![&|<>])&(?![&>])", code):
            return True
    return False


@pytest.mark.parametrize("line, started", [
    ("serve > /tmp/x.log 2>&1 &", True), ("serve & # comment", True), ("serve & disown", True),
    ("serve & echo $! > /tmp/pid", True), ("( serve & )", True), ("serve &\r", True),
    ("a && b", False), ("serve 2>&1 | tee x", False), ("serve &> /tmp/x", False),
    ("a |& b", False), ("# serve &", False), ('[ "${#SHA}" != "40" ]', False),
])
def test_the_background_process_pattern(line, started):
    assert _starts_a_background_process(line) is started


def test_background_services_run_outside_the_checkout():
    # A service keeps writing after its step ends (the API service writes
    # logs/application.log relative to its working directory), and the
    # runtime's startup check in the batteries and the release evidence
    # refuses a checkout with untracked files (run 38669722943: "?? logs/").
    started = [s for s in _steps() if _starts_a_background_process(s.get("run") or "")]
    assert [s["name"] for s in started] == ["Start pinned Systems Modeling API service"]
    for step in started:
        assert step.get("working-directory", "").startswith("/tmp/"), step["name"]


def _scratch_checkout(tmp_path):
    """A one-commit Git checkout; returns it and its HEAD."""
    checkout = tmp_path / "checkout"
    checkout.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    subprocess.run(["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit",
                    "-q", "--allow-empty", "-m", "c"], cwd=checkout, check=True)
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=checkout, check=True,
                          capture_output=True, text=True).stdout.strip()
    return checkout, head


def _bash(script, cwd):
    """Run a step script the way GitHub runs a `run:` step without `shell:` (bash -e)."""
    assert "${{" not in script
    return subprocess.run(["bash", "-e", "-c", script], cwd=cwd, capture_output=True, text=True)


def _validate(tmp_path, requested, dispatch):
    """Run the validate step in a one-commit checkout, GitHub expressions filled in."""
    checkout, head = _scratch_checkout(tmp_path)
    script = (_step(VALIDATE)["run"]
              .replace("${{ github.event.inputs.ref }}", requested.replace("HEAD", head))
              .replace("${{ github.sha }}", dispatch.replace("HEAD", head)))
    return _bash(script, checkout)


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


def test_dirty_checkout_guards_run_before_each_long_phase():
    names = _names()
    assert (names.index("Start pinned Systems Modeling API service") < names.index(GUARDS[0])
            < names.index("Import and validate exact API revision"))
    assert (names.index("Produce second independent serialization transaction (MC-14)")
            < names.index(GUARDS[1])
            < names.index("Import candidate transaction 1 into a distinct API project"))


@pytest.mark.parametrize("guard", GUARDS)
@pytest.mark.parametrize("untracked", [None, "logs/application.log"])
def test_a_dirty_checkout_guard_refuses_what_the_startup_check_refuses(tmp_path, guard, untracked):
    checkout, _ = _scratch_checkout(tmp_path)
    if untracked:
        (checkout / untracked).parent.mkdir(parents=True)
        (checkout / untracked).write_text("x", encoding="utf-8")
    result = _bash(_step(guard)["run"], checkout)
    if untracked:
        assert result.returncode == 1 and "?? logs/" in result.stderr, result.stderr
    else:
        assert result.returncode == 0, result.stderr
