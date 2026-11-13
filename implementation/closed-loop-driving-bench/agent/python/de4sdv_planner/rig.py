# Vendored unchanged from the P3 closed-loop harness (p3_rig.py, slice 10b readiness probes), plus
# ref_origin_from_raw() at the end: the same rear-axle origin computed from raw arrays that the
# agent's LibCarla side reads (no carla module in the embedded interpreter).
"""P3 rig geometry: the pinned checkpoint's nuPlan rig profile placed on a CARLA vehicle.

Frames used here:
  REF  the profile's reference frame: nuPlan ego frame, origin at the rear-axle centre on the
       road plane (z = 0; data_parsing/nuplan/packing.py NUPLAN_EGO_GROUND_Z_M), x forward,
       y left, z up (right-handed).
  OPT  OpenCV optical frame of a camera (x right, y down, z forward), the frame of the
       profile's camera_to_reference.
  ACT  CARLA camera actor frame (Unreal, left-handed): x forward, y right, z up.
  UE   CARLA/Unreal vehicle-local and world frames: left-handed, x forward, y right, z up.
RH <-> UE conversion flips y (S = diag(1, -1, 1)).

CARLA cameras have square pixels and a centred principal point. The render size is chosen so
that squashing the render to the model's square tile reproduces the profile's per-axis tile
intrinsics (fx/W and fy/H); the remaining difference is the principal point, which is recorded.
"""
from __future__ import annotations

import json
import math

import numpy as np

PROFILE = ("/opt/de4sdv-p2/src/Model/plugins/alpasim_driver/alpasim_autoe2e/configs/"
           "calibration/nuplan.json")
SLOTS = ["front", "front_left", "front_right", "rear_left", "rear", "rear_right"]
S3 = np.diag([1.0, -1.0, 1.0])
S4 = np.diag([1.0, -1.0, 1.0, 1.0])
# OPT -> ACT: p_act = A @ p_opt  (act x = opt z, act y = opt x, act z = -opt y)
A_OPT_TO_ACT = np.array([[0.0, 0.0, 1.0], [1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])


def load_profile(path: str = PROFILE):
    payload = json.load(open(path))
    by_slot = {c["slot"]: c for c in payload["cameras"]}
    return payload, [by_slot[s] for s in SLOTS]


def render_spec(cam: dict, width: int | None = None):
    """Square-pixel render (W, H, f, hfov_deg) whose squash reproduces fx/W and fy/H of the profile."""
    K = np.asarray(cam["intrinsic"], dtype=np.float64)
    W0, H0 = cam["image_size_wh"]
    W = int(width or W0)
    f = K[0, 0] * W / W0
    H = int(round(f * H0 / K[1, 1]))
    hfov = 2.0 * math.degrees(math.atan(W / 2.0 / f))
    return W, H, f, hfov


def carla_intrinsic(W: int, H: int, hfov_deg: float) -> np.ndarray:
    f = W / (2.0 * math.tan(math.radians(hfov_deg) / 2.0))
    return np.array([[f, 0.0, W / 2.0], [0.0, f, H / 2.0], [0.0, 0.0, 1.0]])


def scaled_intrinsic(K: np.ndarray, src_wh, target_hw) -> np.ndarray:
    th, tw = target_hw
    sw, sh = src_wh
    K = K.astype(np.float64).copy()
    K[0, :] *= tw / sw
    K[1, :] *= th / sh
    return K


def ue_euler_from_axes(fwd, right, up):
    """Unreal (pitch, yaw, roll) in degrees from actor axes given in UE coordinates."""
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, fwd[2]))))
    yaw = math.degrees(math.atan2(fwd[1], fwd[0]))
    roll = math.degrees(math.atan2(-right[2], up[2]))
    return pitch, yaw, roll


def actor_pose_in_vehicle(T_ref_opt: np.ndarray, ref_origin_ue: np.ndarray):
    """CARLA relative transform (location m, pitch/yaw/roll deg) of a camera actor on the vehicle."""
    R = T_ref_opt[:3, :3]
    t = T_ref_opt[:3, 3]
    fwd, right, up = R[:, 2], R[:, 0], -R[:, 1]          # actor axes in REF (RH)
    fwd_ue, right_ue, up_ue = S3 @ fwd, S3 @ right, S3 @ up
    loc_ue = S3 @ t + ref_origin_ue
    return loc_ue, ue_euler_from_axes(fwd_ue, right_ue, up_ue)


def matrix_of(transform) -> np.ndarray:
    """4x4 local->world matrix of a carla.Transform (UE coordinates)."""
    return np.asarray(transform.get_matrix(), dtype=np.float64)


def T_ref_opt_from_actor(M_veh_act: np.ndarray, ref_origin_ue: np.ndarray) -> np.ndarray:
    """Camera optical frame in REF from the actor's vehicle-local matrix (read back from CARLA)."""
    R_va = M_veh_act[:3, :3]
    t_va = M_veh_act[:3, 3]
    T = np.eye(4)
    T[:3, :3] = S3 @ R_va @ A_OPT_TO_ACT
    T[:3, 3] = S3 @ (t_va - ref_origin_ue)
    return T


def T_world_ref(M_world_veh: np.ndarray, ref_origin_ue: np.ndarray) -> np.ndarray:
    """Pose of REF in a right-handed world frame (world UE with y flipped)."""
    T_o = np.eye(4)
    T_o[:3, 3] = ref_origin_ue
    return S4 @ M_world_veh @ T_o @ S4


def rotation_angle_deg(R: np.ndarray) -> float:
    """Angle of a rotation matrix, atan2(sin, cos) form.

    acos((trace - 1) / 2) is ill-conditioned near zero: CARLA returns float32 matrices, whose
    ~1e-7 trace noise alone reads as ~0.02 deg through acos. sin comes from the skew part.
    """
    c = (np.trace(R) - 1.0) / 2.0
    s = 0.5 * np.linalg.norm([R[2, 1] - R[1, 2], R[0, 2] - R[2, 0], R[1, 0] - R[0, 1]])
    return math.degrees(math.atan2(s, c))


def rotation_angle_deg_acos(R: np.ndarray) -> float:
    c = (np.trace(R) - 1.0) / 2.0
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def ref_origin_from_vehicle(vehicle) -> np.ndarray:
    """Rear-axle centre on the road plane, in vehicle-local UE coordinates (metres).

    Wheel positions are world coordinates; their unit (cm or m) is detected against the
    vehicle's location, and the wheel radius is checked for plausibility.
    """
    pc = vehicle.get_physics_control()
    M = matrix_of(vehicle.get_transform())
    Minv = np.linalg.inv(M)
    loc = vehicle.get_location()
    loc = np.array([loc.x, loc.y, loc.z])
    wheels = pc.wheels
    raw = [np.array([w.position.x, w.position.y, w.position.z]) for w in wheels]
    d_m = max(np.linalg.norm(r - loc) for r in raw)
    d_cm = max(np.linalg.norm(r / 100.0 - loc) for r in raw)
    scale = 1.0 if d_m < d_cm else 0.01
    rear = [raw[2] * scale, raw[3] * scale]               # FL, FR, RL, RR
    pts = [(Minv @ np.append(p, 1.0))[:3] for p in rear]
    centre = np.mean(pts, axis=0)
    radius = float(np.mean([wheels[2].radius, wheels[3].radius]))
    radius_m = radius / 100.0 if radius > 5.0 else radius
    assert 0.15 < radius_m < 0.7, ("implausible wheel radius", radius)
    return np.array([centre[0], centre[1], centre[2] - radius_m]), {
        "wheel_position_unit": "m" if scale == 1.0 else "cm", "wheel_radius_m": radius_m,
        "rear_wheels_vehicle_local_m": [p.tolist() for p in pts]}


def egomotion_rule(payload: dict):
    e = payload.get("egomotion", {})
    floor = float(e.get("curvature_speed_floor_mps", 0.1))
    zero_below = e.get("curvature_zero_below_mps")
    limit = e.get("curvature_limit")

    def curvature(yaw_rate, speed):
        c = yaw_rate / np.maximum(speed, floor)
        if zero_below is not None:
            c = np.where(speed > zero_below, c, 0.0)
        if limit is not None:
            c = np.clip(c, -limit, limit)
        return c
    return curvature


def ref_origin_from_raw(M_world_veh, location, wheel_positions, wheel_radii):
    """ref_origin_from_vehicle() on raw arrays (the agent's LibCarla side reads them in C++).

    M_world_veh: 4x4 vehicle->world matrix (UE); location: vehicle location (m); wheel_positions:
    4 world positions FL, FR, RL, RR as CARLA reports them (cm or m, detected as above);
    wheel_radii: the 4 radii as reported.
    """
    M = np.asarray(M_world_veh, dtype=np.float64).reshape(4, 4)
    Minv = np.linalg.inv(M)
    loc = np.asarray(location, dtype=np.float64).reshape(3)
    raw = [np.asarray(w, dtype=np.float64).reshape(3) for w in wheel_positions]
    d_m = max(np.linalg.norm(r - loc) for r in raw)
    d_cm = max(np.linalg.norm(r / 100.0 - loc) for r in raw)
    scale = 1.0 if d_m < d_cm else 0.01
    rear = [raw[2] * scale, raw[3] * scale]
    pts = [(Minv @ np.append(p, 1.0))[:3] for p in rear]
    centre = np.mean(pts, axis=0)
    radius = float(np.mean([wheel_radii[2], wheel_radii[3]]))
    radius_m = radius / 100.0 if radius > 5.0 else radius
    assert 0.15 < radius_m < 0.7, ("implausible wheel radius", radius)
    return np.array([centre[0], centre[1], centre[2] - radius_m]), {
        "wheel_position_unit": "m" if scale == 1.0 else "cm", "wheel_radius_m": radius_m,
        "rear_wheels_vehicle_local_m": [p.tolist() for p in pts]}


def rig_mount_errors(cams: list, rig: dict, ref_origin_ue) -> tuple[list, list]:
    """Per camera, how far the mount read back from the simulator is from the profile:
    (position error in mm, rotation error in degrees) of T_ref_opt_from_actor against the
    profile's camera_to_reference. rig: the set_rig document (vehicle and camera world matrices)."""
    M_veh = np.asarray(rig["vehicle"]["world_matrix"], dtype=np.float64).reshape(4, 4)
    mm, deg = [], []
    for cam, c in zip(cams, rig["cameras"]):
        M_va = np.linalg.inv(M_veh) @ np.asarray(c["world_matrix"], dtype=np.float64).reshape(4, 4)
        T = T_ref_opt_from_actor(M_va, ref_origin_ue)
        P = np.asarray(cam["camera_to_reference"], dtype=np.float64).reshape(4, 4)
        mm.append(float(np.linalg.norm(T[:3, 3] - P[:3, 3]) * 1000.0))
        deg.append(float(rotation_angle_deg(T[:3, :3] @ P[:3, :3].T)))
    return mm, deg


def c2_projection_block(P_cur, P_front, tile_wh=(512, 512), front_wh=(1024, 1024)) -> list:
    """C2 `projections` (ICD section 10, once per run): per camera, in SLOTS order and with the
    C2 camera names, the 3x4 operator handed to the checkpoint for its tile, row-major; the front
    camera also carries the operator of its high-resolution image.
    P_cur: (6, 3, 4) or (1, 6, 3, 4); P_front: (3, 4), (1, 3, 4) or (1, 1, 3, 4)."""
    P_cur = np.asarray(P_cur, dtype=np.float64).reshape(len(SLOTS), 3, 4)
    P_front = np.asarray(P_front, dtype=np.float64).reshape(3, 4)
    block = [{"camera": slot, "matrix": P_cur[i].reshape(-1).tolist(), "image_size": list(tile_wh)}
             for i, slot in enumerate(SLOTS)]
    block[0].update(front_hi_res_matrix=P_front.reshape(-1).tolist(), front_hi_res_size=list(front_wh))
    return block
