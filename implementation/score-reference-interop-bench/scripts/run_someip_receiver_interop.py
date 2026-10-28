#!/usr/bin/env python3
"""The DE4SDV SOME/IP receiver against the real someipd, in two network namespaces (P0.3).

The "host" namespace holds someipd (vsomeip 3.6.1, service discovery on,
unicast 10.250.0.1), gatewayd, the AutowareToSCORE adapter and the bench's
VisualizationFrame source on 127.0.0.1:4721. The "guest" namespace holds
the receiver and a loopback client on 127.0.0.1:4731, with a private /tmp
and /dev/shm, so the veth pair is the only path between the two. Both
namespaces have a route for 224.0.0.0/4 on their veth end.

Run as root: it creates the namespaces and the captures, and starts every
bench process inside a namespace as the bench user (setpriv), so that LoLa
runs without root and its shared memory belongs to that user. It records
which LoLa shared memory files someipd, gatewayd and the adapter map.

Cases (each with a fresh stack, a capture of the link on the host end and
raw records in <out>/<case>/):
- identity: 200 frames with the receiver subscribed and the client
  connected first;
- resubscribe: frames at 10 Hz across a receiver restart by SIGTERM, one
  by SIGKILL, a restart of the gateway pair (gatewayd killed, someipd
  stopped, both started again, the adapter kept) and a link outage of the
  guest end longer than the subscription TTL;
- no_client: frames while no client is connected, then the client;
- stored_samples: in the order of the stored-sample cases of the gateway
  spike, with the source paused at each step so that the newest frames stay
  in the sample slots: frames into the adapter, then gatewayd and the
  subscription, then the source again (frames from before the phase arrive
  in the phase); then gatewayd restarted beside the running someipd in the
  phase, a stimulus outside the operating rules (stored frames repeat served
  frames); then a restart of the gateway pair (stored frames from before the
  new phase);
- ttl_renewal: the unicast fallback only (no multicast membership) over
  five TTLs.

It evaluates every case with de4sdv_score_bench.someip_receiver_interop
and exits with 0 only when every gate case passes.
"""

from __future__ import annotations

import argparse
from collections import Counter
import glob
import json
import os
from pathlib import Path
import pwd
import shutil
import signal
import subprocess
import sys
import time

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))
sys.path.insert(0, str(BENCH / "scripts"))

import bench_runtime as rt  # noqa: E402
from de4sdv_score_bench.abort_matrix import MISSING, PASS  # noqa: E402
from de4sdv_score_bench.someip_receiver_interop import ANNOUNCED_PROPERTIES, EVALUATORS, load_case  # noqa: E402

HOST_NS = "de4sdv-host"
GUEST_NS = "de4sdv-guest"
HOST_IF = "veth-h"
GUEST_IF = "veth-g"
HOST_IP = "10.250.0.1"
GUEST_IP = "10.250.0.2"
MULTICAST_ROUTE = "224.0.0.0/4"
FRAME_PORT = 4721
LOOPBACK_PORT = 4731
SUBSCRIPTION_TTL_S = 3
LINK_OUTAGE_S = 5.0

SOMEIPD_STARTED = r"\[someipd\] mw::com IPC binding started"
SOMEIPD_OFFERED = r"OFFER\(0100\): \[4dee\.0001"
GATEWAYD_CONNECTED = r"\[gatewayd\] Connected to someipd over the mw::com IPC binding"
GATEWAYD_FOUND = r"LocalServiceInstance created for instance specifier: de4sdv/aebs_signal_frame"
GATE_CASES = ("identity", "resubscribe", "no_client", "ttl_renewal")
MEASUREMENT_CASES = ("stored_samples",)


def run(argv: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(argv, check=check, capture_output=True, text=True)


def netns_down() -> None:
    for namespace in (HOST_NS, GUEST_NS):
        run(["ip", "netns", "del", namespace], check=False)


def netns_up(out: Path) -> dict:
    netns_down()
    for step in (
        ["ip", "netns", "add", HOST_NS],
        ["ip", "netns", "add", GUEST_NS],
        ["ip", "link", "add", HOST_IF, "type", "veth", "peer", "name", GUEST_IF],
        ["ip", "link", "set", HOST_IF, "netns", HOST_NS],
        ["ip", "link", "set", GUEST_IF, "netns", GUEST_NS],
        ["ip", "-n", HOST_NS, "addr", "add", f"{HOST_IP}/24", "dev", HOST_IF],
        ["ip", "-n", GUEST_NS, "addr", "add", f"{GUEST_IP}/24", "dev", GUEST_IF],
        ["ip", "-n", HOST_NS, "link", "set", "lo", "up"],
        ["ip", "-n", GUEST_NS, "link", "set", "lo", "up"],
        ["ip", "-n", HOST_NS, "link", "set", HOST_IF, "up"],
        ["ip", "-n", GUEST_NS, "link", "set", GUEST_IF, "up"],
        # vsomeip offers only once the SD multicast group has a route.
        ["ip", "-n", HOST_NS, "route", "add", MULTICAST_ROUTE, "dev", HOST_IF],
        ["ip", "-n", GUEST_NS, "route", "add", MULTICAST_ROUTE, "dev", GUEST_IF],
    ):
        run(step)
    facts = {namespace: {"addr": run(["ip", "-n", namespace, "addr"]).stdout,
                         "route": run(["ip", "-n", namespace, "route"]).stdout}
             for namespace in (HOST_NS, GUEST_NS)}
    facts["ping_guest_to_host"] = run(["ip", "netns", "exec", GUEST_NS, "ping", "-c", "2", "-W", "2", HOST_IP],
                                      check=False).stdout
    rt.write_json(out / "netns.json", facts)
    return facts


class Stack:
    """The processes of one case, its records and its timeline."""

    def __init__(self, case: str, root: Path, args: argparse.Namespace, user: pwd.struct_passwd,
                 base_env: dict[str, str]) -> None:
        self.case = case
        self.out = root / case
        self.out.mkdir(parents=True, exist_ok=True)
        os.chown(self.out, user.pw_uid, user.pw_gid)
        self.args = args
        self.user = user
        self.bundle = Path(args.bundle)
        self.config = self.bundle / "config"
        self.base_env = base_env
        self.processes: dict[str, rt.BenchProcess] = {}
        self.order: list[str] = []
        self.timeline: dict = {"case": case, "events": [], "disturbances": [], "processes": {},
                               "receiver_logs": [], "gatewayd_logs": [], "parameters": {
                                   "subscription_ttl_s": SUBSCRIPTION_TTL_S, "phase_start_margin_ms": 20,
                                   "frame_port": FRAME_PORT, "loopback_port": LOOPBACK_PORT,
                                   "host_ip": HOST_IP, "guest_ip": GUEST_IP,
                                   "clocks": "both namespaces share the clock of one kernel"}}
        self.receiver_count = 0
        self.go_file = self.out / "go"
        self.pause_file = self.out / "pause"

    # -- timeline
    def note(self, what: str, **fields) -> dict:
        event = {"what": what, "monotonic_ns": time.monotonic_ns(), "realtime_ns": time.time_ns(), **fields}
        self.timeline["events"].append(event)
        print(f"[{self.case}] {what} {fields if fields else ''}", flush=True)
        return event

    # -- processes
    def _prefix(self, namespace: str, private_tmp: bool) -> list[str]:
        drop = ["setpriv", f"--reuid={self.user.pw_uid}", f"--regid={self.user.pw_gid}", "--init-groups", "--"]
        if not private_tmp:
            return ["ip", "netns", "exec", namespace] + drop
        script = ("mount -t tmpfs tmpfs /tmp && mount -t tmpfs tmpfs /dev/shm && exec " +
                  " ".join(drop) + ' "$@"')
        return ["ip", "netns", "exec", namespace, "unshare", "--mount", "--propagation", "private", "--",
                "sh", "-c", script, "sh"]

    def start(self, name: str, namespace: str, argv: list[str], env: dict[str, str] | None = None,
              private_tmp: bool = False, as_root: bool = False) -> rt.BenchProcess:
        prefix = ["ip", "netns", "exec", namespace] if as_root else self._prefix(namespace, private_tmp)
        process = rt.BenchProcess(name, prefix + argv, self.out / f"{name}.log", env=env or self.base_env)
        self.processes[name] = process
        self.order.append(name)
        self.timeline["processes"][name] = {"argv": argv, "namespace": namespace, "pid": process.pid,
                                            "start_monotonic_ns": process.start_monotonic_ns,
                                            "start_realtime_ns": time.time_ns(),
                                            "user": "root" if as_root else self.user.pw_name,
                                            "private_tmp": private_tmp}
        self.note(f"start {name}", pid=process.pid)
        return process

    def stop(self, name: str, sig: int = signal.SIGTERM, timeout_s: float = 10.0) -> int | None:
        process = self.processes[name]
        record = self.timeline["processes"][name]
        if "returncode" in record:
            return record["returncode"]
        self.note(f"stop {name}", signal=signal.Signals(sig).name)
        returncode = process.stop(timeout_s=timeout_s, sig=sig)
        record["returncode"] = returncode
        record["exit_monotonic_ns"] = process.exit_monotonic_ns
        return returncode

    def wait(self, name: str, pattern: str, timeout_s: float, json_event: bool = False) -> bool:
        predicate = rt.json_event_predicate(pattern) if json_event else rt.regex_predicate(pattern)
        ok = self.processes[name].wait_for(predicate, timeout_s)
        self.note(f"wait {name} {pattern}", ok=ok)
        return ok

    def wait_count(self, name: str, needle: str, count: int, timeout_s: float) -> bool:
        deadline = time.monotonic() + timeout_s
        process = self.processes[name]
        while time.monotonic() < deadline:
            if process.log_text().count(needle) >= count:
                self.note(f"wait {name} {needle} x{count}", ok=True)
                return True
            time.sleep(0.05)
        self.note(f"wait {name} {needle} x{count}", ok=False)
        return False

    # -- components
    def gateway_env(self) -> dict[str, str]:
        return dict(self.base_env, LD_LIBRARY_PATH=f"{self.bundle / 'lib'}:{self.base_env.get('LD_LIBRARY_PATH', '')}")

    def start_capture(self) -> None:
        pcap = self.out / "link.pcap"
        self.start("tcpdump", HOST_NS, ["tcpdump", "-i", HOST_IF, "-U", "-s", "0", "-Z", "root",
                                        "--time-stamp-precision=nano", "-w", str(pcap)], as_root=True)
        self.wait("tcpdump", r"listening on", 10.0)

    def start_someipd(self, name: str = "someipd") -> None:
        env = dict(self.gateway_env(), VSOMEIP_CONFIGURATION=str(BENCH / "config" / "vsomeip_netns_host.json"))
        self.start(name, HOST_NS, [str(self.bundle / "bin" / "someipd"), "-s",
                                   str(self.config / "mw_com_config_someipd.json")], env=env)
        self.wait(name, SOMEIPD_STARTED, 20.0)

    def start_gatewayd(self, name: str = "gatewayd", someipd: str = "someipd") -> None:
        self.start(name, HOST_NS, [str(self.bundle / "bin" / "gatewayd"), "-c",
                                   str(self.config / "someip_gateway_config.bin"), "-s",
                                   str(self.config / "mw_com_config_gatewayd.json")], env=self.gateway_env())
        self.timeline["gatewayd_logs"].append(f"{name}.log")
        self.wait(name, GATEWAYD_CONNECTED, 20.0)
        self.wait(someipd, SOMEIPD_OFFERED, 20.0)

    def start_source(self, frames: int) -> None:
        self.start("frame_source", HOST_NS, [sys.executable, str(BENCH / "scripts" / "visualization_frame_source.py"),
                                             "--port", str(FRAME_PORT), "--frames", str(frames), "--period-ms", "100",
                                             "--go-file", str(self.go_file), "--pause-file", str(self.pause_file),
                                             "--log", str(self.out / "source.jsonl"), "--stream-dir", str(self.out)])
        self.wait("frame_source", "listening", 10.0, json_event=True)

    def ros_env(self) -> dict[str, str]:
        # The bench user's environment with ROS 2 sourced, one middleware, loopback only.
        env = dict(self.base_env, RMW_IMPLEMENTATION=self.args.rmw, ROS_LOCALHOST_ONLY="1",
                   ROS_DOMAIN_ID=self.base_env.get("ROS_DOMAIN_ID", "42"), RCUTILS_LOGGING_BUFFERED_STREAM="0")
        for key in ("FASTRTPS_DEFAULT_PROFILES_FILE", "DE4SDV_ADAPTER_FAULT_HOOK"):
            env.pop(key, None)
        return env

    def start_adapter(self) -> None:
        env = self.ros_env()
        self.start("adapter", HOST_NS, [str(self.bundle / "bin" / "de4sdv_score_adapter"), "--mw-com-config",
                                        str(self.config / "mw_com_config_adapter.json"), "--frame-port",
                                        str(FRAME_PORT), "--status-period-s", "10"], env=env)
        self.wait("adapter", "frame_offered", 30.0, json_event=True)
        self.wait("adapter", "frame_stream_connected", 10.0, json_event=True)

    def start_receiver(self, multicast: bool = True) -> str:
        self.receiver_count += 1
        name = f"receiver-{self.receiver_count}"
        argv = [str(Path(self.args.receiver)), "--server-address", HOST_IP,
                "--ttl-s", str(SUBSCRIPTION_TTL_S), "--listen-port", str(LOOPBACK_PORT), "--status-period-s", "1",
                "--log-frames"]
        for property_name, value in ANNOUNCED_PROPERTIES:
            argv += ["--announce-property", f"{property_name}={value}"]
        if not multicast:
            argv.append("--no-multicast")
        self.start(name, GUEST_NS, argv, private_tmp=True)
        self.timeline["receiver_logs"].append(f"{name}.log")
        self.wait(name, "start", 10.0, json_event=True)
        return name

    def start_recorder(self) -> None:
        self.start("recorder", GUEST_NS, [sys.executable, str(BENCH / "scripts" / "loopback_frame_recorder.py"),
                                          "--port", str(LOOPBACK_PORT), "--log", str(self.out / "recorder.jsonl"),
                                          "--stream-dir", str(self.out), "--reconnect"], private_tmp=True)

    def subscribed_count(self, receiver: str) -> int:
        return self.processes[receiver].log_text().count('"event":"subscribed"')

    def go(self) -> None:
        self.go_file.write_text("")
        self.note("go")

    def pause(self) -> None:
        self.pause_file.write_text("")
        self.note("pause source")
        time.sleep(0.3)  # the frame in flight passes

    def resume(self) -> None:
        self.pause_file.unlink(missing_ok=True)
        self.note("resume source")

    def disturbance(self, kind: str, start: dict, expects_resubscription: bool = True, **fields) -> None:
        self.timeline["disturbances"].append({"kind": kind, "start_realtime_ns": start["realtime_ns"],
                                              "end_realtime_ns": time.time_ns(),
                                              "expects_resubscription": expects_resubscription, **fields})

    # -- shared memory
    def shared_memory_snapshot(self) -> None:
        maps: dict[str, list[str]] = {}
        for name in ("someipd", "gatewayd", "adapter"):
            process = self.processes.get(name)
            paths: set[str] = set()
            if process is not None and process.alive():
                try:
                    for line in Path(f"/proc/{process.pid}/maps").read_text().splitlines():
                        parts = line.split(maxsplit=5)
                        if len(parts) == 6 and parts[5].startswith("/dev/shm/"):
                            paths.add(parts[5].replace(" (deleted)", ""))
                except OSError as error:
                    paths.add(f"unreadable: {error}")
            maps[name] = sorted(paths)
        entries = []
        foreign = []
        for path in sorted(glob.glob("/dev/shm/*")):
            info = os.lstat(path)
            entries.append({"path": path, "uid": info.st_uid, "bytes": info.st_size})
            if "lola" in os.path.basename(path) and info.st_uid != self.user.pw_uid:
                foreign.append(path)
        snapshot = {
            "maps": maps,
            "shared_pairs": {
                "adapter-gatewayd": sorted(set(maps["adapter"]) & set(maps["gatewayd"])),
                "gatewayd-someipd": sorted(set(maps["gatewayd"]) & set(maps["someipd"])),
            },
            "dev_shm": entries,
            "foreign_owned_files": foreign,
            "bench_uid": self.user.pw_uid,
        }
        rt.write_json(self.out / "shared-memory.json", snapshot)
        self.note("shared memory snapshot", pairs={k: len(v) for k, v in snapshot["shared_pairs"].items()})

    # -- lifecycle
    def clean_lola_state(self) -> list[str]:
        removed = []
        for pattern in ("/dev/shm/lola-*", "/tmp/mw_com_lola", "/tmp/vsomeip*", "/tmp/de4sdvnetns*"):
            for path in glob.glob(pattern):
                try:
                    if os.path.isdir(path) and not os.path.islink(path):
                        shutil.rmtree(path)
                    else:
                        os.unlink(path)
                    removed.append(path)
                except OSError as error:
                    removed.append(f"{path}: {error}")
        return removed

    def stop_all(self) -> None:
        self.timeline["stop_realtime_ns"] = time.time_ns()
        self.note("stop all")
        for name in ("frame_source",):
            if name in self.processes:
                self.stop(name)
        time.sleep(1.0)
        for name in reversed(self.order):
            if name.startswith("receiver-"):
                self.stop(name, timeout_s=10.0)
        time.sleep(0.5)
        for name in reversed(self.order):
            if name == "tcpdump":
                continue
            self.stop(name, timeout_s=15.0)
        if "tcpdump" in self.processes:
            time.sleep(0.5)
            self.stop("tcpdump", sig=signal.SIGINT)

    def finish(self) -> None:
        for name, process in self.processes.items():
            record = self.timeline["processes"][name]
            record.setdefault("returncode", process.returncode)
            record.setdefault("exit_monotonic_ns", process.exit_monotonic_ns)
        rt.write_json(self.out / "timeline.json", self.timeline)
        for path in self.out.iterdir():
            try:
                os.chown(path, self.user.pw_uid, self.user.pw_gid)
            except OSError:
                pass


def bring_up(stack: Stack, *, gatewayd: bool = True, multicast: bool = True, frames: int = 0,
             client: bool = True) -> str:
    stack.timeline["lola_state_removed"] = stack.clean_lola_state()
    stack.start_capture()
    stack.start_someipd()
    if gatewayd:
        stack.start_gatewayd()
    stack.start_source(frames)
    stack.start_adapter()
    if gatewayd:
        stack.wait("gatewayd", GATEWAYD_FOUND, 20.0)
    receiver = stack.start_receiver(multicast=multicast)
    if client:
        stack.start_recorder()
        stack.wait("recorder", "connected", 15.0, json_event=True)
    if gatewayd:
        stack.wait_count(receiver, '"event":"subscribed"', 1, 20.0)
        stack.shared_memory_snapshot()
    return receiver


def case_identity(stack: Stack) -> None:
    bring_up(stack, frames=200)
    time.sleep(1.0)
    stack.go()
    deadline = time.monotonic() + 40.0
    source_log = stack.out / "source.jsonl"
    done = False
    while time.monotonic() < deadline and not done:
        lines = source_log.read_text(encoding="utf-8").splitlines() if source_log.exists() else []
        done = any(json.loads(line).get("event") == "done" for line in lines if line.startswith("{"))
        time.sleep(0.2)
    stack.note("source done", ok=done)
    time.sleep(2.0)


def _recover(stack: Stack, receiver: str, before: int) -> None:
    stack.wait_count(receiver, '"event":"subscribed"', before + 1, 20.0)
    time.sleep(3.0)


def case_resubscribe(stack: Stack) -> None:
    receiver = bring_up(stack, frames=0)
    stack.go()
    time.sleep(3.0)
    # 1. receiver stopped by SIGTERM and started again
    start = stack.note("disturbance receiver_sigterm_restart")
    stack.stop(receiver, signal.SIGTERM)
    receiver = stack.start_receiver()
    stack.disturbance("receiver_sigterm_restart", start)
    _recover(stack, receiver, 0)
    # 2. receiver killed by SIGKILL and started again
    start = stack.note("disturbance receiver_sigkill_restart")
    stack.stop(receiver, signal.SIGKILL)
    receiver = stack.start_receiver()
    stack.disturbance("receiver_sigkill_restart", start)
    _recover(stack, receiver, 0)
    # 3. the gateway pair restarted together (operating rule OR-2), the adapter kept
    pair_restart(stack, receiver, "gatewayd", "someipd", "gatewayd-2", "someipd-2")
    # 4. the guest end of the link down for longer than the subscription TTL
    before = stack.subscribed_count(receiver)
    start = stack.note("disturbance link_outage", seconds=LINK_OUTAGE_S)
    run(["ip", "-n", GUEST_NS, "link", "set", GUEST_IF, "down"])
    time.sleep(LINK_OUTAGE_S)
    run(["ip", "-n", GUEST_NS, "link", "set", GUEST_IF, "up"])
    # An administrative down removes the routes of the interface; restore the group route.
    run(["ip", "-n", GUEST_NS, "route", "replace", MULTICAST_ROUTE, "dev", GUEST_IF])
    stack.disturbance("link_outage", start, guest_route=run(["ip", "-n", GUEST_NS, "route"]).stdout)
    _recover(stack, receiver, before)


def case_no_client(stack: Stack) -> None:
    bring_up(stack, frames=0, client=False)
    stack.go()
    time.sleep(5.0)
    stack.start_recorder()
    stack.wait("recorder", "connected", 15.0, json_event=True)
    time.sleep(5.0)


def pair_restart(stack: Stack, receiver: str, gatewayd: str, someipd: str, new_gatewayd: str,
                 new_someipd: str, *, paused: bool = False) -> None:
    """gatewayd killed, someipd stopped, both started again (operating rule OR-2); the adapter keeps running.

    With paused, the source is held until the receiver subscribed again, so that
    the stored frames of the new subscriptions in the host half arrive in the new
    phase.
    """
    before = stack.subscribed_count(receiver)
    start = stack.note("disturbance gateway_pair_restart")
    stack.stop(gatewayd, signal.SIGKILL)
    stack.stop(someipd, signal.SIGTERM)
    stack.start_someipd(new_someipd)
    stack.start_gatewayd(new_gatewayd, someipd=new_someipd)
    if paused:
        stack.wait(new_gatewayd, GATEWAYD_FOUND, 20.0)
        stack.wait_count(receiver, '"event":"subscribed"', before + 1, 20.0)
        time.sleep(1.0)
        stack.disturbance("gateway_pair_restart", start)
        stack.resume()
        time.sleep(3.0)
        return
    stack.disturbance("gateway_pair_restart", start)
    _recover(stack, receiver, before)


def case_stored_samples(stack: Stack) -> None:
    receiver = bring_up(stack, gatewayd=False, frames=0)
    # (a) Frames from before the phase, in the phase. The adapter keeps the
    # newest frames in its 20 sample slots while the source is paused.
    # gatewayd reads up to 10 of them at the first notification after its
    # subscription, so the stored frames reach the receiver after it has
    # subscribed, when the source sends again.
    stack.go()
    time.sleep(3.0)
    stack.pause()
    stack.start_gatewayd()
    stack.wait("gatewayd", GATEWAYD_FOUND, 20.0)
    stack.wait_count(receiver, '"event":"subscribed"', 1, 20.0)
    stack.shared_memory_snapshot()
    time.sleep(1.0)
    stack.resume()
    time.sleep(3.0)
    # (b) Copies in the phase: gatewayd alone, beside the running someipd. The
    # receiver stays subscribed, so its phase goes on, and the stored frames of
    # gatewayd's new subscription repeat frames that the receiver served.
    stack.pause()
    start = stack.note("disturbance gatewayd_restart")
    stack.stop("gatewayd", signal.SIGKILL)
    time.sleep(1.0)
    stack.start_gatewayd("gatewayd-2")
    stack.wait("gatewayd-2", GATEWAYD_FOUND, 20.0)
    time.sleep(1.0)
    stack.disturbance("gatewayd_restart", start, expects_resubscription=False)
    stack.resume()
    time.sleep(3.0)
    # (a) again at a resubscription: the gateway pair, so the stored frames are
    # older than the new phase.
    stack.pause()
    pair_restart(stack, receiver, "gatewayd-2", "someipd", "gatewayd-3", "someipd-2", paused=True)


def case_ttl_renewal(stack: Stack) -> None:
    bring_up(stack, frames=0, multicast=False)
    stack.go()
    time.sleep(5 * SUBSCRIPTION_TTL_S)


CASES = {
    "identity": case_identity,
    "resubscribe": case_resubscribe,
    "no_client": case_no_client,
    "stored_samples": case_stored_samples,
    "ttl_renewal": case_ttl_renewal,
}


def summarize(results: dict[str, dict]) -> str:
    lines = ["### SOME/IP receiver against someipd (network namespaces)", "",
             "| Case | Outcome | Key data |", "|---|---|---|"]
    for case, result in results.items():
        metrics = result.get("metrics", {})
        keys = ("frames_produced", "frames_byte_identical", "frames_at_client", "duplicates_at_client",
                "band_frames", "dropped_no_client", "dropped_older_than_phase", "dropped_copy_in_phase",
                "older_frame_age_s", "repeats_on_link", "acked_window_s", "largest_ack_gap_s",
                "nacks_before_first_ack", "receipt_minus_frame_ms", "clock_steps")
        data = "; ".join(f"{key} {metrics[key]}" for key in keys if key in metrics)
        drops = {reason: count for reason, count in metrics.get("drops_by_reason", {}).items() if count}
        phases = Counter(phase["cause"] for phase in metrics.get("phases", []))
        data += f"; drops {drops or 'none'}; phase starts {dict(phases)}"
        lines.append(f"| {case} | {result['outcome']} | {data} |")
        for step in metrics.get("steps", []):
            lines.append(f"| | | step {step['step']}: dropped {step['stored_dropped'] or 'none'}, older on the link "
                         f"{step['older_on_link']}, repeats on the link {step['repeats_on_link']}, served "
                         f"{step['served']} |")
        if result.get("reasons"):
            lines.append(f"| | | reasons: {'; '.join(result['reasons'])} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--receiver", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--env-json", required=True, help="environment of the bench user with ROS 2 sourced")
    parser.add_argument("--rmw", default="rmw_cyclonedds_cpp")
    parser.add_argument("--cases", default=",".join(CASES))
    args = parser.parse_args()
    if os.geteuid() != 0:
        print("run as root: the runner creates network namespaces", file=sys.stderr)
        return 2
    user = pwd.getpwnam(args.user)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    os.chown(out, user.pw_uid, user.pw_gid)
    base_env = json.loads(Path(args.env_json).read_text())
    base_env["PYTHONUNBUFFERED"] = "1"
    rt.write_json(out / "run-facts.json", {
        "receiver_sha256": rt.sha256(Path(args.receiver)),
        "bundle_someipd_sha256": rt.sha256(Path(args.bundle) / "bin" / "someipd"),
        "bundle_gatewayd_sha256": rt.sha256(Path(args.bundle) / "bin" / "gatewayd"),
        "bundle_adapter_sha256": rt.sha256(Path(args.bundle) / "bin" / "de4sdv_score_adapter"),
        "vsomeip_config_sha256": rt.sha256(BENCH / "config" / "vsomeip_netns_host.json"),
        "bench_user": {"name": user.pw_name, "uid": user.pw_uid, "gid": user.pw_gid},
        "setpriv": run(["setpriv", "--version"], check=False).stdout.strip(),
    })
    results: dict[str, dict] = {}
    try:
        netns_up(out)
        for case in args.cases.split(","):
            stack = Stack(case, out, args, user, base_env)
            try:
                CASES[case](stack)
            except Exception as error:  # the case is reported as broken; the run goes on
                stack.note("runner_error", error=repr(error))
                stack.timeline["runner_error"] = repr(error)
            finally:
                stack.stop_all()
                stack.finish()
            try:
                results[case] = EVALUATORS[case](load_case(stack.out))
            except Exception as error:  # evaluation of broken records
                results[case] = {"outcome": "errorEvidence", "reasons": [f"evaluation failed: {error!r}"],
                                 "checks": {}, "metrics": {}}
            rt.write_json(stack.out / "result.json", results[case])
            print(f"[{case}] {results[case]['outcome']} {results[case]['reasons']}", flush=True)
    finally:
        netns_down()
    rt.write_json(out / "results.json", results)
    summary = summarize(results)
    (out / "summary.md").write_text(summary, encoding="utf-8")
    print(summary)
    gates_ok = all(results.get(case, {}).get("outcome") == PASS for case in GATE_CASES if case in args.cases)
    measurements_ok = all(results.get(case, {}).get("outcome") in (PASS, MISSING)
                          for case in MEASUREMENT_CASES if case in args.cases)
    return 0 if gates_ok and measurements_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
