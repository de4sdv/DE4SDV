"""score-path/scripts/path_stop.sh: the stop run's path stop (shared contract 3 of the S1 build).

The script runs against a fake stage: a fake Launch Manager and fake components (bash scripts under $DA_STAGE/bin,
found by their staged paths as on the host), the state a mode-full start writes, and a fake bundle whose
bin/lm_control_client stands in for the LmControl client (launch-manager/control/): it records its arguments, ends the
components a switch to path_stopped ends, and prints the client's record. DA_SUDO is empty.
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
SCRIPT = HERE.parent / "scripts" / "path_stop.sh"
KEYS = ["runTarget", "stopInstantRealNs", "stopInstantMonoNs", "rc"]
COMPONENTS = ["identity_recorder", "someipd", "gatewayd", "vision_pilot", "actuation_adapter"]

FAKE_CLIENT = r'''#!/usr/bin/env python3
import json, os, signal, sys, time
d = os.environ["FAKE_DIR"]
with open(os.path.join(d, "client_argv.json"), "w") as f:
    json.dump({"argv": sys.argv[1:], "cwd": os.getcwd(), "ld": os.environ.get("LD_LIBRARY_PATH")}, f)
mode = open(os.path.join(d, "client_mode")).read().strip()
if mode == "garbage":
    print("mw::log: no configuration"); sys.exit(1)
rc = {"settle": 0, "reject": 4, "keep": 0}[mode]
if mode == "settle":
    for pid in open(os.path.join(d, "kill_pids")).read().split():
        os.kill(int(pid), signal.SIGTERM)
    time.sleep(0.3)
req_real, req_mono = time.time_ns(), time.monotonic_ns()
real, mono = (time.time_ns(), time.monotonic_ns()) if rc == 0 else (req_real, req_mono)
print(json.dumps({"runTarget": "path_stopped", "stopInstantRealNs": real, "stopInstantMonoNs": mono, "rc": rc,
                  "requestRealNs": req_real, "requestMonoNs": req_mono, "settledRealNs": real if rc == 0 else 0,
                  "settledMonoNs": mono if rc == 0 else 0, "settledTarget": "path_stopped" if rc == 0 else "",
                  "settledSource": "request" if rc == 0 else "", "earlierResults": 1,
                  "error": "" if rc == 0 else "activate_run_target(path_stopped): kRunTargetDoesntExist"},
                 separators=(",", ":")))
sys.exit(rc)
'''


class Host:
    def __init__(self, tmp: Path):
        self.tmp = tmp
        self.stage = tmp / "stage"
        self.bundle = tmp / "bundle"
        self.out = tmp / "out"
        self.fake = tmp / "fake"
        for d in (self.stage / "bin", self.stage / "state", self.stage / "lib", self.bundle / "bin",
                  self.bundle / "config" / "launch_manager", self.fake):
            d.mkdir(parents=True, exist_ok=True)
        self.procs: dict[str, subprocess.Popen] = {}

    def start(self, mode: str = "full", components: list[str] | None = None, lm: bool = True) -> None:
        for name in ["launch_manager", *COMPONENTS]:
            script = self.stage / "bin" / name
            script.write_text("#!/bin/bash\nwhile :; do sleep 0.2; done\n")
            script.chmod(0o755)
        if lm:
            self.procs["launch_manager"] = subprocess.Popen(["bash", str(self.stage / "bin" / "launch_manager")])
        for name in COMPONENTS if components is None else components:
            self.procs[name] = subprocess.Popen(["bash", str(self.stage / "bin" / name)])
        lm_pid = self.procs["launch_manager"].pid if lm else 999999
        (self.stage / "state" / "score_side.env").write_text(
            f"MODE={mode}\nSTAGE={self.stage}\nLM_PID={lm_pid}\nLM_BIN={self.stage}/bin/launch_manager\nSTATE=up\n")
        (self.stage / "state" / "staging.json").write_text(json.dumps({"stage": str(self.stage), "mode": mode,
                                                                       "bundle": str(self.bundle)}))
        client = self.bundle / "bin" / "lm_control_client"
        client.write_text(FAKE_CLIENT)
        client.chmod(0o755)
        (self.bundle / "config" / "launch_manager" / "mw_com_config_lm_control_client.json").write_text("{}\n")
        (self.fake / "kill_pids").write_text(" ".join(str(self.procs[n].pid) for n in
                                                      ("actuation_adapter", "gatewayd", "someipd")
                                                      if n in self.procs))

    def run(self, client_mode: str = "settle", **env: str) -> subprocess.CompletedProcess:
        (self.fake / "client_mode").write_text(client_mode)
        full_env = {k: v for k, v in os.environ.items() if not k.startswith(("DA_", "PYTHON"))}
        full_env.update({"DA_STAGE": str(self.stage), "DA_SUDO": "", "DA_PYTHON": sys.executable,
                         "DA_B2_BUNDLE": str(self.tmp / "no-bundle"), "FAKE_DIR": str(self.fake),
                         "DA_PATH_STOP_EFFECT_S": "2", **env})
        return subprocess.run(["bash", str(SCRIPT), str(self.out)], capture_output=True, text=True, env=full_env,
                              timeout=120)

    def stop(self) -> None:
        for proc in self.procs.values():
            if proc.poll() is None:
                proc.send_signal(signal.SIGTERM)
        for proc in self.procs.values():
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()


@pytest.fixture
def host(tmp_path: Path):
    h = Host(tmp_path)
    yield h
    h.stop()


def contract_line(result: subprocess.CompletedProcess) -> dict:
    lines = result.stdout.splitlines()
    assert len(lines) == 1, result.stdout + result.stderr
    doc = json.loads(lines[0])
    assert list(doc) == KEYS
    assert doc["runTarget"] == "path_stopped"
    for key in KEYS[1:]:
        assert isinstance(doc[key], int) and not isinstance(doc[key], bool), key
    assert doc["rc"] == result.returncode
    return doc


def test_the_path_stops_and_the_line_is_the_contract(host: Host) -> None:
    host.start()
    t0_real, t0_mono = time.time_ns(), time.monotonic_ns()
    result = host.run("settle")
    doc = contract_line(result)
    assert doc["rc"] == 0, (host.out / "path_stop.log").read_text()
    record = json.loads((host.out / "path_stop.json").read_text())
    client = record["clientRecord"]
    # the stop instant is the client's settlement, on both clocks of this host
    assert doc["stopInstantRealNs"] == client["settledRealNs"] and doc["stopInstantMonoNs"] == client["settledMonoNs"]
    assert t0_real < doc["stopInstantRealNs"] < time.time_ns()
    assert t0_mono < doc["stopInstantMonoNs"] < time.monotonic_ns()
    assert record["processesAfter"]["actuation_adapter"] == [] and record["processesAfter"]["gatewayd"] == []
    assert record["processesAfter"]["someipd"] == []
    assert record["processesAfter"]["vision_pilot"] == [host.procs["vision_pilot"].pid]
    assert record["processesBefore"]["actuation_adapter"] == [host.procs["actuation_adapter"].pid]
    assert record["bundle"] == str(host.bundle) and len(record["clientSha256"]) == 64
    called = json.loads((host.fake / "client_argv.json").read_text())
    assert called["argv"] == ["--run-target", "path_stopped", "--mw-com-config",
                              str(host.bundle / "config" / "launch_manager" / "mw_com_config_lm_control_client.json"),
                              "--settle-timeout-ms", "30000"]
    assert called["ld"] == str(host.stage / "lib")
    assert called["cwd"] == str(host.out)


def test_a_refused_request_passes_the_clients_rc_and_instant(host: Host) -> None:
    host.start()
    result = host.run("reject")
    doc = contract_line(result)
    assert doc["rc"] == 4
    record = json.loads((host.out / "path_stop.json").read_text())
    assert doc["stopInstantRealNs"] == record["clientRecord"]["requestRealNs"]
    assert "kRunTargetDoesntExist" in record["reason"]
    assert host.procs["actuation_adapter"].poll() is None  # nothing was stopped


def test_without_a_launch_manager_nothing_is_requested(host: Host) -> None:
    host.start(lm=False)
    before = time.time_ns()
    result = host.run("settle")
    doc = contract_line(result)
    assert doc["rc"] == 10
    assert before <= doc["stopInstantRealNs"] <= time.time_ns()
    assert not (host.fake / "client_argv.json").exists()


def test_mode_path_is_refused(host: Host) -> None:
    host.start(mode="path", components=["identity_recorder", "someipd", "gatewayd"])
    doc = contract_line(host.run("settle"))
    assert doc["rc"] == 10
    assert not (host.fake / "client_argv.json").exists()


def test_a_bundle_without_the_client_is_refused(host: Host) -> None:
    host.start()
    (host.bundle / "bin" / "lm_control_client").unlink()
    doc = contract_line(host.run("settle"))
    assert doc["rc"] == 11


def test_a_client_without_a_record_gives_rc_12(host: Host) -> None:
    host.start()
    doc = contract_line(host.run("garbage"))
    assert doc["rc"] == 12


def test_a_reported_switch_without_its_effect_gives_rc_13(host: Host) -> None:
    host.start()
    doc = contract_line(host.run("keep"))  # the client reports path_stopped, but nothing ended
    assert doc["rc"] == 13
    assert "actuation_adapter" in json.loads((host.out / "path_stop.json").read_text())["reason"]
