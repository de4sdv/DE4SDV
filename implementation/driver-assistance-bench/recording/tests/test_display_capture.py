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
    return [json.loads(line)[1:] for line in (d / "calls.log").read_text().splitlines()]


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


def test_capture_brackets_each_recording_with_the_guest_clock(tmp_path: Path, env: dict[str, str]) -> None:
    out = tmp_path / "cap"
    env = dict(env, SEGMENT_S="1")
    p = subprocess.Popen(["bash", str(CAPTURE), "start", str(out), "--max-s", "30"], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    time.sleep(2.5)   # the first segment ends by its time limit, the second is running
    stop = subprocess.run(["bash", str(CAPTURE), "stop", str(out), "--wait-s", "30"], env=env, capture_output=True,
                          text=True, timeout=60)
    log, _ = p.communicate(timeout=60)
    assert stop.returncode == 0, stop.stdout + log
    assert p.returncode == 0, log
    cap = json.loads((out / "capture.json").read_text())
    segs = cap["segments"]
    assert len(segs) >= 2
    assert segs[0]["end"] == "time-limit" and segs[-1]["end"] == "stop"
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
