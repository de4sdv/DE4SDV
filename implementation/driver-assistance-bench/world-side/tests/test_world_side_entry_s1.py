"""The world side's session entry for session kind s1 (lane I-W): run_scenario.sh runs every setting of the s1 run
list and the stop run, and passes DA_ACKERMANN_GAINS through to the world side; calibrate.sh passes it too.

The caller's contract (lane C-s1, session/README.md "Entry-point contracts", ENTRY_SIM_RUN): ``run_scenario.sh
<out> <scenario> <setting id>`` for each run of ``s1_runs.tsv`` (``SC-DRIVING-013 SC-DRIVING-013@30``, ...), the stop
run as ``S1_STOP_SCENARIO S1_STOP_SETTING`` = ``SC-DRIVING-012 stop`` (session/entrypoints.env). The scripts run for
real against the fake CARLA module, paced on the wall clock.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPTS = HERE.parent / "scripts"


def script_env(tmp_path: Path, **extra: str) -> dict[str, str]:
    out = tmp_path / "out"
    out.mkdir(exist_ok=True)
    env = {k: v for k, v in os.environ.items() if k != "DA_ACKERMANN_GAINS"}
    env.update(SIM_PY=sys.executable, DA_OUT=str(out), WORLD_START="35:-2:0.0", RUN_S="1",
               PYTHONPATH=os.pathsep.join([str(HERE / "fake_carla"), os.environ.get("PYTHONPATH", "")]))
    env.update(extra)
    return env


def wait_for(path: Path, proc, timeout: float = 60.0) -> None:
    end = time.monotonic() + timeout
    while not path.exists():
        assert proc.poll() is None, proc.communicate()[0]
        assert time.monotonic() < end, f"{path} did not appear"
        time.sleep(0.05)


def run_entry(tmp_path: Path, scenario: str, setting: str, name: str = "run", **extra: str):
    out = tmp_path / "out" / name
    p = subprocess.Popen(["bash", str(SCRIPTS / "run_scenario.sh"), str(out), scenario, setting],
                         env=script_env(tmp_path, **extra), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    wait_for(out / "simulator" / "ready.json", p)
    (out / "go").touch()
    (out / "release").touch()
    log, _ = p.communicate(timeout=120)
    return p.returncode, log, out / "simulator"


@pytest.mark.parametrize("scenario,setting", [("SC-DRIVING-013", "SC-DRIVING-013@30"),
                                              ("SC-DRIVING-014", "SC-DRIVING-014@30"),
                                              ("SC-DRIVING-015", "SC-DRIVING-015@40")])
def test_run_scenario_runs_every_s1_setting_as_its_run_list_names_it(tmp_path, scenario, setting):
    rc, log, sim = run_entry(tmp_path, scenario, setting)
    assert rc == 0, log
    assert f"RUN_DONE {scenario} {setting}" in log and f" run --map Town06_Opt --port 2000 --setting {setting} " in log
    rec = json.loads((sim / "setting_record.json").read_text())
    assert rec["kind"] == "run" and rec["setting"]["setting_id"] == setting


def test_the_stop_run_is_the_setting_stop(tmp_path):
    rc, log, sim = run_entry(tmp_path, "SC-DRIVING-012", "stop")
    assert rc == 0, log
    assert "RUN_DONE SC-DRIVING-012 stop" in log and "--setting stop " in log
    rec = json.loads((sim / "setting_record.json").read_text())
    assert rec["setting"]["setting_id"] == "stop" and rec["setting"]["judgeable"] is None


def test_run_scenario_passes_the_gains_through(tmp_path):
    rc, log, sim = run_entry(tmp_path, "SC-DRIVING-015", "SC-DRIVING-015@40", DA_ACKERMANN_GAINS="v1")
    assert rc == 0, log
    assert "DA_ACKERMANN_GAINS=v1" in log
    rec = json.loads((sim / "setting_record.json").read_text())
    assert rec["ackermannGains"]["requested"] == "v1" and rec["site"]["siteId"] == "sc015-turnoff"
    rc2, log2, _ = run_entry(tmp_path, "SC-DRIVING-012", "SC-DRIVING-012@20", name="default")
    assert rc2 == 0 and "DA_ACKERMANN_GAINS unset (default)" in log2


def test_run_scenario_ends_rc_2_on_a_refused_gains_value(tmp_path):
    out = tmp_path / "out" / "bad"
    p = subprocess.run(["bash", str(SCRIPTS / "run_scenario.sh"), str(out), "SC-DRIVING-012", "SC-DRIVING-012@20"],
                       env=script_env(tmp_path, DA_ACKERMANN_GAINS="v9"), capture_output=True, text=True, timeout=60)
    assert p.returncode == 2, p.stdout + p.stderr
    assert "FAIL run rc=2" in p.stdout and "DA_ACKERMANN_GAINS='v9' is refused" in p.stdout


def test_calibrate_passes_the_gains_through(tmp_path):
    out = tmp_path / "out" / "cal"
    board = tmp_path / "board.png"
    import camera_calibration as camcal                       # the world side's own writer of a PNG
    board.write_bytes(camcal.bgra_to_png(bytes([0, 0, 0, 255, 255, 255, 255, 255] * 32), 8, 8))
    p = subprocess.run(["bash", str(SCRIPTS / "calibrate.sh"), str(out), "settings"],
                       env=script_env(tmp_path, DA_ACKERMANN_GAINS="v1", CALIB_SPEEDS="20", CALIB_DECELS="1",
                                      CHECKERBOARD=str(board)), capture_output=True, text=True, timeout=300)
    assert p.returncode == 0, p.stdout + p.stderr
    rec = json.loads((out / "calib_decel" / "simulator" / "calibration_decel.json").read_text())
    assert rec["ackermannGains"]["requested"] == "v1"
    assert rec["ackermannGains"]["spawns"][0]["readBackEqual"] is True
