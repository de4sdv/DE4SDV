"""The settings of SC-DRIVING-012 to -015, the stop run, and the entry-condition checks of a run, from the world
record.

Pure Python, no simulator: the world side calls it at the end of a run, and the case evaluators can call it on
an archived ``world.jsonl``.

Model sources (on main 23f13bd7, ``textual-notation-of-model/packages/features/driving/``):

- ``driver_assistance_needs_requirements.sysml``, ``termsOfTheDriverAssistanceRequirements`` (:188-195): the
  settings (SC-DRIVING-012 at 20 km/h, 20 to 22 km/h; at 42 km/h, 40 to 42 km/h; at 60 km/h, 58 to 60 km/h;
  SC-DRIVING-013 at 30 km/h, 30 to 32 km/h, and at 60 km/h, 58 to 60 km/h, behind a target at 20 km/h, 18 to
  20 km/h; SC-DRIVING-014 at 30 km/h, 28 to 30 km/h, toward a curve of at most 25 m radius; SC-DRIVING-015 at
  40 km/h, 38 to 40 km/h, behind the vehicle ahead at the same speed), the functional part and the judged run
  (:196-211, for SC-DRIVING-012 and -013 only), the stop run (:205-211: no run of a setting), the time to
  collision and the needed deceleration;
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
# BENCH READING: "comes to the speed of the target" behind a moving target (SC-DRIVING-013): the closing speed at
# or below this, after the vehicle had closed on the target (a positive closing speed before).
AT_TARGET_SPEED_CLOSING_MPS = 0.0
# PROPOSAL: the vehicle's acceleration assumed to size the road behind a moving target (road_needed_m); lower
# than the calibration's 2.0 m/s2, so that a slow candidate meets the target on the road all the same.
ROAD_SIZING_ACCEL_MPS2 = 1.0
ROAD_MARGIN_M = 40.0
# The further run of SC-DRIVING-012 with the S-CORE path stopped (needs_requirements.sysml:205-211, the stop-run
# decision of 2026-11-18): no run of a setting; its id is the run id of s1_runs.tsv.
STOP_RUN = "stop"
JUDGED_SCENARIOS = ("SC-DRIVING-012", "SC-DRIVING-013")


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
    target_ahead_m: float | None          # None: the site places the target (sites.resolve)
    run_cap_s: float
    speed_limit_mps: float
    # Model: the target's own band (SC-DRIVING-013: 18 to 20 km/h); the target's speed where the model gives none.
    target_low_kmh: float = 0.0
    target_high_kmh: float = 0.0
    # Proposal: the site of the setting (lead contract 2); None on the straight road of the survey.
    site: str | None = None
    # Model: True for a setting with a judged-run term (SC-DRIVING-012, -013), False for a setting without one
    # (SC-DRIVING-014, -015), None for the stop run, which is no run of a setting.
    judgeable: bool | None = True

    def in_tolerance(self, speed_mps: float) -> bool:
        kmh = speed_mps * 3.6
        return self.low_kmh - 1e-9 <= kmh <= self.high_kmh + 1e-9

    @property
    def moving_target(self) -> bool:
        return self.target_speed_kmh > 0.0

    @property
    def ends_at_target_speed(self) -> bool:
        """The functional part ends when the vehicle comes to the target's speed: a judged scenario behind a
        moving target (SC-DRIVING-013). SC-DRIVING-015 follows its vehicle ahead at its speed from the start."""
        return self.moving_target and self.scenario in JUDGED_SCENARIOS

    def as_record(self) -> dict:
        record = asdict(self)
        record["model"] = ["setting_id", "scenario", "approach_kmh", "low_kmh", "high_kmh", "target_speed_kmh",
                           "target_low_kmh", "target_high_kmh", "judgeable"]
        record["proposal"] = ["target_ahead_m", "run_cap_s", "speed_limit_mps", "site"]
        return record


def _speed_limit(low_kmh: float, high_kmh: float) -> float:
    # PROPOSAL: the candidate's speed_limit (m/s, vision_pilot.conf:20) at the middle of the tolerance, so
    # that its own driving can hold the band. The model sets no value (NR, vehicleTargetCriteriaFixedInPhase5).
    return round((low_kmh + high_kmh) / 2.0 * KMH, 3)


def _setting(setting_id: str, approach: float, low: float, high: float, target: tuple[float, float, float],
             ahead: float | None, cap: float, *, site: str | None = None, judgeable: bool | None = True,
             scenario: str | None = None) -> Setting:
    return Setting(setting_id, scenario or setting_id.split("@")[0], approach, low, high, target[0], ahead, cap,
                   _speed_limit(low, high), target[1], target[2], site, judgeable)


STATIONARY = (0.0, 0.0, 0.0)
TARGET_013 = (20.0, 18.0, 20.0)            # "behind a target at 20 km/h (18 to 20 km/h)"
TARGET_015 = (40.0, 40.0, 40.0)            # "behind the vehicle ahead at the same speed" (40 km/h); no band
# PROPOSALS (S1 plan section 3, 2026-11-20): run caps 60 s (75 s for SC-DRIVING-015); the SC-DRIVING-013 targets
# 40 m (@30) and 115 m (@60) ahead; SC-DRIVING-015's vehicle ahead 30 m; SC-DRIVING-014's target where its site
# places it; the stop run as SC-DRIVING-012@20, its path stopped at go + 12 s and its end 10 s of sim time after.
SETTINGS: dict[str, Setting] = {s.setting_id: s for s in (
    _setting("SC-DRIVING-012@20", 20.0, 20.0, 22.0, STATIONARY, 150.0, 60.0),
    _setting("SC-DRIVING-012@42", 42.0, 40.0, 42.0, STATIONARY, 220.0, 60.0),
    _setting("SC-DRIVING-012@60", 60.0, 58.0, 60.0, STATIONARY, 280.0, 60.0),
    _setting("SC-DRIVING-013@30", 30.0, 30.0, 32.0, TARGET_013, 40.0, 60.0),
    _setting("SC-DRIVING-013@60", 60.0, 58.0, 60.0, TARGET_013, 115.0, 60.0),
    _setting("SC-DRIVING-014@30", 30.0, 28.0, 30.0, STATIONARY, None, 60.0, site="sc014-curve", judgeable=False),
    _setting("SC-DRIVING-015@40", 40.0, 38.0, 40.0, TARGET_015, 30.0, 75.0, site="sc015-turnoff",
             judgeable=False),
    _setting(STOP_RUN, 20.0, 20.0, 22.0, STATIONARY, 150.0, 22.0, judgeable=None, scenario="SC-DRIVING-012"),
)}


def setting(setting_id: str) -> Setting:
    try:
        return SETTINGS[setting_id]
    except KeyError:
        raise KeyError(f"unknown setting {setting_id!r}; known: {sorted(SETTINGS)}") from None


def road_needed_m(st: Setting, ahead_m: float) -> float:
    """The straight road a setting of the survey's road needs: to the target plus a margin; behind a moving
    target, to where the vehicle reaches it (PROPOSAL: the vehicle at ROAD_SIZING_ACCEL_MPS2 up to its approach
    speed, then at it; the target at its speed from the start; center distances, so a little long)."""
    if not st.moving_target:
        return ahead_m + ROAD_MARGIN_M
    v, vt, a = st.approach_kmh * KMH, st.target_speed_kmh * KMH, ROAD_SIZING_ACCEL_MPS2
    t1 = v / a
    # met while accelerating: a t^2 / 2 = ahead + vt t
    t_meet = (vt + math.sqrt(vt * vt + 2.0 * a * ahead_m)) / a
    if t_meet <= t1:
        return 0.5 * a * t_meet * t_meet + ROAD_MARGIN_M
    d1 = 0.5 * a * t1 * t1
    gap = ahead_m + vt * t1 - d1
    return d1 + v * gap / (v - vt) + ROAD_MARGIN_M


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
        "straight_heading_max_deg": STRAIGHT_HEADING_MAX_DEG, "at_rest_mps": AT_REST_MPS,
        "at_target_speed_closing_mps": AT_TARGET_SPEED_CLOSING_MPS}}
    if st.judgeable is not True:
        why = ("the stop run is no run of a setting and no judged run (needs_requirements.sysml:205-211)"
               if st.judgeable is None else
               f"{st.scenario} has no judged-run term (needs_requirements.sysml:196-211): the run is recorded")
        out.update(functionalPart={"met": False, "missed": why}, straightBefore={"met": False, "missed": why},
                   judgedRun=False, notJudged=why)
        return out
    if not rows:
        out.update(functionalPart={"met": False, "missed": "no world ticks"},
                   straightBefore={"met": False, "missed": "no world ticks"}, judgedRun=False)
        return out

    # End of the approach: the first contact with the target, or the vehicle at the target's speed: at rest after
    # it moved (a stationary target), or, behind a moving target, the closing speed down to the bench reading
    # after the vehicle had closed on it.
    end_index = len(rows) - 1
    end_reason = "run ended"
    moved = closed = False
    for i, r in enumerate(rows):
        if r["contact"]:
            end_index, end_reason = i, "contact with the target"
            break
        if st.ends_at_target_speed:
            if r["closing"] is not None and r["closing"] > AT_TARGET_SPEED_CLOSING_MPS:
                closed = True
            elif closed and r["closing"] is not None:
                end_index, end_reason = i, "at the speed of the target"
                break
            continue
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


def tolerance_after_start(ticks: list[dict], st: Setting, entry: dict) -> dict:
    """The flag of lead answer B7.2 (2026-11-18): where the functional part starts, and whether the vehicle went
    above the tolerance after that start (a run too fast for its setting). BENCH READING: only leaving the band
    upward is flagged; leaving it downward after the start is the braking the run is about, and is reported."""
    fp = entry.get("functionalPart") or {}
    out: dict = {"rule": "the speed above the tolerance after the functional part started",
                 "toleranceKmh": [st.low_kmh, st.high_kmh], "functionalStartS": fp.get("startS"),
                 "functionalStartFrame": fp.get("startFrame"), "functionalStartSpeedKmh": fp.get("startSpeedKmh"),
                 "functionalStartTtcS": fp.get("startTtcS"), "tooFast": None}
    if not fp.get("met"):
        out["note"] = "no functional part: nothing to flag"
        return out
    rows = [_tick_values(t) for t in ticks]
    after = [r for r in rows if r["t"] is not None and r["speed"] is not None
             and fp["startS"] < r["t"] <= fp["endS"] + 1e-9]
    above = [r for r in after if r["speed"] * 3.6 > st.high_kmh + 1e-9]
    below = [r for r in after if r["speed"] * 3.6 < st.low_kmh - 1e-9]
    out.update({
        "tooFast": bool(above),
        "firstAboveToleranceS": above[0]["t"] if above else None,
        "maxSpeedKmhAfterStart": round(max(r["speed"] for r in after) * 3.6, 3) if after else None,
        "firstBelowToleranceS": below[0]["t"] if below else None,
    })
    return out
