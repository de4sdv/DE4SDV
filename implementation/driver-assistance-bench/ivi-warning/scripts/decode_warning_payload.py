#!/usr/bin/env python3
"""Decode a warning-request SOME/IP payload by the guest's SOME/IP type definition.

The payload is the SOME/IP event's payload, after the 16-byte SOME/IP header: what the SDV Core
broker hands to its REFLECTION translation. The decoder reads interop/someip_type_definition.textproto
(the file the guest's mapping is generated from) and applies the rules the closed-loop driving
bench found the broker to apply: big-endian, no struct length field (length_field_size ZERO).
It knows UINT32 only, the one primitive this struct uses, and refuses anything else.

    scripts/decode_warning_payload.py --hex "00000001 0000303e"
    requested 1
    issue_time_sim_ms 12350
    # consumed 8 of 8 bytes

A payload with bytes left over (for example a 4-byte length prefix in front of the struct) or one
that is too short is refused: exit 1, the reason on stderr.
"""

from __future__ import annotations

import argparse
import pathlib
import re
import struct
import sys
from dataclasses import dataclass

TYPE_DEFINITION = pathlib.Path(__file__).resolve().parent.parent / "interop" / "someip_type_definition.textproto"
PRIMITIVES = {"UINT32": ">I"}
# The ICD's value ranges: requested is 0 or 1.
RANGES = {"requested": (0, 1)}


class DecodeError(ValueError):
    """The payload does not have the shape of the type definition."""


@dataclass(frozen=True)
class TypeDefinition:
    length_field_size: str
    fields: tuple[tuple[str, str], ...]


def load_type_definition(path: pathlib.Path = TYPE_DEFINITION) -> TypeDefinition:
    text = "\n".join(line for line in path.read_text(encoding="utf-8").splitlines()
                     if not line.lstrip().startswith("#"))
    length = re.search(r"^  length_field_size:\s*(\w+)$", text, re.M)
    if length is None:
        raise DecodeError(f"{path}: no struct length_field_size")
    fields = []
    for block in re.findall(r"field\s*\{(.*?)\n\s*\}", text, re.S):
        name = re.search(r'field_name:\s*"([^"]+)"', block)
        primitive = re.search(r"someip_primitive:\s*(\w+)", block)
        if name is None or primitive is None or primitive.group(1) not in PRIMITIVES \
                or "someip_string" in block or "someip_array" in block:
            raise DecodeError(f"{path}: unsupported field:\n{block}")
        fields.append((name.group(1), primitive.group(1)))
    return TypeDefinition(length.group(1), tuple(fields))


def decode(payload: bytes, definition: TypeDefinition) -> dict[str, int]:
    if definition.length_field_size != "ZERO":
        raise DecodeError(f"struct length field {definition.length_field_size}: this decoder reads ZERO only")
    values: dict[str, int] = {}
    offset = 0
    for name, primitive in definition.fields:
        size = struct.calcsize(PRIMITIVES[primitive])
        if offset + size > len(payload):
            raise DecodeError(f"payload too short: {name} at offset {offset} needs {size} bytes of {len(payload)}")
        (values[name],) = struct.unpack_from(PRIMITIVES[primitive], payload, offset)
        offset += size
    if offset != len(payload):
        raise DecodeError(f"{len(payload) - offset} trailing bytes after the struct ({offset} of {len(payload)});"
                          " a 4-byte prefix in front of the struct looks like this")
    return values


def out_of_range(values: dict[str, int]) -> list[str]:
    """The names of the fields whose value lies outside the ICD's range."""
    return [name for name, (low, high) in RANGES.items() if name in values and not low <= values[name] <= high]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--hex", required=True, help="the SOME/IP payload, hex digits (spaces allowed)")
    parser.add_argument("--type-definition", type=pathlib.Path, default=TYPE_DEFINITION)
    args = parser.parse_args(argv)
    payload = bytes.fromhex(re.sub(r"\s+", "", args.hex))
    try:
        values = decode(payload, load_type_definition(args.type_definition))
    except DecodeError as error:
        print(f"refused: {error}", file=sys.stderr)
        return 1
    for name, value in values.items():
        print(f"{name} {value}")
    print(f"# consumed {len(payload)} of {len(payload)} bytes")
    bad = out_of_range(values)
    if bad:
        print(f"refused: out of the ICD's range: {', '.join(bad)}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
