"""Stand-in tests of `stage_ivi_warning_app.sh install` and `stage` against a fake adb (tests/fakes/adb).

They pin what the install must do on a guest (review R5, R6, R10, R17 of fc74de16):

* every push is checked: a failed or a silently corrupt push fails the install, and the APK on
  the guest after the reboot must have the host APK's sha256;
* the broker object policy is merged per lead decision B10/B12-3: the existence of the guest's
  file is probed explicitly, a failed read stops the install, the guest's original is kept under its
  own digest and never overwritten, a second install leaves the merged file as it is, and the
  sha256 before and after and the appended blocks are logged and written into the identity;
* every adb call is bounded, so a wedged adb fails the step;
* the stage gate needs the Gateway client's SdvGatewayClient.java, not only its directory.

No device, no AOSP, no network.
"""

from __future__ import annotations

import hashlib
import os
import subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DA = ROOT.parent
SCRIPT = ROOT / "scripts" / "stage_ivi_warning_app.sh"
FAKE_ADB = HERE / "fakes" / "adb"
OURS = DA / "ivi-warning" / "interop" / "acl" / "ivi_broker_object_policy.textproto"
POLICY = "/product/etc/sdv_authz_acls/com.android.sdv.someip/SomeIpBroker.textproto"
APK_GUEST = "/vendor/priv-app/De4sdvCollisionWarningPresentation/De4sdvCollisionWarningPresentation.apk"
EARLIER = (
    'subscriber {\n  message: "de4sdv.driving.v1.DrivingOperationalState"\n'
    '  topic: "de4sdv-driving-operational-state-plan"\n}\n'
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class Guest:
    def __init__(self, tmp: Path, policy: str | None = None, old_apk: bool = True):
        self.tmp = tmp
        self.root = tmp / "guest"
        self.run_dir = tmp / "run"
        self.calls = tmp / "adb-calls"
        self.aosp = tmp / "aosp"
        self.apk = (self.aosp / "out" / "target" / "product" / "sdv_ivi_cf" / "vendor" / "priv-app"
                    / "De4sdvCollisionWarningPresentation" / "De4sdvCollisionWarningPresentation.apk")
        self.apk.parent.mkdir(parents=True)
        self.apk.write_bytes(b"the new apk\n")
        if policy is not None:
            self.put(POLICY, policy)
        if old_apk:
            self.put(APK_GUEST, "an older apk\n")

    def put(self, path: str, text: str) -> None:
        target = self.root / path.lstrip("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def read(self, path: str) -> bytes:
        return (self.root / path.lstrip("/")).read_bytes()

    def install(self, **faults: str) -> subprocess.CompletedProcess:
        env = {**os.environ, "AOSP_TOP": str(self.aosp), "ADB": str(FAKE_ADB), "FAKE_GUEST": str(self.root),
               "FAKE_CALLS": str(self.calls), "RUN_DIR": str(self.run_dir), "ADB_TIMEOUT_S": "20",
               "ROOT_SETTLE_S": "0", **faults}
        return subprocess.run(["bash", str(SCRIPT), "install"], capture_output=True, text=True, env=env, timeout=180)

    def identity(self) -> str:
        return (self.run_dir / "ivi-warning-app-identity.txt").read_text()


def test_a_fresh_guest_gets_our_policy_and_the_apk_with_its_sha256_checked(tmp_path):
    guest = Guest(tmp_path)
    ran = guest.install()
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert guest.read(APK_GUEST) == guest.apk.read_bytes()
    assert guest.read(POLICY) == OURS.read_bytes()
    identity = guest.identity()
    host = sha(guest.apk.read_bytes())
    assert f"apk_host_sha256: {host}" in identity and f"apk_guest_sha256: {host}" in identity
    assert "object_policy_sha256_before: absent" in identity
    assert f"object_policy_sha256_after: {sha(OURS.read_bytes())}" in identity
    assert 'object_policy_appended:   include: "org.de4sdv.collisionwarning.CollisionWarningPresentation"' in identity


def test_the_policy_is_merged_logged_and_its_original_kept(tmp_path):
    guest = Guest(tmp_path, policy=EARLIER)
    ran = guest.install()
    assert ran.returncode == 0, ran.stdout + ran.stderr
    merged = guest.read(POLICY).decode()
    assert "de4sdv-driving-operational-state-plan" in merged, "the earlier increment's blocks must stay"
    assert 'name: "CollisionWarningPresentationReader"' in merged
    assert merged.startswith(EARLIER)
    before = sha(EARLIER.encode())
    backup = guest.run_dir / f"object-policy.guest.{before}.textproto"
    assert backup.read_text() == EARLIER
    for text in (ran.stdout, guest.identity()):
        assert f"object_policy_sha256_before: {before}" in text
        assert f"object_policy_sha256_after: {sha(merged.encode())}" in text
        assert 'object_policy_appended:   acl_names: "CollisionWarningPresentationReader"' in text


def test_a_second_install_leaves_the_merged_policy_and_the_backup_as_they_are(tmp_path):
    guest = Guest(tmp_path, policy=EARLIER)
    assert guest.install().returncode == 0
    merged = guest.read(POLICY)
    backups = sorted(guest.run_dir.glob("object-policy.guest.*.textproto"))
    again = guest.install()
    assert again.returncode == 0, again.stdout + again.stderr
    assert guest.read(POLICY) == merged
    assert "already merged; left as it is" in again.stdout
    assert f"object_policy_sha256_after: {sha(merged)}" in guest.identity()
    # the first run's backup of the guest's original is still the original
    assert (guest.run_dir / f"object-policy.guest.{sha(EARLIER.encode())}.textproto").read_text() == EARLIER
    assert len(sorted(guest.run_dir.glob("object-policy.guest.*.textproto"))) == len(backups) + 1


def test_a_failed_apk_push_fails_the_install(tmp_path):
    guest = Guest(tmp_path)
    ran = guest.install(FAKE_FAIL_PUSH="*.apk")
    assert ran.returncode != 0
    assert "adb push" in ran.stdout and "failed" in ran.stdout
    assert not (guest.run_dir / "ivi-warning-app-identity.txt").exists()


def test_a_silently_corrupt_apk_push_fails_the_install(tmp_path):
    guest = Guest(tmp_path)
    ran = guest.install(FAKE_CORRUPT_PUSH="*.apk")
    assert ran.returncode != 0
    assert "has sha256" in ran.stdout


def test_a_failed_acl_push_fails_the_install(tmp_path):
    guest = Guest(tmp_path)
    ran = guest.install(FAKE_FAIL_PUSH="*/CollisionWarningPresentation.textproto")
    assert ran.returncode != 0
    assert guest.read(APK_GUEST) == b"an older apk\n", "nothing after the failed push may run"


def test_a_failed_read_of_the_guest_policy_stops_before_any_replace(tmp_path):
    guest = Guest(tmp_path, policy=EARLIER)
    ran = guest.install(FAKE_FAIL_CAT="1")
    assert ran.returncode != 0
    assert "cannot read" in ran.stdout
    assert guest.read(POLICY).decode() == EARLIER


def test_an_unclear_existence_answer_stops_the_install(tmp_path):
    guest = Guest(tmp_path, policy=EARLIER)
    ran = guest.install(FAKE_TEST_ANSWER="error: closed")
    assert ran.returncode != 0
    assert "cannot tell whether" in ran.stdout
    assert guest.read(POLICY).decode() == EARLIER


def test_a_partly_merged_policy_is_refused(tmp_path):
    guest = Guest(tmp_path, policy=EARLIER + 'acls {\n  name: "CollisionWarningPresentationReader"\n}\n')
    ran = guest.install()
    assert ran.returncode != 0
    assert "only part of our blocks" in ran.stdout


def test_a_wedged_adb_fails_the_install_within_the_bound(tmp_path):
    guest = Guest(tmp_path)
    ran = guest.install(FAKE_HANG="wait-for-device", ADB_TIMEOUT_S="2")
    assert ran.returncode != 0
    assert "wait-for-device" in ran.stdout


def test_every_adb_call_of_the_script_is_bounded():
    code = "\n".join(line for line in SCRIPT.read_text().splitlines() if not line.lstrip().startswith("#"))
    assert 'ivi_adb() { timeout "$ADB_TIMEOUT_S" "$ADB" -s "$IVI_ADB" "$@"; }' in code
    assert 'adb_bounded() { timeout "$ADB_TIMEOUT_S" "$ADB" "$@"; }' in code
    unbounded = [line for line in code.splitlines() if '"$ADB"' in line and "timeout" not in line]
    assert unbounded == [], unbounded
    # no push outside push_checked
    pushes = [line.strip() for line in code.splitlines() if "ivi_adb push" in line]
    assert pushes == ['out="$(ivi_adb push "$1" "$2" 2>&1)" || rc=$?'], pushes


def test_stage_needs_the_gateway_client_source_file(tmp_path):
    aosp = tmp_path / "aosp"
    (aosp / "system" / "software_defined_vehicle" / "samples").mkdir(parents=True)
    gateway = aosp / "system" / "software_defined_vehicle" / "sdv_gateway" / "libsdvgatewayclient_java" / "src"
    (gateway / "google" / "sdv" / "gateway" / "client").mkdir(parents=True)
    env = {**os.environ, "AOSP_TOP": str(aosp)}
    ran = subprocess.run(["bash", str(SCRIPT), "stage"], capture_output=True, text=True, env=env, timeout=60)
    assert ran.returncode != 0 and "no Gateway Java client sources" in ran.stdout
    (gateway / "google" / "sdv" / "gateway" / "client" / "SdvGatewayClient.java").write_text("// stand-in\n")
    ran = subprocess.run(["bash", str(SCRIPT), "stage"], capture_output=True, text=True, env=env, timeout=60)
    assert ran.returncode == 0, ran.stdout + ran.stderr
