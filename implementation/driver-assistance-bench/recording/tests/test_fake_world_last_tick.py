"""The world side's fake CARLA as a synchronous world that is not ticking (actor_list_at_last_tick).

Run in a subprocess so that this fake `carla` never meets the chase recorder's own fake in one interpreter.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

WORLD_FAKE = Path(__file__).resolve().parent.parent.parent / "world-side" / "tests" / "fake_carla"

PROBE = r"""
import json, sys
sys.path.insert(0, sys.argv[1])
import carla
srv = carla._Server("Carla/Maps/Town06_Opt")
srv.actor_list_at_last_tick = sys.argv[2] == "1"
ws = carla.Client("h", 2000, _server=srv, name="world_side").get_world()
other = carla.Client("h", 2000, _server=srv, name="other").get_world()
s = ws.get_settings(); s.synchronous_mode, s.fixed_delta_seconds = True, 0.05; ws.apply_settings(s)
ws.tick()
bp = ws.get_blueprint_library().find("vehicle.lincoln.mkz"); bp.set_attribute("role_name", "hero")
hero = ws.spawn_actor(bp, carla.Transform(carla.Location(x=100.0)))
r = {"own_before": ws.get_actors().find(hero.id) is not None,
     "other_before": other.get_actors().find(hero.id) is not None,
     "snap_before": other.get_snapshot().find(hero.id) is not None}
seen = []
other.on_tick(lambda snap: seen.append(snap.find(hero.id) is not None))
ws.tick()
r.update(other_after=other.get_actors().find(hero.id) is not None, tick_saw=list(seen),
         snap_after=other.get_snapshot().has_actor(hero.id))
carla._SHARED_SERVER = srv
r["shared"] = carla.Client("h", 2000)._server is srv
late = carla.Client("h", 2000, _server=srv, name="late").get_world()   # connects after the last tick
r["late_before"] = [len(late.get_actors()), late.get_snapshot().frame]
hero.destroy(); ws.tick()
r["after_destroy"] = [other.get_actors().find(hero.id) is not None, seen[-1]]
r["late_after"] = [len(late.get_actors()), late.get_snapshot().frame == srv.frame]
print(json.dumps(r))
"""


def probe(last_tick: str) -> dict:
    e = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "FAKE_"))}
    p = subprocess.run([sys.executable, "-B", "-c", PROBE, str(WORLD_FAKE), last_tick], env=e,
                       capture_output=True, text=True, timeout=60)
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


def test_an_actor_spawned_after_the_last_tick_is_listed_only_after_the_next() -> None:
    r = probe("1")
    assert r == {"own_before": False, "other_before": False, "snap_before": False, "other_after": True,
                 "tick_saw": [True], "snap_after": True, "shared": True, "after_destroy": [False, False],
                 "late_before": [0, 0], "late_after": [0, True]}


def test_a_client_that_connects_in_the_pause_lists_nothing_until_the_next_tick() -> None:
    # the real server (G4, 2026-11-19): 0 actors and a snapshot of frame 0 until the first tick after the go
    r = probe("1")
    assert r["late_before"] == [0, 0] and r["shared"] is True


def test_without_the_switch_the_list_stays_live() -> None:
    r = probe("0")
    assert r["own_before"] is True and r["other_before"] is True and r["tick_saw"] == [True]
