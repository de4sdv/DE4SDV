"""Render a synthetic front-camera image of four textured boards on a flat road (numpy and OpenCV).

Test helper, run as a subprocess by a Python that has numpy and OpenCV. It casts one ray per sub-pixel from the
camera through CARLA's pinhole (f = width / (2 tan(fov / 2)), principal point at the center), with the camera's
forward, right and up vectors taken from CARLA's rotation formulas (an independent code path from the matrix
homography of camera_calibration.py), intersects the road plane and samples the board texture there.

usage: synthetic_render.py <spec.json> <texture.png> <out.png>
spec: {"camera": {width, height, fov, x, y, z, pitch, yaw, roll} in the ground frame's UE axes,
       "boards": [[X, Y], ...] centers in upstream's frame (X forward, Y left), "board_m": size, "plane_z": z}
"""

import json
import math
import sys

import cv2
import numpy as np


def axes(pitch, yaw, roll):
    p, y, r = (math.radians(v) for v in (pitch, yaw, roll))
    fwd = np.array([math.cos(p) * math.cos(y), math.cos(p) * math.sin(y), math.sin(p)])
    right = np.array([math.cos(y) * math.sin(p) * math.sin(r) - math.sin(y) * math.cos(r),
                      math.sin(y) * math.sin(p) * math.sin(r) + math.cos(y) * math.cos(r),
                      -math.cos(p) * math.sin(r)])
    # CARLA's local z axis (Transform::GetMatrix, third column); UE's frame is left-handed
    up = np.array([-math.cos(y) * math.sin(p) * math.cos(r) - math.sin(y) * math.sin(r),
                   -math.sin(y) * math.sin(p) * math.cos(r) + math.cos(y) * math.sin(r),
                   math.cos(p) * math.cos(r)])
    return fwd, right, up


def main():
    spec = json.load(open(sys.argv[1]))
    tex = cv2.imread(sys.argv[2], cv2.IMREAD_GRAYSCALE).astype(np.float32)
    cam = spec["camera"]
    w, h = int(cam["width"]), int(cam["height"])
    f = w / (2.0 * math.tan(math.radians(cam["fov"]) / 2.0))
    fwd, right, up = axes(cam["pitch"], cam["yaw"], cam["roll"])
    origin = np.array([cam["x"], cam["y"], cam["z"]])
    size = float(spec["board_m"])
    acc = np.zeros((h, w), np.float32)
    n = 3
    for sy in range(n):
        for sx in range(n):
            uu, vv = np.meshgrid(np.arange(w, dtype=np.float64) + (sx + 0.5) / n,
                                 np.arange(h, dtype=np.float64) + (sy + 0.5) / n)
            a = (uu - w / 2.0) / f
            b = -(vv - h / 2.0) / f
            d = fwd[None, None, :] + a[..., None] * right[None, None, :] + b[..., None] * up[None, None, :]
            with np.errstate(divide="ignore", invalid="ignore"):
                t = (spec["plane_z"] - origin[2]) / d[..., 2]
            gx = origin[0] + t * d[..., 0]
            gy = origin[1] + t * d[..., 1]
            X, Y = gx, -gy                       # upstream frame: Y left
            img = np.full((h, w), 110.0, np.float32)
            valid = t > 0
            for bx, by in spec["boards"]:
                lu = (X - bx + size / 2.0) / size
                lv = (Y - by + size / 2.0) / size
                inside = valid & (lu >= 0) & (lu < 1) & (lv >= 0) & (lv < 1)
                col = np.clip((lv * tex.shape[1]).astype(np.int64), 0, tex.shape[1] - 1)
                row = np.clip((lu * tex.shape[0]).astype(np.int64), 0, tex.shape[0] - 1)
                img[inside] = tex[row[inside], col[inside]]
            acc += img
    out = (acc / (n * n)).clip(0, 255).astype(np.uint8)
    cv2.imwrite(sys.argv[3], cv2.cvtColor(out, cv2.COLOR_GRAY2BGR))


if __name__ == "__main__":
    main()
