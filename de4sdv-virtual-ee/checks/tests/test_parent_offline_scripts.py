"""Execute the original standalone scripts; importing them collects no tests."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.parametrize("script", ["check_contract.py", "test_zone_ecu.py", "test_bridge.py", "test_someip.py"])
def test_standalone_check_executes_and_passes(script):
    result = subprocess.run([sys.executable, str(ROOT / "checks" / script)], text=True, capture_output=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "PASS" in result.stdout or "OK" in result.stderr
