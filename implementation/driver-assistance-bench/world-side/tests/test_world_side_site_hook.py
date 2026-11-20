"""The site hook of the world side (lane I-W): settings on a site are built from lane A2's ``sites.resolve`` on the
fake that replays the real Town06_Opt read (``tests/data``), with the setting's own named rule.

Lead contracts of 2026-11-20 (DECISIONS.md, the last entry): ``setting_record.json["site"]`` is
``SiteSpec.as_record()``, guidance included; the props and the target stand at the site's poses; SC-015's target
follows its script along its path on every tick by ``set_transform`` (1.5 m/s2 to 40 km/h, at least 4 s held,
braking to 10 km/h, then the turn onto connector 863); SC-013 keeps ``enable_constant_velocity``.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

import carla  # the fake
from conftest import run_main

import da_world_side as ws_mod
import scenarios
import sites

STEP_S = 0.05      # PSR DriverAssistanceSimulationServer: the fixed step


def _ticks(sim: Path) -> list[dict]:
    return [json.loads(line)["data"] for line in (sim / "world.jsonl").read_text().splitlines()]


def _run(tmp_path, factory, clock, setting, *extra, name="run"):
    run_dir = tmp_path / name
    rc, lines = run_main(["run", "--run-dir", str(run_dir), "--setting", setting, *extra], factory, clock)
    return rc, lines, run_dir / "simulator"


@pytest.fixture
def spy(monkeypatch):
    """Records each sites.resolve call of the world side, then resolves for real."""
    calls: list = []
    real = sites.resolve

    def resolve(world_map, site_id, setting=None, **kw):
        calls.append({"site": site_id, "setting": getattr(setting, "setting_id", None), **kw})
        return real(world_map, site_id, setting, **kw)
    monkeypatch.setattr(ws_mod.sites, "resolve", resolve)
    return calls


def _expected(server, setting_id):
    st = scenarios.setting(setting_id)
    world = carla.Client("127.0.0.1", 2000, _server=server, name="test").get_world()
    lib = [b.id for b in world.get_blueprint_library().filter("static.prop.*")]
    return sites.resolve(world.get_map(), st.site, st, props_available=lib, approach_rule=st.site_approach_rule,
                         approach_min_m=st.site_approach_min_m, lane_rule=st.site_lane, rule_reason=st.site_reason)


def _spawned(server, type_prefix):
    return [server.actors[e[1]] for e in server.log if e[0] == "spawn" and e[2].startswith(type_prefix)
            and e[1] in server.actors]


# ----------------------------------------------------------------------------------------------- SC-DRIVING-014


def test_sc014_starts_at_the_sites_start_with_its_props_and_target_at_the_sites_poses(tmp_path, server, factory,
                                                                                      clock, spy, monkeypatch):
    destroyed: list = []
    monkeypatch.setattr(carla.Actor, "destroy", lambda self: destroyed.append(self.id) or True)   # keep the states
    rc, lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-014@30", "--run-s", "2")
    assert rc == 0, lines
    # the call: the setting's own rule, the server's static.prop list
    assert len(spy) == 1
    call = spy[0]
    spec = _expected(server, "SC-DRIVING-014@30")
    assert (call["site"], call["setting"]) == ("sc014-curve", "SC-DRIVING-014@30")
    assert (call["approach_rule"], call["approach_min_m"], call["lane_rule"]) == ("gentle-bend", 90.0, "outermost")
    assert sorted(call["props_available"]) == sorted(carla.REAL_STATIC_PROPS)
    rec = json.loads((sim / "setting_record.json").read_text())
    # the contract with the evaluator lane: the whole site record, guidance included
    assert rec["site"] == json.loads(json.dumps(spec.as_record()))
    assert rec["site"]["guidance"]["regulation"]["ttcAtTurnInMaxS"] == 1.6
    assert rec["site"]["benchReadings"]["siteSelection"]["lane"] == "outermost"
    assert rec["start"]["start"] == spec.start and rec["start"]["start"].startswith("54:6:")
    # the hero at the start pose (lifted 0.3 m for the spawn)
    hero = next(s for s in _spawned(server, "vehicle.") if s.attributes.get("role_name") == "hero")
    hero_spawn = next(json.loads(x) for x in lines if '"event":"hero"' in x)["spawn"]
    sp = spec.start_pose
    assert (hero_spawn["x"], hero_spawn["y"], hero_spawn["yaw"]) == pytest.approx((sp["x"], sp["y"], sp["yaw"]))
    assert hero_spawn["z"] == pytest.approx(sp["z"] + 0.3)
    assert hero.type_id == "vehicle.lincoln.mkz"
    # every prop at its pose, physics off
    props = [s for s in _spawned(server, "static.prop.")]
    assert len(props) == len(spec.props) > 10
    for state, want in zip(props, spec.props):
        assert state.type_id == want["blueprint"] == "static.prop.streetbarrier"
        t = state.transform
        assert (t.location.x, t.location.y, t.rotation.yaw) == pytest.approx((want["x"], want["y"], want["yaw"]))
        assert state.simulate_physics is False
    assert len(rec["start"]["props"]) == len(spec.props)
    # the target at the site's pose, standing on its hand brake for the whole run
    target = next(s for s in _spawned(server, "vehicle.tesla.model3"))
    tw = spec.target
    ticks = _ticks(sim)
    assert ticks and all((t["target"]["x"], t["target"]["y"]) == pytest.approx((tw["x"], tw["y"])) for t in ticks)
    assert target.transform.rotation.yaw == pytest.approx(tw["yaw"])
    assert target.control.hand_brake is True
    assert rec["target"]["site"] == "sc014-curve" and rec["target"]["speedKmh"] == 0.0


def test_a_site_the_map_refuses_is_a_bench_error_naming_the_reason(tmp_path, server, factory, clock):
    server.blueprints = carla.BlueprintLibrary([b for b in server.blueprints
                                                if "barrier" not in b.id])          # no guard-pipe-like prop
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-014@30", "--run-s", "1")
    assert rc == 2
    reason = json.loads((sim / "error.json").read_text())["reason"]
    assert reason.startswith("site sc014-curve: ") and "no guard-pipe-like prop" in reason
    assert not [s for s in server.actors.values() if s.alive and s.type_id.startswith("vehicle.")]


# ----------------------------------------------------------------------------------------------- SC-DRIVING-015


def test_sc015_target_follows_its_script_along_its_path_on_every_tick(tmp_path, server, factory, clock, spy):
    rc, lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-015@40", "--run-s", "26")
    assert rc == 0, lines
    assert len(spy) == 1 and spy[0]["approach_rule"] == "straight"
    spec = _expected(server, "SC-DRIVING-015@40")
    motion = spec.target_motion()
    ticks = _ticks(sim)
    tid = next(e[1] for e in server.log if e[0] == "spawn" and e[2] == "vehicle.tesla.model3")
    calls = [c for c in server.control_log if c["actor"] == tid]
    assert not [c for c in calls if c["call"] == "enable_constant_velocity"]
    assert len([c for c in calls if c["call"] == "set_transform"]) >= len(ticks)
    phases = set()
    for t in ticks:
        # the pose after each tick: the script at the tick's time plus one step (the motion starts with the go)
        want = motion.at(t["scenarioTimeS"] + STEP_S)
        assert (t["target"]["x"], t["target"]["y"]) == pytest.approx((want["x"], want["y"]), abs=1e-6)
        assert ((t["target"]["yawDegCarla"] - want["yaw"] + 180.0) % 360.0) - 180.0 == pytest.approx(0.0, abs=1e-6)
        assert t["target"]["speedMps"] == pytest.approx(want["speedMps"], abs=1e-9)
        assert t["target"]["motionPhase"] == want["phase"]
        phases.add(want["phase"])
    assert phases == {"accelerate", "hold", "brake", "turn"}
    # 1.5 m/s2 up, 40 km/h held at least 4 s, braked to 10 km/h, then on connector 863
    acc, hold, brake, turn = spec.target_script
    assert acc["accelMps2"] == 1.5 and hold["fromMps"] == pytest.approx(40 / 3.6) and hold["durationS"] >= 4.0
    assert turn["fromMps"] == pytest.approx(10 / 3.6) and turn["connector"] == "863"
    held = [t for t in ticks if t["target"]["motionPhase"] == "hold"]
    assert held[-1]["scenarioTimeS"] - held[0]["scenarioTimeS"] >= 4.0 - STEP_S
    assert all(t["target"]["speedMps"] == pytest.approx(40 / 3.6) for t in held)
    xodr = sites.Xodr(carla.Client("127.0.0.1", 2000, _server=server, name="x").get_world().get_map().to_opendrive())
    connector = [sites.carla_pose(p[0], p[1], p[2]) for p in xodr.sample_piece(("863", 0, -1), 0.25)]
    turning = [t for t in ticks if t["target"]["motionPhase"] == "turn"]
    assert turning and all(t["target"]["speedMps"] == pytest.approx(10 / 3.6) for t in turning)
    late = [t for t in turning if t["scenarioTimeS"] >= turning[0]["scenarioTimeS"] + 2.0]
    assert late and all(min(math.hypot(t["target"]["x"] - c["x"], t["target"]["y"] - c["y"]) for c in connector) < 0.2
                        for t in late[:20])
    rec = json.loads((sim / "setting_record.json").read_text())
    assert rec["site"]["siteId"] == "sc015-turnoff" and rec["site"]["targetScript"] == spec.target_script
    assert rec["target"]["motion"] == "kinematic set_transform" and rec["target"]["script"] is True
    # the target starts 30 m ahead of the hero, at the script's first pose
    t0 = motion.at(0.0)
    sp = spec.start_pose
    assert math.hypot(t0["x"] - sp["x"], t0["y"] - sp["y"]) == pytest.approx(30.0, abs=0.5)


# ----------------------------------------------------------------------------------------------- SC-DRIVING-013


def test_sc013_keeps_constant_velocity_and_has_no_site(tmp_path, server, factory, clock, spy):
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-013@30", "--run-s", "2")
    assert rc == 0
    assert spy == []
    tid = next(e[1] for e in server.log if e[0] == "spawn" and e[2] == "vehicle.tesla.model3")
    calls = [c["call"] for c in server.control_log if c["actor"] == tid]
    assert calls.count("enable_constant_velocity") == 1 and "set_transform" not in calls
    rec = json.loads((sim / "setting_record.json").read_text())
    assert rec["site"] is None and rec["target"]["motion"] == "enable_constant_velocity"
