// Unit tests of the payload checks of the pure receiver core: the 4-byte
// little-endian length prefix and the minimal protobuf wire reader of the
// VisualizationFrame fields sequence (3) and frame_timestamp_ns (4). The
// golden frames were encoded by the protobuf runtime from the message
// definition of interface/aebs_visualization.proto (test/fixtures/README.md).

#include <gtest/gtest.h>

#include <cstdint>
#include <limits>
#include <vector>

#include "de4sdv_someip_receiver/frame_fields.hpp"
#include "fixture_loader.hpp"

namespace {

using de4sdv::someip_receiver::CheckLengthPrefix;
using de4sdv::someip_receiver::FrameReadError;
using de4sdv::someip_receiver::PayloadCheck;
using de4sdv::someip_receiver::ReadFrameFields;
using de4sdv::someip_receiver::ReadLengthPrefix;
using de4sdv::someip_receiver::test::Bytes;
using de4sdv::someip_receiver::test::LoadHexFixture;

Bytes Prefixed(const Bytes& frame) {
  const auto length = static_cast<std::uint32_t>(frame.size());
  Bytes payload{static_cast<std::uint8_t>(length & 0xFFU), static_cast<std::uint8_t>((length >> 8U) & 0xFFU),
                static_cast<std::uint8_t>((length >> 16U) & 0xFFU), static_cast<std::uint8_t>(length >> 24U)};
  for (const std::uint8_t byte : frame) {  // a loop: GCC 11 warns falsely on insert() here
    payload.push_back(byte);
  }
  return payload;
}

void PutVarint(Bytes& out, std::uint64_t value) {
  while (value >= 0x80U) {
    out.push_back(static_cast<std::uint8_t>((value & 0x7FU) | 0x80U));
    value >>= 7U;
  }
  out.push_back(static_cast<std::uint8_t>(value));
}

void PutTag(Bytes& out, std::uint32_t field, std::uint32_t wire_type) { PutVarint(out, (field << 3U) | wire_type); }

TEST(FrameFields, GoldenMinimalFrame) {
  const Bytes frame = LoadHexFixture("visualization_frame_minimal");
  const auto result = ReadFrameFields(frame.data(), frame.size());
  ASSERT_EQ(result.error, FrameReadError::kNone);
  ASSERT_TRUE(result.fields.has_value());
  EXPECT_EQ(result.fields->sequence, 42U);
  EXPECT_EQ(result.fields->frame_timestamp_ns, 1793116443934013818);
}

TEST(FrameFields, GoldenFullFrameWithNestedAndRepeatedFields) {
  const Bytes frame = LoadHexFixture("visualization_frame_full");
  const auto result = ReadFrameFields(frame.data(), frame.size());
  ASSERT_EQ(result.error, FrameReadError::kNone);
  EXPECT_EQ(result.fields->sequence, 1234567U);
  EXPECT_EQ(result.fields->frame_timestamp_ns, 1793116449339467540);
}

TEST(FrameFields, GoldenLargeSequenceAndNegativeTimestamp) {
  const Bytes frame = LoadHexFixture("visualization_frame_large_sequence_negative_timestamp");
  const auto result = ReadFrameFields(frame.data(), frame.size());
  ASSERT_EQ(result.error, FrameReadError::kNone);
  EXPECT_EQ(result.fields->sequence, (std::uint64_t{1} << 63U) + 5U);
  EXPECT_EQ(result.fields->frame_timestamp_ns, -1);
}

TEST(FrameFields, AbsentFieldsReadAsZero) {
  const Bytes frame = LoadHexFixture("visualization_frame_default_sequence_and_timestamp");
  const auto result = ReadFrameFields(frame.data(), frame.size());
  ASSERT_EQ(result.error, FrameReadError::kNone);
  EXPECT_EQ(result.fields->sequence, 0U);
  EXPECT_EQ(result.fields->frame_timestamp_ns, 0);
  EXPECT_EQ(ReadFrameFields(frame.data(), 0).error, FrameReadError::kNone);
}

TEST(FrameFields, TruncatedVarintIsAnError) {
  Bytes frame;
  PutTag(frame, 3, 0);
  PutVarint(frame, 300);  // two bytes
  frame.pop_back();
  EXPECT_EQ(ReadFrameFields(frame.data(), frame.size()).error, FrameReadError::kTruncatedVarint);
}

TEST(FrameFields, TruncatedLengthDelimitedFieldIsAnError) {
  const Bytes frame = LoadHexFixture("visualization_frame_full");
  // Cut inside the source_identity string (field 6), well before the end.
  const auto result = ReadFrameFields(frame.data(), 40);
  EXPECT_EQ(result.error, FrameReadError::kTruncatedField);
  EXPECT_FALSE(result.fields.has_value());
}

TEST(FrameFields, TruncatedFixedFieldIsAnError) {
  Bytes frame;
  PutTag(frame, 20, 1);  // 64-bit
  frame.insert(frame.end(), {1, 2, 3});
  EXPECT_EQ(ReadFrameFields(frame.data(), frame.size()).error, FrameReadError::kTruncatedField);
  Bytes fixed32;
  PutTag(fixed32, 20, 5);  // 32-bit
  fixed32.insert(fixed32.end(), {1, 2});
  EXPECT_EQ(ReadFrameFields(fixed32.data(), fixed32.size()).error, FrameReadError::kTruncatedField);
}

TEST(FrameFields, VarintLongerThanTenBytesIsAnError) {
  Bytes frame;
  PutTag(frame, 3, 0);
  for (int i = 0; i < 10; ++i) {
    frame.push_back(0xFF);
  }
  frame.push_back(0x01);
  EXPECT_EQ(ReadFrameFields(frame.data(), frame.size()).error, FrameReadError::kVarintTooLong);
}

TEST(FrameFields, FieldNumberZeroIsAnError) {
  const Bytes frame{0x00, 0x01};
  EXPECT_EQ(ReadFrameFields(frame.data(), frame.size()).error, FrameReadError::kInvalidFieldNumber);
}

TEST(FrameFields, GroupsAndUnknownWireTypesAreErrors) {
  for (const std::uint32_t wire_type : {3U, 4U, 6U, 7U}) {
    Bytes frame;
    PutTag(frame, 20, wire_type);
    frame.push_back(0x00);
    EXPECT_EQ(ReadFrameFields(frame.data(), frame.size()).error, FrameReadError::kUnsupportedWireType)
        << "wire type " << wire_type;
  }
}

TEST(FrameFields, SequenceAndTimestampMustBeVarints) {
  Bytes sequence;
  PutTag(sequence, 3, 2);
  PutVarint(sequence, 1);
  sequence.push_back(0x05);
  EXPECT_EQ(ReadFrameFields(sequence.data(), sequence.size()).error, FrameReadError::kSequenceWireType);
  Bytes timestamp;
  PutTag(timestamp, 4, 1);
  timestamp.insert(timestamp.end(), 8, 0x00);
  EXPECT_EQ(ReadFrameFields(timestamp.data(), timestamp.size()).error, FrameReadError::kTimestampWireType);
}

TEST(FrameFields, LastOccurrenceCountsAndUnknownFieldsAreSkipped) {
  Bytes frame;
  PutTag(frame, 3, 0);
  PutVarint(frame, 7);
  PutTag(frame, 21, 5);
  frame.insert(frame.end(), 4, 0xAA);
  PutTag(frame, 22, 1);
  frame.insert(frame.end(), 8, 0xBB);
  PutTag(frame, 23, 2);
  PutVarint(frame, 3);
  frame.insert(frame.end(), {0x01, 0x02, 0x03});
  PutTag(frame, 1000, 0);
  PutVarint(frame, 123456789);
  PutTag(frame, 3, 0);
  PutVarint(frame, 9);
  PutTag(frame, 4, 0);
  PutVarint(frame, static_cast<std::uint64_t>(std::numeric_limits<std::int64_t>::max()));
  const auto result = ReadFrameFields(frame.data(), frame.size());
  ASSERT_EQ(result.error, FrameReadError::kNone);
  EXPECT_EQ(result.fields->sequence, 9U);
  EXPECT_EQ(result.fields->frame_timestamp_ns, std::numeric_limits<std::int64_t>::max());
}

TEST(LengthPrefix, CountsTheBytesAfterItLittleEndian) {
  const Bytes payload = Prefixed(LoadHexFixture("visualization_frame_full"));
  EXPECT_EQ(CheckLengthPrefix(payload.data(), payload.size()), PayloadCheck::kOk);
  EXPECT_EQ(ReadLengthPrefix(payload.data()), payload.size() - 4);
  const Bytes empty_frame{0x00, 0x00, 0x00, 0x00};
  EXPECT_EQ(CheckLengthPrefix(empty_frame.data(), empty_frame.size()), PayloadCheck::kOk);
}

TEST(LengthPrefix, MismatchAndShortPayloadAreRejected) {
  Bytes payload = Prefixed(LoadHexFixture("visualization_frame_minimal"));
  payload.push_back(0x00);
  EXPECT_EQ(CheckLengthPrefix(payload.data(), payload.size()), PayloadCheck::kLengthPrefixMismatch);
  EXPECT_EQ(CheckLengthPrefix(payload.data(), 3), PayloadCheck::kTooShort);
}

TEST(LengthPrefix, BigEndianPrefixOfTheSpikePublisherIsRejected) {
  // The first notification payload of the golden TCP stream: 2048 bytes whose
  // prefix 00 00 07 fc is big-endian (the spike publisher's own framing).
  const Bytes stream = LoadHexFixture("tcp_notifications_someipd");
  const Bytes payload(stream.begin() + 16, stream.begin() + 16 + 2048);
  EXPECT_EQ(CheckLengthPrefix(payload.data(), payload.size()), PayloadCheck::kLengthPrefixMismatch);
}

}  // namespace
