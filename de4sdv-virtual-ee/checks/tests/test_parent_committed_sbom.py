"""CI verifies the retained inventory bytes against the current package pins."""
from pathlib import Path
import subprocess
import sys


def test_committed_sboms_match_the_locked_runtime_images():
    checks = Path(__file__).resolve().parents[1]
    result = subprocess.run([sys.executable, str(checks / "sbom_inventory.py"), "check"], text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
