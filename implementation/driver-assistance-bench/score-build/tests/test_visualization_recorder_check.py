"""The visualization recorder's check binary of the S-CORE build (the owner's decision of 2026-11-17: the recorder in
every run of mode full).

The Launch Manager starts vision_pilot with exactly its configured environment, so whether GStreamer's nvh264enc opens
and encodes there can only be shown on the S-CORE host, with the same OpenCV (static, GStreamer back end), the same
GStreamer libraries and the same toolchain as vision_pilot. bin/visualization_recorder_check is
score-interface/tests/visualization_recorder_sim_time_test.cpp (the functional test of the sim_time_s column) built in
the bazel stage against //visionpilot:de4sdv_visualization_recorder, as ort_cuda_check is for ONNX Runtime. The
staging never stages it (stage_score_side.py stages the binaries it names), so no identity record changes.
"""

from __future__ import annotations

import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
BUILD = BENCH / "score-build" / "build_score_bench.sh"
WS_BUILD = BENCH / "score-build" / "workspace" / "BUILD.bazel"
STAGE = BENCH / "score-path" / "scripts" / "stage_score_side.py"
TARGET = "//de4sdv_da_bench/score-build/workspace:visualization_recorder_check"


def _code(path: Path) -> str:
    return "\n".join(ln for ln in path.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("#"))


def test_the_workspace_builds_the_recorder_test_against_the_candidates_recorder() -> None:
    text = _code(WS_BUILD)
    m = re.search(r'cc_binary\(\s*name = "visualization_recorder_check",(.*?)\n\)', text, re.S)
    assert m, "no cc_binary visualization_recorder_check"
    body = m.group(1)
    assert 'srcs = ["visualization_recorder_check.cpp"]' in body
    assert '"//visionpilot:de4sdv_visualization_recorder"' in body
    # the same link as VisionPilot: the Ubuntu 22.04 GStreamer libraries carry newer glibc symbol versions
    assert '"-Wl,--allow-shlib-undefined"' in body and '"-Wl,-rpath,$$ORIGIN/../lib"' in body


def test_the_build_copies_the_test_source_builds_the_target_and_bundles_it() -> None:
    text = _code(BUILD)
    assert ('cp "$BENCH/score-interface/tests/visualization_recorder_sim_time_test.cpp" '
            '"$OVERLAY/score-build/workspace/visualization_recorder_check.cpp"') in text
    targets = re.search(r"TARGETS=\((.*?)\)", text, re.S).group(1).split()
    assert TARGET in targets
    assert '"$SB/de4sdv_da_bench/score-build/workspace/visualization_recorder_check" "$B/bin/"' in text


def test_the_staging_never_stages_the_check() -> None:
    assert "visualization_recorder_check" not in STAGE.read_text(encoding="utf-8")
