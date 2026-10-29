#include "de4sdv_ivi_frame_relay/broker_wrapper.hpp"

namespace de4sdv::ivi_frame_relay {

namespace {

constexpr std::size_t kMaxVarint32Bytes = 5;

// Reads a varint32 in its shortest form from data[position, end); advances
// position. False when it is truncated by end, longer than 5 bytes, above
// 2^32 - 1, or has a last byte of 0 after other bytes (not the shortest form).
bool ReadShortestVarint32(const std::uint8_t* data, std::size_t end, std::size_t& position,
                          std::uint32_t& value) noexcept {
  std::uint64_t result = 0;
  for (std::size_t index = 0; index < kMaxVarint32Bytes; ++index) {
    if (position >= end) {
      return false;
    }
    const std::uint8_t byte = data[position++];
    result |= static_cast<std::uint64_t>(byte & 0x7FU) << (7U * index);
    if ((byte & 0x80U) == 0U) {
      if (index > 0U && byte == 0U) {
        return false;
      }
      if (result > 0xFFFF'FFFFULL) {
        return false;
      }
      value = static_cast<std::uint32_t>(result);
      return true;
    }
  }
  return false;
}

WrapperParse Failure(WrapperCheck check) noexcept {
  WrapperParse parse;
  parse.check = check;
  return parse;
}

WrapperParse Failure(WrapperCheck check, std::size_t message_bytes) noexcept {
  WrapperParse parse = Failure(check);
  parse.message_known = true;
  parse.message_bytes = message_bytes;
  return parse;
}

}  // namespace

const char* ToText(WrapperCheck check) noexcept {
  switch (check) {
    case WrapperCheck::kOk:
      return "ok";
    case WrapperCheck::kOuterVarintInvalid:
      return "wrapper_outer_varint_invalid";
    case WrapperCheck::kOuterLengthExceedsSlot:
      return "wrapper_outer_length_exceeds_slot";
    case WrapperCheck::kFieldMissing:
      return "wrapper_field_missing";
    case WrapperCheck::kTagNotBytesField1:
      return "wrapper_tag_not_bytes_field_1";
    case WrapperCheck::kInnerVarintInvalid:
      return "wrapper_inner_varint_invalid";
    case WrapperCheck::kFieldExceedsMessage:
      return "wrapper_field_exceeds_message";
    case WrapperCheck::kBytesAfterField:
      return "wrapper_bytes_after_field";
    case WrapperCheck::kFillNotZero:
      return "wrapper_fill_not_zero";
  }
  return "unknown";
}

WrapperParse ParseBrokerWrapper(const std::uint8_t* slot, std::size_t slot_bytes) noexcept {
  std::size_t position = 0;
  std::uint32_t message_bytes = 0;
  if (slot == nullptr || !ReadShortestVarint32(slot, slot_bytes, position, message_bytes)) {
    return Failure(WrapperCheck::kOuterVarintInvalid);
  }
  if (message_bytes > slot_bytes - position) {
    return Failure(WrapperCheck::kOuterLengthExceedsSlot, message_bytes);
  }
  if (message_bytes == 0U) {
    return Failure(WrapperCheck::kFieldMissing, message_bytes);
  }
  const std::size_t message_end = position + message_bytes;
  if (slot[position] != kWrapperBytesFieldTag) {
    return Failure(WrapperCheck::kTagNotBytesField1, message_bytes);
  }
  ++position;
  std::uint32_t payload_bytes = 0;
  if (!ReadShortestVarint32(slot, message_end, position, payload_bytes)) {
    return Failure(WrapperCheck::kInnerVarintInvalid, message_bytes);
  }
  const std::size_t rest = message_end - position;
  if (payload_bytes > rest) {
    return Failure(WrapperCheck::kFieldExceedsMessage, message_bytes);
  }
  if (payload_bytes < rest) {
    return Failure(WrapperCheck::kBytesAfterField, message_bytes);
  }
  for (std::size_t index = message_end; index < slot_bytes; ++index) {
    if (slot[index] != 0U) {
      WrapperParse fill = Failure(WrapperCheck::kFillNotZero, message_bytes);
      fill.fill_offset = index;
      fill.fill_value = slot[index];
      return fill;
    }
  }
  WrapperParse parse;
  parse.message_known = true;
  parse.message_bytes = message_bytes;
  parse.payload_offset = position;
  parse.payload_bytes = payload_bytes;
  return parse;
}

}  // namespace de4sdv::ivi_frame_relay
