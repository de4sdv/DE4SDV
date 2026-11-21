"""The Ackermann gains option of the world side (lane I-W): ``DA_ACKERMANN_GAINS`` (default or v1).

Lead contract of 2026-11-20 (DECISIONS.md, the last entry): the gains reach the simulator-host steps as
``DA_ACKERMANN_GAINS``; the default stays CARLA's own until the owner answers D-S1-2. v1 is lane A2's probe variant v1
(s1-map/asm005_probe_table.json): speed_kp 0.3 and accel_kp 0.1, the other four as CARLA's defaults. The world side
applies them to the hero right after each spawn through ``AckermannControllerSettings``, reads them back, and records
the requested and the read-back values in setting_record.json and the calibration records.
"""

from __future__ import annotations

import json

import pytest

import carla  # the fake
from world_side_testkit import AdapterStandIn, run_main

import da_world_side as ws_mod

ENV = "DA_ACKERMANN_GAINS"
FIELDS = ("speed_kp", "speed_ki", "speed_kd", "accel_kp", "accel_ki", "accel_kd")
# asm005_probe_table.json, variant v1, pinned as numbers
V1 = {"speed_kp": 0.3, "speed_ki": 0.0, "speed_kd": 0.25, "accel_kp": 0.1, "accel_ki": 0.0, "accel_kd": 0.01}
# the real server's read-back on a fresh vehicle.lincoln.mkz (G4 read of 2026-11-20)
CARLA_DEFAULT = {"speed_kp": 0.15, "speed_ki": 0.0, "speed_kd": 0.25, "accel_kp": 0.01, "accel_ki": 0.0,
                 "accel_kd": 0.01}


def _run(tmp_path, factory, clock, *extra, command="run", setting="SC-DRIVING-012@20", name="run"):
    run_dir = tmp_path / name
    rc, lines = run_main([command, "--run-dir", str(run_dir), "--setting", setting, *extra], factory, clock)
    return rc, lines, run_dir / "simulator"


def _hero_ids(server):
    return [e[1] for e in server.log if e[0] == "spawn" and e[2] == "vehicle.lincoln.mkz"]


def _applied(server):
    return [c for c in server.control_log if c["call"] == "apply_ackermann_controller_settings"]


def test_unset_means_carlas_own_gains_read_back_and_recorded(tmp_path, server, factory, clock, monkeypatch):
    monkeypatch.delenv(ENV, raising=False)
    AdapterStandIn(server, target_kmh=21.0)
    rc, _lines, sim = _run(tmp_path, factory, clock, "--run-s", "1")
    assert rc == 0
    assert _applied(server) == []                                   # nothing applied: CARLA's own gains
    g = json.loads((sim / "setting_record.json").read_text())["ackermannGains"]
    assert g["env"] == ENV and g["requested"] == "default" and g["values"] is None
    assert len(g["spawns"]) == 1 and g["spawns"][0]["applied"] is None
    assert g["spawns"][0]["readBack"] == pytest.approx(CARLA_DEFAULT)


def test_v1_is_applied_right_after_the_spawn_and_read_back(tmp_path, server, factory, clock, monkeypatch):
    monkeypatch.setenv(ENV, "v1")
    monkeypatch.setattr(carla.Actor, "destroy", lambda self: True)          # keep the states for the spawn frame
    AdapterStandIn(server, target_kmh=21.0)
    rc, _lines, sim = _run(tmp_path, factory, clock, "--run-s", "1")
    assert rc == 0
    applied = _applied(server)
    hero = _hero_ids(server)
    assert [c["actor"] for c in applied] == hero and len(hero) == 1
    assert dict(zip(FIELDS, applied[0]["value"])) == V1
    # right after the spawn: no tick between the spawn and the apply
    assert applied[0]["frame"] == server.actors[hero[0]].spawned_at_frame
    g = json.loads((sim / "setting_record.json").read_text())["ackermannGains"]
    assert g["requested"] == "v1" and g["values"] == V1
    assert g["spawns"][0]["applied"] == V1 and g["spawns"][0]["readBack"] == pytest.approx(V1)
    assert g["spawns"][0]["readBackEqual"] is True
    assert "asm005_probe_table.json" in g["source"]


@pytest.mark.parametrize("value", ["v2", "", "V1", "default "])
def test_any_other_value_is_refused_with_a_named_reason(tmp_path, server, factory, clock, monkeypatch, value):
    monkeypatch.setenv(ENV, value)
    rc, lines, sim = _run(tmp_path, factory, clock, "--run-s", "1")
    assert rc == 2
    err = json.loads(lines[-1])
    assert err["event"] == "error"
    assert f"{ENV}={value!r} is refused" in err["reason"] and "default or v1" in err["reason"]
    assert not server.actors and server.log == []                   # refused before the world was touched


def test_a_read_back_that_differs_is_a_bench_error(tmp_path, server, factory, clock, monkeypatch):
    monkeypatch.setenv(ENV, "v1")
    monkeypatch.setattr(carla.Actor, "apply_ackermann_controller_settings", lambda self, s: None)
    rc, _lines, sim = _run(tmp_path, factory, clock, "--run-s", "1")
    assert rc == 2
    reason = json.loads((sim / "error.json").read_text())["reason"]
    assert "Ackermann gains v1" in reason and "read back" in reason
    assert not (sim / "ready.json").exists()


def test_calib_decel_applies_v1_to_every_passs_hero_and_records_it(tmp_path, server, factory, clock, monkeypatch):
    monkeypatch.setenv(ENV, "v1")
    rc, _lines, sim = _run(tmp_path, factory, clock, "--speeds", "20", "--decels", "1,2", command="calib-decel",
                           name="decel")
    assert rc == 0
    heroes = _hero_ids(server)
    assert len(heroes) == 2 and [c["actor"] for c in _applied(server)] == heroes
    rec = json.loads((sim / "calibration_decel.json").read_text())
    g = rec["ackermannGains"]
    assert g["requested"] == "v1" and len(g["spawns"]) == 2
    assert all(s["readBack"] == pytest.approx(V1) and s["readBackEqual"] for s in g["spawns"])
    assert rec["context"]["ackermannGains"] == g


def test_calib_steer_records_the_gains_in_its_calibration_record(tmp_path, server, factory, clock, monkeypatch):
    monkeypatch.setenv(ENV, "v1")
    AdapterStandIn(server, target_kmh=21.0)
    rc, _lines, sim = _run(tmp_path, factory, clock, "--run-s", "2", command="calib-steer", name="steer")
    assert rc == 0
    rec = json.loads((sim / "calibration_steering.json").read_text())
    assert rec["ackermannGains"]["requested"] == "v1"
    assert rec["ackermannGains"]["spawns"][0]["readBack"] == pytest.approx(V1)


def test_the_dry_run_plan_names_the_gains(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV, "v1")
    lines: list = []
    rc = ws_mod.main(["run", "--run-dir", str(tmp_path / "d"), "--dry-run"], out=lines.append)
    assert rc == 0
    assert json.loads(lines[0])["ackermannGains"] == {"requested": "v1", "values": V1}


def test_the_fake_reads_back_carlas_defaults(server):
    world = carla.Client("127.0.0.1", 2000, _server=server, name="t").get_world()
    hero = world.spawn_actor(world.get_blueprint_library().find("vehicle.lincoln.mkz"), carla.Transform())
    st = hero.get_ackermann_controller_settings()
    assert {k: getattr(st, k) for k in FIELDS} == CARLA_DEFAULT
    hero.apply_ackermann_controller_settings(carla.AckermannControllerSettings(**V1))
    st = hero.get_ackermann_controller_settings()
    assert {k: getattr(st, k) for k in FIELDS} == V1
