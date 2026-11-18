"""The settings of SC-DRIVING-012 and the entry-condition checks of a run, from the world record.

Pure Python, no simulator: the world side calls it at the end of a run, and the case evaluators can call it on
an archived ``world.jsonl``.

Model sources (on main 23f13bd7, ``textual-notation-of-model/packages/features/driving/``):

- ``driver_assistance_needs_requirements.sysml``, ``termsOfTheDriverAssistanceRequirements``: the settings
  (SC-DRIVING-012 at 20 km/h, 20 to 22 km/h; at 42 km/h, 40 to 42 km/h; at 60 km/h, 58 to 60 km/h), the
  functional part, the judged run, the time to collision and the needed deceleration;
- the same file, ``vehicleTargetCriteriaFixedInPhase5``: the approach speeds are System 2's obligation, the
  candidate's own driving holds them, and a run that misses them is not judged.

What is a bench reading and not the model's text is marked BENCH READING in the code.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict

KMH = 1.0 / 3.6
TTC_FUNCTIONAL_MIN_S = 4.0        # functional part: a time to collision of at least 4 s
CENTER_LINE_MAX_M = 0.2           # judged run: center line within 0.2 m of the target's
STRAIGHT_BEFORE_S = 2.0           # judged run: for at least 2 s before the functional part
# BENCH READING: "travels straight" has no number in the model. The bench reads it as the heading of the
# vehicle within this angle of the target's heading over the 2 s; the evaluators may set their own.
STRAIGHT_HEADING_MAX_DEG = 2.0
# BENCH READING: "comes to the speed of the target"; a stationary target, so the vehicle at rest.
AT_REST_MPS = 0.05


@dataclass(frozen=True)
class Setting:
    """One setting: a scenario with an approach speed and its tolerance (model), plus bench proposals."""

    setting_id: str
    scenario: str
    approach_kmh: float
    low_kmh: float
    high_kmh: float
    target_speed_kmh: float
    # Proposals of this bench, not model values; each run's setting record states them.
    target_ahead_m: float
    run_cap_s: float
    speed_limit_mps: float

    def in_tolerance(self, speed_mps: float) -> bool:
        kmh = speed_mps * 3.6
        return self.low_kmh - 1e-9 <= kmh <= self.high_kmh + 1e-9

    def as_record(self) -> dict:
        record = asdict(self)
        record["model"] = ["setting_id", "scenario", "approach_kmh", "low_kmh", "high_kmh", "target_speed_kmh"]
        record["proposal"] = ["target_ahead_m", "run_cap_s", "speed_limit_mps"]
        return record


def _speed_limit(low_kmh: float, high_kmh: float) -> float:
    # PROPOSAL: the candidate's speed_limit (m/s, vision_pilot.conf:20) at the middle of the tolerance, so
    # that its own driving can hold the band. The model sets no value (NR, vehicleTargetCriteriaFixedInPhase5).
    return round((low_kmh + high_kmh) / 2.0 * KMH, 3)


SETTINGS: dict[str, Setting] = {
    "SC-DRIVING-012@20": Setting("SC-DRIVING-012@20", "SC-DRIVING-012", 20.0, 20.0, 22.0, 0.0,
                                 150.0, 90.0, _speed_limit(20.0, 22.0)),
    "SC-DRIVING-012@42": Setting("SC-DRIVING-012@42", "SC-DRIVING-012", 42.0, 40.0, 42.0, 0.0,
                                 220.0, 90.0, _speed_limit(40.0, 42.0)),
    "SC-DRIVING-012@60": Setting("SC-DRIVING-012@60", "SC-DRIVING-012", 60.0, 58.0, 60.0, 0.0,
                                 280.0, 90.0, _speed_limit(58.0, 60.0)),
}


def setting(setting_id: str) -> Setting:
    try:
        return SETTINGS[setting_id]
    except KeyError:
        raise KeyError(f"unknown setting {setting_id!r}; known: {sorted(SETTINGS)}") from None


# ------------------------------------------------------------------ the terms, per tick


def time_to_collision(gap_m: float | None, closing_mps: float | None) -> float | None:
    """Distance in the direction of travel over the closing speed; no value while not closing."""
    if gap_m is None or closing_mps is None or closing_mps <= 0.0:
        return None
    return max(gap_m, 0.0) / closing_mps


def needed_deceleration(gap_m: float | None, closing_mps: float | None) -> float | None:
    """Square of the closing speed over twice the distance; no value while not closing."""
    if gap_m is None or closing_mps is None or closing_mps <= 0.0:
        return None
    if gap_m <= 0.0:
        return math.inf
    return closing_mps * closing_mps / (2.0 * gap_m)


# ------------------------------------------------------------------ entry checks of a run


def _tick_values(tick: dict) -> dict:
    rel = tick.get("relative") or {}
    ego = tick.get("ego") or {}
    return {
        "t": tick.get("scenarioTimeS"),
        "frame": tick.get("frame"),
        "speed": ego.get("speedMps"),
        "gap": rel.get("gapM"),
        "closing": rel.get("closingMps"),
        "offset": rel.get("centerLineOffsetM"),
        "heading": rel.get("headingDiffDeg"),
        "contact": bool(tick.get("targetContact")),
    }


def evaluate_entry(ticks: list[dict], st: Setting) -> dict:
    """The entry conditions of one run of a setting of SC-DRIVING-012, from its world ticks in order.

    Returns a record with one entry per condition, each with ``met`` and the values behind it:

    - ``functionalPart``: the latest tick before the end of the approach at which the vehicle is inside the
      tolerance with a time to collision of at least 4 s (the start), and the end (contact with the target or
      the vehicle at rest);
    - ``straightBefore``: for the 2 s before that start, the center line within 0.2 m of the target's and the
      vehicle travelling straight (BENCH READING above);
    - ``judgedRun``: both met. A run that misses one is reported with what it missed and is not judged.
    """
    rows = [_tick_values(t) for t in ticks]
    rows = [r for r in rows if r["t"] is not None]
    out: dict = {"setting": st.setting_id, "ticks": len(rows), "bench_readings": {
        "straight_heading_max_deg": STRAIGHT_HEADING_MAX_DEG, "at_rest_mps": AT_REST_MPS}}
    if not rows:
        out.update(functionalPart={"met": False, "missed": "no world ticks"},
                   straightBefore={"met": False, "missed": "no world ticks"}, judgedRun=False)
        return out

    # End of the approach: the first contact with the target, or the vehicle at rest after it moved.
    end_index = len(rows) - 1
    end_reason = "run ended"
    moved = False
    for i, r in enumerate(rows):
        if r["contact"]:
            end_index, end_reason = i, "contact with the target"
            break
        if r["speed"] is not None and r["speed"] > 1.0:
            moved = True
        if moved and r["speed"] is not None and r["speed"] <= AT_REST_MPS:
            end_index, end_reason = i, "at the speed of the target"
            break

    start_index = None
    for i in range(end_index, -1, -1):
        r = rows[i]
        ttc = time_to_collision(r["gap"], r["closing"])
        if r["speed"] is not None and st.in_tolerance(r["speed"]) and ttc is not None \
                and ttc >= TTC_FUNCTIONAL_MIN_S:
            start_index = i
            break
    if start_index is None:
        speeds = [r["speed"] for r in rows[: end_index + 1] if r["speed"] is not None]
        out["functionalPart"] = {
            "met": False,
            "missed": "no tick in the tolerance with a time to collision of at least 4 s",
            "maxSpeedKmh": None if not speeds else round(max(speeds) * 3.6, 3),
            "toleranceKmh": [st.low_kmh, st.high_kmh], "endReason": end_reason,
        }
        out["straightBefore"] = {"met": False, "missed": "no functional part"}
        out["judgedRun"] = False
        return out

    start, end = rows[start_index], rows[end_index]
    out["functionalPart"] = {
        "met": True, "startFrame": start["frame"], "startS": start["t"],
        "startSpeedKmh": round(start["speed"] * 3.6, 3),
        "startTtcS": round(time_to_collision(start["gap"], start["closing"]), 3),
        "startGapM": round(start["gap"], 3), "endFrame": end["frame"], "endS": end["t"],
        "endReason": end_reason,
    }

    window = [r for r in rows[: start_index + 1] if r["t"] >= start["t"] - STRAIGHT_BEFORE_S - 1e-9]
    covered = window[0]["t"] if window else start["t"]
    missed = []
    if not window or start["t"] - covered < STRAIGHT_BEFORE_S - 1e-6:
        missed.append(f"the run holds only {start['t'] - covered:.3f} s before the functional part")
    offsets = [abs(r["offset"]) for r in window if r["offset"] is not None]
    headings = [abs(r["heading"]) for r in window if r["heading"] is not None]
    if len(offsets) < len(window) or len(headings) < len(window):
        missed.append("a tick of the window has no center-line offset or heading")
    if offsets and max(offsets) > CENTER_LINE_MAX_M:
        missed.append(f"center line {max(offsets):.3f} m from the target's (limit {CENTER_LINE_MAX_M} m)")
    if headings and max(headings) > STRAIGHT_HEADING_MAX_DEG:
        missed.append(f"heading {max(headings):.3f} deg off the target's (bench limit "
                      f"{STRAIGHT_HEADING_MAX_DEG} deg)")
    speeds = [r["speed"] * 3.6 for r in window if r["speed"] is not None]
    out["straightBefore"] = {
        "met": not missed, "missed": missed or None, "fromS": covered, "toS": start["t"],
        "maxCenterLineOffsetM": None if not offsets else round(max(offsets), 4),
        "maxHeadingDiffDeg": None if not headings else round(max(headings), 4),
        # Reported, not a condition of the model: the speed over the same 2 s.
        "speedKmhMinMax": None if not speeds else [round(min(speeds), 3), round(max(speeds), 3)],
    }
    out["judgedRun"] = bool(out["functionalPart"]["met"] and out["straightBefore"]["met"])
    return out
