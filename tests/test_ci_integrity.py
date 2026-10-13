from configparser import ConfigParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CI = ROOT / ".github" / "workflows" / "ci.yml"
PYTEST_CONFIG = ROOT / "pytest.ini"


def test_required_ci_runs_complete_repository_test_suite() -> None:
    workflow = CI.read_text(encoding="utf-8")
    assert "python -m pytest tests -q" in workflow
    assert "python -m unittest discover -s tests" not in workflow
    assert "pytest tests/test_semantic_mcp.py" not in workflow


def _ci() -> dict:
    import yaml

    return yaml.safe_load(CI.read_text(encoding="utf-8"))


def test_ci_runs_for_pull_requests_and_pushes_to_main() -> None:
    triggers = _ci()[True]  # YAML 1.1: on -> True
    assert set(triggers) == {"pull_request", "push"}
    assert triggers["push"] == {"branches": ["main"]}


def test_a_newer_push_cancels_the_superseded_pull_request_run() -> None:
    """One pull request piled up four full runs of about 16 minutes (#353)."""
    concurrency = _ci()["concurrency"]
    # A pull request's runs share one group; a newer run cancels the older one.
    assert concurrency["cancel-in-progress"] == "${{ github.event_name == 'pull_request' }}"
    assert concurrency["group"].startswith("ci-${{ github.event_name }}-")


def test_a_push_to_main_is_never_cancelled() -> None:
    # cancel-in-progress is false for a push, and a group that two pushes
    # shared would still cancel a queued run, so every push run has its own
    # group: its run id (a pull request has a number, a push has none).
    concurrency = _ci()["concurrency"]
    assert concurrency["group"] == (
        "ci-${{ github.event_name }}-${{ github.event.pull_request.number || github.run_id }}"
    )
    for name, job in _ci()["jobs"].items():
        assert "concurrency" not in job, name


def test_ci_runs_bench_unit_contract_suites() -> None:
    """Implementation benches are not in the root suite; CI must run them.

    The benches use same-named bare imports, so they run through the
    isolated per-bench runner instead of a single pytest invocation.
    """
    workflow = CI.read_text(encoding="utf-8")
    assert "python tools/run_bench_unit_tests.py" in workflow


def test_root_pytest_collection_is_scoped_to_project_tests() -> None:
    parser = ConfigParser()
    assert parser.read(PYTEST_CONFIG, encoding="utf-8") == [str(PYTEST_CONFIG)]
    pytest = parser["pytest"]
    assert pytest.get("testpaths", "").split() == ["tests"]
    assert "implementation" in pytest.get("norecursedirs", "").split()
    assert ".sysand" in pytest.get("norecursedirs", "").split()


def test_bench_runner_fails_closed_on_git_inventory_failure(tmp_path) -> None:
    """A failed git inventory must fail the bench runner, not pass vacuously."""
    import importlib.util
    import subprocess
    import sys
    from unittest import mock

    tool = ROOT / "tools" / "run_bench_unit_tests.py"
    spec = importlib.util.spec_from_file_location("run_bench_unit_tests", tool)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    failing = subprocess.CompletedProcess(
        ["git"], 128, "", "fatal: inventory failed"
    )
    with mock.patch.object(
        module.subprocess, "run", return_value=failing
    ), mock.patch.object(sys, "argv", ["run_bench_unit_tests.py"]):
        assert module.main() == 1
