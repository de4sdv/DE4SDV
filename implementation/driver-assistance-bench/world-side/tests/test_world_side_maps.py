"""The map on the real CARLA 1.0 server (1.0-14ac3b1a5 on the G4, 2026-11-19; facts in
inc-driving-002/phase10/p10-1-world-maps-20261119/FACTS.md).

The paid p10-1 of 20261119T123937Z ended at its warm-up: ``load_world('Town04')`` answered "Map 'Town04' not
found". The base package has four maps; CARLA's AdditionalMaps pack adds Town04_Opt, Town06_Opt and others, under
those exact names (``load_world`` takes nothing else). On Town04_Opt the longest straight under the survey's rule is
235 m, short of the 320 m of SC-DRIVING-012@60 and the 300 m of calib-decel; Town06_Opt has 400 m and more. The
fake CARLA module replays the server's answers (``BASE_PACKAGE_MAPS``, ``WITH_ADDITIONAL_MAPS``, the strict
``load_world``); the straights come from the server's own survey (``data/real_server_straights.json``).
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import carla  # the fake
import da_world_side as ws
import scenarios
from conftest import run_main

HERE = Path(__file__).resolve().parent
WS = HERE.parent
REAL_MAP = "Town06_Opt"       # FACTS.md: the pack's map whose straights hold every setting
PACK_SHA256 = "33678e7c1571892f15df71a88feb2000dadacc0f71ae8e72f9e45813d60930d6"


def test_without_the_pack_the_refusal_names_the_map_the_servers_maps_and_the_install(tmp_path, clock):
    server = carla._Server("Carla/Maps/Town10HD_Opt")
    server.available_maps = list(carla.BASE_PACKAGE_MAPS)          # the 20261119T123937Z server
    server.clock = clock

    def factory(host, port):
        return carla.Client(host, port, _server=server)

    rc, lines = run_main(["survey", "--setting", "SC-DRIVING-012@60", "--run-dir", str(tmp_path)], factory, clock)
    assert rc == 2
    reason = json.loads((tmp_path / "simulator" / "error.json").read_text())["reason"]
    assert f"cannot load map '{REAL_MAP}'" in reason
    assert "Map 'Town06_Opt' not found" in reason                    # the server's own answer
    assert "the server's maps: EmptyMap, Town10HD_Opt, Town12, Town15" in reason
    assert "AdditionalMaps pack" in reason and "world-side/README.md" in reason and "The maps pack" in reason


def test_with_the_pack_the_default_map_loads_by_its_exact_name(tmp_path, clock):
    server = carla._Server("Carla/Maps/Town10HD_Opt")               # sim_setup leaves the server on Town10HD_Opt
    server.clock = clock
    clients = []

    def factory(host, port):
        clients.append(carla.Client(host, port, _server=server))
        return clients[-1]

    rc, lines = run_main(["survey", "--setting", "SC-DRIVING-012@60", "--run-dir", str(tmp_path)], factory, clock)
    assert rc == 0, lines
    assert clients[0].load_calls == [REAL_MAP]
    connected = [json.loads(line) for line in lines if '"connected"' in line][0]
    assert connected["map"] == f"Carla/Maps/{REAL_MAP}"


def test_the_default_map_holds_every_settings_road_on_the_real_server():
    real = json.loads((HERE / "data" / "real_server_straights.json").read_text())["longestStraightM"]
    longest = real.get(ws.DEFAULT_MAP, 0.0)
    for st in scenarios.SETTINGS.values():
        if st.site is not None:            # a site setting's road is the site's (sites.resolve, lane A2)
            continue
        need = ws.needed_road_m(st, st.target_ahead_m)
        assert need <= longest, f"{ws.DEFAULT_MAP}: {st.setting_id} needs {need} m, the server has {longest} m"
    assert ws.build_parser().parse_args(["calib-decel", "--run-dir", "x"]).road_m <= longest
    # why not Town04_Opt: 235 m < 320 m of SC-DRIVING-012@60
    assert real["Town04_Opt"] < ws.needed_road_m(scenarios.SETTINGS["SC-DRIVING-012@60"], 280.0)


def test_one_map_name_in_the_code_the_scripts_and_the_readme():
    assert ws.DEFAULT_MAP == REAL_MAP and REAL_MAP in carla.WITH_ADDITIONAL_MAPS
    common = (WS / "scripts" / "common.sh").read_text()
    assert f"WORLD_MAP=${{WORLD_MAP:-{REAL_MAP}}}" in common
    out = subprocess.run(["bash", "-c", '. "$1"; echo "$WORLD_MAP"', "_", str(WS / "scripts" / "common.sh")],
                         capture_output=True, text=True, env={"PATH": "/usr/bin:/bin"})
    assert out.stdout.strip() == REAL_MAP
    readme = (WS / "README.md").read_text()
    maps = re.findall(r"--map (\S+)", readme)
    assert maps and set(maps) == {REAL_MAP}
    assert not re.search(r"\bTown04\b(?!_Opt)", readme + common + (WS / "da_world_side.py").read_text())


def test_the_readme_gives_the_one_time_install_of_the_pack():
    readme = (WS / "README.md").read_text()
    section = readme.split("## The maps pack", 1)[1].split("\n## ", 1)[0]
    assert f"sha256 `{PACK_SHA256}`" in section and "6830970575 bytes" in section
    assert f"WANT={PACK_SHA256}" in section                         # the streamed install refuses any other
    assert "gs://de4sdv-carla-d19a-packages/carla-1.0-14ac3b1a5/CARLA_UE5_Weekly_AdditionalMaps.tar.gz" in section
    assert "CarlaUnreal/Packs/AdditionalMaps" in section
    assert re.search(r'carla_pack\.py"? verify ', section) and re.search(r'carla_pack\.py"? inspect .*--server', section)
    assert "sha256sum" in section
