"""The world side's session entries and what the wiring added to da_world_side.py: the per-tick time file, the
go/release handshake, the "travels straight" reading and the too-fast and wheelbase flags in the setting record.

The scripts run for real (bash, the real da_world_side.py) against the fake CARLA module on PYTHONPATH, paced on
the wall clock; the in-process tests use the fake clock of conftest.py. Expected values come from the lead's
answers of 2026-11-18 (B7.1, B7.2, B7.4, B13.4) and the fake's own geometry, not from the code under test.
"""

from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from conftest import AdapterStandIn, run_main

import carla  # the fake
import camera_calibration as camcal

HERE = Path(__file__).resolve().parent
WS = HERE.parent
SCRIPTS = WS / "scripts"


def script_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    env = dict(os.environ, SIM_PY=sys.executable, DA_OUT=str(out),
               PYTHONPATH=os.pathsep.join([str(HERE / "fake_carla"), os.environ.get("PYTHONPATH", "")]))
    env.update(extra)
    return env


def wait_for(path: Path, timeout: float = 30.0) -> None:
    end = time.monotonic() + timeout
    while not path.exists():
        assert time.monotonic() < end, f"{path} did not appear"
        time.sleep(0.05)


def tick_rows(sim: Path) -> list[dict]:
    with (sim / "tick_times.csv").open() as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------------------------------------- the scripts


def test_warmup_surveys_with_the_longest_setting_records_the_road_and_warms_up(tmp_path: Path) -> None:
    env = script_env(tmp_path)
    p = subprocess.run(["bash", str(SCRIPTS / "warmup.sh"), str(tmp_path / "out" / "warmup")], env=env,
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "+ " in p.stdout and "survey --map Town04 --port 2000 --setting SC-DRIVING-012@60" in p.stdout
    survey = json.loads((tmp_path / "out" / "warmup" / "survey" / "simulator" / "survey.json").read_text())
    assert survey["neededM"] == 320.0                     # 280 m ahead + 40 m, the 60 km/h setting
    state = json.loads((tmp_path / "out" / "world_start.json").read_text())
    assert state["start"] == survey["candidates"][0]["start"]
    summary = json.loads((tmp_path / "out" / "warmup" / "warmup" / "simulator" / "warmup_summary.json").read_text())
    assert summary["setting"] == "SC-DRIVING-012@20" and summary["ticks"] > 0
    assert tick_rows(tmp_path / "out" / "warmup" / "warmup" / "simulator")


def test_warmup_with_a_given_start_skips_the_survey(tmp_path: Path) -> None:
    env = script_env(tmp_path, WORLD_START="35:-2:0.0")
    p = subprocess.run(["bash", str(SCRIPTS / "warmup.sh"), str(tmp_path / "out" / "warmup")], env=env,
                       capture_output=True, text=True, timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    assert not (tmp_path / "out" / "warmup" / "survey").exists()
    assert json.loads((tmp_path / "out" / "world_start.json").read_text())["start"] == "35:-2:0.0"


def _start_run(tmp_path: Path, scenario: str = "SC-DRIVING-012", setting: str = "20kmh", **extra: str):
    env = script_env(tmp_path, WORLD_START="35:-2:0.0", RUN_S="1", **extra)
    out = tmp_path / "out" / "run1"
    p = subprocess.Popen(["bash", str(SCRIPTS / "run_scenario.sh"), str(out), scenario, setting], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return p, out


def test_run_holds_its_first_tick_until_go_and_ticks_on_until_release(tmp_path: Path) -> None:
    p, out = _start_run(tmp_path)
    sim = out / "simulator"
    wait_for(sim / "ready.json")
    time.sleep(1.0)                                      # two go polls: still no run tick
    assert not (sim / "world.jsonl").exists()
    settle_rows = len(tick_rows(sim))
    (out / "go").touch()
    wait_for(sim / "run_end.json")
    first_hold = len((sim / "hold.jsonl").read_text().splitlines()) if (sim / "hold.jsonl").exists() else 0
    time.sleep(0.6)
    assert len((sim / "hold.jsonl").read_text().splitlines()) > first_hold   # the world still ticks
    assert p.poll() is None
    (out / "release").touch()
    log, _ = p.communicate(timeout=60)
    assert p.returncode == 0, log
    assert "RUN_DONE SC-DRIVING-012 SC-DRIVING-012@20" in log
    summary = json.loads((sim / "summary.json").read_text())
    assert summary["hold"]["endedBy"] == "release file" and summary["hold"]["holdTicks"] > 0
    run_ticks = [json.loads(line)["data"] for line in (sim / "world.jsonl").read_text().splitlines()]
    assert len(run_ticks) == summary["ticks"]
    rows = tick_rows(sim)
    # one row per tick: settle, run, hold and the teardown tick
    assert len(rows) == settle_rows + len(run_ticks) + summary["hold"]["holdTicks"] + 1
    assert list(rows[0]) == ["sim_time_s", "unix_s"]
    keys = {round(float(r["sim_time_s"]), 3) for r in rows}
    assert all(round(t["simTimeS"], 3) in keys for t in run_ticks)    # the composer's lookup
    unix = [float(r["unix_s"]) for r in rows]
    assert unix == sorted(unix) and abs(unix[-1] - time.time()) < 60


def test_a_run_without_go_ends_as_a_bench_error_with_no_run_tick(tmp_path: Path) -> None:
    p, out = _start_run(tmp_path, GO_WAIT_S="1")
    log, _ = p.communicate(timeout=60)
    assert p.returncode == 2, log
    assert "no go file" in json.loads((out / "simulator" / "error.json").read_text())["reason"]
    assert not (out / "simulator" / "world.jsonl").exists()


def test_the_steering_calibration_runs_as_calib_steer_on_the_setting_road(tmp_path: Path) -> None:
    p, out = _start_run(tmp_path, "ASM-DRIVING-006", "20kmh")
    wait_for(out / "simulator" / "ready.json")
    (out / "go").touch()
    (out / "release").touch()
    log, _ = p.communicate(timeout=60)
    assert p.returncode == 0, log
    assert "calib-steer --map Town04" in log and "--setting SC-DRIVING-012@20" in log
    rec = json.loads((out / "simulator" / "setting_record.json").read_text())
    assert rec["kind"] == "calib-steer" and rec["hero"]["lateralOffsetM"] == 0.5
    assert rec["benchReadings"]["straightHeadingMaxDeg"] == 2.0
    assert (out / "simulator" / "calibration_steering.json").exists()


def test_run_scenario_refuses_an_unknown_scenario_and_a_missing_road(tmp_path: Path) -> None:
    env = script_env(tmp_path)
    bad = subprocess.run(["bash", str(SCRIPTS / "run_scenario.sh"), str(tmp_path / "r"), "SC-XX", "20kmh"], env=env,
                         capture_output=True, text=True, timeout=30)
    assert bad.returncode == 64
    noroad = subprocess.run(["bash", str(SCRIPTS / "run_scenario.sh"), str(tmp_path / "r"), "SC-DRIVING-012", "20"],
                            env=env, capture_output=True, text=True, timeout=30)
    assert noroad.returncode == 2 and "warmup.sh writes it" in noroad.stderr


def test_calibrate_runs_calib_decel_then_the_camera_capture_without_the_candidate(tmp_path: Path) -> None:
    board = tmp_path / "board.png"
    board.write_bytes(camcal.bgra_to_png(bytes([0, 0, 0, 255, 255, 255, 255, 255] * 8), 4, 4))
    env = script_env(tmp_path, WORLD_START="35:-2:0.0", CALIB_SPEEDS="20", CALIB_DECELS="5",
                     CHECKERBOARD=str(board))
    out = tmp_path / "out" / "calibrate"
    p = subprocess.run(["bash", str(SCRIPTS / "calibrate.sh"), str(out)], env=env, capture_output=True, text=True,
                       timeout=180)
    assert p.returncode == 0, p.stdout + p.stderr
    assert p.stdout.index("calib-decel") < p.stdout.index("camera-capture")
    decel = json.loads((out / "calib_decel" / "simulator" / "calibration_decel.json").read_text())
    assert decel["passes"] if "passes" in decel else decel
    cap = json.loads((out / "camcal" / "simulator" / "camera_capture.json").read_text())
    assert cap["frame"]["path"] == "calibration_frame.png"
    assert (out / "camcal" / "simulator" / "calibration_frame.png").stat().st_size > 0
    side = (out / "calib_decel" / "simulator" / "worldSide.jsonl").read_text()
    assert '"role":"de4sdv_calibration"' in side


def test_calibrate_needs_the_checkerboard(tmp_path: Path) -> None:
    env = script_env(tmp_path, WORLD_START="35:-2:0.0", CHECKERBOARD=str(tmp_path / "absent.png"))
    p = subprocess.run(["bash", str(SCRIPTS / "calibrate.sh"), str(tmp_path / "c")], env=env, capture_output=True,
                       text=True, timeout=30)
    assert p.returncode == 2 and "no checkerboard" in p.stdout


# ----------------------------------------------------------------------------------- in process, fake clock


def _run(tmp_path, factory, clock, *extra):
    run_dir = tmp_path / "run"
    rc, lines = run_main(["run", "--run-dir", str(run_dir), "--setting", "SC-DRIVING-012@20", *extra], factory,
                         clock)
    return rc, run_dir / "simulator"


def test_tick_times_has_one_row_per_server_tick(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=21.0)
    frame0 = server.frame
    rc, sim = _run(tmp_path, factory, clock)
    assert rc == 0
    rows = tick_rows(sim)
    assert len(rows) == server.frame - frame0
    sims = [float(r["sim_time_s"]) for r in rows]
    assert all(b - a == pytest.approx(0.05, abs=1e-6) for a, b in zip(sims, sims[1:]))


def test_every_setting_record_states_the_reading_of_travels_straight(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=21.0)
    _run(tmp_path, factory, clock)
    rec = json.loads((tmp_path / "run" / "simulator" / "setting_record.json").read_text())
    assert rec["benchReadings"]["straightHeadingMaxDeg"] == 2.0
    assert "within 2.0 deg of the target's heading" in rec["benchReadings"]["travelsStraight"]


@pytest.mark.parametrize("kmh, too_fast", [(21.0, False), (24.0, True)])
def test_the_setting_record_flags_a_hero_above_the_tolerance_after_the_functional_start(
        tmp_path, server, factory, clock, kmh, too_fast):
    AdapterStandIn(server, target_kmh=kmh)
    _run(tmp_path, factory, clock)
    sim = tmp_path / "run" / "simulator"
    rec = json.loads((sim / "setting_record.json").read_text())
    entry = json.loads((sim / "entry_checks.json").read_text())
    flags = rec["runFlags"]
    assert flags["tooFast"] is too_fast
    assert flags["functionalStartS"] == entry["functionalPart"]["startS"]
    if too_fast:
        assert flags["firstAboveToleranceS"] > flags["functionalStartS"]
        assert flags["maxSpeedKmhAfterStart"] > 22.0
    else:
        assert flags["firstAboveToleranceS"] is None


def test_no_functional_part_leaves_the_flag_open(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=15.0)
    _run(tmp_path, factory, clock)
    flags = json.loads((tmp_path / "run" / "simulator" / "setting_record.json").read_text())["runFlags"]
    assert flags["tooFast"] is None and "no functional part" in flags["note"]


def test_the_wheelbase_comes_from_the_wheels_and_is_not_flagged_within_two_percent(tmp_path, server, factory,
                                                                                    clock):
    AdapterStandIn(server, target_kmh=21.0)
    _run(tmp_path, factory, clock)
    wb = json.loads((tmp_path / "run" / "simulator" / "setting_record.json").read_text())["hero"]["wheelbase"]
    assert wb["wheelbaseM"] == pytest.approx(2.85, abs=1e-3)             # the fake mkz's wheelbase
    assert wb["deviationPct"] == pytest.approx(abs(2.85 - 2.86) / 2.86 * 100, abs=1e-2)
    assert wb["flagged"] is False and wb["visionPilotLM"] == 2.86
    assert "bones" in wb["method"] and len(wb["physicsControl"]["wheels"]) == 4


def test_a_wheelbase_more_than_two_percent_off_is_flagged(tmp_path, server, factory, clock, monkeypatch):
    ext, _ = carla.VEHICLE_SHAPES["vehicle.lincoln.mkz"]
    monkeypatch.setitem(carla.VEHICLE_SHAPES, "vehicle.lincoln.mkz", (ext, 2.94))   # +2.8 %
    AdapterStandIn(server, target_kmh=21.0)
    _run(tmp_path, factory, clock)
    wb = json.loads((tmp_path / "run" / "simulator" / "setting_record.json").read_text())["hero"]["wheelbase"]
    assert wb["wheelbaseM"] == pytest.approx(2.94, abs=1e-3) and wb["flagged"] is True


def test_no_wheel_position_is_recorded_as_unmeasured_never_as_a_pass(tmp_path, server, factory, clock, monkeypatch):
    monkeypatch.setattr(carla.Actor, "get_bone_names", lambda self: [])
    AdapterStandIn(server, target_kmh=21.0)
    _run(tmp_path, factory, clock)
    wb = json.loads((tmp_path / "run" / "simulator" / "setting_record.json").read_text())["hero"]["wheelbase"]
    assert wb["wheelbaseM"] is None and wb["flagged"] is None and "unmeasured" in wb


def test_go_file_timeout_and_hold_on_the_fake_clock(tmp_path, server, factory, clock):
    rc, sim = _run(tmp_path, factory, clock, "--go-file", str(tmp_path / "go"), "--go-wait-s", "5")
    assert rc == 2 and not (sim / "world.jsonl").exists()
    (tmp_path / "go2").touch()
    AdapterStandIn(server, target_kmh=21.0)
    run_dir = tmp_path / "run2"
    rc, _ = run_main(["run", "--run-dir", str(run_dir), "--go-file", str(tmp_path / "go2"), "--release-file",
                      str(tmp_path / "rel"), "--release-wait-s", "0.5"], factory, clock)
    assert rc == 0
    summary = json.loads((run_dir / "simulator" / "summary.json").read_text())
    assert summary["hold"]["endedBy"].startswith("no release file")
    holds = [json.loads(line)["data"] for line in (run_dir / "simulator" / "hold.jsonl").read_text().splitlines()]
    assert len(holds) == summary["hold"]["holdTicks"] >= 9    # about 0.5 s of paced 0.05 s ticks
    assert {h["phase"] for h in holds} == {"hold"}
