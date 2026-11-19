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
import re
import signal
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
    result = stage(bench, "--speed-limit", "5.833", "--calibration-dir", str(bench["calibration"]))
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


@pytest.mark.parametrize("mode,carla,json_name", [
    ("full", "10.164.0.2", "launch_manager_config.json"), ("path", "none", "launch_manager_config_path_only.json")])
def test_staging_takes_a_serialized_configuration_only_beside_the_benchs_json(bench: dict, mode: str, carla: str,
                                                                            json_name: str) -> None:
    launch = bench["bundle"] / "config" / "launch_manager"
    ok = stage(bench, "--calibration-dir", str(bench["calibration"]), "--require-serialized", mode=mode, carla=carla)
    assert ok.returncode == 0, ok.stderr
    record = json.loads((bench["stage"] / "state" / "staging.json").read_text())["serialized_launch_config"]
    assert record["built_from"] == str(launch / json_name) and record["bundle_path"].endswith(
        json_name.replace(".json", ".bin"))
    assert record["built_from_sha256"] == hashlib.sha256((launch / json_name).read_bytes()).hexdigest()
    # a .bin converted from another JSON than the bench's: the daemon would run what the record does not name
    (launch / json_name).write_text((launch / json_name).read_text() + "\n")
    stale = stage(bench, "--calibration-dir", str(bench["calibration"]), mode=mode, carla=carla)
    assert stale.returncode == 3 and "differs from the bench's" in stale.stderr
    (launch / json_name).unlink()  # no JSON beside the .bin: cannot tell what it was converted from
    missing = stage(bench, "--calibration-dir", str(bench["calibration"]), "--require-serialized", mode=mode,
                    carla=carla)
    assert missing.returncode == 3 and "the JSON beside it is missing" in missing.stderr


LM_MW_COM = BENCH / "launch-manager" / "config" / "mw_com_config_launch_manager.json"


@pytest.mark.parametrize("mode,carla", [("full", "10.164.0.2"), ("path", "none")])
def test_staging_puts_the_launch_managers_mw_com_configuration_where_the_daemon_reads_it(
        bench: dict, mode: str, carla: str) -> None:
    """The daemon's LmControl skeleton makes mw::com read ./etc/mw_com_config.json in its working directory, the
    stage (launch-manager/tests/test_launch_manager_mw_com_config.py); session 4's daemon aborted without it."""
    ok = stage(bench, "--calibration-dir", str(bench["calibration"]), "--require-serialized", mode=mode, carla=carla)
    assert ok.returncode == 0, ok.stderr
    staged = bench["stage"] / "etc" / "mw_com_config.json"
    assert staged.read_bytes() == LM_MW_COM.read_bytes()
    summary = json.loads((bench["stage"] / "state" / "staging.json").read_text())
    record = summary["launch_manager_mw_com_config"]
    bundle_file = bench["bundle"] / "config" / "launch_manager" / "mw_com_config_launch_manager.json"
    assert record == {"bundle_path": str(bundle_file), "sha256": hashlib.sha256(LM_MW_COM.read_bytes()).hexdigest(),
                      "bench_file": "launch-manager/config/mw_com_config_launch_manager.json",
                      "staged_path": str(staged)}
    assert summary["files"][str(staged)] == record["sha256"]


@pytest.mark.parametrize("mode,carla", [("full", "10.164.0.2"), ("path", "none")])
def test_staging_takes_the_launch_managers_mw_com_configuration_only_when_it_is_the_benchs(
        bench: dict, mode: str, carla: str) -> None:
    bundle_file = bench["bundle"] / "config" / "launch_manager" / "mw_com_config_launch_manager.json"
    # another file than the bench's (here: another applicationID): the daemon would run what the bench does not name
    bundle_file.write_text(bundle_file.read_text().replace("3417", "3410"))
    other = stage(bench, "--calibration-dir", str(bench["calibration"]), mode=mode, carla=carla)
    assert other.returncode == 3 and "mw_com_config_launch_manager.json" in other.stderr
    assert "differs from the bench's" in other.stderr
    bundle_file.unlink()
    missing = stage(bench, "--calibration-dir", str(bench["calibration"]), "--require-serialized", mode=mode,
                    carla=carla)
    assert missing.returncode == 3 and "mw::com configuration" in missing.stderr


def test_a_start_without_the_launch_managers_mw_com_configuration_fails_as_on_the_l4(bench: dict,
                                                                                     tmp_path: Path) -> None:
    """Session 4's rehearsal on the real L4: no etc/mw_com_config.json, the daemon aborts at once. The start must
    refuse before it starts a daemon that cannot run."""
    (bench["bundle"] / "config" / "launch_manager" / "mw_com_config_launch_manager.json").unlink()
    out = tmp_path / "out"
    started = run(START, str(out), "none", env=bench["env"])
    assert started.returncode == 3, started.stdout
    assert "mw::com configuration" in started.stdout + started.stderr
    assert fake_bundle.staged_processes(bench["stage"]) == []


def test_staging_refuses_what_it_lacks(bench: dict) -> None:
    calibration = bench["calibration"]
    assert stage(bench, "--calibration-dir", str(calibration)).returncode == 0
    assert (bench["stage"] / "vision_pilot/config/H.yaml").read_text() == "H: synthetic session calibration\n"
    (bench["bundle"] / "config" / "launch_manager" / "launch_manager_config.bin").unlink()
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
    # the daemon's environment: the configured one only, no HOME; LibCarla's cache dir instead (as on the L4)
    for name in ("vision_pilot", "actuation_adapter"):
        line = (root / f"run/score/stubs/{name}.log").read_text().splitlines()[0]
        assert f"HOME= CARLA_CACHE_DIR={root}/run/carla_cache" in line, line
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
    # the session lane's calls: "$(od score)" at this base, "$(od "score_$w")" per p10-2 run after the session lane
    assert re.search(r'bash "\$ENTRY_SCORE_START" \\?\s*"\$\(od "?score', session)
    assert re.search(r'bash "\$ENTRY_SCORE_STOP" "\$\(od "?score', session)
    for script in (START, STOP):
        assert os.access(script, os.X_OK)
        assert subprocess.run(["bash", "-n", str(script)]).returncode == 0


# --- the camera calibration (the session lane's contract of 2026-11-18) ------------------------------------------


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_staging_never_falls_back_to_the_bundle_in_mode_full(bench: dict) -> None:
    # the bundle has both upstream files, and still mode full refuses without the session's calibration
    assert (bench["bundle"] / "config" / "visionpilot" / "H.yaml").is_file()
    result = stage(bench)
    assert result.returncode == 3 and "DA_CAMERA_CALIBRATION_DIR" in result.stderr
    assert not (bench["stage"] / "vision_pilot" / "config" / "H.yaml").exists()
    # a given directory that lacks a file is refused in both modes, never completed from the bundle
    partial = bench["root"] / "partial"
    partial.mkdir()
    (partial / "H.yaml").write_text("H: alone\n")
    for mode, carla in (("full", "10.164.0.2"), ("path", "none")):
        result = stage(bench, "--calibration-dir", str(partial), mode=mode, carla=carla)
        assert result.returncode == 3 and "homography_C_matrix.yaml" in result.stderr, mode
    # mode path runs no candidate: there the bundle's files may stand in, and the record says so
    assert stage(bench, mode="path", carla="none").returncode == 0
    record = json.loads((bench["stage"] / "state" / "camera_calibration.json").read_text())
    assert record["source"].startswith("bundle fallback (mode path")
    assert record["files"]["H.yaml"]["source_sha256"] == _sha(bench["bundle"] / "config" / "visionpilot" / "H.yaml")


def test_start_refuses_mode_full_without_the_calibration(bench: dict, tmp_path: Path) -> None:
    env = {k: v for k, v in bench["env"].items() if k != "DA_CAMERA_CALIBRATION_DIR"}
    started = run(START, str(tmp_path / "out"), "10.164.0.2", env=env)
    assert started.returncode == 3 and "DA_CAMERA_CALIBRATION_DIR" in started.stdout
    assert not bench["stage"].exists()  # refused before anything was staged or cleared
    assert fake_bundle.staged_processes(bench["stage"]) == []


def test_the_calibration_has_one_name() -> None:
    for path in [*(BENCH / "score-path" / "scripts").iterdir(), BENCH / "score-build" / "scripts" / "p10_1_check.sh"]:
        if path.is_file():
            assert "DA_CALIBRATION_DIR" not in path.read_text(), path
    start = START.read_text()
    assert '--calibration-dir "$DA_CAMERA_CALIBRATION_DIR"' in start


def test_the_start_names_the_staged_calibration_and_the_record_hashes_it(bench: dict, tmp_path: Path) -> None:
    out = tmp_path / "out"
    started = run(START, str(out), "10.164.0.2", env=bench["env"])
    assert started.returncode == 0, started.stdout + started.stderr
    named = json.loads((out / "camera_calibration.json").read_text())
    assert named["source"] == "DA_CAMERA_CALIBRATION_DIR" and named["mode"] == "full"
    assert named["dir"] == str(bench["calibration"].resolve())
    record = json.loads((bench["stage"] / "run" / "score" / "candidate_record.json").read_text())
    by_path = {item["path"]: item["sha256"] for item in record["configuration_files"]}
    for name in ("H.yaml", "homography_C_matrix.yaml"):
        entry = named["files"][name]
        assert entry["source_sha256"] == _sha(bench["calibration"] / name) == entry["staged_sha256"]
        assert by_path[entry["staged_path"]] == entry["source_sha256"], name
    assert run(STOP, str(out), env=bench["env"]).returncode == 0


# --- one p10-2: three starts and stops, each with its own <out> ---------------------------------------------------


def test_start_stop_three_times_like_one_p10_2(bench: dict, tmp_path: Path) -> None:
    records = {}
    for label in ("calib_steer", "run1", "run2"):
        out = tmp_path / f"score_{label}"
        started = run(START, str(out), "10.164.0.2", env=bench["env"])
        assert started.returncode == 0, (label, started.stdout)
        assert not (out / "previous_stage").exists(), label  # the stop before collected everything
        stopped = run(STOP, str(out), env=bench["env"])
        assert stopped.returncode == 0, (label, stopped.stdout)
        assert fake_bundle.staged_processes(bench["stage"]) == [], label
        records[label] = state(out / "score_side_state.env")["RECORD_SHA256"]
    assert len(set(records.values())) == 3
    for label, digest in records.items():  # every run's files stay as its stop collected them
        collected = tmp_path / f"score_{label}" / "score_side"
        assert _sha(collected / "run" / "score" / "candidate_record.json") == digest, label
        for line in (collected / "SHA256SUMS").read_text().splitlines():
            sha, rel = line.split("  ", 1)
            assert _sha(collected / rel) == sha, (label, rel)


def _kill_the_launch_manager(out: Path) -> list[str]:
    s = state(out / "score_side_state.env")
    os.kill(int(s["LM_PID"]), signal.SIGKILL)  # a stop that never runs: the components are left behind
    time.sleep(0.5)
    return [s[f"PID_{n}"] for n in ("identity_recorder", "someipd", "gatewayd")]


def test_a_start_first_collects_what_no_stop_collected(bench: dict, tmp_path: Path) -> None:
    first = tmp_path / "score_run1"
    assert run(START, str(first), "10.164.0.2", env=bench["env"]).returncode == 0
    first_record = state(first / "score_side_state.env")["RECORD_SHA256"]
    orphans = _kill_the_launch_manager(first)
    assert fake_bundle.staged_processes(bench["stage"])  # components without a Launch Manager
    second = tmp_path / "score_run2"
    started = run(START, str(second), "10.164.0.2", env=bench["env"])
    assert started.returncode == 0, started.stdout  # no exit 4: no Launch Manager ran
    kept = second / "previous_stage" / "score_side" / "run" / "score" / "candidate_record.json"
    assert _sha(kept) == first_record
    for pid in orphans:
        assert not Path(f"/proc/{pid}").exists() or "Z" in Path(f"/proc/{pid}/stat").read_text().split()[2]
    assert state(second / "score_side_state.env")["RECORD_SHA256"] != first_record
    assert run(STOP, str(second), env=bench["env"]).returncode == 0


def test_a_start_that_cannot_collect_the_previous_stage_clears_nothing(bench: dict, tmp_path: Path) -> None:
    first = tmp_path / "score_run1"
    assert run(START, str(first), "10.164.0.2", env=bench["env"]).returncode == 0
    _kill_the_launch_manager(first)
    record = bench["stage"] / "run" / "score" / "candidate_record.json"
    before = _sha(record)
    second = tmp_path / "score_run2"
    (second / "previous_stage").mkdir(parents=True)
    (second / "previous_stage" / "score_side").write_text("in the way\n")  # the collection cannot write here
    started = run(START, str(second), "10.164.0.2", env=bench["env"])
    assert started.returncode == 3 and "could not be collected" in started.stdout
    assert _sha(record) == before  # the stage is left as it is


def test_exit_4_only_for_a_launch_manager_that_really_runs(bench: dict, tmp_path: Path) -> None:
    first = tmp_path / "score_run1"
    assert run(START, str(first), "10.164.0.2", env=bench["env"]).returncode == 0
    assert run(START, str(tmp_path / "again"), "10.164.0.2", env=bench["env"]).returncode == 4
    assert run(STOP, str(first), env=bench["env"]).returncode == 0
    # A stale state whose pid now belongs to another process (pid reuse) is no running Launch Manager: neither a
    # process that runs something else, nor one whose later arguments name the Launch Manager's binary.
    lm_bin = f"{bench['stage']}/bin/launch_manager"
    for n, argv in enumerate((["sleep", "60"], [sys.executable, "-c", "import time; time.sleep(60)", lm_bin])):
        other = subprocess.Popen(argv)
        try:
            (bench["stage"] / "state" / "score_side.env").write_text(
                f"LM_PID={other.pid}\nLM_BIN={lm_bin}\nSTATE=up\n")
            assert lm_bin not in Path(f"/proc/{other.pid}/cmdline").read_bytes().decode().split("\0")[:1]
            second = tmp_path / f"score_reused_{n}"
            started = run(START, str(second), "10.164.0.2", env=bench["env"])
            assert started.returncode == 0, (argv, started.stdout)
            assert "REFUSED" not in started.stdout
            assert other.poll() is None, argv  # never signalled
            assert run(STOP, str(second), env=bench["env"]).returncode == 0
            assert other.poll() is None, argv  # the stop never signals it either
        finally:
            other.kill()
            other.wait()


def test_the_start_does_not_wait_for_a_camera_image(bench: dict, tmp_path: Path) -> None:
    # no world ticks here: the candidate never gets an image and never reports running, and the start still returns
    out = tmp_path / "out"
    began = time.monotonic()
    started = run(START, str(out), "10.164.0.2", env={**bench["env"], "DA_START_TIMEOUT_S": "60"})
    assert started.returncode == 0, started.stdout
    assert time.monotonic() - began < 30
    assert "start the world pacer within 420 s" in started.stdout
    script = START.read_text()
    assert "score_interface.jsonl" not in script  # nothing of the candidate's own log gates the start
    assert script.count("running_reported") == 1  # the recorder's report only
    assert run(STOP, str(out), env=bench["env"]).returncode == 0


# --- application ids ---------------------------------------------------------------------------------------------


def test_every_mw_com_manifest_of_the_bench_has_its_own_application_id() -> None:
    """Every process of the S-CORE host runs with uid 0 (the Launch Manager configuration's defaults), so mw::com
    (LoLa) tells them apart by applicationID alone. The test publisher (3415), the record probe (3416) and the Launch
    Manager itself (3417) are this lane's proposals; no other manifest of the bench, staged or not, may take an id
    twice."""
    ids: dict[int, list[str]] = {}
    for path in sorted(BENCH.rglob("*.json")):
        if "tests" in path.relative_to(BENCH).parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if "applicationID" not in text:
            continue
        for value in re.findall(r'"applicationID"\s*:\s*(\d+)', text):
            ids.setdefault(int(value), []).append(str(path.relative_to(BENCH)))
    assert {k: v for k, v in ids.items() if len(v) > 1} == {}
    assert ids == {3410: ["score-path/config/mw_com_config_gatewayd_warning.json"],
                   3411: ["score-path/config/mw_com_config_someipd_warning.json"],
                   3412: ["score-path/config/mw_com_config_vision_pilot.json"],
                   3413: ["actuation-adapter/mw_com_config_actuation_adapter.json"],
                   3414: ["identity-recorder/mw_com_config_identity_recorder.json"],
                   3415: ["ivi-warning/injector/mw_com_config_warning_injector.json"],
                   3416: ["identity-recorder/mw_com_config_candidate_record_probe.json"],
                   3417: ["launch-manager/config/mw_com_config_launch_manager.json"]}
    for config in (LAUNCH, PATH_ONLY):
        data = json.loads(config.read_text())
        assert data["defaults"]["deployment_config"]["sandbox"]["uid"] == 0, config
        for name, component in data["components"].items():
            assert "sandbox" not in component.get("deployment_config", {}), (config, name)


# --- F1 of the first recorded p10-2 (20261119T174606Z): the adapter's wait for the hero ---------------------------


ADAPTER_JSON = BENCH / "actuation-adapter" / "config" / "adapter.json"
SESSION_SH = BENCH / "session" / "da_session.sh"


def test_the_adapter_waits_for_the_hero_across_the_sessions_go_limit_and_reports_before_its_ready_timeout() -> None:
    """The world holds its first tick until the go, so the adapter sees no hero before it. The session's go comes at
    most GO_LIMIT_S (380 s) after the S-CORE start step began, its SSH call at most GO_SSH_S (35 s) later; the
    adapter's process starts inside that step (in calib_steer of 20261119T174606Z 66 s after it began). The adapter
    reports running only after it found the hero, within its ready_timeout_ms of 420 s
    (launch-manager/config/launch_manager_config.json). In run 1 of that session the go came 81 s after the adapter's
    start and its 20 s wait had given up. The figures are pinned as numbers: hero_wait_s at least the go limit plus
    20 s, and at least 20 s under the ready time-out for the connect and the report."""
    session = SESSION_SH.read_text()
    go_limit = int(re.search(r"\bGO_LIMIT_S=(\d+)\b", session).group(1))
    go_ssh = int(re.search(r"\bGO_SSH_S=(\d+)\b", session).group(1))
    assert (go_limit, go_ssh) == (380, 35)
    components = json.loads(LAUNCH.read_text())["components"]
    ready_ms = {name: components[name]["deployment_config"]["ready_timeout_ms"]
                for name in ("actuation_adapter", "vision_pilot")}
    assert ready_ms["actuation_adapter"] == ready_ms["vision_pilot"] == 420000
    hero_wait_s = json.loads(ADAPTER_JSON.read_text())["hero_wait_s"]
    assert go_limit + 20 <= hero_wait_s <= ready_ms["actuation_adapter"] / 1000 - 20, hero_wait_s
    assert hero_wait_s == 400.0
