"""The terms of the driver-assistance requirements, as the S1 case evaluators compute them from the records.

Model: `textual-notation-of-model/packages/features/driving/driver_assistance_needs_requirements.sysml`, the terms
at :188-278 (setting :196-203, functional part :204-208, judged run :209-219, time to collision :220-223, needed
deceleration :224-228, imminent collision :229-233, warning request :240-242, emergency braking :243-250, relative
approach and impact speed and their limit :267-275). Every number here is the model's, except those marked
EVALUATOR READING or BENCH READING (OBSERVABLES.md, "Terms").
"""

from __future__ import annotations

import math
from dataclasses import dataclass

KMH = 1.0 / 3.6

TTC_IMMINENT_MAX_S = 4.0            # :229-233
NEEDED_IMMINENT_MIN_MPS2 = 1.0      # :229-233
EMERGENCY_BRAKING_MPS2 = 5.0        # :243-250 (a command for a deceleration of at least 5.0 m/s2)
TTC_FUNCTIONAL_MIN_S = 4.0          # :204-208
CENTER_LINE_MAX_M = 0.2             # :209-219
STRAIGHT_BEFORE_S = 2.0             # :209-219
WARNING_LEAD_S = 1.0                # :346 (REQ-DRIVING-042)
# BENCH READING (B/world-side/scenarios.py:29-31): "travels straight" as the heading within 2 deg of the target's.
STRAIGHT_HEADING_MAX_DEG = 2.0
# BENCH READING (B/world-side/scenarios.py:33-34): a stationary target's speed reached at 0.05 m/s of closing.
AT_REST_MPS = 0.05
# :271-275: the maximum relative impact speed by relative approach speed, km/h; between two, the higher one's.
IMPACT_LIMITS_KMH = ((42.0, 0.0), (45.0, 15.0), (50.0, 25.0), (55.0, 30.0), (60.0, 35.0))
EPS = 1e-9


@dataclass(frozen=True)
class SettingTerms:
    setting_id: str
    scenario: str
    identity: str            # AssistanceSettingIdentity (driver_assistance_verification_evidence.sysml:119-142)
    low_kmh: float
    high_kmh: float
    target_low_kmh: float | None
    target_high_kmh: float | None
    judged: bool             # SC-DRIVING-012 and -013 have judged runs (:209-219)

    def in_band(self, speed_mps: float) -> bool:
        kmh = speed_mps * 3.6
        return self.low_kmh - EPS <= kmh <= self.high_kmh + EPS

    @property
    def moving_target(self) -> bool:
        return bool(self.target_high_kmh)


def _s(sid, scen, ident, lo, hi, tlo=None, thi=None, judged=True):
    return SettingTerms(sid, scen, ident, lo, hi, tlo, thi, judged)


# :196-203. SC-DRIVING-015's vehicle ahead runs "at the same speed"; no band of its own is stated.
SETTINGS: dict[str, SettingTerms] = {s.setting_id: s for s in (
    _s("SC-DRIVING-012@20", "SC-DRIVING-012", "stationaryAt20", 20.0, 22.0, 0.0, 0.0),
    _s("SC-DRIVING-012@42", "SC-DRIVING-012", "stationaryAt42", 40.0, 42.0, 0.0, 0.0),
    _s("SC-DRIVING-012@60", "SC-DRIVING-012", "stationaryAt60", 58.0, 60.0, 0.0, 0.0),
    _s("SC-DRIVING-013@30", "SC-DRIVING-013", "slowerAt30", 30.0, 32.0, 18.0, 20.0),
    _s("SC-DRIVING-013@60", "SC-DRIVING-013", "slowerAt60", 58.0, 60.0, 18.0, 20.0),
    _s("SC-DRIVING-014@30", "SC-DRIVING-014", "curveAt30", 28.0, 30.0, 0.0, 0.0, judged=False),
    _s("SC-DRIVING-015@40", "SC-DRIVING-015", "turningOffAt40", 38.0, 40.0, None, None, judged=False),
)}
ALL_SETTINGS: tuple[str, ...] = tuple(SETTINGS)
JUDGED_SETTINGS: tuple[str, ...] = tuple(k for k, v in SETTINGS.items() if v.judged)


def _num(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def time_to_collision(gap_m, closing_mps):
    """:220-223: the distance over the closing speed; no value while not closing."""
    gap, closing = _num(gap_m), _num(closing_mps)
    if gap is None or closing is None or closing <= 0.0:
        return None
    return max(gap, 0.0) / closing


def needed_deceleration(gap_m, closing_mps):
    """:224-228: the square of the closing speed over twice the distance; no value while not closing."""
    gap, closing = _num(gap_m), _num(closing_mps)
    if gap is None or closing is None or closing <= 0.0:
        return None
    if gap <= 0.0:
        return math.inf
    return closing * closing / (2.0 * gap)


def is_imminent(gap_m, closing_mps) -> bool:
    """:229-233: a time to collision of at most 4.0 s and a needed deceleration of at least 1.0 m/s2."""
    ttc, needed = time_to_collision(gap_m, closing_mps), needed_deceleration(gap_m, closing_mps)
    return ttc is not None and needed is not None and ttc <= TTC_IMMINENT_MAX_S + EPS \
        and needed >= NEEDED_IMMINENT_MIN_MPS2 - EPS


def max_relative_impact_kmh(approach_kmh: float):
    """:271-275; None above 60 km/h, where the model gives no limit."""
    for upto, limit in IMPACT_LIMITS_KMH:
        if approach_kmh <= upto + EPS:
            return limit
    return None


def warning_starts(warnings: list[dict]) -> list[dict]:
    """:240-242: the warning request starts when the output begins to ask (false to true, or a first true)."""
    out, before = [], False
    for w in warnings:
        on = w.get("requested") is True
        if on and not before:
            out.append(w)
        before = on
    return out


def emergency_braking_starts(commands: list[dict]) -> list[dict]:
    """:243-250: the first command for a deceleration of at least 5.0 m/s2 after a command for less, in seq order;
    a first command of the run that brakes so hard is a start as well."""
    out, before = [], False
    for c in sorted(commands, key=lambda c: c["seq"]):
        acc = _num(c.get("acceleration"))
        hard = acc is not None and acc <= -EMERGENCY_BRAKING_MPS2 + EPS
        if hard and not before:
            out.append(c)
        before = hard
    return out


def _rel(tick: dict) -> tuple:
    rel = tick.get("relative") or {}
    return _num(rel.get("gapM")), _num(rel.get("closingMps"))


def functional_part(ticks: list[dict], st: SettingTerms) -> dict:
    """:204-208, on the world ticks of one run in order.

    End: the first tick with targetContact, or the vehicle at the speed of the target (closing <= 0.05 m/s for a
    stationary target, BENCH READING; <= 0 for a moving one, plan A2). EVALUATOR READING: the end is searched from
    the first tick in the band that closes on the target. Start: the latest tick before the end in the band with a
    time to collision of at least 4 s.
    """
    approach = None
    for i, t in enumerate(ticks):
        speed = _num((t.get("ego") or {}).get("speedMps"))
        _, closing = _rel(t)
        if speed is not None and st.in_band(speed) and closing is not None and closing > 0.0:
            approach = i
            break
    if approach is None:
        return {"met": False, "missed": "no tick in the band that closes on the target"}
    rest = 0.0 if st.moving_target else AT_REST_MPS
    end, reason = None, None
    for i in range(approach, len(ticks)):
        t = ticks[i]
        _, closing = _rel(t)
        if t.get("targetContact") is True:
            end, reason = i, "contact with the target"
            break
        if closing is not None and closing <= rest + EPS:
            end, reason = i, "at the speed of the target"
            break
    if end is None:
        return {"met": False, "missed": "the run ends before contact or the speed of the target"}
    start = None
    for i in range(end, -1, -1):
        speed = _num((ticks[i].get("ego") or {}).get("speedMps"))
        ttc = time_to_collision(*_rel(ticks[i]))
        if speed is not None and st.in_band(speed) and ttc is not None and ttc >= TTC_FUNCTIONAL_MIN_S - EPS:
            start = i
            break
    if start is None:
        return {"met": False, "missed": "no tick in the band with a time to collision of at least 4 s"}
    return {"met": True, "startIndex": start, "endIndex": end, "endReason": reason,
            "startFrame": ticks[start].get("frame"), "endFrame": ticks[end].get("frame"),
            "startSimS": ticks[start]["simTimeS"], "endSimS": ticks[end]["simTimeS"]}


def judged_run(ticks: list[dict], st: SettingTerms) -> dict:
    """:209-219: straight, the center line within 0.2 m of the target's, for at least 2 s before the functional
    part. The window of the dropped-image rule for 036, 037 and 042 is from 2 s before the functional part to its
    end (EVALUATOR READING)."""
    out: dict = {"setting": st.setting_id, "judged": False, "missed": [], "windowS": None}
    if not st.judged:
        out["missed"].append(f"{st.scenario} has no judged run")
        return out
    fp = functional_part(ticks, st)
    out["functionalPart"] = fp
    if not fp["met"]:
        out["missed"].append(f"no functional part: {fp['missed']}")
        return out
    t0 = fp["startSimS"]
    window = [t for t in ticks[: fp["startIndex"] + 1] if t["simTimeS"] >= t0 - STRAIGHT_BEFORE_S - 1e-6]
    if not window or t0 - window[0]["simTimeS"] < STRAIGHT_BEFORE_S - 1e-6:
        out["missed"].append(f"the run holds less than {STRAIGHT_BEFORE_S} s before the functional part")
    offsets = [_num((t.get("relative") or {}).get("centerLineOffsetM")) for t in window]
    headings = [_num((t.get("relative") or {}).get("headingDiffDeg")) for t in window]
    if any(v is None for v in offsets + headings):
        out["missed"].append("a tick before the functional part has no center-line offset or heading")
    offs = [abs(v) for v in offsets if v is not None]
    heads = [abs(v) for v in headings if v is not None]
    if offs and max(offs) > CENTER_LINE_MAX_M + EPS:
        out["missed"].append(f"center line {max(offs):.3f} m from the target's (limit {CENTER_LINE_MAX_M} m)")
    if heads and max(heads) > STRAIGHT_HEADING_MAX_DEG + EPS:
        out["missed"].append(f"heading {max(heads):.3f} deg off the target's (bench reading "
                             f"{STRAIGHT_HEADING_MAX_DEG} deg)")
    out["maxCenterLineOffsetM"] = max(offs) if offs else None
    out["windowS"] = [t0 - STRAIGHT_BEFORE_S, fp["endSimS"]]
    out["judged"] = not out["missed"]
    return out


def relative_speeds(ticks: list[dict], fp: dict) -> dict:
    """:267-270 within the functional part: the closing speed at the first imminent tick, and at the last tick
    before the first contact (EVALUATOR READING: the contact tick's own closing is the rebound)."""
    out: dict = {"approachKmh": None, "firstImminentFrame": None, "impactKmh": 0.0, "contact": False,
                 "contactFrame": None}
    for i in range(fp["startIndex"], fp["endIndex"] + 1):
        gap, closing = _rel(ticks[i])
        if is_imminent(gap, closing):
            out["approachKmh"] = closing * 3.6
            out["firstImminentFrame"] = ticks[i].get("frame")
            break
    end = ticks[fp["endIndex"]]
    if end.get("targetContact") is True:
        out["contact"] = True
        out["contactFrame"] = end.get("frame")
        before = ticks[fp["endIndex"] - 1] if fp["endIndex"] > 0 else end
        _, closing = _rel(before)
        out["impactKmh"] = None if closing is None else max(closing, 0.0) * 3.6
    return out
