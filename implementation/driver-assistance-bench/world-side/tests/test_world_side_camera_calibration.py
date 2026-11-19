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


# ------------------------------------------------------------------ the capture's pre-check (R1 of the closure
# check of 7befc3c1: the real Town06_Opt frame's boards came out washed out, and make-h found 0 checkerboards)

DATA = HERE / "data"


def _bgra_from_grey_png(path: Path, factor: int) -> tuple[int, int, bytes]:
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


def test_r1_the_precheck_fails_the_real_washed_out_town06_frame_with_a_named_reason():
    # the real frame of the world-maps rehearsal (sha256 30bbf9de..., camera-capture of 0a1d83c3 on the G4), stored
    # as a 4x downscaled grey PNG (74 KB), and its camera_capture.json
    cap = json.loads((DATA / "town06_washed_out_capture.json").read_text())
    assert cap["frame"]["sha256"].startswith("30bbf9de")
    cap["boardSizeM"] = cap["boardScale"] * cc.DEFAULT_MESH_SIZE_M
    w, h, raw = _bgra_from_grey_png(DATA / "town06_washed_out_frame_x4.png", 4)
    assert (w, h) == (1920, 1280)
    rec = cc.precheck(cap, raw, w, h, use_opencv=False)
    assert rec["passed"] is False, rec
    for label in ("tl", "tr", "bl", "br"):
        st = rec["boards"][label]
        # the closure check measured p5-p95 about 130-159 on the boards: never a black and white checker
        assert 120 <= st["p5"] <= st["p95"] <= 165 and st["spread"] < cc.PRECHECK_MIN_SPREAD, (label, st)
        assert f"board {label} washed out" in rec["reason"]


def _checker_frame(cap: dict, w: int, h: int, black: int, white: int) -> bytes:
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


def _rig_capture() -> dict:
    layout = cc.board_layout(cc.DEFAULT_NEAR_M, cc.DEFAULT_FAR_M, cc.DEFAULT_HALF_SPACING_M)
    return {"frontCamera": {"image_size_x": "1920", "image_size_y": "1280", "fov": "50.0",
                            "pose": {"x": 1.544, "y": 0.0243, "z": 2.116, "roll": -0.10, "pitch": -0.11,
                                     "yaw": -0.23}},
            "frontBumperXM": 2.45, "groundZ": 0.0, "heroZ": 0.0, "boardLiftM": 0.0,
            "heroWorld": {"x": 0.0, "y": 0.0, "z": 0.0, "pitch": 0.0, "yaw": 0.0, "roll": 0.0},
            "cameraWorld": {"x": 1.544, "y": 0.0243, "z": 2.116, "pitch": -0.11, "yaw": -0.23, "roll": -0.10},
            "boardSizeM": cc.DEFAULT_BOARD_SCALE, "upstreamArgs": {k: list(v) for k, v in layout.items()}}


def test_r1_the_precheck_passes_full_contrast_boards_and_fails_the_same_boards_washed_out():
    cap = _rig_capture()
    good = cc.precheck(cap, _checker_frame(cap, 1920, 1280, 20, 235), 1920, 1280, use_opencv=False)
    assert good["passed"] is True and good["reason"] == "every board at full contrast", good
    assert all(b["spread"] >= 200 for b in good["boards"].values()), good["boards"]
    # the real frame's levels: 135 and 151
    bad = cc.precheck(cap, _checker_frame(cap, 1920, 1280, 135, 151), 1920, 1280, use_opencv=False)
    assert bad["passed"] is False and bad["reason"].count("washed out") == 4, bad["reason"]
    # one board alone washed out is enough to fail, and is named
    raw = bytearray(_checker_frame(cap, 1920, 1280, 20, 235))
    u0, v0, u1, v1 = good["boards"]["tr"]["box"]
    for v in range(v0, v1 + 1):
        raw[4 * (v * 1920 + u0):4 * (v * 1920 + u1 + 1)] = bytes([140, 140, 140, 255]) * (u1 - u0 + 1)
    one = cc.precheck(cap, bytes(raw), 1920, 1280, use_opencv=False)
    assert one["passed"] is False and one["reason"].startswith("board tr washed out"), one["reason"]


def test_r1_camera_capture_fails_at_capture_time_when_the_texture_does_not_take(tmp_path, server, factory, clock,
                                                                              monkeypatch):
    # the real server's answer to the engine plane: the texture parameter does not take, the board renders grey
    monkeypatch.setenv("FAKE_TEXTURE_TAKES", "NoSuchParameter")
    board = tmp_path / "board.png"
    board.write_bytes(_png(8, 8, [[(0, 0, 0, 255) if (x // 2 + y // 2) % 2 else (255, 255, 255, 255)
                                   for x in range(8)] for y in range(8)]))
    rc, _ = run_main(["camera-capture", "--run-dir", str(tmp_path / "c"), "--checkerboard", str(board)],
                     factory, clock)
    assert rc == 2
    cap = json.loads((tmp_path / "c" / "simulator" / "camera_capture.json").read_text())
    assert cap["precheck"]["passed"] is False and "washed out" in cap["precheck"]["reason"], cap["precheck"]
    assert (tmp_path / "c" / "simulator" / "calibration_frame.png").is_file()   # kept for the diagnosis
    side = (tmp_path / "c" / "simulator" / "worldSide.jsonl").read_text()
    assert '"pre-check failed"' in side, side[-2000:]


def test_r1_camera_capture_sets_its_weather_and_records_weather_parameters_and_precheck(tmp_path, server, factory,
                                                                                       clock):
    board = tmp_path / "board.png"
    board.write_bytes(_png(8, 8, [[(0, 0, 0, 255) if (x // 2 + y // 2) % 2 else (255, 255, 255, 255)
                                   for x in range(8)] for y in range(8)]))
    rc, _ = run_main(["camera-capture", "--run-dir", str(tmp_path / "c"), "--checkerboard", str(board),
                      "--texture-params", "Diffuse,Emissive"], factory, clock)
    assert rc == 0
    cap = json.loads((tmp_path / "c" / "simulator" / "camera_capture.json").read_text())
    assert ("weather", "ClearNoon") in server.log and cap["weather"] == "ClearNoon"
    assert cap["textureParams"] == ["Diffuse", "Emissive"] and cap["boardSizeM"] == 2.5
    assert cap["precheck"]["passed"] is True, cap["precheck"]
    rc, out = run_main(["camera-capture", "--run-dir", str(tmp_path / "d"), "--checkerboard", str(board),
                        "--texture-params", "NoSuch"], factory, clock)
    assert rc == 2


@pytest.mark.skipif(not _cv_python_ok(), reason="needs a Python with OpenCV")
def test_r1_upstreams_loop_in_the_precheck_finds_no_board_on_the_real_frame_and_four_on_a_good_one(tmp_path):
    # opencv_boards() is upstream's own detection loop; run under a Python with OpenCV, as the session's make-h
    code = (
        "import json, sys; sys.path[:0] = [sys.argv[1], sys.argv[2]]\n"
        "import camera_calibration as cc, test_world_side_camera_calibration as t\n"
        "w, h, raw = t._bgra_from_grey_png(t.DATA / 'town06_washed_out_frame_x4.png', 4)\n"
        "cap = t._rig_capture()\n"
        "print(json.dumps([cc.opencv_boards(raw, w, h)['found'],"
        " cc.opencv_boards(t._checker_frame(cap, 1920, 1280, 20, 235), 1920, 1280)['found']]))\n")
    done = subprocess.run([CV_PYTHON, "-c", code, str(HERE.parent), str(HERE)], capture_output=True, text=True,
                          env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})
    assert done.returncode == 0, done.stderr[-2000:]
    assert json.loads(done.stdout.strip().splitlines()[-1]) == [0, 4]


# ------------------------------------------------------------------ the settings source (p10-2, the lead's decision of
# 2026-11-19): CARLA 1.0's apply_texture never reaches the engine plane's material (CarlaGameModeBase.cpp:505-548 at
# 14ac3b1a50), so p10-2's H.yaml comes from the simulated camera's settings and pose, not from a board frame

def _g4_capture() -> dict:
    # camera_capture.json of this lane's G4 rehearsal (Town06_Opt, CARLA 1.0-14ac3b1a5): the bench camera's real pose
    cap = json.loads((DATA / "town06_g4_capture.json").read_text())
    assert cap["frame"]["sha256"].startswith("b1f3ea3e") and cap["map"] == "Carla/Maps/Town06_Opt"
    return cap


def _settings_h(tmp_path: Path) -> tuple[dict, list]:
    cap = _g4_capture()
    (tmp_path / "cap").mkdir()
    (tmp_path / "cap" / "camera_capture.json").write_text(json.dumps(cap))
    (tmp_path / "cap" / "calibration_frame.png").write_bytes(cc.bgra_to_png(bytes([90, 90, 90, 255]) * 16, 4, 4))
    rec = cc.make_h(tmp_path / "cap" / "camera_capture.json", VP_CLONE, CV_PYTHON, tmp_path / "set", source="settings")
    return rec, cc.read_opencv_yaml((tmp_path / "set" / "H.yaml").read_text(), "H")


@pytest.mark.skipif(not ((VP_CLONE / ".git").exists() and _cv_python_ok()),
                    reason="needs the VisionPilot clone and a Python with OpenCV")
def test_gate_settings_h_yaml_agrees_with_upstreams_procedure_on_full_contrast_boards_at_the_g4_pose(tmp_path):
    # The gate of the settings source: upstream's own procedure (calc_front_camera_homography.py, unchanged, through
    # make-h's two shims) on four perfectly rendered boards at the bench camera's real G4 pose (1920x1280, FOV 50) must
    # agree with the H.yaml that make-h --source settings writes, within the bench's AGREE_TOLERANCE (2 %, 10-60 m).
    # The boards lie on the road (lift 0), the plane the settings' H describes; the render casts rays through
    # CARLA's camera vectors, independently of the matrix homography (tests/synthetic_render.py)
    rec_set, h_file = _settings_h(tmp_path)
    cap = _g4_capture()
    cap["boardLiftM"] = 0.0
    cap["frame"] = {"path": "board_frame.png"}
    board = tmp_path / "board.png"
    board.write_bytes(cc.upstream_blob(VP_CLONE, cc.UPSTREAM_BOARD))
    spec = tmp_path / "spec.json"
    spec.write_text(json.dumps({"camera": cc.camera_in_ground_frame(cap),
                                "boards": [list(v) for v in cap["upstreamArgs"].values()],
                                "board_m": cap["boardSizeM"], "plane_z": 0.0}))
    subprocess.run([CV_PYTHON, str(HERE / "synthetic_render.py"), str(spec), str(board),
                    str(tmp_path / "board_frame.png")], check=True)
    (tmp_path / "board_capture.json").write_text(json.dumps(cap))
    rec_up = cc.make_h(tmp_path / "board_capture.json", VP_CLONE, CV_PYTHON, tmp_path / "up")
    assert rec_up["result"] == "written", rec_up["upstreamRun"]["stderr"]
    assert len(rec_up["upstreamRun"]["imagePoints"]) == 4
    check = cc.cross_check(rec_up["H_upstream"], h_file)
    print("gate: upstream's H against the settings' H.yaml, max |relErrX| 10-60 m:", check["maxRelErrXInRange"])
    assert cc.AGREE_TOLERANCE == 0.02
    assert check["agreeWithinProposal"] is True and check["maxRelErrXInRange"] <= 0.02, check
    # the same convention, not only the same scale: lateral positions agree too (|dY| < 5 cm at 10-60 m)
    for p in check["points"]:
        if 10.0 <= p["X"] <= 60.0:
            assert abs(p["upstreamY"] - p["Y"]) < 0.05, p


@pytest.mark.skipif(not ((VP_CLONE / ".git").exists() and _cv_python_ok()),
                    reason="needs the VisionPilot clone and a Python with OpenCV")
def test_make_h_settings_writes_upstreams_h_yaml_from_the_camera_settings_and_records_why(tmp_path):
    rec, h_file = _settings_h(tmp_path)
    cap = _g4_capture()
    assert rec["result"] == "written"
    assert rec["source"] == "settings"
    assert "CarlaGameModeBase.cpp:505-548" in rec["sourceReason"] and "14ac3b1a50" in rec["sourceReason"]
    assert rec["crossCheck"] == "not run: no board rendered"
    # H.yaml: the settings' homography of the road plane (z = 0 above groundZ) in upstream's FileStorage layout
    text = (tmp_path / "set" / "H.yaml").read_text()
    assert text.startswith("%YAML:1.0\n---\nH: !!opencv-matrix\n")
    want = cc.image_to_ground(cc.camera_in_ground_frame(cap), 0.0)
    assert all(abs(a - b) <= 1e-12 * max(1.0, abs(b)) for ra, rb in zip(h_file, want) for a, b in zip(ra, rb))
    assert rec["H_settings"] == want and rec["planeZM"] == 0.0
    # upstream's calc script never ran; its find_homography_C_matrix.py derived the second file from that H.yaml
    assert "upstreamRun" not in rec and list(rec["upstreamScripts"]) == [cc.UPSTREAM_C]
    assert rec["cMatrixRun"]["returncode"] == 0
    for name in ("H.yaml", "homography_C_matrix.yaml"):
        entry = rec["files"][name]
        assert entry["sha256"] == cc.sha256(Path(entry["path"]).read_bytes())
    # the capture's frame stays evidence, and its pre-check verdict is recorded, not enforced
    assert rec["frame"]["sha256"] == cc.sha256((tmp_path / "cap" / "calibration_frame.png").read_bytes())
    assert rec["capturePrecheck"]["passed"] is False and "washed out" in rec["capturePrecheck"]["reason"]


def test_make_h_takes_its_source_only_from_the_flag(tmp_path):
    # never a silent fallback: the default is upstream's procedure on the frame; an unknown source is refused
    with pytest.raises(SystemExit) as e:
        cc.main(["make-h", "--capture", "x", "--vp-clone", "y", "--out-dir", str(tmp_path), "--source", "guess"])
    assert e.value.code == 2
    seen = {}

    def fake(capture, clone, python, out, source):
        seen["source"] = source
        return {"result": "written", "files": {}}
    orig = cc.make_h
    cc.make_h = fake
    try:
        assert cc.main(["make-h", "--capture", "x", "--vp-clone", "y", "--out-dir", str(tmp_path)]) == 0
        assert seen["source"] == "checkerboard"
        assert cc.main(["make-h", "--capture", "x", "--vp-clone", "y", "--out-dir", str(tmp_path),
                        "--source", "settings"]) == 0
        assert seen["source"] == "settings"
    finally:
        cc.make_h = orig


@pytest.mark.skipif(not ((VP_CLONE / ".git").exists() and _cv_python_ok()),
                    reason="needs the VisionPilot clone and a Python with OpenCV")
def test_make_h_checkerboard_on_a_washed_out_frame_writes_nothing_and_never_falls_back(tmp_path):
    # the real Town06_Opt frame (4x downscaled fixture, scaled back): upstream's script finds no board, so the
    # default source writes no H.yaml; it never falls back to the settings
    cap = json.loads((DATA / "town06_washed_out_capture.json").read_text())
    w, h, raw = _bgra_from_grey_png(DATA / "town06_washed_out_frame_x4.png", 4)
    (tmp_path / "f.png").write_bytes(cc.bgra_to_png(raw, w, h))
    cap["frame"] = {"path": "f.png"}
    (tmp_path / "c.json").write_text(json.dumps(cap))
    rec = cc.make_h(tmp_path / "c.json", VP_CLONE, CV_PYTHON, tmp_path / "out")
    assert rec["source"] == "checkerboard"
    assert rec["result"].startswith("upstream's script found no homography")
    assert not (tmp_path / "out" / "H.yaml").exists() and "H_settings" not in rec


def test_camera_capture_precheck_record_keeps_a_washed_out_frame_without_failing(tmp_path, server, factory, clock,
                                                                                  monkeypatch):
    # with the settings source the capture's frame is evidence only: --precheck record judges and records the frame
    # and ends 0; --precheck on (the default, the checkerboard source) still exits 2 on the same frame
    monkeypatch.setenv("FAKE_TEXTURE_TAKES", "NoSuchParameter")
    board = tmp_path / "board.png"
    board.write_bytes(_png(8, 8, [[(0, 0, 0, 255) if (x // 2 + y // 2) % 2 else (255, 255, 255, 255)
                                   for x in range(8)] for y in range(8)]))
    rc, _ = run_main(["camera-capture", "--run-dir", str(tmp_path / "c"), "--checkerboard", str(board),
                      "--precheck", "record"], factory, clock)
    assert rc == 0
    cap = json.loads((tmp_path / "c" / "simulator" / "camera_capture.json").read_text())
    assert cap["precheck"]["passed"] is False and "washed out" in cap["precheck"]["reason"], cap["precheck"]
    assert cap["precheck"]["enforced"] is False
    assert (tmp_path / "c" / "simulator" / "calibration_frame.png").is_file()
    rc, _ = run_main(["camera-capture", "--run-dir", str(tmp_path / "d"), "--checkerboard", str(board)],
                     factory, clock)
    assert rc == 2
    cap = json.loads((tmp_path / "d" / "simulator" / "camera_capture.json").read_text())
    assert cap["precheck"]["enforced"] is True
