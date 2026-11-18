"""Dry runs of the S-CORE host's entry scripts: start_score_side.sh and stop_score_side.sh, with their staging.

They run as the session runs them (bash <entry> <out> <carla_host or none>, session/da_session.sh), against a fake
bundle (fake_bundle.py): stub components, a fake Launch Manager, and the identity recorder's real shell, which
hashes the staged tree. The fakes prove nothing about Lifecycle or mw::com; what they show is the scripts' own
logic: the staging, the root-less dry run of the start as root, the wait for the recorder's report and the
processes, the state, the stop with SIGTERM, the forced stop, and the collection.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

TESTS = Path(__file__).resolve().parent
sys.path.insert(0, str(TESTS))
import fake_bundle  # noqa: E402

BENCH = TESTS.parents[1]
SCRIPTS = BENCH / "score-path" / "scripts"
START = SCRIPTS / "start_score_side.sh"
STOP = SCRIPTS / "stop_score_side.sh"
STAGE_PY = SCRIPTS / "stage_score_side.py"
DERIVE = SCRIPTS / "derive_path_only_config.py"
LAUNCH = BENCH / "launch-manager" / "config" / "launch_manager_config.json"
PATH_ONLY = BENCH / "score-path" / "config" / "launch_manager_config_path_only.json"
PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"


@pytest.fixture(scope="module")
def record_driver(tmp_path_factory: pytest.TempPathFactory) -> Path:
    try:
        return fake_bundle.build_record_driver(tmp_path_factory.mktemp("driver"))
    except RuntimeError as error:
        pytest.skip(str(error))


@pytest.fixture()
def bench(tmp_path: Path, record_driver: Path):
    setup = fake_bundle.make_bundle(tmp_path, record_driver)
    yield setup
    # never leave a process behind
    subprocess.run(["bash", str(STOP), str(tmp_path / "cleanup")], env=setup["env"], capture_output=True)
    for line in fake_bundle.staged_processes(setup["stage"]):
        print("left over:", line)


def run(script: Path, *args: str, env: dict, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(script), *args], capture_output=True, text=True, env=env, cwd=BENCH,
                          timeout=timeout)


def state(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text().splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            values[key] = value
    return values


# --- the derived path-only configuration -----------------------------------------------------------------------


def test_the_path_only_configuration_is_up_to_date() -> None:
    result = subprocess.run([sys.executable, str(DERIVE), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


def test_the_path_only_configuration_drops_only_the_candidate_and_the_adapter_from_the_run_target() -> None:
    full = json.loads(LAUNCH.read_text())
    path = json.loads(PATH_ONLY.read_text())
    assert path["components"] == full["components"]
    assert path["fallback_run_target"] == full["fallback_run_target"]
    assert path["initial_run_target"] == full["initial_run_target"] == "supervised_path"
    assert path["run_targets"]["supervised_path"]["depends_on"] == ["identity_recorder", "someipd", "gatewayd"]
    assert path["run_targets"]["supervised_path"]["depends_on"] == full["fallback_run_target"]["depends_on"]
    for key in ("transition_timeout_ms", "recovery_action"):
        assert path["run_targets"]["supervised_path"][key] == full["run_targets"]["supervised_path"][key]


# --- staging ---------------------------------------------------------------------------------------------------


def stage(setup: dict, *extra: str, mode: str = "full", carla: str = "10.164.0.2") -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(STAGE_PY), "--bundle", str(setup["bundle"]), "--stage",
                           str(setup["stage"]), "--mode", mode, "--carla-host", carla, "--upstream-revision", PIN,
                           "--allow-any-stage", *extra], capture_output=True, text=True)


def test_staging_lays_out_what_the_launch_manager_configuration_names(bench: dict) -> None:
    result = stage(bench, "--speed-limit", "5.833")
    assert result.returncode == 0, result.stderr
    root = bench["stage"]
    config = json.loads((root / "config" / "launch_manager_config.json").read_text())
    assert config["defaults"]["deployment_config"]["bin_dir"] == str(root / "bin")
    for name, comp in config["components"].items():
        binary = root / "bin" / comp["component_properties"]["binary_name"]
        assert binary.is_file() and os.access(binary, os.X_OK), name
        for arg in comp["component_properties"].get("process_arguments", []):
            if arg.startswith(str(root)) and not arg.endswith("/run"):
                assert Path(arg).is_file(), (name, arg)
        for key, value in comp.get("deployment_config", {}).get("environmental_variables", {}).items():
            if key in ("MW_COM_CONFIG", "VSOMEIP_CONFIGURATION", "DE4SDV_SCORE_INTERFACE_CONFIG"):
                assert Path(value).is_file(), (name, key, value)
    vp = root / "vision_pilot"
    for rel in ("config/vision_pilot.conf", "config/H.yaml", "config/homography_C_matrix.yaml",
                "modules/models/weights/autosteer_fp32.onnx", "assets/icon.png"):
        assert (vp / rel).is_file(), rel
    conf = (vp / "config" / "vision_pilot.conf").read_text()
    lines = {line.split("=")[0].strip(): line for line in conf.splitlines() if "=" in line}
    assert lines["source.mode"].split("=")[1].strip() == "score"
    assert lines["visualization_on"].split("=")[1].strip() == "false"
    assert lines["rrd_on"].split("=")[1].strip() == "true"
    assert lines["engine.provider"].split("=")[1].strip() == "cuda"
    assert lines["speed_limit"] == "speed_limit      = 5.833;   # m/s"
    assert lines["L"] == "L                = 2.860   # wheelbase part"  # upstream's value stays
    interface = (root / "config" / "de4sdv_score_interface.conf").read_text()
    assert f"mw_com.config = {root}/config/mw_com_config_vision_pilot.json" in interface
    assert "carla.host = 10.164.0.2" in interface and "carla.camera_role = front" in interface
    assert json.loads((root / "config" / "adapter.json").read_text())["carla_host"] == "10.164.0.2"
    assert (root / "etc" / "launch_manager_config.bin").read_bytes() == b"synthetic flatbuffer full"
    assert (root / "facts" / "upstream_revision.txt").read_text() == PIN + "\n"
    assert sorted(p.name for p in (root / "facts").glob("*.diff")) == sorted(
        p.name for p in (BENCH / "score-interface" / "patches").glob("*.diff"))
    summary = json.loads((root / "state" / "staging.json").read_text())
    for path, digest in summary["files"].items():
        assert hashlib.sha256(Path(path).read_bytes()).hexdigest() == digest, path


def test_staging_in_path_mode_takes_the_path_only_configuration(bench: dict) -> None:
    result = stage(bench, mode="path", carla="none")
    assert result.returncode == 0, result.stderr
    root = bench["stage"]
    config = json.loads((root / "config" / "launch_manager_config.json").read_text())
    assert config["run_targets"]["supervised_path"]["depends_on"] == ["identity_recorder", "someipd", "gatewayd"]
    assert (root / "etc" / "launch_manager_config.bin").read_bytes() == b"synthetic flatbuffer path"
    assert "carla.host = none" in (root / "config" / "de4sdv_score_interface.conf").read_text()


def test_staging_refuses_what_it_lacks(bench: dict) -> None:
    (bench["bundle"] / "config" / "visionpilot" / "homography_C_matrix.yaml").unlink()
    result = stage(bench)
    assert result.returncode == 3 and "calibration" in result.stderr
    calibration = bench["root"] / "calib"
    calibration.mkdir()
    (calibration / "H.yaml").write_text("H: from the world side\n")
    (calibration / "homography_C_matrix.yaml").write_text("C: from the world side\n")
    assert stage(bench, "--calibration-dir", str(calibration)).returncode == 0
    assert (bench["stage"] / "vision_pilot/config/H.yaml").read_text() == "H: from the world side\n"
    (bench["bundle"] / "etc" / "launch_manager_config.bin").unlink()
    result = stage(bench, "--calibration-dir", str(calibration), "--require-serialized")
    assert result.returncode == 3 and "serialized" in result.stderr
    (bench["bundle"] / "bin" / "gatewayd").unlink()
    assert stage(bench, "--calibration-dir", str(calibration)).returncode == 3
    other = subprocess.run([sys.executable, str(STAGE_PY), "--bundle", str(bench["bundle"]), "--stage",
                            str(bench["root"] / "elsewhere"), "--mode", "path", "--carla-host", "none",
                            "--upstream-revision", PIN], capture_output=True, text=True)
    assert other.returncode != 0 and "refusing" in (other.stdout + other.stderr)
    full_without_carla = stage(bench, mode="full", carla="none")
    assert full_without_carla.returncode == 2


# --- start and stop --------------------------------------------------------------------------------------------


def test_full_start_then_stop(bench: dict, tmp_path: Path) -> None:
    out = tmp_path / "out"
    started = run(START, str(out), "10.164.0.2", env=bench["env"])
    assert started.returncode == 0, started.stdout + started.stderr
    s = state(out / "score_side_state.env")
    assert s["MODE"] == "full" and s["STATE"] == "up"
    for name in ("identity_recorder", "someipd", "gatewayd", "vision_pilot", "actuation_adapter"):
        assert s[f"PID_{name}"], name
    root = bench["stage"]
    record = root / "run" / "score" / "candidate_record.json"
    assert hashlib.sha256(record.read_bytes()).hexdigest() == s["RECORD_SHA256"]
    # the record hashes the staged tree as the processes find it
    data = json.loads(record.read_text())
    assert data["upstream_revision"] == PIN
    for key in ("configuration_files", "network_files", "binaries", "runtime_libraries"):
        for item in data[key]:
            assert hashlib.sha256(Path(item["path"]).read_bytes()).hexdigest() == item["sha256"], item["path"]
    assert data["configuration_files"][0]["path"] == str(root / "vision_pilot/config/vision_pilot.conf")
    assert data["launch_settings"]["launch_config_text"] == (root / "config/launch_manager_config.json").read_text()
    # the Launch Manager's order: the candidate and the adapter after the recorder's report
    lm_log = (root / "state" / "launch_manager.log").read_text()
    assert lm_log.index("identity_recorder ready") < lm_log.index("started vision_pilot")
    assert lm_log.index("identity_recorder ready") < lm_log.index("started actuation_adapter")
    assert lm_log.index("started someipd") < lm_log.index("started gatewayd")
    stub_log = (root / "run/score/stubs/vision_pilot.log").read_text()
    assert f"cwd {root}/vision_pilot" in stub_log and "LCM_ALIVE_INTERFACE_PATH=/fake/alive/vision_pilot" in stub_log
    # a second start is refused while this one runs
    again = run(START, str(tmp_path / "again"), "10.164.0.2", env=bench["env"])
    assert again.returncode == 4
    # stop
    stopped = run(STOP, str(out), env=bench["env"])
    assert stopped.returncode == 0, stopped.stdout + stopped.stderr
    assert fake_bundle.staged_processes(root) == []
    collected = out / "score_side"
    for rel in ("state/launch_manager.log", "run/score/candidate_record.json", "run/score/identityRecorder.jsonl",
                "vision_pilot/visionpilot.rrd", "config/launch_manager_config.json", "upstream_revision.txt",
                "SHA256SUMS"):
        assert (collected / rel).is_file(), rel
    assert not (collected / "vision_pilot" / "config").exists()  # the staged inputs are not collected twice
    for line in (collected / "SHA256SUMS").read_text().splitlines():
        digest, rel = line.split("  ", 1)
        assert hashlib.sha256((collected / rel).read_bytes()).hexdigest() == digest, rel
    log_lines = [json.loads(line) for line in (collected / "run/score/identityRecorder.jsonl").read_text().splitlines()]
    assert log_lines[-1]["event"] == "stop"
    assert "SIGTERM" in (collected / "state/launch_manager.log").read_text()
    assert (out / "clock_start.txt").is_file() and (out / "clock_stop.txt").is_file()
    assert not (root / "state" / "score_side.env").exists()
    assert "STATE=stopped rc=0" in (root / "state" / "score_side.env.stopped").read_text()


def test_path_start_runs_the_warning_path_only(bench: dict, tmp_path: Path) -> None:
    out = tmp_path / "out"
    started = run(START, str(out), "none", env=bench["env"])
    assert started.returncode == 0, started.stdout + started.stderr
    s = state(out / "score_side_state.env")
    assert s["MODE"] == "path"
    assert "PID_vision_pilot" not in s and "PID_actuation_adapter" not in s
    running = "\n".join(fake_bundle.staged_processes(bench["stage"]))
    assert "/bin/identity_recorder" in running and "/bin/gatewayd" in running
    assert "/bin/vision_pilot" not in running and "/bin/actuation_adapter" not in running
    assert run(STOP, str(out), env=bench["env"]).returncode == 0


def test_no_record_means_no_candidate(bench: dict, tmp_path: Path) -> None:
    (bench["ldconf"] / "de4sdv-cuda-12.8.1.conf").unlink()
    out = tmp_path / "out"
    env = {**bench["env"], "DA_START_TIMEOUT_S": "4"}
    started = run(START, str(out), "10.164.0.2", env=env)
    assert started.returncode in (5, 6), started.stdout
    lm_log = (out / "score_side" / "state" / "launch_manager.log").read_text()
    assert "started vision_pilot" not in lm_log and "started actuation_adapter" not in lm_log
    assert not (bench["stage"] / "run" / "score" / "candidate_record.json").exists()
    assert fake_bundle.staged_processes(bench["stage"]) == []


def test_a_launch_manager_that_ends_fails_the_start(bench: dict, tmp_path: Path) -> None:
    env = {**bench["env"], "FAKE_LM_EXIT_AFTER_S": "0.5"}
    (bench["bundle"] / "bin" / "identity_recorder").write_text("#!/bin/bash\nsleep 30\n")  # never reports
    started = run(START, str(tmp_path / "out"), "none", env=env)
    assert started.returncode == 5 and "the Launch Manager ended" in started.stdout
    assert fake_bundle.staged_processes(bench["stage"]) == []


def test_a_launch_manager_that_ignores_sigterm_is_killed(bench: dict, tmp_path: Path) -> None:
    out = tmp_path / "out"
    env = {**bench["env"], "FAKE_LM_IGNORE_TERM": "1", "DA_STOP_TIMEOUT_S": "2"}
    assert run(START, str(out), "none", env=env).returncode == 0
    stopped = run(STOP, str(out), env=env)
    assert stopped.returncode == 7 and "FORCED" in stopped.stdout
    time.sleep(0.5)
    assert fake_bundle.staged_processes(bench["stage"]) == []
    assert (out / "score_side" / "run" / "score" / "candidate_record.json").is_file()


def test_stop_without_a_start_is_harmless(bench: dict, tmp_path: Path) -> None:
    stopped = run(STOP, str(tmp_path / "out"), env=bench["env"])
    assert stopped.returncode == 0 and "nothing was started" in stopped.stdout


def test_the_entries_are_the_sessions() -> None:
    env = (BENCH / "session" / "entrypoints.env").read_text()
    assert "ENTRY_SCORE_START:=score-path/scripts/start_score_side.sh" in env
    assert "ENTRY_SCORE_STOP:=score-path/scripts/stop_score_side.sh" in env
    session = (BENCH / "session" / "da_session.sh").read_text()
    assert 'bash "$ENTRY_SCORE_START" "$(od score)" "${CARLA_HOST:-none}"' in session
    assert 'bash "$ENTRY_SCORE_STOP" "$(od score)"' in session
    for script in (START, STOP):
        assert os.access(script, os.X_OK)
        assert subprocess.run(["bash", "-n", str(script)]).returncode == 0
