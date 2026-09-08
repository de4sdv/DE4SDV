"""Validate inline local links in tracked Markdown documentation.

A relative Markdown link must resolve, after URL decoding, fragment and
query stripping, and path normalization, to a file that is BOTH present in
the working tree AND tracked repository content (``git ls-files``). A file
that merely exists locally but is not tracked does not make a link valid,
and a tracked-but-deleted (unstaged deletion) target does not either.
A directory link (trailing slash, or a target that resolves to a directory)
is valid only when at least one tracked file lives beneath that directory
AND that content is actually present; the repository root is valid when any
tracked file exists and the root directory itself is present.

The link must stay inside the repository. A relative path that escapes the
repository root is rejected even if a file exists at the escaped location.

Destinations are extracted by a scanner (not a single regex) so every
accepted form is handled exactly: angle-bracket destinations, bare
destinations up to whitespace-then-title-then-``)`` or an unescaped close
paren (balanced ``(...)`` groups allowed), and double- or single-quoted
titles with surrounding whitespace. A link whose destination cannot be
scanned cleanly is reported as unparsable rather than silently skipped.

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

_FENCE = re.compile(r"```.*?```", re.DOTALL)
_LINK_TEXT_RE = re.compile(r"\[[^\]\n]*\]\(")
_QUOTED_TITLE_RE = re.compile(r"""[ \t]+(?:"[^"\n]*"|'[^'\n]*')""")

# Generated artifacts are guarded by the naming checks, not this tool.
_SKIP_SUFFIXES = {".svg"}


class GitInventoryError(RuntimeError):
    """The git file inventory could not be read (fail closed)."""


def _scan_inline_destination(text: str, open_paren: int) -> tuple[str, int] | None:
    """Return ``(destination, end)`` for the inline link opened at ``open_paren``.

    ``open_paren`` is the index of the ``(`` following the link text.
    Accepts an angle-bracket destination, or a bare destination terminated
    by whitespace-then-title-then-``)``, or by an unescaped ``)``. A bare
    destination may contain balanced ``(...)`` groups; the scanner tracks
    depth and backslash escapes. Returns ``None`` when no clean destination
    can be scanned — callers must report that, never silently skip it.
    """
    index = open_paren + 1
    if index < len(text) and text[index] == "<":
        close = text.find(">", index + 1)
        if close == -1 or "\n" in text[index + 1 : close]:
            return None
        return text[index + 1 : close], close + 1
    destination: list[str] = []
    depth = 0
    while index < len(text):
        char = text[index]
        if char == "\\" and index + 1 < len(text):
            destination.append(text[index + 1])
            index += 2
            continue
        if char == "\n":
            return None
        if char == "(":
            depth += 1
            destination.append(char)
        elif char == ")":
            if depth == 0:
                candidate = "".join(destination)
                if not candidate.strip():
                    return None
                title = _QUOTED_TITLE_RE.match(text[index + 1 :])
                end = index + 1 + (title.end() if title else 0)
                if end < len(text) and text[end] == ")":
                    return candidate, end + 1
                return candidate, index + 1
            depth -= 1
            destination.append(char)
        elif char in " \t":
            title = _QUOTED_TITLE_RE.match(text[index:])
            if title:
                after = index + title.end()
                if after < len(text) and text[after] == ")":
                    return "".join(destination), after + 1
                return None
            if "".join(destination).strip():
                # Whitespace inside a bare destination without a title is
                # invalid Markdown; treat as unparsed.
                return None
            # Leading whitespace before the destination is tolerated.
        else:
            destination.append(char)
        index += 1
    return None


def inline_links(text: str) -> list[tuple[str, int]]:
    """Extract ``(destination, line)`` pairs for every inline link in ``text``.

    Links whose destination cannot be scanned cleanly yield the synthetic
    destination ``"\\x00unparsable"`` so callers report them instead of
    silently skipping valid-but-unrecognized Markdown.
    """
    scrubbed = _FENCE.sub(lambda match: "\n" * match.group().count("\n"), text)
    results: list[tuple[str, int]] = []
    search_from = 0
    while match := _LINK_TEXT_RE.search(scrubbed, search_from):
        line = scrubbed[: match.start()].count("\n") + 1
        scanned = _scan_inline_destination(scrubbed, match.end() - 1)
        if scanned is None:
            results.append(("\x00unparsable", line))
            search_from = match.end()
        else:
            destination, end = scanned
            results.append((destination, line))
            search_from = end
    return results


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
        for destination, line in inline_links(text):
            if destination == "\x00unparsable":
                errors.append(
                    f"{name}:{line}: inline link destination could not be "
                    "parsed; fix the link syntax so it is checkable"
                )
                continue
            raw = destination.strip().strip("<>")
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
                # valid when tracked content lives beneath the directory
                # AND that content is present in the working tree. The
                # index alone would let a deleted directory satisfy a link.
                if normalized == ".":
                    tracked_inside = bool(tracked)
                else:
                    tracked_prefix = normalized + "/"
                    tracked_inside = any(
                        tracked_path.startswith(tracked_prefix)
                        for tracked_path in tracked
                    )
                if not tracked_inside:
                    errors.append(
                        f"{name}:{line}: broken local link -> {raw} "
                        f"(no tracked content beneath {normalized})"
                    )
                elif normalized != "." and not resolved.is_dir():
                    errors.append(
                        f"{name}:{line}: broken local link -> {raw} "
                        f"(tracked {normalized} is missing from the working tree)"
                    )
                continue
            # A link target must be BOTH tracked and present in the tree.
            # Membership alone would let a tracked-but-deleted (unstaged
            # deletion) file satisfy the link.
            if normalized not in tracked:
                errors.append(
                    f"{name}:{line}: broken local link -> {raw} "
                    f"(resolved {normalized} is not tracked repository content)"
                )
            elif not resolved.is_file():
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
