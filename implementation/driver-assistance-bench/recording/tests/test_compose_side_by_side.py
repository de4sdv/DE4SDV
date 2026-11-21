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


def test_composition_lists_the_held_spans_and_never_calls_a_boundary_gap_free(run_dir: Path) -> None:
    """Two segments with 1.0 s between segment 1's last frame and segment 2's first frame: the manifest lists that
    span as a segment boundary (its output frames, its length, the capture's bounds), says the output is not
    gap-free, and the IVI clock line under the display says the display was not recorded over those frames."""
    cap = run_dir / "cap"
    flat_video(cap / "seg_1.mp4", [display_level(j) for j in range(10)], 108, 60, 10)   # 0.0 .. 0.9 s
    flat_video(cap / "seg_2.mp4", [display_level(10 + j) for j in range(10)], 108, 60, 10)
    g1 = T0 + DISP0 + OFFSET
    g2 = g1 + 0.9 + 1.0
    (cap / "capture.json").write_text(json.dumps({
        "segments": [{"segment": 1, "file": "seg_1.mp4", "guest_before_s": g1 - 0.02, "guest_after_s": g1,
                      "guest_end_s": g1 + 1.0},
                     {"segment": 2, "file": "seg_2.mp4", "guest_before_s": g2 - 0.02, "guest_after_s": g2,
                      "guest_end_s": g2 + 1.0}],
        "boundaries": [{"after_segment": 1, "before_segment": 2, "unrecorded_min_s": 0.88,
                        "unrecorded_max_s": 1.12}],
        "clock": [{"label": "capture_start", "offset_s": OFFSET, "bound_s": 0.004}]}))
    out = run_dir / "video"
    r = subprocess.run([sys.executable, str(COMPOSE), "--chase", str(run_dir / "chase_view.mp4"),
                        "--display-capture", str(cap), "--out", str(out), "--lossless", "--duration-s", "1.6",
                        "--start-unix", repr(T0 + START)], capture_output=True, text=True, timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    man = json.loads((out / "manifest.json").read_text())
    d = man["display"]
    assert d["gap_free"] is False
    (b,) = [h for h in d["held_spans"] if h["kind"] == "segment boundary"]
    assert (b["after_segment"], b["before_segment"]) == (1, 2)
    assert b["held_s"] == pytest.approx(1.0, abs=1e-6)
    assert (b["capture_unrecorded_min_s"], b["capture_unrecorded_max_s"]) == (0.88, 1.12)
    # output frame k shows time START + k/20 after T0; segment 1's last frame is at DISP0 + 0.9, segment 2's first
    # at DISP0 + 1.9: from frame 18 on, segment 1's last frame is held to the output's end (1.6 s: 32 or 33 frames)
    assert man["output"]["frames"] in (32, 33)
    assert (b["first_output_frame"], b["last_output_frame"]) == (18, man["output"]["frames"] - 1)
    assert "segment boundary" in r.stdout
    cmds = (out / "work" / "clocks.cmd").read_text()
    assert "not recorded" in cmds


def test_composition_of_one_segment_makes_no_gap_free_claim(run_dir: Path) -> None:
    out = run_dir / "video"
    r = subprocess.run([sys.executable, str(COMPOSE), "--chase", str(run_dir / "chase_view.mp4"),
                        "--display-capture", str(run_dir / "cap"), "--out", str(out), "--lossless",
                        "--duration-s", "1.0", "--start-unix", repr(T0 + START)], capture_output=True, text=True,
                       timeout=600)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads((out / "manifest.json").read_text())["display"]
    assert d["gap_free"] is None and "static display" in d["gap_free_rule"]
    assert not [h for h in d["held_spans"] if h["kind"] == "segment boundary"]


def two_segment_capture(cap: Path, seg2_after_s: float = 1.0, pulled1: bool = True) -> tuple[float, float]:
    """seg_1 and seg_2, 10 frames at 10 fps each; seg_2's t0 lies seg2_after_s after seg_1's last frame."""
    flat_video(cap / "seg_1.mp4", [display_level(j) for j in range(10)], 108, 60, 10)   # 0.0 .. 0.9 s
    flat_video(cap / "seg_2.mp4", [display_level(10 + j) for j in range(10)], 108, 60, 10)
    if not pulled1:
        (cap / "seg_1.mp4").unlink()
    g1 = T0 + DISP0 + OFFSET
    g2 = g1 + 0.9 + seg2_after_s
    (cap / "capture.json").write_text(json.dumps({
        "segments": [{"segment": 1, "file": "seg_1.mp4", "guest_before_s": g1 - 0.02, "guest_after_s": g1,
                      "guest_end_s": g1 + 1.0, "pulled": pulled1},
                     {"segment": 2, "file": "seg_2.mp4", "guest_before_s": g2 - 0.02, "guest_after_s": g2,
                      "guest_end_s": g2 + 1.0, "pulled": True}],
        "boundaries": [{"after_segment": 1, "before_segment": 2, "unrecorded_min_s": 0.0,
                        "unrecorded_max_s": None}],
        "clock": [{"label": "capture_start", "offset_s": OFFSET, "bound_s": 0.004}]}))
    return g1, g2


def compose(run_dir: Path, cap: Path, duration_s: str = "1.6", start: float = T0 + START):
    out = run_dir / "video"
    r = subprocess.run([sys.executable, str(COMPOSE), "--chase", str(run_dir / "chase_view.mp4"),
                        "--display-capture", str(cap), "--out", str(out), "--lossless", "--duration-s", duration_s,
                        "--start-unix", repr(start)], capture_output=True, text=True, timeout=600)
    return r, out


def packet_pts_here(path: Path) -> list[float]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "packet=pts_time",
                        "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=True)
    return sorted(float(x.split(",")[0]) for x in r.stdout.split() if x.strip() and x.strip() != "N/A")


def test_composition_bounds_each_boundary_from_packet_times(run_dir: Path) -> None:
    """X2/X4: the capture leaves each boundary's upper bound to the composer, which computes it from the segments'
    packet times (no decode) and the capture's guest clock reads: (guest_end_s of the later segment - its span) -
    (guest_before_s of the earlier one + its span). The held span quotes that bound."""
    cap = run_dir / "cap"
    g1, g2 = two_segment_capture(cap)
    r, out = compose(run_dir, cap)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads((out / "manifest.json").read_text())["display"]
    bs = d.get("boundaries")
    assert bs, "the composer computes no boundary bound"
    (b,) = bs
    p1, p2 = packet_pts_here(cap / "seg_1.mp4"), packet_pts_here(cap / "seg_2.mp4")
    want = ((g2 + 1.0) - (p2[-1] - p2[0])) - ((g1 - 0.02) + (p1[-1] - p1[0]))
    assert b["unrecorded_max_s"] == pytest.approx(want, abs=1e-6)
    assert "packet" in b["unrecorded_max_rule"]
    (h,) = [h for h in d["held_spans"] if h["kind"] == "segment boundary"]
    assert h["capture_unrecorded_max_s"] == pytest.approx(want, abs=1e-6)


def test_the_packet_probe_has_a_time_bound(tmp_path: Path, monkeypatch) -> None:
    """X2: the composer's packet probe gives up after its bound and says so; it never waits on a hung ffprobe."""
    import compose_side_by_side as cs
    assert hasattr(cs, "packet_pts"), "the composer has no bounded packet probe"
    d = tmp_path / "bin"
    d.mkdir()
    (d / "ffprobe").write_text("#!/bin/sh\nsleep 30\n")
    (d / "ffprobe").chmod(0o755)
    monkeypatch.setenv("PATH", "%s:%s" % (d, __import__("os").environ["PATH"]))
    import time
    t0 = time.monotonic()
    pts, why = cs.packet_pts(str(tmp_path / "x.mp4"), timeout_s=1)
    assert pts is None and "1 s" in why
    assert time.monotonic() - t0 < 10


def test_a_boundary_whose_frame_times_overlap_is_still_listed(run_dir: Path) -> None:
    """X8: segment 2 is placed before segment 1's last frame (held time <= 0). The boundary lies inside the output,
    so it is listed and the output is not called gap-free."""
    cap = run_dir / "cap"
    two_segment_capture(cap, seg2_after_s=-0.3)
    r, out = compose(run_dir, cap)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads((out / "manifest.json").read_text())["display"]
    bs = [h for h in d["held_spans"] if h["kind"] == "segment boundary"]
    assert bs and bs[0]["held_s"] <= 0, d["held_spans"]
    assert d["gap_free"] is False


def test_composition_skips_a_segment_not_pulled_and_lists_its_span(run_dir: Path) -> None:
    """X9: segment 1's pull failed (no file). The composer composes segment 2 and lists segment 1's span, on the IVI
    clock from its launch to its end read, as not recorded here (kind "segment not pulled")."""
    cap = run_dir / "cap"
    g1, g2 = two_segment_capture(cap, pulled1=False)
    r, out = compose(run_dir, cap, duration_s="1.0", start=g2 - OFFSET)
    assert r.returncode == 0, r.stdout + r.stderr
    d = json.loads((out / "manifest.json").read_text())["display"]
    (h,) = [h for h in d["held_spans"] if h["kind"] == "segment not pulled"]
    assert h["segment"] == 1
    assert (h["from_ivi_s"], h["to_ivi_s"]) == (pytest.approx(g1 - 0.02), pytest.approx(g1 + 1.0))
    assert [s["file"] for s in d["segments"]] == ["seg_2.mp4"]
    assert d["gap_free"] is False


# Closure of the S1 runs, R7: the chase recorder keeps receiving frames after the world side's last recorded tick (6
# on S1's 012_42_r1, 18 on 013_30_r1), at the variable steps of the world's asynchronous mode, so tick_times.csv has
# no row for them. Only the frames inside the span of tick_times.csv are placed by tick time; the frames before the
# first tick and after the last are left out and listed.
TICK_FIRST, TICK_LAST = 2, 33          # tick_times.csv rows for chase frames 2..33
TICK_LAG = 0.01                        # a tick's real time: T0 + its frame's sim time + this
TRAILING = [1.65 + 0.05, 1.75, 1.769578, 1.78879, 1.80802, 1.827442]   # frames 34..39, asynchronous steps


def _tick_run_dir(run_dir: Path, skip_tick: int | None = None, first: int = TICK_FIRST) -> Path:
    sims = [i * 0.05 for i in range(34)] + TRAILING
    with open(run_dir / "chase_view.mp4.frames.csv", "w") as f:
        f.write("video_index,carla_frame,sim_time_s,arrival_unix_s\n")
        for i, sim in enumerate(sims):
            f.write("%d,%d,%.6f,%.6f\n" % (i, 500 + i, sim, T0 + sim + 0.03))
    with open(run_dir / "tick_times.csv", "w") as f:
        f.write("sim_time_s,unix_s\n")
        for i in range(first, TICK_LAST + 1):
            if i != skip_tick:
                f.write("%.6f,%.6f\n" % (i * 0.05, T0 + i * 0.05 + TICK_LAG))
    return run_dir


def _compose_with_ticks(run_dir: Path, out: Path):
    return subprocess.run([sys.executable, str(COMPOSE), "--chase", str(run_dir / "chase_view.mp4"),
                           "--tick-times", str(run_dir / "tick_times.csv"),
                           "--display-capture", str(run_dir / "cap"), "--out", str(out), "--lossless",
                           "--duration-s", "1.0", "--start-unix", repr(T0 + START)],
                          capture_output=True, text=True, timeout=600)


def test_frames_outside_the_tick_span_are_left_out_and_listed(run_dir: Path) -> None:
    _tick_run_dir(run_dir)
    out = run_dir / "video"
    r = _compose_with_ticks(run_dir, out)
    assert r.returncode == 0, r.stdout + r.stderr
    placed = list(range(TICK_FIRST, TICK_LAST + 1))
    placed_t = [T0 + i * 0.05 + TICK_LAG for i in placed]
    frames = luma(out / "side_by_side.mp4")
    assert len(frames) == 21
    for k, img in enumerate(frames):
        j = bisect_right(placed_t, T0 + START + k / FPS) - 1
        assert j >= 0
        assert at(img, 120, PANE_Y + PANE_H - 40) == chase_level(placed[j]), k
    chase = json.loads((out / "manifest.json").read_text())["chase"]
    assert "world tick real time" in chase["time_source"]
    left = chase["left_out_outside_tick_span"]
    assert left["count"] == 8
    assert left["before_first_tick_sim_time_s"] == [0.0, 0.05]
    assert left["after_last_tick_sim_time_s"] == pytest.approx(TRAILING)
    assert chase["placed_frames"] == len(placed)


def test_trailing_frames_past_the_last_tick_alone_are_left_out(run_dir: Path) -> None:
    # S1's case: every frame up to the last tick has its tick, and the recorder's last frames come after it
    _tick_run_dir(run_dir, first=0)
    out = run_dir / "video"
    r = _compose_with_ticks(run_dir, out)
    assert r.returncode == 0, r.stdout + r.stderr
    left = json.loads((out / "manifest.json").read_text())["chase"]["left_out_outside_tick_span"]
    assert left["count"] == 6 and left["before_first_tick_sim_time_s"] == []
    assert left["after_last_tick_sim_time_s"] == pytest.approx(TRAILING)


def test_a_frame_inside_the_tick_span_without_its_tick_is_refused(run_dir: Path) -> None:
    _tick_run_dir(run_dir, skip_tick=10)
    r = _compose_with_ticks(run_dir, run_dir / "video")
    assert r.returncode != 0
    assert "inside the span of the tick times" in r.stderr and "0.500" in r.stderr, r.stderr
    assert "Traceback" not in r.stderr, r.stderr
