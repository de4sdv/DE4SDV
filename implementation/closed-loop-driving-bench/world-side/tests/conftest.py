"""Shared fixtures: the fake carla module, a synthetic camera profile, a clock.

The camera profile has the keys the agent's `de4sdv_planner.rig` reads
(`slot`, `intrinsic`, `image_size_wh`, `camera_to_reference`, plus top-level
`dataset_name` and `egomotion`). The real nuPlan calibration is not available
on this host and is passed by path on the command line, so a synthetic profile
with the same keys is enough to prove the spawn path.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
RIG_PATH = BENCH / "agent" / "python" / "de4sdv_planner" / "rig.py"
EVALUATORS = BENCH / "case-evaluators"

# the fake carla package must win over any real one
sys.path.insert(0, str(HERE / "fake_carla"))
sys.path.insert(0, str(HERE.parent))          # world_side
sys.path.insert(0, str(EVALUATORS))          # runio, cases

SLOTS = ["front", "front_left", "front_right", "rear_left", "rear", "rear_right"]


class FakeClock:
    """Deterministic monotonic clock; sleep advances it (plus an overshoot)."""

    def __init__(self, start: float = 1000.0, overshoot_s: float = 0.0):
        self.now = float(start)
        self.overshoot_s = float(overshoot_s)
        self.sleeps: list[float] = []

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += float(seconds)

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(float(seconds))
        if seconds > 0.0:
            self.now += float(seconds) + self.overshoot_s


def _rot_z(yaw_rad: float):
    c, s = math.cos(yaw_rad), math.sin(yaw_rad)
    return [[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]]


def _rot_y(pitch_rad: float):
    c, s = math.cos(pitch_rad), math.sin(pitch_rad)
    return [[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]]


def _matmul(a, b):
    return [[sum(a[i][k] * b[k][j] for k in range(3)) for j in range(3)] for i in range(3)]


# OPT (x right, y down, z forward) axes in REF (x forward, y left, z up)
R_BASE = [[0.0, 0.0, 1.0],
          [-1.0, 0.0, 0.0],
          [0.0, -1.0, 0.0]]

CAMERA_MOUNTS = {
    "front": (1.5, 0.0, 1.40, 0.0),
    "front_left": (1.2, 0.85, 1.40, 35.0),
    "front_right": (1.2, -0.85, 1.40, -35.0),
    "rear_left": (-0.2, 0.9, 1.40, 145.0),
    "rear": (-0.5, 0.0, 1.40, 180.0),
    "rear_right": (-0.2, -0.9, 1.40, -145.0),
}


def camera_to_reference(slot: str) -> list[list[float]]:
    x, y, z, yaw_deg = CAMERA_MOUNTS[slot]
    R = _matmul(_rot_z(math.radians(yaw_deg)), _matmul(_rot_y(math.radians(-5.0)), R_BASE))
    return [[R[0][0], R[0][1], R[0][2], x],
            [R[1][0], R[1][1], R[1][2], y],
            [R[2][0], R[2][1], R[2][2], z],
            [0.0, 0.0, 0.0, 1.0]]


def profile_payload() -> dict:
    cameras = []
    for slot in SLOTS:
        W0 = H0 = 512
        f = 0.85 * W0                     # ~60 deg horizontal field of view
        cameras.append({
            "slot": slot,
            "intrinsic": [[f, 0.0, W0 / 2.0], [0.0, f, H0 / 2.0], [0.0, 0.0, 1.0]],
            "image_size_wh": [W0, H0],
            "camera_to_reference": camera_to_reference(slot),
        })
    return {
        "dataset_name": "synthetic-test-profile",
        "cameras": cameras,
        "egomotion": {"curvature_speed_floor_mps": 0.1,
                      "curvature_zero_below_mps": 0.05,
                      "curvature_limit": 0.5},
    }


def write_profile(path: Path) -> Path:
    path.write_text(json.dumps(profile_payload(), indent=1) + "\n")
    return path


def write_route(path: Path, *, map_name: str = "Town10HD_Opt",
                start: tuple[float, float, float] = (0.0, 0.0, 0.0),
                count: int = 5, step_m: float = 5.0,
                destination: tuple[float, float] = (1000.0, 1000.0)) -> Path:
    x, y, heading = start
    waypoints = [[x + i * step_m, y, heading, 296] for i in range(count)]
    path.write_text(json.dumps({"map": map_name, "waypoints": waypoints,
                                "destination": list(destination)}, indent=1) + "\n")
    return path


def write_run_record(run_dir: Path, *, scenario: str = "closedLoopRoute",
                     fault: str = "none") -> Path:
    record = {
        "contractIdentity": "de4sdv.driving.icd.v2",
        "scenario": scenario,
        "runRole": "nominal" if fault == "none" else "fault",
        "campaignId": "world-side-tests",
        "scenarioVariant": {"fault": fault},
    }
    path = run_dir / "run_record.json"
    path.write_text(json.dumps(record, indent=1) + "\n")
    return path


@pytest.fixture
def profile(tmp_path: Path) -> Path:
    return write_profile(tmp_path / "nuplan_synthetic.json")


@pytest.fixture
def route(tmp_path: Path) -> Path:
    return write_route(tmp_path / "route.json")


# ------------------------------------------------------------------ running


def tool_args(route: Path, profile: Path, run_dir: Path, *, warmup: float = 2.0,
              run_s: float = 1.0, faults: tuple = (), extra: tuple = (),
              width: int = 640, front_width: int = 1024):
    """The CLI arguments as the tool parses them (no subprocess)."""
    import world_side

    argv = ["--route", str(route), "--profile", str(profile),
            "--rig-path", str(RIG_PATH), "--run-dir", str(run_dir),
            "--warmup-s", str(warmup), "--run-s", str(run_s),
            "--width", str(width), "--front-width", str(front_width)]
    for fault in faults:
        argv += ["--fault", fault]
    argv += list(extra)
    return world_side.build_parser().parse_args(argv)


def make_tool(route: Path, profile: Path, run_dir: Path, client, clock, *, warmup: float = 2.0,
              run_s: float = 1.0, faults: tuple = (), extra: tuple = ()):
    """A WorldSide on the fake client, not started (R4/R5 inspect the spawns)."""
    import world_side

    args = tool_args(route, profile, run_dir, warmup=warmup, run_s=run_s,
                     faults=faults, extra=extra)
    rig = world_side.load_rig_module(str(RIG_PATH))
    return world_side.WorldSide(args, client_factory=lambda host, port: client,
                                clock=clock, sleep=clock.sleep, rig_module=rig)


def run_tool(route: Path, profile: Path, run_dir: Path, client, clock, *, warmup: float = 2.0,
             run_s: float = 1.0, faults: tuple = (), extra: tuple = (),
             stop_requested=None):
    """Run the tool in process; returns (exit code, run directory)."""
    import world_side

    args = tool_args(route, profile, run_dir, warmup=warmup, run_s=run_s,
                     faults=faults, extra=extra)
    code = world_side.main(
        ["--route", str(route), "--profile", str(profile), "--rig-path", str(RIG_PATH),
         "--run-dir", str(run_dir), "--warmup-s", str(warmup), "--run-s", str(run_s),
         "--width", "640", "--front-width", "1024"]
        + [item for fault in faults for item in ("--fault", fault)]
        + list(extra),
        client_factory=lambda host, port: client, clock=clock, sleep=clock.sleep,
        stop_requested=stop_requested, install_signals=False)
    return code, run_dir


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())
