// Unit tests of the strict parse of the broker's wrapper: three real messages
// of the feasibility run in slots built as the broker builds them, and one
// case per drop reason.

#include <gtest/gtest.h>

#include <algorithm>
#include <cstdint>
#include <string>
#include <vector>

#include "de4sdv_ivi_frame_relay/broker_wrapper.hpp"
#include "de4sdv_ivi_frame_relay/frame_fields.hpp"
#include "fake_gateway_client.hpp"
#include "fixture_loader.hpp"

namespace {

using de4sdv::ivi_frame_relay::CheckLengthPrefix;
using de4sdv::ivi_frame_relay::ParseBrokerWrapper;
using de4sdv::ivi_frame_relay::PayloadCheck;
using de4sdv::ivi_frame_relay::ToText;
using de4sdv::ivi_frame_relay::WrapperCheck;
using de4sdv::ivi_frame_relay::WrapperParse;
using de4sdv::ivi_frame_relay::test::Bytes;
using de4sdv::ivi_frame_relay::test::kSlotBytes;
using de4sdv::ivi_frame_relay::test::LoadHexFixture;
using de4sdv::ivi_frame_relay::test::PutVarint;
using de4sdv::ivi_frame_relay::test::WrapLikeBroker;

// The slot of a recorded message: its outer varint, the message, the zero fill.
Bytes SlotOf(const Bytes& message, std::size_t slot_bytes = kSlotBytes) {
  Bytes slot;
  PutVarint(slot, message.size());
  slot.insert(slot.end(), message.begin(), message.end());
  slot.resize(slot_bytes, 0U);
  return slot;
}

WrapperCheck Check(const Bytes& slot) { return ParseBrokerWrapper(slot.data(), slot.size()).check; }

class RecordedMessage : public ::testing::TestWithParam<const char*> {};

TEST_P(RecordedMessage, ParsesAndKeepsThePayload) {
  const Bytes message = LoadHexFixture(GetParam());
  const Bytes slot = SlotOf(message);
  const WrapperParse parse = ParseBrokerWrapper(slot.data(), slot.size());
  ASSERT_EQ(parse.check, WrapperCheck::kOk) << ToText(parse.check);
  EXPECT_EQ(parse.message_bytes, message.size());
  const Bytes payload(slot.begin() + static_cast<std::ptrdiff_t>(parse.payload_offset),
                      slot.begin() + static_cast<std::ptrdiff_t>(parse.payload_offset + parse.payload_bytes));
  // The payload is the end of the message: tag, inner varint, payload.
  EXPECT_EQ(payload, Bytes(message.end() - static_cast<std::ptrdiff_t>(payload.size()), message.end()));
  EXPECT_EQ(CheckLengthPrefix(payload.data(), payload.size()), PayloadCheck::kOk);
}

TEST_P(RecordedMessage, TheTestWrapperBuildsTheSameMessage) {
  const Bytes message = LoadHexFixture(GetParam());
  const Bytes slot = SlotOf(message);
  const WrapperParse parse = ParseBrokerWrapper(slot.data(), slot.size());
  ASSERT_EQ(parse.check, WrapperCheck::kOk);
  const Bytes payload(slot.begin() + static_cast<std::ptrdiff_t>(parse.payload_offset),
                      slot.begin() + static_cast<std::ptrdiff_t>(parse.payload_offset + parse.payload_bytes));
  EXPECT_EQ(WrapLikeBroker(payload), slot);
}

INSTANTIATE_TEST_SUITE_P(FeasibilityRun, RecordedMessage,
                         ::testing::Values("broker_message_payload_68", "broker_message_payload_516",
                                           "broker_message_payload_2048"));

TEST(BrokerWrapper, LargestPayloadHasTwoByteVarints) {
  const Bytes message = LoadHexFixture("broker_message_payload_2048");
  ASSERT_EQ(message.size(), 2051U);
  const Bytes slot = SlotOf(message);
  EXPECT_EQ(slot[0], 0x83);  // 2051 = 0x803: 0x83 0x10
  EXPECT_EQ(slot[1], 0x10);
  EXPECT_EQ(slot[2], 0x0A);
  const WrapperParse parse = ParseBrokerWrapper(slot.data(), slot.size());
  ASSERT_EQ(parse.check, WrapperCheck::kOk);
  EXPECT_EQ(parse.payload_offset, 5U);
  EXPECT_EQ(parse.payload_bytes, 2048U);
}

TEST(BrokerWrapper, MessageThatFillsTheSlotHasNoFill) {
  const Bytes payload(100, 0x11);
  const Bytes slot = WrapLikeBroker(payload, 0);  // no fill
  ASSERT_EQ(slot.size(), 1U + 1U + 1U + 100U);
  EXPECT_EQ(Check(slot), WrapperCheck::kOk);
}

TEST(BrokerWrapper, OuterVarintMustBeValidAndShortest) {
  EXPECT_EQ(ParseBrokerWrapper(nullptr, 0).check, WrapperCheck::kOuterVarintInvalid);
  EXPECT_EQ(Check(Bytes{}), WrapperCheck::kOuterVarintInvalid);
  EXPECT_EQ(Check(Bytes{0x80}), WrapperCheck::kOuterVarintInvalid);                     // truncated
  EXPECT_EQ(Check(Bytes{0x80, 0x80, 0x80, 0x80, 0x80, 0x01}), WrapperCheck::kOuterVarintInvalid);  // 6 bytes
  EXPECT_EQ(Check(Bytes{0xFF, 0xFF, 0xFF, 0xFF, 0x1F}), WrapperCheck::kOuterVarintInvalid);  // above 2^32 - 1
  Bytes not_shortest = WrapLikeBroker(Bytes(4, 0x00), 64);
  // The length 6 as 0x86 0x00: the same value, not in its shortest form.
  not_shortest.insert(not_shortest.begin(), 0x00);
  not_shortest[0] = static_cast<std::uint8_t>(not_shortest[1] | 0x80U);
  not_shortest[1] = 0x00;
  EXPECT_EQ(Check(not_shortest), WrapperCheck::kOuterVarintInvalid);
}

TEST(BrokerWrapper, MessageMustFitTheSlot) {
  Bytes slot = WrapLikeBroker(Bytes(20, 0x01), 0);
  slot[0] = static_cast<std::uint8_t>(slot[0] + 1U);  // one byte more than the slot holds
  EXPECT_EQ(Check(slot), WrapperCheck::kOuterLengthExceedsSlot);
}

TEST(BrokerWrapper, EmptyMessageHasNoField) {
  Bytes slot(16, 0x00);  // L = 0, then zeros
  EXPECT_EQ(Check(slot), WrapperCheck::kFieldMissing);
}

TEST(BrokerWrapper, OnlyBytesField1IsTheWrapper) {
  Bytes slot = WrapLikeBroker(Bytes(8, 0x01), 32);
  slot[1] = 0x12;  // field 2, wire type 2
  EXPECT_EQ(Check(slot), WrapperCheck::kTagNotBytesField1);
  slot[1] = 0x08;  // field 1, wire type 0
  EXPECT_EQ(Check(slot), WrapperCheck::kTagNotBytesField1);
  slot[1] = 0x0B;  // field 1, wire type 3
  EXPECT_EQ(Check(slot), WrapperCheck::kTagNotBytesField1);
}

TEST(BrokerWrapper, InnerVarintMustBeValidAndShortestInsideTheMessage) {
  // L = 2: tag and one byte 0x80 that the message end truncates.
  EXPECT_EQ(Check(Bytes{0x02, 0x0A, 0x80, 0x01, 0x00}), WrapperCheck::kInnerVarintInvalid);
  // L = 4: an inner length 1 written as 0x81 0x00, then one byte.
  EXPECT_EQ(Check(Bytes{0x04, 0x0A, 0x81, 0x00, 0x55}), WrapperCheck::kInnerVarintInvalid);
}

TEST(BrokerWrapper, FieldLengthMustEqualTheRestOfTheMessage) {
  // L = 5: tag, n = 4, but only 3 bytes follow in the message.
  EXPECT_EQ(Check(Bytes{0x05, 0x0A, 0x04, 0x01, 0x02, 0x03, 0x00}), WrapperCheck::kFieldExceedsMessage);
  // L = 6: tag, n = 2, two bytes, and a second field 0x10 0x01 in the message.
  EXPECT_EQ(Check(Bytes{0x06, 0x0A, 0x02, 0x01, 0x02, 0x10, 0x01, 0x00}), WrapperCheck::kBytesAfterField);
}

TEST(BrokerWrapper, FillAfterTheMessageMustBeZero) {
  Bytes slot = WrapLikeBroker(Bytes(8, 0x01), 64);
  EXPECT_EQ(Check(slot), WrapperCheck::kOk);
  slot.back() = 0x01;
  EXPECT_EQ(Check(slot), WrapperCheck::kFillNotZero);
}

TEST(BrokerWrapper, ShiftedLengthsThatAgreeStillLeavePayloadBytesInTheFill) {
  // Outer and inner length both 4 too small: the message ends inside the
  // payload, and the rest of the payload is in the fill.
  const Bytes payload(40, 0x42);
  Bytes slot = WrapLikeBroker(payload, 128);
  slot[0] = static_cast<std::uint8_t>(slot[0] - 4U);
  slot[2] = static_cast<std::uint8_t>(slot[2] - 4U);
  EXPECT_EQ(Check(slot), WrapperCheck::kFillNotZero);
}

TEST(BrokerWrapper, EachCheckHasItsOwnReason) {
  const std::vector<WrapperCheck> checks{
      WrapperCheck::kOuterVarintInvalid,  WrapperCheck::kOuterLengthExceedsSlot, WrapperCheck::kFieldMissing,
      WrapperCheck::kTagNotBytesField1,   WrapperCheck::kInnerVarintInvalid,     WrapperCheck::kFieldExceedsMessage,
      WrapperCheck::kBytesAfterField,     WrapperCheck::kFillNotZero};
  std::vector<std::string> names;
  for (const WrapperCheck check : checks) {
    const std::string name = ToText(check);
    EXPECT_EQ(name.rfind("wrapper_", 0), 0U) << name;
    EXPECT_EQ(std::count(names.begin(), names.end(), name), 0) << name;
    names.push_back(name);
  }
  EXPECT_STREQ(ToText(WrapperCheck::kFillNotZero), "wrapper_fill_not_zero");
}

}  // namespace
