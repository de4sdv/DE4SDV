"""The two sources of a committed product-model projection since the switch (ADR 0022, step S6).

Each committed projection is generated from the committed receipt of its PLEML
configuration (receipt mode, the authority) and must regenerate from it byte
for byte. Its Bill-of-Features beside the configuration is the
non-authoritative shadow until the YAML retires (step S7): the YAML path's
projection of it must have the same normalised body, the body below the
provenance header with the derivation-source line normalised (plan section 5).
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

from de4sdv.semantic import pleml_receipts

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "tools/configure_variant.py"
PLE = Path("model-based-product-line-engineering")
RECEIPTS = PLE / "feature-models/receipts"


def configuration_of(bill: str | Path) -> str:
    """The PLEML configuration a Bill-of-Features shadows: the same stem in snake case."""
    path = Path(bill)
    return path.with_name(path.stem.replace("-", "_") + ".sysml").as_posix()


def receipt_of(configuration: str) -> Path:
    """The committed receipt whose feature model evaluates ``configuration``."""
    [path] = [path for path in sorted((ROOT / RECEIPTS).glob("*.receipt.json"))
              if configuration in json.loads(path.read_text(encoding="utf-8"))["model_sources"]]
    return path


def _run(*arguments: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), *arguments], cwd=ROOT, capture_output=True,
                          text=True, check=False, timeout=180)


def receipt_projection(configuration: str) -> str:
    """The projection receipt mode writes for ``configuration`` from its committed receipt."""
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "projection.sysml"
        result = _run("--receipt", str(receipt_of(configuration)), "--configuration", configuration,
                      "--output", str(output))
        if result.returncode != 0:
            raise AssertionError(f"receipt mode refused {configuration}: {result.stderr}")
        return output.read_text(encoding="utf-8")


def shadow_projection(bill: str | Path, feature_model: str | Path, shared_assets: str | Path) -> str:
    """The projection the YAML path writes for a Bill-of-Features, the shadow."""
    with tempfile.TemporaryDirectory() as directory:
        output = Path(directory) / "projection.sysml"
        result = _run("--feature-model", str(ROOT / feature_model), "--bof", str(ROOT / bill),
                      "--shared-assets-model", str(ROOT / shared_assets), "--output", str(output))
        if result.returncode != 0:
            raise AssertionError(f"the YAML path refused {bill}: {result.stderr}")
        return output.read_text(encoding="utf-8")


def normalised_body(text: str) -> str:
    return pleml_receipts.normalised_body(text)
