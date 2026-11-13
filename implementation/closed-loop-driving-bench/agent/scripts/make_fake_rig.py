#!/usr/bin/env python3
"""A profile-exact stand-in rig for drivingAgent's fake world (slice 10b).

The six cameras of the AutoE2E camera profile, at their render sizes and mounting poses, on a vehicle
at the world origin, as the world side spawns them in CARLA. The camera actor poses come from
de4sdv_planner.rig.actor_pose_in_vehicle; each is checked by the round trip through
T_ref_opt_from_actor (the agent's set_rig direction): the script refuses to write a rig whose round
trip misses the profile by 1 mm or 0.01 degrees.

    make_fake_rig.py --out rig.json [--profile <calibration json>] [--width 1920] [--front-width 1920]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "python"))
from de4sdv_planner import rig as R  # noqa: E402

# Stand-in vehicle (Lincoln MKZ 2020 class, 2.85 m wheelbase), wheel centres in world metres.
WHEELS = [[1.40, -0.80, 0.35], [1.40, 0.80, 0.35], [-1.45, -0.80, 0.35], [-1.45, 0.80, 0.35]]
RADII = [0.35, 0.35, 0.35, 0.35]


def ue_matrix(loc, pitch: float, yaw: float, roll: float) -> np.ndarray:
    """carla.Transform(location, rotation).get_matrix(): UE local->world, degrees."""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    return np.array([[cp * cy, cy * sp * sr - sy * cr, -cy * sp * cr - sy * sr, loc[0]],
                     [cp * sy, sy * sp * sr + cy * cr, -sy * sp * cr + cy * sr, loc[1]],
                     [sp, -cp * sr, cp * cr, loc[2]],
                     [0.0, 0.0, 0.0, 1.0]])


def build(profile: str, width: int, front_width: int) -> dict:
    payload, cams = R.load_profile(profile)
    M_veh = np.eye(4)
    origin, info = R.ref_origin_from_raw(M_veh, [0.0, 0.0, 0.0], WHEELS, RADII)
    out = []
    for i, cam in enumerate(cams):
        W, H, _f, hfov = R.render_spec(cam, front_width if i == 0 else width)
        T = np.asarray(cam["camera_to_reference"], dtype=np.float64).reshape(4, 4)
        loc, (pitch, yaw, roll) = R.actor_pose_in_vehicle(T, origin)
        M_va = ue_matrix(loc, pitch, yaw, roll)
        back = R.T_ref_opt_from_actor(M_va, origin)
        err_mm = float(np.linalg.norm(back[:3, 3] - T[:3, 3]) * 1000.0)
        err_deg = float(R.rotation_angle_deg(back[:3, :3] @ T[:3, :3].T))
        if not (err_mm < 1.0 and err_deg < 0.01):
            raise SystemExit(f"round trip of {cam['slot']} misses the profile: {err_mm:.4f} mm, {err_deg:.5f} deg")
        out.append({"slot": cam["slot"], "width": W, "height": H, "fov": hfov,
                    "world_matrix": (M_veh @ M_va).reshape(-1).tolist(),
                    "roundtrip_err_mm": err_mm, "roundtrip_err_deg": err_deg})
    return {"stage": "fake rig from the camera profile (stand-in for the world side's spawn)",
            "profile": profile, "dataset": payload.get("dataset_name"),
            "vehicle": {"world_matrix": M_veh.reshape(-1).tolist(), "location": [0.0, 0.0, 0.0],
                        "wheel_positions": WHEELS, "wheel_radii": RADII, "ref_origin": origin.tolist(),
                        "ref_origin_info": info},
            "cameras": out}


def main() -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    ap.add_argument("--out", required=True)
    ap.add_argument("--profile", default=R.PROFILE)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--front-width", type=int, default=1920)
    a = ap.parse_args()
    rig = build(a.profile, a.width, a.front_width)
    Path(a.out).write_text(json.dumps(rig, indent=1) + "\n")
    for c in rig["cameras"]:
        print(f"{c['slot']:<12} {c['width']}x{c['height']} fov {c['fov']:.2f}  round trip "
              f"{c['roundtrip_err_mm']:.2e} mm {c['roundtrip_err_deg']:.2e} deg")
    return 0


if __name__ == "__main__":
    sys.exit(main())
