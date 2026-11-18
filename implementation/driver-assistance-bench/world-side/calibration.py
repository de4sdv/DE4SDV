"""The calibration runs of ASM-DRIVING-005 and ASM-DRIVING-006: analysis and record format.

Pure Python; ``da_world_side.py`` runs the calibrations on CARLA and calls these functions on their ticks.

Model (PSR = driver_assistance_physical_software_realization.sysml at 1f6ad003):

- ASM-DRIVING-005: "the commanded against the achieved deceleration of the scenario's vehicle on the scenario's
  road", up to a deceleration of 5.0 m/s2 with a jerk of 10.0 m/s3;
- ASM-DRIVING-006: "with the ego vehicle placed to the right of its lane centre, the candidate's commands turn it
  left, by the sign of the yaw rate".

The model states what each run shows, not a tolerance. Every number marked PROPOSAL is this bench's, stated in
the record so that the lead can accept or replace it; the record keeps the measured values beside it.
"""

from __future__ import annotations

import math

RECORD_VERSION = 1
# ASM-DRIVING-005
ACCELERATE_MPS2 = 2.0        # PROPOSAL: how the calibration brings the vehicle to the approach speed
HOLD_S = 2.0                 # PROPOSAL: steady speed before the braking
PASS_CAP_S = 60.0            # PROPOSAL: a pass ends after this long in any case
JERK_MPS3 = 10.0             # MAP-DRIVING-DA-COMMAND
STOP_WINDOW_MPS = 1.0        # PROPOSAL: the fit window ends where the speed falls below this
FOLLOW_TOLERANCE = 0.10      # PROPOSAL: achieved within 10 % of commanded reads as "follows"
# ASM-DRIVING-006
STEER_OFFSET_M = 0.5         # PROPOSAL: the start right of the lane center
STEER_MIN_SPEED_MPS = 2.0    # PROPOSAL: the window starts once the vehicle moves at this speed
STEER_WINDOW_S = 3.0         # PROPOSAL: the window's length
YAW_RATE_MIN_DEG_S = 0.1     # PROPOSAL: a turn is read from a slope of at least this size


def lsq_slope(ts: list[float], ys: list[float]) -> float | None:
    """Least-squares slope of ys over ts; None for fewer than three points."""
    n = len(ts)
    if n < 3:
        return None
    mt, my = sum(ts) / n, sum(ys) / n
    den = sum((t - mt) ** 2 for t in ts)
    if den <= 0.0:
        return None
    return sum((t - mt) * (y - my) for t, y in zip(ts, ys)) / den


def _unwrap_deg(values: list[float]) -> list[float]:
    out: list[float] = []
    for v in values:
        if not out:
            out.append(v)
            continue
        d = (v - out[-1] + 180.0) % 360.0 - 180.0
        out.append(out[-1] + d)
    return out


# --------------------------------------------------------------- ASM-DRIVING-005


def analyse_decel(pass_: dict) -> dict:
    """One braking pass: ``samples`` with t (s), speed (m/s), accel (m/s2, longitudinal), commanded, phase."""
    samples = [s for s in pass_["samples"] if s.get("t") is not None and s.get("speed") is not None]
    commanded = float(pass_["commandedDecelMps2"])
    out = {"approachKmh": pass_["approachKmh"], "commandedDecelMps2": commanded, "samples": len(samples)}
    onset = next((i for i, s in enumerate(samples) if s["phase"] == "brake"), None)
    if onset is None:
        out.update(achievedDecelMps2=None, missed="the pass never reached its braking phase")
        return out
    t0 = samples[onset]["t"]
    out["speedAtOnsetKmh"] = round(samples[onset]["speed"] * 3.6, 3)
    ramp_s = commanded / JERK_MPS3
    window = []
    for s in samples[onset:]:
        if s["speed"] < STOP_WINDOW_MPS:
            break
        if s["t"] >= t0 + ramp_s + 0.2 - 1e-9:
            window.append(s)
    slope = lsq_slope([s["t"] for s in window], [s["speed"] for s in window])
    achieved = None if slope is None else -slope
    braking = samples[onset:]
    smoothed = []
    for i in range(len(braking)):
        part = [b["accel"] for b in braking[max(0, i - 2): i + 3] if b.get("accel") is not None]
        smoothed.append((braking[i]["t"], -sum(part) / len(part) if part else None))
    reach = next((t - t0 for t, a in smoothed if a is not None and a >= 0.9 * commanded), None)
    stopped = next((s["t"] - t0 for s in braking if s["speed"] <= 0.1), None)
    out.update({
        "fitWindowS": None if not window else [round(window[0]["t"] - t0, 3), round(window[-1]["t"] - t0, 3)],
        "fitPoints": len(window),
        "achievedDecelMps2": None if achieved is None else round(achieved, 4),
        "achievedOverCommanded": None if achieved is None or commanded == 0 else round(achieved / commanded, 4),
        "peakDecelMps2": None if not smoothed else round(max(a for _, a in smoothed if a is not None), 4)
        if any(a is not None for _, a in smoothed) else None,
        "timeTo90PercentS": None if reach is None else round(reach, 3),
        "rampAtJerkS": round(ramp_s, 3),
        "timeToStopS": None if stopped is None else round(stopped, 3),
    })
    if achieved is None:
        out["missed"] = "fewer than three samples in the fit window"
        out["followsWithinProposal"] = None
    else:
        out["followsWithinProposal"] = abs(achieved - commanded) <= FOLLOW_TOLERANCE * commanded
    return out


def decel_record(passes: list[dict], context: dict) -> dict:
    analysed = [p for p in passes if p.get("achievedDecelMps2") is not None]
    return {
        "recordVersion": RECORD_VERSION, "assumption": "ASM-DRIVING-005", "kind": "calibration",
        "notARunOfASetting": True, "context": context, "passes": passes,
        "proposal": {"accelerateMps2": ACCELERATE_MPS2, "holdS": HOLD_S, "stopWindowMps": STOP_WINDOW_MPS,
                     "followTolerance": FOLLOW_TOLERANCE,
                     "fitWindow": "from the braking onset plus the ramp at the jerk plus 0.2 s, to the speed "
                                  f"falling below {STOP_WINDOW_MPS} m/s; least-squares slope of the speed"},
        "summary": {"passes": len(passes), "analysed": len(analysed),
                    "allFollowWithinProposal": bool(analysed) and len(analysed) == len(passes)
                    and all(p["followsWithinProposal"] for p in analysed),
                    "worstRatio": None if not analysed else min(p["achievedOverCommanded"] for p in analysed)},
    }


# --------------------------------------------------------------- ASM-DRIVING-006


def analyse_steering(ticks: list[dict], start_offset_m: float) -> dict:
    """From the world ticks of a calib-steer run. CARLA's yaw is clockwise seen from above (its y axis points
    to the right), so a left turn is a falling yaw; the lane offset is positive to the right."""
    rows = []
    for t in ticks:
        ego = t.get("ego") or {}
        lane = ego.get("lane") or {}
        if t.get("scenarioTimeS") is None or ego.get("speedMps") is None or ego.get("yawDegCarla") is None:
            continue
        rows.append((t["scenarioTimeS"], ego["speedMps"], ego["yawDegCarla"], lane.get("offsetM"),
                     (t.get("control") or {}).get("steer")))
    out = {"startOffsetM": start_offset_m, "ticks": len(rows),
           "proposal": {"minSpeedMps": STEER_MIN_SPEED_MPS, "windowS": STEER_WINDOW_S,
                        "yawRateMinDegS": YAW_RATE_MIN_DEG_S}}
    first = next((i for i, r in enumerate(rows) if r[1] >= STEER_MIN_SPEED_MPS), None)
    if first is None:
        out.update(shown=None, missed=f"the vehicle never reached {STEER_MIN_SPEED_MPS} m/s")
        return out
    t0 = rows[first][0]
    window = [r for r in rows[first:] if r[0] <= t0 + STEER_WINDOW_S + 1e-9]
    yaws = _unwrap_deg([r[2] for r in window])
    slope = lsq_slope([r[0] for r in window], yaws)
    offsets = [r[3] for r in window if r[3] is not None]
    steers = [r[4] for r in window if r[4] is not None]
    turn = None
    if slope is not None and abs(slope) >= YAW_RATE_MIN_DEG_S:
        turn = "left" if slope < 0 else "right"
    out.update({
        "windowS": [round(t0, 3), round(window[-1][0], 3)],
        "yawRateDegSCarla": None if slope is None else round(slope, 4),
        "yawRateMethod": "least-squares slope of CARLA's unwrapped yaw over the window",
        "turn": turn,
        "offsetAtStartM": None if not offsets else round(offsets[0], 4),
        "offsetAtEndM": None if not offsets else round(offsets[-1], 4),
        "meanAppliedSteer": None if not steers else round(sum(steers) / len(steers), 5),
        "appliedSteerSign": "CARLA's VehicleControl.steer, positive right",
    })
    if start_offset_m <= 0.0:
        out.update(shown=None, missed="the start was not right of the lane center")
    elif turn is None:
        out.update(shown=None, missed="no turn above the proposal's yaw rate in the window")
    else:
        out["shown"] = turn == "left"
    return out


def steering_record(analysis: dict, setting_record: dict) -> dict:
    return {"recordVersion": RECORD_VERSION, "assumption": "ASM-DRIVING-006", "kind": "calibration",
            "notARunOfASetting": True, "controlOfTheHero": "the candidate through the actuation adapter",
            "setting": setting_record, "analysis": analysis}
