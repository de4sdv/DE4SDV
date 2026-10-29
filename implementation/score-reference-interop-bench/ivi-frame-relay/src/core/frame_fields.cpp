#include "de4sdv_ivi_frame_relay/frame_fields.hpp"

namespace de4sdv::ivi_frame_relay {

namespace {

constexpr std::uint32_t kWireVarint = 0;
constexpr std::uint32_t kWireFixed64 = 1;
constexpr std::uint32_t kWireLengthDelimited = 2;
constexpr std::uint32_t kWireFixed32 = 5;
constexpr std::uint32_t kFieldSequence = 3;
constexpr std::uint32_t kFieldFrameTimestamp = 4;
constexpr std::size_t kMaxVarintBytes = 10;

// Reads one varint at position; advances position. Returns the error, kNone on success.
FrameReadError ReadVarint(const std::uint8_t* data, std::size_t size, std::size_t& position, std::uint64_t& value) {
  value = 0;
  for (std::size_t index = 0; index < kMaxVarintBytes; ++index) {
    if (position >= size) {
      return FrameReadError::kTruncatedVarint;
    }
    const std::uint8_t byte = data[position++];
    if (index == kMaxVarintBytes - 1U && byte > 0x01U) {
      return FrameReadError::kVarintTooLong;  // more than 64 bits
    }
    value |= static_cast<std::uint64_t>(byte & 0x7FU) << (7U * index);
    if ((byte & 0x80U) == 0U) {
      return FrameReadError::kNone;
    }
  }
  return FrameReadError::kVarintTooLong;
}

FrameReadResult Failure(FrameReadError error) {
  FrameReadResult result;
  result.error = error;
  return result;
}

}  // namespace

const char* ToText(PayloadCheck check) noexcept {
  switch (check) {
    case PayloadCheck::kOk:
      return "ok";
    case PayloadCheck::kTooShort:
      return "too_short";
    case PayloadCheck::kLengthPrefixMismatch:
      return "length_prefix_mismatch";
  }
  return "unknown";
}

std::uint32_t ReadLengthPrefix(const std::uint8_t* payload) noexcept {
  return static_cast<std::uint32_t>(payload[0]) | (static_cast<std::uint32_t>(payload[1]) << 8U) |
         (static_cast<std::uint32_t>(payload[2]) << 16U) | (static_cast<std::uint32_t>(payload[3]) << 24U);
}

PayloadCheck CheckLengthPrefix(const std::uint8_t* payload, std::size_t size) noexcept {
  if (payload == nullptr || size < kLengthPrefixBytes) {
    return PayloadCheck::kTooShort;
  }
  return static_cast<std::uint64_t>(ReadLengthPrefix(payload)) + kLengthPrefixBytes == size
             ? PayloadCheck::kOk
             : PayloadCheck::kLengthPrefixMismatch;
}

const char* ToText(FrameReadError error) noexcept {
  switch (error) {
    case FrameReadError::kNone:
      return "none";
    case FrameReadError::kTruncatedVarint:
      return "truncated_varint";
    case FrameReadError::kVarintTooLong:
      return "varint_too_long";
    case FrameReadError::kTruncatedField:
      return "truncated_field";
    case FrameReadError::kInvalidFieldNumber:
      return "invalid_field_number";
    case FrameReadError::kUnsupportedWireType:
      return "unsupported_wire_type";
    case FrameReadError::kSequenceWireType:
      return "sequence_wire_type";
    case FrameReadError::kTimestampWireType:
      return "timestamp_wire_type";
  }
  return "unknown";
}

FrameReadResult ReadFrameFields(const std::uint8_t* frame, std::size_t size) {
  FrameFields fields;
  std::size_t position = 0;
  while (position < size) {
    std::uint64_t tag = 0;
    const FrameReadError tag_error = ReadVarint(frame, size, position, tag);
    if (tag_error != FrameReadError::kNone) {
      return Failure(tag_error);
    }
    const std::uint64_t field_number = tag >> 3U;
    const auto wire_type = static_cast<std::uint32_t>(tag & 0x07U);
    if (field_number == 0U || field_number > 0x1FFFFFFFU) {
      return Failure(FrameReadError::kInvalidFieldNumber);
    }
    if (field_number == kFieldSequence && wire_type != kWireVarint) {
      return Failure(FrameReadError::kSequenceWireType);
    }
    if (field_number == kFieldFrameTimestamp && wire_type != kWireVarint) {
      return Failure(FrameReadError::kTimestampWireType);
    }
    switch (wire_type) {
      case kWireVarint: {
        std::uint64_t value = 0;
        const FrameReadError error = ReadVarint(frame, size, position, value);
        if (error != FrameReadError::kNone) {
          return Failure(error);
        }
        if (field_number == kFieldSequence) {
          fields.sequence = value;
        } else if (field_number == kFieldFrameTimestamp) {
          fields.frame_timestamp_ns = static_cast<std::int64_t>(value);  // int64: two's complement
        }
        break;
      }
      case kWireFixed64:
        if (size - position < 8U) {
          return Failure(FrameReadError::kTruncatedField);
        }
        position += 8U;
        break;
      case kWireLengthDelimited: {
        std::uint64_t length = 0;
        const FrameReadError error = ReadVarint(frame, size, position, length);
        if (error != FrameReadError::kNone) {
          return Failure(error);
        }
        if (length > size - position) {
          return Failure(FrameReadError::kTruncatedField);
        }
        position += static_cast<std::size_t>(length);
        break;
      }
      case kWireFixed32:
        if (size - position < 4U) {
          return Failure(FrameReadError::kTruncatedField);
        }
        position += 4U;
        break;
      default:
        return Failure(FrameReadError::kUnsupportedWireType);
    }
  }
  FrameReadResult result;
  result.fields = fields;
  return result;
}

}  // namespace de4sdv::ivi_frame_relay
