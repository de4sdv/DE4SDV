"""The runner disk report of the privileged ingestion (scripts/report_runner_disk.py).

One ``::notice`` annotation per call. When release run 41718067304 died of a
full disk, the job kept GitHub's annotation of the crash and lost its job log;
run 41736484152 showed the notices once the job completed. Whether they outlive
a runner that dies is untested. The report is diagnostic: it exits 0 whatever
it cannot measure and writes nothing into the checkout the dirty-checkout
guards read.
"""
from __future__ import annotations

import ast
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/report_runner_disk.py"
NOTICE = re.compile(r"^::notice title=Runner disk::(?P<message>.*)$")


def _run(tmp_path, *args, path_dirs=(), cwd=None):
    """Run the report with PATH holding only ``path_dirs`` (no host docker leaks in)."""
    path = os.pathsep.join(map(str, path_dirs)) or str(tmp_path / "empty-path")
    env = {**os.environ, "PATH": path}
    result = subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd or tmp_path, env=env,
                            capture_output=True, text=True)
    lines = result.stdout.splitlines()
    assert result.returncode == 0, result.stderr
    assert len(lines) == 1 and NOTICE.match(lines[0]), result.stdout
    return NOTICE.match(lines[0])["message"]


def _fake_docker(tmp_path, body):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    docker = bin_dir / "docker"
    docker.write_text("#!/bin/sh\n" + body + "\n", encoding="utf-8")
    docker.chmod(0o755)
    return bin_dir


def test_one_notice_with_free_space_log_exports_and_database(tmp_path):
    (tmp_path / "sysml-api.log").write_bytes(b"x" * 3 * 1024 ** 2)
    (tmp_path / "de4sdv-a.json").write_bytes(b"x" * 1024 ** 2)
    (tmp_path / "de4sdv-b.json").write_bytes(b"x" * 1024 ** 2)
    calls = tmp_path / "docker.calls"
    bin_dir = _fake_docker(tmp_path, f'printf "%s\\n" "$*" > "{calls}"; echo " 2147483648"')
    glob = str(tmp_path / "de4sdv-*.json")
    message = _run(tmp_path, "--label", "after the import", "--path", str(tmp_path),
                   "--api-log", str(tmp_path / "sysml-api.log"), "--exports", glob,
                   "--postgres-container", "c0ffee", path_dirs=[bin_dir])
    total = shutil.disk_usage(tmp_path).total / 1024 ** 3
    assert re.fullmatch(
        rf"after the import: \d+\.\d GiB free of {total:.1f} GiB on the filesystem of "
        rf"{re.escape(str(tmp_path))}; API service log 3 MiB; 2 files matching "
        rf"{re.escape(glob)}: 2 MiB; database 2048 MiB", message), message
    assert calls.read_text(encoding="utf-8").split() == [
        "exec", "c0ffee", "psql", "-U", "postgres", "-d", "sysml2", "-tAc",
        "select", "pg_database_size('sysml2')"]


@pytest.mark.parametrize("container, docker", [
    ("", None),                              # no service container id
    ("c0ffee", None),                        # no docker on PATH
    ("c0ffee", "echo 123; exit 3"),          # docker fails (what it printed is not a size)
    ("c0ffee", "echo 'not a size'"),         # docker answers without a size
], ids=["no-container", "no-docker", "docker-fails", "no-size"])
def test_what_cannot_be_measured_is_named_and_the_report_still_exits_0(tmp_path, container, docker):
    missing = tmp_path / "no-such-dir"
    message = _run(tmp_path, "--label", "at the end of the run", "--path", str(missing),
                   "--api-log", str(missing / "sysml-api.log"),
                   "--exports", str(missing / "de4sdv-*.json"), "--postgres-container", container,
                   path_dirs=[_fake_docker(tmp_path, docker)] if docker else [])
    assert message == (f"at the end of the run: free space on the filesystem of {missing} unknown; "
                       f"API service log absent; 0 files matching {missing / 'de4sdv-*.json'}: 0 MiB; "
                       "database unknown"), message


def test_an_unexpected_error_still_ends_in_one_notice_and_exit_0(monkeypatch, capsys):
    import importlib

    module = importlib.import_module("scripts.report_runner_disk")

    def broken(*_args):
        raise RuntimeError("boom")

    monkeypatch.setattr(module, "report", broken)
    assert module.main(["--label", "after the import"]) == 0
    assert capsys.readouterr().out == (
        "::notice title=Runner disk::after the import: disk report failed (RuntimeError: boom)\n")


def test_annotation_data_is_escaped(tmp_path):
    message = _run(tmp_path, "--label", "50% done\nnext line", "--path", str(tmp_path))
    assert message.startswith("50%25 done%0Anext line: "), message


def test_the_report_imports_only_the_standard_library():
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import)
                for alias in node.names}
    imported |= {node.module.split(".")[0] for node in ast.walk(tree)
                 if isinstance(node, ast.ImportFrom) and node.module}
    assert imported and imported <= set(sys.stdlib_module_names) | {"__future__"}, imported


def test_the_report_leaves_the_checkout_clean(tmp_path):
    checkout = tmp_path / "checkout"
    (checkout / "scripts").mkdir(parents=True)
    shutil.copy(SCRIPT, checkout / "scripts" / SCRIPT.name)
    git = ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid"]
    subprocess.run(["git", "init", "-q"], cwd=checkout, check=True)
    subprocess.run([*git, "add", "-A"], cwd=checkout, check=True)
    subprocess.run([*git, "commit", "-q", "-m", "c"], cwd=checkout, check=True)
    env = {**os.environ, "PATH": "/usr/bin:/bin"}
    env.pop("PYTHONDONTWRITEBYTECODE", None)
    result = subprocess.run([sys.executable, "scripts/report_runner_disk.py", "--label", "x"],
                            cwd=checkout, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    status = subprocess.run(["git", "status", "--porcelain", "--ignored"], cwd=checkout,
                            capture_output=True, text=True, check=True).stdout
    assert status == "", status
