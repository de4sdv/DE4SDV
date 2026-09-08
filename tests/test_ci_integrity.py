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
