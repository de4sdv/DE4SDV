#!/usr/bin/env python3
"""Local checks of the typed observation path's contract, without AOSP.

What this proves, on any host with Python and network for `grpcio-tools`:

1. the ICD message compiles and every field number and type matches the table
   of interfaces/ICD.md section 3, so the S-CORE side and the observer cannot
   drift silently;
2. a sample of each kind round-trips through the protobuf wire format and
   stays under the 2048-byte bound the S-CORE event and the VSIDL carrier
   declare;
3. the slot layout of the broker's bytes publication (varint length, 0x0A,
   varint length, payload, zero fill) is extracted by the same rules
   SlotFramer.java implements, so the Java framer and this test agree;
4. the identifiers of the seven artifacts agree with one another and with the
   ICD (service 0x4df0, instance 0x0001, events, eventgroup, port 30510, topic
   name, message name, subject package/bundle, max size).

It proves nothing about the runtime: no AOSP, no guest, no broker. Run:

    uv run --with grpcio-tools python tests/test_contract_and_framing.py
"""
from __future__ import annotations

import importlib
import json
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
CONTRACT = ROOT / "contract"
OBSERVED = CONTRACT / "observed" / "de4sdv_driving_operational_state.proto"
CARRIER = CONTRACT / "de4sdv_driving_operational_state_frame.proto"
MAPPING = ROOT / "interop" / "de4sdv_driving_operational_state.vsidl"
BUNDLE = ROOT / "interop" / "de4sdv_driving_operational_state_bundle.vsidl"
BROKER_ACL = ROOT / "interop" / "broker_acl_append.textproto"
SUBJECT_ACL = ROOT / "interop" / "acl" / "ivi_observer_subscriber.textproto"
OBJECT_POLICY = ROOT / "interop" / "acl" / "ivi_broker_object_policy.textproto"
VSOMEIP = ROOT / "interop" / "vsomeip_config.json"
SUBSCRIBER_JAVA = ROOT / "app" / "src" / "org" / "de4sdv" / "drivingstate" / "GatewayStateSubscriber.java"
APP_CARRIER = ROOT / "app" / "proto" / "de4sdv_driving_operational_state_frame.proto"
ICD = ROOT.parent / "interfaces" / "ICD.md"

SERVICE_ID = 0x4DF0
INSTANCE_ID = 0x0001
EVENTS = (0x8001, 0x8002, 0x8003)
EVENT_GROUP = 0x0001
PORT = 30510
TOPIC = "de4sdv-driving-operational-state"
MESSAGE_NAME = "com.android.sdv.someip.De4sdvDrivingOperationalStateFrame"
SUBJECT_PACKAGE = "org.de4sdv.drivingstate"
SUBJECT_BUNDLE = "DrivingStateObserver"

# ICD section 3, as (number, proto type) per field name.
ICD_FIELDS = {
    "schema_major": (1, "uint32"),
    "schema_minor": (2, "uint32"),
    "kind": (3, "enum"),
    "sequence": (4, "uint64"),
    "producer": (5, "string"),
    "publish_time_real": (6, "double"),
    "publish_time_mono": (7, "double"),
    "plan_frame_index": (10, "uint64"),
    "plan_capture_time": (11, "double"),
    "plan_production_time": (12, "double"),
    "plan_reference": (13, "string"),
    "run_record": (14, "string"),
    "plan_acceleration": (15, "float"),
    "plan_curvature": (16, "float"),
    "plan_x": (17, "float"),
    "plan_y": (18, "float"),
    "speed_kmh": (20, "float"),
    "longitudinal_acceleration": (21, "float"),
    "lateral_acceleration": (22, "float"),
    "yaw_rate_dps": (23, "float"),
    "sample_capture_time": (24, "double"),
    "sample_receipt_time_mono": (25, "double"),
    "mode": (30, "uint32"),
    "cause": (31, "uint32"),
    "mode_source": (32, "string"),
    "cause_since_mono": (33, "double"),
    "last_plan_frame_index": (34, "uint64"),
    "dropped_samples": (35, "uint64"),
}

ANNOTATIONS_STUB = """
syntax = "proto3";
package sdv.vsidl.v1;
import "google/protobuf/descriptor.proto";
enum MessageModel { SINGLE_PUB = 0; }
message Publication { uint32 message_count = 1; MessageModel model = 2; }
extend google.protobuf.MessageOptions { Publication publication = 50001; }
extend google.protobuf.FieldOptions { uint32 variable_type_max_size = 50002; }
"""


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_pb(module: str):
    """The generated module, under whichever path protoc chose for this -I set."""
    for candidate in (f"de4sdv.driving.v1.{module}", module):
        try:
            return importlib.import_module(candidate)
        except ImportError:
            continue
    raise AssertionError(f"protoc did not generate {module}")


def compile_protos() -> pathlib.Path:
    out = pathlib.Path(tempfile.mkdtemp(prefix="de4sdv-proto-"))
    stub = out / "stub" / "sdv" / "vsidl" / "v1"
    stub.mkdir(parents=True)
    (stub / "annotations.proto").write_text(ANNOTATIONS_STUB)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "grpc_tools.protoc",
            f"-I{CONTRACT / 'observed'}",
            f"-I{CONTRACT}",
            f"-I{out / 'stub'}",
            f"--python_out={out}",
            str(OBSERVED),
            str(CARRIER),
        ],
        capture_output=True,
        text=True,
    )
    check(result.returncode == 0, f"protoc failed:\n{result.stdout}\n{result.stderr}")
    sys.path.insert(0, str(out))
    return out


def test_field_numbers() -> None:
    pb = load_pb("de4sdv_driving_operational_state_pb2")

    descriptor = pb.DrivingOperationalState.DESCRIPTOR
    found = {field.name: field for field in descriptor.fields}
    check(set(found) == set(ICD_FIELDS), f"field set differs: {sorted(set(found) ^ set(ICD_FIELDS))}")
    type_names = {
        "uint32": 13,
        "uint64": 4,
        "string": 9,
        "double": 1,
        "float": 2,
    }
    for name, (number, kind) in ICD_FIELDS.items():
        field = found[name]
        check(field.number == number, f"{name}: number {field.number} != {number}")
        if kind == "enum":
            check(field.type == 14, f"{name}: not an enum ({field.type})")
        else:
            check(field.type == type_names[kind], f"{name}: type {field.type} != {kind}")
    observed = text(OBSERVED)
    for name in ("plan_acceleration = 15", "plan_curvature = 16", "plan_x = 17", "plan_y = 18"):
        check(f"repeated float {name}" in observed, f"{name} is not a repeated float")
    check(pb.DrivingOperationalState.DESCRIPTOR.enum_types_by_name == {},
          "the Kind enum must be top level, as the ICD declares it")
    check(pb.Kind.Value("PLAN") == 1 and pb.Kind.Value("VEHICLE_STATE") == 2
          and pb.Kind.Value("HEALTH") == 3, "Kind values differ from the ICD")
    print("field numbers and types: ok (28 fields, Kind 1/2/3)")


def sample_plan(pb) -> object:
    message = pb.DrivingOperationalState(
        schema_major=1,
        schema_minor=0,
        kind=pb.PLAN,
        sequence=7,
        producer="statePublisher",
        publish_time_real=1762742400.123456,
        publish_time_mono=8123.456789,
        plan_frame_index=1234,
        plan_capture_time=123.4,
        plan_production_time=8123.400,
        plan_reference="plan-1234",
        run_record="1a2b3c4d5e6f7a8b",
    )
    for index in range(64):
        message.plan_acceleration.append(round(-0.5 + index * 0.01, 3))
        message.plan_curvature.append(round(0.001 * index, 6))
        message.plan_x.append(round(0.1 * index, 2))
        message.plan_y.append(round(0.05 * index, 2))
    return message


def test_round_trip_and_size() -> None:
    pb = load_pb("de4sdv_driving_operational_state_pb2")

    plan = sample_plan(pb)
    wire = plan.SerializeToString()
    check(len(wire) <= 2048, f"the plan sample is {len(wire)} bytes, above the 2048 bound")
    back = pb.DrivingOperationalState.FromString(wire)
    check(back == plan, "the plan sample does not round-trip")
    check(len(back.plan_x) == 64 and len(back.plan_acceleration) == 64, "arrays lost")
    check(back.publish_time_real == plan.publish_time_real, "double stamp changed")

    vehicle = pb.DrivingOperationalState(
        schema_major=1, schema_minor=0, kind=pb.VEHICLE_STATE, sequence=99,
        producer="statePublisher", publish_time_real=1762742401.0,
        publish_time_mono=8124.1, speed_kmh=36.0, longitudinal_acceleration=-1.25,
        lateral_acceleration=0.1, yaw_rate_dps=-0.5, sample_capture_time=123.5,
        sample_receipt_time_mono=8124.0,
    )
    check(pb.DrivingOperationalState.FromString(vehicle.SerializeToString()) == vehicle,
          "the vehicle sample does not round-trip")

    health = pb.DrivingOperationalState(
        schema_major=1, schema_minor=0, kind=pb.HEALTH, sequence=41,
        producer="statePublisher", publish_time_real=1762742402.0,
        publish_time_mono=8125.1, mode=3, cause=7, mode_source="actuationAdapter",
        cause_since_mono=8125.0, last_plan_frame_index=1234, dropped_samples=0,
    )
    check(pb.DrivingOperationalState.FromString(health.SerializeToString()) == health,
          "the health sample does not round-trip")
    print(f"round trip: ok (plan {len(wire)} B of 2048, vehicle "
          f"{len(vehicle.SerializeToString())} B, health {len(health.SerializeToString())} B)")


def encode_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


def slot_of(payload: bytes, fill_to: int = 0) -> bytes:
    """The slot a raw reader sees: varint length, 0x0A, varint length, payload, fill."""
    message = b"\x0a" + encode_varint(len(payload)) + payload
    slot = encode_varint(len(message)) + message
    if fill_to > len(slot):
        slot += b"\x00" * (fill_to - len(slot))
    return slot


def read_varint(data: bytes, start: int):
    value, shift = 0, 0
    for step in range(5):
        position = start + step
        if position >= len(data):
            return None
        byte = data[position]
        value |= (byte & 0x7F) << shift
        shift += 7
        if not byte & 0x80:
            if value > 0xFFFFFFFF:
                return None
            return (value, position + 1)
    return None


def frame(slot: bytes) -> tuple[str, int, int, str]:
    """The rules of SlotFramer.java, field for field."""
    if not slot:
        return ("EMPTY", 0, 0, "empty")
    first = slot[0]
    if first != 0x0A and first != 0x08:
        outer = read_varint(slot, 0)
        if outer is not None:
            message_bytes, message_start = outer
            if (message_bytes > 0 and message_start + message_bytes <= len(slot)
                    and slot[message_start] == 0x0A):
                message_end = message_start + message_bytes
                inner = read_varint(slot, message_start + 1)
                if inner is not None and inner[0] > 0 and inner[1] + inner[0] <= message_end:
                    payload_offset = inner[1]
                    end = payload_offset + inner[0]
                    if not any(slot[end:]):
                        return ("SLOT", payload_offset, inner[0], "slot_length_prefix")
                    return ("INVALID", 0, 0, "slot_bytes_after_field")
                return ("INVALID", 0, 0, "slot_inner_envelope_invalid")
    if first == 0x0A:
        index, value, shift = 1, 0, 0
        next_offset = None
        for step in range(5):
            position = index + step
            if position >= len(slot):
                return ("INVALID", 0, 0, "carrier_length_varint_invalid")
            byte = slot[position]
            value |= (byte & 0x7F) << shift
            shift += 7
            if not byte & 0x80:
                if value > 0xFFFFFFFF:
                    return ("INVALID", 0, 0, "carrier_length_varint_invalid")
                next_offset = position + 1
                break
        if next_offset is None:
            return ("INVALID", 0, 0, "carrier_length_varint_invalid")
        if value <= 0:
            return ("INVALID", 0, 0, "carrier_length_zero")
        if next_offset + value > len(slot):
            return ("INVALID", 0, 0, "carrier_length_exceeds_bytes")
        end = next_offset + value
        if any(slot[end:]):
            return ("INVALID", 0, 0, "carrier_bytes_after_field")
        return ("CARRIER", next_offset, value, "carrier_envelope")
    if first == 0x08:
        return ("DIRECT", 0, len(slot), "ok")
    return ("INVALID", 0, 0, f"unexpected_first_byte_0x{first:02x}")


def test_slot_layout() -> None:
    pb = load_pb("de4sdv_driving_operational_state_pb2")

    payload = sample_plan(pb).SerializeToString()

    # The raw queue slot: varint message length, 0x0A, varint payload length,
    # payload, zero fill. This is what broker_wrapper.cpp parsed on the C API.
    for fill in (0, 2053):
        slot = slot_of(payload, fill)
        layout, offset, length, reason = frame(slot)
        check(layout == "SLOT", f"fill {fill}: layout {layout} ({reason})")
        check(slot[offset:offset + length] == payload, f"fill {fill}: payload differs")
    check(len(slot_of(payload, 2053)) == 2053, "the filled slot is not 2053 bytes")

    # The carrier envelope alone (what the platform's typed subscriber parses).
    envelope = b"\x0a" + encode_varint(len(payload)) + payload
    layout, offset, length, reason = frame(envelope)
    check(layout == "CARRIER" and envelope[offset:offset + length] == payload,
          f"carrier: {layout} ({reason})")

    # The payload alone (what the carrier's `data` field holds).
    direct = frame(payload)
    check(direct[0] == "DIRECT" and direct[1] == 0 and direct[2] == len(payload),
          "the direct layout is not recognised")

    check(frame(b"")[0] == "EMPTY", "empty not recognised")
    check(frame(b"\x0a\x40\x08\x01")[3] == "carrier_length_exceeds_bytes", "overlong not caught")
    check(frame(b"\x0a\x02\x08\x01\x7f")[3] == "carrier_bytes_after_field", "trailing bytes not caught")
    check(frame(b"\x22\x01\x41")[0] == "INVALID", "unexpected first byte not caught")
    print("slot layout: ok (raw slot with and without fill, carrier, direct, failures)")


def text(path: pathlib.Path) -> str:
    check(path.is_file(), f"missing {path}")
    return path.read_text()


def test_artifacts_agree() -> None:
    mapping = text(MAPPING)
    check(f"someip_service_id: 0x{SERVICE_ID:04x}" in mapping, "mapping service id")
    check(f"instance_id: 0x{INSTANCE_ID:04x}" in mapping, "mapping instance id")
    check(f"group_id: 0x{EVENT_GROUP:04x}" in mapping, "mapping event group")
    for event in EVENTS:
        check(mapping.count(f"event_id: 0x{event:04x}") == 1, f"event {event:#06x} not once")
    check(mapping.count("message_translation_mode: INTERPRET_AS_BYTES") == 3,
          "each event needs INTERPRET_AS_BYTES")
    check(mapping.count("type_name: \"De4sdvDrivingOperationalStateFrame\"") == 3, "carrier type name")
    check(mapping.count(f'topic: "{TOPIC}"') == 1, "one topic name in the parameterization")
    check("value: \"de4sdv-driving-operational-state\"" in mapping, "service unit value")

    carrier = text(CARRIER)
    check("package com.android.sdv.someip;" in carrier, "carrier package")
    check("message De4sdvDrivingOperationalStateFrame {" in carrier, "carrier message")
    check("variable_type_max_size) = 2048" in carrier, "carrier max size")
    app_carrier = text(APP_CARRIER)
    check("package com.android.sdv.someip;" in app_carrier, "app carrier package")
    check("message De4sdvDrivingOperationalStateFrame {" in app_carrier, "app carrier message")
    check("bytes data = 1;" in app_carrier, "app carrier field number")

    check('message: "De4sdvDrivingOperationalStateFrame"' in text(BUNDLE), "bundle publisher")
    check(f'topic: "{TOPIC}"' in text(BROKER_ACL), "broker acl topic")
    check(f"message: \"{MESSAGE_NAME}\"" in text(BROKER_ACL), "broker acl message")
    check(f'topic: "{TOPIC}"' in text(SUBJECT_ACL), "subject acl topic")
    check(f"include: \"{SUBJECT_PACKAGE}.{SUBJECT_BUNDLE}\"" in text(OBJECT_POLICY), "object policy")
    check(f'name: "{TOPIC}"' in text(OBJECT_POLICY), "object policy unit")

    vsomeip = json.loads(text(VSOMEIP))
    service = vsomeip["services"][0]
    check(int(service["service"], 16) == SERVICE_ID, "stack service id")
    check(int(service["instance"], 16) == INSTANCE_ID, "stack instance id")
    check(int(service["reliable"]["port"]) == PORT, "stack port")
    check({int(e["event"], 16) for e in service["events"]} == set(EVENTS), "stack events")
    check({int(g["eventgroup"], 16) for g in service["eventgroups"]} == {EVENT_GROUP},
          "stack eventgroup")
    check(vsomeip["unicast"] == "192.168.98.3", "core unicast")

    java = text(SUBSCRIBER_JAVA)
    check(f'SUBJECT_PACKAGE = "{SUBJECT_PACKAGE}"' in java, "java subject package")
    check(f'SUBJECT_BUNDLE = "{SUBJECT_BUNDLE}"' in java, "java subject bundle")
    check(f'TOPIC_NAME = "{TOPIC}"' in java, "java topic")
    check(f'MESSAGE_NAME =\n            "{MESSAGE_NAME}"' in java or f'"{MESSAGE_NAME}"' in java,
          "java message name")

    icd = text(ICD)
    check(f"`0x4DF0`" in icd, "ICD service id")
    check("30510" in icd, "ICD port")
    check("DrivingOperationalState" in icd, "ICD message name")
    print("artifacts agree: ok (7 files + the Java subscriber + the ICD)")


def main() -> int:
    compile_protos()
    test_field_numbers()
    test_round_trip_and_size()
    test_slot_layout()
    test_artifacts_agree()
    print("ALL LOCAL CHECKS PASSED (contract only; no AOSP, no runtime)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
