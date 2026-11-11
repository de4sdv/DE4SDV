#!/usr/bin/env python3
"""Report the per-channel difference between the C++ and Python raster paths.

For every synthetic map, every ego pose and both route cases, renders with
upstream's ``NativeNavigationRasterizer`` (Python, same native library) and
with ``navigation_raster`` (C++), and prints the maximum absolute difference per
channel.  Everything must be exactly 0: the C++ path packs the same primitives
and its span rasterizer reproduces upstream's per-pixel decisions.  The real
map is swept by ``tests/parity_sweep.cpp`` and
``tests/test_navigation_raster_real_parity.py``.

    .venv/bin/python parity_report.py           # human-readable table
    .venv/bin/python parity_report.py --json    # one JSON object

Exit code 0 when every channel of every case is identical, 1 otherwise.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE / "tests"))

import autoe2e_bridge  # noqa: E402
import nav_map_json  # noqa: E402
import synthetic  # noqa: E402

CHANNEL_NAMES = [channel.name for channel in autoe2e_bridge.geometry().MapChannel]
ROUTE_NAMES = [channel.name for channel in autoe2e_bridge.geometry().RouteChannel]


def _render_reference(native_library: Path, navigation_map, route, pose):
    rasterizer = autoe2e_bridge.rasterizer()
    geometry = autoe2e_bridge.geometry().AUTOE2E_NAVIGATION_GEOMETRY
    engine = rasterizer.NativeNavigationRasterizer(
        geometry, library_path=str(native_library)
    )
    return engine.render(
        navigation_map,
        route,
        rasterizer.EgoPose(x_enu_m=pose[0], y_enu_m=pose[1], yaw_rad=pose[2],
                           timestamp_ns=0),
    )


def run(cli: Path, native_library: Path, *, verbose: bool = False) -> dict:
    results = {"cases": 0, "mismatched_cases": 0, "map_max_abs": [0.0] * 14,
               "route_max_abs": [0.0] * 2, "per_case": []}
    with tempfile.TemporaryDirectory() as directory:
        work = Path(directory)
        for kind, factory in synthetic.MAPS.items():
            navigation_map = factory()
            map_path = work / f"{kind}.map.json"
            nav_map_json.dump_map(map_path, navigation_map)
            route_path = synthetic.write_route(work / f"{kind}.route.json", kind)
            route = nav_map_json.load_route(
                route_path, map_version=navigation_map.map_version,
                frame_id=navigation_map.frame.frame_id,
            )
            for pose_index, pose in enumerate(synthetic.poses(kind)):
                reference = _render_reference(
                    native_library, navigation_map, route, pose
                )
                map_out = work / "map.f32"
                route_out = work / "route.u8"
                completed = subprocess.run(
                    [
                        str(cli),
                        "--map", str(map_path),
                        "--route", str(route_path),
                        "--pose", repr(pose[0]), repr(pose[1]), repr(pose[2]),
                        "--map-out", str(map_out),
                        "--route-out", str(route_out),
                    ],
                    capture_output=True, text=True, check=False,
                )
                if completed.returncode != 0:
                    raise SystemExit(f"raster_cli failed: {completed.stderr}")
                cpp_map = np.fromfile(map_out, dtype="<f4").reshape(14, 450, 300)
                cpp_route = np.fromfile(route_out, dtype=np.uint8).reshape(2, 450, 300)
                map_diff = np.abs(
                    cpp_map.astype(np.float64)
                    - reference.map_context.astype(np.float64)
                )
                route_diff = np.abs(
                    cpp_route.astype(np.int16) - reference.route_mask.astype(np.int16)
                )
                per_channel = [float(map_diff[c].max()) for c in range(14)]
                per_route = [float(route_diff[c].max()) for c in range(2)]
                results["cases"] += 1
                results["map_max_abs"] = [
                    max(a, b) for a, b in zip(results["map_max_abs"], per_channel)
                ]
                results["route_max_abs"] = [
                    max(a, b) for a, b in zip(results["route_max_abs"], per_route)
                ]
                identical = (
                    int((cpp_map != reference.map_context).sum()) == 0
                    and int((cpp_route != reference.route_mask).sum()) == 0
                )
                if not identical:
                    results["mismatched_cases"] += 1
                results["per_case"].append({
                    "map": kind,
                    "pose": list(pose),
                    "identical": identical,
                    "map_max_abs": max(per_channel),
                    "route_max_abs": max(per_route),
                })
                if verbose:
                    print(f"{kind:11s} pose{pose_index} x={pose[0]:7.2f} "
                          f"y={pose[1]:7.2f} yaw={pose[2]:6.3f} "
                          f"identical={identical}")
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--cli", default=str(HERE / "build" / "raster_cli"))
    parser.add_argument("--library", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args(argv)
    native_library = autoe2e_bridge.require_native_library() if args.library is None \
        else Path(args.library)
    results = run(Path(args.cli), native_library, verbose=args.verbose)
    if args.json:
        print(json.dumps(results, indent=1, sort_keys=True))
    else:
        print(f"cases: {results['cases']}, mismatched: "
              f"{results['mismatched_cases']}")
        for name, value in zip(CHANNEL_NAMES, results["map_max_abs"]):
            print(f"  map   {name:32s} max abs diff {value:g}")
        for name, value in zip(ROUTE_NAMES, results["route_max_abs"]):
            print(f"  route {name:32s} max abs diff {value:g}")
    worst = max(results["map_max_abs"] + results["route_max_abs"])
    return 0 if worst == 0.0 and results["mismatched_cases"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
