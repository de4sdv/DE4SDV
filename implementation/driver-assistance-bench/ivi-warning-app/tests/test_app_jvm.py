"""Host-JVM tests of the IVI warning presentation (B10).

Two checks, both with the host's JDK and no Android, no JUnit jar and no network:

1. The Android-free classes (the app's java_library de4sdv_collision_warning_model) and their
   tests under app/tests/ are compiled together with a stand-in for the part of JUnit 4 they use
   (tests/jvm/junit/) and run by tests/jvm/runner/TestMain.java. Every @Test method must run and
   pass; the count is taken from the test sources, so a test that silently stops running fails.
2. Every source of the app, the Android classes included, compiles against compile-only stand-ins
   of the Android, SDV Gateway client and protobuf APIs it calls (tests/jvm/stubs/). This is the
   compile-coverage check of the view, the sound, the subscriber and the activity; the AOSP tree
   compiles them against the real classes.

The JDK is found from DE4SDV_JDK, then JAVA_HOME, then PATH. Without one the tests skip and say so.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
SRC = ROOT / "app" / "src" / "org" / "de4sdv" / "collisionwarning"
TESTS = ROOT / "app" / "tests" / "org" / "de4sdv" / "collisionwarning"
JVM = HERE / "jvm"
MODEL_CLASSES = [
    "PresentationTimeline.java",
    "RecordWriter.java",
    "ScreenText.java",
    "WarningRecord.java",
    "WarningRequestReducer.java",
    "WarningTone.java",
]
ANDROID_CLASSES = [
    "MainActivity.java",
    "WarningRequestSubscriber.java",
    "WarningSound.java",
    "WarningView.java",
]


def _jdk_bin() -> Path | None:
    for variable in ("DE4SDV_JDK", "JAVA_HOME"):
        home = os.environ.get(variable)
        if home and (Path(home) / "bin" / "javac").is_file():
            return Path(home) / "bin"
    javac = shutil.which("javac")
    return Path(javac).resolve().parent if javac else None


JDK = _jdk_bin()
needs_jdk = pytest.mark.skipif(JDK is None, reason="no JDK (set DE4SDV_JDK or JAVA_HOME, or put javac on PATH)")


def _javac(out: Path, sources: list[Path]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [str(JDK / "javac"), "-Xlint:all", "-Werror", "-encoding", "UTF-8", "-d", str(out), *map(str, sources)],
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_the_source_split_matches_the_folder():
    on_disk = sorted(p.name for p in SRC.glob("*.java"))
    assert on_disk == sorted(MODEL_CLASSES + ANDROID_CLASSES)


def test_the_model_classes_import_no_android_and_no_protobuf():
    for name in MODEL_CLASSES:
        text = (SRC / name).read_text(encoding="utf-8")
        imports = re.findall(r"^import\s+([\w.]+)", text, flags=re.M)
        assert all(i.startswith("java.") for i in imports), (name, imports)
        assert "android." not in text.replace("Android", ""), name


@needs_jdk
def test_the_jvm_tests_run_and_pass(tmp_path):
    sources = [*(JVM / "junit" / "org" / "junit").glob("*.java"), JVM / "runner" / "TestMain.java"]
    sources += [SRC / n for n in MODEL_CLASSES]
    test_files = sorted(TESTS.glob("*Test.java"))
    assert test_files, "no test sources"
    sources += test_files
    compiled = _javac(tmp_path, sources)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr

    expected = sum(len(re.findall(r"^\s*@Test\b", f.read_text(encoding="utf-8"), flags=re.M)) for f in test_files)
    classes = [f"org.de4sdv.collisionwarning.{f.stem}" for f in test_files]
    ran = subprocess.run(
        [str(JDK / "java"), "-cp", str(tmp_path), "TestMain", *classes],
        capture_output=True,
        text=True,
        timeout=300,
    )
    print(ran.stdout)
    assert ran.returncode == 0, ran.stdout + ran.stderr
    assert f"RESULT run={expected} failed=0" in ran.stdout
    # 9 reducer + 6 record + 3 record writer + 7 timeline + 5 tone and screen text: a deleted test fails here.
    assert expected == 30


@needs_jdk
def test_every_app_source_compiles_against_the_platform_stand_ins(tmp_path):
    stubs = sorted((JVM / "stubs").rglob("*.java"))
    sources = [*stubs, *(SRC / n for n in MODEL_CLASSES + ANDROID_CLASSES)]
    compiled = _javac(tmp_path, sources)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    for name in ANDROID_CLASSES:
        assert (tmp_path / "org" / "de4sdv" / "collisionwarning" / name.replace(".java", ".class")).is_file()


def test_the_stand_ins_are_not_part_of_the_app():
    # The stand-ins must never be staged into the tree: they would shadow the platform's classes.
    assert not list((ROOT / "app").rglob("stubs"))
    staging = (ROOT / "scripts" / "stage_ivi_warning_app.sh").read_text(encoding="utf-8")
    assert "tests/jvm" not in staging


@needs_jdk
def test_the_activity_shows_before_the_sound_fetches_no_last_message_and_appends_its_record(tmp_path):
    """MainActivity against the recording stand-ins (tests/jvm/harness/ActivityHarness.java).

    Pins the two behaviors of 7201198a and the record of R11/R13:
    * the subscription asks for no last-message fetch (fetchLastMessageOnSubscribe=false): after the
      restart before a window, a retained true of an earlier run must not start a warning;
    * on a first true the screen change is posted to the FRONT of the UI queue BEFORE play() starts the
      sound; on the false that follows the clear is posted to the front and no sound starts;
    * the record file is appended to (an earlier run's line stays) and each start writes a lifecycle
      line with its pid; the lines are written by the record writer, so they are all there after
      onDestroy.
    """
    classes = tmp_path / "classes"
    files = tmp_path / "files"
    files.mkdir()
    (files / "warning.jsonl").write_text('{"event":"earlier_run"}\n')
    sources = [*sorted((JVM / "stubs").rglob("*.java")), *(SRC / n for n in MODEL_CLASSES + ANDROID_CLASSES),
               JVM / "harness" / "org" / "de4sdv" / "collisionwarning" / "ActivityHarness.java"]
    compiled = _javac(classes, sources)
    assert compiled.returncode == 0, compiled.stdout + compiled.stderr
    ran = subprocess.run(
        [str(JDK / "java"), f"-Dde4sdv.test.files={files}", "-cp", str(classes), "org.de4sdv.collisionwarning.ActivityHarness"],
        capture_output=True, text=True, timeout=120,
    )
    assert ran.returncode == 0, ran.stdout + ran.stderr
    out = dict(line.split(" ", 1) for line in ran.stdout.splitlines() if " " in line)
    assert out["SUBSCRIBE"] == "gateway:subscribe unit=de4sdv-driving-warning-request fetchLastMessageOnSubscribe=false"
    assert out["START"] == "[main:front, sound:play]", "the screen first, at the front of the queue, then the sound"
    assert out["CLEAR"] == "[main:front]"
    assert "DONE" in ran.stdout
    lines = (files / "warning.jsonl").read_text().splitlines()
    assert lines[0] == '{"event":"earlier_run"}', "the record is appended to, never truncated"
    starts = [l for l in lines if '"event":"lifecycle"' in l and '"phase":"start"' in l]
    assert len(starts) == 1 and '"pid":4242' in starts[0]
    receipts = [l for l in lines if '"event":"receipt"' in l]
    assert [('"verdict":"START"' in r, '"verdict":"CLEAR"' in r) for r in receipts] == [(True, False), (False, True)]
    assert any('"phase":"stop"' in l for l in lines)


def test_the_manifest_absorbs_the_configuration_changes_of_an_aaos_display():
    manifest = (ROOT / "app" / "AndroidManifest.xml").read_text(encoding="utf-8")
    changes = re.search(r'android:configChanges="([^"]+)"', manifest).group(1).split("|")
    for change in ("orientation", "screenSize", "smallestScreenSize", "screenLayout", "keyboardHidden", "uiMode", "density"):
        assert change in changes, change


def test_a_sound_timestamp_older_than_the_requests_play_is_ignored():
    sound = (SRC / "WarningSound.java").read_text(encoding="utf-8")
    assert "stamp.framePosition > 0 && stamp.nanoTime >= tPlay" in sound
    assert sound.index("final long tPlay = System.nanoTime();") < sound.index("track.play();")
