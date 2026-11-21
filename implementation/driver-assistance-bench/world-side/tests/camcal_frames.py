"""Frames and captures of the camera-calibration tests, without pytest.

The test module imports these, and so does the subprocess of a test that runs under DE4SDV_CV_PYTHON (a Python with
OpenCV and numpy, such as /usr/bin/python3). That Python need not carry pytest: the test VM's has none, so a
subprocess that imported the test module (which imports pytest and conftest) ended in ModuleNotFoundError there.
Import only the standard library and camera_calibration here.
"""

from __future__ import annotations

from pathlib import Path

import camera_calibration as cc

DATA = Path(__file__).resolve().parent / "data"


def bgra_from_grey_png(path: Path, factor: int) -> tuple[int, int, bytes]:
    """A grey fixture PNG, scaled up by <factor> (nearest), as CARLA's BGRA raw data."""
    w, h, px = cc.read_png_rgba(path.read_bytes())
    out = bytearray()
    for y in range(h):
        row = bytearray()
        for x in range(w):
            g = px[y][x][0]
            row += bytes([g, g, g, 255]) * factor
        out += bytes(row) * factor
    return w * factor, h * factor, bytes(out)


def checker_frame(cap: dict, w: int, h: int, black: int, white: int) -> bytes:
    """A frame whose boards are drawn from the capture's own geometry: a 4x4 checker of <black> and <white>."""
    raw = bytearray(bytes([150, 150, 150, 255]) * (w * h))
    camera = cc.camera_in_ground_frame(cap)
    to_ground = cc.image_to_ground(camera, float(cap.get("boardLiftM", 0.0)))
    size = cap["boardSizeM"]
    for label, (bx, by) in cap["upstreamArgs"].items():
        quad = [cc.apply_h(cc.ground_to_image(camera, 0.0), bx + dx, by + dy)
                for dx in (-size / 2, size / 2) for dy in (-size / 2, size / 2)]
        u0, u1 = int(min(q[0] for q in quad)), int(max(q[0] for q in quad)) + 1
        v0, v1 = int(min(q[1] for q in quad)), int(max(q[1] for q in quad)) + 1
        for v in range(max(0, v0), min(h, v1)):
            for u in range(max(0, u0), min(w, u1)):
                X, Y = cc.apply_h(to_ground, u, v)
                lx, ly = (X - bx) / size + 0.5, (Y - by) / size + 0.5
                if 0 <= lx < 1 and 0 <= ly < 1:
                    g = black if (int(lx * 4) + int(ly * 4)) % 2 else white
                    i = 4 * (v * w + u)
                    raw[i:i + 3] = bytes([g, g, g])
    return bytes(raw)


def rig_capture() -> dict:
    layout = cc.board_layout(cc.DEFAULT_NEAR_M, cc.DEFAULT_FAR_M, cc.DEFAULT_HALF_SPACING_M)
    return {"frontCamera": {"image_size_x": "1920", "image_size_y": "1280", "fov": "50.0",
                            "pose": {"x": 1.544, "y": 0.0243, "z": 2.116, "roll": -0.10, "pitch": -0.11,
                                     "yaw": -0.23}},
            "frontBumperXM": 2.45, "groundZ": 0.0, "heroZ": 0.0, "boardLiftM": 0.0,
            "heroWorld": {"x": 0.0, "y": 0.0, "z": 0.0, "pitch": 0.0, "yaw": 0.0, "roll": 0.0},
            "cameraWorld": {"x": 1.544, "y": 0.0243, "z": 2.116, "pitch": -0.11, "yaw": -0.23, "roll": -0.10},
            "boardSizeM": cc.DEFAULT_BOARD_SCALE, "upstreamArgs": {k: list(v) for k, v in layout.items()}}
