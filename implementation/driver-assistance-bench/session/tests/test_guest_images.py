"""The identities of the two guest images the guest host boots (guest_up.sh), for the evidence record of each run
(RetainedAssistanceRunEvidence executionEnvironmentIdentity: "the builds of the SDV Core image and of the IVI image").

guest_up.sh creates both guests fresh from the images of the products launch_two_vms.sh names (bench_env.sh:
CORE_PRODUCT sdv_core_cf, IVI_PRODUCT sdv_ivi_cf) and, once each has booted, prints one GUEST_IMAGE line per guest,
read from the booted guest itself: its product, its build id, its build fingerprint and the vbmeta digest of the
images it verified at boot. The session reads them from the step's tail. A property the guest does not answer is
`unread`, never empty. The fake adb below answers getprop from files; every other call goes to the shared fake adb of
test_remote_scripts.py.
"""

from __future__ import annotations

from pathlib import Path

from test_remote_scripts import REMOTE, _launch, calls, fake, sh  # noqa: F401 (fake is a fixture)

CORE, IVI = "0.0.0.0:6521", "0.0.0.0:6522"
PROPS = {
    CORE: {"ro.product.name": "sdv_core_cf", "ro.build.id": "BP4A.251205.006",
           "ro.build.fingerprint": "generic/sdv_core_cf/vsoc_x86_64:17/BP4A.251205.006/eng.mrk.20261117.101500:eng/"
                                   "test-keys",
           "ro.boot.vbmeta.digest": "1f" * 32},
    IVI: {"ro.product.name": "sdv_ivi_cf", "ro.build.id": "BP4A.251205.006",
          "ro.build.fingerprint": "generic/sdv_ivi_cf/vsoc_x86_64:17/BP4A.251205.006/eng.mrk.20261118.181200:eng/"
                                  "test-keys",
          "ro.boot.vbmeta.digest": "2e" * 32},
}
KEYS = ("serial", "product", "build_id", "fingerprint", "vbmeta_digest")
PROP_OF = {"product": "ro.product.name", "build_id": "ro.build.id", "fingerprint": "ro.build.fingerprint",
           "vbmeta_digest": "ro.boot.vbmeta.digest"}


def _adb_with_props(d: Path, props: dict) -> Path:
    for serial, values in props.items():
        for name, value in values.items():
            (d / f"prop_{name}_{serial}").write_text(value + "\n")
    a = d / "bin" / "adb_props"
    a.write_text('#!/bin/bash\nif [ "$1" = -s ] && [ "$3" = shell ] && [ "$4" = getprop ] && [[ "$5" == ro.* ]]; then\n'
                 '  echo "adb $*" >> "$FAKE/calls.log"\n'
                 '  f="$FAKE/prop_$5_$2"; [ -e "$f" ] && printf "%s\\r\\n" "$(cat "$f")"; exit 0\nfi\n'
                 f'exec {d / "bin" / "adb"} "$@"\n')
    a.chmod(0o755)
    return a


def parse(line: str) -> tuple[str, list[str], dict[str, str]]:
    """GUEST_IMAGE <role> key=value ...: the role, the keys in their order, the values."""
    words = line.split()
    assert words[0] == "GUEST_IMAGE", line
    pairs = [w.split("=", 1) for w in words[2:]]
    return words[1], [k for k, _ in pairs], dict(pairs)


def _guest_up(tmp_path: Path, fake, props: dict):
    d, env = fake
    env = dict(env, DE4SDV_ROOT=str(_launch(tmp_path)), BOOT_WAIT_S="5", ADB=str(_adb_with_props(d, props)))
    p = sh(str(REMOTE / "guest_up.sh"), str(tmp_path / "o"), env=env)
    images = [ln for ln in p.stdout.splitlines() if ln.startswith("GUEST_IMAGE ")]
    return p, images, d


def test_guest_up_prints_each_booted_guests_image_identity_in_its_tail(tmp_path: Path, fake) -> None:
    p, images, d = _guest_up(tmp_path, fake, PROPS)
    got = [parse(ln) for ln in images]
    assert [(role, keys) for role, keys, _ in got] == [("sdv_core", list(KEYS)), ("ivi", list(KEYS))], p.stdout
    for (_, _, values), serial in zip(got, (CORE, IVI)):
        assert values == {"serial": serial, **{k: PROPS[serial][PROP_OF[k]] for k in KEYS[1:]}}
    assert p.returncode == 0, p.stdout + p.stderr
    # the session reads them from the step's tail (host_step.sh tail: the log's last 20 lines); the crosvm count
    # stays the last line
    tail = p.stdout.strip().splitlines()[-20:]
    assert all(ln in tail for ln in images) and tail[-1].startswith("CROSVM_BEFORE_LAUNCH ")
    ident = (tmp_path / "o" / "guest_identity.txt").read_text()
    assert all(ln in ident.splitlines() for ln in images)


def test_guest_up_reads_the_image_identity_only_after_the_guest_booted(tmp_path: Path, fake) -> None:
    p, images, d = _guest_up(tmp_path, fake, PROPS)
    log = calls(d)
    for serial in (CORE, IVI):
        boot = max(i for i, c in enumerate(log) if c == f"adb -s {serial} shell getprop sys.boot_completed")
        reads = [i for i, c in enumerate(log) if c == f"adb -s {serial} shell getprop ro.boot.vbmeta.digest"]
        assert reads and reads[0] > boot, (serial, log)


def test_a_property_the_guest_does_not_answer_is_unread_never_empty(tmp_path: Path, fake) -> None:
    props = {CORE: dict(PROPS[CORE]), IVI: dict(PROPS[IVI])}
    del props[IVI]["ro.boot.vbmeta.digest"]
    del props[CORE]["ro.build.id"]
    p, images, _ = _guest_up(tmp_path, fake, props)
    got = {role: values for role, _, values in (parse(ln) for ln in images)}
    assert got.get("ivi", {}).get("vbmeta_digest") == "unread" and got.get("sdv_core", {}).get("build_id") == \
        "unread", p.stdout
    assert got["ivi"]["fingerprint"] == PROPS[IVI]["ro.build.fingerprint"]
