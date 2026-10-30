"""The SD-offer step on a fake adb: the sender gate, the core logcat around the offer, the record.

send_sd_offer.sh send runs on the VM. Here a fake adb stands in for both
guests, so the test runs the real script: it must stop when the sender is
missing or differs from the run manifest, send from the SD source port with
the sender, take the SDV Core VM's logcat around the send and write
sd_core_processed.json (review R43). It never touches a VM.
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
SCRIPT = BENCH / "scripts" / "send_sd_offer.sh"
SENDER_SHA = "a" * 64

FAKE_ADB = r'''#!/usr/bin/env bash
# Fake adb: the IVI answers the route and runs the sender; the core answers its
# clock and streams its logcat (the stack's line about the offer).
log="$FAKE_DIR/adb.log"
serial=""
if [ "$1" = "-s" ]; then serial="$2"; shift 2; fi
echo "$serial $*" >> "$log"
case "$1" in
  connect|root|wait-for-device) exit 0 ;;
  logcat)
    echo "1793000000.900000   812   830 W vsomeip : $FAKE_CORE_LINE"
    sleep 30 ;;
  shell)
    shift; cmd="$*"
    case "$cmd" in
      *"ip route get"*) echo "192.168.98.1 dev eth1 src 192.168.98.118 uid 0" ;;
      "date +%s"*) echo "1793000000" ;;
      *sha256sum*) [ -n "$FAKE_IVI_SHA" ] && echo "$FAKE_IVI_SHA  /data/local/tmp/de4sdv_probe_send" ;;
      *de4sdv_probe_send*) echo "$cmd" > "$FAKE_DIR/sent.txt"; exit "${FAKE_SEND_RC:-0}" ;;
    esac ;;
esac
exit 0
'''


def run_send(tmp_path: Path, *, ivi_sha=SENDER_SHA, core_line="process_offerservice_serviceentry: Ignoring offer "
             "of [4dee.0001]", manifest=True) -> tuple[subprocess.CompletedProcess, Path]:
    adb = tmp_path / "adb"
    adb.write_text(FAKE_ADB)
    adb.chmod(0o755)
    run_dir, out = tmp_path / "run", tmp_path / "case"
    run_dir.mkdir()
    if manifest:
        (run_dir / "run-manifest.yaml").write_text(f"probe_sender:\n  host_sha256: {SENDER_SHA}\n")
    env = {**os.environ, "ADB": str(adb), "FAKE_DIR": str(tmp_path), "FAKE_IVI_SHA": ivi_sha,
           "FAKE_CORE_LINE": core_line, "RUN_DIR": str(run_dir), "SD_PROCESS_WAIT_S": "1"}
    result = subprocess.run(["bash", str(SCRIPT), "send", "192.168.98.118", "30509", str(out)],
                            capture_output=True, text=True, env=env, timeout=60)
    return result, out


def test_r43_the_send_step_records_that_the_core_processed_the_offer(tmp_path):
    result, out = run_send(tmp_path)
    assert result.returncode == 0, result.stdout + result.stderr
    sent = (tmp_path / "sent.txt").read_text()
    assert "--sport 30490" in sent and "--port 30490" in sent and "--device eth1" in sent
    record = json.loads((out / "sd_core_processed.json").read_text())
    assert record["status"] == "processed" and record["result"] == "secure_service_rejected"
    assert record["since_epoch_s"] == 1792999999.0  # the core clock just before the send, less a second
    assert (out / "core-logcat-sd-offer.txt").read_text().strip()


def test_r43_no_line_from_the_core_gives_unknown(tmp_path):
    result, out = run_send(tmp_path, core_line="unrelated line")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads((out / "sd_core_processed.json").read_text())["status"] == "unknown"


def test_the_send_step_stops_when_the_sender_is_missing_on_the_ivi(tmp_path):
    result, out = run_send(tmp_path, ivi_sha="")
    assert result.returncode != 0
    assert not (tmp_path / "sent.txt").exists()
    assert "sender" in (result.stdout + result.stderr)


def test_the_send_step_stops_when_the_sender_differs_from_the_run_manifest(tmp_path):
    result, _out = run_send(tmp_path, ivi_sha="b" * 64)
    assert result.returncode != 0
    assert not (tmp_path / "sent.txt").exists()


def test_the_send_step_stops_without_a_run_manifest(tmp_path):
    result, _out = run_send(tmp_path, manifest=False)
    assert result.returncode != 0
    assert not (tmp_path / "sent.txt").exists()
