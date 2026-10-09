"""Method Check workflow wiring (static + argument spy; no network, no dispatch).

The method check exports the pull-request head with the pinned licensed
serializer in one job and evaluates every declared increment in a second job.
These tests pin: the trigger (the privileged validation's path filters), the
fork and author guard, the secret scoping (the licence reaches exactly one
step, the export; the job that runs the evaluation references no secret), the
exact-revision handoff between the jobs, the advisory exit policy, the
artifact names, and that every workflow command line parses against the real
script parser (the parser is spied; nothing executes).
"""

from __future__ import annotations

import argparse
import importlib
import re
import shlex
import sys
from pathlib import Path
from typing import Any, Iterator

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/method-check.yml"
VALIDATION = ROOT / ".github/workflows/privileged-syside-validation.yml"
INGESTION = ROOT / ".github/workflows/privileged-full-model-api-ingestion.yml"
REV = "a" * 40
#: Paths the method check adds to the privileged validation's filters: its own implementation.
OWN_PATHS = {
    ".github/workflows/method-check.yml",
    "scripts/method_check.py",
    "scripts/evaluate_increment.py",
    "scripts/export_sysml_api_baseline.py",
    "de4sdv/semantic/increment_discovery.py",
}
LICENCE_VALUE = "${{ secrets.SYSIDE_LICENSE_KEY }}"
LICENCE_PRESENCE = "${{ secrets.SYSIDE_LICENSE_KEY != '' }}"
EXPORT_SCRIPT = "scripts/export_sysml_api_baseline.py"
CHECK_SCRIPT = "scripts/method_check.py"
HEAD = "${{ needs.export.outputs.head-sha }}"


def _load(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _workflow() -> dict[str, Any]:
    return _load(WORKFLOW)


def _triggers(workflow: dict[str, Any]) -> dict[str, Any]:
    return workflow[True]  # YAML 1.1: on -> True


def _job(name: str) -> dict[str, Any]:
    return _workflow()["jobs"][name]


def _steps(job: str) -> list[dict[str, Any]]:
    return _job(job)["steps"]


def _step_running(job: str, needle: str) -> tuple[int, dict[str, Any]]:
    matches = [(i, s) for i, s in enumerate(_steps(job)) if needle in (s.get("run") or "")]
    assert len(matches) == 1, needle
    return matches[0]


def _step_using(job: str, action: str) -> list[dict[str, Any]]:
    return [s for s in _steps(job) if str(s.get("uses", "")).startswith(action)]


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


# -- trigger and guards -------------------------------------------------------------


def test_triggers_are_pull_requests_and_maintainer_dispatch_only() -> None:
    assert set(_triggers(_workflow())) == {"pull_request", "workflow_dispatch"}


def test_pull_requests_reuse_the_privileged_validation_path_filters() -> None:
    validation = set(_triggers(_load(VALIDATION))["pull_request"]["paths"])
    method = _triggers(_workflow())["pull_request"]["paths"]
    assert len(method) == len(set(method))
    assert validation <= set(method)
    assert set(method) - validation == OWN_PATHS
    for path in OWN_PATHS:
        assert (ROOT / path).is_file(), path


def test_the_export_job_keeps_the_privileged_validation_guard() -> None:
    # Fork pull requests and authors outside the allowlist never reach the
    # licence: the same condition as the licensed validation job.
    validation = _load(VALIDATION)["jobs"]["syside-validation"]["if"]
    assert _normalized(_job("export")["if"]) == _normalized(validation)
    assert "github.event.pull_request.head.repo.full_name == github.repository" in validation


def test_the_evaluation_runs_only_after_a_successful_licensed_export() -> None:
    job = _job("evaluate")
    assert job["needs"] == "export"
    # No status function: the implicit success() keeps a failed export from evaluating.
    assert job["if"] == "needs.export.outputs.licensed == 'true'"
    assert _job("export")["outputs"]["licensed"] == "${{ steps.licence.outputs.available }}"


def test_permissions_are_read_only_and_never_widened_by_a_job() -> None:
    workflow = _workflow()
    assert workflow["permissions"] == {"contents": "read"}
    for name, job in workflow["jobs"].items():
        assert "permissions" not in job, name


def test_superseded_runs_are_cancelled_and_jobs_are_time_bounded() -> None:
    workflow = _workflow()
    assert "github.event.pull_request.number" in workflow["concurrency"]["group"]
    assert workflow["concurrency"]["cancel-in-progress"] is True
    for name, job in workflow["jobs"].items():
        assert 0 < job["timeout-minutes"] <= 20, name


# -- secret scoping --------------------------------------------------------------------


def test_the_licence_reaches_exactly_one_step_the_export() -> None:
    workflow = _workflow()
    hits = [(path, text) for path, text in _strings(workflow) if "secrets." in text.lower()]
    for path, text in hits:
        # Only ever a step-level environment value of the export job.
        assert path[:3] == ("jobs", "export", "steps") and path[4] == "env" and len(path) == 6, path
        assert text in {LICENCE_VALUE, LICENCE_PRESENCE}, text
    value = [path for path, text in hits if text == LICENCE_VALUE]
    presence = [path for path, text in hits if text == LICENCE_PRESENCE]
    assert len(value) == 1 and len(presence) == 1
    steps = _steps("export")
    export_index, export = _step_running("export", EXPORT_SCRIPT)
    assert value[0][3] == export_index
    # The step that holds the licence runs the export command and nothing else.
    commands = [line.strip() for line in re.sub(r"\\\n\s*", " ", export["run"]).splitlines() if line.strip()]
    assert len(commands) == 1 and commands[0].startswith(f"python {EXPORT_SCRIPT} ")
    assert set(export["env"]) == {"SYSIDE_LICENSE_KEY", "HEAD_SHA"}
    # The presence check sees a boolean, never the value, and runs no repository code.
    licence_step = steps[presence[0][3]]
    assert licence_step["id"] == "licence"
    assert "python" not in licence_step["run"] and "scripts/" not in licence_step["run"]
    assert "env" not in workflow
    for name, job in workflow["jobs"].items():
        assert "env" not in job, name


def test_the_job_that_runs_the_evaluation_references_no_secret() -> None:
    job = _job("evaluate")
    text = yaml.safe_dump(job)
    assert "secrets." not in text and "github.token" not in text
    for step in job["steps"]:
        for value in [*(step.get("env") or {}).values(), *(step.get("with") or {}).values()]:
            assert "secrets." not in str(value) and "token" not in str(value).lower(), step.get("name")
    _index, step = _step_running("evaluate", CHECK_SCRIPT)
    assert step["env"] == {"HEAD_SHA": HEAD}
    # The step proves at run time that its environment holds no credential.
    guard = step["run"].split(f"python {CHECK_SCRIPT}")[0]
    for name in ("SYSIDE_LICENSE_KEY", "GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN"):
        assert name in guard, name
    assert "exit 1" in guard


def test_no_repository_code_runs_in_the_export_job_besides_the_export() -> None:
    export_index, _export = _step_running("export", EXPORT_SCRIPT)
    steps = _steps("export")
    for step in steps[:export_index]:
        run = step.get("run") or ""
        assert not re.search(r"scripts/|tools/|de4sdv/|python3? -c|\./", run), step.get("name")
        assert re.sub(r"python -m pip install[^\n]*", "", run).count("python") == 0, step.get("name")
    after = steps[export_index + 1:]
    assert [s.get("uses", "").split("@")[0] for s in after] == ["actions/upload-artifact"]


def test_every_checkout_keeps_no_credentials() -> None:
    for name in ("export", "evaluate"):
        checkouts = _step_using(name, "actions/checkout")
        assert len(checkouts) == 1, name
        assert checkouts[0]["with"]["persist-credentials"] is False, name


# -- exact revision ---------------------------------------------------------------------


def test_the_export_is_of_the_exact_pull_request_head() -> None:
    checkout = _step_using("export", "actions/checkout")[0]
    assert checkout["with"]["ref"] == "${{ github.event.pull_request.head.sha || inputs.ref }}"
    revision = next(s for s in _steps("export") if s.get("id") == "revision")
    # The expected head reaches the script through the environment, never interpolated.
    assert revision["env"] == {"EXPECTED_HEAD": "${{ github.event.pull_request.head.sha }}"}
    assert "${{" not in revision["run"]
    assert 'git rev-parse HEAD' in revision["run"] and '"$EXPECTED_HEAD"' in revision["run"]
    _index, export = _step_running("export", EXPORT_SCRIPT)
    assert export["env"]["HEAD_SHA"] == "${{ steps.revision.outputs.sha }}"
    assert '--git-commit "$HEAD_SHA"' in export["run"]
    assert _job("export")["outputs"]["head-sha"] == "${{ steps.revision.outputs.sha }}"


def test_the_evaluation_reads_the_exported_revision() -> None:
    checkout = _step_using("evaluate", "actions/checkout")[0]
    assert checkout["with"]["ref"] == HEAD
    verify = next(s for s in _steps("evaluate") if "git rev-parse HEAD" in (s.get("run") or ""))
    assert verify["env"] == {"HEAD_SHA": HEAD}
    upload = _step_using("export", "actions/upload-artifact")[0]["with"]
    download = _step_using("evaluate", "actions/download-artifact")[0]["with"]
    assert upload["name"] == "method-check-export-${{ steps.revision.outputs.sha }}"
    assert download["name"] == f"method-check-export-{HEAD}"
    assert upload["path"] == "${{ runner.temp }}/method-check/model-export.json"
    assert download["path"] == "${{ runner.temp }}/method-check"
    _index, step = _step_running("evaluate", CHECK_SCRIPT)
    assert '--export "$RUNNER_TEMP/method-check/model-export.json"' in step["run"]
    assert '--revision "$HEAD_SHA"' in step["run"]


# -- advisory policy and artifact ----------------------------------------------------------


def test_gaps_never_fail_the_job_but_technical_errors_do() -> None:
    # The script exits 1 only on a technical error (tests/test_method_check.py);
    # the workflow neither masks that exit nor turns gaps into one.
    for name, job in _workflow()["jobs"].items():
        assert "continue-on-error" not in job, name
        for step in job["steps"]:
            assert "continue-on-error" not in step, step.get("name")
            run = step.get("run") or ""
            assert "|| true" not in run and "set +e" not in run, step.get("name")


def test_the_result_is_uploaded_with_the_head_sha_even_after_a_technical_error() -> None:
    upload = [s for s in _step_using("evaluate", "actions/upload-artifact")]
    assert len(upload) == 1
    assert upload[0]["if"] == "${{ !cancelled() }}"
    assert upload[0]["with"]["name"] == f"method-check-{HEAD}"
    assert upload[0]["with"]["path"] == "${{ runner.temp }}/method-check/result/"
    _index, step = _step_running("evaluate", CHECK_SCRIPT)
    assert '--output-dir "$RUNNER_TEMP/method-check/result"' in step["run"]
    assert '--artifact "method-check-$HEAD_SHA"' in step["run"]
    assert '--summary "$GITHUB_STEP_SUMMARY"' in step["run"]


def test_the_serializer_is_the_pinned_privileged_toolchain() -> None:
    from de4sdv.semantic.projection_o2p import read_syside_pin

    pin = read_syside_pin(ROOT)  # SYSIDE_VERSION of the licensed validation
    install = next(s for s in _steps("export") if "pip install" in (s.get("run") or ""))
    assert f'"syside=={pin}"' in install["run"]
    assert f'"syside=={pin}"' in INGESTION.read_text(encoding="utf-8")
    assert "sysand==0.1.0" in install["run"] and "sysand==0.1.0" in VALIDATION.read_text(encoding="utf-8")
    assert "sysand sync" in install["run"]
    assert f"python {EXPORT_SCRIPT}" in INGESTION.read_text(encoding="utf-8")


# -- command lines parse with the real parsers (argument spy) -------------------------------


def _commands() -> list[tuple[str, list[str]]]:
    out = []
    for job in ("export", "evaluate"):
        for step in _steps(job):
            joined = re.sub(r"\\\n\s*", " ", step.get("run") or "")
            for line in joined.splitlines():
                line = line.strip()
                if line.startswith("python scripts/"):
                    line = line.replace('"$HEAD_SHA"', REV).replace("$HEAD_SHA", REV)
                    line = line.replace("$RUNNER_TEMP", "/tmp/runner").replace("$GITHUB_STEP_SUMMARY", "/tmp/summary")
                    out.append((step["name"], shlex.split(line)))
    return out


class _Parsed(Exception):
    pass


def test_both_scripts_appear_on_the_command_lines() -> None:
    assert sorted(argv[1] for _name, argv in _commands()) == [EXPORT_SCRIPT, CHECK_SCRIPT]


@pytest.mark.parametrize("name, argv", _commands(), ids=[c[0] for c in _commands()])
def test_workflow_command_lines_parse_with_the_real_parsers(monkeypatch, name, argv) -> None:
    module = importlib.import_module("scripts." + Path(argv[1]).stem)
    captured = {}
    real = argparse.ArgumentParser.parse_args

    def spy(self, args=None, namespace=None):
        captured["namespace"] = real(self, args, namespace)
        raise _Parsed

    monkeypatch.setattr(argparse.ArgumentParser, "parse_args", spy)
    monkeypatch.setattr(sys, "argv", argv[1:])
    with pytest.raises(_Parsed):
        if argv[1] == CHECK_SCRIPT:
            module.main(argv[2:])
        else:
            module.main()
    namespace = vars(captured["namespace"])
    assert REV in (namespace.get("git_commit"), namespace.get("revision"))
