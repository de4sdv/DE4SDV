"""The guest-host and safety-net scripts of the session kit, run for real (bash) against fake tools on PATH.

The fakes (sudo, pgrep, cvd, adb, ip, the guest build script, the launch script) log every call to calls.log; a
file holds the number of crosvm processes. Expected orders come from the lead's B13.3 (the guests' stop before any
power-off, none with guests running), the guest-prep-20261118 operator's report (cvd stop then no crosvm; fresh
guests; Enforcing unless the session is marked permissive) and B10.2 (am start -S before each window).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REMOTE = HERE.parent / "remote"

FAKES = {
    "sudo": '#!/bin/bash\necho "sudo $*" >> "$FAKE/calls.log"\n[ "$1" = shutdown ] || [ "$1" = systemd-run ] && exit 0\n'
            'exec "$@"\n',
    "pgrep": '#!/bin/bash\necho "pgrep $*" >> "$FAKE/calls.log"\nn=$(cat "$FAKE/crosvm" 2>/dev/null || echo 0)\n'
             'echo "$n"; [ "$n" != 0 ]\n',
    "cvd": '#!/bin/bash\necho "cvd $*" >> "$FAKE/calls.log"\n'
           'if [ "$1" = fleet ]; then echo \'{"groups": [{"group_name": "cvd_1"}, {"group_name": "cvd_2"}]}\'; exit 0; fi\n'
           'case "$*" in *stop*) [ -e "$FAKE/stubborn" ] || { n=$(cat "$FAKE/crosvm"); echo $((n > 0 ? n - 1 : 0)) '
           '> "$FAKE/crosvm"; } ;; esac\n',
    "ip": '#!/bin/bash\necho "ip $*" >> "$FAKE/calls.log"\n'
          'case "$*" in "route get"*) echo "multicast 224.0.0.251 dev ${FAKE_ROUTE_DEV:-cvd-ebr} table local";; esac\n',
    "adb": '#!/bin/bash\necho "adb $*" >> "$FAKE/calls.log"\n[ "$1" = -s ] && shift 2\nc="$*"\n'
           'case "$c" in\n'
           '  "shell getprop sys.boot_completed") echo 1 ;;\n'
           '  "shell getenforce") cat "$FAKE/mode" 2>/dev/null || echo Enforcing ;;\n'
           '  "shell pm path "*) [ -e "$FAKE/no_app" ] || echo "package:/vendor/priv-app/App/App.apk" ;;\n'
           '  "shell sha256sum "*) echo "abc123  $3" ;;\n'
           '  "shell am start"*) echo "Starting: Intent { cmp=$6 }"; echo "Status: ok" ;;\n'
           '  "shell pidof "*) [ -e "$FAKE/no_pid" ] || echo 4242 ;;\n'
           '  "logcat -d") cat "$FAKE/logcat" 2>/dev/null ;;\n'
           '  "logcat -d -T "*) cat "$FAKE/logcat_since_mark" 2>/dev/null ;;\n'
           '  "shell date +%s.%N") LC_ALL=C awk -v o="$(cat "$FAKE/guest_off" 2>/dev/null || echo 0)" -v t="$(date +%s.%N)" '
           '\'BEGIN { printf "%.6f\\n", t + o }\' ;;\n'
           '  "shell toybox date -s "*) [ -e "$FAKE/clock_settable" ] && echo 0 > "$FAKE/guest_off" ;;\n'
           'esac\nexit 0\n',
}


@pytest.fixture()
def fake(tmp_path: Path) -> tuple[Path, dict[str, str]]:
    d = tmp_path / "fake"
    (d / "bin").mkdir(parents=True)
    for name, body in FAKES.items():
        (d / "bin" / name).write_text(body)
        (d / "bin" / name).chmod(0o755)
    (d / "crosvm").write_text("2\n")
    env = dict(os.environ, FAKE=str(d), PATH=f"{d / 'bin'}:{os.environ['PATH']}", ADB=str(d / "bin" / "adb"),
               CVD=str(d / "bin" / "cvd"), HOME=str(tmp_path / "home"), STOP_SETTLE_S="0", START_WAIT_S="0",
               POLL_S="0")
    (tmp_path / "home").mkdir()
    return d, env


def calls(d: Path) -> list[str]:
    p = d / "calls.log"
    return p.read_text().splitlines() if p.exists() else []


def sh(*args: str, env: dict[str, str], timeout: float = 60) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", *args], env=env, capture_output=True, text=True, timeout=timeout)


# ---------------------------------------------------------------------------------------- guest_stop.sh


def test_guest_stop_stops_every_group_and_reports_no_crosvm(fake) -> None:
    d, env = fake
    p = sh(str(REMOTE / "guest_stop.sh"), env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert p.stdout.strip().splitlines()[-1] == "crosvm_processes_after_stop: 0"
    assert [c for c in calls(d) if c.startswith("cvd --group_name")] == \
        ["cvd --group_name=cvd_1 stop", "cvd --group_name=cvd_2 stop"]
    assert not any("smoke_boot" in c or "verify-images" in c for c in calls(d))


def test_guest_stop_fails_when_a_crosvm_is_left(fake) -> None:
    d, env = fake
    (d / "stubborn").touch()
    p = sh(str(REMOTE / "guest_stop.sh"), env=env)
    assert p.returncode == 1
    assert p.stdout.strip().splitlines()[-1] == "crosvm_processes_after_stop: 2"
    assert len([c for c in calls(d) if c.startswith("cvd --group_name")]) == 4      # two tries


# --------------------------------------------------------------------------------------- safety_net.sh


def _kit(tmp_path: Path) -> Path:
    """safety_net.sh in a kit layout (~/da-kit/<sid>/bench/session/remote/), as the session uploads it."""
    remote = tmp_path / "home" / "da-kit" / "S1" / "bench" / "session" / "remote"
    remote.mkdir(parents=True)
    (remote / "safety_net.sh").write_bytes((REMOTE / "safety_net.sh").read_bytes())
    return remote / "safety_net.sh"


def test_safety_net_fire_stops_the_guests_before_the_power_off(tmp_path: Path, fake) -> None:
    d, env = fake
    net = _kit(tmp_path)
    stop = f'echo "guests stop" >> "{d}/calls.log"; echo 0 > "{d}/crosvm"'
    p = sh(str(net), "fire", stop, env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    log = calls(d)
    assert log.index("guests stop") < log.index("sudo shutdown -h now")
    assert "no crosvm left: powering off" in (net.parents[3] / "safety_net.log").read_text()


def test_safety_net_never_powers_off_with_guests_running(tmp_path: Path, fake) -> None:
    d, env = fake
    net = _kit(tmp_path)
    p = sh(str(net), "fire", f'echo "guests stop" >> "{d}/calls.log"', env=env)   # crosvm stays at 2
    assert p.returncode == 1
    assert "guests stop" in calls(d) and not any("shutdown" in c for c in calls(d))
    assert "NOT powering off" in (net.parents[3] / "safety_net.log").read_text()


def test_safety_net_arm_on_the_guest_host_is_a_timer_that_fires_the_stop(tmp_path: Path, fake) -> None:
    d, env = fake
    net = _kit(tmp_path)
    p = sh(str(net), "arm", "12", "bash $HOME/da-kit/S1/bench/session/remote/guest_stop.sh", env=env)
    assert p.returncode == 0 and p.stdout.strip() == "safety-net-12"
    (timer,) = [c for c in calls(d) if c.startswith("sudo systemd-run")]
    assert "--on-active=12min" in timer and "--unit=da-safety-net-S1" in timer
    assert timer.endswith("safety_net.sh fire bash $HOME/da-kit/S1/bench/session/remote/guest_stop.sh")
    assert not any("shutdown" in c for c in calls(d))


def test_safety_net_arm_elsewhere_is_a_plain_shutdown(tmp_path: Path, fake) -> None:
    d, env = fake
    p = sh(str(_kit(tmp_path)), "arm", "12", env=env)
    assert p.returncode == 0 and p.stdout.strip() == "safety-net-12"
    assert calls(d) == ["sudo shutdown -h +12"]


# ------------------------------------------------------------------------------------ guest_prepare.sh


def _build_script(tmp_path: Path, fail: str = "") -> Path:
    """A stand-in with the real script's layout (guest-build/build_guests_incremental.sh: LOGS, IDENT and WORK derived
    under B12_DIR, step logs b12-<step>.log, the summary and the app's identity under identity/, verify's output in
    work/app-verify.out). It refuses a caller's LOGS, IDENT or WORK outright (exit 2): the session sets none."""
    s = tmp_path / "build_guests_incremental.sh"
    s.write_text('#!/bin/bash\n'
                 'echo "build $1 IVI_PERMISSIVE=$IVI_PERMISSIVE B12_DIR=$B12_DIR" >> "$FAKE/calls.log"\n'
                 'echo "rerun $B12_RERUN_CMD" >> "$FAKE/calls.log"\n'
                 '[ -n "${LOGS+x}${IDENT+x}${WORK+x}" ] && { echo "caller set LOGS/IDENT/WORK" >> "$FAKE/calls.log"; '
                 'exit 2; }\n'
                 'LOGS=$B12_DIR/logs; IDENT=$B12_DIR/identity; WORK=$B12_DIR/work\n'
                 'mkdir -p "$LOGS" "$IDENT" "$WORK"; echo "log of $1" > "$LOGS/b12-$1.log"\n'
                 'echo "$(date -u) $1: done" >> "$IDENT/b12-summary.txt"\n'
                 '[ "$1" = install ] && echo "apk_guest_sha256: abc" > "$IDENT/ivi-warning-app-identity.txt"\n'
                 '[ "$1" = verify ] && { echo "initComms ok" > "$WORK/app-verify.out"; '
                 'echo "logcat line" > "$IDENT/b12-app-logcat.txt"; }\n'
                 f'[ "$1" = "{fail}" ] && exit 1\nexit 0\n')
    return s


def test_guest_prepare_runs_install_then_verify_and_keeps_their_records(tmp_path: Path, fake) -> None:
    d, env = fake
    ab = tmp_path / "ab"
    env = dict(env, GUEST_BUILD_SCRIPT=str(_build_script(tmp_path)), AB=str(ab), DA_SESSION_ID="s1")
    (ab / "b12-session-s1" / "identity").mkdir(parents=True)
    (ab / "b12-session-s1" / "identity" / "b12-summary.txt").write_text("an earlier run\n")
    out = tmp_path / "out"
    p = sh(str(REMOTE / "guest_prepare.sh"), str(out), env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert [c for c in calls(d) if c.startswith("build")] == \
        [f"build install IVI_PERMISSIVE=0 B12_DIR={ab}/b12-session-s1",
         f"build verify IVI_PERMISSIVE=0 B12_DIR={ab}/b12-session-s1"]
    for name in ("b12-install.log", "b12-verify.log", "ivi-warning-app-identity.txt", "b12-app-logcat.txt",
                 "app-verify.out"):
        assert (out / name).exists(), name
    assert "an earlier run" not in (out / "b12-summary-this-run.txt").read_text()


def test_guest_prepare_stops_at_a_failed_install(tmp_path: Path, fake) -> None:
    d, env = fake
    env = dict(env, GUEST_BUILD_SCRIPT=str(_build_script(tmp_path, fail="install")), AB=str(tmp_path / "ab"),
               IVI_PERMISSIVE="1", DA_SESSION_ID="s1")
    out = tmp_path / "out"
    p = sh(str(REMOTE / "guest_prepare.sh"), str(out), env=env)
    assert p.returncode == 1
    assert [c for c in calls(d) if c.startswith("build")] == \
        [f"build install IVI_PERMISSIVE=1 B12_DIR={tmp_path}/ab/b12-session-s1"]
    assert (out / "b12-install.log").exists()   # the failed step's log is kept


def test_guest_prepare_never_hands_the_build_script_logs_ident_or_work(tmp_path: Path, fake) -> None:
    d, env = fake
    ab = tmp_path / "ab"   # the 2026-11-17 kit's folders, which the real script refuses with exit 2
    env = dict(env, GUEST_BUILD_SCRIPT=str(_build_script(tmp_path)), AB=str(ab), DA_SESSION_ID="s1",
               LOGS=str(ab / "logs"), IDENT=str(ab / "identity"), WORK=str(ab / "work"))
    p = sh(str(REMOTE / "guest_prepare.sh"), str(tmp_path / "out"), env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "caller set LOGS/IDENT/WORK" not in calls(d)


def test_guest_prepare_refuses_without_a_session_id(tmp_path: Path, fake) -> None:
    d, env = fake
    env = {k: v for k, v in env.items() if k != "DA_SESSION_ID"}
    env.update(GUEST_BUILD_SCRIPT=str(_build_script(tmp_path)), AB=str(tmp_path / "ab"))
    p = sh(str(REMOTE / "guest_prepare.sh"), str(tmp_path / "out"), env=env)
    assert p.returncode == 1 and "no DA_SESSION_ID" in p.stdout
    assert not [c for c in calls(d) if c.startswith("build")]


def test_guest_prepare_names_the_session_as_the_permissive_rerun(tmp_path: Path, fake) -> None:
    d, env = fake
    env = dict(env, GUEST_BUILD_SCRIPT=str(_build_script(tmp_path)), AB=str(tmp_path / "ab"), DA_SESSION_ID="s1")
    assert sh(str(REMOTE / "guest_prepare.sh"), str(tmp_path / "out"), env=env).returncode == 0
    reruns = [c for c in calls(d) if c.startswith("rerun ")]
    assert reruns and all("da_session.sh" in c and "--permissive-ivi" in c for c in reruns)
    assert not any("build_guests_incremental.sh" in c for c in reruns)


def test_guest_prepare_collects_where_the_guest_build_script_writes() -> None:
    script = (HERE.parent.parent / "guest-build" / "build_guests_incremental.sh").read_text()
    for line in (': "${LOGS:=$B12_DIR/logs}"', ': "${IDENT:=$B12_DIR/identity}"', ': "${WORK:=$B12_DIR/work}"',
                 'SUMMARY="$IDENT/b12-summary.txt"', 'tee -a "$LOGS/b12-$1.log"', '> "$WORK/app-verify.out"',
                 '> "$IDENT/b12-app-logcat.txt"', 'cp -f "$identity" "$IDENT/"',
                 'local identity="$WORK/app/ivi-warning-app-identity.txt"',
                 'if [ -n "${B12_RERUN_CMD:-}" ]; then printf \'%s\' "$B12_RERUN_CMD"'):
        assert line in script, line


def test_guest_prepare_wraps_steps_the_guest_build_script_has() -> None:
    script = (HERE.parent.parent / "guest-build" / "build_guests_incremental.sh").read_text()
    assert "  install) install_app ;;" in script and "  verify) verify ;;" in script


# -------------------------------------------------------------------------------------- app_restart.sh

APP = {"APP_PACKAGE": "org.de4sdv.collisionwarning", "APP_COMPONENT": "org.de4sdv.collisionwarning/.MainActivity"}


def test_app_restart_records_selinux_and_restarts_with_am_start_s(tmp_path: Path, fake) -> None:
    d, env = fake
    p = sh(str(REMOTE / "app_restart.sh"), str(tmp_path / "o"), "run1", env=dict(env, **APP))
    assert p.returncode == 0, p.stdout + p.stderr
    rec = (tmp_path / "o" / "app_restart_run1.txt").read_text()
    assert "getenforce core Enforcing" in rec and "getenforce ivi Enforcing" in rec
    assert "apk /vendor/priv-app/App/App.apk sha256 abc123" in rec and "pid 4242" in rec
    starts = [c for c in calls(d) if " am start" in c]
    assert starts == ["adb -s 0.0.0.0:6522 shell am start -S -W -n org.de4sdv.collisionwarning/.MainActivity"]
    assert not any("setenforce" in c for c in calls(d))


@pytest.mark.parametrize("marker, starts", [("no_app", 0), ("no_pid", 1)])
def test_app_restart_fails_without_the_app_or_its_process(tmp_path: Path, fake, marker: str, starts: int) -> None:
    d, env = fake
    (d / marker).touch()
    p = sh(str(REMOTE / "app_restart.sh"), str(tmp_path / "o"), "w", env=dict(env, **APP))
    assert p.returncode == 1
    assert len([c for c in calls(d) if " am start" in c]) == starts


# -------------------------------------------------------------------------------------- offer_check.sh


def test_the_multicast_route_goes_to_the_guest_bridge(tmp_path: Path, fake) -> None:
    d, env = fake
    p = sh(str(REMOTE / "offer_check.sh"), "route", str(tmp_path / "o"), env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    assert "sudo ip route replace 224.0.0.0/4 dev cvd-ebr" in calls(d)
    bad = sh(str(REMOTE / "offer_check.sh"), "route", str(tmp_path / "o2"), env=dict(env, FAKE_ROUTE_DEV="ens4"))
    assert bad.returncode == 1


def _ids() -> tuple[str, str]:
    d = json.loads((HERE.parent.parent / "interfaces" / "service_ids.json").read_text())
    return d["icd"]["data_tunnel"]["service_unit"], d["icd"]["someip_warning_request"]["service_id"]


def test_the_unit_check_passes_on_a_registration_line(tmp_path: Path, fake) -> None:
    d, env = fake
    unit, _ = _ids()
    (d / "logcat").write_text(f"11-19 08:00:00.000 1 2 I SomeIpBroker: registered unit {unit}\n")
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), env=dict(env, UNIT_WAIT_S="0"))
    assert p.returncode == 0, p.stdout
    assert f"UNIT_REGISTERED {unit}" in p.stdout
    assert unit in (tmp_path / "o" / "unit_lines.txt").read_text()


def test_the_unit_check_fails_on_a_broker_error_for_the_service_or_no_registration(tmp_path: Path, fake) -> None:
    d, env = fake
    unit, service = _ids()
    (d / "logcat").write_text(f"11-19 08:00:00.000 1 2 E someip_broker_agent: no mapping for service "
                              f"{service[2:]}\n11-19 08:00:01.000 1 2 I SomeIpBroker: registered unit {unit}\n")
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), env=dict(env, UNIT_WAIT_S="0"))
    assert p.returncode == 1 and "broker errors" in p.stdout
    (d / "logcat").write_text("11-19 08:00:00.000 1 2 I SomeIpBroker: started\n")
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o2"), env=dict(env, UNIT_WAIT_S="0"))
    assert p.returncode == 1 and "no registration" in p.stdout


# ------------------------------------------------------------------------------------------ guest_up.sh


def _launch(tmp_path: Path) -> Path:
    root = tmp_path / "de4sdv"
    s = root / "implementation" / "score-broker-path-bench" / "scripts" / "launch_two_vms.sh"
    s.parent.mkdir(parents=True)
    s.write_text('#!/bin/bash\necho "launch $1" >> "$FAKE/calls.log"\n')
    return root


@pytest.mark.parametrize("permissive", ["0", "1"])
def test_guest_up_creates_fresh_guests_and_sets_permissive_only_when_marked(tmp_path: Path, fake,
                                                                           permissive: str) -> None:
    d, env = fake
    env = dict(env, DE4SDV_ROOT=str(_launch(tmp_path)), IVI_PERMISSIVE=permissive, BOOT_WAIT_S="5")
    p = sh(str(REMOTE / "guest_up.sh"), str(tmp_path / "o"), env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    log = calls(d)
    assert log.index("launch down") < log.index("launch up")
    setenforce = [c for c in log if "setenforce" in c]
    assert setenforce == (["adb -s 0.0.0.0:6522 shell setenforce 0"] if permissive == "1" else [])
    ident = (tmp_path / "o" / "guest_identity.txt").read_text()
    assert ident.count("getenforce ") == 2


@pytest.mark.parametrize("line", [
    "I SomeIpBroker: unit {unit} unregistered",
    "W SomeIpBroker: unit {unit} not registered: no provider of 0x4df1 yet",
    "W SomeIpBroker: failed to register unit {unit}",
])
def test_the_unit_check_refuses_a_negated_registration(tmp_path: Path, fake, line: str) -> None:
    # R7: a line naming the unit and "regist" that says the opposite is no registration
    d, env = fake
    unit, _ = _ids()
    (d / "logcat").write_text("11-19 08:00:00.000 1 2 " + line.format(unit=unit) + "\n")
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), env=dict(env, UNIT_WAIT_S="0"))
    assert p.returncode == 1 and "no registration" in p.stdout, p.stdout


def test_the_unit_check_reads_only_the_log_since_the_mark(tmp_path: Path, fake) -> None:
    # R7: a broker error that names the service from before the S-CORE side's start (the offer) is no failure of
    # the check after it; the mark is the SDV Core guest's clock read before the start
    d, env = fake
    unit, service = _ids()
    reg = f"11-19 08:00:01.000 1 2 I SomeIpBroker: registered unit {unit}\n"
    (d / "logcat").write_text(f"11-19 07:59:00.000 1 2 E someip_broker_agent: service {service[2:]} not available\n"
                              + reg)
    (d / "logcat_since_mark").write_text(reg)
    (d / "guest_off").write_text("0\n")
    mark = tmp_path / "mark"
    m = sh(str(REMOTE / "offer_check.sh"), "mark", str(mark), env=env)
    assert m.returncode == 0 and m.stdout.startswith("LOGCAT_MARK "), m.stdout
    since = (mark / "logcat_since.txt").read_text().strip()
    assert re.fullmatch(r"\d+\.\d{3}", since)
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark), env=dict(env, UNIT_WAIT_S="0"))
    assert p.returncode == 0, p.stdout
    assert f"adb -s 0.0.0.0:6521 logcat -d -T {since}" in calls(d)
    whole = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o2"), env=dict(env, UNIT_WAIT_S="0"))
    assert whole.returncode == 1 and "broker errors" in whole.stdout     # the same log read since the boot


def test_the_receipts_of_a_window_are_counted(tmp_path: Path, fake) -> None:
    d, env = fake
    cap = tmp_path / "cap"
    cap.mkdir()
    p = sh(str(REMOTE / "offer_check.sh"), "receipts", str(cap), env=env)
    assert p.returncode == 0 and p.stdout.strip() == "RECEIPTS 0"
    (cap / "app_record_warning.jsonl").write_text('{"a": 1}\n{"a": 2}\n')
    p = sh(str(REMOTE / "offer_check.sh"), "receipts", str(cap), env=env)
    assert p.stdout.strip() == "RECEIPTS 2"


def test_the_neighbour_caches_of_both_guests_are_flushed(tmp_path: Path, fake) -> None:
    # R18: the S-CORE host takes 192.168.98.1 over the VXLAN with another MAC
    d, env = fake
    p = sh(str(REMOTE / "offer_check.sh"), "neigh", str(tmp_path / "o"), env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    flush = [c for c in calls(d) if "ip neigh flush" in c]
    assert flush == ["adb -s 0.0.0.0:6521 shell ip neigh flush dev eth1",
                     "adb -s 0.0.0.0:6522 shell ip neigh flush dev eth1"]
