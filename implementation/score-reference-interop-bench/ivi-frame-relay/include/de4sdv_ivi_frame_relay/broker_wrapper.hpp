// Pure core of the DE4SDV IVI frame relay: the strict parse of the broker's
// wrapper in one Data Tunnel slot.
//
// The SOME/IP broker of the SDV Core VM maps the frame event with
// INTERPRET_AS_BYTES. It publishes each SOME/IP payload as a protobuf message
// with one bytes field, built by hand
// (some_ip/broker_agent_comms/src/translator/broker_translator.rs:248-262 at
// android17-release) into a zero-filled buffer of the publication's message
// size (the same file, 266-279):
//
//   [outer varint L][0x0A][inner varint n][n payload bytes][zero fill]
//
// with L = 1 + size(n) + n, and each varint written in its shortest form.
// Data Tunnel carries the whole slot, and readAvailableMessages gives the
// relay slots of messageSizeBytes each.
//
// The parse is strict (owner decision of 2026-10-29), and the model states
// it for a slot of the publication's fixed size (iviFrameRelay of
// middleware_score_physical_software_realization.sysml):
// - the outer varint is a valid varint32 in its shortest form; it gives the
//   length L of the message that follows, and the message must fit in the
//   slot;
// - the message holds exactly one field: field 1 of wire type 2, tag 0x0A;
// - the length of that field, also a shortest varint32, equals the rest of
//   the message: no other byte follows the field in the message, and the
//   field does not run past it;
// - every byte of the slot after the message is zero, as the broker writes
//   it.
// Anything else is malformed. The relay drops the slot with the reason of
// the first check that fails. A fill drop logs L, the offset of the first
// byte that is not zero and its value, because no run has yet recorded the
// bytes of a slot after its message in the IVI VM. Only then does the relay
// check the payload's own length prefix (frame_fields.hpp).

#ifndef DE4SDV_IVI_FRAME_RELAY_BROKER_WRAPPER_HPP
#define DE4SDV_IVI_FRAME_RELAY_BROKER_WRAPPER_HPP

#include <cstddef>
#include <cstdint>

namespace de4sdv::ivi_frame_relay {

// The tag of field 1 with wire type 2 (length-delimited).
constexpr std::uint8_t kWrapperBytesFieldTag = 0x0A;

enum class WrapperCheck : std::uint8_t {
  kOk,
  kOuterVarintInvalid,      // truncated, longer than 5 bytes, above 2^32 - 1, or not in its shortest form
  kOuterLengthExceedsSlot,  // the message that L gives does not fit in the slot
  kFieldMissing,            // L is 0: the message holds no field
  kTagNotBytesField1,       // the first byte of the message is not 0x0A
  kInnerVarintInvalid,      // the field length is truncated by the message end, too long, too large, or not shortest
  kFieldExceedsMessage,     // the field length is more than the rest of the message
  kBytesAfterField,         // the field length is less than the rest of the message: other bytes follow
  kFillNotZero,             // a byte of the slot after the message is not zero
};

// The drop reason of each check, for example "wrapper_fill_not_zero".
const char* ToText(WrapperCheck check) noexcept;

struct WrapperParse {
  WrapperCheck check{WrapperCheck::kOk};
  // L, once the outer varint is read; also on a later failure, for the drop line.
  bool message_known{false};
  std::size_t message_bytes{0};
  std::size_t payload_offset{0};  // from the start of the slot
  std::size_t payload_bytes{0};   // n
  // kFillNotZero: the first byte after the message that is not zero.
  std::size_t fill_offset{0};
  std::uint8_t fill_value{0};
};

WrapperParse ParseBrokerWrapper(const std::uint8_t* slot, std::size_t slot_bytes) noexcept;

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_BROKER_WRAPPER_HPP
