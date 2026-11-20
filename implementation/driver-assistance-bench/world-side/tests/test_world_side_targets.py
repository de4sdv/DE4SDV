"""S1 targets on the fake CARLA: the SC-DRIVING-013 target at a constant 20 km/h by either of CARLA's means (A3),
its end at the target's speed (A2), the per-tick ``vehiclesAhead`` of the shared contract (A6), and the site
settings built through ``sites.resolve`` (stubbed here: lane A2 owns ``world-side/sites.py``)."""

from __future__ import annotations

import json
import math
import sys
import types
from pathlib import Path

import pytest

import carla  # the fake
from conftest import AdapterStandIn, run_main

import da_world_side as ws_mod

TICK_M = 20.0 / 3.6 * 0.05            # 0.2778 m: 20 km/h for one step of 0.05 s
TARGET_MPS = 20.0 / 3.6               # 5.556 m/s
CONTRACT_FIELDS = {"actorId", "role", "gapM", "closingMps", "ttcS", "neededDecelMps2", "inLane", "overlapRatio"}


def _ticks(sim: Path) -> list[dict]:
    return [json.loads(line)["data"] for line in (sim / "world.jsonl").read_text().splitlines()]


def _run(tmp_path, factory, clock, setting, *extra, name="run"):
    run_dir = tmp_path / name
    rc, lines = run_main(["run", "--run-dir", str(run_dir), "--setting", setting, *extra], factory, clock)
    return rc, lines, run_dir / "simulator"


def _target_id(server) -> int:
    return next(e[1] for e in server.log if e[0] == "spawn" and e[2] == "vehicle.tesla.model3")


# ------------------------------------------------------------------ A3: the moving target at 20 km/h


def _assert_constant_20_kmh(ticks):
    xs = [t["target"]["x"] for t in ticks]
    steps = [b - a for a, b in zip(xs, xs[1:])]
    assert len(steps) > 50
    for step in steps:
        assert step == pytest.approx(TICK_M, rel=0.01)
    for t in ticks:
        assert t["target"]["speedMps"] == pytest.approx(TARGET_MPS, rel=0.001)
        assert round(t["target"]["speedMps"], 3) == 5.556


def test_the_013_target_moves_at_20_kmh_by_constant_velocity_where_carla_has_it(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=31.0)
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-013@30", "--run-s", "10")
    assert rc == 0
    ticks = _ticks(sim)
    _assert_constant_20_kmh(ticks)
    tid = _target_id(server)
    calls = [c for c in server.control_log if c["actor"] == tid]
    assert [c["call"] for c in calls if c["call"] == "enable_constant_velocity"] == ["enable_constant_velocity"]
    assert not [c for c in calls if c["call"] == "set_transform"]
    enabled = next(c for c in calls if c["call"] == "enable_constant_velocity")
    assert enabled["value"] == pytest.approx((TARGET_MPS, 0.0))           # local frame: forward only
    rec = json.loads((sim / "setting_record.json").read_text())
    assert rec["target"]["motion"] == "enable_constant_velocity"
    assert rec["target"]["speedKmh"] == 20.0
    # it moves from the run's first tick on, not during the set-up ticks before the go
    assert ticks[0]["target"]["x"] - (rec["start"]["s"] + 40.0) == pytest.approx(TICK_M, rel=0.01)


def test_the_013_target_moves_kinematically_where_carla_lacks_constant_velocity(tmp_path, server, factory, clock,
                                                                                monkeypatch):
    monkeypatch.delattr(carla.Actor, "enable_constant_velocity")
    AdapterStandIn(server, target_kmh=31.0)
    physics: list = []

    def watch(srv):                          # a posed target has its physics off while it moves
        for st in srv.actors.values():
            if st.type_id == "vehicle.tesla.model3":
                physics.append(st.simulate_physics)
    server.pre_tick_hooks.append(watch)
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-013@30", "--run-s", "10")
    assert rc == 0
    assert physics[0] is True and physics[-1] is False
    ticks = _ticks(sim)
    _assert_constant_20_kmh(ticks)
    tid = _target_id(server)
    moves = [c for c in server.control_log if c["actor"] == tid and c["call"] == "set_transform"]
    assert len(moves) >= len(ticks)                                     # one pose per tick of the run
    rec = json.loads((sim / "setting_record.json").read_text())
    assert rec["target"]["motion"] == "kinematic set_transform"
    assert ticks[0]["target"]["x"] - (rec["start"]["s"] + 40.0) == pytest.approx(TICK_M, rel=0.01)
    # the recorded closing speed uses the target's own 5.556 m/s, not CARLA's zero velocity of a posed actor
    for t in ticks:
        assert t["relative"]["closingMps"] == pytest.approx(t["ego"]["speedMps"] - TARGET_MPS, abs=1e-6)


def test_the_012_target_still_stands_on_its_hand_brake(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=21.0)
    _rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-012@20", "--run-s", "5")
    ticks = _ticks(sim)
    assert {t["target"]["x"] for t in ticks} == {ticks[0]["target"]["x"]}
    tid = _target_id(server)
    assert {c["call"] for c in server.control_log if c["actor"] == tid} == {"apply_control"}


# ------------------------------------------------------------------ A2 on the fake: the end at the target's speed


def test_a_013_run_ends_when_the_vehicle_holds_the_target_speed(tmp_path, server, factory, clock):
    # the stand-in candidate closes at 31 km/h and, 12 m behind the target, slows to 20 km/h and follows
    adapter = AdapterStandIn(server, target_kmh=31.0)
    state = {"follow": False}

    def follow(srv):
        hero = adapter.hero
        if hero is None:
            return
        tgt = [s for s in srv.actors.values() if s.type_id == "vehicle.tesla.model3"][0]
        gap = tgt.transform.location.x - hero.get_location().x - 4.85
        if gap < 12.0:
            state["follow"] = True
        if state["follow"]:
            adapter.target = TARGET_MPS
    server.pre_tick_hooks.insert(0, follow)
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-013@30")
    assert rc == 0
    summary = json.loads((sim / "summary.json").read_text())
    assert summary["endReason"] == "at the speed of the target"
    entry = summary["entry"]
    assert entry["functionalPart"]["met"] is True
    assert entry["functionalPart"]["endReason"] == "at the speed of the target"
    ticks = _ticks(sim)
    assert ticks[-1]["scenarioTimeS"] < 60.0 - 1.0                      # not the cap
    matched = next(t for t in ticks if t["scenarioTimeS"] > 5.0 and t["relative"]["closingMps"] <= 0.0)
    assert ticks[-1]["scenarioTimeS"] - matched["scenarioTimeS"] >= ws_mod.REST_HOLD_S - 0.05 - 1e-9
    assert not any(t["targetContact"] for t in ticks)


# ------------------------------------------------------------------ A6: vehiclesAhead


def test_vehicles_ahead_holds_the_contract_fields_for_every_vehicle_up_to_300_m(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=31.0)
    others = carla.Client("127.0.0.1", 2000, _server=server, name="traffic")
    placed: dict = {}

    def place(srv):                    # before the first tick of the world side's run: three more vehicles
        if placed or not any(s.type_id == "vehicle.tesla.model3" for s in srv.actors.values()):
            return
        world = others.get_world()
        bp = world.get_blueprint_library().find("vehicle.lincoln.mkz")
        hero = [s for s in srv.actors.values() if s.attributes.get("role_name") == "hero"][0]
        x0, y0 = hero.transform.location.x, hero.transform.location.y
        other_lane = 0.0 if y0 > 1.75 else 3.5             # the fake's two lanes: y 0 and y 3.5
        for name, dx, y in (("next_lane", 60.0, other_lane), ("far", 320.0, y0), ("behind", -30.0, y0),
                            ("ahead_250", 250.0, y0)):
            bp.set_attribute("role_name", name)
            placed[name] = world.spawn_actor(bp, carla.Transform(carla.Location(x0 + dx, y, 0.0))).id
    server.pre_tick_hooks.insert(0, place)
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-013@30", "--run-s", "3")
    assert rc == 0
    ticks = _ticks(sim)
    tid = _target_id(server)
    for t in ticks:
        ahead = {v["actorId"]: v for v in t["vehiclesAhead"]}
        for v in ahead.values():
            assert set(v) == CONTRACT_FIELDS
        assert set(ahead) == {tid, placed["next_lane"], placed["ahead_250"]}
        target = ahead[tid]
        assert target["role"] == ws_mod.TARGET_ROLE and target["inLane"] is True
        assert target["overlapRatio"] == pytest.approx(1.0)
        for key in ("gapM", "closingMps", "ttcS", "neededDecelMps2"):        # the primary target: as relative
            if t["relative"][key] is None:
                assert target[key] is None
            else:
                assert target[key] == pytest.approx(t["relative"][key], abs=1e-9)
        side = ahead[placed["next_lane"]]
        assert side["role"] == "next_lane" and side["inLane"] is False and side["overlapRatio"] == 0.0
        far = ahead[placed["ahead_250"]]
        assert far["inLane"] is True and 0.0 < far["gapM"] <= 300.0


class _SiteSpec:
    """The fields this world side reads from ``sites.resolve`` (lane A2's SiteSpec)."""

    def __init__(self, start_transform, target_spawn, target_path=(), target_speed_mps=None, props=(),
                 record=None):
        self.start_transform = start_transform
        self.target_spawn = target_spawn
        self.target_path = list(target_path)
        self.target_speed_mps = target_speed_mps
        self.props = list(props)
        self.record = record or {}


@pytest.fixture
def stub_sites(monkeypatch):
    calls: list = []
    specs: dict = {}

    def resolve(world_map, site_id, setting):
        calls.append((site_id, setting.setting_id))
        return specs[site_id](world_map)
    module = types.SimpleNamespace(resolve=resolve)
    monkeypatch.setattr(ws_mod, "sites", module)
    return calls, specs


def _pose(x, y, yaw=0.0):
    return carla.Transform(carla.Location(x, y, 0.0), carla.Rotation(yaw=yaw))


def test_the_014_target_beyond_the_curve_is_never_in_the_lane(tmp_path, server, factory, clock, stub_sites):
    # SC-DRIVING-014 (operational_context.sysml:271-298): the stationary vehicle stands on the extension of the
    # lane's centre, just off the road: ahead of the vehicle, never in its path. The fake's road ends at 200 m;
    # the target stands 12 m beyond the end, on the lane centre's extension.
    server.map.length = 200.0
    calls, specs = stub_sites
    specs["sc014-curve"] = lambda m: _SiteSpec(_pose(20.0, 0.0), _pose(212.0 + 2.4, 0.0))
    AdapterStandIn(server, target_kmh=29.0)
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-014@30", "--run-s", "15")
    assert rc == 0, _lines
    assert calls == [("sc014-curve", "SC-DRIVING-014@30")]
    ticks = _ticks(sim)
    tid = _target_id(server)
    seen = [next(v for v in t["vehiclesAhead"] if v["actorId"] == tid) for t in ticks]
    assert len(seen) == len(ticks)
    assert all(v["inLane"] is False for v in seen)
    assert all(v["overlapRatio"] == pytest.approx(1.0) for v in seen)       # straight ahead all the same
    rec = json.loads((sim / "setting_record.json").read_text())
    assert rec["start"]["site"] == "sc014-curve"
    summary = json.loads((sim / "summary.json").read_text())
    assert summary["entry"]["judgedRun"] is False and "no judged-run term" in summary["entry"]["notJudged"]


def _turn_off_path(x_turn=150.0, radius=11.0, step=0.5):
    """Straight along lane -1 (y 0) to x_turn, then a right quarter circle of the radius (CARLA: right is +y)."""
    path = [_pose(x, 0.0) for x in [i * step for i in range(int(x_turn / step) + 1)]]
    for k in range(1, 46):
        phi = math.radians(2.0 * k)
        path.append(_pose(x_turn + radius * math.sin(phi), radius * (1.0 - math.cos(phi)), math.degrees(phi)))
    return path


def test_the_015_target_is_in_the_lane_until_its_turn(tmp_path, server, factory, clock, stub_sites):
    # SC-DRIVING-015 (operational_context.sysml:300-323): the vehicle ahead slows down and turns off at a corner,
    # the vehicle goes straight on. Here: 40 km/h for 4 s, then 10 km/h, a right turn of 11 m radius at x 150.
    calls, specs = stub_sites
    path = _turn_off_path()

    def profile(t):
        return 40.0 / 3.6 if t < 4.0 else 10.0 / 3.6
    specs["sc015-turnoff"] = lambda m: _SiteSpec(_pose(20.0, 0.0), _pose(50.0, 0.0),
                                                 [p for p in path if p.location.x >= 50.0 or p.location.y > 0],
                                                 target_speed_mps=profile)
    adapter = AdapterStandIn(server, target_kmh=41.0)

    def follow(srv):                    # closes at 41 km/h, then 25 m behind holds the vehicle ahead's 10 km/h
        hero = adapter.hero
        tgt = [st for st in srv.actors.values() if st.type_id == "vehicle.tesla.model3"]
        if hero is not None and tgt and tgt[0].transform.location.x - hero.get_location().x < 25.0:
            adapter.target = 10.0 / 3.6
    server.pre_tick_hooks.insert(0, follow)
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-015@40", "--run-s", "40")
    assert rc == 0, _lines
    assert calls == [("sc015-turnoff", "SC-DRIVING-015@40")]
    ticks = _ticks(sim)
    # SC-DRIVING-015 follows its vehicle ahead at its speed: coming to that speed ends nothing
    summary = json.loads((sim / "summary.json").read_text())
    assert summary["endReason"] == "run cap"
    assert any(t["relative"]["closingMps"] > 1.0 for t in ticks)
    assert any(t["relative"]["closingMps"] <= 0.0 for t in ticks if t["scenarioTimeS"] > 8.0)
    tid = _target_id(server)
    states = []
    for t in ticks:
        v = next((v for v in t["vehiclesAhead"] if v["actorId"] == tid), None)
        if v is not None:
            states.append((t["target"]["x"], t["target"]["y"], v["inLane"]))
    assert states[0][2] is True
    first_out = next(i for i, s in enumerate(states) if s[2] is False)
    assert all(s[2] is True for s in states[:first_out])
    assert all(s[2] is False for s in states[first_out:])                  # in the lane until its turn
    assert states[first_out][0] > 150.0 and states[first_out - 1][1] < 3.5   # it left the lane in the turn
    assert not any(t["targetContact"] for t in ticks)
    rec = json.loads((sim / "setting_record.json").read_text())
    assert rec["target"]["motion"] == "kinematic set_transform"
    assert rec["target"]["speedKmh"] == 40.0


def test_a_site_setting_without_sites_module_is_a_bench_error(tmp_path, server, factory, clock, monkeypatch):
    monkeypatch.setattr(ws_mod, "sites", None)
    rc, _lines, sim = _run(tmp_path, factory, clock, "SC-DRIVING-014@30", "--run-s", "1")
    assert rc == 2
    assert "sites" in json.loads((sim / "error.json").read_text())["reason"]
    assert not server.actors


def test_straight_settings_never_call_sites(tmp_path, server, factory, clock, stub_sites):
    calls, _specs = stub_sites
    for sid in ("SC-DRIVING-012@20", "SC-DRIVING-013@60", "stop"):
        rc, _lines, _sim = _run(tmp_path, factory, clock, sid, "--run-s", "1", name=sid.replace("@", "_"))
        assert rc == 0
    assert calls == []
