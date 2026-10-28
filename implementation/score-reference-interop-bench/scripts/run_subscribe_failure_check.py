#!/usr/bin/env python3
"""Refused speed subscription of the one-process adapter (runtime check).

With fresh LoLa state it starts the vehicle-speed provider with a copy of
its mw::com configuration that offers 4 sample slots for the speed event,
fewer than the 5 the adapter subscribes with, so LoLa refuses the
subscription. Then it starts the adapter and waits until it ends, and
evaluates the end with de4sdv_score_bench.subscribe_failure.

Run in a shell with /opt/ros/humble/setup.bash and config/ros_environment.sh
sourced. Exit status 0 only for a pass.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

import bench_runtime as rt  # noqa: E402
from de4sdv_score_bench.subscribe_failure import evaluate_subscribe_failure  # noqa: E402

PROVIDER_SAMPLE_SLOTS = 4
ADAPTER_MAX_SAMPLES = 5


def provider_configuration(source: Path, target: Path) -> None:
    configuration = json.loads(source.read_text(encoding="utf-8"))
    events = [event for instance in configuration["serviceInstances"] for deployment in instance["instances"]
              for event in deployment.get("events", []) if event.get("eventName") == "vehicle_speed"]
    if len(events) != 1:
        raise SystemExit(f"{source} does not hold one vehicle_speed event")
    events[0]["numberOfSampleSlots"] = PROVIDER_SAMPLE_SLOTS
    target.write_text(json.dumps(configuration, indent=4) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--core-dir", required=True)
    args = parser.parse_args()
    bundle = Path(args.bundle)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    cleaned: list[str] = []
    rt.clean_lola_state(cleaned)
    env = rt.bench_environment()
    provider_config = out / "mw_com_config_vehicle_speed_provider_4_slots.json"
    provider_configuration(bundle / "config" / "mw_com_config_vehicle_speed_provider.json", provider_config)
    provider = rt.BenchProcess(
        "provider",
        [str(bundle / "bin" / "vehicle_speed_provider"), "--service_instance_manifest", str(provider_config),
         "--values", "36,72", "--period-ms", "100"],
        out / "provider.log", env=env)
    provider.wait_for(rt.json_event_predicate("offered"), 20.0)
    binary = bundle / "bin" / "de4sdv_score_adapter"
    adapter = rt.BenchProcess("adapter", [str(binary), "--mw-com-config",
                                          str(bundle / "config" / "mw_com_config_adapter.json")],
                              out / "adapter.log", env=rt.adapter_environment(bundle, env))
    ended_by_itself = adapter.wait_exit(30.0)
    returncode = adapter.returncode if ended_by_itself else adapter.stop(timeout_s=10.0)
    provider.stop(timeout_s=5.0)
    core = rt.find_core(Path(args.core_dir), adapter.pid)
    record = {
        "provider_sample_slots": PROVIDER_SAMPLE_SLOTS,
        "adapter_max_samples": ADAPTER_MAX_SAMPLES,
        "returncode": returncode,
        "ended_by_itself": ended_by_itself,
        "core": core is not None,
    }
    if core is not None:
        rt.gdb_backtrace(binary, core, out, "adapter-core")
    result = evaluate_subscribe_failure(record, adapter.log_text())
    result["record"] = record
    result["ros_environment"] = rt.environment_record(env)
    rt.write_json(out / "subscribe-failure.json", result)
    lines = [
        "### Refused speed subscription (provider offers 4 sample slots, the adapter asks for 5)",
        "",
        f"Outcome: **{result['outcome']}** {'; '.join(result['reasons'])}",
        "",
        f"- adapter ended by itself: {ended_by_itself}; exit code {returncode}; core {core is not None}",
    ]
    (out / "subscribe-failure.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if result["outcome"] == "passBoundedVerification" else 1


if __name__ == "__main__":
    raise SystemExit(main())
