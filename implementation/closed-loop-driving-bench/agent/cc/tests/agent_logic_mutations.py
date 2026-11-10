#!/usr/bin/env python3
"""Single-point mutation probes of the agent's requirement-linked rules.

Each entry changes exactly one rule of the library, rebuilds the C++ test, and
requires at least one test to fail. The source is restored after every probe and
its SHA-256 is compared with the pre-run value at the end.

    python3 mutations.py

Exit status 0 when every mutant is killed and the restored sources are intact.
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from pathlib import Path

# The unit lives in agent/cc/; this script and the tests in agent/cc/tests/.
HERE = Path(__file__).resolve().parents[1]
BENCH = Path(os.environ.get("DE4SDV_BENCH", str(Path(__file__).resolve().parents[3])))
INCLUDE = BENCH / "interfaces" / "include"
BUILD = HERE / ".build"
MUTANT_BIN = BUILD / "agent_logic_test_mutant"

# name, file, old text, new text, rule
MUTATIONS = [
    (
        "camera stale threshold 200 -> 300 ms",
        "agent_logic.h",
        "inline constexpr std::int64_t kCameraStaleMs = 200;",
        "inline constexpr std::int64_t kCameraStaleMs = 300;",
        "REQ-DRIVING-023",
    ),
    (
        "camera stale comparison > becomes >=",
        "agent_logic.cpp",
        "AgeMs(conditions.step_frame, camera.frame_index) > kCameraStaleMs",
        "AgeMs(conditions.step_frame, camera.frame_index) >= kCameraStaleMs",
        "REQ-DRIVING-023 (200 ms must not trigger)",
    ),
    (
        "motion stale threshold 200 -> 300 ms",
        "agent_logic.h",
        "inline constexpr std::int64_t kMotionStaleMs = 200;",
        "inline constexpr std::int64_t kMotionStaleMs = 300;",
        "REQ-DRIVING-024",
    ),
    (
        "motion finiteness drops yawRate",
        "agent_logic.cpp",
        "std::isfinite(sample.lateralAcceleration) &&\n                             std::isfinite(sample.yawRate);",
        "std::isfinite(sample.lateralAcceleration);",
        "REQ-DRIVING-024 (any non-finite field is invalid)",
    ),
    (
        "route stale threshold 1000 -> 900 ms",
        "agent_logic.h",
        "inline constexpr std::int64_t kRouteStaleMs = 1000;",
        "inline constexpr std::int64_t kRouteStaleMs = 900;",
        "REQ-DRIVING-025",
    ),
    (
        "plan stale threshold 300 -> 400 ms",
        "agent_logic.h",
        "inline constexpr std::int64_t kPlanStaleMs = 300;",
        "inline constexpr std::int64_t kPlanStaleMs = 400;",
        "REQ-DRIVING-026",
    ),
    (
        "plan age comparison > becomes >=",
        "agent_logic.cpp",
        "               AgeMs(step_frame, newest_valid_.frameIndex) > kPlanStaleMs) {",
        "               AgeMs(step_frame, newest_valid_.frameIndex) >= kPlanStaleMs) {",
        "REQ-DRIVING-026 (300 ms must not trigger)",
    ),
    (
        "plan validity accepts 63 pairs",
        "agent_logic.cpp",
        "if (plan.sampleCount != kPlanSamples) return false;",
        "if (plan.sampleCount > kPlanSamples) return false;",
        "REQ-DRIVING-027",
    ),
    (
        "plan validity drops the curvature check",
        "agent_logic.cpp",
        "!std::isfinite(plan.samples[i].curvature)) {",
        "false) {",
        "REQ-DRIVING-027 (both pairs finite)",
    ),
    (
        "lowest cause becomes highest cause",
        "agent_logic.cpp",
        "if (!found || static_cast<std::uint8_t>(cause) < static_cast<std::uint8_t>(lowest)) {",
        "if (!found || static_cast<std::uint8_t>(cause) > static_cast<std::uint8_t>(lowest)) {",
        "REQ-DRIVING-020..-027 (deterministic cause order)",
    ),
    (
        "first cause wins: the latch is overwritten",
        "agent_logic.cpp",
        "  if (cause_ != Cause::kNone) return;\n  if (cause == Cause::kNone) return;",
        "  if (cause == Cause::kNone) return;",
        "REQ-DRIVING-029 / ICD 3 (cause latches)",
    ),
    (
        "kStarting lets an input fault start the stop",
        "agent_logic.cpp",
        "    if (plan_valid && !conditions.Any()) mode_ = Mode::kDriving;",
        "    if (conditions.Any()) {\n      EnterStop(conditions.Lowest(), step_frame, monotonic_seconds);\n"
        "    } else if (plan_valid) {\n      mode_ = Mode::kDriving;\n    }",
        "REQ-DRIVING-023..-025 (priming faults do not stop)",
    ),
    (
        "stop deceleration -4 becomes -5 m/s^2",
        "agent_logic.h",
        "inline constexpr double kStopAccelerationMps2 = 4.0;",
        "inline constexpr double kStopAccelerationMps2 = 5.0;",
        "REQ-DRIVING-020",
    ),
    (
        "standstill threshold 0.1 -> 0.2 km/h",
        "agent_logic.h",
        "inline constexpr double kStandstillKmh = 0.1;",
        "inline constexpr double kStandstillKmh = 0.2;",
        "REQ-DRIVING-022",
    ),
    (
        "standstill comparison < becomes >",
        "agent_logic.cpp",
        "if (motion.has_sample && motion.sample.speed < kStandstillKmh) {",
        "if (motion.has_sample && motion.sample.speed > kStandstillKmh) {",
        "REQ-DRIVING-022",
    ),
    (
        "stop command drops the held steering",
        "agent_logic.cpp",
        "      static_cast<float>(has_held_steering_ ? held_steering_deg_ : 0.0);",
        "      static_cast<float>(0.0);",
        "REQ-DRIVING-021",
    ),
    (
        "sample index clamp floor 0 -> 1",
        "agent_logic.cpp",
        "  if (index < 0) return 0;",
        "  if (index < 0) return 1;",
        "REQ-DRIVING-026 (k = step - plan frame, clamped)",
    ),
    (
        "sample index clamp ceiling 63 -> 62",
        "agent_logic.cpp",
        "  if (index >= static_cast<std::int64_t>(kPlanSamples)) return kPlanSamples - 1;",
        "  if (index >= static_cast<std::int64_t>(kPlanSamples)) return kPlanSamples - 2;",
        "REQ-DRIVING-026 (k clamped to 63)",
    ),
    (
        "steering rate limit doubled",
        "agent_logic.cpp",
        "  const double max_step = config_.max_steering_rate_deg_per_s * kRateLimitStepSeconds;",
        "  const double max_step =\n      config_.max_steering_rate_deg_per_s * kRateLimitStepSeconds * 2.0;",
        "REQ-DRIVING-012",
    ),
    (
        "road-wheel angle clamp removed",
        "agent_logic.cpp",
        "  const double clamped = std::min(limit, std::max(-limit, raw_deg));",
        "  const double clamped = raw_deg + 0.0 * limit;  // clamp removed",
        "REQ-DRIVING-012",
    ),
    (
        "unknown command law accepted as first_control",
        "agent_logic.cpp",
        '  if (law_name == "first_control") {',
        '  if (law_name != "pure_pursuit") {',
        "REQ-DRIVING-012 (configured law)",
    ),
    (
        "kRefused is not permanent",
        "agent_logic.cpp",
        "    mode_ = Mode::kRefused;\n  } else if (mode_ == Mode::kStarting) {",
        "    mode_ = Mode::kStarting;\n  } else if (mode_ == Mode::kStarting) {",
        "REQ-DRIVING-035",
    ),
    # Added in the orchestrator's review (README, C2 and C3 resolved).
    (
        "stop command names the newest valid plan, not the held one",
        "agent_logic.cpp",
        "    // held and the plan it was computed from named.\n    EmitStopCommand(&out, monotonic_seconds);",
        "    // held and the plan it was computed from named.\n"
        "    if (newest_valid_plan != nullptr && has_held_steering_) {\n"
        "      held_plan_reference_ = PlanReferenceOf(*newest_valid_plan);\n"
        "      held_plan_frame_ = newest_valid_plan->frameIndex;\n"
        "    }\n"
        "    EmitStopCommand(&out, monotonic_seconds);",
        "REQ-DRIVING-011, VC-DRIVING-022 (reference frozen at the stop)",
    ),
    (
        "plan age judged before an invalid arrival",
        "agent_logic.cpp",
        "    } else if (plan_arrived && !plan_valid) {\n      stop = Cause::kPlanInvalid;\n"
        "    } else if (has_valid_plan_ &&\n               AgeMs(step_frame, newest_valid_.frameIndex) > kPlanStaleMs) {\n"
        "      stop = Cause::kPlanStale;\n    }",
        "    } else if (has_valid_plan_ &&\n               AgeMs(step_frame, newest_valid_.frameIndex) > kPlanStaleMs) {\n"
        "      stop = Cause::kPlanStale;\n"
        "    } else if (plan_arrived && !plan_valid) {\n      stop = Cause::kPlanInvalid;\n    }",
        "REQ-DRIVING-027, VC-DRIVING-027 (cause order)",
    ),
    (
        "an invalid plan outranks an input cause",
        "agent_logic.cpp",
        "    if (conditions.Any()) {\n      stop = conditions.Lowest();\n    } else if (plan_arrived && !plan_valid) {",
        "    if (plan_arrived && !plan_valid) {\n      stop = Cause::kPlanInvalid;\n"
        "    } else if (conditions.Any()) {\n      stop = conditions.Lowest();\n    } else if (plan_arrived && !plan_valid) {",
        "cause order (inputs first)",
    ),
    (
        "primed falls back to the step count when the engine did not condition the step",
        "agent_logic.cpp",
        "  if (engine) return conditioned && engine_primed;",
        "  if (engine && conditioned) return engine_primed;",
        "ICD A26 (priming.complete, VC-DRIVING-001)",
    ),
    (
        "primed ignores the engine's answer",
        "agent_logic.cpp",
        "  if (engine) return conditioned && engine_primed;",
        "  if (engine) return conditioned && (engine_primed || conditioned);",
        "ICD A26",
    ),
    (
        "the stand-in is primed one step early",
        "agent_logic.cpp",
        "frame - first_frame + 1 >= priming_frames;",
        "frame - first_frame + 2 >= priming_frames;",
        "ICD A26 (stand-in step count)",
    ),
    (
        "the stand-in step count wraps around before the first step",
        "agent_logic.cpp",
        "  return frame >= first_frame && frame - first_frame + 1 >= priming_frames;",
        "  return frame - first_frame + 1 >= priming_frames;",
        "ICD A26 (no wrap-around)",
    ),
    # The pure-pursuit anchor (ICD A31).
    (
        "pure pursuit takes sample k's position for the vehicle's",
        "agent_logic.cpp",
        "  const double y = static_cast<double>(plan.samples[target].y);\n",
        "  const double y = static_cast<double>(plan.samples[target].y) -\n"
        "                   static_cast<double>(plan.samples[k].y);\n",
        "ICD A31 (the plan's own frame)",
    ),
    (
        "pure pursuit turns the path into sample k's heading",
        "agent_logic.cpp",
        "  const double y = static_cast<double>(plan.samples[target].y);\n",
        "  const double y = static_cast<double>(plan.samples[target].y) -\n"
        "                   std::sin(static_cast<double>(plan.samples[k].heading)) * x;\n",
        "ICD A31 (the plan's own frame)",
    ),
    (
        "pure pursuit's target search starts at the first sample",
        "agent_logic.cpp",
        "  for (std::size_t index = static_cast<std::size_t>(k) + 1; index < kPlanSamples; ++index) {\n"
        "    const double x = static_cast<double>(plan.samples[index].x);",
        "  for (std::size_t index = 0; index < kPlanSamples; ++index) {\n"
        "    const double x = static_cast<double>(plan.samples[index].x);",
        "ICD A31 (target after sample k)",
    ),
]

BUILD_COMMAND = [
    "g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror",
    "-I", str(HERE), "-I", str(INCLUDE),
    str(HERE / "tests" / "agent_logic_test.cpp"),
    str(HERE / "agent_logic.cpp"), str(HERE / "json_lite.cpp"),
]


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path) -> tuple[bool, str]:
    result = subprocess.run(BUILD_COMMAND + ["-o", str(output)],
                            capture_output=True, text=True)
    return result.returncode == 0, (result.stderr or "")[-800:]


def main() -> int:
    BUILD.mkdir(exist_ok=True)
    sources = [HERE / "agent_logic.h", HERE / "agent_logic.cpp"]

    # A killed run leaves the mutated text next to its .orig file: restore it.
    for path in sources:
        backup = path.with_suffix(path.suffix + ".orig")
        if backup.exists():
            path.write_text(backup.read_text())
            backup.unlink()
            print(f"restored {path.name} from {backup.name} left by an interrupted run")

    pristine = {name: sha(HERE / name) for name in ("agent_logic.h", "agent_logic.cpp")}

    ok, error = build(BUILD / "agent_logic_test")
    if not ok:
        print("the pristine library does not build:\n" + error)
        return 2
    clean = subprocess.run([str(BUILD / "agent_logic_test")], capture_output=True, text=True)
    if clean.returncode != 0:
        print("the pristine tests fail:\n" + clean.stdout[-2000:])
        return 2
    print(f"pristine: {clean.stdout.strip().splitlines()[-1]}")

    rows = []
    for name, filename, old, new, rule in MUTATIONS:
        path = HERE / filename
        original = path.read_text()
        count = original.count(old)
        if count != 1:
            rows.append((name, f"{filename}:?", "NOT APPLIED", rule, f"{count} matches"))
            continue
        line = original[: original.index(old)].count("\n") + 1
        backup = path.with_suffix(path.suffix + ".orig")
        backup.write_text(original)
        path.write_text(original.replace(old, new, 1))
        try:
            compiled, build_error = build(MUTANT_BIN)
            if not compiled:
                rows.append((name, f"{filename}:{line}", "BUILD ERROR", rule, build_error))
                continue
            run = subprocess.run([str(MUTANT_BIN)], capture_output=True, text=True)
            summary = ""
            if run.stdout.strip():
                summary = run.stdout.strip().splitlines()[-1]
            rows.append((name, f"{filename}:{line}",
                         "killed" if run.returncode != 0 else "SURVIVED", rule, summary))
        finally:
            path.write_text(original)
            backup.unlink()

    restored = all(sha(HERE / name) == digest for name, digest in pristine.items())

    width = max(len(r[0]) for r in rows)
    print()
    print("| mutation" + " " * (width - 8) + " | file:line | result | rule |")
    print("|" + "-" * (width + 2) + "|---|" + "---|" + "---|")
    for name, where, result, rule, detail in rows:
        print(f"| {name:<{width}} | {where} | {result} | {rule} |")
    survivors = [r for r in rows if r[2] != "killed"]
    print()
    print(f"{len(rows)} mutations, {len(rows) - len(survivors)} killed, {len(survivors)} not killed")
    print(f"sources restored byte-identical: {restored}")
    if survivors:
        for name, where, result, rule, detail in survivors:
            print(f"  - {name} ({where}): {result} {detail}")
        return 1
    return 0 if restored else 1


if __name__ == "__main__":
    sys.exit(main())
