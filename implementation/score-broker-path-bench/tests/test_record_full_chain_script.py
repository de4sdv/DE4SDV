"""record_full_chain.sh on stubs: the recording anchors and the IVI frame-path pane.

The anchors (hmi-anchor.yaml) are what make the video and the logs comparable:
the IVI clock read immediately before and after the screenrecord launch brackets
the video's t=0, so a log line is placed on the video instead of being inferred
from the pixels. The fourth pane (ivi-frames) puts the ingress and the app on one
terminal, which is the "same moment" surface of the recording.

These run the real script with a fake adb, a fake hostscan gate and a real
`script` binary. They never touch a VM.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

BENCH = Path(__file__).resolve().parents[1]
SCRIPT = BENCH / "scripts" / "record_full_chain.sh"

# The gate reads `date +%s` and a logcat buffer; hostscan judges the newest
# onGatewayFrame line against that clock. The anchor reads `date +%s.%N` twice;
# the fake hands out two increasing values so the bracket is visible.
FAKE_ADB = r'''#!/usr/bin/env bash
serial=""
if [ "$1" = "-s" ]; then serial="$2"; shift 2; fi
case "$1" in
  connect|root|wait-for-device) exit 0 ;;
  logcat)
    [ "$2" = "-G" ] && exit 0
    if [ "$2" = "-d" ]; then
      echo "1793478495.871  5619  5653 I MainActivity: onGatewayFrame: frame seq=335 egoSpeed=6.5 pts=0 intervention=false warning=false braking=false lifecycle=armed range=null bearing=null rss=null"
    else
      echo "adb logcat-stream" >> "$FAKE_DIR/calls.log"
      exec sleep 20
    fi
    ;;
  pull) : > "$3"; exit 0 ;;
  shell)
    shift; cmd="$*"
    case "$cmd" in
      "date +%s") echo "1793478496" ;;
      "date +%s.%N")
        n=$(cat "$FAKE_DIR/clock_reads" 2>/dev/null || echo 0)
        echo "$((n + 1))" > "$FAKE_DIR/clock_reads"
        case "$n" in 0) echo "1793478496.100000000" ;; *) echo "1793478496.300000000" ;; esac ;;
      screenrecord*) echo "adb screenrecord" >> "$FAKE_DIR/calls.log"; exec sleep 20 ;;
      *) exit 0 ;;
    esac
    ;;
esac
exit 0
'''


def setup(tmp_path: Path) -> dict:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    adb = bindir / "adb"
    adb.write_text(FAKE_ADB)
    adb.chmod(0o755)
    return {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "ADB": str(adb),
            "FAKE_DIR": str(tmp_path),
            "RELAY_BIN": "x", "RELAY_RC": "x", "RELAY_LOGCAT_TAG": "relay_tag",
            "RELAY_SUBJECT_PACKAGE": "x", "RELAY_SUBJECT_BUNDLE": "x", "RELAY_SUBJECT_INSTANCE": "x"}


def run(env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), *args], capture_output=True, text=True, env=env, timeout=60)


def test_hmi_writes_the_anchor_pair_around_the_screenrecord_launch(tmp_path):
    env = setup(tmp_path)
    out = tmp_path / "rec"
    result = run(env, "hmi", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    anchor = (out / "hmi-anchor.yaml").read_text()
    assert "schema: de4sdv.recording-anchor.v1" in anchor
    assert "ivi_before_epoch_s: 1793478496.100000000" in anchor
    assert "ivi_after_epoch_s: 1793478496.300000000" in anchor
    assert "host_before:" in anchor and "host_after:" in anchor
    assert "the video's t=0 lies in that interval" in anchor
    # the gate record it belongs to is written too
    gate = (out / "monitoring-gate.json").read_text()
    assert '"monitoring": true' in gate
    # the launch itself happened between the two reads
    calls = (tmp_path / "calls.log").read_text().splitlines()
    assert "adb screenrecord" in calls
    run(env, "stop", str(out))


def test_hmi_refuses_before_writing_an_anchor_when_the_gate_fails(tmp_path):
    env = setup(tmp_path)
    out = tmp_path / "rec"
    # a stale frame line: the buffer's newest line is far behind the guest clock
    adb = Path(env["ADB"])
    adb.write_text(FAKE_ADB.replace("1793478495.871", "1793478000.871"))
    result = run(env, "hmi", str(out))
    assert result.returncode != 0
    assert "REFUSING" in result.stdout
    assert not (out / "hmi-anchor.yaml").exists()


def test_start_records_the_ivi_frame_path_pane(tmp_path):
    env = setup(tmp_path)
    out = tmp_path / "rec"
    result = run(env, "start", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    panes = sorted(p.name for p in out.glob(".pane.*.pid"))
    assert panes == [".pane.core-broker.pid", ".pane.host-stack.pid",
                     ".pane.ivi-frames.pid", ".pane.relay.pid"]
    assert (out / "ivi-frames.typescript").exists()
    run(env, "stop", str(out))
