#!/usr/bin/env python3
"""Side-by-side video of a bench run for the owner: the simulator's chase view and the driver's display, aligned.

  compose_side_by_side.py --chase <chase_view.mp4> --display-capture <capture dir> --out <dir> [options]

Left: the chase view recorded on the simulator host (chase_recorder.py), with VisionPilot's visualization from the
visualization recorder as an inset at the top right when --inset is given. Right: the IVI display capture
(display_capture.sh). Output 1920x1080 at --fps (20). Only the real captures are shown; nothing is rendered over
them except one caption line and the two clocks: the simulation time of the chase frame shown and the IVI clock of
the display frame shown.

Alignment, all on real (UTC) time:
  * a chase frame is placed at the real time of its world tick: --tick-times (CSV sim_time_s,unix_s from the world
    side) when given, else its arrival at the recorder (<video>.frames.csv, the simulator host's clock; later than
    the tick by the render time). Over a simulator stall the last frame is held;
  * a display frame is placed at t0 + pts on the IVI clock, t0 = the guest clock read just after the segment's
    screenrecord launch (segments.jsonl) plus --display-t0-correction-s (read from the clock the app shows on the
    display, when that check has been made), then moved to this host's clock with the offset the capture measured
    at its start (clock.jsonl). The encoder starts after that read, so until the correction is measured the display
    may lead the chase view by up to about 0.2 s (INC-DRIVING-001's observation);
  * an inset frame is the newest visualization frame whose capture simulation time is at or before the simulation
    time of the chase frame shown (--inset-time-column, default sim_time_s). The inset is composited here, after the
    run, and the manifest says so.
Held frames: between two display frames the pane holds the earlier one. manifest.json lists, as display.held_spans,
every such span at a segment boundary (the display was not recorded there: the capture's bounds are quoted with it)
and every other one of at least --held-span-min-s (a display that did not change, or an encoder stall: the frame
times cannot tell them apart). Over a boundary span the IVI clock line says the display was not recorded since the
frame shown. display.gap_free is false when a boundary falls in the output, and null otherwise: no output is called
gap-free.
The raw files are only read; their sha256 are taken before and after and must be equal. manifest.json lists the
sources with their sha256 and every offset used; timeline.csv gives the source frame of each output frame.
"""
from __future__ import annotations

import argparse
import bisect
import csv
import datetime
import hashlib
import json
import os
import shutil
import subprocess
import sys

W, H = 1920, 1080
PANE_W, PANE_H = 960, 540
PANE_Y = 240
CAPTION_Y = PANE_Y - 70
INSET_W, INSET_H = 300, 200
INSET_X, INSET_Y = PANE_W - INSET_W - 16, PANE_Y + 16
CLOCK_Y = PANE_Y + PANE_H + 24
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def frame_pts(path: str) -> list[float]:
    """Presentation times of every decoded frame, in decode-output order (as `-vsync passthrough` writes them)."""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "frame=best_effort_timestamp_time", "-of", "csv=p=0", path],
                       capture_output=True, text=True, check=True)
    return [float(x.split(",")[0]) for x in r.stdout.split() if x.strip() and x.strip() != "N/A"]


def read_csv(path: str) -> list[dict[str, str]]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def pick(times: list[float], t: float) -> int:
    """Index of the newest frame at or before t (-1: none yet). Holding the last frame covers a stall."""
    return bisect.bisect_right(times, t) - 1


def utc(t: float) -> str:
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]


class Frames:
    """Decoded frames of one or more files, scaled and padded to one pane, read one after the other."""

    def __init__(self, files: list[str], w: int, h: int):
        self.files, self.w, self.h = list(files), w, h
        self.size = w * h * 3 // 2
        self.proc = None
        self.index = -1
        self.current = bytes([16]) * (w * h) + bytes([128]) * (w * h // 2)   # black until the first frame

    def _open_next(self) -> bool:
        if self.proc is not None:
            self.proc.stdout.close()
            self.proc.wait()
        if not self.files:
            self.proc = None
            return False
        vf = ("scale=%d:%d:force_original_aspect_ratio=decrease,pad=%d:%d:(ow-iw)/2:(oh-ih)/2,format=yuv420p"
              % (self.w, self.h, self.w, self.h))
        self.proc = subprocess.Popen(["ffmpeg", "-v", "error", "-i", self.files.pop(0), "-vsync", "passthrough",
                                      "-vf", vf, "-f", "rawvideo", "-"], stdout=subprocess.PIPE)
        return True

    def advance_to(self, target: int) -> bytes:
        while self.index < target:
            data = self.proc.stdout.read(self.size) if self.proc is not None else b""
            if len(data) < self.size:
                if not self._open_next():
                    raise RuntimeError("fewer decoded frames than listed (wanted index %d)" % target)
                continue
            self.current = data
            self.index += 1
        return self.current

    def close(self):
        if self.proc is not None:
            self.proc.stdout.close()
            self.proc.wait()


def retime(files: list[str], picks: list[int], w: int, h: int, fps: int, out: str) -> None:
    """Writes one pane at constant rate: output frame k shows source frame picks[k] (black while picks[k] < 0)."""
    enc = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "yuv420p", "-s",
                            "%dx%d" % (w, h), "-r", str(fps), "-i", "-", "-c:v", "libx264", "-preset", "ultrafast",
                            "-qp", "0", out], stdin=subprocess.PIPE)
    src = Frames(files, w, h)
    try:
        for p in picks:
            enc.stdin.write(src.advance_to(p) if p >= 0 else bytes([16]) * (w * h) + bytes([128]) * (w * h // 2))
    finally:
        src.close()
        enc.stdin.close()
        if enc.wait() != 0:
            raise RuntimeError("pane encode failed: " + out)


def esc(text: str) -> str:
    """drawtext text inside a sendcmd file: escape what the option parser reads."""
    return text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "").replace(";", ",").replace(",", "\\,")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--chase", required=True, help="chase_view.mp4; its frames CSV is <mp4>.frames.csv by default")
    ap.add_argument("--chase-frames")
    ap.add_argument("--tick-times", help="CSV sim_time_s,unix_s: the real time of each world tick")
    ap.add_argument("--display-capture", required=True, help="the folder display_capture.sh wrote")
    ap.add_argument("--display-t0-correction-s", type=float, default=0.0)
    ap.add_argument("--inset", help="the visualization recorder's video")
    ap.add_argument("--inset-frames", help="its frames CSV (default <video>.frames.csv)")
    ap.add_argument("--inset-time-column", default="sim_time_s")
    ap.add_argument("--out", required=True)
    ap.add_argument("--fps", type=int, default=20)
    ap.add_argument("--start-unix", type=float)
    ap.add_argument("--duration-s", type=float)
    ap.add_argument("--caption", default="Left: CARLA chase view, VisionPilot's visualization inset placed after the "
                                         "run. Right: the IVI display.")
    ap.add_argument("--crf", default="18")
    ap.add_argument("--lossless", action="store_true", help="libx264 -qp 0 (tests)")
    ap.add_argument("--held-span-min-s", type=float, default=0.5,
                    help="list held display frames within a segment from this length on (boundaries: always)")
    a = ap.parse_args(argv)
    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool) is None:
            sys.exit("%s is not installed" % tool)
    os.makedirs(a.out, exist_ok=True)
    cap_dir = a.display_capture
    capture = json.load(open(os.path.join(cap_dir, "capture.json")))
    chase_csv = a.chase_frames or a.chase + ".frames.csv"
    sources = [a.chase, chase_csv, os.path.join(cap_dir, "capture.json")]
    seg_files = [os.path.join(cap_dir, s["file"]) for s in capture["segments"]]
    sources += seg_files
    if a.tick_times:
        sources.append(a.tick_times)
    inset_csv = None
    if a.inset:
        inset_csv = a.inset_frames or a.inset + ".frames.csv"
        sources += [a.inset, inset_csv]
    before = {p: sha256(p) for p in sources}

    # chase frames: simulation time and real time
    rows = read_csv(chase_csv)
    rows.sort(key=lambda r: int(r["video_index"]))
    n_video = len(frame_pts(a.chase))
    if n_video != len(rows):
        sys.exit("the chase video has %d frames, its frames CSV %d rows" % (n_video, len(rows)))
    chase_sim = [float(r["sim_time_s"]) for r in rows]
    if a.tick_times:
        ticks = {round(float(r["sim_time_s"]), 3): float(r["unix_s"]) for r in read_csv(a.tick_times)}
        chase_t = [ticks[round(s, 3)] for s in chase_sim]
        chase_source = "world tick real time (--tick-times)"
    else:
        chase_t = [float(r["arrival_unix_s"]) for r in rows]
        chase_source = "arrival at the recorder (simulator host clock)"
    if any(b < x for x, b in zip(chase_t, chase_t[1:])):
        sys.exit("chase frame times go backwards")

    # display frames: IVI clock, then this host's clock
    clock = {c["label"]: c for c in capture.get("clock", [])}
    off = clock.get("capture_start", {}).get("offset_s")
    disp_ivi, disp_seg, seg_info = [], [], []
    for n_seg, (s, f) in enumerate(zip(capture["segments"], seg_files), 1):
        pts = frame_pts(f)
        t0 = float(s["guest_after_s"]) + a.display_t0_correction_s
        disp_ivi += [t0 + p - pts[0] for p in pts]
        disp_seg += [s.get("segment", n_seg)] * len(pts)
        seg_info.append({"file": s["file"], "frames": len(pts), "first_pts_s": pts[0], "last_pts_s": pts[-1],
                         "guest_before_s": s["guest_before_s"], "guest_after_s": s["guest_after_s"], "t0_ivi_s": t0})
    disp_t = [t - (off or 0.0) for t in disp_ivi]

    # inset frames: capture simulation time
    inset_sim = []
    if a.inset:
        irows = read_csv(inset_csv)
        if a.inset_time_column not in (irows[0] if irows else {}):
            sys.exit("the inset frames CSV has no column %r: align it by simulation time or leave --inset out"
                     % a.inset_time_column)
        irows.sort(key=lambda r: int(r["video_index"]))
        inset_sim = [float(r[a.inset_time_column]) for r in irows]
        n_inset = len(frame_pts(a.inset))
        if n_inset != len(irows):
            sys.exit("the inset video has %d frames, its frames CSV %d rows" % (n_inset, len(irows)))

    start = a.start_unix if a.start_unix is not None else max(chase_t[0], disp_t[0])
    end = start + a.duration_s if a.duration_s is not None else min(chase_t[-1], disp_t[-1])
    n = int((end - start) * a.fps + 1e-9) + 1
    if n < 1:
        sys.exit("the chase view and the display capture do not overlap in time")
    times = [start + k / a.fps for k in range(n)]
    pc = [pick(chase_t, t) for t in times]
    pd = [pick(disp_t, t) for t in times]
    pi = [pick(inset_sim, chase_sim[c]) if (a.inset and c >= 0) else -1 for c in pc]

    # held display frames: the output frames that show display frame i while frame i+1 is not yet due
    bounds = {(b["after_segment"], b["before_segment"]): b for b in capture.get("boundaries", [])}
    held, not_recorded = [], {}
    for i in range(len(disp_t) - 1):
        boundary = disp_seg[i] != disp_seg[i + 1]
        if not boundary and disp_t[i + 1] - disp_t[i] < a.held_span_min_s:
            continue
        k0, k1 = bisect.bisect_left(times, disp_t[i]), bisect.bisect_left(times, disp_t[i + 1]) - 1
        if k0 > k1:
            continue   # outside the output
        span = {"kind": "segment boundary" if boundary else "within a segment",
                "held_s": disp_t[i + 1] - disp_t[i], "first_output_frame": k0, "last_output_frame": k1,
                "from_ivi_s": disp_ivi[i], "to_ivi_s": disp_ivi[i + 1], "from_utc": utc(disp_ivi[i]),
                "to_utc": utc(disp_ivi[i + 1])}
        if boundary:
            b = bounds.get((disp_seg[i], disp_seg[i + 1]), {})
            span.update({"after_segment": disp_seg[i], "before_segment": disp_seg[i + 1],
                         "capture_unrecorded_min_s": b.get("unrecorded_min_s"),
                         "capture_unrecorded_max_s": b.get("unrecorded_max_s")})
            for k in range(k0, k1 + 1):
                not_recorded[k] = disp_ivi[i]
        held.append(span)

    work = os.path.join(a.out, "work")
    os.makedirs(work, exist_ok=True)
    retime([a.chase], pc, PANE_W, PANE_H, a.fps, os.path.join(work, "pane_chase.mkv"))
    retime(seg_files, pd, PANE_W, PANE_H, a.fps, os.path.join(work, "pane_display.mkv"))
    if a.inset:
        retime([a.inset], pi, INSET_W, INSET_H, a.fps, os.path.join(work, "pane_inset.mkv"))

    # the clocks: one sendcmd line per change, half a frame before the frame it labels
    cmds, last = [], (None, None)
    with open(os.path.join(a.out, "timeline.csv"), "w") as tl:
        tl.write("k,unix_s,chase_index,sim_time_s,display_index,ivi_clock_s,inset_index\n")
        for k, t in enumerate(times):
            sim = "simulation time %.2f s" % chase_sim[pc[k]] if pc[k] >= 0 else "simulation time: no frame yet"
            ivi = "IVI clock %s UTC" % utc(disp_ivi[pd[k]]) if pd[k] >= 0 else "IVI clock: no frame yet"
            if k in not_recorded:
                ivi = "IVI display not recorded since %s UTC (segment boundary)" % utc(not_recorded[k])
            at = max(0.0, (k - 0.5) / a.fps)
            if sim != last[0]:
                cmds.append("%.4f drawtext@sim reinit 'text=%s';" % (at, esc(sim)))
            if ivi != last[1]:
                cmds.append("%.4f drawtext@ivi reinit 'text=%s';" % (at, esc(ivi)))
            last = (sim, ivi)
            tl.write("%d,%.6f,%d,%s,%d,%s,%d\n" % (k, t, pc[k], "%.6f" % chase_sim[pc[k]] if pc[k] >= 0 else "",
                                                   pd[k], "%.6f" % disp_ivi[pd[k]] if pd[k] >= 0 else "", pi[k]))
    open(os.path.join(work, "clocks.cmd"), "w").write("\n".join(cmds) + "\n")
    open(os.path.join(work, "caption.txt"), "w").write(a.caption)
    font = "fontfile=%s:" % FONT if os.path.exists(FONT) else ""
    text = "%sfontsize=26:fontcolor=white:" % font
    fg = ["color=c=black:s=%dx%d:r=%d,format=yuv420p[bg]" % (W, H, a.fps),
          "[bg][0:v]overlay=0:%d:format=yuv420:shortest=1[a]" % PANE_Y,
          "[a][1:v]overlay=%d:%d:format=yuv420[b]" % (PANE_W, PANE_Y)]
    tail = "b"
    if a.inset:
        fg.append("[b][2:v]overlay=%d:%d:format=yuv420[c]" % (INSET_X, INSET_Y))
        tail = "c"
    fg.append("[%s]sendcmd=f=clocks.cmd,drawtext@cap=%stextfile=caption.txt:x=(w-text_w)/2:y=%d,"
              "drawtext@sim=%stext='simulation time':x=24:y=%d,drawtext@ivi=%stext='IVI clock':x=%d:y=%d[v]"
              % (tail, text, CAPTION_Y, text, CLOCK_Y, text, PANE_W + 24, CLOCK_Y))
    video = os.path.join(a.out, "side_by_side.mp4")
    enc = ["-c:v", "libx264", "-preset", "medium"] + (["-qp", "0"] if a.lossless else ["-crf", a.crf])
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", "pane_chase.mkv", "-i", "pane_display.mkv"]
    if a.inset:
        cmd += ["-i", "pane_inset.mkv"]
    cmd += ["-filter_complex", ";".join(fg), "-map", "[v]", "-frames:v", str(n), *enc, "-pix_fmt", "yuv420p",
            "-r", str(a.fps), os.path.abspath(video)]
    subprocess.run(cmd, cwd=work, check=True)

    after = {p: sha256(p) for p in sources}
    if after != before:
        sys.exit("a source file changed while composing: %s" % [p for p in sources if after[p] != before[p]])
    ffv = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True).stdout.split("\n")[0]
    manifest = {
        "output": {"file": "side_by_side.mp4", "sha256": sha256(video), "frames": n, "fps": a.fps,
                   "size": "%dx%d" % (W, H), "start_unix_s": start, "start_utc": utc(start), "duration_s": n / a.fps},
        "sources": [{"path": os.path.abspath(p), "sha256": before[p]} for p in sources],
        "sources_unchanged": True,
        "chase": {"frames": len(rows), "time_source": chase_source, "first_sim_time_s": chase_sim[0],
                  "last_sim_time_s": chase_sim[-1]},
        "display": {"segments": seg_info, "display_t0_correction_s": a.display_t0_correction_s,
                    "ivi_offset_to_host_s": off, "ivi_offset_bound_s": clock.get("capture_start", {}).get("bound_s"),
                    "t0_rule": "guest clock read just after the screenrecord launch, plus the correction",
                    "held_spans": held,
                    "gap_free": False if any(h["kind"] == "segment boundary" for h in held) else None,
                    "gap_free_rule": "false when a segment boundary falls in the output (the display was not "
                                     "recorded there); otherwise null: a hold within a segment is a static display "
                                     "or an encoder stall, which the frame times cannot tell apart"},
        "inset": ({"file": os.path.abspath(a.inset), "join": "newest frame with %s <= the chase frame's simulation "
                   "time" % a.inset_time_column, "composited": "after the run, in this composition"}
                  if a.inset else None),
        "overlays": ["one caption line", "simulation time of the chase frame shown",
                     "IVI clock of the display frame shown"],
        "caption": a.caption,
        "ffmpeg": ffv,
        "command": cmd,
    }
    json.dump(manifest, open(os.path.join(a.out, "manifest.json"), "w"), indent=1)
    print("composed %d frames (%.2f s) from %s into %s" % (n, n / a.fps, utc(start), video))
    for h in held:
        if h["kind"] == "segment boundary":
            print("display not recorded at the segment boundary %d/%d: held %.3f s over output frames %d..%d "
                  "(capture's bounds %s..%s s)" % (h["after_segment"], h["before_segment"], h["held_s"],
                                                   h["first_output_frame"], h["last_output_frame"],
                                                   h["capture_unrecorded_min_s"], h["capture_unrecorded_max_s"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
