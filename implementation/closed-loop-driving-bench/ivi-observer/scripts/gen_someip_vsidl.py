#!/usr/bin/env python3
"""Generate the SOME/IP mapping of the driving operational state (ICD v2 section 3).

The mapping file is generated, not typed by hand, for one reason: a VSIDL
mapping file has no way to name a `type_definition` and reuse it, so the same
43-field struct has to appear once per offered event. Three hand-maintained
copies is three chances to diverge; one source plus a generator plus a test that
regenerates and compares is not.

    scripts/gen_someip_vsidl.py               # write interop/de4sdv_driving_operational_state.vsidl
    scripts/gen_someip_vsidl.py --check       # exit 1 if the committed file is stale
    scripts/gen_someip_vsidl.py --one-unit    # write interop/variants/...one_unit.vsidl (all
                                              # three events on ONE service unit; see below)

Reads:  interop/someip_type_definition.textproto  (the canonical struct)
        codec/icd_table.py                        (ids, names, sanity of the block)
Writes: interop/de4sdv_driving_operational_state.vsidl
"""

from __future__ import annotations

import argparse
import pathlib
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from codec import icd_table as table  # noqa: E402

TYPE_TEXT = ROOT / "interop" / "someip_type_definition.textproto"
MAPPING = ROOT / "interop" / "de4sdv_driving_operational_state.vsidl"
MAPPING_ONE_UNIT = ROOT / "interop" / "variants" / "de4sdv_driving_operational_state.one_unit.vsidl"

PACKAGE = "de4sdv.driving.v1"
TYPE_NAME = "DrivingOperationalState"
BROKER_PACKAGE = "com.android.sdv.someip"
BROKER_BUNDLE = "SomeIpBroker"
# The service unit name(s) the broker registers. They are what the broker publish ACL, the IVI
# object policy, the IVI subject grant and the app's subscription name. There is no
# sdv_topic_parameterization: the catalog is compiled for target API pdk29
# (catalog/CATALOG_UPDATE), and the proven DE4SDV mapping (catalog/de4sdv_score) uses service
# units only.
SERVICE_UNIT = "de4sdv-driving-operational-state"
SERVICE_UNITS = (
    (0, "de4sdv-driving-operational-state-plan"),
    (1, "de4sdv-driving-operational-state-vehicle-state"),
    (2, "de4sdv-driving-operational-state-health"),
)
SERVICE_ID = "0x4df0"
INSTANCE_ID = "0x0001"
EVENT_GROUP = "0x0001"
EVENTS = (("0x8001", "plan", 0), ("0x8002", "vehicle state", 1), ("0x8003", "health", 2))
TYPE_INDENT = " " * 10

HEADER = f"""\
# DE4SDV INC-DRIVING-001 slice 10b, typed observation path (GAP-DRIVING-006).
# Bench-only. GENERATED FILE: do not edit; regenerate with
#   python3 scripts/gen_someip_vsidl.py            (this file: three service units)
#   python3 scripts/gen_someip_vsidl.py --one-unit (variant: one service unit)
# from interop/someip_type_definition.textproto and codec/icd_table.py.
# tests/test_contract_and_encoding.py fails when this file is stale.
#
# Maps the one SOME/IP service of the driving operational state (service
# {SERVICE_ID}, instance {INSTANCE_ID}, eventgroup {EVENT_GROUP}, events 0x8001 plan /
# 0x8002 vehicle state / 0x8003 health -- ICD section 3; TCP 30510 is the stack's
# vsomeip_config.json, not this file) onto the typed message
# {PACKAGE}.{TYPE_NAME} -- the type the model names:
#
#   MAP-DRIVING-OPERATIONAL-STATE: "one SOME/IP service with three events, plan,
#   vehicle state and health, mapped onto one VSIDL message
#   DrivingOperationalState with a kind field".
#
# Translation: message_translation_mode REFLECTION on all three events. The broker
# reads the SOME/IP payload by the type_definition below (big-endian, no struct
# length field, AUTOSAR strings, FLOAT32 arrays with a 4-byte BYTE count) and fills
# the protobuf fields BY NAME (metadata.rs field_by_name). A field_name the message
# does not have fails the whole event's metadata at broker start, it does not leave
# one field at its default.
#
# sdv_unit_type: package_name is the PROTOBUF package of the message, type_name its
# bare name -- that pair is the key of the runtime VSIDL config
# (vsidl_rc_generator UnitType::from) and every mapping of the catalog follows it.
# service_bundle_name is deprecated and ignored for the key.
#
# Service units: {{units}}
# The broker creates one SDV publisher per offered event (pubsub_handler.rs,
# handle_someip_event_mapping_infos). The publication is SINGLE_PUB: "Each channel can
# only have one publisher. A single service bundle can publish multiple channels"
# (vsidl annotations.proto, SdvPublication.PublisherModel). Three units of one type
# keep one publisher per unit; three events on ONE unit would put three broker
# publishers on one channel, which that model excludes (and MULTI_PUB forbids several
# publishers of one type in one bundle). The one-unit file is kept as a variant only.
#
# The one type_definition the three events share is emitted verbatim three times:
# textproto has no aliasing, so "one definition" is a property the generator
# guarantees and the test checks, not something the format can express.
"""


def type_definition_block() -> str:
    body = TYPE_TEXT.read_text(encoding="utf-8")
    # Keep the fragment's own comments out of the mapping (they are long); the
    # mapping header explains the conventions once. A comment line inside a field
    # block would otherwise survive, so drop every full-line comment.
    lines = [line for line in body.splitlines() if not line.lstrip().startswith("#")]
    block = "\n".join(lines).strip()
    if not block.startswith("type_definition {"):
        raise SystemExit(f"{TYPE_TEXT} must contain exactly the type_definition block")
    fields = block.count("field_name:")
    if fields != len(table.FIELDS):
        raise SystemExit(
            f"{TYPE_TEXT} declares {fields} fields, the ICD table has {len(table.FIELDS)}"
        )
    return textwrap.indent(block, TYPE_INDENT)


def event_block(event_id: str, label: str, unit_key: int, type_definition: str) -> str:
    # One instance_impl per offered event: SomeIpInstanceImplementation's interface_type is a
    # oneof (someip.proto), and every upstream mapping with several events repeats
    # instance_impl (catalog/sample/rear_tire_system_someip.vsidl, carla_client/...).
    return f"""\
    instance_impl {{
      offered_event {{
        # {label}
        group_id: {EVENT_GROUP}
        event_id: {event_id}
        simple_event {{
          sdv_unit_type {{
            package_name: "{PACKAGE}"
            service_bundle_name: "{BROKER_BUNDLE}"
            type_name: "{TYPE_NAME}"
          }}
          service_unit: {unit_key}
          message_translation_mode: REFLECTION
{type_definition}
        }}
      }}
    }}
"""


def render(one_unit: bool = False) -> str:
    type_definition = type_definition_block()
    units = ((0, SERVICE_UNIT),) if one_unit else SERVICE_UNITS
    events = "".join(
        event_block(event_id, label, 0 if one_unit else key, type_definition)
        for event_id, label, key in EVENTS
    )
    unit_lines = "".join(
        f'      sdv_service_unit_parameterization {{{{key: {key} value: "{name}"}}}}\n'
        for key, name in units
    ).replace("{{", "{").replace("}}", "}")
    body = f"""
package: "{BROKER_PACKAGE}"

some_ip_mapping {{
  someip_service_mapping {{
    someip_service_id: {SERVICE_ID}
    version_major: 0x1
    version_minor: 0x0
    instance {{
      instance_id: {INSTANCE_ID}
      # The service unit names the broker registers (the ACLs' topic names).
{unit_lines}    }}
{events}  }}
}}
"""
    names = ", ".join(name for _, name in units)
    return HEADER.replace("{units}", names) + body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="generate the SOME/IP mapping")
    parser.add_argument("--check", action="store_true", help="compare, do not write")
    parser.add_argument("--one-unit", action="store_true", help="the one-service-unit variant")
    args = parser.parse_args(argv)

    target = MAPPING_ONE_UNIT if args.one_unit else MAPPING
    rendered = render(one_unit=args.one_unit)
    if args.check:
        current = target.read_text(encoding="utf-8") if target.is_file() else ""
        if current != rendered:
            print(f"STALE: {target} differs from the generator output", file=sys.stderr)
            return 1
        print(f"mapping up to date ({len(rendered.splitlines())} lines)")
        return 0

    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(rendered, encoding="utf-8")
    print(
        f"wrote {target} ({len(rendered.splitlines())} lines, "
        f"{len(table.FIELDS)} fields x {len(EVENTS)} events)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
