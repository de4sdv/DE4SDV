"""Static and stand-in tests of the B12 script, build_guests_incremental.sh.

Static: both scripts parse (bash -n); nothing deletes the kept tree, its out directory or the
archive; no installclean or clean; every lunch uses a recorded variant; the guest groups are removed
only under GUESTS=fresh; the SELinux mode changes only under IVI_PERMISSIVE=1.

Stand-in: the steps `detect`, `core` and `ivi` run against a synthetic AOSP tree under tmp_path
whose `lunch` and `m` only record their arguments. They show the idempotent detection of B11 on
the SDV Core side (nothing is built when tree and image carry it, an incremental m when only the
tree does), and the variant refusals before any lunch. No AOSP, no guest, no network.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DA = ROOT.parent
SCRIPT = ROOT / "build_guests_incremental.sh"
APP_SCRIPT = DA / "ivi-warning-app" / "scripts" / "stage_ivi_warning_app.sh"
CORE_STAGE = DA / "ivi-warning" / "scripts" / "stage_sdv_core_interop.sh"
TEXT = SCRIPT.read_text(encoding="utf-8")
APP_TEXT = APP_SCRIPT.read_text(encoding="utf-8")


def _code(text: str) -> str:
    """The script without its comment lines and trailing comments."""
    lines = []
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        lines.append(re.sub(r"\s+#\s.*$", "", line))
    return "\n".join(lines)


@pytest.mark.parametrize("path", [SCRIPT, APP_SCRIPT])
def test_the_scripts_parse(path):
    assert subprocess.run(["bash", "-n", str(path)], capture_output=True).returncode == 0


def test_the_script_deletes_nothing_of_the_kept_tree_or_the_archive():
    code = _code(TEXT)
    assert "rm -rf" not in code and "rm -r " not in code
    # its only rm is its own marker file
    assert re.findall(r"\brm\b[^\n]*", code) == ['rm -f -- "$BOOTED_MARK"']
    commands = re.sub(r'"[^"\n]*"', '""', code)  # messages may name the trap; commands may not
    for word in ("installclean", "m clean", "clobber", "gcloud", "archive_guest_artifacts", "git push"):
        assert word not in commands, word
    app = _code(APP_TEXT)
    # the app script replaces only its own staging directory, behind a path check
    assert len(re.findall(r"rm -r", app)) == 2
    assert re.findall(r'rm -rf -- "\$STAGED"', app) == ['rm -rf -- "$STAGED"'] * 2
    assert 'STAGED="$SAMPLES/de4sdv_collision_warning"' in APP_TEXT
    assert "*/samples/de4sdv_collision_warning)" in app
    assert "installclean" not in re.sub(r'"[^"\n]*"', '""', app)


def test_every_build_uses_the_recorded_variant():
    code = _code(TEXT)
    assert ': "${RECORDED_CORE_VARIANT:=eng}"' in TEXT
    assert ': "${RECORDED_IVI_VARIANT:=userdebug}"' in TEXT
    assert ': "${RECORDED_IVI_VARIANT:=userdebug}"' in APP_TEXT
    assert re.findall(r'lunch "[^"]*"', code) == ['lunch "${product}-${RELEASE}-${variant}"']
    calls = re.findall(r"^\s*lunch_m ([^\n]*)", code, flags=re.M)
    assert calls and all('"$RECORDED_CORE_VARIANT"' in c or '"$RECORDED_IVI_VARIANT"' in c for c in calls), calls
    # lunch_m itself guards before it lunches
    body = re.search(r"^lunch_m\(\) \{.*?^\}", code, flags=re.M | re.S).group(0)
    assert body.index("guard_variant") < body.index("lunch \"")
    assert re.findall(r'lunch "[^"]*"', _code(APP_TEXT)) == ['lunch "${IVI_PRODUCT}-${RELEASE}-${RECORDED_IVI_VARIANT}"']
    # the core image build is a plain m, never the INC-DRIVING-001 script's build (it drops 0x4df1)
    assert "stage_sdv_core_interop.sh\" build" not in code and "closed-loop-driving-bench" not in code


def test_guest_groups_are_removed_only_when_asked_and_stopped_at_the_end():
    code = _code(TEXT)
    down = [m.start() for m in re.finditer(r'"\$LAUNCH" down', code)]
    assert len(down) == 1
    assert code.rfind("fresh)", 0, down[0]) > code.rfind("case \"$GUESTS\" in", 0, down[0]) > 0
    assert re.search(r'"\$c" --group_name="\$g" stop', code)
    assert "run_step stop_guests || exit 1" in code and "trap on_exit EXIT" in code
    assert "in_user_unit && die" in code


def test_the_selinux_mode_changes_only_when_asked():
    code = _code(TEXT)
    commands = re.sub(r'"[^"\n]*"', '""', code)  # messages may name it; one command may run it
    assert commands.count("setenforce") == 1
    index = code.index("shell setenforce 0")
    assert 'if [ "$IVI_PERMISSIVE" = 1 ]; then' in code[max(0, index - 200):index]
    assert "setenforce" not in re.sub(r'"[^"\n]*"', '""', _code(APP_TEXT))
    # R9: a permissive run must read back Permissive, or the step dies
    assert '[ "$(adb_t -s "$IVI_ADB" shell getenforce | tr -d \'\\r\')" = Permissive ] || die' in code


# ------------------------------------------------------------------ stand-in tree

ENVSETUP = r"""
lunch() { echo "lunch $*" >> "$CALLS"; }
m() {
  echo "m $*" >> "$CALLS"
  case " $* " in
    *" De4sdvCollisionWarningPresentation "*)
      mkdir -p "$(dirname "$FAKE_APK")"; echo apk > "$FAKE_APK" ;;
    *)
      mkdir -p "$(dirname "$FAKE_INSTALLED")"
      cp "$FAKE_STACK" "$FAKE_INSTALLED"
      touch -d "@$(( $(date +%s) + 5 ))" "$FAKE_CORE_OUT/super.img" "$FAKE_CORE_OUT/vbmeta.img" ;;
  esac
}
"""
IMAGES = ["super.img", "vbmeta.img", "boot.img", "init_boot.img", "vendor_boot.img"]


class Tree:
    def __init__(self, tmp: Path, core_variant: str = "eng", ivi_variant: str = "userdebug"):
        self.tmp = tmp
        self.aosp = tmp / "aosp"
        self.calls = tmp / "calls"
        self.ab = tmp / "ab"
        sdv = self.aosp / "system" / "software_defined_vehicle"
        self.samples = sdv / "samples"
        self.stack = sdv / "some_ip" / "vsomeip_stack" / "vsomeip_config.json"
        self.catalog = self.samples / "some_ip" / "catalog"
        self.broker_vsidl = self.catalog / "agent" / "broker.vsidl"
        self.broker_acl = self.samples / "some_ip" / "config" / "broker_apex" / "someip_acl.textproto"
        self.core_out = self.aosp / "out" / "target" / "product" / "sdv_core_cf"
        self.ivi_out = self.aosp / "out" / "target" / "product" / "sdv_ivi_cf"
        self.installed = self.core_out / "vendor" / "etc" / "someip" / "vsomeip_config.json"
        (self.aosp / "build").mkdir(parents=True)
        (self.aosp / "build" / "envsetup.sh").write_text(ENVSETUP)
        for path in (self.stack.parent, self.broker_vsidl.parent, self.broker_acl.parent,
                     sdv / "sdv_gateway" / "libsdvgatewayclient_java" / "src" / "google" / "sdv" / "gateway" / "client"):
            path.mkdir(parents=True, exist_ok=True)
        (sdv / "sdv_gateway" / "libsdvgatewayclient_java" / "src" / "google" / "sdv" / "gateway" / "client"
         / "SdvGatewayClient.java").write_text("// stand-in\n")
        self.stack.write_text('{"services": []}\n')
        (self.stack.parent / "Android.bp").write_text('prebuilt_etc { name: "vsomeip_config.json" }\n')
        (self.catalog / "Android.bp").write_text('srcs: ["**/*.proto", "**/*.vsidl"]\n')
        self.broker_vsidl.write_text('publisher {\n  message: "x.y.Z"\n}\n')
        self.broker_acl.write_text("# acl\n")
        for out, variant in ((self.core_out, core_variant), (self.ivi_out, ivi_variant)):
            out.mkdir(parents=True)
            (out / "previous_build_config.mk").write_text(f"PREVIOUS_BUILD_CONFIG := {out.name}-{variant}\n")
            for image in IMAGES:
                (out / image).write_text(image)
        self.calls.write_text("")
        # B12's image records for the stand-in images (the committed ones name the real images).
        self.records = tmp / "records"
        self.records.mkdir()
        self.ivi_record = self.records / "sdv_ivi_cf.sha256"
        self.core_record = self.records / "sdv_core_cf.sha256"
        self.write_records()

    def write_records(self) -> None:
        for out, record in ((self.ivi_out, self.ivi_record), (self.core_out, self.core_record)):
            record.write_text(subprocess.run(["sha256sum", *IMAGES], cwd=out, capture_output=True, text=True,
                                             check=True).stdout)

    def env(self) -> dict:
        env = {k: v for k, v in os.environ.items() if not k.startswith(("RECORDED_", "VARIANT", "IVI_VARIANT"))}
        env.update(
            AOSP_TOP=str(self.aosp), AB=str(self.ab), HOME=str(self.tmp), CALLS=str(self.calls),
            FAKE_STACK=str(self.stack), FAKE_INSTALLED=str(self.installed), FAKE_CORE_OUT=str(self.core_out),
            FAKE_APK=str(self.ivi_out / "vendor" / "priv-app" / "De4sdvCollisionWarningPresentation"
                         / "De4sdvCollisionWarningPresentation.apk"),
            DE4SDV_ROOT=str(self.tmp / "none"),
            IVI_IMAGE_RECORD=str(self.ivi_record), CORE_IMAGE_RECORD=str(self.core_record),
            B12_CGROUP_FILE=str(self.tmp / "no-cgroup"),
        )
        return env

    def render(self) -> Path:
        out = self.tmp / "rendered.json"
        subprocess.run(["bash", str(CORE_STAGE), "render", str(out)], check=True, capture_output=True,
                       env={**self.env(), "SCORE_SOMEIP_PEER": "192.168.98.1", "RUN_DIR": str(self.tmp / "r")})
        return out

    def stage_b11_into_tree(self) -> None:
        shutil.copy(self.render(), self.stack)
        target = self.catalog / "de4sdv_driver_assistance"
        target.mkdir(parents=True, exist_ok=True)
        shutil.copy(DA / "ivi-warning" / "contract" / "de4sdv_driving_collision_warning_request.proto", target)
        shutil.copy(DA / "ivi-warning" / "interop" / "de4sdv_driving_collision_warning_request.vsidl",
                    target / "de4sdv_driving_collision_warning_request_someip.vsidl")
        with self.broker_acl.open("a") as f:
            f.write('publisher {\n  message: "de4sdv.driving.v1.CollisionWarningRequest"\n'
                    '  topic: "de4sdv-driving-warning-request"\n}\n')
        with self.broker_vsidl.open("a") as f:
            f.write('publisher {\n  message: "de4sdv.driving.v1.CollisionWarningRequest"\n}\n')

    def build_image(self) -> None:
        self.installed.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(self.stack, self.installed)
        later = time.time() + 5
        for image in ("super.img", "vbmeta.img"):
            os.utime(self.core_out / image, (later, later))

    def run(self, step: str) -> subprocess.CompletedProcess:
        return subprocess.run(["bash", str(SCRIPT), step], capture_output=True, text=True, env=self.env(), timeout=120)

    def calls_lines(self) -> list[str]:
        return [line.strip() for line in self.calls.read_text().splitlines() if line.strip()]


def test_detect_names_a_tree_without_b11(tmp_path):
    tree = Tree(tmp_path)
    ran = tree.run("detect")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "core: tree does not carry B11" in ran.stdout
    assert tree.calls_lines() == []


def test_core_builds_nothing_when_tree_and_image_carry_b11(tmp_path):
    tree = Tree(tmp_path)
    tree.stage_b11_into_tree()
    tree.build_image()
    assert "core: tree and image carry B11" in tree.run("detect").stdout
    ran = tree.run("core")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert "nothing to build" in ran.stdout
    assert tree.calls_lines() == []


def test_core_runs_one_incremental_m_when_only_the_tree_carries_b11(tmp_path):
    tree = Tree(tmp_path)
    tree.stage_b11_into_tree()
    # an image built before the staging: the installed config is the old one
    tree.installed.parent.mkdir(parents=True, exist_ok=True)
    tree.installed.write_text('{"services": []}\n')
    assert "tree carries B11, image does not" in tree.run("detect").stdout
    ran = tree.run("core")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert tree.calls_lines() == ["lunch sdv_core_cf-cp2a-eng", "m"]
    assert "core: rebuilt" in ran.stdout
    # run again: now idempotent
    tree.calls.write_text("")
    again = tree.run("core")
    assert again.returncode == 0 and "nothing to build" in again.stdout
    assert tree.calls_lines() == []


def test_a_stale_image_detection_needs_newer_images(tmp_path):
    tree = Tree(tmp_path)
    tree.stage_b11_into_tree()
    tree.build_image()
    earlier = time.time() - 3600
    os.utime(tree.core_out / "vbmeta.img", (earlier, earlier))
    ran = tree.run("detect")
    assert "tree carries B11, image does not" in ran.stdout
    assert "vbmeta.img is not newer" in ran.stdout


def test_an_image_with_another_installed_stack_config_does_not_count(tmp_path):
    tree = Tree(tmp_path)
    tree.stage_b11_into_tree()
    tree.build_image()
    # images newer than the installed file, but the file is not the render (an image built from
    # another staging, e.g. the INC-DRIVING-001 stack config without 0x4df1)
    mtime = (tree.installed.stat().st_mtime, tree.installed.stat().st_mtime)
    tree.installed.write_text('{"services": [{"service": "0x4dee"}]}\n')
    os.utime(tree.installed, mtime)
    ran = tree.run("detect")
    assert "tree carries B11, image does not" in ran.stdout
    assert "installed stack config differs from the render" in ran.stdout


def test_core_refuses_another_variant_before_any_lunch(tmp_path):
    tree = Tree(tmp_path, core_variant="userdebug")
    tree.stage_b11_into_tree()
    ran = tree.run("core")
    assert ran.returncode != 0
    assert "installclean" in ran.stdout and "'userdebug'" in ran.stdout
    assert tree.calls_lines() == []


def test_ivi_refuses_another_variant_before_any_lunch(tmp_path):
    tree = Tree(tmp_path, ivi_variant="eng")
    ran = tree.run("ivi")
    assert ran.returncode != 0
    assert "recorded variant is 'userdebug'" in ran.stdout
    assert tree.calls_lines() == []


def test_ivi_builds_the_app_module_only_and_leaves_the_images(tmp_path):
    tree = Tree(tmp_path)
    before = {i: (tree.ivi_out / i).stat().st_mtime_ns for i in IMAGES}
    ran = tree.run("ivi")
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert tree.calls_lines() == [
        "lunch sdv_ivi_cf-cp2a-userdebug",
        "m De4sdvCollisionWarningPresentation De4sdvCollisionWarningPresentationTests",
    ]
    assert {i: (tree.ivi_out / i).stat().st_mtime_ns for i in IMAGES} == before
    staged = tree.samples / "de4sdv_collision_warning"
    assert (staged / "contract" / "de4sdv_driving_collision_warning_request.proto").is_file()
    assert (staged / "app" / "src" / "google" / "sdv" / "gateway" / "client" / "SdvGatewayClient.java").is_file()
    assert not list(staged.rglob("stubs"))
    assert "images unchanged by the module build" in ran.stdout


def test_the_tree_jvm_run_names_every_test_class_of_the_app():
    tests = sorted(p.stem for p in (DA / "ivi-warning-app" / "app" / "tests" / "org" / "de4sdv" / "collisionwarning").glob("*Test.java"))
    named = sorted(set(re.findall(r"org\.de4sdv\.collisionwarning\.(\w+Test)\b", TEXT)))
    assert named == tests
