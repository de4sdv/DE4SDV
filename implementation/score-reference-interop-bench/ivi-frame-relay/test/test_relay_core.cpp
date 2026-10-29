// Unit tests of the relay core: the subscription phase of the model, the
// checks of each slot with their drop reasons, the unchanged payload, the
// phase ends of the layer, the second client, DATA_LOSS, the ingress
// trigger, the clock controls, the start diagnostic and the stalled call.

#include <gtest/gtest.h>

#include <algorithm>
#include <cstdint>
#include <string>
#include <utility>
#include <vector>

#include "de4sdv_ivi_frame_relay/discard_policy.hpp"
#include "de4sdv_ivi_frame_relay/relay_core.hpp"
#include "fake_gateway_client.hpp"

namespace {

using de4sdv::ivi_frame_relay::Clock;
using de4sdv::ivi_frame_relay::DropReason;
using de4sdv::ivi_frame_relay::EventLog;
using de4sdv::ivi_frame_relay::FrameSink;
using de4sdv::ivi_frame_relay::GatewayCallMonitor;
using de4sdv::ivi_frame_relay::GatewayNotificationKind;
using de4sdv::ivi_frame_relay::GatewayResult;
using de4sdv::ivi_frame_relay::kDropReasonCount;
using de4sdv::ivi_frame_relay::LogRecord;
using de4sdv::ivi_frame_relay::PhaseStartDiscardPolicy;
using de4sdv::ivi_frame_relay::PropertySetter;
using de4sdv::ivi_frame_relay::RelayConfig;
using de4sdv::ivi_frame_relay::RelayCore;
using de4sdv::ivi_frame_relay::SubscriptionEnd;
using de4sdv::ivi_frame_relay::ToText;
using de4sdv::ivi_frame_relay::WorkerEvent;
using de4sdv::ivi_frame_relay::WorkerEventKind;
using de4sdv::ivi_frame_relay::test::Bytes;
using de4sdv::ivi_frame_relay::test::FramePayload;
using de4sdv::ivi_frame_relay::test::FrameSlot;
using de4sdv::ivi_frame_relay::test::kMs;
using de4sdv::ivi_frame_relay::test::kSecond;
using de4sdv::ivi_frame_relay::test::kSlotBytes;
using de4sdv::ivi_frame_relay::test::kStartClock;
using de4sdv::ivi_frame_relay::test::Prefixed;
using de4sdv::ivi_frame_relay::test::WrapLikeBroker;

class RecordingSink final : public FrameSink {
 public:
  bool Forward(const std::uint8_t* payload, std::size_t size) override {
    if (fail) {
      return false;
    }
    written.emplace_back(payload, payload + size);
    return true;
  }
  std::vector<Bytes> written;
  bool fail{false};
};

class RecordingLog final : public EventLog {
 public:
  void Log(const Clock& now, const LogRecord& record) override {
    events.push_back(record.event());
    lines.push_back(record.ToJson(now));
  }
  std::size_t Count(const std::string& event) const {
    return static_cast<std::size_t>(std::count(events.begin(), events.end(), event));
  }
  // The last line of the event; empty when none.
  std::string Last(const std::string& event) const {
    for (std::size_t index = events.size(); index > 0; --index) {
      if (events[index - 1] == event) {
        return lines[index - 1];
      }
    }
    return {};
  }
  std::vector<std::string> events;
  std::vector<std::string> lines;
};

class RecordingProperties final : public PropertySetter {
 public:
  bool SetProperty(const Clock&, const std::string& name, const std::string& value) override {
    set.emplace_back(name, value);
    return true;
  }
  std::vector<std::pair<std::string, std::string>> set;
};

bool Has(const std::string& line, const std::string& text) { return line.find(text) != std::string::npos; }

struct Harness {
  explicit Harness(RelayConfig relay = RelayConfig{}) : config{std::move(relay)} {}

  RelayConfig config;
  RecordingSink sink;
  RecordingLog log;
  RecordingProperties properties;
  PhaseStartDiscardPolicy policy;
  GatewayCallMonitor monitor;
  RelayCore core{config, sink, policy, log, &properties, &monitor};
  Clock now = kStartClock;

  const Clock& Advance(std::int64_t ns) {
    now.monotonic_ns += ns;
    now.realtime_ns += ns;
    return now;
  }

  WorkerEvent Event(WorkerEventKind kind) const {
    WorkerEvent event;
    event.kind = kind;
    event.at = now;
    event.subscription = subscription;
    event.publication.publication_id = publication_id;
    event.publication.message_size_bytes = kSlotBytes;
    event.publication.message_count = 16;
    return event;
  }

  void Subscribe() {
    ++subscription;
    ++publication_id;
    core.OnWorkerEvent(Event(WorkerEventKind::kSubscribed));
  }

  void End(SubscriptionEnd end) {
    WorkerEvent event = Event(WorkerEventKind::kSubscriptionEnded);
    event.end = end;
    core.OnWorkerEvent(event);
  }

  void Slot(const Bytes& slot) {
    WorkerEvent event = Event(WorkerEventKind::kMessage);
    event.slot = slot;
    core.OnWorkerEvent(event);
  }

  // A frame produced offset_ns after the phase start (negative: before).
  void Frame(std::uint64_t sequence, std::int64_t offset_ns) {
    Slot(FrameSlot(sequence, core.phase_start_realtime_ns() + offset_ns));
  }

  void Connect() { ASSERT_TRUE(core.OnClientAccepted(now)); }

  std::uint64_t Drops(DropReason reason) const {
    return core.counters().drops.at(static_cast<std::size_t>(reason));
  }

  std::uint64_t subscription{0};
  std::int32_t publication_id{1};
};

TEST(RelayCore, PhaseStartsWhenTheClientJoinsASubscription) {
  Harness h;
  h.Subscribe();
  EXPECT_FALSE(h.core.in_phase());
  h.Advance(250 * kMs);
  h.Connect();
  ASSERT_TRUE(h.core.in_phase());
  EXPECT_EQ(h.core.phase_start_realtime_ns(), h.now.realtime_ns);
  EXPECT_TRUE(Has(h.log.Last("phase_start"), "\"cause\":\"client_connected\""));
  EXPECT_EQ(h.core.counters().phases_started, 1U);
}

TEST(RelayCore, PhaseStartsWhenTheSubscriptionJoinsAClient) {
  Harness h;
  h.Connect();
  EXPECT_FALSE(h.core.in_phase());
  h.Advance(400 * kMs);
  h.Subscribe();
  ASSERT_TRUE(h.core.in_phase());
  EXPECT_EQ(h.core.phase_start_realtime_ns(), h.now.realtime_ns);
  EXPECT_TRUE(Has(h.log.Last("phase_start"), "\"cause\":\"subscribed\""));
}

TEST(RelayCore, PhaseStartIsTheLaterConditionAlsoWhenTheEventsComeLate) {
  Harness h;
  const Clock subscribed_at = h.now;
  h.Advance(30 * kMs);
  h.Connect();  // the main thread accepts first
  WorkerEvent late = h.Event(WorkerEventKind::kSubscribed);
  late.at = subscribed_at;  // the worker's earlier stamp, processed later
  late.subscription = 1;
  h.core.OnWorkerEvent(late);
  ASSERT_TRUE(h.core.in_phase());
  EXPECT_EQ(h.core.phase_start_realtime_ns(), h.now.realtime_ns);
}

TEST(RelayCore, MarginOfTwentyMillisecondsBeforeThePhaseStart) {
  Harness h;
  h.Subscribe();
  h.Connect();
  h.Advance(5 * kMs);
  h.Frame(1, -19 * kMs);
  h.Frame(2, -21 * kMs);
  h.Frame(3, 0);
  EXPECT_EQ(h.core.counters().frames_delivered, 2U);
  EXPECT_EQ(h.Drops(DropReason::kOlderThanPhase), 1U);
  EXPECT_EQ(PhaseStartDiscardPolicy::kPhaseStartMarginNs, 20 * kMs);
}

TEST(RelayCore, ServedBytesAreThePayloadOfTheWrapperUnchanged) {
  Harness h;
  h.Subscribe();
  h.Connect();
  const Bytes payload = FramePayload(7, h.core.phase_start_realtime_ns() + 1 * kMs, 300);
  h.Slot(WrapLikeBroker(payload));
  ASSERT_EQ(h.sink.written.size(), 1U);
  EXPECT_EQ(h.sink.written[0], payload);
}

TEST(RelayCore, OutsideAPhaseEverySlotIsReadAndDropped) {
  Harness h;
  h.Slot(FrameSlot(1, h.now.realtime_ns));
  EXPECT_EQ(h.Drops(DropReason::kNotSubscribed), 1U);
  h.Subscribe();
  h.Slot(FrameSlot(2, h.now.realtime_ns));
  EXPECT_EQ(h.Drops(DropReason::kNoClient), 1U);
  EXPECT_TRUE(h.sink.written.empty());
  EXPECT_TRUE(Has(h.log.Last("frame"), "\"verdict\":\"no_client\""));
}

TEST(RelayCore, EachMalformedSlotIsDroppedWithItsOwnReason) {
  Harness h;
  h.Subscribe();
  h.Connect();
  const Bytes good = FrameSlot(1, h.now.realtime_ns);
  Bytes bad_outer = good;
  bad_outer[0] = 0x80;
  bad_outer[1] = 0x80;
  bad_outer[2] = 0x80;
  bad_outer[3] = 0x80;
  bad_outer[4] = 0x80;
  Bytes too_long = good;
  too_long[0] = 0xFF;
  too_long[1] = 0x7F;  // 16383 bytes do not fit the 4101-byte slot
  Bytes empty(kSlotBytes, 0U);
  Bytes wrong_tag = good;
  wrong_tag[1] = 0x12;
  Bytes after_field = WrapLikeBroker(Bytes(10, 0x01));
  after_field[0] = static_cast<std::uint8_t>(after_field[0] + 2U);  // two more bytes in the message
  after_field[13] = 0x10;
  after_field[14] = 0x01;
  Bytes exceeds = WrapLikeBroker(Bytes(10, 0x01));
  exceeds[2] = static_cast<std::uint8_t>(exceeds[2] + 1U);
  Bytes fill = good;
  fill.back() = 0x01;
  for (const Bytes* slot : {&bad_outer, &too_long, &empty, &wrong_tag, &after_field, &exceeds, &fill}) {
    h.Slot(*slot);
  }
  EXPECT_EQ(h.Drops(DropReason::kWrapperOuterVarintInvalid), 1U);
  EXPECT_EQ(h.Drops(DropReason::kWrapperOuterLengthExceedsSlot), 1U);
  EXPECT_EQ(h.Drops(DropReason::kWrapperFieldMissing), 1U);
  EXPECT_EQ(h.Drops(DropReason::kWrapperTagNotBytesField1), 1U);
  EXPECT_EQ(h.Drops(DropReason::kWrapperBytesAfterField), 1U);
  EXPECT_EQ(h.Drops(DropReason::kWrapperFieldExceedsMessage), 1U);
  EXPECT_EQ(h.Drops(DropReason::kWrapperFillNotZero), 1U);
  EXPECT_TRUE(h.sink.written.empty());
  EXPECT_TRUE(Has(h.log.Last("frame"), "\"verdict\":\"wrapper_fill_not_zero\""));
}

TEST(RelayCore, PayloadChecksComeAfterTheWrapper) {
  Harness h;
  h.Subscribe();
  h.Connect();
  h.Slot(WrapLikeBroker(Prefixed(Bytes(2045, 0x01))));  // 2049 bytes
  h.Slot(WrapLikeBroker(Bytes{0x01, 0x00, 0x00}));
  Bytes mismatch = FramePayload(3, h.now.realtime_ns);
  mismatch[0] = static_cast<std::uint8_t>(mismatch[0] + 1U);
  h.Slot(WrapLikeBroker(mismatch));
  h.Slot(WrapLikeBroker(Prefixed(Bytes{0x1A, 0x01, 0x00})));  // field 3 with wire type 2
  h.Slot(FrameSlot(0, h.now.realtime_ns));                  // sequence 0
  EXPECT_EQ(h.Drops(DropReason::kPayloadTooLarge), 1U);
  EXPECT_EQ(h.Drops(DropReason::kPayloadTooShort), 1U);
  EXPECT_EQ(h.Drops(DropReason::kLengthPrefixMismatch), 1U);
  EXPECT_EQ(h.Drops(DropReason::kFrameUnreadable), 1U);
  EXPECT_EQ(h.Drops(DropReason::kFieldNotPositive), 1U);
  // A corrupted payload shifts nothing: the next good frame is served.
  h.Frame(4, 1 * kMs);
  EXPECT_EQ(h.sink.written.size(), 1U);
}

TEST(RelayCore, LargestPayloadIsServed) {
  Harness h;
  h.Subscribe();
  h.Connect();
  // 19 bytes of fields and 2025 of filler: a frame of 2044 bytes.
  const Bytes payload = FramePayload(5, h.core.phase_start_realtime_ns(), 2025);
  ASSERT_EQ(payload.size(), 2048U);
  h.Slot(WrapLikeBroker(payload));
  EXPECT_EQ(h.sink.written.size(), 1U);
}

TEST(RelayCore, ACopyInThePhaseIsDroppedAndTheWindowIsClearedAtEachPhaseStart) {
  Harness h;
  h.Subscribe();
  h.Connect();
  h.Frame(5, 1 * kMs);
  h.Frame(5, 1 * kMs);
  EXPECT_EQ(h.Drops(DropReason::kCopyInPhase), 1U);
  const std::int64_t stamp = h.core.phase_start_realtime_ns() + 1 * kMs;
  h.End(SubscriptionEnd::kSilenceTimeout);
  h.Advance(10 * kMs);  // the new phase starts 9 ms after the stamp
  h.Subscribe();
  h.Slot(FrameSlot(5, stamp));
  EXPECT_EQ(h.sink.written.size(), 2U);  // in the margin and not served in this phase
}

TEST(RelayCore, EverySlotEndsInExactlyOneOutcome) {
  Harness h;
  h.Slot(FrameSlot(1, h.now.realtime_ns));
  h.Subscribe();
  h.Slot(FrameSlot(2, h.now.realtime_ns));
  h.Connect();
  h.Frame(3, 0);
  h.Frame(3, 0);
  h.Frame(4, -1 * kSecond);
  h.Slot(Bytes(kSlotBytes, 0xFF));
  const auto& c = h.core.counters();
  EXPECT_EQ(c.messages_read, 6U);
  EXPECT_EQ(c.frames_delivered + c.frames_dropped(), c.messages_read);
}

TEST(RelayCore, ALayerCausedPhaseEndIsADeliveryFailureAndKeepsTheClient) {
  Harness h;
  h.Subscribe();
  h.Connect();
  h.Frame(1, 1 * kMs);
  h.Advance(100 * kMs);
  h.End(SubscriptionEnd::kPublicationDestroyed);
  EXPECT_FALSE(h.core.in_phase());
  EXPECT_TRUE(h.core.client_connected());
  const std::string end = h.log.Last("phase_end");
  EXPECT_TRUE(Has(end, "\"cause\":\"publication_destroyed\""));
  EXPECT_TRUE(Has(end, "\"layer_caused\":true"));
  EXPECT_TRUE(Has(end, "\"client_connected\":true"));
  EXPECT_EQ(h.core.counters().phases_ended_by_layer, 1U);
  EXPECT_EQ(h.core.counters().ended_publication_destroyed, 1U);
  // Frames before the new subscription are dropped, those of the new phase served.
  h.Slot(FrameSlot(2, h.now.realtime_ns));
  EXPECT_EQ(h.Drops(DropReason::kNotSubscribed), 1U);
  h.Advance(2 * kSecond);
  h.Subscribe();
  ASSERT_TRUE(h.core.in_phase());
  h.Frame(3, -900 * kMs);  // a stored frame of the new publication
  h.Frame(4, 2 * kMs);
  EXPECT_EQ(h.Drops(DropReason::kOlderThanPhase), 1U);
  EXPECT_EQ(h.sink.written.size(), 2U);
  EXPECT_EQ(h.core.counters().phases_started, 2U);
}

TEST(RelayCore, EachLayerEndIsRecorded) {
  for (const SubscriptionEnd end :
       {SubscriptionEnd::kPublicationDestroyed, SubscriptionEnd::kDisconnected, SubscriptionEnd::kSilenceTimeout}) {
    Harness h;
    h.Subscribe();
    h.Connect();
    h.End(end);
    EXPECT_TRUE(Has(h.log.Last("phase_end"), std::string{"\"cause\":\""} + ToText(end) + "\"")) << ToText(end);
    EXPECT_TRUE(Has(h.log.Last("phase_end"), "\"layer_caused\":true")) << ToText(end);
    EXPECT_TRUE(Has(h.log.Last("subscription_ended"), "\"layer_caused_phase_end\":true")) << ToText(end);
  }
}

TEST(RelayCore, ClientLossEndsThePhaseAndIsNoLayerEnd) {
  Harness h;
  h.Subscribe();
  h.Connect();
  h.core.OnClientDisconnected(h.now);
  EXPECT_FALSE(h.core.in_phase());
  EXPECT_TRUE(Has(h.log.Last("phase_end"), "\"layer_caused\":false"));
  EXPECT_EQ(h.core.counters().phases_ended_by_layer, 0U);
  EXPECT_TRUE(h.core.subscribed());
}

TEST(RelayCore, ASecondClientIsRefusedAndStartsNoPhase) {
  Harness h;
  h.Subscribe();
  h.Connect();
  const std::int64_t start = h.core.phase_start_realtime_ns();
  h.Advance(1 * kSecond);
  EXPECT_FALSE(h.core.OnClientAccepted(h.now));
  EXPECT_EQ(h.core.counters().clients_refused, 1U);
  EXPECT_EQ(h.core.phase_start_realtime_ns(), start);
  EXPECT_EQ(h.core.counters().phases_started, 1U);
}

TEST(RelayCore, DataLossIsCountedAsAGapAndThePhaseGoesOn) {
  Harness h;
  h.Subscribe();
  h.Connect();
  WorkerEvent loss = h.Event(WorkerEventKind::kDataLoss);
  loss.status = GatewayResult{15, "overflow"};
  h.core.OnWorkerEvent(loss);
  EXPECT_TRUE(h.core.in_phase());
  EXPECT_EQ(h.core.counters().data_loss_reads, 1U);
  EXPECT_TRUE(Has(h.log.Last("data_loss"), "\"counts_as\":\"gap\""));
  EXPECT_EQ(h.core.counters().phases_ended, 0U);
}

TEST(RelayCore, AFailedWriteDropsTheFrameAndEndsTheClient) {
  Harness h;
  h.Subscribe();
  h.Connect();
  h.sink.fail = true;
  h.Frame(1, 1 * kMs);
  EXPECT_EQ(h.Drops(DropReason::kClientWriteFailed), 1U);
  EXPECT_FALSE(h.core.client_connected());
  EXPECT_FALSE(h.core.in_phase());
  EXPECT_TRUE(Has(h.log.Last("phase_end"), "\"cause\":\"client_write_failed\""));
  h.sink.fail = false;
  h.Connect();  // the next client is accepted
  EXPECT_TRUE(h.core.in_phase());
}

TEST(RelayCore, StopEndsThePhase) {
  Harness h;
  h.Subscribe();
  h.Connect();
  h.core.Stop(h.now);
  EXPECT_FALSE(h.core.in_phase());
  EXPECT_TRUE(Has(h.log.Last("phase_end"), "\"cause\":\"relay_stop\""));
}

TEST(RelayCore, IngressTriggerRepeatsUntilTheFirstClientAndNeverAfter) {
  RelayConfig config;
  config.ingress_start_property = "de4sdv.aebs.ingress.start";
  Harness h{config};
  h.core.OnStart(h.now);
  h.core.OnListening(h.now);
  ASSERT_EQ(h.properties.set.size(), 2U);
  EXPECT_EQ(h.properties.set[0], (std::pair<std::string, std::string>{"de4sdv.aebs.ingress.start", "0"}));
  EXPECT_EQ(h.properties.set[1], (std::pair<std::string, std::string>{"de4sdv.aebs.ingress.start", "1"}));
  for (int second = 1; second <= 3; ++second) {
    h.Advance(1 * kSecond);
    h.core.OnTick(h.now);
  }
  EXPECT_EQ(h.core.counters().ingress_triggers, 4U);
  h.Connect();
  for (int second = 0; second < 20; ++second) {
    h.Advance(1 * kSecond);
    h.core.OnTick(h.now);
  }
  EXPECT_EQ(h.core.counters().ingress_triggers, 4U);
  h.core.OnClientDisconnected(h.now);
  h.Advance(5 * kSecond);
  h.core.OnTick(h.now);
  EXPECT_EQ(h.core.counters().ingress_triggers, 4U);
}

TEST(RelayCore, IngressTriggerGivesUpAfterTenRepeats) {
  RelayConfig config;
  config.ingress_start_property = "de4sdv.aebs.ingress.start";
  Harness h{config};
  h.core.OnListening(h.now);
  for (int second = 0; second < 15; ++second) {
    h.Advance(1 * kSecond);
    h.core.OnTick(h.now);
  }
  EXPECT_EQ(h.core.counters().ingress_triggers, 11U);
  EXPECT_EQ(h.log.Count("ingress_trigger_gave_up"), 1U);
}

TEST(RelayCore, ClockStepsAreLoggedAndMarkTheirPhase) {
  Harness h;
  h.core.ObserveClock(h.now);
  h.Subscribe();
  h.Connect();
  Clock stepped = h.now;
  stepped.realtime_ns += 2 * kMs;
  h.core.ObserveClock(stepped);
  EXPECT_EQ(h.core.counters().clock_steps, 1U);
  EXPECT_TRUE(Has(h.log.Last("clock_step"), "\"step_ns\":2000000"));
  h.core.OnClientDisconnected(stepped);
  EXPECT_TRUE(Has(h.log.Last("phase_end"), "\"clock_steps_in_phase\":1"));
}

TEST(RelayCore, PhaseEndLogsTheRangeOfReceiptMinusFrameTime) {
  Harness h;
  h.Subscribe();
  h.Connect();
  h.Advance(40 * kMs);
  h.Frame(1, 8 * kMs);   // received 32 ms after its stamp
  h.Frame(2, -10 * kMs);  // 50 ms
  h.core.OnClientDisconnected(h.now);
  const std::string end = h.log.Last("phase_end");
  EXPECT_TRUE(Has(end, "\"receipt_minus_frame_min_ns\":32000000"));
  EXPECT_TRUE(Has(end, "\"receipt_minus_frame_max_ns\":50000000"));
  EXPECT_TRUE(Has(end, "\"frames_served\":2"));
}

TEST(RelayCore, StartDiagnosticNamesTheAclOrTheMappingOnceAfterThirtySeconds) {
  Harness h;
  h.core.OnStart(h.now);
  h.core.OnWorkerEvent(h.Event(WorkerEventKind::kClientCreate));
  for (int second = 0; second < 30; ++second) {
    WorkerEvent failed = h.Event(WorkerEventKind::kSubscribeFailed);
    failed.status = GatewayResult{5, "No publication service unit found"};
    failed.attempt = static_cast<std::uint64_t>(second) + 1U;
    h.core.OnWorkerEvent(failed);
    h.Advance(1 * kSecond - 1 * kMs);
    h.core.OnTick(h.now);
    h.Advance(1 * kMs);
  }
  EXPECT_EQ(h.log.Count("subscription_start_diagnostic"), 0U);
  h.core.OnTick(h.now);
  ASSERT_EQ(h.log.Count("subscription_start_diagnostic"), 1U);
  const std::string line = h.log.Last("subscription_start_diagnostic");
  EXPECT_TRUE(Has(line, "\"likely_fault\":\"acl_or_mapping\""));
  EXPECT_TRUE(Has(line, "\"status_text\":\"No publication service unit found\""));
  EXPECT_TRUE(Has(line, "\"subscribe_failures\":30"));
  EXPECT_TRUE(Has(line, "\"retry_period_ns\":10000000000"));
  h.Advance(30 * kSecond);
  h.core.OnTick(h.now);
  EXPECT_EQ(h.log.Count("subscription_start_diagnostic"), 1U);
}

TEST(RelayCore, StartDiagnosticNamesTheClientWhenNoneWasCreated) {
  Harness h;
  h.core.OnStart(h.now);
  WorkerEvent failed = h.Event(WorkerEventKind::kClientCreate);
  failed.status = GatewayResult{14, "SD agent unavailable"};
  h.core.OnWorkerEvent(failed);
  h.monitor.Begin("create_client", h.now.monotonic_ns);
  h.Advance(30 * kSecond);
  h.core.OnTick(h.now);
  const std::string line = h.log.Last("subscription_start_diagnostic");
  EXPECT_TRUE(Has(line, "\"likely_fault\":\"gateway_client\""));
  EXPECT_TRUE(Has(line, "\"gateway_call_in_progress\":\"create_client\""));
  EXPECT_TRUE(Has(line, "\"last_failure_stage\":\"create_client\""));
}

TEST(RelayCore, NoStartDiagnosticAfterASubscription) {
  Harness h;
  h.core.OnStart(h.now);
  h.Advance(29 * kSecond);
  h.Subscribe();
  h.End(SubscriptionEnd::kSilenceTimeout);
  h.Advance(60 * kSecond);
  h.core.OnTick(h.now);
  EXPECT_EQ(h.log.Count("subscription_start_diagnostic"), 0U);
}

TEST(RelayCore, AStalledGatewayCallIsReportedOnceAndItsReturnToo) {
  RelayConfig config;
  Harness h{config};
  h.Subscribe();
  h.Connect();
  h.monitor.Begin("read", h.now.monotonic_ns);
  h.Advance(9900 * kMs);
  h.core.OnTick(h.now);
  EXPECT_EQ(h.log.Count("gateway_call_stalled"), 0U);
  h.Advance(100 * kMs);
  h.core.OnTick(h.now);
  h.core.OnTick(h.now);
  ASSERT_EQ(h.log.Count("gateway_call_stalled"), 1U);
  EXPECT_TRUE(Has(h.log.Last("gateway_call_stalled"), "\"call\":\"read\""));
  EXPECT_TRUE(h.core.in_phase());  // the main thread goes on
  h.Advance(2 * kSecond);
  h.monitor.End(h.now.monotonic_ns);
  h.core.OnTick(h.now);
  EXPECT_TRUE(Has(h.log.Last("gateway_call_returned"), "\"ran_ns\":12000000000"));
  EXPECT_EQ(h.core.counters().gateway_calls_stalled, 1U);
}

TEST(RelayCore, RepeatedReadFailuresGiveOneLinePerSecond) {
  Harness h;
  h.Subscribe();
  for (int index = 0; index < 50; ++index) {
    WorkerEvent failed = h.Event(WorkerEventKind::kReadFailed);
    failed.status = GatewayResult{3, "invalid"};
    h.core.OnWorkerEvent(failed);
    h.Advance(20 * kMs);
  }
  EXPECT_EQ(h.core.counters().read_failures, 50U);
  EXPECT_EQ(h.log.Count("read_failed"), 1U);
}

TEST(RelayCore, NotificationsThatTheWorkerDidNotActOnAreCounted) {
  Harness h;
  WorkerEvent note = h.Event(WorkerEventKind::kNotification);
  note.notification = GatewayNotificationKind::kOtherClientNotification;
  note.raw_type = 5;
  note.note = "not_acted_on";
  h.core.OnWorkerEvent(note);
  EXPECT_EQ(h.core.counters().notifications_not_acted_on, 1U);
  EXPECT_TRUE(Has(h.log.Last("gateway_notification"), "\"raw_type\":5"));
}

TEST(RelayCore, StatusLineHoldsEveryDropReason) {
  Harness h;
  const LogRecord status = h.core.Status("status");
  for (std::size_t index = 0; index < kDropReasonCount; ++index) {
    const std::string key = std::string{"\"drop_"} + ToText(static_cast<DropReason>(index)) + "\":0";
    EXPECT_TRUE(Has(status.fields(), key)) << key;
  }
  EXPECT_TRUE(Has(status.fields(), "\"phases_ended_by_layer\":0"));
  EXPECT_TRUE(Has(status.fields(), "\"data_loss_reads\":0"));
}

TEST(RelayCore, SubscribedLineNamesTheFlag) {
  Harness h;
  h.Subscribe();
  EXPECT_TRUE(Has(h.log.Last("subscribed"), "\"subscriber_flag\":\"ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE\""));
  EXPECT_TRUE(Has(h.log.Last("subscribed"), "\"subscriber_flags\":0"));
}

}  // namespace
