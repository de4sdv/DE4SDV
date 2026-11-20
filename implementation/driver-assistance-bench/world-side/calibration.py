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

import json
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
        # the hero's Ackermann gains (DA_ACKERMANN_GAINS): requested, applied and read back per pass's hero
        "ackermannGains": context.get("ackermannGains"),
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


def last_command(commands: list[dict] | None) -> dict | None:
    """The candidate's last driving command of a record: the newest CARLA frame of the commands that carry one,
    else the newest ``issueTime_sim_s``. ``commands`` are the S-CORE side's ``out.driving_command`` records (or
    any record with ``frame`` or ``issueTime_sim_s``); None when there is no command record at all."""
    if commands is None:
        return None
    frames = [int(c["frame"]) for c in commands if c.get("frame") is not None]
    if frames:
        return {"frame": max(frames), "simTimeS": None, "commands": len(commands)}
    times = [float(c["issueTime_sim_s"]) for c in commands if c.get("issueTime_sim_s") is not None]
    return {"frame": None, "simTimeS": max(times) if times else None, "commands": len(commands)}


def _windows(rows: list[tuple], t_from: float, t_to: float):
    """The windows of STEER_WINDOW_S, sliding one tick at a time from ``t_from``, inside [t_from, t_to] (the
    first one shorter where the range is): (window rows, yaw slope) each."""
    starts = [i for i, r in enumerate(rows) if t_from - 1e-9 <= r[0] <= t_to + 1e-9]
    for k, i in enumerate(starts):
        if k and rows[i][0] + STEER_WINDOW_S > t_to + 1e-9:
            return
        window = [r for r in rows[i:] if r[0] <= min(rows[i][0] + STEER_WINDOW_S, t_to) + 1e-9]
        yield window, lsq_slope([r[0] for r in window], _unwrap_deg([r[2] for r in window]))


def _first_window_with_a_turn(rows: list[tuple], t_from: float, t_to: float):
    """The first window whose yaw slope reaches the proposal's rate, else the first window; and the window of the
    steepest slope (reported beside it). Returns (window rows, slope, steepest (rows, slope))."""
    first = chosen = steepest = None
    for window, slope in _windows(rows, t_from, t_to):
        first = first or (window, slope)
        if slope is not None and (steepest is None or steepest[1] is None or abs(slope) > abs(steepest[1])):
            steepest = (window, slope)
        if chosen is None and slope is not None and abs(slope) >= YAW_RATE_MIN_DEG_S:
            chosen = (window, slope)
    chosen = chosen or first or ([], None)
    return chosen[0], chosen[1], steepest or ([], None)


def analyse_steering(ticks: list[dict], start_offset_m: float, *, settled_mps: float,
                     commands: list[dict] | None = None) -> dict:
    """From the world ticks of a calib-steer run. CARLA's yaw is clockwise seen from above (its y axis points
    to the right), so a left turn is a falling yaw; the lane offset is positive to the right.

    The judgement (fix of the attempt-3 diagnosis, DIAGNOSIS.md:43-57 and :252-258):

    - it starts at the first tick at the setting's speed (``settled_mps``, the band's low end), not while the
      vehicle still accelerates;
    - it ends at the candidate's last command (``commands``: the S-CORE side's ``out.driving_command``
      records); every tick after it is cut, since the world then holds the last applied control. Without a
      command record (None) the world record is judged to its end and the result is marked provisional;
    - the turn is the sign of the yaw rate (ASM-DRIVING-006) in the first window of STEER_WINDOW_S, from the
      settled tick on and before the lane centre is first reached, whose slope reaches YAW_RATE_MIN_DEG_S;
    - the offset trend is reported beside it: the offset at the settled tick, the minimum |offset| and the
      first tick at or across the lane centre."""
    rows = []
    for t in ticks:
        ego = t.get("ego") or {}
        lane = ego.get("lane") or {}
        if t.get("scenarioTimeS") is None or ego.get("speedMps") is None or ego.get("yawDegCarla") is None:
            continue
        rows.append((t["scenarioTimeS"], ego["speedMps"], ego["yawDegCarla"], lane.get("offsetM"),
                     (t.get("control") or {}).get("steer"), t.get("frame"), t.get("simTimeS")))
    out: dict = {"startOffsetM": start_offset_m, "ticks": len(rows),
                 "proposal": {"settledMps": round(settled_mps, 4), "windowS": STEER_WINDOW_S,
                              "yawRateMinDegS": YAW_RATE_MIN_DEG_S,
                              "window": "the first window, sliding from the first tick at the setting's speed to "
                                        "the first tick at or across the lane centre, whose yaw slope reaches "
                                        "the rate"},
                 "windowS": None, "turn": None, "settledAtS": None, "judgedToS": None}
    last = last_command(commands)
    out["provisional"] = last is None
    if last is None:
        out["cut"] = {"lastCommandFrame": None, "lastCommandS": None, "ticksCut": 0, "commands": None,
                      "reason": "no command record given: judged to the end of the world record (provisional)"}
    else:
        if last["frame"] is not None:
            kept = [r for r in rows if r[5] is not None and r[5] <= last["frame"]]
            at = next((r[0] for r in rows if r[5] == last["frame"]), kept[-1][0] if kept else None)
        else:
            kept = [r for r in rows if last["simTimeS"] is not None and r[6] is not None
                    and r[6] <= last["simTimeS"] + 1e-9]
            at = kept[-1][0] if kept else None
        out["cut"] = {"lastCommandFrame": last["frame"], "lastCommandS": at, "ticksCut": len(rows) - len(kept),
                      "commands": last["commands"],
                      "reason": "the candidate's last command: the world holds the last applied control after it"}
        rows = kept
        if not rows:                         # an empty command record keeps no tick
            out.update(shown=None, missed="no command in the record: nothing the candidate commanded to judge")
            return out
    out["judgedToS"] = rows[-1][0] if rows else None
    first = next((i for i, r in enumerate(rows) if r[1] >= settled_mps - 1e-9), None)
    if first is None:
        out.update(shown=None, missed=f"the vehicle never reached the setting's speed, {settled_mps:.3f} m/s, "
                                      "before the last command")
        return out
    t0 = rows[first][0]
    out["settledAtS"] = round(t0, 3)
    judged = rows[first:]
    offsets = [(r[0], r[3]) for r in judged if r[3] is not None]
    start = offsets[0][1] if offsets else None
    crossing = None
    if start is not None and start > 0.0:
        crossing = next((t for t, o in offsets if o <= 0.0), None)
    least = min(offsets, key=lambda p: abs(p[1])) if offsets else None
    out["offsetTrend"] = {
        "startM": None if start is None else round(start, 4),
        "minAbsM": None if least is None else round(abs(least[1]), 4),
        "minAbsAtS": None if least is None else round(least[0], 3),
        "firstZeroCrossingS": None if crossing is None else round(crossing, 3),
        "endM": None if not offsets else round(offsets[-1][1], 4),
        "endS": None if not offsets else round(offsets[-1][0], 3),
    }
    t_to = crossing if crossing is not None else judged[-1][0]
    window, slope, steepest = _first_window_with_a_turn(judged, t0, t_to)
    steers = [r[4] for r in window if r[4] is not None]
    turn = None
    if slope is not None and abs(slope) >= YAW_RATE_MIN_DEG_S:
        turn = "left" if slope < 0 else "right"
    w_offsets = [r[3] for r in window if r[3] is not None]
    out.update({
        "windowS": None if not window else [round(window[0][0], 3), round(window[-1][0], 3)],
        "yawRateDegSCarla": None if slope is None else round(slope, 4),
        "yawRateMethod": "least-squares slope of CARLA's unwrapped yaw over the window",
        "steepestWindow": {"windowS": None if not steepest[0] else [round(steepest[0][0][0], 3),
                                                                    round(steepest[0][-1][0], 3)],
                           "yawRateDegSCarla": None if steepest[1] is None else round(steepest[1], 4)},
        "turn": turn,
        "offsetAtStartM": None if not w_offsets else round(w_offsets[0], 4),
        "offsetAtEndM": None if not w_offsets else round(w_offsets[-1], 4),
        "meanAppliedSteer": None if not steers else round(sum(steers) / len(steers), 5),
        "appliedSteerSign": "CARLA's VehicleControl.steer, positive right",
    })
    if start_offset_m <= 0.0:
        out.update(shown=None, missed="the start was not right of the lane center")
    elif start is not None and start <= 0.0:
        out.update(shown=None, missed="the vehicle was at or left of the lane centre when it reached the setting's "
                                      "speed")
    elif turn is None:
        out.update(shown=None, missed="no turn above the proposal's yaw rate from the setting's speed to the lane "
                                      "centre or the last command")
    else:
        out["shown"] = turn == "left"
    return out


def steering_record(analysis: dict, setting_record: dict) -> dict:
    return {"recordVersion": RECORD_VERSION, "assumption": "ASM-DRIVING-006", "kind": "calibration",
            "notARunOfASetting": True, "controlOfTheHero": "the candidate through the actuation adapter",
            "setting": setting_record, "ackermannGains": setting_record.get("ackermannGains"),
            "analysis": analysis}


# --------------------------------------------------------------- re-judging a fetched record


def _jsonl(path) -> list[dict]:
    out = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                out.append(json.loads(line))
    return out


def main(argv: list[str] | None = None) -> int:
    """``calibration.py steer --world world.jsonl --score score_interface.jsonl --setting-low-kmh 20 --out F``:
    judges a fetched calib-steer record with the candidate's commands (the S-CORE side's record), which the world
    side does not have during the run."""
    import argparse

    p = argparse.ArgumentParser(description=main.__doc__)
    p.add_argument("what", choices=["steer"])
    p.add_argument("--world", required=True, help="the run's simulator/world.jsonl")
    p.add_argument("--score", default=None, help="score_side/run/score/score_interface.jsonl; none: provisional")
    p.add_argument("--setting-low-kmh", type=float, required=True, help="the setting's band, low end (km/h)")
    p.add_argument("--start-offset-m", type=float, default=STEER_OFFSET_M)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    ticks = [r["data"] for r in _jsonl(a.world) if r.get("event") == "tick"]
    commands = None
    if a.score:
        commands = [r for r in _jsonl(a.score) if r.get("kind") == "out.driving_command"]
    analysis = analyse_steering(ticks, a.start_offset_m, settled_mps=a.setting_low_kmh / 3.6, commands=commands)
    record = steering_record(analysis, {"world": str(a.world), "score": a.score, "settingLowKmh": a.setting_low_kmh})
    with open(a.out, "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=1, allow_nan=False)
    print(json.dumps({"shown": analysis.get("shown"), "turn": analysis.get("turn"),
                      "windowS": analysis.get("windowS"), "offsetTrend": analysis.get("offsetTrend"),
                      "cut": analysis.get("cut"), "missed": analysis.get("missed")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
