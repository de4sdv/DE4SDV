// Unit tests of the subscription state machine of the pure receiver core:
// TCP first, then SubscribeEventgroup with the local TCP endpoint; Ack,
// Nack, TTL renewal and expiry; offers, StopOffer and server reboots; the
// unicast fallback without any offer. The SD datagrams of someipd come from
// golden fixtures where the test needs real bytes.

#include <gtest/gtest.h>

#include <cstdint>
#include <string>
#include <vector>

#include "de4sdv_someip_receiver/subscription.hpp"
#include "fixture_loader.hpp"

namespace {

using de4sdv::someip_receiver::Clock;
using de4sdv::someip_receiver::EncodeSubscribeEventgroup;
using de4sdv::someip_receiver::EventLog;
using de4sdv::someip_receiver::Ipv4Endpoint;
using de4sdv::someip_receiver::kL4ProtocolTcp;
using de4sdv::someip_receiver::kNoDeadline;
using de4sdv::someip_receiver::LogRecord;
using de4sdv::someip_receiver::ParseSdMessage;
using de4sdv::someip_receiver::SdEntry;
using de4sdv::someip_receiver::SdEntryType;
using de4sdv::someip_receiver::SdMessage;
using de4sdv::someip_receiver::SubscribeRequest;
using de4sdv::someip_receiver::SubscriptionConfig;
using de4sdv::someip_receiver::SubscriptionListener;
using de4sdv::someip_receiver::SubscriptionLoss;
using de4sdv::someip_receiver::SubscriptionMachine;
using de4sdv::someip_receiver::SubscriptionState;
using de4sdv::someip_receiver::SubscriptionTransport;
using de4sdv::someip_receiver::test::Bytes;
using de4sdv::someip_receiver::test::LoadHexFixture;

constexpr std::int64_t kMs = 1'000'000;
constexpr std::int64_t kS = 1'000'000'000;
constexpr std::uint32_t kServer = 0x0AFA0001;  // 10.250.0.1
constexpr std::uint32_t kGuest = 0x0AFA0002;   // 10.250.0.2
constexpr std::uint32_t kOther = 0x0AFA0009;
const Ipv4Endpoint kLocal{kGuest, 35005, kL4ProtocolTcp};
const Ipv4Endpoint kServerTcp{kServer, 30509, kL4ProtocolTcp};

struct SentDatagram {
  Bytes bytes;
  std::uint32_t address;
  std::uint16_t port;
};

class FakeTransport : public SubscriptionTransport {
 public:
  void ConnectTcp(const Ipv4Endpoint& server) override { connects.push_back(server); }
  void CloseTcp() override { ++closes; }
  bool SendSd(const std::vector<std::uint8_t>& datagram, std::uint32_t address, std::uint16_t port) override {
    sent.push_back(SentDatagram{datagram, address, port});
    return send_ok;
  }

  std::vector<Ipv4Endpoint> connects;
  int closes{0};
  std::vector<SentDatagram> sent;
  bool send_ok{true};
};

class FakeListener : public SubscriptionListener {
 public:
  void OnSubscribed(const Clock& now) override { subscribed_at.push_back(now.monotonic_ns); }
  void OnSubscriptionLost(const Clock& now, SubscriptionLoss loss) override {
    lost_at.push_back(now.monotonic_ns);
    losses.push_back(loss);
  }
  std::vector<std::int64_t> subscribed_at;
  std::vector<std::int64_t> lost_at;
  std::vector<SubscriptionLoss> losses;
};

class RecordingLog : public EventLog {
 public:
  void Log(const Clock&, const LogRecord& record) override { events.push_back(record.event()); }
  std::vector<std::string> events;
  bool Has(const std::string& event) const {
    for (const auto& item : events) {
      if (item == event) {
        return true;
      }
    }
    return false;
  }
};

Clock At(std::int64_t monotonic_ns) { return Clock{monotonic_ns, 1'793'000'000'000'000'000 + monotonic_ns}; }

SdMessage Parsed(const Bytes& datagram) {
  const auto result = ParseSdMessage(datagram.data(), datagram.size());
  EXPECT_TRUE(result.message.has_value());
  return result.message.value_or(SdMessage{});
}

SdMessage Fixture(const std::string& name) { return Parsed(LoadHexFixture(name)); }

SdEntry Entry(SdEntryType type, std::uint32_t ttl, std::uint16_t eventgroup = 0x0001) {
  SdEntry entry;
  entry.type = static_cast<std::uint8_t>(type);
  entry.service_id = 0x4DEE;
  entry.instance_id = 0x0001;
  entry.major_version = 1;
  entry.ttl = ttl;
  entry.eventgroup_id = eventgroup;
  return entry;
}

SdMessage Message(std::uint16_t session, std::vector<SdEntry> entries, bool reboot = true) {
  SdMessage message;
  message.session_id = session;
  message.reboot = reboot;
  message.unicast = true;
  message.entries = std::move(entries);
  return message;
}

SdMessage Ack(std::uint16_t session, std::uint32_t ttl = 3) {
  return Message(session, {Entry(SdEntryType::kSubscribeEventgroupAck, ttl)});
}

SdMessage Offer(std::uint16_t session, std::uint32_t ttl = 3, bool reboot = true) {
  SdEntry entry = Entry(SdEntryType::kOfferService, ttl);
  entry.endpoints.push_back(kServerTcp);
  return Message(session, {entry}, reboot);
}

struct Bench {
  SubscriptionConfig config;
  FakeTransport transport;
  FakeListener listener;
  RecordingLog log;
  SubscriptionMachine machine;

  explicit Bench(SubscriptionConfig base = Defaults()) : config{base}, machine{config, transport, listener, log} {}

  static SubscriptionConfig Defaults() {
    SubscriptionConfig config;
    config.server_address = kServer;
    return config;
  }

  // Connects through the fallback at time t and returns the time of the first subscribe.
  std::int64_t ConnectAndSubscribe(std::int64_t t) {
    machine.OnTick(At(t));
    machine.OnTcpConnected(At(t + 1 * kMs), kLocal);
    const std::int64_t subscribe_at = t + 1 * kMs + config.subscribe_delay_ns;
    machine.OnTick(At(subscribe_at));
    return subscribe_at;
  }

  SdMessage LastSent() const { return Parsed(transport.sent.back().bytes); }
};

TEST(SubscriptionMachine, FallbackConnectsToTheConfiguredServerWithoutAnOffer) {
  Bench bench;
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kIdle);
  bench.machine.OnTick(At(0));
  ASSERT_EQ(bench.transport.connects.size(), 1U);
  EXPECT_EQ(bench.transport.connects[0], kServerTcp);
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kConnecting);
  EXPECT_FALSE(bench.machine.has_offer());
}

TEST(SubscriptionMachine, FirstSubscribeWaitsForTheDelayAndEqualsTheVsomeipClientBytes) {
  Bench bench;
  bench.machine.OnTick(At(0));
  bench.machine.OnTcpConnected(At(1 * kMs), kLocal);
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kSubscribing);
  bench.machine.OnTick(At(1 * kMs + bench.config.subscribe_delay_ns - 1));
  EXPECT_TRUE(bench.transport.sent.empty());
  bench.machine.OnTick(At(1 * kMs + bench.config.subscribe_delay_ns));
  ASSERT_EQ(bench.transport.sent.size(), 1U);
  EXPECT_EQ(bench.transport.sent[0].address, kServer);
  EXPECT_EQ(bench.transport.sent[0].port, 30490);
  // The vsomeip 3.7.6 client sent these bytes from 10.250.0.2:35005 with session 1.
  EXPECT_EQ(bench.transport.sent[0].bytes, LoadHexFixture("sd_subscribe_from_vsomeip_client"));
}

TEST(SubscriptionMachine, AckStartsOnePhaseAndRenewalsKeepIt) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t + 1 * kMs), Fixture("sd_subscribe_ack"), kServer, false);
  EXPECT_TRUE(bench.machine.subscribed());
  ASSERT_EQ(bench.listener.subscribed_at.size(), 1U);
  EXPECT_EQ(bench.listener.subscribed_at[0], t + 1 * kMs);
  for (int renewal = 1; renewal <= 5; ++renewal) {
    const std::int64_t at = t + 1 * kMs + renewal * bench.config.renew_period_ns;
    bench.machine.OnTick(At(at));
    EXPECT_EQ(bench.LastSent().session_id, renewal + 1);
    EXPECT_EQ(bench.LastSent().entries.at(0).ttl, 3U);
    bench.machine.OnSdMessage(At(at + 1 * kMs), Ack(static_cast<std::uint16_t>(renewal + 1)), kServer, false);
  }
  EXPECT_TRUE(bench.machine.subscribed());
  EXPECT_EQ(bench.listener.subscribed_at.size(), 1U);
  EXPECT_TRUE(bench.listener.losses.empty());
  EXPECT_EQ(bench.machine.counters().acks, 6U);
  EXPECT_EQ(bench.machine.counters().subscribes_sent, 6U);
}

TEST(SubscriptionMachine, TtlEndsWithoutAckSoTheSubscriptionIsLost) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t), Ack(1), kServer, false);
  bench.machine.OnTick(At(t + 1 * kS));
  bench.machine.OnTick(At(t + 2 * kS));
  bench.machine.OnTick(At(t + 3 * kS - 1));
  EXPECT_TRUE(bench.machine.subscribed());
  const std::size_t sent_before = bench.transport.sent.size();
  bench.machine.OnTick(At(t + 3 * kS));
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kSubscribing);
  ASSERT_EQ(bench.listener.losses.size(), 1U);
  EXPECT_EQ(bench.listener.losses[0], SubscriptionLoss::kTtlExpired);
  EXPECT_EQ(bench.machine.counters().ttl_expiries, 1U);
  // The TCP connection stays; the machine subscribes again in the same tick.
  EXPECT_EQ(bench.transport.closes, 0);
  EXPECT_EQ(bench.transport.sent.size(), sent_before + 1);
  EXPECT_EQ(bench.LastSent().entries.at(0).ttl, 3U);
  bench.machine.OnSdMessage(At(t + 3 * kS + 1 * kMs), Ack(9), kServer, false);
  EXPECT_TRUE(bench.machine.subscribed());
  EXPECT_EQ(bench.listener.subscribed_at.size(), 2U);
}

TEST(SubscriptionMachine, NoAckWithinTheTimeoutClosesTheConnection) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  const std::int64_t since = 1 * kMs;
  bench.machine.OnTick(At(since + bench.config.subscribe_timeout_ns - 1));
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kSubscribing);
  bench.machine.OnTick(At(since + bench.config.subscribe_timeout_ns));
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kIdle);
  EXPECT_EQ(bench.transport.closes, 1);
  EXPECT_EQ(bench.machine.counters().subscribe_timeouts, 1U);
  EXPECT_TRUE(bench.listener.losses.empty());  // it was never subscribed
  const std::int64_t retry = since + bench.config.subscribe_timeout_ns + bench.config.connect_retry_period_ns;
  bench.machine.OnTick(At(retry - 1));
  EXPECT_EQ(bench.transport.connects.size(), 1U);
  bench.machine.OnTick(At(retry));
  EXPECT_EQ(bench.transport.connects.size(), 2U);
  (void)t;
}

TEST(SubscriptionMachine, NackClosesTheConnectionAndRetriesLater) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t + 1 * kMs), Fixture("sd_subscribe_nack_offer_pending"), kServer, false);
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kIdle);
  EXPECT_EQ(bench.transport.closes, 1);
  EXPECT_EQ(bench.machine.counters().nacks, 1U);
  EXPECT_TRUE(bench.listener.subscribed_at.empty());
  bench.machine.OnTick(At(t + 1 * kMs + bench.config.connect_retry_period_ns));
  EXPECT_EQ(bench.transport.connects.size(), 2U);
}

TEST(SubscriptionMachine, NackWhileSubscribedEndsThePhase) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t), Ack(1), kServer, false);
  bench.machine.OnSdMessage(At(t + 1 * kS), Ack(2, 0), kServer, false);
  ASSERT_EQ(bench.listener.losses.size(), 1U);
  EXPECT_EQ(bench.listener.losses[0], SubscriptionLoss::kNack);
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kIdle);
}

TEST(SubscriptionMachine, OfferStartsAConnectionAtOnce) {
  SubscriptionConfig config = Bench::Defaults();
  config.reliable_port = 40000;  // the offer names 30509
  Bench bench{config};
  bench.machine.OnTick(At(0));  // fallback attempt
  bench.machine.OnTcpConnectFailed(At(1 * kMs), 111);
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kIdle);
  bench.machine.OnSdMessage(At(5 * kMs), Fixture("sd_offer_multicast"), kServer, true);
  ASSERT_EQ(bench.transport.connects.size(), 2U);
  EXPECT_EQ(bench.transport.connects[1], kServerTcp);
  EXPECT_TRUE(bench.machine.has_offer());
  EXPECT_EQ(bench.machine.counters().offers, 1U);
  EXPECT_EQ(bench.machine.counters().tcp_connect_failures, 1U);
}

TEST(SubscriptionMachine, OfferEndsAfterItsTtl) {
  Bench bench;
  bench.machine.OnSdMessage(At(0), Offer(1), kServer, true);
  EXPECT_TRUE(bench.machine.has_offer());
  bench.machine.OnTick(At(3 * kS));
  EXPECT_FALSE(bench.machine.has_offer());
}

TEST(SubscriptionMachine, OtherSendersAreIgnored) {
  Bench bench;
  bench.machine.OnTick(At(0));
  bench.machine.OnTcpConnectFailed(At(1 * kMs), 113);
  bench.machine.OnSdMessage(At(2 * kMs), Fixture("sd_offer_multicast"), kOther, true);
  EXPECT_EQ(bench.transport.connects.size(), 1U);
  EXPECT_FALSE(bench.machine.has_offer());
  EXPECT_EQ(bench.machine.counters().sd_messages_from_other_senders, 1U);
}

TEST(SubscriptionMachine, FindServiceOfAnotherClientIsIgnored) {
  Bench bench;
  bench.machine.OnSdMessage(At(0), Fixture("sd_find_service_from_vsomeip_client"), kServer, true);
  EXPECT_EQ(bench.machine.counters().sd_entries_ignored, 1U);
  EXPECT_TRUE(bench.transport.connects.empty());
}

TEST(SubscriptionMachine, StopOfferEndsThePhaseAndTheConnection) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t), Offer(1), kServer, true);
  bench.machine.OnSdMessage(At(t + 1 * kMs), Ack(1), kServer, false);
  bench.machine.OnSdMessage(At(t + 2 * kS), Fixture("sd_stop_offer"), kServer, true);
  ASSERT_EQ(bench.listener.losses.size(), 1U);
  EXPECT_EQ(bench.listener.losses[0], SubscriptionLoss::kStopOffer);
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kIdle);
  EXPECT_EQ(bench.transport.closes, 1);
  EXPECT_FALSE(bench.machine.has_offer());
  EXPECT_EQ(bench.machine.counters().stop_offers, 1U);
}

TEST(SubscriptionMachine, ClosedTcpConnectionEndsThePhaseAndReconnects) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t), Ack(1), kServer, false);
  bench.machine.OnTcpClosed(At(t + 1 * kS));
  ASSERT_EQ(bench.listener.losses.size(), 1U);
  EXPECT_EQ(bench.listener.losses[0], SubscriptionLoss::kTcpClosed);
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kIdle);
  EXPECT_EQ(bench.machine.counters().tcp_closed_by_peer, 1U);
  bench.machine.OnTick(At(t + 1 * kS + bench.config.connect_retry_period_ns));
  EXPECT_EQ(bench.transport.connects.size(), 2U);
}

TEST(SubscriptionMachine, ConnectAttemptTimesOut) {
  Bench bench;
  bench.machine.OnTick(At(0));
  bench.machine.OnTick(At(bench.config.connect_timeout_ns - 1));
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kConnecting);
  bench.machine.OnTick(At(bench.config.connect_timeout_ns));
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kIdle);
  EXPECT_EQ(bench.transport.closes, 1);
  EXPECT_EQ(bench.machine.counters().tcp_connect_failures, 1U);
}

TEST(SubscriptionMachine, ServerRebootSeenInTheOffersEndsTheOldConnection) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t), Fixture("sd_offer_before_restart_last"), kServer, true);  // session 7
  bench.machine.OnSdMessage(At(t + 1 * kMs), Ack(5), kServer, false);
  ASSERT_TRUE(bench.machine.subscribed());
  // The restarted someipd offers with session 1 and the reboot flag.
  bench.machine.OnSdMessage(At(t + 2 * kS), Fixture("sd_offer_after_someipd_restart"), kServer, true);
  EXPECT_EQ(bench.machine.counters().server_reboots_detected, 1U);
  ASSERT_EQ(bench.listener.losses.size(), 1U);
  EXPECT_EQ(bench.listener.losses[0], SubscriptionLoss::kServerReboot);
  EXPECT_EQ(bench.transport.closes, 1);
  // The same message is a valid offer, so the machine connects again at once.
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kConnecting);
  EXPECT_EQ(bench.transport.connects.size(), 2U);
}

TEST(SubscriptionMachine, AckFromARestartedServerKeepsTheNewConnection) {
  Bench bench;
  std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t), Ack(6, 3), kServer, false);
  bench.machine.OnTcpClosed(At(t + 1 * kS));
  t = bench.ConnectAndSubscribe(t + 2 * kS);
  // The first unicast message of the restarted server: session 1 with the reboot flag.
  bench.machine.OnSdMessage(At(t + 1 * kMs), Ack(1), kServer, false);
  EXPECT_EQ(bench.machine.counters().server_reboots_detected, 1U);
  EXPECT_TRUE(bench.machine.subscribed());
  // One close only: the release of the connection that the peer closed.
  EXPECT_EQ(bench.transport.closes, 1);
}

TEST(SubscriptionMachine, SessionWrapsToOneAndClearsTheRebootFlag) {
  SubscriptionConfig config = Bench::Defaults();
  config.renew_period_ns = 1;
  config.subscribe_delay_ns = 0;
  Bench bench{config};
  bench.machine.OnTick(At(0));
  bench.machine.OnTcpConnected(At(1), kLocal);
  bench.machine.OnTick(At(1));
  bench.machine.OnSdMessage(At(1), Ack(1, 0xFFFFFF), kServer, false);
  std::int64_t now = 1;
  // Bounded loop: a machine that sends nothing must fail, not hang.
  for (int tick = 0; tick < 0x10000 && bench.machine.counters().subscribes_sent < 0xFFFFU; ++tick) {
    ++now;
    bench.machine.OnTick(At(now));
  }
  ASSERT_EQ(bench.machine.counters().subscribes_sent, 0xFFFFU);
  EXPECT_EQ(bench.LastSent().session_id, 0xFFFF);
  EXPECT_TRUE(bench.LastSent().reboot);
  ++now;
  bench.machine.OnTick(At(now));
  EXPECT_EQ(bench.LastSent().session_id, 1);
  EXPECT_FALSE(bench.LastSent().reboot);
}

TEST(SubscriptionMachine, FailedSendIsCountedAndRetried) {
  Bench bench;
  bench.transport.send_ok = false;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  EXPECT_EQ(bench.machine.counters().subscribe_send_failures, 1U);
  bench.transport.send_ok = true;
  bench.machine.OnTick(At(t + bench.config.renew_period_ns));
  EXPECT_EQ(bench.machine.counters().subscribes_sent, 1U);
}

TEST(SubscriptionMachine, EverySdMessageGetsANewSessionId) {
  // someipd takes a session ID that does not grow, with the reboot flag set,
  // as a reboot of the receiver and expires its subscription. So no ID is
  // used twice, also not after a failed send.
  Bench bench;
  bench.transport.send_ok = false;
  std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.transport.send_ok = true;
  t += bench.config.renew_period_ns;
  bench.machine.OnTick(At(t));
  bench.machine.OnSdMessage(At(t), Ack(1), kServer, false);
  for (int renewal = 1; renewal <= 3; ++renewal) {
    t += bench.config.renew_period_ns;
    bench.machine.OnTick(At(t));
  }
  bench.machine.Stop(At(t + 1));
  std::vector<std::uint16_t> sessions;
  for (const auto& sent : bench.transport.sent) {
    sessions.push_back(Parsed(sent.bytes).session_id);
  }
  // Session 1 went to the failed send; the next messages take 2, 3, ...
  EXPECT_EQ(sessions, (std::vector<std::uint16_t>{1, 2, 3, 4, 5, 6}));
  EXPECT_EQ(bench.machine.next_session_id(), 7);
}

TEST(SubscriptionMachine, AckForAnotherEventgroupIsNotOurs) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t), Message(1, {Entry(SdEntryType::kSubscribeEventgroupAck, 3, 0x0002)}), kServer,
                            false);
  EXPECT_FALSE(bench.machine.subscribed());
  EXPECT_EQ(bench.machine.counters().sd_entries_ignored, 1U);
}

TEST(SubscriptionMachine, StrayAckWithoutAConnectionIsCounted) {
  Bench bench;
  bench.machine.OnSdMessage(At(0), Ack(1), kServer, false);
  EXPECT_FALSE(bench.machine.subscribed());
  EXPECT_EQ(bench.machine.counters().acks_unexpected, 1U);
}

TEST(SubscriptionMachine, StopSendsStopSubscribeAndCloses) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t), Ack(1), kServer, false);
  bench.machine.Stop(At(t + 1 * kS));
  const SdMessage stop = bench.LastSent();
  EXPECT_EQ(stop.entries.at(0).type, static_cast<std::uint8_t>(SdEntryType::kSubscribeEventgroup));
  EXPECT_EQ(stop.entries.at(0).ttl, 0U);
  EXPECT_EQ(bench.machine.state(), SubscriptionState::kStopped);
  EXPECT_EQ(bench.transport.closes, 1);
  ASSERT_EQ(bench.listener.losses.size(), 1U);
  EXPECT_EQ(bench.listener.losses[0], SubscriptionLoss::kStopped);
  bench.machine.OnTick(At(t + 10 * kS));
  EXPECT_EQ(bench.transport.connects.size(), 1U);
  EXPECT_EQ(bench.machine.NextDeadline(), kNoDeadline);
}

TEST(SubscriptionMachine, FramingLossEndsTheConnection) {
  Bench bench;
  const std::int64_t t = bench.ConnectAndSubscribe(0);
  bench.machine.OnSdMessage(At(t), Ack(1), kServer, false);
  bench.machine.OnStreamFramingLost(At(t + 1 * kMs));
  ASSERT_EQ(bench.listener.losses.size(), 1U);
  EXPECT_EQ(bench.listener.losses[0], SubscriptionLoss::kStreamFramingLost);
  EXPECT_EQ(bench.transport.closes, 1);
}

TEST(SubscriptionMachine, NextDeadlineFollowsTheState) {
  Bench bench;
  EXPECT_EQ(bench.machine.NextDeadline(), 0);
  bench.machine.OnTick(At(0));
  EXPECT_EQ(bench.machine.NextDeadline(), bench.config.connect_timeout_ns);
  bench.machine.OnTcpConnected(At(10 * kMs), kLocal);
  EXPECT_EQ(bench.machine.NextDeadline(), 10 * kMs + bench.config.subscribe_delay_ns);
  bench.machine.OnTick(At(10 * kMs + bench.config.subscribe_delay_ns));
  bench.machine.OnSdMessage(At(40 * kMs), Ack(1), kServer, false);
  EXPECT_EQ(bench.machine.NextDeadline(), 40 * kMs + bench.config.renew_period_ns);
}

TEST(SubscriptionMachine, GoldenExchangeOfTheVsomeipClient) {
  // The offer, the connection and the subscribe of the client, then the Ack of someipd.
  Bench bench;
  bench.machine.OnSdMessage(At(0), Fixture("sd_offer_multicast"), kServer, true);
  ASSERT_EQ(bench.transport.connects.size(), 1U);
  EXPECT_EQ(bench.transport.connects[0], kServerTcp);
  bench.machine.OnTcpConnected(At(200'000), kLocal);
  bench.machine.OnTick(At(200'000 + bench.config.subscribe_delay_ns));
  ASSERT_EQ(bench.transport.sent.size(), 1U);
  EXPECT_EQ(bench.transport.sent[0].bytes, LoadHexFixture("sd_subscribe_from_vsomeip_client"));
  bench.machine.OnSdMessage(At(25 * kMs), Fixture("sd_subscribe_ack"), kServer, false);
  EXPECT_TRUE(bench.machine.subscribed());
  EXPECT_EQ(bench.machine.counters().server_reboots_detected, 0U);
  EXPECT_TRUE(bench.log.Has("subscribed"));
}

}  // namespace
