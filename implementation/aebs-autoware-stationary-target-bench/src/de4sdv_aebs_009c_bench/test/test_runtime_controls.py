"""Focused contract tests for the fail-closed 009C inherited runtime controls."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import shutil
import subprocess
import sys

import pytest
import yaml


BENCH = Path(__file__).resolve().parents[3]
ROOT = BENCH.parents[1]
INHERITED = ROOT / "implementation/aebs-autoware-executable-bench"
IMAGE = (
    "ghcr.io/autowarefoundation/autoware:universe-devel-humble-20260722"
    "@sha256:03f6e177d507504a26710041674a1386b1a63fe964870cb5ff48b5e59c635c17"
)
MANIFEST_SHA = "a06657a0a98eea21862ce94bf79a5b49509b1d7f0f7581af6cd3bee9bdcb2e8a"
LOCK_SHA = "6621ad7fb9196a7f1bccb31a3cae32dbb7e86e0cd249af8e86c39e579bdcf89d"


def load_script(name: str, filename: str):
    scripts = BENCH / "scripts"
    if str(scripts) not in sys.path:
        sys.path.insert(0, str(scripts))
    spec = importlib.util.spec_from_file_location(name, scripts / filename)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_identity():
    return load_script("identity_009c", "execution_identity.py")


def copy_authoritative_bench(destination: Path) -> None:
    shutil.copytree(
        BENCH,
        destination,
        symlinks=True,
        ignore=shutil.ignore_patterns(
            "evidence", "workspace", ".pytest_cache", ".ruff_cache", "__pycache__"
        ),
    )
    (destination / "evidence/009c").mkdir(parents=True)
    (destination / "workspace").mkdir()
    (destination / "workspace/.gitkeep").write_bytes(b"")


def test_lock_inherits_exact_verified_009a_inputs_without_claims() -> None:
    lock = yaml.safe_load((BENCH / "runtime-lock.yaml").read_text())
    upstream = yaml.safe_load((INHERITED / "runtime-lock.yaml").read_text())
    scenario = yaml.safe_load(
        (BENCH / "config/scenario-009c-aeb-mrm.yaml").read_text()
    )

    assert lock["schema"] == "de4sdv.aebs-009c.runtime-lock.v1"
    assert lock["increment"] == "INC-AEBS-009C"
    assert lock["scenario_id"] == "SCN-AEBS-009C-AEB-MRM-001"
    assert lock["status"] == "defined_not_executed"
    assert lock["container"] == upstream["container"]
    assert lock["sources"] == upstream["sources"]
    assert lock["map"] == upstream["map"]
    inherited = lock["inherited_009a"]
    assert inherited["execution_manifest_sha256"] == MANIFEST_SHA
    assert inherited["runtime_lock_sha256"] == LOCK_SHA
    assert inherited["disposition"] == "runtime_verified_009a_readiness_only"
    assert inherited["execution_manifest_path"].endswith("evidence/readiness.json")
    assert inherited["runtime_lock_path"].endswith("runtime-lock.yaml")
    assert lock["selected_ros_packages"] == ["de4sdv_aebs_009c_bench"]
    assert lock["timeouts"] == scenario["timeouts"]
    assert lock["evidence"]["directory"].endswith("evidence/009c")
    boundaries = " ".join(lock["claim_boundaries"]).lower()
    for term in ("runtime", "scenario", "safety", "compliance"):
        assert term in boundaries
    assert "retained validated evidence" in boundaries


def test_compose_is_digest_pinned_loopback_and_mounts_only_overlay_rw() -> None:
    compose = yaml.safe_load((BENCH / "compose.yaml").read_text())
    service = compose["services"]["bench"]
    assert service["image"] == IMAGE
    assert service["platform"] == "linux/arm64"
    assert service["network_mode"] == "host"
    assert service["environment"]["ROS_DOMAIN_ID"] == "91"
    assert service.get("privileged") is not True
    volumes = service["volumes"]
    text = "\n".join(volumes)
    assert "../..:/de4sdv:ro" in volumes
    assert "aebs-autoware-executable-bench/workspace:ro" in text
    assert "aebs-autoware-stationary-target-bench/workspace:rw" in text
    assert "aebs-autoware-stationary-target-bench/evidence:rw" in text
    assert "/map-cache:ro" in text
    cyclone = (BENCH / "cyclonedds.xml").read_text()
    assert 'NetworkInterface name="lo"' in cyclone
    assert "<AllowMulticast>false</AllowMulticast>" in cyclone


def test_scripts_are_overlay_only_and_do_not_claim_success() -> None:
    prepare = (BENCH / "scripts/prepare_workspace.sh").read_text()
    build = (BENCH / "scripts/build.sh").read_text()
    launch = (BENCH / "scripts/launch.sh").read_text()
    all_scripts = prepare + build + launch
    assert "verify_runtime.py" in all_scripts
    assert "vcs import" not in prepare
    assert "git clone" not in prepare
    assert "de4sdv_aebs_009c_bench" in prepare
    assert "--packages-select de4sdv_aebs_009c_bench" in build.replace("\\\n", " ")
    assert "--parallel-workers 1" in build.replace("\\\n", " ")
    assert "aebs_009c_bench.launch.py" in launch
    assert 'mkdir -p "$run_dir"' not in launch
    assert '"$BENCH/scripts/verify_map.py"' in launch
    assert "aebs-autoware-executable-bench/scripts/verify_map.py" not in launch
    local_map_verifier = (BENCH / "scripts/verify_map.py").read_text()
    assert 'bench / "evidence/009c/map-runtime.json"' in local_map_verifier
    assert "not readiness" in launch.lower()
    assert "source /opt/autoware/setup.bash" in build
    for script in (prepare, build, launch):
        source_index = script.index("source /opt/autoware/setup.bash")
        restore_index = script.index("\n  set -u\n", source_index)
        assert script.rfind("set -eo pipefail", 0, source_index) >= 0
        assert restore_index > script.rindex("source ", source_index, restore_index)
    run_scenario = (BENCH / "scripts/run_scenario.sh").read_text()
    source_index = run_scenario.index("source /opt/autoware/setup.bash")
    restore_index = run_scenario.index("\n  set -u\n", source_index)
    assert run_scenario.rfind("set -eo pipefail", 0, source_index) >= 0
    assert restore_index > run_scenario.rindex("source ", source_index, restore_index)
    assert "aebs-autoware-executable-bench/workspace/install/setup.bash" in build
    assert "aebs-autoware-stationary-target-bench/workspace/install/setup.bash" in launch
    assert "pass_observed_chain" not in all_scripts
    assert "scenario_executed" not in all_scripts
    for name in ("prepare_workspace.sh", "build.sh", "launch.sh", "run_scenario.sh"):
        assert (BENCH / "scripts" / name).stat().st_mode & 0o111


def test_identity_changes_for_authoritative_input_and_ignores_pycache(tmp_path: Path) -> None:
    identity = load_identity()
    copied = tmp_path / "bench"
    copy_authoritative_bench(copied)
    first = identity.execution_manifest_sha256(copied)
    config = copied / "config/scenario-009c-aeb-mrm.yaml"
    config.write_text(config.read_text() + "\n# identity mutation\n")
    assert identity.execution_manifest_sha256(copied) != first
    config.write_text(config.read_text().replace("\n# identity mutation\n", "\n"))
    restored = identity.execution_manifest_sha256(copied)
    cache = copied / "scripts/__pycache__"
    cache.mkdir(exist_ok=True)
    (cache / "junk.pyc").write_bytes(b"ignored")
    assert identity.execution_manifest_sha256(copied) == restored
    for cache_name in (".pytest_cache", ".ruff_cache"):
        tool_cache = copied / "src/de4sdv_aebs_009c_bench" / cache_name
        tool_cache.mkdir(exist_ok=True)
        (tool_cache / "volatile").write_text("changes during verification")
        assert identity.execution_manifest_sha256(copied) == restored
    inputs = identity.execution_inputs(copied)
    assert inputs["@inherited-009a-execution-manifest"] == MANIFEST_SHA
    (copied / "compose.yaml").unlink()
    with pytest.raises(FileNotFoundError):
        identity.execution_manifest_sha256(copied)


def test_runtime_verifier_accepts_live_inheritance_and_rejects_mismatch(
    tmp_path: Path,
) -> None:
    command = [
        sys.executable,
        str(BENCH / "scripts/verify_runtime.py"),
        "--bench",
        str(BENCH),
        "--inherited-bench",
        str(INHERITED),
    ]
    accepted = subprocess.run(command, text=True, capture_output=True)
    assert accepted.returncode == 0, accepted.stderr
    copied = tmp_path / "bench"
    copy_authoritative_bench(copied)
    lock_path = copied / "runtime-lock.yaml"
    lock_path.write_text(lock_path.read_text().replace(LOCK_SHA, "0" * 64))
    rejected = subprocess.run(
        [
            sys.executable,
            str(copied / "scripts/verify_runtime.py"),
            "--bench",
            str(copied),
            "--inherited-bench",
            str(INHERITED),
        ],
        text=True,
        capture_output=True,
    )
    assert rejected.returncode != 0
    assert "runtime lock" in rejected.stderr.lower()


def test_map_evidence_atomic_writer_rejects_unsafe_destinations(tmp_path: Path) -> None:
    verifier = load_script("verify_map_009c", "verify_map.py")
    bench = tmp_path / "bench"
    evidence = bench / "evidence/009c"
    evidence.mkdir(parents=True)
    outside = tmp_path / "outside.json"
    outside.write_text("unchanged", encoding="utf-8")
    destination = evidence / "map-runtime.json"
    destination.symlink_to(outside)
    with pytest.raises(ValueError):
        verifier.atomic_evidence_write(destination, {"ok": True}, bench)
    assert outside.read_text(encoding="utf-8") == "unchanged"
    destination.unlink()
    destination.mkdir()
    with pytest.raises(ValueError):
        verifier.atomic_evidence_write(destination, {"ok": True}, bench)
    with pytest.raises(ValueError):
        verifier.atomic_evidence_write(tmp_path / "escape.json", {"ok": True}, bench)


def test_map_verifier_rejects_symlink_root_and_nonregular_entry(tmp_path: Path) -> None:
    verifier = load_script("verify_map_paths_009c", "verify_map.py")
    bench = tmp_path / "bench"
    copy_authoritative_bench(bench)
    lock = yaml.safe_load((bench / "runtime-lock.yaml").read_text())
    cache = tmp_path / "cache"
    real = tmp_path / "real-map"
    real.mkdir()
    map_root = cache / lock["map"]["extracted_directory"]
    map_root.parent.mkdir(parents=True)
    map_root.symlink_to(real, target_is_directory=True)
    with pytest.raises(ValueError, match="symlink"):
        verifier.verify(cache, bench)
    map_root.unlink()
    map_root.mkdir()
    fifo = map_root / "unexpected-fifo"
    fifo.parent.mkdir(parents=True, exist_ok=True)
    import os
    os.mkfifo(fifo)
    with pytest.raises(ValueError, match="nonregular"):
        verifier.verify(cache, bench)
