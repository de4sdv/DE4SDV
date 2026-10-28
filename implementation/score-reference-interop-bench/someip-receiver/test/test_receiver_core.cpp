// Unit tests of the receiver core: the subscription phase of the discard
// rule (subscribed and one client), every notification of the frame event
// delivered or dropped with one reason, the payload unchanged, no queue.
// Each event carries its clock, so the tests set every time they need.

#include <gtest/gtest.h>

#include <cstdint>
#include <string>
#include <utility>
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
using de4sdv::someip_receiver::kIngressRetriggerPeriodNs;
using de4sdv::someip_receiver::kL4ProtocolTcp;
using de4sdv::someip_receiver::LogRecord;
using de4sdv::someip_receiver::PhaseStartDiscardPolicy;
using de4sdv::someip_receiver::PropertySetter;
using de4sdv::someip_receiver::ReceiverConfig;
using de4sdv::someip_receiver::ReceiverCore;
using de4sdv::someip_receiver::SubscriptionTransport;
using de4sdv::someip_receiver::test::Bytes;
using de4sdv::someip_receiver::test::LoadHexFixture;

constexpr std::int64_t kMs = 1'000'000;
constexpr std::int64_t kS = 1'000'000'000;
constexpr std::int64_t kRealtimeBase = 1'793'116'440'000'000'000;
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

class FakeProperties : public PropertySetter {
 public:
  bool SetProperty(const Clock&, const std::string& name, const std::string& value) override {
    sets.emplace_back(name, value);
    return ok;
  }
  std::vector<std::pair<std::string, std::string>> sets;
  bool ok{true};
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
  PhaseStartDiscardPolicy policy;
  Lines log;
  FakeProperties properties;
  ReceiverCore core;

  static ReceiverConfig Defaults() {
    ReceiverConfig config;
    config.subscription.server_address = kServer;
    config.log_frames = true;
    return config;
  }

  explicit Bench(ReceiverConfig base = Defaults())
      : config{base}, core{config, transport, sink, policy, log, &properties} {}

  // Fallback connect, subscribe and Ack; returns the Ack time.
  std::int64_t Subscribe(std::int64_t t, std::uint16_t ack_session = 1) {
    core.OnTick(At(t));
    core.OnTcpConnected(At(t + 1 * kMs), kLocal);
    core.OnTick(At(t + 1 * kMs + config.subscription.subscribe_delay_ns));
    const std::int64_t ack_at = t + 2 * kMs + config.subscription.subscribe_delay_ns;
    SdAck(ack_at, ack_session);
    return ack_at;
  }

  void SdAck(std::int64_t t, std::uint16_t session, std::uint32_t ttl = 3) {
    const Bytes ack = Ack(session, ttl);
    core.OnSdDatagram(At(t), kServer, false, ack.data(), ack.size());
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

// A phase that starts with the client at ack + 1 ms; returns the phase start (monotonic).
std::int64_t StartPhase(Bench& bench) {
  const std::int64_t ack = bench.Subscribe(0);
  EXPECT_TRUE(bench.core.OnClientAccepted(At(ack + 1 * kMs)));
  EXPECT_TRUE(bench.core.in_phase());
  return ack + 1 * kMs;
}

std::int64_t Realtime(std::int64_t monotonic) { return kRealtimeBase + monotonic; }

TEST(ReceiverCore, PhaseStartsWhenTheSecondConditionStartsToHold) {
  Bench bench;
  const std::int64_t ack = bench.Subscribe(0);
  EXPECT_TRUE(bench.core.subscribed());
  EXPECT_FALSE(bench.core.in_phase());  // subscribed, no client
  EXPECT_EQ(bench.log.Count("\"event\":\"phase_start\""), 0);
  ASSERT_TRUE(bench.core.OnClientAccepted(At(ack + 7 * kMs)));
  EXPECT_TRUE(bench.core.in_phase());
  ASSERT_EQ(bench.log.Count("\"event\":\"phase_start\""), 1);
  EXPECT_EQ(bench.log.Count("\"cause\":\"client_connected\",\"phase_start_realtime_ns\":" +
                            std::to_string(Realtime(ack + 7 * kMs))),
            1);
}

TEST(ReceiverCore, ClientWithoutSubscriptionStartsNoPhase) {
  Bench bench;
  ASSERT_TRUE(bench.core.OnClientAccepted(At(0)));
  EXPECT_FALSE(bench.core.in_phase());
  EXPECT_EQ(bench.core.counters().phases_started, 0U);
  const std::int64_t ack = bench.Subscribe(1 * kMs);
  EXPECT_TRUE(bench.core.in_phase());
  EXPECT_EQ(bench.log.Count("\"cause\":\"subscription_acknowledged\",\"phase_start_realtime_ns\":" +
                            std::to_string(Realtime(ack))),
            1);
}

TEST(ReceiverCore, RenewalAckDoesNotRestartThePhase) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  for (int renewal = 1; renewal <= 5; ++renewal) {
    const std::int64_t at = start + renewal * kS;
    bench.core.OnTick(At(at));
    bench.SdAck(at + 1 * kMs, static_cast<std::uint16_t>(renewal + 1));
  }
  EXPECT_TRUE(bench.core.in_phase());
  EXPECT_EQ(bench.core.counters().phases_started, 1U);
  EXPECT_EQ(bench.core.counters().phases_ended, 0U);
}

TEST(ReceiverCore, SecondClientIsRefusedAndStartsNoPhase) {
  Bench bench;
  bench.Subscribe(0);
  ASSERT_TRUE(bench.core.OnClientAccepted(At(100 * kMs)));
  EXPECT_FALSE(bench.core.OnClientAccepted(At(200 * kMs)));
  EXPECT_EQ(bench.core.counters().clients_refused, 1U);
  EXPECT_EQ(bench.core.counters().phases_started, 1U);
  EXPECT_EQ(bench.log.Count("\"event\":\"client_refused\""), 1);
  // The first client stays the only one: its loss ends the phase.
  bench.core.OnClientDisconnected(At(300 * kMs));
  EXPECT_FALSE(bench.core.in_phase());
  EXPECT_EQ(bench.log.Count("\"event\":\"phase_end\",\"cause\":\"client_lost\""), 1);
}

TEST(ReceiverCore, FramesOutsideAPhaseAreReadAndDropped) {
  Bench bench;
  bench.core.OnTick(At(0));
  bench.core.OnTcpConnected(At(1 * kMs), kLocal);
  bench.Data(2 * kMs, FrameNotification(1, Realtime(2 * kMs)));  // connected, not subscribed
  const std::int64_t ack = 30 * kMs;
  bench.core.OnTick(At(25 * kMs));
  bench.SdAck(ack, 1);
  bench.Data(ack + 1 * kMs, FrameNotification(2, Realtime(ack + 1 * kMs)));  // subscribed, no client
  EXPECT_EQ(bench.Dropped(DropReason::kNotSubscribed), 1U);
  EXPECT_EQ(bench.Dropped(DropReason::kNoClient), 1U);
  EXPECT_TRUE(bench.sink.delivered.empty());
  // The client connects: nothing was kept for it.
  ASSERT_TRUE(bench.core.OnClientAccepted(At(ack + 2 * kMs)));
  EXPECT_TRUE(bench.sink.delivered.empty());
  bench.ExpectBalanced();
}

TEST(ReceiverCore, MarginOfTwentyMillisecondsBeforeThePhaseStart) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  bench.Data(start + 1 * kMs, FrameNotification(10, Realtime(start) - 19 * kMs));
  bench.Data(start + 2 * kMs, FrameNotification(11, Realtime(start) - 21 * kMs));
  ASSERT_EQ(bench.sink.delivered.size(), 1U);
  EXPECT_EQ(bench.Dropped(DropReason::kOlderThanPhase), 1U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, OlderFrameThatIsNoCopyIsServedAndACopyIsDropped) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  bench.Data(start + 10 * kMs, FrameNotification(20, Realtime(start) + 9 * kMs));
  bench.Data(start + 11 * kMs, FrameNotification(19, Realtime(start) + 5 * kMs));  // older, no copy
  bench.Data(start + 12 * kMs, FrameNotification(20, Realtime(start) + 9 * kMs));  // copy
  EXPECT_EQ(bench.sink.delivered.size(), 2U);
  EXPECT_EQ(bench.Dropped(DropReason::kCopyInPhase), 1U);
  EXPECT_EQ(bench.log.Count("\"verdict\":\"copy_in_phase\""), 1);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, FieldsWithoutPositiveValueAreDropped) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  bench.Data(start + 1 * kMs, Notification(Prefixed(Frame(0, Realtime(start)))));
  bench.Data(start + 2 * kMs, Notification(Prefixed(Frame(5, 0))));
  bench.Data(start + 3 * kMs, Notification(Prefixed(Frame(6, -1))));
  // A frame without fields 3 and 4: both read as 0.
  bench.Data(start + 4 * kMs, Notification(Prefixed(Bytes{0x08, 0x01, 0x10, 0x01})));
  EXPECT_EQ(bench.Dropped(DropReason::kFieldNotPositive), 4U);
  EXPECT_TRUE(bench.sink.delivered.empty());
  bench.ExpectBalanced();
}

TEST(ReceiverCore, LossOfEitherConditionEndsThePhase) {
  Bench bench;
  std::int64_t start = StartPhase(bench);
  // TTL of the last acknowledged subscription ends without a renewal Ack.
  bench.core.OnTick(At(start + 3 * kS));
  EXPECT_FALSE(bench.core.in_phase());
  EXPECT_EQ(bench.log.Count("\"cause\":\"subscription_lost:ttl_expired\""), 1);
  bench.SdAck(start + 3 * kS + 5 * kMs, 9);
  EXPECT_TRUE(bench.core.in_phase());
  // Nack.
  bench.SdAck(start + 4 * kS, 10, 0);
  EXPECT_FALSE(bench.core.in_phase());
  EXPECT_EQ(bench.log.Count("\"cause\":\"subscription_lost:nack\""), 1);
  // Loss of the TCP connection.
  start = bench.Subscribe(start + 5 * kS, 11);
  EXPECT_TRUE(bench.core.in_phase());
  bench.core.OnTcpClosed(At(start + 1 * kS));
  EXPECT_FALSE(bench.core.in_phase());
  EXPECT_EQ(bench.log.Count("\"cause\":\"subscription_lost:tcp_closed\""), 1);
  // StopOffer.
  start = bench.Subscribe(start + 2 * kS, 12);
  EXPECT_TRUE(bench.core.in_phase());
  const Bytes stop = LoadHexFixture("sd_stop_offer");
  bench.core.OnSdDatagram(At(start + 1 * kS), kServer, true, stop.data(), stop.size());
  EXPECT_FALSE(bench.core.in_phase());
  EXPECT_EQ(bench.log.Count("\"cause\":\"subscription_lost:stop_offer\""), 1);
  EXPECT_EQ(bench.core.counters().phases_started, 4U);
  EXPECT_EQ(bench.core.counters().phases_ended, 4U);
}

TEST(ReceiverCore, StoredFramesAfterAResubscriptionAreDropped) {
  Bench bench;
  std::int64_t start = StartPhase(bench);
  bench.Data(start + 100 * kMs, FrameNotification(40, Realtime(start) + 90 * kMs));
  bench.core.OnTcpClosed(At(start + 1 * kS));
  start = bench.Subscribe(start + 5 * kS, 2);  // the client stayed: the Ack starts the phase
  ASSERT_TRUE(bench.core.in_phase());
  // Ten frames that the layer stored about 4 s before, one a copy of frame 40.
  bench.Data(start + 1 * kMs, FrameNotification(40, Realtime(start) - 4910 * kMs));
  for (std::uint64_t sequence = 41; sequence <= 49; ++sequence) {
    bench.Data(start + 1 * kMs, FrameNotification(sequence, Realtime(start) - 4000 * kMs));
  }
  bench.Data(start + 50 * kMs, FrameNotification(50, Realtime(start) + 40 * kMs));
  EXPECT_EQ(bench.Dropped(DropReason::kOlderThanPhase), 10U);
  ASSERT_EQ(bench.sink.delivered.size(), 2U);
  EXPECT_EQ(bench.core.counters().phases_started, 2U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, ServedPayloadIsUnchanged) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  Bytes stream;
  std::vector<Bytes> payloads;
  for (std::uint64_t sequence = 1; sequence <= 3; ++sequence) {
    const Bytes payload = Prefixed(Frame(sequence, Realtime(start) + static_cast<std::int64_t>(sequence) * kMs));
    payloads.push_back(payload);
    const Bytes message = Notification(payload, static_cast<std::uint16_t>(sequence));
    stream.insert(stream.end(), message.begin(), message.end());
  }
  bench.Data(start + 10 * kMs, stream);
  EXPECT_EQ(bench.sink.delivered, payloads);
  EXPECT_EQ(bench.log.Count("\"event\":\"frame\",\"verdict\":\"delivered\""), 3);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, LargestFrameOf2044BytesIsDelivered) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  Bytes frame = Frame(7, Realtime(start));
  // Pad with an unknown length-delimited field (number 16) up to 2044 bytes.
  frame.push_back(0x82);
  frame.push_back(0x01);
  const std::size_t room = 2044 - frame.size() - 2;
  PutVarint(frame, room);
  frame.insert(frame.end(), room, 0x5A);
  ASSERT_EQ(frame.size(), 2044U);
  const Bytes payload = Prefixed(frame);
  bench.Data(start + 1 * kMs, Notification(payload));
  ASSERT_EQ(bench.sink.delivered.size(), 1U);
  EXPECT_EQ(bench.sink.delivered[0], payload);
  EXPECT_EQ(bench.sink.delivered[0].size(), 2048U);
}

TEST(ReceiverCore, PayloadAboveTheSampleSizeIsDropped) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  Bytes frame = Frame(7, Realtime(start));
  frame.resize(2045, 0x00);
  bench.Data(start + 1 * kMs, Notification(Prefixed(frame)));
  EXPECT_TRUE(bench.sink.delivered.empty());
  EXPECT_EQ(bench.Dropped(DropReason::kPayloadTooLarge), 1U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, LengthPrefixMismatchIsDroppedAndTheStreamStaysIntact) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  Bytes bad = Prefixed(Frame(1, Realtime(start)));
  bad[0] = static_cast<std::uint8_t>(bad[0] + 1);  // the prefix counts one byte too many
  Bytes stream = Notification(bad);
  const Bytes good = FrameNotification(2, Realtime(start) + 1 * kMs);
  stream.insert(stream.end(), good.begin(), good.end());
  bench.Data(start + 2 * kMs, stream);
  EXPECT_EQ(bench.Dropped(DropReason::kLengthPrefixMismatch), 1U);
  ASSERT_EQ(bench.sink.delivered.size(), 1U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, SpikePayloadsWithBigEndianPrefixAreAllDropped) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  bench.Data(start + 1 * kMs, LoadHexFixture("tcp_notifications_someipd"));
  EXPECT_EQ(bench.core.counters().frames_received, 4U);
  EXPECT_EQ(bench.Dropped(DropReason::kLengthPrefixMismatch), 4U);
  EXPECT_TRUE(bench.sink.delivered.empty());
  bench.ExpectBalanced();
}

TEST(ReceiverCore, UnreadableFrameIsDropped) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  const Bytes truncated{0x08, 0x01, 0x18, 0x81};  // the varint of field 3 is cut
  bench.Data(start + 1 * kMs, Notification(Prefixed(truncated)));
  EXPECT_EQ(bench.Dropped(DropReason::kFrameUnreadable), 1U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, OtherMessagesAndMagicCookiesAreNotFrames) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  Bytes stream = Notification(Prefixed(Frame(1, Realtime(start))), 1, 0x8002);  // another event
  const Bytes cookie{0xFF, 0xFF, 0x80, 0x00, 0x00, 0x00, 0x00, 0x08,
                     0xDE, 0xAD, 0xBE, 0xEF, 0x01, 0x01, 0x02, 0x00};
  stream.insert(stream.end(), cookie.begin(), cookie.end());
  const Bytes request = Notification(Prefixed(Frame(2, Realtime(start))), 2, 0x8001, 0x00);
  stream.insert(stream.end(), request.begin(), request.end());
  bench.Data(start + 1 * kMs, stream);
  EXPECT_EQ(bench.core.counters().other_messages, 1U);
  EXPECT_EQ(bench.core.counters().magic_cookies, 1U);
  EXPECT_EQ(bench.core.counters().frames_received, 1U);
  EXPECT_EQ(bench.Dropped(DropReason::kMalformedNotification), 1U);
  EXPECT_TRUE(bench.sink.delivered.empty());
  bench.ExpectBalanced();
}

TEST(ReceiverCore, FailedWriteDropsTheFrameAndEndsThePhase) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  bench.sink.fail = true;
  bench.Data(start + 1 * kMs, FrameNotification(1, Realtime(start)));
  EXPECT_EQ(bench.Dropped(DropReason::kClientWriteFailed), 1U);
  EXPECT_FALSE(bench.core.client_connected());
  EXPECT_FALSE(bench.core.in_phase());
  EXPECT_EQ(bench.core.counters().clients_lost, 1U);
  bench.sink.fail = false;
  bench.Data(start + 2 * kMs, FrameNotification(2, Realtime(start) + 1 * kMs));
  EXPECT_EQ(bench.Dropped(DropReason::kNoClient), 1U);
  bench.ExpectBalanced();
}

TEST(ReceiverCore, LostFramingEndsTheConnectionAndResetsTheReassembly) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  Bytes broken = FrameNotification(1, Realtime(start));
  broken[7] = 0x03;  // length 3
  bench.Data(start + 1 * kMs, broken);
  EXPECT_FALSE(bench.core.subscribed());
  EXPECT_FALSE(bench.core.in_phase());
  EXPECT_EQ(bench.core.counters().stream_framing_errors, 1U);
  EXPECT_EQ(bench.transport.closes, 1);
  const std::int64_t again = bench.Subscribe(start + 1 * kS, 2);
  bench.Data(again + 1 * kMs, FrameNotification(2, Realtime(again)));
  EXPECT_EQ(bench.sink.delivered.size(), 1U);
}

TEST(ReceiverCore, PartialMessageOfAClosedConnectionIsNotDelivered) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  const Bytes message = FrameNotification(1, Realtime(start));
  bench.core.OnTcpData(At(start + 1 * kMs), message.data(), 20);
  bench.core.OnTcpClosed(At(start + 2 * kMs));
  const std::int64_t again = bench.Subscribe(start + 1 * kS, 2);
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
                          "drop_frame_unreadable", "drop_not_subscribed", "drop_no_client", "drop_field_not_positive",
                          "drop_older_than_phase", "drop_copy_in_phase", "drop_client_write_failed",
                          "frames_received", "frames_delivered", "subscription_state", "client_connected", "in_phase",
                          "phases_started", "phases_ended", "clients_refused"}) {
    EXPECT_NE(status.fields().find(std::string{"\""} + key + "\":"), std::string::npos) << key;
  }
}

TEST(ReceiverCore, ClockStepInAPhaseIsLoggedAndMarksThePhase) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  bench.core.OnTick(Clock{start + 100 * kMs, Realtime(start + 100 * kMs)});
  EXPECT_EQ(bench.log.Count("\"event\":\"clock_step\""), 0);
  // CLOCK_REALTIME jumps 5 ms ahead of CLOCK_MONOTONIC.
  bench.core.OnTick(Clock{start + 200 * kMs, Realtime(start + 200 * kMs) + 5 * kMs});
  EXPECT_EQ(bench.log.Count("\"event\":\"clock_step\",\"step_ns\":5000000"), 1);
  EXPECT_EQ(bench.core.counters().clock_steps, 1U);
  bench.core.OnClientDisconnected(Clock{start + 300 * kMs, Realtime(start + 300 * kMs) + 5 * kMs});
  EXPECT_EQ(bench.log.Count("\"event\":\"phase_end\""), 1);
  EXPECT_EQ(bench.log.Count("\"clock_steps_in_phase\":1"), 1);
}

TEST(ReceiverCore, SlowDriftIsNoClockStep) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  for (int tick = 1; tick <= 50; ++tick) {
    // 0.05 ms per 100 ms: 500 ppm, the fastest slew of the kernel's own adjustment.
    const std::int64_t t = start + tick * 100 * kMs;
    bench.core.OnTick(Clock{t, Realtime(t) + tick * 50'000});
  }
  EXPECT_EQ(bench.core.counters().clock_steps, 0U);
}

TEST(ReceiverCore, TheSlewAllowanceGrowsWithTheInterval) {
  Bench bench;
  bench.core.ObserveClock(At(0));
  // 10 s without an event: 4 ms of slew (400 ppm) is no step, 7 ms is one
  // (the allowance is 1 ms + 5 ms).
  bench.core.ObserveClock(Clock{10 * kS, Realtime(10 * kS) + 4 * kMs});
  EXPECT_EQ(bench.core.counters().clock_steps, 0U);
  bench.core.ObserveClock(Clock{20 * kS, Realtime(20 * kS) + 11 * kMs});
  EXPECT_EQ(bench.core.counters().clock_steps, 1U);
  // A step back is a step too.
  bench.core.ObserveClock(Clock{20 * kS + 100 * kMs, Realtime(20 * kS + 100 * kMs) + 9 * kMs});
  EXPECT_EQ(bench.core.counters().clock_steps, 2U);
}

TEST(ReceiverCore, PhaseStartAndFramesLogTheClockFacts) {
  ReceiverConfig config = Bench::Defaults();
  config.log_frames = false;
  Bench bench{config};
  const std::int64_t start = StartPhase(bench);
  EXPECT_EQ(bench.log.Count("\"realtime_minus_monotonic_ns\":" + std::to_string(kRealtimeBase)), 1);
  for (std::uint64_t sequence = 1; sequence <= 8; ++sequence) {
    const std::int64_t produced = Realtime(start) + static_cast<std::int64_t>(sequence) * 100 * kMs;
    // Received 3 ms after it was produced.
    bench.core.OnTcpData(At(start + static_cast<std::int64_t>(sequence) * 100 * kMs + 3 * kMs),
                         FrameNotification(sequence, produced).data(), FrameNotification(sequence, produced).size());
  }
  // Without --log-frames, the first five frames served in a phase are logged.
  EXPECT_EQ(bench.log.Count("\"event\":\"frame\""), 5);
  EXPECT_EQ(bench.log.Count("\"receipt_minus_frame_ns\":3000000"), 5);
  const std::string status = bench.core.Status("status").ToJson(At(start + kS));
  EXPECT_NE(status.find("\"frames_served_in_phase\":8,\"clock_steps_in_phase\":0,"
                        "\"receipt_minus_frame_min_ns\":3000000,\"receipt_minus_frame_max_ns\":3000000"),
            std::string::npos)
      << status;
  bench.core.OnClientDisconnected(At(start + 2 * kS));
  EXPECT_EQ(bench.log.Count("\"receipt_minus_frame_min_ns\":3000000,\"receipt_minus_frame_max_ns\":3000000"), 1);
}

// The ingress is a oneshot service that init starts on its start property.
constexpr char kIngressStart[] = "de4sdv.aebs.ingress.start";
using PropertySets = std::vector<std::pair<std::string, std::string>>;

ReceiverConfig WithIngressTrigger() {
  ReceiverConfig config = Bench::Defaults();
  config.ingress_start_property = kIngressStart;
  return config;
}

PropertySets Triggers(int count) {
  PropertySets sets;
  for (int index = 0; index < count; ++index) {
    sets.emplace_back(kIngressStart, "0");
    sets.emplace_back(kIngressStart, "1");
  }
  return sets;
}

TEST(ReceiverCore, IngressStartsAtListenAndAgainEveryTwoSecondsWithoutAClient) {
  Bench bench{WithIngressTrigger()};
  bench.core.OnListening(At(0));
  EXPECT_EQ(bench.properties.sets, Triggers(1));
  EXPECT_EQ(bench.log.Count("\"event\":\"ingress_trigger\",\"reason\":\"listening\""), 1);
  EXPECT_LE(bench.core.NextDeadline(), kIngressRetriggerPeriodNs);
  bench.core.OnTick(At(kIngressRetriggerPeriodNs - 1));
  EXPECT_EQ(bench.properties.sets, Triggers(1));
  bench.core.OnTick(At(kIngressRetriggerPeriodNs));
  EXPECT_EQ(bench.properties.sets, Triggers(2));
  bench.core.OnTick(At(2 * kIngressRetriggerPeriodNs + 50 * kMs));
  EXPECT_EQ(bench.properties.sets, Triggers(3));
  EXPECT_EQ(bench.log.Count("\"event\":\"ingress_trigger\",\"reason\":\"no_client\""), 2);
  EXPECT_EQ(bench.log.Count("\"triggers_without_client\":3"), 1);
  EXPECT_EQ(bench.core.counters().ingress_triggers, 3U);
}

TEST(ReceiverCore, NoIngressTriggerWhileAClientIsConnected) {
  Bench bench{WithIngressTrigger()};
  bench.core.OnListening(At(0));
  ASSERT_TRUE(bench.core.OnClientAccepted(At(100 * kMs)));
  for (std::int64_t t = kS; t <= 20 * kS; t += kS) {
    bench.core.OnTick(At(t));
  }
  EXPECT_EQ(bench.properties.sets, Triggers(1));
  // The ingress exits: the first trigger comes one period after the loss.
  bench.core.OnClientDisconnected(At(20 * kS + 300 * kMs));
  bench.core.OnTick(At(20 * kS + 300 * kMs + kIngressRetriggerPeriodNs - 1));
  EXPECT_EQ(bench.properties.sets, Triggers(1));
  bench.core.OnTick(At(20 * kS + 300 * kMs + kIngressRetriggerPeriodNs));
  EXPECT_EQ(bench.properties.sets, Triggers(2));
  EXPECT_EQ(bench.log.Count("\"reason\":\"no_client\",\"property\":\"de4sdv.aebs.ingress.start\",\"ok\":true,"
                            "\"triggers_without_client\":1"),
            1);
}

TEST(ReceiverCore, NoIngressTriggerBeforeListenAfterStopOrWithoutAProperty) {
  Bench bench{WithIngressTrigger()};
  bench.core.OnTick(At(5 * kS));
  EXPECT_TRUE(bench.properties.sets.empty());
  bench.core.OnListening(At(6 * kS));
  bench.core.Stop(At(7 * kS));
  bench.core.OnTick(At(30 * kS));
  EXPECT_EQ(bench.properties.sets, Triggers(1));

  Bench without;
  without.core.OnListening(At(0));
  without.core.OnTick(At(10 * kS));
  EXPECT_TRUE(without.properties.sets.empty());
  EXPECT_EQ(without.log.Count("ingress_trigger"), 0);
}

TEST(ReceiverCore, AFailedIngressTriggerIsLoggedAndRepeated) {
  Bench bench{WithIngressTrigger()};
  bench.properties.ok = false;
  bench.core.OnListening(At(0));
  EXPECT_EQ(bench.log.Count("\"ok\":false"), 1);
  bench.properties.ok = true;
  bench.core.OnTick(At(kIngressRetriggerPeriodNs));
  EXPECT_EQ(bench.properties.sets, Triggers(2));
}

TEST(ReceiverCore, StopSendsStopSubscribeAndEndsThePhase) {
  Bench bench;
  const std::int64_t start = StartPhase(bench);
  const int sent = bench.transport.sent;
  bench.core.Stop(At(start + 1 * kS));
  EXPECT_EQ(bench.transport.sent, sent + 1);
  EXPECT_FALSE(bench.core.subscribed());
  EXPECT_FALSE(bench.core.in_phase());
}

}  // namespace
