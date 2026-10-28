#!/usr/bin/env python3
"""REQ-MW-018 abort matrix of the one-process adapter (rehearsal of VC-MW-019).

For each variant and for the adapter of record and the control build (the
same sources without baselibs' abort override), with fresh LoLa state:
start the vehicle-speed provider, start the adapter and wait until it logs
ready, deliver the trigger with ``ros2 param set``, record how the process
ends, turn the core into a gdb backtrace, and evaluate the raw artifacts with
de4sdv_score_bench.abort_matrix. The fault hook is off for the rclcpp
variant and on (DE4SDV_ADAPTER_FAULT_HOOK=1) for the two hook variants.

Run in a shell with /opt/ros/humble sourced, as the non-root bench user,
with kernel.core_pattern pointing into --core-dir. Exit status 0 only when
the gate passes: 3 of 3 variants of the adapter of record end with SIGABRT at
the override.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

import bench_runtime as rt  # noqa: E402
from de4sdv_score_bench.abort_matrix import HOOK_VARIANTS, VARIANTS, evaluate_variant, summarize_matrix  # noqa: E402

NODE = "/de4sdv_score_adapter"
TRIGGERS = {
    "rclcpp_internal": ("de4sdv_undeclared_parameter", "1"),
    "adapter_code": ("de4sdv_fault_hook", "adapter_code"),
    "libstdcxx": ("de4sdv_fault_hook", "libstdcxx"),
}
BINARIES = {"adapter": "de4sdv_score_adapter", "control": "de4sdv_score_adapter_no_abort_control"}


def run_variant(args: argparse.Namespace, role: str, variant: str) -> dict:
    bundle = Path(args.bundle)
    run_dir = Path(args.out) / f"{role}-{variant}"
    run_dir.mkdir(parents=True, exist_ok=True)
    binary = bundle / "bin" / BINARIES[role]
    cleaned: list[str] = []
    rt.clean_lola_state(cleaned)
    hook = variant in HOOK_VARIANTS
    env = rt.ros_environment(args.rmw, args.localhost_only, {"DE4SDV_ADAPTER_FAULT_HOOK": "1"} if hook else None)

    provider = rt.BenchProcess(
        "provider",
        [str(bundle / "bin" / "vehicle_speed_provider"), "--service_instance_manifest",
         str(bundle / "config" / "mw_com_config_vehicle_speed_provider.json"), "--values", "36,72,50",
         "--period-ms", "100", "--log", str(run_dir / "provider.jsonl")],
        run_dir / "provider.stdout.log", env=env)
    provider_offered = provider.wait_for(rt.json_event_predicate("offered"), 20.0)

    adapter = rt.BenchProcess(
        role,
        [str(binary), "--mw-com-config", str(bundle / "config" / "mw_com_config_adapter.json"),
         "--frame-port", str(args.frame_port), "--status-period-s", "5"],
        run_dir / "adapter.log", env=env)
    ready = provider_offered and adapter.wait_for(rt.json_event_predicate("ready"), 30.0) and adapter.alive()
    if ready:
        time.sleep(2.0)  # ROS 2 discovery of the node by the CLI
    parameter, value = TRIGGERS[variant]
    trigger_env = rt.ros_environment(args.rmw, args.localhost_only)
    trigger = rt.run_command(
        ["ros2", "param", "set", "--no-daemon", "--spin-time", "5", NODE, parameter, value], trigger_env,
        timeout_s=40.0) if ready else {
            "argv": [], "start_monotonic_ns": rt.monotonic_ns(), "end_monotonic_ns": rt.monotonic_ns(),
            "returncode": None, "timed_out": False, "output": "not run: the adapter was not ready"}
    if role == "adapter":
        adapter.wait_exit(15.0)
    else:
        time.sleep(3.0)
    alive_at_check = adapter.alive()
    returncode_at_check = adapter.returncode
    exit_ns = adapter.exit_monotonic_ns
    stop_returncode = adapter.stop(timeout_s=10.0) if alive_at_check else None
    provider.stop(timeout_s=5.0)

    core = rt.find_core(Path(args.core_dir), adapter.pid)
    backtrace_text = None
    if core is not None:
        backtrace_text = rt.gdb_backtrace(binary, core, run_dir, "adapter-core")
    record = {
        "role": role,
        "variant": variant,
        "fault_hook_environment": "1" if hook else "unset",
        "ready_before_trigger": bool(ready),
        "trigger": trigger,
        "process": {
            "returncode": returncode_at_check,
            "exit_monotonic_ns": exit_ns,
            "alive_at_check": alive_at_check,
            "stop_returncode": stop_returncode,
        },
        "core_file": core.name if core else None,
        "core_bytes": core.stat().st_size if core else None,
    }
    rt.write_json(run_dir / "record.json", record)
    rt.write_json(run_dir / "lola_state_removed.json", cleaned)
    result = evaluate_variant(record, backtrace_text, adapter.log_text())
    rt.write_json(run_dir / "result.json", result)
    if core is not None and not args.keep_cores:
        core.unlink()
    print(f"{role:8s} {variant:16s} {result['outcome']:28s} signal={result['signal']} "
          f"top={result['top_frames'][:2]} caller={result['caller']} {'; '.join(result['reasons'])}", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True, help="runtime bundle of the build job")
    parser.add_argument("--out", required=True)
    parser.add_argument("--core-dir", required=True)
    parser.add_argument("--rmw", default="rmw_cyclonedds_cpp")
    parser.add_argument("--localhost-only", type=int, choices=(0, 1), default=1)
    parser.add_argument("--frame-port", type=int, default=4721)
    parser.add_argument("--roles", default="adapter,control")
    parser.add_argument("--keep-cores", action="store_true")
    args = parser.parse_args()
    args.localhost_only = bool(args.localhost_only)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    results = []
    for role in args.roles.split(","):
        for variant in VARIANTS:
            results.append(run_variant(args, role, variant))
    summary = summarize_matrix(results)
    adapter_binary = Path(args.bundle) / "bin" / BINARIES["adapter"]
    summary["rmw"] = args.rmw
    summary["ros_localhost_only"] = args.localhost_only
    summary["nm_dynamic_cxa_allocate_exception"] = rt.nm_dynamic_line(adapter_binary, "__cxa_allocate_exception")
    summary["adapter_sha256"] = rt.sha256(adapter_binary)
    control_binary = Path(args.bundle) / "bin" / BINARIES["control"]
    if control_binary.exists():
        summary["control_sha256"] = rt.sha256(control_binary)
    summary["results"] = results
    rt.write_json(out / "abort-matrix-summary.json", summary)
    lines = [
        f"### REQ-MW-018 abort matrix ({args.rmw}, ROS_LOCALHOST_ONLY={int(args.localhost_only)})",
        "",
        f"Adapter of record ends with SIGABRT at the override: **{summary['adapter_sigabrt_at_override']}**; "
        f"control build survives: {summary['control_survived']}; discriminates: {summary['discriminates']}.",
        "",
        f"`nm -D`: `{summary['nm_dynamic_cxa_allocate_exception']}`",
        "",
        "| role | variant | outcome | signal | top frames | thrower |",
        "|---|---|---|---|---|---|",
    ]
    for result in results:
        lines.append(f"| {result['role']} | {result['variant']} | {result['outcome']} | {result['signal']} | "
                     f"{' ← '.join(result['top_frames'][:2])} | {result['caller']} |")
    (out / "abort-matrix-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if summary["gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
