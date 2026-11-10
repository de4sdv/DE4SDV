#!/usr/bin/env python3
"""Write synthetic bench run directories per ICD v2 (sections 6, 7, 8, 10).

These runs are TEST FIXTURES for the evaluators, not bench evidence. They
carry the records ICD v2 defines: the prefixed log files, the operational
state as the decoded SOME/IP struct, the scaled C2 metadata record plus the
sampled input bundles, the C3 stamps in the commander's log record, and the
run record of section 8 (C4/C7).

Usage:
    python make_synthetic_run.py --out /tmp/runs --all
    python make_synthetic_run.py --out /tmp/one --scenario degradedInputOrPlan \
        --fault camera_missing --entry-speed 10
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import shutil
from pathlib import Path

import numpy as np

STEP_S = 0.1
STEP_MS = 100
WHEELBASE_M = 2.85
MAX_ACC = 3.0
MAX_DEC = 8.0
MAX_ROAD_WHEEL_ANGLE_DEG = 35.0           # the command limit (ICD section 5)
VEHICLE_MAX_STEER_ANGLE_DEG = 70.0        # CARLA mkz_2020 front wheels at steer +-1: the steer's full scale (A30)
MAX_STEER_RATE_DEG_S = 180.0
STOP_ACCEL = -4.0
STANDSTILL_KMH = 0.1

MONO0 = 1000.0                    # CLOCK_MONOTONIC base of the S-CORE host, s
REAL0 = 1762300000.0              # CLOCK_REALTIME base, s
GUEST_REAL_OFFSET = 0.0004        # chrony residual between hosts, s

MODES = ["kStarting", "kDriving", "kStopResponse", "kStandstill", "kRefused"]
CAUSES = ["kNone", "kCameraMissing", "kCameraInvalid", "kCameraStale",
          "kMotionInvalid", "kMotionStale", "kRouteStale", "kRouteEmpty",
          "kPlanStale", "kPlanInvalid", "kCommandTimeout", "kCheckpointRefused",
          "kRunEnd"]
CAMERAS = ["front", "front_left", "front_right", "rear_left", "rear", "rear_right"]

FAULT_CAUSE = {
    "none": None,
    # the images of one camera are withheld from F: judged by its newest valid image,
    # the camera has a condition once that image is more than 200 ms old, at F + 2
    # (REQ-DRIVING-023; README, Readings)
    "camera_missing": "kCameraStale",
    "camera_invalid": "kCameraInvalid",
    "camera_stale": "kCameraStale",
    "motion_stale": "kMotionStale",
    "motion_invalid": "kMotionInvalid",
    "route_stale": "kRouteStale",
    "route_empty": "kRouteEmpty",
    "plan_stale": "kPlanStale",
    "plan_dropped": "kPlanStale",
    "plan_invalid_nan": "kPlanInvalid",
    "plan_invalid_63": "kPlanInvalid",
    "comm_stop": "kCommandTimeout",
    "checkpoint_mismatch": "kCheckpointRefused",
    "checkpoint_unpinned": "kCheckpointRefused",
}

BUNDLE_PERIOD_STEPS = 50          # every 50th step (ICD v2 C2)
BUNDLE_FAULT_WINDOW_S = 0.5       # plus every step within +/-0.5 s of a fault
GEOMETRY = "autoe2e-bev-450x300-0p4m-v1"
MAP_CONTEXT = {"channels": 14, "height": 450, "width": 300, "geometry": GEOMETRY}

# The origin of the camera rig (REF) that drivingAgent's set_rig returns and logs
# in its `rig` record: the rear-axle centre on the road plane, in vehicle axes
# (CARLA: x forward, y right, z up), metres; about the value read from a
# vehicle.lincoln.mkz_2020 hero.
RIG_ORIGIN = [-1.3886, 0.0, 0.0051]
EGO_POSE_WINDOW = 66              # the poses of frames k-65 .. k of a step k


def ego_pose(st: dict) -> dict:
    """A state's C1 `egoPose` {x, y, yaw}, map frame, as the tick records it."""
    return {"x": round(st["x"], 4), "y": round(st["y"], 4), "yaw": round(st["yaw"], 6)}


def ego_motion_rows(poses: list[dict], origin) -> list[list[float]]:
    """The 64 ego-motion rows the agent gives the checkpoint at a step k.

    `poses` are the C1 `egoPose` {x, y, yaw} (map frame, ICD section 9) of the
    66 frames k-65 .. k, oldest first; `origin` is the rig origin [x, y, z] in
    vehicle axes, so a pose moves by (x, -y) in its own map-frame axes. The
    rows are worked out as upstream's closed-loop driver does it
    (`egomotion_from_poses`, agent/python/de4sdv_planner/history.py):
    numpy.gradient at 0.1 s over the positions, speed its norm, acceleration
    numpy.gradient of the speed, rows [1:-1], so row j is frame k-64+j. Yaw
    rate and curvature are given as zero (REQ-DRIVING-008 as amended on
    2026-11-09).
    """
    if len(poses) != EGO_POSE_WINDOW:
        raise ValueError(f"need {EGO_POSE_WINDOW} poses, got {len(poses)}")
    ox, oy = float(origin[0]), float(origin[1])
    xy = np.array([[p["x"] + ox * math.cos(p["yaw"]) + oy * math.sin(p["yaw"]),
                    p["y"] + ox * math.sin(p["yaw"]) - oy * math.cos(p["yaw"])]
                   for p in poses], dtype=np.float64)
    speed = np.linalg.norm(np.gradient(xy, STEP_S, axis=0), axis=1)
    accel = np.gradient(speed, STEP_S)
    return [[round(float(v), 6), round(float(a), 6), 0.0, 0.0]
            for v, a in zip(speed[1:-1], accel[1:-1])]


def rig_result(origin=RIG_ORIGIN) -> dict:
    """The `result` of drivingAgent's `rig` record, as set_rig returns it
    (agent/cc/agent_ffi.cpp:854-885, agent/python/de4sdv_planner/__init__.py),
    without the projection matrices."""
    return {"engine": "checkpoint", "origin": list(origin),
            "origin_info": {"wheel_position_unit": "cm", "wheel_radius_m": 0.355,
                            "rear_wheels_vehicle_local_m": [
                                [origin[0], -0.7965, round(origin[2] + 0.355, 4)],
                                [origin[0], 0.7965, round(origin[2] + 0.355, 4)]]},
            "rig_pose_err_mm": [1.787] * len(CAMERAS),
            "rig_pose_err_deg": [2.0e-05] * len(CAMERAS),
            "front_hi_res": {"width": 1024, "height": 1024}, "tile_wh": [512, 512]}


def ns(t: float) -> int:
    return int(round(t * 1e9))


def split_s(t: float) -> tuple[int, int]:
    s = int(math.floor(t))
    n = int(round((t - s) * 1e9))
    if n >= 1_000_000_000:
        s, n = s + 1, n - 1_000_000_000
    return s, n


def sha16(text: bytes) -> str:
    return hashlib.sha256(text).hexdigest()[:16]


class Logs:
    """One JSONL writer per file, seq per file, ICD section 6 envelope."""

    def __init__(self, root: Path):
        self.root = root
        self.seq: dict[str, int] = {}
        self.files: dict[str, object] = {}

    def write(self, rel: str, host: str, component: str, event: str, data: dict,
              t_mono: float, t_real: float) -> None:
        p = self.root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        fh = self.files.get(rel)
        if fh is None:
            fh = open(p, "a", encoding="utf-8")
            self.files[rel] = fh
        s = self.seq.get(rel, 0) + 1
        self.seq[rel] = s
        rec = {"t_mono_ns": ns(t_mono), "t_real_ns": ns(t_real), "host": host,
               "component": component, "event": event, "seq": s, "data": data}
        fh.write(json.dumps(rec, separators=(",", ":"), allow_nan=False) + "\n")

    def close(self) -> None:
        for fh in self.files.values():
            fh.close()
        self.files.clear()


SINGLE_POINT_ROAD = (30, 13)      # (waypoint index, road id): a road-id run of one point


def build_route() -> dict:
    """A 600 m left-hand arc of 100 m radius from the origin.

    Waypoint 30 carries another road id than its neighbours: a road-id run of
    one point. The navigation library builds one centre line per run of two
    or more points and drops such a point (navigation/navigation_raster.cpp
    ParseRouteJson, lines 815-827), as real routes do at short junction roads.
    """
    radius = 100.0
    wps = []
    for i in range(121):
        th = 5.0 * i / radius
        road = SINGLE_POINT_ROAD[1] if i == SINGLE_POINT_ROAD[0] else 12
        wps.append([round(radius * math.sin(th), 6),
                    round(radius * (1 - math.cos(th)), 6), round(th, 6), road])
    end = wps[-1]
    return {"map": "Town10HD_Opt", "waypoints": wps, "destination": [end[0], end[1]]}


def centre_line_points(waypoints: list) -> list:
    """The route points the navigation library keeps: one centre line per run
    of constant road id with two or more points (navigation_raster.cpp:815-827)."""
    out, start = [], 0
    for i in range(1, len(waypoints) + 1):
        if i == len(waypoints) or round(waypoints[i][3]) != round(waypoints[start][3]):
            if i - start >= 2:
                out.extend(waypoints[start:i])
            start = i
    return out


def plan_samples(accel: float, curvature: float, v0: float) -> list[dict]:
    out = []
    x = 0.0
    for i in range(64):
        v = max(0.0, v0 + accel * STEP_S * i)
        x += v * STEP_S
        out.append({"acceleration": round(accel, 6),
                    "curvature": round(curvature, 6),
                    "x": round(x, 4),
                    "y": round(0.5 * curvature * x * x, 4),
                    "heading": round(curvature * x, 6)})
    return out


def steer_from_curvature(curv: float) -> float:
    ang = math.degrees(math.atan(WHEELBASE_M * curv))
    return max(-MAX_ROAD_WHEEL_ANGLE_DEG, min(MAX_ROAD_WHEEL_ANGLE_DEG, ang))


class RunBuilder:
    def __init__(self, root: Path, *, scenario: str, fault: str = "none",
                 role: str = "nominal", campaign: str = "nominal",
                 entry_speed: float = 0.0, aaos_mode: str = "absent",
                 frames: int = 700, prime: int = 65, fault_frame: int = 250,
                 checkpoint_case: str = "pinned"):
        self.root = root
        self.scenario = scenario
        self.fault = fault
        self.role = role
        self.campaign = campaign
        self.entry_speed = entry_speed
        self.aaos_mode = aaos_mode
        self.frames = frames
        self.prime = prime
        self.fault_frame = fault_frame
        self.checkpoint_case = checkpoint_case
        self.simulated = scenario != "aaosUnavailable"      # replays have no simulator
        self.root.mkdir(parents=True, exist_ok=True)
        self.logs = Logs(root)

        self.route = build_route()
        self.route_bytes = (json.dumps(self.route, indent=1) + "\n").encode()
        self.route_sha = hashlib.sha256(self.route_bytes).hexdigest()
        self.checkpoint_bytes = b"\x00DE4SDV-synthetic-checkpoint\x00" * 8
        self.checkpoint_sha = hashlib.sha256(self.checkpoint_bytes).hexdigest()

        self.v = entry_speed if fault not in ("checkpoint_mismatch",
                                              "checkpoint_unpinned") else 0.0
        self.x = self.y = self.yaw = self.curvature = 0.0
        self.accel_long = self.yaw_rate = 0.0
        self.s = 0.0
        self.control = {"throttle": 0.0, "brake": 0.0, "steer": 0.0,
                        "accelMps2": 0.0, "source": "actuationAdapter"}
        self.base_curve = 0.01
        self.states: dict[int, dict] = {}
        self.plan_payloads: list[dict] = []
        self.last_plan_ref = ""
        self.last_plan_capture = 0.0
        self.last_plan_frame = 0
        self.last_plan_production = 0.0
        self.stop_frame: int | None = None
        self.stop_cause: str | None = None
        self.standstill_frame: int | None = None
        self.actuated_steer = 0.0
        self.prev_steer: float | None = None
        self.commanded = False
        self.injections: list[dict] = []
        self.run_identity = "0" * 16
        self._prepare_artifacts()

    # ----------------------------------------------------------------- setup
    def _prepare_artifacts(self) -> None:
        (self.root / "config").mkdir(exist_ok=True)
        (self.root / "navigation").mkdir(exist_ok=True)
        art = self.root / "artifacts"
        art.mkdir(exist_ok=True)
        # The checkpoint is retained once per campaign in a real deployment
        # (ICD v2 C7). The fixture keeps one copy here so a single run is
        # self-contained; the evaluator also resolves ../checkpoint.bin.
        (art / "checkpoint.bin").write_bytes(self.checkpoint_bytes)
        (self.root / "navigation" / "route.json").write_bytes(self.route_bytes)
        (self.root / "navigation" / "map.json").write_text(
            json.dumps({"map": self.route["map"], "origin": [0.0, 0.0, 0.0]},
                       indent=1) + "\n")
        cfg = {"configurationIdentity": "DRIVING-CONFIG-001",
               "checkpointSha256": self.checkpoint_sha,
               "autoE2ESourceRevision": "autoe2e-0.9.0+synth",
               "commandLaw": "first_control",
               "geometry": "autoe2e-bev-450x300-0p4m-v1", "cameras": CAMERAS}
        (self.root / "config" / "agent.json").write_text(json.dumps(cfg, indent=1) + "\n")
        self.config_sha = hashlib.sha256(
            (self.root / "config" / "agent.json").read_bytes()).hexdigest()
        self.limits = {"vehicle_blueprint": "vehicle.lincoln.mkz_2020",
                       "wheelbase_m": WHEELBASE_M,
                       "max_acceleration_mps2": MAX_ACC,
                       "max_deceleration_mps2": MAX_DEC,
                       "max_road_wheel_angle_deg": MAX_ROAD_WHEEL_ANGLE_DEG,
                       "max_steering_rate_deg_per_s": MAX_STEER_RATE_DEG_S,
                       "command_law": "first_control"}
        (self.root / "config" / "vehicle.json").write_text(
            json.dumps(self.limits, indent=1) + "\n")

    def _sha(self, rel: str) -> str:
        return hashlib.sha256((self.root / rel).read_bytes()).hexdigest()

    def write_run_record(self) -> None:
        rec = {
            "contractIdentity": "de4sdv.driving.icd.v2",
            "scenario": self.scenario,
            "configurationIdentity": "DRIVING-CONFIG-001",
            "checkpointSha256": self.checkpoint_sha,
            "autoE2ESourceRevision": "autoe2e-0.9.0+synth",
            "configurationSha256": self.config_sha,
            "scoreFEORevision": "score-feo-synth+event-patch:0",
            "scoreCommunicationVersion": "score-com-1.0",
            "scoreLifecycleVersion": "score-lifecycle-1.0",
            "scoreSOMEIPGatewayCommit": "0" * 40,
            "simulatorBuild": "carla-0.9.16-synth",
            "executionEnvironmentIdentity": "gce-g4+sim-l4+aaos-build",
            "cuDNNVersion": "9.4.0", "parityCheck": "pass", "warmupSteps": 8,
            "commandLaw": "first_control",
            # C4
            "campaignId": self.campaign,
            "runRole": self.role,
            "scenarioVariant": {"fault": self.fault,
                                "entrySpeedMps": self.entry_speed,
                                "aaosMode": self.aaos_mode,
                                "checkpointCase": self.checkpoint_case},
            # C7
            "checkpointPath": "artifacts/checkpoint.bin",
            "configurationPath": "config/agent.json",
            "vehicleConfiguration": {"path": "config/vehicle.json",
                                     "sha256": self._sha("config/vehicle.json")},
            "navigationMap": {"path": "navigation/map.json",
                              "sha256": self._sha("navigation/map.json")},
            "route": {"path": "navigation/route.json", "sha256": self.route_sha},
            "writtenAtMonoNs": ns(MONO0 - 0.5),
            "writtenAtRealNs": ns(REAL0 - 0.5),
        }
        if self.aaos_mode != "absent":
            rec["inputReplay"] = {"sourceRun": "run-closedloop-0001", "digest": "5f" * 32}
        text = json.dumps(rec, indent=1, sort_keys=True) + "\n"
        (self.root / "run_record.json").write_text(text)
        self.run_identity = sha16(text.encode())

    # ----------------------------------------------------------------- timing
    def t_mono(self, f: float, off: float = 0.0) -> float:
        return MONO0 + f * STEP_S + off

    def t_real(self, f: float, off: float = 0.0) -> float:
        return REAL0 + f * STEP_S + off

    # ----------------------------------------------------------------- faults
    def fault_onset(self) -> int | None:
        if self.fault in ("none", "checkpoint_mismatch", "checkpoint_unpinned"):
            return None
        return self.fault_frame

    def trigger_frame(self) -> int | None:
        F = self.fault_onset()
        if F is None:
            return None
        return {
            "camera_missing": F + 2, "camera_invalid": F, "motion_invalid": F,
            "route_empty": F, "camera_stale": F + 2, "motion_stale": F + 2,
            "route_stale": F + 11, "plan_stale": F + 3, "plan_dropped": F + 3,
            # A24 (ICD section 4): the last command is applied at F - 1; the
            # adapter's stop begins once more than 200 ms have passed, at the
            # third tick after it (actuation-adapter/adapter_core.cpp:231-235)
            "comm_stop": F + 2, "plan_invalid_nan": F + 1, "plan_invalid_63": F + 1,
        }.get(self.fault, F)

    def _camera_status(self, f: int, name: str) -> tuple[bool, str, int]:
        """(valid, status, capture_sim_ms) of one camera at one step."""
        F = self.fault_onset()
        ct = f * STEP_MS
        if F is None:
            return True, "ok", ct
        if self.fault == "camera_missing" and name == "rear_left" and f >= F:
            return False, "missing", (F - 1) * STEP_MS
        if self.fault == "camera_invalid" and name == "front_left" and f == F:
            return False, "invalid", ct
        if self.fault == "camera_stale" and name == "rear" and f >= F:
            return True, "stale", (F - 1) * STEP_MS
        return True, "ok", ct

    def _motion(self, f: int, st: dict) -> dict:
        """The step's motion sample in the shape the agent logs it
        (agent/cc/agent_ffi.cpp:1088-1095): no valid/status field; a
        non-finite value is JSON null."""
        F = self.fault_onset()
        ct = f * STEP_MS
        if F is not None and self.fault == "motion_stale" and f >= F:
            return {"stage": "synthetic", "speed": round(self.entry_speed * 3.6, 4),
                    "longitudinalAcceleration": 0.0, "lateralAcceleration": 0.0,
                    "yawRate": 0.0, "captureTime": round((F - 1) * STEP_S, 4),
                    "frame": f}
        d = {"stage": "synthetic", "speed": round(st["v"] * 3.6, 4),
             "longitudinalAcceleration": round(st["accel"], 6),
             "lateralAcceleration": round(st["v"] * st["yaw_rate"], 6),
             "yawRate": round(math.degrees(st["yaw_rate"]), 6),
             "captureTime": round(ct / 1000.0, 4), "frame": f}
        if F is not None and self.fault == "motion_invalid" and f == F:
            d["speed"] = None
        return d

    def _route_state(self, f: int) -> dict | None:
        F = self.fault_onset()
        issue = round(f * STEP_S, 4)
        corridor = 60
        if F is not None:
            if self.fault == "route_stale" and f >= F:
                return None          # the provider stops announcing (ICD 9)
            if self.fault == "route_empty" and f >= F:
                corridor = 0
        return {"version": 2, "corridorPoints": corridor, "issueTime": issue,
                "routeFile": str(self.root / "navigation" / "route.json"),
                "routeSha256": self.route_sha,
                "clocks": {"issueTime": "simulation"}}

    # ----------------------------------------------------------------- frame
    def write_frame(self, f: int) -> None:
        st = self.states[f]
        trig = self.trigger_frame()
        tm, tr = self.t_mono(f), self.t_real(f)

        at_rest = st["v"] * 3.6 < STANDSTILL_KMH
        if trig is not None and self.stop_frame is None and f >= trig:
            self.stop_frame = f
            self.stop_cause = FAULT_CAUSE[self.fault]
            cause = self.stop_cause or "kNone"
            if self.fault == "comm_stop":
                # actuation-adapter/log_records.h:117-128 (StopResponseBegin)
                self.logs.write("score/actuationAdapter.jsonl", "score", "actuationAdapter",
                                "stop_response.begin",
                                {"cause": cause, "actuationTime": round(f * STEP_S, 4),
                                 "stopSinceMono": round(tm + 0.043, 9),
                                 "acceleration": STOP_ACCEL,
                                 "steeringAngle": round(self.actuated_steer, 6),
                                 "clocks": {"actuationTime": "simulation",
                                            "stopSinceMono": "monotonic"}},
                                tm + 0.043, tr + 0.043)
            else:
                # agent/cc/agent_logic.cpp:623-633 (record::StopBegin)
                self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent",
                                "stop_response.begin",
                                {"cause": cause, "causeValue": CAUSES.index(cause),
                                 "frame": f, "capture_sim_ms": f * STEP_MS,
                                 "source": "superviseLoop",
                                 "decision_mono_s": round(tm + 0.041, 9),
                                 "clocks": {"capture_sim_ms": "simulation",
                                            "decision_mono_s": "monotonic"}},
                                tm + 0.041, tr + 0.041)
        in_stop = self.stop_frame is not None and f >= self.stop_frame
        if in_stop and at_rest and self.standstill_frame is None and f > (self.stop_frame or 0):
            self.standstill_frame = f
            cause = self.stop_cause or "kNone"
            if self.fault == "comm_stop":
                # actuation-adapter/log_records.h:131-140 (StopResponseStandstill)
                self.logs.write("score/actuationAdapter.jsonl", "score", "actuationAdapter",
                                "stop_response.standstill",
                                {"cause": cause, "frame": f, "t_sim_ms": f * STEP_MS,
                                 "speedMps": round(st["v"], 6),
                                 "clocks": {"t_sim_ms": "simulation"}},
                                tm + 0.044, tr + 0.044)
            else:
                # agent/cc/agent_logic.cpp:635-647 (record::Standstill)
                self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent",
                                "stop_response.standstill",
                                {"cause": cause, "causeValue": CAUSES.index(cause),
                                 "frame": f, "capture_sim_ms": f * STEP_MS,
                                 "speedKmh": round(st["v"] * 3.6, 6),
                                 "speedMps": round(st["v"], 6), "source": "superviseLoop",
                                 "decision_mono_s": round(tm + 0.044, 9),
                                 "clocks": {"capture_sim_ms": "simulation",
                                            "decision_mono_s": "monotonic"}},
                                tm + 0.044, tr + 0.044)

        if self.scenario == "checkpointRefusal":
            mode = "kRefused"
        elif in_stop:
            mode = "kStandstill" if self.standstill_frame is not None else "kStopResponse"
        elif f < self.prime:
            mode = "kStarting"
        else:
            mode = "kDriving"
        self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent", "out.mode",
                        {"mode": MODES.index(mode),
                         "cause": CAUSES.index((self.stop_cause or "kNone") if in_stop else "kNone"),
                         "frameIndex": f, "captureTime": round(f * STEP_S, 4),
                         "decisionTime": round(tm + 0.028, 6),
                         "clocks": {"captureTime": "simulation",
                                    "decisionTime": "monotonic"}},
                        tm + 0.028, tr + 0.028)

        # --- 1. world tick (C1) ---------------------------------------------
        if self.simulated:
            sensors = [{"name": name, "actor_id": 100 + i,
                        "alive": True,
                        "attached": not (self.fault == "camera_missing"
                                         and name == "rear_left"
                                         and self.fault_onset() is not None
                                         and f >= self.fault_onset())}
                       for i, name in enumerate(CAMERAS)]
            wd = {"frame": f, "sim_ms": f * STEP_MS,
                  "egoPose": ego_pose(st),
                  "velocity": {"speed_mps": round(st["v"], 6),
                               "heading_rad": round(st["yaw"], 6)},
                  "acceleration": {"longitudinal_mps2": round(st["accel"], 6),
                                   "lateral_mps2": round(st["v"] * st["yaw_rate"], 6)},
                  "angular_velocity": {"roll_rad_s": 0.0, "pitch_rad_s": 0.0,
                                       "yaw_rad_s": round(st["yaw_rate"], 6)},
                  "lane": {"road": "Town10HD_Opt", "lane": 12,
                           "lat_m": 0.0, "junction": ""},
                  "control": dict(self.control), "controlSource": "actuationAdapter",
                  "autopilotEnabled": False, "trafficManagerEnabled": False,
                  "collisions": [], "laneInvasions": [],
                  "sensors": sensors}
            self.logs.write("simulator/world.jsonl", "simulator", "pacer", "tick", wd,
                            tm + 0.060, tr + 0.060)

        # --- 2. agent inputs -------------------------------------------------
        motion = self._motion(f, st)
        self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent",
                        "out.ego_motion_sample",
                        dict(motion, clocks={"captureTime": "simulation"}),
                        tm + 0.006, tr + 0.006)
        route = self._route_state(f)
        if route is not None:
            self.logs.write("score/route_provider.jsonl", "score", "routeProvider",
                            "out.route_announcement", route, tm, tr)
            self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent", "in.route",
                            route, tm + 0.004, tr + 0.004)

        # --- 3. planning ------------------------------------------------------
        plan_this_frame = False
        payload = None
        injected_plan: str | None = None
        if f == 400 and self.fault == "none" and self.scenario == "closedLoopRoute":
            injected_plan = "opposite_sign"
        if f == 450 and self.fault == "none" and self.scenario == "closedLoopRoute":
            injected_plan = "over_limits"

        planning = (f >= self.prime and not in_stop and self.scenario != "checkpointRefusal")
        if self.fault in ("plan_stale", "plan_dropped") and self.fault_onset() is not None \
                and f >= self.fault_onset():
            planning = False
        if self.fault == "comm_stop" and self.fault_onset() is not None \
                and f >= self.fault_onset():
            planning = True                      # the agent keeps inferring, comm is down

        curve, accel = self.base_curve, 0.0
        if planning:
            if self.scenario == "degradedInputOrPlan" or self.aaos_mode != "absent":
                accel = 0.0
            else:
                accel = 1.5 if st["v"] < 8.0 else 0.0
            if injected_plan == "opposite_sign":
                curve = -self.base_curve
            elif injected_plan == "over_limits":
                accel = 6.0                      # beyond max_acceleration_mps2
            ref = f"{self.run_identity}/{f}"
            production = tm + 0.030
            bad = None
            if self.fault == "plan_invalid_nan" and self.fault_onset() == f:
                bad = "nan"
            if self.fault == "plan_invalid_63" and self.fault_onset() == f:
                bad = "63"
            samples = plan_samples(accel, curve, st["v"])
            if bad == "nan":
                samples[0]["acceleration"] = None
            payload = {"frameIndex": f, "captureTime": round(f * STEP_S, 4),
                       "productionTime": round(production, 6),
                       "horizon": 6.4, "sampleCount": 63 if bad == "63" else 64,
                       "samples": samples[:63] if bad == "63" else samples,
                       "producer": "drivingAgent/inferPlan",
                       "runRecord": self.run_identity, "planReference": ref,
                       "clocks": {"captureTime": "simulation",
                                  "productionTime": "monotonic"}}
            self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent",
                            "out.plan", payload, production, tr + 0.030)
            if not (self.fault == "plan_dropped" and self.fault_onset() is not None
                    and f >= self.fault_onset()):
                self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent",
                                "in.plan", payload, tm + 0.032, tr + 0.032)
            plan_this_frame = True
            if bad is None:
                # the commander never takes an invalid plan as its newest valid one
                self.last_plan_ref = ref
                self.last_plan_capture = f * STEP_S
                self.last_plan_frame = f
                self.last_plan_production = production
                self.plan_payloads.append(payload)
            if injected_plan is not None:
                self.injections.append({
                    "action": "plan_inject", "t_sim_ms": f * STEP_MS,
                    "t_mono_ns": ns(tm + 0.020), "t_real_ns": ns(tr + 0.020),
                    "detail": {"planReference": ref, "curvature": round(curve, 6),
                               "acceleration": round(accel, 6),
                               "reason": ("REQ-011 opposite curvature sign"
                                          if injected_plan == "opposite_sign"
                                          else "REQ-012 over the acceleration limit")}})
            if bad is not None:
                self.injections.append({
                    "action": "plan_inject", "t_sim_ms": f * STEP_MS,
                    "t_mono_ns": ns(tm + 0.020), "t_real_ns": ns(tr + 0.020),
                    "detail": {"planReference": ref, "invalid": bad}})

        # --- 4. command -------------------------------------------------------
        # no command before the first driving step (agent/cc/agent_logic.cpp:530-532)
        issued = self.scenario != "checkpointRefusal" and f >= self.prime
        if self.fault == "comm_stop" and self.fault_onset() is not None \
                and f >= self.fault_onset():
            issued = False
        cmd = None
        if issued:
            if in_stop:
                cmd_accel, cmd_steer = STOP_ACCEL, self.actuated_steer
            elif plan_this_frame:
                cmd_accel = max(-MAX_DEC, min(MAX_ACC, accel))
                cmd_steer = steer_from_curvature(curve)
                self.actuated_steer = cmd_steer
            else:
                cmd_accel, cmd_steer = 0.0, self.actuated_steer
            prev = self.prev_steer if self.prev_steer is not None else cmd_steer
            lim = MAX_STEER_RATE_DEG_S * STEP_S
            cmd_steer = max(prev - lim, min(prev + lim, cmd_steer))
            self.prev_steer = cmd_steer
            # ICD v2 C3: the step's simulation stamp and the named plan's
            # capture stamp are in the commander's log record, not in the
            # exact payload.
            cmd = {"acceleration": round(cmd_accel, 6),
                   "steeringAngle": round(cmd_steer, 6),
                   "productionTime": round(tm + 0.040, 6),
                   "planReference": self.last_plan_ref,
                   "clocks": {"productionTime": "monotonic"},
                   "step_capture_sim_ms": f * STEP_MS,
                   "plan_capture_sim_ms": int(round(self.last_plan_capture * 1000))}
            self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent",
                            "out.command", cmd, tm + 0.040, tr + 0.040)
            # the adapter's reception record (actuation-adapter/log_records.h:46-63)
            self.logs.write("score/actuationAdapter.jsonl", "score", "actuationAdapter",
                            "in.command",
                            {"acceleration": cmd["acceleration"],
                             "steeringAngle": cmd["steeringAngle"],
                             "productionTime": cmd["productionTime"],
                             "planReference": cmd["planReference"],
                             "arrival_mono_s": round(tm + 0.042, 9),
                             "valid": True, "rejectReason": "none",
                             "clocks": {"productionTime": "monotonic"}},
                            tm + 0.042, tr + 0.042)

        # --- 5. actuation -----------------------------------------------------
        # The adapter's records (actuation-adapter/log_records.h): one
        # out.actuation_state per applied command and one when its own stop
        # begins (adapter_core.cpp:128-175, 249-268); out.vehicle_control for
        # every control it applies, with the trigger of
        # actuation_adapter_main.cpp:182-186 and 209-211.
        act = None
        if cmd is not None:
            act = {"applied": 1, "stopInForce": 0, "cause": "kNone",
                   "acceleration": cmd["acceleration"],
                   "steeringAngle": cmd["steeringAngle"],
                   "actuationTime": round(f * STEP_S, 4), "stopSince": 0.0,
                   "stopSinceMono": 0.0,
                   "planReference": cmd["planReference"],
                   "clocks": {"actuationTime": "simulation",
                              "stopSince": "simulation",
                              "stopSinceMono": "monotonic"}}
        applied = act                     # what the vehicle gets this tick
        adapter_stop = in_stop and self.fault == "comm_stop"
        if adapter_stop:
            ss, ssns = split_s(self.t_mono(self.stop_frame or 0))
            applied = {"applied": 0, "stopInForce": 1,
                       "cause": "kCommandTimeout",
                       "acceleration": STOP_ACCEL,
                       "steeringAngle": round(self.actuated_steer, 6),
                       "actuationTime": round((self.stop_frame or 0) * STEP_S, 4),
                       "stopSince": round((self.stop_frame or 0) * STEP_S, 4),
                       "stopSinceMono": ss + ssns / 1e9,
                       "planReference": "",       # the stop is the adapter's own
                       "clocks": {"actuationTime": "simulation",
                                  "stopSince": "simulation",
                                  "stopSinceMono": "monotonic"}}
            act = applied if f == self.stop_frame else None
        if act is not None:
            self.logs.write("score/actuationAdapter.jsonl", "score", "actuationAdapter",
                            "out.actuation_state", act, tm + 0.045, tr + 0.045)
        trigger = ("stop" if adapter_stop else "command" if cmd is not None
                   else "hold" if not self.commanded else None)
        if cmd is not None:
            self.commanded = True
        if trigger is not None and self.scenario != "aaosUnavailable":
            accel = applied["acceleration"] if applied is not None else 0.0
            self.logs.write("score/actuationAdapter.jsonl", "score", "actuationAdapter",
                            "out.vehicle_control",
                            {"frame": f, "t_sim_ms": f * STEP_MS,
                             "throttle": round(max(0.0, accel) / MAX_ACC, 4),
                             "brake": round(max(0.0, -accel) / MAX_DEC, 4) if applied
                             else 0.5,
                             "steer": round(-self.actuated_steer / VEHICLE_MAX_STEER_ANGLE_DEG, 6),
                             "handBrake": False, "trigger": trigger,
                             "controlSource": "actuationAdapter",
                             "clocks": {"t_sim_ms": "simulation"}},
                            tm + 0.046, tr + 0.046)

        if self.simulated:
            self._integrate(applied)

        # --- 6. publications --------------------------------------------------
        if self.scenario == "checkpointRefusal":
            self._health(f, "kRefused", "kCheckpointRefused", tm, tr)
            return
        if plan_this_frame and payload is not None:
            self._publish_plan(f, payload, tm, tr)
        self._publish_vehicle_state(f, motion, tm, tr)
        self._health(f, mode, self.stop_cause if in_stop else "kNone", tm, tr)

    def _integrate(self, act: dict | None) -> None:
        """Advance to the next frame with the applied control."""
        accel = act["acceleration"] if act is not None else 0.0
        curv = (math.tan(math.radians(act["steeringAngle"])) / WHEELBASE_M
                if act is not None else 0.0)
        v_old = self.v
        self.v = max(0.0, v_old + accel * STEP_S)
        self.yaw += 0.5 * (v_old + self.v) * curv * STEP_S
        self.x += self.v * STEP_S * math.cos(self.yaw)
        self.y += self.v * STEP_S * math.sin(self.yaw)
        self.s += self.v * STEP_S
        self.accel_long = (self.v - v_old) / STEP_S
        self.yaw_rate = self.v * curv
        self.curvature = curv
        if self.v <= 0.0:
            self.accel_long, self.yaw_rate = 0.0, 0.0
        self.control = {"throttle": round(max(0.0, accel) / MAX_ACC, 4),
                        "brake": round(max(0.0, -accel) / MAX_DEC, 4),
                        "steer": round(-math.degrees(math.atan(WHEELBASE_M * curv))
                                       / VEHICLE_MAX_STEER_ANGLE_DEG, 6),
                        "accelMps2": round(accel, 6),
                        "source": "actuationAdapter"}

    def _publish_plan(self, f: int, payload: dict, tm: float, tr: float) -> None:
        ps, pns = split_s(tm + 0.035)
        rs, rns = split_s(tr + 0.035)
        prod_s, prod_ns = split_s(payload["productionTime"])
        body = {"schema_major": 2, "schema_minor": 0, "kind": 1,
                "sequence": len(self.plan_payloads), "producer": "statePublisher",
                "publish_real_s": rs, "publish_real_ns": rns,
                "publish_mono_s": ps, "publish_mono_ns": pns,
                "plan_frame_index": f,
                "plan_capture_ms": int(round(payload["captureTime"] * 1000)),
                "plan_production_mono_s": prod_s, "plan_production_mono_ns": prod_ns,
                "plan_reference": payload["planReference"],
                "run_record": self.run_identity,
                "plan_producer": "drivingAgent/inferPlan",
                "plan_sample_count": payload["sampleCount"],
                "plan_horizon_s": payload["horizon"],
                "plan_acceleration": [s["acceleration"] for s in payload["samples"]],
                "plan_curvature": [s["curvature"] for s in payload["samples"]],
                "plan_x": [s["x"] for s in payload["samples"]],
                "plan_y": [s["y"] for s in payload["samples"]]}
        self.logs.write("score/statePublisher.jsonl", "score", "statePublisher",
                        "out.plan", dict(body), tm + 0.035, tr + 0.035)
        self.logs.write("guest/observer.jsonl", "guest", "observer", "rx.plan",
                        dict(body), tm + 0.038, tr + 0.038 + GUEST_REAL_OFFSET)

    def _publish_vehicle_state(self, f: int, motion: dict, tm: float, tr: float) -> None:
        ps, pns = split_s(tm + 0.045)
        rs, rns = split_s(tr + 0.045)
        receipt = tm + 0.006
        rec_s, rec_ns = split_s(receipt)
        body = {"schema_major": 2, "schema_minor": 0, "kind": 2,
                "sequence": f + 1, "producer": "statePublisher",
                "publish_real_s": rs, "publish_real_ns": rns,
                "publish_mono_s": ps, "publish_mono_ns": pns,
                "speed_kmh": motion["speed"],
                "longitudinal_acceleration": motion["longitudinalAcceleration"],
                "lateral_acceleration": motion["lateralAcceleration"],
                "yaw_rate_dps": motion["yawRate"],
                "sample_capture_ms": int(round(motion["captureTime"] * 1000)),
                "sample_receipt_mono_s": rec_s, "sample_receipt_mono_ns": rec_ns}
        self.logs.write("score/statePublisher.jsonl", "score", "statePublisher",
                        "out.vehicle_state", dict(body), tm + 0.045, tr + 0.045)
        self.logs.write("guest/observer.jsonl", "guest", "observer", "rx.vehicle_state",
                        dict(body), tm + 0.048, tr + 0.048 + GUEST_REAL_OFFSET)

    def _health(self, f: int, mode: str, cause: str, tm: float, tr: float) -> None:
        ps, pns = split_s(tm + 0.050)
        rs, rns = split_s(tr + 0.050)
        since_s = since_ns = 0
        if self.stop_frame is not None:
            cs, cn = split_s(self.t_mono(self.stop_frame))
            since_s, since_ns = cs, cn
        lpp_s, lpp_ns = split_s(self.last_plan_production)
        body = {"schema_major": 2, "schema_minor": 0, "kind": 3,
                "sequence": f + 1, "producer": "statePublisher",
                "publish_real_s": rs, "publish_real_ns": rns,
                "publish_mono_s": ps, "publish_mono_ns": pns,
                "mode": MODES.index(mode), "cause": CAUSES.index(cause),
                "mode_source": ("actuationAdapter" if self.fault == "comm_stop"
                                else ("" if f < self.prime else "superviseLoop")),
                "cause_since_mono_s": since_s, "cause_since_mono_ns": since_ns,
                "last_plan_frame_index": self.last_plan_frame,
                "last_plan_capture_ms": int(round(self.last_plan_capture * 1000)),
                "step_capture_ms": f * STEP_MS,
                "last_plan_production_mono_s": lpp_s,
                "last_plan_production_mono_ns": lpp_ns,
                "dropped_samples": 0,
                "checkpoint_expected_sha256": "",
                "checkpoint_actual_sha256": "",
                "refusal_reason": ""}
        if self.scenario == "checkpointRefusal":
            body.update({
                "checkpoint_expected_sha256": self.checkpoint_sha
                if self.checkpoint_case == "mismatch" else "",
                "checkpoint_actual_sha256": "ff" * 32,
                "refusal_reason": "mismatch" if self.checkpoint_case == "mismatch"
                else "no_pin"})
        self.logs.write("score/statePublisher.jsonl", "score", "statePublisher",
                        "out.health", dict(body), tm + 0.050, tr + 0.050)
        self.logs.write("guest/observer.jsonl", "guest", "observer", "rx.health",
                        dict(body), tm + 0.053, tr + 0.053 + GUEST_REAL_OFFSET)

    def _initial_state(self, f: int) -> dict:
        return {"v": self.v, "accel": self.accel_long, "yaw_rate": self.yaw_rate,
                "curv": self.curvature, "x": self.x, "y": self.y, "yaw": self.yaw}

    # ----------------------------------------------------------------- run
    def build(self) -> Path:
        self.write_run_record()
        tm0, tr0 = self.t_mono(0), self.t_real(0)
        for rel, comp in (("score/drivingAgent.jsonl", "drivingAgent"),
                          ("score/actuationAdapter.jsonl", "actuationAdapter"),
                          ("score/statePublisher.jsonl", "statePublisher"),
                          ("score/route_provider.jsonl", "routeProvider")):
            self.logs.write(rel, "score", comp, "start", {"pid": 1000}, tm0 - 0.9, tr0 - 0.9)
        self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent", "config",
                        {"configurationIdentity": "DRIVING-CONFIG-001",
                         "checkpointSha256": self.checkpoint_sha,
                         "geometry": "autoe2e-bev-450x300-0p4m-v1"},
                        tm0 - 0.8, tr0 - 0.8)
        # the engine the agent built (agent/cc/agent_ffi.cpp:656-657)
        refused = self.scenario == "checkpointRefusal"
        self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent", "engine",
                        {"stage": "synthetic", "setup_s": 55.0, "refused": refused,
                         "setup": {"engine": "checkpoint",
                                   "engineRecord": {"engine": "checkpoint"}}},
                        tm0 - 0.6, tr0 - 0.6)
        if not refused:
            # the rig, before the first step, unless the checkpoint was refused
            # (agent/cc/agent_ffi.cpp:854-885): its origin is the REF origin the
            # ego-motion rows are worked out at
            self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent", "rig",
                            {"stage": "synthetic", "result": rig_result()},
                            tm0 - 0.5, tr0 - 0.5)
        if self.scenario == "checkpointRefusal":
            self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent", "error",
                            {"code": "checkpoint_refused",
                             "detail": "checkpoint identity not accepted",
                             "expectedSha256": self.checkpoint_sha
                             if self.checkpoint_case == "mismatch" else "",
                             "actualSha256": "ff" * 32,
                             "reason": "mismatch" if self.checkpoint_case == "mismatch"
                             else "no_pin"}, tm0 - 0.4, tr0 - 0.4)
        if self.fault_onset() is not None or self.scenario == "checkpointRefusal":
            f0 = self.fault_onset()
            self.logs.write("bench/injection.jsonl", "bench", "benchController",
                            "injection",
                            {"action": "fault_begin",
                             "t_sim_ms": 0 if f0 is None else f0 * STEP_MS,
                             "t_mono_ns": ns(tm0 + (f0 or 0) * STEP_S),
                             "t_real_ns": ns(tr0 + (f0 or 0) * STEP_S),
                             "detail": {"fault": self.fault}},
                            tm0 + (f0 or 0) * STEP_S, tr0 + (f0 or 0) * STEP_S)
        if self.fault == "comm_stop":
            F = self.fault_onset()
            self.logs.write("bench/injection.jsonl", "bench", "benchController",
                            "injection",
                            {"action": "comm_stop", "t_sim_ms": (F or 0) * STEP_MS,
                             "t_mono_ns": ns(self.t_mono(F or 0)),
                             "t_real_ns": ns(self.t_real(F or 0)),
                             "detail": {"target": "driving-system-mwcom"}},
                            self.t_mono(F or 0), self.t_real(F or 0))

        for f in range(self.frames):
            self.states[f] = self._initial_state(f)
            self.write_frame(f)
            if f == self.prime:
                self.logs.write("score/drivingAgent.jsonl", "score", "drivingAgent",
                                "priming.complete",
                                {"frame": f, "sim_ms": f * STEP_MS,
                                 "historiesReady": True}, self.t_mono(f, 0.020),
                                self.t_real(f, 0.020))

        for entry in self.injections:
            self.logs.write("bench/injection.jsonl", "bench", "benchController",
                            "injection", entry, entry["t_mono_ns"] / 1e9,
                            entry["t_real_ns"] / 1e9)

        if self.scenario != "checkpointRefusal":
            self._write_checkpoint_inputs()
            self._write_bundles()
            self._write_reference_inference()
        self.logs.close()
        return self.root

    def _route_window(self, pose: dict) -> list[tuple[float, float, int, int]]:
        """A16: the route points in the raster window at `pose`.

        Returns (ex, ey, row, col) for each point inside the strict window.
        """
        x0, y0 = pose["x_map_m"], pose["y_map_m"]
        c, s = math.cos(pose["yaw_map_rad"]), math.sin(pose["yaw_map_rad"])
        out = []
        # the producer counts centre-line points (agent/cc/navigation_input.cpp:108-124)
        for wp in centre_line_points(self.route["waypoints"]):
            dx, dy = wp[0] - x0, wp[1] - y0
            ex = c * dx + s * dy
            ey = -s * dx + c * dy
            if not (-10.0 + 0.8 < ex < 120.0 - 0.8
                    and -60.0 + 0.8 < ey < 60.0 - 0.8):
                continue
            out.append((ex, ey, int(math.floor((120.0 - ex) / 0.4)),
                        int(math.floor((60.0 - ey) / 0.4))))
        return out

    def _corridor_cells(self, pose: dict) -> list[list[int]]:
        """The route corridor on the A16 raster: each in-window route cell
        plus one cell around it, so the synthetic on-corridor count equals
        its in-window count."""
        cells = set()
        for _, _, row, col in self._route_window(pose):
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    r, c = row + dr, col + dc
                    if 0 <= r < 450 and 0 <= c < 300:
                        cells.add((r, c))
        return [list(c) for c in sorted(cells)]

    def _input_step(self, f: int, first: bool) -> dict:
        st = self.states.get(f) or self._initial_state(f)
        pose = {"x_map_m": round(st["x"], 6), "y_map_m": round(st["y"], 6),
                "yaw_map_rad": round(st["yaw"], 6)}
        ann = self._route_state(f)
        accepted = ann is not None and (ann.get("corridorPoints") or 0) > 0
        window = self._route_window(pose) if accepted else []
        cells = self._corridor_cells(pose) if accepted else []
        cams = []
        for name in CAMERAS:
            ok, status, ct_ms = self._camera_status(f, name)
            present = status != "missing"
            cam = {
                "name": name,
                # a camera without an image this step has null stamps
                # (agent/cc/agent_ffi.cpp:1028-1033)
                "image_frame": int(round(ct_ms / STEP_MS)) if present else None,
                "capture_sim_ms": ct_ms if present else None,
                "arrival_mono_ns": ns(self.t_mono(f, 0.005)) if present else None,
                "width": 512, "height": 512,
                "valid": ok, "status": status,
                # the agent writes the seven references every step, oldest
                # first (agent/cc/agent_ffi.cpp:1041)
                "history": [f - 5 * j for j in range(7, 0, -1)],
            }
            if name == "front":
                # A11/A17: the front image is also handed to the checkpoint at
                # 1024x1024; width/height above is the 512x512 tile (A17).
                cam["front_hi_res"] = {"width": 1024, "height": 1024}
            cams.append(cam)
        camera_ok = all(c["valid"] and c["status"] == "ok" for c in cams)
        # A26 (agent/cc/agent_ffi.cpp:997-1018, 1072-1073): a step with an input
        # condition is not conditioned, and a step that is not conditioned is
        # not primed.
        conditioned = camera_ok and ann is not None
        primed = conditioned and f >= self.prime
        hist = []
        if primed:
            # The engine works the rows out from the poses of frames f-65 .. f,
            # moved to the rig origin (agent/DESIGN.md, "Ego-motion history"), so
            # row j is the sample of frame f-64+j and the newest row is frame f-1.
            # The agent writes rows only for a conditioned step (agent_ffi.cpp:1049).
            # REQ-DRIVING-008 as amended on 2026-11-09 (GAP-DRIVING-010): yaw rate
            # and curvature are given as zero.
            poses = [ego_pose(self.states[g]) for g in range(f - EGO_POSE_WINDOW + 1, f + 1)]
            hist = ego_motion_rows(poses, RIG_ORIGIN)
        d = {"frame": f, "sim_ms": f * STEP_MS, "cameras": cams,
             "ego_motion_history": hist,
             "map_context_render_sim_ms": max(0, f - 1) * STEP_MS,
             "mapContext": dict(MAP_CONTEXT),
             "routeMask": {
                 "channels": 2, "height": 450, "width": 300,
                 "geometry": GEOMETRY,
                 "corridorCells": len(cells),
                 "routeSha256": self.route_sha if accepted else None,
                 "waypointsInWindow": len(window),
                 # the synthetic producer paints every in-window waypoint's
                 # cell, so on-corridor equals in-window
                 "waypointsOnCorridor": len(window) if accepted else 0},
             "rasterPose": pose,
             "corridor_cell_count": len(cells),
             "destination_cell_count": 1 if accepted else 0,
             "input_conditions": {
                 "camera_ok": camera_ok,
                 "motion_ok": True,
                 "route_ok": ann is not None}}
        d["conditioned"] = conditioned
        d["primed"] = primed
        d["mergedFrames"] = []
        if first:
            # ICD v2 C2: the projection operators once per run, plus on change.
            d["projections"] = [
                {"camera": name, "matrix": [256.0, 420.0, 0.0, 0.0,
                                            256.0, 0.0, -420.0, 0.0,
                                            1.0, 0.0, 0.0, 0.0],
                 "image_size": [512, 512],
                 "images_covered": self.frames}
                for name in CAMERAS]
        return d

    def _write_checkpoint_inputs(self) -> None:
        # one record per step from the agent's first step, primed or not
        # (agent/cc/agent_ffi.cpp:1020-1079)
        for f in range(0, self.frames):
            self.logs.write("score/checkpointInputs.jsonl", "score",
                            "drivingAgent/conditionInputs", "out.checkpoint_inputs",
                            self._input_step(f, first=(f == 0)),
                            MONO0 + f * STEP_S + 0.030, REAL0 + f * STEP_S + 0.030)

    def _bundle_frames(self) -> list[int]:
        sched = {f for f in range(0, self.frames, BUNDLE_PERIOD_STEPS)}
        F = self.fault_onset()
        if F is not None:
            w = int(round(BUNDLE_FAULT_WINDOW_S / STEP_S))
            sched |= {f for f in range(F - w, F + w + 1) if 0 <= f < self.frames}
        return sorted(sched)

    def _write_bundles(self) -> None:
        d = self.root / "score" / "bundles"
        d.mkdir(parents=True, exist_ok=True)
        for f in self._bundle_frames():
            np.savez_compressed(
                str(d / f"{f}.npz"), frame=f,
                camera_names=np.array(CAMERAS),
                images=np.zeros((len(CAMERAS), 3, 8, 8), dtype=np.uint8),
                ego_motion=np.array(self._input_step(f, first=False)["ego_motion_history"],
                                    dtype=np.float32))

    def _write_reference_inference(self) -> None:
        sampled = set(self._bundle_frames())
        for payload in self.plan_payloads:
            if payload["frameIndex"] not in sampled:
                continue
            self.logs.write("score/referenceInference.jsonl", "score",
                            "referenceInference", "reference_inference",
                            {"frameIndex": payload["frameIndex"],
                             "checkpointSha256": self.checkpoint_sha,
                             "sourceRevision": "autoe2e-0.9.0+synth",
                             "acceleration": [s["acceleration"] for s in payload["samples"]],
                             "curvature": [s["curvature"] for s in payload["samples"]]},
                            MONO0 + payload["frameIndex"] * STEP_S + 0.5,
                            REAL0 + payload["frameIndex"] * STEP_S + 0.5)


def build(out: Path, **kw) -> Path:
    if out.exists():
        shutil.rmtree(out)          # a run directory is one run, never appended to
    return RunBuilder(out, **kw).build()


def build_all(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    made: dict[str, Path] = {}

    def mk(name: str, **kw) -> None:
        p = root / name
        if p.exists():
            shutil.rmtree(p)
        made[name] = build(p, **kw)

    mk("nominal", scenario="closedLoopRoute", fault="none", role="nominal",
       campaign="closed-loop-route", frames=700, prime=65)
    mk("comm-stop", scenario="closedLoopRoute", fault="comm_stop", role="comm_stop",
       campaign="closed-loop-route", frames=620, prime=65, fault_frame=500)
    for fault in ("camera_missing", "camera_invalid", "camera_stale",
                  "motion_stale", "motion_invalid", "route_stale", "route_empty",
                  "plan_stale", "plan_dropped", "plan_invalid_nan", "plan_invalid_63"):
        mk(f"fault-{fault}", scenario="degradedInputOrPlan", fault=fault,
           role=fault, campaign="degraded", frames=400, prime=65, fault_frame=250,
           entry_speed=10.0)
    for speed in (10, 20):
        mk(f"stop-entry{speed}", scenario="degradedInputOrPlan", fault="camera_missing",
           role=f"entry{speed}", campaign="stop-response", frames=400, prime=65,
           fault_frame=250, entry_speed=float(speed))
    for role in ("ref1", "ref2", "late", "stopped"):
        mk(f"aaos-{role}", scenario="aaosUnavailable", fault="none", role=role,
           campaign="obs-independence", frames=350, prime=65,
           aaos_mode={"late": "late", "stopped": "stopped"}.get(role, "on_time"))
    for case in ("mismatch", "unpinned"):
        mk(f"refusal-{case}", scenario="checkpointRefusal",
           fault="checkpoint_mismatch" if case == "mismatch" else "checkpoint_unpinned",
           role=case, campaign="checkpoint-refusal", frames=150, prime=65,
           checkpoint_case=case)
    return made


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--all", action="store_true", help="write the whole fixture set")
    ap.add_argument("--scenario", default="closedLoopRoute")
    ap.add_argument("--fault", default="none")
    ap.add_argument("--entry-speed", type=float, default=0.0)
    ap.add_argument("--role", default="nominal")
    ap.add_argument("--campaign", default="nominal")
    ap.add_argument("--frames", type=int, default=700)
    ap.add_argument("--prime", type=int, default=65)
    ap.add_argument("--fault-frame", type=int, default=250)
    ap.add_argument("--aaos-mode", default="absent")
    ap.add_argument("--checkpoint-case", default="pinned")
    args = ap.parse_args()

    if args.all:
        for name, p in build_all(args.out).items():
            print(f"{name}\t{p}")
        return
    print(build(args.out, scenario=args.scenario, fault=args.fault, role=args.role,
                campaign=args.campaign, entry_speed=args.entry_speed, frames=args.frames,
                fault_frame=args.fault_frame, aaos_mode=args.aaos_mode,
                checkpoint_case=args.checkpoint_case))


if __name__ == "__main__":
    main()
