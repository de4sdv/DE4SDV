#!/usr/bin/env python3
"""The camera calibration file of the CARLA front camera: geometry, the run of upstream's script, the record.

The candidate estimates distances through the homography of ``H.yaml`` in its working directory
(vision_pilot.cpp:114 at 014e0e7a), which has to match the simulated camera (PSR ``gapCameraImageAndGeometry``).
The owner chose on 2026-11-18 that the bench supplies that file for the CARLA camera, computed with upstream's
script, hashed and named in every verdict. The procedure:

1. ``da_world_side.py camera-capture`` (simulator host): four of upstream's 4x4 checkerboards
   (Calibration/checkerboard-bw-4x4.png) are laid flat on the road ahead of the hero as textured flat meshes, and
   one front image is saved with the boards' true centers in upstream's frame: X forward, Y left, origin at the
   front bumper's center on the ground (Calibration/README.md:23).
2. ``camera_calibration.py make-h`` (any host with OpenCV and numpy): runs upstream's
   Calibration/calc_front_camera_homography.py, unchanged, on that image with those centers, then upstream's
   VisionPilot/scripts/find_homography_C_matrix.py, unchanged, for the second matrix file the candidate reads
   (image_preprocessor.cpp:7 loads homography_C_matrix.yaml, which upstream's build derives from H.yaml:
   VisionPilot/CMakeLists.txt:49-53). It cross-checks upstream's H against the homography computed here from
   the camera's settings and pose, and writes the record with the sha256 of both files.

This module itself is pure Python (no numpy), so its geometry runs in the bench's unit tests.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import struct
import subprocess
import sys
import zlib
from pathlib import Path

VP_PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"
UPSTREAM_CALC = "Calibration/calc_front_camera_homography.py"
UPSTREAM_C = "VisionPilot/scripts/find_homography_C_matrix.py"
UPSTREAM_BOARD = "Calibration/checkerboard-bw-4x4.png"
# A flat mesh that takes the texture: CARLA's static.prop.mesh with a mesh_path and a uniform scale
# (Unreal/CarlaUnreal/Plugins/Carla/Source/Carla/Actor/StaticMeshFactory.cpp:15-36 at 14ac3b1a50). The engine's
# 1 m plane is a CANDIDATE: whether the package cooks it, and whether its material takes the texture (the game
# mode sets the texture parameters "BaseColor" and "Difuse", CarlaGameModeBase.cpp:505-533), is unverified.
DEFAULT_MESH_PATH = "/Engine/BasicShapes/Plane.Plane"
DEFAULT_BOARD_SCALE = 2.5        # a 2.5 m board, 0.625 m squares (proposal)
DEFAULT_NEAR_M = 8.0             # board centers ahead of the bumper (proposal)
DEFAULT_FAR_M = 13.0
DEFAULT_HALF_SPACING_M = 1.6     # board centers left and right of the vehicle's center line (proposal)
AGREE_RANGE_M = (10.0, 60.0)     # PROPOSAL: the cross-check range ahead of the bumper
AGREE_TOLERANCE = 0.02           # PROPOSAL: upstream's H and the settings' H agree within 2 % of the distance

PIXEL_CENTER = 0.5               # OpenCV's pixel-center convention, see ground_to_image
Matrix = list[list[float]]


# ------------------------------------------------------------------ linear algebra


def matmul(a: Matrix, b: Matrix) -> Matrix:
    return [[sum(a[i][k] * b[k][j] for k in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def transpose(a: Matrix) -> Matrix:
    return [list(row) for row in zip(*a)]


def solve(a: Matrix, b: list[float]) -> list[float]:
    """Gaussian elimination with partial pivoting."""
    n = len(a)
    m = [list(map(float, a[i])) + [float(b[i])] for i in range(n)]
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        if abs(m[piv][col]) < 1e-15:
            raise ValueError("singular system")
        m[col], m[piv] = m[piv], m[col]
        for r in range(n):
            if r != col:
                f = m[r][col] / m[col][col]
                for c in range(col, n + 1):
                    m[r][c] -= f * m[col][c]
    return [m[i][n] / m[i][i] for i in range(n)]


def inverse3(h: Matrix) -> Matrix:
    cols = [solve(h, [1.0 if i == j else 0.0 for i in range(3)]) for j in range(3)]
    return transpose(cols)


def normalized(h: Matrix) -> Matrix:
    s = h[2][2]
    return [[v / s for v in row] for row in h]


def apply_h(h: Matrix, x: float, y: float) -> tuple[float, float]:
    w = h[2][0] * x + h[2][1] * y + h[2][2]
    return ((h[0][0] * x + h[0][1] * y + h[0][2]) / w, (h[1][0] * x + h[1][1] * y + h[1][2]) / w)


def dlt(src: list[tuple[float, float]], dst: list[tuple[float, float]]) -> Matrix:
    """The homography (h33 = 1) that maps four src points onto four dst points, exactly."""
    if len(src) != 4 or len(dst) != 4:
        raise ValueError("four point pairs")
    a, b = [], []
    for (x, y), (u, v) in zip(src, dst):
        a.append([x, y, 1.0, 0.0, 0.0, 0.0, -u * x, -u * y]); b.append(u)
        a.append([0.0, 0.0, 0.0, x, y, 1.0, -v * x, -v * y]); b.append(v)
    h = solve(a, b)
    return [h[0:3], h[3:6], [h[6], h[7], 1.0]]


# ------------------------------------------------------------------ the camera


def rotation_ue(pitch: float, yaw: float, roll: float) -> Matrix:
    """CARLA's rotation (Transform::GetMatrix, degrees): local -> parent, UE axes x forward, y right, z up."""
    cy, sy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    cr, sr = math.cos(math.radians(roll)), math.sin(math.radians(roll))
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    return [[cp * cy, cy * sp * sr - sy * cr, -cy * sp * cr - sy * sr],
            [cp * sy, sy * sp * sr + cy * cr, -sy * sp * cr + cy * sr],
            [sp, -cp * sr, cp * cr]]


def focal_px(width: int, fov_deg: float) -> float:
    """CARLA's pinhole: f = width / (2 tan(fov / 2)), principal point at the image center."""
    return width / (2.0 * math.tan(math.radians(fov_deg) / 2.0))


def ground_to_image(camera: dict, plane_z: float = 0.0) -> Matrix:
    """The homography from upstream's ground frame (X forward, Y left, meters, on the plane z = plane_z) to the
    image (u right, v down, pixels), for a camera given in the ground frame's UE axes:
    camera = {width, height, fov, x, y, z (camera position, UE axes: y right), pitch, yaw, roll (degrees)}."""
    f = focal_px(int(camera["width"]), float(camera["fov"]))
    # The optical axis meets the image at its geometric center, (width / 2, height / 2) in continuous image
    # coordinates; OpenCV, and so upstream's script, puts pixel (0, 0)'s center at (0, 0): half a pixel less.
    cx, cy = camera["width"] / 2.0 - PIXEL_CENTER, camera["height"] / 2.0 - PIXEL_CENTER
    r = rotation_ue(camera["pitch"], camera["yaw"], camera["roll"])
    rt = transpose(r)
    t = [camera["x"], camera["y"], camera["z"]]
    # point - t = X * (1, 0, 0) + Y * (0, -1, 0) + ((0, 0, plane_z) - t); camera axes = R^T (point - t)
    c1 = [rt[i][0] for i in range(3)]
    c2 = [-rt[i][1] for i in range(3)]
    d = [-t[0], -t[1], plane_z - t[2]]
    c3 = [sum(rt[i][k] * d[k] for k in range(3)) for i in range(3)]
    m = [[cx, f, 0.0], [cy, 0.0, -f], [1.0, 0.0, 0.0]]
    return matmul(m, transpose([c1, c2, c3]))


def image_to_ground(camera: dict, plane_z: float = 0.0) -> Matrix:
    """H as upstream's H.yaml holds it: image (u, v) -> ground (X, Y), normalized to h33 = 1."""
    return normalized(inverse3(ground_to_image(camera, plane_z)))


def camera_in_ground_frame(capture: dict) -> dict:
    """The front camera's pose in upstream's ground frame from a camera-capture record: origin at the front
    bumper's center on the ground, axes along the hero's heading (UE axes, y right)."""
    cam = capture["frontCamera"]
    pose = cam["pose"]
    if capture.get("cameraWorld") and capture.get("heroWorld"):
        # From the simulator's own world poses of the camera and the hero at the capture.
        hw, cw = capture["heroWorld"], capture["cameraWorld"]
        yaw = math.radians(hw["yaw"])
        bumper = float(capture["frontBumperXM"])
        ox, oy = hw["x"] + bumper * math.cos(yaw), hw["y"] + bumper * math.sin(yaw)
        dx, dy = cw["x"] - ox, cw["y"] - oy
        return {"width": int(cam["image_size_x"]), "height": int(cam["image_size_y"]), "fov": float(cam["fov"]),
                "x": dx * math.cos(yaw) + dy * math.sin(yaw), "y": -dx * math.sin(yaw) + dy * math.cos(yaw),
                "z": cw["z"] - float(capture["groundZ"]), "pitch": cw["pitch"],
                "yaw": (cw["yaw"] - hw["yaw"] + 180.0) % 360.0 - 180.0, "roll": cw["roll"]}
    hero_pitch = float(capture.get("heroPitchDeg", 0.0))
    hero_roll = float(capture.get("heroRollDeg", 0.0))
    height_above_ground = float(capture.get("heroZ", 0.0)) - float(capture.get("groundZ", 0.0))
    # Camera position in the hero frame, rotated by the hero's pitch and roll (the heading is the frame's own).
    r = rotation_ue(hero_pitch, 0.0, hero_roll)
    p = [pose["x"], pose["y"], pose["z"]]
    w = [sum(r[i][k] * p[k] for k in range(3)) for i in range(3)]
    return {"width": int(cam["image_size_x"]), "height": int(cam["image_size_y"]), "fov": float(cam["fov"]),
            "x": w[0] - float(capture["frontBumperXM"]), "y": w[1], "z": w[2] + height_above_ground,
            # Small angles: the camera's mount angles plus the hero's attitude.
            "pitch": pose["pitch"] + hero_pitch, "yaw": pose["yaw"], "roll": pose["roll"] + hero_roll}


def board_layout(near_m: float, far_m: float, half_spacing_m: float) -> dict[str, tuple[float, float]]:
    """Upstream's four boards: top = far, left = +Y (Calibration/README.md:16-23)."""
    return {"tl": (far_m, half_spacing_m), "tr": (far_m, -half_spacing_m),
            "bl": (near_m, half_spacing_m), "br": (near_m, -half_spacing_m)}


def predicted_pixels(camera: dict, layout: dict, plane_z: float = 0.0) -> dict:
    h = ground_to_image(camera, plane_z)
    return {k: [round(c, 2) for c in apply_h(h, x, y)] for k, (x, y) in layout.items()}


def cross_check(h_upstream: Matrix, h_settings: Matrix, xs=None, ys=(-1.75, 0.0, 1.75)) -> dict:
    """Map ground points to the image with the settings' homography and back with upstream's; report how far
    upstream's H puts each point, as a share of its distance."""
    xs = xs or [10.0, 15.0, 20.0, 30.0, 40.0, 60.0, 80.0, 100.0, 120.0]
    to_image = inverse3(h_settings)
    rows = []
    for x in xs:
        for y in ys:
            u, v = apply_h(to_image, x, y)
            ux, uy = apply_h(h_upstream, u, v)
            rows.append({"X": x, "Y": y, "u": round(u, 2), "v": round(v, 2), "upstreamX": round(ux, 4),
                         "upstreamY": round(uy, 4), "relErrX": round((ux - x) / x, 5)})
    in_range = [abs(r["relErrX"]) for r in rows if AGREE_RANGE_M[0] <= r["X"] <= AGREE_RANGE_M[1]]
    worst = max(in_range) if in_range else None
    return {"points": rows, "range": list(AGREE_RANGE_M), "maxRelErrXInRange": worst,
            "tolerance": AGREE_TOLERANCE, "agreeWithinProposal": worst is not None and worst <= AGREE_TOLERANCE,
            "maxRelErrXAll": max(abs(r["relErrX"]) for r in rows)}


# ------------------------------------------------------------------ files


def write_opencv_yaml(h: Matrix, name: str = "H") -> str:
    """OpenCV's FileStorage YAML for a 3x3 double matrix (the layout of upstream's VisionPilot/config/H.yaml)."""
    data = ", ".join(f"{v:.15e}" for row in h for v in row)
    return (f"%YAML:1.0\n---\n{name}: !!opencv-matrix\n   rows: 3\n   cols: 3\n   dt: d\n"
            f"   data: [ {data} ]\n")


def read_opencv_yaml(text: str, name: str = "H") -> Matrix:
    m = re.search(rf"^{re.escape(name)}:\s*!!opencv-matrix(.*?)data:\s*\[(.*?)\]", text, re.S | re.M)
    if not m:
        raise ValueError(f"no opencv-matrix {name!r}")
    rows = int(re.search(r"rows:\s*(\d+)", m.group(1)).group(1))
    cols = int(re.search(r"cols:\s*(\d+)", m.group(1)).group(1))
    values = [float(v) for v in m.group(2).replace("\n", " ").split(",") if v.strip()]
    if len(values) != rows * cols:
        raise ValueError(f"{name}: {len(values)} values for {rows}x{cols}")
    return [values[i * cols:(i + 1) * cols] for i in range(rows)]


def _png_chunks(data: bytes):
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("not a PNG file")
    i = 8
    while i < len(data):
        (n,) = struct.unpack(">I", data[i:i + 4])
        yield data[i + 4:i + 8], data[i + 8:i + 8 + n]
        i += 12 + n


def read_png_rgba(data: bytes) -> tuple[int, int, list[list[tuple[int, int, int, int]]]]:
    """Decode an 8-bit, non-interlaced grey, RGB or RGBA PNG to rows of RGBA tuples."""
    width = height = None
    channels = None
    idat = b""
    for kind, body in _png_chunks(data):
        if kind == b"IHDR":
            width, height, depth, ctype, _c, _f, interlace = struct.unpack(">IIBBBBB", body)
            if depth != 8 or interlace != 0 or ctype not in (0, 2, 4, 6):
                raise ValueError(f"unsupported PNG: depth {depth}, colour type {ctype}, interlace {interlace}")
            channels = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
        elif kind == b"IDAT":
            idat += body
    raw = zlib.decompress(idat)
    stride = width * channels
    rows, prev = [], bytearray(stride)
    pos = 0
    for _ in range(height):
        ftype, line = raw[pos], bytearray(raw[pos + 1: pos + 1 + stride])
        pos += 1 + stride
        for x in range(stride):
            a = line[x - channels] if x >= channels else 0
            b = prev[x]
            c = prev[x - channels] if x >= channels else 0
            if ftype == 1:
                line[x] = (line[x] + a) & 0xFF
            elif ftype == 2:
                line[x] = (line[x] + b) & 0xFF
            elif ftype == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 0xFF
            elif ftype == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 0xFF
            elif ftype != 0:
                raise ValueError(f"PNG filter {ftype}")
        prev = line
        px = []
        for x in range(width):
            s = line[x * channels:(x + 1) * channels]
            if channels == 1:
                px.append((s[0], s[0], s[0], 255))
            elif channels == 2:
                px.append((s[0], s[0], s[0], s[1]))
            elif channels == 3:
                px.append((s[0], s[1], s[2], 255))
            else:
                px.append((s[0], s[1], s[2], s[3]))
        rows.append(px)
    return width, height, rows


def bgra_to_png(raw: bytes, width: int, height: int) -> bytes:
    """CARLA's BGRA image bytes to an RGB PNG (filter 0)."""
    if len(raw) != width * height * 4:
        raise ValueError(f"{len(raw)} bytes for {width}x{height} BGRA")
    lines = bytearray()
    for y in range(height):
        row = raw[y * width * 4:(y + 1) * width * 4]
        rgb = bytearray(width * 3)
        rgb[0::3], rgb[1::3], rgb[2::3] = row[2::4], row[1::4], row[0::4]
        lines += b"\x00" + rgb

    def chunk(kind: bytes, body: bytes) -> bytes:
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(lines), 6)) + chunk(b"IEND", b""))


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ------------------------------------------------------------------ upstream's scripts


# The script's file is run unchanged, from its pinned blob, under two shims of its environment, each recorded:
# - GUI: it ends by opening a window (calc_front_camera_homography.py:235-239); on a host without a display the
#   four GUI calls are stubbed;
# - corner shape: it indexes cornerSubPix's result as (N, 2) points (:93-99: center = corners[4], then
#   int(center[0])), but OpenCV's Python binding returns (N, 1, 2) (OpenCV 4.11 here), so at the pin the script
#   stops with "only length-1 arrays can be converted" at :99. The shim returns the same values as (N, 2).
RUNNER_SHIMS = [
    "cv2.namedWindow, cv2.imshow, cv2.destroyAllWindows: no-ops; cv2.waitKey: returns -1",
    "cv2.cornerSubPix: the same corners, reshaped from (N, 1, 2) to (N, 2)",
]
RUNNER = (
    "import sys, runpy, cv2\n"
    "for name in ('namedWindow', 'imshow', 'destroyAllWindows'):\n"
    "    setattr(cv2, name, lambda *a, **k: None)\n"
    "cv2.waitKey = lambda *a, **k: -1\n"
    "_corner_sub_pix = cv2.cornerSubPix\n"
    "cv2.cornerSubPix = lambda *a, **k: _corner_sub_pix(*a, **k).reshape(-1, 2)\n"
    "script = sys.argv[1]\n"
    "sys.argv = sys.argv[1:]\n"
    "runpy.run_path(script, run_name='__main__')\n"
)

POINT_LINE = re.compile(r"^(Top-Left|Top-Right|Bottom-Left|Bottom-Right): Image \(u,v\) = \(([-\d.]+), ([-\d.]+)\)",
                        re.M)


def upstream_blob(clone: Path, path: str, pin: str = VP_PIN) -> bytes:
    return subprocess.run(["git", "-C", str(clone), "show", f"{pin}:{path}"], check=True,
                          capture_output=True).stdout


def opencv_version(python: str) -> str | None:
    done = subprocess.run([python, "-c", "import cv2, numpy; print(cv2.__version__, numpy.__version__)"],
                          capture_output=True, text=True)
    return done.stdout.strip() or None


def run_upstream_calc(python: str, script: Path, image: Path, out_yaml: Path, args_xy: dict, cwd: Path) -> dict:
    cmd = [python, "-c", RUNNER, str(script), "--img", str(image), "--out", str(out_yaml)]
    for key in ("tl", "tr", "bl", "br"):
        x, y = args_xy[key]
        cmd += [f"--{key}", repr(float(x)), repr(float(y))]
    done = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    points = {m.group(1): [float(m.group(2)), float(m.group(3))] for m in POINT_LINE.finditer(done.stdout)}
    return {"command": cmd[:2] + ["<runner>"] + cmd[3:], "returncode": done.returncode, "stdout": done.stdout,
            "stderr": done.stderr[-4000:], "imagePoints": points}


def run_upstream_c(python: str, script: Path, h_yaml: Path, work: Path, out_yaml: Path) -> dict:
    """find_homography_C_matrix.py reads '../config/H.yaml' from its working directory (its line 50)."""
    (work / "config").mkdir(parents=True, exist_ok=True)
    (work / "scripts").mkdir(parents=True, exist_ok=True)
    (work / "config" / "H.yaml").write_bytes(h_yaml.read_bytes())
    done = subprocess.run([python, str(script), "--output", str(out_yaml)], cwd=work / "scripts",
                          capture_output=True, text=True)
    return {"returncode": done.returncode, "stdout": done.stdout, "stderr": done.stderr[-4000:]}


def make_h(capture_path: Path, vp_clone: Path, python: str, out_dir: Path) -> dict:
    capture_path, vp_clone, out_dir = capture_path.resolve(), vp_clone.resolve(), out_dir.resolve()
    capture = json.loads(capture_path.read_text())
    frame = capture_path.parent / capture["frame"]["path"]
    out_dir.mkdir(parents=True, exist_ok=True)
    up = out_dir / "upstream"
    up.mkdir(exist_ok=True)
    blobs = {}
    for path in (UPSTREAM_CALC, UPSTREAM_C):
        data = upstream_blob(vp_clone, path)
        (up / Path(path).name).write_bytes(data)
        blobs[path] = {"sha256": sha256(data), "pin": VP_PIN}
    h_yaml = out_dir / "H.yaml"
    calc = run_upstream_calc(python, up / Path(UPSTREAM_CALC).name, frame, h_yaml, capture["upstreamArgs"], out_dir)
    record = {"recordVersion": 1, "kind": "camera-calibration-file", "decision": "the owner's decision 6 of "
              "2026-11-18: an H.yaml for the CARLA camera computed with upstream's script, hashed and named in "
              "every verdict", "capture": {"path": str(capture_path), "sha256": sha256(capture_path.read_bytes())},
              "frame": {"path": str(frame), "sha256": sha256(frame.read_bytes())}, "upstreamScripts": blobs,
              "upstreamRun": {k: calc[k] for k in ("command", "returncode", "imagePoints", "stdout", "stderr")},
              "runnerShims": RUNNER_SHIMS, "opencvVersion": opencv_version(python)}
    if calc["returncode"] != 0 or not h_yaml.is_file():
        record["result"] = "upstream's script found no homography; no file written"
        (out_dir / "camera_calibration_record.json").write_text(json.dumps(record, indent=1))
        return record
    h_up = read_opencv_yaml(h_yaml.read_text(), "H")
    camera = camera_in_ground_frame(capture)
    plane_z = float(capture.get("boardLiftM", 0.0))
    h_set = image_to_ground(camera, plane_z)
    c_yaml = out_dir / "homography_C_matrix.yaml"
    crun = run_upstream_c(python, up / Path(UPSTREAM_C).name, h_yaml, out_dir / "c_work", c_yaml)
    record.update({
        "cameraInGroundFrame": camera, "boardPlaneZM": plane_z,
        "predictedPixels": predicted_pixels(camera, {k: tuple(v) for k, v in capture["upstreamArgs"].items()},
                                            plane_z),
        "H_upstream": h_up, "H_settings": h_set, "crossCheck": cross_check(h_up, h_set),
        "files": {"H.yaml": {"path": str(h_yaml), "sha256": sha256(h_yaml.read_bytes())}},
        "cMatrixRun": crun,
    })
    if crun["returncode"] == 0 and c_yaml.is_file():
        record["files"]["homography_C_matrix.yaml"] = {"path": str(c_yaml), "sha256": sha256(c_yaml.read_bytes())}
    record["result"] = "written"
    (out_dir / "camera_calibration_record.json").write_text(json.dumps(record, indent=1))
    return record


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Camera calibration file of the CARLA front camera")
    sub = p.add_subparsers(dest="command", required=True)
    mk = sub.add_parser("make-h", help="run upstream's scripts on a camera-capture record")
    mk.add_argument("--capture", required=True, type=Path, help="simulator/camera_capture.json")
    mk.add_argument("--vp-clone", required=True, type=Path, help="a VisionPilot clone holding the pin")
    mk.add_argument("--python", default=sys.executable, help="a Python with OpenCV and numpy")
    mk.add_argument("--out-dir", required=True, type=Path)
    pr = sub.add_parser("predict", help="pixel positions of the board centers from the camera settings")
    pr.add_argument("--front-bumper-x", type=float, required=True, help="the hero's bumper x in its frame, m")
    pr.add_argument("--near-m", type=float, default=DEFAULT_NEAR_M)
    pr.add_argument("--far-m", type=float, default=DEFAULT_FAR_M)
    pr.add_argument("--half-spacing-m", type=float, default=DEFAULT_HALF_SPACING_M)
    a = p.parse_args(argv)
    if a.command == "make-h":
        record = make_h(a.capture, a.vp_clone, a.python, a.out_dir)
        print(json.dumps({k: record.get(k) for k in ("result", "files")}, indent=1))
        return 0 if record.get("result") == "written" else 1
    from da_world_side import FRONT_CAMERA  # noqa: WPS433
    camera = {"width": FRONT_CAMERA["image_size_x"], "height": FRONT_CAMERA["image_size_y"],
              "fov": FRONT_CAMERA["fov"], "x": FRONT_CAMERA["x"] - a.front_bumper_x, "y": FRONT_CAMERA["y"],
              "z": FRONT_CAMERA["z"], "pitch": FRONT_CAMERA["pitch"], "yaw": FRONT_CAMERA["yaw"],
              "roll": FRONT_CAMERA["roll"]}
    print(json.dumps(predicted_pixels(camera, board_layout(a.near_m, a.far_m, a.half_spacing_m)), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
