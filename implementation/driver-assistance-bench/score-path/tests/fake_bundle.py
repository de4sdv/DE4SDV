"""A fake bundle of the S-CORE build for the dry runs of the S-CORE side's scripts. Test code only.

The bundle has the layout build_score_bench.sh packs (score-build/README.md), with invented contents: the
components are stub_component.sh, the Launch Manager is fake_launch_manager.py, and the identity recorder is the
recorder's real shell with the POSIX file system and a printing publisher (identity-recorder/tests/
record_driver.cpp), so the dry runs hash the staged tree for real. The bench's own patch series stands for the
bundle's facts/, since the recorder needs a non-empty difference. No model text, no upstream file.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

TESTS = Path(__file__).resolve().parent
BENCH = TESTS.parents[1]
RECORDER = BENCH / "identity-recorder"
ADAPTER = BENCH / "actuation-adapter"

UPSTREAM_LIKE_CONF = """# synthetic stand-in for upstream's vision_pilot.conf (same keys, invented comments)
source.mode             = video
engine.provider     = cuda
model.precision    = fp32
speed_limit      = 33.3;   # m/s
L                = 2.860   # wheelbase part
visualization_on = true
rrd_on  = false
rrd_log = visionpilot.rrd
"""

# The two facts files the S-CORE start's platform record reads (score_platform_record.py), in the lines the S-CORE
# build wrote on 2026-11-20 (build_score_bench.sh: `bazel mod explain` into score-mod-explain.txt, and sources.txt).
# Bazel's tree lines end with a space; it is written as an escape here so that no source line ends in one.
FACTS_SCORE_MOD_EXPLAIN = "<root> (score_feo@0.0.0)\n" + "".join("\u251c\u2500\u2500\u2500" + m + " \n" for m in (
    "aspect_rules_lint@2.5.0", "platforms@1.1.0", "score_communication@0.6.0", "score_lifecycle@0.10.0")) + \
    "\u2514\u2500\u2500\u2500score_tooling@3.0.1 \n\n"
FACTS_SOURCES = (
    "VisionPilot 014e0e7a56ee8e597c2cab8175233f74edd9b856 with cee80df29819b292b67ab11990509243155d950939fff128c03762f29b"
    "aac0e0  0001-de4sdv-visualization-recorder.diff \n"
    "FEO 313b3d849c17881d3a11b6bf62aa2afab6565ef0; gateway d9eac670b7534352749da3d30f52aebf5129f168; CARLA "
    "14ac3b1a502da45a44506cb2ed82ab800f1baf4c; ONNX Runtime 1.26.0 (nuget sha256 "
    "cf7943f58b9360fe1448c4baf40ac12ce4175978ecd3fe6f21a4c00976f63a59)\n"
    "repository unknown\n")
# nvidia-smi's answer on the L4 to the record's query (name,driver_version; the build's checks/gpu.txt of 2026-11-20
# also lists memory.total: "NVIDIA L4, 580.178.04, 23034 MiB")
SMI_L4_ANSWER = "NVIDIA L4, 580.178.04"


def build_record_driver(out_dir: Path) -> Path:
    compiler = shutil.which("g++")
    if compiler is None:
        raise RuntimeError("g++ is not installed")
    out = out_dir / "record_driver"
    sources = [RECORDER / "tests" / "record_driver.cpp", RECORDER / "recorder_shell.cpp",
               RECORDER / "record_probe.cpp", RECORDER / "sha256.cpp", RECORDER / "file_system.cpp",
               RECORDER / "record_inputs.cpp", RECORDER / "candidate_record.cpp", ADAPTER / "json_lite.cpp"]
    subprocess.run([compiler, "-std=c++17", "-O1", f"-I{RECORDER}", f"-I{BENCH / 'interfaces' / 'include'}",
                    f"-I{ADAPTER}", *map(str, sources), "-o", str(out)], check=True)
    return out


def make_bundle(root: Path, record_driver: Path, extra_bins: dict[str, str] | None = None) -> dict:
    bundle = root / "bundle"
    for d in ("bin", "lib", "config/gateway", "config/visionpilot", "share/visionpilot/modules/models/weights",
              "share/visionpilot/assets", "facts", "config/launch_manager"):
        (bundle / d).mkdir(parents=True, exist_ok=True)
    stub = TESTS / "stub_component.sh"
    for name in ("vision_pilot", "actuation_adapter", "gatewayd", "someipd"):
        shutil.copy(stub, bundle / "bin" / name)
    shutil.copy(record_driver, bundle / "bin" / "identity_recorder")
    shutil.copy(TESTS / "fake_launch_manager.py", bundle / "bin" / "launch_manager")
    for name, text in (extra_bins or {}).items():
        (bundle / "bin" / name).write_text(text)
    for p in (bundle / "bin").iterdir():
        p.chmod(0o755)
    (bundle / "lib" / "libonnxruntime.so.1").write_bytes(b"synthetic ort")
    (bundle / "config" / "gateway" / "someip_gateway_config_warning.bin").write_bytes(b"\x00synthetic gateway")
    (bundle / "config" / "visionpilot" / "vision_pilot.conf").write_text(UPSTREAM_LIKE_CONF)
    (bundle / "config" / "visionpilot" / "H.yaml").write_text("H: synthetic bundle\n")
    (bundle / "config" / "visionpilot" / "homography_C_matrix.yaml").write_text("C: synthetic bundle\n")
    for net in ("autodrive", "autosteer", "autospeed"):
        for precision in ("fp32", "int8"):
            (bundle / "share/visionpilot/modules/models/weights" / f"{net}_{precision}.onnx").write_bytes(
                f"synthetic {net} {precision}".encode())
    (bundle / "share/visionpilot/assets/icon.png").write_bytes(b"synthetic png")
    patches = BENCH / "score-interface" / "patches"
    for p in sorted(patches.glob("*.diff")) + [patches / "SHA256SUMS"]:
        shutil.copy(p, bundle / "facts" / p.name)
    (bundle / "facts" / "score-mod-explain.txt").write_text(FACTS_SCORE_MOD_EXPLAIN)
    (bundle / "facts" / "sources.txt").write_text(FACTS_SOURCES)
    # the S-CORE host's nvidia-smi, as the L4 answers the platform record's query (never this host's own)
    smi = root / "nvidia-smi"
    smi.write_text("#!/bin/bash\necho '%s'\n" % SMI_L4_ANSWER)
    smi.chmod(0o755)
    # config/launch_manager/: each .bin beside the JSON it was converted from (build_score_bench.sh's bundle step)
    launch = bundle / "config" / "launch_manager"
    (launch / "launch_manager_config.bin").write_bytes(b"synthetic flatbuffer full")
    (launch / "launch_manager_config_path_only.bin").write_bytes(b"synthetic flatbuffer path")
    shutil.copy(BENCH / "launch-manager" / "config" / "launch_manager_config.json", launch)
    shutil.copy(BENCH / "score-path" / "config" / "launch_manager_config_path_only.json", launch)
    # the daemon's own mw::com configuration, beside them (the bundle step copies the bench's file)
    shutil.copy(BENCH / "launch-manager" / "config" / "mw_com_config_launch_manager.json", launch)
    ldconf = root / "ld.so.conf.d"
    gpu = root / "gpu" / "lib"
    ldconf.mkdir(exist_ok=True)
    gpu.mkdir(parents=True, exist_ok=True)
    (ldconf / "de4sdv-cuda-12.8.1.conf").write_text(f"# synthetic\n{gpu}\n")
    (gpu / "libcudart.so.12").write_bytes(b"synthetic cudart")
    (gpu / "libcudnn.so.9").write_bytes(b"synthetic cudnn")
    # the session's camera calibration of the CARLA camera (world-side/camera_calibration.py), synthetic here
    calibration = root / "camera_calibration"
    calibration.mkdir(exist_ok=True)
    (calibration / "H.yaml").write_text("H: synthetic session calibration\n")
    (calibration / "homography_C_matrix.yaml").write_text("C: synthetic session calibration\n")
    stage = root / "de4sdv-da-bench"
    env = {**os.environ, "DA_STAGE": str(stage), "DA_B2_BUNDLE": str(bundle), "DA_SUDO": "", "DA_TEST_SERVE": "1",
           "DA_TEST_LDCONFIG_DIR": str(ldconf), "DA_TEST_SYSTEM_ROOT": str(root / "nosystem"),
           "DA_START_TIMEOUT_S": "30", "DA_STOP_TIMEOUT_S": "15", "DA_CAMERA_CALIBRATION_DIR": str(calibration),
           "DA_NVIDIA_SMI": str(smi)}
    for key in ("FAKE_LM_IGNORE_TERM", "FAKE_LM_EXIT_AFTER_S", "FAKE_LM_SUPERVISE",
                "DA_SPEED_LIMIT"):
        env.pop(key, None)
    return {"bundle": bundle, "stage": stage, "env": env, "ldconf": ldconf, "root": root, "calibration": calibration}


def staged_processes(stage: Path) -> list[str]:
    """Command lines of every process that runs a file of the stage's bin/.

    -ww: whole lines, whatever $COLUMNS this process inherits (test_process_listing_width.py).
    """
    out = subprocess.run(["ps", "-ww", "-eo", "stat=,args="], capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if f"{stage}/bin/" in line and not line.lstrip().startswith("Z")]
