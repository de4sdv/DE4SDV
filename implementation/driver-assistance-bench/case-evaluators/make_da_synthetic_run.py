"""Synthetic S1 session trees for the tests of the case evaluators.

Writes the records of one or more runs in the layout and the line format of the fetched attempt-3 records
(`sessions/incoming_20261120T092051Z/`): `world_<run>/simulator/world.jsonl` with `tick` lines,
`score_<run>/score_side/run/score/{score_interface,actuationAdapter,identityRecorder}.jsonl`,
`capture_<run>/app_record_warning.jsonl`, `ivi_clock_<run>/clock.jsonl` and `session.json`. Field names and key
order follow the real lines (OBSERVABLES.md). Where a producer is pinned (lead contracts of 2026-11-20), the names are
its own: the site record of 014 and 015 is `SiteSpec.as_record()` (world-side/sites.py at b9938fe9), the stop run is run
`stop` of setting `stop` (world-side/scenarios.py STOP_RUN at db6bf573), and the stop instant is session.json
`s1.stop_instant` and `s1.path_stop` as session/da_session.sh writes them (a0bd4bd7). The run labels are the s1 run
list's (`012_20_r1`, ..., `stop`).

The world is a point-mass model on a straight lane: the ego approaches a target at its setting's speed, the
candidate issues one command per two ticks (10 Hz) from the true gap and closing speed, and the ego's acceleration
follows the command after `lag_ticks`. A policy sets when the candidate warns and brakes; options plant the defects
that the fail and inconclusive fixtures need.
"""

from __future__ import annotations

import json
import math
import zlib
from dataclasses import dataclass, field
from pathlib import Path

STEP_S = 0.05
KMH = 1.0 / 3.6
EGO_HALF_LENGTH_M = 2.44
TARGET_HALF_LENGTH_M = 2.4

SETTING_SPEEDS = {  # (ego km/h inside the band, target km/h)
    "SC-DRIVING-012@20": (21.0, 0.0), "SC-DRIVING-012@42": (41.0, 0.0), "SC-DRIVING-012@60": (59.0, 0.0),
    "SC-DRIVING-013@30": (31.0, 19.0), "SC-DRIVING-013@60": (59.0, 19.0),
    "SC-DRIVING-014@30": (29.0, 0.0), "SC-DRIVING-015@40": (39.0, 39.0),
}
S1_SETTINGS = list(SETTING_SPEEDS)
STOP = "stop"                              # world-side/scenarios.py STOP_RUN: the stop run's setting and run id
SETTING_SPEEDS[STOP] = (21.0, 0.0)         # SC-DRIVING-012@20's (scenarios.py: _setting(STOP_RUN, 20.0, ...))
# The guidance of world-side/sites.py (b9938fe9) GUIDANCE_014 and GUIDANCE_015, verbatim
GUIDANCE_014 = {"source": "UN R152 annex, guidance of the curved road with guard pipes (R152:1744-1756)",
                "approachKmh": [28.0, 30.0], "atCurveEntryMinKmh": 22.0, "ttcAtTurnInMaxS": 1.6,
                "inCurveMinKmh": 21.0, "ttcAtOverlapZeroMaxS": 1.1,
                "curveRadiusMaxM": 25.0, "radiusMeasuredAt": "the outer side of the road"}
GUIDANCE_015 = {"source": "UN R152 annex, guidance of the forward vehicle turning off (R152:1705-1716)",
                "bothKmh": [38.0, 40.0], "targetTurnKmh": [8.0, 10.0], "egoAtTurnBeginMinKmh": 26.0,
                "ttcAtTurnBeginMaxS": 4.7, "egoAfterMinKmh": 20.0, "ttcAtOverlapZeroMaxS": 2.5}


def _line(obj: dict) -> str:
    return json.dumps(obj, separators=(",", ":"))


def warning_bytes(requested: bool, issue_time_sim_s: float) -> str:
    """The 8 bytes of the warning request as S records them (payloads.h:91-94), hex."""
    return f"{int(bool(requested)):08x}{int(round(issue_time_sim_s * 1000.0)):08x}"


@dataclass
class RunSpec:
    run_id: str
    setting_id: str
    kind: str = "run"                       # "run", or "stop" for the stop run (its setting record says "run")
    sim_base_s: float = 600.0               # session sim time at the first tick
    mono_base_ns: int = 1_000_000_000_000
    real_base_ns: int = 1_795_168_000_000_000_000
    start_ttc_s: float = 9.0                # the start gap, as a time to collision at the setting's speed
    lag_ticks: int = 2                      # the ego's acceleration follows the command after this many ticks
    warn_at_needed: float | None = 1.0      # the candidate starts warning at this needed deceleration (TTC <= 4)
    eb_at_needed: float | None = 4.0        # ... and brakes at eb_accel from this needed deceleration
    eb_accel: float = -9.0
    brake_accel: float = -3.0               # a command used by brake_window (not an emergency braking)
    brake_window_s: tuple | None = None     # (from, to) scenario s: command brake_accel, regardless of the gap
    false_warning_at_s: float | None = None  # a warning start at this scenario time, whatever the gap
    false_eb_at_s: float | None = None       # an emergency braking start (one command of eb_accel) at this time
    after_end_s: float = 1.0                # ticks written after the end of the approach
    run_cap_s: float = 40.0
    center_offset_m: float = 0.0            # the ego's center-line offset from the target's
    drops_at_s: list = field(default_factory=list)   # scenario times of dropped camera images
    vehicles_ahead: bool = True             # write data.vehiclesAhead (shared contract 1)
    target_in_lane: bool = True             # vehiclesAhead[].inLane of the target
    guidance: dict | None = None            # setting_record.json site.guidance (014/015); {} when None
    site_id: str | None = None              # setting_record.json site.siteId: a site record is written when set
    warn_lead_s: float | None = None        # one warning start this long before the first emergency braking start
    control_of_the_hero: bool = True        # setting_record.json controlOfTheHero
    world_side_control_calls: int = 0
    unmatched_ackermann: bool = False       # an out.ackermann_control with no command of its seq in S
    foreign_control_source: bool = False    # the actuation of command seq 3 names another control source
    bad_crc_at_adapter: bool = False        # the adapter's checkValue of one command differs from S's crc
    record_after_first_command: bool = False
    record_accepted: bool = True
    diff_bytes: int = 111751
    forged_receipt: bool = False            # a receipt that matches no S warning request
    stop_after_s: float | None = None       # stop run: the path stop at this scenario time
    commands_after_stop: bool = False       # stop run: the adapter applies a control after the stop
    receipt_after_stop: bool = False        # stop run: a receipt after the stop
    late_receipt_after_stop: bool = False   # stop run: a request issued before the stop, read 0.5 s after it
    world_control_change_after_stop: bool = False  # stop run: the world's control changes with no adapter output
    # The simulator's Ackermann controller regulates toward the held target on every physics step, so the control
    # that world.jsonl records (hero.get_control()) changes on ticks that no command reaches, as on the real server
    # (closure review of 44a4be29..86cadee0, R1: attempt 3's run1, 321 of 351 command-free ticks changed it)
    regulates: bool = True
    world_side_control_call_after_stop: bool = False  # stop run: the world side applies a control after the stop
    tick_without_control_calls_after_stop: bool = False  # stop run: a tick after the stop lacks worldSideControlCalls
    no_score: bool = False
    no_world: bool = False
    broken_world_line: bool = False


def simulate(spec: RunSpec) -> dict:
    """Ticks, commands and warnings of one run, from the point-mass model."""
    ego_kmh, target_kmh = SETTING_SPEEDS[spec.setting_id]
    v_e, v_t = ego_kmh * KMH, target_kmh * KMH
    closing0 = v_e - v_t
    gap = spec.start_ttc_s * closing0 if closing0 > 0.5 else 30.0
    x_e = 0.0
    x_t = x_e + EGO_HALF_LENGTH_M + gap + TARGET_HALF_LENGTH_M
    cmd_hist: list[float] = []           # the command in force at each tick (by issue)
    ticks, commands, warnings = [], [], []
    current_cmd, warning_on, eb_on = 0.0, False, False
    end_k, contact_done, approached = None, False, False
    stop_k = None if spec.stop_after_s is None else int(round(spec.stop_after_s / STEP_S))
    n_max = int(spec.run_cap_s / STEP_S)
    seq, held = 0, 0.0
    for k in range(n_max + 1):
        t = k * STEP_S
        gap = (x_t - TARGET_HALF_LENGTH_M) - (x_e + EGO_HALF_LENGTH_M)
        closing = v_e - v_t
        contact = (not contact_done) and gap <= 0.0
        rel_closing = closing
        if contact:
            contact_done = True
            rel_closing = -0.8 * closing        # the rebound the real contact tick shows
            v_e = v_t
        ttc = gap / closing if closing > 0 and gap > 0 else None
        needed = (closing * closing / (2 * gap)) if closing > 0 and gap > 0 else None
        applied = cmd_hist[-spec.lag_ticks] if len(cmd_hist) >= spec.lag_ticks > 0 else 0.0
        if stop_k is not None and k > stop_k and not spec.commands_after_stop:
            applied = held
        held = applied
        tick = {"frame": 1000 + k, "phase": "run", "simTimeS": spec.sim_base_s + t, "scenarioTimeS": round(t, 6),
                "ego": {"x": x_e, "y": 0.0, "z": 0.0, "yawDegCarla": 0.0, "speedMps": v_e,
                        "longAccelMps2": applied,
                        "yawRateDegSCarla": 0.0, "lane": {"road": 40, "lane": -7, "offsetM": spec.center_offset_m}},
                "control": {"throttle": max(applied, 0.0) / 3.0, "steer": 0.0, "brake": max(-applied, 0.0) / 9.0,
                            "handBrake": False},
                "worldSideControlCalls": spec.world_side_control_calls if k == 5 else 0,
                "collisions": [{"type": "collision", "frame": 1000 + k, "other_actor_id": 156,
                                "other_actor": "vehicle.tesla.model3"}] if contact else [],
                "laneInvasions": [], "tickDurationS": 0.002, "latenessS": 0.0,
                "target": {"x": x_t, "y": 0.0, "yawDegCarla": 0.0, "speedMps": v_t},
                "relative": {"gapM": gap, "closingMps": rel_closing, "centerLineOffsetM": spec.center_offset_m,
                             "headingDiffDeg": 0.0, "ttcS": ttc, "neededDecelMps2": needed},
                "targetContact": contact}
        if spec.vehicles_ahead:
            tick["vehiclesAhead"] = [{"actorId": 156, "role": "target", "gapM": gap, "closingMps": rel_closing,
                                      "ttcS": ttc, "neededDecelMps2": needed, "inLane": spec.target_in_lane,
                                      "overlapRatio": 1.0 if spec.target_in_lane else 0.0}]
        # The candidate: one command per two ticks, from this tick's truth (10 Hz, as the real passes).
        if k % 2 == 0 and end_k is None or (k % 2 == 0 and spec.kind == "stop"):
            seq += 1
            new_cmd = 0.0
            if spec.eb_at_needed is not None and (eb_on or (needed is not None and needed >= spec.eb_at_needed)):
                eb_on = True
                new_cmd = spec.eb_accel if closing > 0 else 0.0
            if spec.brake_window_s and spec.brake_window_s[0] <= t <= spec.brake_window_s[1]:
                new_cmd = spec.brake_accel
            if spec.false_eb_at_s is not None and abs(t - spec.false_eb_at_s) < STEP_S:
                new_cmd = spec.eb_accel
            if spec.warn_at_needed is not None and needed is not None and ttc is not None and ttc <= 4.0 \
                    and needed >= spec.warn_at_needed:
                warning_on = True
            if spec.false_warning_at_s is not None and abs(t - spec.false_warning_at_s) < STEP_S:
                warning_on = True
            current_cmd = new_cmd
            commands.append({"seq": seq, "k": k, "acceleration": new_cmd})
            warnings.append({"k": k, "requested": warning_on})
        cmd_hist.append(current_cmd)
        if spec.regulates:
            tick["control"]["throttle"] = round(tick["control"]["throttle"] + 0.004 * (1 + k % 3), 6)
        if spec.world_control_change_after_stop and stop_k is not None and k > stop_k + 10:
            tick["control"] = dict(tick["control"], throttle=0.3)
        if spec.world_side_control_call_after_stop and stop_k is not None and k > stop_k + 5:
            tick["worldSideControlCalls"] = 1      # the counter of the world side's calls (da_world_side.py:1302)
        if spec.tick_without_control_calls_after_stop and stop_k is not None and k == stop_k + 6:
            del tick["worldSideControlCalls"]
        ticks.append(tick)
        # Advance the world by one tick.
        if not contact_done:
            v_e = max(v_e + applied * STEP_S, 0.0)
        x_e += v_e * STEP_S
        x_t += v_t * STEP_S
        approached = approached or closing > 0.5
        if end_k is None and (contact or (approached and v_e - v_t <= (0.05 if v_t == 0 else 0.0))):
            end_k = k
        if spec.kind != "stop" and end_k is not None and k >= end_k + int(spec.after_end_s / STEP_S):
            break
    return {"ticks": ticks, "commands": commands, "warnings": warnings, "stop_k": stop_k}


def write_run(root: Path, spec: RunSpec) -> dict:
    sim = simulate(spec)
    ticks = sim["ticks"]
    by_k = {i: t for i, t in enumerate(ticks)}

    def mono(k: int, extra_ms: float = 0.0) -> int:
        return spec.mono_base_ns + int((k * STEP_S + extra_ms / 1000.0) * 1e9)

    def real(k: int, extra_ms: float = 0.0) -> int:
        return spec.real_base_ns + int((k * STEP_S + extra_ms / 1000.0) * 1e9)

    if not spec.no_world:
        wdir = root / "sim-lead-fetch" / "x" / "out" / f"world_{spec.run_id}" / "simulator"
        wdir.mkdir(parents=True, exist_ok=True)
        with open(wdir / "world.jsonl", "w") as fh:
            for i, t in enumerate(ticks):
                fh.write(_line({"t_mono_ns": 5_000_000_000 + i, "t_real_ns": real(i), "host": "simulator",
                                "component": "worldSide", "event": "tick", "seq": i + 1, "data": t}) + "\n")
            if spec.broken_world_line:
                fh.write('{"t_mono_ns": 1, "event": "tick", "data": {\n')
        scenario = "SC-DRIVING-012" if spec.setting_id == STOP else spec.setting_id.split("@")[0]
        # da_world_side.py cmd_run (db6bf573) writes kind "run" for every run of run_scenario.sh, the stop run too
        setting_record = {"kind": "run", "setting": {"setting_id": spec.setting_id, "scenario": scenario},
                          "map": "Carla/Maps/Town06_Opt",
                          "simulator": {"versions": {"client": "1.0-14ac3b1a5", "server": "1.0-14ac3b1a5"},
                                        "stepS": STEP_S, "synchronous": True}}
        if spec.control_of_the_hero:
            setting_record["controlOfTheHero"] = ("the actuation adapter only; this process applies no control to "
                                                  "the hero, no autopilot and no Traffic Manager")
        if spec.site_id is not None:   # SiteSpec.as_record() (world-side/sites.py:625-630 at b9938fe9)
            setting_record["site"] = {"siteId": spec.site_id, "map": "Town06_Opt", "xodrSha256": "a90b6131" * 8,
                                      "start": "10:-5:0.0", "startPose": {}, "target": {}, "targetScript": [],
                                      "targetPathPoints": 0, "props": [], "geometry": {},
                                      "guidance": dict(spec.guidance or {}), "checks": {}, "alternatives": [],
                                      "benchReadings": {}, "egoPathPoints": 0}
        (wdir / "setting_record.json").write_text(json.dumps(setting_record, indent=1))
        (wdir / "summary.json").write_text(json.dumps({"kind": "run", "setting": spec.setting_id,
                                                       "worldSideControlCallsOnTheHero": 0}))

    stop_mono = None if sim["stop_k"] is None else mono(sim["stop_k"], 10.0)
    stop_real = None if sim["stop_k"] is None else real(sim["stop_k"], 10.0)
    if not spec.no_score:
        sdir = root / "score" / "fetch" / "x" / "out" / f"score_{spec.run_id}" / "score_side" / "run" / "score"
        sdir.mkdir(parents=True, exist_ok=True)
        s_lines, a_lines = [_line({"kind": "start", "mono_ns": mono(0), "real_ns": real(0)})], []
        drop_ks = {int(round(d / STEP_S)) for d in spec.drops_at_s}
        first_cmd_k = sim["commands"][0]["k"] if sim["commands"] else 0
        record_k = first_cmd_k + (2 if spec.record_after_first_command else 0)
        record_extra = 20.0 if spec.record_after_first_command else -5.0
        record_line = _line({"kind": "in.candidate_record", "accepted": spec.record_accepted,
                             "recordSha256": "5ff680b0" * 8,
                             "upstreamRevision": "014e0e7a56ee8e597c2cab8175233f74edd9b856",
                             "diffBytes": spec.diff_bytes, "mono_ns": mono(record_k, record_extra),
                             "real_ns": real(record_k, record_extra)})
        if not spec.record_after_first_command:
            s_lines.append(record_line)
        a_seq = 0
        for k in sorted({c["k"] for c in sim["commands"]} | drop_ks):
            tk = by_k.get(k)
            if tk is None:
                continue
            kind = "drop.camera_image" if k in drop_ks else "in.camera_image"
            s_lines.append(_line({"kind": "in.camera_image", "frame": tk["frame"], "sim_s": tk["simTimeS"],
                                  "mono_ns": mono(k, 1.0)}))
            if kind == "drop.camera_image":
                s_lines.append(_line({"kind": "drop.camera_image", "frame": tk["frame"], "sim_s": tk["simTimeS"],
                                      "mono_ns": mono(k, 2.0)}))
        for c, w in zip(sim["commands"], sim["warnings"]):
            k = c["k"]
            tk = by_k[k]
            crc = zlib.crc32(f"{c['seq']}:{c['acceleration']}".encode())
            s_lines.append(_line({"kind": "out.driving_command", "seq": c["seq"], "crc": f"0x{crc:08x}",
                                  "issueTime_sim_s": tk["simTimeS"], "frame": tk["frame"],
                                  "acceleration": c["acceleration"], "steeringAngle_deg": 0, "sent": True,
                                  "mono_ns": mono(k, 30.0), "real_ns": real(k, 30.0)}))
            if spec.record_after_first_command and c["seq"] == 1:
                s_lines.append(record_line)
            s_lines.append(_line({"kind": "out.warning_request", "requested": w["requested"],
                                  "issueTime_sim_s": tk["simTimeS"], "frame": tk["frame"],
                                  "bytes": warning_bytes(w["requested"], tk["simTimeS"]), "sent": True,
                                  "mono_ns": mono(k, 31.0), "real_ns": real(k, 31.0)}))
            after_stop = stop_mono is not None and mono(k, 40.0) > stop_mono
            if after_stop and not spec.commands_after_stop:
                continue
            a_seq += 1
            check = crc ^ 1 if (spec.bad_crc_at_adapter and c["seq"] == 3) else crc
            a_lines.append(_line({"t_mono_ns": mono(k, 35.0), "t_real_ns": real(k, 35.0), "host": "score",
                                  "component": "actuationAdapter", "event": "in.driving_command", "seq": a_seq,
                                  "data": {"seq": c["seq"], "crc_ok": True, "issueTime_sim_s": tk["simTimeS"],
                                           "verdict": "accepted", "acceleration": c["acceleration"],
                                           "steeringAngle": 0, "checkValue": check}}))
            a_seq += 1
            nxt = by_k.get(k + 1, tk)
            a_lines.append(_line({"t_mono_ns": mono(k, 40.0), "t_real_ns": real(k, 40.0), "host": "score",
                                  "component": "actuationAdapter", "event": "out.ackermann_control", "seq": a_seq,
                                  "data": {"frame": nxt["frame"], "t_sim_s": nxt["simTimeS"], "seq": c["seq"],
                                           "steer": 0, "acceleration": c["acceleration"],
                                           "controlSource": "replay" if (spec.foreign_control_source
                                                                         and c["seq"] == 3)
                                           else "actuationAdapter"}}))
        if spec.unmatched_ackermann:
            a_seq += 1
            k = sim["commands"][len(sim["commands"]) // 2]["k"]
            a_lines.append(_line({"t_mono_ns": mono(k, 45.0), "t_real_ns": real(k, 45.0), "host": "score",
                                  "component": "actuationAdapter", "event": "out.ackermann_control", "seq": a_seq,
                                  "data": {"frame": by_k[k]["frame"], "t_sim_s": by_k[k]["simTimeS"], "seq": 99999,
                                           "steer": 0, "acceleration": 0.5, "controlSource": "replay"}}))
        if spec.warn_lead_s is not None:
            eb = next(c for c in sim["commands"] if c["acceleration"] <= -5.0)
            t_w = by_k[eb["k"]]["simTimeS"] - spec.warn_lead_s
            kw = max(i for i, t in by_k.items() if t["simTimeS"] <= t_w + 1e-9)
            s_lines.append(_line({"kind": "out.warning_request", "requested": True, "issueTime_sim_s": t_w,
                                  "frame": by_k[kw]["frame"], "bytes": warning_bytes(True, t_w), "sent": True,
                                  "mono_ns": mono(kw, 32.0), "real_ns": real(kw, 32.0)}))
        s_lines.append(_line({"kind": "summary", "images_dropped": len(drop_ks), "mono_ns": mono(len(ticks))}))
        (sdir / "score_interface.jsonl").write_text("\n".join(s_lines) + "\n")
        (sdir / "actuationAdapter.jsonl").write_text("\n".join(a_lines) + "\n")
        (sdir / "identityRecorder.jsonl").write_text(_line({
            "t_mono_ns": mono(0, -60000.0), "t_real_ns": real(0, -60000.0), "host": "score",
            "component": "identityRecorder", "event": "record", "seq": 1,
            "data": {"path": "/tmp/de4sdv-da-bench/run/score/candidate_record.json", "sha256": "5ff680b0" * 8,
                     "bytes": 150530, "upstream_revision": "014e0e7a56ee8e597c2cab8175233f74edd9b856",
                     "diff_bytes": spec.diff_bytes, "diff_sha256": "f86664a3" * 8}}) + "\n")
        (sdir / "candidate_record.json").write_text(json.dumps(candidate_record(spec), indent=1))
        top = sdir.parents[2]            # score_<run>/: the stop's own records of the run
        (top / "candidate_rrd.json").write_text(json.dumps([{
            "path": f"/home/mrk/da-kit/x/out/score_{spec.run_id}/score_side/vision_pilot/visionpilot.rrd",
            "bytes": 3315297533, "sha256": "c573d647" * 8, "stage_path": "/tmp/de4sdv-da-bench/vision_pilot/"
            "visionpilot.rrd", "collected_as": "hard link"}]))
        (top / "staging.json").write_text(json.dumps({"stage": "/tmp/de4sdv-da-bench", "mode": "full",
                                                      "bundle": "/opt/da-b2/bundle",
                                                      "upstream_revision": "014e0e7a56ee8e597c2cab8175233f74edd9b856"}))

    # The IVI app: one receipt per warning request sent; its real clock 0.4 s behind the S-CORE host's.
    gdir = root / "guest" / "out" / f"capture_{spec.run_id}"
    gdir.mkdir(parents=True, exist_ok=True)
    r_lines = [_line({"event": "lifecycle", "t_mono_ns": 1, "t_real_ns": real(0, -9000.0), "phase": "start",
                      "pid": 3206, "subject": "org.de4sdv.collisionwarning.CollisionWarningPresentation",
                      "message": "de4sdv.driving.v1.CollisionWarningRequest",
                      "publisher": "com.android.sdv.someip.SomeIpBroker",
                      "unit": "de4sdv-driving-warning-request",
                      "translation": "REFLECTION at the SDV Core SOME/IP broker", "poll_ms": 10})]
    rseq = 0
    for c, w in zip(sim["commands"], sim["warnings"]):
        k = c["k"]
        if stop_mono is not None and mono(k, 31.0) > stop_mono and not spec.receipt_after_stop:
            continue
        rseq += 1
        tk = by_k[k]
        r_lines.append(_line({"event": "receipt", "t_mono_ns": rseq, "t_real_ns": real(k, 60.0),
                              "seq": rseq, "requested": int(w["requested"]),
                              "issue_time_sim_ms": int(round(tk["simTimeS"] * 1000.0)),
                              "verdict": "ACCEPTED", "request": int(w["requested"]), "reason": ""}))
    if spec.late_receipt_after_stop and stop_real is not None:
        before = [c for c in sim["commands"] if mono(c["k"], 31.0) <= stop_mono]
        k = before[-1]["k"]
        r_lines.append(_line({"event": "receipt", "t_mono_ns": 998, "t_real_ns": stop_real + 500_000_000,
                              "seq": rseq + 1, "requested": 0,
                              "issue_time_sim_ms": int(round(by_k[k]["simTimeS"] * 1000.0)),
                              "verdict": "STALE", "request": 0, "reason": ""}))
    if spec.forged_receipt:
        k = sim["commands"][len(sim["commands"]) // 2]["k"]
        r_lines.append(_line({"event": "receipt", "t_mono_ns": 999, "t_real_ns": real(k, 61.0), "seq": rseq + 1,
                              "requested": 1, "issue_time_sim_ms": int(round(by_k[k]["simTimeS"] * 1000.0)) + 7,
                              "verdict": "ACCEPTED", "request": 1, "reason": ""}))
    (gdir / "app_record_warning.jsonl").write_text("\n".join(r_lines) + "\n")
    cdir = root / "guest" / "out" / f"ivi_clock_{spec.run_id}"
    cdir.mkdir(parents=True, exist_ok=True)
    (cdir / "clock.jsonl").write_text(_line({"label": "after_second_set", "reads": 15, "offset_s": -0.0009,
                                             "bound_s": 0.025}) + "\n")
    # the chase view of the run on the simulator host (rec_<run>/, l4_recorder_v3.py)
    rdir = root / "sim-lead-fetch" / "x" / "out" / f"rec_{spec.run_id}"
    rdir.mkdir(parents=True, exist_ok=True)
    (rdir / "chase_view.mp4").write_bytes(b"\x00\x00\x00\x18ftypmp42" + spec.run_id.encode())
    # session.json score_runs.<run> as da_session.sh (a0bd4bd7) writes it for s1, plus the PROPOSAL
    # visualization_recording (OBSERVABLES.md, lane D)
    rid = "stop" if spec.kind == "stop" else spec.setting_id
    rep = "further" if spec.kind == "stop" else f"r{spec.run_id[-1]}"
    out: dict = {"setting": spec.setting_id, "run_id": rid, "runIdentity": f"{rid}/{rep}",
                 "scenario": "SC-DRIVING-012" if spec.setting_id == STOP else spec.setting_id.split("@")[0],
                 "simulatedConfiguration": {"sha256": f"{zlib.crc32(spec.setting_id.encode()):08x}" * 8,
                                            "files": ["world-side/scenarios.py"], "rule": "sha256 of the files"},
                 "visualization_recording": {"sha256": "7e57a11a" * 8, "path": "visualization.mp4"}}
    if stop_mono is not None:
        out["_stop_line"] = {"runTarget": "path_stopped", "stopInstantRealNs": stop_real,
                             "stopInstantMonoNs": stop_mono, "rc": 0}
    return out


def candidate_record(spec: RunSpec) -> dict:
    """candidate_record.json in the identity recorder's shape (schema de4sdv.driver_assistance.candidate_record.v1, as
    attempt 3's record holds it), shortened."""
    return {"schema": "de4sdv.driver_assistance.candidate_record.v1", "mapping": "MAP-DRIVING-DA-CANDIDATE-RECORD",
            "host": "score", "upstream_revision": "014e0e7a56ee8e597c2cab8175233f74edd9b856",
            "source_difference": {"bytes": spec.diff_bytes, "sha256": "f86664a3" * 8, "files": [
                {"name": "0001-de4sdv-visualization-recorder.diff", "sha256": "cee80df2" * 8, "bytes": 30271,
                 "text": "diff --git"},
                {"name": "0002-de4sdv-score-interface.diff", "sha256": "8a6d7fe4" * 8, "bytes": 80000,
                 "text": "diff --git"}]},
            "candidate": {"component": "vision_pilot", "source_mode": "score", "model_precision": "fp32"},
            "configuration_files": [{"role": "vision_pilot.conf", "path": "/tmp/de4sdv-da-bench/vision_pilot/config/"
                                     "vision_pilot.conf", "sha256": "ae60bd56" * 8, "bytes": 1864}],
            "network_files": [{"role": "network autodrive", "path": "/tmp/de4sdv-da-bench/vision_pilot/modules/models/"
                               "weights/autodrive_fp32.onnx", "sha256": "196a8228" * 8, "bytes": 43015192}],
            "launch_settings": {"launch_config_path": "/tmp/de4sdv-da-bench/config/launch_manager_config.json",
                                "launch_config_text": "{}", "components": [{"component": "vision_pilot"}]}}


# session.json fields that no producer writes yet: this generator's names are OBSERVABLES.md's PROPOSALS (lane D)
SESSION_PROPOSALS = {
    "configuration_identity": "DRIVING-CONFIG-002",
    "configuration_receipt_sha256": "0c0ffee0" * 8,
    "visualization_recorder_delay": "2.0 ms at the median, 5.8 ms at the 99th percentile (readiness probe of "
                                    "2026-11-17, S-CORE host with an NVIDIA L4)",
    "score_platform": {"lifecycle_version": "v0.10.0", "communication_version": "v0.1.3",
                       "someip_gateway_commit": "5a5e1b2c" * 5},
    "execution_environment": {"score_gpu": "NVIDIA L4", "sdv_core_image": "sdv-core 2026-11-17 build 41",
                              "ivi_image": "ivi 2026-11-17 build 17"},
}


def label(setting_id: str, rep: int) -> str:
    """The s1 run list's label of a run (da_session.sh, a0bd4bd7): SC-DRIVING-012@20 r1 is 012_20_r1."""
    scenario, speed = setting_id.split("@")
    return f"{scenario[-3:]}_{speed}_r{rep}"


def s1_specs(**overrides_by_run) -> list[RunSpec]:
    """The 14 runs of the seven settings and the stop run, in the S1 order, each one passing every case."""
    specs, base = [], 600.0
    for sid in S1_SETTINGS:
        for rep in (1, 2):
            rid = label(sid, rep)
            kw: dict = {}
            if sid.startswith("SC-DRIVING-014"):
                kw.update(target_in_lane=False, warn_at_needed=None, eb_at_needed=None,
                          brake_window_s=(1.0, 30.0), brake_accel=-0.6, site_id="sc014-curve",
                          guidance=dict(GUIDANCE_014))
            if sid.startswith("SC-DRIVING-015"):
                kw.update(warn_at_needed=None, eb_at_needed=None, site_id="sc015-turnoff",
                          run_cap_s=8.0, guidance=dict(GUIDANCE_015))
            kw.update(overrides_by_run.get(rid, {}))
            specs.append(RunSpec(rid, sid, sim_base_s=base, mono_base_ns=int(base * 1e9) * 3,
                                 real_base_ns=1_795_168_000_000_000_000 + int(base * 1e9), **kw))
            base += 100.0
    kw = {"warn_at_needed": None, "eb_at_needed": None, "stop_after_s": 2.0, "run_cap_s": 6.0, "start_ttc_s": 30.0}
    kw.update(overrides_by_run.get("stop", {}))
    specs.append(RunSpec(STOP, STOP, kind="stop", sim_base_s=base, mono_base_ns=int(base * 1e9) * 3,
                         real_base_ns=1_795_168_000_000_000_000 + int(base * 1e9), **kw))
    return specs


def write_session(root: Path, specs: list[RunSpec], session_extra: dict | None = None,
                  proposals: bool = True) -> Path:
    """The session tree and its session.json: score_runs and s1 as da_session.sh (a0bd4bd7) writes them for kind s1,
    the fields of the session that attempt 3's session.json holds, and (proposals) SESSION_PROPOSALS."""
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    runs, stop_line = {}, None
    for spec in specs:
        runs[spec.run_id] = write_run(root, spec)
        stop_line = runs[spec.run_id].pop("_stop_line", None) or stop_line
    s1 = {"runs_file": "kit:bench/session/s1_runs.tsv", "runs": [], "runs_done": list(runs), "runs_owed": [],
          "stop_instant": None, "path_stop": None}
    if stop_line is not None:
        line = json.dumps(stop_line, separators=(",", ":"))
        s1["stop_instant"] = dict(stop_line)
        s1["path_stop"] = {"label": STOP, "go_unix_s": 1795168000.0, "call_unix_s": 1795168012.0,
                           "after_go_s": 12.0, "line": line, "stop_instant": dict(stop_line)}
    session = {"session_id": "synthetic", "kind": "s1", "exit_code": 0, "bench_commit": "39a964a2" * 5,
               "worktree_changes": "0", "candidate": {"name": "vision_pilot", "bundle": "pin ac20dccd"},
               "started": ["sim", "score", "guest"],
               "internal_ips_from_gcloud": {"sim": "10.10.0.2", "score": "10.164.0.5", "guest": "10.164.0.6"},
               "score_runs": runs, "s1": s1}
    if proposals:
        session.update(json.loads(json.dumps(SESSION_PROPOSALS)))
    session.update(session_extra or {})
    (root / "session.json").write_text(json.dumps(session, indent=1))
    return root


if __name__ == "__main__":  # pragma: no cover
    import sys
    write_session(Path(sys.argv[1]), s1_specs())
    print(sys.argv[1])
