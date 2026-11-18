"""Builds and runs the actuation adapter's C++ unit tests with the host's g++.

The adapter's pure parts (configuration, core, records, shell) are C++17, the
S-CORE toolchain's default; each test binary is built as C++17 and as C++20.
The CARLA 1.0 client unit (simulator_client_carla.cpp) needs LibCarla and is not
built here: the tests link the fake client of tests/fake_simulator_client.cpp.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ADAPTER = HERE.parent
INCLUDE = ADAPTER.parent / "interfaces" / "include"

FLAGS = ["-Wall", "-Wextra", "-Werror", "-pedantic", f"-I{ADAPTER}", f"-I{HERE}", f"-I{INCLUDE}"]

BINARIES = {
    "actuation_core_test": [
        HERE / "actuation_core_test.cpp",
        ADAPTER / "actuation_core.cpp",
    ],
    "adapter_config_test": [
        HERE / "adapter_config_test.cpp",
        ADAPTER / "adapter_config.cpp",
        ADAPTER / "json_lite.cpp",
    ],
}

ARGUMENTS = {
    "adapter_config_test": [str(ADAPTER / "config" / "adapter.json")],
}


def build(name: str, standard: str, out_dir: Path) -> Path:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    binary = out_dir / f"{name}_{standard.replace('+', 'p')}"
    sources = [str(path) for path in BINARIES[name]]
    subprocess.run([str(compiler), f"-std={standard}", *FLAGS, *sources, "-o", str(binary)], check=True)
    return binary


@pytest.mark.parametrize("standard", ["c++17", "c++20"])
@pytest.mark.parametrize("name", sorted(BINARIES))
def test_unit_binary(tmp_path: Path, name: str, standard: str) -> None:
    binary = build(name, standard, tmp_path)
    result = subprocess.run([str(binary), *ARGUMENTS.get(name, [])], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{name}: all passed" in result.stdout, result.stdout
