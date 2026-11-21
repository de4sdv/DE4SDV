"""The warning presentation's build and manifest files name the right package, modules and ids.

Every expected id is read from ../interfaces/service_ids.json (the machine-readable ICD and the
lane choices) and from the ACL files of ../ivi-warning/interop/acl, never retyped here: the app
must claim the subject the SD agent grants and subscribe to the unit the broker publishes.
"""

from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DA = ROOT.parent
IDS = json.loads((DA / "interfaces" / "service_ids.json").read_text(encoding="utf-8"))
APP = ROOT / "app"
SRC = APP / "src" / "org" / "de4sdv" / "collisionwarning"
ANDROID_NS = "{http://schemas.android.com/apk/res/android}"
SUBJECT = IDS["lane_choices"]["ivi_subscriber"]
BROKER = IDS["lane_choices"]["sdv_core_broker"]
TUNNEL = IDS["icd"]["data_tunnel"]


def _bp_modules(path: Path) -> dict[str, str]:
    """Module type and body per name, for the flat Android.bp files of this folder."""
    text = re.sub(r"//[^\n]*", "", path.read_text(encoding="utf-8"))
    modules = {}
    for match in re.finditer(r"^(\w+)\s*\{(.*?)^\}", text, flags=re.M | re.S):
        kind, body = match.group(1), match.group(2)
        name = re.search(r'^\s*name:\s*"([^"]+)"', body, flags=re.M)
        if name:
            modules[name.group(1)] = kind + "\n" + body
    return modules


def _list(body: str, key: str) -> list[str]:
    match = re.search(rf"^\s*{key}:\s*\[(.*?)\]", body, flags=re.M | re.S)
    return re.findall(r'"([^"]+)"', match.group(1)) if match else []


def _java_constant(name: str) -> str:
    text = (SRC / "WarningRequestSubscriber.java").read_text(encoding="utf-8")
    match = re.search(rf'static final String {name} = "([^"]*)";', text)
    assert match, name
    return match.group(1)


def test_the_manifest_package_is_the_granted_subject():
    manifest = ET.parse(APP / "AndroidManifest.xml").getroot()
    assert manifest.get("package") == SUBJECT["package"] == "org.de4sdv.collisionwarning"
    application = manifest.find("application")
    libraries = [lib.get(ANDROID_NS + "name") for lib in application.findall("uses-library")]
    assert libraries == ["libsdvgatewayclient-java-sdk"]
    activity = application.find("activity")
    assert activity.get(ANDROID_NS + "name") == ".MainActivity"
    assert (SRC / "MainActivity.java").is_file()
    assert "package org.de4sdv.collisionwarning;" in (SRC / "MainActivity.java").read_text(encoding="utf-8")


def test_the_app_module_is_a_platform_signed_vendor_priv_app():
    modules = _bp_modules(APP / "Android.bp")
    app = modules["De4sdvCollisionWarningPresentation"]
    assert app.startswith("android_app")
    assert 'manifest: "AndroidManifest.xml"' in app
    assert re.search(r"vendor:\s*true", app) and re.search(r"privileged:\s*true", app)
    assert 'certificate: "platform"' in app
    assert _list(app, "uses_libs") == ["libsdvgatewayclient-java-sdk"]
    static = _list(app, "static_libs")
    assert "de4sdv_collision_warning_model" in static
    assert "de4sdv_collision_warning_request_proto_java" in static
    assert "libprotobuf-java-lite" in static


def test_the_android_free_library_is_exactly_what_the_app_excludes():
    modules = _bp_modules(APP / "Android.bp")
    library = _list(modules["de4sdv_collision_warning_model"], "srcs")
    excluded = _list(modules["De4sdvCollisionWarningPresentation"], "exclude_srcs")
    assert library == excluded
    assert all((APP / path).is_file() for path in library)
    tests = modules["De4sdvCollisionWarningPresentationTests"]
    assert tests.startswith("java_test")
    assert _list(tests, "static_libs") == ["de4sdv_collision_warning_model", "junit"]


def test_the_contract_module_compiles_the_one_proto_of_the_path():
    modules = _bp_modules(ROOT / "contract" / "Android.bp")
    proto = modules["de4sdv_collision_warning_request_proto_java"]
    srcs = _list(proto, "srcs")
    assert srcs == ["de4sdv_driving_collision_warning_request.proto"]
    source = DA / "ivi-warning" / "contract" / srcs[0]
    assert source.is_file(), "the proto the staging copies is the guests' contract file"
    text = source.read_text(encoding="utf-8")
    assert re.search(r"^package de4sdv\.driving\.v1;", text, flags=re.M)
    assert "message " + TUNNEL["message"].rsplit(".", 1)[1] + " {" in text
    assert 'type: "lite"' in proto
    if 'import "sdv/vsidl/v1/annotations.proto";' in text:
        assert _list(proto, "include_dirs") == [
            "system/software_defined_vehicle/vsidl/language/src/protos",
            "external/protobuf/src",
        ]
    # No java_outer_classname or java_package: the generated class is
    # de4sdv.driving.v1.De4SdvDrivingCollisionWarningRequest.CollisionWarningRequest, as imported.
    assert "java_outer_classname" not in text and "java_package" not in text
    subscriber = (SRC / "WarningRequestSubscriber.java").read_text(encoding="utf-8")
    assert "import de4sdv.driving.v1.De4SdvDrivingCollisionWarningRequest.CollisionWarningRequest;" in subscriber


def test_no_build_file_carries_a_module_type_this_tree_refuses():
    for path in (APP / "Android.bp", ROOT / "contract" / "Android.bp"):
        text = path.read_text(encoding="utf-8")
        assert not re.search(r"^\s*soong_namespace\s*\{", text, flags=re.M), path
        assert not re.search(r"^\s*proto_library\s*\{", text, flags=re.M), path


def test_the_subscriber_names_the_ids_of_the_path():
    assert _java_constant("SUBJECT_PACKAGE") == SUBJECT["package"]
    assert _java_constant("SUBJECT_BUNDLE") == SUBJECT["bundle"]
    assert _java_constant("PUBLISHER_PACKAGE") == BROKER["package"]
    assert _java_constant("PUBLISHER_BUNDLE") == BROKER["bundle"]
    assert _java_constant("MESSAGE_NAME") == TUNNEL["message"]
    assert _java_constant("UNIT") == TUNNEL["service_unit"]


def test_the_acls_grant_what_the_app_claims():
    acl = DA / "ivi-warning" / "interop" / "acl"
    grant = (acl / "ivi_warning_subscriber.textproto").read_text(encoding="utf-8")
    policy = (acl / "ivi_broker_object_policy.textproto").read_text(encoding="utf-8")
    assert f'topic: "{_java_constant("UNIT")}"' in grant
    assert f'message: "{_java_constant("MESSAGE_NAME")}"' in grant
    assert f'include: "{_java_constant("SUBJECT_PACKAGE")}.{_java_constant("SUBJECT_BUNDLE")}"' in policy
    assert f'name: "{_java_constant("UNIT")}"' in policy
    # The subject is encoded by the install path: <package>/<bundle>.textproto.
    assert f"{SUBJECT['package']}/{SUBJECT['bundle']}.textproto" in grant


def test_the_staging_script_uses_the_same_module_and_package():
    script = (ROOT / "scripts" / "stage_ivi_warning_app.sh").read_text(encoding="utf-8")
    assert "APP_MODULE=De4sdvCollisionWarningPresentation" in script
    assert "TEST_MODULE=De4sdvCollisionWarningPresentationTests" in script
    assert "TAG=DE4SDV_COLLISION_WARNING" in script and "RECORD=warning.jsonl" in script
    record = (SRC / "WarningRecord.java").read_text(encoding="utf-8")
    assert 'TAG = "DE4SDV_COLLISION_WARNING"' in record and 'FILE = "warning.jsonl"' in record
