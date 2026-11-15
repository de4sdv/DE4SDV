"""SBOM generation must scan immutable baseline refs, not stale mutable tags."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import yaml

ROOT = Path(__file__).resolve().parents[2]
ZONE_DIGEST = "sha256:" + "a" * 64
GW_DIGEST = "sha256:" + "b" * 64


def fixture(tmp_path):
    root = tmp_path / "ee"
    (root / "checks").mkdir(parents=True)
    (root / "vehicle").mkdir()
    (root / "bin").mkdir()
    shutil.copy2(ROOT / "checks/make_sbom.sh", root / "checks/make_sbom.sh")
    helper = ROOT / "checks/sbom_inventory.py"
    if helper.exists():
        shutil.copy2(helper, root / "checks/sbom_inventory.py")
    images = [
        {"ref": "registry.example:5000/zone-ecu:12", "digest": ZONE_DIGEST, "target_ids": ["fn-fl"]},
        {"ref": "registry.example:5000/can-gw:5", "digest": GW_DIGEST, "target_ids": ["fn-hpc"]},
    ]
    (root / "vehicle/parts.yaml").write_text(yaml.safe_dump({"kind": "baseline", "parts": images}))
    (root / "vehicle/vxp.lock").write_text(yaml.safe_dump({"images": [{k: p[k] for k in ("ref", "digest")} for p in images]}))
    scanner = root / "bin/syft"
    scanner.write_text(f"#!{sys.executable}\n" + '''import json, os, pathlib, sys
args = sys.argv[1:]
if args == ["version", "-o", "json"]:
    print(json.dumps({"version": "1.57.1"})); sys.exit(0)
ref = args[0]
with open(os.environ["SCAN_LOG"], "a") as f: f.write(ref + "\\n")
digest = ref.split("@")[-1] if "@" in ref else "sha256:" + "0" * 64
native = {"source": {"type": "image", "name": ref, "metadata": {
    "userInput": ref, "imageID": os.environ.get("WRONG_IMAGE_ID", "sha256:" + "d" * 64),
    "manifestDigest": os.environ.get("WRONG_DIGEST", digest),
    "repoDigests": [ref], "architecture": "amd64", "os": "linux"
}}, "descriptor": {"name": "syft", "version": "1.57.1"}}
cdx = {"bomFormat": "CycloneDX", "specVersion": "1.7", "metadata": {"component": {"type": "container", "name": ref}}, "components": [{"name": "synthetic-package", "version": "1"}]}
for index, arg in enumerate(args):
    if arg == "-o":
        fmt, path = args[index+1].split("=", 1)
        pathlib.Path(path).write_text(json.dumps(native if fmt == "syft-json" else cdx))
''')
    scanner.chmod(0o755)
    podman = root / "bin/podman"
    podman.write_text(f"#!{sys.executable}\n" + '''import json, os, sys
ref = sys.argv[3]
print(json.dumps({"imageID": "d" * 64, "repoDigests": [] if os.environ.get("MISSING_REPO_DIGEST") else [ref], "architecture": "amd64", "os": "linux"}))
''')
    podman.chmod(0o755)
    env = {**os.environ, "PATH": str(root / "bin") + os.pathsep + os.environ["PATH"], "SCAN_LOG": str(root / "calls"), "PYTHON": sys.executable}
    return root, env


def test_generator_scans_digest_refs_from_the_baseline(tmp_path):
    root, env = fixture(tmp_path)
    result = subprocess.run(["sh", str(root / "checks/make_sbom.sh")], env=env, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    calls = (root / "calls").read_text().splitlines()
    assert set(calls) == {"registry.example:5000/zone-ecu@" + ZONE_DIGEST, "registry.example:5000/can-gw@" + GW_DIGEST}, "scanner inputs must be the immutable current baseline, not hardcoded tags"
    check = subprocess.run([sys.executable, str(root / "checks/sbom_inventory.py"), "check"], env=env, text=True, capture_output=True, timeout=20)
    assert check.returncode == 0, check.stdout + check.stderr
    receipt = json.loads((root / "sbom/inventory.json").read_text())
    assert {entry["source"]["manifestDigest"] for entry in receipt["images"]} == {ZONE_DIGEST, GW_DIGEST}


def test_generator_rejects_scanner_source_for_a_different_image(tmp_path):
    root, env = fixture(tmp_path)
    env["WRONG_IMAGE_ID"] = "sha256:" + "c" * 64
    result = subprocess.run(["sh", str(root / "checks/make_sbom.sh")], env=env, text=True, capture_output=True, timeout=20)
    assert result.returncode == 1
    assert "scanner image ID differs from the inspected image" in result.stdout
    assert not (root / "sbom/inventory.json").exists()


def test_podman_export_manifest_can_differ_while_image_binding_matches(tmp_path):
    # The real scanner's Podman export changes the manifest representation, not
    # the image/config identity; it must bind via native RepoDigests + image ID.
    root, env = fixture(tmp_path)
    env["WRONG_DIGEST"] = "sha256:" + "c" * 64
    result = subprocess.run(["sh", str(root / "checks/make_sbom.sh")], env=env, text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, "a verified Podman export must be scannable: " + result.stdout + result.stderr


def test_inspected_image_must_resolve_the_exact_locked_repo_digest(tmp_path):
    root, env = fixture(tmp_path)
    env["MISSING_REPO_DIGEST"] = "1"
    result = subprocess.run(["sh", str(root / "checks/make_sbom.sh")], env=env, text=True, capture_output=True, timeout=20)
    assert result.returncode == 1, "a requested ref alone cannot establish its image binding"
    assert "locked ref absent from inspected RepoDigests" in result.stdout
    assert not (root / "calls").exists()


def test_generator_rejects_parts_lock_mismatch_before_scanning(tmp_path):
    root, env = fixture(tmp_path)
    path = root / "vehicle/vxp.lock"
    text = path.read_text()
    path.write_text(text.replace(ZONE_DIGEST, "sha256:" + "c" * 64))
    result = subprocess.run(["sh", str(root / "checks/make_sbom.sh")], env=env, text=True, capture_output=True, timeout=20)
    assert result.returncode == 1
    assert "parts and lock disagree" in result.stdout
    assert not (root / "calls").exists()


def test_offline_inventory_check_rejects_changed_sbom_bytes(tmp_path):
    root, env = fixture(tmp_path)
    run = subprocess.run(["sh", str(root / "checks/make_sbom.sh")], env=env, text=True, capture_output=True, timeout=20)
    assert run.returncode == 0, run.stdout + run.stderr
    path = root / "sbom/zone-ecu.cdx.json.gz"
    path.write_bytes(path.read_bytes() + b"modified")
    check = subprocess.run([sys.executable, str(root / "checks/sbom_inventory.py"), "check"], env=env, text=True, capture_output=True, timeout=20)
    assert check.returncode == 1
    assert "SBOM hash mismatch" in check.stdout
