"""Tests of the runner-only guard of the CI scripts of the bench.

The ci_* scripts may change the host they run on (packages, ~/.bazelrc,
/usr/local, large build trees). They run on a disposable CI runner only:
without GITHUB_ACTIONS=true, and without --runner as the first argument,
each one refuses at once and changes nothing.
"""

import os
from pathlib import Path
import subprocess

import pytest

SCRIPTS = sorted((Path(__file__).resolve().parents[1] / "scripts").glob("ci_*.sh"))


def test_there_are_ci_scripts():
    assert len(SCRIPTS) >= 7


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_a_ci_script_refuses_to_run_outside_a_runner(script, tmp_path):
    env = {key: value for key, value in os.environ.items() if key != "GITHUB_ACTIONS"}
    env["HOME"] = str(tmp_path)
    completed = subprocess.run(["bash", str(script), str(tmp_path / "facts")], env=env, capture_output=True,
                               text=True, timeout=30, check=False)
    assert completed.returncode == 2
    assert "runs only on a CI runner" in completed.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_a_ci_script_names_the_runner_flag_in_its_usage(script):
    text = script.read_text(encoding="utf-8")
    assert f"# Usage: {script.name} [--runner] " in text
    assert 'if [ "${1:-}" = "--runner" ]; then' in text
