#!/usr/bin/env python3
"""A fake Launch Manager for the dry runs of start_score_side.sh, stop_score_side.sh and p10_1_check.sh. Test code
only: it is not Lifecycle and proves nothing about it.

It reads config/launch_manager_config.json in its working directory (the stage; the real daemon reads the
serialized etc/launch_manager_config.bin, which it checks only for presence). Like the real daemon, it aborts when
etc/mw_com_config.json is missing or no JSON, and exits 1 when that file does not hold the instance
LaunchManager/StateManager/Instance (launch-manager/tests/test_launch_manager_mw_com_config.py). It starts the
components of the initial run target in dependency order with the merged settings (bin_dir/binary_name,
process_arguments, environmental_variables, working_dir), waits for a component of type Reporting until its run log
reports running
(the identity recorder's lifecycle record) and for the others until their process runs, logs each step, and on
SIGTERM stops the components in reverse order with SIGTERM and exits 0. Each component gets exactly its configured
environment, as from the daemon (nothing inherited), plus the test knobs DA_TEST_*, DA_STUB_* and FAKE_*.

Knobs: FAKE_LM_IGNORE_TERM=1 ignores SIGTERM; FAKE_LM_EXIT_AFTER_S=<s> ends with status 3 after s seconds;
FAKE_LM_SUPERVISE=1 emulates the alive supervision of the supervised components: a component whose process is
SIGSTOPped for more than 0.6 s is killed (SIGKILL), "Alive Supervision (...) switched to EXPIRED" and a switch to
fallback_run_target are logged, and the components outside it are stopped.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

STAGE = Path.cwd()
CONFIG = json.loads((STAGE / "config" / "launch_manager_config.json").read_text())
STOP = False
TEST_KNOBS = ("DA_TEST_", "DA_STUB_", "FAKE_")


def log(text: str) -> None:
    print(f"{time.strftime('%H:%M:%S')} fake-lm: {text}", flush=True)


def merged(name: str) -> dict:
    defaults = CONFIG["defaults"]
    comp = CONFIG["components"][name]
    dc = {**defaults["deployment_config"], **comp.get("deployment_config", {})}
    # a component's own list replaces the defaults' list, as each component of the bench's file repeats
    # LD_LIBRARY_PATH
    env = comp.get("deployment_config", {}).get("environmental_variables",
                                                defaults["deployment_config"].get("environmental_variables", {}))
    cp = comp["component_properties"]
    profile = {**defaults["component_properties"]["application_profile"], **cp.get("application_profile", {})}
    return {"binary": os.path.join(dc["bin_dir"], cp["binary_name"]), "args": cp.get("process_arguments", []),
            "env": env, "cwd": dc["working_dir"], "type": profile["application_type"],
            "depends_on": cp.get("depends_on", [])}


def order(target: str) -> list[str]:
    wanted = CONFIG["run_targets"][target]["depends_on"] if target in CONFIG["run_targets"] else \
        CONFIG["fallback_run_target"]["depends_on"]
    done: list[str] = []

    def visit(name: str) -> None:
        if name in done:
            return
        for dep in merged(name)["depends_on"]:
            visit(dep)
        done.append(name)

    for name in wanted:
        visit(name)
    return done


def ready(name: str, proc: subprocess.Popen, settings: dict) -> bool:
    if proc.poll() is not None:
        return False
    if settings["type"] == "Reporting":
        run_dir = settings["args"][settings["args"].index("--run-dir") + 1]
        record = Path(run_dir) / "score" / "identityRecorder.jsonl"
        return record.is_file() and '"state":"running_reported"' in record.read_text()
    return True


def on_term(signum, frame) -> None:  # noqa: ARG001
    global STOP
    STOP = True


def state_of(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/stat").read_text().rsplit(")", 1)[1].split()[0]
    except OSError:
        return "?"


def main() -> int:
    if os.environ.get("FAKE_LM_IGNORE_TERM") == "1":
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
    else:
        signal.signal(signal.SIGTERM, on_term)
    if not (STAGE / "etc" / "launch_manager_config.bin").is_file():
        log("no etc/launch_manager_config.bin")
        return 2
    # Like the daemon at v0.10.0: its LmControl skeleton makes mw::com read ./etc/mw_com_config.json, which must
    # parse (else mw::com aborts) and resolve the skeleton's instance (else the daemon exits 1).
    try:
        com = json.loads((STAGE / "etc" / "mw_com_config.json").read_text())
    except (OSError, ValueError):
        log("lola log fatal: Parsing config file ./etc/mw_com_config.json failed. Terminating.")
        os.abort()
    if [i.get("instanceSpecifier") for i in com.get("serviceInstances", [])].count(
            "LaunchManager/StateManager/Instance") != 1:
        log("Failed to set up LmControl service provider")
        return 1
    exit_after = float(os.environ.get("FAKE_LM_EXIT_AFTER_S", "0") or 0)
    began = time.monotonic()
    initial = CONFIG["initial_run_target"]
    log(f"run target {initial}: {order(initial)}")
    procs: dict[str, subprocess.Popen] = {}
    for name in order(initial):
        s = merged(name)
        # Like the daemon: exactly the configured environment (Lifecycle v0.10.0 process_launcher.cpp:395), nothing
        # inherited (no HOME, no PATH), plus the test knobs of the stubs and the recorder's driver
        env = {**{k: v for k, v in os.environ.items() if k.startswith(TEST_KNOBS)}, **s["env"]}
        if s["type"] in ("Reporting_And_Supervised",):
            env["LCM_ALIVE_INTERFACE_PATH"] = f"/fake/alive/{name}"
        procs[name] = subprocess.Popen([s["binary"], *s["args"]], cwd=s["cwd"], env=env)
        log(f"started {name} pid {procs[name].pid}")
        deadline = time.monotonic() + 30
        while not ready(name, procs[name], s):
            if exit_after and time.monotonic() - began > exit_after:
                log("exiting on FAKE_LM_EXIT_AFTER_S")
                return stop_all(procs, 3)
            if STOP or time.monotonic() > deadline or procs[name].poll() is not None:
                log(f"{name} not ready (exit {procs[name].poll()})")
                return stop_all(procs, 4)
            time.sleep(0.05)
        log(f"{name} ready")
    stopped_since: dict[str, float] = {}
    switched = False
    while not STOP:
        if exit_after and time.monotonic() - began > exit_after:
            log("exiting on FAKE_LM_EXIT_AFTER_S")
            return stop_all(procs, 3)
        if os.environ.get("FAKE_LM_SUPERVISE") == "1" and not switched:
            for name, proc in procs.items():
                if merged(name)["type"] != "Reporting_And_Supervised" or proc.poll() is not None:
                    continue
                if state_of(proc.pid) == "T":
                    stopped_since.setdefault(name, time.monotonic())
                    if time.monotonic() - stopped_since[name] > 0.6:
                        log(f"Alive Supervision ({name}) switched to EXPIRED")
                        proc.send_signal(signal.SIGKILL)
                        proc.wait()
                        keep = CONFIG["fallback_run_target"]["depends_on"]
                        log(f"switching to run target fallback_run_target: {keep}")
                        for other, p in procs.items():
                            if other not in keep and p.poll() is None:
                                p.send_signal(signal.SIGCONT)
                                p.terminate()
                                p.wait()
                        switched = True
                        break
                else:
                    stopped_since.pop(name, None)
        time.sleep(0.05)
    log("SIGTERM: switching to Off")
    return stop_all(procs, 0)


def stop_all(procs: dict, status: int) -> int:
    for name in reversed(list(procs)):
        proc = procs[name]
        if proc.poll() is None:
            proc.send_signal(signal.SIGCONT)
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            log(f"stopped {name} (exit {proc.returncode})")
    return status


if __name__ == "__main__":
    sys.exit(main())
