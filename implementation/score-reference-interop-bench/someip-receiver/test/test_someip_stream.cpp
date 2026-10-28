// Unit tests of the SOME/IP-over-TCP reassembly of the pure receiver core.
// The golden fixture is the TCP byte stream of the first four notifications
// that someipd (vsomeip 3.6.1) sent to a guest client in a retained capture.

#include <gtest/gtest.h>

#include <cstdint>
#include <vector>

#include "de4sdv_someip_receiver/someip_stream.hpp"
#include "fixture_loader.hpp"

namespace {

using de4sdv::someip_receiver::Header;
using de4sdv::someip_receiver::SomeipStreamReassembler;
using de4sdv::someip_receiver::test::Bytes;
using de4sdv::someip_receiver::test::LoadHexFixture;

constexpr std::size_t kMaxPayload = 2048;

struct Message {
  Header header;
  Bytes payload;
};

struct Collector {
  std::vector<Message> messages;
  SomeipStreamReassembler::MessageHandler Handler() {
    return [this](const Header& header, const std::uint8_t* payload, std::size_t size) {
      messages.push_back(Message{header, Bytes(payload, payload + size)});
    };
  }
};

Bytes Notification(std::uint16_t session, std::size_t payload_size, std::uint8_t seed) {
  Bytes message{0x4D, 0xEE, 0x80, 0x01};
  const auto length = static_cast<std::uint32_t>(8 + payload_size);
  message.push_back(static_cast<std::uint8_t>(length >> 24U));
  message.push_back(static_cast<std::uint8_t>((length >> 16U) & 0xFFU));
  message.push_back(static_cast<std::uint8_t>((length >> 8U) & 0xFFU));
  message.push_back(static_cast<std::uint8_t>(length & 0xFFU));
  message.push_back(0x00);
  message.push_back(0x00);
  message.push_back(static_cast<std::uint8_t>(session >> 8U));
  message.push_back(static_cast<std::uint8_t>(session & 0xFFU));
  message.push_back(0x01);
  message.push_back(0x01);
  message.push_back(0x02);
  message.push_back(0x00);
  for (std::size_t i = 0; i < payload_size; ++i) {
    message.push_back(static_cast<std::uint8_t>(seed + i * 3U));
  }
  return message;
}

void ExpectGoldenStream(const std::vector<Message>& messages) {
  ASSERT_EQ(messages.size(), 4U);
  const std::size_t sizes[] = {2048, 20, 1500, 1501};
  for (std::size_t i = 0; i < messages.size(); ++i) {
    EXPECT_EQ(messages[i].header.service_id, 0x4DEE);
    EXPECT_EQ(messages[i].header.method_id, 0x8001);
    EXPECT_EQ(messages[i].header.session_id, i + 1);
    EXPECT_EQ(messages[i].header.message_type, 0x02);
    EXPECT_EQ(messages[i].header.return_code, 0x00);
    EXPECT_EQ(messages[i].header.interface_version, 0x01);
    EXPECT_EQ(messages[i].payload.size(), sizes[i]);
  }
}

TEST(SomeipStream, GoldenStreamInOneRead) {
  const Bytes stream = LoadHexFixture("tcp_notifications_someipd");
  SomeipStreamReassembler reassembler{kMaxPayload};
  Collector collector;
  EXPECT_TRUE(reassembler.Feed(stream.data(), stream.size(), collector.Handler()));
  ExpectGoldenStream(collector.messages);
  EXPECT_FALSE(reassembler.HasPartialMessage());
  EXPECT_EQ(reassembler.stats().messages, 4U);
  EXPECT_EQ(reassembler.stats().bytes_read, stream.size());
}

TEST(SomeipStream, GoldenStreamByteByByte) {
  const Bytes stream = LoadHexFixture("tcp_notifications_someipd");
  SomeipStreamReassembler reassembler{kMaxPayload};
  Collector collector;
  for (const std::uint8_t byte : stream) {
    ASSERT_TRUE(reassembler.Feed(&byte, 1, collector.Handler()));
  }
  ExpectGoldenStream(collector.messages);
}

TEST(SomeipStream, GoldenStreamAtUnevenCuts) {
  const Bytes stream = LoadHexFixture("tcp_notifications_someipd");
  const std::size_t cuts[] = {1, 7, 15, 16, 17, 1448, 3, 2000, 600, 13};
  SomeipStreamReassembler reassembler{kMaxPayload};
  Collector collector;
  std::size_t position = 0;
  std::size_t cut = 0;
  while (position < stream.size()) {
    const std::size_t take = std::min(cuts[cut % (sizeof(cuts) / sizeof(cuts[0]))], stream.size() - position);
    ASSERT_TRUE(reassembler.Feed(stream.data() + position, take, collector.Handler()));
    position += take;
    ++cut;
  }
  ExpectGoldenStream(collector.messages);
  // The payload bytes are the stream bytes after each header.
  EXPECT_EQ(collector.messages[1].payload, Bytes(stream.begin() + 2064 + 16, stream.begin() + 2064 + 36));
}

TEST(SomeipStream, PartialMessageWaitsForTheRest) {
  const Bytes first = Notification(1, 10, 0x10);
  const Bytes second = Notification(2, 30, 0x20);
  Bytes stream = first;
  stream.insert(stream.end(), second.begin(), second.begin() + 20);
  SomeipStreamReassembler reassembler{kMaxPayload};
  Collector collector;
  ASSERT_TRUE(reassembler.Feed(stream.data(), stream.size(), collector.Handler()));
  ASSERT_EQ(collector.messages.size(), 1U);
  EXPECT_TRUE(reassembler.HasPartialMessage());
  ASSERT_TRUE(reassembler.Feed(second.data() + 20, second.size() - 20, collector.Handler()));
  ASSERT_EQ(collector.messages.size(), 2U);
  EXPECT_EQ(collector.messages[1].payload, Bytes(second.begin() + 16, second.end()));
}

TEST(SomeipStream, EmptyPayloadIsAMessage) {
  const Bytes empty = Notification(5, 0, 0);
  SomeipStreamReassembler reassembler{kMaxPayload};
  Collector collector;
  ASSERT_TRUE(reassembler.Feed(empty.data(), empty.size(), collector.Handler()));
  ASSERT_EQ(collector.messages.size(), 1U);
  EXPECT_TRUE(collector.messages[0].payload.empty());
}

TEST(SomeipStream, OversizePayloadIsSkippedAndTheNextMessageSurvives) {
  Bytes stream = Notification(1, 3000, 0x01);
  const Bytes next = Notification(2, 40, 0x02);
  stream.insert(stream.end(), next.begin(), next.end());
  SomeipStreamReassembler reassembler{kMaxPayload};
  Collector collector;
  ASSERT_TRUE(reassembler.Feed(stream.data(), stream.size(), collector.Handler()));
  ASSERT_EQ(collector.messages.size(), 1U);
  EXPECT_EQ(collector.messages[0].header.session_id, 2);
  EXPECT_EQ(reassembler.stats().messages_oversize_skipped, 1U);
}

TEST(SomeipStream, LengthBelowEightLosesTheFraming) {
  Bytes broken = Notification(1, 4, 0x01);
  broken[7] = 0x07;  // length 7: shorter than the rest of the header
  const Bytes next = Notification(2, 4, 0x02);
  SomeipStreamReassembler reassembler{kMaxPayload};
  Collector collector;
  EXPECT_FALSE(reassembler.Feed(broken.data(), broken.size(), collector.Handler()));
  EXPECT_TRUE(reassembler.framing_lost());
  EXPECT_FALSE(reassembler.Feed(next.data(), next.size(), collector.Handler()));
  EXPECT_TRUE(collector.messages.empty());
  EXPECT_EQ(reassembler.stats().framing_errors, 1U);
  reassembler.Reset();
  EXPECT_TRUE(reassembler.Feed(next.data(), next.size(), collector.Handler()));
  EXPECT_EQ(collector.messages.size(), 1U);
}

TEST(SomeipStream, HugeLengthLosesTheFraming) {
  Bytes huge = Notification(1, 4, 0x01);
  huge[4] = 0x7F;  // about 2 GB
  SomeipStreamReassembler reassembler{kMaxPayload};
  Collector collector;
  EXPECT_FALSE(reassembler.Feed(huge.data(), huge.size(), collector.Handler()));
  EXPECT_TRUE(reassembler.framing_lost());
}

TEST(SomeipStream, ResetDiscardsAPartialMessage) {
  const Bytes message = Notification(1, 100, 0x05);
  SomeipStreamReassembler reassembler{kMaxPayload};
  Collector collector;
  ASSERT_TRUE(reassembler.Feed(message.data(), 50, collector.Handler()));
  reassembler.Reset();
  EXPECT_EQ(reassembler.stats().partial_messages_discarded, 1U);
  ASSERT_TRUE(reassembler.Feed(message.data(), message.size(), collector.Handler()));
  ASSERT_EQ(collector.messages.size(), 1U);
  EXPECT_EQ(collector.messages[0].payload.size(), 100U);
}

}  // namespace
