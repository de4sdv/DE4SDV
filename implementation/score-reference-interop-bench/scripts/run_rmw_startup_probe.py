#!/usr/bin/env python3
"""Startup probe of the one-process adapter under ROS 2 middleware setups.

baselibs' abort override turns every throw in the adapter process into an
abort, also a throw that a ROS 2 middleware catches itself on its normal
path. Each case starts the vehicle-speed provider and the adapter (fault
hook off), optionally after or before other ROS 2 participants on the host
(scripts/ros_peer.py, one participant per process), holds, stops, turns a
core into a backtrace with the core's address mappings, and evaluates the
case against its expectation (de4sdv_score_bench.startup_probe):

- the bench environment (config/ros_environment.sh, rmw_cyclonedds_cpp with
  config/cyclonedds.xml) as first participant, after 11 others and before 11
  others; the last other participant counts the adapter's VelocityReports;
- a control of the participant index: the same configuration without
  MaxAutoParticipantIndex, so with the CycloneDDS default, after 11 others.
  It must fail, and it reports how many others got a participant;
- a control of ROS_LOCALHOST_ONLY: the bench environment with
  ROS_LOCALHOST_ONLY=1. rmw_cyclonedds_cpp then adds the address 127.0.0.1
  to the interface that cyclonedds.xml selects, and CycloneDDS refuses the
  same interface twice, so no participant is created.

The README records the results of the earlier Fast DDS cases.

Run in a shell with /opt/ros/humble/setup.bash and config/ros_environment.sh
sourced. Exit status 0 only when every case is as expected.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
from pathlib import Path
import sys
import time

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

import bench_runtime as rt  # noqa: E402
from de4sdv_score_bench.abort_matrix import EXECUTABLES  # noqa: E402
from de4sdv_score_bench.backtrace import (  # noqa: E402
    check_abort_top_frames,
    first_named_frame_below_override,
    frame_text,
    read_located_frames,
)
from de4sdv_score_bench.startup_probe import evaluate_case, summarize_probe  # noqa: E402

OTHER_PARTICIPANTS = 11

# The loopback configuration of config/cyclonedds.xml without
# MaxAutoParticipantIndex, so with the CycloneDDS default.
DEFAULT_INDEX_CONFIGURATION = (
    '<CycloneDDS xmlns="https://cdds.io/config"><Domain Id="any"><Discovery>'
    '<ParticipantIndex>auto</ParticipantIndex><Peers><Peer Address="localhost"/></Peers></Discovery>'
    '<General><Interfaces><NetworkInterface name="lo" priority="default" multicast="false"/></Interfaces>'
    '<AllowMulticast>false</AllowMulticast></General></Domain></CycloneDDS>'
)
SAME_INTERFACE_TWICE = "the same interface may not be selected twice"

# What a case changes in the bench environment.
BENCH_SETUP: dict[str, str] = {}
CYCLONEDDS_DEFAULT_INDEX = {"CYCLONEDDS_URI": DEFAULT_INDEX_CONFIGURATION}
CYCLONEDDS_WITH_LOCALHOST_ONLY = {"ROS_LOCALHOST_ONLY": "1"}


@dataclass(frozen=True)
class Case:
    name: str
    setup: dict[str, str]
    peers_before: int
    peers_after: int
    expected: str
    log_text: str | None = None


CASES = [
    Case("cyclonedds_bench_environment_first_participant", BENCH_SETUP, 0, 0, "runs"),
    Case("cyclonedds_bench_environment_after_11_participants", BENCH_SETUP, OTHER_PARTICIPANTS, 0, "runs"),
    Case("cyclonedds_bench_environment_before_11_participants", BENCH_SETUP, 0, OTHER_PARTICIPANTS, "runs"),
    Case("cyclonedds_default_participant_index_after_11_participants", CYCLONEDDS_DEFAULT_INDEX,
         OTHER_PARTICIPANTS, 0, "does_not_start"),
    Case("cyclonedds_bench_environment_with_ros_localhost_only", CYCLONEDDS_WITH_LOCALHOST_ONLY, 0, 0,
         "does_not_start", SAME_INTERFACE_TWICE),
]


def start_peers(count: int, first_number: int, run_dir: Path, env: dict[str, str], count_last: bool,
                peers: list[rt.BenchProcess]) -> int:
    """Starts count peers one after the other; returns how many got ready."""
    ready = 0
    for number in range(first_number, first_number + count):
        argv = [sys.executable, str(BENCH / "scripts" / "ros_peer.py"), "--name", f"de4sdv_probe_peer_{number}"]
        if count_last and number == first_number + count - 1:
            argv.append("--count-velocity")
        peer = rt.BenchProcess(f"peer_{number}", argv, run_dir / f"peer_{number}.log", env=env)
        peers.append(peer)
        if peer.wait_for(rt.json_event_predicate("peer_ready"), 20.0) and peer.alive():
            ready += 1
    return ready


def velocity_reports(peers: list[rt.BenchProcess]) -> int | None:
    for peer in peers:
        if "--count-velocity" not in peer.argv:
            continue
        for line in peer.log_text().splitlines():
            if '"event": "peer_stopped"' in line:
                return json.loads(line)["velocity_reports"]
        return 0
    return None


def run_case(args: argparse.Namespace, case: Case) -> dict:
    bundle = Path(args.bundle)
    run_dir = Path(args.out) / case.name
    run_dir.mkdir(parents=True, exist_ok=True)
    cleaned: list[str] = []
    rt.clean_lola_state(cleaned)
    env = rt.bench_environment(case.setup)
    provider = rt.BenchProcess(
        "provider",
        [str(bundle / "bin" / "vehicle_speed_provider"), "--service_instance_manifest",
         str(bundle / "config" / "mw_com_config_vehicle_speed_provider.json"), "--values", "36,72",
         "--period-ms", "100"],
        run_dir / "provider.log", env=env)
    provider.wait_for(rt.json_event_predicate("offered"), 20.0)
    peers: list[rt.BenchProcess] = []
    count_velocity = case.expected == "runs" and case.peers_before + case.peers_after >= OTHER_PARTICIPANTS
    peers_ready = start_peers(case.peers_before, 1, run_dir, env, count_velocity and case.peers_after == 0, peers)
    binary = bundle / "bin" / EXECUTABLES["adapter"]
    adapter = rt.BenchProcess("adapter", [str(binary), "--mw-com-config",
                                          str(bundle / "config" / "mw_com_config_adapter.json"),
                                          "--status-period-s", "5"],
                              run_dir / "adapter.log", env=rt.adapter_environment(bundle, env))
    ready = adapter.wait_for(rt.json_event_predicate("ready"), 25.0) and adapter.alive()
    if ready:
        peers_ready += start_peers(case.peers_after, case.peers_before + 1, run_dir, env,
                                   count_velocity and case.peers_after > 0, peers)
        deadline = time.monotonic() + args.hold_s
        while time.monotonic() < deadline and adapter.alive():
            time.sleep(0.5)
    survived = adapter.alive()
    end_returncode = adapter.returncode
    stop_returncode = adapter.stop(timeout_s=15.0) if survived else None
    for peer in reversed(peers):
        peer.stop(timeout_s=5.0)
    provider.stop(timeout_s=5.0)
    core = rt.find_core(Path(args.core_dir), adapter.pid)
    override_check_passed = None
    first_named = None
    if core is not None:
        backtrace, mappings = rt.gdb_backtrace(binary, core, run_dir, "adapter-core")
        frames = read_located_frames(backtrace, mappings)
        check = check_abort_top_frames(frames, binary.name)
        override_check_passed = check.passed
        named = first_named_frame_below_override(frames, check)
        first_named = frame_text(named) if named is not None else None
        core.unlink()
    record = {
        "case": case.name,
        "binary": binary.name,
        "expected": case.expected,
        "ros_environment": rt.environment_record(env),
        "peers_before": case.peers_before,
        "peers_after": case.peers_after if ready else 0,
        "peers_ready": peers_ready,
        "peer_velocity_reports": velocity_reports(peers),
        "ready": bool(ready),
        "survived_hold": bool(survived and ready),
        "end_returncode": end_returncode,
        "stop_returncode": stop_returncode,
        "core": core is not None,
        "override_check_passed": override_check_passed,
        "first_named_frame_below_override": first_named,
        "required_log_text": case.log_text,
        "required_log_text_found": None if case.log_text is None else case.log_text in adapter.log_text(),
    }
    evaluation = evaluate_case(record)
    rt.write_json(run_dir / "record.json", record)
    rt.write_json(run_dir / "result.json", evaluation)
    print(f"{case.name:58s} expected={case.expected} observed={evaluation['observed']} "
          f"as_expected={evaluation['as_expected']} peers_ready={peers_ready} {'; '.join(evaluation['reasons'])}",
          flush=True)
    return {"record": record, "evaluation": evaluation}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--core-dir", required=True)
    parser.add_argument("--hold-s", type=float, default=30.0)
    args = parser.parse_args()
    Path(args.out).mkdir(parents=True, exist_ok=True)
    runs = [run_case(args, case) for case in CASES]
    summary = summarize_probe([run["evaluation"] for run in runs])
    rt.write_json(Path(args.out) / "rmw-startup-probe.json", {"summary": summary, "cases": runs})
    lines = [
        "### Adapter startup under ROS 2 middleware setups (abort override linked)",
        "",
        f"Gate: **{summary['gate']}** ({summary['as_expected']} of {summary['cases']} cases as expected)",
        "",
        "| case | expected | observed | other participants ready | first named frame below the override "
        "| log text of the control | as expected |",
        "|---|---|---|---|---|---|---|",
    ]
    for run in runs:
        record, evaluation = run["record"], run["evaluation"]
        peers = record["peers_before"] + record["peers_after"]
        counted = record["peer_velocity_reports"]
        peers_text = f"{record['peers_ready']} of {peers}" + (f", {counted} VelocityReports counted"
                                                                if counted is not None else "")
        log_text = ("" if record["required_log_text"] is None
                    else f"{record['required_log_text']}: {'found' if record['required_log_text_found'] else 'missing'}")
        lines.append(f"| {record['case']} | {record['expected']} | {evaluation['observed']} | "
                     f"{peers_text} | {record['first_named_frame_below_override']} | {log_text} | "
                     f"{evaluation['as_expected']} |")
    (Path(args.out) / "rmw-startup-probe.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))
    return 0 if summary["gate"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
