"""Builds and runs the unit tests of the DE4SDV S-CORE interface for VisionPilot, and checks the patch series.

- core_test.cpp: the module's core against the bench's payloads.h only (runs wherever g++ runs).
- the vectors of core_test --vectors against Python's zlib and struct, computed here at test time.
- adapters_test.cpp: the adapters against upstream's real headers at the pin and OpenCV 4. It needs a local
  VisionPilot clone that holds the pin (VISIONPILOT_CLONE) and pkg-config's opencv4; it is skipped, with the reason,
  where either is missing.
- src/lola_bindings.cpp: a syntax check against the closed-loop driving bench's local mw::com mock, which is no
  S-CORE header; the real compile is the S-CORE Bazel build's.
- the patch series: the new files of 0002 equal module/, the shas equal patches/SHA256SUMS, 0001 is the VIS8 patch,
  and every line 0002 adds to upstream C++ outside the enum sits under ENABLE_SCORE_INTERFACE.
"""

from __future__ import annotations

import hashlib
import math
import os
import shutil
import struct
import subprocess
import zlib
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
MODULE = ROOT / "module"
PATCHES = ROOT / "patches"
INTERFACES = ROOT.parent / "interfaces" / "include"
MWCOM_MOCK = ROOT.parents[1] / "closed-loop-driving-bench" / "state-publisher" / "tests" / "mock"
PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"
VIS8_SHA256 = "29a1f5d0a087b05f1b8e2e2d57cd6fd5f818d9a2d996fe2b0256f254c2a5ad27"  # the VIS8 patch as delivered
PATCH_MODULE_PREFIX = "VisionPilot/modules/de4sdv/score_interface/"
UPSTREAM_HEADERS = [
    "modules/sensing/camera_interface/include/camera_interface/camera_interface.hpp",
    "modules/sensing/vehicle_interface/include/vehicle_interface/vehicle_interface.hpp",
    "modules/common/include/common/types.hpp",
]
CORE_SOURCES = ["core.cpp", "stop_signal.cpp", "settings.cpp"]
FLAGS = ["-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic"]


def _compiler() -> str:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    assert compiler is not None
    return compiler


def _build_core(tmp_path: Path) -> Path:
    binary = tmp_path / "core_test"
    subprocess.run(
        [_compiler(), *FLAGS, f"-I{MODULE / 'include'}", f"-I{INTERFACES}", f"-I{HERE}",
         str(HERE / "core_test.cpp"), *[str(MODULE / "src" / s) for s in CORE_SOURCES], "-o", str(binary)],
        check=True,
    )
    return binary


def test_core(tmp_path: Path) -> None:
    binary = _build_core(tmp_path)
    result = subprocess.run([str(binary)], capture_output=True, text=True,
                            env={**os.environ, "TMPDIR": str(tmp_path)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "core_test: all passed" in result.stdout


def _f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def test_vectors_against_python_zlib_and_struct(tmp_path: Path) -> None:
    """Each command and warning request the module forms, recomputed here with zlib and struct."""
    binary = _build_core(tmp_path)
    out = subprocess.run([str(binary), "--vectors"], capture_output=True, text=True, check=True).stdout
    commands = [line.split() for line in out.splitlines() if line.startswith("CMD ")]
    warnings = [line.split() for line in out.splitlines() if line.startswith("WRN ")]
    assert len(commands) == 5 and len(warnings) == 3
    for _, steer, accel, issue, seq, payload_hex in commands:
        payload = bytes.fromhex(payload_hex)
        assert len(payload) == 24
        acceleration, steering_angle, issue_time, sequence, check = struct.unpack("<ffdII", payload)
        assert acceleration == _f32(float(accel))
        # MAP-DRIVING-DA-COMMAND: steeringAngle = -steering[1] * 180 / pi
        assert struct.pack("<f", steering_angle) == struct.pack("<f", _f32(-float(steer) * 180.0 / math.pi))
        assert issue_time == float(issue)
        assert sequence == int(seq)
        assert check == zlib.crc32(payload[:20])
    for _, requested, issue, payload_hex in warnings:
        assert bytes.fromhex(payload_hex) == struct.pack(">II", int(requested), round(float(issue) * 1000.0))


def _pin_tree() -> Path | None:
    clone = os.environ.get("VISIONPILOT_CLONE")
    if not clone:
        return None
    probe = subprocess.run(["git", "-C", clone, "cat-file", "-e", f"{PIN}^{{commit}}"], capture_output=True)
    return Path(clone) if probe.returncode == 0 else None


def _opencv_include() -> Path | None:
    """The OpenCV 4 include directory: pkg-config's, else the distribution's. The Jetson's opencv4.pc names
    /usr/local/include/opencv4, which does not exist; its headers are in /usr/include/opencv4."""
    candidates: list[Path] = []
    if shutil.which("pkg-config") is not None:
        flags = subprocess.run(["pkg-config", "--cflags-only-I", "opencv4"], capture_output=True, text=True)
        if flags.returncode == 0:
            candidates += [Path(f[2:]) for f in flags.stdout.split() if f.startswith("-I")]
    candidates.append(Path("/usr/include/opencv4"))
    return next((c for c in candidates if (c / "opencv2" / "core" / "mat.hpp").is_file()), None)


def test_adapters_against_upstream_headers(tmp_path: Path) -> None:
    clone = _pin_tree()
    if clone is None:
        pytest.skip(f"VISIONPILOT_CLONE is not set to a clone holding {PIN}")
    opencv_include = _opencv_include()
    if opencv_include is None:
        pytest.skip("no OpenCV 4 headers (opencv2/core/mat.hpp) found")
    include = tmp_path / "upstream"
    for path in UPSTREAM_HEADERS:
        text = subprocess.run(["git", "-C", str(clone), "show", f"{PIN}:VisionPilot/{path}"],
                              capture_output=True, check=True).stdout
        target = include / path.split("/include/", 1)[1]
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(text)
    binary = tmp_path / "adapters_test"
    sources = [*CORE_SOURCES, "adapters.cpp", "score_interface.cpp"]
    subprocess.run(
        [_compiler(), *FLAGS, f"-I{MODULE / 'include'}", f"-I{INTERFACES}", f"-I{HERE}", f"-I{include}",
         f"-I{opencv_include}", str(HERE / "adapters_test.cpp"), *[str(MODULE / "src" / s) for s in sources],
         "-lopencv_core", "-o", str(binary)],
        check=True,
    )
    result = subprocess.run([str(binary)], capture_output=True, text=True,
                            env={**os.environ, "TMPDIR": str(tmp_path)})
    assert result.returncode == 0, result.stdout + result.stderr
    assert "adapters_test: all passed" in result.stdout


def test_lola_bindings_syntax_against_local_mock() -> None:
    if not (MWCOM_MOCK / "score" / "mw" / "com" / "types.h").is_file():
        pytest.skip("the closed-loop driving bench's mw::com mock is not present")
    subprocess.run(
        [_compiler(), "-std=c++17", "-Wall", "-Wextra", "-Werror", "-fsyntax-only", f"-I{MODULE / 'include'}",
         f"-I{INTERFACES}", f"-I{MWCOM_MOCK}", str(MODULE / "src" / "lola_bindings.cpp")],
        check=True,
    )


def _patch_files(diff: str) -> dict[str, list[str]]:
    """Maps each file of a git diff to its lines."""
    files: dict[str, list[str]] = {}
    current: list[str] | None = None
    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            current = files.setdefault(line.split(" b/", 1)[1], [])
            continue
        if current is not None:
            current.append(line)
    return files


def _new_file_text(lines: list[str]) -> str:
    assert "new file mode 100644" in lines[0]
    body = lines[lines.index(next(l for l in lines if l.startswith("@@ -0,0 "))) + 1:]
    added = []
    for line in body:
        if line.startswith("+"):
            added.append(line[1:])
        elif line == "\\ No newline at end of file":
            raise AssertionError("every new file ends with a newline")
        elif line == "":
            continue
        else:
            raise AssertionError(f"unexpected line in a new file: {line!r}")
    return "\n".join(added) + "\n"


def test_patch_new_files_equal_module_tree() -> None:
    files = _patch_files((PATCHES / "0002-de4sdv-score-interface.diff").read_text())
    new = {p[len(PATCH_MODULE_PREFIX):]: lines for p, lines in files.items() if p.startswith(PATCH_MODULE_PREFIX)}
    tree = {p.relative_to(MODULE).as_posix() for p in MODULE.rglob("*") if p.is_file()}
    assert set(new) == tree
    for relative, lines in new.items():
        assert _new_file_text(lines) == (MODULE / relative).read_text(), relative


def test_patch_shas() -> None:
    sums = {}
    for line in (PATCHES / "SHA256SUMS").read_text().splitlines():
        digest, name = line.split()
        sums[name] = digest
    assert set(sums) == {"0001-de4sdv-visualization-recorder.diff", "0002-de4sdv-score-interface.diff"}
    for name, digest in sums.items():
        assert hashlib.sha256((PATCHES / name).read_bytes()).hexdigest() == digest, name
    assert sums["0001-de4sdv-visualization-recorder.diff"] == VIS8_SHA256


def test_upstream_cpp_additions_are_guarded() -> None:
    """Outside the one enum line, every line 0002 adds to upstream C++ lies under #if ENABLE_SCORE_INTERFACE, except
    source_label's case for the new enumerator, which parse_source_mode reaches only under that macro."""
    files = _patch_files((PATCHES / "0002-de4sdv-score-interface.diff").read_text())
    upstream_cpp = [p for p in files if not p.startswith(PATCH_MODULE_PREFIX) and p.endswith((".cpp", ".hpp"))]
    assert sorted(upstream_cpp) == [
        "VisionPilot/app/vision_pilot.cpp",
        "VisionPilot/modules/config/include/config/vision_pilot_config.hpp",
        "VisionPilot/modules/config/src/vision_pilot_config.cpp",
    ]
    unguarded: list[str] = []
    removed: list[str] = []
    for path in upstream_cpp:
        depth = 0
        for line in files[path]:
            if line.startswith(("+++", "---")):
                continue
            if line.startswith("-"):
                removed.append(line[1:])
            if not line.startswith("+"):
                continue
            text = line[1:].strip()
            if text == "#if ENABLE_SCORE_INTERFACE":
                depth += 1
                continue
            if text.startswith("#endif") and depth > 0:
                depth -= 1
                continue
            if depth == 0:
                unguarded.append(text)
    assert removed == ["enum class SourceMode { Ros2 = 0, V4l2 = 1, Video = 2 };"]
    assert unguarded == [
        "enum class SourceMode { Ros2 = 0, V4l2 = 1, Video = 2, Score = 3 /* DE4SDV S-CORE interface */ };",
        'case SourceMode::Score: return "score";  // DE4SDV S-CORE interface',
    ]
