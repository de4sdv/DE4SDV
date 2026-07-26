#!/usr/bin/env python3
"""Verify exact clean source checkouts and attach their identities to evidence."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import subprocess

import yaml

from execution_identity import execution_manifest_sha256

SHA40 = re.compile(r"^[0-9a-f]{40}$")


def git(checkout: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(checkout), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("bench", type=Path)
    parser.add_argument("evidence", type=Path)
    args = parser.parse_args()

    bench = args.bench.resolve()
    manifest = yaml.safe_load((bench / "autoware-009a.repos").read_text())
    lock = yaml.safe_load((bench / "runtime-lock.yaml").read_text())
    locked_sources = {item["name"]: item for item in lock["sources"]}
    repositories = []
    all_match = set(manifest["repositories"]) == set(locked_sources)
    for name, definition in sorted(manifest["repositories"].items()):
        locked = locked_sources.get(name, {})
        expected_revision = locked.get("commit")
        expected_tree = locked.get("tree")
        manifest_matches_lock = (
            definition.get("type") == "git"
            and definition.get("url") == locked.get("repository")
            and definition.get("version") == expected_revision
            and SHA40.fullmatch(str(expected_tree or "")) is not None
        )
        checkout = bench / "workspace/src" / name
        actual_revision = git(checkout, "rev-parse", "HEAD")
        actual_tree = git(checkout, "rev-parse", "HEAD^{tree}")
        porcelain = git(checkout, "status", "--porcelain=v1", "--untracked-files=all")
        submodule_status = git(checkout, "submodule", "status", "--recursive").splitlines()
        worktree_clean = porcelain == ""
        submodules_clean = not any(
            line.startswith(("-", "+", "U")) for line in submodule_status
        )
        matches = (
            manifest_matches_lock
            and actual_revision == expected_revision
            and actual_tree == expected_tree
            and worktree_clean
            and submodules_clean
        )
        all_match = all_match and matches
        repositories.append(
            {
                "name": name,
                "url": definition["url"],
                "manifest_matches_lock": manifest_matches_lock,
                "expected_revision": expected_revision,
                "actual_revision": actual_revision,
                "expected_tree": expected_tree,
                "actual_tree": actual_tree,
                "worktree_clean": worktree_clean,
                "worktree_status": porcelain.splitlines(),
                "submodule_status": submodule_status,
                "matches": matches,
            }
        )

    document = json.loads(args.evidence.read_text())
    document["execution_manifest_sha256"] = execution_manifest_sha256(bench)
    document["repositories"] = repositories
    document["all_revisions_match"] = all_match
    document["command_exit_status"] = 0 if all_match else 1
    args.evidence.write_text(json.dumps(document, indent=2, sort_keys=True) + "\n")
    if not all_match:
        raise SystemExit("one or more source checkouts differ from their locked clean trees")


if __name__ == "__main__":
    main()
