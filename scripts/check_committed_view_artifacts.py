#!/usr/bin/env python3
"""Check that committed view SVGs match exact generated artifacts."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

try:
    from scripts.generate_view_index import artifact_filename, collect_views
except ModuleNotFoundError:  # Direct execution from scripts/.
    from generate_view_index import artifact_filename, collect_views


def check_committed_view_artifacts(
    model_folder: Path, generated_folder: Path
) -> list[str]:
    tracked_folder = model_folder / "diagrams"
    collected = collect_views(model_folder)
    expected = {
        artifact_filename(spec.name, spec.view_type)
        for _, views in collected
        for spec in views
    }
    committed = {path.name for path in tracked_folder.glob("*.svg")}
    errors: list[str] = []

    for name in sorted(expected - committed):
        errors.append(f"missing committed diagram: {tracked_folder / name}")
    for name in sorted(committed - expected):
        errors.append(f"stale committed diagram: {tracked_folder / name}")

    for name in sorted(expected & committed):
        generated = generated_folder / name
        tracked = tracked_folder / name
        if not generated.is_file():
            errors.append(f"missing generated diagram: {generated}")
        elif generated.read_bytes() != tracked.read_bytes():
            errors.append(f"stale committed diagram content: {tracked}")

    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("model_folder", type=Path)
    parser.add_argument("generated_folder", type=Path)
    args = parser.parse_args()

    errors = check_committed_view_artifacts(
        args.model_folder.resolve(), args.generated_folder.resolve()
    )
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("committed view artifacts match generated artifacts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
