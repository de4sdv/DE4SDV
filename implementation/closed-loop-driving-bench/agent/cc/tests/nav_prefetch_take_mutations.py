#!/usr/bin/env python3
"""Single-point mutation probes for the step's take of the nav prefetch
(TakeNavPrefetch and RenderNavPrefetch in navigation_input.cpp).

Each entry replaces exactly one source fragment in a copy of navigation_input.cpp,
builds tests/navigation_input_test.cpp against that copy with the real rasterizer,
runs it with the bench's map and route, and reports which tests caught it. The
sources are never written; the script exits non-zero if any mutation survives,
does not apply or does not build.
  nav_prefetch_take_mutations.py <map.json> <route.json> <upstream rasterizer object>
(tests/run_tests.sh --mutations runs it when the navigation input's test runs.)
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from mutation_report import killed_by, print_table  # noqa: E402

HERE = Path(__file__).resolve().parents[1]           # agent/cc
BENCH = HERE.parents[1]                              # closed-loop-driving-bench
NAVD = BENCH / "navigation"
UPN = NAVD / ".upstream" / "Model" / "navigation" / "native"
INC = BENCH / "interfaces" / "include"
SOURCE = HERE / "navigation_input.cpp"
TEST = HERE / "tests" / "navigation_input_test.cpp"
CXXFLAGS = ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-pthread"]
INCLUDES = [f"-I{HERE}", f"-I{NAVD}", f"-I{UPN}", f"-I{INC}"]

# (name, rule, old, new): `old` must occur exactly once in navigation_input.cpp.
MUTATIONS = [
    ("T01 a use hands over the chain's rasters",
     "a use hands the checkpoint this frame's prefetched rasters",
     "  take.map_context = hit_map;\n  take.route_mask = hit_route;\n",
     "  take.map_context = &nav.map_context();\n  take.route_mask = &nav.route_mask();\n"),
    ("T02 a use hands over the previous use's rasters",
     "the rasters are swapped into the caller's buffers",
     "  hit_map->swap(pf.map_context);\n  hit_route->swap(pf.route_mask);\n",
     ""),
    ("T03 the carried route events dropped",
     "the changes of renders never used reach the next take",
     "prefetch->Take(frame, max_wait_ns, &pf, &take.route_events, &take.take_ms)",
     "prefetch->Take(frame, max_wait_ns, &pf, nullptr, &take.take_ms)"),
    ("T04 an unused render's own route event dropped",
     "the change of a render the step does not use is logged",
     "    if (!pf.route_event.empty()) take.route_events.push_back(pf.route_event);\n",
     ""),
    ("T05 an unused render's own event before the carried ones",
     "the carried changes come first, oldest first",
     "take.route_events.push_back(pf.route_event);",
     "take.route_events.insert(take.route_events.begin(), pf.route_event);"),
    ("T06 a used render's route event returned as well",
     "a used render's change is logged once, by the step",
     "  if (use != UseDecision::kUse) {\n",
     "  if (use == UseDecision::kUse && !pf.route_event.empty()) take.route_events.push_back(pf.route_event);\n"
     "  if (use != UseDecision::kUse) {\n"),
    ("T07 the announcement not observed at the take",
     "a use's route observation is the announcement read at the take",
     "  NavigationInput::ObserveAnnouncement(now, &pf.step.route);\n",
     ""),
    ("T08 the pose check compares the drawn pose with itself",
     "a render drawn at another pose is not used",
     "DecideUse(pf.ok, pf.pose, step_pose,",
     "DecideUse(pf.ok, pf.pose, (static_cast<void>(step_pose), pf.pose),"),
    ("T09 the route check compares the drawn route with itself",
     "a render drawn with another route is not used",
     "pf.step.route_identity, NavigationInput::RouteIdentity(now));",
     "pf.step.route_identity, pf.step.route_identity);"),
    ("T10 a timed-out take reported as not submitted",
     "C2's outcome names why the step rendered on the chain",
     "    take.outcome = NavPrefetchOutcome::kTimedOut;\n",
     "    take.outcome = NavPrefetchOutcome::kNotSubmitted;\n"),
    ("T11 a failed render reported as a pose change",
     "C2's outcome names why the step rendered on the chain",
     "    if (use == UseDecision::kRenderFailed) take.outcome = NavPrefetchOutcome::kRenderFailed;\n",
     "    if (use == UseDecision::kRenderFailed) take.outcome = NavPrefetchOutcome::kPoseChanged;\n"),
    ("T12 C2's string for a pose change is route_changed",
     "the outcome strings are ICD A31's",
     "    case NavPrefetchOutcome::kPoseChanged: return \"pose_changed\";\n",
     "    case NavPrefetchOutcome::kPoseChanged: return \"route_changed\";\n"),
    ("T13 the prefetch render keeps no route event",
     "the prefetch thread's render hands its route change to the take",
     "  if (r->ok && !r->step.route_event.empty()) {\n",
     "  if (r->ok && r->step.route_event.empty()) {\n"),
    ("T14 a frame never requested goes on to the use decision",
     "C2's outcome names why the step rendered on the chain",
     "  if (o == TakeOutcome::kNotSubmitted) {\n    take.outcome = NavPrefetchOutcome::kNotSubmitted;\n    return take;\n  }\n",
     ""),
    ("T15 a use returns no step fields",
     "a use returns the step's navigation fields with its rasters",
     "  take.step = std::move(pf.step);   // its route_event: the step logs it once, with its frame\n",
     ""),
    ("T16 a use reported as not submitted",
     "C2's outcome says when the step used the prefetched render",
     "  take.outcome = NavPrefetchOutcome::kHit;\n",
     ""),
    ("T17 a route change reported as a pose change",
     "C2's outcome names why the step rendered on the chain",
     "    if (use == UseDecision::kRouteChanged) take.outcome = NavPrefetchOutcome::kRouteChanged;\n",
     "    if (use == UseDecision::kRouteChanged) take.outcome = NavPrefetchOutcome::kPoseChanged;\n"),
    ("T18 the prefetch render does not record its pose",
     "a render drawn at another pose is not used",
     "  r->pose = pose;\n",
     ""),
]


def run(command: list[str], timeout: int | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(command, capture_output=True, text=True, timeout=timeout)


def main() -> int:
    if len(sys.argv) != 4:
        print(__doc__)
        return 2
    map_path, route_path, rasterizer = sys.argv[1:4]
    source = SOURCE.read_text(encoding="utf-8")
    work = Path(tempfile.mkdtemp(prefix="nav_take_mut_"))
    rows = []
    try:
        # Everything but navigation_input.cpp is built once.
        objects = []
        for name, path in (("test", TEST), ("route_listener", HERE / "route_listener.cpp"),
                           ("navigation_raster", NAVD / "navigation_raster.cpp")):
            obj = work / f"{name}.o"
            built = run(["g++", *CXXFLAGS, *INCLUDES, "-c", str(path), "-o", str(obj)])
            if built.returncode != 0:
                print(f"{path.name} does not build:\n{built.stderr[-800:]}")
                return 2
            objects.append(str(obj))
        objects.append(rasterizer)

        def build_and_run(cpp: Path, binary: Path):
            obj = binary.with_suffix(".o")
            built = run(["g++", *CXXFLAGS, *INCLUDES, "-c", str(cpp), "-o", str(obj)])
            if built.returncode != 0:
                return None, built.stderr[-600:]
            linked = run(["g++", *CXXFLAGS, str(obj), *objects, "-o", str(binary)])
            if linked.returncode != 0:
                return None, linked.stderr[-600:]
            try:
                return run([str(binary), map_path, route_path], timeout=300), ""
            except subprocess.TimeoutExpired:
                return "timeout", ""

        pristine_dir = work / "pristine"
        pristine_dir.mkdir()
        shutil.copy(SOURCE, pristine_dir / "navigation_input.cpp")
        clean, error = build_and_run(pristine_dir / "navigation_input.cpp", pristine_dir / "test")
        if clean is None or clean == "timeout" or clean.returncode != 0:
            print("the pristine tests do not pass:\n" + (error or getattr(clean, "stdout", str(clean))[-2000:]))
            return 2
        print(f"pristine: {clean.stdout.strip().splitlines()[-1]}")

        for name, rule, old, new in MUTATIONS:
            count = source.count(old)
            if count != 1:
                rows.append((name, rule, "NOT APPLIED", f"{count} matches"))
                continue
            mutant_dir = work / name.split()[0]
            mutant_dir.mkdir()
            cpp = mutant_dir / "navigation_input.cpp"
            # The mutant's own directory holds no header: navigation_input.h comes from -I agent/cc.
            cpp.write_text(source.replace(old, new, 1), encoding="utf-8")
            result, error = build_and_run(cpp, mutant_dir / "test")
            if result is None:
                rows.append((name, rule, "BUILD ERROR", error.strip().splitlines()[-1] if error.strip() else ""))
            elif result == "timeout":
                rows.append((name, rule, "killed", "timed out"))
            elif result.returncode != 0:
                rows.append((name, rule, "killed", killed_by(result.stdout + result.stderr, result.returncode)))
            else:
                summary = result.stdout.strip().splitlines()[-1] if result.stdout.strip() else ""
                rows.append((name, rule, "SURVIVED", summary))
    finally:
        shutil.rmtree(work, ignore_errors=True)

    unchanged = SOURCE.read_text(encoding="utf-8") == source
    print()
    print_table([(name, rule, result, by if result == "killed" else "") for name, rule, result, by in rows])
    survivors = [r for r in rows if r[2] != "killed"]
    print()
    for name, _, result, detail in survivors:
        print(f"  - {name}: {result} {detail}")
    print(f"source unchanged: {unchanged}")
    ok = not survivors and unchanged and len(rows) == len(MUTATIONS)
    print(f"NAV_PREFETCH_TAKE_MUTATIONS {'PASS' if ok else 'FAIL'}: {len(rows)} mutations, "
          f"{len(rows) - len(survivors)} killed, {len(survivors)} not killed")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
