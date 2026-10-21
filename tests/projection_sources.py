"""The source of a committed product-model projection (ADR 0022).

Each committed projection is generated from the committed receipt of its PLEML
configuration by the configurator's writer, and must regenerate from it byte
for byte.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/configure_variant.py"
PLE = Path("model-based-product-line-engineering")
RECEIPTS = PLE / "feature-models/receipts"
CONFIGURATIONS = PLE / "feature-configurations"


def receipt_of(configuration: str) -> Path:
    """The committed receipt whose feature model evaluates ``configuration``."""
    [path] = [path for path in sorted((ROOT / RECEIPTS).glob("*.receipt.json"))
              if configuration in json.loads(path.read_text(encoding="utf-8"))["model_sources"]]
    return path


def _run(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=ROOT, capture_output=True,
                          text=True, check=False, timeout=180)


def receipt_projection(configuration: str) -> str:
    """The projection the configurator writes for ``configuration`` from its committed receipt."""
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "projection.sysml"
        result = _run("--receipt", str(receipt_of(configuration)), "--configuration", configuration,
                      "--output", str(output))
        if result.returncode != 0:
            raise AssertionError(f"the configurator refused {configuration}: {result.stderr}")
        return output.read_text(encoding="utf-8")
