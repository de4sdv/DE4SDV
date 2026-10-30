"""The bench's relay inputs name the merged IVI frame relay (main 5835cb6f), and agree with its own files.

The relay is on main (implementation/score-reference-interop-bench/ivi-frame-relay),
so the bench names its values directly: the init-service name (which is also the
liblog tag and the binary), the init file, and the authz subject. This test reads
the relay's own files, so a change there that the bench does not follow fails here
instead of on the VM.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

import pytest

BENCH = Path(__file__).resolve().parents[1]
ROOT = BENCH.parents[1]
RELAY = ROOT / "implementation" / "score-reference-interop-bench" / "ivi-frame-relay"


def _bench_env(*names: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if not k.startswith("RELAY_")}
    script = f'. "{BENCH}/scripts/bench_env.sh"; ' + "; ".join(f'printf "%s\\n" "${{{n}:-}}"' for n in names)
    script += "; require_relay_inputs >/dev/null && echo OK || echo MISSING"
    out = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env, check=True).stdout
    lines = out.splitlines()
    return dict(zip(names, lines[:len(names)])) | {"require": lines[-1]}


def _service() -> tuple[str, str]:
    """(name, path) of the relay's init service in its .rc."""
    match = re.search(r"^service (\S+) (\S+)", (RELAY / "de4sdv_ivi_frame_relay.rc").read_text(), re.MULTILINE)
    assert match, "the relay's .rc declares no service"
    return match.group(1), match.group(2)


def _subject() -> tuple[str, str, str]:
    text = (RELAY / "include" / "de4sdv_ivi_frame_relay" / "options.hpp").read_text()
    match = re.search(r'SubjectIdentity subject\{"([^"]+)", "([^"]+)", "([^"]+)"\}', text)
    assert match, "the relay's options.hpp holds no default subject"
    return match.groups()


def test_the_bench_names_the_merged_relay_by_default():
    values = _bench_env("RELAY_BIN", "RELAY_RC", "RELAY_LOGCAT_TAG", "RELAY_SUBJECT_PACKAGE",
                        "RELAY_SUBJECT_BUNDLE", "RELAY_SUBJECT_INSTANCE", "IVI_PRODUCT", "AOSP_TOP")
    service, binary_path = _service()
    assert values["RELAY_LOGCAT_TAG"] == service
    assert Path(values["RELAY_RC"]).resolve() == (RELAY / "de4sdv_ivi_frame_relay.rc").resolve()
    assert (values["RELAY_SUBJECT_PACKAGE"], values["RELAY_SUBJECT_BUNDLE"], values["RELAY_SUBJECT_INSTANCE"]) \
        == _subject()
    module = re.search(r'cc_binary \{\s*name: "([^"]+)"', (RELAY / "Android.bp").read_text()).group(1)
    assert Path(values["RELAY_BIN"]).name == module == Path(binary_path).name
    # The AOSP build installs the system binary under the product out tree at the .rc's path.
    assert values["RELAY_BIN"] == f"{values['AOSP_TOP']}/out/target/product/{values['IVI_PRODUCT']}{binary_path}"
    assert values["require"] == "OK"


def test_the_example_settings_and_the_broker_policy_name_the_same_relay():
    service, _ = _service()
    package, bundle, _instance = _subject()
    settings = json.loads((BENCH / "config" / "run-settings.example.json").read_text())
    assert settings["relay_logcat_tag"] == service
    policy = (BENCH / "aosp-overlay" / "ivi-acl" / "broker_object_policy.textproto").read_text()
    assert f'include: "{package}.{bundle}"' in policy


@pytest.mark.parametrize("name", ["RELAY_BIN", "RELAY_RC", "RELAY_LOGCAT_TAG", "RELAY_SUBJECT_PACKAGE",
                                  "RELAY_SUBJECT_BUNDLE", "RELAY_SUBJECT_INSTANCE"])
def test_an_empty_relay_input_still_fails_fast(name):
    env = {k: v for k, v in os.environ.items() if not k.startswith("RELAY_")} | {name: ""}
    script = f'. "{BENCH}/scripts/bench_env.sh"; require_relay_inputs'
    result = subprocess.run(["bash", "-c", script], capture_output=True, text=True, env=env)
    assert result.returncode != 0 and name in result.stdout
