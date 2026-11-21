"""Stand-in runs of the B12 script's safety paths (review R1, R2, R4, R7, R8, R9, R14, R18 of fc74de16).

The synthetic tree of test_guest_build_script.py, plus stand-ins for the guest host: a fake adb
(../../ivi-warning-app/tests/fakes/adb, one guest directory per adb port), a fake cvd whose `fleet`
names the two groups and whose `stop` is recorded, and a fake launch_two_vms.sh. They show:

* preflight reads B12's own image records, never the kit's stale state/images-*.sha256, and stops on
  a mismatch or a missing record; the committed records are tonight's images;
* the refusals: an IVI image change during the module build, a core build under running guests,
  a tree whose broker.vsidl lacks the message;
* `all` stops the guests on any failure once boot began, and on HUP, INT and TERM;
* under Enforcing a failed Gateway lookup stops the run and prints the rerun command with
  IVI_PERMISSIVE=1, without setting permissive; IVI_PERMISSIVE=1 sets it and reads it back;
* B12's files go to $AB/b12-<date>/, never into the kit's identity/ or logs/.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import time
from pathlib import Path

import pytest

from test_guest_build_script import DA, ROOT, SCRIPT, Tree

FAKE_ADB = DA / "ivi-warning-app" / "tests" / "fakes" / "adb"
RECORDS = ROOT / "image-records"
FAKE_CVD = r"""#!/usr/bin/env bash
echo "cvd $*" >> "$FAKE_CALLS"
case "$*" in
  fleet)
    [ -f "$FAKE_HOST/no-groups" ] && { echo '{"groups": []}'; exit 0; }
    echo '{"groups": [{"group_name": "cvd_1", "instances": [{"instance_name": "2", "status": "Running"}]},'
    echo '            {"group_name": "cvd_2", "instances": [{"instance_name": "3", "status": "Running"}]}]}' ;;
esac
exit 0
"""
FAKE_LAUNCH = r"""#!/usr/bin/env bash
echo "launch $*" >> "$FAKE_CALLS"
[ "${FAKE_UP_FAIL:-0}" = 1 ] && [ "$1" = up ] && exit 1
exit 0
"""


class Host(Tree):
    """The synthetic tree on a stand-in guest host, with B11 already in the core image."""

    def __init__(self, tmp: Path, **kwargs):
        super().__init__(tmp, **kwargs)
        bin_dir = self.aosp / "out" / "host" / "linux-x86" / "bin"
        bin_dir.mkdir(parents=True)
        (bin_dir / "adb").symlink_to(FAKE_ADB)
        (bin_dir / "cvd").write_text(FAKE_CVD)
        (bin_dir / "cvd").chmod(0o755)
        launch = tmp / "none" / "implementation" / "score-broker-path-bench" / "scripts" / "launch_two_vms.sh"
        launch.parent.mkdir(parents=True)
        launch.write_text(FAKE_LAUNCH)
        self.host = tmp / "host"
        self.host.mkdir()
        self.core_guest = tmp / "guest-core"
        self.ivi_guest = tmp / "guest-ivi"
        self.logcat = tmp / "logcat.txt"
        self.logcat.write_text("I DE4SDV_COLLISION_WARNING: event=lifecycle phase=config key=initComms value=x\n")
        self.stage_b11_into_tree()
        self.build_image()
        self.write_records()

    def env(self) -> dict:
        env = super().env()
        env.update(FAKE_HOST=str(self.host), FAKE_GUEST_6521=str(self.core_guest), FAKE_GUEST_6522=str(self.ivi_guest),
                   FAKE_LOGCAT=str(self.logcat), BUILD_MIN_FREE_GB="0", GUESTS="fresh", ADB_TIMEOUT_S="60",
                   VERIFY_WAIT_S="1", ROOT_SETTLE_S="0", STOP_SETTLE_S="0", START_SETTLE_S="0", FAKE_CALLS=str(self.calls), B12_DIR=str(self.ab / "b12-test"))
        return env

    def run(self, step: str, **extra: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(SCRIPT), step], capture_output=True, text=True,
                              env={**self.env(), **extra}, timeout=300)

    def cvd_stops(self) -> list[str]:
        return [line for line in self.calls_lines() if line.startswith("cvd --group_name=") and line.endswith(" stop")]


# ------------------------------------------------------------------ R1: B12's own image records

def test_the_committed_records_are_the_images_of_2026_11_18():
    def record(name: str) -> dict[str, str]:
        pairs = [line.split() for line in (RECORDS / name).read_text().splitlines()]
        assert all(len(pair) == 2 and len(pair[0]) == 64 for pair in pairs), name
        return {image: digest for digest, image in pairs}

    ivi = record("sdv_ivi_cf.sha256")
    core = record("sdv_core_cf.sha256")
    assert ivi["super.img"] == "91a4d73f7ce3e350dc31215ddcbe6ec5d4065a201a1a793bcd4c837934fd157f"
    assert sorted(ivi) == sorted(["super.img", "vbmeta.img", "boot.img", "init_boot.img", "vendor_boot.img"])
    assert len(core) == 27
    assert core["super.img"].startswith("434b485f") and core["vbmeta.img"].startswith("535d7aba")
    text = SCRIPT.read_text()
    assert 'IVI_IMAGE_RECORD:=$HERE/image-records/sdv_ivi_cf.sha256' in text
    assert "images-$IVI_PRODUCT" not in text and "$STATE" not in text, "the kit's stale record is never read"


def test_preflight_passes_beside_the_kits_stale_record(tmp_path):
    host = Host(tmp_path)
    stale = host.ab / "state" / "images-sdv_ivi_cf.sha256"
    stale.parent.mkdir(parents=True)
    stale.write_text("5abe6a7cf4b4b5d6a7be2f8c220d95792e1dc9412be8f11f1b465d3bc10ea735  "
                     f"{host.ivi_out}/super.img\n")
    ran = host.run("preflight")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "sdv_ivi_cf images equal the B12 record (5 images" in ran.stdout
    assert "sdv_core_cf images equal the B12 record" in ran.stdout


@pytest.mark.parametrize("product", ["sdv_ivi_cf", "sdv_core_cf"])
def test_preflight_stops_on_an_image_that_differs_from_the_record(tmp_path, product):
    host = Host(tmp_path)
    (host.aosp / "out" / "target" / "product" / product / "super.img").write_text("rewritten in place\n")
    ran = host.run("preflight")
    assert ran.returncode != 0
    assert "differ from the B12 record" in ran.stdout and "super.img: FAILED" in ran.stdout + ran.stderr
    assert host.cvd_stops() == []


def test_preflight_stops_without_a_record(tmp_path):
    host = Host(tmp_path)
    host.ivi_record.unlink()
    ran = host.run("preflight")
    assert ran.returncode != 0 and "no B12 image record" in ran.stdout


# ------------------------------------------------------------------ refusals

def test_ivi_stops_when_the_module_build_changes_an_ivi_image(tmp_path):
    host = Host(tmp_path)
    envsetup = host.aosp / "build" / "envsetup.sh"
    envsetup.write_text(envsetup.read_text().replace(
        'echo apk > "$FAKE_APK" ;;', f'echo apk > "$FAKE_APK"; echo installclean > "{host.ivi_out}/boot.img" ;;'))
    ran = host.run("ivi")
    assert ran.returncode != 0
    assert "the IVI images changed during the module build" in ran.stdout


def test_core_refuses_to_build_under_running_guests(tmp_path):
    host = Host(tmp_path)
    host.installed.write_text('{"services": []}\n')  # the image lacks B11: core would build
    crosvm = tmp_path / "crosvm"
    sleep = shutil.which("sleep")
    assert sleep
    shutil.copy(sleep, crosvm)
    guest = subprocess.Popen([str(crosvm), "60"])
    try:
        time.sleep(0.3)
        ran = host.run("core")
    finally:
        guest.kill()
        guest.wait()
    assert ran.returncode != 0 and "guests are running" in ran.stdout
    assert host.calls_lines() == [] or not any(line.startswith(("lunch", "m")) for line in host.calls_lines())


def test_the_tree_detection_needs_the_message_in_broker_vsidl(tmp_path):
    host = Host(tmp_path)
    host.broker_vsidl.write_text('publisher {\n  message: "x.y.Z"\n}\n')
    ran = host.run("detect")
    assert "core: tree does not carry B11" in ran.stdout
    assert "broker.vsidl lacks" in ran.stdout


# ------------------------------------------------------------------ R7, R8

def test_the_no_build_core_records_the_image_identity(tmp_path):
    host = Host(tmp_path)
    ran = host.run("core")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "nothing to build" in ran.stdout
    assert "the images equal the B12 record" in ran.stdout
    identity = host.ab / "b12-test" / "identity" / "b12-core-images.sha256"
    assert len(identity.read_text().splitlines()) == 5


def test_b12_writes_nothing_into_the_kits_identity_or_logs(tmp_path):
    host = Host(tmp_path)
    env = host.env()
    del env["B12_DIR"]
    ran = subprocess.run(["bash", str(SCRIPT), "preflight"], capture_output=True, text=True, env=env, timeout=120)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert not (host.ab / "identity").exists() and not (host.ab / "logs").exists()
    dated = [p.name for p in host.ab.iterdir() if p.name.startswith("b12-")]
    assert len(dated) == 1 and (host.ab / dated[0] / "identity" / "b12-summary.txt").is_file()


def test_boot_refuses_a_systemd_unit(tmp_path):
    host = Host(tmp_path)
    cgroup = tmp_path / "cgroup"
    cgroup.write_text("0::/user.slice/user-1000.slice/user@1000.service/app.slice/b12.service\n")
    ran = host.run("boot", B12_CGROUP_FILE=str(cgroup))
    assert ran.returncode != 0 and "systemd unit" in ran.stdout
    assert not any(line.startswith("launch") for line in host.calls_lines())


# ------------------------------------------------------------------ all: success and the failure path

def test_all_passes_and_ends_with_the_guests_stopped(tmp_path):
    host = Host(tmp_path)
    ran = host.run("all")
    assert ran.returncode == 0, ran.stdout[-4000:] + ran.stderr
    assert "B12 PASSED" in ran.stdout
    assert "launch down" in host.calls_lines() and "launch up" in host.calls_lines()
    assert host.cvd_stops() == ["cvd --group_name=cvd_1 stop", "cvd --group_name=cvd_2 stop"]
    summary = (host.ab / "b12-test" / "identity" / "b12-summary.txt").read_text()
    assert "SELinux core Enforcing, IVI Enforcing" in summary
    assert "apk sha256" in summary and "object_policy_sha256_after" in summary
    assert not any("setenforce" in line for line in host.calls_lines())


def test_a_failure_after_boot_stops_the_guests(tmp_path):
    host = Host(tmp_path)
    ran = host.run("all", FAKE_FAIL_PUSH="*.apk")
    assert ran.returncode != 0
    assert "B12 FAILED" in ran.stdout
    assert host.cvd_stops() == ["cvd --group_name=cvd_1 stop", "cvd --group_name=cvd_2 stop"]


def test_a_failure_before_boot_leaves_the_guests_alone(tmp_path):
    host = Host(tmp_path)
    (host.ivi_out / "super.img").write_text("changed\n")
    ran = host.run("all")
    assert ran.returncode != 0 and "B12 FAILED" in ran.stdout
    assert host.cvd_stops() == []


def test_keep_guests_on_failure_keeps_them_and_says_so(tmp_path):
    host = Host(tmp_path)
    ran = host.run("all", FAKE_FAIL_PUSH="*.apk", KEEP_GUESTS_ON_FAILURE="1")
    assert ran.returncode != 0
    assert host.cvd_stops() == []
    assert "stop them (./build_guests_incremental.sh stop) before the host" in ran.stdout


@pytest.mark.parametrize("sig, rc", [(signal.SIGHUP, 129), (signal.SIGINT, 130), (signal.SIGTERM, 143)])
def test_a_signal_after_boot_stops_the_guests(tmp_path, sig, rc):
    host = Host(tmp_path)
    out = tmp_path / "all.out"
    with out.open("w") as sink:
        run = subprocess.Popen(["bash", str(SCRIPT), "all"], stdout=sink, stderr=subprocess.STDOUT,
                               env={**host.env(), "FAKE_HANG": "remount"}, start_new_session=True)
        try:
            deadline = time.time() + 200
            while not any(line.endswith(" remount") for line in host.calls_lines()):
                assert time.time() < deadline, out.read_text()[-3000:]
                assert run.poll() is None, out.read_text()[-3000:]
                time.sleep(0.2)
            time.sleep(0.5)
            run.send_signal(sig)  # the script's own pid only, as a dropped SSH or a kill would
            assert run.wait(timeout=120) == rc, out.read_text()[-3000:]
        finally:
            if run.poll() is None:
                os.killpg(run.pid, signal.SIGKILL)
                run.wait()
    text = out.read_text()
    assert "B12 FAILED" in text
    assert host.cvd_stops() == ["cvd --group_name=cvd_1 stop", "cvd --group_name=cvd_2 stop"], text[-3000:]


# ------------------------------------------------------------------ R4, R18: verify

def test_a_gateway_lookup_failure_under_enforcing_stops_with_the_permissive_rerun_command(tmp_path):
    host = Host(tmp_path)
    host.logcat.write_text("E DE4SDV_COLLISION_WARNING: initComms/discovery: not declared\n")
    ran = host.run("all", B12_RERUN_CMD="IVI_PERMISSIVE=1 B12_RERUN=2 bash b12_launch.sh start da-b12-x.tar.gz")
    assert ran.returncode != 0
    assert "failed under SELinux Enforcing" in ran.stdout
    assert "the rerun command: IVI_PERMISSIVE=1 B12_RERUN=2 bash b12_launch.sh start da-b12-x.tar.gz" in ran.stdout
    assert not any("setenforce" in line for line in host.calls_lines()), "never permissive on its own"
    assert host.cvd_stops() == ["cvd --group_name=cvd_1 stop", "cvd --group_name=cvd_2 stop"]


def test_the_default_rerun_command_names_ivi_permissive(tmp_path):
    host = Host(tmp_path)
    host.logcat.write_text("")
    ran = host.run("all")
    assert ran.returncode != 0
    line = next(l for l in ran.stdout.splitlines() if "the rerun command:" in l)
    assert "IVI_PERMISSIVE=1 GUESTS=fresh" in line and "build_guests_incremental.sh all" in line


def test_ivi_permissive_sets_it_and_marks_the_run_conditional(tmp_path):
    host = Host(tmp_path)
    ran = host.run("all", IVI_PERMISSIVE="1")
    assert ran.returncode == 0, ran.stdout[-4000:]
    assert any(line.endswith("shell setenforce 0") for line in host.calls_lines())
    summary = (host.ab / "b12-test" / "identity" / "b12-summary.txt").read_text()
    assert "conditional on a permissive IVI" in summary
    assert "SELinux core Enforcing, IVI Permissive" in summary


def test_verify_needs_the_unit_in_the_broker_apex(tmp_path):
    host = Host(tmp_path)
    ran = host.run("all", FAKE_NO_UNIT_IN_APEX="1")
    assert ran.returncode != 0
    assert "broker APEX (someip-config.binpb) does not name de4sdv-driving-warning-request" in ran.stdout
