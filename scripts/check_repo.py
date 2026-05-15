#!/usr/bin/env python3
"""Minimal repository health checks for DE4SDV."""

from __future__ import annotations

from pathlib import Path
import sys

REQUIRED_FILES = [
    "README.md",
    "CONTRIBUTING.md",
    "GOVERNANCE.md",
    "SECURITY.md",
    "SUPPORT.md",
    "CODE_OF_CONDUCT.md",
    "docs/terminology/glossary.md",
]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing: list[str] = []

    for rel in REQUIRED_FILES:
        if not (root / rel).exists():
            missing.append(rel)

    if missing:
        print("Repository check failed. Missing required files:")
        for rel in missing:
            print(f"- {rel}")
        return 1

    print("Repository check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
