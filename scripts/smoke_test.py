#!/usr/bin/env python3
"""Smoke tests for repository consistency."""

from __future__ import annotations

from pathlib import Path
import sys


def assert_exists(path: Path) -> None:
    if not path.exists():
        raise AssertionError(f"Expected path to exist: {path}")


def main() -> int:
    root = Path(__file__).resolve().parents[1]

    # Core folders
    for rel in [
        "docs",
        "textual-notation-of-model",
        "simulation",
        "compliance",
        "devsecops",
    ]:
        assert_exists(root / rel)

    # New contribution scaffolding
    for rel in [
        ".github/ISSUE_TEMPLATE",
        ".github/PULL_REQUEST_TEMPLATE/pull_request_template.md",
        ".github/workflows/ci.yml",
    ]:
        assert_exists(root / rel)

    print("Smoke test passed.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AssertionError as exc:
        print(f"Smoke test failed: {exc}")
        raise SystemExit(1)
