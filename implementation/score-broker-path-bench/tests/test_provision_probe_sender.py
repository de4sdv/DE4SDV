"""The sender install step on a fake adb: push to both guests, record the digest, stop when missing.

provision_probe_sender.sh install runs on the VM. Here a fake adb keeps one
directory per guest, so the test runs the real script: it pushes the built
sender to both guests, checks the on-guest sha256 of each against the host
file, records it in the run manifest, and stops when the built sender is
missing or a guest holds other bytes. It never touches a VM.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
SCRIPT = BENCH / "scripts" / "provision_probe_sender.sh"

FAKE_ADB = r'''#!/usr/bin/env bash
serial=""
if [ "$1" = "-s" ]; then serial="$2"; shift 2; fi
dir="$FAKE_DIR/guest-${serial//[^0-9]/}"; mkdir -p "$dir"
case "$1" in
  connect|root|wait-for-device) exit 0 ;;
  push) cp "$2" "$dir/$(basename "$3")"
        [ "$serial" = "$FAKE_CORRUPT_SERIAL" ] && printf 'x' >> "$dir/$(basename "$3")"
        exit 0 ;;
  shell)
    shift; cmd="$*"
    case "$cmd" in
      sha256sum*) path="$(echo "$cmd" | awk '{print $2}')"; f="$dir/$(basename "$path")"
                  [ -f "$f" ] && sha256sum "$f" | awk -v p="$path" '{print $1"  "p}' ;;
      rm*) rm -f "$dir"/* ;;
    esac
    exit 0 ;;
esac
exit 0
'''


def run(tmp_path: Path, action: str, *, binary=True, corrupt="") -> tuple[subprocess.CompletedProcess, Path]:
    adb = tmp_path / "adb"
    adb.write_text(FAKE_ADB)
    adb.chmod(0o755)
    built = tmp_path / "out" / "de4sdv_probe_send"
    built.parent.mkdir(exist_ok=True)
    if binary:
        built.write_bytes(b"\x7fELF fake sender")
    run_dir = tmp_path / "run"
    env = {**os.environ, "ADB": str(adb), "FAKE_DIR": str(tmp_path), "RUN_DIR": str(run_dir),
           "PROBE_SENDER_BIN": str(built), "FAKE_CORRUPT_SERIAL": corrupt}
    result = subprocess.run(["bash", str(SCRIPT), action], capture_output=True, text=True, env=env, timeout=60)
    return result, run_dir


def test_install_pushes_to_both_guests_and_records_the_sha256_in_the_run_manifest(tmp_path):
    result, run_dir = run(tmp_path, "install")
    assert result.returncode == 0, result.stdout + result.stderr
    digest = hashlib.sha256(b"\x7fELF fake sender").hexdigest()
    manifest = (run_dir / "run-manifest.yaml").read_text()
    assert f"  host_sha256: {digest}" in manifest
    assert f"  core_sha256: {digest}" in manifest and f"  ivi_sha256: {digest}" in manifest
    assert "  guest_path: /data/local/tmp/de4sdv_probe_send" in manifest
    for guest in ("guest-00006521", "guest-00006522"):
        assert (tmp_path / guest / "de4sdv_probe_send").read_bytes() == b"\x7fELF fake sender"
    # The probe and the SD offer read the digest back through bench_env's helper.
    check = subprocess.run(["bash", "-c", f'. "{BENCH}/scripts/bench_env.sh"; '
                            f'run_manifest_sender_sha256 "{run_dir}/run-manifest.yaml"'],
                           capture_output=True, text=True)
    assert check.stdout.strip() == digest


def test_a_second_install_replaces_the_sender_block_once(tmp_path):
    run(tmp_path, "install")
    result, run_dir = run(tmp_path, "install")
    assert result.returncode == 0
    assert (run_dir / "run-manifest.yaml").read_text().count("probe_sender:") == 1


def test_install_stops_when_the_built_sender_is_missing(tmp_path):
    result, run_dir = run(tmp_path, "install", binary=False)
    assert result.returncode != 0
    assert "not found" in result.stdout + result.stderr
    assert not (run_dir / "run-manifest.yaml").exists()


def test_install_stops_when_a_guest_holds_other_bytes(tmp_path):
    result, run_dir = run(tmp_path, "install", corrupt="0.0.0.0:6521")
    assert result.returncode != 0
    manifest = run_dir / "run-manifest.yaml"
    assert not manifest.exists() or "host_sha256" not in manifest.read_text()
