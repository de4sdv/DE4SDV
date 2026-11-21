"""The identity recorder's real path on disk, checked by independent tools.

record_driver (tests/record_driver.cpp) runs the recorder's shell with the POSIX file system and the record
writer, mw::com replaced by a printing publisher, on a synthetic stage that this test lays out. The test then
recomputes every recorded SHA-256 with Python's hashlib, parses the record with json, checks the event against
the file, and runs scripts/check_candidate_record.py on it. With VISIONPILOT_CLONE set to a clone that holds
014e0e7a, the record of the real patch series is re-derived: a fresh clone at the recorded revision, the
recorded difference applied, a non-empty result (REQ-DRIVING-044's reproducibility check).

The stage's contents are invented, except the bench's own patch series (score-interface/patches), which the
re-derivation needs; no model text is in any fixture.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
RECORDER = HERE.parent
BENCH = RECORDER.parent
ADAPTER = BENCH / "actuation-adapter"
PATCHES = BENCH / "score-interface" / "patches"
PIN = "014e0e7a56ee8e597c2cab8175233f74edd9b856"
CHECKER = RECORDER / "scripts" / "check_candidate_record.py"

SOURCES = [HERE / "record_driver.cpp", RECORDER / "recorder_shell.cpp", RECORDER / "record_probe.cpp",
           RECORDER / "sha256.cpp", RECORDER / "file_system.cpp", RECORDER / "record_inputs.cpp",
           RECORDER / "candidate_record.cpp", ADAPTER / "json_lite.cpp"]


@pytest.fixture(scope="module")
def driver(tmp_path_factory: pytest.TempPathFactory) -> Path:
    compiler = shutil.which("g++")
    if compiler is None:
        pytest.skip("g++ is not installed")
    out = tmp_path_factory.mktemp("driver") / "record_driver"
    subprocess.run([compiler, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-pedantic", f"-I{RECORDER}",
                    f"-I{BENCH / 'interfaces' / 'include'}", f"-I{ADAPTER}", *map(str, SOURCES), "-o", str(out)],
                   check=True)
    return out


def lay_out_stage(root: Path, *, diffs: dict[str, bytes] | None = None) -> dict[str, Path]:
    """A synthetic stage in the layout of score-path/scripts/stage_score_side.py."""
    stage = root / "de4sdv-da-bench"
    wd = stage / "vision_pilot"
    for d in ("bin", "lib", "config", "facts", "run", "etc", "vision_pilot/config",
              "vision_pilot/modules/models/weights"):
        (stage / d).mkdir(parents=True, exist_ok=True)
    launch = json.loads((BENCH / "launch-manager" / "config" / "launch_manager_config.json").read_text())
    text = json.dumps(launch, indent=4).replace("/tmp/de4sdv-da-bench", str(stage))
    (stage / "config" / "launch_manager_config.json").write_text(text)
    for name in ("identity_recorder", "someipd", "gatewayd", "vision_pilot", "actuation_adapter"):
        (stage / "bin" / name).write_bytes(b"\x7fELF synthetic " + name.encode())
    (stage / "lib" / "libonnxruntime.so.1").write_bytes(b"synthetic ort")
    os.symlink("libonnxruntime.so.1", stage / "lib" / "libonnxruntime.so")
    (stage / "etc" / "launch_manager_config.bin").write_bytes(b"\x10\x00synthetic flatbuffer")
    for name in ("mw_com_config_vision_pilot.json", "mw_com_config_identity_recorder.json",
                 "mw_com_config_gatewayd_warning.json", "mw_com_config_someipd_warning.json",
                 "mw_com_config_actuation_adapter.json", "vsomeip_someipd_warning.json"):
        (stage / "config" / name).write_text('{"synthetic": "' + name + '"}\n')
    (stage / "config" / "someip_gateway_config_warning.bin").write_bytes(b"\x00\x01synthetic gateway")
    (stage / "config" / "adapter.json").write_text('{"carla_host": "10.0.0.9"}\n')
    (stage / "config" / "de4sdv_score_interface.conf").write_text(
        f"mw_com.config = {stage / 'config' / 'mw_com_config_vision_pilot.json'}\ncarla.host = 10.0.0.9\n")
    (wd / "config" / "vision_pilot.conf").write_text("source.mode = score\nmodel.precision = fp32\n")
    (wd / "config" / "H.yaml").write_text("H: synthetic\n")
    (wd / "config" / "homography_C_matrix.yaml").write_text("C: synthetic\n")
    for net in ("autodrive", "autosteer", "autospeed"):
        (wd / "modules" / "models" / "weights" / f"{net}_fp32.onnx").write_bytes(b"synthetic " + net.encode())
    if diffs is None:
        diffs = {p.name: p.read_bytes() for p in sorted(PATCHES.glob("*.diff"))}
    sums = ""
    for name, data in diffs.items():
        (stage / "facts" / name).write_bytes(data)
        sums += f"{hashlib.sha256(data).hexdigest()}  {name}\n"
    (stage / "facts" / "SHA256SUMS").write_text(sums)
    (stage / "facts" / "upstream_revision.txt").write_text(PIN + "\n")
    ldconf = root / "ld.so.conf.d"
    gpu = root / "gpu" / "lib"
    ldconf.mkdir()
    gpu.mkdir(parents=True)
    (ldconf / "de4sdv-cuda-12.8.1.conf").write_text(f"{gpu}\n")
    (gpu / "libcudart.so.12.8.90").write_bytes(b"synthetic cudart")
    os.symlink("libcudart.so.12.8.90", gpu / "libcudart.so.12")
    (gpu / "libcudnn.so.9").write_bytes(b"synthetic cudnn")
    return {"stage": stage, "ldconf": ldconf, "system": root / "nosystem"}


def run_driver(driver: Path, paths: dict[str, Path]) -> subprocess.CompletedProcess:
    return subprocess.run([str(driver), "--run-dir", str(paths["stage"] / "run"), "--ldconfig-dir",
                           str(paths["ldconf"]), "--system-root", str(paths["system"])],
                          capture_output=True, text=True)


def event_fields(stdout: str) -> dict[str, str]:
    line = next(line for line in stdout.splitlines() if line.startswith("event "))
    return dict(part.split("=", 1) for part in line.split()[1:])


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_record_on_disk_matches_hashlib(tmp_path: Path, driver: Path) -> None:
    paths = lay_out_stage(tmp_path)
    result = run_driver(driver, paths)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "report_running" in result.stdout
    record_path = paths["stage"] / "run" / "score" / "candidate_record.json"
    raw = record_path.read_bytes()
    record = json.loads(raw)
    event = event_fields(result.stdout)
    # the event names this file, by its digest
    assert event["recordSha256"] == hashlib.sha256(raw).hexdigest()
    assert event["recordPath"] == str(record_path)
    assert event["upstreamRevision"] == PIN == record["upstream_revision"]
    total = sum(len(p.read_bytes()) for p in PATCHES.glob("*.diff"))
    assert int(event["diffBytes"]) == total == record["source_difference"]["bytes"]
    # the difference is verbatim, in name order
    names = [f["name"] for f in record["source_difference"]["files"]]
    assert names == sorted(p.name for p in PATCHES.glob("*.diff"))
    for item in record["source_difference"]["files"]:
        assert item["text"].encode() == (PATCHES / item["name"]).read_bytes()
    # every listed file's digest, recomputed
    listed = 0
    for key in ("configuration_files", "network_files", "binaries", "runtime_libraries"):
        for item in record[key]:
            assert sha256_file(Path(item["path"])) == item["sha256"], item["path"]
            assert Path(item["path"]).stat().st_size == item["bytes"]
            listed += 1
    roles = [f["role"] for f in record["configuration_files"]]
    assert roles[:5] == ["vision_pilot.conf", "H.yaml", "homography_C_matrix.yaml", "DE4SDV interface configuration",
                         "mw::com manifest of vision_pilot"]
    paths_listed = {f["path"] for f in record["configuration_files"]}
    for name in ("mw_com_config_identity_recorder.json", "mw_com_config_gatewayd_warning.json",
                 "mw_com_config_someipd_warning.json", "mw_com_config_actuation_adapter.json",
                 "vsomeip_someipd_warning.json", "someip_gateway_config_warning.bin", "adapter.json",
                 "launch_manager_config.json"):
        assert str(paths["stage"] / "config" / name) in paths_listed, name
    assert str(paths["stage"] / "etc" / "launch_manager_config.bin") in paths_listed
    assert {Path(b["path"]).name for b in record["binaries"]} == {
        "identity_recorder", "someipd", "gatewayd", "vision_pilot", "actuation_adapter"}
    libs = {Path(item["path"]).name: item for item in record["runtime_libraries"]}
    assert set(libs) == {"libonnxruntime.so.1", "libonnxruntime.so", "libcudart.so.12.8.90", "libcudart.so.12",
                         "libcudnn.so.9"}
    assert libs["libcudart.so.12"]["link_target"] == "libcudart.so.12.8.90"
    assert record["ldconfig_conf"]["path"] == str(paths["ldconf"] / "de4sdv-cuda-12.8.1.conf")
    # the launch settings verbatim, with the working directory
    assert record["launch_settings"]["launch_config_text"] == (
        paths["stage"] / "config" / "launch_manager_config.json").read_text()
    vp = next(c for c in record["launch_settings"]["components"] if c["component"] == "vision_pilot")
    assert vp["working_dir"] == str(paths["stage"] / "vision_pilot")
    assert vp["application_type"] == "Reporting_And_Supervised"
    assert vp["depends_on"] == ["identity_recorder"]  # the stop run's target holds it without the warning path
    rec = next(c for c in record["launch_settings"]["components"] if c["component"] == "identity_recorder")
    assert rec["application_type"] == "Reporting"
    assert listed >= 20
    # the independent checker agrees, rehashing on this host
    check = subprocess.run([sys.executable, str(CHECKER), str(record_path), "--event-sha256", event["recordSha256"],
                            "--rehash"], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    report = json.loads(check.stdout)
    assert report["ok"] and report["rehash_counts"]["absent_here"] == 0


def test_one_change_gives_another_record_and_the_checker_sees_it(tmp_path: Path, driver: Path) -> None:
    paths = lay_out_stage(tmp_path)
    assert run_driver(driver, paths).returncode == 0
    record_path = paths["stage"] / "run" / "score" / "candidate_record.json"
    first = json.loads(record_path.read_bytes())
    h = paths["stage"] / "vision_pilot" / "config" / "H.yaml"
    h.write_text("H: changed\n")
    check = subprocess.run([sys.executable, str(CHECKER), str(record_path), "--rehash"], capture_output=True,
                           text=True)
    assert check.returncode == 1 and "H.yaml differs" in check.stdout
    assert run_driver(driver, paths).returncode == 0
    second = json.loads(record_path.read_bytes())
    old = next(f for f in first["configuration_files"] if f["role"] == "H.yaml")
    new = next(f for f in second["configuration_files"] if f["role"] == "H.yaml")
    assert old["sha256"] != new["sha256"] == hashlib.sha256(b"H: changed\n").hexdigest()
    # a wrong event digest is caught
    wrong = subprocess.run([sys.executable, str(CHECKER), str(record_path), "--event-sha256", "0" * 64],
                           capture_output=True, text=True)
    assert wrong.returncode == 1


def test_no_record_without_the_inputs(tmp_path: Path, driver: Path) -> None:
    paths = lay_out_stage(tmp_path)
    (paths["stage"] / "vision_pilot" / "config" / "homography_C_matrix.yaml").unlink()
    result = run_driver(driver, paths)
    assert result.returncode == 3
    assert "report_running" not in result.stdout and "event " not in result.stdout
    assert not (paths["stage"] / "run" / "score" / "candidate_record.json").exists()
    log = (paths["stage"] / "run" / "score" / "identityRecorder.jsonl").read_text().splitlines()
    error = [json.loads(line) for line in log if json.loads(line)["event"] == "error"][-1]
    assert "homography_C_matrix.yaml" in error["data"]["reason"]
    for key in ("t_mono_ns", "t_real_ns", "host", "component", "seq"):
        assert key in error


def test_the_checker_flags_a_tampered_difference(tmp_path: Path, driver: Path) -> None:
    paths = lay_out_stage(tmp_path)
    assert run_driver(driver, paths).returncode == 0
    record_path = paths["stage"] / "run" / "score" / "candidate_record.json"
    record = json.loads(record_path.read_bytes())
    record["source_difference"]["files"][0]["text"] += "+tampered\n"
    tampered = tmp_path / "tampered.json"
    tampered.write_text(json.dumps(record))
    check = subprocess.run([sys.executable, str(CHECKER), str(tampered)], capture_output=True, text=True)
    assert check.returncode == 1 and "sha256 differs from its text" in check.stdout


def vp_clone() -> Path:
    clone = os.environ.get("VISIONPILOT_CLONE")
    if not clone:
        pytest.skip("VISIONPILOT_CLONE is not set to a clone that holds 014e0e7a")
    found = subprocess.run(["git", "-C", clone, "cat-file", "-e", PIN + "^{commit}"], capture_output=True)
    if found.returncode != 0:
        pytest.skip(f"{clone} does not hold {PIN}")
    return Path(clone)


def test_the_record_re_derives_at_the_pin(tmp_path: Path, driver: Path) -> None:
    clone = vp_clone()
    paths = lay_out_stage(tmp_path)
    assert run_driver(driver, paths).returncode == 0
    record_path = paths["stage"] / "run" / "score" / "candidate_record.json"
    check = subprocess.run([sys.executable, str(CHECKER), str(record_path), "--vp-clone", str(clone),
                            "--scratch", str(tmp_path / "scratch")], capture_output=True, text=True)
    assert check.returncode == 0, check.stdout + check.stderr
    assert json.loads(check.stdout)["checks"]["apply_at_revision"] == "ok"


def test_a_difference_that_does_not_apply_at_the_pin_is_caught(tmp_path: Path, driver: Path) -> None:
    clone = vp_clone()
    bogus = (b"diff --git a/VisionPilot/no_such_file.txt b/VisionPilot/no_such_file.txt\n"
             b"--- a/VisionPilot/no_such_file.txt\n+++ b/VisionPilot/no_such_file.txt\n@@ -1 +1 @@\n-a\n+b\n")
    paths = lay_out_stage(tmp_path, diffs={"0001-bogus.diff": bogus})
    assert run_driver(driver, paths).returncode == 0
    record_path = paths["stage"] / "run" / "score" / "candidate_record.json"
    check = subprocess.run([sys.executable, str(CHECKER), str(record_path), "--vp-clone", str(clone),
                            "--scratch", str(tmp_path / "scratch")], capture_output=True, text=True)
    assert check.returncode == 1 and "does not apply" in check.stdout
