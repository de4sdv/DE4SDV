"""The chase recorder (chase_recorder.py) on a fake CARLA module, with the real ffmpeg.

The view's own pitch is checked against the spring-arm rule computed here with math.atan2; the video's frame count
is read back with ffprobe.
"""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RECORDER = HERE.parent / "chase_recorder.py"
sys.path.insert(0, str(HERE.parent))

import chase_recorder as cr  # noqa: E402


def test_view_b_own_pitch_follows_the_spring_arm_rule() -> None:
    # wanted 15 degrees down from x -10, z 5: the arm looks atan2(5, 10) down already
    assert cr.spring_arm_own_pitch(-10.0, 5.0, -15.0) == pytest.approx(-15.0 + math.degrees(math.atan2(5.0, 10.0)))
    assert round(cr.spring_arm_own_pitch(-10.0, 5.0, -15.0), 2) == 11.57
    # INC-DRIVING-001's placement with its plain -12 looked about 38 degrees down
    assert cr.spring_arm_own_pitch(-6.5, 3.2, -38.2) == pytest.approx(-12.0, abs=0.1)


def test_encoder_choice_and_command() -> None:
    assert cr.choose_encoder("auto", lambda: True) == ("h264_nvenc", None)
    enc, why = cr.choose_encoder("auto", lambda: False)
    assert enc == "libx264" and "NVENC" in why
    assert cr.choose_encoder("libx264", lambda: True) == ("libx264", None)
    cmd = cr.ffmpeg_command(1920, 1080, 20, "h264_nvenc", "12M", "v.mp4")
    assert cmd[cmd.index("-s") + 1] == "1920x1080" and cmd[cmd.index("-r") + 1] == "20"
    assert cmd[cmd.index("-c:v") + 1] == "h264_nvenc" and cmd[-1] == "v.mp4"
    with pytest.raises(ValueError):
        cr.encoder_args("mpeg4", "1M")


def run_recorder(tmp: Path, frames: int, *extra: str, **env: str) -> tuple[subprocess.CompletedProcess, Path]:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not installed")
    out = tmp / "rec"
    e = dict(os.environ, PYTHONPATH=str(HERE / "fake_carla"), FAKE_CARLA_FRAMES=str(frames),
             FAKE_CARLA_SPAWN_LOG=str(tmp / "spawn.json"), **env)
    p = subprocess.run([sys.executable, str(RECORDER), "--out", str(out), "--width", "64", "--height", "36",
                        "--max-s", "30", *extra], env=e, capture_output=True, text=True, timeout=120)
    return p, out


def test_recording_on_the_fake_simulator(tmp_path: Path) -> None:
    p, out = run_recorder(tmp_path, 30, "--encoder", "auto")
    assert p.returncode == 0, p.stdout + p.stderr
    st = json.loads((out / "summary.json").read_text())
    spawn = json.loads((tmp_path / "spawn.json").read_text())
    assert spawn["attachment"] == "SpringArmGhost" and spawn["attach_to"] == 77
    assert (spawn["x"], spawn["y"], spawn["z"]) == (-10.0, 0.0, 5.0)
    assert spawn["pitch"] == pytest.approx(-15.0 + math.degrees(math.atan2(5.0, 10.0)))   # computed here
    assert spawn["attrs"]["image_size_x"] == "64" and spawn["attrs"]["sensor_tick"] == "0.0"
    assert st["end"] == "world left synchronous mode (end of run)"
    assert st["frames"] == 30 and st["gaps"] == [] and st["ffmpeg_rc"] == 0
    rows = (out / "chase_view.mp4.frames.csv").read_text().splitlines()
    assert rows[0] == "video_index,carla_frame,sim_time_s,arrival_unix_s"
    body = [r.split(",") for r in rows[1:]]
    assert len(body) == st["written"] == st["queued"] - st["write_errors"]
    assert [int(r[0]) for r in body] == list(range(len(body)))
    assert [float(r[2]) for r in body] == [pytest.approx(int(r[1]) * 0.05) for r in body]
    n = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                        "stream=nb_read_frames,r_frame_rate", "-of", "json", str(out / "chase_view.mp4")],
                       capture_output=True, text=True, check=True)
    stream = json.loads(n.stdout)["streams"][0]
    assert int(stream["nb_read_frames"]) == len(body)
    assert stream["r_frame_rate"] == "20/1"
    # this host has no NVENC: the recorder fell back and said so
    if st["encoder"] == "libx264":
        assert "NVENC" in st["encoder_fallback"]


def test_the_recorder_waits_for_a_loading_simulator(tmp_path: Path) -> None:
    p, out = run_recorder(tmp_path, 5, "--encoder", "libx264", FAKE_CARLA_LOAD_S="3", FAKE_HERO_AFTER_S="1")
    assert p.returncode == 0, p.stdout + p.stderr
    st = json.loads((out / "summary.json").read_text())
    assert st["sim_answered_after_s"] >= 2.5
    assert "the simulator answered after" in p.stdout


def test_no_simulator_within_the_wait_fails(tmp_path: Path) -> None:
    p, out = run_recorder(tmp_path, 5, "--sim-wait-s", "1", FAKE_CARLA_LOAD_S="60")
    assert p.returncode == 1
    assert "did not answer" in json.loads((out / "summary.json").read_text())["end"]
