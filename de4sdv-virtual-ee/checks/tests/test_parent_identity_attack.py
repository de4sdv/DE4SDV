"""R8 attack: an archive must not be able to assert its own identity.

check-archive --repo reconstructs the complete expected identity (tracked
inventory, named groups, tree and scope tree) from Git at the recorded
execution commit and accepts only a record that matches it exactly. A record
that is coherent with itself (digests recomputed, manifest and after-record
rehashed) but not with the commit is rejected.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

CHECKS = Path(__file__).resolve().parents[1]
SCOPE_SRC = CHECKS.parent
HELPER = CHECKS / "run_identity.py"
PY = "/usr/bin/python3"
GIT_ENV = {
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
    "GIT_CONFIG_NOSYSTEM": "1", "GIT_CONFIG_GLOBAL": os.devnull,
}


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True,
                          text=True, env={**os.environ, **GIT_ENV}).stdout.strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def helper(*args: str):
    return subprocess.run([PY, str(HELPER), *args], capture_output=True, text=True, timeout=120,
                          env={**os.environ, **GIT_ENV})


def make_repo(top: Path) -> Path:
    top.mkdir()
    shutil.copytree(SCOPE_SRC, top / "de4sdv-virtual-ee",
                    ignore=shutil.ignore_patterns("results", "__pycache__", ".pytest_cache"))
    (top / "README.md").write_text("root\n")
    (top / ".gitignore").write_text("__pycache__/\n*.py[cod]\n.env\n")
    git(top, "init", "-q", "-b", "main")
    git(top, "add", "-A")
    git(top, "commit", "-q", "-m", "fixture")
    return top


@pytest.fixture
def repo(tmp_path) -> Path:
    return make_repo(tmp_path / "repo")


def check(repo: Path, archive: Path):
    return helper("check-archive", "--repo", str(repo), str(archive))


def test_a_minimal_self_asserted_identity_is_rejected(repo):
    """The parent's reproduced forgery: head only, clean false, empty inventory."""
    head = git(repo, "rev-parse", "HEAD")
    archive = repo / "de4sdv-virtual-ee" / "results" / "forged"
    archive.mkdir(parents=True)
    before = archive / "identity-before.json"
    before.write_text(json.dumps({"git": {"head": head}, "clean": False, "inventory": [], "named": {}}, indent=2))
    (archive / "manifest.json").write_text(json.dumps({"git_head": head, "identity_sha256": sha256(before)}))
    (archive / "identity-after.json").write_text(json.dumps({"matches": True, "before_sha256": sha256(before)}))
    proc = check(repo, archive)
    assert proc.returncode == 1, f"forged identity accepted: {proc.stdout}{proc.stderr}"
    assert "identity complete" not in proc.stdout
