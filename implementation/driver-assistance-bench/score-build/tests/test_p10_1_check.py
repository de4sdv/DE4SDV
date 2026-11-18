"""Dry runs of score-build/scripts/p10_1_check.sh, the P10-1 check of the S-CORE host.

It runs as the session runs it (bash <entry> <out>, session/da_session.sh) against the fake bundle of
score-path/tests/fake_bundle.py, with stand-ins for the late subscriber (a script that reads the record file), for
ort_cuda_check (a script that prints the run times it is given) and for the test publisher (the publisher's real
plan and shell, ivi-warning/injector/tests/injector_driver.cpp). The fakes prove nothing about Lifecycle, mw::com
or the GPU; the tests show the script's verdict logic: one line per check, PASS, FAIL or NOT RUN, and exit 1 on
any FAIL.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
BENCH = HERE.parents[1]
sys.path.insert(0, str(BENCH / "score-path" / "tests"))
import fake_bundle  # noqa: E402

SCRIPT = BENCH / "score-build" / "scripts" / "p10_1_check.sh"
INJECTOR = BENCH / "ivi-warning" / "injector"

PROBE = """#!/usr/bin/env python3
import hashlib, json, os, sys, time
args = dict(zip(sys.argv[1::2], sys.argv[2::2]))
assert os.path.isfile(os.environ["MW_COM_CONFIG"])
time.sleep(float(args.get("--wait-s", "0")))
record = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), "..", "run", "score", "candidate_record.json")
data = open(record, "rb").read()
line = json.dumps({"check": "candidate_record_late_subscriber", "ok": True, "reason": "",
                   "record_sha256": hashlib.sha256(data).hexdigest(), "subscribed_real_ns": time.time_ns()},
                  separators=(",", ":"))
open(args["--out"], "w").write(line + "\\n")
print(line)
"""

ORT = """#!/bin/bash
# stand-in for ort_cuda_check: FAKE_ORT_MS="<first run>,<later runs>" per network
IFS=, read -r first later <<< "${FAKE_ORT_MS:-150,60}"
echo "model $1"
for ((k = 1; k <= $2; k++)); do
  [ "$k" = 1 ] && ms=$first || ms=$later
  echo "run $k: 3 outputs, $ms.000 ms"
done
echo "ORT_CUDA_CHECK PASS"
"""


@pytest.fixture(scope="module")
def binaries(tmp_path_factory: pytest.TempPathFactory) -> dict:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    out = tmp_path_factory.mktemp("bins")
    driver = fake_bundle.build_record_driver(out)
    injector = out / "injector_driver"
    subprocess.run([compiler, "-std=c++17", f"-I{INJECTOR}", f"-I{BENCH / 'interfaces' / 'include'}",
                    f"-I{BENCH / 'actuation-adapter'}", str(INJECTOR / "tests" / "injector_driver.cpp"),
                    str(INJECTOR / "injection_plan.cpp"), str(INJECTOR / "injector_shell.cpp"), "-o", str(injector)],
                   check=True)
    return {"driver": driver, "injector": injector}


@pytest.fixture()
def setup(tmp_path: Path, binaries: dict):
    s = fake_bundle.make_bundle(tmp_path, binaries["driver"],
                                extra_bins={"candidate_record_probe": PROBE, "ort_cuda_check": ORT})
    shutil.copy(binaries["injector"], s["bundle"] / "bin" / "warning_injector")
    s["env"].update({"DA_P10_1_LATE_WAIT_S": "0.5", "DA_P10_1_CUDA_RUNS": "5", "DA_P10_1_ALIVE_HOLD_S": "1",
                     "DA_P10_1_STALL_HOLD_S": "2", "DA_P10_1_SUPERVISED_WAIT_S": "10", "DA_INJECT_LEAD_IN_S": "0.2",
                     "DA_INJECT_TAIL_S": "0.1", "DA_TEST_SINK_FILE": str(tmp_path / "sent.hex")})
    for key in ("DA_P10_1_CARLA_HOST", "GATEWAYD_RX_REGEX", "DA_STUB_GATEWAYD_LINE", "FAKE_ORT_MS"):
        s["env"].pop(key, None)
    yield s
    subprocess.run(["bash", str(BENCH / "score-path" / "scripts" / "stop_score_side.sh"), str(tmp_path / "cleanup")],
                   env=s["env"], capture_output=True)


def run_check(setup: dict, out: Path, **env: str) -> tuple[int, dict[str, tuple[str, str]], str]:
    result = subprocess.run(["bash", str(SCRIPT), str(out)], capture_output=True, text=True,
                            env={**setup["env"], **env}, cwd=BENCH, timeout=300)
    rows = json.loads((out / "p10_1_verdicts.json").read_text())["checks"]
    verdicts = {r["check"].split("_", 1)[0]: (r["verdict"], r["detail"]) for r in rows}
    text = (out / "p10_1_verdicts.txt").read_text()
    assert len(text.splitlines()) == 8 == len(verdicts), text
    assert fake_bundle.staged_processes(setup["stage"]) == [], "a process outlived the check"
    return result.returncode, verdicts, result.stdout


def test_without_a_simulator(setup: dict, tmp_path: Path) -> None:
    rc, v, stdout = run_check(setup, tmp_path / "out")
    assert rc == 0, stdout
    assert v["C1"][0] == "PASS"
    assert v["C6"][0] == "PASS" and "worst of 4 later passes 180.0 ms" in v["C6"][1]
    assert v["C7"][0] == "PASS"
    assert v["C5"][0] == "NOT RUN" and "GATEWAYD_RX_REGEX" in v["C5"][1]
    for check in ("C2", "C3", "C4"):
        assert v[check][0] == "NOT RUN" and "CARLA" in v[check][1], check
    assert v["C8"][0] == "NOT RUN" and "clip replayer" in v["C8"][1]
    assert len((tmp_path / "sent.hex").read_text().split()) == 3  # the 3 sends of C5 went out
    assert "P10-1: 3 PASS, 0 FAIL, 5 NOT RUN" in stdout
    # the evidence of both starts is collected
    for part in ("path", "full"):
        assert (tmp_path / "out" / part / "score_side" / "run" / "score" / "candidate_record.json").is_file()


def test_with_a_ticking_world_every_check_runs(setup: dict, tmp_path: Path) -> None:
    rc, v, stdout = run_check(setup, tmp_path / "out", DA_P10_1_CARLA_HOST="127.0.0.1", DA_P10_1_SKIP_PORT_CHECK="1",
                              FAKE_LM_SUPERVISE="1", GATEWAYD_RX_REGEX="fake gatewayd forwarded",
                              DA_STUB_GATEWAYD_LINE="fake gatewayd forwarded 0x4df1")
    assert rc == 0, stdout
    for check in ("C1", "C2", "C3", "C4", "C5", "C6", "C7"):
        assert v[check][0] == "PASS", (check, v[check])
    assert v["C8"][0] == "NOT RUN"
    assert "the candidate sent 2 commands, the adapter accepted 1" in v["C4"][1]
    events = (tmp_path / "out" / "full" / "score_side" / "supervision_events.txt").read_text()
    assert "EXPIRED" in events and "fallback_run_target" in events


def test_a_candidate_that_is_not_taken_off_fails(setup: dict, tmp_path: Path) -> None:
    rc, v, _ = run_check(setup, tmp_path / "out", DA_P10_1_CARLA_HOST="127.0.0.1", DA_P10_1_SKIP_PORT_CHECK="1")
    assert rc == 1
    assert v["C3"][0] == "FAIL" and "no switch to fallback_run_target" in v["C3"][1]
    assert v["C2"][0] == "PASS"


def test_a_slow_cuda_pass_fails(setup: dict, tmp_path: Path) -> None:
    rc, v, _ = run_check(setup, tmp_path / "out", FAKE_ORT_MS="2000,100")
    assert v["C6"][0] == "PASS"  # the first pass may be slow
    rc, v, _ = run_check(setup, tmp_path / "out2", FAKE_ORT_MS="150,140")
    assert rc == 1 and v["C6"][0] == "FAIL" and "worst of 4 later passes 420.0 ms" in v["C6"][1]


def test_a_silent_gatewayd_fails(setup: dict, tmp_path: Path) -> None:
    rc, v, _ = run_check(setup, tmp_path / "out", GATEWAYD_RX_REGEX="never printed")
    assert rc == 1 and v["C5"][0] == "FAIL" and "0 lines match" in v["C5"][1]


def test_without_the_probe_and_the_cuda_check(setup: dict, tmp_path: Path) -> None:
    (setup["bundle"] / "bin" / "candidate_record_probe").unlink()
    (setup["bundle"] / "bin" / "ort_cuda_check").unlink()
    rc, v, _ = run_check(setup, tmp_path / "out")
    assert rc == 0
    assert v["C7"][0] == "NOT RUN" and v["C6"][0] == "NOT RUN"


def test_the_entry_is_the_sessions() -> None:
    env = (BENCH / "session" / "entrypoints.env").read_text()
    assert "ENTRY_SCORE_P10_1:=score-build/scripts/p10_1_check.sh" in env
    assert 'bash "$ENTRY_SCORE_P10_1" "$(od p10_1)"' in (BENCH / "session" / "da_session.sh").read_text()
    assert subprocess.run(["bash", "-n", str(SCRIPT)]).returncode == 0
