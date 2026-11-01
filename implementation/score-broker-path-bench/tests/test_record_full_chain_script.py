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

# The host pane runs `journalctl -f`; a CI runner has the binary but no system
# journal, so it exits at once. Stub it the same way as adb, or the pane is
# judged dead for a reason that has nothing to do with the harness.
FAKE_JOURNALCTL = r'''#!/usr/bin/env bash
echo "journalctl $*" >> "$FAKE_DIR/calls.log"
exec sleep 20
'''

# On the bench the host half spans two scopes: the frame assembler runs as a
# system unit, the S-CORE daemons as the operator's --user units. This stub says
# so, which is the only way to test that the pane watches the journal that
# actually holds a unit instead of the other one.
FAKE_SYSTEMCTL = r'''#!/usr/bin/env bash
# `show -p LoadState --value <unit>`: loaded in the unit's own scope, not-found
# otherwise. `list-units --all --plain --no-legend <pattern>`: the units that
# pattern resolves to in that scope. Nothing else is modelled.
if [ "$1" = "--user" ]; then
  shift
  case "$1" in
    show) [ "${5%.service}" = "s2-someipd" ] && { echo "loaded"; exit 0; }; echo "not-found" ;;
    list-units) echo "s2-someipd.service loaded active running S-CORE SOME/IP daemon" ;;
    *) exit 1 ;;
  esac
  exit 0
fi
case "$1" in
  show) [ "${5%.service}" = "s2-bridge" ] && { echo "loaded"; exit 0; }; echo "not-found" ;;
  list-units) echo "s2-bridge.service loaded active running AEBS frame assembler" ;;
  *) exit 1 ;;
esac
exit 0
'''


def setup(tmp_path: Path) -> dict:
    bindir = tmp_path / "bin"
    bindir.mkdir()
    for name, body in (("adb", FAKE_ADB), ("journalctl", FAKE_JOURNALCTL)):
        path = bindir / name
        path.write_text(body)
        path.chmod(0o755)
    return {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", "ADB": str(bindir / "adb"),
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


def test_host_stack_pane_follows_the_journal_that_holds_each_unit(tmp_path):
    """A system unit and a --user unit need two journals and no replay.

    In the S3 window this pane watched `journalctl -u 'de4sdv-*'`, matched
    nothing, and replayed 13 lines from three hours earlier — stale output that
    looks like evidence. Both scopes must be followed, from now (-n 0), and the
    unit must be named rather than globbed.
    """
    env = setup(tmp_path)
    bin_path = Path(env["PATH"].split(os.pathsep)[0])
    systemctl = bin_path / "systemctl"
    systemctl.write_text(FAKE_SYSTEMCTL)
    systemctl.chmod(0o755)
    env["HOST_STACK_UNITS"] = "s2-bridge s2-someipd"
    out = tmp_path / "rec"
    result = run(env, "start", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    calls = [ln for ln in (tmp_path / "calls.log").read_text().splitlines() if ln.startswith("journalctl")]
    system = [c for c in calls if "--user" not in c]
    user = [c for c in calls if "--user" in c]
    assert len(system) == 1 and "-u s2-bridge" in system[0], calls
    assert len(user) == 1 and "-u s2-someipd" in user[0], calls
    for c in calls:
        assert "-n 0" in c, f"pane would replay the journal tail: {c}"
        assert "de4sdv-*" not in c, f"unit glob matches nothing: {c}"
    run(env, "stop", str(out))


def test_host_stack_units_pattern_is_expanded_in_both_scopes(tmp_path):
    """The bench names its units `s2-*`; a pattern has to become units.

    Without expansion a pattern resolves in no scope, the pane falls back to the
    whole journal, and the run's own lines are lost in the noise — the same
    silent-gap failure in a different shape.
    """
    env = setup(tmp_path)
    bin_path = Path(env["PATH"].split(os.pathsep)[0])
    systemctl = bin_path / "systemctl"
    systemctl.write_text(FAKE_SYSTEMCTL)
    systemctl.chmod(0o755)
    env["HOST_STACK_UNITS"] = "s2-*"
    out = tmp_path / "rec"
    result = run(env, "start", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    calls = [ln for ln in (tmp_path / "calls.log").read_text().splitlines() if ln.startswith("journalctl")]
    joined = " ".join(calls)
    assert "-u s2-bridge" in joined, calls
    assert "--user" in joined and "-u s2-someipd" in joined, calls
    assert "s2-*" not in joined, f"pattern reached journalctl: {calls}"
    run(env, "stop", str(out))


def test_host_stack_pane_follows_the_unit_log_files_when_given(tmp_path):
    """The units write to files, so the pane must follow the files.

    S3b: with four resolved units the pane still recorded nothing, because each
    unit runs `exec … >> logs/… 2>&1` — the journal holds their start and stop
    lines and no content. The S-CORE entry in `someipd.log` had 163 lines during
    that window and none of them reached the evidence.
    """
    env = setup(tmp_path)
    a = tmp_path / "someipd.log"
    b = tmp_path / "gatewayd.log"
    a.write_text("")
    b.write_text("")
    env["HOST_STACK_LOGS"] = f"{a} {b}"
    out = tmp_path / "rec"
    result = run(env, "start", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    calls = (tmp_path / "calls.log").read_text()
    assert "journalctl" not in calls, "the journal is the wrong source when files are given"
    run(env, "stop", str(out))
    manifest = (out / "recording-manifest.yaml").read_text()
    assert "host_stack_source: logs" in manifest


def test_start_refuses_a_log_file_that_does_not_exist(tmp_path):
    """A tail over a missing file records nothing; that must fail the start."""
    env = setup(tmp_path)
    env["HOST_STACK_LOGS"] = str(tmp_path / "not-there.log")
    out = tmp_path / "rec"
    result = run(env, "start", str(out))
    assert result.returncode != 0
    assert "does not exist" in result.stdout
    run(env, "stop", str(out))


def test_aeb_pane_is_recorded_when_its_command_is_set(tmp_path):
    """The Autoware-side hop gets its own pane, and the manifest says so."""
    env = setup(tmp_path)
    env["AEB_PANE_CMD"] = "sleep 20"
    out = tmp_path / "rec"
    result = run(env, "start", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    panes = sorted(p.name for p in out.glob(".pane.*.pid"))
    assert ".pane.aeb-decision.pid" in panes, panes
    run(env, "stop", str(out))
    manifest = (out / "recording-manifest.yaml").read_text()
    assert "aeb_pane: recorded" in manifest


def test_start_says_so_when_no_host_unit_resolves(tmp_path):
    """No systemd units (CI): follow the whole journal, but never silently."""
    env = setup(tmp_path)
    out = tmp_path / "rec"
    result = run(env, "start", str(out))
    assert result.returncode == 0, result.stdout + result.stderr
    assert "none of HOST_STACK_UNITS" in result.stdout + result.stderr
    assert "NOTE: AEB_PANE_CMD unset" in result.stdout + result.stderr
    run(env, "stop", str(out))
