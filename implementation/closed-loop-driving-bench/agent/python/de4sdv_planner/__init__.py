"""drivingAgent's embedded planner package (INC-DRIVING-001 slice 10b, WP2; DESIGN.md).

Called from C++ (cc/planner_bridge.cpp) on FEO worker 40, in this order:
  setup(config_json) -> json        inferPlan startup: checkpoint identity first (REQ-DRIVING-035),
                                    then the engine (load, warm-up, parity); run-record fields
  set_rig(rig_json) -> json         conditionInputs, once: projections from the rig read back from CARLA
  condition(frame, images, shapes, world_from_vehicle, map_context, route_mask)
      -> (primed, measured_rows, checkpoint_rows, record_json)
                                    conditionInputs, every step: tiles, histories, ego-motion rows
  infer(frame) -> None | (samples, v0, record_json)
                                    inferPlan, every step: 64 x (a, kappa, x, y, heading) float32
  write_run_record(path, fields_json) -> json
                                    inferPlan startup, before the first plan: ICD section 8
  shutdown() -> None

Engines: "checkpoint" (the R2 stack of the closed-loop probes, checkpoint.py) and "stub" (numpy only,
for the S-CORE host without a GPU: same API, same histories, a straight constant-speed plan, every
record marked "engine": "stub").
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import time

import numpy as np

from . import history as H
from . import rig as R

_ENGINE = None


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def identity_check(cfg: dict) -> dict:
    """REQ-DRIVING-035: refuse when the configuration names no SHA-256 or the checkpoint differs."""
    pin = str(cfg.get("checkpoint_sha256") or "").lower()
    path = str(cfg.get("checkpoint_path") or "")
    actual = sha256_file(path) if path and os.path.isfile(path) else ""
    if not pin:
        return {"refused": True, "reason": "no_pin", "expectedSha256": "", "actualSha256": actual}
    if actual != pin:
        return {"refused": True, "reason": "mismatch", "expectedSha256": pin, "actualSha256": actual}
    return {"refused": False, "reason": "", "expectedSha256": pin, "actualSha256": actual}


def ue_pose_in_map(M_world_veh, origin) -> tuple[float, float, float]:
    """REF (the vehicle origin + the rig's origin offset, CARLA/UE axes) as a map-frame pose
    (ICD section 9: x_map = x, y_map = -y, yaw_map = -yaw)."""
    M = np.asarray(M_world_veh, dtype=np.float64).reshape(4, 4)
    o = np.zeros(3) if origin is None else np.asarray(origin, dtype=np.float64).reshape(3)
    p = M[:3, :3] @ o + M[:3, 3]
    return float(p[0]), float(-p[1]), float(-math.atan2(M[1, 0], M[0, 0]))


def pure_pursuit_curvature(route_xy: np.ndarray, pose, lookahead_m: float, limit: float = 0.2) -> float:
    """Curvature (1/m, positive to the left) toward the route point lookahead_m ahead of the
    route point nearest to the pose, all in the map frame (right-handed, y left)."""
    x, y, yaw = pose
    i = int(np.argmin(np.hypot(route_xy[:, 0] - x, route_xy[:, 1] - y)))
    seg = np.hypot(np.diff(route_xy[i:, 0]), np.diff(route_xy[i:, 1]))
    j = i + int(np.searchsorted(np.cumsum(seg), lookahead_m)) + 1 if len(seg) else i
    qx, qy = route_xy[min(j, len(route_xy) - 1)]
    dx = math.cos(yaw) * (qx - x) + math.sin(yaw) * (qy - y)
    dy = -math.sin(yaw) * (qx - x) + math.cos(yaw) * (qy - y)
    d2 = dx * dx + dy * dy
    return 0.0 if d2 < 1e-6 else float(np.clip(2.0 * dy / d2, -limit, limit))


class StubEngine:
    """No model: conditions the same histories and returns a straight plan at the measured speed.

    Integration mode (bench plumbing only, never a model result): with stub_route (ICD section 9
    route, map frame) and stub_target_speed_mps in the planner configuration, the plan follows the
    route by pure pursuit at the target speed, so the commander, the actuation adapter's control
    conversion and the vehicle run in closed loop. Every plan is labelled stub-pure-pursuit.

    Stall (integration runs only): with stub_stall_ms and stub_stall_every, the plan of every frame
    that is a multiple of stub_stall_every takes stub_stall_ms longer, so that FEO merges the frames
    that arrive meanwhile (DESIGN.md, merged frames). The engine record and each stalled plan's
    record carry the stall.
    """

    name = "stub"

    def __init__(self, cfg: dict):
        payload, self.cams = R.load_profile(cfg["profile"]) if cfg.get("profile") else ({}, [])
        self.curv = R.egomotion_rule(payload)
        self.poses = H.PoseRing()
        self.frames_with_images: set[int] = set()
        self.rows: dict[int, np.ndarray] = {}
        self.origin = None
        self.record = {"engine": self.name, "cudnn": None, "parity": None, "warmupSteps": 0}
        self.route_xy = None
        if cfg.get("stub_route"):
            with open(cfg["stub_route"]) as f:
                self.route_xy = np.asarray([w[:2] for w in json.load(f)["waypoints"]], dtype=np.float64)
        self.target_mps = float(cfg.get("stub_target_speed_mps", 0.0))
        self.lookahead_m = float(cfg.get("stub_lookahead_m", 6.0))
        self.pose_map: dict[int, tuple[float, float, float]] = {}
        self.stall = None
        if "stub_stall_ms" in cfg or "stub_stall_every" in cfg:
            ms, every = float(cfg.get("stub_stall_ms", -1)), int(cfg.get("stub_stall_every", 0))
            if not (ms >= 0.0 and every >= 1):
                raise ValueError("stub_stall_ms >= 0 and stub_stall_every >= 1 are both needed, got %r and %r"
                                 % (cfg.get("stub_stall_ms"), cfg.get("stub_stall_every")))
            self.stall = {"ms": ms, "every": every}
        self.record["stall"] = self.stall

    def bind_thread(self) -> dict:
        import threading
        return {"engine": self.name, "thread": threading.get_ident()}

    def set_rig(self, rig: dict) -> dict:
        v = rig["vehicle"]
        self.origin, info = R.ref_origin_from_raw(v["world_matrix"], v["location"], v["wheel_positions"],
                                                  v["wheel_radii"])
        out = {"engine": self.name, "origin": self.origin.tolist(), "origin_info": info}
        if self.cams:  # the mount check needs no GPU: the agent's rig gate works with this engine too
            out["rig_pose_err_mm"], out["rig_pose_err_deg"] = R.rig_mount_errors(self.cams, rig, self.origin)
        return out

    def condition(self, k, images, shapes, M_world_veh, map_context, route_mask):
        if all(im is not None for im in images):
            self.frames_with_images.add(k)
        self.frames_with_images = {j for j in self.frames_with_images if j >= k - 40}
        self.poses.add(k, R.T_world_ref(M_world_veh, self.origin))
        if self.route_xy is not None:
            self.pose_map[k] = ue_pose_in_map(M_world_veh, self.origin)
            self.pose_map = {j: p for j, p in self.pose_map.items() if j >= k - 8}
        primed = self.poses.complete(k) and all(j in self.frames_with_images for j in H.camera_history_frames(k) + [k])
        measured = H.egomotion_rows(self.poses.window(k), self.curv) if self.poses.complete(k) else None
        if measured is not None:
            self.rows[k] = measured
        self.rows = {j: r for j, r in self.rows.items() if j >= k - 8}
        return primed, measured, {"engine": self.name}

    def infer(self, k):
        if k not in self.rows or k not in self.frames_with_images:
            return None
        rec = {"engine": self.name}
        if self.stall is not None and k % self.stall["every"] == 0:
            time.sleep(self.stall["ms"] / 1000.0)
            rec["stall_ms"] = self.stall["ms"]
        v0 = float(self.rows[k][-1, 0])
        if self.route_xy is None or k not in self.pose_map:
            t = np.arange(1, 65, dtype=np.float32) * 0.1
            samples = np.zeros((64, 5), dtype=np.float32)
            samples[:, 2] = v0 * t
            return samples, v0, rec
        kappa = pure_pursuit_curvature(self.route_xy, self.pose_map[k], self.lookahead_m)
        samples = np.zeros((64, 5), dtype=np.float32)
        v, x, y, h = v0, 0.0, 0.0, 0.0
        for i in range(64):           # ego frame at the step: integrate the plan's own pose
            a = float(np.clip((self.target_mps - v) / 2.0, -2.0, 1.0))
            v = max(0.0, v + a * 0.1)
            h += kappa * v * 0.1
            x += v * math.cos(h) * 0.1
            y += v * math.sin(h) * 0.1
            samples[i] = (a, kappa, x, y, h)
        return samples, v0, {**rec, "mode": "stub-pure-pursuit", "curvature": kappa}


def setup(config_json: str) -> str:
    global _ENGINE
    cfg = json.loads(config_json)
    ident = identity_check(cfg)
    out = {"identity": ident, "engine": cfg.get("engine", "stub")}
    if ident["refused"]:
        return json.dumps(out)
    if cfg.get("engine") == "checkpoint":
        from .checkpoint import CheckpointEngine
        _ENGINE = CheckpointEngine(cfg)
    else:
        _ENGINE = StubEngine(cfg)
    out["engineRecord"] = _ENGINE.record
    return json.dumps(out)


def bind_thread() -> str:
    """Bind the engine to the calling thread: inferPlan's startup on FEO worker 40, the thread of every
    later condition and infer call. setup() runs before FEO starts (FEO allows an activity's startup
    no longer than its receive timeout)."""
    return json.dumps(_ENGINE.bind_thread())


def set_rig(rig_json: str) -> str:
    return json.dumps(_ENGINE.set_rig(json.loads(rig_json)))


def _as_array(mv, shape, dtype):
    return None if mv is None else np.frombuffer(mv, dtype=dtype).reshape(shape)


def condition(frame, images, shapes, world_from_vehicle, map_context, route_mask):
    """images: 6 memoryviews (BGRA, H x W x 4) or None; shapes: 6 (H, W); world_from_vehicle: 16 float64
    bytes (UE, row-major); map_context / route_mask: float32 memoryviews or None."""
    M = np.frombuffer(world_from_vehicle, dtype=np.float64).reshape(4, 4)
    imgs = [None if im is None else np.frombuffer(im, dtype=np.uint8).reshape(h, w, 4)
            for im, (h, w) in zip(images, shapes)]
    primed, measured, rec = _ENGINE.condition(int(frame), imgs, shapes, M, map_context, route_mask)
    if measured is None:
        return bool(primed), b"", b"", json.dumps(rec)
    return bool(primed), measured.tobytes(), H.checkpoint_rows(measured).tobytes(), json.dumps(rec)


def infer(frame):
    r = _ENGINE.infer(int(frame))
    if r is None:
        return None
    samples, v0, rec = r
    return np.ascontiguousarray(samples, dtype=np.float32).tobytes(), float(v0), json.dumps(rec)


def warm(frame):
    """inferPlan while the agent primes (DESIGN.md, warm-up while priming): the engine may warm its history cache.
    Returns the record to log, or "" when there is nothing to log (an engine without a warm-up, or
    a frame whose camera history is not complete yet)."""
    fn = getattr(_ENGINE, "warm", None)
    if fn is None:
        return ""
    rec = fn(int(frame))
    return "" if rec.get("warm") == "wait" else json.dumps(rec)


def write_run_record(path: str, fields_json: str) -> str:
    """ICD section 8: writes run_record.json once, before the first plan, and returns its identity.

    `fields_json` holds the fields the agent knows (C4 scenario fields, configuration paths, ...).
    Every `{"path": p}` object among the top-level fields gains the SHA-256 of the file it names
    (C7: vehicleConfiguration, navigationMap, route); `null` when the file does not exist. The
    write stamps `writtenAtMonoNs` / `writtenAtRealNs`. The identity is the first 16 hex digits of
    the SHA-256 of the bytes written (ICD section 8). An existing record is never overwritten.
    """
    if os.path.exists(path):
        raise FileExistsError(f"run record exists and is frozen: {path}")
    fields = json.loads(fields_json)
    for value in fields.values():
        if isinstance(value, dict) and isinstance(value.get("path"), str) and "sha256" not in value:
            value["sha256"] = sha256_file(value["path"]) if os.path.isfile(value["path"]) else None
    fields["writtenAtMonoNs"] = time.monotonic_ns()
    fields["writtenAtRealNs"] = time.time_ns()
    data = (json.dumps(fields, indent=1) + "\n").encode()
    tmp = path + ".tmp"
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    digest = hashlib.sha256(data).hexdigest()
    return json.dumps({"path": path, "sha256": digest, "identity": digest[:16]})


def shutdown():
    global _ENGINE
    if _ENGINE is not None and hasattr(_ENGINE, "close"):
        _ENGINE.close()
    _ENGINE = None
