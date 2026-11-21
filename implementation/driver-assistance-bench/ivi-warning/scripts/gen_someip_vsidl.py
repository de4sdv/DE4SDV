#!/usr/bin/env python3
"""Generate the SOME/IP mapping of the warning request (VSIDL, REFLECTION).

Adapted from the closed-loop driving bench's ivi-observer/scripts/gen_someip_vsidl.py. The mapping
is generated so that its ids come from one place and its struct from one place:

    reads   ../interfaces/service_ids.json               (service, instance, eventgroup, event,
                                                          the message and its service unit)
            interop/someip_type_definition.textproto     (the canonical struct)
            contract/de4sdv_driving_collision_warning_request.proto (field count sanity)
    writes  interop/de4sdv_driving_collision_warning_request.vsidl

    scripts/gen_someip_vsidl.py            write the mapping
    scripts/gen_someip_vsidl.py --check    exit 1 if the committed mapping is stale
"""

from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
IDS = ROOT.parent / "interfaces" / "service_ids.json"
TYPE_TEXT = ROOT / "interop" / "someip_type_definition.textproto"
PROTO = ROOT / "contract" / "de4sdv_driving_collision_warning_request.proto"
MAPPING = ROOT / "interop" / "de4sdv_driving_collision_warning_request.vsidl"
TYPE_INDENT = " " * 10

HEADER = """\
# DE4SDV INC-DRIVING-002, the driver-assistance bench: the warning request on the guests.
# Draft, bench-only, not yet validated. GENERATED FILE: do not edit; regenerate with
#   python3 scripts/gen_someip_vsidl.py
# from ../interfaces/service_ids.json and interop/someip_type_definition.textproto.
# tests/test_warning_contract.py fails when this file is stale.
#
# Maps the SOME/IP service of the warning request (service {service}, instance {instance},
# eventgroup {eventgroup}, event {event}; reliable TCP {port} is the stack's vsomeip_config.json,
# not this file) onto the typed message {message}, published by the SDV Core
# SOME/IP broker as the service unit {unit} (MAP-DRIVING-DA-WARNING-REQUEST: \"serialization to
# the new message at the SOME/IP interop of SDV Core\").
#
# Translation: message_translation_mode REFLECTION. The broker reads the payload by the
# type_definition below (big-endian, no struct length field) and fills the protobuf fields BY
# NAME; a field_name the message does not have fails the event's metadata at broker start.
#
# sdv_unit_type: package_name is the PROTOBUF package of the message and type_name its bare name,
# the key of the runtime VSIDL config; service_bundle_name is kept as the closed-loop driving
# bench's mapping has it. One event, one instance_impl, one service unit: the publication is
# SINGLE_PUB. No sdv_topic_parameterization: the catalog is compiled for target API pdk29.
"""


def _ids() -> dict:
    return json.loads(IDS.read_text(encoding="utf-8"))


def type_definition_block() -> str:
    lines = [line for line in TYPE_TEXT.read_text(encoding="utf-8").splitlines()
             if not line.lstrip().startswith("#")]
    block = "\n".join(lines).strip()
    if not block.startswith("type_definition {") or block.count("type_definition {") != 1:
        raise SystemExit(f"{TYPE_TEXT} must contain exactly one type_definition block")
    fields = block.count("field_name:")
    proto_fields = len(re.findall(r"^\s*uint32\s+\w+\s*=\s*\d+\s*;", PROTO.read_text(encoding="utf-8"), re.M))
    if fields != proto_fields:
        raise SystemExit(f"{TYPE_TEXT} declares {fields} fields, the message {proto_fields}")
    return textwrap.indent(block, TYPE_INDENT)


def render() -> str:
    ids = _ids()
    icd, lane = ids["icd"], ids["lane_choices"]
    someip = icd["someip_warning_request"]
    tunnel = icd["data_tunnel"]
    broker = lane["sdv_core_broker"]
    package, type_name = tunnel["message"].rsplit(".", 1)
    header = HEADER.format(service=someip["service_id"], instance=someip["instance_id"],
                           eventgroup=someip["eventgroup_id"], event=someip["event_id"],
                           port=someip["port"], message=tunnel["message"], unit=tunnel["service_unit"])
    body = f"""
package: "{broker['package']}"

some_ip_mapping {{
  someip_service_mapping {{
    someip_service_id: {someip['service_id']}
    version_major: 0x1
    version_minor: 0x0
    instance {{
      instance_id: {someip['instance_id']}
      # The service unit the broker registers (the ACLs' topic name).
      sdv_service_unit_parameterization {{key: 0 value: "{tunnel['service_unit']}"}}
    }}
    instance_impl {{
      offered_event {{
        # the warning request
        group_id: {someip['eventgroup_id']}
        event_id: {someip['event_id']}
        simple_event {{
          sdv_unit_type {{
            package_name: "{package}"
            service_bundle_name: "{broker['bundle']}"
            type_name: "{type_name}"
          }}
          service_unit: 0
          message_translation_mode: REFLECTION
{type_definition_block()}
        }}
      }}
    }}
  }}
}}
"""
    return header + body


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="generate the SOME/IP mapping of the warning request")
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
    print(f"wrote {MAPPING} ({len(rendered.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
