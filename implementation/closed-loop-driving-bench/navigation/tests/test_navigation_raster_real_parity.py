"""Bit-exact parity of the optimised render on the real CARLA map.

The optimised ``Render`` packs the primitives once, culls them to the raster
window of the pose and fills the map channels with its own span rasterizer.
Those are performance changes only: on the real exported map (Town10HD_Opt) it
must stay bit-identical to

* ``RenderReference`` -- the unoptimised path that re-packs every call and hands
  every primitive to upstream's native renderer, and
* upstream's own reference path,
  ``navigation.rasterizer.NativeNavigationRasterizer.render``.

Both are checked over the same 80 poses: 60 evenly spaced along the route
centre lines and 20 random poses inside the map bounds (four held at the map
edge, two at junction centroids).

The real map is an artefact of the CARLA export, not part of the repository, so
the tests skip when it is absent.  Point ``DE4SDV_NAVIGATION_REAL_MAP_DIR`` at a
directory holding ``map.json`` and ``route.json`` to run them.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import numpy as np
import pytest

import autoe2e_bridge
import nav_map_json

MAP_CHANNELS = 14
ROUTE_CHANNELS = 2
HEIGHT = 450
WIDTH = 300

POSE_COUNT = 80


def _real_map_directory() -> Path:
    # The export is a run artefact, not a repository file: the test runs only where the
    # environment names a directory holding it.
    return Path(os.environ.get("DE4SDV_NAVIGATION_REAL_MAP_DIR", "/nonexistent/navigation_town10"))


REAL_MAP_DIR = _real_map_directory()
REAL_MAP = REAL_MAP_DIR / "map.json"
REAL_ROUTE = REAL_MAP_DIR / "route.json"

pytestmark = pytest.mark.skipif(
    not (REAL_MAP.is_file() and REAL_ROUTE.is_file()),
    reason=f"real CARLA map export not found under {REAL_MAP_DIR}",
)


@pytest.fixture(scope="module")
def parity_sweep_binary(repository_root: Path) -> Path:
    path = repository_root / "build" / "parity_sweep"
    if not path.is_file():
        pytest.fail("build/parity_sweep missing; run `make parity`")
    return path


@pytest.fixture(scope="module")
def sweep(parity_sweep_binary: Path, tmp_path_factory) -> dict:
    """Run the fast-vs-reference sweep over 80 poses and return its summary."""
    poses_out = tmp_path_factory.mktemp("real-parity") / "poses.txt"
    completed = subprocess.run(
        [
            str(parity_sweep_binary),
            "--map", str(REAL_MAP),
            "--route", str(REAL_ROUTE),
            "--poses-out", str(poses_out),
            "--json",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    summary = json.loads(completed.stdout)
    summary["poses"] = [
        tuple(float(value) for value in line.split())
        for line in poses_out.read_text().splitlines()
        if line.strip()
    ]
    return summary


def _upstream_engine(native_library: Path):
    rasterizer = autoe2e_bridge.rasterizer()
    geometry = autoe2e_bridge.geometry().AUTOE2E_NAVIGATION_GEOMETRY
    return rasterizer.NativeNavigationRasterizer(
        geometry, library_path=str(native_library)
    ), rasterizer


def _render_cpp(raster_cli: Path, directory: Path, pose):
    map_out = directory / "map.f32"
    route_out = directory / "route.u8"
    completed = subprocess.run(
        [
            str(raster_cli),
            "--map", str(REAL_MAP),
            "--route", str(REAL_ROUTE),
            "--pose", repr(pose[0]), repr(pose[1]), repr(pose[2]),
            "--map-out", str(map_out),
            "--route-out", str(route_out),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return (
        np.fromfile(map_out, dtype="<f4").reshape(MAP_CHANNELS, HEIGHT, WIDTH),
        np.fromfile(route_out, dtype=np.uint8).reshape(
            ROUTE_CHANNELS, HEIGHT, WIDTH
        ),
    )


def test_sweep_covers_route_and_random_poses(sweep: dict):
    assert len(sweep["poses"]) == POSE_COUNT
    assert sweep["route_poses"] == 60
    assert sweep["random_poses"] == 20
    assert (REAL_MAP_DIR / "map.json").is_file()
    # Every pose is inside the map bounds (edge poses included).
    payload = json.loads(REAL_MAP.read_text(encoding="ascii"))
    x_min, y_min, x_max, y_max = payload["bounds_enu_m"]
    for x, y, _yaw in sweep["poses"]:
        assert x_min <= x <= x_max
        assert y_min <= y <= y_max


def test_optimised_render_matches_reference_path(sweep: dict):
    """Render vs RenderReference over 60 route and 20 random poses."""
    assert sweep["poses"], "no poses"
    assert sweep["mismatched_poses"] == 0
    assert sweep["map_mismatch_pixels"] == 0
    assert sweep["route_mismatch_pixels"] == 0
    assert max(sweep["map_max_abs"]) == 0.0
    assert max(sweep["route_max_abs"]) == 0.0


def test_optimised_render_matches_upstream_python(
    sweep: dict, native_library: Path, raster_cli: Path, tmp_path: Path
):
    """Render vs upstream's Python reference path, same 80 poses."""
    navigation_map = nav_map_json.load_map(REAL_MAP)
    route = nav_map_json.load_route(
        REAL_ROUTE,
        map_version=navigation_map.map_version,
        frame_id=navigation_map.frame.frame_id,
    )
    engine, rasterizer = _upstream_engine(native_library)
    worst_map = 0.0
    worst_route = 0.0
    populated = np.zeros(MAP_CHANNELS, dtype=bool)
    for pose in sweep["poses"]:
        reference = engine.render(
            navigation_map,
            route,
            rasterizer.EgoPose(
                x_enu_m=pose[0], y_enu_m=pose[1], yaw_rad=pose[2], timestamp_ns=0
            ),
        )
        cpp_map, cpp_route = _render_cpp(raster_cli, tmp_path, pose)
        assert np.array_equal(cpp_map, reference.map_context), (
            f"pose {pose}: map pixels differ; max abs "
            f"{float(np.abs(cpp_map.astype(np.float64) - reference.map_context).max())}"
        )
        assert np.array_equal(cpp_route, reference.route_mask), (
            f"pose {pose}: route pixels differ"
        )
        worst_map = max(
            worst_map,
            float(
                np.abs(
                    cpp_map.astype(np.float64) - reference.map_context.astype(np.float64)
                ).max()
            ),
        )
        worst_route = max(
            worst_route,
            float(
                np.abs(
                    cpp_route.astype(np.int16) - reference.route_mask.astype(np.int16)
                ).max()
            ),
        )
        populated |= np.array([channel.any() for channel in reference.map_context])
    assert worst_map == 0.0
    assert worst_route == 0.0
    # The sweep must exercise the channels it claims to (no vacuous zeros).
    assert populated.sum() >= 8


def test_reference_path_matches_upstream_python(
    sweep: dict, native_library: Path, raster_cli: Path, tmp_path: Path
):
    """RenderReference vs upstream, at a few poses."""
    navigation_map = nav_map_json.load_map(REAL_MAP)
    route = nav_map_json.load_route(
        REAL_ROUTE,
        map_version=navigation_map.map_version,
        frame_id=navigation_map.frame.frame_id,
    )
    engine, rasterizer = _upstream_engine(native_library)
    for pose in sweep["poses"][::10]:
        reference = engine.render(
            navigation_map,
            route,
            rasterizer.EgoPose(
                x_enu_m=pose[0], y_enu_m=pose[1], yaw_rad=pose[2], timestamp_ns=0
            ),
        )
        # raster_cli renders the optimised path; the sweep already proves it is
        # bit-identical to RenderReference, so both equal upstream.
        cpp_map, cpp_route = _render_cpp(raster_cli, tmp_path, pose)
        assert np.array_equal(cpp_map, reference.map_context)
        assert np.array_equal(cpp_route, reference.route_mask)
