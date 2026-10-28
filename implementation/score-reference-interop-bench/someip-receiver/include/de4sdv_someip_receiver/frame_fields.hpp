// Pure core of the DE4SDV minimal SOME/IP receiver: the checks of one frame
// event payload.
//
// The AutowareToSCORE adapter sends each frame of the INC-AEBS-010 frame
// assembler unchanged with its 4-byte little-endian length prefix as one
// sample, so a payload is prefix plus frame. The receiver checks that the
// prefix counts the bytes after it, and reads two fields of the frame, a
// VisualizationFrame of interface/aebs_visualization.proto of the
// visualization bench: sequence (field 3, uint64) and frame_timestamp_ns
// (field 4, int64). It forwards the payload unchanged.
//
// The reader is a minimal protobuf wire reader, not libprotobuf: it walks
// the top-level fields, skips all others without decoding them, and fails
// on a malformed top-level encoding or on field 3 or 4 with a wrong wire
// type. A field that is absent reads as 0, as in proto3; when a field
// occurs twice, the last value counts. The HMI ingress decodes and checks
// the whole frame later.

#ifndef DE4SDV_SOMEIP_RECEIVER_FRAME_FIELDS_HPP
#define DE4SDV_SOMEIP_RECEIVER_FRAME_FIELDS_HPP

#include <cstddef>
#include <cstdint>
#include <optional>

namespace de4sdv::someip_receiver {

constexpr std::size_t kLengthPrefixBytes = 4;

enum class PayloadCheck : std::uint8_t {
  kOk,
  kTooShort,             // fewer than 4 bytes
  kLengthPrefixMismatch, // the prefix does not count the bytes after it
};

const char* ToText(PayloadCheck check) noexcept;

PayloadCheck CheckLengthPrefix(const std::uint8_t* payload, std::size_t size) noexcept;
std::uint32_t ReadLengthPrefix(const std::uint8_t* payload) noexcept;

struct FrameFields {
  std::uint64_t sequence{0};
  std::int64_t frame_timestamp_ns{0};
};

enum class FrameReadError : std::uint8_t {
  kNone,
  kTruncatedVarint,
  kVarintTooLong,
  kTruncatedField,
  kInvalidFieldNumber,
  kUnsupportedWireType,  // groups and the wire types 6 and 7
  kSequenceWireType,
  kTimestampWireType,
};

const char* ToText(FrameReadError error) noexcept;

struct FrameReadResult {
  std::optional<FrameFields> fields;
  FrameReadError error{FrameReadError::kNone};
};

// Reads the frame bytes after the length prefix.
FrameReadResult ReadFrameFields(const std::uint8_t* frame, std::size_t size);

}  // namespace de4sdv::someip_receiver

#endif  // DE4SDV_SOMEIP_RECEIVER_FRAME_FIELDS_HPP
