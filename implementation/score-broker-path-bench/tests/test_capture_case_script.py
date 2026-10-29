"""capture_case.sh on stubs: the IVI-VM-down capture starts after the reboot (review R26 item 3).

The guest captures and the relay-log stream end when the IVI VM reboots, so
for the IVI-VM-down condition the captures must start after the reboot, and
the clock-start measurement must follow the clock setting that the case
judges from (VC-MW-020 condition 2). These tests run the real script with a fake
adb, a fake sudo/tcpdump and stub VM and clock helpers, and check the order of
the calls and the boot-identity guards. They never touch a VM.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
SCRIPT = BENCH / "scripts" / "capture_case.sh"

FAKE_ADB = r'''#!/usr/bin/env bash
serial=""
if [ "$1" = "-s" ]; then serial="$2"; shift 2; fi
case "$1" in
  connect|root|wait-for-device) exit 0 ;;
  logcat) [ "$2" = "-G" ] && exit 0; echo "adb logcat-stream" >> "$FAKE_DIR/calls.log"; exec sleep 20 ;;
  pull) : > "$3"; exit 0 ;;
  shell)
    shift; cmd="$*"
    case "$cmd" in
      *boot_id*) cat "$FAKE_DIR/boot_id" ;;
      *"tcpdump -i lo"*) echo "adb guest-capture-lo" >> "$FAKE_DIR/calls.log" ;;
      *"tcpdump -i sdv_dt"*) echo "adb guest-capture-vlan2" >> "$FAKE_DIR/calls.log" ;;
    esac
    exit 0 ;;
esac
exit 0
'''
FAKE_SUDO = r'''#!/usr/bin/env bash
if [ "$1" = tcpdump ]; then echo "sudo tcpdump $*" >> "$FAKE_DIR/calls.log"; exec sleep 20; fi
exec "$@"
'''
FAKE_VM = r'''#!/usr/bin/env bash
echo "vm $*" >> "$FAKE_DIR/calls.log"
[ "$1" = reboot-ivi ] && [ -z "$FAKE_SAME_BOOT" ] && echo "boot-2" > "$FAKE_DIR/boot_id"
exit 0
'''
FAKE_CLOCK = r'''#!/usr/bin/env bash
if [ -n "${2:-}" ]; then echo "clock $1 $(basename "$2")"; else echo "clock $1"; fi >> "$FAKE_DIR/calls.log"
exit 0
'''


def setup(tmp_path: Path, **extra) -> dict:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in (("adb", FAKE_ADB), ("sudo", FAKE_SUDO), ("vm.sh", FAKE_VM), ("clock.sh", FAKE_CLOCK)):
        path = bindir / name
        path.write_text(body)
        path.chmod(0o755)
    (tmp_path / "boot_id").write_text("boot-1\n")
    return {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "ADB": str(bindir / "adb"),
            "FAKE_DIR": str(tmp_path), "VM_SCRIPT": str(bindir / "vm.sh"), "CLOCK_SCRIPT": str(bindir / "clock.sh"),
            "RELAY_BIN": "x", "RELAY_RC": "x", "RELAY_LOGCAT_TAG": "relay_tag", "RELAY_SUBJECT_PACKAGE": "x",
            "RELAY_SUBJECT_BUNDLE": "x", "RELAY_SUBJECT_INSTANCE": "x", **extra}


def run(env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=90)


def calls(tmp_path: Path) -> list[str]:
    path = tmp_path / "calls.log"
    return path.read_text().splitlines() if path.exists() else []


def test_r26_ivi_vm_down_reboots_then_captures_then_sets_the_clock_then_measures(tmp_path):
    env = setup(tmp_path)
    out = tmp_path / "case"
    result = run(env, "ivi-vm-down", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    log = calls(tmp_path)
    reboot = log.index("vm reboot-ivi")
    capture = log.index("adb guest-capture-lo")
    stream = log.index("adb logcat-stream")
    setup_clock = log.index("clock setup")
    measure = log.index("clock measure clock-start.pcap")
    assert reboot < capture and reboot < stream < setup_clock < measure
    assert capture < setup_clock
    boot = (out / "ivi_boot.txt").read_text()
    assert "before_reboot: boot-1" in boot and "capture_start: boot-2" in boot
    run(env, "stop", str(out))


def test_r26_ivi_vm_down_stops_when_the_ivi_did_not_reboot(tmp_path):
    env = setup(tmp_path, FAKE_SAME_BOOT="1")
    result = run(env, "ivi-vm-down", str(tmp_path / "case"))
    assert result.returncode != 0
    assert "adb guest-capture-lo" not in calls(tmp_path)


def test_r26_stop_fails_when_the_ivi_rebooted_inside_the_capture(tmp_path):
    env = setup(tmp_path)
    out = tmp_path / "case"
    assert run(env, "start", str(out)).returncode == 0
    (tmp_path / "boot_id").write_text("boot-9\n")  # a reboot during the window ends the guest captures
    result = run(env, "stop", str(out))
    assert result.returncode != 0
    assert "capture_stop: boot-9" in (out / "ivi_boot.txt").read_text()
    assert "ivi_rebooted_in_window: true" in (out / "capture-manifest.yaml").read_text()


def test_a_plain_start_and_stop_with_one_boot_is_clean(tmp_path):
    env = setup(tmp_path)
    out = tmp_path / "case"
    assert run(env, "start", str(out)).returncode == 0
    result = run(env, "stop", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "ivi_rebooted_in_window: false" in (out / "capture-manifest.yaml").read_text()
