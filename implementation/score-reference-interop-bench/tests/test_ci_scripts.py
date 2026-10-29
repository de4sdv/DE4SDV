"""Tests of the runner-only guard of the CI scripts of the bench.

The ci_* scripts may change the host they run on (packages, ~/.bazelrc,
/usr/local, large build trees). They run on a disposable CI runner only:
without GITHUB_ACTIONS=true, and without --runner as the first argument,
each one refuses at once and changes nothing. The guard is one file,
scripts/runner_only.sh, that each script sources as its first command after
set; without that file a script refuses too, and so does a script read from
stdin, which has no path of its own to find the guard by.
"""

import os
from pathlib import Path
import shutil
import subprocess

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
SCRIPTS = sorted(SCRIPTS_DIR.glob("ci_*.sh"))
GUARD_LINE = 'source "$(dirname "${BASH_SOURCE[0]:?}")/runner_only.sh" || exit 2'


def _environment(**changes: str) -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key != "GITHUB_ACTIONS"}
    env.update(changes)
    return env


def _run_off_a_runner(script: Path, home: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script), str(home / "facts")], env=_environment(HOME=str(home)),
                          capture_output=True, text=True, timeout=30, check=False)


def test_there_are_ci_scripts():
    assert len(SCRIPTS) >= 7


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_a_ci_script_refuses_to_run_outside_a_runner(script, tmp_path):
    completed = _run_off_a_runner(script, tmp_path)
    assert completed.returncode == 2
    assert f"{script.name}: runs only on a CI runner" in completed.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_a_ci_script_without_the_guard_file_refuses_too(script, tmp_path):
    alone = tmp_path / "scripts" / script.name
    alone.parent.mkdir()
    shutil.copy(script, alone)
    home = tmp_path / "home"
    home.mkdir()
    assert _run_off_a_runner(alone, home).returncode == 2
    assert list(home.iterdir()) == []


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_a_ci_script_read_from_stdin_refuses_also_with_a_guard_file_in_the_working_directory(script, tmp_path):
    (tmp_path / "runner_only.sh").write_text("# planted: does nothing\n", encoding="utf-8")
    with script.open("rb") as stdin:
        completed = subprocess.run(["bash", "-s", str(tmp_path / "facts")], stdin=stdin, cwd=tmp_path,
                                   env=_environment(HOME=str(tmp_path)), capture_output=True, timeout=30, check=False)
    assert completed.returncode == 2, completed.stderr
    assert [path.name for path in tmp_path.iterdir()] == ["runner_only.sh"]


@pytest.mark.parametrize("script", SCRIPTS, ids=lambda path: path.name)
def test_a_ci_script_sources_the_guard_first_and_names_the_runner_flag_in_its_usage(script):
    text = script.read_text(encoding="utf-8")
    assert f"# Usage: {script.name} [--runner] " in text
    commands = [line for line in text.splitlines() if line.strip() and not line.startswith("#")]
    assert commands[0].startswith("set -"), commands[0]
    assert commands[1] == GUARD_LINE


@pytest.mark.parametrize(("changes", "arguments"), [({}, ["--runner", "a", "b"]), ({"GITHUB_ACTIONS": "true"}, ["a", "b"])])
def test_the_guard_hands_the_script_its_arguments_without_the_runner_flag(changes, arguments):
    command = f'source "{SCRIPTS_DIR / "runner_only.sh"}" || exit 9; echo "$#:$*"'
    completed = subprocess.run(["bash", "-c", command, "ci_example.sh", *arguments], env=_environment(**changes),
                               capture_output=True, text=True, timeout=30, check=False)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout == "2:a b\n"
