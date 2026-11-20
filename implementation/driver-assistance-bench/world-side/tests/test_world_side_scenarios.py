"""The settings and the entry-condition terms (pure). The settings are read back from the model file on this
branch; the expected values of the terms are computed here by hand from their definitions."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import scenarios

ROOT = Path(__file__).resolve().parents[4]
NR = ROOT / "textual-notation-of-model/packages/features/driving/driver_assistance_needs_requirements.sysml"


def _model_text() -> str:
    return " ".join(NR.read_text(encoding="utf-8").split()).replace(" * ", " ")


def test_seven_settings_match_model_terms():
    # needs_requirements.sysml:188-195, termsOfTheDriverAssistanceRequirements, "Setting": the ids and the bands
    # are read from the model's sentence, not from scenarios.py
    text = _model_text()
    m = re.search(r"The settings are (.*?) Each setting is run twice", text)
    assert m, "the model's settings sentence changed: update scenarios.SETTINGS with it"
    sentence = m.group(1)
    found = re.findall(r"(SC-DRIVING-01[2-5])?\s*at (\d+) km/h \((\d+) to (\d+) km/h\)", sentence)
    model, scenario = {}, None
    for sc, approach, low, high in found:
        scenario = sc or scenario
        model[f"{scenario}@{approach}"] = (float(approach), float(low), float(high))
    # the target's own band of SC-DRIVING-013 ("behind a target at 20 km/h (18 to 20 km/h)") is no setting
    target_013 = model.pop("SC-DRIVING-013@20")
    assert target_013 == (20.0, 18.0, 20.0)
    assert sorted(model) == ["SC-DRIVING-012@20", "SC-DRIVING-012@42", "SC-DRIVING-012@60", "SC-DRIVING-013@30",
                             "SC-DRIVING-013@60", "SC-DRIVING-014@30", "SC-DRIVING-015@40"]
    runs_of_a_setting = {k: v for k, v in scenarios.SETTINGS.items() if v.judgeable is not None}
    assert sorted(runs_of_a_setting) == sorted(model)
    for sid, (approach, low, high) in model.items():
        st = scenarios.setting(sid)
        assert (st.scenario, st.approach_kmh, st.low_kmh, st.high_kmh) == (sid.split("@")[0], approach, low, high)
    for sid in ("SC-DRIVING-013@30", "SC-DRIVING-013@60"):
        st = scenarios.setting(sid)
        assert (st.target_speed_kmh, st.target_low_kmh, st.target_high_kmh) == target_013
    assert "SC-DRIVING-014 at 30 km/h (28 to 30 km/h), toward a curve of at most 25 m radius" in sentence
    assert "SC-DRIVING-015 at 40 km/h (38 to 40 km/h), behind the vehicle ahead at the same speed" in sentence
    assert scenarios.setting("SC-DRIVING-015@40").target_speed_kmh == 40.0          # "at the same speed"
    for sid in ("SC-DRIVING-012@20", "SC-DRIVING-012@42", "SC-DRIVING-012@60", "SC-DRIVING-014@30"):
        assert scenarios.setting(sid).target_speed_kmh == 0.0                         # a stationary target
    # judged-run terms exist for SC-DRIVING-012 and -013 only (needs_requirements.sysml:196-211)
    assert {k for k, v in runs_of_a_setting.items() if v.judgeable} == {
        "SC-DRIVING-012@20", "SC-DRIVING-012@42", "SC-DRIVING-012@60", "SC-DRIVING-013@30", "SC-DRIVING-013@60"}
    assert "time to collision of at least 4 s" in text
    assert "within 0.2 m of that of the target, for at least 2 s before its functional part" in text


def test_every_setting_names_its_site_by_the_shared_contract():
    # lead contract 2: None for the straight-road settings and the stop run; the two site ids for 014 and 015
    sites = {sid: st.site for sid, st in scenarios.SETTINGS.items()}
    assert sites == {"SC-DRIVING-012@20": None, "SC-DRIVING-012@42": None, "SC-DRIVING-012@60": None,
                     "SC-DRIVING-013@30": None, "SC-DRIVING-013@60": None,
                     "SC-DRIVING-014@30": "sc014-curve", "SC-DRIVING-015@40": "sc015-turnoff",
                     scenarios.STOP_RUN: None}
    assert all(st.setting_id == sid for sid, st in scenarios.SETTINGS.items())
    record = scenarios.setting("SC-DRIVING-014@30").as_record()
    assert record["site"] == "sc014-curve" and "site" in record["proposal"]


def test_the_stop_run_is_no_run_of_a_setting_and_drives_sc012_at_20():
    # needs_requirements.sysml:205-211: the stop run is no run of a setting and no judged run
    st = scenarios.setting(scenarios.STOP_RUN)
    assert st.judgeable is None and st.scenario == "SC-DRIVING-012"
    at20 = scenarios.setting("SC-DRIVING-012@20")
    assert (st.approach_kmh, st.low_kmh, st.high_kmh) == (at20.approach_kmh, at20.low_kmh, at20.high_kmh)
    # the path stops at go + 12 s; the cap, 42 s from the go, leaves 10 s of sim time after the stop's bound (22.2 s)
    # plus a margin, and the target stands as far as SC-DRIVING-012@60's, out of the hero's reach within the cap (J7
    # of the closure check of 44a4be29; test_world_side_stop_run_window.py)
    assert st.run_cap_s == 42.0
    assert st.target_ahead_m == scenarios.setting("SC-DRIVING-012@60").target_ahead_m == 280.0
    entry = scenarios.evaluate_entry(_approach(), st)
    assert entry["judgedRun"] is False and "no run of a setting" in entry["notJudged"]


def test_runs_of_014_and_015_are_recorded_not_judged():
    for sid in ("SC-DRIVING-014@30", "SC-DRIVING-015@40"):
        entry = scenarios.evaluate_entry(_approach(), scenarios.setting(sid))
        assert entry["judgedRun"] is False
        assert "no judged-run term" in entry["notJudged"]


def test_proposed_caps_and_target_distances():
    # S1 plan section 3: caps 60 s (75 s for 015); 013 targets 40 m (@30) and 115 m (@60) ahead; 015 30 m
    caps = {sid: st.run_cap_s for sid, st in scenarios.SETTINGS.items() if st.judgeable is not None}
    assert caps == {"SC-DRIVING-012@20": 60.0, "SC-DRIVING-012@42": 60.0, "SC-DRIVING-012@60": 60.0,
                    "SC-DRIVING-013@30": 60.0, "SC-DRIVING-013@60": 60.0, "SC-DRIVING-014@30": 60.0,
                    "SC-DRIVING-015@40": 75.0}
    assert scenarios.setting("SC-DRIVING-013@30").target_ahead_m == 40.0
    assert scenarios.setting("SC-DRIVING-013@60").target_ahead_m == 115.0
    assert scenarios.setting("SC-DRIVING-015@40").target_ahead_m == 30.0


def test_a_moving_target_needs_the_road_to_where_the_vehicle_reaches_it():
    # 013@60: the target at 115 m moves on at 20 km/h; the vehicle (PROPOSAL: 1.0 m/s2 up to 60 km/h) reaches
    # it about 242 m from the start, plus the 40 m margin of the stationary settings. By hand: at speed after
    # 16.67 s and 138.9 m, the target then at 115 + 5.556 * 16.67 = 207.6 m; 68.7 m at 11.11 m/s: 6.18 s more.
    st = scenarios.setting("SC-DRIVING-013@60")
    assert scenarios.road_needed_m(st, 115.0) == pytest.approx(138.89 + 16.667 * 6.18 + 40.0, abs=1.0)
    assert scenarios.road_needed_m(scenarios.setting("SC-DRIVING-012@60"), 280.0) == 320.0


def test_ttc_and_needed_deceleration_by_hand():
    assert scenarios.time_to_collision(22.2, 5.55) == pytest.approx(4.0)
    assert scenarios.time_to_collision(10.0, 0.0) is None
    assert scenarios.time_to_collision(10.0, -1.0) is None
    # (20 km/h)^2 / (2 * 3.0864 m) = 5.0 m/s2
    assert scenarios.needed_deceleration(3.0864197530864197, 20 / 3.6) == pytest.approx(5.0)
    assert scenarios.needed_deceleration(5.0, 0.0) is None


def test_tolerance_bounds_are_inclusive():
    st = scenarios.setting("SC-DRIVING-012@20")
    assert st.in_tolerance(20.0 / 3.6) and st.in_tolerance(22.0 / 3.6)
    assert not st.in_tolerance(19.99 / 3.6) and not st.in_tolerance(22.01 / 3.6)


def _tick(t, speed, gap, offset=0.0, heading=0.0, contact=False):
    return {"scenarioTimeS": t, "frame": int(round(t / 0.05)), "ego": {"speedMps": speed},
            "relative": {"gapM": gap, "closingMps": speed, "centerLineOffsetM": offset, "headingDiffDeg": heading},
            "targetContact": contact}


def _approach(v_kmh=21.0, gap0=60.0, offset_fn=lambda t: 0.0, heading_fn=lambda t: 0.0, t_end=None):
    v = v_kmh / 3.6
    out, t = [], 0.0
    while True:
        gap = gap0 - v * t
        if gap <= 0.0 or (t_end is not None and t > t_end):
            out.append(_tick(t, v, max(gap, 0.0), offset_fn(t), heading_fn(t), contact=gap <= 0.0))
            break
        out.append(_tick(t, v, gap, offset_fn(t), heading_fn(t)))
        t = round(t + 0.05, 6)
    return out


def test_functional_part_starts_at_the_last_tick_with_ttc_of_four_seconds():
    ticks = _approach()
    entry = scenarios.evaluate_entry(ticks, scenarios.setting("SC-DRIVING-012@20"))
    v = 21.0 / 3.6
    # gap0 - v t >= 4 v  <=>  t <= (60 - 4 v) / v; the last tick at the 0.05 s step
    expected_start = int(((60.0 - 4.0 * v) / v) / 0.05) * 0.05
    assert entry["functionalPart"]["met"] is True
    assert entry["functionalPart"]["startS"] == pytest.approx(expected_start, abs=1e-6)
    assert entry["functionalPart"]["endReason"] == "contact with the target"
    assert entry["straightBefore"]["met"] is True and entry["judgedRun"] is True


def test_an_offset_just_over_the_limit_in_the_window_misses_the_judged_run():
    ticks = _approach(offset_fn=lambda t: 0.2001 if 5.0 < t < 5.2 else 0.1999)   # window 4.25-6.25 s
    entry = scenarios.evaluate_entry(ticks, scenarios.setting("SC-DRIVING-012@20"))
    assert entry["functionalPart"]["met"] is True
    assert entry["straightBefore"]["met"] is False
    assert entry["straightBefore"]["maxCenterLineOffsetM"] == pytest.approx(0.2001)


def test_an_offset_outside_the_two_seconds_does_not_count():
    ticks = _approach(offset_fn=lambda t: 0.5 if t < 1.0 else 0.0)
    entry = scenarios.evaluate_entry(ticks, scenarios.setting("SC-DRIVING-012@20"))
    assert entry["judgedRun"] is True


def test_a_heading_off_the_target_misses_straight():
    ticks = _approach(heading_fn=lambda t: 2.5)
    entry = scenarios.evaluate_entry(ticks, scenarios.setting("SC-DRIVING-012@20"))
    assert entry["straightBefore"]["met"] is False


def test_fewer_than_two_seconds_before_the_functional_part():
    # gap0 so close that the start is at about 1 s: the window cannot hold 2 s
    v = 21.0 / 3.6
    ticks = _approach(gap0=4.0 * v + v * 1.0)
    entry = scenarios.evaluate_entry(ticks, scenarios.setting("SC-DRIVING-012@20"))
    assert entry["functionalPart"]["met"] is True
    assert entry["straightBefore"]["met"] is False
    assert "holds only" in entry["straightBefore"]["missed"][0]


def test_no_ticks():
    entry = scenarios.evaluate_entry([], scenarios.setting("SC-DRIVING-012@20"))
    assert entry["judgedRun"] is False and entry["functionalPart"]["met"] is False


def _follow(v_kmh=31.0, target_kmh=20.0, gap0=40.0, brake_at_gap=12.0, decel=2.0, t_end=60.0):
    """SC-DRIVING-013: the vehicle at v_kmh behind a target at target_kmh; from brake_at_gap it brakes at decel
    down to the target's speed and then follows at it."""
    v, vt, gap, t, out, braking = v_kmh / 3.6, target_kmh / 3.6, gap0, 0.0, [], False
    while t <= t_end + 1e-9:
        out.append({"scenarioTimeS": round(t, 6), "frame": int(round(t / 0.05)), "ego": {"speedMps": v},
                    "relative": {"gapM": gap, "closingMps": v - vt, "centerLineOffsetM": 0.0,
                                 "headingDiffDeg": 0.0}, "targetContact": False})
        braking = braking or gap <= brake_at_gap
        if braking:
            v = max(vt, v - decel * 0.05)
        gap -= (v - vt) * 0.05
        t += 0.05
    return out


def test_a_moving_target_run_ends_when_the_vehicle_comes_to_the_target_speed():
    # needs_requirements.sysml:196-200 "... until the vehicle hits the target or comes to the speed of the
    # target"; BENCH READING: the closing speed at or below 0 after the vehicle closed on the target
    ticks = _follow()
    entry = scenarios.evaluate_entry(ticks, scenarios.setting("SC-DRIVING-013@30"))
    fp = entry["functionalPart"]
    assert fp["met"] is True and fp["endReason"] == "at the speed of the target"
    first_matched = next(t for t in ticks if t["relative"]["closingMps"] <= 0.0)
    assert fp["endS"] == pytest.approx(first_matched["scenarioTimeS"])
    assert fp["endS"] < 30.0                                    # not the end of the record (60 s)
    assert entry["judgedRun"] is True
    assert entry["bench_readings"]["at_target_speed_closing_mps"] == 0.0


def test_a_moving_target_is_not_matched_while_it_pulls_away_at_the_start():
    # at the start the vehicle is slower than the target (closing < 0): that is no end of the approach
    ticks = _follow(v_kmh=31.0)
    for k, t in enumerate(ticks[:60]):                       # the first 3 s: the vehicle accelerates from 0
        t["ego"]["speedMps"] = min(31.0 / 3.6, 3.0 * k * 0.05)
        t["relative"]["closingMps"] = t["ego"]["speedMps"] - 20.0 / 3.6
    entry = scenarios.evaluate_entry(ticks, scenarios.setting("SC-DRIVING-013@30"))
    assert entry["functionalPart"]["endS"] > 3.0
    assert entry["functionalPart"]["endReason"] == "at the speed of the target"
