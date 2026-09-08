"""Validate inline local links in tracked Markdown documentation.

A relative Markdown link must resolve, after URL decoding, fragment and
query stripping, and path normalization, to a file that is BOTH present in
the working tree AND tracked repository content (``git ls-files``). A file
that merely exists locally but is not tracked does not make a link valid,
and a tracked-but-deleted (unstaged deletion) target does not either.
A directory link (trailing slash, or a target that resolves to a directory)
is valid only when at least one tracked file lives beneath that directory;
the repository root is valid when ANY tracked file exists.

The link must stay inside the repository. A relative path that escapes the
repository root is rejected even if a file exists at the escaped location.

Explicitly out of scope: remote URLs, same-page anchors, generated SVG
targets (guarded by the naming checks), and link text.

Usage:
    python tools/check_markdown_links.py            # fail on broken links
    python tools/check_markdown_links.py --list     # print tracked Markdown
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]

# Inline Markdown links: [text](destination "optional title"). Accepts
# plain destinations, angle-bracket destinations, and double- or
# single-quoted titles. Reference-style definitions and bare autolinks are
# out of scope.
_INLINE_LINK = re.compile(
    r"\[[^\]\n]*\]\("
    r"(?:<([^>\n]*)>|([^)\s]+))"
    r"(?:[ \t]+(?:(?:\"[^\"]*\")|(?:\'[^\']*\')))?"
    r"\)"
)
_FENCE = re.compile(r"```.*?```", re.DOTALL)

# Generated artifacts are guarded by the naming checks, not this tool.
_SKIP_SUFFIXES = {".svg"}


class GitInventoryError(RuntimeError):
    """The git file inventory could not be read (fail closed)."""


def tracked_files() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True
    )
    if completed.returncode != 0:
        raise GitInventoryError(
            "git ls-files failed: "
            + completed.stderr.decode("utf-8", errors="replace").strip()
        )
    stdout = completed.stdout.decode("utf-8", errors="replace")
    return [path for path in stdout.split("\0") if path]


def tracked_surface() -> frozenset[str]:
    """Normalized repository-relative paths of every tracked file."""
    return frozenset(
        str(PurePosixPath(name)) for name in tracked_files()
    )


def broken_links(
    markdown_files: list[str],
    tracked: frozenset[str] | None = None,
) -> list[str]:
    """Return sorted, de-duplicated broken-link reports for the given files.

    ``tracked`` defaults to the real repository surface; tests may inject a
    synthetic surface.
    """
    if tracked is None:
        tracked = tracked_surface()
    errors: list[str] = []
    for name in markdown_files:
        absolute = ROOT / name
        text = absolute.read_text(encoding="utf-8", errors="replace")
        scrubbed = _FENCE.sub(lambda match: "\n" * match.group().count("\n"), text)
        for match in _INLINE_LINK.finditer(scrubbed):
            raw = next(group for group in match.groups() if group is not None)
            raw = raw.strip().strip("<>")
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw) or raw.startswith("#"):
                continue  # remote or same-page anchor
            path_part = urllib.parse.unquote(raw.split("#")[0].split("?")[0])
            if not path_part:
                continue  # pure fragment/query target
            if Path(path_part).suffix.lower() in _SKIP_SUFFIXES:
                continue
            # Resolve relative to the Markdown file's directory, then make
            # the result repository-relative and canonical.
            resolved = (absolute.parent / path_part).resolve()
            try:
                repo_relative = resolved.relative_to(ROOT.resolve())
            except ValueError:
                line = scrubbed[: match.start()].count("\n") + 1
                errors.append(
                    f"{name}:{line}: link escapes repository root -> {raw}"
                )
                continue
            normalized = PurePosixPath(repo_relative).as_posix()
            target_is_directory = (
                path_part.endswith("/")
                or (resolved.is_dir() and not resolved.is_file())
            )
            if target_is_directory:
                # Git tracks files, not directories: a directory link is
                # valid when tracked content lives beneath the directory.
                if normalized == ".":
                    tracked_inside = bool(tracked)
                else:
                    tracked_prefix = normalized + "/"
                    tracked_inside = any(
                        tracked_path.startswith(tracked_prefix)
                        for tracked_path in tracked
                    )
                if not tracked_inside:
                    line = scrubbed[: match.start()].count("\n") + 1
                    errors.append(
                        f"{name}:{line}: broken local link -> {raw} "
                        f"(no tracked content beneath {normalized})"
                    )
                continue
            # A link target must be BOTH tracked and present in the tree.
            # Membership alone would let a tracked-but-deleted (unstaged
            # deletion) file satisfy the link.
            if normalized not in tracked:
                line = scrubbed[: match.start()].count("\n") + 1
                errors.append(
                    f"{name}:{line}: broken local link -> {raw} "
                    f"(resolved {normalized} is not tracked repository content)"
                )
            elif not resolved.is_file():
                line = scrubbed[: match.start()].count("\n") + 1
                errors.append(
                    f"{name}:{line}: broken local link -> {raw} "
                    f"(tracked {normalized} is missing from the working tree)"
                )
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list", action="store_true", help="list tracked Markdown files"
    )
    arguments = parser.parse_args()

    try:
        markdown_files = [
            name for name in tracked_files() if name.lower().endswith(".md")
        ]
    except GitInventoryError as error:
        print(f"Markdown local-link check failed: {error}", file=sys.stderr)
        return 1
    if arguments.list:
        for name in markdown_files:
            print(name)
        return 0

    errors = broken_links(markdown_files)
    if errors:
        print("Markdown local-link check failed:")
        for error in errors:
            print(f"- {error}")
        return 1
    print(f"Markdown local-link check passed ({len(markdown_files)} files).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
