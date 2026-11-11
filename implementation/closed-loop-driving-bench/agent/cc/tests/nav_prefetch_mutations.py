#!/usr/bin/env python3
"""Single-point mutation probes for the agent's nav prefetch (nav_prefetch.h).

Each entry replaces exactly one source fragment in a copy of the header, builds
tests/nav_prefetch_test.cpp against that copy and reports whether a test caught
it. The sources are never written; the script exits non-zero if any mutation
survives or does not apply.
"""
import os
import shutil
import subprocess
import sys
import tempfile

# The unit lives in agent/cc/; this script and the tests in agent/cc/tests/.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HEADER = os.path.join(ROOT, "nav_prefetch.h")
TEST = os.path.join(ROOT, "tests", "nav_prefetch_test.cpp")
CXXFLAGS = ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-pthread"]

MUTATIONS = [
    {
        "name": "P01 a take does not wait for a render in flight",
        "old": "    if (in_flight_ && in_flight_frame_ == frame) return true;\n",
        "new": "",
    },
    {
        "name": "P02 older results dropped without their route events",
        "old": "  void DiscardOlderLocked(std::uint64_t frame) {\n"
               "    if (frame > taken_through_) taken_through_ = frame;\n"
               "    for (auto it = results_.begin(); it != results_.end() && it->first < frame;) {\n"
               "      if (!it->second.route_event.empty()) carried_.push_back(it->second.route_event);\n",
        "new": "  void DiscardOlderLocked(std::uint64_t frame) {\n"
               "    if (frame > taken_through_) taken_through_ = frame;\n"
               "    for (auto it = results_.begin(); it != results_.end() && it->first < frame;) {\n",
    },
    {
        "name": "P03 a render a take overtook drops its route event",
        "old": "        // Taken past while it rendered: never planned. Keep its route event.\n"
               "        if (!r.route_event.empty()) carried_.push_back(r.route_event);\n",
        "new": "        // Taken past while it rendered: never planned. Keep its route event.\n",
    },
    {
        "name": "P04 a full queue drops its newest request",
        "old": "        queue_.pop_front();\n        ++stats_.droppedQueue;\n",
        "new": "        queue_.pop_back();\n        ++stats_.droppedQueue;\n",
    },
    {
        "name": "P05 carried route events never handed to the take",
        "old": "      for (auto& e : carried_) carried->push_back(std::move(e));\n",
        "new": "",
    },
    {
        "name": "P06 requests accepted before Arm(true)",
        "old": "      if (!armed_ || stop_ || !worker_.joinable()) {\n",
        "new": "      if (stop_ || !worker_.joinable()) {\n",
    },
    {
        "name": "P07 the pose check ignores the yaw",
        "old": " && p.pitch == q.pitch && p.yaw == q.yaw;",
        "new": " && p.pitch == q.pitch;",
    },
    {
        "name": "P08 the use decision ignores the route",
        "old": "  if (drawn_route != route_now) return UseDecision::kRouteChanged;\n",
        "new": "  (void)drawn_route;\n  (void)route_now;\n",
    },
    {
        "name": "P09 the use decision ignores a failed render",
        "old": "  if (!render_ok) return UseDecision::kRenderFailed;\n",
        "new": "  (void)render_ok;\n",
    },
]


def main():
    source = open(HEADER, encoding="utf-8").read()
    failures = 0
    work = tempfile.mkdtemp(prefix="nav_prefetch_mut_")
    try:
        for entry in MUTATIONS:
            count = source.count(entry["old"])
            if count != 1:
                print(f"FAIL  {entry['name']}: fragment found {count} times, not once")
                failures += 1
                continue
            mutant_dir = os.path.join(work, entry["name"].split()[0])
            os.makedirs(mutant_dir)
            with open(os.path.join(mutant_dir, "nav_prefetch.h"), "w", encoding="utf-8") as f:
                f.write(source.replace(entry["old"], entry["new"], 1))
            binary = os.path.join(mutant_dir, "test")
            # The mutant's directory first: the test's #include "nav_prefetch.h" finds the copy.
            build = subprocess.run(["g++", *CXXFLAGS, "-I" + mutant_dir, "-I" + ROOT, TEST, "-o", binary],
                                   capture_output=True, text=True)
            if build.returncode != 0:
                print(f"FAIL  {entry['name']}: the mutant does not build\n{build.stderr[-600:]}")
                failures += 1
                continue
            try:
                run = subprocess.run([binary], capture_output=True, text=True, timeout=120)
                caught = run.returncode != 0
                tail = [line for line in run.stdout.splitlines() if line.startswith("FAIL")][:2]
            except subprocess.TimeoutExpired:
                caught, tail = True, ["timed out"]
            if caught:
                print(f"ok    {entry['name']} killed :: {'; '.join(tail)}")
            else:
                print(f"FAIL  {entry['name']} survived")
                failures += 1
    finally:
        shutil.rmtree(work, ignore_errors=True)
    print(f"NAV_PREFETCH_MUTATIONS {'PASS' if failures == 0 else 'FAIL'}: {len(MUTATIONS)} mutations, {failures} not killed")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
