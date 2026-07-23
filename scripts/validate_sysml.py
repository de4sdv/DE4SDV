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
)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    model_files: dict[Path, list[Path]] = {}

    for model_path in MODEL_PATHS:
        absolute_path = root / model_path
        files = sorted(absolute_path.rglob("*.sysml")) if absolute_path.exists() else []
        if not files:
            print(
                f"SysML validation failed: no .sysml files found under {model_path.as_posix()}/.",
                file=sys.stderr,
            )
            return 1
        model_files[model_path] = files

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
    for files in model_files.values():
        for path in files:
            print(f"- {path.relative_to(root).as_posix()}")

    cmd = [syside, "check", *(path.as_posix() for path in MODEL_PATHS)]
    result = subprocess.run(cmd, cwd=root)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
