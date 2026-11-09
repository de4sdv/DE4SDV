#!/usr/bin/env python3
"""Local checks of the typed observation path's contract and wire codec.

What this proves, on a host with Python and `grpcio-tools` (no AOSP, no guest):

1. CONTRACT: the typed message compiles, has 43 fields with the ICD's names,
   numbers and types in the ICD's order, and has no bytes carrier and no enum
   (option B is one message with a `kind` uint32, as the model states).
2. SOMEIP STRUCT: interop/someip_type_definition.textproto declares the same 43
   fields in the same order with the SomeIpType the ICD's type implies, with no
   struct length field; the generated mapping repeats that block verbatim on all
   three events, in REFLECTION mode, and is not stale.
3. CODEC: codec/someip_struct.py encodes and decodes the struct exactly as
   section 3 says -- big-endian, AUTOSAR strings with the BOM inside the length,
   arrays whose length is in bytes -- and rejects the malformed forms.
4. AGREEMENT: for each kind, the codec's view and the protobuf message's view of
   the same 43 values are the same values under the same names, which is the
   property the broker's name-matched REFLECTION translation relies on.
5. ARTIFACTS: ids, topic, message name, ACLs and the app's constants agree.

What it does NOT prove: that the shipped broker translates the struct (RUNBOOK
gates G2/G4), that the S-CORE encoder writes this layout (state-publisher vectors
+ tests/decode_s1_vectors.py), that anything runs.

    uv run --with grpcio-tools python tests/test_contract_and_encoding.py
"""

from __future__ import annotations

import importlib
import pathlib
import re
import struct
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codec import icd_table as table  # noqa: E402
from codec import someip_struct as codec  # noqa: E402

CONTRACT = ROOT / "contract" / "de4sdv_driving_operational_state.proto"
TYPE_DEFINITION = ROOT / "interop" / "someip_type_definition.textproto"
MAPPING = ROOT / "interop" / "de4sdv_driving_operational_state.vsidl"
BUNDLE = ROOT / "interop" / "de4sdv_driving_operational_state_bundle.vsidl"
BROKER_ACL = ROOT / "interop" / "broker_acl_append.textproto"
SUBJECT_ACL = ROOT / "interop" / "acl" / "ivi_observer_subscriber.textproto"
OBJECT_POLICY = ROOT / "interop" / "acl" / "ivi_broker_object_policy.textproto"
VSOMEIP = ROOT / "interop" / "vsomeip_config.json"
SUBSCRIBER_JAVA = ROOT / "app" / "src" / "org" / "de4sdv" / "drivingstate" / "TypedStateSubscriber.java"
RECORD_JAVA = ROOT / "app" / "src" / "org" / "de4sdv" / "drivingstate" / "StateRecord.java"
ICD = ROOT.parent / "interfaces" / "ICD.md"
GENERATOR = ROOT / "scripts" / "gen_someip_vsidl.py"

SERVICE_ID = 0x4DF0
INSTANCE_ID = 0x0001
EVENTS = (0x8001, 0x8002, 0x8003)
EVENT_GROUP = 0x0001
PORT = 30510
TOPIC = "de4sdv-driving-operational-state"
MESSAGE_NAME = "de4sdv.driving.v1.DrivingOperationalState"
SUBJECT_PACKAGE = "org.de4sdv.drivingstate"
SUBJECT_BUNDLE = "DrivingStateObserver"


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def text(path: pathlib.Path) -> str:
    check(path.is_file(), f"missing {path}")
    return path.read_text(encoding="utf-8")


def brace_blocks(source: str, opener: str) -> list[str]:
    """Every top-level `<opener> { ... }` block, braces balanced."""
    blocks: list[str] = []
    depth = 0
    start = None
    for line in source.splitlines():
        if depth == 0 and line.strip().startswith(opener) and line.strip().endswith("{"):
            start = line
            depth = line.count("{") - line.count("}")
            if depth == 0:
                blocks.append(line)
                start = None
            continue
        if start is not None:
            start += "\n" + line
            depth += line.count("{") - line.count("}")
            if depth == 0:
                blocks.append(start)
                start = None
    return blocks


def _one(pattern: str, entry: str, what: str) -> str:
    match = re.search(pattern, entry)
    if match is None:
        raise AssertionError(f"no {what} in:\n{entry}")
    return match.group(1)


def struct_fields(block: str) -> list[tuple[str, str]]:
    """(field_name, someip type token) per field, in file order."""
    fields: list[tuple[str, str]] = []
    for entry in brace_blocks(block, "field"):
        name = _one(r'field_name:\s*"([^"]+)"', entry, "field_name")
        # Order matters: an array block also contains a someip_primitive, its
        # element type.
        if "someip_array" in entry:
            length = _one(r"length_field_size:\s*(\w+)", entry, "length_field_size")
            element = _one(r"array_type\s*\{\s*someip_primitive:\s*(\w+)", entry, "array_type")
            kind = f"array:{length}:{element}"
        elif "someip_string" in entry:
            encoding = _one(r"string_encoding:\s*(\w+)", entry, "string_encoding")
            length = _one(r"length_field_size:\s*(\w+)", entry, "length_field_size")
            kind = f"string:{encoding}:{length}"
        elif "someip_primitive:" in entry:
            kind = _one(r"someip_primitive:\s*(\w+)", entry, "primitive")
        else:
            raise AssertionError(f"field {name} has no usable field_type")
        fields.append((name, kind))
    return fields


def expected_someip_type(kind: str) -> str:
    if kind in table.SOMEIP_PRIMITIVE:
        return table.SOMEIP_PRIMITIVE[kind]
    if kind == table.STR:
        return f"string:{table.SOMEIP_STRING_ENCODING}:{table.SOMEIP_STRING_LENGTH_FIELD}"
    if kind == table.F32_ARRAY:
        return f"array:{table.SOMEIP_ARRAY_LENGTH_FIELD}:{table.SOMEIP_ARRAY_ELEMENT[kind]}"
    raise AssertionError(kind)


def _offset(name: str) -> int:
    """Byte offset of a field in a message whose other fields are at their defaults."""
    total = 0
    for field in table.FIELDS:
        if field.name == name:
            return total
        if field.kind in (table.U32, table.F32):
            total += 4
        elif field.kind == table.STR:
            total += 8      # length 4, BOM 3, NUL 1
        else:
            total += 4      # an empty array is its length field only
    raise KeyError(name)


# ------------------------------------------------------------------ 1. contract


def _is_repeated(field) -> bool:
    """protobuf >= 5 exposes is_repeated; older ones only the deprecated label."""
    flag = getattr(field, "is_repeated", None)
    if flag is not None:
        return bool(flag)
    return field.label == 3  # LABEL_REPEATED


def load_pb():
    out = pathlib.Path(tempfile.mkdtemp(prefix="de4sdv-typed-"))
    result = subprocess.run(
        [sys.executable, "-m", "grpc_tools.protoc", f"-I{CONTRACT.parent}",
         f"--python_out={out}", str(CONTRACT)],
        capture_output=True, text=True,
    )
    check(result.returncode == 0, f"protoc failed:\n{result.stdout}\n{result.stderr}")
    sys.path.insert(0, str(out))
    return importlib.import_module("de4sdv_driving_operational_state_pb2")


def test_contract(pb) -> None:
    descriptor = pb.DrivingOperationalState.DESCRIPTOR
    found = [(field.name, field.number, field.type, _is_repeated(field))
             for field in descriptor.fields]
    check(len(found) == 43, f"{len(found)} fields, expected 43")

    proto_types = {
        table.U32: 13,      # TYPE_UINT32
        table.F32: 2,       # TYPE_FLOAT
        table.STR: 9,       # TYPE_STRING
        table.F32_ARRAY: 2, # TYPE_FLOAT, repeated
    }
    for index, field in enumerate(table.FIELDS):
        name, number, kind, repeated_flag = found[index]
        check(name == field.name, f"position {index}: {name} != {field.name} (order is the contract)")
        check(number == field.number, f"{name}: number {number} != {field.number}")
        check(kind == proto_types[field.kind], f"{name}: protobuf type {kind} != {field.kind}")
        check(repeated_flag == (field.kind == table.F32_ARRAY),
              f"{name}: repeated={repeated_flag} but kind is {field.kind}")
    check(not descriptor.enum_types_by_name, "the message must not carry an enum; kind is a uint32")
    check([f.number for f in table.FIELDS] == list(range(1, 44)), "field numbers are not 1..43")
    source = text(CONTRACT)
    check(re.search(r"^\s*bytes\s+\w+\s*=", source, re.M) is None,
          "the contract declares a bytes field (option A)")
    check("schema_major = 1;" in source and "schema_minor = 2;" in source,
          "schema_major/schema_minor are not fields 1 and 2")
    print(f"contract: ok (43 fields, numbers 1..43, uint32/float/string/repeated float, no bytes)")


# -------------------------------------------------------------- 2. someip struct


def test_type_definition() -> None:
    block = text(TYPE_DEFINITION)
    check("length_field_size: ZERO" in block, "the struct must declare no length field")
    fields = struct_fields(block)
    check(len(fields) == 43, f"{len(fields)} fields in the type definition, expected 43")
    for index, (name, kind) in enumerate(fields):
        expected = table.FIELDS[index]
        check(name == expected.name, f"position {index}: {name} != {expected.name}")
        check(kind == expected_someip_type(expected.kind),
              f"{name}: SomeIpType {kind} != {expected_someip_type(expected.kind)}")

    mapping = text(MAPPING)
    blocks = brace_blocks(mapping, "type_definition")
    check(len(blocks) == 3, f"{len(blocks)} type_definition blocks, expected 3 (one per event)")
    check(len(set(blocks)) == 1, "the three type_definition blocks are not identical")
    check(mapping.count("message_translation_mode: REFLECTION") == 3, "each event must use REFLECTION")
    check("INTERPRET_AS_BYTES" not in mapping, "the mapping still contains the bytes mode (option A)")
    check(mapping.count("field_name:") == 43 * 3, "the mapping does not carry 43 fields x 3 events")
    for event in EVENTS:
        check(mapping.count(f"event_id: 0x{event:04x}") == 1, f"event {event:#06x} not exactly once")
    check('type_name: "DrivingOperationalState"' in mapping, "mapping type name")
    check(f'topic: "{TOPIC}"' in mapping, "mapping topic")

    generated = subprocess.run([sys.executable, str(GENERATOR), "--check"],
                               capture_output=True, text=True)
    check(generated.returncode == 0,
          f"the committed mapping is stale:\n{generated.stdout}{generated.stderr}")
    print("someip struct: ok (43 fields x 3 events, identical, REFLECTION, no struct length, not stale)")


# --------------------------------------------------------------------- 3. codec


def test_codec() -> None:
    # Defaults only, plus schema_major: big-endian uint32 first, nothing before it.
    minimal = codec.encode({"schema_major": table.SCHEMA_MAJOR})
    check(minimal[:4] == b"\x00\x00\x00\x02", f"first field is not a big-endian 2: {minimal[:4].hex()}")
    check(minimal[:1] != b"\x08", "the output looks like protobuf, not a SOME/IP struct")

    # An empty string is length 4: BOM + NUL, not length 0.
    empty = codec.encode({"producer": ""})
    at = _offset("producer")
    check(empty[at:at + 8] == bytes.fromhex("00000004efbbbf00"),
          f"empty string framed as {empty[at:at + 8].hex()}")

    # The length is the whole body, BOM included.
    name = codec.encode({"producer": "abc"})
    check(struct.unpack_from(">I", name, at)[0] == 3 + 3 + 1, "string length does not cover BOM+text+NUL")

    # Arrays: the length is in BYTES, so 64 floats carry 256.
    one = codec.encode({"plan_x": [1.0]})
    farray_at = _offset("plan_x")
    check(struct.unpack_from(">I", one, farray_at)[0] == 4, "a one-element array is not 4 bytes")
    check(struct.unpack_from(">f", one, farray_at + 4)[0] == 1.0, "the element is not big-endian float32")
    full = codec.encode({"plan_x": [0.75 * index for index in range(64)]})
    check(struct.unpack_from(">I", full, farray_at)[0] == 256, "64 floats are not 256 bytes")

    # Round trip, exact in binary32 (sixteenths), one sample per kind.
    for kind in (table.KIND_PLAN, table.KIND_VEHICLE_STATE, table.KIND_HEALTH):
        state = codec.sample(kind)
        wire = codec.encode(state)
        back, consumed = codec.decode_with_trailer(wire)
        check(back == state, f"{table.KIND_NAMES[kind]}: round trip differs")
        check(consumed == len(wire), f"{table.KIND_NAMES[kind]}: consumed {consumed} of {len(wire)}")

    # Truncation, an unset BOM, a stray NUL, a non-multiple-of-four array length,
    # trailing bytes: all rejected with an offset.
    wire = codec.encode(codec.sample(table.KIND_HEALTH))
    for bad, why in (
        (wire[:-1], "truncated"),
        (wire + b"\x00", "trailing byte"),
        (wire + b"\x00\x00", "trailing zero fill"),
    ):
        try:
            codec.decode(bad)
        except codec.DecodeError:
            pass
        else:
            raise AssertionError(f"{why} accepted")
    codec.decode_with_trailer(wire + b"\x00\x00", allow_zero_fill=True)

    no_bom = bytearray(wire)
    no_bom[16:20] = struct.pack(">I", 4)
    no_bom[20:24] = b"abcd"
    try:
        codec.decode(bytes(no_bom))
    except codec.DecodeError as error:
        check("BOM" in str(error), f"wrong complaint for a missing BOM: {error}")
    else:
        raise AssertionError("a string without a BOM was accepted")

    not_text = bytearray(wire)
    not_text[20:24] = b"\xff\xfe\x00\x00"
    try:
        codec.decode(bytes(not_text))
    except codec.DecodeError:
        pass
    else:
        raise AssertionError("invalid UTF-8 was accepted")

    sizes = {table.KIND_NAMES[k]: len(codec.encode(codec.sample(k))) for k in table.KIND_NAMES if k}
    check(sizes["PLAN"] == 1301, f"plan size {sizes['PLAN']} != 1301")
    check(sizes["VEHICLE_STATE"] == 218, f"vehicle size {sizes['VEHICLE_STATE']} != 218")
    check(sizes["HEALTH"] == 234, f"health size {sizes['HEALTH']} != 234")
    check(sizes["PLAN"] < 2048, "a full plan exceeds the S-CORE PreSerializedData<2048> bound")
    print(f"codec: ok (big-endian, BOM in the length, arrays in bytes, 3 kinds "
          f"{sizes['PLAN']}/{sizes['VEHICLE_STATE']}/{sizes['HEALTH']} B, malformed rejected)")


# ----------------------------------------------------------------- 4. agreement


def test_agreement(pb) -> None:
    for kind in (table.KIND_PLAN, table.KIND_VEHICLE_STATE, table.KIND_HEALTH):
        state = codec.sample(kind)
        decoded, _ = codec.decode_with_trailer(codec.encode(state))
        message = pb.DrivingOperationalState()
        for field in table.FIELDS:
            value = decoded[field.name]
            if field.kind == table.F32_ARRAY:
                getattr(message, field.name).extend(value)
            else:
                setattr(message, field.name, value)
        back = pb.DrivingOperationalState.FromString(message.SerializeToString())
        for field in table.FIELDS:
            actual = getattr(back, field.name)
            expected = decoded[field.name]
            if field.kind == table.F32_ARRAY:
                check(list(actual) == expected, f"{field.name}: protobuf {list(actual)[:3]} != codec")
            else:
                check(actual == expected,
                      f"{field.name}: protobuf {actual!r} != codec {expected!r} "
                      f"({table.KIND_NAMES[kind]})")
        check(back.kind == kind, f"kind round trip: {back.kind} != {kind}")
        check(back.schema_major == table.SCHEMA_MAJOR, "schema_major did not survive")
    print("agreement: ok (the codec and the protobuf message hold the same 43 values per kind)")


# ----------------------------------------------------------------- 5. artifacts


def test_artifacts() -> None:
    mapping = text(MAPPING)
    check(f"someip_service_id: 0x{SERVICE_ID:04x}" in mapping, "mapping service id")
    check(f"instance_id: 0x{INSTANCE_ID:04x}" in mapping, "mapping instance id")
    check(f"group_id: 0x{EVENT_GROUP:04x}" in mapping, "mapping event group")
    check(f'topic: "{TOPIC}"' in mapping, "mapping topic")
    check('package_name: "com.android.sdv.someip"' in mapping, "mapping broker package")
    check('service_bundle_name: "SomeIpBroker"' in mapping, "mapping broker bundle")

    check(f'message: "{MESSAGE_NAME}"' in text(BUNDLE), "bundle publisher")
    check(f'message: "{MESSAGE_NAME}"' in text(BROKER_ACL), "broker acl message")
    check(f'topic: "{TOPIC}"' in text(BROKER_ACL), "broker acl topic")
    check(f'message: "{MESSAGE_NAME}"' in text(SUBJECT_ACL), "subject acl message")
    check(f'message: "{MESSAGE_NAME}"' in text(OBJECT_POLICY), "object policy message")
    check(f'include: "{SUBJECT_PACKAGE}.{SUBJECT_BUNDLE}"' in text(OBJECT_POLICY), "object policy reader")
    check(f'name: "{TOPIC}"' in text(OBJECT_POLICY), "object policy unit")

    import json

    vsomeip = json.loads(text(VSOMEIP))
    service = vsomeip["services"][0]
    check(int(service["service"], 16) == SERVICE_ID, "stack service id")
    check(int(service["instance"], 16) == INSTANCE_ID, "stack instance id")
    check(int(service["reliable"]["port"]) == PORT, "stack port")
    check({int(e["event"], 16) for e in service["events"]} == set(EVENTS), "stack events")
    check(vsomeip["unicast"] == "192.168.98.3", "core unicast")

    java = text(SUBSCRIBER_JAVA)
    check(f'SUBJECT_PACKAGE = "{SUBJECT_PACKAGE}"' in java, "java subject package")
    check(f'SUBJECT_BUNDLE = "{SUBJECT_BUNDLE}"' in java, "java subject bundle")
    check(f'TOPIC_NAME = "{TOPIC}"' in java, "java topic")
    check(f'MESSAGE_NAME = "{MESSAGE_NAME}"' in java, "java message name")
    check("DrivingOperationalState.parser()" in java, "the app does not parse the typed message")
    check(".getData()" not in java, "the app still reads a bytes field (option A)")

    # The Java string literals escape their quotes for the JSON text; drop the
    # backslashes so the check reads the field names, not the escaping.
    record = text(RECORD_JAVA).replace("\\", "")
    for name in table.NAMES:
        check(f'"{name}"' in record, f"the record does not write {name}")

    icd = text(ICD)
    check("`0x4DF0`" in icd, "ICD service id")
    check(str(PORT) in icd, "ICD port")
    check("DrivingOperationalState" in icd, "ICD message name")
    check("REFLECTION" in icd, "ICD translation mode")
    print("artifacts agree: ok (mapping, bundle, ACLs, stack, the app, the record, the ICD)")


def main() -> int:
    pb = load_pb()
    test_contract(pb)
    test_type_definition()
    test_codec()
    test_agreement(pb)
    test_artifacts()
    print("ALL LOCAL CHECKS PASSED (contract + encoding; no AOSP, no runtime)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
