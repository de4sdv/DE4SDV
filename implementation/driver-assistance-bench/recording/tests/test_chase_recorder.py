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
WORLD_FAKE = HERE.parent.parent / "world-side" / "tests" / "fake_carla"
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


# ------------------------------------------------------------------ a synchronous world that pauses before the go
# p10-2's session 20261119T174606Z, run 1: the world side spawned the hero, ticked 10 times, then waited 156 s for the go
# without ticking. A client's actor list is the state of the last tick, so the recorder's own camera (spawned in the
# pause) was missing from it, and the recorder ended at once with 0 frames: "ego or camera deleted by another client".


def run_paused(tmp: Path, *world: str, rec: tuple = ()) -> tuple[subprocess.CompletedProcess, dict, dict]:
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not installed")
    out = tmp / "rec"
    e = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "FAKE_"))}
    e["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([sys.executable, "-B", str(HERE / "paused_world.py"), str(WORLD_FAKE), str(RECORDER), *world,
                        "--", "--out", str(out), "--width", "64", "--height", "36", "--encoder", "libx264",
                        "--max-s", "60", *rec], env=e, capture_output=True, text=True, timeout=120)
    facts = [json.loads(x[6:]) for x in p.stdout.splitlines() if x.startswith("WORLD ")]
    assert facts, p.stdout + p.stderr
    st = json.loads((out / "summary.json").read_text()) if (out / "summary.json").exists() else {}
    return p, st, facts[0]


def test_a_pause_between_setup_and_go_is_no_deletion(tmp_path: Path) -> None:
    p, st, w = run_paused(tmp_path, "--pause-s", "3", "--run-ticks", "40")
    assert st["end"] == "world left synchronous mode (end of run)", p.stdout + p.stderr
    assert p.returncode == 0
    assert st["ego_id"] == w["hero_id"] != w["target_id"]          # locked onto the hero by its role
    assert st["frames"] == st["written"] == 40 and st["gaps"] == []
    assert (st["first_frame"], st["last_frame"]) == (w["run_frames"][0], w["run_frames"][-1])
    rows = (tmp_path / "rec" / "chase_view.mp4.frames.csv").read_text().splitlines()[1:]
    assert [int(r.split(",")[1]) for r in rows] == w["run_frames"]


def test_a_camera_deleted_on_a_tick_ends_the_recording(tmp_path: Path) -> None:
    p, st, w = run_paused(tmp_path, "--pause-s", "2", "--run-ticks", "200", "--delete", "camera@10")
    assert w["deleted"][0] == "camera" and w["deleted"][1] == st["camera_id"]
    assert st["end"] == "ego or camera deleted by another client", p.stdout + p.stderr
    assert st["gone"] == {"actor": st["camera_id"], "frame": w["deleted"][2] + 1}   # the first tick without it
    assert st["frames"] == 9 and st["last_frame"] == w["run_frames"][8]
    assert st["ran_s"] < w["go_at_s"] + 5                            # not the run's end (200 ticks, 10 s)


def test_a_hero_deleted_on_a_tick_ends_the_recording(tmp_path: Path) -> None:
    p, st, w = run_paused(tmp_path, "--pause-s", "2", "--run-ticks", "200", "--delete", "hero@10")
    assert w["deleted"][:2] == ["hero", st["ego_id"]]
    assert st["end"] == "ego or camera deleted by another client", p.stdout + p.stderr
    assert st["gone"] == {"actor": st["ego_id"], "frame": w["deleted"][2] + 1}
    assert st["frames"] >= 9                                         # the camera renders until the next poll
    assert st["ran_s"] < w["go_at_s"] + 5


def test_a_transient_poll_error_does_not_end_the_recording(tmp_path: Path) -> None:
    # the world's get_settings times out once or twice in the pause (a long first render, say)
    p, st, w = run_paused(tmp_path, "--pause-s", "4", "--run-ticks", "40", "--settings-errors", "2.2:3.4")
    assert w.get("settings_errors", 0) >= 1
    assert st["end"] == "world left synchronous mode (end of run)", p.stdout + p.stderr
    assert st["poll_errors"] == w["settings_errors"] and st["frames"] == 40 and p.returncode == 0


def test_a_simulator_that_stops_answering_ends_the_recording(tmp_path: Path) -> None:
    p, st, w = run_paused(tmp_path, "--pause-s", "30", "--run-ticks", "5", "--settings-errors", "2.2:100",
                          rec=("--poll-errors-max", "3"))
    assert st["end"] == "the simulator did not answer 3 polls in a row", p.stdout + p.stderr
    assert st["poll_errors"] == 3 and p.returncode == 1
    assert st["ran_s"] < 15


def test_only_failed_polls_in_a_row_end_the_recording(tmp_path: Path) -> None:
    # three error windows of 1.9 s (1 or 2 polls at the 1 s poll interval each), 1.2 s apart (an answered poll
    # between them): at least 3 failed polls, never 3 in a row
    p, st, w = run_paused(tmp_path, "--pause-s", "11", "--run-ticks", "20",
                          "--settings-errors", "2.0:3.9,5.1:7.0,8.2:10.1",
                          rec=("--poll-errors-max", "3"))
    assert st["poll_errors"] == w["settings_errors"] >= 3
    assert st["end"] == "world left synchronous mode (end of run)", p.stdout + p.stderr
    assert st["frames"] == 20 and p.returncode == 0


def test_the_default_cap_outlasts_the_session_go_wait() -> None:
    # the session's go limit (GO_LIMIT_S, 380 s) plus p10-2's 90 s run, with margin: the recorder starts before the
    # world side and must still be recording at the run's end
    a = cr.build_parser().parse_args(["--out", "x"])
    assert a.max_s >= 380 + 90 + 60


class _Snap:
    def __init__(self, frame: int, *ids: int) -> None:
        self.frame, self.ids = frame, ids

    def find(self, actor_id: int):
        return object() if actor_id in self.ids else None


def test_liveness_is_judged_on_ticks_only_after_first_appearance() -> None:
    w = cr.TickLiveness(ego_id=1, camera_id=2)
    w.on_tick(_Snap(10, 1))          # the camera spawned between ticks: not in this tick yet
    assert w.gone is None
    w.on_tick(_Snap(11, 1, 2))
    w.on_tick(_Snap(12, 1, 2))
    assert w.gone is None and w.ticks == 3 and w.camera_first_frame == 11
    w.on_tick(_Snap(13, 1))
    assert w.gone == {"actor": 2, "frame": 13}


def test_the_hero_is_gone_from_the_first_tick_that_lacks_it() -> None:
    # the hero was found in the actor list, which is the state of a tick: it has appeared already
    w = cr.TickLiveness(ego_id=1, camera_id=2)
    w.on_tick(_Snap(20, 2))
    assert w.gone == {"actor": 1, "frame": 20}
    w.on_tick(_Snap(21, 1, 2))
    assert w.gone == {"actor": 1, "frame": 20}   # the first verdict stands
