"""Privileged PLE Authority workflow wiring (static; no network, no dispatch).

Pins: the triggers (pull requests on the PLEML files, the runner and these
tests only, plus maintainer dispatch), the fork and author guard of the
licensed validation, read-only permissions, the exact-head resolution as the
only checkout, the fenced PLEML package installed and byte-checked before any
step reads it, the clean-checkout discipline of the PLE qualification
workflow, the API service
started outside the checkout, the dirty-checkout refusals around every
recording step, the secret scoping (the licence reaches only the two Syside
steps), the validation roots, the runner command line (parsed against the
real parser) and the artifact.
"""

from __future__ import annotations

import re
import shlex
from pathlib import Path
from typing import Any, Iterator

import pytest
import yaml

import test_ple_authority_model as model_test
import test_ple_qualification_clean_checkout as clean
from de4sdv.semantic import pleml_package
from scripts import run_ple_authority as runner

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/privileged-ple-authority.yml"
VALIDATION = ROOT / ".github/workflows/privileged-syside-validation.yml"
QUALIFICATION = ROOT / ".github/workflows/privileged-ple-qualification.yml"
INGESTION = ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml"
RUNNER = "scripts/run_ple_authority.py"
#: PLEML 1.1.1 as the fenced Sysand project installs it (ADR 0022, step S1).
LIBRARY = pleml_package.LIBRARY_PATH.as_posix()
PROJECT = pleml_package.PROJECT.as_posix()
LICENCE_VALUE = "${{ secrets.SYSIDE_LICENSE_KEY }}"
LICENCE_PRESENCE = "${{ secrets.SYSIDE_LICENSE_KEY != '' }}"
JOB = "authority"
GUARD_TEXT = "the checkout is not clean:"
API_START = "Start the isolated API and verify readiness"
OWN_PATHS = {
    "model-based-product-line-engineering/feature-models/**/*.sysml",
    "model-based-product-line-engineering/feature-configurations/**/*.sysml",
    "scripts/run_ple_authority.py",
    "tests/test_ple_authority_model.py",
    "tests/test_ple_authority_runner.py",
    "tests/test_ple_authority_workflow.py",
    ".github/workflows/privileged-ple-authority.yml",
}
#: The PLEML pin: a re-pin gets this licensed validation (the upstream release policy).
PIN_PATHS = {
    "model-based-product-line-engineering/libraries/pleml/**",
    "de4sdv/semantic/pleml_package.py",
    "scripts/check_pleml_package.py",
    "scripts/run_ple_qualification.py",
}
#: The committed receipts and what they bind (review R14): the referenced documents of the
#: bundle and the catalogues of the shadow checks, so that a change to either reruns the job.
BOUND_PATHS = {
    f"{runner.RECEIPTS_DIR}/**",
    "model-based-product-line-engineering/feature-models/*.yaml",
    *runner.REFERENCED_SOURCES,
}


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


def _named(name: str) -> tuple[int, dict[str, Any]]:
    [(index, step)] = [(i, s) for i, s in enumerate(_steps()) if s.get("name") == name]
    return index, step


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


def test_triggers_are_the_authority_paths_and_maintainer_dispatch() -> None:
    triggers = _workflow()[True]
    assert set(triggers) == {"pull_request", "workflow_dispatch"}
    paths = triggers["pull_request"]["paths"]
    assert len(paths) == len(set(paths)) and set(paths) == OWN_PATHS | PIN_PATHS | BOUND_PATHS
    for path in OWN_PATHS | PIN_PATHS | BOUND_PATHS:
        if path.endswith("/**"):
            assert (ROOT / path[:-3]).is_dir() or path == f"{runner.RECEIPTS_DIR}/**", path
        elif "/**/" in path:
            base, pattern = path.split("/**/")
            assert any((ROOT / base).rglob(pattern)), path
        elif "*" in path:
            assert sorted((ROOT / path).parent.glob(Path(path).name)), path
        else:
            assert (ROOT / path).is_file(), path
    catalogues = {family.catalogue.as_posix() for family in model_test.FAMILIES.values()}
    assert {p.relative_to(ROOT).as_posix() for p in (ROOT / "model-based-product-line-engineering/feature-models")
            .glob("*.yaml")} == catalogues, "the catalogues are exactly the three families'"
    # The runner reads the pin from the package record and its inputs from the qualification runner.
    assert {"de4sdv/semantic/pleml_package.py", f"{PROJECT}/sysand-lock.toml"} <= set(runner.EXECUTOR_INPUTS)
    # The job reads production documents but changes no production selector: none of its own,
    # pin or receipt paths is a trigger of the production validation.
    validation = set(_load(VALIDATION)[True]["pull_request"]["paths"])
    assert not ((OWN_PATHS | PIN_PATHS | {f"{runner.RECEIPTS_DIR}/**"}) & validation)
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


def test_the_executor_is_the_exact_head_and_the_only_checkout() -> None:
    steps = _steps()
    checkouts = [s for s in steps if str(s.get("uses", "")).startswith("actions/checkout@")]
    assert len(checkouts) == 1, "no frozen experiment: the library comes from the fenced Sysand project"
    [head] = checkouts
    assert head["name"] == "Checkout the executor commit"
    assert head["with"] == {"ref": "${{ github.event.pull_request.head.sha || inputs.ref }}",
                            "fetch-depth": 0, "persist-credentials": False}
    revision = next(s for s in steps if s.get("id") == "revision")
    assert revision["env"] == {"EXPECTED_HEAD": "${{ github.event.pull_request.head.sha }}"}
    assert "${{" not in revision["run"]
    assert "git rev-parse HEAD" in revision["run"] and '"$EXPECTED_HEAD"' in revision["run"]


def test_the_fenced_package_is_installed_and_byte_checked_before_any_step_reads_it() -> None:
    steps = _steps()
    index, step = _named("Install and byte-check the fenced PLEML package")
    assert f"(cd {PROJECT} && sysand sync)" in step["run"]
    assert ("python scripts/check_pleml_package.py --release-diff --from-index --verify-tag "
            '--out "$RUNNER_TEMP/ple-evidence/pleml-package.json"') in step["run"]
    readers = [i for i, s in enumerate(steps)
               if any(reader in (s.get("run") or "") for reader in ("tests/test_ple_", "syside check", RUNNER))]
    assert readers and min(readers) > index
    # The installed package is untracked and ignored, so the dirty-checkout guards never see it.
    import subprocess

    assert subprocess.run(["git", "check-ignore", "-q", LIBRARY], cwd=ROOT).returncode == 0
    assert runner.LIBRARY["label"] == LIBRARY and runner.LIBRARY_PATH == ROOT / LIBRARY


# -- the clean-checkout discipline of #375, applied with the merged helpers ----------------

_RUN_STEPS = [s["name"] for s in _steps() if s.get("run")]
_OUTPUTS = ("ple-evidence",)


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
        for token in argv:
            if any(output in token for output in _OUTPUTS):
                assert clean._outside_the_checkout(token), (name, token)


@pytest.mark.parametrize("name", _RUN_STEPS)
def test_no_heredoc_writes_through_a_checkout_relative_path(name) -> None:
    step = next(s for s in _steps() if s.get("name") == name)
    for body in clean.HEREDOC.findall(step["run"]):
        assert clean._checkout_relative_writes(body) == [], name


def test_only_the_api_service_runs_in_the_background_and_outside_the_checkout() -> None:
    started = [s for s in _steps() if clean._starts_a_background_process(s.get("run") or "")]
    assert [s["name"] for s in started] == [API_START]
    _index, step = _named(API_START)
    assert step["working-directory"].startswith("/tmp/")
    assert '> "$RUNNER_TEMP/ple-evidence/sysml-api.log" 2>&1 &' in step["run"]


def test_the_api_service_is_the_pinned_one_of_the_ingestion_on_java_11() -> None:
    _index, build = _step("SysML-v2-API-Services.git")
    ingestion = next(s for s in _load(INGESTION)["jobs"]["ingest-and-validate"]["steps"]
                     if "SysML-v2-API-Services.git" in (s.get("run") or ""))
    pin = re.search(r"checkout ([0-9a-f]{40})", ingestion["run"])[1]
    assert f"checkout {pin}" in build["run"]
    assert "sbt-launch-1.2.8.jar" in build["run"] and '"$JAVA_HOME_11_X64/bin/java"' in build["run"]
    _index, start = _named(API_START)
    assert 'JAVA_HOME="$JAVA_HOME_11_X64"' in start["run"]
    assert "http://127.0.0.1:9000/projects" in start["run"]
    [java] = [s for s in _steps() if str(s.get("uses", "")).startswith("actions/setup-java@")]
    assert java["with"]["java-version"].split() == ["11", "21"], "the Modeler CLI runs on the default, 21"
    services = _workflow()["jobs"][JOB]["services"]
    assert services["postgres"]["image"] == "postgres:16"


def test_the_guards_are_the_ingestion_guard_verbatim() -> None:
    reference = next(s for s in _load(INGESTION)["jobs"]["ingest-and-validate"]["steps"]
                     if s.get("name") == "Refuse a dirty checkout before the import")
    guards = [s for s in _steps() if GUARD_TEXT in (s.get("run") or "")]
    for guard in guards:
        assert guard["run"] == reference["run"], guard["name"]
        assert "continue-on-error" not in guard


@pytest.mark.parametrize("kind", [None, "nested experiment checkout", "service log", "modified tracked file"])
def test_a_dirty_checkout_guard_refuses_what_the_runner_would_refuse(tmp_path, kind) -> None:
    checkout = tmp_path / "checkout"
    clean._scratch_checkout(checkout)
    expected = clean._dirty(checkout, kind) if kind else None
    guard = next(s for s in _steps() if GUARD_TEXT in (s.get("run") or ""))
    result = clean._bash(guard["run"], checkout)
    if expected:
        assert result.returncode == 1 and expected in result.stderr, result.stderr
    else:
        assert result.returncode == 0, result.stderr


def test_dirty_checkout_refusals_surround_every_recording_step() -> None:
    steps = _steps()
    guards = [i for i, s in enumerate(steps) if GUARD_TEXT in (s.get("run") or "")]
    assert len(guards) == 4
    for index in guards:
        assert steps[index]["name"].startswith("Refuse a dirty checkout")
    tests_index, _ = _step("tests/test_ple_authority_model.py")
    check_index, _ = _step("syside check")
    runner_index, _ = _step(RUNNER)
    for recording in (tests_index, check_index, runner_index):
        assert recording - 1 in guards, steps[recording]["name"]
    assert runner_index + 1 in guards, "a guard runs after the runner"
    assert steps[runner_index + 1]["if"].startswith("always()")


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
    runner_index, runner_step = _step(RUNNER)
    assert value_steps == sorted([check_index, runner_index])
    assert set(check["env"]) == {"SYSIDE_LICENSE_KEY"}
    assert set(runner_step["env"]) == {"SYSIDE_LICENSE_KEY", "HEAD_SHA"}
    for step in _steps():
        run = step.get("run") or ""
        assert "git push" not in run and "gh pr merge" not in run and "deploy.py" not in run


def test_syside_check_covers_the_reviewed_roots_the_pinned_library_and_the_pleml_files() -> None:
    from scripts.validate_sysml import MODEL_PATHS

    _index, check = _step("syside check")
    # The default `bash -e` shell has no pipefail: without it, `tee` would mask a failed check.
    assert check["run"].lstrip().startswith("set -eo pipefail\n")
    command = " ".join(re.sub(r"\\\n\s*", " ", check["run"]).split()) + " "
    for root in MODEL_PATHS:
        assert f" {root.as_posix()} " in command, root
    assert f" {LIBRARY} " in command and "external/pleml" not in command
    for directory in ("model-based-product-line-engineering/feature-models",
                      "model-based-product-line-engineering/feature-configurations"):
        assert f" {directory} " in command, directory
    assert '"$RUNNER_TEMP/ple-evidence/syside-check.txt"' in command


def test_the_runner_command_parses_against_the_real_parser() -> None:
    _index, step = _step(RUNNER)
    assert step["env"]["HEAD_SHA"] == "${{ steps.revision.outputs.sha }}"
    command = re.sub(r"\\\n\s*", " ", step["run"]).strip()
    assert command.startswith(f"python {RUNNER} ")
    substituted = command.replace("$HEAD_SHA", "a" * 40).replace("$RUNNER_TEMP", "/tmp/runner-temp")
    args = runner.build_parser().parse_args(shlex.split(substituted)[2:])
    assert args.licensed is True and args.expected_executor == "a" * 40
    assert "--library" not in command, "the runner reads the library from the fenced package"
    assert args.api_url == "http://127.0.0.1:9000"
    assert args.out == Path("/tmp/runner-temp/ple-evidence/authority")
    _start_index, start = _named(API_START)
    assert "-Dplay.server.http.port=9000" in start["run"]
    assert _start_index < _index, "the API is ready before the runner"


def test_the_unlicensed_tests_are_the_authority_tests() -> None:
    _index, step = _step("tests/test_ple_authority_model.py")
    assert "env" not in step
    for test in ("tests/test_ple_authority_model.py", "tests/test_ple_authority_runner.py",
                 "tests/test_ple_authority_workflow.py"):
        assert test in step["run"] and (ROOT / test).is_file(), test


def test_the_artifact_is_named_by_head_and_run_and_retained_under_runner_temp() -> None:
    steps = _steps()
    [upload] = [s for s in steps if str(s.get("uses", "")).startswith("actions/upload-artifact@")]
    assert upload["if"].startswith("always()")
    assert upload["with"]["name"] == "ple-authority-${{ steps.revision.outputs.sha }}-${{ github.run_id }}"
    assert upload["with"]["path"] == "${{ runner.temp }}/ple-evidence/"
    assert upload["with"]["retention-days"] == 30
    assert steps[-1] is upload
    assert not any("download-artifact" in str(s.get("uses", "")) for s in steps)


def test_the_retired_scope_alignment_workflow_is_gone() -> None:
    assert not (ROOT / ".github/workflows/privileged-ple-scope-alignment.yml").exists()
