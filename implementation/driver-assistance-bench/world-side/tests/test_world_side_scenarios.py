"""The settings and the entry-condition terms (pure). The settings are read back from the model file on this
branch; the expected values of the terms are computed here by hand from their definitions."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

import scenarios

ROOT = Path(__file__).resolve().parents[4]
NR = ROOT / "textual-notation-of-model/packages/features/driving/driver_assistance_needs_requirements.sysml"


def test_the_settings_of_sc012_are_the_model_terms():
    text = " ".join(NR.read_text(encoding="utf-8").split())
    text = text.replace(" * ", " ")
    m = re.search(r"SC-DRIVING-012 at 20 km/h \(20 to 22 km/h\), at 42 km/h \(40 to 42 km/h\) and at 60 km/h "
                  r"\(58 to 60 km/h\)", text)
    assert m, "the model's settings sentence changed: update scenarios.SETTINGS with it"
    got = {(s.approach_kmh, s.low_kmh, s.high_kmh) for s in scenarios.SETTINGS.values()}
    assert got == {(20.0, 20.0, 22.0), (42.0, 40.0, 42.0), (60.0, 58.0, 60.0)}
    assert all(s.target_speed_kmh == 0.0 for s in scenarios.SETTINGS.values())    # a stationary target
    assert "time to collision of at least 4 s" in text
    assert "within 0.2 m of that of the target, for at least 2 s before its functional part" in text


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
