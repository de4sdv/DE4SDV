#!/usr/bin/env python3
"""List the model folders whose views are published (VIEWS.md and diagrams/).

A view folder is a folder under the model roots whose own `.sysml` files
declare a SysML `view` usage, read the way `scripts/generate_view_index.py`
reads them, or that already holds published views (`VIEWS.md` or
`diagrams/`), so a folder whose views were all removed stays checked until
its published views go too. Upstream libraries, snapshots and synthetic
fixtures are never view folders. The Privileged Syside Validation workflow
checks the published views of every folder listed here; nothing names a view
folder by hand.

    python scripts/list_view_folders.py [MODEL_PATH ...]

MODEL_PATH defaults to the model roots the licensed validation checks; a
model file stands for its folder. Prints one repository-relative folder per
line, sorted. Exits 1 when no folder is found (an empty list would check
nothing) and 2 when a model path does not exist.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Iterable, Sequence

try:
    from scripts.generate_view_index import collect_views
except ModuleNotFoundError:  # Direct execution from scripts/.
    from generate_view_index import collect_views

ROOT = Path(__file__).resolve().parents[1]

#: The model roots of the licensed validation (its default MODEL_PATHS).
MODEL_ROOTS = (
    "textual-notation-of-model",
    "model-based-product-line-engineering/product-models",
    "model-based-product-line-engineering/scoping",
    "model-based-product-line-engineering/feature-models",
    "model-based-product-line-engineering/feature-configurations",
)

#: Never view folders: upstream libraries (`libraries/`, the `.sysand/`
#: dependency tree), historical snapshots (excluded from rendering) and
#: synthetic fixtures.
EXCLUDED_PARTS = frozenset({"libraries", ".sysand", "snapshots", "fixture", "fixtures"})


def _candidates(base: Path) -> set[Path]:
    if base.is_file():
        return {base.parent}
    found = {path.parent for path in base.rglob("*.sysml")}
    found |= {path.parent for path in base.rglob("VIEWS.md")}
    found |= {path.parent for path in base.rglob("diagrams") if path.is_dir()}
    return found


def _is_view_folder(folder: Path) -> bool:
    return (
        bool(collect_views(folder))
        or (folder / "VIEWS.md").is_file()
        or (folder / "diagrams").is_dir()
    )


def view_folders(model_paths: Iterable[str] = MODEL_ROOTS, *, repository: Path = ROOT) -> list[str]:
    """Repository-relative view folders under the model paths, sorted."""
    folders: set[str] = set()
    for model_path in model_paths:
        base = repository / model_path
        if not base.exists():
            raise FileNotFoundError(f"model path not found: {model_path}")
        for folder in _candidates(base):
            relative = folder.relative_to(repository)
            if EXCLUDED_PARTS & set(relative.parts):
                continue
            if _is_view_folder(folder):
                folders.add(relative.as_posix())
    return sorted(folders)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("model_paths", nargs="*", default=list(MODEL_ROOTS),
                        help="model folders or files (default: the validated model roots)")
    args = parser.parse_args(argv)
    try:
        folders = view_folders(args.model_paths, repository=ROOT)
    except FileNotFoundError as error:
        print(error, file=sys.stderr)
        return 2
    if not folders:
        print(f"no view folder under: {' '.join(args.model_paths)}", file=sys.stderr)
        return 1
    for folder in folders:
        print(folder)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
