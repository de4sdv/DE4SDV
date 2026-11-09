"""Unit tests of de4sdv_planner's numpy parts (history.py, rig.ref_origin_from_raw, the API with the
stub engine). Run: python3 -m pytest -q agent/python/tests  (numpy only; no torch, no GPU)."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import de4sdv_planner as P  # noqa: E402
from de4sdv_planner import history as H  # noqa: E402
from de4sdv_planner import rig as R  # noqa: E402


def circle_poses(n, v, omega, x0=10.0, y0=-5.0, yaw0=0.3):
    """REF poses of a vehicle at constant speed v (m/s) and yaw rate omega (rad/s), 0.1 s apart."""
    out = []
    for i in range(n):
        t = 0.1 * i
        yaw = yaw0 + omega * t
        if abs(omega) < 1e-12:
            x, y = x0 + v * t * math.cos(yaw0), y0 + v * t * math.sin(yaw0)
        else:
            r = v / omega
            x = x0 + r * (math.sin(yaw) - math.sin(yaw0))
            y = y0 - r * (math.cos(yaw) - math.cos(yaw0))
        T = np.eye(4)
        T[:2, :2] = [[math.cos(yaw), -math.sin(yaw)], [math.sin(yaw), math.cos(yaw)]]
        T[0, 3], T[1, 3] = x, y
        out.append(T)
    return out


def rule(yr, speed):
    return yr / np.maximum(speed, 0.1)


def test_rows_on_a_circle_match_the_kinematics():
    v, omega = 8.0, 0.2
    rows = H.egomotion_rows(circle_poses(66, v, omega), rule)
    assert rows.shape == (64, 4) and rows.dtype == np.float32
    assert np.allclose(rows[:, 0], v, atol=0.02)          # chord speed of a 0.1 s step
    # numpy.gradient's one-sided differences at the window ends leave +-0.002 m/s^2 in the first
    # and last acceleration rows on a constant-speed circle: the CL harness fed exactly this.
    assert np.allclose(rows[1:-1, 1], 0.0, atol=1e-6)
    assert np.all(np.abs(rows[[0, -1], 1]) < 3e-3)
    assert np.allclose(rows[:, 2], omega, atol=1e-6)
    assert np.allclose(rows[:, 3], omega / v, atol=1e-3)


def test_rows_are_frames_k_minus_64_to_k_minus_1():
    # speed ramps: pose i at 0.5 * a * t^2 along x; central differences give v(t_i) = a * t_i exactly
    a = 2.0
    poses = []
    for i in range(66):
        T = np.eye(4)
        T[0, 3] = 0.5 * a * (0.1 * i) ** 2
        poses.append(T)
    rows = H.egomotion_rows(poses, rule)
    t = 0.1 * np.arange(1, 65)                              # pose indices 1 .. 64 of 0 .. 65
    assert np.allclose(rows[:, 0], a * t, atol=1e-5)
    assert rows[-1, 0] == pytest.approx(a * 6.4, abs=1e-4)  # newest row = frame k-1


def test_checkpoint_rows_zero_yaw_rate_and_curvature_only():
    rows = H.egomotion_rows(circle_poses(66, 6.0, -0.15), rule)
    ck = H.checkpoint_rows(rows)
    assert np.array_equal(ck[:, :2], rows[:, :2])
    assert not ck[:, 2:].any()
    assert rows[:, 2:].any()                                # the measured rows keep the yaw rate


def test_camera_history_frames_and_pose_window():
    assert H.camera_history_frames(1000) == [965, 970, 975, 980, 985, 990, 995]
    ring = H.PoseRing()
    for k in range(935, 1000):
        ring.add(k, np.eye(4))
    assert not ring.complete(1000)
    ring.add(1000, np.eye(4))
    assert ring.complete(1000) and len(ring.window(1000)) == 66
    assert min(ring.pose) >= 1000 - 80


def test_ref_origin_from_raw_matches_the_vehicle_version():
    M = np.eye(4)
    M[:3, 3] = [100.0, 50.0, 0.5]
    wheels_cm = [[(100 + 1.4) * 100, (50 - 0.8) * 100, 85.0], [(100 + 1.4) * 100, (50 + 0.8) * 100, 85.0],
                 [(100 - 1.45) * 100, (50 - 0.8) * 100, 85.0], [(100 - 1.45) * 100, (50 + 0.8) * 100, 85.0]]
    origin, info = R.ref_origin_from_raw(M, [100.0, 50.0, 0.5], wheels_cm, [35.0, 35.0, 35.0, 35.0])
    assert info["wheel_position_unit"] == "cm"
    assert np.allclose(origin, [-1.45, 0.0, 0.85 - 0.5 - 0.35], atol=1e-9)


def stub_config(tmp_path, pin=None):
    ck = tmp_path / "ckpt.bin"
    ck.write_bytes(b"stand-in checkpoint")
    return {"engine": "stub", "checkpoint_path": str(ck),
            "checkpoint_sha256": P.sha256_file(str(ck)) if pin is None else pin}


def test_identity_refusal_no_pin_and_mismatch(tmp_path):
    out = json.loads(P.setup(json.dumps(stub_config(tmp_path, pin=""))))
    assert out["identity"]["refused"] and out["identity"]["reason"] == "no_pin"
    out = json.loads(P.setup(json.dumps(stub_config(tmp_path, pin="0" * 64))))
    assert out["identity"]["refused"] and out["identity"]["reason"] == "mismatch"
    assert out["identity"]["expectedSha256"] == "0" * 64 and len(out["identity"]["actualSha256"]) == 64


def test_stub_api_primes_then_plans(tmp_path):
    out = json.loads(P.setup(json.dumps(stub_config(tmp_path))))
    assert not out["identity"]["refused"]
    M0 = np.eye(4)
    rig = {"vehicle": {"world_matrix": M0.reshape(-1).tolist(), "location": [0.0, 0.0, 0.0],
                       "wheel_positions": [[1.4, -0.8, 0.35], [1.4, 0.8, 0.35], [-1.45, -0.8, 0.35], [-1.45, 0.8, 0.35]],
                       "wheel_radii": [0.35] * 4}, "cameras": []}
    json.loads(P.set_rig(json.dumps(rig)))
    img = memoryview(bytes(4 * 4 * 4))
    primed_at = None
    for i, k in enumerate(range(2000, 2080)):
        M = np.eye(4)
        M[0, 3] = 5.0 * 0.1 * i                              # 5 m/s along x
        primed, measured, ck, rec = P.condition(k, [img] * 6, [(4, 4)] * 6, M.tobytes(), None, None)
        if primed and primed_at is None:
            primed_at = k
        r = P.infer(k)
        assert (r is not None) == (len(measured) > 0)
    assert primed_at == 2000 + 65                            # 66 poses; camera history needs k-35 (earlier)
    samples, v0, rec = P.infer(2079)
    s = np.frombuffer(samples, dtype=np.float32).reshape(64, 5)
    assert v0 == pytest.approx(5.0, abs=1e-4) and s[0, 2] == pytest.approx(0.5, abs=1e-4)
    ckr = np.frombuffer(ck, dtype=np.float32).reshape(64, 4)
    assert not ckr[:, 2:].any()


def test_bind_thread_runs_on_the_calling_thread(tmp_path):
    """setup() runs before FEO starts (main thread); bind_thread() is called by inferPlan's startup on
    FEO worker 40 and must report that thread, not the setup thread."""
    import threading
    out = json.loads(P.setup(json.dumps(stub_config(tmp_path))))
    assert not out["identity"]["refused"]
    seen = {}
    worker = threading.Thread(target=lambda: seen.update(json.loads(P.bind_thread())))
    worker.start()
    worker.join()
    assert seen == {"engine": "stub", "thread": worker.ident}
    assert worker.ident != threading.get_ident()


def _synthetic_profile(path):
    """Six forward-looking optical frames (x right, y down, z forward) yawed around REF."""
    R_fwd = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
    cams = []
    for slot, yaw in zip(R.SLOTS, (0.0, 55.0, -55.0, 110.0, 180.0, -110.0)):
        c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        Rz = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])
        T = np.eye(4)
        T[:3, :3] = Rz @ R_fwd
        T[:3, 3] = [1.5 * c, 1.5 * s, 1.6]
        cams.append({"slot": slot, "intrinsic": [[800.0, 0.0, 960.0], [0.0, 800.0, 540.0], [0.0, 0.0, 1.0]],
                     "image_size_wh": [1920, 1080], "camera_to_reference": T.tolist()})
    path.write_text(json.dumps({"dataset_name": "synthetic", "cameras": cams,
                                "egomotion": {"curvature_speed_floor_mps": 0.1}}))
    return path


def test_stub_engine_checks_the_rig_mounts(tmp_path):
    """The agent's rig gate (10 mm / 0.1 deg) must work without a GPU: the stub engine reports the
    same per-camera mount errors as the checkpoint engine."""
    import importlib.util
    profile = _synthetic_profile(tmp_path / "profile.json")
    spec = importlib.util.spec_from_file_location(
        "make_fake_rig", Path(__file__).resolve().parents[2] / "scripts" / "make_fake_rig.py")
    mfr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mfr)
    rig = mfr.build(str(profile), 1920, 1920)
    cfg = dict(stub_config(tmp_path), profile=str(profile))
    assert not json.loads(P.setup(json.dumps(cfg)))["identity"]["refused"]
    out = json.loads(P.set_rig(json.dumps(rig)))
    assert max(out["rig_pose_err_mm"]) < 1e-6 and max(out["rig_pose_err_deg"]) < 1e-6
    moved = json.loads(json.dumps(rig))
    m = np.asarray(moved["cameras"][3]["world_matrix"]).reshape(4, 4)
    m[0, 3] += 0.05                                     # cam_rear_left 5 cm along world x
    moved["cameras"][3]["world_matrix"] = m.reshape(-1).tolist()
    out = json.loads(P.set_rig(json.dumps(moved)))
    assert out["rig_pose_err_mm"][3] == pytest.approx(50.0, abs=1e-6)
    assert max(out["rig_pose_err_mm"][:3] + out["rig_pose_err_mm"][4:]) < 1e-6
    turned = json.loads(json.dumps(rig))
    m = np.asarray(turned["cameras"][0]["world_matrix"]).reshape(4, 4)
    c, s = math.cos(math.radians(0.5)), math.sin(math.radians(0.5))
    m[:3, :3] = np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]) @ m[:3, :3]
    turned["cameras"][0]["world_matrix"] = m.reshape(-1).tolist()
    out = json.loads(P.set_rig(json.dumps(turned)))
    assert out["rig_pose_err_deg"][0] == pytest.approx(0.5, abs=1e-6)


def _circle_route(radius, left, n=200):
    """A circle through the map origin, starting heading +x; left = counter-clockwise."""
    sgn = 1.0 if left else -1.0
    th = np.linspace(0.0, 1.5 * math.pi, n)
    return np.stack([radius * np.sin(th), sgn * radius * (1.0 - np.cos(th))], axis=1)


@pytest.mark.parametrize("left", [True, False])
def test_pure_pursuit_on_a_circle_returns_its_curvature(left):
    """On the route, heading along it, pure pursuit to any route point is exactly 1/R, with the
    sign of the turn (positive to the left)."""
    route = _circle_route(20.0, left)
    for i in (0, 37, 90):
        th = 1.5 * math.pi * i / 199
        sgn = 1.0 if left else -1.0
        pose = (float(route[i, 0]), float(route[i, 1]), sgn * th)
        kappa = P.pure_pursuit_curvature(route, pose, 6.0)
        assert kappa == pytest.approx(sgn / 20.0, rel=0.02)


def test_ue_pose_in_map_negates_y_and_yaw():
    yaw_ue = math.radians(30.0)
    M = np.eye(4)
    M[:3, :3] = [[math.cos(yaw_ue), -math.sin(yaw_ue), 0], [math.sin(yaw_ue), math.cos(yaw_ue), 0], [0, 0, 1]]
    M[:3, 3] = [10.0, 4.0, 0.3]
    x, y, yaw = P.ue_pose_in_map(M.reshape(-1).tolist(), [-1.0, 0.0, 0.0])
    assert (x, y, yaw) == pytest.approx((10.0 - math.cos(yaw_ue), -(4.0 - math.sin(yaw_ue)), -yaw_ue))


def test_stub_pure_pursuit_plan_turns_left_and_reaches_the_target_speed(tmp_path):
    """The stand-in planner of the bench integration runs: a left route gives positive curvature
    (ICD PlanSample: positive to the left) and a plan that accelerates toward the target."""
    route = _circle_route(20.0, left=True)
    rf = tmp_path / "route.json"
    rf.write_text(json.dumps({"map": "test", "waypoints": [[float(a), float(b), 0.0, 1] for a, b in route]}))
    eng = P.StubEngine({"stub_route": str(rf), "stub_target_speed_mps": 3.0})
    eng.origin = np.zeros(3)
    eng.pose_map[7] = (0.0, 0.0, 0.0)                       # at the route start, heading +x
    eng.rows[7] = np.zeros((64, 4), dtype=np.float32)       # standing still
    eng.frames_with_images.add(7)
    samples, v0, info = eng.infer(7)
    assert v0 == 0.0 and info["mode"] == "stub-pure-pursuit"
    assert samples[0, 1] == pytest.approx(1.0 / 20.0, rel=0.05)
    assert samples[0, 0] == pytest.approx(1.0)              # accelerate (limited to 1 m/s^2)
    assert abs(samples[-1, 0]) < 0.2                         # near the target at the horizon end
    assert samples[-1, 3] > 0.0                              # the integrated path bends left


def test_c2_projection_block_names_and_shapes():
    """C2 projections: the C2 camera names (the checkpoint's slot names, ICD A25) in the fixed order,
    12 row-major numbers per operator, the tile size, and the front high-resolution operator on the
    front camera only."""
    P = np.arange(6 * 12, dtype=np.float32).reshape(1, 6, 3, 4)
    F = (np.arange(12, dtype=np.float32) + 100).reshape(1, 1, 3, 4)
    block = R.c2_projection_block(P, F)
    assert [b["camera"] for b in block] == ["front", "front_left", "front_right",
                                            "rear_left", "rear", "rear_right"]
    assert block[2]["matrix"] == list(range(24, 36)) and block[2]["image_size"] == [512, 512]
    assert block[0]["front_hi_res_matrix"] == list(range(100, 112)) and block[0]["front_hi_res_size"] == [1024, 1024]
    assert all("front_hi_res_matrix" not in b for b in block[1:])
    json.dumps(block)                                       # plain JSON for the agent


def test_write_run_record_identity_and_file_hashes(tmp_path):
    import hashlib
    import json
    import de4sdv_planner as P
    cfg = tmp_path / "vehicle_limits.json"
    cfg.write_text('{"wheelbase_m": 2.85}\n')
    path = tmp_path / "run_record.json"
    fields = {"contractIdentity": "de4sdv.driving.icd.v2", "scenarioVariant": {"fault": "camera_missing"},
              "vehicleConfiguration": {"path": str(cfg)}, "route": {"path": str(tmp_path / "absent.json")}}
    out = json.loads(P.write_run_record(str(path), json.dumps(fields)))
    data = path.read_bytes()
    assert out["sha256"] == hashlib.sha256(data).hexdigest()
    assert out["identity"] == out["sha256"][:16] and len(out["identity"]) == 16
    rec = json.loads(data)
    assert rec["scenarioVariant"] == {"fault": "camera_missing"}
    assert rec["vehicleConfiguration"]["sha256"] == hashlib.sha256(cfg.read_bytes()).hexdigest()
    assert rec["route"]["sha256"] is None
    assert isinstance(rec["writtenAtMonoNs"], int) and isinstance(rec["writtenAtRealNs"], int)
    # frozen: a second write is refused and leaves the file unchanged
    import pytest
    with pytest.raises(FileExistsError):
        P.write_run_record(str(path), json.dumps(fields))
    assert path.read_bytes() == data
