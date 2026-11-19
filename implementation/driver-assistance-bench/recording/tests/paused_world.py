#!/usr/bin/env python3
"""Run chase_recorder.py's main() against the world side's fake CARLA, with a world-side-like client that pauses.

The pattern of p10-2's session 20261119T174606Z, run 1: the world side sets synchronous mode at 0.05 s, spawns a
target vehicle (role "target") and the hero (role "hero"), ticks --setup-ticks times, writes ready, waits --pause-s
for the go WITHOUT ticking, then ticks --run-ticks times (one per 0.05 s of wall time) and leaves synchronous mode.
The fake's world is the real server's: an actor list is the state of the last tick (actor_list_at_last_tick).

Usage: paused_world.py <world-side fake dir> <recorder> [--pause-s S] [--setup-ticks N] [--run-ticks N]
       [--hero-after-s S] [--delete camera@K|hero@K] [--settings-errors FROM_S:TO_S[,...]] [--] <recorder args...>
Prints one line "WORLD {json}" (the world's facts) and exits with the recorder's status.
"""
from __future__ import annotations

import argparse
import json
import runpy
import sys
import threading
import time


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("fake_dir")
    ap.add_argument("recorder")
    ap.add_argument("--pause-s", type=float, default=3.0)
    ap.add_argument("--setup-ticks", type=int, default=10)
    ap.add_argument("--run-ticks", type=int, default=40)
    ap.add_argument("--hero-after-s", type=float, default=1.0)
    ap.add_argument("--delete", default="")
    ap.add_argument("--settings-errors", default="", help="get_settings raises between these world times (s): FROM:TO[,FROM:TO...]")
    argv = sys.argv[1:]
    cut = argv.index("--") if "--" in argv else len(argv)
    a = ap.parse_args(argv[:cut])
    rest = argv[cut + 1:]
    sys.path.insert(0, a.fake_dir)
    import carla

    srv = carla._Server("Carla/Maps/Town06_Opt")
    srv.actor_list_at_last_tick = True
    carla._SHARED_SERVER = srv
    facts: dict = {"run_frames": [], "deleted": None}
    t0 = time.time()

    if a.settings_errors:
        windows = [tuple(float(x) for x in w.split(":")) for w in a.settings_errors.split(",")]
        real = carla.World.get_settings

        def flaky(self):
            if self._client.name == "recorder" and any(lo <= time.time() - t0 < hi for lo, hi in windows):
                facts["settings_errors"] = facts.get("settings_errors", 0) + 1
                raise RuntimeError("time-out of 10000ms while waiting for the simulator")
            return real(self)
        carla.World.get_settings = flaky

    def world_side() -> None:
        client = carla.Client("127.0.0.1", 2000, _server=srv, name="world_side")
        world = client.get_world()
        st = world.get_settings()
        st.synchronous_mode, st.fixed_delta_seconds = True, 0.05
        world.apply_settings(st)
        world.tick()
        time.sleep(a.hero_after_s)
        lib = world.get_blueprint_library()
        sp = carla.Transform(carla.Location(x=100.0, y=0.0, z=0.5))
        bp = lib.find("vehicle.lincoln.mkz")
        bp.set_attribute("role_name", "target")
        target = world.spawn_actor(bp, carla.Transform(carla.Location(x=160.0, y=0.0, z=0.5)))
        bp = lib.find("vehicle.lincoln.mkz")
        bp.set_attribute("role_name", "hero")
        hero = world.spawn_actor(bp, sp)
        facts["hero_id"], facts["target_id"] = hero.id, target.id
        for _ in range(a.setup_ticks):
            world.tick()
        facts["ready_frame"] = srv.frame
        time.sleep(a.pause_s)                      # the go wait: no tick
        facts["go_frame"], facts["go_at_s"] = srv.frame, round(time.time() - t0, 2)
        what, _, at = a.delete.partition("@")
        for k in range(1, a.run_ticks + 1):
            if what and k == int(at):
                victim = hero if what == "hero" else next(
                    carla.Actor(client, s) for s in srv.actors.values() if s.type_id == "sensor.camera.rgb")
                facts["deleted"] = [what, victim.id, srv.frame]
                victim.destroy()
            hero.apply_control(carla.VehicleControl(throttle=0.5))
            facts["run_frames"].append(world.tick())
            time.sleep(0.05)
        st = world.get_settings()
        st.synchronous_mode, st.fixed_delta_seconds = False, None
        world.apply_settings(st)
        facts["left_sync_at_s"] = round(time.time() - t0, 2)

    th = threading.Thread(target=world_side, daemon=True)
    th.start()
    # the recorder's own Client(host, port) joins srv through _SHARED_SERVER; name it for the error injection
    real_init = carla.Client.__init__

    def named_init(self, host, port=2000, worker_threads=0, *, _server=None, name="recorder"):
        real_init(self, host, port, worker_threads, _server=_server, name=name)
    carla.Client.__init__ = named_init
    sys.argv = [a.recorder, *rest]
    try:
        runpy.run_path(a.recorder, run_name="__main__")
        rc = 0
    except SystemExit as exc:
        rc = int(exc.code or 0)
    th.join(timeout=5)
    print("WORLD " + json.dumps(facts), flush=True)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
