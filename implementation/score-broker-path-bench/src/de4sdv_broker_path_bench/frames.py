"""AEBS signal frames on a length-delimited stream, and their wire decoding.

The INC-AEBS-010 frame server sends each frame as a 4-byte little-endian
length prefix and the frame (de4sdv_aebs_010_bridge/source_adapter.py:295).
The IVI frame relay serves the same stream to the ingress. A frame is a
VisualizationFrame of interface/aebs_visualization.proto of the INC-AEBS-010
bench; this module decodes the protobuf wire format itself, so the
evaluators need no generated code.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

from .pcap import TcpStream

#: The largest frame the path carries: a sample of PreSerializedData<2048>
#: holds the 4-byte prefix and the frame.
MAX_FRAME_BYTES = 2044

FIELD_NAMES = {
    1: "schema_major",
    2: "schema_minor",
    3: "sequence",
    4: "frame_timestamp_ns",
    5: "bridge_receipt_timestamp_ns",
    6: "source_identity",
    7: "rss_distance",
    8: "native_intervention",
    9: "target_range",
    10: "target_bearing",
    11: "de4sdv_warning_request",
    12: "de4sdv_braking_request",
    13: "de4sdv_lifecycle_state",
    14: "target_points",
    15: "ego_speed",
}
#: The FieldValue fields of a frame (each carries a source kind).
FIELD_VALUE_FIELDS = (7, 8, 9, 10, 11, 12, 13, 15)
SOURCE_KINDS = {0: "unspecified", 1: "nativeAutowareAEB", 2: "de4sdvAebsCoordinator", 3: "displayDerived"}
NATIVE = 1
#: The source kind that the frame assembler gives each field
#: (de4sdv_aebs_010_bridge/frame_assembler.py).
ASSEMBLER_SOURCE_KIND = {7: 1, 8: 1, 9: 3, 10: 3, 15: 3, 11: 2, 12: 2, 13: 2}
#: Fields that carry coordinator output or a display-derived value: REQ-MW-015
#: forbids that one of them arrives marked as native Autoware AEB output.
NOT_NATIVE_FIELDS = (9, 10, 11, 12, 13, 15)

STAGES = ("MONITORING", "WARNING", "INTERVENTION", "RELEASED")


class WireError(ValueError):
    """The bytes are not a well-formed protobuf message."""


def read_varint(buffer: bytes, index: int) -> tuple[int, int]:
    value = 0
    shift = 0
    while True:
        if index >= len(buffer):
            raise WireError("truncated varint")
        byte = buffer[index]
        index += 1
        value |= (byte & 0x7F) << shift
        if not byte & 0x80:
            return value, index
        shift += 7
        if shift > 63:
            raise WireError("varint longer than 10 bytes")


def decode_fields(buffer: bytes) -> list[tuple[int, int, object]]:
    """(field number, wire type, value) of each field, in wire order."""
    fields: list[tuple[int, int, object]] = []
    index = 0
    while index < len(buffer):
        key, index = read_varint(buffer, index)
        number, wire = key >> 3, key & 7
        if number == 0:
            raise WireError("field number 0")
        if wire == 0:
            value, index = read_varint(buffer, index)
        elif wire == 1:
            if index + 8 > len(buffer):
                raise WireError("truncated fixed64")
            value = buffer[index:index + 8]
            index += 8
        elif wire == 2:
            length, index = read_varint(buffer, index)
            if index + length > len(buffer):
                raise WireError("length-delimited field runs past the end")
            value = bytes(buffer[index:index + length])
            index += length
        elif wire == 5:
            if index + 4 > len(buffer):
                raise WireError("truncated fixed32")
            value = buffer[index:index + 4]
            index += 4
        else:
            raise WireError(f"unsupported wire type {wire}")
        fields.append((number, wire, value))
    return fields


def to_int64(value: int) -> int:
    return value - (1 << 64) if value >= 1 << 63 else value


@dataclass(frozen=True)
class FrameFacts:
    sequence: int | None
    frame_timestamp_ns: int | None
    schema_major: int | None
    source_kinds: dict[int, int] = field(default_factory=dict)
    bools: dict[int, bool] = field(default_factory=dict)
    enums: dict[int, str] = field(default_factory=dict)


def frame_facts(payload: bytes) -> FrameFacts:
    sequence = timestamp = major = None
    kinds: dict[int, int] = {}
    bools: dict[int, bool] = {}
    enums: dict[int, str] = {}
    for number, wire, value in decode_fields(payload):
        if number == 1 and wire == 0:
            major = int(value)
        elif number == 3 and wire == 0:
            sequence = int(value)
        elif number == 4 and wire == 0:
            timestamp = to_int64(int(value))
        elif number in FIELD_VALUE_FIELDS and wire == 2:
            for sub_number, sub_wire, sub_value in decode_fields(value):  # type: ignore[arg-type]
                if sub_number == 1 and sub_wire == 0:
                    kinds[number] = int(sub_value)
                elif sub_number == 6 and sub_wire == 0:
                    bools[number] = bool(sub_value)
                elif sub_number == 7 and sub_wire == 2:
                    enums[number] = bytes(sub_value).decode("utf-8", "replace")  # type: ignore[arg-type]
    return FrameFacts(sequence, timestamp, major, kinds, bools, enums)


def stage(facts: FrameFacts) -> str:
    """The presentation stage of a frame, by the precedence of the app's reducer.

    VisualizationStateReducer.onFrame of the INC-AEBS-010 app: released wins,
    then the native intervention or the braking request, then the warning.
    """
    if facts.enums.get(13) == "released_verified_stop":
        return "RELEASED"
    if facts.bools.get(8) or facts.bools.get(12):
        return "INTERVENTION"
    if facts.bools.get(11):
        return "WARNING"
    return "MONITORING"


def field_tree(payload: bytes) -> dict[str, list[object]]:
    """A comparable tree of a frame: field name to its values, FieldValues and points decoded."""
    tree: dict[str, list[object]] = {}
    for number, wire, value in decode_fields(payload):
        name = FIELD_NAMES.get(number, f"field_{number}")
        if number in FIELD_VALUE_FIELDS and wire == 2:
            item: object = {f"f{sub}:{w}": (v.hex() if isinstance(v, (bytes, bytearray)) else v)
                            for sub, w, v in decode_fields(value)}  # type: ignore[arg-type]
        elif isinstance(value, (bytes, bytearray)):
            item = value.hex()
        else:
            item = value
        tree.setdefault(name, []).append(item)
    return tree


def diff_trees(produced: dict[str, list[object]], received: dict[str, list[object]]) -> list[str]:
    differences = []
    for name in sorted(set(produced) | set(received)):
        if produced.get(name) != received.get(name):
            differences.append(f"{name}: produced {produced.get(name)!r}, received {received.get(name)!r}")
    return differences


@dataclass(frozen=True)
class StreamFrame:
    """One frame of a stream: its offset, its bytes and the time its last byte arrived."""

    offset: int
    payload: bytes
    delivered_ns: int
    connection: int  # index of the TCP connection in the capture


def _plausible_header(data: bytes | bytearray, index: int, max_frame: int) -> int | None:
    if index + 6 > len(data):
        return None
    length = struct.unpack("<I", data[index:index + 4])[0]
    if not 2 <= length <= max_frame or data[index + 4:index + 6] != b"\x08\x01":
        return None
    return length


def resync(data: bytes | bytearray, start: int, max_frame: int = MAX_FRAME_BYTES) -> int | None:
    """The first offset at or after ``start`` where two well-formed frames follow each other.

    A frame starts with schema_major = 1 (bytes 08 01). The check also decodes
    the frame, so a match inside a frame is unlikely; the second frame (or the
    end of the stream) confirms the boundary.
    """
    for index in range(start, max(start, len(data) - 6)):
        length = _plausible_header(data, index, max_frame)
        if length is None or index + 4 + length > len(data):
            continue
        try:
            facts = frame_facts(bytes(data[index + 4:index + 4 + length]))
        except WireError:
            continue
        if facts.sequence is None:
            continue
        following = index + 4 + length
        if following == len(data) or _plausible_header(data, following, max_frame) is not None:
            return index
    return None


def split_frames(stream: TcpStream, connection: int,
                 max_frame: int = MAX_FRAME_BYTES) -> tuple[list[StreamFrame], list[str]]:
    """The frames of one connection, and the problems met on the way."""
    data = stream.data
    problems: list[str] = []
    gap_offsets = sorted(offset for offset, _length in stream.gaps)
    index = 0
    if stream.mid_stream_start:
        found = resync(data, 0, max_frame)
        if found is None:
            return [], (["no frame boundary found in a stream joined mid-way"] if data else [])
        if found:
            problems.append(f"stream joined mid-way: skipped {found} bytes before the first frame")
        index = found
    frames: list[StreamFrame] = []
    while index + 4 <= len(data):
        length = struct.unpack("<I", data[index:index + 4])[0]
        end = index + 4 + length
        # A frame whose bytes span a capture discontinuity cannot be read. A
        # frame that starts exactly at a gap boundary is intact (the gap is
        # before it), so the check is strict and the resync starts at the gap
        # offset, not one byte past the bad prefix, so the frame after the gap
        # is not lost (a frame at a gap is unknown, not a missing delivery).
        spanned = [gap for gap in gap_offsets if index < gap < end]
        if not 1 <= length <= max_frame or spanned:
            if spanned:
                reason = "a capture gap"
                resync_from = spanned[0]
            else:
                reason = f"length prefix {length}"
                resync_from = index + 1
            found = resync(data, resync_from, max_frame)
            problems.append(f"framing lost at offset {index} ({reason}); "
                            + (f"resynchronized at {found}" if found is not None else "no resync"))
            if found is None:
                return frames, problems
            index = found
            continue
        if end > len(data):
            problems.append(f"incomplete last frame at offset {index} ({len(data) - index} of {4 + length} bytes)")
            break
        delivered = stream.delivery_ns(end)
        if delivered is None:
            problems.append(f"no delivery time for the frame at offset {index}")
            break
        frames.append(StreamFrame(index, bytes(data[index + 4:end]), delivered, connection))
        index = end
    return frames, problems
