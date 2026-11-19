"""The display capture (display_capture.sh) and the IVI clock (ivi_clock.sh) against a fake adb.

The fake's guest clock runs a known offset ahead of this host's, so the measured offset can be checked against it;
the files' digests are recomputed here with hashlib.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent.parent
CAPTURE = BENCH / "recording" / "display_capture.sh"
CLOCK = BENCH / "session" / "remote" / "ivi_clock.sh"
FAKE_ADB = HERE / "fake_adb.py"


def calls(d: Path) -> list[list[str]]:
    return [c for _, c in stamped(d)]


def stamped(d: Path) -> list[tuple[float, list[str]]]:
    """The fake's calls with the time each began (this host's clock)."""
    p = d / "calls.log"
    lines = []
    for line in (p.read_text().splitlines() if p.exists() else []):
        try:
            lines.append(json.loads(line))
        except json.JSONDecodeError:   # a line the fake is still writing
            break
    return [(c[0], c[1:]) for c in lines]


def recordings(d: Path) -> list[list[str]]:
    return [c for c in calls(d) if any("screenrecord" in a for a in c)]


def wait_until(what: str, cond, p: subprocess.Popen, timeout_s: float = 60) -> None:
    """Wait for a state of the capture (the test orders the events itself; no sleep stands in for an order)."""
    until = time.monotonic() + timeout_s
    while not cond():
        assert p.poll() is None, "the capture ended before %s: %s" % (what, p.communicate()[0])
        assert time.monotonic() < until, "no %s within %s s" % (what, timeout_s)
        time.sleep(0.01)


@pytest.fixture()
def env(tmp_path: Path) -> dict[str, str]:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not installed")
    fake = tmp_path / "adb"
    fake.mkdir()
    seg = tmp_path / "seg.mp4"
    subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-f", "lavfi", "-i",
                    "testsrc=size=320x180:rate=10", "-t", "1", "-pix_fmt", "yuv420p", "-y", str(seg)], check=True)
    return dict(os.environ, ADB=str(FAKE_ADB), FAKE_ADB_DIR=str(fake), FAKE_SEG_MP4=str(seg), POLL_S="0.05",
                CLOCK_READS="5", LC_ALL="C")


@pytest.mark.parametrize("call_delay_s", ["0", "0.25"], ids=["idle-host", "loaded-host"])
def test_capture_brackets_each_recording_with_the_guest_clock(tmp_path: Path, env: dict[str, str],
                                                              call_delay_s: str) -> None:
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    fake = Path(env["FAKE_ADB_DIR"])
    # the fake's recordings reach their time limit when this test says so, not on this host's clock: the stop
    # then comes while the second recording runs on a fast host and on a loaded one alike (a fixed sleep did not)
    env = dict(env, SEGMENT_S="1", FAKE_LIMIT_DIR=str(limits), FAKE_CALL_DELAY_S=call_delay_s)
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "30"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
    # past the first recording's 1 s on this host's clock it still runs: two polls of it after that time
    t_limit = [t for t, c in stamped(fake) if any("screenrecord" in a for a in c)][0] + 1.2
    later = lambda: [c for t, c in stamped(fake) if t >= t_limit]
    wait_until("two calls after the first recording's time on this host's clock", lambda: len(later()) >= 2, p)
    assert all(any("kill -0" in a for a in c) for c in later()[:2]), later()[:2]
    (limits / "limit_1").touch()   # the first segment ends by its time limit
    wait_until("second recording", lambda: len(recordings(fake)) >= 2, p)
    stop = subprocess.run(["bash", str(CAPTURE), "stop", str(out), "--wait-s", "30"], env=env, capture_output=True,
                          text=True, timeout=60)
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0, stop.stdout + log
    assert p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    segs = cap["segments"]
    assert [s["end"] for s in segs] == ["time-limit", "stop"]
    assert cap["end"] == "stop"
    for s in segs:
        assert s["host_before_s"] <= s["host_after_s"]
        assert s["guest_before_s"] <= s["guest_after_s"] <= s["guest_end_s"]
        # the fake guest clock runs 0.25 s (FAKE_GUEST_OFFSET) ahead of this host's. Both guest reads happen inside
        # the host's bracket, so on this host's clock they lie between host_before_s and host_after_s; the bound is
        # the bracket's own round trip, which a loaded host widens, never a fixed window (1 ms: print rounding)
        assert s["host_before_s"] - 1e-3 <= s["guest_before_s"] - 0.25 <= s["guest_after_s"] - 0.25 \
            <= s["host_after_s"] + 1e-3
    adb = calls(Path(env["FAKE_ADB_DIR"]))
    rec = [c for c in adb if any("screenrecord" in a for a in c)]
    assert len(rec) == len(segs)
    for c in rec:
        shell = " ".join(c)
        # both clock reads and the backgrounded recording run in one guest shell, in this order
        assert shell.index("date +%s.%N;") < shell.index("screenrecord") < shell.rindex("date +%s.%N")
        assert "> /dev/null 2>&1 &" in shell
        assert "--display-id 4619827259835644672" in shell
    assert any(any("kill -INT" in a for a in c) for c in adb)
    for when in ("start", "end"):
        for d in cap["display_ids"]:
            assert (out / f"screencap_{when}_{d}.png").read_bytes().startswith(b"\x89PNG")
    assert cap["display_ids"] == ["4619827259835644672", "4619827551948147201"]
    for name, digest in cap["sha256"].items():
        assert hashlib.sha256((out / name).read_bytes()).hexdigest() == digest
    for s in segs:
        assert s["sha256"] == hashlib.sha256((out / s["file"]).read_bytes()).hexdigest()
    clock = [json.loads(line) for line in (out / "clock.jsonl").read_text().splitlines()]
    assert [c["label"] for c in clock] == ["capture_start", "capture_end"]
    for c in clock:
        assert abs(c["offset_s"] - 0.25) <= c["bound_s"] + 0.02
    assert (out / "audio_flinger_start.txt").exists() and (out / "audio_flinger_end.txt").exists()
    assert "receipt" in (out / "logcat.txt").read_text()
    assert "no audio capture" in cap["sound"]


@pytest.mark.parametrize("window", ["poll", "pull"])
def test_a_stop_after_a_segments_time_limit_starts_no_new_segment(tmp_path: Path, env: dict[str, str],
                                                                   window: str) -> None:
    """The stop comes just after a segment reached its time limit: at the poll that finds it ended (before its end
    marker) or while its file is pulled. Those are the windows of the flaky run on x86. No segment starts after the
    stop, and every segment says truly how it ended. The pull runs beside the next recording (it is no longer on the
    boundary), so a stop during segment 1's pull finds segment 2 recording and ends it by SIGINT."""
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    (limits / "limit_1").touch()
    fake = Path(env["FAKE_ADB_DIR"])
    held = {"poll": lambda c: any("kill -0 4000" in a for a in c),
            "pull": lambda c: "pull" in c and c[-1].endswith("/seg_1.mp4")}[window]
    env = dict(env, SEGMENT_S="1", FAKE_LIMIT_DIR=str(limits))
    env["FAKE_HOLD_" + window.upper()] = "1:%s" % (out / "STOP")   # the held call answers once the stop came
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "30"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    wait_until("the held call", lambda: any(held(c) for c in calls(fake)), p)
    stop = subprocess.run(["bash", str(CAPTURE), "stop", str(out), "--wait-s", "30"], env=env, capture_output=True,
                          text=True, timeout=60)
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0, stop.stdout + log
    assert p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    assert cap["end"] == "stop"
    t_stop = (out / "STOP").stat().st_mtime
    assert not [t for t, c in stamped(fake) if any("screenrecord" in a for a in c) and t > t_stop]
    n = {"poll": 1, "pull": 2}[window]
    assert [s["end"] for s in cap["segments"]] == ["time-limit", "stop"][:n]
    assert len(recordings(fake)) == n
    assert any(any("kill -INT 4001" in a for a in c) for c in calls(fake)) == (window == "pull")
    assert not any(any("kill -INT 4000" in a for a in c) for c in calls(fake))
    for k, s in enumerate(cap["segments"], 1):
        assert s["guest_before_s"] <= s["guest_after_s"] <= s["guest_end_s"]
        assert s["sha256"] == hashlib.sha256((out / f"seg_{k}.mp4").read_bytes()).hexdigest()
    assert (out / "capture.done").read_text() == "capture ended (stop), %d segment(s)\n" % n


def test_capture_ends_at_its_limit_without_a_stop(tmp_path: Path, env: dict[str, str]) -> None:
    out = tmp_path / "cap"
    r = subprocess.run(["bash", str(CAPTURE), "start", str(out), "--max-s", "1"], env=dict(env, SEGMENT_S="5"),
                       capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    cap = json.loads((out / "capture.json").read_text())
    assert cap["end"] == "max-s"
    assert [s["end"] for s in cap["segments"]] == ["time-limit"]
    assert "--time-limit 1 " in " ".join(" ".join(c) for c in calls(Path(env["FAKE_ADB_DIR"])))


def test_capture_refuses_an_existing_capture(tmp_path: Path, env: dict[str, str]) -> None:
    out = tmp_path / "cap"
    out.mkdir()
    (out / "capture.json").write_text("{}")
    r = subprocess.run(["bash", str(CAPTURE), "start", str(out)], env=env, capture_output=True, text=True, timeout=30)
    assert r.returncode == 2


def test_clock_set_brings_the_guest_clock_to_this_host(tmp_path: Path, env: dict[str, str]) -> None:
    out = tmp_path / "clock"
    r = subprocess.run(["bash", str(CLOCK), "set", str(out)], env=env, capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stdout + r.stderr
    lines = [json.loads(line) for line in (out / "clock.jsonl").read_text().splitlines()]
    assert lines[0]["label"] == "before_set" and abs(lines[0]["offset_s"] - 0.25) <= lines[0]["bound_s"] + 0.02
    last = lines[-1]
    assert last["label"] in ("after_set", "after_second_set")
    assert abs(last["offset_s"]) <= last["bound_s"] + 0.03
    sets = [c for c in calls(Path(env["FAKE_ADB_DIR"])) if any("toybox date -s @" in a for a in c)]
    assert 1 <= len(sets) <= 2


def test_the_app_record_is_pulled_from_the_current_users_files(tmp_path: Path, env: dict[str, str]) -> None:
    record = tmp_path / "warning.jsonl"
    record.write_text('{"event": "receipt"}\n')
    out = tmp_path / "cap"
    env = dict(env, SEGMENT_S="1", FAKE_APP_RECORD=str(record),
               APP_RECORD_PATHS="/data/user/@user@/org.de4sdv.collisionwarning/files/warning.jsonl")
    p = subprocess.run(["bash", str(CAPTURE), "start", str(out), "--max-s", "1"], env=env, capture_output=True,
                       text=True, timeout=60)
    assert p.returncode == 0, p.stdout + p.stderr
    assert (out / "app_record_warning.jsonl").read_text() == record.read_text()
    pulls = [c for c in calls(Path(env["FAKE_ADB_DIR"])) if "pull" in c and any("warning.jsonl" in a for a in c)]
    assert pulls and pulls[0][pulls[0].index("pull") + 1] == \
        "/data/user/10/org.de4sdv.collisionwarning/files/warning.jsonl"


def two_segments(tmp_path: Path, env: dict[str, str], stop_env: dict[str, str] | None = None,
                 stop_args: tuple[str, ...] = ("--wait-s", "30"), before_stop=None, **knobs: str):
    """A capture whose first segment reaches its time limit when the test says so and whose second one is stopped."""
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="1", FAKE_LIMIT_DIR=str(limits), **knobs)
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
    time.sleep(1.1)   # the fake's mp4 lasts 0.9 s: the recording runs longer than its file, as a real one does
    (limits / "limit_1").touch()
    wait_until("second recording", lambda: len(recordings(fake)) >= 2, p, timeout_s=15)
    if before_stop:
        before_stop(out, fake, p)
    t0 = time.monotonic()
    stop = subprocess.run(["bash", str(CAPTURE), "stop", str(out), *stop_args], env=stop_env or env,
                          capture_output=True, text=True, timeout=120)
    return out, fake, p, stop, time.monotonic() - t0


def test_the_next_segment_starts_while_the_last_one_is_pulled(tmp_path: Path, env: dict[str, str]) -> None:
    """Segment 2 is launched while segment 1's pull still runs (held here until segment 2 records): the pull is no
    longer part of the unrecorded span at a boundary. Every segment is still pulled, with its sha256."""
    release = tmp_path / "release_pull"

    def release_pull(out, fake, p):
        # segment 2 records, and the pull of segment 1 is in flight (held): neither waited for the other
        wait_until("the held pull", lambda: any("pull" in c and c[-2].endswith("/seg_1.mp4") for c in calls(fake)), p)
        assert not (out / "seg_1.mp4").exists()
        release.touch()

    out, fake, p, stop, _ = two_segments(tmp_path, env, FAKE_HOLD_PULL="1:%s" % release, before_stop=release_pull)
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0, stop.stdout + log
    assert p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    assert [s["file"] for s in cap["segments"]] == ["seg_1.mp4", "seg_2.mp4"]
    for s in cap["segments"]:
        assert s["pulled"] is True
        assert s["sha256"] == cap["sha256"][s["file"]] == hashlib.sha256((out / s["file"]).read_bytes()).hexdigest()
    assert cap["pull_failures"] == []
    # each guest file is removed once it is on this host, so the guest holds at most the running and the last segment
    rms = [" ".join(c) for c in calls(fake) if any(a.startswith("rm -f /data/local/tmp/da_capture/seg_") for a in c)]
    assert len(rms) == 2
    assert not list(out.glob("*.pending"))


def test_a_failed_pull_is_reported_and_keeps_the_guest_file(tmp_path: Path, env: dict[str, str]) -> None:
    out, fake, p, stop, _ = two_segments(tmp_path, env, FAKE_PULL_FAIL="1")
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0, stop.stdout + log
    assert p.returncode == 0, log   # the window's other records (the app's receipts) still count
    cap = json.loads((out / "capture.json").read_text())
    s1, s2 = cap["segments"]
    assert s1["pulled"] is False and s1["sha256"] is None and not (out / "seg_1.mp4").exists()
    assert s2["pulled"] is True
    assert cap["pull_failures"] == [{"segment": 1, "guest_path": "/data/local/tmp/da_capture/seg_1.mp4"}]
    assert cap["guest_dir_kept"] == "/data/local/tmp/da_capture"
    shells = [" ".join(c) for c in calls(fake) if c[:1] == ["shell"] or "shell" in c]
    assert not [c for c in shells if "rm -rf /data/local/tmp/da_capture" in c or "rm -f /data/local/tmp/da_capture/seg_1" in c]
    assert "WARNING: pull of seg_1.mp4 failed; the guest file is kept: /data/local/tmp/da_capture/seg_1.mp4" in log
    assert "kept on the guest: /data/local/tmp/da_capture/seg_1.mp4" in (out / "capture.done").read_text()


def test_a_recording_that_ends_at_its_limit_before_the_signal_says_time_limit(tmp_path: Path,
                                                                               env: dict[str, str]) -> None:
    """The stop is seen while the recording lives, and the recording reaches its time limit before kill -INT
    arrives: the signal goes to an ended process, and the segment says time-limit, not stop."""
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    release = tmp_path / "release_int"
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="1", FAKE_LIMIT_DIR=str(limits), FAKE_HOLD_INT="1:%s" % release)
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
    (out / "STOP").touch()
    wait_until("the signal", lambda: any(any("kill -INT 4000" in a for a in c) for c in calls(fake)), p)
    (limits / "limit_1").touch()   # the recording ends at its limit while the signal is on its way
    release.touch()
    log, _ = p.communicate(timeout=60)
    assert p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    assert [s["end"] for s in cap["segments"]] == ["time-limit"]
    assert cap["end"] == "stop"
    assert len(recordings(fake)) == 1


def test_the_stop_waits_for_the_pending_pulls(tmp_path: Path, env: dict[str, str]) -> None:
    """The pull of the last segment takes 6 s, longer than the stop's 3 s for the capture's tail: the stop's wait
    is computed from the bytes still to pull (PULL_BPS) and covers them."""
    size = (Path(env["FAKE_SEG_MP4"])).stat().st_size
    env = dict(env, PULL_BPS=str(max(1, size // 8)))   # 8 s per pending segment at this rate
    out, fake, p, stop, took = two_segments(tmp_path, env, stop_args=("--wait-s", "3"), FAKE_PULL_DELAY_S="6")
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0, stop.stdout + stop.stderr + log
    assert took > 6
    assert p.returncode == 0, log
    assert [s["pulled"] for s in json.loads((out / "capture.json").read_text())["segments"]] == [True, True]


def test_the_stop_wait_has_a_hard_cap(tmp_path: Path, env: dict[str, str]) -> None:
    """A pull that never ends: the stop gives up at its cap (WAIT_CAP_S), whatever the pending bytes would allow."""
    release = tmp_path / "release_pull"
    env = dict(env, PULL_BPS="1", WAIT_CAP_S="4")   # the pending bytes alone would allow days
    try:
        out, fake, p, stop, took = two_segments(tmp_path, env, stop_args=("--wait-s", "1"),
                                                FAKE_HOLD_PULL="2:%s" % release)
        assert stop.returncode == 1, stop.stdout
        assert "did not end within" in stop.stdout and took < 15, (took, stop.stdout)
    finally:
        release.touch()
    log, _ = p.communicate(timeout=60)
    assert p.returncode == 0, log


def test_the_end_of_a_segment_is_found_by_a_fast_poll(tmp_path: Path, env: dict[str, str]) -> None:
    """POLL_S is 8 s here, but within NEAR_END_S of the segment's time limit the capture polls every FAST_POLL_S:
    the next segment starts within about one poll and one launch of the end, not up to POLL_S later."""
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="2", POLL_S="8", FAST_POLL_S="0.1", NEAR_END_S="2", FAKE_LIMIT_DIR=str(limits))
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
        time.sleep(2.3)
        (limits / "limit_1").touch()
        t_end = time.time()
        wait_until("second recording", lambda: len(recordings(fake)) >= 2, p, timeout_s=20)
        t_next = [t for t, c in stamped(fake) if any("screenrecord" in a for a in c)][1]
        assert t_next - t_end < 2.5, t_next - t_end
    finally:
        (out / "STOP").touch()
        log, _ = p.communicate(timeout=60)
    assert p.returncode == 0, log


def ffprobe_pts(path: Path) -> list[float]:
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                        "frame=best_effort_timestamp_time", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True, check=True)
    return [float(x.split(",")[0]) for x in r.stdout.split() if x.strip() and x.strip() != "N/A"]


def test_the_gap_at_each_boundary_is_written(tmp_path: Path, env: dict[str, str]) -> None:
    """capture.json bounds the unrecorded span between segment 1's last frame and segment 2's first frame, on the
    guest clock: from below by the guest clock reads alone, from above with the files' frame times (ffprobe)."""
    if shutil.which("ffprobe") is None:
        pytest.skip("ffprobe is not installed")
    # segment 2 too runs longer than the fake's 0.9 s file before the stop, as a real recording does
    out, fake, p, stop, _ = two_segments(tmp_path, env, before_stop=lambda *_: time.sleep(1.1))
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0 and p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    s1, s2 = cap["segments"]
    d = []
    for s in (s1, s2):
        pts = ffprobe_pts(out / s["file"])
        assert s["frames"] == len(pts)
        assert s["first_pts_s"] == pytest.approx(pts[0], abs=1e-6)
        assert s["last_pts_s"] == pytest.approx(pts[-1], abs=1e-6)
        d.append(pts[-1] - pts[0])
    (b,) = cap["boundaries"]
    assert (b["after_segment"], b["before_segment"]) == (1, 2)
    # the last frame of 1 is at or after its launch plus its span; the first frame of 2 at or after its launch and at
    # or before the read after its end minus its span
    assert b["unrecorded_min_s"] == pytest.approx(s2["guest_before_s"] - s1["guest_end_s"], abs=1e-6)
    assert b["unrecorded_max_s"] == pytest.approx((s2["guest_end_s"] - d[1]) - (s1["guest_before_s"] + d[0]),
                                                  abs=1e-6)
    assert b["unrecorded_min_s"] >= 0
    assert b["unrecorded_min_s"] <= b["unrecorded_max_s"]
    assert "upper bound" in b["unrecorded_max_rule"]
