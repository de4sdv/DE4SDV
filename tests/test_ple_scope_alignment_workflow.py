"""Privileged PLE Scope Alignment workflow wiring (static; no network, no dispatch).

Pins: the triggers (pull requests on the scope-alignment paths only, plus
maintainer dispatch), the fork and author guard of the licensed validation,
read-only permissions, the exact-head resolution, the frozen experiment
checkout relocated outside the executor checkout, the dirty-checkout refusals
around every recording step, the secret scoping (the licence reaches only the
two Syside steps), the runner command line (parsed against the real parser),
the receipt predicate (executed against synthetic receipts) and the artifact.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterator

import pytest
import yaml

import test_ple_qualification_clean_checkout as clean

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/privileged-ple-scope-alignment.yml"
VALIDATION = ROOT / ".github/workflows/privileged-syside-validation.yml"
QUALIFICATION = ROOT / ".github/workflows/privileged-ple-qualification.yml"
RUNNER = "scripts/run_ple_scope_alignment.py"
#: The frozen experiment at PLEML 1.1.0 (tag pleml-1.1.0-frozen) and its PLEML pin.
FROZEN = "69bbe093c179f2121274b9f604c7d6a10de19e77"
PIN = "76e2be934453d77c4094141400b8ad8eb90a54a2"
LICENCE_VALUE = "${{ secrets.SYSIDE_LICENSE_KEY }}"
LICENCE_PRESENCE = "${{ secrets.SYSIDE_LICENSE_KEY != '' }}"
JOB = "scope-alignment"
GUARD_TEXT = "the checkout is not clean:"
OWN_PATHS = {
    "model-based-product-line-engineering/pleml-scope-alignment/**",
    "scripts/run_ple_scope_alignment.py",
    "de4sdv/semantic/ple_scope_alignment.py",
    "tests/test_ple_scope_alignment_model.py",
    "tests/test_ple_scope_alignment_evaluator.py",
    "tests/test_ple_scope_alignment_workflow.py",
    "scripts/compare_ple_scope_alignment.py",
    "tests/test_ple_scope_alignment_oracle.py",
    ".github/workflows/privileged-ple-scope-alignment.yml",
}
ORACLE = "scripts/compare_ple_scope_alignment.py"


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _workflow() -> dict[str, Any]:
    return _load(WORKFLOW)


def _steps() -> list[dict[str, Any]]:
    return _workflow()["jobs"][JOB]["steps"]


def _step(needle: str) -> tuple[int, dict[str, Any]]:
    matches = [(i, s) for i, s in enumerate(_steps()) if needle in (s.get("run") or "")]
    assert len(matches) == 1, needle
    return matches[0]


def _strings(value: Any, path: tuple = ()) -> Iterator[tuple[tuple, str]]:
    if isinstance(value, dict):
        for key, item in value.items():
            yield from _strings(item, (*path, key))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from _strings(item, (*path, index))
    elif isinstance(value, str):
        yield path, value


def _normalized(text: str) -> str:
    return " ".join(text.split())


def test_triggers_are_the_scope_alignment_paths_and_maintainer_dispatch() -> None:
    triggers = _workflow()[True]
    assert set(triggers) == {"pull_request", "workflow_dispatch"}
    paths = triggers["pull_request"]["paths"]
    assert len(paths) == len(set(paths)) and set(paths) == OWN_PATHS
    for path in OWN_PATHS:
        if path.endswith("/**"):
            assert any(f.is_file() for f in ROOT.glob(path[:-3] + "/*")), path
        else:
            assert (ROOT / path).is_file(), path
    # No general model path: the production selectors stay untouched (owner decision D7).
    validation = set(_load(VALIDATION)[True]["pull_request"]["paths"])
    assert not (set(paths) & validation)
    assert triggers["workflow_dispatch"]["inputs"]["ref"]["required"] is True


def test_the_job_keeps_the_privileged_validation_guard_and_read_only_permissions() -> None:
    workflow = _workflow()
    guard = _load(VALIDATION)["jobs"]["syside-validation"]["if"]
    assert _normalized(workflow["jobs"][JOB]["if"]) == _normalized(guard)
    assert "github.event.pull_request.head.repo.full_name == github.repository" in guard
    assert workflow["permissions"] == {"contents": "read"}
    assert list(workflow["jobs"]) == [JOB]
    assert "permissions" not in workflow["jobs"][JOB]
    assert "env" not in workflow and "env" not in workflow["jobs"][JOB]
    assert 0 < workflow["jobs"][JOB]["timeout-minutes"] <= 45
    assert "github.event.pull_request.number" in workflow["concurrency"]["group"]
    assert workflow["concurrency"]["cancel-in-progress"] is True


def test_the_executor_is_the_exact_head_and_the_experiment_is_frozen_and_relocated() -> None:
    steps = _steps()
    checkouts = [s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@")]
    assert len(checkouts) == 2
    head, experiment = checkouts
    # The executor is the pull-request head or the dispatched ref, so the step names neither.
    assert head["name"] == "Checkout the executor commit"
    assert "pull-request head is the executor" not in WORKFLOW.read_text()
    assert head["with"]["ref"] == "${{ github.event.pull_request.head.sha || inputs.ref }}"
    assert head["with"]["persist-credentials"] is False
    # The oracle tests read the retained record's revision from history: never a shallow checkout.
    assert head["with"]["fetch-depth"] == 0
    assert experiment["with"] == {"ref": FROZEN, "path": "_ple-experiment", "submodules": "recursive",
                                  "persist-credentials": False}
    revision = next(s for s in steps if s.get("id") == "revision")
    assert revision["env"] == {"EXPECTED_HEAD": "${{ github.event.pull_request.head.sha }}"}
    assert "${{" not in revision["run"]
    assert "git rev-parse HEAD" in revision["run"] and '"$EXPECTED_HEAD"' in revision["run"]
    # The relocation is the merged PLE qualification step (#375), verbatim.
    _index, relocate = _step('mv _ple-experiment "$RUNNER_TEMP/_ple-experiment"')
    qualification = next(s for s in _load(QUALIFICATION)["jobs"]["qualify"]["steps"]
                         if s.get("name") == "Relocate the frozen experiment outside the executor checkout")
    assert relocate["name"] == qualification["name"] and relocate["run"] == qualification["run"]
    assert steps.index(relocate) == steps.index(experiment) + 1
    _index, verify = _step(f"grep -qx {FROZEN} ")
    assert f"grep -qx {PIN} " in verify["run"]
    assert 'rev-parse HEAD > "$RUNNER_TEMP/ple-evidence/experiment-revision.txt"' in verify["run"]
    assert 'rev-parse HEAD > "$RUNNER_TEMP/ple-evidence/pleml-pin.txt"' in verify["run"]
    assert steps.index(verify) == steps.index(relocate) + 1


# -- the clean-checkout discipline of #375, applied with the merged helpers ----------------

_RUN_STEPS = [s["name"] for s in _steps() if s.get("run")]
_OUTPUTS = ("_ple-experiment", "ple-evidence")


@pytest.mark.parametrize("name", _RUN_STEPS)
def test_no_run_step_writes_a_relative_or_workspace_path(name) -> None:
    step = next(s for s in _steps() if s.get("name") == name)
    for code in clean._shell_lines(step["run"]):
        argv = shlex.split(code)
        for path in clean._written_paths(argv):
            assert clean._outside_the_checkout(path), (name, path)
        if "tee" in argv:
            assert clean._outside_the_checkout(argv[argv.index("tee") + 1]), (name, code)


@pytest.mark.parametrize("name", _RUN_STEPS)
def test_every_workflow_output_is_addressed_outside_the_checkout(name) -> None:
    step = next(s for s in _steps() if s.get("name") == name)
    for code in clean._shell_lines(step["run"]):
        argv = shlex.split(code)
        for index, token in enumerate(argv):
            if any(output in token for output in _OUTPUTS):
                if argv[0] == "mv" and index < len(argv) - 1:
                    continue  # the relocation takes the experiment out of the checkout
                assert clean._outside_the_checkout(token), (name, token)


@pytest.mark.parametrize("name", _RUN_STEPS)
def test_no_heredoc_writes_through_a_checkout_relative_path(name) -> None:
    step = next(s for s in _steps() if s.get("name") == name)
    for body in clean.HEREDOC.findall(step["run"]):
        assert clean._checkout_relative_writes(body) == [], name
        assert re.search(r"""(?:Path|open)\(\s*['"](?:_ple-experiment|ple-evidence)""", body) is None, name


def test_no_background_process_is_started() -> None:
    assert [s["name"] for s in _steps() if clean._starts_a_background_process(s.get("run") or "")] == []


def test_the_guards_are_the_ingestion_guard_verbatim() -> None:
    ingestion = _load(ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml")
    reference = next(s for s in ingestion["jobs"]["ingest-and-validate"]["steps"]
                     if s.get("name") == "Refuse a dirty checkout before the import")
    guards = [s for s in _steps() if GUARD_TEXT in (s.get("run") or "")]
    for guard in guards:
        assert guard["run"] == reference["run"], guard["name"]
        assert "continue-on-error" not in guard


@pytest.mark.parametrize("kind", [None, "nested experiment checkout", "service log", "modified tracked file"])
def test_a_dirty_checkout_guard_refuses_what_the_receipt_would_record(tmp_path, kind) -> None:
    checkout = tmp_path / "checkout"
    clean._scratch_checkout(checkout)
    expected = clean._dirty(checkout, kind) if kind else None
    guard = next(s for s in _steps() if GUARD_TEXT in (s.get("run") or ""))
    result = clean._bash(guard["run"], checkout)
    if expected:
        assert result.returncode == 1 and expected in result.stderr, result.stderr
    else:
        assert result.returncode == 0, result.stderr


def test_the_relocation_leaves_a_clean_executor_checkout_and_a_working_experiment(tmp_path) -> None:
    workspace, temp = tmp_path / "workspace", tmp_path / "runner-temp"
    clean._scratch_checkout(workspace)
    head = clean._experiment_checkout(workspace, tmp_path / "pleml")
    temp.mkdir()
    _index, relocate = _step('mv _ple-experiment "$RUNNER_TEMP/_ple-experiment"')
    result = clean._bash(relocate["run"], workspace, dict(os.environ, RUNNER_TEMP=str(temp)))
    assert result.returncode == 0, result.stderr
    assert clean._git(workspace, "status", "--porcelain") == ""
    assert not (workspace / "_ple-experiment").exists()
    assert clean._git(temp / "_ple-experiment", "rev-parse", "HEAD") == head
    (temp / "_ple-experiment").mkdir(exist_ok=True)
    occupied = clean._bash(relocate["run"], workspace, dict(os.environ, RUNNER_TEMP=str(temp)))
    assert occupied.returncode == 1


def test_dirty_checkout_refusals_surround_every_recording_step() -> None:
    steps = _steps()
    guards = [i for i, s in enumerate(steps) if GUARD_TEXT in (s.get("run") or "")]
    assert len(guards) >= 3
    for index in guards:
        run = steps[index]["run"]
        assert 'dirty="$(git status --porcelain)"' in run and "exit 1" in run
        assert steps[index]["name"].startswith("Refuse a dirty checkout")
    check_index, _ = _step("syside check")
    runner_index, _ = _step(RUNNER)
    assert check_index - 1 in guards
    assert runner_index - 1 in guards
    assert any(index > runner_index for index in guards), "a guard runs after the evaluation"


def test_the_licence_reaches_only_the_two_syside_steps() -> None:
    workflow = _workflow()
    hits = [(path, text) for path, text in _strings(workflow) if "secrets." in text.lower()]
    for path, text in hits:
        assert path[:3] == ("jobs", JOB, "steps") and path[4] == "env" and len(path) == 6, path
        assert text in {LICENCE_VALUE, LICENCE_PRESENCE}, text
    presence = [path for path, text in hits if text == LICENCE_PRESENCE]
    assert len(presence) == 1
    licence_step = _steps()[presence[0][3]]
    assert licence_step["id"] == "licence"
    assert "python" not in licence_step["run"] and "scripts/" not in licence_step["run"]
    value_steps = sorted(path[3] for path, text in hits if text == LICENCE_VALUE)
    check_index, check = _step("syside check")
    runner_index, runner = _step(RUNNER)
    assert value_steps == sorted([check_index, runner_index])
    assert set(check["env"]) == {"SYSIDE_LICENSE_KEY"}
    assert set(runner["env"]) == {"SYSIDE_LICENSE_KEY", "HEAD_SHA"}
    for step in _steps():
        run = step.get("run") or ""
        assert "git push" not in run and "gh pr merge" not in run and "deploy.py" not in run


def test_syside_check_covers_the_reviewed_roots_the_pinned_library_and_the_model() -> None:
    from scripts.validate_sysml import MODEL_PATHS

    _index, check = _step("syside check")
    # The default `bash -e` shell has no pipefail: without it, `tee` would mask a failed check.
    assert check["run"].lstrip().startswith("set -eo pipefail\n")
    command = " ".join(re.sub(r"\\\n\s*", " ", check["run"]).split())
    for root in MODEL_PATHS:
        assert f" {root.as_posix()} " in command + " ", root
    assert '"$RUNNER_TEMP/_ple-experiment/external/pleml/PLEML.sysml"' in command
    assert "model-based-product-line-engineering/pleml-scope-alignment/aebs_product_line_scope_alignment.sysml" in command
    assert "syside-check.txt" in command


def test_the_runner_command_parses_against_the_real_parser() -> None:
    _index, step = _step(RUNNER)
    assert step["env"]["HEAD_SHA"] == "${{ steps.revision.outputs.sha }}"
    command = re.sub(r"\\\n\s*", " ", step["run"]).strip()
    assert command.startswith(f"python {RUNNER} ")
    substituted = command.replace("$HEAD_SHA", "a" * 40).replace("$RUNNER_TEMP", "/tmp/runner-temp")
    argv = shlex.split(substituted)[2:]
    spec = importlib.util.spec_from_file_location("_ple_scope_alignment_runner", ROOT / RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    args = module.build_parser().parse_args(argv)
    assert args.licensed is True and args.expected_executor == "a" * 40
    assert args.experiment == Path("/tmp/runner-temp/_ple-experiment")
    assert args.out == Path("/tmp/runner-temp/ple-evidence/scope-alignment")


def test_the_unlicensed_tests_run_with_the_verified_interpreter() -> None:
    _index, step = _step("tests/test_ple_scope_alignment_evaluator.py")
    assert step["env"] == {"DE4SDV_PLE_INTERPRETER": "${{ runner.temp }}/_ple-experiment/tools/pleml_gate_a.py"}
    assert "tests/test_ple_scope_alignment_model.py" in step["run"]
    assert "tests/test_ple_scope_alignment_workflow.py" in step["run"]
    assert "tests/test_ple_scope_alignment_oracle.py" in step["run"]


def test_the_comparison_oracle_runs_unlicensed_on_the_fresh_receipt_between_two_guards() -> None:
    steps = _steps()
    check_index, _check = _step("receipt['expectation']")
    oracle_index, step = _step(ORACLE)
    assert oracle_index > check_index, "the oracle runs after the receipt passed its predicate"
    assert step["env"] == {"HEAD_SHA": "${{ steps.revision.outputs.sha }}"}, "no licence, only the exact head"
    guards = [i for i, s in enumerate(steps) if GUARD_TEXT in (s.get("run") or "")]
    assert oracle_index - 1 in guards and oracle_index + 1 in guards
    command_line, summary_line = list(clean._shell_lines(step["run"]))
    argv = shlex.split(command_line)
    assert argv[:2] == ["python", ORACLE]
    options = dict(zip(argv[2::2], argv[3::2]))
    assert options["--evidence"] == "fresh" and options["--run-id"] == "$GITHUB_RUN_ID"
    assert options["--receipt"] == "$RUNNER_TEMP/ple-evidence/scope-alignment/receipt.json"
    assert options["--governed-scope"] == "$RUNNER_TEMP/ple-evidence/scope-alignment/governed-scope-validation.json"
    assert options["--out"] == "$RUNNER_TEMP/ple-evidence/comparison"
    [upload] = [s for s in steps if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
    expected_name = upload["with"]["name"].replace("${{ steps.revision.outputs.sha }}", "$HEAD_SHA").replace(
        "${{ github.run_id }}", "$GITHUB_RUN_ID")
    assert options["--artifact"] == expected_name, "the oracle binds the same artifact name the upload uses"
    assert shlex.split(summary_line) == ["cat", "$RUNNER_TEMP/ple-evidence/comparison/comparison.md",
                                         ">>", "$GITHUB_STEP_SUMMARY"]
    # The command line parses against the real parser.
    from scripts import compare_ple_scope_alignment as module

    substituted = [token.replace("$HEAD_SHA", "a" * 40).replace("$GITHUB_RUN_ID", "1")
                   .replace("$RUNNER_TEMP", "/tmp/runner-temp") for token in argv[2:]]
    args = module.build_parser().parse_args(substituted)
    assert args.evidence == "fresh" and args.artifact == "ple-scope-alignment-" + "a" * 40 + "-1"
    assert args.out == Path("/tmp/runner-temp/ple-evidence/comparison")


def _predicate(tmp_path: Path, receipt: dict[str, Any]) -> subprocess.CompletedProcess[str]:
    _index, step = _step("receipt['expectation']")
    code = step["run"].split("python - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]
    evidence = tmp_path / "ple-evidence/scope-alignment"
    evidence.mkdir(parents=True)
    (evidence / "receipt.json").write_text(json.dumps(receipt))
    environment = dict(os.environ, RUNNER_TEMP=str(tmp_path), GITHUB_STEP_SUMMARY=str(tmp_path / "summary.md"))
    return subprocess.run([sys.executable, "-B", "-c", code], cwd=tmp_path, env=environment,
                          capture_output=True, text=True)


def _good_receipt() -> dict[str, Any]:
    return {
        "mode": "licensed-serialization", "fresh_serialization": True, "executor_source_dirty": False,
        "qualified": False, "adoption_authorized": False, "authority_activation_authorized": False,
        "api_ingestion": False,
        "expectation": {"matches": True, "mismatches": []},
        "alignment": {"configurations": [
            {"configuration": "standaloneAutowareAEBSReferenceMemberConfiguration", "role": "member",
             "status": "configuration-valid", "violated_bound": None, "selected_alternatives": ["standalone"],
             "derived_asset_variants": [{"variation": "osPlatform", "variant": "linux"}]}],
            "checks": {"frozen_resolver_agrees": True, "feature_binding_metadata_observed": True,
                       "configuration_binding_metadata_observed": True}},
    }


def test_the_receipt_predicate_accepts_the_expected_receipt_and_writes_the_summary(tmp_path) -> None:
    result = _predicate(tmp_path, _good_receipt())
    assert result.returncode == 0, result.stderr
    summary = (tmp_path / "summary.md").read_text()
    assert "standaloneAutowareAEBSReferenceMemberConfiguration" in summary
    assert "qualified: false" in summary


@pytest.mark.parametrize("mutation,message", [
    ({"expectation": {"matches": False, "mismatches": ["x"]}}, "expected outcome"),
    ({"executor_source_dirty": True}, "dirty"),
    ({"qualified": True}, "promoted"),
    ({"adoption_authorized": True}, "promoted"),
    ({"fresh_serialization": False}, "fresh"),
    ({"alignment": {"configurations": [], "checks": {"frozen_resolver_agrees": False}}}, "frozen resolver"),
    ({"alignment": {"configurations": [], "checks": {"frozen_resolver_agrees": True, "feature_binding_metadata_observed": False,
                                                      "configuration_binding_metadata_observed": True}}}, "metadata"),
    ({"alignment": {"configurations": [], "checks": {"frozen_resolver_agrees": True, "feature_binding_metadata_observed": True,
                                                      "configuration_binding_metadata_observed": False}}}, "metadata"),
])
def test_the_receipt_predicate_rejects_promotion_and_drift(tmp_path, mutation, message) -> None:
    receipt = _good_receipt()
    receipt.update(mutation)
    result = _predicate(tmp_path, receipt)
    assert result.returncode != 0
    assert message in result.stderr


def test_the_artifact_is_named_by_head_and_run_and_retained_under_runner_temp() -> None:
    steps = _steps()
    [upload] = [s for s in steps if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
    assert upload["if"].startswith("always()")
    assert upload["with"]["name"] == "ple-scope-alignment-${{ steps.revision.outputs.sha }}-${{ github.run_id }}"
    assert upload["with"]["path"] == "${{ runner.temp }}/ple-evidence/"
    assert upload["with"]["retention-days"] == 30
    assert steps[-1] is upload
    assert not any("download-artifact" in str(s.get("uses", "")) for s in steps)
