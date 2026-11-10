"""The 35 case evaluators of INC-DRIVING-001.

Each function reads one run directory (ICD section 7) and decides one
verification case against the success criteria of its requirement, as the
model's `processData` states them. It adds no criterion of its own; where the
requirement names a threshold the threshold is in THRESHOLDS of the module.

Outcomes are the DrivingEvidenceOutcome literals of the model:

* passBoundedVerification - the record meets the criteria;
* failObservedBehavior     - the record shows them not met;
* inconclusiveMissingEvidence - a record, event or field the case needs is
  absent. Never a pass. `missing` names what, and `icd_changes` names the
  proposed ICD change that would supply it;
* errorEvidence            - the record cannot be read (malformed);
* notApplicable            - this run is not one of the case's runs (the
  caller leaves it out of verdicts.json and lists it under `skipped`).

Every verdict carries `measured` (the numbers the judgement rests on),
`thresholds` and `evidence` (file + seq of the records read).
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from runio import (STEP_MS, STEP_S, Run, RunFormatError, MissingEvidence, close, finite,
                   frames_between, maybe_num, num)
from gaps import ICD_CHANGES

PASS = "passBoundedVerification"
FAIL = "failObservedBehavior"
INCONCL = "inconclusiveMissingEvidence"
ERROR = "errorEvidence"
BLOCKED = "blockedTargetRuntime"
NOT_APPLICABLE = "notApplicable"

VERDICT = {PASS: "pass", "passBoundedValidation": "pass", FAIL: "fail",
           INCONCL: "inconclusive", BLOCKED: "inconclusive", ERROR: "error"}

MODES = ["kStarting", "kDriving", "kStopResponse", "kStandstill", "kRefused"]
CAUSES = ["kNone", "kCameraMissing", "kCameraInvalid", "kCameraStale",
          "kMotionInvalid", "kMotionStale", "kRouteStale", "kRouteEmpty",
          "kPlanStale", "kPlanInvalid", "kCommandTimeout", "kCheckpointRefused",
          "kRunEnd"]
CAMERAS = ["front", "front_left", "front_right", "rear_left", "rear", "rear_right"]
# A25: before it, the agent named the C2 cameras by their CARLA role names,
# cam_<slot>. They are read as the slots, with a note.
CAMERA_ALIASES = {f"cam_{slot}": slot for slot in CAMERAS}


def stub_engine_note(run: Run) -> str | None:
    """A17: the stub engine hands the simulator image to the planner as it is
    and makes no inference of the pinned checkpoint."""
    if run.engine() == "stub":
        return ("the run's planner engine is the stub (agent `engine` record): it "
                "makes no checkpoint inference and hands the simulator image as it "
                "is (ICD A17)")
    return None

# Every number a case judges against, one place, so a reviewer can check the
# reading of the requirement without reading the code.
THRESHOLDS = {
    "step_s": 0.1,
    "plan_publish_latency_s": 0.10,        # REQ-015
    "sample_publish_latency_s": 0.10,      # REQ-016
    "health_period_s": 0.20,               # REQ-017
    "camera_stale_s": 0.20,                # REQ-023
    "motion_stale_s": 0.20,                # REQ-024
    "route_stale_s": 1.00,                 # REQ-025
    "plan_stale_s": 0.30,                  # REQ-026
    "stop_begin_latency_s": 0.10,          # REQ-023..-027
    "adapter_timeout_s": 0.20,             # REQ-028 / ICD 4
    "stop_to_actuation_s": 0.30,           # REQ-028
    "stop_publication_latency_s": 0.10,    # REQ-029
    "stop_deceleration_mps2": -4.0,
    "stop_deceleration_tol_mps2": 0.20,    # REQ-020
    "standstill_kmh": 0.10,                # ICD 4
    "planning_latency_s": 0.10,            # REQ-013
    "planning_pass_fraction": 0.99,        # REQ-013
    "rtf_min": 0.95,                       # REQ-013
    "planning_p99_spread_s": 0.010,        # REQ-019
    "camera_history_offsets_s": [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5],   # REQ-004
    "ego_history_len": 64,                 # REQ-008
    "ego_speed_tol_mps": 0.05,             # REQ-008
    "ego_accel_tol_mps2": 0.10,
    # REQ-DRIVING-008 as amended on 2026-11-09 (GAP-DRIVING-010): yaw rate and
    # curvature are given to the checkpoint as zero, not compared with the simulator.
    "ego_yaw_given_radps": 0.0,
    "ego_curvature_given_1pm": 0.0,
    "map_context_render_age_s": 0.50,      # REQ-006
    "map_context_channels": 14,            # REQ-006
    "map_context_shape_hw": [450, 300],    # REQ-006
    "route_mask_channels": 2,              # REQ-007
    "route_mask_shape_hw": [450, 300],     # REQ-007
    # A16: the route window of geometry autoe2e-bev-450x300-0p4m-v1, shrunk
    # by two pixels; a point is in it strictly inside these bounds.
    "map_window_forward_m": [-10.0, 120.0],
    "map_window_lateral_m": [-60.0, 60.0],
    "map_window_margin_m": 0.8,
    "camera_tile_px": [512, 512],          # A17
    "front_hi_res_px": [1024, 1024],       # A11
    "projection_tol_px": 2.0,              # REQ-005
    "map_context_geometry": "autoe2e-bev-450x300-0p4m-v1",
    "window_s": 60.0,                      # REQ-013/-015/-016/-017
    "run_identity_prefix_hex": 16,         # ICD 8
    # ICD v2 C2 bundle sampling: every 50th step, plus every step within
    # +/-0.5 s of an injected fault.
    "bundle_period_steps": 50,
    "bundle_fault_window_s": 0.5,
}


# --------------------------------------------------------------------- model
@dataclass
class Result:
    vc: str
    outcome: str
    measured: dict = field(default_factory=dict)
    thresholds: dict = field(default_factory=dict)
    evidence: list = field(default_factory=list)
    missing: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    icd_changes: list = field(default_factory=list)

    def as_dict(self) -> dict:
        return {"vc": self.vc, "outcome": self.outcome,
                "verdict": VERDICT.get(self.outcome, "inconclusive"),
                "measured": _clean(self.measured),
                "thresholds": _clean(self.thresholds),
                "evidence": self.evidence, "missing": self.missing,
                "notes": self.notes, "icd_changes": self.icd_changes}


def _clean(obj):
    """JSON-safe copy: numpy scalars to Python, NaN/inf to null."""
    if isinstance(obj, dict):
        return {k: _clean(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_clean(v) for v in obj]
    if isinstance(obj, (np.floating, float)):
        f = float(obj)
        return f if math.isfinite(f) else None
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def ev(file: str, rec: dict) -> dict:
    return {"file": file, "seq": rec["seq"]}


def enum_name(v, table: list[str]) -> str | None:
    if isinstance(v, bool):
        return None
    if isinstance(v, int) and 0 <= v < len(table):
        return table[v]
    if isinstance(v, str):
        return v
    return None


def ok(vc: str, measured: dict, thresholds: dict, evidence: list,
       notes: list | None = None) -> Result:
    return Result(vc, PASS, measured, thresholds, evidence, notes=notes or [])


def bad(vc: str, measured: dict, thresholds: dict, evidence: list,
        notes: list | None = None) -> Result:
    return Result(vc, FAIL, measured, thresholds, evidence, notes=notes or [])


def inconclusive(vc: str, what: str, change: str | None, detail: str = "",
                 measured: dict | None = None) -> Result:
    return Result(vc, INCONCL, measured or {}, {}, [], missing=[what],
                  notes=[detail] if detail else [],
                  icd_changes=[change] if change else [])


def not_applicable(vc: str, why: str) -> Result:
    return Result(vc, NOT_APPLICABLE, notes=[why])


# --------------------------------------------------------------------- registry
CASES: dict[str, dict] = {}


def case(vc: str, scenarios: tuple[str, ...], needs: tuple[str, ...] = ()):
    def deco(fn):
        CASES[vc] = {"fn": fn, "scenarios": scenarios, "needs": list(needs),
                     "doc": (fn.__doc__ or "").strip()}
        return fn
    return deco


# --------------------------------------------------------------------- helpers
def plans_by_frame(plans: list[dict]) -> dict[int, dict]:
    out: dict[int, dict] = {}
    for p in plans:
        f = p.get("frame")
        if isinstance(f, int) and f not in out:
            out[f] = p
    return out


def plan_frame(p: dict) -> int | None:
    f = p.get("frame")
    return f if isinstance(f, int) else None


def means_stopped(mode) -> bool:
    return enum_name(mode, MODES) in ("kStopResponse", "kStandstill")


def stop_window(run: Run) -> tuple[dict, dict | None]:
    begin = run.stop_begin()
    if begin is None:
        raise MissingEvidence("stop_response.begin", None,
                              "the run records no start of a stop response")
    return begin, run.standstill()


def actuations_between(run: Run, t0: float, t1: float | None) -> list[dict]:
    out = []
    for a in run.actuations():
        t = a["actuation_s"]
        if t is None:
            continue
        if t < t0 - 1e-6:                   # the actuation of the step t0 belongs to [t0,..]
            continue
        if t1 is not None and t > t1 + 1e-6:
            continue
        out.append(a)
    return out


def sensors_at(run: Run) -> dict[int, list[dict]]:
    out = {}
    for f, rec in run.world_by_frame().items():
        s = rec["data"].get("sensors")
        if isinstance(s, list):
            out[f] = s
    return out


# The engine works the ego-motion rows of a step k out from the REF poses of
# frames k-65 .. k (agent DESIGN.md, "Ego-motion history"): numpy.gradient,
# central inside the window and one-sided at its ends, rows [1:-1]. Its newest
# row is therefore the sample of frame k-1, and row j of a step's 64 rows is
# frame step - 64 + j.
EGO_ROWS = 64
EGO_NEWEST_ROW_LAG = 1
EGO_POSE_WINDOW = EGO_ROWS + 2          # the poses of frames k-65 .. k


def ego_row_frame(step_frame: int, j: int) -> int:
    return step_frame - EGO_ROWS - EGO_NEWEST_ROW_LAG + 1 + j


def ego_pose_frames(step_frame: int) -> range:
    """The frames whose poses a step's rows are worked out from, oldest first."""
    return range(step_frame - EGO_POSE_WINDOW + 1, step_frame + 1)


def source_speed_acceleration(poses, origin) -> tuple[np.ndarray, np.ndarray]:
    """The speed and acceleration of a step's 64 rows, worked out the source's way.

    REQ-DRIVING-008 as amended on 2026-11-10, as upstream's closed-loop driver
    works them out (`egomotion_from_poses` of alpasim_autoe2e). `poses` are the
    66 C1 poses (x, y, yaw) of the step's window, map frame (ICD section 9);
    `origin` is the rig origin (x, y, z) in vehicle axes, y to the right, so a
    pose moves by (x, -y) in its own axes. The velocity is numpy.gradient of the
    moved positions at 0.1 s, the speed its norm, the acceleration
    numpy.gradient of the speed; rows [1:-1].
    """
    ox, oy = float(origin[0]), float(origin[1])
    p = np.asarray(poses, dtype=np.float64)
    c, s = np.cos(p[:, 2]), np.sin(p[:, 2])
    xy = np.stack([p[:, 0] + ox * c + oy * s, p[:, 1] + ox * s - oy * c], axis=1)
    speed = np.linalg.norm(np.gradient(xy, STEP_S, axis=0), axis=1)
    accel = np.gradient(speed, STEP_S)
    return speed[1:-1], accel[1:-1]


def plan_steps(run: Run) -> list[dict]:
    """The C2 records of the steps that have a plan.

    REQ-DRIVING-003, -004, -006, -007, -008 and -010 state their criteria for
    the inputs recorded for every plan. The agent writes a C2 record for every
    step, primed or not (agent/cc/agent_ffi.cpp:1020-1079), so a step without a
    plan is not judged. No plan in the run, or a plan without its C2 record,
    is missing evidence.
    """
    steps = run.input_steps()
    frames = {plan_frame(p) for p in run.plans(required=False)} - {None}
    if not frames:
        raise MissingEvidence("score/drivingAgent.jsonl:out.plan", None,
                              "the case judges the inputs of each plan; this run has no plan")
    out = [s for s in steps if s["frame"] in frames]
    without = sorted(frames - {s["frame"] for s in out})
    if without:
        raise MissingEvidence(f"score/checkpointInputs.jsonl:frame {without[0]}", "C2",
                              f"{len(without)} plans have no C2 record of their inputs, "
                              f"first frames {without[:5]}")
    return out


def camera_views(run: Run) -> list[dict]:
    """The per-step camera metadata of ICD v2 C2 (conditionInputs)."""
    return run.input_steps()


def driving_after_priming(run: Run):
    """Reading of REQ-DRIVING-023 to -025 (README, "Readings"): the stop
    response presupposes a driving vehicle. While starting, the agent logs a
    fault, starts no stop and primes again (agent/cc/agent_logic.cpp:335-338).
    A condition is a baseline only at a step at or after priming.complete
    (C10) whose previous mode record is kDriving.

    Returns (priming frame, predicate on a step frame).
    """
    import bisect
    prime = run.priming_frame()
    modes = sorted((m["frame"], enum_name(m["mode"], MODES)) for m in run.modes()
                   if isinstance(m["frame"], int))
    frames = [f for f, _ in modes]

    def eligible(f: int) -> bool:
        i = bisect.bisect_left(frames, f) - 1
        return f >= prime and i >= 0 and modes[i][1] == "kDriving"
    return prime, eligible


NOT_WHILE_DRIVING = ("no {what} condition at a step at or after priming.complete while the "
                     "agent drove: the stop response presupposes a driving vehicle "
                     "(README, Readings)")


def first_camera_condition(run: Run, eligible=None) -> tuple[int, str] | None:
    """First step with a camera condition under the reading of REQ-DRIVING-023
    (README, "Readings"; camera_conditions_by_reading).

    Returns (frame, cause) or None. The conditions are read from the C2
    metadata record: per camera image frame, capture_sim_ms, valid and status.
    C1's world sensors only name the actor and whether it is attached/alive;
    they carry no capture time, so the staleness instant comes from C2. Steps
    for which `eligible(frame)` is false are skipped.
    """
    conds = camera_conditions_by_reading(run)
    for f in sorted(conds):
        if eligible is None or eligible(f):
            return f, conds[f]["cause"]
    return None


# Reading of REQ-DRIVING-023, both halves (README, "Readings"): the statement
# with its rationale "one late image is tolerated, a second means the camera
# has stopped". The owner may change this reading.
CAMERA_NEWEST_IMAGE_LIMIT_MS = int(round(THRESHOLDS["camera_stale_s"] * 1000))    # 200
CAMERA_CAUSES = ("kCameraMissing", "kCameraInvalid", "kCameraStale")


def camera_conditions_by_reading(run: Run) -> dict[int, dict]:
    """The steps with a camera condition under the reading of REQ-DRIVING-023.

    A camera condition exists at a step when a camera has had no valid image to
    date (kCameraMissing), its image at the step is invalid (kCameraInvalid),
    or its newest valid image is more than CAMERA_NEWEST_IMAGE_LIMIT_MS of
    simulation time older than the step (kCameraStale), whether or not the
    step's own image arrived. A step whose own image missed while the camera's
    newest image is at most that old is not a condition.

    The agent's C2 record describes the step's own slot: a camera whose image
    did not arrive for the frame has null stamps and status "missing"
    (agent/cc/frame_store.h:94, agent_ffi.cpp:1026-1033). The newest image is
    therefore the latest image of the camera in any C2 step up to this one, or
    in a merged frame the agent conditioned, which needs every camera valid
    (agent_ffi.cpp:575-615). Returns {frame: {"cause", "camera", "age_ms"}}.
    """
    newest: dict[int, float] = {}
    out: dict[int, dict] = {}
    for step in camera_views(run):
        f, step_ms = step["frame"], step["sim_ms"]
        for m in step.get("merged_frames") or []:
            if isinstance(m, dict) and m.get("conditioned") is True \
                    and isinstance(m.get("frame"), int):
                for i in range(len(step["cameras"])):
                    newest[i] = max(newest.get(i, -1.0), m["frame"] * float(STEP_MS))
        found = None
        for i, cam in enumerate(step["cameras"]):
            status = cam.get("status")
            ct = cam.get("capture_sim_ms")
            present = ct is not None and status != "missing"
            invalid = status == "invalid" or (status is None and cam.get("valid") is False)
            if present and not invalid:
                newest[i] = max(newest.get(i, -1.0), float(ct))
            if present and invalid:
                found = found or {"cause": "kCameraInvalid", "camera": cam.get("name"),
                                  "age_ms": None}
                continue
            if i not in newest:
                found = found or {"cause": "kCameraMissing", "camera": cam.get("name"),
                                  "age_ms": None}
                continue
            age = step_ms - newest[i]
            if age > CAMERA_NEWEST_IMAGE_LIMIT_MS + 1e-9:
                found = found or {"cause": "kCameraStale",
                                  "camera": cam.get("name"), "age_ms": age}
        if found:
            out[f] = found
    return out


def camera_by_reading(run: Run, vc: str, fault_run: bool) -> Result:
    """VC-DRIVING-023, both halves, read as stated in the README ("Readings"):
    every camera-caused stop begins at most 100 ms after a camera condition
    under the reading, and the first condition while the agent drives begins
    the stop response within 100 ms. Without such a condition the no-fault
    half (a run of SC-DRIVING-001) passes and the fault half (SC-DRIVING-003)
    is inconclusive."""
    conds = camera_conditions_by_reading(run)
    prime, eligible = driving_after_priming(run)
    lag = int(round(THRESHOLDS["stop_begin_latency_s"] / STEP_S))
    camera_stops = [s for s in run.stops("stop_response.begin")
                    if enum_name(s["cause"], CAUSES) in CAMERA_CAUSES]
    first = first_camera_condition(run, eligible)
    measured = {"reading": "README, Readings: REQ-DRIVING-023",
                "newest_image_limit_ms": CAMERA_NEWEST_IMAGE_LIMIT_MS,
                "steps_with_a_condition": len(conds),
                "first_condition_frame": first[0] if first else None,
                "camera_caused_stops": [{"frame": s["frame"],
                                         "cause": enum_name(s["cause"], CAUSES)}
                                        for s in camera_stops[:3]],
                "priming_frame": prime}
    th = {"newest_image_limit_ms": CAMERA_NEWEST_IMAGE_LIMIT_MS,
          "stop_begin_latency_s": THRESHOLDS["stop_begin_latency_s"]}
    evid = [ev(s["file"], s["rec"]) for s in camera_stops[:1]]
    for s in camera_stops:
        window = range(s["frame"] - lag, s["frame"] + 1)
        if not any(f in conds for f in window):
            measured["stop_without_condition_frame"] = s["frame"]
            return bad(vc, measured, th, evid,
                       [f"a camera-caused stop began at frame {s['frame']} with no camera "
                        "condition under the reading (one late image is tolerated)"])
    if first is None:
        if fault_run:
            return inconclusive(vc, "a camera condition while the agent drove", None,
                                NOT_WHILE_DRIVING.format(what="camera"),
                                dict(measured, fault=run.fault()))
        return ok(vc, measured, th, evid,
                  ["no camera condition while the agent drove and no stop without one "
                   "(the no-fault half; README, Readings)"])
    frame, cause = first
    res = stop_timing(run, frame, cause)
    res.vc = vc
    res.measured.update(measured)
    res.measured.update({"condition_frame": frame, "condition": cause})
    res.thresholds.update(th)
    res.thresholds.update({"condition": cause})
    res.notes.append("a camera condition under the reading while the agent drove")
    return res


def stop_timing(run: Run, baseline_frame: int, cause: str) -> Result:
    """Shared judgement of REQ-023..-027: stop begins within 100 ms, right cause."""
    begin = run.stop_begin()
    t_base = baseline_frame * STEP_S
    if begin is None:
        return bad("", {"baseline_sim_s": t_base, "stop_begin_sim_s": None},
                   {"stop_begin_latency_s": THRESHOLDS["stop_begin_latency_s"]}, [],
                   ["the condition was recorded but no stop response began"])
    delay = begin["t_sim"] - t_base
    got = enum_name(begin["cause"], CAUSES)
    thresholds = {"stop_begin_latency_s": THRESHOLDS["stop_begin_latency_s"],
                  "expected_cause": cause}
    measured = {"baseline_sim_s": t_base, "stop_begin_sim_s": begin["t_sim"],
                "delay_s": delay, "cause": got}
    evid = [ev(begin["file"], begin["rec"])]
    if got != cause:
        return bad("", measured, thresholds, evid,
                   [f"stop response cause {got} is not {cause}"])
    if delay > THRESHOLDS["stop_begin_latency_s"] + 1e-9:
        return bad("", measured, thresholds, evid,
                   [f"stop began {delay * 1000:.0f} ms after the condition, limit 100 ms"])
    if delay < -1e-9:
        return bad("", measured, thresholds, evid,
                   ["stop began before the condition was observable"])
    return ok("", measured, thresholds, evid)


# The SC-DRIVING-003 fault each case is about. A run carries one fault; the
# cases of the other faults are not applicable to it, and are reported as such
# rather than as inconclusive.
FAULT_FAMILY = {
    "VC-DRIVING-023": ("camera_missing", "camera_invalid", "camera_stale"),
    "VC-DRIVING-024": ("motion_stale", "motion_invalid"),
    "VC-DRIVING-025": ("route_stale", "route_empty"),
    "VC-DRIVING-026": ("plan_stale", "plan_dropped"),
    "VC-DRIVING-027": ("plan_invalid_nan", "plan_invalid_63"),
    "VC-DRIVING-028": ("comm_stop",),
    "VC-DRIVING-014": ("comm_stop",),
}
FAULT_LABEL = {
    "camera_missing": "the images of one camera are withheld",
    "camera_invalid": "a corrupt camera image is delivered",
    "camera_stale": "camera images older than 200 ms are delivered",
    "motion_stale": "the motion samples are frozen",
    "motion_invalid": "a non-finite motion sample is delivered",
    "route_stale": "the route provider stops announcing",
    "route_empty": "a route with an empty corridor is delivered",
    "plan_stale": "planning stalls",
    "plan_dropped": "plans are dropped",
    "plan_invalid_nan": "a plan with a non-finite value is injected",
    "plan_invalid_63": "a plan of 63 pairs is injected",
    "comm_stop": "the S-CORE communication of the driving system is stopped",
}


CAUSE_TO_FAULT = {
    "kCameraMissing": "camera_missing", "kCameraInvalid": "camera_invalid",
    "kCameraStale": "camera_stale", "kMotionStale": "motion_stale",
    "kMotionInvalid": "motion_invalid", "kRouteStale": "route_stale",
    "kRouteEmpty": "route_empty", "kPlanStale": "plan_stale_or_dropped",
    "kPlanInvalid": "plan_invalid", "kCommandTimeout": "comm_stop",
}


def gate(run: Run, vc: str) -> Result | None:
    """Is this case's fault the fault of this run?

    The run record's scenarioVariant.fault answers it (ICD change C4). Without
    that label, the stop cause the run itself recorded answers it; if there is
    neither, the run cannot be routed to the case and the outcome is missing
    evidence, not "not applicable".
    """
    fam = FAULT_FAMILY.get(vc)
    if fam is None:
        return None
    label = run.variant.get("fault")
    if isinstance(label, str):
        if label in fam:
            return None
        return not_applicable(
            vc, f"this run's fault is {label!r}; the case needs a run in which "
                + ", ".join(FAULT_LABEL.get(f, f) for f in fam))
    begin = run.stop_begin()
    observed = CAUSE_TO_FAULT.get(enum_name(begin["cause"], CAUSES)) if begin else None
    if observed is None:
        return inconclusive(vc, "run_record.scenarioVariant.fault", "C4",
                            "the run neither names its fault nor records a stop that "
                            "identifies it")
    if observed in fam or (observed == "plan_stale_or_dropped"
                           and set(fam) & {"plan_stale", "plan_dropped"})             or (observed == "plan_invalid"
                and set(fam) & {"plan_invalid_nan", "plan_invalid_63"}):
        return None
    return not_applicable(
        vc, f"the stop cause shows a {observed} condition; the case needs a run in which "
            + ", ".join(FAULT_LABEL.get(f, f) for f in fam))


# --------------------------------------------------------------------- cases
@case("VC-DRIVING-001", ("closedLoopRoute",), needs=("C10", "C9", "C2"))
def vc001(run: Run) -> Result:
    """No two consecutive 100 ms steps without a new plan, from the end of
    priming to the end of the run or the start of the stop response (REQ-001
    as amended).

    A new plan at step k is an out.plan whose frameIndex is k. A single step
    without one is allowed: a frame FEO merged into the next step after an
    overrun gets no plan of its own (ICD A23, C2 mergedFrames), nor does a step
    whose camera image missed the deadline. The window's first step needs no
    plan before it.

    The end of priming is the agent's priming.complete record. A record that
    names a step the engine did not condition predates ICD A26 (run N: frame
    113, the engine primed at 179); it is flagged, and the end of priming is
    the engine's first conditioned primed step at or after it (C2, A26). The
    run ends at the world's last tick (C1), or at the agent's last step, its
    last C2 record, when that is later: an agent that stops planning while the
    world ticks on leaves the steps after it without a plan. A run without a
    world record ends at the agent's last step, with a note.
    """
    vc = "VC-DRIVING-001"
    plans = run.plans()
    recorded = run.priming_frame()
    steps = run.input_steps()
    by_frame = {s["frame"]: s for s in steps}
    prime, conflict = recorded, None
    at = by_frame.get(recorded)
    if at is not None and at.get("conditioned") is False:
        engine = next((s["frame"] for s in steps if s["frame"] >= recorded
                       and s.get("primed") is True and s.get("conditioned") is True), None)
        conflict = {"frame": recorded, "engine_primed_frame": engine,
                    "problem": "priming.complete names a step the engine did not condition "
                               "(a record from before ICD A26)"}
        if engine is None:
            return inconclusive(vc, "score/checkpointInputs.jsonl: a conditioned primed step",
                                "C2", conflict["problem"] + "; the engine never primed",
                                {"priming_record_conflict": conflict})
        prime = engine
    stop = run.stop_begin()
    agent_last = steps[-1]["frame"]
    world_last = None
    if stop:
        end = int(round(stop["t_sim"] / STEP_S)) - 1
    else:
        try:
            ticks = run.world_by_frame()
        except MissingEvidence:
            ticks = {}
        world_last = max(ticks) if ticks else None
        end = agent_last if world_last is None else max(world_last, agent_last)
    frames = [plan_frame(p) for p in plans]
    counts = Counter(f for f in frames if f is not None)
    window = range(prime, end + 1)
    planned = set(counts)
    without = [f for f in window if f not in planned]
    # a step without a new plan fails when the step before it in the window had none
    pairs = [[f - 1, f] for f in without if f - 1 >= prime and f - 1 not in planned]
    merged = {m["frame"] for s in steps for m in s["merged_frames"]
              if isinstance(m, dict) and isinstance(m.get("frame"), int)}
    longest = run_len = 0
    for i, f in enumerate(without):
        run_len = run_len + 1 if i and without[i - 1] == f - 1 else 1
        longest = max(longest, run_len)
    doubled = sorted(f for f, c in counts.items() if c > 1)
    bad_time = [p for p in plans
                if plan_frame(p) is None or p["capture_ms"] is None
                or not close(p["capture_ms"], plan_frame(p) * 100, 1e-6)]
    evid = [ev(p["file"], p["rec"]) for p in (plans[0], plans[-1])] if plans else []
    measured = {"plans": len(plans), "steps_in_window": len(window),
                "first_step": prime, "last_step": end,
                "steps_without_a_new_plan": len(without),
                "merged_frames_without_a_plan": len(merged.intersection(without)),
                "first_steps_without_a_new_plan": without[:10],
                "longest_run_without_a_new_plan": longest,
                "failing_pairs": pairs[:10],
                "doubled_steps": doubled[:10], "steps_with_wrong_capture_time": len(bad_time),
                "priming_record_conflict": conflict,
                "agents_last_step": agent_last, "world_last_tick": world_last}
    th = {"consecutive_steps_without_a_new_plan_max": 1, "step_s": STEP_S}
    flag = ([f"flagged: priming.complete at frame {recorded} names a step the engine did "
             f"not condition (before ICD A26); the end of priming is the engine's first "
             f"conditioned primed step, {prime}"] if conflict else [])
    if not stop and world_last is None:
        flag.append(f"the run has no world record (simulator/world.jsonl): the window ends "
                    f"at the agent's last C2 record, frame {agent_last}, and steps after "
                    f"the agent stopped cannot be judged")
    elif not stop and world_last > agent_last:
        flag.append(f"the world ticked to frame {world_last}, {world_last - agent_last} "
                    f"steps after the agent's last C2 record (frame {agent_last})")
    if without and not pairs:
        flag.append(f"{len(without)} steps without their own plan, none next to another "
                    f"({measured['merged_frames_without_a_plan']} merged by FEO, ICD A23)")
    if pairs or doubled or bad_time:
        notes = list(flag)
        if pairs:
            notes.append(f"{len(pairs)} pairs of consecutive steps without a new plan, "
                         f"first {pairs[:5]}")
        if doubled:
            notes.append(f"steps with more than one plan: {doubled[:5]}")
        if bad_time:
            notes.append(f"{len(bad_time)} plans whose capture_sim stamp is not "
                         f"frame x 100 ms")
        return bad(vc, measured, th, evid, notes)
    return ok(vc, measured, th, evid, flag)


@case("VC-DRIVING-002", ("closedLoopRoute",), needs=("C11", "C2"))
def vc002(run: Run) -> Result:
    """Every sampled plan reproduces the offline inference of the pinned
    checkpoint on the recorded inputs within 1 % (REQ-002).

    ICD v2 C2 retains full input bundles only for every 50th step and for the
    steps within +/-0.5 s of an injected fault, and C11 re-runs the checkpoint
    on those bundles. The case is therefore judged on the sampled plan steps;
    `measured.coverage` says how many of the run's plans that is. A sampled
    step without its bundle or without a reference entry is missing evidence,
    never a pass.
    """
    vc = "VC-DRIVING-002"
    stub = stub_engine_note(run)
    if stub:
        return inconclusive(vc, "a run of the checkpoint engine", None, stub)
    plans = run.plans()
    ref = run.reference_inference()
    ckpt = run.record.get("checkpointSha256")
    if not isinstance(ckpt, str) or not ckpt:
        return inconclusive(vc, "run_record.checkpointSha256", "C7",
                            "the run record does not name the checkpoint it loaded")
    ident = run.identity()
    schedule = run.bundle_schedule()
    bundles = run.bundle_frames()
    sampled = [p for p in plans if plan_frame(p) in schedule]
    if not sampled:
        return inconclusive(vc, "a plan at a sampled bundle step", "C2",
                            "no plan falls on the C2 sampling schedule "
                            "(every 50th step and fault +/-0.5 s)")
    no_bundle = sorted({plan_frame(p) for p in sampled if plan_frame(p) not in bundles})
    if no_bundle:
        return inconclusive(vc, f"score/bundles/{no_bundle[0]}.npz", "C2",
                            f"{len(no_bundle)} sampled plan steps have no retained input "
                            f"bundle, first frames {no_bundle[:5]}")
    worst_a = worst_c = 0.0
    missing_ref, wrong_ident, nonfinite = [], [], []
    evid = []
    for p in sampled:
        f = plan_frame(p)
        if p.get("run_record") != ident:
            wrong_ident.append(f)
        if f not in ref:
            missing_ref.append(f)
            continue
        r = ref[f]
        if r.get("checkpointSha256") != ckpt:
            wrong_ident.append(f)
        acc = np.array([s["acceleration"] for s in p["samples"]], dtype=float)
        cur = np.array([s["curvature"] for s in p["samples"]], dtype=float)
        ra = np.array(r.get("acceleration") or [], dtype=float)
        rc = np.array(r.get("curvature") or [], dtype=float)
        if ra.size != acc.size or rc.size != cur.size:
            missing_ref.append(f)
            continue
        if not np.all(np.isfinite(acc)) or not np.all(np.isfinite(cur)):
            nonfinite.append(f)
            continue
        tol_a = 0.01 * max(float(np.max(np.abs(acc))), 1e-6)
        tol_c = 0.01 * max(float(np.max(np.abs(cur))), 1e-12)
        worst_a = max(worst_a, float(np.max(np.abs(acc - ra))) / tol_a)
        worst_c = max(worst_c, float(np.max(np.abs(cur - rc))) / tol_c)
        if len(evid) < 2:
            evid.append(ev(p["file"], p["rec"]))
    measured = {"plans": len(plans), "sampled_plan_steps": len(sampled),
                "sampled_frames": sorted({plan_frame(p) for p in sampled})[:20],
                "bundles_present": len(bundles), "reference_inferences": len(ref),
                "coverage": f"{len(sampled)}/{len(plans)} plans sampled",
                "plans_without_reference": missing_ref[:10],
                "plans_with_wrong_identity": wrong_ident[:10],
                "plans_with_nonfinite_output": nonfinite[:10],
                "worst_error_fraction_of_tolerance": {"acceleration": worst_a,
                                                      "curvature": worst_c}}
    th = {"tolerance_fraction_of_signal_max": 0.01, "checkpoint": ckpt,
          "run_record": ident, "bundle_period_steps": THRESHOLDS["bundle_period_steps"],
          "bundle_fault_window_s": THRESHOLDS["bundle_fault_window_s"]}
    if missing_ref or wrong_ident:
        notes = []
        if missing_ref:
            notes.append("no reference inference for these sampled plan frames: "
                         f"{missing_ref[:5]} (C11 retains it)")
        if wrong_ident:
            notes.append(f"plans not naming this run/checkpoint: {wrong_ident[:5]}")
        return inconclusive(vc, "sampled plans without a reference inference", "C11",
                            "; ".join(notes), measured)
    if nonfinite:
        return bad(vc, measured, th, evid,
                   [f"plans with non-finite acceleration/curvature: {nonfinite[:5]}"])
    if worst_a > 1.0 or worst_c > 1.0:
        return bad(vc, measured, th, evid,
                   ["a plan differs from the offline inference by more than 1 % of "
                    "the signal's largest magnitude"])
    return ok(vc, measured, th, evid,
              [f"judged on {len(sampled)} of {len(plans)} plans: the C2 bundle sampling "
               "bounds REQ-002's every-plan claim"])


@case("VC-DRIVING-003", ("closedLoopRoute",), needs=("C2",))
def vc003(run: Run) -> Result:
    """Six current 512x512 images in the fixed order, with the front image also
    at 1024x1024 (REQ-003).

    A17 fixes a camera width/height as the size of the image handed to the
    checkpoint; A11 adds the front high-resolution size,
    cameras[front].front_hi_res. Runs before those amendments carry neither,
    and the case stays inconclusive rather than passing.

    A plan step whose record lacks one of the six cameras (the slots of ICD
    A25, see cameras_missing) fails. Camera names that are no slot leave the
    order unjudged, inconclusive, unless the step lists fewer than six.
    """
    vc = "VC-DRIVING-003"
    stub = stub_engine_note(run)
    if stub:
        return inconclusive(vc, "a run of the checkpoint engine", None, stub)
    recs = plan_steps(run)
    bad_records = []
    no_hi_res = []
    unknown_names = []
    aliased = False
    evid = []
    tile = THRESHOLDS["camera_tile_px"]
    hi_px = THRESHOLDS["front_hi_res_px"]
    for step in recs:
        cams = step["cameras"]
        raw = [c.get("name") for c in cams]
        names = [CAMERA_ALIASES.get(n, n) for n in raw]
        aliased = aliased or names != raw
        problems = []
        if sorted(map(str, names)) != sorted(CAMERAS):
            lack = cameras_missing(cams)
            if lack:
                problems.append(lack["text"])
            else:
                unknown_names.append({"frame": step["frame"], "names": raw})
        elif names != CAMERAS:
            problems.append(f"order {names}")
        for c in cams:
            if (c.get("width"), c.get("height")) != tuple(tile):
                problems.append(f"{c.get('name')} is {c.get('width')}x{c.get('height')}")
            if c.get("image_frame") != step["frame"]:
                problems.append(f"{c.get('name')} image frame {c.get('image_frame')} "
                                f"is not the step")
        front = next((c for c, n in zip(cams, names) if n == "front"),
                     cams[0] if cams else None)
        hi = front.get("front_hi_res") if front else None
        if not isinstance(hi, dict):
            no_hi_res.append(step["frame"])
        elif (hi.get("width"), hi.get("height")) != tuple(hi_px):
            problems.append(f"front_hi_res is {hi.get('width')}x{hi.get('height')}")
        if problems:
            bad_records.append({"frame": step["frame"], "problems": problems})
        if len(evid) < 2:
            evid.append(ev(step["file"], step["rec"]))
    measured = {"records": len(recs), "records_with_a_problem": len(bad_records),
                "problems": bad_records[:5],
                "steps_without_front_hi_res": len(no_hi_res),
                "frames_without_front_hi_res": no_hi_res[:10],
                "steps_with_unknown_camera_names": len(unknown_names),
                "unknown_camera_names": unknown_names[:2]}
    th = {"cameras": CAMERAS, "current_size": tile, "front_hi_res": hi_px}
    notes = (["camera names cam_<slot> are read as the slots: the agent wrote the "
              "CARLA role names before ICD A25"] if aliased else [])
    if bad_records:
        return bad(vc, measured, th, evid, notes)
    if unknown_names:
        return Result(vc, INCONCL, measured, {}, evid,
                      missing=["checkpointInputs.cameras[].name as the checkpoint's slots "
                               "(ICD A25)"],
                      notes=notes + ["the camera names are not the checkpoint's slots, so "
                                     "the order cannot be judged"],
                      icd_changes=["C2"])
    if no_hi_res:
        return inconclusive(
            vc, "checkpointInputs.cameras[front].front_hi_res {width, height}", "C2",
            f"{len(no_hi_res)} of {len(recs)} steps carry no front_hi_res (runs "
            "before A11); the six 512x512 images are otherwise recorded and current",
            measured)
    return ok(vc, measured, th, evid,
              notes + ["the sizes are the producer's statement; the images themselves "
                       "are only in the sampled bundles"])


def cameras_missing(cams: list[dict]) -> dict | None:
    """The cameras of REQ-DRIVING-003 a step's C2 record does not hold.

    The six cameras are the slots of ICD A25 (CAMERAS); a camera named
    cam_<slot> is that slot (records before A25). A slot that no camera of the
    step is named by is missing: the plan was given no current image of it,
    none of its seven earlier images and no capture record of them. A record
    that names a camera which is no slot cannot show which slot is missing; it
    lacks a camera only when it lists fewer than six. Returns None when nothing
    is shown missing, else {"missing": slot names (empty when the names are
    unknown), "count", "text"}.
    """
    names = [CAMERA_ALIASES.get(n, n) if isinstance(n, str) else n
             for n in (c.get("name") for c in cams)]
    if all(n in CAMERAS for n in names):
        missing = [s for s in CAMERAS if s not in names]
        if not missing:
            return None
        return {"missing": missing, "count": len(missing),
                "text": f"no {', '.join(missing)} camera"}
    if len(names) < len(CAMERAS):
        return {"missing": [], "count": len(CAMERAS) - len(names),
                "text": f"{len(names)} cameras, not six"}
    return None


@case("VC-DRIVING-004", ("closedLoopRoute",), needs=("C2",))
def vc004(run: Run) -> Result:
    """Seven earlier images per camera at 0.5 s to 3.5 s before the step (REQ-004).

    A camera the step's record lacks has none of its seven (cameras_missing)."""
    vc = "VC-DRIVING-004"
    recs = plan_steps(run)
    offs = THRESHOLDS["camera_history_offsets_s"]
    bad_records = []
    evid = []
    for step in recs:
        problems = []
        lack = cameras_missing(step["cameras"])
        if lack:
            problems.append(f"{lack['text']}: 0 of 7 history images for it")
        for c in step["cameras"]:
            hist = c.get("history") or []
            if len(hist) != 7:
                problems.append(f"{c.get('name')}: {len(hist)} history refs")
                continue
            if any(not isinstance(r, int) for r in hist):
                problems.append(f"{c.get('name')}: non-integer history ref")
                continue
            ages = sorted((step["frame"] - r) / 10.0 for r in hist)   # 10 frames = 1 s
            if not all(close(a, o, 1e-3) for a, o in zip(ages, offs)):
                problems.append(f"{c.get('name')}: ages {[round(a, 3) for a in ages]}")
        if problems:
            bad_records.append({"frame": step["frame"], "problems": problems})
        if len(evid) < 2:
            evid.append(ev(step["file"], step["rec"]))
    measured = {"records": len(recs), "records_with_a_problem": len(bad_records),
                "problems": bad_records[:5]}
    th = {"history_images_per_camera": 7, "offsets_s": offs}
    if bad_records:
        return bad(vc, measured, th, evid)
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-005", ("closedLoopRoute",), needs=("C2",))
def vc005(run: Run) -> Result:
    """One projection operator per image; a reference marker at a known
    vehicle-frame position maps to within 2 px of where it appears (REQ-005).

    ICD v2 C2 records the projection operator once per run (and on change) but
    not the pixel the marker appears at, so the comparison has only one side.
    """
    vc = "VC-DRIVING-005"
    recs = run.input_steps()
    has_op = any(c.get("projection") for step in recs for c in step["cameras"])
    if not has_op:
        return inconclusive(vc, "checkpointInputs.projections", "C2",
                            "no projection operator is recorded")
    return inconclusive(
        vc, "checkpointInputs.marker.image_px", "C2",
        "C2 records the operator; the pixel the reference marker appears at is not "
        "recorded, and a person must measure it in a retained bundle image "
        "(1 bundle at frame 300 of the nominal run) - see OBSERVABLES.md",
        {"records": len(recs)})


@case("VC-DRIVING-006", ("closedLoopRoute",), needs=("C2",))
def vc006(run: Run) -> Result:
    """map_context: 14 channels, 450x300, right geometry, rendered no more than
    500 ms of simulation time before the step (REQ-006).

    A11 adds mapContext to the per-step C2 record; the render time is C2's
    map_context_render_sim_ms. A run before A11 carries no mapContext and the
    case stays inconclusive.
    """
    vc = "VC-DRIVING-006"
    recs = plan_steps(run)
    no_meta = [s["frame"] for s in recs if s["map_context"] is None]
    if no_meta:
        return inconclusive(
            vc, "checkpointInputs.mapContext {channels, width, height, geometry}", "C2",
            f"{len(no_meta)} of {len(recs)} steps carry no mapContext (runs before "
            "A11); the raster itself is only in the sampled bundles",
            {"records": len(recs), "steps_without_mapContext": len(no_meta)})
    hw = THRESHOLDS["map_context_shape_hw"]
    geometry = THRESHOLDS["map_context_geometry"]
    age_limit = THRESHOLDS["map_context_render_age_s"]
    bad_records = []
    worst_age = None
    evid = []
    for step in recs:
        mc = step["map_context"]
        problems = []
        if mc.get("channels") != THRESHOLDS["map_context_channels"]:
            problems.append(f"channels {mc.get('channels')}")
        if (mc.get("height"), mc.get("width")) != tuple(hw):
            problems.append(f"shape {mc.get('height')}x{mc.get('width')}")
        if mc.get("geometry") != geometry:
            problems.append(f"geometry {mc.get('geometry')!r}")
        rt = step["map_context_render_sim_ms"]
        if rt is None:
            problems.append("no render time")
        else:
            age = (step["sim_ms"] - rt) / 1000.0
            worst_age = age if worst_age is None else max(worst_age, age)
            if age < 0.0:
                problems.append(f"render {age:.3f} s in the future")
            elif age > age_limit:
                problems.append(f"render age {age:.3f} s")
        if problems:
            bad_records.append({"frame": step["frame"], "problems": problems})
        if len(evid) < 2:
            evid.append(ev(step["file"], step["rec"]))
    measured = {"records": len(recs), "records_with_a_problem": len(bad_records),
                "problems": bad_records[:5], "worst_render_age_s": worst_age}
    th = {"channels": THRESHOLDS["map_context_channels"], "shape_hw": hw,
          "geometry": geometry, "render_age_s": age_limit}
    if bad_records:
        return bad(vc, measured, th, evid)
    return ok(vc, measured, th, evid,
              ["mapContext is the producer's statement; the raster itself is only "
               "in the sampled bundles"])


def _llround(v: float) -> int:
    """std::llround: halves away from zero."""
    return int(math.floor(abs(v) + 0.5)) * (1 if v >= 0 else -1)


def route_centre_line_points(waypoints: list) -> list:
    """The points of the route's centre lines, as the navigation library builds
    them: one centre line per run of constant road id (waypoint[3], rounded as
    std::llround) with two or more points; a run of one point is dropped
    (navigation/navigation_raster.cpp:815-827). The producer counts these
    points (agent/cc/navigation_input.cpp:108-124)."""
    out: list = []
    start = 0
    for i in range(1, len(waypoints) + 1):
        if i == len(waypoints) or _llround(waypoints[i][3]) != _llround(waypoints[start][3]):
            if i - start >= 2:
                out.extend(waypoints[start:i])
            start = i
    return out


def route_waypoints_in_window(waypoints: list, pose: dict) -> int:
    """A16: how many route centre-line points fall in the 450x300 window.

    `pose` is the REF pose both rasters were rendered at. A point's position
    in the raster frame is ex forward and ey left; the window is the geometry
    window shrunk by two pixels, and the bounds are strict.
    """
    x0 = float(pose["x_map_m"])
    y0 = float(pose["y_map_m"])
    yaw = float(pose["yaw_map_rad"])
    c, s = math.cos(yaw), math.sin(yaw)
    f_lo, f_hi = THRESHOLDS["map_window_forward_m"]
    l_lo, l_hi = THRESHOLDS["map_window_lateral_m"]
    m = THRESHOLDS["map_window_margin_m"]
    n = 0
    for wp in waypoints:
        dx = float(wp[0]) - x0
        dy = float(wp[1]) - y0
        ex = c * dx + s * dy
        ey = -s * dx + c * dy
        if f_lo + m < ex < f_hi - m and l_lo + m < ey < l_hi - m:
            n += 1
    return n


@case("VC-DRIVING-007", ("closedLoopRoute",), needs=("C2",))
def vc007(run: Run) -> Result:
    """route_mask: two channels, 450x300, right geometry, and the corridor
    covers the route navigation gave (REQ-007).

    A11 adds routeMask to the per-step C2 record; A16 adds the waypoint counts
    and the raster pose, so the in-window count can be re-derived from the
    route file and compared with the producer's own count. The counts cannot
    reveal a left-right mirrored raster (A16); only a retained bundle can.
    """
    import hashlib
    import json

    vc = "VC-DRIVING-007"
    recs = plan_steps(run)
    no_mask = [s["frame"] for s in recs if s["route_mask"] is None]
    no_pose = [s["frame"] for s in recs if s["raster_pose"] is None]
    if no_mask or no_pose:
        missing = []
        if no_mask:
            missing.append("checkpointInputs.routeMask {channels, width, height, "
                           "geometry, waypointsInWindow, waypointsOnCorridor}")
        if no_pose:
            missing.append("checkpointInputs.rasterPose {x_map_m, y_map_m, yaw_map_rad}")
        return Result(vc, INCONCL,
                      {"records": len(recs), "steps_without_routeMask": len(no_mask),
                       "steps_without_rasterPose": len(no_pose)},
                      missing=missing, icd_changes=["C2"],
                      notes=["runs before A11/A16 carry neither field"])

    rec_route = run.record.get("route")
    rec_sha = rec_route.get("sha256") if isinstance(rec_route, dict) else None
    # Without a route in the run record, each step is compared with the
    # announcement in force at it: the newest one issued at or before the step.
    announced = sorted(((a["issue_s"], a["sha"]) for a in run.route_announcements()
                        if isinstance(a.get("sha"), str) and a["sha"]
                        and a.get("issue_s") is not None), key=lambda x: x[0])
    issue_times = [t for t, _ in announced]

    def sha_in_force(step_ms: int) -> str | None:
        import bisect
        i = bisect.bisect_right(issue_times, step_ms / 1000.0 + 1e-9) - 1
        return announced[i][1] if i >= 0 else None

    if isinstance(rec_sha, str) and rec_sha:
        route_sha, sha_source = rec_sha, "run_record.route.sha256"
    elif announced:
        route_sha = sorted({sha for _, sha in announced})   # each step: the one in force
        sha_source = "route_announcement.routeSha256"
    else:
        return Result(vc, INCONCL, {"records": len(recs)},
                      missing=["run_record.route.sha256 or route_provider "
                               "out.route_announcement.routeSha256"],
                      icd_changes=["C7"],
                      notes=["the run names no route sha256, so the mask cannot be "
                             "tied to the route navigation gave"])

    plan_frames = {plan_frame(p) for p in run.plans(required=False)}
    hw = THRESHOLDS["route_mask_shape_hw"]
    geometry = THRESHOLDS["map_context_geometry"]
    mask_problems = []
    sha_mismatches = []
    corridor_mismatches = []
    window_steps = 0
    corridor_cells = []
    evid = []
    for step in recs:
        rm = step["route_mask"]
        rp = step["raster_pose"]
        for key in ("x_map_m", "y_map_m", "yaw_map_rad"):
            v = rp.get(key)
            if not isinstance(v, (int, float)) or isinstance(v, bool) \
                    or not math.isfinite(float(v)):
                raise RunFormatError(f"checkpointInputs.rasterPose.{key} is not a "
                                     f"finite number at frame {step['frame']}")
        problems = []
        if rm.get("channels") != THRESHOLDS["route_mask_channels"]:
            problems.append(f"channels {rm.get('channels')}")
        if (rm.get("height"), rm.get("width")) != tuple(hw):
            problems.append(f"shape {rm.get('height')}x{rm.get('width')}")
        if rm.get("geometry") != geometry:
            problems.append(f"geometry {rm.get('geometry')!r}")
        wiw = rm.get("waypointsInWindow")
        woc = rm.get("waypointsOnCorridor")
        if not isinstance(wiw, int) or isinstance(wiw, bool):
            problems.append(f"waypointsInWindow {wiw!r}")
            wiw = None
        if not isinstance(woc, int) or isinstance(woc, bool):
            problems.append(f"waypointsOnCorridor {woc!r}")
            woc = None
        if rm.get("corridorCells") is not None:
            corridor_cells.append(rm.get("corridorCells"))
        if wiw is not None:
            if wiw > 0:
                window_steps += 1
            if wiw > 0 and woc is not None and woc != wiw:
                corridor_mismatches.append({"frame": step["frame"],
                                            "waypointsInWindow": wiw,
                                            "waypointsOnCorridor": woc})
        sha = rm.get("routeSha256")
        expected = route_sha if isinstance(route_sha, str) else sha_in_force(step["sim_ms"])
        if sha is None or sha == "":
            # no accepted route: never on a plan step, and both counts 0 (A16)
            if step["frame"] in plan_frames:
                sha_mismatches.append({"frame": step["frame"], "recorded": None,
                                       "reason": "a plan step without a route sha256"})
            elif (wiw or 0) > 0 or (woc or 0) > 0:
                sha_mismatches.append({"frame": step["frame"], "recorded": None,
                                       "reason": "waypoints counted but no route sha256"})
        elif sha != expected:
            sha_mismatches.append({"frame": step["frame"], "recorded": sha,
                                   "expected": expected})
        if problems:
            mask_problems.append({"frame": step["frame"], "problems": problems})
        if len(evid) < 2:
            evid.append(ev(step["file"], step["rec"]))

    # A16 recount: the route file the run names, if retained and its sha256
    # matches, gives the in-window count independently of the producer.
    def resolve(rel: str):
        p = run.path(rel)
        if p.exists():
            return p
        shared = run.root.parent / Path(rel).name      # one copy per campaign
        return shared if shared.exists() else None

    waypoints = None
    recount_why = None
    if not (isinstance(rec_route, dict) and isinstance(rec_route.get("path"), str)):
        recount_why = "the run record names no route file"
    elif not (isinstance(rec_route.get("sha256"), str) and rec_route["sha256"]):
        recount_why = "the run record names no route sha256"
    else:
        p = resolve(rec_route["path"])
        if p is None:
            recount_why = (f"{rec_route['path']} is not retained in the run or "
                           "campaign dir")
        else:
            got = hashlib.sha256(p.read_bytes()).hexdigest()
            if got != rec_route["sha256"]:
                recount_why = (f"the retained route file hashes to {got}, not "
                               f"{rec_route['sha256']}")
            else:
                try:
                    doc = json.loads(p.read_text())
                except json.JSONDecodeError as exc:
                    raise RunFormatError(f"{rec_route['path']}: {exc}") from exc
                wps = doc.get("waypoints") if isinstance(doc, dict) else None
                if not isinstance(wps, list) or not all(
                        isinstance(w, list) and len(w) == 4
                        and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                                for v in w) for w in wps):
                    raise RunFormatError(
                        f"{rec_route['path']}: waypoints is not a list of "
                        "[x, y, heading_rad, road_id] (ICD section 9)")
                waypoints = route_centre_line_points(wps)

    recount_mismatches = []
    frames_compared = 0
    if waypoints is not None:
        for step in recs:
            if not step["route_mask"].get("routeSha256"):
                continue      # no accepted route: A16 fixes both counts at 0
            n = route_waypoints_in_window(waypoints, step["raster_pose"])
            frames_compared += 1
            recorded = step["route_mask"].get("waypointsInWindow")
            if recorded != n:
                recount_mismatches.append({"frame": step["frame"],
                                           "recorded": recorded, "recounted": n})

    measured = {"steps": len(recs), "route_sha": route_sha,
                "route_sha_source": sha_source,
                "steps_with_a_route_sha": sum(
                    1 for s in recs if s["route_mask"].get("routeSha256")),
                "steps_with_waypoints_in_window": window_steps,
                "mask_problems": mask_problems[:5],
                "sha_mismatches": sha_mismatches[:10],
                "corridor_mismatches": corridor_mismatches[:10],
                "corridor_cells": {"min": min(corridor_cells) if corridor_cells else None,
                                   "max": max(corridor_cells) if corridor_cells else None},
                "recount_done": waypoints is not None,
                "recount_frames": frames_compared,
                "recount_mismatches": recount_mismatches[:10],
                "recount_skipped_because": recount_why}
    th = {"channels": THRESHOLDS["route_mask_channels"], "shape_hw": hw,
          "geometry": geometry, "route_sha256": route_sha,
          "window_forward_m": THRESHOLDS["map_window_forward_m"],
          "window_lateral_m": THRESHOLDS["map_window_lateral_m"],
          "window_margin_m": THRESHOLDS["map_window_margin_m"]}
    if mask_problems:
        return bad(vc, measured, th, evid,
                   ["the route_mask metadata is not the geometry the case requires"])
    if sha_mismatches:
        return bad(vc, measured, th, evid,
                   ["a step's routeSha256 is not the route sha256 the run names"])
    if corridor_mismatches:
        return bad(vc, measured, th, evid,
                   ["a step has fewer waypoints on the corridor than in the window"])
    if window_steps == 0:
        return bad(vc, measured, th, evid,
                   ["no step has a route waypoint inside the BEV window, so the "
                    "corridor covers no part of the route"])
    if recount_mismatches:
        return bad(vc, measured, th, evid,
                   [f"{len(recount_mismatches)} steps differ between the recorded "
                    "waypointsInWindow and the A16 recount from the route file"])
    notes = ["waypointsInWindow/waypointsOnCorridor are the producer's counts; the "
             "recount re-derives the window count from the retained route file and "
             "rasterPose" if waypoints is not None
             else f"recount not done: {recount_why}"]
    notes.append("a left-right mirrored raster is not detectable from counts (A16); "
                 "the raster itself is only in the sampled bundles")
    notes.append(f"the route sha256 comes from {sha_source}"
                 + ("" if isinstance(route_sha, str) else
                    ", the announcement in force at each step"))
    return ok(vc, measured, th, evid, notes)


@case("VC-DRIVING-008", ("closedLoopRoute",), needs=("C1", "C2"))
def vc008(run: Run) -> Result:
    """The 64-sample ego-motion history of every plan: oldest first, the newest
    100 ms before the step, speed and acceleration within their tolerances of
    the source's, and yaw rate and curvature given as zero (REQ-DRIVING-008 as
    amended on 2026-11-10).

    C2 records the rows as 64 x 4 values, oldest first. The reference comes
    from the C1 `egoPose` of the 66 frames step-65 .. step, moved to the origin
    of the camera rig (drivingAgent `rig` record) and worked out the source's
    way (`source_speed_acceleration`); row j is frame step-64+j. The speed and
    acceleration the simulator reports are not read. A record with a missing
    tick in its 66 frames has a problem. Only the steps with a plan are judged.
    """
    vc = "VC-DRIVING-008"
    recs = plan_steps(run)
    origin, rig_rec = rig_origin(run)
    wb = run.world_by_frame()
    worst = {"speed": 0.0, "accel": 0.0, "yaw": 0.0, "curv": 0.0}
    bad_records = []
    evid = [ev("score/drivingAgent.jsonl", rig_rec)]
    for step in recs:
        f = step["frame"]
        hist = step["ego_motion_history"]
        problems = []
        frames = ego_pose_frames(f)
        if len(hist) != THRESHOLDS["ego_history_len"]:
            problems.append(f"{len(hist)} samples")
        elif any(not isinstance(row, list) or len(row) != 4 for row in hist):
            k = next(k for k, row in enumerate(hist)
                     if not isinstance(row, list) or len(row) != 4)
            problems.append(f"row {k} is not four values")
        elif any(g not in wb for g in frames):
            problems.append(f"no world tick for frame {next(g for g in frames if g not in wb)}")
        else:
            poses = [[float(wd_get(wb[g], "egoPose", key)) for key in ("x", "y", "yaw")]
                     for g in frames]
            speed, accel = source_speed_acceleration(poses, origin)
            # JSON null is a non-finite value (ICD section 6): never within a tolerance
            rows = np.array([[float("nan") if v is None else float(v) for v in row]
                             for row in hist], dtype=np.float64)
            dv = np.abs(rows[:, 0] - speed)
            da = np.abs(rows[:, 1] - accel)
            dy = np.abs(rows[:, 2] - THRESHOLDS["ego_yaw_given_radps"])
            dc = np.abs(rows[:, 3] - THRESHOLDS["ego_curvature_given_1pm"])
            for key, err in (("speed", dv), ("accel", da), ("yaw", dy), ("curv", dc)):
                finite = err[np.isfinite(err)]
                if finite.size:
                    worst[key] = max(worst[key], float(finite.max()))
            within = ((dv <= THRESHOLDS["ego_speed_tol_mps"] + 1e-9)
                      & (da <= THRESHOLDS["ego_accel_tol_mps2"] + 1e-9)
                      & (dy == 0.0) & (dc == 0.0))
            if not within.all():
                k = int(np.argmin(within))
                problems.append(f"sample frame {ego_row_frame(f, k)}: dv={dv[k]:.3f} "
                                f"da={da[k]:.3f} dyaw={dy[k]:.3f} dcurv={dc[k]:.4f}")
        if problems:
            bad_records.append({"frame": f, "problems": problems})
        if len(evid) < 3:
            evid.append(ev(step["file"], step["rec"]))
    measured = {"records": len(recs), "worst_abs_error": worst,
                "records_with_a_problem": len(bad_records), "problems": bad_records[:5],
                "rig_origin_m": origin}
    th = {"samples": THRESHOLDS["ego_history_len"], "spacing_s": STEP_S,
          "poses_per_record": EGO_POSE_WINDOW,
          "speed_tol_mps": THRESHOLDS["ego_speed_tol_mps"],
          "accel_tol_mps2": THRESHOLDS["ego_accel_tol_mps2"],
          "yaw_rate_given_radps": THRESHOLDS["ego_yaw_given_radps"],
          "curvature_given_1pm": THRESHOLDS["ego_curvature_given_1pm"]}
    notes = ["the reference speed and acceleration are worked out from the C1 poses at "
             "the rig origin, as upstream's closed-loop driver works them out; the "
             "simulator's reported speed and acceleration are not read"]
    if bad_records:
        return bad(vc, measured, th, evid, notes)
    return ok(vc, measured, th, evid, notes)


@case("VC-DRIVING-009", ("closedLoopRoute",), needs=("C1", "C2", "C9"))
def vc009(run: Run) -> Result:
    """The vehicle is held at standstill until eight images per camera at 0.5 s
    and 64 motion samples exist, then released (REQ-009).

    The release frame is the first step the engine conditioned and reports
    primed (C2 `primed`, ICD A26). History references and sample counts do not
    show it: the agent writes the references every step, and an unconditioned
    step makes the engine prime again.
    """
    vc = "VC-DRIVING-009"
    steps = run.input_steps()
    wb = run.world_by_frame()
    # The engine says when its histories are complete: C2 `primed` (ICD A26).
    # A step it did not condition is never primed, so a record that says so is
    # not trusted (a pre-A26 fallback).
    primed = [s for s in steps if s["primed"] is True and s["conditioned"] is not False]
    if not primed:
        return inconclusive(vc, "checkpointInputs.primed on a conditioned step", "C2",
                            "no step records that the engine's histories were complete "
                            "(ICD A26)", {"steps": len(steps)})
    release = primed[0]["frame"]
    held_bad, moved_bad = [], []
    for a in run.actuations():
        t = a["actuation_s"]
        if t is None or t >= release * STEP_S - 1e-9:
            continue
        if a["applied"] and (a["accel"] or 0.0) > 0.05:
            held_bad.append({"t": t, "accel": a["accel"]})
    for f in sorted(wb):
        if f < release and float(wd_get(wb[f], "velocity", "speed_mps")) * 3.6 \
                > THRESHOLDS["standstill_kmh"]:
            moved_bad.append(f)
    after = [a for a in run.actuations()
             if a["actuation_s"] is not None and a["actuation_s"] >= release * STEP_S
             and a["applied"] and (a["accel"] or 0.0) > 0.05]
    moved_after = [f for f in sorted(wb) if f >= release
                   and float(wd_get(wb[f], "velocity", "speed_mps")) * 3.6
                   > THRESHOLDS["standstill_kmh"]]
    measured = {"release_frame": release,
                "release_source": "first C2 step with primed true (ICD A26)",
                "commands_above_zero_before_release": held_bad[:5],
                "moving_frames_before_release": moved_bad[:5],
                "first_accelerating_command_after_release":
                    after[0]["actuation_s"] if after else None,
                "moving_frames_after_release": len(moved_after)}
    th = {"camera_images": 8, "camera_spacing_s": 0.5,
          "motion_samples": 64, "standstill_kmh": THRESHOLDS["standstill_kmh"]}
    evid = [ev(a["file"], a["rec"]) for a in after[:1]] + \
           [ev(steps[0]["file"], steps[0]["rec"])]
    if moved_bad or held_bad:
        return bad(vc, measured, th, evid,
                   ["the vehicle moved or a positive command was issued before the "
                    "histories were complete"])
    if not after or not moved_after:
        return bad(vc, measured, th, evid,
                   ["the vehicle was not released after the histories were complete"])
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-010", ("closedLoopRoute",), needs=("C2", "C1"))
def vc010(run: Run) -> Result:
    """Every image and sample in a history names a capture record of the run and
    no capture record appears twice in one history (REQ-010).

    C2 gives camera history references as frame indices (a capture record is
    the (camera, frame) pair; the world tick proves the frame exists). The ego
    rows carry no id, so their identity is positional: row k is frame
    step-64+k (agent DESIGN.md, "Ego-motion history"). That convention is
    stated in OBSERVABLES.md. A camera the step's record lacks
    (cameras_missing) gave the checkpoint images with no capture record.
    """
    vc = "VC-DRIVING-010"
    steps = plan_steps(run)
    wb = run.world_by_frame()
    unknown, dups, lacking = [], [], []
    evid = []
    for step in steps:
        f = step["frame"]
        lack = cameras_missing(step["cameras"])
        if lack:
            lacking.append({"frame": f, "problem": lack["text"]})
        for c in step["cameras"]:
            refs = c.get("history") or []
            if len(refs) != len(set(refs)):
                dups.append({"frame": f, "camera": c.get("name")})
            for r in refs:
                if not isinstance(r, int) or r < 0 or r >= f or r not in wb:
                    unknown.append({"frame": f, "camera": c.get("name"),
                                    "captureFrame": r})
        rows = step["ego_motion_history"]
        if len(rows) != 64:
            dups.append({"frame": f, "camera": "ego-motion",
                         "problem": f"{len(rows)} rows"})
        frames = [ego_row_frame(f, k) for k in range(len(rows))]
        if len(frames) != len(set(frames)) or any(x < 0 or x not in wb for x in frames):
            unknown.append({"frame": f, "sampleFrames": frames[:2] + frames[-2:]})
        if len(evid) < 2:
            evid.append(ev(step["file"], step["rec"]))
    measured = {"records": len(steps),
                "unknown_capture_records": unknown[:5],
                "duplicated_in_one_history": dups[:5],
                "steps_without_the_six_cameras": lacking[:5]}
    th = {"duplicates_per_history": 0, "ego_row_identity": "positional frame",
          "cameras": CAMERAS}
    if unknown or dups or lacking:
        notes = []
        if lacking:
            notes.append(f"{len(lacking)} plan steps do not hold the six cameras: the "
                         f"images given for a missing one have no capture record of the run")
        if unknown:
            notes.append("history elements with no capture record of the run")
        if dups:
            notes.append("a capture record appears twice in one history")
        return bad(vc, measured, th, evid, notes)
    return ok(vc, measured, th, evid,
              ["ego rows are identified by their position, not by a recorded id"])


@case("VC-DRIVING-011", ("closedLoopRoute",), needs=("C1", "C8"))
def vc011(run: Run) -> Result:
    """Every command names its plan and that plan its inference, no autopilot,
    traffic-manager, recorded or scripted control reached the actuation, and a
    test plan of opposite curvature reverses the steering within 100 ms
    (REQ-011)."""
    vc = "VC-DRIVING-011"
    commands = run.commands()
    plans = {p["reference"]: p for p in run.plans_in("score/drivingAgent.jsonl", "in.plan")}
    modes = {m["frame"]: enum_name(m["mode"], MODES) for m in run.modes()}
    ckpt = run.record.get("checkpointSha256")
    unmatched, wrong_prod = [], []
    evid = []
    for c in commands:
        f = c["step_frame"]
        if f is not None and modes.get(f) not in (None, "kDriving"):
            continue                      # stop-response and priming commands name no plan
        p = plans.get(c["reference"])
        if not c["reference"] or p is None:
            unmatched.append({"frame": f, "planReference": c["reference"]})
            continue
        if not p.get("producer") or p.get("run_record") != run.identity() or not ckpt:
            wrong_prod.append({"frame": f, "producer": p.get("producer")})
        if len(evid) < 3:
            evid.append(ev(c["file"], c["rec"]))
    # no other control reached the actuation
    wb = run.world_by_frame()
    foreign = []
    for f, rec in wb.items():
        d = rec["data"]
        src = d.get("controlSource")
        if src is None:
            raise MissingEvidence("simulator/world.jsonl:controlSource", "C1",
                                  "the world tick does not say where the applied control "
                                  "came from")
        if src != "actuationAdapter" or d.get("autopilotEnabled") \
                or d.get("trafficManagerEnabled"):
            foreign.append({"frame": f, "controlSource": src,
                            "autopilot": d.get("autopilotEnabled"),
                            "trafficManager": d.get("trafficManagerEnabled")})
    # the test plan of opposite curvature sign
    inj = [i for i in run.injections() if i["action"] == "plan_inject"
           and (i["detail"].get("reason") or "").startswith("REQ-011")]
    if not inj:
        return inconclusive(vc, "bench/injection.jsonl:REQ-011 test plan", "C8",
                            "no record of the test plan of opposite curvature sign")
    T = inj[0]["t_sim"]
    acts = [a for a in run.actuations() if a["actuation_s"] is not None]
    before = [a for a in acts if a["actuation_s"] < T - 1e-9]
    window = [a for a in acts if T - 1e-9 <= a["actuation_s"] <= T + 0.1 + 1e-9]
    reversed_at = None
    if before and window:
        s0 = before[-1]["steer"]
        for a in window:
            if s0 is not None and a["steer"] is not None and abs(a["steer"]) > 0.05 \
                    and math.copysign(1, a["steer"]) != math.copysign(1, s0):
                reversed_at = a["actuation_s"] - T
                break
    measured = {"commands": len(commands), "commands_without_plan": unmatched[:5],
                "plans_without_inference_identity": wrong_prod[:5],
                "foreign_control_ticks": foreign[:5],
                "test_plan_sim_s": T, "steering_reversed_after_s": reversed_at}
    th = {"reversal_latency_s": 0.10, "control_source": "actuationAdapter"}
    if unmatched or wrong_prod:
        return inconclusive(vc, "command -> plan -> inference chain", "C8",
                            "the chain cannot be closed from the records", measured)
    if foreign:
        return bad(vc, measured, th, evid,
                   ["a control that is not the driving system's reached the vehicle"])
    if reversed_at is None:
        return bad(vc, measured, th, evid,
                   ["the steering sign did not reverse after the test plan"])
    if reversed_at > 0.1 + 1e-9:
        return bad(vc, measured, th, evid,
                   [f"the steering sign reversed {reversed_at * 1000:.0f} ms after the "
                    "test plan, limit 100 ms"])
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-012", ("closedLoopRoute",), needs=("C7", "C8", "C9"))
def vc012(run: Run) -> Result:
    """Every command stays inside the limits the configuration names, under test
    plans that exceed them (REQ-012)."""
    vc = "VC-DRIVING-012"
    limits = run.limits()
    inj = [i for i in run.injections() if i["action"] == "plan_inject"
           and (i["detail"].get("reason") or "").startswith("REQ-012")]
    if not inj:
        return inconclusive(vc, "bench/injection.jsonl:REQ-012 test plan", "C8",
                            "no record of a test plan that exceeds the limits")
    over = float(limits["max_acceleration_mps2"])
    dec = float(limits["max_deceleration_mps2"])
    ang = float(limits["max_road_wheel_angle_deg"])
    rate = float(limits["max_steering_rate_deg_per_s"])
    violations = []
    prev = None
    for a in run.actuations():
        if not a["applied"] or a["accel"] is None:
            continue
        if a["accel"] > over + 1e-6 or a["accel"] < -dec - 1e-6:
            violations.append({"t": a["actuation_s"], "acceleration": a["accel"]})
        if a["steer"] is not None and abs(a["steer"]) > ang + 1e-6:
            violations.append({"t": a["actuation_s"], "steeringAngle": a["steer"]})
        if prev is not None and a["steer"] is not None and prev["steer"] is not None:
            dt = (a["actuation_s"] or 0) - (prev["actuation_s"] or 0)
            if dt > 1e-9 and abs(a["steer"] - prev["steer"]) / dt > rate + 1e-6:
                violations.append({"t": a["actuation_s"],
                                   "steering_rate": abs(a["steer"] - prev["steer"]) / dt})
        prev = a
    measured = {"limits": limits, "actuations_checked": len(run.actuations()),
                "violations": violations[:5], "violation_count": len(violations),
                "test_plan_sim_s": inj[0]["t_sim"]}
    th = {"max_acceleration_mps2": over, "max_deceleration_mps2": dec,
          "max_road_wheel_angle_deg": ang, "max_steering_rate_deg_per_s": rate}
    evid = [ev(i["file"], i["rec"]) for i in inj[:1]]
    if violations:
        return bad(vc, measured, th, evid)
    return ok(vc, measured, th, evid)


def mode_in_force(run: Run):
    """The agent's mode at a step: its newest out.mode record at or before it."""
    import bisect
    modes = sorted((m["frame"], enum_name(m["mode"], MODES)) for m in run.modes()
                   if isinstance(m["frame"], int))
    frames = [f for f, _ in modes]

    def at(f: int) -> str | None:
        i = bisect.bisect_right(frames, f) - 1
        return modes[i][1] if i >= 0 else None
    return at


def window_cover_note(first: float, last: float, unit: str = "s") -> str | None:
    """A 60 s window needs records that span it (REQ-013/-015/-016/-017)."""
    span = last - first
    if span + STEP_S + 1e-9 < THRESHOLDS["window_s"]:
        return (f"the records span {span:.1f} {unit} of the 60 s window: the run cannot "
                "show the criterion")
    return None


@case("VC-DRIVING-013", ("closedLoopRoute",), needs=("C2", "C9", "C10", "C1"))
def vc013(run: Run) -> Result:
    """99 % of plans within 100 ms of wall-clock after their newest image was
    available, no two consecutive misses, real-time factor at least 0.95
    (REQ-013).

    The window is 60 s of wall clock from the end of priming (the agent's
    priming.complete record). Every plan in it must be a plan made while the
    agent drives, the plans must span it, and the real-time factor is taken
    over the same window; otherwise the run cannot show the criterion.
    """
    vc = "VC-DRIVING-013"
    stub = stub_engine_note(run)
    if stub:
        return inconclusive(vc, "a run of the checkpoint engine", None,
                            stub + "; its plan times say nothing about the driving system's")
    plans = run.plans()
    prime_recs = run.events("score/drivingAgent.jsonl", "priming.complete", required=False)
    if not prime_recs:
        raise MissingEvidence("score/drivingAgent.jsonl:priming.complete", "C10",
                              "the window starts at the end of priming")
    arr = {}
    for step in camera_views(run):
        arrivals = [c["arrival_mono_ns"] for c in step["cameras"]
                    if c.get("arrival_mono_ns") is not None]
        if arrivals:
            arr[step["frame"]] = max(arrivals) / 1e9   # newest image available
    if not arr:
        return inconclusive(vc, "checkpointInputs.cameras[].arrival_mono_ns", "C2",
                            "no monotonic arrival time for the camera images")
    arrivals = sorted(arr)
    wb = run.world_by_frame()
    t0 = prime_recs[0]["t_mono_ns"] / 1e9          # the agent host's monotonic clock
    t0_real = prime_recs[0]["t_real_ns"] / 1e9
    mode_at = mode_in_force(run)
    window = [p for p in plans if p["production_mono"] is not None
              and 0.0 <= p["production_mono"] - t0 <= THRESHOLDS["window_s"]]
    not_driving = [plan_frame(p) for p in window if mode_at(plan_frame(p)) != "kDriving"]
    cover = window_cover_note(t0, max((p["production_mono"] for p in window), default=t0))
    lat, misses, frames = [], [], []
    for p in window:
        f = plan_frame(p)
        cand = [a for a in arrivals if a <= f]
        if not cand:
            continue
        d = p["production_mono"] - arr[cand[-1]]
        lat.append(d)
        frames.append(f)
        if d > THRESHOLDS["planning_latency_s"] + 1e-9:
            misses.append(f)
    # real-time factor over the same window, from the pacer's own two stamps.
    # The ticks are written on the simulator host, so the window is selected on
    # the real-time clock of both hosts; the factor uses the ticks' own stamps.
    rtf = None
    ticks = sorted((r["t_real_ns"] / 1e9, r["data"]["sim_ms"] / 1000.0) for r in wb.values()
                   if 0.0 <= r["t_real_ns"] / 1e9 - t0_real <= THRESHOLDS["window_s"])
    if len(ticks) > 1:
        sim = ticks[-1][1] - ticks[0][1]
        real = ticks[-1][0] - ticks[0][0]
        rtf = sim / real if real > 0 else None
    streak = 0
    worst_streak = 0
    for f in frames:
        streak = streak + 1 if f in misses else 0
        worst_streak = max(worst_streak, streak)
    frac = 1.0 - (len(misses) / len(lat)) if lat else 0.0
    measured = {"plans_in_window": len(lat), "within_100ms": len(lat) - len(misses),
                "fraction_within": frac, "misses": misses[:10],
                "longest_consecutive_misses": worst_streak,
                "rtf": rtf, "worst_latency_s": max(lat) if lat else None,
                "window_start_frame": run.priming_frame(),
                "plans_not_driving_in_window": len(not_driving),
                "first_not_driving_frame": not_driving[0] if not_driving else None}
    th = {"planning_latency_s": THRESHOLDS["planning_latency_s"],
          "min_fraction": THRESHOLDS["planning_pass_fraction"],
          "max_consecutive_misses": 1, "rtf_min": THRESHOLDS["rtf_min"],
          "window_s": THRESHOLDS["window_s"]}
    if not_driving:
        return inconclusive(vc, "60 s of plans made while driving", None,
                            f"the agent did not drive at frame {not_driving[0]} within the "
                            "60 s window from the end of priming", measured)
    if cover:
        return inconclusive(vc, "60 s of plans made while driving", None, cover, measured)
    if rtf is None or rtf < THRESHOLDS["rtf_min"]:
        return inconclusive(vc, "a run at a real-time factor of at least 0.95", "C1",
                            "the real-time factor over the window is "
                            + ("not recorded" if rtf is None else f"{rtf:.3f}"), measured)
    evid = [ev(plans[0]["file"], plans[0]["rec"])]
    notes = []
    if frac < THRESHOLDS["planning_pass_fraction"]:
        notes.append(f"{frac * 100:.1f} % of plans within 100 ms")
    if worst_streak > 1:
        notes.append(f"{worst_streak} consecutive plans missed the period")
    if notes:
        return bad(vc, measured, th, evid, notes)
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-014", ("closedLoopRoute",), needs=("C8", "C9"))
def vc014(run: Run) -> Result:
    """Every command at the actuation matches its plan in the S-CORE records, and
    after the communication of the driving system is stopped no command computed
    from a plan reaches the actuation (REQ-014).

    An applied actuation state that names no plan is a command matched to no
    plan, before the stop and after it. Only the adapter's own stop
    (stopInForce) names none by design (actuation-adapter/adapter_core.cpp)."""
    vc = "VC-DRIVING-014"
    g = gate(run, vc)
    if g is not None:
        return g
    plans = {p["reference"]: p for p in run.plans()}
    agent_cmds = {c["reference"] for c in run.commands() if c["reference"]}
    adapter_cmds = run.adapter_commands()
    matched, unmatched = 0, []
    evid = []
    for a in run.actuations():
        if not a["applied"]:
            continue
        ref = a["reference"]
        if not ref:
            if not a["stop"]:
                unmatched.append({"t": a["actuation_s"], "planReference": ref})
            continue
        hop = [c for c in adapter_cmds if c["reference"] == ref]
        if ref in agent_cmds and ref in plans and hop:
            matched += 1
            if len(evid) < 3:
                evid.append(ev(a["file"], a["rec"]))
                evid.append(ev(hop[0]["file"], hop[0]["rec"]))
        else:
            unmatched.append({"t": a["actuation_s"], "planReference": ref})
    stops = [i for i in run.injections() if i["action"] == "comm_stop"]
    if not stops:
        if run.fault() != "comm_stop":
            return not_applicable(vc, "this run does not stop the S-CORE communication of "
                                      "the driving system; REQ-014 applies to that run")
        return inconclusive(vc, "bench/injection.jsonl:comm_stop", "C8",
                            "no record of the moment the S-CORE communication was stopped")
    T = stops[0]["t_sim"]
    after = []
    for a in run.actuations():
        if a["actuation_s"] is None or a["actuation_s"] <= T + 1e-9 or not a["applied"]:
            continue
        p = plans.get(a["reference"])
        if p is not None and (p["capture_ms"] or 0) / 1000.0 > T + 1e-9:
            after.append({"t": a["actuation_s"], "planReference": a["reference"]})
    measured = {"commands_matched": matched, "commands_unmatched": unmatched[:5],
                "comm_stop_sim_s": T, "plan_derived_actuations_after_stop": after[:5]}
    th = {"comm_stop_required": True, "unmatched_allowed": 0}
    evid.append(ev(stops[0]["file"], stops[0]["rec"]))
    if unmatched:
        return bad(vc, measured, th, evid,
                   ["a command reached the actuation without its plan in the S-CORE records"])
    if after:
        return bad(vc, measured, th, evid,
                   ["a command computed from a plan reached the actuation after the stop"])
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-015", ("closedLoopRoute",), needs=("C12",))
def vc015(run: Run) -> Result:
    """Each plan published once, equal to its record, with its own producer and
    production time, within 100 ms of wall clock after production (REQ-015).

    ICD v2 C12 puts plan_producer, plan_sample_count and plan_horizon on the
    PLAN publication; the evaluator requires them (the publication's `producer`
    is the publisher, statePublisher).
    """
    vc = "VC-DRIVING-015"
    plans = run.plans()
    pubs = run.plan_pubs()
    by_frame: dict[int, list[dict]] = {}
    for p in pubs:
        by_frame.setdefault(p["frame"], []).append(p)
    t0 = plans[0]["production_mono"]
    cover = window_cover_note(t0, max(p["production_mono"] for p in plans
                                      if p["production_mono"] is not None))
    if cover:
        return inconclusive(vc, "out.plan over a 60 s window", None, cover,
                            {"plans": len(plans)})
    problems = []
    checked = 0
    lat = []
    evid = [ev(plans[0]["file"], plans[0]["rec"])]
    for p in plans:
        if p["production_mono"] - t0 > THRESHOLDS["window_s"]:
            continue
        checked += 1
        got = by_frame.get(plan_frame(p), [])
        if len(got) != 1:
            problems.append({"frame": plan_frame(p), "publications": len(got)})
            continue
        q = got[0]
        if q["publish_mono"] is None or q["production_mono"] is None:
            problems.append({"frame": plan_frame(p),
                             "problem": "no publish/production monotonic time"})
            continue
        if q["plan_producer"] != p.get("producer"):
            problems.append({"frame": plan_frame(p),
                             "problem": f"plan_producer {q['plan_producer']!r} is not "
                                        f"{p.get('producer')!r}"})
        d = q["publish_mono"] - p["production_mono"]
        lat.append(d)
        if d > THRESHOLDS["plan_publish_latency_s"] + 1e-9:
            problems.append({"frame": plan_frame(p), "latency_s": d})
        acc = np.array([s["acceleration"] for s in p["samples"]], dtype=float)
        cur = np.array([s["curvature"] for s in p["samples"]], dtype=float)
        pa = np.array(q["accel"], dtype=float)
        pc = np.array(q["curv"], dtype=float)
        if pa.size != acc.size or pc.size != cur.size \
                or not np.allclose(pa, acc, atol=1e-6) or not np.allclose(pc, cur, atol=1e-6):
            problems.append({"frame": plan_frame(p), "problem": "published plan differs "
                                                             "from the plan record"})
        if q["reference"] != p["reference"]:
            problems.append({"frame": plan_frame(p), "problem": "plan reference differs"})
        if q["sample_count"] != p.get("sample_count"):
            problems.append({"frame": plan_frame(p),
                             "problem": "plan_sample_count differs from the record"})
        if len(evid) < 3:
            evid.append(ev(q["file"], q["rec"]))
    if any(q.get("plan_producer") in (None, "") for q in pubs):
        return inconclusive(vc, "rx.plan.plan_producer/plan_sample_count/plan_horizon",
                            "C12", "the PLAN publication does not carry the plan's "
                                   "producer and completeness", {"publications": len(pubs)})
    measured = {"plans_in_window": checked, "publications": len(pubs),
                "worst_latency_s": max(lat) if lat else None,
                "problems": problems[:5], "problem_count": len(problems)}
    th = {"publish_latency_s": THRESHOLDS["plan_publish_latency_s"],
          "publications_per_plan": 1, "array_tol": 1e-6}
    if problems:
        return bad(vc, measured, th, evid,
                   [f"{len(problems)} plans not published as required, first "
                    f"{problems[0]}"])
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-016", ("closedLoopRoute",), needs=("C9",))
def vc016(run: Run) -> Result:
    """The motion sample of every step published once, equal to its record, with
    producer and sample time, within 100 ms after receipt (REQ-016)."""
    vc = "VC-DRIVING-016"
    samples = run.ego_samples()
    pubs = run.vs_pubs()
    if samples and all(s["capture_ms"] is None for s in samples):
        raise MissingEvidence("out.ego_motion_sample.clocks.captureTime", "C9",
                              "motion samples carry no simulation capture stamp")
    by_capture: dict[float, list[dict]] = {}
    for p in pubs:
        if p["sample_capture_ms"] is not None:
            by_capture.setdefault(round(p["sample_capture_ms"], 3), []).append(p)
    t0 = samples[0]["capture_ms"]
    cover = window_cover_note(t0 / 1000.0, max(s["capture_ms"] for s in samples
                                                if s["capture_ms"] is not None) / 1000.0)
    if cover:
        return inconclusive(vc, "out.ego_motion_sample over a 60 s window", None, cover,
                            {"samples": len(samples)})
    checked, problems, lat = 0, [], []
    evid = [ev(samples[0]["file"], samples[0]["rec"])]
    for s in samples:
        if s["capture_ms"] - t0 > THRESHOLDS["window_s"] * 1000:
            continue
        checked += 1
        got = by_capture.get(round(s["capture_ms"], 3), [])
        if len(got) != 1:
            problems.append({"capture_ms": s["capture_ms"], "publications": len(got)})
            continue
        q = got[0]
        if q["publish_mono"] is None or q["receipt_mono"] is None:
            problems.append({"capture_ms": s["capture_ms"],
                             "problem": "no publish/receipt time"})
            continue
        d = q["publish_mono"] - q["receipt_mono"]
        lat.append(d)
        if d > THRESHOLDS["sample_publish_latency_s"] + 1e-9:
            problems.append({"capture_ms": s["capture_ms"], "latency_s": d})
        if s["speed_kmh"] is not None and q["speed_kmh"] is not None \
                and abs(s["speed_kmh"] - q["speed_kmh"]) > 1e-3:
            problems.append({"capture_ms": s["capture_ms"], "problem": "speed differs"})
        if len(evid) < 3:
            evid.append(ev(q["file"], q["rec"]))
    measured = {"samples_in_window": checked, "publications": len(pubs),
                "worst_latency_s": max(lat) if lat else None,
                "problems": problems[:5], "problem_count": len(problems)}
    th = {"publish_latency_s": THRESHOLDS["sample_publish_latency_s"],
          "publications_per_sample": 1, "speed_tol_kmh": 1e-3}
    if problems:
        return bad(vc, measured, th, evid,
                   [f"{len(problems)} motion samples not published as required, first "
                    f"{problems[0]}"])
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-017", ("closedLoopRoute",), needs=("C5",))
def vc017(run: Run) -> Result:
    """Health at least every 200 ms of wall clock over a 60 s window, each with
    mode, cause while stopped and the age of the newest valid plan (REQ-017)."""
    vc = "VC-DRIVING-017"
    hs = run.health_pubs()
    if len(hs) < 2:
        return inconclusive(vc, "guest/observer.jsonl:rx.health", None,
                            "fewer than two health publications")
    t0 = hs[0]["t_real"]
    cover = window_cover_note(t0, hs[-1]["t_real"])
    if cover:
        return inconclusive(vc, "guest/observer.jsonl:rx.health over a 60 s window", None,
                            cover, {"publications": len(hs)})
    win = [h for h in hs if h["t_real"] - t0 <= THRESHOLDS["window_s"]]
    gaps = [b["t_real"] - a["t_real"] for a, b in zip(win, win[1:])]
    worst_gap = max(gaps) if gaps else None
    gap_bad = [{"after": win[i]["t_real"] - t0, "gap_s": g}
               for i, g in enumerate(gaps) if g > THRESHOLDS["health_period_s"] + 1e-9]
    age_missing = [h for h in win
                   if h["last_plan_capture_ms"] is None or h["step_capture_ms"] is None
                   or h["last_plan_production_mono"] is None]
    if age_missing:
        return inconclusive(vc, "rx.health.last_plan_capture_ms/step_capture_ms/"
                                "last_plan_production_mono_s", "C5",
                            f"{len(age_missing)} of {len(win)} health publications carry no "
                            "plan age", {"publications": len(win),
                                         "without_plan_age": len(age_missing)})
    field_bad = []
    for h in win:
        if h["mode"] is None or h["producer"] in (None, "") or h["publish_mono"] is None:
            field_bad.append({"t": h["t_real"] - t0, "problem": "mode/producer/time"})
        age = (h["step_capture_ms"] - h["last_plan_capture_ms"]) / 1000.0
        if age < -1e-9:
            field_bad.append({"t": h["t_real"] - t0, "problem": f"negative plan age {age}"})
        # The observer records the mode and the cause as their u32 values (ICD
        # section 3, fields 30-31; ivi-observer StateRecord.java:138-141 writes
        # the name only as mode_name and cause_name); a name is read as its value.
        if means_stopped(h["mode"]) and (h["cause"] is None
                                         or enum_name(h["cause"], CAUSES) == "kNone"):
            field_bad.append({"t": h["t_real"] - t0, "problem": "stopped without a cause"})
    measured = {"publications": len(win), "worst_gap_s": worst_gap,
                "gaps_over_200ms": gap_bad[:5], "window_s": THRESHOLDS["window_s"],
                "field_problems": field_bad[:5],
                "ages_s": [round((h["step_capture_ms"] - h["last_plan_capture_ms"]) / 1000.0, 3)
                           for h in win][:10]}
    th = {"health_period_s": THRESHOLDS["health_period_s"],
          "window_s": THRESHOLDS["window_s"]}
    evid = [ev(h["file"], h["rec"]) for h in win[:2]]
    if gap_bad:
        return bad(vc, measured, th, evid,
                   [f"a gap of {gap_bad[0]['gap_s'] * 1000:.0f} ms between health "
                    "publications, limit 200 ms"])
    if field_bad:
        return bad(vc, measured, th, evid,
                   [f"health publication without a required field: {field_bad[0]}"])
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-020", ("degradedInputOrPlan",), needs=("C1", "C9"))
def vc020(run: Run) -> Result:
    """Commanded deceleration of 4 m/s^2 within 0.2 from the start of the stop
    response to standstill (REQ-020)."""
    vc = "VC-DRIVING-020"
    begin, stand = stop_window(run)
    T0 = begin["t_sim"]
    T1 = stand["t_sim"] if stand else None
    acts = actuations_between(run, T0, T1)
    if not acts:
        if run.actuations() and all(a["actuation_s"] is None for a in run.actuations()):
            raise MissingEvidence("out.actuation_state.clocks.actuationTime", "C9",
                                  "actuation records carry no simulation-time stamp")
        return inconclusive(vc, "actuation between stop begin and standstill", None,
                            "no actuation record in the stop window")
    if T1 is None:
        return inconclusive(vc, "stop_response.standstill", None,
                            "the stop never reached standstill in this run")
    entry = _speed_mps(run, int(round(T0 / STEP_S)))
    bad_acts = [{"t": a["actuation_s"], "acceleration": a["accel"]}
                for a in acts if a["accel"] is None
                or abs(a["accel"] - THRESHOLDS["stop_deceleration_mps2"])
                > THRESHOLDS["stop_deceleration_tol_mps2"] + 1e-9]
    measured = {"entry_speed_mps": entry, "stop_begin_s": T0, "standstill_s": T1,
                "actuations": len(acts),
                "worst_deviation_mps2": max((abs(a["accel"]
                                                 - THRESHOLDS["stop_deceleration_mps2"])
                                             for a in acts if a["accel"] is not None),
                                            default=None),
                "violations": bad_acts[:5]}
    th = {"deceleration_mps2": THRESHOLDS["stop_deceleration_mps2"],
          "tolerance_mps2": THRESHOLDS["stop_deceleration_tol_mps2"]}
    evid = [ev(begin["file"], begin["rec"]), ev(stand["file"], stand["rec"])]
    if bad_acts:
        return bad(vc, measured, th, evid,
                   [f"{len(bad_acts)} actuations off 4 m/s^2 by more than 0.2, first "
                    f"{bad_acts[0]}"])
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-021", ("degradedInputOrPlan",), needs=("C9",))
def vc021(run: Run) -> Result:
    """Steering held at the last value computed from a valid plan, from the start
    of the stop response to standstill (REQ-021)."""
    vc = "VC-DRIVING-021"
    begin, stand = stop_window(run)
    if run.actuations() and all(a["actuation_s"] is None for a in run.actuations()):
        raise MissingEvidence("out.actuation_state.clocks.actuationTime", "C9",
                              "actuation records carry no simulation-time stamp")
    if stand is None:
        # the window ends at standstill; a run that never reaches it does not
        # show the whole window (VC-DRIVING-020 and -022 read it the same way)
        return inconclusive(vc, "stop_response.standstill", None,
                            "the stop never reached standstill in this run")
    T0 = begin["t_sim"]
    prev = [a for a in run.actuations()
            if a["actuation_s"] is not None and a["actuation_s"] < T0 - 1e-9
            and a["applied"] and a["reference"]]
    if not prev:
        return inconclusive(vc, "last valid-plan actuation before the stop", None,
                            "no actuation from a valid plan precedes the stop")
    held = prev[-1]["steer"]
    acts = actuations_between(run, T0, stand["t_sim"])
    if not acts:
        if run.actuations() and all(a["actuation_s"] is None for a in run.actuations()):
            raise MissingEvidence("out.actuation_state.clocks.actuationTime", "C9",
                                  "actuation records carry no simulation-time stamp")
        return inconclusive(vc, "actuation in the stop window", None, "no actuation records")
    dev = [{"t": a["actuation_s"], "steeringAngle": a["steer"],
            "deviation_deg": None if a["steer"] is None else abs(a["steer"] - held)}
           for a in acts if a["steer"] is None or abs(a["steer"] - held) > 1e-6]
    measured = {"held_steering_deg": held, "stop_begin_s": T0,
                "actuations": len(acts), "deviations": dev[:5],
                "deviation_count": len(dev)}
    th = {"steering_tol_deg": 1e-6}
    evid = [ev(begin["file"], begin["rec"])] + [ev(prev[-1]["file"], prev[-1]["rec"])]
    if dev:
        return bad(vc, measured, th, evid,
                   ["the steering command did not stay at the last valid value"])
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-022", ("degradedInputOrPlan",), needs=("C1", "C9"))
def vc022(run: Run) -> Result:
    """The vehicle stays at standstill to the end of the run and no command comes
    from a plan made after the stop response began (REQ-022)."""
    vc = "VC-DRIVING-022"
    begin, stand = stop_window(run)
    if run.actuations() and all(a["actuation_s"] is None for a in run.actuations()):
        raise MissingEvidence("out.actuation_state.clocks.actuationTime", "C9",
                              "actuation records carry no simulation-time stamp")
    if stand is None:
        return inconclusive(vc, "stop_response.standstill", None,
                            "the stop never reached standstill in this run")
    T0, T1 = begin["t_sim"], stand["t_sim"]
    wb = run.world_by_frame()
    moved = [{"frame": f, "speed_kmh": float(wd_get(r, "velocity", "speed_mps")) * 3.6}
             for f, r in wb.items() if f * STEP_S >= T1
             and float(wd_get(r, "velocity", "speed_mps")) * 3.6
             > THRESHOLDS["standstill_kmh"]]
    plans = {p["reference"]: p for p in run.plans() if p["reference"]}
    late_cmds = []
    for a in run.actuations():
        if a["actuation_s"] is None or a["actuation_s"] <= T0 + 1e-9:
            continue
        p = plans.get(a["reference"])
        if p is not None and (p["capture_ms"] or 0) / 1000.0 > T0 + 1e-9:
            late_cmds.append({"t": a["actuation_s"], "planReference": a["reference"],
                              "plan_capture_s": (p["capture_ms"] or 0) / 1000.0})
    tail = [f for f in sorted(wb) if f * STEP_S >= T1]
    # in the standstill the command is the stop response (ICD 4: -4 m/s^2, brake,
    # held until the run ends); a command that pulls the vehicle is not a hold
    pulling = [{"t": a["actuation_s"], "acceleration": a["accel"]}
               for a in run.actuations()
               if a["actuation_s"] is not None and a["actuation_s"] >= T1 - 1e-6
               and a["applied"] and (a["accel"] or 0.0) > 0.05]
    measured = {"standstill_s": T1, "ticks_after_standstill": len(tail),
                "moving_ticks": moved[:5], "commands_from_late_plans": late_cmds[:5],
                "pulling_commands_after_standstill": pulling[:5]}
    th = {"standstill_kmh": THRESHOLDS["standstill_kmh"],
          "plans_made_after_stop_allowed": 0,
          "acceleration_after_standstill_max_mps2": 0.05}
    evid = [ev(stand["file"], stand["rec"])]
    if pulling:
        return bad(vc, measured, th, evid,
                   [f"a command after standstill pulls the vehicle "
                    f"({pulling[0]['acceleration']:.2f} m/s^2)"])
    if moved:
        return bad(vc, measured, th, evid,
                   [f"the vehicle moved after standstill ({moved[0]['speed_kmh']:.2f} km/h)"])
    if late_cmds:
        return bad(vc, measured, th, evid,
                   ["a command was computed from a plan made after the stop began"])
    if not tail:
        return inconclusive(vc, "world ticks after standstill", None,
                            "the run ends at standstill with no tail to judge")
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-023", ("closedLoopRoute", "degradedInputOrPlan"), needs=("C2", "C10"))
def vc023(run: Run) -> Result:
    """Missing, invalid or more-than-200-ms-old camera images begin the stop
    response within 100 ms of simulation time (REQ-023).

    Both halves take the reading of the README ("Readings"): a camera is judged
    by its newest valid image, so a single late image is not a condition, and a
    camera-caused stop without a condition in the 100 ms before it fails. The
    baseline is the first condition at a step at or after priming.complete
    while the agent drives. On a run of SC-DRIVING-001 (the no-fault half) a
    run without such a condition passes; on a degraded run it is inconclusive.
    """
    vc = "VC-DRIVING-023"
    if run.scenario == "closedLoopRoute":
        return camera_by_reading(run, vc, fault_run=False)
    g = gate(run, vc)
    if g is not None:
        return g
    return camera_by_reading(run, vc, fault_run=True)


@case("VC-DRIVING-024", ("degradedInputOrPlan",), needs=("C9", "C10"))
def vc024(run: Run) -> Result:
    """An invalid or more-than-200-ms-old motion sample begins the stop response
    within 100 ms of simulation time (REQ-024).

    The baseline is the first motion condition at a step at or after
    priming.complete while the agent drives (README, Readings).
    """
    vc = "VC-DRIVING-024"
    g = gate(run, vc)
    if g is not None:
        return g
    samples = run.ego_samples()
    if samples and all(s["capture_ms"] is None for s in samples):
        raise MissingEvidence("out.ego_motion_sample.clocks.captureTime", "C9",
                              "motion samples carry no simulation capture stamp")
    if any(s.get("step") is None for s in samples):
        raise MissingEvidence("out.ego_motion_sample.frame", None,
                              "a motion sample does not name its step frame "
                              "(agent/cc/agent_ffi.cpp:1094)")
    prime, eligible = driving_after_priming(run)
    cond = None
    for s in samples:
        if not eligible(s["step"]):
            continue
        if s["valid"] is False or s["speed_kmh"] is None or not finite(s["speed_kmh"]):
            cond = (s["step"], "kMotionInvalid")
            break
    if cond is None:
        for s in samples:
            if s["capture_ms"] is None or not eligible(s["step"]):
                continue
            f = s["step"]     # the sample's own step frame, not its record index
            if (f * 100 - s["capture_ms"]) / 1000.0 > THRESHOLDS["motion_stale_s"] + 1e-9:
                cond = (f, "kMotionStale")
                break
    if cond is None:
        return inconclusive(vc, "a motion condition while the agent drove", None,
                            NOT_WHILE_DRIVING.format(what="motion"),
                            {"fault": run.fault(), "priming_frame": prime})
    frame, cause = cond
    res = stop_timing(run, frame, cause)
    res.vc = vc
    res.measured.update({"condition_frame": frame, "condition": cause})
    return res


@case("VC-DRIVING-025", ("degradedInputOrPlan",), needs=("C9", "C10"))
def vc025(run: Run) -> Result:
    """A route older than 1 s of simulation time or with no corridor begins the
    stop response within 100 ms (REQ-025).

    The baseline is the first route condition at a step at or after
    priming.complete while the agent drives (README, Readings).
    """
    vc = "VC-DRIVING-025"
    g = gate(run, vc)
    if g is not None:
        return g
    anns = run.route_announcements()
    if not anns:
        return inconclusive(vc, "score/route_provider.jsonl:out.route_announcement", None,
                            "no route announcement records")
    if all(a["issue_s"] is None for a in anns):
        raise MissingEvidence("out.route_announcement.clocks.issueTime", "C9",
                              "route announcements carry no simulation issue time")
    prime, eligible = driving_after_priming(run)
    cond = None
    last_issue = None
    for a in anns:
        if a["corridor"] == 0:
            f = int(round(a["issue_s"] / STEP_S)) if a["issue_s"] is not None else None
            if f is not None and eligible(f):
                cond = (f, "kRouteEmpty")
                break
            continue
        last_issue = a["issue_s"]
    if cond is None and last_issue is not None:
        # the announcement channel is periodic at 500 ms; the first step at which
        # the newest issue time is older than 1 s is the baseline. The run ends
        # at the agent's last step (its last mode record).
        last_sim = max(m["frame"] for m in run.modes() if isinstance(m["frame"], int)) * STEP_S
        if last_issue + THRESHOLDS["route_stale_s"] >= last_sim:
            return inconclusive(vc, "a route older than 1 s", None,
                                "the route stayed fresh to the end of the run",
                                {"last_issue_s": last_issue, "last_sim_s": last_sim})
        f = int(round(last_issue / STEP_S)) + 1
        while f * STEP_S - last_issue <= THRESHOLDS["route_stale_s"] + 1e-9:
            f += 1
        if eligible(f):
            cond = (f, "kRouteStale")
    if cond is None or cond[0] is None:
        return inconclusive(vc, "a route condition while the agent drove", None,
                            NOT_WHILE_DRIVING.format(what="route"),
                            {"fault": run.fault(), "priming_frame": prime})
    frame, cause = cond
    res = stop_timing(run, frame, cause)
    res.vc = vc
    res.measured.update({"condition_frame": frame, "condition": cause,
                         "last_issue_s": last_issue})
    return res


@case("VC-DRIVING-026", ("degradedInputOrPlan",), needs=("C3", "C9"))
def vc026(run: Run) -> Result:
    """A newest valid plan more than 300 ms old at a command begins the stop
    response within 100 ms (REQ-026).

    ICD v2 C3 puts `step_capture_sim_ms` and the named plan's
    `plan_capture_sim_ms` in commandVehicle's out.command log record (the
    payload stays exact). The age is computed at the command, in simulation
    time, from those two stamps and the commander's in.plan view.
    """
    vc = "VC-DRIVING-026"
    g = gate(run, vc)
    if g is not None:
        return g
    cmds = run.commands()
    if not cmds:
        return inconclusive(vc, "out.command", "C3", "no command records in this run")
    without = [c for c in cmds
               if c["step_capture_ms"] is None or c["plan_capture_ms"] is None]
    if without:
        raise MissingEvidence(
            "out.command.step_capture_sim_ms/plan_capture_sim_ms", "C3",
            f"{len(without)} of {len(cmds)} command records carry no simulation-time "
            "stamp, so the plan age at the command cannot be computed")
    valid = [p for p in run.plans_in("score/drivingAgent.jsonl", "in.plan")
             if p["sample_count"] == 64 and p["capture_ms"] is not None
             and all(finite(s["acceleration"]) and finite(s["curvature"])
                     for s in p["samples"])]
    if not valid:
        return inconclusive(vc, "in.plan (commander view)", None,
                            "no valid plan reached the commander in this run")
    valid.sort(key=lambda p: p["capture_ms"])
    times = [p["capture_ms"] for p in valid]
    import bisect
    baseline = None
    ages = []
    for c in cmds:
        i = bisect.bisect_right(times, c["step_capture_ms"] + 1e-6) - 1
        if i < 0:
            continue
        age_ms = c["step_capture_ms"] - times[i]
        ages.append({"t_ms": c["step_capture_ms"], "age_ms": age_ms,
                     "named_plan_capture_ms": c["plan_capture_ms"]})
        if age_ms / 1000.0 > THRESHOLDS["plan_stale_s"] + 1e-9:
            baseline = int(round(c["step_capture_ms"] / 100))
            break
    if baseline is None:
        return inconclusive(vc, "a plan older than 300 ms at a command", None,
                            "the plan age never passed 300 ms at a command",
                            {"commands": len(cmds), "valid_plans": len(valid)})
    res = stop_timing(run, baseline, "kPlanStale")
    res.vc = vc
    res.measured.update({"baseline_frame": baseline,
                         "plan_age_at_baseline_s": ages[-1]["age_ms"] / 1000.0,
                         "step_capture_ms": ages[-1]["t_ms"],
                         "named_plan_capture_ms": ages[-1]["named_plan_capture_ms"],
                         "plans_seen_by_commander": len(valid)})
    return res


@case("VC-DRIVING-027", ("degradedInputOrPlan",), needs=("C8",))
def vc027(run: Run) -> Result:
    """An invalid plan (a non-finite value or 63 pairs) begins the stop response
    within 100 ms and no command is computed from it (REQ-027)."""
    vc = "VC-DRIVING-027"
    g = gate(run, vc)
    if g is not None:
        return g
    inj = [i for i in run.injections() if i["action"] == "plan_inject"
           and i["detail"].get("invalid")]
    if not inj:
        return inconclusive(vc, "bench/injection.jsonl:invalid plan", "C8",
                            "no record of the invalid plan's arrival")
    T = inj[0]["t_sim"]
    frame = int(round(T / STEP_S))
    res = stop_timing(run, frame, "kPlanInvalid")
    res.vc = vc
    ref = inj[0]["detail"].get("planReference")
    used = [c for c in run.commands() if c["reference"] == ref]
    res.measured.update({"injected_plan_reference": ref, "invalid": inj[0]["detail"].get("invalid"),
                        "commands_from_it": len(used), "arrival_sim_s": T})
    if used and res.outcome == PASS:
        return bad(vc, res.measured, res.thresholds,
                   res.evidence + [ev(c["file"], c["rec"]) for c in used[:2]],
                   ["a command was computed from the invalid plan"])
    return res


@case("VC-DRIVING-028", ("closedLoopRoute",), needs=("C9",))
def vc028(run: Run) -> Result:
    """After the S-CORE communication of the driving system is stopped, the
    commands at the actuation follow the stop response no later than 300 ms of
    simulation time after the last command arrived (REQ-028)."""
    vc = "VC-DRIVING-028"
    g = gate(run, vc)
    if g is not None:
        return g
    all_acts = run.actuations()
    if all_acts and all(a["actuation_s"] is None for a in all_acts):
        raise MissingEvidence("out.actuation_state.clocks.actuationTime", "C9",
                              "actuation records carry no simulation-time stamp")
    acts = [a for a in all_acts if a["actuation_s"] is not None]
    applied = [a for a in acts if a["applied"] and a["reference"]]
    stops = [a for a in acts if a["stop"]]
    if not applied or not stops:
        if run.fault() != "comm_stop":
            return not_applicable(vc, "this run does not stop the S-CORE communication of "
                                      "the driving system; REQ-028 applies to that run")
        return inconclusive(vc, "adapter stop after the last applied command", None,
                            "this run has no adapter-applied stop response")
    last = applied[-1]["actuation_s"] if applied[-1]["actuation_s"] < stops[0]["actuation_s"] \
        else None
    prior = [a for a in applied if a["actuation_s"] < stops[0]["actuation_s"] - 1e-9]
    if not prior:
        return inconclusive(vc, "last command before the adapter stop", None,
                            "no applied command precedes the adapter's stop")
    last = prior[-1]["actuation_s"]
    S = stops[0]["actuation_s"]
    delay = S - last
    held = [a for a in acts if a["actuation_s"] >= S - 1e-9
            and (not a["stop"] or abs((a["accel"] or 0.0) + 4.0) > 1e-6)]
    # After its stop the adapter publishes no actuation state; it applies the
    # stop control at every tick and logs it as out.vehicle_control with
    # trigger "stop" (actuation-adapter/actuation_adapter_main.cpp:182-186).
    stop_frame = int(round(S / STEP_S))
    controls = [v for v in run.vehicle_controls()
                if v["frame"] is not None and v["frame"] >= stop_frame]
    not_stop = [{"frame": v["frame"], "trigger": v["trigger"]}
                for v in controls if v["trigger"] != "stop"]
    measured = {"last_command_s": last, "stop_in_force_s": S, "delay_s": delay,
                "cause": enum_name(stops[0]["cause"], CAUSES),
                "actuations_not_in_stop_after": len(held),
                "controls_after_stop": len(controls),
                "controls_after_stop_not_stop": not_stop[:5]}
    th = {"stop_to_actuation_s": THRESHOLDS["stop_to_actuation_s"],
          "deceleration_mps2": THRESHOLDS["stop_deceleration_mps2"]}
    evid = [ev(stops[0]["file"], stops[0]["rec"])] + \
           [ev(prior[-1]["file"], prior[-1]["rec"])]
    if enum_name(stops[0]["cause"], CAUSES) != "kCommandTimeout":
        return bad(vc, measured, th, evid,
                   [f"the adapter's stop cause is {measured['cause']}, not kCommandTimeout"])
    if delay > THRESHOLDS["stop_to_actuation_s"] + 1e-9:
        return bad(vc, measured, th, evid,
                   [f"the stop response reached the actuation {delay * 1000:.0f} ms after "
                    "the last command, limit 300 ms"])
    if held or not_stop:
        return bad(vc, measured, th, evid,
                   ["an actuation after the adapter's stop is not the stop response"])
    if not controls:
        return inconclusive(vc, "score/actuationAdapter.jsonl:out.vehicle_control after the "
                                "adapter's stop", None,
                            "the adapter publishes no actuation state after its stop, so only "
                            "its applied controls show that the stop was held",
                            measured)
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-029", ("degradedInputOrPlan", "closedLoopRoute"), needs=())
def vc029(run: Run) -> Result:
    """A publication that the driving system is stopped, with the cause, within
    100 ms of monotonic time after the stop begins, and every later health
    publication shows the mode stopped (REQ-029).

    Both ends are on the S-CORE host (ICD v2 answer to S5): the stop begin's
    envelope t_mono_ns and the publisher's HEALTH `publish_mono_s/_ns` in
    score/statePublisher.jsonl. The guest's receipt time is not used.
    """
    vc = "VC-DRIVING-029"
    begin = run.stop_begin()
    if begin is None:
        return not_applicable(vc, "this run has no stop response; REQ-029 applies to the "
                                  "stopped runs of REQ-023 to REQ-028")
    cause = enum_name(begin["cause"], CAUSES)
    hs = run.health_side()
    if not hs:
        return inconclusive(vc, "score/statePublisher.jsonl:out.health", "C5",
                            "the publisher's own health records are absent")
    first = None
    for h in hs:
        if h["publish_mono"] is None:
            continue
        if h["publish_mono"] >= begin["t_mono"] - 0.005 and means_stopped(h["mode"]) \
                and enum_name(h["cause"], CAUSES) == cause:
            first = h
            break
    if first is None:
        return bad(vc, {"stop_begin_mono": begin["t_mono"], "cause": cause,
                        "health_publications": len(hs)},
                   {"stop_publication_latency_s":
                    THRESHOLDS["stop_publication_latency_s"]},
                   [ev(begin["file"], begin["rec"])],
                   [f"no publisher health publication shows the stop with cause {cause}"])
    lat = first["publish_mono"] - begin["t_mono"]
    later = [h for h in hs if h["publish_mono"] is not None
             and h["publish_mono"] > first["publish_mono"] + 1e-9]
    not_stopped = [{"t_mono": h["publish_mono"], "mode": enum_name(h["mode"], MODES)}
                   for h in later if not means_stopped(h["mode"])]
    measured = {"clock": "monotonic (S-CORE host)",
                "stop_begin_mono": begin["t_mono"],
                "stop_publication_mono": first["publish_mono"],
                "latency_s": lat, "cause": cause, "publications_after": len(later),
                "later_publications_not_stopped": not_stopped[:5]}
    th = {"stop_publication_latency_s": THRESHOLDS["stop_publication_latency_s"],
          "clock": "monotonic"}
    evid = [ev(begin["file"], begin["rec"]), ev(first["file"], first["rec"])]
    if lat > THRESHOLDS["stop_publication_latency_s"] + 1e-9:
        return bad(vc, measured, th, evid,
                   [f"the stop was published {lat * 1000:.0f} ms after it began, limit 100 ms"])
    if not_stopped:
        return bad(vc, measured, th, evid,
                   ["a later health publication shows a mode that is not stopped"])
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-030", ("closedLoopRoute",), needs=("C2", "C9"))
def vc030(run: Run) -> Result:
    """Every camera image and motion sample in the records carries a capture time
    marked as simulation time (REQ-030).

    ICD v2 section 6 marks the clock in the field name: the C2 camera stamps
    are `capture_sim_ms`; the motion payload keeps `captureTime` and carries a
    `clocks` entry naming simulation time.
    """
    vc = "VC-DRIVING-030"
    steps = run.input_steps()
    samples = run.ego_samples()
    if not samples:
        return inconclusive(vc, "out.ego_motion_sample", None, "no motion sample records")
    problems = []
    marked = 0
    skipped_slots = 0
    for step in steps:
        for c in step["cameras"]:
            ct = c.get("capture_sim_ms")
            if c.get("status") == "missing":
                # no image this step: the agent writes the slot with status
                # "missing" and null stamps (ICD A28; agent/cc/agent_ffi.cpp:552,
                # 1039-1044). Any other slot holds an image, which needs its stamp.
                skipped_slots += 1
                continue
            if ct is None:
                problems.append({"frame": step["frame"], "camera": c.get("name"),
                                 "problem": "no capture_sim_ms stamp"})
            elif not finite(float(ct)):
                problems.append({"frame": step["frame"], "camera": c.get("name"),
                                 "problem": "non-finite capture_sim_ms"})
            else:
                marked += 1
    unmarked_ego = []
    for s in samples:
        if s["capture_ms"] is None or not finite(s["capture_ms"]):
            problems.append({"sample": s["step"], "problem": "no capture time"})
        elif s.get("capture_clock") != "simulation":
            unmarked_ego.append(s["step"])
        else:
            marked += 1
    if unmarked_ego:
        return inconclusive(vc, "out.ego_motion_sample.clocks.captureTime", "C9",
                            f"{len(unmarked_ego)} motion samples carry no clock tag "
                            "(the C2 camera stamps are marked by their _sim_ms suffix)",
                            {"samples": len(samples), "unmarked": len(unmarked_ego)})
    measured = {"steps": len(steps),
                "images": sum(len(s["cameras"]) for s in steps) - skipped_slots,
                "camera_slots_without_an_image": skipped_slots,
                "samples": len(samples), "marked_as_simulation": marked,
                "problems": problems[:5], "problem_count": len(problems)}
    th = {"clock_domain": "simulation"}
    evid = [ev(steps[0]["file"], steps[0]["rec"])] if steps else []
    if problems:
        return bad(vc, measured, th, evid,
                   [f"{len(problems)} stamps are not a simulation-time capture time, "
                    f"first {problems[0]}"])
    if measured["images"] == 0:
        # "every camera image ... carries a capture time" is not shown by a
        # record that holds no image
        return inconclusive(vc, "score/checkpointInputs.jsonl:cameras (an image)", None,
                            f"no camera image in the records: {len(steps)} steps, "
                            f"{skipped_slots} camera slots, each without an image",
                            measured)
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-031", ("closedLoopRoute",), needs=("C9",))
def vc031(run: Run) -> Result:
    """Every plan carries the capture time of its newest camera image marked as
    simulation time and a production time marked as the host's monotonic clock
    (REQ-031)."""
    vc = "VC-DRIVING-031"
    plans = run.plans()
    if not plans:
        return inconclusive(vc, "out.plan", None, "no plans in this run")
    problems, unmarked, marked = [], [], 0
    for p in plans:
        if p["capture_clock"] is None or p["production_clock"] is None:
            unmarked.append(plan_frame(p))
            continue
        if p["capture_ms"] is None:
            problems.append({"frame": plan_frame(p), "problem": "no capture time"})
        elif p["capture_clock"] != "simulation":
            problems.append({"frame": plan_frame(p),
                             "problem": f"capture time marked {p['capture_clock']}"})
        elif p["production_mono"] is None:
            problems.append({"frame": plan_frame(p), "problem": "no production time"})
        elif p["production_clock"] is None:
            unmarked.append(plan_frame(p))
        elif p["production_clock"] != "monotonic":
            problems.append({"frame": plan_frame(p),
                             "problem": f"production time marked {p['production_clock']}"})
        else:
            marked += 1
    measured = {"plans": len(plans), "both_stamps_marked": marked,
                "problems": problems[:5], "problem_count": len(problems),
                "unmarked": unmarked[:5]}
    th = {"capture_clock": "simulation", "production_clock": "monotonic"}
    if unmarked:
        return inconclusive(vc, "out.plan.clocks {captureTime, productionTime}", "C9",
                            "the stamps exist but the record has no clock tag for each",
                            measured)
    evid = [ev(plans[0]["file"], plans[0]["rec"])]
    if problems:
        return bad(vc, measured, th, evid,
                   [f"{len(problems)} plans lack a correctly marked stamp, first "
                    f"{problems[0]}"])
    return ok(vc, measured, th, evid)


@case("VC-DRIVING-032", ("closedLoopRoute",), needs=("C2", "C9"))
def vc032(run: Run) -> Result:
    """For every command, from the records alone: input age at actuation and the
    planning interval in simulation time, planning time and S-CORE transport
    delay on the monotonic clock; no computation combines two domains (REQ-032).

    Joins: the agent's out.command and the adapter's in.command carry the same
    productionTime (agent/cc/agent_logic.cpp:653, actuation-adapter/
    log_records.h:46-63); the adapter logs a command's out.actuation_state right
    after its in.command (actuation_adapter_main.cpp:244-256). A command names
    its plan by planReference; every stop command names one frozen plan (ICD
    section 4), so commands are never joined by it. The success criterion sets
    no range for the four quantities; they are reported, not bounded.
    """
    vc = "VC-DRIVING-032"
    plans = run.plans()
    cmds = run.commands()
    if not run.exists("score/actuationAdapter.jsonl"):
        # the adapter's records are read first, as before (a consumer of the
        # evaluators, agent/cc/tests/test_records_against_evaluators.py, relies on it)
        raise MissingEvidence("score/actuationAdapter.jsonl", None,
                              "the adapter's reception and actuation of the commands are not "
                              "recorded")
    arr = {}
    for step in camera_views(run):
        arrivals = [c["arrival_mono_ns"] for c in step["cameras"]
                    if c.get("arrival_mono_ns") is not None]
        if arrivals:
            arr[step["frame"]] = max(arrivals) / 1e9
    if not arr:
        return inconclusive(vc, "checkpointInputs.cameras[].arrival_mono_ns", "C2",
                            "the newest camera image's availability on the monotonic clock "
                            "is not recorded")
    received = run.adapter_commands()
    if not received:
        return inconclusive(vc, "score/actuationAdapter.jsonl:in.command", None,
                            "the adapter's reception of the commands is not recorded")
    by_production: dict[float, dict] = {}
    for h in received:
        if h["production_mono"] is not None:
            by_production.setdefault(round(h["production_mono"], 6), h)
    by_ref = {p["reference"]: p for p in plans if p["reference"]}
    previous_capture = {}
    caps = sorted({p["capture_ms"] for p in plans if p["capture_ms"] is not None})
    for a, b in zip(caps, caps[1:]):
        previous_capture[b] = a
    ages, intervals, planning, transport = [], [], [], []
    problems, not_received, not_applied = [], 0, 0
    complete = 0
    without_plan = 0
    for c in cmds:
        if c["production_mono"] is None:
            problems.append({"command": c["rec"]["seq"], "problem": "no production time"})
            continue
        if not c["reference"]:
            without_plan += 1           # a stop command with no plan to date
            h = by_production.get(round(c["production_mono"], 6))
            if h is not None and h["arrival_mono"] is not None:
                transport.append(h["arrival_mono"] - c["production_mono"])
            continue
        p = by_ref.get(c["reference"])
        if p is None:
            problems.append({"command": c["rec"]["seq"], "plan": c["reference"],
                             "problem": "the plan it names has no out.plan record"})
            continue
        if (p["capture_clock"] != "simulation") or (p["production_clock"] != "monotonic"):
            problems.append({"plan": p["reference"], "problem": "stamps not marked"})
            continue
        if p["production_mono"] is None or p["capture_ms"] is None:
            problems.append({"plan": p["reference"], "problem": "no production or capture time"})
            continue
        got = 0
        f = plan_frame(p)
        if f in arr:
            planning.append(p["production_mono"] - arr[f])
            got += 1
        if p["capture_ms"] in previous_capture:
            intervals.append((p["capture_ms"] - previous_capture[p["capture_ms"]]) / 1000.0)
            got += 1
        h = by_production.get(round(c["production_mono"], 6))
        if h is None:
            not_received += 1
            continue
        if h["arrival_mono"] is not None:
            transport.append(h["arrival_mono"] - c["production_mono"])
            got += 1
        act = h["actuation"]
        if act is None or act["actuation_s"] is None:
            not_applied += 1
            continue
        ages.append(act["actuation_s"] - p["capture_ms"] / 1000.0)
        got += 1
        complete += got == 4

    def span(xs):
        return {"min": min(xs) if xs else None, "max": max(xs) if xs else None}
    measured = {"commands": len(cmds), "commands_with_all_four": complete,
                "commands_without_a_plan": without_plan,
                "commands_not_received": not_received, "commands_not_applied": not_applied,
                "input_age_at_actuation_s": span(ages),
                "planning_interval_s": span(intervals),
                "planning_time_s": span(planning),
                "score_transport_delay_s": span(transport),
                "samples": {"age": len(ages), "interval": len(intervals),
                            "planning": len(planning), "transport": len(transport)},
                "problems": problems[:5]}
    th = {"ranges": "none: REQ-DRIVING-032 states no range for the four quantities"}
    if problems:
        return inconclusive(vc, "clock-domain tags", "C9",
                            "a command or its plan is not stamped and marked with its clocks",
                            measured)
    # Each quantity is a later stamp minus an earlier one on one clock. A negative
    # value is no delay: a join or a stamp is wrong (a join by plan reference gives
    # such values while a frozen plan is commanded), so the run shows nothing.
    negative = {name: sum(1 for x in xs if x < -1e-6)
                for name, xs in (("input_age_at_actuation_s", ages),
                                 ("planning_interval_s", intervals),
                                 ("planning_time_s", planning),
                                 ("score_transport_delay_s", transport))}
    negative = {k: n for k, n in negative.items() if n}
    if negative:
        measured["negative_samples"] = negative
        return inconclusive(vc, "consistent production, arrival and actuation stamps", None,
                            "negative " + ", ".join(f"{k} in {n} samples" for k, n in negative.items())
                            + ": a later stamp precedes an earlier one on the same clock, so a join "
                              "or a stamp is wrong", measured)
    if not (ages and intervals and planning and transport):
        return inconclusive(vc, "the records of all four quantities", None,
                            "no command yields every quantity", measured)
    evid = [ev(plans[0]["file"], plans[0]["rec"])]
    notes = ["each quantity is computed from stamps of one clock domain; the values are "
             "reported, not bounded (the success criterion states no range)"]
    if not_received or not_applied:
        notes.append(f"{not_received} commands have no adapter reception and {not_applied} "
                     "no applied actuation record: their age at actuation is not defined")
    return ok(vc, measured, th, evid, notes)


@case("VC-DRIVING-033", ("closedLoopRoute",), needs=("C7",))
def vc033(run: Run) -> Result:
    """The run record precedes the first plan and the values an independent
    engineer derives from the named files equal the recorded ones (REQ-033).

    ICD v2 C7 names checkpointPath, configurationPath, vehicleConfiguration,
    navigationMap and route with their SHA-256 values, plus writtenAtMonoNs.
    The checkpoint copy is retained once per campaign, so the evaluator looks
    for it in the run directory and then next to it (the campaign directory).
    """
    vc = "VC-DRIVING-033"
    import hashlib
    plans = run.plans()
    if not plans:
        return inconclusive(vc, "out.plan", None, "no plan in this run")
    rec = run.record
    written = rec.get("writtenAtMonoNs")
    if not isinstance(written, int):
        return inconclusive(vc, "run_record.writtenAtMonoNs", "C7",
                            "the run record carries no time of writing")
    first = plans[0]["production_mono"]

    def entry(label: str, rel, sha):
        if not isinstance(rel, str) or not rel:
            return label, None, sha, "no path"
        if not isinstance(sha, str) or not sha:
            return label, None, sha, "no recorded sha256"
        # a retained copy in the run or campaign directory; never an unverified
        # file of the evaluating host (runio.Run.named_file)
        p, why = run.named_file(rel, sha)
        if p is None:
            return label, None, sha, why
        return label, p, sha, None

    checks = [
        entry("checkpointSha256", rec.get("checkpointPath"), rec.get("checkpointSha256")),
        entry("configurationSha256", rec.get("configurationPath"),
              rec.get("configurationSha256")),
    ]
    for label, key in (("vehicleConfiguration", "vehicleConfiguration"),
                       ("navigationMap", "navigationMap"), ("route", "route")):
        obj = rec.get(key) or {}
        if not isinstance(obj, dict):
            obj = {}
        checks.append(entry(label, obj.get("path"), obj.get("sha256")))

    derived, problems = {}, []
    for label, p, sha, why in checks:
        if why:
            return inconclusive(vc, f"run_record.{label}: {why}", "C7",
                                "the record names no retained file to hash")
        derived[label] = hashlib.sha256(p.read_bytes()).hexdigest()
        if derived[label] != sha:
            problems.append({label: {"recorded": sha, "derived": derived[label]}})
    measured = {"written_at_mono_ns": written, "first_plan_production_mono": first,
                "record_precedes_first_plan": written / 1e9 < first,
                "derived": derived, "problems": problems,
                "checkpoint_copy": "one per campaign (C7)"}
    th = {"sha256": "derived equals recorded"}
    if not measured["record_precedes_first_plan"]:
        return bad(vc, measured, th, [],
                   ["the run record was written after the first plan"])
    if problems:
        return bad(vc, measured, th, [],
                   ["a recorded identity differs from the hash of the file it names"])
    notes = ["the source revision is checked out by an independent engineer; the "
             "evaluator can only compare the recorded string",
             "the checkpoint is retained once per campaign, not per run (C7)"]
    if not rec.get("autoE2ESourceRevision"):
        return bad(vc, measured, th, [], ["the run record names no source revision"])
    return ok(vc, measured, th, [], notes)


@case("VC-DRIVING-034", ("closedLoopRoute",), needs=())
def vc034(run: Run) -> Result:
    """Every plan names the run record of REQ-033 (REQ-034)."""
    vc = "VC-DRIVING-034"
    plans = run.plans()
    if not plans:
        return inconclusive(vc, "out.plan", None, "no plan in this run")
    ident = run.identity()
    wrong = [{"frame": plan_frame(p), "runRecord": p.get("run_record")}
             for p in plans if p.get("run_record") != ident]
    measured = {"plans": len(plans), "run_record_identity": ident,
                "plans_with_other_identity": wrong[:5], "wrong_count": len(wrong)}
    th = {"run_record_identity": ident, "prefix_hex": 16}
    evid = [ev(plans[0]["file"], plans[0]["rec"])]
    if wrong:
        return bad(vc, measured, th, evid,
                   [f"{len(wrong)} plans name another run record, first {wrong[0]}"])
    return ok(vc, measured, th, evid)


# REQ-DRIVING-035 names two starts, and the health names the condition of each
# (ICD section 3, HEALTH field 43 refusal_reason: "mismatch", "no_pin"; A5). A
# checkpoint file that differs from the named one in one byte (checkpointCase
# "mismatch") is refused with "mismatch"; a configuration that names no
# checkpoint SHA-256 ("unpinned") with "no_pin". These are the two starts the
# case's run record names (ICD C4 scenarioVariant.checkpointCase) and the two
# roles of the checkpoint-refusal campaign; the agent refuses them so
# (agent/python/de4sdv_planner/__init__.py identity_check).
REFUSAL_REASON = {"mismatch": "mismatch", "unpinned": "no_pin"}


@case("VC-DRIVING-035", ("checkpointRefusal",), needs=("C6", "C1"))
def vc035(run: Run) -> Result:
    """A checkpoint that differs in one byte, and a configuration that names no
    checkpoint, produce no plan, keep the vehicle at standstill and the health
    names the mismatch (REQ-035).

    The refusal reason judged is the one the run's start calls for
    (REFUSAL_REASON); a health that names the other reason fails. A start that
    is neither of the two, or a run without a world tick (the standstill is not
    observed), is inconclusive."""
    vc = "VC-DRIVING-035"
    case = (run.variant or {}).get("checkpointCase")
    want = REFUSAL_REASON.get(case) if isinstance(case, str) else None
    plans = run.plans(required=False)
    wb = run.world_by_frame()
    moving = [{"frame": f, "speed_kmh": float(wd_get(r, "velocity", "speed_mps")) * 3.6}
              for f, r in wb.items()
              if float(wd_get(r, "velocity", "speed_mps")) * 3.6
              > THRESHOLDS["standstill_kmh"]]
    hs = run.health_pubs()
    refusal = [h for h in hs if enum_name(h["cause"], CAUSES) == "kCheckpointRefused"]
    detail_ok = [h for h in refusal if want is not None and h.get("refusal_reason") == want
                 and ((want == "mismatch" and h.get("expected_sha") and h.get("actual_sha")
                       and h["expected_sha"] != h["actual_sha"])
                      or (want == "no_pin" and not h.get("expected_sha")))]
    other = [h for h in refusal if want is not None and h.get("refusal_reason")
             and h.get("refusal_reason") != want]
    measured = {"checkpoint_case": case, "plans": len(plans), "world_ticks": len(wb),
                "moving_ticks": moving[:5], "health_publications": len(hs),
                "refusal_healths": len(refusal),
                "refusals_naming_the_mismatch": len(detail_ok),
                "refusals_naming_another_reason": sorted({h["refusal_reason"] for h in other})}
    th = {"plans_allowed": 0, "standstill_kmh": THRESHOLDS["standstill_kmh"],
          "refusal_reason": want}
    evid = [ev(h["file"], h["rec"]) for h in (refusal[:1] or hs[:1])]
    if plans:
        return bad(vc, measured, th, evid, ["a plan was produced from a refused checkpoint"])
    if moving:
        return bad(vc, measured, th, evid, ["the vehicle was not at standstill"])
    if other:
        return bad(vc, measured, th, evid,
                   [f"the health names the refusal reason {other[0]['refusal_reason']!r}; "
                    f"a start with checkpointCase {case!r} calls for {want!r}"])
    if not wb:
        return inconclusive(vc, "simulator/world.jsonl:tick", "C1",
                            "no world tick is recorded, so the vehicle is not observed at "
                            "standstill", measured)
    if not refusal:
        return inconclusive(vc, "health with cause kCheckpointRefused", "C6",
                            "the health never names the refusal", measured)
    if want is None:
        return inconclusive(vc, "run_record.scenarioVariant.checkpointCase", "C4",
                            f"the run's checkpointCase is {case!r}, neither start of "
                            "REQ-DRIVING-035 (mismatch: a checkpoint that differs in one "
                            "byte; unpinned: a configuration that names no checkpoint "
                            "SHA-256), so the refusal reason it calls for is not known",
                            measured)
    if not detail_ok:
        return inconclusive(vc, "rx.health.checkpoint_expected_sha256/refusal_reason", "C6",
                            "the refusal is published without naming the mismatch", measured)
    return ok(vc, measured, th, evid)


# --------------------------------------------------------------------- utilities
def json_route(run: Run) -> dict:
    import json
    route = run.record.get("route") or {}
    p = run.path(str(route.get("path"))) if isinstance(route, dict) and route.get("path") \
        else run.path("navigation/route.json")
    if not p.exists():
        # the provider names the route file; fall back to it
        for a in run.route_announcements():
            q = run.path(str(a.get("route_file") or ""))
            if q.exists():
                p = q
                break
    if not p.exists():
        raise MissingEvidence("navigation/route.json", "C7",
                              "the route file the run drove is not retained")
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as exc:
        raise RunFormatError(f"{p}: {exc}") from exc


def route_sha(run: Run) -> str | None:
    import hashlib
    route = run.record.get("route") or {}
    p = run.path(str(route.get("path"))) if isinstance(route, dict) and route.get("path") \
        else run.path("navigation/route.json")
    if p.exists():
        return hashlib.sha256(p.read_bytes()).hexdigest()
    for a in run.route_announcements():
        if a.get("sha"):
            return str(a["sha"])
    return None


def ego_pose_at(run: Run, frame) -> dict | None:
    if not isinstance(frame, int):
        return None
    r = run.world_by_frame().get(frame)
    if r is None:
        return None
    p = r["data"]["egoPose"]
    return {"x": float(p["x"]), "y": float(p["y"]), "yaw": float(p["yaw"])}


def wd_get(rec: dict, *path: str):
    """A required world field; its absence is C1 missing evidence, not an error."""
    d = rec["data"]
    for k in path:
        if not isinstance(d, dict) or k not in d or d[k] is None:
            raise MissingEvidence("simulator/world.jsonl:" + ".".join(path), "C1",
                                  "the pacer does not record this ego observable")
        d = d[k]
    return d


def rig_origin(run: Run) -> tuple[list[float], dict]:
    """The origin of the camera rig (REF) and the record that gives it.

    drivingAgent logs `rig` once, before the first step: `result` is what its
    planner's set_rig returned (agent/cc/agent_ffi.cpp:854-885), and
    `result.origin` the REF origin [x, y, z] in vehicle axes (CARLA: x forward,
    y right, z up), metres. A `result` logged as a JSON string is read too.
    """
    import json
    rel = "score/drivingAgent.jsonl"
    for rec in run.events(rel, "rig", required=False):
        res = rec["data"].get("result")
        if isinstance(res, str):
            try:
                res = json.loads(res)
            except json.JSONDecodeError as exc:
                raise RunFormatError(f"{rel}:{rec['seq']}: rig result is not JSON: {exc}") \
                    from exc
        origin = res.get("origin") if isinstance(res, dict) else None
        if origin is None:
            continue
        if not (isinstance(origin, list) and len(origin) == 3
                and all(isinstance(v, (int, float)) and not isinstance(v, bool)
                        for v in origin)):
            raise RunFormatError(f"{rel}:{rec['seq']}: rig result.origin is not three "
                                 f"numbers: {origin!r}")
        return [float(v) for v in origin], rec
    raise MissingEvidence(f"{rel}:rig.result.origin", None,
                          "the origin of the camera rig is not recorded, so the poses "
                          "cannot be moved to it")


def _speed_mps(run: Run, frame: int) -> float | None:
    r = run.world_by_frame().get(frame)
    return float(wd_get(r, "velocity", "speed_mps")) if r else None


# --------------------------------------------------------------------- driver
SCENARIO_CASES = {
    "closedLoopRoute": [f"VC-DRIVING-{i:03d}" for i in range(1, 18)]
                        + ["VC-DRIVING-023", "VC-DRIVING-028", "VC-DRIVING-029"]
                        + [f"VC-DRIVING-{i:03d}" for i in range(30, 35)],
    "degradedInputOrPlan": [f"VC-DRIVING-{i:03d}" for i in range(20, 28)]
                            + ["VC-DRIVING-029"],
    "aaosUnavailable": ["VC-DRIVING-018", "VC-DRIVING-019"],
    "checkpointRefusal": ["VC-DRIVING-035"],
}
for vc, spec in CASES.items():
    assert spec["scenarios"], vc
    for s in spec["scenarios"]:
        assert vc in SCENARIO_CASES.get(s, []), f"{vc} not in SCENARIO_CASES[{s}]"


def label_conflicts(run: Run) -> list[str]:
    """Where the run's own records contradict its scenario label.

    The model identifies a start with a checkpoint that is not pinned as
    checkpointRefusal (DrivingScenarioIdentity; VC-DRIVING-035). A run with a
    checkpointCase other than "pinned" (ICD C4), or with any kRefused mode
    record, is such a run whatever its label says.
    """
    if run.scenario == "checkpointRefusal":
        return []
    reasons = []
    case = (run.variant or {}).get("checkpointCase")
    if isinstance(case, str) and case and case != "pinned":
        reasons.append(f"its checkpointCase is {case!r}")
    try:
        refused = sum(1 for m in run.modes() if enum_name(m["mode"], MODES) == "kRefused")
    except (MissingEvidence, RunFormatError):
        refused = 0
    if refused:
        reasons.append(f"the agent logged {refused} kRefused mode records")
    if not reasons:
        return []
    return [f"the run record names scenario {run.scenario!r}, but " + " and ".join(reasons)
            + ": the model identifies such a run as checkpointRefusal (VC-DRIVING-035), "
              "and it is judged as one"]


def effective_scenario(run: Run) -> str:
    return "checkpointRefusal" if label_conflicts(run) else run.scenario


def applicable(run: Run) -> list[str]:
    return list(SCENARIO_CASES.get(effective_scenario(run), []))


def evaluate_case(run: Run, vc: str) -> Result:
    spec = CASES[vc]
    fn = spec["fn"]
    try:
        return fn(run)
    except MissingEvidence as exc:
        return inconclusive(vc, exc.what, exc.icd_change, exc.detail)
    except RunFormatError as exc:
        return Result(vc, ERROR, notes=[str(exc)])
    except Exception as exc:                     # a defect in the evaluator, not evidence
        return Result(vc, ERROR, notes=[f"evaluator error: {type(exc).__name__}: {exc}"])
