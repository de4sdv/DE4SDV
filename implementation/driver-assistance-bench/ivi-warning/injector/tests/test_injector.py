"""The warning-request test publisher of P10-3: its C++ units, its contracts, and inject_warning_requests.sh.

The plan and the shell build with the host's g++ (C++17 and C++20) and run with a fake mw::com sink and a fake
clock (injector_test.cpp). The 8 bytes are compared with Python's struct at test time. warning_injector_main.cpp is
compiled for syntax against the closed-loop bench's local mw::com mock (a mock, NOT S-CORE). The script runs as
in the session against a fake stage and state, with injector_driver (the real plan and shell, a file for a sink)
as bin/warning_injector. Evidence of the path, not of the candidate (brief R1).
"""

from __future__ import annotations

import json
import os
import re
import shutil
import struct
import subprocess
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
INJECTOR = HERE.parent
WARNING = INJECTOR.parent
BENCH = WARNING.parent
ADAPTER = BENCH / "actuation-adapter"
INCLUDE = BENCH / "interfaces" / "include"
MWCOM_MOCK = BENCH.parent / "closed-loop-driving-bench" / "state-publisher" / "tests" / "mock"
SEQUENCE = INJECTOR / "config" / "p10_3_sequence.txt"
SCRIPT = WARNING / "scripts" / "inject_warning_requests.sh"
MANIFEST = INJECTOR / "mw_com_config_warning_injector.json"
FLAGS = ["-Wall", "-Wextra", "-Werror", "-pedantic", f"-I{INJECTOR}", f"-I{INCLUDE}", f"-I{ADAPTER}",
         f"-I{ADAPTER / 'tests'}"]
CORE = [INJECTOR / "injection_plan.cpp", INJECTOR / "injector_shell.cpp"]


def compiler() -> str:
    found = shutil.which("g++")
    if found is None:
        pytest.skip("g++ is not installed")
    return found


def build(source: Path, out: Path, standard: str = "c++17") -> Path:
    subprocess.run([compiler(), f"-std={standard}", *FLAGS, str(source), *map(str, CORE), "-o", str(out)],
                   check=True)
    return out


@pytest.mark.parametrize("standard", ["c++17", "c++20"])
def test_unit_binary(tmp_path: Path, standard: str) -> None:
    binary = build(HERE / "injector_test.cpp", tmp_path / "injector_test", standard)
    result = subprocess.run([str(binary), str(SEQUENCE)], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "injector_test: all passed" in result.stdout


@pytest.mark.parametrize("requested,issue", [("true", "1002.0"), ("false", "0.05"), ("1", "4294967.295"),
                                             ("0", "12.3456")])
def test_the_bytes_are_the_icds(tmp_path: Path, requested: str, issue: str) -> None:
    binary = build(HERE / "injector_test.cpp", tmp_path / "injector_test")
    out = subprocess.run([str(binary), "--encode", requested, issue], capture_output=True, text=True, check=True)
    expected = struct.pack(">II", 1 if requested in ("true", "1") else 0, round(float(issue) * 1000))
    assert out.stdout.strip() == expected.hex()


def test_the_main_compiles_for_syntax_against_the_mwcom_mock(tmp_path: Path) -> None:
    subprocess.run([compiler(), "-std=c++17", "-Wall", "-Wextra", "-Werror", "-fsyntax-only", "-isystem",
                    str(MWCOM_MOCK), *FLAGS, str(INJECTOR / "warning_injector_main.cpp")], check=True, cwd=tmp_path)


def icd_warning_row() -> list[str]:
    for line in (BENCH / "interfaces" / "ICD.md").read_text(encoding="utf-8").splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if cells and cells[0] == "MAP-DRIVING-DA-WARNING-REQUEST":
            return cells
    raise AssertionError("no MAP-DRIVING-DA-WARNING-REQUEST row in ICD.md")


def test_the_manifest_is_the_candidates_warning_instance_in_an_asil_b_process() -> None:
    ours = json.loads(MANIFEST.read_text(encoding="utf-8"))
    candidate = json.loads((BENCH / "score-path" / "config" / "mw_com_config_vision_pilot.json").read_text())
    name = "/de4sdv/driver_assistance/WarningRequest"
    assert ours["serviceTypes"] == [s for s in candidate["serviceTypes"] if s["serviceTypeName"] == name]
    assert ours["serviceInstances"] == [s for s in candidate["serviceInstances"] if s["serviceTypeName"] == name]
    assert ours["global"]["asil-level"] == candidate["global"]["asil-level"] == "B"
    assert ours["global"]["applicationID"] == 3415
    row = icd_warning_row()
    assert ours["serviceInstances"][0]["instanceSpecifier"] == row[2].strip("`")
    assert ours["serviceTypes"][0]["bindings"][0]["serviceId"] == int(row[3])
    gatewayd = json.loads((BENCH / "score-path" / "config" / "mw_com_config_gatewayd_warning.json").read_text())
    assert [s for s in gatewayd["serviceTypes"] if s["serviceTypeName"] == name] == ours["serviceTypes"]
    main = (INJECTOR / "warning_injector_main.cpp").read_text(encoding="utf-8")
    assert re.search(r'kWarningSpecifier = "' + re.escape(row[2].strip("`")) + '"', main)
    assert 'Event<WarningRequestSample> warning_request{*this, "warning_request"}' in main
    # the sample's capacity is the gateway's max_message_size, as the candidate's binding has it
    gateway = json.loads((BENCH / "score-path" / "config" / "someip_gateway_config_warning.json").read_text())
    assert "2048" in json.dumps(gateway)
    assert re.search(r"kWarningRequestSampleCapacity = 2048;", main)


def test_every_source_includes_cstdint_and_is_in_bazel() -> None:
    build_file = (INJECTOR / "BUILD.bazel").read_text(encoding="utf-8")
    for path in sorted(INJECTOR.glob("*.cpp")) + sorted(INJECTOR.glob("*.h")) + sorted(HERE.glob("*.cpp")):
        text = path.read_text(encoding="utf-8")
        if re.search(r"\bu?int(8|16|32|64)_t\b", text):
            assert "#include <cstdint>" in text, path.name
        if path.parent == INJECTOR:
            assert f'"{path.name}"' in build_file, path.name


# --- inject_warning_requests.sh, as the session runs it -------------------------------------------------------


@pytest.fixture()
def stage(tmp_path: Path) -> dict:
    driver = build(HERE / "injector_driver.cpp", tmp_path / "injector_driver")
    root = tmp_path / "de4sdv-da-bench"
    (root / "bin").mkdir(parents=True)
    (root / "config").mkdir()
    (root / "state").mkdir()
    shutil.copy(driver, root / "bin" / "warning_injector")
    shutil.copy(MANIFEST, root / "config" / MANIFEST.name)
    procs = []
    for name in ("identity_recorder", "someipd", "gatewayd"):
        stub = root / "bin" / name
        stub.write_text("#!/bin/bash\nsleep 60\n")
        stub.chmod(0o755)
        procs.append(subprocess.Popen([str(stub)]))
    holder = subprocess.Popen(["sleep", "60"])
    procs.append(holder)
    state = root / "state" / "score_side.env"
    state.write_text(f"MODE=path\nLM_PID={holder.pid}\nSTATE=starting\nSTATE=up\n")
    env = {**os.environ, "DA_STAGE": str(root), "DA_SUDO": "", "DA_INJECT_LEAD_IN_S": "0.2",
           "DA_INJECT_TAIL_S": "0.1", "DA_TEST_SINK_FILE": str(tmp_path / "sent.hex")}
    time.sleep(0.3)
    yield {"root": root, "state": state, "env": env, "sent": tmp_path / "sent.hex", "tmp": tmp_path}
    for p in procs:
        p.kill()
        p.wait()


def write_sequence(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n")
    return path


def test_the_script_sends_the_sequence_and_logs_each_send(stage: dict) -> None:
    seq = write_sequence(stage["tmp"] / "seq.txt", ["0 false 50.0", "0.2 true 50.05", "0.4 false 50.1"])
    out = stage["tmp"] / "out"
    result = subprocess.run(["bash", str(SCRIPT), str(out)], capture_output=True, text=True,
                            env={**stage["env"], "DA_INJECT_SEQUENCE": str(seq)}, cwd=BENCH)
    assert result.returncode == 0, result.stdout + result.stderr
    sent = stage["sent"].read_text().split()
    assert sent == [struct.pack(">II", 0, 50000).hex(), struct.pack(">II", 1, 50050).hex(),
                    struct.pack(">II", 0, 50100).hex()]
    records = [json.loads(line) for line in (out / "warning_injector.jsonl").read_text().splitlines()]
    sends = [r for r in records if r["event"] == "out.warning_request"]
    assert [s["data"]["bytes"] for s in sends] == sent
    for s in sends:
        d = s["data"]
        assert d["ok"] is True
        assert d["send_mono_ns"] <= d["sent_mono_ns"] and d["send_real_ns"] <= d["sent_real_ns"]
        assert abs(d["send_real_ns"] / 1e9 - time.time()) < 120
    gaps = [(b["data"]["send_mono_ns"] - a["data"]["send_mono_ns"]) / 1e9 for a, b in zip(sends, sends[1:])]
    assert all(0.15 < g < 0.6 for g in gaps), gaps
    for name in ("sequence.txt", "inputs.sha256", "clock_before.txt", "clock_after.txt"):
        assert (out / name).is_file(), name
    assert "real_ns" in (out / "clock_before.txt").read_text()
    assert "3 requests sent" in (out / "inject_warning_requests.log").read_text()


def test_the_script_refuses_without_the_path_mode(stage: dict) -> None:
    out = stage["tmp"] / "out"
    stage["state"].write_text(stage["state"].read_text().replace("MODE=path", "MODE=full"))
    result = subprocess.run(["bash", str(SCRIPT), str(out)], capture_output=True, text=True, env=stage["env"])
    assert result.returncode == 9 and "mode full" in result.stdout
    assert not stage["sent"].exists()


def test_the_script_refuses_while_the_candidate_runs(stage: dict) -> None:
    stub = stage["root"] / "bin" / "vision_pilot"
    stub.write_text("#!/bin/bash\nsleep 60\n")
    stub.chmod(0o755)
    candidate = subprocess.Popen([str(stub)])
    try:
        time.sleep(0.3)
        result = subprocess.run(["bash", str(SCRIPT), str(stage["tmp"] / "out")], capture_output=True, text=True,
                                env=stage["env"])
        assert result.returncode == 9 and "candidate's process runs" in result.stdout
    finally:
        candidate.kill()
        candidate.wait()


def test_the_script_refuses_when_the_side_is_down(stage: dict) -> None:
    stage["state"].write_text("MODE=path\nSTATE=stopped\n")
    result = subprocess.run(["bash", str(SCRIPT), str(stage["tmp"] / "out")], capture_output=True, text=True,
                            env=stage["env"])
    assert result.returncode == 9 and "not up" in result.stdout


def test_the_publishers_failures_pass_through(stage: dict) -> None:
    out = stage["tmp"] / "out"
    result = subprocess.run(["bash", str(SCRIPT), str(out)], capture_output=True, text=True,
                            env={**stage["env"], "DA_TEST_OFFER_FAIL": "1"})
    assert result.returncode == 4
    bad = write_sequence(stage["tmp"] / "bad.txt", ["0 true 1.0", "0 false 2.0"])
    result = subprocess.run(["bash", str(SCRIPT), str(stage["tmp"] / "out2")], capture_output=True, text=True,
                            env={**stage["env"], "DA_INJECT_SEQUENCE": str(bad)})
    assert result.returncode == 3
