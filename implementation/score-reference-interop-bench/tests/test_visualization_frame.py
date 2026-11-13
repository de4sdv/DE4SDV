"""Tests of the minimal VisualizationFrame encoder and reader of the bench.

The bench's frame source encodes frames with the schema identity, sequence,
frame_timestamp_ns, bridge_receipt_timestamp_ns and source_identity fields
only; the evaluators read sequence and frame_timestamp_ns back. The golden
frames were encoded by the protobuf runtime from the message definition of
interface/aebs_visualization.proto of the visualization bench
(ivi-frame-relay/test/fixtures/README.md), so equal bytes show that the
encoder writes what protobuf writes for the same values.
"""

from pathlib import Path
import sys

import pytest

BENCH = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BENCH / "src"))

from de4sdv_score_bench.visualization_frame import (  # noqa: E402
    FrameFields,
    encode_frame,
    length_prefixed,
    read_fields,
    read_payload,
)

FIXTURES = BENCH / "ivi-frame-relay" / "test" / "fixtures"


def golden(name: str) -> bytes:
    return bytes.fromhex((FIXTURES / f"{name}.hex").read_text().strip())


def test_minimal_frame_equals_the_protobuf_runtime():
    frame = encode_frame(42, 1793116443934013818, bridge_receipt_timestamp_ns=1793116443934113818,
                         source_identity="de4sdv_aebs_010_bridge")
    assert frame == golden("visualization_frame_minimal")


def test_large_sequence_and_negative_timestamp_equal_the_protobuf_runtime():
    frame = encode_frame((1 << 63) + 5, -1, source_identity="edge")
    assert frame == golden("visualization_frame_large_sequence_negative_timestamp")


def test_default_values_are_not_written_as_in_proto3():
    assert encode_frame(0, 0, source_identity="defaults") == golden("visualization_frame_default_sequence_and_timestamp")


@pytest.mark.parametrize("name, sequence, timestamp", [
    ("visualization_frame_minimal", 42, 1793116443934013818),
    ("visualization_frame_full", 1234567, 1793116449339467540),
    ("visualization_frame_large_sequence_negative_timestamp", (1 << 63) + 5, -1),
    ("visualization_frame_default_sequence_and_timestamp", 0, 0),
])
def test_reader_reads_the_golden_frames(name, sequence, timestamp):
    assert read_fields(golden(name)) == FrameFields(sequence, timestamp)


@pytest.mark.parametrize("size", [50, 64, 127, 128, 129, 130, 200, 512, 800, 1100, 2043, 2044])
def test_frame_is_padded_to_the_exact_size(size):
    frame = encode_frame(17, 1793116443934013818, bridge_receipt_timestamp_ns=1793116443934013818 + 5,
                         source_identity="de4sdv-ci-frame-source", size=size)
    assert len(frame) == size
    assert read_fields(frame) == FrameFields(17, 1793116443934013818)


@pytest.mark.parametrize("size", [10, 49, 156])
def test_impossible_size_is_rejected(size):
    # 49: the source identity does not fit; 156: the string length needs one
    # varint byte more exactly at the size (127 + 1 and 128 + 2 bytes).
    with pytest.raises(ValueError):
        encode_frame(17, 1793116443934013818, bridge_receipt_timestamp_ns=1793116443934013818 + 5,
                     source_identity="de4sdv-ci-frame-source", size=size)


@pytest.mark.parametrize("broken, message", [
    (b"\x18\x81", "truncated varint"),
    (b"\x18" + b"\xff" * 10 + b"\x01", "varint too long"),
    (b"\x32\x05ab", "truncated field"),
    (b"\x00\x01", "field number 0"),
    (b"\x1a\x01\x00", "sequence wire type"),
    (b"\x21" + b"\x00" * 8, "timestamp wire type"),
    (b"\x83\x01\x00", "wire type 3"),
])
def test_reader_rejects_malformed_frames(broken, message):
    with pytest.raises(ValueError):
        read_fields(broken)


def test_last_occurrence_counts():
    assert read_fields(b"\x18\x07\x18\x09\x20\x05").sequence == 9


def test_payload_is_prefix_and_frame():
    frame = encode_frame(3, 99, size=64)
    payload = length_prefixed(frame)
    assert payload[:4] == (64).to_bytes(4, "little")
    assert read_payload(payload) == (True, FrameFields(3, 99))
    assert read_payload(payload + b"\x00")[0] is False
    assert read_payload(b"\x01\x00")[0] is False
