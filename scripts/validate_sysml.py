#!/usr/bin/env python3
"""Validate DE4SDV SysML v2 textual notation with Sensmetry SysIDE CLI."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

MODEL_DIR = Path("textual-notation-of-model")


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    model_dir = root / MODEL_DIR

    sysml_files = sorted(model_dir.rglob("*.sysml")) if model_dir.exists() else []
    if not sysml_files:
        print("SysML validation skipped: no .sysml files found under textual-notation-of-model/.")
        return 0

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
            ".sysml files locally with the Syside Editor extension.\n"
            "Documentation: https://docs.sensmetry.com/modeler/cli/commands.html",
            file=sys.stderr,
        )
        return 1

    rel_files = [path.relative_to(root).as_posix() for path in sysml_files]
    print("Validating SysML v2 textual notation with Sensmetry SysIDE Modeler CLI:")
    for rel in rel_files:
        print(f"- {rel}")

    cmd = [syside, "check", MODEL_DIR.as_posix()]
    result = subprocess.run(cmd, cwd=root)
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
