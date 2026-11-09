"""Test setup: module paths and the built artifacts.

Run with ``make test`` (which builds the native and our library first) or
``.venv/bin/python -m pytest tests`` from the navigation directory.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FAKES = HERE / "fakes"

for entry in (str(ROOT), str(FAKES)):
    if entry not in sys.path:
        sys.path.insert(0, entry)


@pytest.fixture(scope="session")
def repository_root() -> Path:
    return ROOT


@pytest.fixture(scope="session")
def native_library() -> Path:
    path = ROOT / "build" / "libnavigation_rasterizer.so"
    if not path.is_file():
        pytest.fail(
            "build/libnavigation_rasterizer.so missing; run `make native` "
            "(it builds upstream's native rasterizer unmodified)"
        )
    return path


@pytest.fixture(scope="session")
def raster_cli() -> Path:
    path = ROOT / "build" / "raster_cli"
    if not path.is_file():
        pytest.fail("build/raster_cli missing; run `make cli`")
    return path


def run_cli(cli: Path, *arguments: str) -> dict:
    """Run the C++ driver and return its JSON summary."""
    import json

    result = subprocess.run(
        [str(cli), *arguments],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"raster_cli failed: {result.stderr}"
    return json.loads(result.stdout)


@pytest.fixture(scope="session")
def cli_runner():
    return run_cli
