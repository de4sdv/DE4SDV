"""The camera calibration file: the homography from the camera's settings, checked against values derived here
by hand and by an independent projection; the 4-point solve, the file formats, the capture on the fake CARLA,
and (where a Python with OpenCV and the VisionPilot clone are present) upstream's script on a synthetic frame."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
import zlib
import struct
from pathlib import Path

import pytest

import camera_calibration as cc
from conftest import run_main

HERE = Path(__file__).resolve().parent
VP_CLONE = Path(os.environ.get("VISIONPILOT_CLONE", Path.home() / "de4sdv-upstream" / "vision_pilot"))
CV_PYTHON = os.environ.get("DE4SDV_CV_PYTHON", "/usr/bin/python3")
RIG = {"width": 1920, "height": 1280, "fov": 50.0, "x": 1.544 - 2.45, "y": 0.0243, "z": 2.116,
       "pitch": -0.11, "yaw": -0.23, "roll": -0.10}


def test_level_camera_matches_the_closed_form():
    # A level camera at height h, x0 behind the origin: a ground point (X, Y) is seen at
    # u = cx - f Y / (X - x0), v = cy + f h / (X - x0), with cx = W/2 - 0.5 and cy = H/2 - 0.5.
    cam = {"width": 1920, "height": 1280, "fov": 50.0, "x": -1.0, "y": 0.0, "z": 2.0,
           "pitch": 0.0, "yaw": 0.0, "roll": 0.0}
    f = 1920 / (2 * math.tan(math.radians(25.0)))
    h = cc.image_to_ground(cam)
    for X, Y in ((5.0, 0.0), (10.0, 1.5), (40.0, -2.0)):
        d = X + 1.0
        u, v = 959.5 - f * Y / d, 639.5 + f * 2.0 / d
        gx, gy = cc.apply_h(h, u, v)
        assert gx == pytest.approx(X, abs=1e-9) and gy == pytest.approx(Y, abs=1e-9)


def _project_by_vectors(cam, X, Y, z=0.0):
    """Independent projection: CARLA's forward/right/up vectors, dot products, no matrices."""
    p, yw, r = (math.radians(cam[k]) for k in ("pitch", "yaw", "roll"))
    fwd = (math.cos(p) * math.cos(yw), math.cos(p) * math.sin(yw), math.sin(p))
    right = (math.cos(yw) * math.sin(p) * math.sin(r) - math.sin(yw) * math.cos(r),
             math.sin(yw) * math.sin(p) * math.sin(r) + math.cos(yw) * math.cos(r), -math.cos(p) * math.sin(r))
    up = (-math.cos(yw) * math.sin(p) * math.cos(r) - math.sin(yw) * math.sin(r),
          -math.sin(yw) * math.sin(p) * math.cos(r) + math.cos(yw) * math.sin(r), math.cos(p) * math.cos(r))
    d = (X - cam["x"], -Y - cam["y"], z - cam["z"])
    dot = lambda a, b: sum(i * j for i, j in zip(a, b))  # noqa: E731
    f = cam["width"] / (2 * math.tan(math.radians(cam["fov"]) / 2))
    return (cam["width"] / 2 - 0.5 + f * dot(d, right) / dot(d, fwd),
            cam["height"] / 2 - 0.5 - f * dot(d, up) / dot(d, fwd))


@pytest.mark.parametrize("pose", [RIG, {**RIG, "pitch": -4.0, "yaw": 1.5, "roll": 2.0, "z": 1.4}])
def test_settings_homography_agrees_with_an_independent_projection(pose):
    h_inv = cc.ground_to_image(pose)
    for X, Y in ((8.0, 1.6), (13.0, -1.6), (30.0, 0.0), (80.0, 3.0)):
        assert cc.apply_h(h_inv, X, Y) == pytest.approx(_project_by_vectors(pose, X, Y), abs=1e-7)


def test_board_layout_is_upstreams_top_far_left_positive():
    lay = cc.board_layout(8.0, 13.0, 1.6)
    assert lay == {"tl": (13.0, 1.6), "tr": (13.0, -1.6), "bl": (8.0, 1.6), "br": (8.0, -1.6)}
    px = cc.predicted_pixels(RIG, lay)
    assert px["tl"][0] < px["tr"][0] and px["bl"][0] < px["br"][0]        # left is left in the image
    assert px["tl"][1] < px["bl"][1]                                       # far is higher in the image
    for u, v in px.values():                                               # the default layout is in view
        assert 0 < u < 1920 and 0 < v < 1280


def test_dlt_recovers_a_known_homography_exactly():
    h_true = cc.image_to_ground(RIG)
    img = [(700.0, 950.0), (1200.0, 950.0), (600.0, 1120.0), (1330.0, 1125.0)]
    world = [cc.apply_h(h_true, u, v) for u, v in img]
    h = cc.dlt(img, world)
    for row, row_true in zip(h, h_true):
        assert row == pytest.approx(row_true, rel=1e-7, abs=1e-12)


def test_cross_check_is_zero_for_the_same_file_and_finds_a_long_one():
    h = cc.image_to_ground(RIG)
    assert cc.cross_check(h, h)["maxRelErrXInRange"] == pytest.approx(0.0, abs=1e-9)
    longer = [[1.11 * v for v in h[0]], [1.11 * v for v in h[1]], list(h[2])]    # distances 11 % long
    res = cc.cross_check(longer, h)
    assert res["maxRelErrXInRange"] == pytest.approx(0.11, abs=1e-6)
    assert res["agreeWithinProposal"] is False


def test_opencv_yaml_round_trip_and_upstreams_layout():
    h = cc.image_to_ground(RIG)
    text = cc.write_opencv_yaml(h)
    assert text.startswith("%YAML:1.0\n---\nH: !!opencv-matrix\n")
    back = cc.read_opencv_yaml(text)
    for row, row_h in zip(back, h):
        assert row == pytest.approx(row_h, rel=1e-14)
    # the shape of upstream's own file (VisionPilot/config/H.yaml at the pin): data over several lines
    sample = ("%YAML:1.0\n---\n# comment\nH: !!opencv-matrix\n  rows: 3\n  cols: 3\n  dt: d\n"
              "  data: [ 1.0e-04, -2.0e-03, -6.0e+00,\n          3.0e-03,  6.0e-05, -3.0e+00,\n"
              "          1.0e-05, -1.0e-03,  1.0e+00 ]\n")
    assert cc.read_opencv_yaml(sample)[2] == [1.0e-05, -1.0e-03, 1.0]


def _png(width, height, rows, ctype=6, filt=0):
    ch = {0: 1, 2: 3, 6: 4}[ctype]
    raw = b"".join(bytes([filt]) + bytes(v for px in row for v in px[:ch]) for row in rows)
    def chunk(k, b):
        return struct.pack(">I", len(b)) + k + b + struct.pack(">I", zlib.crc32(k + b) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, ctype, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))


def test_png_decoder_on_a_built_image_and_the_bgra_writer():
    rows = [[(x * 10, y * 20, 7, 255) for x in range(5)] for y in range(3)]
    w, h, px = cc.read_png_rgba(_png(5, 3, rows))
    assert (w, h) == (5, 3) and px == rows
    bgra = bytes(v for row in rows for (r, g, b, a) in row for v in (b, g, r, a))
    w, h, px = cc.read_png_rgba(cc.bgra_to_png(bgra, 5, 3))
    assert px == rows


@pytest.mark.skipif(not (VP_CLONE / ".git").exists(), reason="no VisionPilot clone")
def test_upstream_checkerboard_decodes_to_a_four_by_four_pattern():
    data = cc.upstream_blob(VP_CLONE, cc.UPSTREAM_BOARD)
    w, h, px = cc.read_png_rgba(data)
    assert (w, h) == (600, 600)
    cells = [[px[75 + 150 * j][75 + 150 * i][0] for i in range(4)] for j in range(4)]
    for j in range(4):
        for i in range(4):
            assert cells[j][i] in (0, 255)
            if i < 3:
                assert cells[j][i] != cells[j][i + 1]
            if j < 3:
                assert cells[j][i] != cells[j + 1][i]


def test_camera_capture_on_the_fake_lays_four_textured_boards(tmp_path, server, factory, clock):
    board = tmp_path / "board.png"
    board.write_bytes(_png(8, 8, [[(0, 0, 0, 255) if (x // 2 + y // 2) % 2 else (255, 255, 255, 255)
                                   for x in range(8)] for y in range(8)]))
    rc, _ = run_main(["camera-capture", "--run-dir", str(tmp_path / "c"), "--checkerboard", str(board)],
                     factory, clock)
    assert rc == 0
    cap = json.loads((tmp_path / "c" / "simulator" / "camera_capture.json").read_text())
    assert [b["label"] for b in cap["boards"]] == ["tl", "tr", "bl", "br"]
    hero_x = cap["heroWorld"]["x"]
    bumper = cap["frontBumperXM"]
    for b in cap["boards"]:
        X, Y = b["upstreamXY"]
        # the fake's road runs along +x with CARLA's y to the right: world = hero + (bumper + X, -Y)
        assert b["world"]["x"] == pytest.approx(hero_x + bumper + X, abs=1e-9)
        assert b["world"]["y"] == pytest.approx(cap["heroWorld"]["y"] - Y, abs=1e-9)
        assert b["world"]["z"] == pytest.approx(cap["groundZ"] + cap["boardLiftM"])
    assert cap["upstreamArgs"] == {"tl": [13.0, 1.6], "tr": [13.0, -1.6], "bl": [8.0, 1.6], "br": [8.0, -1.6]}
    assert cap["meshPath"] == "/Engine/BasicShapes/Plane.Plane" and cap["boardScale"] == 2.5
    frame = tmp_path / "c" / "simulator" / cap["frame"]["path"]
    w, h, _px = cc.read_png_rgba(frame.read_bytes())
    assert (w, h) == (1920, 1280)
    assert cap["checkerboard"]["sha256"] == cc.sha256(board.read_bytes())
    # every board got the texture, flipped vertically as PythonAPI/util/apply_texture.py does
    states = [s for s in server.log if s[0] == "spawn" and s[2] == "static.prop.mesh"]
    assert len(states) == 4
    assert not server.actors


def _cv_python_ok() -> bool:
    if not shutil.which(CV_PYTHON) and not Path(CV_PYTHON).exists():
        return False
    done = subprocess.run([CV_PYTHON, "-c", "import cv2, numpy"], capture_output=True)
    return done.returncode == 0


@pytest.mark.skipif(not ((VP_CLONE / ".git").exists() and _cv_python_ok()),
                    reason="needs the VisionPilot clone and a Python with OpenCV")
def test_upstream_script_on_a_synthetic_frame_agrees_with_the_settings(tmp_path):
    board = tmp_path / "board.png"
    board.write_bytes(cc.upstream_blob(VP_CLONE, cc.UPSTREAM_BOARD))
    layout = cc.board_layout(cc.DEFAULT_NEAR_M, cc.DEFAULT_FAR_M, cc.DEFAULT_HALF_SPACING_M)
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"camera": RIG, "boards": [list(v) for v in layout.values()],
                                "board_m": cc.DEFAULT_BOARD_SCALE, "plane_z": 0.0}))
    subprocess.run([CV_PYTHON, str(HERE / "synthetic_render.py"), str(spec), str(board), str(tmp_path / "f.png")],
                   check=True)
    capture = {"frontCamera": {"image_size_x": "1920", "image_size_y": "1280", "fov": "50.0",
                               "pose": {"x": 1.544, "y": 0.0243, "z": 2.116, "roll": -0.10, "pitch": -0.11,
                                        "yaw": -0.23}},
               "frontBumperXM": 2.45, "groundZ": 0.0, "heroZ": 0.0, "boardLiftM": 0.0,
               "heroWorld": {"x": 0.0, "y": 0.0, "z": 0.0, "pitch": 0.0, "yaw": 0.0, "roll": 0.0},
               "cameraWorld": {"x": 1.544, "y": 0.0243, "z": 2.116, "pitch": -0.11, "yaw": -0.23, "roll": -0.10},
               "frame": {"path": "f.png"}, "upstreamArgs": {k: list(v) for k, v in layout.items()}}
    (tmp_path / "capture.json").write_text(json.dumps(capture))
    rec = cc.make_h(tmp_path / "capture.json", VP_CLONE, CV_PYTHON, tmp_path / "out")
    assert rec["result"] == "written", rec["upstreamRun"]["stderr"]
    names = {"tl": "Top-Left", "tr": "Top-Right", "bl": "Bottom-Left", "br": "Bottom-Right"}
    for key, (u, v) in rec["predictedPixels"].items():
        got = rec["upstreamRun"]["imagePoints"][names[key]]
        assert abs(got[0] - u) < 0.5 and abs(got[1] - v) < 0.5
    assert rec["crossCheck"]["maxRelErrXInRange"] < 0.005
    assert rec["crossCheck"]["agreeWithinProposal"] is True
    for name in ("H.yaml", "homography_C_matrix.yaml"):
        entry = rec["files"][name]
        assert entry["sha256"] == cc.sha256(Path(entry["path"]).read_bytes())
    assert rec["upstreamScripts"][cc.UPSTREAM_CALC]["pin"] == cc.VP_PIN
    assert rec["runnerShims"] == cc.RUNNER_SHIMS
