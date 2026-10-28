"""Minimal VisualizationFrame encoder and reader of the bench (no protobuf library).

The frames that the bench's frame source sends are VisualizationFrame
messages of interface/aebs_visualization.proto of the visualization bench
with five fields: schema_major (1) and schema_minor (2), both 1, sequence (3),
frame_timestamp_ns (4), bridge_receipt_timestamp_ns (5) and source_identity
(6). The encoder writes the fields in field-number order and omits default
values, as the protobuf runtime does, so the bytes equal the runtime's
bytes for the same values. With a size, it pads source_identity so that the
frame has exactly that size.

The reader takes sequence and frame_timestamp_ns from any frame. It is a
second, independent implementation of the receiver's wire reader: it walks
the top-level fields, skips all others, and rejects a malformed top-level
encoding and field 3 or 4 with a wrong wire type. An absent field reads as 0.
"""

from __future__ import annotations

import struct
from typing import NamedTuple

LENGTH_PREFIX_BYTES = 4
_WIRE_VARINT = 0
_WIRE_FIXED64 = 1
_WIRE_LENGTH_DELIMITED = 2
_WIRE_FIXED32 = 5
_FIELD_SEQUENCE = 3
_FIELD_TIMESTAMP = 4
_MAX_VARINT_BYTES = 10


class FrameFields(NamedTuple):
    sequence: int
    frame_timestamp_ns: int


def _varint(value: int) -> bytes:
    if value < 0:
        value &= (1 << 64) - 1  # int64: two's complement in ten bytes
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def _tag(field: int, wire_type: int) -> bytes:
    return _varint((field << 3) | wire_type)


def _scalar(field: int, value: int) -> bytes:
    return _tag(field, _WIRE_VARINT) + _varint(value) if value else b""


def encode_frame(sequence: int, frame_timestamp_ns: int, *, bridge_receipt_timestamp_ns: int = 0,
                 source_identity: str = "", size: int | None = None) -> bytes:
    """One VisualizationFrame; with size, exactly size bytes or ValueError."""
    base = (_scalar(1, 1) + _scalar(2, 1) + _scalar(_FIELD_SEQUENCE, sequence)
            + _scalar(_FIELD_TIMESTAMP, frame_timestamp_ns) + _scalar(5, bridge_receipt_timestamp_ns))
    identity = source_identity.encode("utf-8")
    if size is None:
        if not identity:
            return base
        return base + _tag(6, _WIRE_LENGTH_DELIMITED) + _varint(len(identity)) + identity
    room = size - len(base) - 1  # one tag byte for field 6
    for length_bytes in (1, 2, 3):
        string_length = room - length_bytes
        if string_length >= len(identity) and len(_varint(string_length)) == length_bytes:
            filler = bytes(ord("a") + (index % 26) for index in range(string_length - len(identity)))
            frame = base + _tag(6, _WIRE_LENGTH_DELIMITED) + _varint(string_length) + identity + filler
            assert len(frame) == size
            return frame
    raise ValueError(f"no VisualizationFrame of {size} bytes holds these fields")


def length_prefixed(frame: bytes) -> bytes:
    """The stream form of the INC-AEBS-010 frame server: 4-byte little-endian length, then the frame."""
    return struct.pack("<I", len(frame)) + frame


def _read_varint(data: bytes, position: int) -> tuple[int, int]:
    value = 0
    for index in range(_MAX_VARINT_BYTES):
        if position >= len(data):
            raise ValueError("truncated varint")
        byte = data[position]
        position += 1
        if index == _MAX_VARINT_BYTES - 1 and byte > 0x01:
            raise ValueError("varint too long")
        value |= (byte & 0x7F) << (7 * index)
        if not byte & 0x80:
            return value, position
    raise ValueError("varint too long")


def read_fields(frame: bytes) -> FrameFields:
    """sequence and frame_timestamp_ns of a frame; ValueError when malformed."""
    sequence = 0
    timestamp = 0
    position = 0
    while position < len(frame):
        tag, position = _read_varint(frame, position)
        field, wire_type = tag >> 3, tag & 0x07
        if field == 0 or field > 0x1FFFFFFF:
            raise ValueError("invalid field number")
        if field in (_FIELD_SEQUENCE, _FIELD_TIMESTAMP) and wire_type != _WIRE_VARINT:
            raise ValueError(f"wrong wire type {wire_type} of field {field}")
        if wire_type == _WIRE_VARINT:
            value, position = _read_varint(frame, position)
            if field == _FIELD_SEQUENCE:
                sequence = value
            elif field == _FIELD_TIMESTAMP:
                timestamp = value - (1 << 64) if value >= (1 << 63) else value
        elif wire_type == _WIRE_FIXED64:
            if len(frame) - position < 8:
                raise ValueError("truncated field")
            position += 8
        elif wire_type == _WIRE_LENGTH_DELIMITED:
            length, position = _read_varint(frame, position)
            if length > len(frame) - position:
                raise ValueError("truncated field")
            position += length
        elif wire_type == _WIRE_FIXED32:
            if len(frame) - position < 4:
                raise ValueError("truncated field")
            position += 4
        else:
            raise ValueError(f"unsupported wire type {wire_type}")
    return FrameFields(sequence, timestamp)


def read_payload(payload: bytes) -> tuple[bool, FrameFields | None]:
    """(True, fields) for a payload whose prefix counts the frame bytes and whose frame reads."""
    if len(payload) < LENGTH_PREFIX_BYTES:
        return False, None
    if struct.unpack("<I", payload[:LENGTH_PREFIX_BYTES])[0] != len(payload) - LENGTH_PREFIX_BYTES:
        return False, None
    try:
        return True, read_fields(payload[LENGTH_PREFIX_BYTES:])
    except ValueError:
        return False, None
