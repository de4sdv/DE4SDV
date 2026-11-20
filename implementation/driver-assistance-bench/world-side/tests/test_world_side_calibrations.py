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
        out.append({"scenarioTimeS": t, "frame": 1000 + k, "ego": {"speedMps": speed,
                                                                 "yawDegCarla": 90.0 + yaw_rate_deg_s * t,
                                                                 "lane": {"offsetM": offset0 - 0.01 * t}},
                    "control": {"steer": -0.01 if yaw_rate_deg_s < 0 else 0.01}})
    return out


def test_steering_left_from_the_right_shows_the_assumption():
    res = calibration.analyse_steering(_steer_ticks(-2.0), 0.5, settled_mps=2.0)
    assert res["turn"] == "left" and res["shown"] is True
    assert res["yawRateDegSCarla"] == pytest.approx(-2.0)
    assert res["windowS"][0] == pytest.approx(2.0)          # speed 1 m/s2 * t reaches 2 m/s at 2 s


def test_steering_right_from_the_right_does_not_show_it():
    res = calibration.analyse_steering(_steer_ticks(+2.0), 0.5, settled_mps=2.0)
    assert res["turn"] == "right" and res["shown"] is False


def test_steering_with_no_turn_is_missed_not_shown():
    res = calibration.analyse_steering(_steer_ticks(0.0), 0.5, settled_mps=2.0)
    assert res["shown"] is None and "no turn" in res["missed"]


def test_steering_never_moving():
    res = calibration.analyse_steering(_steer_ticks(-2.0, v=1.0), 0.5, settled_mps=2.0)
    assert res["shown"] is None


def test_yaw_unwrapping_across_180():
    ticks = _steer_ticks(-2.0)
    for t in ticks:
        t["ego"]["yawDegCarla"] = ((t["ego"]["yawDegCarla"] + 87.0 + 180.0) % 360.0) - 180.0 + 0.0
    res = calibration.analyse_steering(ticks, 0.5, settled_mps=2.0)
    assert res["yawRateDegSCarla"] == pytest.approx(-2.0)


# ---------------------------------------- ASM-DRIVING-006: the judgement fix of the attempt-3 diagnosis (A7)

SETTLED_20 = 20.0 / 3.6          # SC-DRIVING-012@20: the band starts at 20 km/h


def _return_ticks(offset_fn, *, v=21.0 / 3.6, accel=1.0, t_end=60.0, lane_yaw=90.0, first_frame=5000):
    """A calib-steer record: the vehicle accelerates at ``accel`` to ``v`` (the speed then settles there), its
    lane offset follows ``offset_fn(tau)`` from the instant the speed settles (tau in s; 0.5 m before), and its
    yaw is the lane's plus the heading that this offset path needs (CARLA: positive offset right, a left turn is
    a falling yaw). Built here in closed form, independent of calibration.py."""
    t_settle = v / accel
    out = []
    for k in range(int(round(t_end / 0.05)) + 1):
        t = k * 0.05
        speed = min(v, accel * t)
        tau = t - t_settle
        offset = offset_fn(tau) if tau > 0 else offset_fn(0.0)
        if tau > 0:
            h = 1e-3
            lateral = (offset_fn(tau + h) - offset_fn(max(0.0, tau - h))) / (tau + h - max(0.0, tau - h))
        else:
            lateral = 0.0
        heading = math.degrees(math.atan2(lateral, speed)) if speed > 0 else 0.0
        out.append({"scenarioTimeS": round(t, 6), "frame": first_frame + k,
                    "ego": {"speedMps": speed, "yawDegCarla": lane_yaw + heading, "lane": {"offsetM": offset}},
                    "control": {"steer": -0.001 if lateral < 0 else 0.0}})
    return out


def _smooth_return(tau):
    """0.5 m to 0 over 10 s (a half cosine), then held at 0."""
    return 0.25 * (1.0 + math.cos(math.pi * min(tau, 10.0) / 10.0))


def test_a_slow_return_after_the_speed_settles_reads_shown():
    # RED (a) of the S1 plan, task A7: the response begins once the speed has settled, as in attempt 3
    # (diagnosis DIAGNOSIS.md:43-57); the judgement from 2 m/s on (3 s while still accelerating) read 'missed'
    ticks = _return_ticks(_smooth_return)
    res = calibration.analyse_steering(ticks, 0.5, settled_mps=SETTLED_20)
    assert res["shown"] is True and res["turn"] == "left"
    t_settle = SETTLED_20 / 1.0                                 # the first tick at 20 km/h, at 1 m/s2
    assert res["settledAtS"] == pytest.approx(t_settle, abs=0.051)
    assert res["windowS"][0] >= res["settledAtS"] - 1e-9
    trend = res["offsetTrend"]
    assert trend["startM"] == pytest.approx(0.5, abs=1e-3)
    assert trend["minAbsM"] == pytest.approx(0.0, abs=1e-3)
    assert trend["minAbsAtS"] == pytest.approx(21.0 / 3.6 + 10.0, abs=0.06)
    # beside the first window that reaches the rate: the steepest window before the lane centre
    steep = res["steepestWindow"]
    assert abs(steep["yawRateDegSCarla"]) >= abs(res["yawRateDegSCarla"]) and steep["yawRateDegSCarla"] < 0
    assert res["settledAtS"] - 1e-9 <= steep["windowS"][0] and steep["windowS"][1] <= res["judgedToS"] + 1e-9


def test_the_offset_trend_names_the_first_zero_crossing():
    ticks = _return_ticks(lambda tau: 0.5 * math.cos(math.pi * min(tau, 14.0) / 20.0))
    res = calibration.analyse_steering(ticks, 0.5, settled_mps=SETTLED_20)
    trend = res["offsetTrend"]
    assert trend["firstZeroCrossingS"] == pytest.approx(21.0 / 3.6 + 10.0, abs=0.06)
    assert trend["minAbsM"] == pytest.approx(0.0, abs=0.01)
    assert res["shown"] is True


def test_the_judgement_starts_at_the_setting_speed_not_at_two_metres_a_second():
    # a vehicle that leans right while it accelerates, then returns left after the speed settled
    def offset(tau):
        return _smooth_return(tau)
    ticks = _return_ticks(offset)
    t_settle = 21.0 / 3.6
    for t in ticks:
        if t["scenarioTimeS"] < t_settle:              # a right drift of the yaw during the acceleration
            t["ego"]["yawDegCarla"] = 90.0 + 0.5 * t["scenarioTimeS"]
        else:
            t["ego"]["yawDegCarla"] += 0.5 * t_settle
    res = calibration.analyse_steering(ticks, 0.5, settled_mps=SETTLED_20)
    assert res["settledAtS"] == pytest.approx(5.6)            # the first tick at 20 km/h, at 1 m/s2
    assert res["windowS"][0] >= res["settledAtS"] - 1e-9
    assert res["turn"] == "left" and res["shown"] is True


def test_the_offset_trend_starts_at_the_settled_tick_not_at_the_record_start():
    # the vehicle sways right while it accelerates (0.9 m); the trend is read from the first tick at 20 km/h
    ticks = _return_ticks(_smooth_return)
    for t in ticks:
        if t["scenarioTimeS"] < 5.6 - 1e-9:
            t["ego"]["lane"]["offsetM"] = 0.9
    res = calibration.analyse_steering(ticks, 0.5, settled_mps=SETTLED_20)
    assert res["settledAtS"] == pytest.approx(5.6)
    assert res["offsetTrend"]["startM"] == pytest.approx(0.5, abs=1e-6)


def test_a_turn_after_the_lane_centre_is_not_the_response_to_the_start_offset():
    # the vehicle drifts across the centre with no turn (a constant small heading), then turns right from the
    # left: that right turn answers its new offset, not the start right of centre; the judgement stops at the
    # first tick at or across the centre
    v = 21.0 / 3.6
    ticks = _return_ticks(lambda tau: 0.5 - 0.05 * tau, t_end=40.0)
    t_cross = v + 10.0
    for t in ticks:
        if t["scenarioTimeS"] > t_cross:
            t["ego"]["yawDegCarla"] += 0.5 * (t["scenarioTimeS"] - t_cross)
    res = calibration.analyse_steering(ticks, 0.5, settled_mps=SETTLED_20)
    assert res["offsetTrend"]["firstZeroCrossingS"] == pytest.approx(t_cross, abs=0.06)
    assert res["shown"] is None and res["turn"] is None
    assert res["windowS"][1] <= t_cross + 0.06


def _commands(ticks, until_s):
    return [{"kind": "out.driving_command", "seq": i + 1, "frame": t["frame"]}
            for i, t in enumerate(x for x in ticks if x["scenarioTimeS"] <= until_s + 1e-9)][::2]


def test_a_record_whose_commands_end_before_the_cap_is_not_judged_past_the_last_command():
    # RED (b) of the S1 plan, task A7: in attempt 3 the commands ended at about 80.5 s of a 90 s cap, and the
    # world held the last applied steer; the car then left the lane (DIAGNOSIS.md:256-258). Here the vehicle
    # holds its offset while the candidate commands, and only after its last command (30 s) does it go left.
    late = 30.0 - 21.0 / 3.6
    ticks = _return_ticks(lambda tau: 0.5 if tau < late else _smooth_return(tau - late), t_end=45.0)
    cmds = _commands(ticks, 30.0)
    last = max(c["frame"] for c in cmds)
    last_s = next(t["scenarioTimeS"] for t in ticks if t["frame"] == last)
    res = calibration.analyse_steering(ticks, 0.5, settled_mps=SETTLED_20, commands=cmds)
    assert res["shown"] is None and res["turn"] is None
    assert res["cut"]["lastCommandFrame"] == last
    assert res["cut"]["lastCommandS"] == pytest.approx(last_s)
    assert res["cut"]["ticksCut"] == sum(1 for t in ticks if t["frame"] > last)
    assert res["judgedToS"] <= last_s + 1e-9
    assert res["windowS"] is None or res["windowS"][1] <= last_s + 1e-9
    assert res["offsetTrend"]["minAbsM"] == pytest.approx(0.5, abs=1e-6)       # nothing after the cut
    assert res["offsetTrend"]["firstZeroCrossingS"] is None
    assert res["provisional"] is False
    # the same record judged to its end would read the late return as shown: the cut is what decides
    whole = calibration.analyse_steering(ticks, 0.5, settled_mps=SETTLED_20)
    assert whole["shown"] is True and whole["provisional"] is True
    assert whole["cut"]["lastCommandFrame"] is None


def test_commands_are_matched_by_sim_time_when_they_carry_no_frame():
    ticks = _return_ticks(_smooth_return, t_end=40.0)
    for t in ticks:
        t["simTimeS"] = 400.0 + t["scenarioTimeS"]
    cmds = [{"kind": "out.driving_command", "issueTime_sim_s": 400.0 + 20.0}]
    res = calibration.analyse_steering(ticks, 0.5, settled_mps=SETTLED_20, commands=cmds)
    assert res["cut"]["lastCommandS"] == pytest.approx(20.0, abs=1e-6)
    assert res["judgedToS"] == pytest.approx(20.0, abs=1e-6)


def test_a_record_with_no_command_is_not_judged():
    ticks = _return_ticks(_smooth_return, t_end=30.0)
    res = calibration.analyse_steering(ticks, 0.5, settled_mps=SETTLED_20, commands=[])
    assert res["shown"] is None and "no command" in res["missed"]


def test_steering_judgement_reads_the_score_record_driving_commands(tmp_path):
    ticks = _return_ticks(_smooth_return, t_end=30.0)
    world = tmp_path / "world.jsonl"
    world.write_text("".join(json.dumps({"event": "tick", "data": t}) + "\n" for t in ticks))
    score = tmp_path / "score_interface.jsonl"
    lines = [{"kind": "start"}, {"kind": "in.camera_image", "frame": ticks[-1]["frame"]}]
    lines += [{"kind": "out.driving_command", "seq": i, "frame": t["frame"], "issueTime_sim_s": 0.0}
              for i, t in enumerate(ticks[:400:2], 1)]
    score.write_text("".join(json.dumps(x) + "\n" for x in lines))
    out = tmp_path / "judged.json"
    rc = calibration.main(["steer", "--world", str(world), "--score", str(score), "--setting-low-kmh", "20",
                           "--start-offset-m", "0.5", "--out", str(out)])
    assert rc == 0
    rec = json.loads(out.read_text())
    assert rec["assumption"] == "ASM-DRIVING-006"
    assert rec["analysis"]["cut"]["lastCommandFrame"] == ticks[398]["frame"]   # camera images are no commands
    assert rec["analysis"]["cut"]["commands"] == 200


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
    first = json.loads((tmp_path / "s" / "simulator" / "world.jsonl").read_text().splitlines()[0])["data"]
    assert first["ego"]["lane"]["offsetM"] == pytest.approx(0.5, abs=0.05)
    # judged from the first tick at 20 km/h on; the stand-in steers from the start, so the offset is smaller there
    assert rec["analysis"]["settledAtS"] > 2.0
    assert rec["analysis"]["offsetTrend"]["startM"] < 0.5
    assert rec["analysis"]["turn"] == "left" and rec["analysis"]["shown"] is True
    # the world side has no command record: the judgement is provisional (the session re-judges it)
    assert rec["analysis"]["provisional"] is True and rec["analysis"]["cut"]["lastCommandFrame"] is None
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
