"""ASM-DRIVING-005 and -006: the analyses on synthetic profiles computed here in closed form, the record formats,
and both calibration subcommands on the fake CARLA."""

from __future__ import annotations

import json
import math

import pytest

import calibration
from conftest import AdapterStandIn, run_main


def _brake_profile(v0, d, jerk=10.0, dt=0.05, scale=1.0):
    """Hold v0 for 1 s, then decelerate with the jerk ramp to scale * d until rest (closed form per sample)."""
    out, t, v, a = [], 0.0, v0, 0.0
    while t < 1.0:
        out.append({"t": round(t, 6), "speed": v, "accel": 0.0, "commanded": 0.0, "phase": "hold"})
        t += dt
    t_on = t
    while v > 0.0:
        a = min(scale * d, jerk * (t - t_on))
        out.append({"t": round(t, 6), "speed": v, "accel": -a, "commanded": -d, "phase": "brake"})
        v = max(0.0, v - a * dt)
        t += dt
    out.append({"t": round(t, 6), "speed": 0.0, "accel": 0.0, "commanded": -d, "phase": "brake"})
    return out


@pytest.mark.parametrize("d", [1.0, 3.0, 5.0])
def test_decel_follows_when_the_vehicle_reaches_the_command(d):
    res = calibration.analyse_decel({"approachKmh": 60.0, "commandedDecelMps2": d,
                                     "samples": _brake_profile(60 / 3.6, d)})
    assert res["achievedDecelMps2"] == pytest.approx(d, rel=1e-6)
    assert res["achievedOverCommanded"] == pytest.approx(1.0, rel=1e-6)
    assert res["followsWithinProposal"] is True
    assert res["rampAtJerkS"] == pytest.approx(d / 10.0)
    assert res["timeTo90PercentS"] <= d / 10.0 + 0.15


def test_decel_short_of_the_command_is_reported():
    res = calibration.analyse_decel({"approachKmh": 60.0, "commandedDecelMps2": 5.0,
                                     "samples": _brake_profile(60 / 3.6, 5.0, scale=0.8)})
    assert res["achievedDecelMps2"] == pytest.approx(4.0, rel=1e-6)
    assert res["followsWithinProposal"] is False


def test_decel_record_format():
    passes = [calibration.analyse_decel({"approachKmh": 20.0, "commandedDecelMps2": 5.0,
                                         "samples": _brake_profile(20 / 3.6, 5.0)})]
    rec = calibration.decel_record(passes, {"setting": "SC-DRIVING-012@20"})
    assert rec["assumption"] == "ASM-DRIVING-005" and rec["notARunOfASetting"] is True
    assert rec["recordVersion"] == 1
    assert set(rec["proposal"]) >= {"followTolerance", "fitWindow"}
    assert rec["summary"] == {"passes": 1, "analysed": 1, "allFollowWithinProposal": True,
                              "worstRatio": pytest.approx(1.0)}
    json.dumps(rec, allow_nan=False)


def _steer_ticks(yaw_rate_deg_s, offset0=0.5, v=5.0):
    out = []
    for k in range(200):
        t = k * 0.05
        speed = min(v, 1.0 * t)
        out.append({"scenarioTimeS": t, "ego": {"speedMps": speed, "yawDegCarla": 90.0 + yaw_rate_deg_s * t,
                                                "lane": {"offsetM": offset0 - 0.01 * t}},
                    "control": {"steer": -0.01 if yaw_rate_deg_s < 0 else 0.01}})
    return out


def test_steering_left_from_the_right_shows_the_assumption():
    res = calibration.analyse_steering(_steer_ticks(-2.0), 0.5)
    assert res["turn"] == "left" and res["shown"] is True
    assert res["yawRateDegSCarla"] == pytest.approx(-2.0)
    assert res["windowS"][0] == pytest.approx(2.0)          # speed 1 m/s2 * t reaches 2 m/s at 2 s


def test_steering_right_from_the_right_does_not_show_it():
    res = calibration.analyse_steering(_steer_ticks(+2.0), 0.5)
    assert res["turn"] == "right" and res["shown"] is False


def test_steering_with_no_turn_is_missed_not_shown():
    res = calibration.analyse_steering(_steer_ticks(0.0), 0.5)
    assert res["shown"] is None and "no turn" in res["missed"]


def test_steering_never_moving():
    res = calibration.analyse_steering(_steer_ticks(-2.0, v=1.0), 0.5)
    assert res["shown"] is None


def test_yaw_unwrapping_across_180():
    ticks = _steer_ticks(-2.0)
    for t in ticks:
        t["ego"]["yawDegCarla"] = ((t["ego"]["yawDegCarla"] + 87.0 + 180.0) % 360.0) - 180.0 + 0.0
    res = calibration.analyse_steering(ticks, 0.5)
    assert res["yawRateDegSCarla"] == pytest.approx(-2.0)


# ------------------------------------------------------------- the subcommands on the fake


def test_calib_decel_on_the_fake_commands_the_adapter_rule_and_writes_the_record(tmp_path, server, factory,
                                                                                clock):
    rc, lines = run_main(["calib-decel", "--run-dir", str(tmp_path / "c"), "--speeds", "20", "--decels", "1,5"],
                         factory, clock)
    assert rc == 0
    roles = [json.loads(line)["role"] for line in lines if json.loads(line).get("event") == "hero"]
    assert roles == ["de4sdv_calibration", "de4sdv_calibration"]      # no candidate client attaches to it
    rec = json.loads((tmp_path / "c" / "simulator" / "calibration_decel.json").read_text())
    assert [p["commandedDecelMps2"] for p in rec["passes"]] == [1.0, 5.0]
    # the fake reaches the commanded rate: the analysis reads it back
    for p in rec["passes"]:
        assert p["achievedDecelMps2"] == pytest.approx(p["commandedDecelMps2"], rel=0.02)
    calls = [c for c in server.control_log if c["call"] == "apply_ackermann_control"]
    assert calls and all(c["client"] == "world_side" for c in calls)
    for c in calls:
        steer, speed, accel, jerk = c["value"]
        assert steer == 0.0 and jerk == 10.0 and speed >= 0.0
    # one command per 0.1 s: never two in a row on consecutive frames
    frames = [c["frame"] for c in calls]
    assert all(b - a >= 2 for a, b in zip(frames, frames[1:]) if b != a)
    # speed = max(0, v + 2 a) with v from the snapshot: a braking command at 5 m/s2 from 20 km/h targets 0
    brakes = [c for c in calls if c["value"][2] == -5.0]
    assert brakes[0]["value"][1] == pytest.approx(0.0)
    assert not server.actors


def test_calib_steer_on_the_fake_starts_right_of_center_and_reads_a_left_turn(tmp_path, server, factory, clock):
    def steer_toward_center(hero):          # the stand-in candidate steers left (negative CARLA steer)
        return -0.01 if hero.get_location().y > 0.05 else 0.0
    AdapterStandIn(server, target_kmh=21.0, steer_fn=steer_toward_center)
    rc, _ = run_main(["calib-steer", "--run-dir", str(tmp_path / "s"), "--run-s", "15"], factory, clock)
    assert rc == 0
    rec = json.loads((tmp_path / "s" / "simulator" / "calibration_steering.json").read_text())
    assert rec["assumption"] == "ASM-DRIVING-006"
    assert rec["setting"]["hero"]["lateralOffsetM"] == 0.5
    assert rec["setting"]["target"] is None
    assert rec["analysis"]["offsetAtStartM"] == pytest.approx(0.5, abs=0.05)
    assert rec["analysis"]["turn"] == "left" and rec["analysis"]["shown"] is True
    hero_calls = [c for c in server.control_log if c["client"] == "world_side"
                  and c["call"].startswith("apply")]
    assert hero_calls == []


def test_warmup_moves_the_hero_by_pose_only_and_removes_it(tmp_path, server, factory, clock):
    rc, _ = run_main(["warmup", "--run-dir", str(tmp_path / "w"), "--warmup-step-m", "5"], factory, clock)
    assert rc == 0
    summary = json.loads((tmp_path / "w" / "simulator" / "warmup_summary.json").read_text())
    assert summary["ticks"] == 28 and summary["distanceM"] == pytest.approx(140.0)   # (150 - 10) / 5
    calls = {c["call"] for c in server.control_log if c["client"] == "world_side"}
    assert calls <= {"set_transform", "apply_control"}       # apply_control: the target's hand brake only
    targets = {e[1] for e in server.log if e[0] == "spawn" and e[2] == "vehicle.tesla.model3"}
    assert all(c["actor"] in targets for c in server.control_log if c["call"] == "apply_control")
    assert not server.actors
    assert math.isclose(summary["pacing"]["stepS"], 0.05)
