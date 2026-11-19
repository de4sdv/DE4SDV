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
import tarfile
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
REMOTE = HERE.parent / "remote"

FAKES = {
    "sudo": '#!/bin/bash\necho "sudo $*" >> "$FAKE/calls.log"\n[ "$1" = shutdown ] || [ "$1" = systemd-run ] && exit 0\n'
            'exec "$@"\n',
    "systemctl": '#!/bin/bash\necho "systemctl $*" >> "$FAKE/calls.log"\n'
                 'last="${@: -1}"; [ "$1" = list-timers ] && [ ! -e "$FAKE/no_timer" ] && '
                 'echo "Thu 2026-11-19 12:00:00 UTC 4h left - - $last ${last%.timer}.service"\nexit 0\n',
    "pgrep": '#!/bin/bash\necho "pgrep $*" >> "$FAKE/calls.log"\n[ -e "$FAKE/pgrep_error" ] && exit 2\n'
             'n=$(cat "$FAKE/crosvm" 2>/dev/null || echo 0)\necho "$n"; [ "$n" != 0 ]\n',
    "cvd": '#!/bin/bash\necho "cvd $*" >> "$FAKE/calls.log"\n'
           'if [ "$1" = fleet ]; then echo \'{"groups": [{"group_name": "cvd_1"}, {"group_name": "cvd_2"}]}\'; exit 0; fi\n'
           'case "$*" in *stop*) [ -e "$FAKE/stubborn" ] || { n=$(cat "$FAKE/crosvm"); echo $((n > 0 ? n - 1 : 0)) '
           '> "$FAKE/crosvm"; } ;; esac\n',
    "ip": '#!/bin/bash\necho "ip $*" >> "$FAKE/calls.log"\n'
          'case "$*" in "route get"*) echo "multicast 224.0.0.251 dev ${FAKE_ROUTE_DEV:-cvd-ebr} table local";; esac\n',
    # logcat per guest: $FAKE/logcat_<serial> (whole buffer) and logcat_since_mark_<serial> (-T), else the shared
    # logcat / logcat_since_mark; $FAKE/late_<serial> is added to a read once that guest's reads exceed
    # late_after_<serial> (a line that arrives late); guest_off_<serial> is that guest's clock offset
    "adb": '#!/bin/bash\necho "adb $*" >> "$FAKE/calls.log"\nserial=""\n[ "$1" = -s ] && { serial=$2; shift 2; }\nc="$*"\n'
           'late() { local k="$FAKE/reads_$serial" n; n=$(( $(cat "$k" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$k"\n'
           '  [ -e "$FAKE/late_$serial" ] && [ "$n" -gt "$(cat "$FAKE/late_after_$serial" 2>/dev/null || echo 0)" ] '
           '&& cat "$FAKE/late_$serial"; return 0; }\n'
           'pick() { [ -e "$FAKE/$1_$serial" ] && cat "$FAKE/$1_$serial" || cat "$FAKE/$1" 2>/dev/null; return 0; }\n'
           'case "$c" in\n'
           '  "shell ip "*) echo "fake-net $serial: ${c#shell }" ;;\n'
           '  "shell getprop sys.boot_completed") echo 1 ;;\n'
           '  "shell getenforce") cat "$FAKE/mode_$serial" 2>/dev/null || echo Enforcing ;;\n'
           '  "shell pm path "*) [ -e "$FAKE/no_app" ] || echo "package:/vendor/priv-app/App/App.apk" ;;\n'
           '  "shell sha256sum "*) echo "abc123  $3" ;;\n'
           '  "shell am start"*) echo "Starting: Intent { cmp=$6 }"; echo "Status: ok" ;;\n'
           '  "shell pidof "*) [ -e "$FAKE/no_pid" ] || echo 4242 ;;\n'
           '  "logcat -d") pick logcat; late ;;\n'
           '  "logcat -d -T "*) pick logcat_since_mark; late ;;\n'
           '  "shell date +%s.%N") [ -e "$FAKE/no_clock_$serial" ] || LC_ALL=C awk -v o="$(pick guest_off | head -1)" -v t="$(date +%s.%N)" '
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


def test_guest_stop_fails_when_the_crosvm_count_fails(fake) -> None:
    # S11: a pgrep that errors (rc 2, no output) is no count of 0
    d, env = fake
    (d / "crosvm").write_text("0\n")
    (d / "pgrep_error").touch()
    p = sh(str(REMOTE / "guest_stop.sh"), env=env)
    assert p.returncode == 1, p.stdout + p.stderr
    assert p.stdout.strip().splitlines()[-1] == "crosvm_processes_after_stop: unknown"


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


def test_safety_net_never_powers_off_when_the_crosvm_count_fails(tmp_path: Path, fake) -> None:
    # S11: a pgrep that errors (rc 2, no output) counted as "no crosvm left", and the fire powered off
    d, env = fake
    net = _kit(tmp_path)
    (d / "pgrep_error").touch()
    p = sh(str(net), "fire", f'echo "guests stop" >> "{d}/calls.log"; echo 0 > "{d}/crosvm"', env=env)
    assert p.returncode == 1
    assert "guests stop" in calls(d) and not any("shutdown" in c or "poweroff" in c for c in calls(d))
    log = (net.parents[3] / "safety_net.log").read_text()
    assert "crosvm count unknown" in log and "NOT powering off" in log


def test_safety_net_arm_on_the_guest_host_is_a_timer_that_fires_the_stop(tmp_path: Path, fake) -> None:
    d, env = fake
    net = _kit(tmp_path)
    p = sh(str(net), "arm", "12", "bash $HOME/da-kit/S1/bench/session/remote/guest_stop.sh", env=env)
    assert p.returncode == 0 and p.stdout.strip().splitlines()[-1] == "safety-net-12"
    (timer,) = [c for c in calls(d) if c.startswith("sudo systemd-run")]
    assert "--on-active=12min" in timer and "--unit=da-safety-net-S1" in timer
    assert timer.endswith("safety_net.sh fire bash $HOME/da-kit/S1/bench/session/remote/guest_stop.sh")
    assert not any("shutdown" in c for c in calls(d))


def test_safety_net_arm_elsewhere_is_a_poweroff_timer_and_lists_it(tmp_path: Path, fake) -> None:
    # R15: not shutdown -h +N, whose last 5 minutes write /run/nologin
    d, env = fake
    p = sh(str(_kit(tmp_path)), "arm", "12", env=env)
    assert p.returncode == 0 and p.stdout.strip().splitlines()[-1] == "safety-net-12"
    assert "timer: " in p.stdout and "da-safety-net-S1.timer" in p.stdout
    (timer,) = [c for c in calls(d) if c.startswith("sudo systemd-run")]
    assert "--on-active=12min" in timer and timer.endswith("/bin/systemctl poweroff")
    assert not any("shutdown" in c for c in calls(d))


def test_safety_net_arm_without_a_listed_timer_is_not_armed(tmp_path: Path, fake) -> None:
    d, env = fake
    (d / "no_timer").touch()
    net = _kit(tmp_path)
    for args in (("arm", "12"), ("arm", "12", "bash stop.sh")):
        p = sh(str(net), *args, env=env)
        assert p.returncode == 1 and "safety-net-12" not in p.stdout.splitlines()


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
    (d / "logcat_since_mark_0.0.0.0:6522").write_text(NEW_SUBSCRIBED)
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


# The restarted app subscribes again (W2 of the re-check at 437a833b): am start -S kills the process that subscribed
# before the unit gate, so app_restart.sh waits for the new process's own link line, in the IVI log since an IVI-clock
# mark taken right before am start. The lines are in the real threadtime format; the fake's pidof answers 4242.
APP_NEW = "11-19 10:00:{s:02d}.000  4242  4260 I DE4SDV_COLLISION_WARNING: event=lifecycle t_mono_ns=1 t_real_ns=2 "
NEW_SUBSCRIBED = APP_NEW.format(s=1) + "phase=link link=SUBSCRIBED detail=instance1\n"
NEW_WAITING = APP_NEW.format(s=0) + 'phase=link link=WAITING detail="discovery started; waiting for the broker\'s unit x"\n'
NEW_UNAVAILABLE = APP_NEW.format(s=0) + ('phase=link link=UNAVAILABLE detail="subscribe instance1:de4sdv-driving-warning-'
                                         'request: SdvGatewayRuntimeException statusCode 5 NOT_FOUND"\n')
NEW_DROPPED = APP_NEW.format(s=3) + 'phase=link link=WAITING detail="publication destroyed"\n'
# the process the gate saw subscribe, killed by am start -S: its SUBSCRIBED line is no sign of the new process
OLD_SUBSCRIBED = ("11-19 09:59:59.000  3205  3235 I DE4SDV_COLLISION_WARNING: event=lifecycle t_mono_ns=1 t_real_ns=2 "
                  "phase=link link=SUBSCRIBED detail=instance1\n")


def _restart(tmp_path: Path, d: Path, env: dict, since: str, late: str | None = None, late_after: int = 2,
             wait: str = "30") -> tuple[subprocess.CompletedProcess, float]:
    (d / "logcat_since_mark_0.0.0.0:6522").write_text(since)
    if late is not None:
        (d / "late_0.0.0.0:6522").write_text(late)
        (d / "late_after_0.0.0.0:6522").write_text(f"{late_after}\n")
    t0 = time.monotonic()
    p = sh(str(REMOTE / "app_restart.sh"), str(tmp_path / "o"), "w1",
           env=dict(env, APP_SUBSCRIBE_WAIT_S=wait, POLL_S="0.2", **APP))
    return p, time.monotonic() - t0


def test_app_restart_waits_for_the_new_processes_subscribed_line_since_its_mark(tmp_path: Path, fake) -> None:
    d, env = fake
    (d / "guest_off_0.0.0.0:6522").write_text("1000\n")   # the IVI's own clock
    p, dt = _restart(tmp_path, d, env, OLD_SUBSCRIBED + NEW_WAITING, late=NEW_SUBSCRIBED)
    assert p.returncode == 0, p.stdout + p.stderr
    assert dt >= 0.3                                     # it waited for the late line
    assert "APP_SUBSCRIBED 4242" in p.stdout and p.stdout.strip().splitlines()[-1] == "APP_RESTARTED w1"
    rec = (tmp_path / "o" / "app_restart_w1.txt").read_text()
    mark = re.search(r"^ivi mark (\S+)$", rec, re.M).group(1)
    assert float(mark) - time.time() > 900                # read on the IVI's clock
    c = calls(d)
    i_mark = c.index("adb -s 0.0.0.0:6522 shell date +%s.%N")
    i_start = next(i for i, x in enumerate(c) if " am start" in x)
    assert i_mark < i_start                               # the mark right before am start
    assert f"adb -s 0.0.0.0:6522 logcat -d -T {mark}" in c[i_start:]
    assert "link=SUBSCRIBED detail=instance1" in rec and "APP_SUBSCRIBED 4242" in rec


def test_app_restart_never_takes_the_old_processes_subscribed_line_after_the_mark(tmp_path: Path, fake) -> None:
    # m30 of the lane's harness: the killed process can log SUBSCRIBED after the IVI mark, before am start -S ends it;
    # only the new pid's line passes, so with none from it the step waits its whole bound and fails
    d, env = fake
    p, dt = _restart(tmp_path, d, env, OLD_SUBSCRIBED, wait="1")
    assert p.returncode == 1 and dt >= 1, p.stdout
    fail = [x for x in p.stdout.splitlines() if x.startswith("FAIL")]
    assert fail and "pid 4242" in fail[0] and "none since the mark" in fail[0], p.stdout
    assert "APP_SUBSCRIBED" not in p.stdout
    # the new pid's SUBSCRIBED after the old one's passes
    p2, _ = _restart(tmp_path / "b", d, env, OLD_SUBSCRIBED + NEW_SUBSCRIBED)
    assert p2.returncode == 0 and "APP_SUBSCRIBED 4242" in p2.stdout, p2.stdout
    assert NEW_SUBSCRIBED.strip() in p2.stdout


def test_app_restart_fails_when_the_new_process_never_subscribes(tmp_path: Path, fake) -> None:
    d, env = fake
    p, dt = _restart(tmp_path, d, env, OLD_SUBSCRIBED + NEW_WAITING, wait="1")
    assert p.returncode == 1, p.stdout
    fail = [x for x in p.stdout.splitlines() if x.startswith("FAIL")]
    assert fail and "4242" in fail[0] and "within 1 s" in fail[0], p.stdout
    assert dt >= 1
    assert "link=WAITING" in p.stdout                     # the new process's link lines since the mark
    assert "APP_RESTARTED" not in p.stdout
    assert "FAIL" in (tmp_path / "o" / "app_restart_w1.txt").read_text()


def test_app_restart_counts_unavailable_lines_and_never_decides_on_them(tmp_path: Path, fake) -> None:
    d, env = fake
    p, _ = _restart(tmp_path, d, env, NEW_UNAVAILABLE, late=NEW_SUBSCRIBED)
    assert p.returncode == 0 and "APP_SUBSCRIBED 4242" in p.stdout, p.stdout
    assert "UNAVAILABLE 1 time(s)" in p.stdout and "statusCode 5 NOT_FOUND" in p.stdout, p.stdout


def test_app_restart_fails_on_unavailable_lines_only_at_its_bound(tmp_path: Path, fake) -> None:
    d, env = fake
    p, dt = _restart(tmp_path, d, env, NEW_UNAVAILABLE, wait="1")
    assert p.returncode == 1 and dt >= 1, p.stdout
    fail = [x for x in p.stdout.splitlines() if x.startswith("FAIL")]
    assert fail and "UNAVAILABLE lines since the mark: 1" in fail[0] and "statusCode 5" in fail[0], p.stdout


def test_app_restart_needs_the_last_link_line_to_be_subscribed(tmp_path: Path, fake) -> None:
    # W5: a SUBSCRIBED followed by WAITING ("publication destroyed") is a dropped link: wait on, fail at the bound
    d, env = fake
    p, dt = _restart(tmp_path, d, env, NEW_SUBSCRIBED + NEW_DROPPED, wait="1")
    assert p.returncode == 1 and dt >= 1, p.stdout
    p2, _ = _restart(tmp_path / "b", d, env, NEW_SUBSCRIBED + NEW_DROPPED,
                     late=APP_NEW.format(s=9) + "phase=link link=SUBSCRIBED detail=instance1\n")
    assert p2.returncode == 0 and "APP_SUBSCRIBED 4242" in p2.stdout, p2.stdout


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
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), env=dict(env, UNIT_SOURCE="core", UNIT_WAIT_S="0"))
    assert p.returncode == 0, p.stdout
    assert f"UNIT_REGISTERED {unit}" in p.stdout
    assert unit in (tmp_path / "o" / "unit_lines.txt").read_text()


def test_the_unit_check_fails_on_a_broker_error_for_the_service_or_no_registration(tmp_path: Path, fake) -> None:
    d, env = fake
    unit, service = _ids()
    (d / "logcat").write_text(f"11-19 08:00:00.000 1 2 E someip_broker_agent: no mapping for service "
                              f"{service[2:]}\n11-19 08:00:01.000 1 2 I SomeIpBroker: registered unit {unit}\n")
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), env=dict(env, UNIT_SOURCE="core", UNIT_WAIT_S="0"))
    assert p.returncode == 1 and "broker errors" in p.stdout
    (d / "logcat").write_text("11-19 08:00:00.000 1 2 I SomeIpBroker: started\n")
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o2"), env=dict(env, UNIT_SOURCE="core", UNIT_WAIT_S="0"))
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


@pytest.mark.parametrize("crosvm, pgrep_error, expected", [("0", False, "0"), ("3", False, "3"), ("0", True, "unknown")])
def test_guest_up_counts_crosvm_before_its_launch(tmp_path: Path, fake, crosvm: str, pgrep_error: bool,
                                                  expected: str) -> None:
    # S1 rests on "no guest runs before the session starts one": every session's guest_up counts first, and its last
    # line repeats the count, so the session's step tail carries it; a pgrep error is "unknown", never 0
    d, env = fake
    (d / "crosvm").write_text(crosvm + "\n")
    if pgrep_error:
        (d / "pgrep_error").touch()
    env = dict(env, DE4SDV_ROOT=str(_launch(tmp_path)), BOOT_WAIT_S="5")
    p = sh(str(REMOTE / "guest_up.sh"), str(tmp_path / "o"), env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    log = calls(d)
    assert log.index("pgrep -c -x crosvm") < log.index("launch down")
    assert p.stdout.strip().splitlines()[-1] == f"CROSVM_BEFORE_LAUNCH {expected}"
    assert (tmp_path / "o" / "crosvm_before_launch.txt").read_text().strip() == expected


def _guest_up_kit(tmp_path: Path) -> tuple[Path, Path]:
    """A kit with the real host_step.sh and the real guest_up.sh, as the session uploads them."""
    kit = tmp_path / "home" / "da-kit" / "S1"
    rem = kit / "bench" / "session" / "remote"
    rem.mkdir(parents=True)
    (kit / "session_id").write_text("S1\n")
    for name in ("host_step.sh", "guest_up.sh"):
        (rem / name).write_bytes((REMOTE / name).read_bytes())
    return kit, rem / "host_step.sh"


def _wait_text(path: Path, text: str, timeout: float = 15) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists() and text in path.read_text():
            return
        time.sleep(0.05)
    raise AssertionError(f"{text!r} not in {path}")


def _end_leftovers(d: Path) -> None:
    """Ends what a failing run left behind in other process groups (pids the fakes wrote), never by name."""
    for f in ("launch_pid", "adb_hang_pids"):
        for w in ((d / f).read_text().split() if (d / f).exists() else []):
            pid = int(w)
            try:
                g = os.getpgid(pid)
                if g != os.getpgid(0):
                    os.killpg(g, 9)
                else:
                    os.kill(pid, 9)
            except ProcessLookupError:
                pass


def _alive(pid: int) -> bool:
    try:
        st = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return False
    return st.rsplit(")", 1)[1].split()[0] != "Z"


def test_a_termed_guest_up_reads_running_until_its_launch_has_cleaned_up(tmp_path: Path, fake) -> None:
    # T1: GNU timeout puts the launch in its own process group, so a TERM to the step's group ended only guest_up.sh;
    # the status read "rc 255" at once and the session stopped the guest host under a launch still creating guests
    d, env = fake
    launch = tmp_path / "launch.sh"
    launch.write_text('trap \'echo "launch got TERM" >> "$FAKE/launch_marks"; sleep 4; '
                      'echo "launch cleanup done" >> "$FAKE/launch_marks"; exit 143\' TERM\n'
                      'echo $$ > "$FAKE/launch_pid"; echo started >> "$FAKE/launch_marks"\nsleep 60 & wait\n')
    env = dict(env, GUEST_LAUNCH_CMD=f"bash {launch}")
    kit, hs = _guest_up_kit(tmp_path)
    st = lambda: sh(str(hs), "status", "guest_up", env=env).stdout.strip()   # noqa: E731
    assert sh(str(hs), "start", "guest_up", "--", "bash", "session/remote/guest_up.sh", str(kit / "out" / "gu"),
              env=env).returncode == 0
    marks = d / "launch_marks"
    try:
        _wait_text(marks, "started")
        assert "signalled guest_up (TERM)" in sh(str(hs), "signal", "guest_up", "TERM", env=env).stdout
        time.sleep(1)
        assert st() == "running"   # the launch still cleans up: the step has not ended
        deadline = time.monotonic() + 20
        while st() == "running" and time.monotonic() < deadline:
            time.sleep(0.1)
        assert "launch cleanup done" in marks.read_text()   # the step ended only after the launch had ended
        end = st()
        assert end.startswith("rc ") and end != "rc 0", end
        assert "FAIL launch ended by TERM" in (kit / "out" / "guest_up.log").read_text()
    finally:
        _end_leftovers(d)


def _hanging_adb(d: Path) -> Path:
    """adb whose `connect` hangs (a wedged vsock proxy); every other call goes to the fake adb."""
    a = d / "bin" / "adb_hang"
    a.write_text('#!/bin/bash\nif [ "$1" = connect ]; then echo $$ >> "$FAKE/adb_hang_pids"; exec sleep 60; fi\n'
                 f'exec {d / "bin" / "adb"} "$@"\n')
    a.chmod(0o755)
    return a


def test_guest_up_bounds_each_adb_call_of_its_boot_wait(tmp_path: Path, fake) -> None:
    # T7: a hung `adb connect` held guest_up until the session's step time-out (2400 s)
    d, env = fake
    env = dict(env, DE4SDV_ROOT=str(_launch(tmp_path)), ADB=str(_hanging_adb(d)), ADB_TO_S="1", BOOT_WAIT_S="5")
    p = subprocess.Popen(["bash", str(REMOTE / "guest_up.sh"), str(tmp_path / "o")], env=env, text=True,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, start_new_session=True)
    try:
        out, _ = p.communicate(timeout=30)
        ended = True
    except subprocess.TimeoutExpired:
        ended, out = False, ""
    finally:
        try:
            os.killpg(p.pid, 9)
        except ProcessLookupError:
            pass
        p.communicate()
        _end_leftovers(d)
    assert ended, "guest_up waited on a hung adb call"
    assert p.returncode == 0 and "GUEST_UP_DONE" in out, out


def test_a_termed_guest_up_leaves_no_bounded_adb_call_behind(tmp_path: Path, fake) -> None:
    # T7 without T1 again: a bound under GNU timeout in its own process group outlives a TERM to the step's group
    d, env = fake
    env = dict(env, GUEST_LAUNCH_CMD="true", ADB=str(_hanging_adb(d)), ADB_TO_S="30")
    kit, hs = _guest_up_kit(tmp_path)
    assert sh(str(hs), "start", "guest_up", "--", "bash", "session/remote/guest_up.sh", str(kit / "out" / "gu"),
              env=env).returncode == 0
    _wait_text(d / "adb_hang_pids", "\n")
    pid = int((d / "adb_hang_pids").read_text().split()[0])
    sh(str(hs), "signal", "guest_up", "TERM", env=env)
    deadline = time.monotonic() + 10
    while sh(str(hs), "status", "guest_up", env=env).stdout.strip() == "running" and time.monotonic() < deadline:
        time.sleep(0.1)
    assert sh(str(hs), "status", "guest_up", env=env).stdout.strip().startswith("rc ")
    deadline = time.monotonic() + 2
    while _alive(pid) and time.monotonic() < deadline:
        time.sleep(0.05)
    alive = _alive(pid)
    _end_leftovers(d)
    assert not alive, "an adb call outlived the step it belongs to"


def _timeout_calls(path: Path) -> list[str]:
    out = []
    for line in path.read_text().splitlines():
        code = line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
        if re.search(r"(^|[\s;({|&])timeout\s", code):
            out.append(code.strip())
    return out


def test_every_bound_in_a_session_step_stays_where_a_term_to_the_step_reaches_it() -> None:
    # T1/T7: GNU timeout without --foreground moves its command into a new process group; a TERM to the step's group
    # then ends the step while the command runs on. Each bound is --foreground (short calls: the TERM reaches them),
    # or guest_up's launch, run in the background and waited for with the TERM forwarded to it
    bench = REMOTE.parent.parent
    files = sorted(REMOTE.glob("*.sh"))
    seen = {}
    for f in files:
        for c in _timeout_calls(f):
            seen[(f.name, c)] = c
    # the guest build script's own adb bound, which the prepare step's install and verify use
    build = bench / "guest-build" / "build_guests_incremental.sh"
    (adb_t,) = [c for c in _timeout_calls(build) if c.startswith("adb_t()")]
    seen[("build_guests_incremental.sh", adb_t)] = adb_t
    assert seen
    bad = [k for k, c in seen.items() if "timeout --foreground " not in c
           and not (k[0] == "guest_up.sh" and c.endswith("& LP=$!"))]
    assert not bad, bad
    launch = [c for (n, c) in seen if n == "guest_up.sh" and c.endswith("& LP=$!")]
    assert len(launch) == 1 and "bash -c \"$LAUNCH\"" in launch[0]


@pytest.mark.parametrize("line", [
    "I SomeIpBroker: unit {unit} unregistered",
    "W SomeIpBroker: unit {unit} not registered: no provider of 0x4df1 yet",
    "W SomeIpBroker: failed to register unit {unit}",
    "W SomeIpBroker: registration of unit {unit} failed",
    "W SomeIpBroker: unit {unit} registration timed out",
    "W SomeIpBroker: could not register unit {unit}",
])
def test_the_unit_check_refuses_a_negated_registration(tmp_path: Path, fake, line: str) -> None:
    # R7: a line naming the unit and "regist" that says the opposite is no registration
    d, env = fake
    unit, _ = _ids()
    (d / "logcat").write_text("11-19 08:00:00.000 1 2 " + line.format(unit=unit) + "\n")
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), env=dict(env, UNIT_SOURCE="core", UNIT_WAIT_S="0"))
    assert p.returncode == 1 and "no registration" in p.stdout, p.stdout


@pytest.mark.parametrize("line", [
    "I SomeIpBroker: registered unit {unit} (subscription timeout 5000 ms)",
    "I SomeIpBroker: registered unit {unit}, errors=0",
    "I SomeIpBroker: unit {unit} registered; no failover configured",
])
def test_the_unit_check_passes_a_registration_line_that_merely_names_a_failure_word(tmp_path: Path, fake,
                                                                                    line: str) -> None:
    # S8: the negation matched "timeout", "error", "fail" anywhere in the line; a false fail costs a paid P10-3
    d, env = fake
    unit, _ = _ids()
    (d / "logcat").write_text("11-19 08:00:00.000 1 2 " + line.format(unit=unit) + "\n")
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), env=dict(env, UNIT_SOURCE="core", UNIT_WAIT_S="0"))
    assert p.returncode == 0 and f"UNIT_REGISTERED {unit}" in p.stdout, p.stdout


def test_the_unit_check_negation_is_a_per_session_setting(tmp_path: Path, fake) -> None:
    d, env = fake
    unit, _ = _ids()
    (d / "logcat").write_text(f"11-19 08:00:00.000 1 2 I SomeIpBroker: registered unit {unit} (degraded)\n")
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"),
           env=dict(env, UNIT_SOURCE="core", UNIT_WAIT_S="0", UNIT_NEGATION_RE="degraded"))
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
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark), env=dict(env, UNIT_SOURCE="core", UNIT_WAIT_S="0"))
    assert p.returncode == 0, p.stdout
    assert f"adb -s 0.0.0.0:6521 logcat -d -T {since}" in calls(d)
    whole = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o2"), env=dict(env, UNIT_SOURCE="core", UNIT_WAIT_S="0"))
    assert whole.returncode == 1 and "broker errors" in whole.stdout     # the same log read since the boot


# The app's gate (UNIT_SOURCE=app, the default): session p10-3 20261119T094924Z showed that the SDV Core broker logs no
# line naming the unit at its default level, so a core-side registration line can never pass; the IVI app's own link
# line is the readiness signal of the core-to-IVI leg. The line formats below are the real ones of that session.
CORE_IVI, CORE_SER = "0.0.0.0:6522", "0.0.0.0:6521"
APP_T = "11-19 09:57:{s:02d}.000  3205  3235 I DE4SDV_COLLISION_WARNING: event=lifecycle t_mono_ns=1 t_real_ns=2 "
LINK_WAITING = APP_T.format(s=10) + 'phase=link link=WAITING detail="discovery started; waiting for the broker\'s unit x"\n'
LINK_SUBSCRIBED = APP_T.format(s=17) + 'phase=link link=SUBSCRIBED detail="instance1"\n'
LINK_UNAVAILABLE = APP_T.format(s=17) + ('phase=link link=UNAVAILABLE detail="subscribe instance1:de4sdv-driving-warning-'
                                         'request: SdvGatewayRuntimeException statusCode 5 NOT_FOUND"\n')
CORE_LINES = (
    "11-19 09:57:08.288   601   682 I SdvServiceManagerServer: main::mesh::async_client: Connecting to "
    "192.168.99.5:2000 using unsecure channel\n"
    "11-19 09:57:16.849   542   569 I sdv_someip_stack_agent: endpoint_manager_impl::create_remote_client: "
    "192.168.98.1:30511 reliable: 1 using local port: 0\n"
    "11-19 09:57:16.853   542   666 I sdv_someip_stack_agent: REGISTER EVENT(1221): [4df1.0001.8001:is_provider=false]\n"
    "11-19 09:57:16.853   542   666 I sdv_someip_stack_agent: SUBSCRIBE(1221): [4df1.0001.0001:8001:1]\n"
    "11-19 09:57:17.000   542   666 I sdv_someip_stack_agent: SUBSCRIBE(1222): [1234.0001.0001:8001:1]\n")
IVI_SDV = ("11-19 09:56:00.000   600   601 I SdvServiceManager: main::mesh::manager: connected to instance1\n"
           "11-19 09:56:00.100   700   701 I SomeIpBroker: started\n")
# a mesh line under neither tag: the diagnostics keep it by its own word, not as a SdvServiceManager line
IVI_MESH_ONLY = "11-19 09:56:00.200   710   711 W sdv_sd_agent: sd_mesh peer instance3 unreachable\n"
# the app's line from before the offer (the real session's last IVI line): only in the IVI buffer since boot, never
# in the log since the mark; a fail at run 2 is diagnosed from these lines
PRE_OFFER_WAITING = ("11-19 09:56:10.887  3205  3235 I DE4SDV_COLLISION_WARNING: event=lifecycle t_mono_ns=34209898502 "
                     "t_real_ns=1795082170887000000 phase=link link=WAITING detail=\"discovery started; waiting for the "
                     "broker's unit de4sdv-driving-warning-request\"\n")
# the app's start line names the broker (publisher=...SomeIpBroker): a line of the app, never of the mesh file (W6)
APP_START_LOGCAT = ("11-19 09:56:10.640  3205  3205 I DE4SDV_COLLISION_WARNING: event=lifecycle t_mono_ns=1 t_real_ns=2 "
                    "phase=start pid=3205 publisher=com.android.sdv.someip.SomeIpBroker unit=de4sdv-driving-warning-"
                    "request\n")
IVI_BOOT = APP_START_LOGCAT + PRE_OFFER_WAITING + IVI_SDV + IVI_MESH_ONLY + LINK_WAITING
DIAG_FILES = ("ivi_collision_warning_since_boot.txt", "ivi_sdv_service_manager_broker_mesh.txt",
              "core_sdv_service_manager_since_mark.txt", "core_someip_service.txt", "net_core.txt", "net_ivi.txt")


def _app_mark(tmp_path: Path, d: Path, env: dict) -> Path:
    (d / f"guest_off_{CORE_SER}").write_text("0\n")
    (d / f"guest_off_{CORE_IVI}").write_text("1000\n")   # the IVI's own clock, 1000 s off the core's
    mark = tmp_path / "mark"
    m = sh(str(REMOTE / "offer_check.sh"), "mark", str(mark), env=env)
    assert m.returncode == 0, m.stdout + m.stderr
    return mark


def _diag_present(out: Path) -> None:
    diag = out / "diag"
    for f in DIAG_FILES:
        assert (diag / f).exists(), f
    app = (diag / "ivi_collision_warning_since_boot.txt").read_text()
    assert PRE_OFFER_WAITING in app and LINK_WAITING in app     # every app line since boot, the pre-offer one too
    sdv = (diag / "ivi_sdv_service_manager_broker_mesh.txt").read_text()
    assert "I SdvServiceManager: main::mesh::manager" in sdv and "I SomeIpBroker: started" in sdv
    assert IVI_MESH_ONLY in sdv                                  # a mesh line under another tag
    assert "DE4SDV_COLLISION_WARNING" not in sdv                  # never the app's own lines (W6)
    assert "SdvServiceManagerServer" in (diag / "core_sdv_service_manager_since_mark.txt").read_text()
    someip = (diag / "core_someip_service.txt").read_text()
    assert "4df1.0001.8001" in someip and "1234.0001" not in someip
    for f, ser in (("net_core.txt", CORE_SER), ("net_ivi.txt", CORE_IVI)):
        net = (diag / f).read_text()
        assert f"fake-net {ser}: ip -br addr" in net and "ip route" in net, net


def test_the_mark_takes_the_ivi_clock_too(tmp_path: Path, fake) -> None:
    d, env = fake
    mark = _app_mark(tmp_path, d, env)
    core = float((mark / "logcat_since.txt").read_text())
    ivi = float((mark / "ivi_logcat_since.txt").read_text())
    assert 990 < ivi - core < 1010    # each guest's own clock


def test_the_mark_fails_without_the_ivi_clock_unless_the_source_is_the_core(tmp_path: Path, fake) -> None:
    d, env = fake
    (d / f"no_clock_{CORE_IVI}").touch()
    p = sh(str(REMOTE / "offer_check.sh"), "mark", str(tmp_path / "m"), env=env)
    assert p.returncode == 1 and "no clock read of the IVI guest" in p.stdout, p.stdout
    p = sh(str(REMOTE / "offer_check.sh"), "mark", str(tmp_path / "m2"), env=dict(env, UNIT_SOURCE="core"))
    assert p.returncode == 0 and (tmp_path / "m2" / "logcat_since.txt").exists(), p.stdout


def test_the_unit_gate_waits_for_the_apps_subscribed_line_since_the_ivi_mark(tmp_path: Path, fake) -> None:
    d, env = fake
    mark = _app_mark(tmp_path, d, env)
    (d / f"logcat_since_mark_{CORE_SER}").write_text(CORE_LINES)
    (d / f"logcat_since_mark_{CORE_IVI}").write_text(LINK_WAITING)
    (d / f"logcat_{CORE_IVI}").write_text(IVI_BOOT)
    (d / f"late_{CORE_IVI}").write_text(LINK_SUBSCRIBED)   # SUBSCRIBED only from the 4th read of the IVI log on
    (d / f"late_after_{CORE_IVI}").write_text("3\n")
    t0 = time.monotonic()
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark),
           env=dict(env, UNIT_WAIT_S="30", POLL_S="0.3"))
    assert p.returncode == 0, p.stdout
    assert time.monotonic() - t0 >= 0.6                     # it waited for the late line
    unit, _ = _ids()
    assert f"UNIT_SUBSCRIBED {unit} source=app" in p.stdout
    assert "source app" in p.stdout and "up to 30 s" in p.stdout     # the bound and the source are logged
    ivi_since = (mark / "ivi_logcat_since.txt").read_text().strip()
    assert f"adb -s {CORE_IVI} logcat -d -T {ivi_since}" in calls(d)
    out = tmp_path / "o"
    assert "link=SUBSCRIBED" in (out / "app_link_lines.txt").read_text()
    ctx = (out / "unit_context.txt").read_text()            # both legs, kept on a pass too
    assert "REGISTER EVENT(1221): [4df1.0001.8001" in ctx and "SUBSCRIBE(1221): [4df1.0001.0001" in ctx
    assert "link=SUBSCRIBED" in ctx and "1234.0001" not in ctx
    assert not (out / "diag").exists()


def test_the_unit_gate_fails_without_a_subscribed_line_and_saves_every_diagnostic(tmp_path: Path, fake) -> None:
    d, env = fake
    mark = _app_mark(tmp_path, d, env)
    (d / f"logcat_since_mark_{CORE_SER}").write_text(CORE_LINES)
    (d / f"logcat_since_mark_{CORE_IVI}").write_text(LINK_WAITING)
    (d / f"logcat_{CORE_IVI}").write_text(IVI_BOOT)
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark),
           env=dict(env, UNIT_WAIT_S="1", POLL_S="0.2"))
    assert p.returncode == 1 and "FAIL" in p.stdout and "link=SUBSCRIBED" in p.stdout, p.stdout
    assert "last link line: WAITING" in p.stdout
    _diag_present(tmp_path / "o")
    assert "DIAGNOSTICS" in p.stdout
    ctx = (tmp_path / "o" / "unit_context.txt").read_text()
    assert "REGISTER EVENT(1221)" in ctx and "link=WAITING" in ctx


def test_an_unavailable_link_the_app_retries_does_not_fail_the_gate(tmp_path: Path, fake) -> None:
    # The app logs UNAVAILABLE for every failed initComms, subscribe or read and retries after RETRY_DELAY_MS (5 s)
    # (WarningRequestSubscriber.java connect/subscribe/drain), so an UNAVAILABLE line never decides: a SUBSCRIBED
    # after it passes, and the gate names the UNAVAILABLE lines it saw since the mark
    d, env = fake
    mark = _app_mark(tmp_path, d, env)
    (d / f"logcat_since_mark_{CORE_SER}").write_text(CORE_LINES)
    (d / f"logcat_since_mark_{CORE_IVI}").write_text(LINK_WAITING + LINK_UNAVAILABLE + LINK_SUBSCRIBED.replace(":17", ":22"))
    (d / f"logcat_{CORE_IVI}").write_text(IVI_BOOT)
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark),
           env=dict(env, UNIT_WAIT_S="60", POLL_S="0.2"))
    assert p.returncode == 0 and "UNIT_SUBSCRIBED" in p.stdout, p.stdout
    assert "UNAVAILABLE 1 time(s)" in p.stdout and "statusCode 5 NOT_FOUND" in p.stdout, p.stdout
    assert not (tmp_path / "o" / "diag").exists()


def test_unavailable_links_alone_fail_only_at_the_bound_with_the_last_detail(tmp_path: Path, fake) -> None:
    d, env = fake
    mark = _app_mark(tmp_path, d, env)
    (d / f"logcat_since_mark_{CORE_SER}").write_text(CORE_LINES)
    (d / f"logcat_since_mark_{CORE_IVI}").write_text(LINK_WAITING + LINK_UNAVAILABLE)
    (d / f"logcat_{CORE_IVI}").write_text(IVI_BOOT)
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark),
           env=dict(env, UNIT_WAIT_S="2", POLL_S="0.2"))
    assert p.returncode == 1 and "within 2 s" in p.stdout, p.stdout
    assert "UNAVAILABLE lines since the mark: 1" in p.stdout and "statusCode 5 NOT_FOUND" in p.stdout, p.stdout
    _diag_present(tmp_path / "o")


def test_the_unit_gate_names_the_last_link_line_before_the_mark_at_its_bound(tmp_path: Path, fake) -> None:
    # W3: a naming problem is logged once, at the app's start, before the mark (WarningRequestSubscriber.java)
    d, env = fake
    mark = _app_mark(tmp_path, d, env)
    naming = ("11-19 09:56:10.900  3205  3235 I DE4SDV_COLLISION_WARNING: event=lifecycle t_mono_ns=1 t_real_ns=2 "
              'phase=link link=UNAVAILABLE detail="naming: bundle x does not match [A-Z][A-Za-z0-9]*"\n')
    (d / f"logcat_since_mark_{CORE_SER}").write_text(CORE_LINES)
    (d / f"logcat_since_mark_{CORE_IVI}").write_text("")
    (d / f"logcat_{CORE_IVI}").write_text(IVI_BOOT.replace(LINK_WAITING, "") + naming)
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark),
           env=dict(env, UNIT_WAIT_S="0", POLL_S="0.2"))
    assert p.returncode == 1, p.stdout
    fail = [x for x in p.stdout.splitlines() if x.startswith("FAIL")]
    assert fail and "none since the mark" in fail[0], p.stdout
    assert "last link line before the mark:" in fail[0] and "naming: bundle x" in fail[0], fail


def test_the_unit_gate_decides_on_the_last_link_line_since_the_mark(tmp_path: Path, fake) -> None:
    # W5: SUBSCRIBED, then WAITING "publication destroyed": the link dropped, so the gate waits on
    d, env = fake
    mark = _app_mark(tmp_path, d, env)
    dropped = APP_T.format(s=20) + 'phase=link link=WAITING detail="publication destroyed"\n'
    (d / f"logcat_since_mark_{CORE_SER}").write_text(CORE_LINES)
    (d / f"logcat_since_mark_{CORE_IVI}").write_text(LINK_SUBSCRIBED + dropped)
    (d / f"logcat_{CORE_IVI}").write_text(IVI_BOOT)
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark),
           env=dict(env, UNIT_WAIT_S="1", POLL_S="0.2"))
    assert p.returncode == 1 and "last link line: WAITING" in p.stdout, p.stdout
    (d / f"late_{CORE_IVI}").write_text(APP_T.format(s=25) + 'phase=link link=SUBSCRIBED detail="instance1"\n')
    (d / f"late_after_{CORE_IVI}").write_text("0\n")
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o2"), str(mark),
           env=dict(env, UNIT_WAIT_S="30", POLL_S="0.2"))
    assert p.returncode == 0 and "UNIT_SUBSCRIBED" in p.stdout, p.stdout


def test_the_unit_gate_keeps_the_core_broker_error_check(tmp_path: Path, fake) -> None:
    d, env = fake
    mark = _app_mark(tmp_path, d, env)
    (d / f"logcat_since_mark_{CORE_SER}").write_text(CORE_LINES + "11-19 09:57:18.000 1 2 E someip_broker_agent: no "
                                                     "mapping for service 4df1\n")
    (d / f"logcat_since_mark_{CORE_IVI}").write_text(LINK_SUBSCRIBED)
    (d / f"logcat_{CORE_IVI}").write_text(IVI_BOOT)
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark), env=dict(env, UNIT_WAIT_S="0"))
    assert p.returncode == 1 and "broker errors" in p.stdout, p.stdout
    _diag_present(tmp_path / "o")


def test_the_core_source_ignores_the_apps_line_and_saves_diagnostics_on_its_fail(tmp_path: Path, fake) -> None:
    d, env = fake
    mark = _app_mark(tmp_path, d, env)
    (d / f"logcat_since_mark_{CORE_SER}").write_text(CORE_LINES)
    (d / f"logcat_since_mark_{CORE_IVI}").write_text(LINK_SUBSCRIBED)
    (d / f"logcat_{CORE_IVI}").write_text(IVI_BOOT)
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark),
           env=dict(env, UNIT_SOURCE="core", UNIT_WAIT_S="0"))
    assert p.returncode == 1 and "no registration" in p.stdout and "source core" in p.stdout, p.stdout
    _diag_present(tmp_path / "o")
    bad = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o2"), str(mark),
             env=dict(env, UNIT_SOURCE="broker", UNIT_WAIT_S="0"))
    assert bad.returncode == 2 and "UNIT_SOURCE" in bad.stdout + bad.stderr


def test_the_core_source_decides_from_the_core_log_and_never_reads_the_ivi(tmp_path: Path, fake) -> None:
    # UNIT_SOURCE=core keeps the earlier gate whole: a registration line in the core's log passes it, the IVI app's
    # lines are never read (not even an UNAVAILABLE one), and no app_link_lines.txt is made
    d, env = fake
    unit, _ = _ids()
    mark = _app_mark(tmp_path, d, env)
    (d / f"logcat_since_mark_{CORE_SER}").write_text(CORE_LINES + f"11-19 09:57:18.000 1 2 I SomeIpBroker: registered "
                                                     f"unit {unit}\n")
    (d / f"logcat_since_mark_{CORE_IVI}").write_text(LINK_UNAVAILABLE)
    (d / f"logcat_{CORE_IVI}").write_text(IVI_BOOT + LINK_UNAVAILABLE)
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark),
           env=dict(env, UNIT_SOURCE="core", UNIT_WAIT_S="5", POLL_S="0.2"))
    assert p.returncode == 0 and f"UNIT_REGISTERED {unit} source=core" in p.stdout, p.stdout
    assert "UNAVAILABLE" not in p.stdout
    assert [c for c in calls(d) if c.startswith(f"adb -s {CORE_SER} logcat")], calls(d)
    assert not [c for c in calls(d) if c.startswith(f"adb -s {CORE_IVI} logcat")], calls(d)
    assert not (tmp_path / "o" / "app_link_lines.txt").exists()
    assert unit in (tmp_path / "o" / "unit_lines.txt").read_text()


def test_a_missing_ivi_mark_fails_the_app_gate(tmp_path: Path, fake) -> None:
    d, env = fake
    mark = tmp_path / "mark"
    mark.mkdir()
    (mark / "logcat_since.txt").write_text("1795082222.858\n")    # an old mark: the core's clock only
    p = sh(str(REMOTE / "offer_check.sh"), "unit", str(tmp_path / "o"), str(mark), env=dict(env, UNIT_WAIT_S="0"))
    assert p.returncode == 1 and "no IVI logcat mark" in p.stdout, p.stdout


def test_the_diagnostics_of_a_failed_unit_gate_come_back_with_the_sessions_fetch(tmp_path: Path, fake) -> None:
    # the session fetches the host's out/ folder as host_step.sh pack tars it: the gate's files must sit under it
    d, env = fake
    kit = tmp_path / "home" / "da-kit" / "S1"
    rem = kit / "bench" / "session" / "remote"
    rem.mkdir(parents=True)
    (kit / "bench" / "interfaces").mkdir()
    (kit / "bench" / "interfaces" / "service_ids.json").write_bytes(
        (HERE.parent.parent / "interfaces" / "service_ids.json").read_bytes())
    (kit / "session_id").write_text("S1\n")
    for name in ("host_step.sh", "offer_check.sh"):
        (rem / name).write_bytes((REMOTE / name).read_bytes())
    (d / f"logcat_since_mark_{CORE_SER}").write_text(CORE_LINES)
    (d / f"logcat_since_mark_{CORE_IVI}").write_text(LINK_WAITING)
    (d / f"logcat_{CORE_IVI}").write_text(IVI_BOOT)
    hs, oc, out = str(rem / "host_step.sh"), "session/remote/offer_check.sh", kit / "out"
    assert sh(hs, "run", "logmark_inject", "--", "bash", oc, "mark", str(out / "logmark_inject"), env=env).returncode == 0
    r = sh(hs, "run", "unit_inject", "--", "bash", oc, "unit", str(out / "unit_inject"), str(out / "logmark_inject"),
           env=dict(env, UNIT_WAIT_S="0"))
    assert r.returncode == 1
    p = sh(hs, "pack", env=env)
    assert p.returncode == 0, p.stderr
    with tarfile.open(kit / "out.tgz") as t:
        names = set(t.getnames())
    for f in DIAG_FILES:
        assert f"out/unit_inject/diag/{f}" in names, f
    assert "out/unit_inject/unit_context.txt" in names and "out/logmark_inject/ivi_logcat_since.txt" in names


# The app's record files/warning.jsonl is appended (RecordWriter.java) and every app start writes lifecycle, link and
# status lines, so a line count is never 0 (W1 of the re-check at 437a833b). A receipt is a line whose event is
# "receipt" (MainActivity.onRequest -> recordAt(.., "receipt", ..)); the lines below are in the app's own format
# (WarningRecord.json: "event", "t_mono_ns", "t_real_ns" first, then the pairs in order, no spaces).


def _jl(event: str, **kv) -> str:
    return json.dumps({"event": event, "t_mono_ns": 1, "t_real_ns": 2, **kv}, separators=(",", ":")) + "\n"


def _start(pid: int) -> str:
    return _jl("lifecycle", phase="start", pid=pid, subject="org.de4sdv.collisionwarning.CollisionWarningPresentation",
               message="de4sdv.driving.v1.WarningRequest", publisher="com.android.sdv.someip.SomeIpBroker",
               unit="de4sdv-driving-warning-request", translation="REFLECTION at the SDV Core SOME/IP broker",
               poll_ms=50)


def _receipt(seq: int) -> str:
    return _jl("receipt", seq=seq, requested=seq % 2 == 1, issue_time_sim_ms=1000 * seq, verdict="ACCEPTED",
               request=seq, reason="")


def _status(n: int) -> str:   # a status line names the receipts too: "receipts":n is no receipt event
    return _jl("status", link="SUBSCRIBED", receipts=n, requests=n, refused=0)


def _app_start_lines(pid: int, link: str = "SUBSCRIBED") -> str:
    return (_start(pid) + _jl("sound_prepared", stream="alarm") + _jl("lifecycle", phase="config", key="k", value="v")
            + _jl("lifecycle", phase="link", link=link, detail="instance1") + _status(0))


# guest_prepare's verify start (3205), then the window's restart (4242, the fake's pidof): no request ever arrived
LIFECYCLE_ONLY = (_app_start_lines(3205, "WAITING") + _status(0)
                  + _jl("lifecycle", phase="stop", receipts=0, requests=0, refused=0) + _app_start_lines(4242))
EARLIER_ONLY = (_app_start_lines(3205) + _receipt(1) + _receipt(2) + _receipt(3) + _status(3)
                + _jl("lifecycle", phase="stop", receipts=3, requests=3, refused=0) + _app_start_lines(4242))
AFTER_THE_START = (EARLIER_ONLY + _receipt(1) + _jl("display_shown", request=1, since_receipt_ns=5) + _receipt(2)
                   + _jl("display_cleared", request=2) + _status(2))


def _count(tmp_path: Path, env: dict, record: str | None, pid: str | None, name: str) -> subprocess.CompletedProcess:
    cap = tmp_path / name
    cap.mkdir()
    if record is not None:
        (cap / "app_record_warning.jsonl").write_text(record)
    args = [str(REMOTE / "offer_check.sh"), "receipts", str(cap)]
    if pid is not None:
        (tmp_path / f"{name}_restart.txt").write_text(f"window inject x\npid {pid} 2026-11-19T10:00:00.000Z\n")
        args.append(str(tmp_path / f"{name}_restart.txt"))
    return sh(*args, env=env)


def _last(p: subprocess.CompletedProcess) -> str:
    assert p.returncode == 0, p.stdout + p.stderr
    return p.stdout.strip().splitlines()[-1]


def test_the_receipts_of_a_window_are_counted(tmp_path: Path, fake) -> None:
    d, env = fake
    assert _last(_count(tmp_path, env, None, None, "empty")) == "RECEIPTS 0"
    assert _last(_count(tmp_path, env, AFTER_THE_START, None, "plain")) == "RECEIPTS 2"
    assert _last(_count(tmp_path, env, AFTER_THE_START, "4242", "pid")) == "RECEIPTS 2"


@pytest.mark.parametrize("pid", [None, "4242"])
def test_a_record_of_lifecycle_lines_only_counts_no_receipt(tmp_path: Path, fake, pid) -> None:
    d, env = fake
    assert len(LIFECYCLE_ONLY.splitlines()) > 9
    assert _last(_count(tmp_path, env, LIFECYCLE_ONLY, pid, "c")) == "RECEIPTS 0"


@pytest.mark.parametrize("pid", [None, "4242"])
def test_receipts_from_an_earlier_app_start_are_not_counted(tmp_path: Path, fake, pid) -> None:
    d, env = fake
    assert _last(_count(tmp_path, env, EARLIER_ONLY, pid, "c")) == "RECEIPTS 0"


def test_the_receipts_need_the_windows_own_app_start(tmp_path: Path, fake) -> None:
    # with the window's restart record, the receipts are those after the start line of the pid app_restart.sh read:
    # a record whose last start is another process's (a stale file, a pull from another user) counts none
    d, env = fake
    p = _count(tmp_path, env, AFTER_THE_START, "5555", "other")
    assert _last(p) == "RECEIPTS 0" and "5555" in p.stdout, p.stdout
    cap = tmp_path / "norec"
    cap.mkdir()
    (cap / "app_record_warning.jsonl").write_text(AFTER_THE_START)
    p = sh(str(REMOTE / "offer_check.sh"), "receipts", str(cap), str(tmp_path / "missing.txt"), env=env)
    assert _last(p) == "RECEIPTS 0", p.stdout


def test_the_neighbour_caches_of_both_guests_are_flushed(tmp_path: Path, fake) -> None:
    # R18: the S-CORE host takes 192.168.98.1 over the VXLAN with another MAC
    d, env = fake
    p = sh(str(REMOTE / "offer_check.sh"), "neigh", str(tmp_path / "o"), env=env)
    assert p.returncode == 0, p.stdout + p.stderr
    flush = [c for c in calls(d) if "ip neigh flush" in c]
    assert flush == ["adb -s 0.0.0.0:6521 shell ip neigh flush dev eth1",
                     "adb -s 0.0.0.0:6522 shell ip neigh flush dev eth1"]


# ------------------------------------------------------------------- the session's SELinux mark (R16)


@pytest.mark.parametrize("ivi, permissive, rc", [
    ("Enforcing", "0", 0), ("Permissive", "0", 1), ("Enforcing", "1", 1), ("Permissive", "1", 0)])
def test_app_restart_fails_when_the_ivi_mode_is_not_the_sessions_mark(tmp_path: Path, fake, ivi: str,
                                                                      permissive: str, rc: int) -> None:
    # owner decision (b) of 2026-11-18: Enforcing unless the session is marked --permissive-ivi, then Permissive
    d, env = fake
    (d / "mode_0.0.0.0:6522").write_text(ivi + "\n")
    (d / "logcat_since_mark_0.0.0.0:6522").write_text(NEW_SUBSCRIBED)   # the restarted app subscribes (W2)
    p = sh(str(REMOTE / "app_restart.sh"), str(tmp_path / "o"), "w1", env=dict(env, IVI_PERMISSIVE=permissive, **APP))
    assert p.returncode == rc, p.stdout + p.stderr
    starts = [c for c in calls(d) if " am start" in c]
    assert len(starts) == (1 if rc == 0 else 0)                # never a window on a guest off the mark
    if rc:
        assert "FAIL SELinux on the ivi guest" in p.stdout


def test_app_restart_fails_on_a_permissive_sdv_core_guest(tmp_path: Path, fake) -> None:
    d, env = fake
    (d / "mode_0.0.0.0:6521").write_text("Permissive\n")
    p = sh(str(REMOTE / "app_restart.sh"), str(tmp_path / "o"), "w1", env=dict(env, IVI_PERMISSIVE="1", **APP))
    assert p.returncode == 1 and "FAIL SELinux on the core guest" in p.stdout


# ------------------------------------------------------------------------------------ ivi_clock.sh (R17)


def _clock_lines(out: Path) -> list[dict]:
    return [json.loads(line) for line in (out / "clock.jsonl").read_text().splitlines()]


def test_ivi_clock_set_brings_the_offset_within_its_limit_and_writes_json_in_any_locale(tmp_path: Path, fake) -> None:
    d, env = fake
    (d / "guest_off").write_text("5\n")
    (d / "clock_settable").touch()
    out = tmp_path / "clk"
    p = sh(str(REMOTE / "ivi_clock.sh"), "set", str(out), env=dict(env, CLOCK_READS="3", LC_ALL="de_DE.UTF-8"))
    assert p.returncode == 0, p.stdout + p.stderr
    lines = _clock_lines(out)                                # json.loads fails on "5,016991"
    assert lines[0]["label"] == "before_set" and abs(lines[0]["offset_s"] - 5) < 1
    assert abs(lines[-1]["offset_s"]) <= 0.1 and lines[-1]["bound_s"] >= 0


def test_ivi_clock_set_fails_when_the_set_has_no_effect(tmp_path: Path, fake) -> None:
    d, env = fake
    (d / "guest_off").write_text("5\n")                     # the guest ignores date -s
    out = tmp_path / "clk"
    p = sh(str(REMOTE / "ivi_clock.sh"), "set", str(out), env=dict(env, CLOCK_READS="3"))
    assert p.returncode == 1, p.stdout + p.stderr
    assert "FAIL the IVI clock is" in p.stderr
    assert abs(_clock_lines(out)[-1]["offset_s"] - 5) < 1


def test_ivi_clock_measure_only_records(tmp_path: Path, fake) -> None:
    d, env = fake
    (d / "guest_off").write_text("2\n")
    out = tmp_path / "clk"
    p = sh(str(REMOTE / "ivi_clock.sh"), "measure", str(out), "end", env=dict(env, CLOCK_READS="2"))
    assert p.returncode == 0
    (line,) = _clock_lines(out)
    assert line["label"] == "end" and line["reads"] == 2 and not any("date -s" in c for c in calls(d))


# ------------------------------------------------------------------------------------------ host_step.sh


def test_host_step_detached_step_reports_its_status_tail_and_answers_a_signal(tmp_path: Path, fake) -> None:
    # R10: the session starts every step detached, polls its status and reads its tail; at a time-out it signals it
    d, env = fake
    kit = tmp_path / "home" / "da-kit" / "S1"
    (kit / "bench" / "session" / "remote").mkdir(parents=True)
    (kit / "session_id").write_text("S1\n")
    hs = kit / "bench" / "session" / "remote" / "host_step.sh"
    hs.write_bytes((REMOTE / "host_step.sh").read_bytes())
    assert sh(str(hs), "start", "quick", "--", "bash", "-c", "echo hello", env=env).returncode == 0
    deadline = time.monotonic() + 10
    while sh(str(hs), "status", "quick", env=env).stdout.strip() != "rc 0" and time.monotonic() < deadline:
        time.sleep(0.1)
    tail = sh(str(hs), "tail", "quick", env=env).stdout
    assert "hello" in tail and tail.strip().endswith("=== quick end rc=0")
    assert sh(str(hs), "start", "slow", "--", "sleep", "30", env=env).returncode == 0
    assert sh(str(hs), "status", "slow", env=env).stdout.strip() == "running"
    assert "signalled slow (TERM)" in sh(str(hs), "signal", "slow", "TERM", env=env).stdout
    deadline = time.monotonic() + 10
    while not sh(str(hs), "status", "slow", env=env).stdout.startswith("rc ") and time.monotonic() < deadline:
        time.sleep(0.1)
    assert sh(str(hs), "status", "slow", env=env).stdout.strip() in ("rc 143", "rc 255")


def test_host_step_status_reads_running_while_any_process_of_the_step_lives(tmp_path: Path, fake) -> None:
    # S2: after a TERM the step's leader is gone at once, while its command still cleans up; "rc 255" then let the
    # trap stop the guests and their host under a launch that still ran
    d, env = fake
    kit = tmp_path / "home" / "da-kit" / "S1"
    (kit / "bench" / "session" / "remote").mkdir(parents=True)
    (kit / "session_id").write_text("S1\n")
    hs = kit / "bench" / "session" / "remote" / "host_step.sh"
    hs.write_bytes((REMOTE / "host_step.sh").read_bytes())
    child = tmp_path / "child.sh"
    child.write_text("trap 'sleep 3; echo child cleanup done; exit 0' TERM\nsleep 30 & wait\n")
    assert sh(str(hs), "start", "gstep", "--", "bash", str(child), env=env).returncode == 0
    time.sleep(0.5)
    assert sh(str(hs), "status", "gstep", env=env).stdout.strip() == "running"
    assert "signalled gstep (TERM)" in sh(str(hs), "signal", "gstep", "TERM", env=env).stdout
    time.sleep(0.5)
    assert sh(str(hs), "status", "gstep", env=env).stdout.strip() == "running"   # the cleanup still runs
    deadline = time.monotonic() + 15
    while sh(str(hs), "status", "gstep", env=env).stdout.strip() == "running" and time.monotonic() < deadline:
        time.sleep(0.2)
    assert sh(str(hs), "status", "gstep", env=env).stdout.strip().startswith("rc ")
    assert "child cleanup done" in (kit / "out" / "gstep.log").read_text()


# ------------------------------------------------- F3 of the first recorded p10-2: the pack leaves the .rrd on the host


def test_the_pack_leaves_every_rerun_record_on_the_host_and_lists_it(tmp_path: Path) -> None:
    """calib_steer's visionpilot.rrd (4.7 GB) made the S-CORE host's out.tgz 3.74 GB and its copy ran past 18 min.
    The pack excludes *.rrd, lists each with its size in out/pack_excluded.tsv (in the pack), and deletes nothing."""
    kit = tmp_path / "home" / "da-kit" / "S1"
    rem = kit / "bench" / "session" / "remote"
    rem.mkdir(parents=True)
    (rem / "host_step.sh").write_bytes((REMOTE / "host_step.sh").read_bytes())
    (kit / "session_id").write_text("S1\n")
    vp = kit / "out" / "score_run1" / "score_side" / "vision_pilot"
    vp.mkdir(parents=True)
    (vp / "visionpilot.rrd").write_bytes(b"r" * 4096)
    (vp / "frames.csv").write_text("frame\n")
    (kit / "out" / "score_run1" / "candidate_rrd.json").write_text("[]\n")
    p = subprocess.run(["bash", str(rem / "host_step.sh"), "pack"], capture_output=True, text=True,
                       env={**os.environ, "HOME": str(tmp_path / "home")})
    assert p.returncode == 0, p.stderr
    with tarfile.open(kit / "out.tgz") as t:
        names = set(t.getnames())
        listed = t.extractfile("out/pack_excluded.tsv").read().decode()
    assert not [n for n in names if n.endswith(".rrd")], names
    assert "out/score_run1/score_side/vision_pilot/frames.csv" in names and "out/score_run1/candidate_rrd.json" in names
    assert listed.splitlines() == ["out/score_run1/score_side/vision_pilot/visionpilot.rrd\t4096"], listed
    assert (vp / "visionpilot.rrd").stat().st_size == 4096   # still on the host's disk
