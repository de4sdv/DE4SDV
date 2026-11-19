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
        # both clock reads and the backgrounded recording run in one guest shell, in this order; each read carries
        # its mark (Q5): b= before the recording, a= after it
        assert shell.count("echo b=$(date +%s.%N);") == 1 and shell.count("echo a=$(date +%s.%N);") == 1, shell
        assert shell.index("echo b=$(date +%s.%N);") < shell.index("screenrecord") \
            < shell.index("echo a=$(date +%s.%N);"), shell
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
            "pull": lambda c: "pull" in c and c[-2].endswith("/seg_1.mp4")}[window]   # the guest file
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


def test_the_capture_ends_only_after_the_last_pull_ended(tmp_path: Path, env: dict[str, str]) -> None:
    """The pull of the last segment (seg_2, the end of the drive) is held past the stop. capture.json and
    capture.done are written, and the guest's files removed, only once that pull ended; capture.json lists seg_2 as
    pulled, with the sha256 of the complete file. A capture that ended beside a running pull would leave the last
    segment missing (or truncated) in the evidence."""
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    release = tmp_path / "release_pull"
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="1", FAKE_LIMIT_DIR=str(limits), FAKE_HOLD_PULL="2:%s" % release)
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    stop = None
    try:
        wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
        (limits / "limit_1").touch()
        wait_until("second recording", lambda: len(recordings(fake)) >= 2, p)
        stop = subprocess.Popen(["bash", str(CAPTURE), "stop", str(out), "--wait-s", "30"], env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        wait_until("the held pull of seg_2",
                   lambda: any("pull" in c and c[-2].endswith("/seg_2.mp4") for c in calls(fake)), p)
        # the capture's tail runs up to the end's clock measurement (calls after the logcat); then only the pull
        # holds it. Give it a bounded time to (wrongly) finish beside the pull
        wait_until("the end's logcat", lambda: any(c[:1] == ["logcat"] or "logcat" in c for c in calls(fake)), p)
        until = time.monotonic() + 3
        while time.monotonic() < until and not (out / "capture.done").exists() and p.poll() is None:
            time.sleep(0.02)
        assert not (out / "capture.done").exists(), "capture.done written while the pull of seg_2 ran"
        assert not (out / "capture.json").exists(), "capture.json written while the pull of seg_2 ran"
    finally:
        t_release = time.time()
        release.touch()
    log, _ = p.communicate(timeout=60)
    s_out, _ = stop.communicate(timeout=60)
    assert p.returncode == 0, log
    assert stop.returncode == 0, s_out + log
    assert (out / "capture.done").stat().st_mtime >= t_release
    assert (out / "capture.json").stat().st_mtime >= t_release
    cap = json.loads((out / "capture.json").read_text())
    s2 = cap["segments"][1]
    assert s2["file"] == "seg_2.mp4" and s2["pulled"] is True
    complete = hashlib.sha256(Path(env["FAKE_SEG_MP4"]).read_bytes()).hexdigest()
    assert s2["sha256"] == cap["sha256"]["seg_2.mp4"] == complete
    assert hashlib.sha256((out / "seg_2.mp4").read_bytes()).hexdigest() == complete
    # the guest file of seg_2 (by its own rm or the folder's) goes only after its pull ended
    gone = [t for t, c in stamped(fake) if any("rm -rf /data/local/tmp/da_capture" in a
                                               or "rm -f /data/local/tmp/da_capture/seg_2" in a for a in c)]
    assert gone and min(gone) >= t_release, (gone, t_release)


def test_a_pull_slower_than_a_segment_delays_neither_the_next_launch_nor_the_stop(tmp_path: Path,
                                                                                env: dict[str, str]) -> None:
    """The pull of seg_1 is held (a pull that takes longer than a segment): seg_2 reaches its limit and seg_3
    starts, and then a stop reaches seg_3 within the poll bound, all while that pull still runs. A pull run in
    the loop, even after the next launch, would hold the alive poll: no end of seg_2 seen, no stop found."""
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    release = tmp_path / "release_pull"
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="1", FAKE_LIMIT_DIR=str(limits), FAKE_HOLD_PULL="1:%s" % release)
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    held = lambda: any("pull" in c and c[-2].endswith("/seg_1.mp4") for c in calls(fake))
    try:
        wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
        (limits / "limit_1").touch()
        wait_until("second recording and the held pull of seg_1", lambda: len(recordings(fake)) >= 2 and held(), p)
        (limits / "limit_2").touch()
        # POLL_S is 0.05 s here: a few polls and one launch, not the pull's time
        wait_until("third recording while seg_1 is pulled", lambda: len(recordings(fake)) >= 3, p, timeout_s=10)
        (out / "STOP").touch()
        wait_until("the stop's signal to seg_3 while seg_1 is pulled",
                   lambda: any(any("kill -INT 4002" in a for a in c) for c in calls(fake)), p, timeout_s=10)
        assert not (out / "seg_1.mp4").exists()   # the pull is still held
    finally:
        release.touch()
    log, _ = p.communicate(timeout=60)
    assert p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    assert [s["end"] for s in cap["segments"]] == ["time-limit", "time-limit", "stop"]
    assert [s["pulled"] for s in cap["segments"]] == [True, True, True]


def test_a_live_recording_is_not_taken_as_ended_when_adb_writes_after_alive(tmp_path: Path,
                                                                           env: dict[str, str]) -> None:
    """The alive poll's adb writes "alive" and then more (FAKE_ALIVE_TAIL_S). A reader that stops at the match
    (grep -q under pipefail) gives adb SIGPIPE and the poll a failed status: a live recording would read ended, its
    file be pulled while it is written, and a second screenrecord start beside it. The poll reads the whole answer."""
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="1", FAKE_LIMIT_DIR=str(limits), FAKE_ALIVE_TAIL_S="0.2")
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    polls = lambda: [c for c in calls(fake) if any("kill -0 4000" in a for a in c)]
    try:
        wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
        wait_until("three polls of the live recording (or a second recording)",
                   lambda: len(polls()) >= 3 or len(recordings(fake)) >= 2, p)
        assert len(recordings(fake)) == 1, "a second recording started beside the live first one"
        assert not any("pull" in c and c[-2].endswith("/seg_1.mp4") for c in calls(fake)), \
            "the live recording's file was pulled"
        (limits / "limit_1").touch()
        wait_until("second recording", lambda: len(recordings(fake)) >= 2, p)
    finally:
        (out / "STOP").touch()
    log, _ = p.communicate(timeout=60)
    assert p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    assert [s["end"] for s in cap["segments"]] == ["time-limit", "stop"]


def test_no_adb_answer_is_read_by_a_reader_that_stops_at_its_match() -> None:
    """Under pipefail, `adb ... | grep -q` (or head, grep -m) can give adb SIGPIPE: the pipeline then fails though
    the answer matched. The display capture and the IVI clock read adb's whole answer and compare the value."""
    import re
    for script in (CAPTURE, CLOCK):
        for n, line in enumerate(script.read_text().splitlines(), 1):
            code = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
            if re.search(r"(\ba |\badbt |\$ADB\b|\badb\b)[^|]*\|.*\b(grep -[a-zA-Z]*[qm]|head)\b", code):
                raise AssertionError("%s:%d reads adb with a reader that stops early: %s" % (script.name, n, line))


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
        # X3: the give-up names the guest paths still to pull, which stay on the guest
        assert "/data/local/tmp/da_capture/seg_2.mp4" in stop.stdout, stop.stdout
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


def test_the_capture_leaves_the_frame_times_to_the_composer(tmp_path: Path, env: dict[str, str]) -> None:
    """X2/X4: the capture probes no frame times (they scale with the recording's length) and says so: the frame
    fields and each boundary's upper bound are null, and the record names where they are computed."""
    out, fake, p, stop, _ = two_segments(tmp_path, env)
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0 and p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    s1, s2 = cap["segments"]
    (b,) = cap["boundaries"]
    assert (b["after_segment"], b["before_segment"]) == (1, 2)
    # from below by the guest clock reads alone, here
    assert b["unrecorded_min_s"] == pytest.approx(s2["guest_before_s"] - s1["guest_end_s"], abs=1e-6)
    assert b["unrecorded_min_s"] >= 0
    assert b["unrecorded_max_s"] is None
    assert "compose_side_by_side.py" in b["unrecorded_max_where"]
    assert cap["not_filled_here"]["fields"] == ["boundaries[].unrecorded_max_s", "frame times"]
    assert "compose_side_by_side.py" in cap["not_filled_here"]["where"]
    assert "packet" in cap["not_filled_here"]["where"]


def fake_ffprobe(tmp_path: Path, sleep_s: float) -> tuple[Path, Path]:
    """An ffprobe on PATH that takes sleep_s per call (a frame probe of a long recording) and logs each call."""
    d = tmp_path / "slowbin"
    d.mkdir()
    log = tmp_path / "ffprobe.calls"
    (d / "ffprobe").write_text("#!/bin/sh\necho \"$*\" >> %s\nsleep %s\n" % (log, sleep_s))
    (d / "ffprobe").chmod(0o755)
    return d, log


def test_the_stop_is_not_delayed_by_a_frame_probe(tmp_path: Path, env: dict[str, str]) -> None:
    """X2 BLOCKER: an ffprobe on the guest host that takes 30 s per segment (as a decode of every frame of a long
    recording does) costs the stop nothing: nothing in the stop path probes the files."""
    d, log = fake_ffprobe(tmp_path, 30)
    env = dict(env, PATH="%s:%s" % (d, env["PATH"]))
    out, fake, p, stop, took = two_segments(tmp_path, env, stop_args=("--wait-s", "5"))
    log_out, _ = p.communicate(timeout=120)
    assert stop.returncode == 0, (took, stop.stdout, log_out)
    assert not log.exists(), "the capture ran ffprobe: " + log.read_text()
    assert took < 15, took


def test_no_frame_probe_in_the_capture() -> None:
    """X2: a static check beside the slow-probe test: the capture script never names ffprobe outside comments."""
    code = [line.split("#", 1)[0] for line in CAPTURE.read_text().splitlines() if not line.lstrip().startswith("#")]
    assert not [c for c in code if "ffprobe" in c]


def test_a_failed_alive_poll_does_not_end_a_live_recording(tmp_path: Path, env: dict[str, str]) -> None:
    """X1 BLOCKER (R1): the 3rd poll of the live recording 1 gets no answer (adb's "error: closed", rc 1). The
    segment ends only on the guest's own "ended": no second recording starts beside it, its file is neither pulled
    nor removed while it records, and the next polls find it alive again."""
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="1", FAKE_LIMIT_DIR=str(limits), FAKE_POLL_FAIL="1:3-3")
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    polls = lambda: [c for c in calls(fake) if any("kill -0 4000" in a for a in c)]
    try:
        wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
        wait_until("six polls of the live recording (or a second recording)",
                   lambda: len(polls()) >= 6 or len(recordings(fake)) >= 2, p)
        assert len(recordings(fake)) == 1, "a second recording started beside the live first one"
        assert not any("pull" in c and c[-2].endswith("/seg_1.mp4") for c in calls(fake)), \
            "the live recording's file was pulled"
        assert not any(any("rm -f /data/local/tmp/da_capture/seg_1" in a for a in c) for c in calls(fake)), \
            "the live recording's guest file was removed"
        (limits / "limit_1").touch()
        wait_until("second recording", lambda: len(recordings(fake)) >= 2, p)
    finally:
        (out / "STOP").touch()
    log, _ = p.communicate(timeout=60)
    assert p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    assert [s["end"] for s in cap["segments"]] == ["time-limit", "stop"]
    assert [s["pulled"] for s in cap["segments"]] == [True, True]


def test_polls_without_an_answer_end_the_capture_as_an_error_that_still_stops_cleanly(tmp_path: Path,
                                                                                       env: dict[str, str]) -> None:
    """X1: from its 3rd poll on, recording 1 gets no answer. After ALIVE_UNKNOWN_S (here 1 s) of no answer the
    capture ends with END=error: no relaunch, the live recording is sent SIGINT, the app's record is pulled, and
    capture.json and capture.done say error. The segment's file is not pulled (its state is unknown) and is kept on
    the guest."""
    record = tmp_path / "warning.jsonl"
    record.write_text('{"event": "receipt"}\n')
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="1", FAKE_LIMIT_DIR=str(limits), FAKE_POLL_FAIL="1:3", ALIVE_UNKNOWN_S="1",
               FAKE_APP_RECORD=str(record), APP_RECORD_PATHS="/data/user/@user@/x/files/warning.jsonl")
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        wait_until("the capture's end", lambda: (out / "capture.done").exists() or len(recordings(fake)) >= 2, p,
                   timeout_s=30)
    except AssertionError:
        pass
    finally:
        (out / "STOP").touch()
    try:
        log, _ = p.communicate(timeout=60)
    except subprocess.TimeoutExpired:
        p.kill()
        raise
    assert len(recordings(fake)) == 1, "a second recording started beside the live first one"
    assert p.returncode == 1, log
    cap = json.loads((out / "capture.json").read_text())
    assert cap["end"] == "error"
    (s1,) = cap["segments"]
    assert s1["end"] == "no-answer" and s1["pulled"] is False
    assert cap["pull_failures"] == [{"segment": 1, "guest_path": "/data/local/tmp/da_capture/seg_1.mp4"}]
    assert any(any("kill -INT 4000" in a for a in c) for c in calls(fake))
    assert not any(any("rm -f /data/local/tmp/da_capture/seg_1" in a or "rm -rf /data/local/tmp/da_capture" in a
                       for a in c) for c in calls(fake))
    assert (out / "app_record_warning.jsonl").read_text() == record.read_text()
    assert (out / "capture.done").read_text().startswith("capture ended (error)")


def test_every_adb_call_of_the_capture_has_a_time_bound() -> None:
    """X5: every adb invocation in display_capture.sh (through a(), ab() or "$ADB" itself) and the clock script it
    runs are under `timeout --foreground`, so a call that hangs cannot hold the loop, the tail or the end."""
    import re
    lines = CAPTURE.read_text().splitlines()
    code = [(n, line.split(" #", 1)[0]) for n, line in enumerate(lines, 1) if not line.lstrip().startswith("#")]
    direct = [(n, c) for n, c in code if '"$ADB"' in c or "$ADB " in c]
    assert direct, "no adb invocation found"
    for n, c in direct:
        assert re.search(r'timeout --foreground "?\$\{?\w+\}?"? +"\$ADB"', c), "%d: adb without a bound: %s" % (n, c)
    for n, c in code:
        if '"$CLOCK"' in c:
            assert re.search(r'timeout --foreground "?\$\{?\w+\}?"? +bash "\$CLOCK"', c), \
                "%d: the clock script without a bound: %s" % (n, c)


def test_a_hung_adb_call_in_the_tail_costs_neither_the_app_records_nor_the_stop(tmp_path: Path,
                                                                                  env: dict[str, str]) -> None:
    """X5: after the stop, the guest's audio dump and its end stills hang (an adb shell on a device gone offline).
    Each call is cut at ADB_TIMEOUT_S, the app's record is pulled first, and the stop returns 0."""
    record = tmp_path / "warning.jsonl"
    record.write_text('{"event": "receipt"}\n')
    stop_file = tmp_path / "cap" / "STOP"
    env = dict(env, ADB_TIMEOUT_S="2", FAKE_HANG="dumpsys media.audio_flinger:%s" % stop_file,
               FAKE_APP_RECORD=str(record), APP_RECORD_PATHS="/data/user/@user@/x/files/warning.jsonl")
    out, fake, p, stop, took = two_segments(tmp_path, env, stop_args=("--wait-s", "20"))
    log, _ = p.communicate(timeout=120)
    assert stop.returncode == 0, (took, stop.stdout, log)
    assert (out / "app_record_warning.jsonl").read_text() == record.read_text()
    t_rec = [t for t, c in stamped(fake) if "pull" in c and any("warning.jsonl" in a for a in c)]
    t_hang = [t for t, c in stamped(fake) if "dumpsys media.audio_flinger" in " ".join(c)]
    assert len(t_hang) >= 2, t_hang   # the start's, then the tail's
    assert t_rec and t_rec[0] < t_hang[1], "the app's record was not pulled before the tail's other calls"


def test_the_stop_waits_while_the_pull_makes_progress(tmp_path: Path, env: dict[str, str]) -> None:
    """X3 (R2): the last segment's pull takes 8 s (it grows in 10 parts), with a tail of 3 s and PULL_BPS far above
    the real rate. The stop counts the local file's growth as progress and waits to the end, within its cap. The pull
    writes `.part` and renames it only once complete: the final name never holds a part of the file."""
    env = dict(env, PULL_BPS="1000000000")
    full = Path(env["FAKE_SEG_MP4"]).stat().st_size
    seen_final_early = []

    def watch(out, fake, p):
        import threading

        def run():
            until = time.monotonic() + 30
            while time.monotonic() < until and not (out / "capture.done").exists():
                try:
                    n = (out / "seg_2.mp4").stat().st_size
                except FileNotFoundError:
                    n = None
                if n is not None and n < full:   # a part of the file under its final name
                    seen_final_early.append(n)
                time.sleep(0.01)
        threading.Thread(target=run, daemon=True).start()

    out, fake, p, stop, took = two_segments(tmp_path, env, stop_args=("--wait-s", "3", "--wait-cap-s", "60"),
                                            before_stop=watch, FAKE_PULL_GROW="2:8")
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0, (took, stop.stdout, log)
    assert took > 7, took
    assert not seen_final_early, "a part of seg_2.mp4 was under its final name while it was pulled"
    pulls = [c for c in calls(fake) if "pull" in c and c[-2].endswith(".mp4")]
    assert pulls and all(c[-1].endswith(".mp4.part") for c in pulls), pulls
    cap = json.loads((out / "capture.json").read_text())
    assert [s["pulled"] for s in cap["segments"]] == [True, True]
    assert not list(out.glob("*.part"))


def test_a_cut_pull_never_leaves_a_part_under_the_final_name(tmp_path: Path, env: dict[str, str]) -> None:
    """X3: the pull of seg_1 fails after writing half of the file: no seg_1.mp4 exists, the part is kept aside."""
    out, fake, p, stop, _ = two_segments(tmp_path, env, FAKE_PULL_FAIL="1")
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0, stop.stdout + log
    assert not (out / "seg_1.mp4").exists()
    assert not (out / "seg_1.mp4.part").exists()
    assert (out / "seg_1.mp4.partial").exists()


def test_a_recording_that_ends_early_is_labeled_and_a_second_one_ends_the_capture(tmp_path: Path,
                                                                                   env: dict[str, str]) -> None:
    """X6 (R3): from the 2nd recording on, every recording dies at once (a full /data, a display gone). Each is
    labeled ended-early (its guest-clock duration well short of its 3 s limit, no stop asked), and after the 2nd
    early end the capture ends with END=error: no relaunch loop."""
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="3", FAKE_LIMIT_DIR=str(limits), FAKE_DEAD_FROM="2")
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
        time.sleep(1.5)   # recording 1 runs longer than its limit minus EARLY_S: it is not early
        (limits / "limit_1").touch()
        until = time.monotonic() + 10
        while p.poll() is None and time.monotonic() < until and len(recordings(fake)) < 6:
            time.sleep(0.05)
    finally:
        (out / "STOP").touch()
    log, _ = p.communicate(timeout=60)
    assert len(recordings(fake)) == 3, (len(recordings(fake)), log)
    cap = json.loads((out / "capture.json").read_text())
    assert [s["end"] for s in cap["segments"]] == ["time-limit", "ended-early", "ended-early"]
    assert cap["end"] == "error"
    assert p.returncode == 1, log


def test_at_most_two_pulls_are_in_flight(tmp_path: Path, env: dict[str, str]) -> None:
    """X6/X7: every pull is held. Segments 1, 2 and 3 reach their limit and segment 4 records: only two pulls run,
    the third waits for a free place, and after the release every segment is pulled."""
    out = tmp_path / "cap"
    limits = tmp_path / "limits"
    limits.mkdir()
    release = tmp_path / "release"
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="1", FAKE_LIMIT_DIR=str(limits), FAKE_HOLD_PULL="*:%s" % release)
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    seg_pulls = lambda: [c for c in calls(fake) if "pull" in c and c[-2].endswith(".mp4")]
    try:
        for k in (1, 2, 3):
            wait_until("recording %d" % k, lambda: len(recordings(fake)) >= k, p)
            (limits / ("limit_%d" % k)).touch()
        wait_until("recording 4", lambda: len(recordings(fake)) >= 4, p)
        wait_until("three polls of recording 4",
                   lambda: len([c for c in calls(fake) if any("kill -0 4003" in a for a in c)]) >= 3, p)
        assert len(seg_pulls()) == 2, seg_pulls()
    finally:
        release.touch()
        (out / "STOP").touch()
    log, _ = p.communicate(timeout=60)
    assert p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    assert [s["pulled"] for s in cap["segments"]] == [True, True, True, True]


def test_each_launch_reads_the_guests_free_space(tmp_path: Path, env: dict[str, str]) -> None:
    """X7: /data's free space is read at every launch, in the launch's own guest shell after its second clock read
    (no round trip added to the boundary), and kept per segment."""
    out, fake, p, stop, _ = two_segments(tmp_path, env, FAKE_DF_AVAIL_KB="1234567")
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0 and p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    assert [s.get("guest_data_free_kb") for s in cap["segments"]] == [1234567, 1234567]
    for c in recordings(fake):
        shell = " ".join(c)
        assert shell.rindex("date +%s.%N") < shell.index("df -k /data")


def test_the_stop_bound_fits_the_sessions_step_bound() -> None:
    """X10, Q3: the session passes the stop its cap (--wait-cap-s) derived from T_CAPTURE_END, counted from before
    rstep's start SSH call: that call (60 s, its time-out), the stop's own last poll and exit (2 s), then one status
    poll whose SSH call (60 s, rpoll's time-out) may have read \"running\" just before the stop ended, and POLL_S.
    The README's sum is that sum, and the cap is no shorter than the capture's own default."""
    import re
    sess = (BENCH / "session" / "da_session.sh").read_text()
    t = int(re.search(r"\bT_CAPTURE_END=(\d+)\b", sess).group(1))
    poll = int(re.search(r"\bPOLL_S=(\d+)\b", sess).group(1))
    assert 'routall ssh_l "$r" 60 "$HS start' in sess and 'rout ssh_l "$1" "${3:-60}"' in sess
    assert "CAP_WAIT_S=$(( T_CAPTURE_END - 60 - 2 - 60 - CAP_P ))" in sess
    assert '--wait-cap-s "$CAP_WAIT_S"' in sess
    cap = t - 60 - 2 - 60 - poll
    m = re.search(r"WAIT_CAP_S=\$\{WAIT_CAP_S:-(\d+)\}", CAPTURE.read_text())
    assert m and cap >= int(m.group(1)), (cap, m and m.group(1))
    readme = (BENCH / "recording" / "README.md").read_text()
    assert re.search(r"T_CAPTURE_END +(\d+) s", readme).group(1) == str(t)
    assert re.search(r"= --wait-cap-s +(\d+) s", readme).group(1) == str(cap)


@pytest.mark.parametrize("stray", ["WARNING: linker: unused DT entry", "b=not a clock"], ids=["warning", "bad-mark"])
def test_a_stray_line_in_the_launch_answer_neither_breaks_capture_json_nor_reads_as_a_clean_end(
        tmp_path: Path, env: dict[str, str], stray: str) -> None:
    """Q5: the clock reads of a launch are taken by their marks, not by line number, and checked as numbers; one
    stray line before the answer (a linker warning on the guest's stdout, or one that carries a mark) leaves
    capture.json valid. A mark whose value is not a number gives null, never a broken JSON line."""
    out, fake, p, stop, _ = two_segments(tmp_path, env, FAKE_LAUNCH_STRAY=stray)
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0 and p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    for s in cap["segments"]:
        assert isinstance(s["guest_after_s"], float), s
        if stray.startswith("b="):
            assert s["guest_before_s"] is None, s
            continue
        assert isinstance(s["guest_before_s"], float), s
        assert s["guest_before_s"] <= s["guest_after_s"] <= s["guest_end_s"], s
    assert [s.get("guest_data_free_kb") for s in cap["segments"]] == [4000000, 4000000]
    assert (out / "capture.done").read_text().startswith("capture ended (stop)")


def test_capture_done_says_error_when_capture_json_could_not_be_written(tmp_path: Path, env: dict[str, str]) -> None:
    """Q5: capture.done is written only after capture.json; when the step that writes capture.json fails, the
    capture ends as an error and capture.done says so, never \"capture ended (stop)\"."""
    import sys
    stub = tmp_path / "pybin"
    stub.mkdir()
    (stub / "python3").write_text(
        "#!/bin/bash\n# fails the step that writes capture.json, runs every other Python (the fake adb) as it is\n"
        "if [ \"$1\" = - ]; then f=$(mktemp); cat > \"$f\"\n"
        "  if grep -q '\"capture.json\"' \"$f\"; then rm -f \"$f\"; exit 3; fi\n"
        "  shift; exec %s \"$f\" \"$@\"\nfi\nexec %s \"$@\"\n" % (sys.executable, sys.executable))
    (stub / "python3").chmod(0o755)
    env = dict(env, PATH="%s:%s" % (stub, env["PATH"]))
    out, fake, p, stop, _ = two_segments(tmp_path, env)
    log, _ = p.communicate(timeout=60)
    assert not (out / "capture.json").exists()
    assert p.returncode == 1, log
    done = (out / "capture.done").read_text()
    assert done.startswith("capture ended (error)") and "capture.json" in done, done


def test_alive_unknown_counts_from_the_start_of_the_first_unanswered_poll(tmp_path: Path,
                                                                          env: dict[str, str]) -> None:
    """Q7: every poll hangs to its POLL_TIMEOUT_S (2 s) once the hang file exists. The no-answer end comes
    ALIVE_UNKNOWN_S (3 s) after the first unanswered poll began, at the end of the poll that passes it (about 4 s),
    not ALIVE_UNKNOWN_S after that poll's end (about 6 s)."""
    hang = tmp_path / "hang"
    out = tmp_path / "cap"
    fake = Path(env["FAKE_ADB_DIR"])
    env = dict(env, SEGMENT_S="60", POLL_TIMEOUT_S="2", ALIVE_UNKNOWN_S="3", FAKE_HANG="kill -0:%s" % hang)
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "60"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
        hang.touch()
        t_hang = time.time()
        wait_until("the SIGINT of the no-answer end",
                   lambda: any(any("kill -INT 4000" in a for a in c) for c in calls(fake)), p, timeout_s=30)
    finally:
        (out.mkdir(exist_ok=True), (out / "STOP").touch())
    log, _ = p.communicate(timeout=90)
    first = min(t for t, c in stamped(fake) if t >= t_hang and any("kill -0 4000" in a for a in c))
    sigint = min(t for t, c in stamped(fake) if any("kill -INT 4000" in a for a in c))
    assert sigint - first < 5.5, (sigint - first, log)
    assert json.loads((out / "capture.json").read_text())["end"] == "error"


def test_the_guest_space_is_checked_for_every_segment_of_max_s(tmp_path: Path, env: dict[str, str]) -> None:
    """Q4: the session passes --max-s from the window's worst case. At its start the capture compares /data's free
    space with that many segments and with what the pulls during the recording leave there (the recording and
    MAX_PULLS pulls), warns when it fits fewer than all, and records the figures in capture.json."""
    seg_kb = 8000000 // 8 * 170 // 1024
    env = dict(env, FAKE_DF_AVAIL_KB=str(5 * seg_kb))   # more than 3 in flight, fewer than ceil(2995/170) = 18
    out = tmp_path / "cap"
    fake = Path(env["FAKE_ADB_DIR"])
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "2995"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        wait_until("first recording", lambda: len(recordings(fake)) >= 1, p)
    finally:
        (out / "STOP").touch()
    log, _ = p.communicate(timeout=60)
    assert p.returncode == 0, log
    space = json.loads((out / "capture.json").read_text())["guest_space"]
    assert space == {"free_kb": 5 * seg_kb, "segment_kb_max": seg_kb, "segments_max": 18,
                     "in_flight_kb": 3 * seg_kb, "all_segments_kb": 18 * seg_kb, "segments_that_fit": 5}, space
    assert "fits 5 of the 18 segments" in log, log
