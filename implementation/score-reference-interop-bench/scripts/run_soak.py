#!/usr/bin/env python3
"""Nominal soak of the one-process adapter (brittleness check of the design).

With fresh LoLa state it starts, as the non-root bench user: someipd and
gatewayd of the S-CORE SOME/IP gateway on the host loopback (no guest; the
gateway configuration's frame event has gatewayd as its subscriber), the
synthetic frame source on 127.0.0.1:4721, the independent speed observer,
the vehicle-speed provider at 10 Hz with finite values, and the adapter with
the fault hook off. It keeps them running for --duration-s and checks every
10 s that each of them lives and that the adapter is the only client of the
frame stream (ss -tnp). Then it stops the adapter with SIGTERM (second
LoLa rule) and the rest, turns every core into a backtrace with the core's
address mappings, and evaluates the raw artifacts with
de4sdv_score_bench.soak.

Run in a shell with /opt/ros/humble/setup.bash and config/ros_environment.sh
sourced. Exit status 0 only for a pass.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import sys
import time

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

import bench_runtime as rt  # noqa: E402
from de4sdv_score_bench.soak import evaluate_soak  # noqa: E402

PROVIDER_VALUES = [0.0, 10.0, 36.0, 50.0, 72.0, 100.0, 130.0, 20.5]
LIVENESS_PERIOD_S = 10
SOMEIPD_STARTED = r"\[someipd\] mw::com IPC binding started"
GATEWAYD_CONNECTED = r"\[gatewayd\] Connected to someipd over the mw::com IPC binding"
GATEWAYD_SUBSCRIBED = r"\[gatewayd\] LocalServiceInstance created for instance specifier: de4sdv/aebs_signal_frame"
ADAPTER_NODE = "/de4sdv_score_adapter"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--core-dir", required=True)
    parser.add_argument("--duration-s", type=int, default=600)
    parser.add_argument("--frame-port", type=int, default=4721)
    parser.add_argument("--without-gateway", action="store_true")
    args = parser.parse_args()
    bundle = Path(args.bundle)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    config = bundle / "config"
    cleaned: list[str] = []
    rt.clean_lola_state(cleaned)
    rt.write_json(out / "lola_state_removed.json", cleaned)
    env = rt.bench_environment()
    gateway_env = dict(env, LD_LIBRARY_PATH=f"{bundle / 'lib'}:{env.get('LD_LIBRARY_PATH', '')}")
    notes: dict[str, object] = {"ros_environment": rt.environment_record(env), "provider_values_kmh": PROVIDER_VALUES}
    processes: list[rt.BenchProcess] = []

    def start(name: str, argv: list[str], process_env: dict[str, str]) -> rt.BenchProcess:
        process = rt.BenchProcess(name, argv, out / f"{name}.log", env=process_env)
        processes.append(process)
        return process

    gatewayd = None
    if not args.without_gateway:
        someipd = start("someipd", [str(bundle / "bin" / "someipd"), "-s", str(config / "mw_com_config_someipd.json")],
                        dict(gateway_env, VSOMEIP_CONFIGURATION=str(config / "vsomeip_loopback.json")))
        notes["someipd_started"] = someipd.wait_for(rt.regex_predicate(SOMEIPD_STARTED), 20.0)
        gatewayd = start("gatewayd", [str(bundle / "bin" / "gatewayd"), "-c", str(config / "someip_gateway_config.bin"),
                                      "-s", str(config / "mw_com_config_gatewayd.json")], gateway_env)
        notes["gatewayd_connected"] = gatewayd.wait_for(rt.regex_predicate(GATEWAYD_CONNECTED), 20.0)
    frames = start("frame_source", [sys.executable, str(BENCH / "scripts" / "synthetic_frame_source.py"),
                                    "--port", str(args.frame_port), "--log", str(out / "frames.jsonl")], env)
    frames.wait_for(rt.json_event_predicate("listening"), 10.0)
    observer = start("observer", [sys.executable, str(BENCH / "scripts" / "speed_observer.py"),
                                  "--out", str(out / "observer.jsonl")], env)
    observer.wait_for(rt.json_event_predicate("observer_ready"), 20.0)
    provider = start("provider", [str(bundle / "bin" / "vehicle_speed_provider"), "--service_instance_manifest",
                                  str(config / "mw_com_config_vehicle_speed_provider.json"),
                                  "--values", ",".join(str(value) for value in PROVIDER_VALUES),
                                  "--period-ms", "100", "--log", str(out / "provider.jsonl")], env)
    provider.wait_for(rt.json_event_predicate("offered"), 20.0)
    adapter_binary = bundle / "bin" / "de4sdv_score_adapter"
    adapter = start("adapter", [str(adapter_binary), "--mw-com-config", str(config / "mw_com_config_adapter.json"),
                                "--frame-port", str(args.frame_port), "--status-period-s", "60"],
                    rt.adapter_environment(bundle, env))
    ready = adapter.wait_for(rt.json_event_predicate("ready"), 30.0) and adapter.alive()
    ready_ns = rt.monotonic_ns() if ready else None
    gatewayd_subscribed = None
    if gatewayd is not None:
        gatewayd_subscribed = gatewayd.wait_for(rt.regex_predicate(GATEWAYD_SUBSCRIBED), 20.0)
    node_info_text = None
    if ready:
        # The adapter node's ROS 2 endpoints, seen by one more participant in
        # the same ROS 2 environment.
        node_info = rt.run_command(["ros2", "node", "info", "--no-daemon", "--spin-time", "5", ADAPTER_NODE], env,
                                   timeout_s=60.0)
        node_info_text = node_info["output"]
        rt.write_json(out / "adapter-node-info.json", node_info)
        (out / "adapter-node-info.txt").write_text(node_info_text, encoding="utf-8")

    checks = []
    if ready:
        deadline = time.monotonic() + args.duration_s
        while time.monotonic() < deadline:
            time.sleep(min(float(LIVENESS_PERIOD_S), max(0.0, deadline - time.monotonic())))
            # The frame assembler gives its stream to its newest client, so the
            # adapter must be its only client.
            checks.append({"monotonic_ns": rt.monotonic_ns(),
                           "alive": {process.name: process.alive() for process in processes},
                           "frame_stream_client_pids": rt.frame_stream_client_pids(args.frame_port)})
            if not adapter.alive():
                break
    stop_request_ns = rt.monotonic_ns()
    if adapter.alive():
        early_exit = None
        stop_returncode = adapter.stop(timeout_s=15.0)  # SIGTERM: the second LoLa rule
    else:
        early_exit = adapter.returncode
        stop_returncode = None
    for process in reversed(processes):
        if process is not adapter:
            notes[f"{process.name}_stop_returncode"] = process.stop(timeout_s=10.0)

    core_dir = Path(args.core_dir)
    core = rt.find_core(core_dir, adapter.pid)
    backtrace_text, mappings_text = (rt.gdb_backtrace(adapter_binary, core, out, "adapter-core") if core
                                     else (None, None))
    notes["other_cores"] = rt.backtrace_other_cores(core_dir, [p for p in processes if p is not adapter], out)
    run = {
        "planned_duration_s": args.duration_s,
        "adapter_ready_monotonic_ns": ready_ns,
        "stop_request_monotonic_ns": stop_request_ns,
        "early_exit_returncode": early_exit,
        "stop_returncode": stop_returncode,
        "adapter_core_files": [core.name] if core else [],
        "provider_values_kmh": PROVIDER_VALUES,
        "gateway": gatewayd is not None,
        "gatewayd_subscribed": gatewayd_subscribed,
        "liveness_period_s": LIVENESS_PERIOD_S,
        "liveness_checks": checks,
        "adapter_pid": adapter.pid,
    }
    rt.write_json(out / "soak-run.json", run)
    rt.write_json(out / "soak-notes.json", notes)

    def read(name: str) -> str:
        path = out / name
        return path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""

    result = evaluate_soak(run, adapter_log_text=read("adapter.log"), provider_log_text=read("provider.jsonl"),
                           observer_log_text=read("observer.jsonl"), frame_source_log_text=read("frames.jsonl"),
                           gatewayd_log_text=read("gatewayd.log"), node_info_text=node_info_text,
                           backtrace_text=backtrace_text, mappings_text=mappings_text)
    result["adapter_sha256"] = rt.sha256(adapter_binary)
    result["notes"] = notes
    rt.write_json(out / "soak-result.json", result)
    pairing = result["speed_pairing"] or {}
    environment = notes["ros_environment"]
    other_cores = "; ".join(
        f"{record['process']} ({record['returncode']}): {' <- '.join((record['named_top_frames'] or [])[:6])}"
        for record in notes["other_cores"]) or "none"
    lines = [
        f"### Adapter soak ({environment['RMW_IMPLEMENTATION']}, CYCLONEDDS_URI={environment['CYCLONEDDS_URI']}, "
        f"planned {args.duration_s} s)",
        "",
        f"Outcome: **{result['outcome']}** {'; '.join(result['reasons'])}",
        "",
        f"- soak {result['soak_s']} s; liveness checks {result['liveness_checks']}; published {result['published']}; "
        f"observed {result['observed_messages']}; paired {pairing.get('paired')}; unpaired {pairing.get('unpaired')}; "
        f"missing between paired {pairing.get('missing_between_paired')}; sent before the subscription "
        f"{pairing.get('sent_before_subscription')}; paired seq {pairing.get('first_paired_seq')} to "
        f"{pairing.get('last_paired_seq')}; latency ms {pairing.get('latency_ms')}",
        f"- frames: source {result['frame_source_frames']}, forwarded {result['frames_forwarded']}, sent "
        f"{result['frames_sent']}, bytes read {result['frame_bytes_read']}; allocate failures "
        f"{result['frames_allocate_failed']}; stream losses {result['frame_connection_losses']}; stream clients "
        f"{result['frame_stream_clients']}; gatewayd subscribed {gatewayd_subscribed}, gatewayd failures "
        f"{result['gatewayd_failures']}",
        f"- adapter node endpoints (ros2 node info): {result['adapter_endpoints']}",
        f"- RSS first/last {result['rss_kib_first']}/{result['rss_kib_last']} KiB; mw::log fallback "
        f"{result['mw_log_fallback']}; first named frame below the override {result['abort_caller']}",
        f"- cores of other processes: {other_cores}",
    ]
    (out / "soak-result.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if result["outcome"] == "passBoundedVerification" else 1


if __name__ == "__main__":
    raise SystemExit(main())
