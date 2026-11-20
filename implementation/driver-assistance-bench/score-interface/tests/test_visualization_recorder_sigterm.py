"""The visualization recording closes well when the candidate is stopped as the Launch Manager stops it (the owner's
decision of 2026-11-17 keeps the recorder in every run).

The Launch Manager ends vision_pilot with SIGTERM (at the session's score_stop, stop_score_side.sh). Patch 0002 makes
the candidate leave its loop on that signal (stop_signal.cpp: a sigaction handler without SA_RESTART that only sets a
flag; vision_pilot.cpp breaks the loop and runs the shutdown after it), and patch 0001's shutdown calls the recorder's
stop(): drain, close the encoder (EOS: the muxer finalizes the file), write the summary. The check binary
(visualization_recorder_sim_time_test.cpp, bundled as bin/visualization_recorder_check) has the same order in its
`until-sigterm` mode, so a SIGTERM mid-encode can be shown on the S-CORE host with nvh264enc under the Launch
Manager's exact environment. Here the same source runs the recorder's GStreamer route with x264enc in place of
nvh264enc (DE4SDV_VISUALIZATION_GST_ENCODER; this host has no NVENC): after the SIGTERM the process ends 0, the
summary exists, and ffprobe reads a duration and as many frames as frames.csv has rows.
"""

from __future__ import annotations

import json
import os
import signal
import shutil
import subprocess
import time
from pathlib import Path

import pytest

from test_score_interface import HERE, PATCHES, PIN, _compiler, _opencv_include

SOURCE = HERE / "visualization_recorder_sim_time_test.cpp"


def _gst_has(element: str) -> bool:
    return shutil.which("gst-inspect-1.0") is not None and subprocess.run(
        ["gst-inspect-1.0", element], capture_output=True).returncode == 0


@pytest.fixture(scope="module")
def check_binary(tmp_path_factory: pytest.TempPathFactory) -> Path:
    clone = os.environ.get("VISIONPILOT_CLONE")
    ort, eigen = os.environ.get("ORT_INCLUDE"), os.environ.get("EIGEN_INCLUDE")
    if not clone or not ort or not eigen:
        pytest.skip("needs VISIONPILOT_CLONE, ORT_INCLUDE and EIGEN_INCLUDE")
    opencv_include = _opencv_include()
    if opencv_include is None:
        pytest.skip("no OpenCV 4 headers")
    for tool, why in (("ffprobe", "ffprobe"),):
        if shutil.which(tool) is None:
            pytest.skip(f"no {why}")
    for element in ("x264enc", "h264parse", "matroskamux", "videoconvert", "appsrc"):
        if not _gst_has(element):
            pytest.skip(f"GStreamer has no {element}")
    tmp = tmp_path_factory.mktemp("sigterm")
    tree = tmp / "vp"
    subprocess.run(["git", "clone", "-q", "--shared", "--no-checkout", clone, str(tree)], check=True)
    subprocess.run(["git", "-C", str(tree), "sparse-checkout", "set", "--no-cone", "/*", "!*.onnx", "!*.pt", "!*.pth",
                    "!*.mp4"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tree), "checkout", "-q", PIN], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(tree), "apply", str(PATCHES / "0001-de4sdv-visualization-recorder.diff")],
                   check=True)
    vp = tree / "VisionPilot"
    includes = [f"-I{d}" for d in sorted((vp / "modules").rglob("include")) if d.is_dir()]
    binary = tmp / "visualization_recorder_check"
    subprocess.run([_compiler(), "-std=c++17", "-O1", *includes, f"-I{ort}", f"-I{eigen}", f"-I{opencv_include}",
                    str(SOURCE), str(vp / "modules/de4sdv/visualization_recorder/src/visualization_recorder.cpp"),
                    str(vp / "modules/visualization/src/visual_interface.cpp"), "-o", str(binary),
                    "-lopencv_videoio", "-lopencv_imgcodecs", "-lopencv_imgproc", "-lopencv_highgui", "-lopencv_core",
                    "-lpthread"], check=True)
    return binary


def _ffprobe(video: Path) -> dict:
    p = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-show_entries",
                        "stream=codec_name,nb_read_frames:format=duration", "-of", "json", str(video)],
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def test_a_sigterm_mid_encode_ends_the_loop_and_closes_the_video(check_binary: Path, tmp_path: Path) -> None:
    video = tmp_path / "visualization.mkv"
    env = {"PATH": os.environ.get("PATH", "/usr/bin:/bin"), "DE4SDV_VISUALIZATION_RECORD": str(video),
           "DE4SDV_VISUALIZATION_GST_ENCODER": "x264enc", "HOME": str(tmp_path)}
    p = subprocess.Popen([str(check_binary), "100000", "until-sigterm"], env=env, stdout=subprocess.PIPE,
                         stderr=subprocess.STDOUT, text=True)
    try:
        csv = Path(str(video) + ".frames.csv")
        t0 = time.monotonic()
        while time.monotonic() - t0 < 60 and (not csv.is_file() or len(csv.read_text().splitlines()) < 20):
            time.sleep(0.1)
        assert p.poll() is None, "the check ended before the SIGTERM: " + (p.stdout.read() if p.stdout else "")
        p.send_signal(signal.SIGTERM)   # mid-encode, as the Launch Manager stops vision_pilot
        out, _ = p.communicate(timeout=60)
    finally:
        if p.poll() is None:
            p.kill()
    assert p.returncode == 0, f"rc {p.returncode}: the SIGTERM killed the process instead of ending its loop\n{out}"
    assert "STOP: SIGTERM" in out, out
    summary = Path(str(video) + ".summary.txt")
    assert summary.is_file(), "no summary: the recorder's stop() never ran"
    assert "encoder_open=1" in summary.read_text()
    rows = len(csv.read_text().splitlines()) - 1
    probe = _ffprobe(video)
    (stream,) = probe["streams"]
    assert stream["codec_name"] == "h264"
    assert int(stream["nb_read_frames"]) == rows >= 20, (stream, rows)
    assert float(probe["format"]["duration"]) > 0, probe


def test_the_check_keeps_its_counted_mode() -> None:
    # the unit test of the sim_time_s column runs the check with a pass count and no signal
    text = SOURCE.read_text()
    assert 'argc > 1 ? std::atoi(argv[1]) : 30' in text
    assert "until-sigterm" in text and "sigaction(SIGTERM" in text
