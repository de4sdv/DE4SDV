#!/usr/bin/env python3
"""Startup probe of the one-process adapter under several ROS 2 middleware setups.

baselibs' abort override turns every throw in the adapter process into an
abort, also a throw that a ROS 2 middleware catches itself on its normal
path. This probe starts the adapter (fault hook off) with the
vehicle-speed provider running, once per case, optionally after another ROS 2
participant took the first ports, and records whether the adapter gets ready
and stops cleanly on SIGTERM, or aborts, with the backtrace of the abort:

- rmw_fastrtps_cpp with its default transports and ROS_LOCALHOST_ONLY=1, the
  bench configuration of the plan;
- rmw_fastrtps_cpp with a UDP-only loopback profile (no shared-memory
  transport), as first participant and after another one;
- rmw_cyclonedds_cpp with ROS_LOCALHOST_ONLY=1, as first participant and
  after another one.

A case passes when the adapter gets ready, stays up for --hold-s and exits
with 0 on SIGTERM. The probe reports; its exit status is always 0 unless the
runner itself fails.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

import bench_runtime as rt  # noqa: E402
from de4sdv_score_bench.backtrace import check_abort_top_frames, parse_gdb_backtrace  # noqa: E402

PROFILE = BENCH / "config" / "fastdds_udp_loopback_profile.xml"
CASES = [
    ("fastrtps_default_localhost_only", "rmw_fastrtps_cpp", True, None, False),
    ("fastrtps_udp_only_first_participant", "rmw_fastrtps_cpp", False, PROFILE, False),
    ("fastrtps_udp_only_after_another_participant", "rmw_fastrtps_cpp", False, PROFILE, True),
    ("cyclonedds_localhost_only_first_participant", "rmw_cyclonedds_cpp", True, None, False),
    ("cyclonedds_localhost_only_after_another_participant", "rmw_cyclonedds_cpp", True, None, True),
]


def thrower(backtrace_text: str) -> str | None:
    frames = parse_gdb_backtrace(backtrace_text)
    check = check_abort_top_frames(frames)
    if check.caller_frame is None:
        return None
    below = frames[frames.index(check.caller_frame):]
    named = next((frame for frame in below if frame.function != "??"), check.caller_frame)
    return f"{named.function} in {check.caller_frame.library or 'the adapter executable'}"


def run_case(args: argparse.Namespace, name: str, rmw: str, localhost_only: bool, profile: Path | None,
             prior: bool) -> dict:
    bundle = Path(args.bundle)
    run_dir = Path(args.out) / name
    run_dir.mkdir(parents=True, exist_ok=True)
    cleaned: list[str] = []
    rt.clean_lola_state(cleaned)
    extra = {"FASTRTPS_DEFAULT_PROFILES_FILE": str(profile)} if profile else None
    env = rt.ros_environment(rmw, localhost_only, extra)
    provider = rt.BenchProcess(
        "provider",
        [str(bundle / "bin" / "vehicle_speed_provider"), "--service_instance_manifest",
         str(bundle / "config" / "mw_com_config_vehicle_speed_provider.json"), "--values", "36,72",
         "--period-ms", "100"],
        run_dir / "provider.log", env=env)
    provider.wait_for(rt.json_event_predicate("offered"), 20.0)
    other = None
    if prior:
        other = rt.BenchProcess("other_participant",
                                ["ros2", "topic", "pub", "-r", "2", "/de4sdv_probe", "std_msgs/msg/String",
                                 "{data: probe}"], run_dir / "other_participant.log", env=env)
        time.sleep(6.0)
    binary = bundle / "bin" / "de4sdv_score_adapter"
    adapter = rt.BenchProcess("adapter", [str(binary), "--mw-com-config",
                                          str(bundle / "config" / "mw_com_config_adapter.json"),
                                          "--status-period-s", "5"], run_dir / "adapter.log", env=env)
    ready = adapter.wait_for(rt.json_event_predicate("ready"), 25.0) and adapter.alive()
    if ready:
        deadline = time.monotonic() + args.hold_s
        while time.monotonic() < deadline and adapter.alive():
            time.sleep(0.5)
    survived = adapter.alive()
    end_returncode = adapter.returncode
    stop_returncode = adapter.stop(timeout_s=15.0) if survived else None
    if other is not None:
        other.stop(timeout_s=5.0)
    provider.stop(timeout_s=5.0)
    core = rt.find_core(Path(args.core_dir), adapter.pid)
    abort_thrower = None
    if core is not None:
        abort_thrower = thrower(rt.gdb_backtrace(binary, core, run_dir, "adapter-core"))
        core.unlink()
    result = {
        "case": name,
        "rmw": rmw,
        "ros_localhost_only": localhost_only,
        "fastdds_profile": profile.name if profile else None,
        "another_participant_first": prior,
        "ready": bool(ready),
        "survived_hold_s": survived and bool(ready),
        "end_returncode_before_stop": end_returncode,
        "stop_returncode": stop_returncode,
        "abort_thrower": abort_thrower,
        "passed": bool(ready) and survived and stop_returncode == 0,
    }
    rt.write_json(run_dir / "result.json", result)
    print(f"{name:52s} ready={result['ready']} survived={result['survived_hold_s']} "
          f"stop={stop_returncode} end={end_returncode} thrower={abort_thrower}", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--core-dir", required=True)
    parser.add_argument("--hold-s", type=float, default=30.0)
    args = parser.parse_args()
    Path(args.out).mkdir(parents=True, exist_ok=True)
    results = [run_case(args, *case) for case in CASES]
    rt.write_json(Path(args.out) / "rmw-startup-probe.json", results)
    lines = ["### Adapter startup under ROS 2 middleware setups (abort override linked)", "",
             "| case | ready | stays up and stops with 0 | abort thrower |", "|---|---|---|---|"]
    for result in results:
        lines.append(f"| {result['case']} | {result['ready']} | {result['passed']} | {result['abort_thrower']} |")
    (Path(args.out) / "rmw-startup-probe.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
