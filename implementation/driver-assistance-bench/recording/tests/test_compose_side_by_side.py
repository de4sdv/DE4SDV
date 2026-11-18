"""The side-by-side composition on short synthetic videos made here with ffmpeg.

Each synthetic frame is one flat luma level, so the frame a pane shows can be read back from the output's pixels.
The expected frame of every output frame is computed here from the synthetic times, with a stall in the chase view,
independently of the composer's own code; the digests are recomputed with hashlib.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from bisect import bisect_right
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
COMPOSE = HERE.parent / "compose_side_by_side.py"
FPS = 20
T0 = 1795000000.0            # a fixed UTC start
OFFSET = 0.5                 # the IVI clock runs 0.5 s ahead of the host's
STALL_AT, STALL_S = 20, 1.0  # chase frame 20 and later arrive 1 s late
DISP0 = 0.313                # the display's first frame, host time after T0
START = 0.337                # the output's start: no output frame time coincides with a source frame time

sys.path.insert(0, str(HERE.parent))
from compose_side_by_side import INSET_H, INSET_W, INSET_X, INSET_Y, PANE_H, PANE_W, PANE_Y  # noqa: E402

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg is not installed")


def flat_video(path: Path, levels: list[int], w: int, h: int, fps: int) -> None:
    raw = b"".join(bytes([v]) * (w * h) + bytes([128]) * (w * h // 2) for v in levels)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s", f"{w}x{h}", "-r",
                    str(fps), "-i", "-", "-c:v", "libx264", "-qp", "0", "-pix_fmt", "yuv420p", str(path)],
                   input=raw, check=True)


def chase_level(i: int) -> int:
    return 20 + 5 * i


def display_level(j: int) -> int:
    return 30 + 6 * j


def inset_level(m: int) -> int:
    return 100 + 4 * m


@pytest.fixture()
def run_dir(tmp_path: Path) -> Path:
    d = tmp_path / "run"
    (d / "cap").mkdir(parents=True)
    chase_n, disp_n, inset_n = 40, 30, 20
    flat_video(d / "chase_view.mp4", [chase_level(i) for i in range(chase_n)], 64, 36, FPS)
    with open(d / "chase_view.mp4.frames.csv", "w") as f:
        f.write("video_index,carla_frame,sim_time_s,arrival_unix_s\n")
        for i in range(chase_n):
            f.write("%d,%d,%.6f,%.6f\n" % (i, 500 + i, i * 0.05, T0 + i * 0.05 + (STALL_S if i >= STALL_AT else 0)))
    flat_video(d / "cap" / "seg_1.mp4", [display_level(j) for j in range(disp_n)], 108, 60, 10)
    guest_after = T0 + DISP0 + OFFSET   # the display's first frame at host time T0 + DISP0
    (d / "cap" / "capture.json").write_text(json.dumps({
        "segments": [{"segment": 1, "file": "seg_1.mp4", "guest_before_s": guest_after - 0.02,
                      "guest_after_s": guest_after}],
        "clock": [{"label": "capture_start", "offset_s": OFFSET, "bound_s": 0.004}]}))
    flat_video(d / "vis.mkv", [inset_level(m) for m in range(inset_n)], 96, 64, 10)
    with open(d / "vis.mkv.frames.csv", "w") as f:
        f.write("video_index,frame_id,sim_time_s\n")
        for m in range(inset_n):
            f.write("%d,%d,%.6f\n" % (m, m, m * 0.1 + 0.02))
    return d


def luma(video: Path) -> list[bytes]:
    """The Y plane of each frame, as stored (yuv420p; no range conversion)."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-f", "rawvideo", "-pix_fmt", "yuv420p", "-"],
                         capture_output=True, check=True).stdout
    size = 1920 * 1080 * 3 // 2
    return [raw[k:k + 1920 * 1080] for k in range(0, len(raw), size)]


def at(frame: bytes, x: int, y: int) -> int:
    return frame[y * 1920 + x]


def test_composition_places_each_pane_by_its_clock(run_dir: Path) -> None:
    out = run_dir / "video"
    sources = [run_dir / "chase_view.mp4", run_dir / "chase_view.mp4.frames.csv", run_dir / "cap" / "seg_1.mp4",
               run_dir / "cap" / "capture.json", run_dir / "vis.mkv", run_dir / "vis.mkv.frames.csv"]
    digests = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    r = subprocess.run([sys.executable, str(COMPOSE), "--chase", str(run_dir / "chase_view.mp4"),
                        "--display-capture", str(run_dir / "cap"), "--inset", str(run_dir / "vis.mkv"),
                        "--out", str(out), "--lossless", "--duration-s", "2.0", "--start-unix", repr(T0 + START)],
                       capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr

    # expected, from the synthetic times
    chase_t = [T0 + i * 0.05 + (STALL_S if i >= STALL_AT else 0) for i in range(40)]
    disp_t = [T0 + DISP0 + j * 0.1 for j in range(30)]
    inset_sim = [m * 0.1 + 0.02 for m in range(20)]
    start = T0 + START
    frames = luma(out / "side_by_side.mp4")
    assert len(frames) == 41
    held = 0
    for k, img in enumerate(frames):
        t = start + k / FPS
        c = bisect_right(chase_t, t) - 1
        d = bisect_right(disp_t, t) - 1
        m = bisect_right(inset_sim, c * 0.05) - 1
        assert at(img, 120, PANE_Y + PANE_H - 40) == chase_level(c), k          # chase pane, below the inset
        assert at(img, PANE_W + PANE_W // 2, PANE_Y + PANE_H // 2) == display_level(d), k
        if m >= 0:
            assert at(img, INSET_X + INSET_W // 2, INSET_Y + INSET_H // 2) == inset_level(m), k
        held += c == STALL_AT - 1
    assert held > 10   # the frame before the stall is held for about the stall's length

    tl = (out / "timeline.csv").read_text().splitlines()
    assert tl[0] == "k,unix_s,chase_index,sim_time_s,display_index,ivi_clock_s,inset_index"
    row = tl[1].split(",")
    assert int(row[2]) == 6 and float(row[5]) == pytest.approx(disp_t[0] + OFFSET, abs=1e-6)

    man = json.loads((out / "manifest.json").read_text())
    for p in sources:
        entry = [s for s in man["sources"] if s["path"] == str(p.resolve())]
        assert entry and entry[0]["sha256"] == digests[p]
        assert hashlib.sha256(p.read_bytes()).hexdigest() == digests[p]          # raw files untouched
    assert man["output"]["sha256"] == hashlib.sha256((out / "side_by_side.mp4").read_bytes()).hexdigest()
    assert man["output"]["size"] == "1920x1080" and man["output"]["frames"] == 41
    assert man["display"]["ivi_offset_to_host_s"] == OFFSET
    assert man["inset"]["composited"].startswith("after the run")
    assert "arrival at the recorder" in man["chase"]["time_source"]


def test_composition_refuses_an_inset_without_simulation_time(run_dir: Path) -> None:
    (run_dir / "vis.mkv.frames.csv").write_text("video_index,frame_id,t_arrive_ns\n0,0,1\n")
    r = subprocess.run([sys.executable, str(COMPOSE), "--chase", str(run_dir / "chase_view.mp4"),
                        "--display-capture", str(run_dir / "cap"), "--inset", str(run_dir / "vis.mkv"),
                        "--out", str(run_dir / "video")], capture_output=True, text=True, timeout=120)
    assert r.returncode != 0
    assert "no column 'sim_time_s'" in r.stderr


def test_composition_refuses_a_frames_csv_that_does_not_match_the_video(run_dir: Path) -> None:
    p = run_dir / "chase_view.mp4.frames.csv"
    p.write_text("\n".join(p.read_text().splitlines()[:-3]) + "\n")
    r = subprocess.run([sys.executable, str(COMPOSE), "--chase", str(run_dir / "chase_view.mp4"),
                        "--display-capture", str(run_dir / "cap"), "--out", str(run_dir / "video")],
                       capture_output=True, text=True, timeout=120)
    assert r.returncode != 0
    assert "40 frames" in r.stderr
