// Unit tests of the receiver core: every notification of the frame event
// ends delivered or dropped with one reason, the payload goes to the
// loopback client unchanged, and nothing is queued.

#include <gtest/gtest.h>

#include <cstdint>
#include <string>
#include <vector>

#include "de4sdv_someip_receiver/receiver_core.hpp"
#include "fixture_loader.hpp"

namespace {

using de4sdv::someip_receiver::Clock;
using de4sdv::someip_receiver::DropReason;
using de4sdv::someip_receiver::EncodeSubscribeEventgroup;
using de4sdv::someip_receiver::EventLog;
using de4sdv::someip_receiver::FrameSink;
using de4sdv::someip_receiver::Ipv4Endpoint;
using de4sdv::someip_receiver::kL4ProtocolTcp;
using de4sdv::someip_receiver::LogRecord;
using de4sdv::someip_receiver::ProvisionalDiscardPolicy;
using de4sdv::someip_receiver::ReceiverConfig;
using de4sdv::someip_receiver::ReceiverCore;
using de4sdv::someip_receiver::SubscriptionTransport;
using de4sdv::someip_receiver::test::Bytes;
using de4sdv::someip_receiver::test::LoadHexFixture;

constexpr std::int64_t kMs = 1'000'000;
constexpr std::int64_t kS = 1'000'000'000;
constexpr std::int64_t kRealtimeBase = 1'793'116'440'000'000'000;
constexpr std::int64_t kBound = 50 * kMs;
constexpr std::uint32_t kServer = 0x0AFA0001;
const Ipv4Endpoint kLocal{0x0AFA0002, 41000, kL4ProtocolTcp};

Clock At(std::int64_t t) { return Clock{t, kRealtimeBase + t}; }

void PutVarint(Bytes& out, std::uint64_t value) {
  while (value >= 0x80U) {
    out.push_back(static_cast<std::uint8_t>((value & 0x7FU) | 0x80U));
    value >>= 7U;
  }
  out.push_back(static_cast<std::uint8_t>(value));
}

// A VisualizationFrame with schema 1.1, sequence and frame_timestamp_ns.
Bytes Frame(std::uint64_t sequence, std::int64_t timestamp_ns) {
  Bytes frame{0x08, 0x01, 0x10, 0x01, 0x18};
  PutVarint(frame, sequence);
  frame.push_back(0x20);
  PutVarint(frame, static_cast<std::uint64_t>(timestamp_ns));
  return frame;
}

Bytes Prefixed(const Bytes& frame) {
  const auto length = static_cast<std::uint32_t>(frame.size());
  Bytes payload{static_cast<std::uint8_t>(length & 0xFFU), static_cast<std::uint8_t>((length >> 8U) & 0xFFU),
                static_cast<std::uint8_t>((length >> 16U) & 0xFFU), static_cast<std::uint8_t>(length >> 24U)};
  for (const std::uint8_t byte : frame) {
    payload.push_back(byte);
  }
  return payload;
}

Bytes Notification(const Bytes& payload, std::uint16_t session = 1, std::uint16_t method = 0x8001,
                   std::uint8_t message_type = 0x02) {
  Bytes message{0x4D, 0xEE, static_cast<std::uint8_t>(method >> 8U), static_cast<std::uint8_t>(method & 0xFFU)};
  const auto length = static_cast<std::uint32_t>(8 + payload.size());
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
  message.push_back(message_type);
  message.push_back(0x00);
  for (const std::uint8_t byte : payload) {
    message.push_back(byte);
  }
  return message;
}

Bytes FrameNotification(std::uint64_t sequence, std::int64_t timestamp_ns) {
  return Notification(Prefixed(Frame(sequence, timestamp_ns)), static_cast<std::uint16_t>(sequence & 0xFFFFU));
}

Bytes Ack(std::uint16_t session, std::uint32_t ttl = 3) {
  // SubscribeEventgroupAck has the layout of the subscribe entry without options;
  // the golden Ack of someipd with its session and TTL patched.
  Bytes ack = LoadHexFixture("sd_subscribe_ack");
  ack[10] = static_cast<std::uint8_t>(session >> 8U);
  ack[11] = static_cast<std::uint8_t>(session & 0xFFU);
  ack[35] = static_cast<std::uint8_t>(ttl & 0xFFU);
  return ack;
}

class FakeTransport : public SubscriptionTransport {
 public:
  void ConnectTcp(const Ipv4Endpoint&) override { ++connects; }
  void CloseTcp() override { ++closes; }
  bool SendSd(const std::vector<std::uint8_t>&, std::uint32_t, std::uint16_t) override {
    ++sent;
    return true;
  }
  int connects{0};
  int closes{0};
  int sent{0};
};

class FakeSink : public FrameSink {
 public:
  bool Forward(const std::uint8_t* payload, std::size_t size) override {
    if (fail) {
      return false;
    }
    delivered.emplace_back(payload, payload + size);
    return true;
  }
  std::vector<Bytes> delivered;
  bool fail{false};
};

class Lines : public EventLog {
 public:
  void Log(const Clock& now, const LogRecord& record) override { lines.push_back(record.ToJson(now)); }
  int Count(const std::string& needle) const {
    int count = 0;
    for (const auto& line : lines) {
      if (line.find(needle) != std::string::npos) {
        ++count;
      }
    }
    return count;
  }
  std::vector<std::string> lines;
};

struct Bench {
  ReceiverConfig config;
  FakeTransport transport;
  FakeSink sink;
  ProvisionalDiscardPolicy policy{kBound};
  Lines log;
  ReceiverCore core;

  static ReceiverConfig Defaults() {
    ReceiverConfig config;
    config.subscription.server_address = kServer;
    config.log_frames = true;
    return config;
  }

  explicit Bench(ReceiverConfig base = Defaults()) : config{base}, core{config, transport, sink, policy, log} {}

  // Fallback connect, subscribe and Ack; returns the Ack time.
  std::int64_t Subscribe(std::int64_t t, std::uint16_t ack_session = 1) {
    core.OnTick(At(t));
    core.OnTcpConnected(At(t + 1 * kMs), kLocal);
    core.OnTick(At(t + 1 * kMs + config.subscription.subscribe_delay_ns));
    const std::int64_t ack_at = t + 2 * kMs + config.subscription.subscribe_delay_ns;
    const Bytes ack = Ack(ack_session);
    core.OnSdDatagram(At(ack_at), kServer, false, ack.data(), ack.size());
    return ack_at;
  }

  void Data(std::int64_t t, const Bytes& bytes) { core.OnTcpData(At(t), bytes.data(), bytes.size()); }

  std::uint64_t Dropped(DropReason reason) const {
    return core.counters().drops.at(static_cast<std::size_t>(reason));
  }

  void ExpectBalanced() const {
    const auto& c = core.counters();
    EXPECT_EQ(c.frames_received, c.frames_delivered + c.frames_dropped());
  }
};

TEST(ReceiverCore, SubscribedWithClientDeliversThePayloadUnchanged) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  EXPECT_TRUE(bench.core.subscribed());
  bench.core.OnClientConnected(At(ack + 1 * kMs));
  Bytes stream;
  std::vector<Bytes> payloads;
  for (std::uint64_t sequence = 1; sequence <= 3; ++sequence) {
    const Bytes payload = Prefixed(Frame(sequence, kRealtimeBase + ack + static_cast<std::int64_t>(sequence) * kMs));
    payloads.push_back(payload);
    const Bytes message = Notification(payload, static_cast<std::uint16_t>(sequence));
    stream.insert(stream.end(), message.begin(), message.end());
  }
  bench.Data(ack + 10 * kMs, stream);
  EXPECT_EQ(bench.sink.delivered, payloads);
  EXPECT_EQ(bench.core.counters().frames_delivered, 3U);
  EXPECT_EQ(bench.log.Count("\"event\":\"frame\",\"verdict\":\"delivered\""), 3);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, LargestFrameOf2044BytesIsDelivered) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  bench.core.OnClientConnected(At(ack));
  Bytes frame = Frame(7, kRealtimeBase + ack);
  // Pad with an unknown length-delimited field (number 16) up to 2044 bytes.
  frame.push_back(0x82);
  frame.push_back(0x01);
  const std::size_t room = 2044 - frame.size() - 2;
  PutVarint(frame, room);
  frame.insert(frame.end(), room, 0x5A);
  ASSERT_EQ(frame.size(), 2044U);
  const Bytes payload = Prefixed(frame);
  bench.Data(ack + 1 * kMs, Notification(payload));
  ASSERT_EQ(bench.sink.delivered.size(), 1U);
  EXPECT_EQ(bench.sink.delivered[0], payload);
  EXPECT_EQ(bench.sink.delivered[0].size(), 2048U);
}

TEST(ReceiverCore, PayloadAboveTheSampleSizeIsDropped) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  bench.core.OnClientConnected(At(ack));
  Bytes frame = Frame(7, kRealtimeBase + ack);
  frame.resize(2045, 0x00);  // trailing zero bytes are not a valid field, but the size check comes first
  bench.Data(ack + 1 * kMs, Notification(Prefixed(frame)));
  EXPECT_TRUE(bench.sink.delivered.empty());
  EXPECT_EQ(bench.Dropped(DropReason::kPayloadTooLarge), 1U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, FramesWithoutClientAreDroppedAndNotQueued) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  for (std::uint64_t sequence = 1; sequence <= 5; ++sequence) {
    bench.Data(ack + static_cast<std::int64_t>(sequence) * 100 * kMs,
               FrameNotification(sequence, kRealtimeBase + ack + static_cast<std::int64_t>(sequence) * 100 * kMs));
  }
  EXPECT_EQ(bench.Dropped(DropReason::kNoClient), 5U);
  const std::int64_t connected = ack + 600 * kMs;
  bench.core.OnClientConnected(At(connected));
  EXPECT_TRUE(bench.sink.delivered.empty());  // nothing queued for the new client
  // A frame produced before the client connected, still in flight: older than the phase.
  bench.Data(connected + 1 * kMs, FrameNotification(6, kRealtimeBase + connected - kBound - 1));
  bench.Data(connected + 2 * kMs, FrameNotification(7, kRealtimeBase + connected + 1 * kMs));
  ASSERT_EQ(bench.sink.delivered.size(), 1U);
  EXPECT_EQ(bench.Dropped(DropReason::kOlderThanPhase), 1U);
  EXPECT_EQ(bench.core.counters().phases_by_client, 1U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, FramesBeforeTheAckAreDropped) {
  Bench bench;
  bench.core.OnClientConnected(At(0));
  bench.core.OnTick(At(0));
  bench.core.OnTcpConnected(At(1 * kMs), kLocal);
  bench.Data(2 * kMs, FrameNotification(1, kRealtimeBase + 2 * kMs));
  EXPECT_EQ(bench.Dropped(DropReason::kNotSubscribed), 1U);
  EXPECT_TRUE(bench.sink.delivered.empty());
  bench.ExpectBalanced();
}

TEST(ReceiverCore, StoredFramesAfterAResubscriptionAreDroppedAndCounted) {
  Bench bench;
  std::int64_t ack = bench.Subscribe(0);
  bench.core.OnClientConnected(At(ack));
  bench.Data(ack + 100 * kMs, FrameNotification(40, kRealtimeBase + ack + 90 * kMs));
  // The TCP connection closes; a new connection and subscription follow 5 s later.
  bench.core.OnTcpClosed(At(ack + 1 * kS));
  ack = bench.Subscribe(ack + 5 * kS, 2);
  ASSERT_TRUE(bench.core.subscribed());
  // The layer sends ten frames that it stored about 4 s before the new phase,
  // one of them a duplicate of a delivered frame, then new frames.
  bench.Data(ack + 1 * kMs, FrameNotification(40, kRealtimeBase + ack - 4100 * kMs));
  for (std::uint64_t sequence = 41; sequence <= 49; ++sequence) {
    bench.Data(ack + 1 * kMs, FrameNotification(sequence, kRealtimeBase + ack - 4000 * kMs));
  }
  bench.Data(ack + 50 * kMs, FrameNotification(50, kRealtimeBase + ack + 40 * kMs));
  EXPECT_EQ(bench.Dropped(DropReason::kSequenceNotIncreasing), 1U);
  EXPECT_EQ(bench.Dropped(DropReason::kOlderThanPhase), 9U);
  ASSERT_EQ(bench.sink.delivered.size(), 2U);
  EXPECT_EQ(bench.core.counters().phases_by_subscription, 2U);
  EXPECT_EQ(bench.log.Count("\"event\":\"phase_start\""), 3);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, LengthPrefixMismatchIsDroppedAndTheStreamStaysIntact) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  bench.core.OnClientConnected(At(ack));
  Bytes bad = Prefixed(Frame(1, kRealtimeBase + ack));
  bad[0] = static_cast<std::uint8_t>(bad[0] + 1);  // the prefix counts one byte too many
  Bytes stream = Notification(bad);
  const Bytes good = FrameNotification(2, kRealtimeBase + ack + 1 * kMs);
  stream.insert(stream.end(), good.begin(), good.end());
  bench.Data(ack + 2 * kMs, stream);
  EXPECT_EQ(bench.Dropped(DropReason::kLengthPrefixMismatch), 1U);
  ASSERT_EQ(bench.sink.delivered.size(), 1U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, SpikePayloadsWithBigEndianPrefixAreAllDropped) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  bench.core.OnClientConnected(At(ack));
  bench.Data(ack + 1 * kMs, LoadHexFixture("tcp_notifications_someipd"));
  EXPECT_EQ(bench.core.counters().frames_received, 4U);
  EXPECT_EQ(bench.Dropped(DropReason::kLengthPrefixMismatch), 4U);
  EXPECT_TRUE(bench.sink.delivered.empty());
  bench.ExpectBalanced();
}

TEST(ReceiverCore, UnreadableFrameIsDropped) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  bench.core.OnClientConnected(At(ack));
  const Bytes truncated{0x08, 0x01, 0x18, 0x81};  // the varint of field 3 is cut
  bench.Data(ack + 1 * kMs, Notification(Prefixed(truncated)));
  EXPECT_EQ(bench.Dropped(DropReason::kFrameUnreadable), 1U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, OtherMessagesAndMagicCookiesAreNotFrames) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  bench.core.OnClientConnected(At(ack));
  Bytes stream = Notification(Prefixed(Frame(1, kRealtimeBase + ack)), 1, 0x8002);  // another event
  const Bytes cookie{0xFF, 0xFF, 0x80, 0x00, 0x00, 0x00, 0x00, 0x08,
                     0xDE, 0xAD, 0xBE, 0xEF, 0x01, 0x01, 0x02, 0x00};
  stream.insert(stream.end(), cookie.begin(), cookie.end());
  const Bytes request = Notification(Prefixed(Frame(2, kRealtimeBase + ack)), 2, 0x8001, 0x00);
  stream.insert(stream.end(), request.begin(), request.end());
  bench.Data(ack + 1 * kMs, stream);
  EXPECT_EQ(bench.core.counters().other_messages, 1U);
  EXPECT_EQ(bench.core.counters().magic_cookies, 1U);
  EXPECT_EQ(bench.core.counters().frames_received, 1U);
  EXPECT_EQ(bench.Dropped(DropReason::kMalformedNotification), 1U);
  EXPECT_TRUE(bench.sink.delivered.empty());
  bench.ExpectBalanced();
}

TEST(ReceiverCore, FailedWriteDropsTheFrameAndTheClient) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  bench.core.OnClientConnected(At(ack));
  bench.sink.fail = true;
  bench.Data(ack + 1 * kMs, FrameNotification(1, kRealtimeBase + ack));
  EXPECT_EQ(bench.Dropped(DropReason::kClientWriteFailed), 1U);
  EXPECT_FALSE(bench.core.client_connected());
  EXPECT_EQ(bench.core.counters().clients_lost, 1U);
  bench.sink.fail = false;
  bench.Data(ack + 2 * kMs, FrameNotification(2, kRealtimeBase + ack + 1 * kMs));
  EXPECT_EQ(bench.Dropped(DropReason::kNoClient), 1U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, LostFramingEndsTheConnectionAndResetsTheReassembly) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  bench.core.OnClientConnected(At(ack));
  Bytes broken = FrameNotification(1, kRealtimeBase + ack);
  broken[7] = 0x03;  // length 3
  bench.Data(ack + 1 * kMs, broken);
  EXPECT_FALSE(bench.core.subscribed());
  EXPECT_EQ(bench.core.counters().stream_framing_errors, 1U);
  EXPECT_EQ(bench.transport.closes, 1);
  // The next connection starts with clean framing.
  const std::int64_t again = bench.Subscribe(ack + 1 * kS, 2);
  bench.Data(again + 1 * kMs, FrameNotification(2, kRealtimeBase + again));
  EXPECT_EQ(bench.sink.delivered.size(), 1U);
}

TEST(ReceiverCore, PartialMessageOfAClosedConnectionIsNotDelivered) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  bench.core.OnClientConnected(At(ack));
  const Bytes message = FrameNotification(1, kRealtimeBase + ack);
  bench.core.OnTcpData(At(ack + 1 * kMs), message.data(), 20);
  bench.core.OnTcpClosed(At(ack + 2 * kMs));
  const std::int64_t again = bench.Subscribe(ack + 1 * kS, 2);
  bench.core.OnTcpData(At(again + 1 * kMs), message.data() + 20, message.size() - 20);
  EXPECT_TRUE(bench.sink.delivered.empty());
}

TEST(ReceiverCore, MalformedSdDatagramIsCountedAndIgnored) {
  Bench bench;
  Bytes offer = LoadHexFixture("sd_offer_multicast");
  offer.pop_back();
  bench.core.OnSdDatagram(At(0), kServer, true, offer.data(), offer.size());
  EXPECT_EQ(bench.core.counters().sd_malformed, 1U);
  EXPECT_EQ(bench.transport.connects, 0);
}

TEST(ReceiverCore, StatusHoldsEveryDropReason) {
  Bench bench;
  const LogRecord status = bench.core.Status("status");
  for (const char* key : {"drop_malformed_notification", "drop_payload_too_large", "drop_length_prefix_mismatch",
                          "drop_frame_unreadable", "drop_not_subscribed", "drop_no_client",
                          "drop_sequence_not_increasing", "drop_older_than_phase", "drop_client_write_failed",
                          "frames_received", "frames_delivered", "subscription_state", "client_connected"}) {
    EXPECT_NE(status.fields().find(std::string{"\""} + key + "\":"), std::string::npos) << key;
  }
}

TEST(ReceiverCore, StopSendsStopSubscribe) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  const int sent = bench.transport.sent;
  bench.core.Stop(At(ack + 1 * kS));
  EXPECT_EQ(bench.transport.sent, sent + 1);
  EXPECT_FALSE(bench.core.subscribed());
}

}  // namespace
