"""Builds and runs the unit tests of the DE4SDV S-CORE interface for VisionPilot, and checks the patch series.

- core_test.cpp: the module's core against the bench's payloads.h only (runs wherever g++ runs).
- the vectors of core_test --vectors against Python's zlib and struct, computed here at test time.
- adapters_test.cpp: the adapters against upstream's real headers at the pin and OpenCV 4. It needs a local
  VisionPilot clone that holds the pin (VISIONPILOT_CLONE) and pkg-config's opencv4; it is skipped, with the reason,
  where either is missing.
- src/lola_bindings.cpp: a syntax check against the closed-loop driving bench's local mw::com mock, which is no
  S-CORE header; the real compile is the S-CORE Bazel build's.
- src/lifecycle_bindings.cpp: a syntax check against declarations of the Lifecycle v0.10.0 API
  (launch-manager/tests/lifecycle_mock), which are no S-CORE header either.
- the patch series: the new files of 0002 equal module/, the shas equal patches/SHA256SUMS, 0001 is the VIS8 patch
  with the sim_time_s column of frames.csv (brief item B3) and its upstream hunks unchanged, every line 0002 adds
  to upstream C++ outside the enum sits under ENABLE_SCORE_INTERFACE, the alive call sits in the pass with a result
  (C-1), and 0003 guards LocalDisplay's cv::destroyAllWindows() with show_window_ (C-2).
- the sim_time_s column: a functional run of the patched recorder with a stand-in ffmpeg, when a VisionPilot clone
  (VISIONPILOT_CLONE), ONNX Runtime and Eigen headers (ORT_INCLUDE, EIGEN_INCLUDE) and pkg-config's opencv4 are there.
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
LIFECYCLE_MOCK = ROOT.parent / "launch-manager" / "tests" / "lifecycle_mock"
PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"
VIS8_SHA256 = "29a1f5d0a087b05f1b8e2e2d57cd6fd5f818d9a2d996fe2b0256f254c2a5ad27"  # the VIS8 patch as delivered
# sha256 of the upstream-file sections (VisionPilot/CMakeLists.txt, app/CMakeLists.txt, app/vision_pilot.cpp) of the
# VIS8 patch as delivered, joined by newlines; computed with Python's hashlib from that file. B3 leaves them unchanged.
VIS8_UPSTREAM_SECTIONS_SHA256 = "9775468e4909bb58d427081625d6b2593d10222b7ca1c6bf43ea2b1d9722b70b"
RECORDER_PREFIX = "VisionPilot/modules/de4sdv/visualization_recorder/"
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


def test_lifecycle_bindings_syntax_against_the_api_declarations() -> None:
    """src/lifecycle_bindings.cpp against the Lifecycle v0.10.0 API as launch-manager/tests/lifecycle_mock declares
    it; the real compile is the S-CORE Bazel build's."""
    subprocess.run(
        [_compiler(), "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", "-fsyntax-only",
         f"-I{MODULE / 'include'}", f"-I{INTERFACES}", f"-I{LIFECYCLE_MOCK}",
         str(MODULE / "src" / "lifecycle_bindings.cpp")],
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
    assert set(sums) == {"0001-de4sdv-visualization-recorder.diff", "0002-de4sdv-score-interface.diff",
                         "0003-de4sdv-headless-display.diff"}
    for name, digest in sums.items():
        assert hashlib.sha256((PATCHES / name).read_bytes()).hexdigest() == digest, name
    # 0001 is no longer the VIS8 patch byte for byte: B3 added the sim_time_s column (test below)
    assert sums["0001-de4sdv-visualization-recorder.diff"] != VIS8_SHA256


def _sections(diff: str) -> dict[str, list[str]]:
    out: dict[str, list[str]] = {}
    current = None
    for line in diff.split("\n"):
        if line.startswith("diff --git "):
            current = line.split(" b/", 1)[1]
            out[current] = []
        if current is not None:
            out[current].append(line)
    return out


def test_0001_keeps_the_vis8_upstream_hunks_and_adds_the_sim_time_column() -> None:
    sections = _sections((PATCHES / "0001-de4sdv-visualization-recorder.diff").read_text())
    upstream = [p for p in sections if not p.startswith(RECORDER_PREFIX)]
    assert upstream == ["VisionPilot/CMakeLists.txt", "VisionPilot/app/CMakeLists.txt", "VisionPilot/app/vision_pilot.cpp"]
    joined = "\n".join("\n".join(sections[p]) for p in upstream)
    assert hashlib.sha256(joined.encode()).hexdigest() == VIS8_UPSTREAM_SECTIONS_SHA256
    header = "\n".join(sections[RECORDER_PREFIX + "include/de4sdv/visualization_recorder.hpp"])
    source = "\n".join(sections[RECORDER_PREFIX + "src/visualization_recorder.cpp"])
    assert "+        void set_pass_sim_time(double sim_time_s) { pass_sim_time_s_ = sim_time_s; }" in header
    assert '+                               "t_encoded_ns,sim_time_s\\n");' in source
    assert '+                        std::fprintf(csv_, "%llu,%llu,%lld,%lld,%lld,%lld,%lld,%s\\n",' in source
    # the time is taken for one hand-off only, never carried into the next pass
    assert "+        pass_sim_time_s_ = std::numeric_limits<double>::quiet_NaN();" in source


def test_0002_hands_the_pass_capture_time_to_the_recorder() -> None:
    files = _patch_files((PATCHES / "0002-de4sdv-score-interface.diff").read_text())
    added = [line[1:].strip() for line in files["VisionPilot/app/vision_pilot.cpp"] if line.startswith("+")]
    call = "visualization_recorder->set_pass_sim_time(score_interface->pass_capture_time_s());"
    assert call in added
    publish = added.index("if (score_interface) score_interface->warning_request_publisher().Publish(plan);")
    assert publish < added.index(call)  # in the same guarded block, before the recorder's hand-off
    context = files["VisionPilot/app/vision_pilot.cpp"]
    handoff = next(i for i, line in enumerate(context) if "DE4SDV VIS8: the one hand-off" in line)
    assert next(i for i, line in enumerate(context) if call in line) < handoff


CYCLE_CALL = "if (score_interface) score_interface->CycleCompleted();"
PUBLISH_CALL = "if (score_interface) score_interface->warning_request_publisher().Publish(plan);"
RESULT_BLOCK = "if (const auto r = pipeline.process(warped, resized))"


def _hunks(lines: list[str]) -> list[list[str]]:
    hunks: list[list[str]] = []
    for line in lines:
        if line.startswith("@@ "):
            hunks.append([])
        elif hunks:
            hunks[-1].append(line)
    return hunks


def test_0002_reports_running_only_in_a_pass_with_a_result() -> None:
    """C-1 (p10-1 run 20261119T134840Z): upstream's pipeline returns no result for the first frame (a two-frame
    buffer, VisionPilot/modules/models/src/inference.cpp:152-159 at the pin), so a call at the end of the loop body
    reported running after a pass that ran no network and put the cold first inference under the alive supervision.
    The one CycleCompleted() call sits inside the result block, after the warning hand-off."""
    vp = _patch_files((PATCHES / "0002-de4sdv-score-interface.diff").read_text())["VisionPilot/app/vision_pilot.cpp"]
    added = [line for line in vp if line.startswith("+") and CYCLE_CALL in line]
    assert len(added) == 1, added
    # the result block's indentation (12 spaces), not the loop body's (8)
    assert added[0][1:] == " " * 12 + CYCLE_CALL
    hunk = next(h for h in _hunks(vp) if any(CYCLE_CALL in line for line in h))
    texts = [line[1:] for line in hunk]
    call = next(i for i, t in enumerate(texts) if CYCLE_CALL in t)
    publish = next(i for i, t in enumerate(texts) if PUBLISH_CALL in t)
    assert publish < call
    # nothing between the hand-off and the call leaves the result block
    assert not any(t.startswith("        }") for t in texts[publish:call]), texts[publish:call]
    # the end of the loop body, after the recorder's loop stamps, gets no call
    assert not any("loop_stamps.push(" in t for t in texts[:call])


def _block(text: str, head: str) -> str:
    """The text between the braces of the block that opens after `head` (no braces in its strings or comments)."""
    start = text.index("{", text.index(head))
    depth = 0
    for i in range(start, len(text)):
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        if depth == 0:
            return text[start:i + 1]
    raise AssertionError(f"the block after {head!r} does not close")


def test_patched_loop_reports_running_only_inside_the_result_block(tmp_path: Path) -> None:
    """C-1 on upstream's file at the pin with 0001 and 0002 applied: the call lies in the block that runs only when
    pipeline.process() returned a result, after the warning hand-off, and nowhere else."""
    clone = _pin_tree()
    if clone is None:
        pytest.skip(f"VISIONPILOT_CLONE is not set to a clone holding {PIN}")
    tree = tmp_path / "vp"
    target = tree / "VisionPilot" / "app" / "vision_pilot.cpp"
    target.parent.mkdir(parents=True)
    target.write_bytes(subprocess.run(["git", "-C", str(clone), "show", f"{PIN}:VisionPilot/app/vision_pilot.cpp"],
                                      check=True, capture_output=True).stdout)
    subprocess.run(["git", "-C", str(tree), "init", "-q"], check=True)
    for patch in ("0001-de4sdv-visualization-recorder.diff", "0002-de4sdv-score-interface.diff"):
        subprocess.run(["git", "-C", str(tree), "apply", "--include=VisionPilot/app/vision_pilot.cpp",
                        str(PATCHES / patch)], check=True)
    text = target.read_text()
    assert text.count(CYCLE_CALL) == 1
    block = _block(text, RESULT_BLOCK)
    assert CYCLE_CALL in block
    assert block.index(PUBLISH_CALL) < block.index(CYCLE_CALL)


DESTROY = "cv::destroyAllWindows();"
GUARDED_DESTROY = "if (show_window_) cv::destroyAllWindows();"
LOCAL_DISPLAY = "VisionPilot/modules/visualization/src/local_display.cpp"


def test_0003_guards_both_destroy_all_windows_calls_with_show_window() -> None:
    """C-2: upstream's LocalDisplay calls cv::destroyAllWindows() unconditionally in its destructor and in stop()
    (local_display.cpp:18 and :106 at the pin), though it opens a window only when show_window_ (:13). OpenCV 4.6.0
    built without a GUI backend throws there (window.cpp:1258-1262), so the headless candidate aborted at its exit and
    lost its supervision.stop record and counters. 0003 changes exactly these two lines."""
    files = _patch_files((PATCHES / "0003-de4sdv-headless-display.diff").read_text())
    assert list(files) == [LOCAL_DISPLAY]
    lines = files[LOCAL_DISPLAY]
    removed = [line[1:] for line in lines if line.startswith("-") and not line.startswith("---")]
    added = [line[1:] for line in lines if line.startswith("+") and not line.startswith("+++")]
    assert [r.strip() for r in removed] == [DESTROY, DESTROY]
    assert len(added) == 2
    for old, new in zip(removed, added):
        assert new.startswith(old[: len(old) - len(old.lstrip())] + GUARDED_DESTROY), new  # same indentation
    hunks = _hunks(lines)
    assert len(hunks) == 2
    assert any("LocalDisplay::~LocalDisplay()" in line for line in hunks[0])
    assert any("bool LocalDisplay::stop()" in line for line in hunks[1])


def _series() -> list[Path]:
    """The candidate's series in apply order (score-interface/series.sh; DA_CANDIDATE, default pin: 0001-0003)."""
    out = subprocess.run(["bash", str(ROOT / "series.sh"), "list"], check=True, capture_output=True, text=True)
    return [Path(line) for line in out.stdout.split()]


def test_patched_local_display_destroys_windows_only_with_show_window(tmp_path: Path) -> None:
    """C-2 on upstream's file at the pin with the whole series of the candidate (DA_CANDIDATE) applied in order:
    every cv::destroyAllWindows() of LocalDisplay is guarded by show_window_, in the destructor and in stop()."""
    clone = _pin_tree()
    if clone is None:
        pytest.skip(f"VISIONPILOT_CLONE is not set to a clone holding {PIN}")
    tree = tmp_path / "vp"
    target = tree / LOCAL_DISPLAY
    target.parent.mkdir(parents=True)
    target.write_bytes(subprocess.run(["git", "-C", str(clone), "show", f"{PIN}:{LOCAL_DISPLAY}"],
                                      check=True, capture_output=True).stdout)
    subprocess.run(["git", "-C", str(tree), "init", "-q"], check=True)
    for patch in _series():
        subprocess.run(["git", "-C", str(tree), "apply", f"--include={LOCAL_DISPLAY}", str(patch)], check=True)
    text = target.read_text()
    calls = [line.strip() for line in text.splitlines() if DESTROY in line]
    assert len(calls) == 2 and all(c.startswith(GUARDED_DESTROY) for c in calls), calls
    assert GUARDED_DESTROY in _block(text, "LocalDisplay::~LocalDisplay()")
    assert GUARDED_DESTROY in _block(text, "bool LocalDisplay::stop()")


PR427_LINES = {  # the lines 0004 ports from upstream PR #427 (a38f227c), as they land in the patched tree
    "VisionPilot/app/vision_pilot.cpp":
        "const double cipo_v = has_cipo ? ego_v + r->cipo.velocity_ms : cfg.speed_limit;",
    "VisionPilot/modules/safety_guardian/planning/src/longitudinal_planning.cpp":
        "double delta_v = ego_v - cipo_v; // cipo_v is the lead's speed",
    "VisionPilot/modules/safety_guardian/fusion/src/longitudinal_fusion.cpp":
        "const bool ad_only_allowed = !cfg_.ad_only_needs_as_track || as_track_;",
    "VisionPilot/modules/safety_guardian/fusion/include/fusion/longitudinal_fusion.hpp":
        "bool  ad_only_needs_as_track = true;",
    "VisionPilot/modules/config/src/vision_pilot_config.cpp":
        'optional(kv, "fusion.ad_only_needs_as_track", "true"), "fusion.ad_only_needs_as_track");',
}


def test_the_candidates_whole_series_applies_at_the_pin(tmp_path: Path) -> None:
    """Every file the candidate's series (DA_CANDIDATE) touches, taken from the pin, with every patch applied whole
    and in order with git apply. The pin's series leaves the PR #427 lines out; the pr427 series has each of them,
    and its longitudinal_planning.cpp is upstream's file at a38f227c byte for byte when the clone holds that commit."""
    clone = _pin_tree()
    if clone is None:
        pytest.skip(f"VISIONPILOT_CLONE is not set to a clone holding {PIN}")
    series = _series()
    names = [p.name for p in series]
    candidate = os.environ.get("DA_CANDIDATE", "pin")
    assert names[:3] == ["0001-de4sdv-visualization-recorder.diff", "0002-de4sdv-score-interface.diff",
                         "0003-de4sdv-headless-display.diff"]
    assert names[3:] == ({"pin": [], "pr427": ["0004-de4sdv-port-of-upstream-pr427.diff"]}[candidate])
    tree = tmp_path / "vp"
    tree.mkdir()
    subprocess.run(["git", "-C", str(tree), "init", "-q"], check=True)
    touched = sorted({line.split(" b/", 1)[1] for p in series for line in p.read_text().splitlines()
                      if line.startswith("diff --git ")} | set(PR427_LINES))
    for path in touched:
        shown = subprocess.run(["git", "-C", str(clone), "show", f"{PIN}:{path}"], capture_output=True)
        if shown.returncode == 0:
            (tree / path).parent.mkdir(parents=True, exist_ok=True)
            (tree / path).write_bytes(shown.stdout)
    for patch in series:
        applied = subprocess.run(["git", "-C", str(tree), "apply", "--check", str(patch)], capture_output=True,
                                 text=True)
        assert applied.returncode == 0, (patch.name, applied.stderr)
        subprocess.run(["git", "-C", str(tree), "apply", str(patch)], check=True)
    for path, line in PR427_LINES.items():
        present = line in (tree / path).read_text()
        assert present == (candidate == "pr427"), (candidate, path)
    if candidate == "pr427":
        planner = "VisionPilot/modules/safety_guardian/planning/src/longitudinal_planning.cpp"
        upstream = subprocess.run(["git", "-C", str(clone), "rev-parse", "--verify", "-q", f"a38f227c:{planner}"],
                                  capture_output=True, text=True)
        if upstream.returncode == 0:
            ours = subprocess.run(["git", "hash-object", str(tree / planner)], check=True, capture_output=True,
                                  text=True)
            assert ours.stdout.strip() == upstream.stdout.strip()


def test_visualization_recorder_writes_the_sim_time_column(tmp_path: Path) -> None:
    clone = os.environ.get("VISIONPILOT_CLONE")
    ort, eigen = os.environ.get("ORT_INCLUDE"), os.environ.get("EIGEN_INCLUDE")
    if not clone or not ort or not eigen:
        pytest.skip("needs VISIONPILOT_CLONE, ORT_INCLUDE and EIGEN_INCLUDE")
    if subprocess.run(["git", "-C", clone, "cat-file", "-e", PIN + "^{commit}"], capture_output=True).returncode:
        pytest.skip(f"{clone} does not hold {PIN}")
    opencv_include = _opencv_include()
    if opencv_include is None:
        pytest.skip("no OpenCV 4 headers")
    libs = ["-lopencv_videoio", "-lopencv_imgcodecs", "-lopencv_imgproc", "-lopencv_highgui", "-lopencv_core"]
    tree = tmp_path / "vp"
    subprocess.run(["git", "clone", "-q", "--shared", "--no-checkout", clone, str(tree)], check=True)
    subprocess.run(["git", "-C", str(tree), "sparse-checkout", "set", "--no-cone", "/*", "!*.onnx", "!*.pt", "!*.pth",
                    "!*.mp4"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tree), "checkout", "-q", PIN], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tree), "apply", str(PATCHES / "0001-de4sdv-visualization-recorder.diff")],
                   check=True)
    vp = tree / "VisionPilot"
    includes = [f"-I{d}" for d in sorted((vp / "modules").rglob("include")) if d.is_dir()]
    binary = tmp_path / "sim_time_test"
    subprocess.run([_compiler(), "-std=c++17", "-O1", *includes, f"-I{ort}", f"-I{eigen}", f"-I{opencv_include}",
                    str(HERE / "visualization_recorder_sim_time_test.cpp"),
                    str(vp / "modules/de4sdv/visualization_recorder/src/visualization_recorder.cpp"),
                    str(vp / "modules/visualization/src/visual_interface.cpp"), "-o", str(binary),
                    *libs, "-lpthread"], check=True)
    fake = tmp_path / "bin"
    fake.mkdir()
    (fake / "ffmpeg").write_text("#!/bin/sh\ncat > /dev/null\n")
    (fake / "ffmpeg").chmod(0o755)
    video = tmp_path / "visualization.mkv"
    env = {**os.environ, "PATH": f"{fake}:{os.environ['PATH']}", "DE4SDV_VISUALIZATION_RECORD": str(video),
           "DE4SDV_VISUALIZATION_ENCODER": "ffmpeg"}
    result = subprocess.run([str(binary), "30"], capture_output=True, text=True, env=env, timeout=120)
    assert result.returncode == 0, result.stdout + result.stderr
    rows = (tmp_path / "visualization.mkv.frames.csv").read_text().splitlines()
    assert rows[0].split(",")[-1] == "sim_time_s"
    assert len(rows) > 10
    seen_empty = seen_time = False
    for row in rows[1:]:
        cells = row.split(",")
        assert len(cells) == len(rows[0].split(","))
        frame_id = int(cells[1])
        if frame_id % 3 == 0:
            assert cells[-1] == "", row  # no time given for this pass, none inherited
            seen_empty = True
        else:
            assert math.isclose(float(cells[-1]), 100.0 + 0.05 * frame_id, abs_tol=5e-7), row
            seen_time = True
    assert seen_empty and seen_time


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
