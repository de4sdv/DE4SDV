"""Performance instrumentation for the privileged full-model ingestion workflow.

Scope of this module:

- the generic monotonic stage-timing wrapper
  (``scripts/measure_ingestion_command.py``) used to instrument every shell
  stage of ``privileged-full-model-api-ingestion.yml``: success records,
  failure records, exit-status preservation, stdin-script shell semantics,
  and the guarantee that neither command arguments nor the environment leak
  into the JSONL;
- regression guards that the workflow's required stages still run their
  exact commands — two independent serializer transactions
  (``prepare_candidate_export.py``) and three import invocations
  (``import_sysml_api_baseline.py``) — now wrapped but unchanged, with the
  timing JSONL always uploaded next to the evidence;
- the corrected runtime expectation: measured end-to-end runs are
  multi-hour, so the old ``~35-60 min`` comment is gone while timeout and
  schedule semantics stay untouched.

Dependency-cache assessment (why there is no ``actions/cache`` here): the
Python pin set (``syside==0.10.3``, ``PyYAML==6.0.2``, ``pytest==8.4.2``,
``requirements-mcp.txt``) installs in seconds, so caching saves negligible
time; the sbt/Ivy build (~4 min) resolves transitive dependencies WITHOUT an
upstream lockfile (the pinned upstream pins sbt 1.2.8 but publishes no
dependency lock), so an exact-key cache cannot be proven safe against
mutable/unpinned artifacts and a stale cache would silently change the built
service. Fail-closed (fresh resolution) beats a speculative cache; no cache
is added until an exact, provably safe key exists.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "scripts" / "measure_ingestion_command.py"
WORKFLOW_PATH = (
    ROOT / ".github" / "workflows" / "privileged-full-model-api-ingestion.yml"
)
WORKFLOW_TEXT = WORKFLOW_PATH.read_text(encoding="utf-8")
WORKFLOW = yaml.safe_load(WORKFLOW_TEXT)
JOB = WORKFLOW["jobs"]["ingest-and-validate"]
TIMINGS_PATH = "/tmp/de4sdv-ingestion-timings.jsonl"

SERIALIZER_STEP_NAMES = (
    "Produce isolated committed-candidate export (transaction 1)",
    "Produce second independent serialization transaction (MC-14)",
)
IMPORT_STEP_NAMES = (
    "Import and validate exact API revision",
    "Import candidate transaction 1 into a distinct API project",
    "Import candidate transaction 2 into a second distinct API project",
)
REQUIRED_STEP_SIGNATURES = {
    "validate-exact-revision-checkout": 'case "$SHA" in',
    "install-sysand-and-model-deps": '"$HOME/.local/bin/sysand" sync',
    "install-syside-serializer": '"syside==0.10.3" "PyYAML==6.0.2" "pytest==8.4.2"',
    "export-reviewed-baseline": "python scripts/export_sysml_api_baseline.py",
    "build-api-service": "java -Xmx4g -jar /tmp/sbt-launch.jar stage",
    "start-api-service": (
        "/tmp/sysmlv2-api-services/target/universal/stage/bin/sysml-v2-api-services"
    ),
    "import-exact-api-revision": "python scripts/import_sysml_api_baseline.py",
    "semantic-queries": "python scripts/validate_full_model_semantic_queries.py",
    "product-line-scope-api": "python scripts/validate_product_line_scope_api.py",
    "semantic-mcp-tools": "python scripts/validate_semantic_mcp.py",
    "serialize-candidate-1": "--transaction-label candidate-1",
    "serialize-candidate-2": "--transaction-label candidate-2",
    "import-candidate-1": "--binding /tmp/de4sdv-candidate-binding.json",
    "import-candidate-2": "--binding /tmp/de4sdv-candidate-binding-2.json",
    "reimport-correspondence": "python scripts/verify_reimport_correspondence.py",
    "pilot-readback": "python scripts/verify_pilot_readback.py",
    "production-ingestion-tests": "tests/test_semantic_mcp.py -q",
    "o3-candidate-bundle": "run_o3_equivalence.py bundle",
    "o3-runtime-equivalence": "run_o3_equivalence.py compare",
    "trim-api-service-log": "tail -c 100000000",
}


def _run_steps() -> list[dict]:
    return [step for step in JOB["steps"] if "run" in step]


def _steps_by_name() -> dict[str, dict]:
    return {step["name"]: step for step in JOB["steps"] if "name" in step}


def _normalized(text: str) -> str:
    # Join shell line continuations before collapsing whitespace so exact
    # command comparisons work inside the heredoc-wrapped run blocks.
    return " ".join(text.replace("\\\n", " ").split())


def _label_of(step: dict) -> str:
    match = re.search(r"--label\s+(\S+)", step["run"])
    assert match, step["name"]
    return match.group(1)


def _wrapper_env(jsonl_path: Path | None) -> dict[str, str]:
    env = dict(os.environ)
    env.pop("DE4SDV_INGESTION_TIMINGS", None)
    if jsonl_path is not None:
        env["DE4SDV_INGESTION_TIMINGS"] = str(jsonl_path)
    return env


def _run_wrapper(
    args: list[str], *, env: dict[str, str], stdin: str | None = None
) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(WRAPPER), *args],
        env=env,
        input=stdin,
        capture_output=True,
        text=True,
        check=False,
    )


def _read_records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


# --------------------------------------------------------------------------
# Wrapper behaviour
# --------------------------------------------------------------------------


def test_wrapper_records_success_stage_with_exit_zero(tmp_path: Path) -> None:
    jsonl = tmp_path / "timings" / "stages.jsonl"
    completed = _run_wrapper(
        ["--label", "export-reviewed-baseline", "--", sys.executable, "-c", "print('stage-ok')"],
        env=_wrapper_env(jsonl),
    )

    assert completed.returncode == 0
    assert "stage-ok" in completed.stdout
    records = _read_records(jsonl)
    assert len(records) == 1
    record = records[0]
    assert record["stage"] == "export-reviewed-baseline"
    assert record["exit_code"] == 0
    assert record["signal"] is None
    assert record["duration_ns"] > 0
    assert record["duration_s"] > 0
    assert record["child_max_rss_kb_after"] >= record["child_max_rss_kb_before"]
    assert record["child_max_rss_kb_delta"] >= 0
    assert record["schema"].startswith("de4sdv.ingestion.")


def test_wrapper_preserves_failing_exit_and_appends_failure_record(tmp_path: Path) -> None:
    jsonl = tmp_path / "stages.jsonl"
    env = _wrapper_env(jsonl)
    _run_wrapper(
        ["--label", "ok-stage", "--", sys.executable, "-c", "print('ok')"],
        env=env,
    )
    failed = _run_wrapper(
        ["--label", "failing-stage", "--", sys.executable, "-c", "raise SystemExit(7)"],
        env=env,
    )

    assert failed.returncode == 7
    records = _read_records(jsonl)
    assert [record["stage"] for record in records] == ["ok-stage", "failing-stage"]
    assert [record["exit_code"] for record in records] == [0, 7]


def test_wrapper_reports_signal_termination_as_128_plus_signal(tmp_path: Path) -> None:
    jsonl = tmp_path / "stages.jsonl"
    completed = _run_wrapper(
        [
            "--label",
            "signal-stage",
            "--",
            sys.executable,
            "-c",
            "import os, signal; os.kill(os.getpid(), signal.SIGTERM)",
        ],
        env=_wrapper_env(jsonl),
    )

    assert completed.returncode == 143
    record = _read_records(jsonl)[0]
    assert record["exit_code"] == 143
    assert record["signal"] == 15


def test_wrapper_records_unspawnable_command_as_127(tmp_path: Path) -> None:
    jsonl = tmp_path / "stages.jsonl"
    completed = _run_wrapper(
        ["--label", "missing-stage", "--", "definitely-not-a-real-command-de4sdv"],
        env=_wrapper_env(jsonl),
    )

    assert completed.returncode == 127
    record = _read_records(jsonl)[0]
    assert record["exit_code"] == 127


def test_wrapper_never_emits_arguments_or_environment(tmp_path: Path) -> None:
    jsonl = tmp_path / "stages.jsonl"
    secret = "sekret-argument-value-8f3a"
    env_secret = "sekret-env-value-1c9d"
    env = _wrapper_env(jsonl)
    env["SYSIDE_LICENSE_KEY"] = env_secret
    completed = _run_wrapper(
        [
            "--label",
            "leak-check-stage",
            "--",
            sys.executable,
            "-c",
            "pass",
            secret,
        ],
        env=env,
    )

    assert completed.returncode == 0
    payload = jsonl.read_text(encoding="utf-8")
    assert secret not in payload
    assert env_secret not in payload
    record = _read_records(jsonl)[0]
    assert "command" not in record
    assert "argv" not in record
    assert set(record) == {
        "schema",
        "stage",
        "started_at",
        "finished_at",
        "duration_ns",
        "duration_s",
        "exit_code",
        "signal",
        "child_max_rss_kb_before",
        "child_max_rss_kb_after",
        "child_max_rss_kb_delta",
    }


def test_wrapper_stdin_script_mode_runs_and_records(tmp_path: Path) -> None:
    jsonl = tmp_path / "stages.jsonl"
    env = _wrapper_env(jsonl)
    completed = _run_wrapper(
        ["--label", "build-api-service", "--stdin-script"],
        env=env,
        stdin="echo stdin-mode-ok\nexit 0\n",
    )
    assert completed.returncode == 0
    assert "stdin-mode-ok" in completed.stdout

    failed = _run_wrapper(
        ["--label", "trim-api-service-log", "--stdin-script"],
        env=env,
        stdin="exit 9\n",
    )
    assert failed.returncode == 9
    records = _read_records(jsonl)
    assert [record["exit_code"] for record in records] == [0, 9]


def test_wrapper_stdin_shell_preserves_actions_failure_semantics(tmp_path: Path) -> None:
    jsonl = tmp_path / "stages.jsonl"
    env = _wrapper_env(jsonl)
    # `-e`: a failing command aborts the script before `echo after` runs.
    aborted = _run_wrapper(
        ["--label", "errored", "--stdin-script"],
        env=env,
        stdin="false\necho after\n",
    )
    assert aborted.returncode == 1
    assert "after" not in aborted.stdout
    # `-o pipefail`: a failing pipeline fails the script.
    piped = _run_wrapper(
        ["--label", "piped", "--stdin-script"],
        env=env,
        stdin="false | true\nexit 0\n",
    )
    assert piped.returncode == 1


def test_wrapper_shell_commands_cannot_consume_script_input(tmp_path: Path) -> None:
    completed = _run_wrapper(
        ["--label", "stdin-isolation", "--stdin-script"],
        env=_wrapper_env(tmp_path / "timings.jsonl"),
        stdin="read -r unused || true\nprintf 'still-executed\\n'\n",
    )
    assert completed.returncode == 0
    assert "still-executed" in completed.stdout


def test_wrapper_without_jsonl_env_still_runs_command(tmp_path: Path) -> None:
    completed = _run_wrapper(
        ["--label", "unmeasured-stage", "--", sys.executable, "-c", "print('ran')"],
        env=_wrapper_env(None),
    )

    assert completed.returncode == 0
    assert "ran" in completed.stdout
    assert "ran unmeasured" in completed.stderr


# --------------------------------------------------------------------------
# Workflow wiring: every shell stage measured, evidence preserved
# --------------------------------------------------------------------------


def test_every_shell_stage_is_measured_with_a_unique_label() -> None:
    labels: list[str] = []
    for step in _run_steps():
        run = step["run"]
        assert "measure_ingestion_command.py" in run, step["name"]
        assert "--stdin-script" in run, step["name"]
        labels.append(_label_of(step))
    assert len(labels) == len(_run_steps())
    assert len(set(labels)) == len(labels)
    assert set(labels) == set(REQUIRED_STEP_SIGNATURES)


def test_required_stages_still_run_their_exact_commands() -> None:
    by_label = {_label_of(step): step for step in _run_steps()}
    assert set(by_label) == set(REQUIRED_STEP_SIGNATURES)
    for label, signature in REQUIRED_STEP_SIGNATURES.items():
        assert signature in by_label[label]["run"], label


def test_two_serializer_transactions_preserved_exactly() -> None:
    assert WORKFLOW_TEXT.count("prepare_candidate_export.py") == 2
    steps = _steps_by_name()
    first = _normalized(steps[SERIALIZER_STEP_NAMES[0]]["run"])
    second = _normalized(steps[SERIALIZER_STEP_NAMES[1]]["run"])
    assert _normalized(
        'python scripts/prepare_candidate_export.py '
        '--repository "$GITHUB_WORKSPACE" '
        '--git-commit "$(git rev-parse HEAD)" '
        "--worktree /tmp/de4sdv-candidate-checkout "
        "--output /tmp/de4sdv-candidate-export.json "
        "--identity /tmp/de4sdv-candidate-export-identity.json "
        "--transaction-label candidate-1 "
        "--baseline-export /tmp/de4sdv-full-model-export.json"
    ) in first
    assert _normalized(
        'python scripts/prepare_candidate_export.py '
        '--repository "$GITHUB_WORKSPACE" '
        '--git-commit "$(git rev-parse HEAD)" '
        "--worktree /tmp/de4sdv-candidate-checkout "
        "--output /tmp/de4sdv-candidate-export-2.json "
        "--identity /tmp/de4sdv-candidate-export-identity-2.json "
        "--transaction-label candidate-2 "
        "--reuse-checkout "
        "--sync-deps=false"
    ) in second


def test_three_import_invocations_preserved_exactly() -> None:
    assert WORKFLOW_TEXT.count("import_sysml_api_baseline.py") == 3
    steps = _steps_by_name()
    for name, expected in zip(
        IMPORT_STEP_NAMES,
        (
            _normalized(
                "python scripts/import_sysml_api_baseline.py "
                "--api-url http://127.0.0.1:9000 "
                "--export /tmp/de4sdv-full-model-export.json "
                "--binding /tmp/de4sdv-full-model-binding.json "
                "--report /tmp/de4sdv-full-model-semantic-validation.json"
            ),
            _normalized(
                "python scripts/import_sysml_api_baseline.py "
                "--api-url http://127.0.0.1:9000 "
                "--export /tmp/de4sdv-candidate-export.json "
                "--binding /tmp/de4sdv-candidate-binding.json "
                "--report /tmp/de4sdv-candidate-semantic-validation.json "
                "--candidate"
            ),
            _normalized(
                "python scripts/import_sysml_api_baseline.py "
                "--api-url http://127.0.0.1:9000 "
                "--export /tmp/de4sdv-candidate-export-2.json "
                "--binding /tmp/de4sdv-candidate-binding-2.json "
                "--report /tmp/de4sdv-candidate-semantic-validation-2.json "
                "--candidate"
            ),
        ),
    ):
        assert expected in _normalized(steps[name]["run"]), name


def test_timings_env_points_at_uploaded_artifact_path() -> None:
    assert JOB["env"]["DE4SDV_INGESTION_TIMINGS"] == TIMINGS_PATH
    upload = next(
        step
        for step in JOB["steps"]
        if step.get("uses", "").startswith("actions/upload-artifact@")
    )
    assert upload["if"] == "always()"
    assert TIMINGS_PATH in upload["with"]["path"]
    assert upload["with"]["name"] == "full-model-api-ingestion-${{ github.sha }}"


def test_trim_stage_still_runs_on_always() -> None:
    trim = _steps_by_name()["Trim API service log for upload"]
    assert trim["if"] == "always()"


def test_every_measured_run_block_is_valid_bash() -> None:
    if shutil.which("bash") is None:  # pragma: no cover - bash is present in CI
        pytest.skip("bash not available")
    for step in _run_steps():
        script = re.sub(r"\$\{\{[^}]*\}\}", "EXPR", step["run"])
        checked = subprocess.run(
            ["bash", "--noprofile", "--norc", "-n"],
            input=script,
            capture_output=True,
            text=True,
            check=False,
        )
        assert checked.returncode == 0, f"{step['name']}: {checked.stderr}"


# --------------------------------------------------------------------------
# Assessment guards: no speculative caches, corrected runtime comment
# --------------------------------------------------------------------------


def test_no_speculative_dependency_cache() -> None:
    # Measured evidence (module docstring): Python pins install in seconds and
    # the sbt/Ivy build has no upstream lockfile, so no exact safe cache key
    # exists. A cache must not be added without a provably exact key (the
    # assessment comment above the build step documents this; only its
    # mention is allowed — no cache step may exist).
    assert "uses: actions/cache" not in WORKFLOW_TEXT
    assert "restore-keys" not in WORKFLOW_TEXT


def test_runtime_comment_corrected_without_semantics_changes() -> None:
    assert "35-60" not in WORKFLOW_TEXT
    assert "timeout-minutes: 360" in WORKFLOW_TEXT
    assert 'cron: "30 2 * * *"' in WORKFLOW_TEXT
    trigger_block = WORKFLOW_TEXT.split("on:", 1)[1].split("permissions:", 1)[0]
    assert "pull_request" not in trigger_block
    assert "never per-PR" in WORKFLOW_TEXT
