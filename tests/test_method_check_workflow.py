"""Method Check workflow wiring (static + argument spy; no network, no dispatch).

The method check exports the pull-request head with the pinned licensed
serializer in one job and evaluates every declared increment in a second job;
a third job reports a failed export. These tests pin: the trigger (the
privileged validation's path filters), the fork and author guard, the secret
scoping (the licence reaches exactly one step, the export; the jobs that run
the evaluation and the failure report reference no secret), the exact-revision
handoff between the jobs, the advisory exit policy, the artifact names, the
report of a failed export, and that every workflow command line parses against
the real script parser (the parser is spied; nothing executes).
"""

from __future__ import annotations

import argparse
import ast
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
#: Paths the method check adds to the privileged validation's filters: its own implementation, and
#: the modules and data files the evaluation reads.
OWN_PATHS = {
    ".github/workflows/method-check.yml",
    "scripts/method_check.py",
    "scripts/evaluate_increment.py",
    "scripts/export_sysml_api_baseline.py",
    "scripts/check_member_product_applications.py",
    "de4sdv/__init__.py",
    "de4sdv/semantic/**",
    "de4sdv/sysml_api/**",
}
LICENCE_VALUE = "${{ secrets.SYSIDE_LICENSE_KEY }}"
LICENCE_PRESENCE = "${{ secrets.SYSIDE_LICENSE_KEY != '' }}"
EXPORT_SCRIPT = "scripts/export_sysml_api_baseline.py"
CHECK_SCRIPT = "scripts/method_check.py"
#: The appliesToMemberProduct gate over the same export (#412 R3, D3): a job of its own, which a
#: refusal fails, beside the advisory evaluation.
GATE_SCRIPT = "scripts/check_member_product_applications.py"
GATE_JOB = "member-product-gate"
HEAD = "${{ needs.export.outputs.head-sha }}"
#: The job that reports a failed export (the evaluation job never runs then).
REPORT_JOB = "export-failure-report"
DIAGNOSTICS = "method-check-diagnostics/export-diagnostics.txt"
DIAGNOSTICS_VARIABLE = "DE4SDV_EXPORT_DIAGNOSTICS"
CREDENTIALS = ("SYSIDE_LICENSE_KEY", "GITHUB_TOKEN", "ACTIONS_RUNTIME_TOKEN", "ACTIONS_ID_TOKEN_REQUEST_TOKEN")


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
        if path.endswith("/**"):
            # A directory filter must cover at least one file, or it filters nothing.
            assert any(f.is_file() for f in ROOT.glob(path + "/*")), path
        else:
            assert (ROOT / path).is_file(), path


def _repository_imports(script: Path, seen: set[Path]) -> None:
    """Every repository module a script reaches through imports."""
    if script in seen or not script.is_file():
        return
    seen.add(script)
    for node in ast.walk(ast.parse(script.read_text(encoding="utf-8"))):
        names: list[str] = []
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names = [node.module] + [f"{node.module}.{alias.name}" for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level:
            package = script.parent.relative_to(ROOT).parts
            package = package[: len(package) - (node.level - 1)] if node.level > 1 else package
            base = ".".join((*package, node.module) if node.module else package)
            names = [base] + [f"{base}.{alias.name}" for alias in node.names]
        elif isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        for name in names:
            parts = name.split(".")
            # Importing a.b.c runs a/__init__.py and a/b/__init__.py before the module itself.
            parents = [ROOT.joinpath(*parts[:count], "__init__.py") for count in range(1, len(parts))]
            for candidate in (*parents, ROOT / (name.replace(".", "/") + ".py"),
                              ROOT / name.replace(".", "/") / "__init__.py"):
                _repository_imports(candidate, seen)


def _glob(pattern: str) -> re.Pattern[str]:
    """A workflow path filter as a regular expression (GitHub glob: ** spans directories, * does not)."""
    parts, index = [], 0
    while index < len(pattern):
        if pattern.startswith("**/", index):
            parts.append("(?:.*/)?")
            index += 3
        elif pattern.startswith("**", index):
            parts.append(".*")
            index += 2
        elif pattern[index] == "*":
            parts.append("[^/]*")
            index += 1
        else:
            parts.append(re.escape(pattern[index]))
            index += 1
    return re.compile("".join(parts) + r"\Z")


def _uncovered(paths, filters) -> list[str]:
    """The repository paths no pull_request path filter matches."""
    compiled = [_glob(f) for f in filters]
    return [path for path in paths if not any(pattern.match(path) for pattern in compiled)]


def test_every_module_the_check_runs_triggers_it() -> None:
    """A change to any repository module the Method Check imports must run it."""
    filters = _triggers(_workflow())["pull_request"]["paths"]
    seen: set[Path] = set()
    for script in (CHECK_SCRIPT, "scripts/evaluate_increment.py", GATE_SCRIPT):
        _repository_imports(ROOT / script, seen)
    modules = sorted(path.relative_to(ROOT).as_posix() for path in seen)
    assert any(module.startswith("de4sdv/semantic/") for module in modules)
    assert "de4sdv/__init__.py" in modules  # parent packages run on import too
    assert _uncovered(modules, filters) == []


def test_every_data_file_the_evaluation_reads_triggers_it() -> None:
    """The evaluation builds the trace-vocabulary contract from the files of TRACE_CONTRACT_INPUTS (the
    generated contract and the projection, profile and frozen-record files its class pins are checked
    against): a change to any of them must run the check. Python inputs are covered by the import walk
    above; this pins the others."""
    from de4sdv.semantic.model_contract import TRACE_CONTRACT_INPUTS, TRACE_CONTRACT_PATH

    data = [path for path in TRACE_CONTRACT_INPUTS if not path.endswith(".py")]
    assert TRACE_CONTRACT_PATH in data
    assert data and all((ROOT / path).is_file() for path in data)
    assert _uncovered(data, _triggers(_workflow())["pull_request"]["paths"]) == []


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
    # Besides the licence and the revision, only the (non-secret) path where a failed export records why.
    assert set(export["env"]) == {"SYSIDE_LICENSE_KEY", "HEAD_SHA", DIAGNOSTICS_VARIABLE}
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
    # After the export only uploads run: the export, or the diagnostics of a failed export.
    after = steps[export_index + 1:]
    assert [s.get("uses", "").split("@")[0] for s in after] == ["actions/upload-artifact"] * 2
    assert all("run" not in step for step in after)


def test_every_checkout_keeps_no_credentials() -> None:
    for name in ("export", "evaluate", GATE_JOB, REPORT_JOB):
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


def test_a_failed_export_leaves_its_diagnostics_for_the_report() -> None:
    # The export records why it failed (its own refusal text, Syside's model
    # diagnostics included; any other error by its type only) and the export
    # job uploads that file only on failure. The success path is unchanged.
    _index, export = _step_running("export", EXPORT_SCRIPT)
    # The workflow of a pull-request event comes from the merge commit, but the
    # export script from the head, which may predate --diagnostics. So the path
    # travels in the environment, which an older script ignores, and the
    # command line keeps the options every export script has.
    assert export["env"][DIAGNOSTICS_VARIABLE] == "${{ runner.temp }}/" + DIAGNOSTICS
    assert re.findall(r"--[a-z-]+", export["run"]) == ["--git-commit", "--output"]
    success, failure = _step_using("export", "actions/upload-artifact")
    assert success["if"] == "steps.licence.outputs.available == 'true'"
    assert success["with"]["name"] == "method-check-export-${{ steps.revision.outputs.sha }}"
    assert failure["if"] == "${{ failure() && steps.licence.outputs.available == 'true' }}"
    assert failure["with"]["name"] == "method-check-export-diagnostics-${{ steps.revision.outputs.sha }}"
    assert failure["with"]["path"] == "${{ runner.temp }}/method-check-diagnostics/"
    assert failure["with"]["if-no-files-found"] == "ignore"


def test_a_failed_export_is_reported_by_a_job_that_holds_no_secret() -> None:
    job = _job(REPORT_JOB)
    assert job["needs"] == "export"
    # Only after a licensed export that failed: never after a skipped,
    # cancelled or successful export (the evaluation reports those).
    assert job["if"] == "${{ failure() && needs.export.outputs.licensed == 'true' }}"
    text = yaml.safe_dump(job)
    assert "secrets." not in text and "github.token" not in text
    # It renders what the export recorded and evaluates nothing, so it runs the
    # workflow's own revision: that renderer knows --export-failed even when
    # the exported head predates it.
    checkout = _step_using(REPORT_JOB, "actions/checkout")[0]
    assert checkout["with"] == {"ref": "${{ github.sha }}", "persist-credentials": False}
    # The diagnostics artifact may be absent (the export job can fail before
    # the export runs), so it is matched by pattern, which tolerates no match.
    download = _step_using(REPORT_JOB, "actions/download-artifact")[0]["with"]
    assert download == {
        "pattern": f"method-check-export-diagnostics-{HEAD}",
        "path": "${{ runner.temp }}/method-check-diagnostics",
        "merge-multiple": True,
    }
    _index, step = _step_running(REPORT_JOB, CHECK_SCRIPT)
    assert step["env"] == {"HEAD_SHA": HEAD}
    guard = step["run"].split(f"python {CHECK_SCRIPT}")[0]
    for name in CREDENTIALS:
        assert name in guard, name
    assert "exit 1" in guard
    assert f'--export-failed "$RUNNER_TEMP/{DIAGNOSTICS}"' in step["run"]
    assert '--output-dir "$RUNNER_TEMP/method-check/result"' in step["run"]
    assert '--artifact "method-check-$HEAD_SHA"' in step["run"]
    assert '--summary "$GITHUB_STEP_SUMMARY"' in step["run"]
    # The same artifact name as an evaluation, so one download recipe serves both.
    upload = _step_using(REPORT_JOB, "actions/upload-artifact")
    assert len(upload) == 1
    assert upload[0]["if"] == "${{ !cancelled() }}"
    assert upload[0]["with"]["name"] == f"method-check-{HEAD}"
    assert upload[0]["with"]["path"] == "${{ runner.temp }}/method-check/result/"


def test_the_serializer_is_the_pinned_privileged_toolchain() -> None:
    from de4sdv.semantic.native_grounding_projection import read_syside_pin

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
    for job in ("export", "evaluate", GATE_JOB, REPORT_JOB):
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
    # The export once; the method check for an evaluation and for a failed export; the gate once.
    assert sorted(argv[1] for _name, argv in _commands()) == sorted(
        [EXPORT_SCRIPT, CHECK_SCRIPT, CHECK_SCRIPT, GATE_SCRIPT])


def test_the_member_product_gate_is_a_job_of_its_own_that_a_refusal_fails() -> None:
    """#412 R3 and D3: a job of its own derives appliesToMemberProduct over the exported head, so a
    refusal fails the gate and never the advisory evaluation. Like the evaluation, it runs on a
    fresh runner after a successful licensed export, on the exported revision. Its step holds no
    credential and reads the downloaded export of the exact revision. Its record is uploaded even
    after a refusal, and no step masks its exit code."""
    job = _job(GATE_JOB)
    assert job["name"] == "appliesToMemberProduct gate (fails on refusal)"
    assert job["needs"] == "export"
    assert job["if"] == "needs.export.outputs.licensed == 'true'"
    text = yaml.safe_dump(job)
    assert "secrets." not in text and "github.token" not in text
    checkout = _step_using(GATE_JOB, "actions/checkout")[0]
    assert checkout["with"]["ref"] == HEAD
    verify = next(s for s in _steps(GATE_JOB) if "git rev-parse HEAD" in (s.get("run") or ""))
    assert verify["env"] == {"HEAD_SHA": HEAD}
    download = _step_using(GATE_JOB, "actions/download-artifact")[0]["with"]
    assert download == {"name": f"method-check-export-{HEAD}", "path": "${{ runner.temp }}/method-check"}
    gate_index, gate = _step_running(GATE_JOB, GATE_SCRIPT)
    assert gate["env"] == {"HEAD_SHA": HEAD} and "if" not in gate
    guard = gate["run"].split(f"python {GATE_SCRIPT}")[0]
    for name in CREDENTIALS:
        assert name in guard, name
    assert "exit 1" in guard
    command = " ".join(re.sub(r"\\\n\s*", " ", gate["run"]).split())
    assert '--export "$RUNNER_TEMP/method-check/model-export.json"' in command
    assert '--revision "$HEAD_SHA"' in command
    assert '--output "$RUNNER_TEMP/member-product-gate/member-products.json"' in command
    assert '--summary "$GITHUB_STEP_SUMMARY"' in command
    [upload] = _step_using(GATE_JOB, "actions/upload-artifact")
    assert _steps(GATE_JOB).index(upload) > gate_index
    assert upload["if"] == "${{ !cancelled() }}"
    assert upload["with"]["name"] == f"member-product-gate-{HEAD}"
    assert upload["with"]["path"] == "${{ runner.temp }}/member-product-gate/"


def test_the_evaluation_stays_advisory_and_runs_no_gate() -> None:
    """The evaluate job keeps its one script, the method check; the gate is not a step of it."""
    assert not [s for s in _steps("evaluate") if GATE_SCRIPT in (s.get("run") or "")]
    assert _job("evaluate")["name"] == "Method check (advisory)"


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
