"""Builds and runs the C++ tests of the bench's payload header."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
INCLUDE = HERE.parent / "include"


@pytest.mark.parametrize("standard", ["c++17", "c++20"])
def test_payloads_header(tmp_path: Path, standard: str) -> None:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    binary = tmp_path / "payloads_test"
    subprocess.run(
        [compiler, f"-std={standard}", "-Wall", "-Wextra", "-Werror", "-pedantic",
         f"-I{INCLUDE}", str(HERE / "payloads_test.cpp"), "-o", str(binary)],
        check=True,
    )
    result = subprocess.run([str(binary)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "payloads_test: all passed" in result.stdout
