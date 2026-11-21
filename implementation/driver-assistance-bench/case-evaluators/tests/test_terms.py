"""The terms of the S1 evaluators (terms.py) against the model's numbers.

Each figure below is written from driver_assistance_needs_requirements.sysml, not read from terms.py.
"""

import math

import pytest

import make_da_synthetic_run as syn
import terms
from case_evaluators_testkit import MODEL

NR = MODEL / "driver_assistance_needs_requirements.sysml"


def test_seven_settings_with_the_model_bands():
    # driver_assistance_needs_requirements.sysml:188-195
    want = {
        "SC-DRIVING-012@20": ("SC-DRIVING-012", "stationaryAt20", 20.0, 22.0, True),
        "SC-DRIVING-012@42": ("SC-DRIVING-012", "stationaryAt42", 40.0, 42.0, True),
        "SC-DRIVING-012@60": ("SC-DRIVING-012", "stationaryAt60", 58.0, 60.0, True),
        "SC-DRIVING-013@30": ("SC-DRIVING-013", "slowerAt30", 30.0, 32.0, True),
        "SC-DRIVING-013@60": ("SC-DRIVING-013", "slowerAt60", 58.0, 60.0, True),
        "SC-DRIVING-014@30": ("SC-DRIVING-014", "curveAt30", 28.0, 30.0, False),
        "SC-DRIVING-015@40": ("SC-DRIVING-015", "turningOffAt40", 38.0, 40.0, False),
    }
    got = {k: (s.scenario, s.identity, s.low_kmh, s.high_kmh, s.judged) for k, s in terms.SETTINGS.items()}
    assert got == want
    assert terms.ALL_SETTINGS == tuple(want)
    assert terms.JUDGED_SETTINGS == tuple(k for k, v in want.items() if v[4])
    assert terms.SETTINGS["SC-DRIVING-013@30"].target_low_kmh == 18.0
    assert terms.SETTINGS["SC-DRIVING-013@60"].target_high_kmh == 20.0
    text = NR.read_text()
    assert "SC-DRIVING-013 at 30\n     *   km/h (30 to 32 km/h)" in text and "(18 to 20 km/h)" in text


def test_band_is_inclusive():
    st = terms.SETTINGS["SC-DRIVING-012@20"]
    assert st.in_band(20.0 / 3.6) and st.in_band(22.0 / 3.6)
    assert not st.in_band(19.9 / 3.6) and not st.in_band(22.1 / 3.6)


def test_time_to_collision_and_needed_deceleration():
    assert terms.time_to_collision(20.0, 5.0) == pytest.approx(4.0)
    assert terms.time_to_collision(20.0, 0.0) is None
    assert terms.time_to_collision(20.0, -1.0) is None
    assert terms.needed_deceleration(10.0, 10.0) == pytest.approx(5.0)
    assert terms.needed_deceleration(10.0, 0.0) is None
    assert terms.needed_deceleration(0.0, 1.0) == math.inf


def test_imminent_needs_ttc_at_most_4_and_needed_at_least_1():
    # :221-225: TTC at most 4.0 s and needed deceleration at least 1.0 m/s2
    assert terms.is_imminent(8.0, 4.0)            # TTC 2.0, needed 1.0
    assert not terms.is_imminent(8.2, 4.0)        # needed 0.976
    assert not terms.is_imminent(20.0, 5.0)       # TTC 4.0 but needed 0.625


def test_imminent_boundaries_exact():
    assert terms.is_imminent(40.0, 10.0)          # TTC 4.0, needed 1.25
    assert not terms.is_imminent(40.4, 10.0)      # TTC 4.04
    assert not terms.is_imminent(10.0, 0.0)
    assert not terms.is_imminent(None, 3.0)


def test_maximum_relative_impact_speed_table():
    # :263-267: 0 up to 42, 15 at 45, 25 at 50, 30 at 55, 35 at 60; between two, the higher one's
    assert terms.max_relative_impact_kmh(20.0) == 0.0
    assert terms.max_relative_impact_kmh(42.0) == 0.0
    assert terms.max_relative_impact_kmh(42.01) == 15.0
    assert terms.max_relative_impact_kmh(45.0) == 15.0
    assert terms.max_relative_impact_kmh(45.5) == 25.0
    assert terms.max_relative_impact_kmh(50.0) == 25.0
    assert terms.max_relative_impact_kmh(52.0) == 30.0
    assert terms.max_relative_impact_kmh(55.0) == 30.0
    assert terms.max_relative_impact_kmh(59.0) == 35.0
    assert terms.max_relative_impact_kmh(60.0) == 35.0
    assert terms.max_relative_impact_kmh(60.5) is None


def test_warning_starts():
    ws = [{"requested": r, "issueTime_sim_s": float(i)} for i, r in enumerate([False, True, True, False, True])]
    assert [w["issueTime_sim_s"] for w in terms.warning_starts(ws)] == [1.0, 4.0]
    first_on = [{"requested": True, "issueTime_sim_s": 0.0}, {"requested": True, "issueTime_sim_s": 1.0}]
    assert [w["issueTime_sim_s"] for w in terms.warning_starts(first_on)] == [0.0]


def test_emergency_braking_starts_at_minus_5():
    accs = [-1.0, -6.0, -6.0, -1.0, -5.0, -4.99]
    cmds = [{"seq": i + 1, "acceleration": a, "issueTime_sim_s": float(i)} for i, a in enumerate(accs)]
    assert [c["seq"] for c in terms.emergency_braking_starts(cmds)] == [2, 5]
    # in seq order, whatever the order of the lines
    assert [c["seq"] for c in terms.emergency_braking_starts(list(reversed(cmds)))] == [2, 5]
    first = [{"seq": 1, "acceleration": -7.0, "issueTime_sim_s": 0.0}]
    assert [c["seq"] for c in terms.emergency_braking_starts(first)] == [1]


def _ticks(spec):
    return syn.simulate(spec)["ticks"]


def test_functional_part_and_judged_run_of_a_stationary_target():
    ticks = _ticks(syn.RunSpec("r", "SC-DRIVING-012@20"))
    st = terms.SETTINGS["SC-DRIVING-012@20"]
    fp = terms.functional_part(ticks, st)
    assert fp["met"]
    start = ticks[fp["startIndex"]]
    assert terms.time_to_collision(start["relative"]["gapM"], start["relative"]["closingMps"]) >= 4.0 - 1e-9
    nxt = ticks[fp["startIndex"] + 1]
    assert terms.time_to_collision(nxt["relative"]["gapM"], nxt["relative"]["closingMps"]) < 4.0
    assert fp["endReason"] == "at the speed of the target"
    assert ticks[fp["endIndex"]]["relative"]["closingMps"] <= 0.05
    jr = terms.judged_run(ticks, st)
    assert jr["judged"] and jr["missed"] == []
    assert jr["windowS"][0] == pytest.approx(start["simTimeS"] - 2.0)
    assert jr["windowS"][1] == pytest.approx(ticks[fp["endIndex"]]["simTimeS"])


def test_functional_part_of_a_moving_target_ends_at_its_speed():
    ticks = _ticks(syn.RunSpec("r", "SC-DRIVING-013@30"))
    fp = terms.functional_part(ticks, terms.SETTINGS["SC-DRIVING-013@30"])
    assert fp["met"] and fp["endReason"] == "at the speed of the target"
    assert ticks[fp["endIndex"]]["relative"]["closingMps"] <= 0.0
    assert ticks[fp["endIndex"] - 1]["relative"]["closingMps"] > 0.0


def test_moving_target_end_needs_closing_at_most_0_not_0_05():
    # plan A2: a moving target's speed is reached at closing <= 0; 0.03 m/s still closes on it
    st = terms.SETTINGS["SC-DRIVING-013@30"]
    v_e, v_t = 31.0 / 3.6, 19.0 / 3.6
    closings = [v_e - v_t] * 120 + [0.03, -0.2]
    ticks, gap = [], 60.0
    for i, c in enumerate(closings):
        ticks.append({"frame": i, "simTimeS": i * 0.05, "ego": {"speedMps": v_t + c if i >= 120 else v_e},
                      "relative": {"gapM": gap, "closingMps": c, "centerLineOffsetM": 0.0, "headingDiffDeg": 0.0},
                      "targetContact": False})
        gap -= max(c, 0.0) * 0.05
    fp = terms.functional_part(ticks, st)
    assert fp["met"] and fp["endIndex"] == 121


def test_functional_part_ends_at_contact():
    ticks = _ticks(syn.RunSpec("r", "SC-DRIVING-012@20", warn_at_needed=None, eb_at_needed=None))
    fp = terms.functional_part(ticks, terms.SETTINGS["SC-DRIVING-012@20"])
    assert fp["endReason"] == "contact with the target" and ticks[fp["endIndex"]]["targetContact"]


def test_judged_run_missed_by_center_line():
    ticks = _ticks(syn.RunSpec("r", "SC-DRIVING-012@20", center_offset_m=0.25))
    jr = terms.judged_run(ticks, terms.SETTINGS["SC-DRIVING-012@20"])
    assert not jr["judged"] and any("0.2" in m for m in jr["missed"])


def test_judged_run_missed_without_band():
    # a run at 21 km/h judged against the 40-42 km/h band has no functional part
    ticks = _ticks(syn.RunSpec("r", "SC-DRIVING-012@20"))
    jr = terms.judged_run(ticks, terms.SETTINGS["SC-DRIVING-012@42"])
    assert not jr["judged"] and "no functional part" in " ".join(jr["missed"])


def test_impact_speed_is_the_closing_before_the_contact_tick():
    ticks = _ticks(syn.RunSpec("r", "SC-DRIVING-012@20", warn_at_needed=None, eb_at_needed=None))
    fp = terms.functional_part(ticks, terms.SETTINGS["SC-DRIVING-012@20"])
    rs = terms.relative_speeds(ticks, fp)
    ci = fp["endIndex"]
    assert ticks[ci]["relative"]["closingMps"] < 0          # the rebound
    assert rs["impactKmh"] == pytest.approx(ticks[ci - 1]["relative"]["closingMps"] * 3.6)
    assert rs["approachKmh"] == pytest.approx(21.0, abs=0.01)


def test_no_contact_gives_impact_zero():
    ticks = _ticks(syn.RunSpec("r", "SC-DRIVING-012@20"))
    fp = terms.functional_part(ticks, terms.SETTINGS["SC-DRIVING-012@20"])
    rs = terms.relative_speeds(ticks, fp)
    assert rs["impactKmh"] == 0.0 and rs["contact"] is False
    assert rs["approachKmh"] is not None and rs["firstImminentFrame"] is not None
