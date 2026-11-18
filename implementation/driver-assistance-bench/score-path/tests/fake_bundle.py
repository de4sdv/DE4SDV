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
              "share/visionpilot/assets", "facts", "etc"):
        (bundle / d).mkdir(parents=True, exist_ok=True)
    stub = TESTS / "stub_component.sh"
    for name in ("VisionPilot", "actuation_adapter", "gatewayd", "someipd"):
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
    (bundle / "etc" / "launch_manager_config.bin").write_bytes(b"synthetic flatbuffer full")
    (bundle / "etc" / "launch_manager_config_path_only.bin").write_bytes(b"synthetic flatbuffer path")
    ldconf = root / "ld.so.conf.d"
    gpu = root / "gpu" / "lib"
    ldconf.mkdir(exist_ok=True)
    gpu.mkdir(parents=True, exist_ok=True)
    (ldconf / "de4sdv-cuda-12.8.1.conf").write_text(f"# synthetic\n{gpu}\n")
    (gpu / "libcudart.so.12").write_bytes(b"synthetic cudart")
    (gpu / "libcudnn.so.9").write_bytes(b"synthetic cudnn")
    stage = root / "de4sdv-da-bench"
    env = {**os.environ, "DA_STAGE": str(stage), "DA_B2_BUNDLE": str(bundle), "DA_SUDO": "", "DA_TEST_SERVE": "1",
           "DA_TEST_LDCONFIG_DIR": str(ldconf), "DA_TEST_SYSTEM_ROOT": str(root / "nosystem"),
           "DA_START_TIMEOUT_S": "30", "DA_STOP_TIMEOUT_S": "15"}
    for key in ("FAKE_LM_IGNORE_TERM", "FAKE_LM_EXIT_AFTER_S", "FAKE_LM_SUPERVISE", "DA_CALIBRATION_DIR",
                "DA_SPEED_LIMIT"):
        env.pop(key, None)
    return {"bundle": bundle, "stage": stage, "env": env, "ldconf": ldconf, "root": root}


def staged_processes(stage: Path) -> list[str]:
    """Command lines of every process that runs a file of the stage's bin/."""
    out = subprocess.run(["ps", "-eo", "stat=,args="], capture_output=True, text=True).stdout
    return [line for line in out.splitlines() if f"{stage}/bin/" in line and not line.lstrip().startswith("Z")]
