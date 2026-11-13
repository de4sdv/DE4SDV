#!/usr/bin/env python3
"""Independent reference codec of the driving operational state's SOME/IP struct.

Written from `interfaces/ICD.md` v2 section 3 and the AOSP SOME/IP type-definition
rules -- big-endian primitives, AUTOSAR UTF-8 strings with a four-byte length that
counts the BOM, the bytes and the terminating NUL, and dynamic FLOAT32 arrays
whose four-byte length is in BYTES. No C++ of the publisher is read or reused: it
is the independent half of the pair, so that agreement between it and the S-CORE
encoder (state-publisher/tests/vectors) means something.

Wire form (ICD section 3):

    <43 fields in table order, no struct length field, big-endian>

    u32    4 bytes, unsigned
    f32    4 bytes, IEEE-754 binary32
    str    4-byte length N, then N bytes: EF BB BF + UTF-8 text + 00
           (so N >= 4, and an empty string is 00 00 00 04 EF BB BF 00)
    f32[]  4-byte length M in bytes, then M/4 FLOAT32 values

Usage as a library:

    from codec.someip_struct import encode, decode, sample

Usage from a shell (VM gates, vector checks):

    python3 codec/someip_struct.py selftest
    python3 codec/someip_struct.py sample --kind plan --hex
    python3 codec/someip_struct.py decode --hex 00000002...

The decoder is strict and positional: a short buffer, a bad string length, a
missing BOM, a length not divisible by four or a non-zero trailing byte raise
DecodeError with the byte offset, because every one of those is a real wire fault
on this path and none of them should degrade into a default value.
"""

from __future__ import annotations

import argparse
import struct
import sys
from typing import Any, Dict, Iterable, List, Mapping, Sequence, Tuple

if __package__ in (None, ""):
    sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent.parent))

from codec import icd_table as table  # noqa: E402

BOM = b"\xef\xbb\xbf"
ZERO = b"\x00"


class DecodeError(ValueError):
    """The buffer is not a section 3 struct. `offset` is where it went wrong."""

    def __init__(self, message: str, offset: int) -> None:
        super().__init__(f"{message} at byte {offset}")
        self.offset = offset


# --------------------------------------------------------------------- encode


def _as_u32(name: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name}: expected an int, got {type(value).__name__}")
    if not 0 <= value <= 0xFFFFFFFF:
        raise ValueError(f"{name}: {value} outside 0..2^32-1")
    return value


def _as_f32(name: str, value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{name}: expected a number, got {type(value).__name__}")
    return float(value)


def _encode_string(name: str, value: Any) -> bytes:
    if not isinstance(value, str):
        raise TypeError(f"{name}: expected a str, got {type(value).__name__}")
    text = value.encode("utf-8")
    if b"\x00" in text:
        # A NUL inside the text would move the terminator and make the length
        # ambiguous for any reader that scans for 0x00.
        raise ValueError(f"{name}: contains a NUL character")
    body = BOM + text + ZERO
    return struct.pack(">I", len(body)) + body


def _encode_f32_array(name: str, value: Iterable[Any]) -> bytes:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError(f"{name}: expected a sequence of numbers")
    elements = [struct.pack(">f", _as_f32(f"{name}[{i}]", v)) for i, v in enumerate(value)]
    body = b"".join(elements)
    return struct.pack(">I", len(body)) + body


def encode(state: Mapping[str, Any]) -> bytes:
    """Encode all 43 fields, in table order. Missing fields take their default."""
    unknown = set(state) - set(table.NAMES)
    if unknown:
        raise KeyError(f"unknown field(s): {sorted(unknown)}")
    out = bytearray()
    for field in table.FIELDS:
        value = state.get(field.name, table.default(field.name))
        if field.kind == table.U32:
            out += struct.pack(">I", _as_u32(field.name, value))
        elif field.kind == table.F32:
            out += struct.pack(">f", _as_f32(field.name, value))
        elif field.kind == table.STR:
            out += _encode_string(field.name, value)
        elif field.kind == table.F32_ARRAY:
            out += _encode_f32_array(field.name, value)
        else:  # pragma: no cover - the table is closed
            raise KeyError(field.kind)
    return bytes(out)


# --------------------------------------------------------------------- decode


def _need(data: bytes, offset: int, count: int, what: str) -> None:
    if offset + count > len(data):
        raise DecodeError(f"{what}: needs {count} bytes, {len(data) - offset} left", offset)


def _read_u32(data: bytes, offset: int, what: str) -> Tuple[int, int]:
    _need(data, offset, 4, what)
    return struct.unpack_from(">I", data, offset)[0], offset + 4


def _read_string(data: bytes, offset: int, what: str) -> Tuple[str, int]:
    length, offset = _read_u32(data, offset, f"{what} length")
    _need(data, offset, length, what)
    if length < len(BOM) + len(ZERO):
        raise DecodeError(f"{what}: length {length} cannot hold BOM + NUL", offset - 4)
    body = data[offset:offset + length]
    if not body.startswith(BOM):
        raise DecodeError(f"{what}: no UTF-8 BOM (EF BB BF)", offset)
    if body[-1:] != ZERO:
        raise DecodeError(f"{what}: no terminating NUL", offset + length - 1)
    text = body[len(BOM):-1]
    if ZERO in text:
        raise DecodeError(f"{what}: NUL inside the text", offset + len(BOM) + text.index(ZERO))
    try:
        return text.decode("utf-8"), offset + length
    except UnicodeDecodeError as error:
        raise DecodeError(f"{what}: not UTF-8 ({error.reason})", offset + len(BOM) + error.start) from error


def _read_f32_array(data: bytes, offset: int, what: str) -> Tuple[List[float], int]:
    length, offset = _read_u32(data, offset, f"{what} length")
    if length % 4:
        raise DecodeError(f"{what}: length {length} is not a multiple of 4", offset - 4)
    _need(data, offset, length, what)
    count = length // 4
    values = list(struct.unpack_from(f">{count}f", data, offset)) if count else []
    return values, offset + length


def decode(data: bytes) -> Dict[str, Any]:
    """Decode all 43 fields. Rejects trailing bytes."""
    return decode_with_trailer(data, allow_zero_fill=False)[0]


def decode_with_trailer(
    data: bytes, *, allow_zero_fill: bool = False
) -> Tuple[Dict[str, Any], int]:
    """Decode the struct; return it with the number of bytes it occupied.

    `allow_zero_fill` accepts the broker's or a slot's zero padding after the
    struct (and nothing else); without it a trailing byte is an error, because an
    encoder that emits more than 43 fields is not the ICD's encoder.
    """
    if not isinstance(data, (bytes, bytearray, memoryview)):
        raise TypeError("decode() takes bytes")
    data = bytes(data)
    state: Dict[str, Any] = {}
    offset = 0
    for field in table.FIELDS:
        if field.kind == table.U32:
            state[field.name], offset = _read_u32(data, offset, field.name)
        elif field.kind == table.F32:
            _need(data, offset, 4, field.name)
            state[field.name] = struct.unpack_from(">f", data, offset)[0]
            offset += 4
        elif field.kind == table.STR:
            state[field.name], offset = _read_string(data, offset, field.name)
        elif field.kind == table.F32_ARRAY:
            state[field.name], offset = _read_f32_array(data, offset, field.name)
        else:  # pragma: no cover
            raise KeyError(field.kind)
    trailer = data[offset:]
    if trailer:
        if not allow_zero_fill:
            raise DecodeError(f"{len(trailer)} trailing byte(s) after field 43", offset)
        if any(trailer):
            first = next(index for index, byte in enumerate(trailer) if byte)
            raise DecodeError("non-zero trailing byte", offset + first)
    return state, offset


# -------------------------------------------------------------------- samples


def sample(kind: int = table.KIND_PLAN, *, sequence: int = 1) -> Dict[str, Any]:
    """A complete message for one kind, in the ICD's units.

    The numbers are exact in binary32 (multiples of 1/8) so a comparison across
    languages is exact, and the string fields are short but non-empty where the
    kind uses them. Fields outside the kind's group are the ICD's defaults.
    """
    state = table.defaults()
    state.update(
        {
            "schema_major": table.SCHEMA_MAJOR,
            "schema_minor": table.SCHEMA_MINOR,
            "kind": kind,
            "sequence": sequence,
            "producer": "statePublisher",
            "publish_real_s": 1762742400,
            "publish_real_ns": 123456789,
            "publish_mono_s": 8123,
            "publish_mono_ns": 456789012,
        }
    )
    if kind == table.KIND_PLAN:
        state.update(
            {
                "plan_frame_index": 1234,
                "plan_capture_ms": 123400,
                "plan_production_mono_s": 8123,
                "plan_production_mono_ns": 400000000,
                "plan_reference": "0123456789abcdef/1234",
                "run_record": "0123456789abcdef",
                "plan_producer": "drivingAgent/inferPlan",
                "plan_sample_count": 64,
                "plan_horizon_s": 6.5,
                "plan_acceleration": [0.25 * index - 4.0 for index in range(64)],
                "plan_curvature": [0.5 * index for index in range(64)],
                "plan_x": [0.75 * index for index in range(64)],
                "plan_y": [-0.125 * index for index in range(64)],
            }
        )
    elif kind == table.KIND_VEHICLE_STATE:
        state.update(
            {
                "speed_kmh": 36.0,
                "longitudinal_acceleration": -1.25,
                "lateral_acceleration": 0.125,
                "yaw_rate_dps": -0.5,
                "sample_capture_ms": 123500,
                "sample_receipt_mono_s": 8124,
                "sample_receipt_mono_ns": 125000000,
            }
        )
    elif kind == table.KIND_HEALTH:
        state.update(
            {
                "mode": 3,
                "cause": 7,
                "mode_source": "actuationAdapter",
                "cause_since_mono_s": 8125,
                "cause_since_mono_ns": 0,
                "last_plan_frame_index": 1234,
                "last_plan_capture_ms": 123400,
                "step_capture_ms": 123500,
                "last_plan_production_mono_s": 8123,
                "last_plan_production_mono_ns": 400000000,
                "dropped_samples": 0,
            }
        )
    else:
        raise ValueError(f"kind {kind} is not 1, 2 or 3")
    return state


# ------------------------------------------------------------------------ CLI


def _hexdump(data: bytes, limit: int = 32) -> str:
    return " ".join(f"{byte:02x}" for byte in data[:limit]) + (" ..." if len(data) > limit else "")


def selftest() -> int:
    failures = 0
    for kind in (table.KIND_PLAN, table.KIND_VEHICLE_STATE, table.KIND_HEALTH):
        state = sample(kind, sequence=1)
        wire = encode(state)
        back, consumed = decode_with_trailer(wire)
        name = table.KIND_NAMES[kind]
        same = back == state
        print(
            f"{name:14s} {len(wire):5d} B  consumed {consumed:5d}  "
            f"first bytes {_hexdump(wire, 8)}  round trip {'ok' if same else 'DIFFERS'}"
        )
        failures += 0 if same and consumed == len(wire) else 1
    print("CODEC SELFTEST " + ("PASSED" if failures == 0 else f"FAILED ({failures})"))
    return 0 if failures == 0 else 1


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ICD v2 section 3 SOME/IP struct codec")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("selftest", help="round-trip one sample of each kind")

    sample_parser = sub.add_parser("sample", help="print a sample frame")
    sample_parser.add_argument("--kind", choices=("plan", "vehicle_state", "health"), default="plan")
    sample_parser.add_argument("--hex", action="store_true", help="hex instead of JSON")
    sample_parser.add_argument("--sequence", type=int, default=1)

    decode_parser = sub.add_parser("decode", help="decode a hex frame")
    decode_parser.add_argument("--hex", required=True, help="the struct bytes, hex, spaces allowed")
    decode_parser.add_argument("--allow-zero-fill", action="store_true")

    args = parser.parse_args(argv)
    if args.command == "selftest":
        return selftest()
    if args.command == "sample":
        kind = {"plan": table.KIND_PLAN, "vehicle_state": table.KIND_VEHICLE_STATE,
                "health": table.KIND_HEALTH}[args.kind]
        wire = encode(sample(kind, sequence=args.sequence))
        if args.hex:
            print(wire.hex())
        else:
            import json

            print(json.dumps(sample(kind, sequence=args.sequence), indent=1))
        return 0
    if args.command == "decode":
        raw = bytes.fromhex(args.hex.replace(" ", "").replace("\n", ""))
        try:
            state, consumed = decode_with_trailer(raw, allow_zero_fill=args.allow_zero_fill)
        except DecodeError as error:
            print(f"DECODE FAILED: {error}", file=sys.stderr)
            return 1
        import json

        print(json.dumps(state, indent=1))
        print(f"# consumed {consumed} of {len(raw)} bytes", file=sys.stderr)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
