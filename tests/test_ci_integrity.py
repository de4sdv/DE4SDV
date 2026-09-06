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


def test_root_pytest_collection_is_scoped_to_project_tests() -> None:
    parser = ConfigParser()
    assert parser.read(PYTEST_CONFIG, encoding="utf-8") == [str(PYTEST_CONFIG)]
    pytest = parser["pytest"]
    assert pytest.get("testpaths", "").split() == ["tests"]
    assert "implementation" in pytest.get("norecursedirs", "").split()
    assert ".sysand" in pytest.get("norecursedirs", "").split()
