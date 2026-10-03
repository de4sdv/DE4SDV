"""Executable workflow dataflow tests; no API closure or activation evidence."""
from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml"
REPORT = "/tmp/o4/de4sdv-o4-definition-migration-probe.json"
ERRORS = "/tmp/o4/de4sdv-o4-definition-migration-probe.stderr.log"
STEP = "Probe O4 definition closure against fresh full-model binding"


def _steps():
    return yaml.safe_load(WORKFLOW.read_text())["jobs"]["ingest-and-validate"]["steps"]


def _probe_step():
    matches = [s for s in _steps() if s.get("name") == STEP]
    assert len(matches) == 1, "privileged ingestion must execute the existing O4 probe"
    return matches[0]


def test_workflow_executes_fresh_binding_probe_and_retains_scope_bound_outputs():
    steps = _steps()
    probe = _probe_step()
    names = [s.get("name") for s in steps]
    assert names.index("Import and validate exact API revision") < names.index(STEP)
    assert names.index("Exercise read-only semantic MCP tools") < names.index(STEP)
    assert names.index(STEP) < names.index("Produce isolated committed-candidate export (transaction 1)")
    # Refusal must stay fatal and unconditional: a step-level `if` could skip
    # the probe entirely, and `continue-on-error` would swallow its exit code.
    assert probe.get("if") is None, "probe must never be conditionally skipped"
    assert probe.get("continue-on-error") is None, "probe refusal must remain fatal"
    upload = next(s for s in steps if s.get("name") == "Upload exact-head ingestion evidence")
    assert upload["if"] == "always()"
    retained = upload["with"]["path"].splitlines()
    assert REPORT in retained and ERRORS in retained


@pytest.mark.parametrize("exit_code", [0, 2, 1])
def test_workflow_shell_selects_exact_current_revision_and_propagates_refusal(tmp_path, exit_code):
    # Transport spy only: captures the executed CLI argv, never fabricates a
    # semantic result. Real CLI refusal is exercised separately below.
    step = _probe_step()
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    capture = tmp_path / "argv.json"
    shim = bin_dir / "python"
    shim.write_text(
        f"#!{sys.executable}\n"
        "import json, os, sys\n"
        "from pathlib import Path\n"
        "Path(os.environ['ARGV_CAPTURE']).write_text(json.dumps(sys.argv[1:]))\n"
        "print('transport-spy-only', file=sys.stderr)\n"
        "sys.exit(int(os.environ['PROBE_EXIT']))\n"
    )
    shim.chmod(0o755)
    # Redirect only output storage into pytest's owned directory, preserving
    # every input path and the real git rev-parse in the workflow command.
    run = step["run"].replace("/tmp/o4", shlex.quote(str(tmp_path / "o4")))
    env = dict(os.environ, PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
               ARGV_CAPTURE=str(capture), PROBE_EXIT=str(exit_code))
    result = subprocess.run(["bash", "-e", "-o", "pipefail", "-c", run],
                            cwd=ROOT, env=env, capture_output=True, text=True)
    assert result.returncode == exit_code
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    assert json.loads(capture.read_text()) == [
        "scripts/probe_definition_migration.py",
        "--root", str(ROOT),
        "--binding", "/tmp/de4sdv-full-model-binding.json",
        "--export", "/tmp/de4sdv-full-model-export.json",
        "--expected-git-revision", revision,
    ]
    assert (tmp_path / "o4" / Path(ERRORS).name).read_text() == "transport-spy-only\n"
    assert (tmp_path / "o4" / Path(REPORT).name).read_text() == ""


@pytest.mark.parametrize("content", [None, "[]", "{}"])
def test_real_probe_refuses_missing_or_malformed_selected_binding(tmp_path, content):
    binding = tmp_path / "fresh-binding.json"
    if content is not None:
        binding.write_text(content)
    result = subprocess.run([
        sys.executable, "-B", str(ROOT / "scripts/probe_definition_migration.py"),
        "--root", str(ROOT), "--binding", str(binding),
        "--export", str(tmp_path / "fresh-export.json"),
        "--expected-git-revision",
        subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
    ], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("refused:")
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("binding_revision,expected,scope,validated,closed", [
    ("a" * 40, "a" * 40, "full-model", "passed", True),
    ("b" * 40, "a" * 40, "full-model", "passed", False),
    ("a" * 40, None, "full-model", "passed", False),
    ("a" * 40, "a" * 40, "candidate", "passed", False),
    ("a" * 40, "a" * 40, "full-model", "failed", False),
])
def test_synthetic_probe_reads_selected_bytes_and_never_closes_stale_scope(
    tmp_path, binding_revision, expected, scope, validated, closed,
):
    # Explicit in-memory candidate seam, not the verified repository loader:
    # this tests report behavior only, never privileged provenance/closure.
    from de4sdv.semantic.definition_candidate import DefinitionCandidate
    from de4sdv.semantic.definition_migration import probe_definition_migration
    from de4sdv.semantic.kernel_contract import KernelContract, declaration_identity
    from de4sdv.sysml_api.revisions import RevisionBinding

    directory = ROOT / "docs/method-conformance/o4"
    projection = json.loads((directory / "definition-projection.json").read_text())
    profile = json.loads((directory / "definition-profile.json").read_text())
    candidate = DefinitionCandidate(
        source_revision=projection["binding"]["source_revision"],
        bound_inputs=projection["binding"]["bound_inputs"],
        identities=tuple(row["identity"] for row in projection["rows"]),
        rows=tuple(projection["rows"]), entries=tuple(profile["entries"]),
    )
    contract = KernelContract.load(ROOT / "approach/framework/ontology/de4sdv-basic-ontology.yaml")
    bindings = []
    elements = []
    for index, identity in enumerate(candidate.identities):
        mapping = candidate.row_for(identity)["grounding"]["kernel_binding_contract"]
        name, metaclass = declaration_identity(mapping["declaration"])
        element_id = f"synthetic-selected-{index}"
        elements.append({"@id": element_id, "@type": metaclass, "declaredName": name})
        bindings.append(dict(ontology_class=identity, element_id=element_id, **dict(mapping)))
    binding_path = tmp_path / "selected-binding.json"
    binding_path.write_text(json.dumps({
        "git_repository": "de4sdv/DE4SDV", "git_commit": binding_revision,
        "sysml_project_id": "synthetic-project", "sysml_commit_id": "synthetic-commit",
        "import_timestamp": "synthetic", "import_tool_version": "fixture",
        "semantic_validation": validated, "scope": scope,
        "ontology": contract.identity.to_dict(), "kernel_bindings": bindings,
    }))
    # Non-vacuity guard: an empty identity population would make the closure
    # and export assertions below pass over zero rows.
    assert candidate.identities, "fixture identities must not be empty"
    selected = tmp_path / "selected-export.json"
    selected.write_text(json.dumps({"elements": elements}))
    # A nearby plausible export is deliberately NOT selected: it is empty, so
    # selecting it instead would make resolved_count 0 and fail below.
    (tmp_path / "candidate-export.json").write_text(json.dumps({"elements": []}))
    report = probe_definition_migration(
        ROOT, contract=contract, candidate=candidate,
        binding=RevisionBinding.load(binding_path), export=selected,
        expected_git_revision=expected,
    )
    assert report["closure"]["closed"] is closed
    assert report["activation_eligible"] is closed
    assert report["closure"]["binding_git_revision"] == binding_revision
    assert report["closure"]["expected_git_revision"] == expected
    assert bool(report["activation_prerequisite"]) is not closed
    assert report["export"]["resolved_count"] == len(candidate.identities)
    assert report["export"]["identity_claim"] == "none (declaration-form evidence only)"
    assert {row["validated_binding_element_id"] for row in report["identities"]} == {
        row["element_id"] for row in bindings
    }
    assert all(row["export_matched_element_ids"][0].startswith("synthetic-selected-")
               for row in report["identities"])
