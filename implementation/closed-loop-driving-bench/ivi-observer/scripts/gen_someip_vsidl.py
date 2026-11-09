#!/usr/bin/env python3
"""Generate the SOME/IP mapping of the driving operational state (ICD v2 section 3).

The mapping file is generated, not typed by hand, for one reason: a VSIDL
mapping file has no way to name a `type_definition` and reuse it, so the same
43-field struct has to appear once per offered event. Three hand-maintained
copies is three chances to diverge; one source plus a generator plus a test that
regenerates and compares is not.

    scripts/gen_someip_vsidl.py            # write interop/de4sdv_driving_operational_state.vsidl
    scripts/gen_someip_vsidl.py --check    # exit 1 if the committed file is stale

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

PACKAGE = "de4sdv.driving.v1"
TYPE_NAME = "DrivingOperationalState"
BROKER_PACKAGE = "com.android.sdv.someip"
BROKER_BUNDLE = "SomeIpBroker"
TOPIC = "de4sdv-driving-operational-state"
SERVICE_UNIT = "de4sdv-driving-operational-state"
SERVICE_ID = "0x4df0"
INSTANCE_ID = "0x0001"
EVENT_GROUP = "0x0001"
EVENTS = (("0x8001", "plan"), ("0x8002", "vehicle state"), ("0x8003", "health"))
TYPE_INDENT = " " * 10

HEADER = f"""\
# DE4SDV INC-DRIVING-001 slice 10b, typed observation path (GAP-DRIVING-006).
# Bench-only. GENERATED FILE: do not edit; regenerate with
#   python3 scripts/gen_someip_vsidl.py
# from interop/someip_type_definition.textproto and codec/icd_table.py.
# tests/test_contract_and_encoding.py fails when this file is stale.
#
# Maps the one SOME/IP service of the driving operational state (service
# {SERVICE_ID}, instance {INSTANCE_ID}, eventgroup {EVENT_GROUP}, events 0x8001 plan /
# 0x8002 vehicle state / 0x8003 health, reliable, TCP 30510 -- ICD section 3) to
# one Data Tunnel topic, `{TOPIC}`, typed
# {PACKAGE}.{TYPE_NAME} -- the type the model names:
#
#   MAP-DRIVING-OPERATIONAL-STATE: "one SOME/IP service with three events, plan,
#   vehicle state and health, mapped onto one VSIDL message
#   DrivingOperationalState with a kind field".
#
# Translation: message_translation_mode REFLECTION on all three events. The broker
# lays out the SOME/IP payload by the type_definition below (big-endian struct,
# no struct length field, AUTOSAR strings, length-prefixed FLOAT32 arrays) and
# fills the protobuf message's fields BY NAME. There is no bytes carrier and no
# payload decoding anywhere on the guest: the IVI app receives the typed message.
#
# One topic parameter for three events: one subscription, one ACL pair and one
# loss counter at the observer, and the two clocks on its screen come from one
# stream. The order within a kind is the publisher's `sequence`; the interleaving
# across kinds carries no meaning and is not used.
#
# If vsidlc or the broker refuses three offered events on one topic parameter, the
# variant is three topics (keys 1/2/3, `{TOPIC}-plan` and so on) and three
# subscriptions in the app; RUNBOOK step 6 names the switch and its cost.
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


def event_block(event_id: str, label: str, type_definition: str) -> str:
    return f"""\
      offered_event {{
        # {label}
        group_id: {EVENT_GROUP}
        event_id: {event_id}
        simple_event {{
          sdv_unit_type {{
            package_name: "{BROKER_PACKAGE}"
            service_bundle_name: "{BROKER_BUNDLE}"
            type_name: "{TYPE_NAME}"
          }}
          service_unit: 0
          topic: 1
          message_translation_mode: REFLECTION
{type_definition}
        }}
      }}
"""


def render() -> str:
    type_definition = type_definition_block()
    events = "".join(
        event_block(event_id, label, type_definition) for event_id, label in EVENTS
    )
    body = f"""
package: "{BROKER_PACKAGE}"

some_ip_mapping {{
  someip_service_mapping {{
    someip_service_id: {SERVICE_ID}
    version_major: 0x1
    version_minor: 0x0
    instance {{
      instance_id: {INSTANCE_ID}
      # Key 0 is the service unit name, which is what the broker's publish ACL and
      # the IVI broker object policy see; key 1 names the topic.
      sdv_service_unit_parameterization {{key: 0 value: "{SERVICE_UNIT}"}}
      sdv_topic_parameterization {{
        key: 1
        value {{
          topic: "{TOPIC}"
          capacity: 16
        }}
      }}
    }}
    instance_impl {{
{events}    }}
  }}
}}
"""
    return HEADER + body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="generate the SOME/IP mapping")
    parser.add_argument("--check", action="store_true", help="compare, do not write")
    args = parser.parse_args(argv)

    rendered = render()
    if args.check:
        current = MAPPING.read_text(encoding="utf-8") if MAPPING.is_file() else ""
        if current != rendered:
            print(f"STALE: {MAPPING} differs from the generator output", file=sys.stderr)
            return 1
        print(f"mapping up to date ({len(rendered.splitlines())} lines)")
        return 0

    MAPPING.write_text(rendered, encoding="utf-8")
    print(
        f"wrote {MAPPING} ({len(rendered.splitlines())} lines, "
        f"{len(table.FIELDS)} fields x {len(EVENTS)} events)"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
