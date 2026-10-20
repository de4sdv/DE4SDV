#!/usr/bin/env python3
"""Validate all DE4SDV SysML v2 model roots with Sensmetry SysIDE CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

MODEL_PATHS = (
    Path("textual-notation-of-model"),
    Path("model-based-product-line-engineering/product-models"),
    Path("model-based-product-line-engineering/scoping"),
    Path("model-based-product-line-engineering/feature-models"),
    Path("model-based-product-line-engineering/feature-configurations"),
)
#: The synthetic fixtures of the model roots (the invalid configuration and
#: the parity probes under feature-configurations/fixtures/) are no production
#: model files: the export never reads them, and the privileged PLE authority
#: workflow validates them with the model roots. The check excludes them, as
#: the licensed validation in CI does.
EXCLUDED_PART = "fixtures"
EXCLUDED_GLOB = f"**/{EXCLUDED_PART}/**"


def model_files(root: Path, model_path: Path) -> list[Path]:
    """The .sysml files of one model root that the check validates."""
    base = root / model_path
    if not base.exists():
        return []
    return [path for path in sorted(base.rglob("*.sysml"))
            if EXCLUDED_PART not in path.relative_to(base).parts]


def check_command(syside: str) -> list[str]:
    """The licensed check of the model roots, without their fixtures."""
    return [syside, "check", *(path.as_posix() for path in MODEL_PATHS), "--exclude", EXCLUDED_GLOB]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    model_files_by_path: dict[Path, list[Path]] = {}

    for model_path in MODEL_PATHS:
        files = model_files(root, model_path)
        if not files:
            print(
                f"SysML validation failed: no .sysml files found under {model_path.as_posix()}/.",
                file=sys.stderr,
            )
            return 1
        model_files_by_path[model_path] = files

    syside = shutil.which("syside")
    if syside is None:
        print(
            "SysML validation failed: Sensmetry SysIDE Modeler CLI executable "
            "'syside' was not found on PATH.",
            file=sys.stderr,
        )
        print(
            "Install the CLI and rerun: python scripts/validate_sysml.py\n"
            "If you use VS Code and have Syside access, you can also validate changed "
            ".sysml files locally with the Syside Editor VS Code extension.\n"
            "Documentation: https://docs.sensmetry.com/modeler/cli/commands.html",
            file=sys.stderr,
        )
        return 1

    print("Validating SysML v2 textual notation with Sensmetry SysIDE Modeler CLI:")
    for files in model_files_by_path.values():
        for path in files:
            print(f"- {path.relative_to(root).as_posix()}")

    result = subprocess.run(check_command(syside), cwd=root)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
