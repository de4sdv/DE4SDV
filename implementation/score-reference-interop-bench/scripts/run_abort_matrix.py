#!/usr/bin/env python3
"""REQ-MW-018 abort matrix of the one-process adapter (rehearsal of VC-MW-019).

For each variant and for the adapter of record and the control build (the
same sources without baselibs' abort override), with fresh LoLa state:
start the vehicle-speed provider, start the adapter with the start
configuration of a member run and wait until it logs ready, send the
real-time signal that the adapter logged for the variant at start, record
how the process ends, turn the core into a gdb backtrace with the core's
address mappings, and evaluate the raw artifacts with
de4sdv_score_bench.abort_matrix.

Run in a shell with /opt/ros/humble/setup.bash and config/ros_environment.sh
sourced, as the non-root bench user, with kernel.core_pattern pointing into
--core-dir. Exit status 0 only when the gate passes: 3 of 3 variants of the
adapter of record end with SIGABRT at the override, and the control build
survives 3 of 3.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import time

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

import bench_runtime as rt  # noqa: E402
from de4sdv_score_bench.abort_matrix import VARIANTS, evaluate_variant, summarize_matrix  # noqa: E402

BINARIES = {"adapter": "de4sdv_score_adapter", "control": "de4sdv_score_adapter_no_abort_control"}


def logged_fault_signal(log_text: str, variant: str) -> int | None:
    """The signal that the adapter logged at start for the variant."""
    for line in log_text.splitlines():
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("event") == "start" and isinstance(event.get("fault_signals"), dict):
            value = event["fault_signals"].get(variant)
            return value if type(value) is int else None
    return None


def run_variant(args: argparse.Namespace, role: str, variant: str) -> dict:
    bundle = Path(args.bundle)
    run_dir = Path(args.out) / f"{role}-{variant}"
    run_dir.mkdir(parents=True, exist_ok=True)
    binary = bundle / "bin" / BINARIES[role]
    cleaned: list[str] = []
    rt.clean_lola_state(cleaned)
    env = rt.bench_environment()

    provider = rt.BenchProcess(
        "provider",
        [str(bundle / "bin" / "vehicle_speed_provider"), "--service_instance_manifest",
         str(bundle / "config" / "mw_com_config_vehicle_speed_provider.json"), "--values", "36,72,50",
         "--period-ms", "100", "--log", str(run_dir / "provider.jsonl")],
        run_dir / "provider.stdout.log", env=env)
    provider_offered = provider.wait_for(rt.json_event_predicate("offered"), 20.0)

    # The start configuration of a member run: no option and no variable
    # selects the fault; the signal does.
    adapter = rt.BenchProcess(
        role,
        [str(binary), "--mw-com-config", str(bundle / "config" / "mw_com_config_adapter.json"),
         "--frame-port", str(args.frame_port), "--status-period-s", "5"],
        run_dir / "adapter.log", env=rt.adapter_environment(bundle, env))
    ready = provider_offered and adapter.wait_for(rt.json_event_predicate("ready"), 30.0) and adapter.alive()
    signal_number = logged_fault_signal(adapter.log_text(), variant)
    sent_ns = None
    if ready and signal_number is not None:
        time.sleep(1.0)
        sent_ns = rt.monotonic_ns()
        os.kill(adapter.pid, signal_number)
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
    mappings_text = None
    if core is not None:
        backtrace_text, mappings_text = rt.gdb_backtrace(binary, core, run_dir, "adapter-core")
    record = {
        "role": role,
        "variant": variant,
        "ready_before_trigger": bool(ready),
        "trigger": {"signal": signal_number, "sent_monotonic_ns": sent_ns},
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
    result = evaluate_variant(record, backtrace_text, adapter.log_text(), mappings_text)
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
    parser.add_argument("--frame-port", type=int, default=4721)
    parser.add_argument("--roles", default="adapter,control")
    parser.add_argument("--keep-cores", action="store_true")
    args = parser.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    environment = rt.environment_record(rt.bench_environment())

    results = []
    for role in args.roles.split(","):
        for variant in VARIANTS:
            results.append(run_variant(args, role, variant))
    summary = summarize_matrix(results)
    adapter_binary = Path(args.bundle) / "bin" / BINARIES["adapter"]
    summary["ros_environment"] = environment
    summary["nm_dynamic_cxa_allocate_exception"] = rt.nm_dynamic_line(adapter_binary, "__cxa_allocate_exception")
    summary["adapter_sha256"] = rt.sha256(adapter_binary)
    control_binary = Path(args.bundle) / "bin" / BINARIES["control"]
    if control_binary.exists():
        summary["control_sha256"] = rt.sha256(control_binary)
    summary["results"] = results
    rt.write_json(out / "abort-matrix-summary.json", summary)
    lines = [
        f"### REQ-MW-018 abort matrix ({environment['RMW_IMPLEMENTATION']}, "
        f"CYCLONEDDS_URI={environment['CYCLONEDDS_URI']}, ROS_DOMAIN_ID={environment['ROS_DOMAIN_ID']})",
        "",
        f"Gate: **{summary['gate']}**. Adapter of record ends with SIGABRT at the override: "
        f"**{summary['adapter_sigabrt_at_override']}**; control build survives: **{summary['control_survived']}**; "
        f"discriminates: {summary['discriminates']}. {'; '.join(summary['gate_problems'])}",
        "",
        f"`nm -D`: `{summary['nm_dynamic_cxa_allocate_exception']}`",
        "",
        "| role | variant | outcome | signal | top frames | caller below the override | first named frame below the override |",
        "|---|---|---|---|---|---|---|",
    ]
    for result in results:
        lines.append(f"| {result['role']} | {result['variant']} | {result['outcome']} | {result['signal']} | "
                     f"{' ← '.join(result['top_frames'][:2])} | {result['caller']} | "
                     f"{result['first_named_frame']} |")
    (out / "abort-matrix-summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if summary["gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
