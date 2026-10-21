#!/usr/bin/env python3
"""DE4SDV throwaway spike (INC-MW-011 gateway feasibility), never merged.

Runs the cross-domain scenarios: the host network domain holds the
mw::com publisher, gatewayd and someipd; the guest network domain holds the
vsomeip 3.7.6 client with a private /tmp and /dev/shm, so the only path between
the two is the veth pair. Every scenario writes its own directory with the
process logs, the guest-side packet capture and orchestrator.log, a timeline
of the orchestrator's own actions (CLOCK_MONOTONIC ns, the clock all spike
processes log with). analyze.py turns the directories into verdicts.

Run as root (the CI job uses sudo). Subcommands: netns-up, netns-down, run.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import resource
import shlex
import signal
import subprocess
import sys
import time
from pathlib import Path

HOST_NS = "de4sdv-host"
GUEST_NS = "de4sdv-guest"
HOST_IF = "veth-h"
GUEST_IF = "veth-g"
HOST_IP = "10.250.0.1"
GUEST_IP = "10.250.0.2"

GATEWAYD_IPC_READY = r"\[gatewayd\] IPC connection to someipd established"
GATEWAYD_FOUND = r"LocalServiceInstance created for instance specifier: de4sdv/aebs_signal_frame"
SOMEIPD_OFFER = r"OFFER\(0100\): \[4dee\.0001"
CLIENT_SUBSCRIBED = r"SUBSCRIPTION_STATUS status=0x0\b"

STALE_PATTERNS = (
    "/dev/shm/lola-*",
    "/dev/shm/*de4sdv_aebs_signal_frame*",
    "/tmp/mw_com_lola",
    "/tmp/lola-*",
    "/tmp/de4sdvhost-*",
    "/tmp/vsomeip*",
)


def sh(cmd: list[str], check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=check, capture_output=True, text=True)


# --------------------------------------------------------------------------- netns


def netns_up(out: Path) -> None:
    netns_down(quiet=True)
    steps = [
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
        # vsomeip offers only once the SD multicast address has a route.
        ["ip", "-n", HOST_NS, "route", "add", "224.0.0.0/4", "dev", HOST_IF],
        ["ip", "-n", GUEST_NS, "route", "add", "224.0.0.0/4", "dev", GUEST_IF],
    ]
    for step in steps:
        sh(step)
    record = {}
    for ns in (HOST_NS, GUEST_NS):
        record[ns] = {
            "addr": sh(["ip", "-n", ns, "addr"]).stdout,
            "route": sh(["ip", "-n", ns, "route"]).stdout,
        }
    record["root_ns_has_veth"] = HOST_IF in sh(["ip", "link"]).stdout or GUEST_IF in sh(["ip", "link"]).stdout
    record["ping_guest_to_host"] = sh(
        ["ip", "netns", "exec", GUEST_NS, "ping", "-c", "2", "-W", "2", HOST_IP], check=False
    ).stdout
    out.mkdir(parents=True, exist_ok=True)
    (out / "netns.json").write_text(json.dumps(record, indent=2))
    print(record["ping_guest_to_host"])


def netns_down(quiet: bool = False) -> None:
    for ns in (HOST_NS, GUEST_NS):
        result = sh(["ip", "netns", "del", ns], check=False)
        if result.returncode != 0 and not quiet:
            print(result.stderr.strip())


# --------------------------------------------------------------------------- scenario plumbing


class Scenario:
    def __init__(self, name: str, root: Path, paths: dict, description: str) -> None:
        self.name = name
        self.paths = paths
        self.out = root / name
        self.out.mkdir(parents=True, exist_ok=True)
        self.control = self.out / "client-control"
        self.control.mkdir(exist_ok=True)
        self.timeline = (self.out / "orchestrator.log").open("a")
        self.procs: dict[str, tuple[subprocess.Popen, object]] = {}
        self.meta: dict = {
            "name": name,
            "description": description,
            "clock": {"monotonic_ns": time.monotonic_ns(), "realtime_ns": time.time_ns()},
            "processes": {},
            "waits": [],
        }
        # Diagnostic options, set by a scenario before it starts processes.
        self.debug_logs = False  # mw::log at kDebug on the console for the host processes
        self.core_dumps = False  # RLIMIT_CORE unlimited for the started processes
        self.manifest_variant = ""  # "" or "_2subs": the mw::com manifests of publisher and gatewayd

    # -- timeline
    def note(self, message: str) -> int:
        stamp = time.monotonic_ns()
        self.timeline.write(f"{stamp} {message}\n")
        self.timeline.flush()
        print(f"[{self.name}] {stamp} {message}", flush=True)
        return stamp

    # -- processes
    def start(self, name: str, ns: str, argv: list[str], env: dict | None = None, private_tmp: bool = False) -> subprocess.Popen:
        log = (self.out / f"{name}.stdout.log").open("ab")
        env_args = ["env"] + [f"{key}={value}" for key, value in (env or {}).items()]
        if private_tmp:
            inner = " ".join(shlex.quote(part) for part in env_args + argv)
            cmd = [
                "ip", "netns", "exec", ns, "unshare", "--mount", "--propagation", "private", "--",
                "sh", "-c", f"mount -t tmpfs tmpfs /tmp && mount -t tmpfs tmpfs /dev/shm && exec {inner}",
            ]
        else:
            cmd = ["ip", "netns", "exec", ns] + env_args + argv
        preexec = None
        if self.core_dumps:
            def preexec() -> None:
                resource.setrlimit(resource.RLIMIT_CORE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY))
        process = subprocess.Popen(cmd, stdout=log, stderr=subprocess.STDOUT, start_new_session=True,
                                   preexec_fn=preexec)
        self.procs[name] = (process, log)
        stamp = self.note(f"START {name} pid={process.pid} ns={ns} private_tmp={private_tmp} "
                          f"debug_logs={self.debug_logs} core_dumps={self.core_dumps}")
        self.meta["processes"][name] = {"pid": process.pid, "ns": ns, "argv": argv, "env": env or {},
                                        "private_tmp": private_tmp, "started_ns": stamp,
                                        "core_dumps": self.core_dumps}
        return process

    def record_maps(self, name: str, delay: float = 1.0) -> None:
        """Records which vsomeip library a running process mapped (version evidence)."""
        time.sleep(delay)
        process = self.procs[name][0]
        libs = set()
        try:
            for line in Path(f"/proc/{process.pid}/maps").read_text().splitlines():
                if "vsomeip" in line or "score_com_serializer" in line:
                    libs.add(line.split()[-1])
        except OSError as error:
            libs.add(f"unreadable: {error}")
        self.meta["processes"][name]["mapped_libraries"] = sorted(libs)
        self.note(f"MAPS {name} {sorted(libs)}")

    def alive(self, name: str) -> bool:
        return name in self.procs and self.procs[name][0].poll() is None

    def send_signal(self, name: str, sig: int) -> int:
        process = self.procs[name][0]
        stamp = self.note(f"SIGNAL {name} {signal.Signals(sig).name}")
        if process.poll() is None:
            os.kill(process.pid, sig)
        return stamp

    def stop(self, name: str, sig: int = signal.SIGTERM, timeout: float = 10.0) -> None:
        if name not in self.procs or "exit_code" in self.meta["processes"][name]:
            return
        process, log = self.procs[name]
        if process.poll() is None:
            self.send_signal(name, sig)
            try:
                process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                self.note(f"KILL {name} after {timeout}s")
                os.kill(process.pid, signal.SIGKILL)
                process.wait(timeout=10)
        self.meta["processes"][name]["exit_code"] = process.returncode
        self.meta["processes"][name]["stopped_ns"] = time.monotonic_ns()
        self.note(f"EXITED {name} code={process.returncode}")
        log.close()

    def stop_all(self) -> None:
        for name in reversed(list(self.procs)):
            self.stop(name, signal.SIGINT if name == "tcpdump" else signal.SIGTERM)

    # -- waits
    def _wait(self, what: str, predicate, timeout: float) -> bool:
        deadline = time.monotonic() + timeout
        start = self.note(f"WAIT {what}")
        while time.monotonic() < deadline:
            if predicate():
                stamp = self.note(f"WAIT_OK {what}")
                self.meta["waits"].append({"what": what, "ok": True, "ns": stamp - start})
                return True
            time.sleep(0.05)
        self.note(f"WAIT_TIMEOUT {what} after {timeout}s")
        self.meta["waits"].append({"what": what, "ok": False})
        return False

    def wait_log(self, name: str, pattern: str, timeout: float = 30.0, count: int = 1) -> bool:
        path = self.out / f"{name}.stdout.log"
        regex = re.compile(pattern, re.MULTILINE)

        def found() -> bool:
            try:
                return len(regex.findall(path.read_text(errors="replace"))) >= count
            except OSError:
                return False

        return self._wait(f"{name} log /{pattern}/ x{count}", found, timeout)

    def wait_file(self, path: Path, timeout: float = 30.0) -> bool:
        return self._wait(f"file {path.name}", path.exists, timeout)

    def wait_exit(self, name: str, timeout: float = 15.0) -> bool:
        return self._wait(f"exit {name}", lambda: not self.alive(name), timeout)

    def client_messages(self) -> int:
        try:
            return (self.out / "client_events.log").read_text(errors="replace").count(" MSG n=")
        except OSError:
            return 0

    def wait_client_messages(self, count: int, timeout: float = 30.0) -> bool:
        return self._wait(f"client messages >= {count}", lambda: self.client_messages() >= count, timeout)

    def touch(self, path: Path) -> int:
        path.write_text("")
        return self.note(f"TOUCH {path.name}")

    def rss_kib(self, name: str) -> int | None:
        try:
            for line in Path(f"/proc/{self.procs[name][0].pid}/status").read_text().splitlines():
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
        except (OSError, KeyError):
            return None
        return None

    def finish(self) -> None:
        self.stop_all()
        self.meta["finished"] = {"monotonic_ns": time.monotonic_ns(), "realtime_ns": time.time_ns()}
        (self.out / "scenario.json").write_text(json.dumps(self.meta, indent=2))
        self.timeline.close()

    # -- components
    def host_env(self) -> dict:
        env = {"LD_LIBRARY_PATH": self.paths["host_ld_library_path"]}
        if self.debug_logs and self.paths.get("mw_log_debug"):
            env["MW_LOG_CONFIG_FILE"] = self.paths["mw_log_debug"]
        return env

    def manifest(self, role: str) -> str:
        return self.paths[f"mw_com_{role}{self.manifest_variant}"]

    def start_tcpdump(self) -> None:
        pcap = str(self.out / "guest_wire.pcap")
        argv = ["tcpdump", "-i", GUEST_IF, "-U", "-s", "0", "-Z", "root", "--time-stamp-precision=nano", "-w", pcap]
        override = os.environ.get("SPIKE_CAPTURE_CMD")  # the local dry run only
        if override:
            argv = [part.replace("{pcap}", pcap).replace("{if}", GUEST_IF) for part in json.loads(override)]
        self.start("tcpdump", GUEST_NS, argv)
        self.wait_log("tcpdump", r"listening on", 10)

    def start_someipd(self, name: str = "someipd") -> None:
        env = self.host_env() | {"VSOMEIP_CONFIGURATION": self.paths["vsomeip_host"]}
        self.start(name, HOST_NS, [self.paths["someipd"], "-c", self.paths["someip_config_bin"]], env=env)
        self.wait_log(name, SOMEIPD_OFFER, 20)
        self.record_maps(name, 0.2)

    def start_gatewayd(self, name: str = "gatewayd", wait_ipc: bool = True) -> None:
        argv = [self.paths["gatewayd"], "-c", self.paths["someip_config_bin"], "-s", self.manifest("gatewayd")]
        self.start(name, HOST_NS, argv, env=self.host_env())
        if wait_ipc:
            self.wait_log(name, GATEWAYD_IPC_READY, 20)
        self.record_maps(name, 0.2)

    def start_publisher(self, tag: str = "publisher", extra: list[str] | None = None, wait_offer: bool = True) -> None:
        argv = [self.paths["publisher"], "--service_instance_manifest", self.manifest("publisher"),
                "--out", str(self.out), "--tag", tag] + (extra or [])
        self.start(tag, HOST_NS, argv, env=self.host_env())
        if wait_offer:
            self.wait_file(self.out / f"{tag}.offered", 20)

    def start_client(self) -> None:
        env = {"VSOMEIP_CONFIGURATION": self.paths["vsomeip_guest"],
               "LD_LIBRARY_PATH": self.paths["guest_ld_library_path"]}
        argv = [self.paths["client"], "--out", str(self.out), "--control-dir", str(self.control)]
        self.start("client", GUEST_NS, argv, env=env, private_tmp=True)
        self.record_maps("client", 1.0)

    def wait_subscribed(self, count: int = 1, timeout: float = 30.0) -> bool:
        path = self.out / "client_events.log"
        regex = re.compile(CLIENT_SUBSCRIBED)

        def found() -> bool:
            try:
                return len(regex.findall(path.read_text(errors="replace"))) >= count
            except OSError:
                return False

        return self._wait(f"client subscribed x{count}", found, timeout)


def clean_host_state() -> list[str]:
    import glob
    import shutil

    removed = []
    for pattern in STALE_PATTERNS:
        for path in glob.glob(pattern):
            try:
                if os.path.isdir(path) and not os.path.islink(path):
                    shutil.rmtree(path)
                else:
                    os.remove(path)
                removed.append(path)
            except OSError:
                pass
    return removed


# --------------------------------------------------------------------------- scenarios


def s1_main(sc: Scenario) -> None:
    """200 frames, client subscribed first: byte identity by digest (the gate)."""
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "200", "--period-ms", "50", "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    time.sleep(1.0)
    sc.touch(sc.out / "go")
    sc.wait_file(sc.out / "publisher.done", 60)
    sc.wait_client_messages(200, 10)
    time.sleep(1.0)


def s2_late_subscriber(sc: Scenario) -> None:
    """REQ-MW-019: frames 1..50 before any guest subscription must never reach the guest."""
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "100", "--period-ms", "50", "--pause-at", "50",
                              "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.touch(sc.out / "go")
    sc.wait_file(sc.out / "publisher.paused-50", 30)
    time.sleep(1.0)
    sc.start_client()
    sc.wait_subscribed()
    time.sleep(2.0)
    sc.touch(sc.out / "resume-50")
    sc.wait_file(sc.out / "publisher.done", 30)
    time.sleep(3.0)


def s3_resubscribe(sc: Scenario) -> None:
    """REQ-MW-019: frames 41..80 produced while the guest is unsubscribed must never arrive."""
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "120", "--period-ms", "50", "--pause-at", "40,80",
                              "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    time.sleep(1.0)
    sc.touch(sc.out / "go")
    sc.wait_file(sc.out / "publisher.paused-40", 30)
    time.sleep(1.0)
    sc.touch(sc.control / "unsubscribe")
    sc.wait_log("client", r"UNSUBSCRIBE_CALLED", 10)
    time.sleep(2.0)
    sc.touch(sc.out / "resume-40")
    sc.wait_file(sc.out / "publisher.paused-80", 30)
    time.sleep(1.0)
    sc.touch(sc.control / "resubscribe")
    sc.wait_subscribed(count=2, timeout=15)
    time.sleep(2.0)
    sc.touch(sc.out / "resume-80")
    sc.wait_file(sc.out / "publisher.done", 30)
    time.sleep(3.0)


def s4_gatewayd_crash_restart(sc: Scenario) -> None:
    """gatewayd killed and restarted while the guest stays subscribed: recovery and replay."""
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "100", "--period-ms", "50", "--pause-at", "50",
                              "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    time.sleep(1.0)
    sc.touch(sc.out / "go")
    sc.wait_file(sc.out / "publisher.paused-50", 30)
    time.sleep(1.0)
    sc.meta["gatewayd_killed_ns"] = sc.send_signal("gatewayd", signal.SIGKILL)
    sc.wait_exit("gatewayd", 10)
    sc.stop("gatewayd")
    time.sleep(1.0)
    sc.start_gatewayd("gatewayd-2")
    sc.wait_log("gatewayd-2", GATEWAYD_FOUND, 20)
    time.sleep(2.0)
    sc.meta["resumed_ns"] = sc.touch(sc.out / "resume-50")
    sc.wait_file(sc.out / "publisher.done", 30)
    time.sleep(3.0)


def s5_late_gatewayd(sc: Scenario) -> None:
    """Frames 1..20 published before gatewayd and before the guest subscribed (static SOME/IP offer)."""
    sc.start_tcpdump()
    sc.start_publisher(extra=["--frames", "60", "--period-ms", "50", "--pause-at", "20"])
    sc.wait_file(sc.out / "publisher.paused-20", 30)
    sc.start_someipd()
    sc.start_client()
    sc.wait_subscribed()
    sc.meta["client_subscribed_ns"] = sc.note("CLIENT_SUBSCRIBED_BEFORE_GATEWAYD")
    time.sleep(1.0)
    sc.start_gatewayd()
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    time.sleep(2.0)
    sc.touch(sc.out / "resume-20")
    sc.wait_file(sc.out / "publisher.done", 30)
    time.sleep(3.0)


def s6_publisher_restart(sc: Scenario) -> None:
    """The publisher (the adapter of the model) exits and a new instance offers again."""
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "50", "--period-ms", "50", "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    time.sleep(1.0)
    sc.touch(sc.out / "go")
    sc.wait_file(sc.out / "publisher.done", 30)
    sc.wait_exit("publisher", 10)
    sc.stop("publisher")
    sc.meta["publisher_a_exited_ns"] = sc.note("PUBLISHER_A_EXITED")
    time.sleep(4.0)
    sc.start_publisher("publisher-b", extra=["--frames", "50", "--period-ms", "50", "--start-seq", "51",
                                             "--go-file", str(sc.out / "go-b")])
    time.sleep(4.0)
    sc.touch(sc.out / "go-b")
    sc.wait_file(sc.out / "publisher-b.done", 30)
    time.sleep(3.0)


def s7_host_stop_sequence(sc: Scenario) -> None:
    """(b) What the guest sees when the host side stops: publisher, then gatewayd, then someipd."""
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "0", "--period-ms", "100", "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    sc.touch(sc.out / "go")
    time.sleep(3.0)
    sc.meta["stop_publisher_ns"] = sc.send_signal("publisher", signal.SIGTERM)
    sc.wait_exit("publisher", 10)
    time.sleep(7.0)
    sc.meta["stop_gatewayd_ns"] = sc.send_signal("gatewayd", signal.SIGTERM)
    sc.wait_exit("gatewayd", 10)
    time.sleep(7.0)
    sc.meta["stop_someipd_ns"] = sc.send_signal("someipd", signal.SIGTERM)
    sc.wait_exit("someipd", 10)
    time.sleep(7.0)


def s8_someipd_kill(sc: Scenario) -> None:
    """(b) someipd killed (no orderly StopOffer possible): when does the guest notice?"""
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "0", "--period-ms", "100", "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    sc.touch(sc.out / "go")
    time.sleep(3.0)
    sc.meta["kill_someipd_ns"] = sc.send_signal("someipd", signal.SIGKILL)
    sc.wait_exit("someipd", 10)
    time.sleep(10.0)


def s9_stalled_guest(sc: Scenario) -> None:
    """A subscribed guest that stops reading for 30 s: host queue bound and backlog after resume."""
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "0", "--period-ms", "50", "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    sc.touch(sc.out / "go")
    time.sleep(3.0)
    rss = [{"phase": "before", "someipd_kib": sc.rss_kib("someipd"), "gatewayd_kib": sc.rss_kib("gatewayd")}]
    sc.meta["stall_start_ns"] = sc.send_signal("client", signal.SIGSTOP)
    for i in range(6):
        time.sleep(5.0)
        rss.append({"phase": f"stalled+{5 * (i + 1)}s", "someipd_kib": sc.rss_kib("someipd"),
                    "gatewayd_kib": sc.rss_kib("gatewayd")})
    sc.meta["stall_end_ns"] = sc.send_signal("client", signal.SIGCONT)
    time.sleep(5.0)
    rss.append({"phase": "after", "someipd_kib": sc.rss_kib("someipd"), "gatewayd_kib": sc.rss_kib("gatewayd")})
    sc.meta["rss"] = rss
    sc.meta["stop_publisher_ns"] = sc.send_signal("publisher", signal.SIGTERM)
    sc.wait_exit("publisher", 10)
    time.sleep(2.0)


def s10_guest_request_probe(sc: Scenario) -> None:
    """REQ-MW-016 support: the guest sends requests to the service; nothing on the host may take them."""
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "80", "--period-ms", "50", "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    sc.touch(sc.out / "go")
    time.sleep(1.0)
    sc.meta["probe_ns"] = sc.touch(sc.control / "probe")
    sc.wait_log("client", r"PROBE_SENT", 10)
    sc.wait_file(sc.out / "publisher.done", 30)
    time.sleep(2.0)


def s11_gatewayd_sigterm_publisher_alive(sc: Scenario) -> None:
    """Diagnosis: gatewayd SIGTERM while the publisher keeps offering and sending (exit status, core)."""
    sc.debug_logs = True
    sc.core_dumps = True
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "0", "--period-ms", "100", "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    sc.touch(sc.out / "go")
    time.sleep(2.0)
    sc.meta["sigterm_gatewayd_ns"] = sc.send_signal("gatewayd", signal.SIGTERM)
    sc.wait_exit("gatewayd", 10)
    sc.stop("gatewayd")
    time.sleep(1.0)


def s12_gatewayd_sigterm_without_publisher(sc: Scenario) -> None:
    """Diagnosis: gatewayd SIGTERM before any mw::com provider exists (exit status, core)."""
    sc.debug_logs = True
    sc.core_dumps = True
    sc.start_someipd()
    sc.start_gatewayd()
    time.sleep(2.0)
    sc.meta["sigterm_gatewayd_ns"] = sc.send_signal("gatewayd", signal.SIGTERM)
    sc.wait_exit("gatewayd", 10)
    sc.stop("gatewayd")
    time.sleep(1.0)


def s13_gatewayd_crash_restart_debug(sc: Scenario) -> None:
    """Diagnosis: s04 again with mw::log at kDebug, to see where the path stops after the restart."""
    sc.debug_logs = True
    s4_gatewayd_crash_restart(sc)


def s14_gatewayd_crash_restart_2subs(sc: Scenario) -> None:
    """Diagnosis: s04 with maxSubscribers 2 and 20 sample slots in both mw::com manifests (kDebug logs)."""
    sc.debug_logs = True
    sc.manifest_variant = "_2subs"
    s4_gatewayd_crash_restart(sc)


def s15_gatewayd_crash_then_publisher_restart(sc: Scenario) -> None:
    """Diagnosis: gatewayd killed and restarted, then the publisher restarted too: does the path come back?"""
    sc.debug_logs = True
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "50", "--period-ms", "50", "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    sc.touch(sc.out / "go")
    sc.wait_file(sc.out / "publisher.done", 30)
    sc.wait_exit("publisher", 10)
    sc.stop("publisher")
    sc.meta["gatewayd_killed_ns"] = sc.send_signal("gatewayd", signal.SIGKILL)
    sc.wait_exit("gatewayd", 10)
    sc.stop("gatewayd")
    time.sleep(1.0)
    sc.start_gatewayd("gatewayd-2")
    sc.start_publisher("publisher-b", extra=["--frames", "50", "--period-ms", "50", "--start-seq", "51",
                                             "--go-file", str(sc.out / "go-b")])
    sc.wait_log("gatewayd-2", GATEWAYD_FOUND, 20)
    time.sleep(2.0)
    sc.touch(sc.out / "go-b")
    sc.wait_file(sc.out / "publisher-b.done", 30)
    time.sleep(3.0)


def s16_main_1000_frames_100hz(sc: Scenario) -> None:
    """1000 frames at 100 Hz, ten times the HMI rate: identity, order and gaps under load."""
    sc.start_tcpdump()
    sc.start_someipd()
    sc.start_gatewayd()
    sc.start_publisher(extra=["--frames", "1000", "--period-ms", "10", "--go-file", str(sc.out / "go")])
    sc.wait_log("gatewayd", GATEWAYD_FOUND, 20)
    sc.start_client()
    sc.wait_subscribed()
    time.sleep(1.0)
    sc.touch(sc.out / "go")
    sc.wait_file(sc.out / "publisher.done", 60)
    sc.wait_client_messages(1000, 10)
    time.sleep(1.0)


SCENARIOS = {
    "s01-main": s1_main,
    "s02-late-subscriber": s2_late_subscriber,
    "s03-resubscribe": s3_resubscribe,
    "s04-gatewayd-crash-restart": s4_gatewayd_crash_restart,
    "s05-late-gatewayd": s5_late_gatewayd,
    "s06-publisher-restart": s6_publisher_restart,
    "s07-host-stop-sequence": s7_host_stop_sequence,
    "s08-someipd-kill": s8_someipd_kill,
    "s09-stalled-guest": s9_stalled_guest,
    "s10-guest-request-probe": s10_guest_request_probe,
    "s11-gatewayd-sigterm-publisher-alive": s11_gatewayd_sigterm_publisher_alive,
    "s12-gatewayd-sigterm-without-publisher": s12_gatewayd_sigterm_without_publisher,
    "s13-gatewayd-crash-restart-debug": s13_gatewayd_crash_restart_debug,
    "s14-gatewayd-crash-restart-2subs": s14_gatewayd_crash_restart_2subs,
    "s15-gatewayd-crash-then-publisher-restart": s15_gatewayd_crash_then_publisher_restart,
    "s16-main-1000-frames-100hz": s16_main_1000_frames_100hz,
}


def run(args: argparse.Namespace) -> int:
    paths = json.loads(Path(args.paths).read_text())
    root = Path(args.out)
    root.mkdir(parents=True, exist_ok=True)
    selected = list(SCENARIOS) if args.scenarios == "all" else args.scenarios.split(",")
    for name in selected:
        function = SCENARIOS[name]
        removed = clean_host_state()
        sc = Scenario(name, root, paths, (function.__doc__ or "").strip())
        sc.meta["cleaned"] = removed
        sc.note(f"SCENARIO_BEGIN {name}")
        try:
            function(sc)
        except Exception as error:  # the analysis reports the scenario as broken, the run continues
            sc.meta["orchestrator_error"] = repr(error)
            sc.note(f"ORCHESTRATOR_ERROR {error!r}")
        finally:
            sc.note(f"SCENARIO_END {name}")
            sc.finish()
        subprocess.run(["sync"], check=False)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    up = sub.add_parser("netns-up")
    up.add_argument("--out", required=True)
    sub.add_parser("netns-down")
    runner = sub.add_parser("run")
    runner.add_argument("--paths", required=True, help="JSON with the binary and configuration paths")
    runner.add_argument("--out", required=True)
    runner.add_argument("--scenarios", default="all")
    args = parser.parse_args()
    if args.command == "netns-up":
        netns_up(Path(args.out))
        return 0
    if args.command == "netns-down":
        netns_down()
        return 0
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
