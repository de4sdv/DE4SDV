"""The guest contract of the warning request: the typed message and its SOME/IP mapping.

MAP-DRIVING-DA-WARNING-REQUEST: "serialization to the new message at the SOME/IP interop of SDV
Core; no value changes on the path". The SDV Core broker translates the SOME/IP struct in
REFLECTION mode and fills the protobuf fields BY NAME, so the struct's field names and the
message's field names must be the same, in the same order, with matching types.

Checks, with no AOSP tree and no protobuf compiler (the message is read as text):
- the .proto declares de4sdv.driving.v1.CollisionWarningRequest exactly as ICD.md (service_ids.json)
  says, as a VSIDL publication;
- the SOME/IP type definition has the same names, in field-number order, as UINT32, with no
  struct length field, and equals the ICD's byte layout;
- the generated VSIDL mapping is not stale and maps 0x4df1/0x8001 onto the message and the unit;
- the broker's publisher declaration and ACL and the IVI subscriber ACL and object policy name the
  same message, unit and subject.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BENCH = ROOT.parent
IDS = json.loads((BENCH / "interfaces" / "service_ids.json").read_text(encoding="utf-8"))
ICD = IDS["icd"]
LANE = IDS["lane_choices"]
PROTO = ROOT / "contract" / "de4sdv_driving_collision_warning_request.proto"
TYPE_DEFINITION = ROOT / "interop" / "someip_type_definition.textproto"
MAPPING = ROOT / "interop" / "de4sdv_driving_collision_warning_request.vsidl"
BUNDLE = ROOT / "interop" / "de4sdv_driving_collision_warning_request_bundle.vsidl"
BROKER_ACL = ROOT / "interop" / "broker_acl_append.textproto"
SUBJECT_ACL = ROOT / "interop" / "acl" / "ivi_warning_subscriber.textproto"
OBJECT_POLICY = ROOT / "interop" / "acl" / "ivi_broker_object_policy.textproto"
GENERATOR = ROOT / "scripts" / "gen_someip_vsidl.py"

TUNNEL = ICD["data_tunnel"]
PACKAGE, MESSAGE = TUNNEL["message"].rsplit(".", 1)
UNIT = TUNNEL["service_unit"]
SOMEIP = ICD["someip_warning_request"]
BROKER = LANE["sdv_core_broker"]
SUBJECT = LANE["ivi_subscriber"]
PROTO_TO_SOMEIP = {"uint32": "UINT32"}


def _text(path: Path) -> str:
    assert path.is_file(), f"missing {path}"
    return path.read_text(encoding="utf-8")


def _without_comments(text: str, marker: str) -> str:
    return "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(marker))


def proto_fields() -> list[tuple[str, str, int]]:
    """(type, name, number) of CollisionWarningRequest, in file order."""
    source = _without_comments(_text(PROTO), "//")
    body = re.search(rf"\bmessage\s+{MESSAGE}\s*\{{(.*)\}}", source, re.S)
    assert body, f"no message {MESSAGE}"
    return [(kind, name, int(number)) for kind, name, number in
            re.findall(r"^\s*([\w.]+)\s+(\w+)\s*=\s*(\d+)\s*[;\[]", body.group(1), re.M)]


def type_definition_fields(text: str) -> list[tuple[str, str]]:
    """(field_name, someip type) per field of a type_definition block, in order."""
    fields = []
    for block in re.findall(r"field\s*\{(.*?)\n\s*\}", text, re.S):
        name = re.search(r'field_name:\s*"([^"]+)"', block)
        primitive = re.search(r"someip_primitive:\s*(\w+)", block)
        assert name and primitive, f"field without a name or a primitive type:\n{block}"
        assert "someip_string" not in block and "someip_array" not in block
        fields.append((name.group(1), primitive.group(1)))
    return fields


def test_proto_declares_the_icd_message() -> None:
    source = _text(PROTO)
    assert re.search(r'^syntax\s*=\s*"proto3";', source, re.M)
    assert re.search(rf"^package\s+{re.escape(PACKAGE)};", source, re.M)
    assert len(re.findall(r"^\s*message\s+\w+", _without_comments(source, "//"), re.M)) == 1
    assert proto_fields() == [(f["type"], f["name"], f["number"]) for f in TUNNEL["fields"]]
    # Fixed-size message: no string, bytes, repeated field or enum to bound or to carry.
    code = _without_comments(source, "//")
    for word in ("string", "bytes", "repeated", "enum", "oneof", "map<"):
        assert word not in code, f"the message carries a {word}"


def test_proto_is_a_vsidl_publication() -> None:
    source = _text(PROTO)
    assert 'import "sdv/vsidl/v1/annotations.proto";' in source
    option = re.search(r"option\s*\(\.sdv\.vsidl\.v1\.publication\)\s*=\s*\{([^}]*)\};", source)
    assert option, "no publication option (the pdk29 catalog fails with PublicationTypeDoesNotExist)"
    assert re.search(r"model\s*:\s*SINGLE_PUB\b", option.group(1))
    count = int(re.search(r"message_count\s*:\s*(\d+)", option.group(1)).group(1))
    assert count >= 2 and count % 2 == 0


def test_type_definition_matches_the_proto_by_name_and_number() -> None:
    text = _text(TYPE_DEFINITION)
    blocks = re.findall(r"^type_definition\s*\{", text, re.M)
    assert len(blocks) == 1
    assert re.search(r"^  length_field_size:\s*ZERO$", text, re.M), "the struct must declare no length field"
    by_number = sorted(proto_fields(), key=lambda field: field[2])
    assert [number for _, _, number in by_number] == list(range(1, len(by_number) + 1))
    expected = [(name, PROTO_TO_SOMEIP[kind]) for kind, name, _ in by_number]
    assert type_definition_fields(text) == expected
    # ... and the ICD's byte layout: same names, same types, in offset order.
    layout = ICD["warning_request_someip_payload"]["fields"]
    assert type_definition_fields(text) == [(f["name"], f["type"]) for f in layout]


def test_generated_mapping_is_not_stale() -> None:
    result = subprocess.run([sys.executable, str(GENERATOR), "--check"], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_mapping_maps_the_service_onto_the_message() -> None:
    mapping = _text(MAPPING)
    assert f'package: "{BROKER["package"]}"' in mapping
    assert re.search(rf"someip_service_id: {SOMEIP['service_id']}\b", mapping)
    assert re.search(rf"instance_id: {SOMEIP['instance_id']}\b", mapping)
    assert mapping.count("instance_impl {") == 1
    assert mapping.count("offered_event {") == 1
    assert re.search(rf"group_id: {SOMEIP['eventgroup_id']}\b", mapping)
    assert re.search(rf"event_id: {SOMEIP['event_id']}\b", mapping)
    assert f'sdv_service_unit_parameterization {{key: 0 value: "{UNIT}"}}' in mapping
    assert re.search(r"service_unit: 0\b", mapping)
    # The unit type is keyed by the PROTOBUF package and the bare message name.
    assert f'package_name: "{PACKAGE}"' in mapping
    assert f'type_name: "{MESSAGE}"' in mapping
    assert f'service_bundle_name: "{BROKER["bundle"]}"' in mapping
    assert mapping.count("message_translation_mode: REFLECTION") == 1
    code = _without_comments(mapping, "#")
    for absent in ("INTERPRET_AS_BYTES", "sdv_topic_parameterization"):
        assert absent not in code
    # The type definition is the canonical file's block, verbatim.
    canonical = _without_comments(_text(TYPE_DEFINITION), "#").strip()
    emitted = re.search(r"^( *)type_definition \{.*?^\1\}", mapping, re.S | re.M)
    assert emitted
    dedented = "\n".join(line[len(emitted.group(1)):] for line in emitted.group(0).splitlines())
    assert dedented == canonical


def test_broker_declares_and_may_publish_the_unit() -> None:
    bundle = _text(BUNDLE)
    assert f'package: "{BROKER["package"]}"' in bundle
    assert f'name: "{BROKER["bundle"]}"' in bundle
    assert re.search(rf'publisher\s*\{{\s*message:\s*"{re.escape(TUNNEL["message"])}"\s*\}}', bundle)
    acl = _without_comments(_text(BROKER_ACL), "#")
    blocks = re.findall(r"publisher\s*\{([^}]*)\}", acl)
    assert len(blocks) == 1
    assert f'message: "{TUNNEL["message"]}"' in blocks[0]
    assert f'topic: "{UNIT}"' in blocks[0]


def test_ivi_subject_may_subscribe_and_the_broker_object_names_it() -> None:
    subject = _without_comments(_text(SUBJECT_ACL), "#")
    assert re.findall(r"subscriber\s*\{([^}]*)\}", subject) == [
        f'\n  message: "{TUNNEL["message"]}"\n  topic: "{UNIT}"\n']
    install = f"/product/etc/sdv_authz_acls/{SUBJECT['package']}/{SUBJECT['bundle']}.textproto"
    assert install in _text(SUBJECT_ACL)

    policy_text = _text(OBJECT_POLICY)
    policy = _without_comments(policy_text, "#")
    assert f"/product/etc/sdv_authz_acls/{BROKER['package']}/{BROKER['bundle']}.textproto" in policy_text
    assert f'message: "{TUNNEL["message"]}"' in policy and f'topic: "{UNIT}"' in policy
    acl = re.search(r'acls\s*\{\s*name:\s*"(\w+)"\s*include:\s*"([^"]+)"\s*\}', policy)
    assert acl and acl.group(2) == f"{SUBJECT['package']}.{SUBJECT['bundle']}"
    unit = re.search(r'service_units\s*\{\s*name:\s*"([^"]+)"\s*acl_names:\s*"(\w+)"\s*\}', policy)
    assert unit and unit.groups() == (UNIT, acl.group(1))


def test_names_follow_the_gateway_conventions() -> None:
    # Service unit names are lowercase [a-z0-9-]; service bundle names start with [A-Z].
    assert re.fullmatch(r"[a-z0-9-]+", UNIT)
    assert re.fullmatch(r"[A-Z]\w*", SUBJECT["bundle"])
    assert SUBJECT["package"].count(".") >= 1
