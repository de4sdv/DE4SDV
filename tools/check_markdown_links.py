"""Validate inline local links in tracked Markdown documentation.

A relative Markdown link must resolve to a tracked repository file. This
check covers navigation integrity only: it does not validate anchors,
remote URLs, or link text.

Usage:
    python tools/check_markdown_links.py            # fail on broken links
    python tools/check_markdown_links.py --list     # print all local links
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Inline Markdown links: [text](target). Reference-style definitions and
# bare autolinks are out of scope.
_INLINE_LINK = re.compile(r"\[[^\]\n]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
_FENCE = re.compile(r"```.*?```", re.DOTALL)

_SKIP_SUFFIXES = {".svg"}  # generated artifacts are guarded by naming checks


def tracked_files() -> list[str]:
    completed = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, text=True
    )
    return [path for path in completed.stdout.split("\0") if path]


def broken_links(markdown_files: list[str]) -> list[str]:
    errors: list[str] = []
    for name in markdown_files:
        absolute = ROOT / name
        text = absolute.read_text(encoding="utf-8", errors="replace")
        scrubbed = _FENCE.sub(lambda match: "\n" * match.group().count("\n"), text)
        for match in _INLINE_LINK.finditer(scrubbed):
            raw = match.group(1).strip().strip("<>")
            if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", raw) or raw.startswith("#"):
                continue  # remote or same-page anchor
            path_part = urllib.parse.unquote(raw.split("#")[0].split("?")[0])
            if not path_part:
                continue
            if Path(path_part).suffix.lower() in _SKIP_SUFFIXES:
                continue
            target = absolute.parent / path_part
            if not target.exists():
                line = scrubbed[: match.start()].count("\n") + 1
                errors.append(f"{name}:{line}: broken local link -> {raw}")
    return sorted(set(errors))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--list", action="store_true", help="list Markdown files with local links"
    )
    arguments = parser.parse_args()

    markdown_files = [
        name for name in tracked_files() if name.lower().endswith(".md")
    ]
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
