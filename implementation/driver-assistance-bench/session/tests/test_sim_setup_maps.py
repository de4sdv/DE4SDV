"""sim_setup.sh's map check: before it reports ready, every map the session kind's world side needs is in the
server's get_available_maps(), so a host without CARLA's AdditionalMaps pack ends a session at sim_setup with a
named reason, not at the warm-up (the paid p10-1 of 20261119T123937Z: sim_setup rc 0, then the warm-up's survey
"Map 'Town04' not found").

The script runs for real (bash) with stand-ins for sudo, systemd-run, systemctl, pkill, ss, nvidia-smi and ffmpeg
on PATH, and the world side's fake CARLA module as the client: its map lists replay the real server's answers
(1.0-14ac3b1a5 on the G4, 2026-11-19, p10-1-world-maps-20261119/FACTS.md).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
BENCH = HERE.parent.parent
SIM_SETUP = BENCH / "session" / "remote" / "sim_setup.sh"
FAKE_CARLA = BENCH / "world-side" / "tests" / "fake_carla"
BASE_PACKAGE_MAPS = "EmptyMap,Town10HD_Opt,Town12,Town15"
WITH_ADDITIONAL_MAPS = ("Eixample,EmptyMap,Mine_01,Town01_Opt,Town02_Opt,Town03_Opt,Town04_Opt,Town05_Opt,"
                        "Town06_Opt,Town07_Opt,Town10HD_Opt,Town11,Town12,Town13,Town15,Town_C")

STANDINS = {
    "sudo": 'exec "$@"\n',
    "systemd-run": 'echo "systemd-run $*" >> "$FAKE_LOG"\n',
    "systemctl": 'echo "systemctl $*" >> "$FAKE_LOG"\n',
    "pkill": "exit 1\n",
    "ss": 'echo "LISTEN 0 128 0.0.0.0:2000 0.0.0.0:*"\n',
    "nvidia-smi": 'echo "NVIDIA RTX PRO 6000, 580.178.04, 97887 MiB"\n',
    "ffmpeg": "exit 0\n",
}


def run_sim_setup(tmp_path: Path, maps: str, **extra: str) -> subprocess.CompletedProcess:
    fakebin = tmp_path / "bin"
    fakebin.mkdir()
    for name, body in STANDINS.items():
        f = fakebin / name
        f.write_text("#!/bin/bash\n" + body)
        f.chmod(0o755)
    root = tmp_path / "sim"
    carla_root = root / "pkg" / "Carla-1.0-Linux-Shipping"
    carla_root.mkdir(parents=True)
    (carla_root / "CarlaUnreal.sh").write_text("#!/bin/bash\n")
    (carla_root / "CarlaUnreal.sh").chmod(0o755)
    (root / "carla_root").write_text(str(carla_root))
    env = {"PATH": f"{fakebin}:/usr/bin:/bin", "HOME": str(tmp_path), "SIM_ROOT": str(root),
           "SIM_PY": sys.executable, "PYTHONPATH": str(FAKE_CARLA), "PYTHONDONTWRITEBYTECODE": "1",
           "MIN_FREE_GB": "0", "SIM_WAIT_S": "5", "FAKE_LOG": str(tmp_path / "fake.log"), "FAKE_CARLA_MAPS": maps}
    env.update(extra)
    return subprocess.run(["bash", str(SIM_SETUP), str(tmp_path / "out")], env=env, capture_output=True, text=True,
                          timeout=120)


def test_sim_setup_fails_with_a_named_reason_when_the_world_sides_map_is_not_on_the_server(tmp_path: Path):
    p = run_sim_setup(tmp_path, BASE_PACKAGE_MAPS)
    log = p.stdout + p.stderr
    assert p.returncode != 0, log
    assert "the simulator answered" in log                       # the server is up: the map is what is missing
    assert "FAIL map(s) not on the server: Town06_Opt" in log
    assert "the server's maps: EmptyMap, Town10HD_Opt, Town12, Town15" in log
    assert "install CARLA's AdditionalMaps pack once on this host (world-side/README.md, \"The maps pack\")" in log


def test_sim_setup_passes_when_the_world_sides_map_is_on_the_server(tmp_path: Path):
    p = run_sim_setup(tmp_path, WITH_ADDITIONAL_MAPS)
    log = p.stdout + p.stderr
    assert p.returncode == 0, log
    assert "maps the world side needs, all on the server: Town06_Opt" in log


def test_sim_setup_checks_the_map_the_session_s_world_side_is_given(tmp_path: Path):
    # WORLD_MAP is the world side's own setting (world-side/scripts/common.sh), so sim_setup checks that name
    p = run_sim_setup(tmp_path, WITH_ADDITIONAL_MAPS.replace("Town13,", ""), WORLD_MAP="Town13")
    log = p.stdout + p.stderr
    assert p.returncode != 0, log
    assert "FAIL map(s) not on the server: Town13" in log
