#!/usr/bin/env python3
"""Check that UPSTREAM.md lists every GitHub repository the tree names.

A tracked file names a repository when it holds a GitHub address of the form
``github.com/<owner>/<repository>``, with or without a scheme, as an SSH
address, or under the raw-file, archive-download or API host. Each named
repository that is not DE4SDV's own must have one of two things:

- an entry in UPSTREAM.md: any link there to the same repository;
- an omission in ``OMISSIONS`` below, with a reason.

The check fails for a named repository that has neither, for an omission
that UPSTREAM.md links as well, and for an omission that no tracked file
names any more.

A repository may be linked in UPSTREAM.md and named nowhere else: several
upstream projects are recorded by a package, module or image name.

Out of scope: projects on other hosts, projects named without an address,
and whether a link answers.

Usage:
    python tools/check_upstream_index.py          # fail on a missing entry
    python tools/check_upstream_index.py --list   # print what the tree names
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = "UPSTREAM.md"

# Owners whose repositories are DE4SDV's own.
OWN_OWNERS = frozenset({"de4sdv"})

# Repositories that tracked files name and UPSTREAM.md leaves out on purpose.
# Key: lower-case owner/repository. Value: why it has no entry.
OMISSIONS: dict[str, str] = {
    "bazelbuild/bazelisk": (
        "build tool; the runner script of the S-CORE reference bench downloads it by version and digest"
    ),
    "mholt/caddy-ratelimit": (
        "module of the web-server image for the public API; deployment/caddy/Dockerfile pins its revision"
    ),
}

# First path segments of github.com pages that are not repository owners.
_NOT_OWNERS = frozenset(
    {
        "about",
        "apps",
        "codespaces",
        "enterprise",
        "features",
        "login",
        "marketplace",
        "notifications",
        "organizations",
        "orgs",
        "readme",
        "search",
        "security",
        "settings",
        "sponsors",
        "topics",
        "user-attachments",
        "users",
    }
)

_REPOSITORY = re.compile(
    rb"(?<![A-Za-z0-9.-])"
    rb"(?:(?:www\.)?github\.com[/:]|raw\.githubusercontent\.com/|codeload\.github\.com/|api\.github\.com/repos/)"
    rb"([A-Za-z0-9][A-Za-z0-9-]*)/([A-Za-z0-9_.-]+)",
    re.IGNORECASE,
)
_OMISSION_KEY = re.compile(r"[a-z0-9][a-z0-9-]*/[a-z0-9_.-]+")


class GitInventoryError(RuntimeError):
    """The git file inventory could not be read (fail closed)."""


def repositories(data: bytes) -> list[str]:
    """Every third-party repository that the data names, as written, in order."""
    if b"\0" in data[:8000]:
        return []  # binary
    if b"github" not in data.lower():
        return []  # no address to parse; most files, and it spares the large generated ones
    found = []
    for match in _REPOSITORY.finditer(data):
        owner = match.group(1).decode("ascii")
        name = match.group(2).decode("ascii").rstrip(".")
        if name.lower().endswith(".git"):
            name = name[: -len(".git")]
        if name and owner.lower() not in _NOT_OWNERS and owner.lower() not in OWN_OWNERS:
            found.append(f"{owner}/{name}")
    return found


def named_repositories(files: Mapping[str, bytes]) -> dict[str, list[str]]:
    """Lower-case repository to the sorted files that name it; the index itself is not such a file."""
    named: dict[str, list[str]] = {}
    for path in sorted(files):
        if path == INDEX:
            continue
        for repository in dict.fromkeys(name.lower() for name in repositories(files[path])):
            named.setdefault(repository, []).append(path)
    return named


def linked_repositories(files: Mapping[str, bytes]) -> frozenset[str]:
    """Lower-case repositories that the index links."""
    return frozenset(name.lower() for name in repositories(files.get(INDEX, b"")))


def index_errors(files: Mapping[str, bytes], omissions: Mapping[str, str] | None = None) -> list[str]:
    """One error per repository without an entry and per omission that does not hold."""
    omissions = OMISSIONS if omissions is None else omissions
    if INDEX not in files:
        return [f"{INDEX} is not a tracked file"]
    named = named_repositories(files)
    linked = linked_repositories(files)
    errors = []
    for repository, paths in sorted(named.items()):
        if repository in linked or repository in omissions:
            continue
        more = len(paths) - 1
        tail = f" and {more} more file{'s' if more > 1 else ''}" if more else ""
        errors.append(f"{repository} has no entry in {INDEX}: named in {paths[0]}{tail}")
    for key, reason in sorted(omissions.items()):
        if not _OMISSION_KEY.fullmatch(key):
            errors.append(f"omission {key} is not written as lower-case owner/repository")
        elif not reason.strip():
            errors.append(f"omission {key} has no reason")
        elif key in linked:
            errors.append(f"omission {key} is linked in {INDEX}: keep the entry or the omission")
        elif key not in named:
            errors.append(f"omission {key} is named in no tracked file: remove it")
    return errors


def tracked_files() -> list[str]:
    completed = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True)
    if completed.returncode != 0:
        raise GitInventoryError(
            "git ls-files failed: " + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    return [path for path in completed.stdout.decode("utf-8", errors="replace").split("\0") if path]


def read_tracked() -> dict[str, bytes]:
    """Content of every tracked file that is present in the working tree."""
    files = {}
    for path in tracked_files():
        file = ROOT / path
        if file.is_file():
            files[path] = file.read_bytes()
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--list", action="store_true", help="list the repositories the tree names")
    arguments = parser.parse_args()

    try:
        files = read_tracked()
    except GitInventoryError as error:
        print(f"Upstream index check failed: {error}", file=sys.stderr)
        return 1
    named = named_repositories(files)
    if arguments.list:
        linked = linked_repositories(files)
        for repository, paths in sorted(named.items()):
            state = "entry" if repository in linked else "omission" if repository in OMISSIONS else "MISSING"
            print(f"{state:8} {repository}  ({len(paths)} file{'s' if len(paths) > 1 else ''}, first: {paths[0]})")
        return 0

    errors = index_errors(files)
    if errors:
        print("Upstream index check failed:")
        for error in errors:
            print(f"- {error}")
        print(
            f"Give the project an entry in {INDEX}. A build tool or the like that the page leaves out\n"
            "goes into OMISSIONS in tools/check_upstream_index.py, with a reason."
        )
        return 1
    print(f"Upstream index check passed ({len(named)} repositories named in {len(files)} files).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
