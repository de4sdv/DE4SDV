"""A run of SC-DRIVING-012 on the fake CARLA: spawn, rig, target, the entry checks passing and failing, no
control of the hero by the world side, the setting record, pacing and teardown."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from conftest import AdapterStandIn, run_main

import da_world_side as ws_mod
import scenarios


def _run(tmp_path, factory, clock, *extra):
    run_dir = tmp_path / "run"
    rc, lines = run_main(["run", "--run-dir", str(run_dir), "--setting", "SC-DRIVING-012@20", *extra],
                         factory, clock)
    return rc, lines, run_dir / "simulator"


def _ticks(sim: Path) -> list[dict]:
    return [json.loads(line)["data"] for line in (sim / "world.jsonl").read_text().splitlines()]


def test_a_run_at_21_kmh_meets_the_entry_conditions(tmp_path, server, factory, clock):
    adapter = AdapterStandIn(server, target_kmh=21.0)
    rc, _lines, sim = _run(tmp_path, factory, clock)
    assert rc == 0
    entry = json.loads((sim / "entry_checks.json").read_text())
    assert entry["functionalPart"]["met"] is True
    assert entry["straightBefore"]["met"] is True
    assert entry["judgedRun"] is True
    assert entry["functionalPart"]["endReason"] == "contact with the target"
    assert entry["functionalPart"]["startTtcS"] >= 4.0
    assert 20.0 <= entry["functionalPart"]["startSpeedKmh"] <= 22.0
    assert adapter.applied > 0


def test_the_world_side_never_controls_the_hero(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=21.0)
    _run(tmp_path, factory, clock)
    hero_ids = {e[1] for e in server.log if e[0] == "spawn" and e[2] == "vehicle.lincoln.mkz"}
    world_side_on_hero = [c for c in server.control_log if c["client"] == "world_side" and c["actor"] in hero_ids]
    assert world_side_on_hero == []
    adapter_calls = [c for c in server.control_log if c["client"] == "adapter"]
    assert adapter_calls and all(c["call"] == "apply_ackermann_control" for c in adapter_calls)
    assert not [e for e in server.log if e[0] == "traffic_manager"]
    ticks = _ticks(tmp_path / "run" / "simulator")
    assert all(t["worldSideControlCalls"] == 0 for t in ticks)


def test_too_slow_misses_the_functional_part(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=15.0)
    rc, _lines, sim = _run(tmp_path, factory, clock)
    assert rc == 0
    entry = json.loads((sim / "entry_checks.json").read_text())
    assert entry["functionalPart"]["met"] is False
    assert entry["functionalPart"]["maxSpeedKmh"] < 20.0
    assert entry["judgedRun"] is False


def test_too_fast_has_a_functional_part_from_the_pass_through_the_band(tmp_path, server, factory, clock):
    # The term as written: "from the latest instant at which the vehicle travels at its approach speed within
    # the tolerance with a time to collision of at least 4 s". A hero that accelerates through 20-22 km/h far
    # from the target and holds 24 km/h has such an instant during its acceleration. The checks follow the
    # term and report the start; whether such a run is judged is a question for the lead (README).
    AdapterStandIn(server, target_kmh=24.0)
    _rc, _lines, sim = _run(tmp_path, factory, clock)
    entry = json.loads((sim / "entry_checks.json").read_text())
    assert entry["functionalPart"]["met"] is True
    assert entry["functionalPart"]["startTtcS"] > 15.0
    ticks = _ticks(sim)
    after = [t for t in ticks if t["scenarioTimeS"] > entry["functionalPart"]["startS"] + 1.0]
    assert max(t["ego"]["speedMps"] for t in after) * 3.6 > 22.0


def test_a_drift_off_the_center_line_misses_the_judged_run(tmp_path, server, factory, clock):
    # A small constant right steer: the hero leaves the target's center line before the functional part.
    AdapterStandIn(server, target_kmh=21.0, steer_rad=0.002)
    _rc, _lines, sim = _run(tmp_path, factory, clock)
    entry = json.loads((sim / "entry_checks.json").read_text())
    assert entry["straightBefore"]["met"] is False
    assert any("center line" in m for m in entry["straightBefore"]["missed"])
    assert entry["judgedRun"] is False


def test_a_target_too_close_leaves_no_time_to_collision_of_four_seconds(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=21.0)
    _rc, _lines, sim = _run(tmp_path, factory, clock, "--target-ahead-m", "18")
    entry = json.loads((sim / "entry_checks.json").read_text())
    assert entry["functionalPart"]["met"] is False


def test_setting_record_states_the_model_values_and_the_proposals(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=21.0)
    _run(tmp_path, factory, clock)
    rec = json.loads((tmp_path / "run" / "simulator" / "setting_record.json").read_text())
    st = rec["setting"]
    assert (st["approach_kmh"], st["low_kmh"], st["high_kmh"]) == (20.0, 20.0, 22.0)
    assert set(st["model"]) >= {"approach_kmh", "low_kmh", "high_kmh"}
    assert set(st["proposal"]) == {"target_ahead_m", "run_cap_s", "speed_limit_mps", "site"}
    assert st["site"] is None
    assert rec["simulator"]["stepS"] == 0.05 and rec["simulator"]["synchronous"] is True
    assert rec["hero"]["type_id"] == "vehicle.lincoln.mkz" and rec["hero"]["role"] == "hero"
    cam = rec["frontCamera"]
    assert (cam["image_size_x"], cam["image_size_y"], cam["fov"], cam["sensor_tick"]) == ("1920", "1280", "50.0",
                                                                                          "0.1")
    assert cam["role"] == "front"
    assert cam["pose"] == {"x": 1.544, "y": 0.0243, "z": 2.116, "roll": -0.10, "pitch": -0.11, "yaw": -0.23}
    assert rec["target"]["aheadM"] == 150.0 and rec["target"]["speedKmh"] == 0.0
    assert rec["start"]["sameDirectionLanes"] >= 2
    assert math.isclose(rec["candidateSpeedLimitMps"], 21.0 / 3.6, abs_tol=1e-3)


def test_target_stands_on_the_hero_lane_center(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=21.0)
    _run(tmp_path, factory, clock)
    first = _ticks(tmp_path / "run" / "simulator")[0]
    assert first["target"]["y"] == pytest.approx(first["ego"]["y"], abs=1e-9)
    # gap = center distance - mkz front 2.45 - model3 rear 2.40 (the fake's extents, box centered on x 0)
    assert first["relative"]["gapM"] == pytest.approx(first["target"]["x"] - first["ego"]["x"] - 2.45 - 2.40,
                                                      abs=1e-9)
    rec = json.loads((tmp_path / "run" / "simulator" / "setting_record.json").read_text())
    # the fake's lane runs along x with s = x: the target stands 150 m along the lane from the start
    assert first["target"]["x"] == pytest.approx(rec["start"]["s"] + 150.0, abs=1e-9)
    assert rec["target"]["s"] == pytest.approx(rec["start"]["s"] + 150.0, abs=1e-9)
    assert first["relative"]["centerLineOffsetM"] == pytest.approx(0.0, abs=1e-9)


def test_settings_applied_then_restored_and_every_actor_destroyed(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=21.0)
    _run(tmp_path, factory, clock)
    settings = [e for e in server.log if e[0] == "settings"]
    assert settings[0][1:] == (True, 0.05)
    assert settings[-1][1:] == (False, None)
    spawned = {e[1] for e in server.log if e[0] == "spawn"}
    destroyed = {e[1] for e in server.log if e[0] == "destroy"}
    assert spawned == destroyed and not server.actors


def test_ticks_are_paced_at_the_step_and_a_stall_is_listed(tmp_path, server, factory, clock):
    AdapterStandIn(server, target_kmh=21.0)
    state = {"n": 0}

    def slow(srv):
        state["n"] += 1
        if state["n"] == 300:
            clock.advance(0.5)         # one tick takes 0.5 s of wall time: the next starts 0.5 s later
    server.pre_tick_hooks.append(slow)
    _run(tmp_path, factory, clock)
    summary = json.loads((tmp_path / "run" / "simulator" / "summary.json").read_text())
    stalls = summary["pacing"]["stalls"]
    assert len(stalls) == 1 and stalls[0]["gapS"] == pytest.approx(0.5, abs=1e-6)
    # every wait the pacer slept is at most one step
    assert max(clock.sleeps) <= 0.05 + 1e-9


def test_the_run_ends_at_the_cap_without_a_candidate(tmp_path, server, factory, clock):
    _rc, _lines, sim = _run(tmp_path, factory, clock, "--run-s", "5")
    summary = json.loads((sim / "summary.json").read_text())
    assert summary["endReason"] == "run cap"
    assert summary["ticks"] == 101           # 0.0 .. 5.0 s of scenario time at 0.05 s
    entry = json.loads((sim / "entry_checks.json").read_text())
    assert entry["judgedRun"] is False


def test_ready_file_names_the_roles_the_candidate_and_adapter_attach_to(tmp_path, server, factory, clock):
    _run(tmp_path, factory, clock, "--run-s", "1")
    ready = json.loads((tmp_path / "run" / "simulator" / "ready.json").read_text())
    assert ready["hero_role"] == "hero" and ready["camera_role"] == "front"


def test_a_missing_vehicle_is_a_bench_error(tmp_path, server, factory, clock):
    server.blueprints = type(server.blueprints)([b for b in server.blueprints if b.id != "vehicle.lincoln.mkz"])
    rc, lines, sim = _run(tmp_path, factory, clock, "--run-s", "1")
    assert rc == 2
    assert "none of the vehicles" in json.loads((sim / "error.json").read_text())["reason"]
    assert not server.actors


def test_a_start_on_a_short_straight_is_refused(tmp_path, server, factory, clock):
    server.map.bend_from = 300.0
    rc, _lines, sim = _run(tmp_path, factory, clock, "--start", "35:-1:200")
    assert rc == 2
    assert "straight for" in json.loads((sim / "error.json").read_text())["reason"]


def test_the_survey_skips_bends_and_junctions(tmp_path, server, factory, clock):
    server.map.length = 600.0
    server.map.junction_from, server.map.junction_to = 250.0, 270.0
    rc, _lines = run_main(["survey", "--run-dir", str(tmp_path / "s"), "--limit", "0"], factory, clock)
    assert rc == 0
    found = json.loads((tmp_path / "s" / "simulator" / "survey.json").read_text())["candidates"]
    assert found
    for c in found:          # a stretch of 190 m that crosses neither the junction nor the map's end
        assert c["s"] + 190.0 < 250.0 or c["s"] > 270.0
        assert c["s"] + 190.0 <= 600.0


def test_dry_run_creates_no_client(tmp_path, capsys):
    rc = ws_mod.main(["run", "--run-dir", str(tmp_path / "d"), "--dry-run"],
                     client_factory=lambda *a: pytest.fail("no client in a dry run"))
    assert rc == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["stepS"] == 0.05 and plan["frontCamera"]["sensor_tick"] == 0.1


def test_every_setting_of_sc012_is_runnable_on_the_fake(tmp_path, server, factory, clock):
    for sid, kmh in (("SC-DRIVING-012@42", 41.0), ("SC-DRIVING-012@60", 59.0)):
        srv_hooks = list(server.pre_tick_hooks)
        server.pre_tick_hooks.clear()
        AdapterStandIn(server, target_kmh=kmh)
        run_dir = tmp_path / sid
        rc, _ = run_main(["run", "--run-dir", str(run_dir), "--setting", sid], factory, clock)
        assert rc == 0
        entry = json.loads((run_dir / "simulator" / "entry_checks.json").read_text())
        assert entry["judgedRun"] is True, (sid, entry)
        server.pre_tick_hooks[:] = srv_hooks
        assert scenarios.setting(sid).in_tolerance(kmh / 3.6)


def test_the_source_has_no_autopilot_and_no_traffic_manager_and_one_control_site():
    src = (Path(ws_mod.__file__)).read_text()
    assert "set_autopilot" not in src and "get_trafficmanager" not in src
    # the only Ackermann control is the ASM-DRIVING-005 calibration's own command
    body = src.split("def _decel_pass", 1)
    assert src.count("apply_ackermann_control(") == 1 and "apply_ackermann_control(" in body[1].split("\ndef ")[0]
