"""Builds and runs the identity recorder's C++ unit tests with the host's g++, as C++17 and C++20.

The pure parts (SHA-256, the input resolution, the record, the record writer, the shell, the late subscriber's
check) need no S-CORE: the tests drive them with fakes for the file system, mw::com and the lifecycle client
(tests/fake_file_system.h and the fakes in recorder_shell_test.cpp). The SHA-256 vectors are compared with Python's
hashlib at test time; no digest is written into the C++ tests.
"""

from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RECORDER = HERE.parent
BENCH = RECORDER.parent
ADAPTER = BENCH / "actuation-adapter"
INCLUDE = BENCH / "interfaces" / "include"

FLAGS = ["-Wall", "-Wextra", "-Werror", "-pedantic", f"-I{RECORDER}", f"-I{HERE}", f"-I{INCLUDE}", f"-I{ADAPTER}",
         f"-I{ADAPTER / 'tests'}"]

CORE = [RECORDER / "sha256.cpp", RECORDER / "file_system.cpp", RECORDER / "record_inputs.cpp",
        RECORDER / "candidate_record.cpp", ADAPTER / "json_lite.cpp"]

BINARIES = {
    "sha256_test": [HERE / "sha256_test.cpp", RECORDER / "sha256.cpp"],
    "record_inputs_test": [HERE / "record_inputs_test.cpp", *CORE],
    "candidate_record_test": [HERE / "candidate_record_test.cpp", *CORE],
    "recorder_shell_test": [HERE / "recorder_shell_test.cpp", RECORDER / "recorder_shell.cpp",
                            RECORDER / "record_probe.cpp", *CORE],
}


def build(name: str, standard: str, out_dir: Path) -> Path:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    binary = out_dir / f"{name}_{standard.replace('+', 'p')}"
    sources = [str(path) for path in BINARIES[name]]
    subprocess.run([compiler, f"-std={standard}", *FLAGS, *sources, "-o", str(binary)], check=True)
    return binary


@pytest.mark.parametrize("standard", ["c++17", "c++20"])
@pytest.mark.parametrize("name", sorted(BINARIES))
def test_unit_binary(tmp_path: Path, name: str, standard: str) -> None:
    binary = build(name, standard, tmp_path)
    result = subprocess.run([str(binary)], capture_output=True, text=True, env={"TMPDIR": str(tmp_path)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"{name}: all passed" in result.stdout, result.stdout


def test_sha256_equals_hashlib(tmp_path: Path) -> None:
    binary = build("sha256_test", "c++17", tmp_path)
    out = subprocess.run([str(binary), "--vectors"], capture_output=True, text=True, check=True).stdout
    lines = [line.split() for line in out.splitlines()]
    assert len(lines) == 16, out
    for hex_input, digest in lines:
        if hex_input == "million-a":
            data = b"a" * 1_000_000
        else:
            data = b"" if hex_input == "-" else bytes.fromhex(hex_input)
        assert digest == hashlib.sha256(data).hexdigest(), hex_input[:20]
