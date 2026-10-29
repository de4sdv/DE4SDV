// Unit tests of the gateway worker with the fake client and a manual clock:
// the subscription by name with ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE, the
// reads, DATA_LOSS, the 3 s timeout and the back-off, PublicationDestroyed,
// Disconnected, late notifications of old generations, and the stop.

#include <gtest/gtest.h>

#include <cstdint>
#include <string>
#include <vector>

#include "de4sdv_ivi_frame_relay/gateway_worker.hpp"
#include "fake_gateway_client.hpp"

namespace {

using de4sdv::ivi_frame_relay::GatewayCallMonitor;
using de4sdv::ivi_frame_relay::GatewayNotification;
using de4sdv::ivi_frame_relay::GatewayNotificationKind;
using de4sdv::ivi_frame_relay::GatewayResult;
using de4sdv::ivi_frame_relay::GatewayWorker;
using de4sdv::ivi_frame_relay::kSubscriberFlagNone;
using de4sdv::ivi_frame_relay::PublicationName;
using de4sdv::ivi_frame_relay::SubjectIdentity;
using de4sdv::ivi_frame_relay::SubscriptionEnd;
using de4sdv::ivi_frame_relay::WorkerConfig;
using de4sdv::ivi_frame_relay::WorkerEvent;
using de4sdv::ivi_frame_relay::WorkerEventKind;
using de4sdv::ivi_frame_relay::test::Bytes;
using de4sdv::ivi_frame_relay::test::CollectingSink;
using de4sdv::ivi_frame_relay::test::FakeGatewayClient;
using de4sdv::ivi_frame_relay::test::FrameSlot;
using de4sdv::ivi_frame_relay::test::kMs;
using de4sdv::ivi_frame_relay::test::kSecond;
using de4sdv::ivi_frame_relay::test::kSlotBytes;
using de4sdv::ivi_frame_relay::test::ManualClock;

// The status of a refused subscribe in the feasibility runs (no ACL, or no publication).
const GatewayResult kNoPublication{13, "Status(-8, EX_SERVICE_SPECIFIC): '13: No publication service unit found'"};

WorkerConfig Config() {
  return WorkerConfig{SubjectIdentity{"de4sdv.ivi_frame_relay", "IviFrameRelay", "default"},
                      PublicationName{"instance1", "com.android.sdv.someip", "SomeIpBroker",
                                      "de4sdv-score-aebs-signal-frame"}};
}

struct Harness {
  ManualClock clock;
  FakeGatewayClient client{&clock};
  CollectingSink sink;
  GatewayCallMonitor monitor;
  GatewayWorker worker{Config(), client, sink, clock, &monitor};
  std::int64_t start{0};

  Harness() {
    worker.Start();
    start = clock.Now().monotonic_ns;
  }

  std::int64_t Since() { return clock.Now().monotonic_ns - start; }

  // Steps the worker and moves the clock to each deadline, up to and with
  // the steps due at the end of duration.
  void RunFor(std::int64_t duration) {
    const std::int64_t end = clock.Now().monotonic_ns + duration;
    for (int guard = 0; guard < 1'000'000; ++guard) {
      const std::int64_t deadline = worker.Step();
      const std::int64_t now = clock.Now().monotonic_ns;
      if (deadline > end) {
        clock.AdvanceTo(end);
        return;
      }
      if (deadline > now) {
        clock.AdvanceTo(deadline);
      }
    }
    FAIL() << "the worker made no progress";
  }

  std::vector<WorkerEvent> Of(WorkerEventKind kind) const {
    std::vector<WorkerEvent> found;
    for (const WorkerEvent& event : sink.events) {
      if (event.kind == kind) {
        found.push_back(event);
      }
    }
    return found;
  }
};

TEST(GatewayWorker, CreatesTheClientAndSubscribesByNameWithFlagNone) {
  Harness h;
  h.RunFor(10 * kMs);
  ASSERT_GE(h.sink.events.size(), 3U);
  EXPECT_EQ(h.sink.events[0].kind, WorkerEventKind::kClientCreate);
  EXPECT_STREQ(h.sink.events[0].note, "client_new");
  EXPECT_TRUE(h.sink.events[0].status.ok());
  EXPECT_EQ(h.sink.events[1].kind, WorkerEventKind::kClientCreate);
  EXPECT_STREQ(h.sink.events[1].note, "init_comms");
  EXPECT_EQ(h.sink.events[2].kind, WorkerEventKind::kSubscribed);
  const WorkerEvent& subscribed = h.sink.events[2];
  EXPECT_EQ(subscribed.publication.subscriber_flags, kSubscriberFlagNone);
  EXPECT_EQ(subscribed.publication.message_size_bytes, kSlotBytes);
  EXPECT_EQ(subscribed.subscription, 1U);
  EXPECT_STREQ(subscribed.rule, "start");
  EXPECT_EQ(h.client.last_flags(), kSubscriberFlagNone);
  EXPECT_EQ(h.client.last_subject().package, "de4sdv.ivi_frame_relay");
  EXPECT_EQ(h.client.last_publication().unit, "de4sdv-score-aebs-signal-frame");
  EXPECT_EQ(h.client.last_publication().vm, "instance1");
  EXPECT_TRUE(h.worker.subscribed());
  EXPECT_FALSE(h.monitor.Current().has_value());  // every call has returned
}

TEST(GatewayWorker, SubscribedEventCarriesTheTimeTheCallReturned) {
  Harness h;
  h.client.SetCallLatency(7 * kMs);
  h.RunFor(20 * kMs);
  const auto subscribed = h.Of(WorkerEventKind::kSubscribed);
  ASSERT_EQ(subscribed.size(), 1U);
  // Client_new, initComms and subscribe, 7 ms each: the subscription holds from 21 ms.
  EXPECT_EQ(subscribed[0].at.monotonic_ns - h.start, 21 * kMs);
}

TEST(GatewayWorker, FailedSubscribesCarryTheirStatusAndFollowTheStartSchedule) {
  Harness h;
  h.client.FailSubscribes(1000, kNoPublication);
  h.RunFor(45 * kSecond);
  const auto failed = h.Of(WorkerEventKind::kSubscribeFailed);
  // Every second until 30 s, then every 10 s: 0, 1, ..., 30, 40.
  ASSERT_EQ(failed.size(), 32U);
  for (std::size_t index = 0; index <= 30U; ++index) {
    EXPECT_EQ(failed[index].at.monotonic_ns - h.start, static_cast<std::int64_t>(index) * kSecond) << index;
  }
  EXPECT_EQ(failed[31].at.monotonic_ns - h.start, 40 * kSecond);
  EXPECT_EQ(failed[0].status.code, 13);
  EXPECT_EQ(failed[0].status.text, kNoPublication.text);
  EXPECT_EQ(failed[0].attempt, 1U);
  EXPECT_STREQ(failed[29].rule, "start");
  EXPECT_STREQ(failed[30].rule, "start_after_diagnostic");
  EXPECT_EQ(failed[30].next_attempt_ns - failed[30].at.monotonic_ns, 10 * kSecond);
  EXPECT_FALSE(h.worker.subscribed());
}

TEST(GatewayWorker, AFailedClientNewIsRetriedWithABoundedWait) {
  Harness h;
  h.client.FailClientNews(1000, GatewayResult{14, "gateway service unavailable"});
  h.RunFor(45 * kSecond);
  const auto creates = h.Of(WorkerEventKind::kClientCreate);
  // Client_new itself failed, so no client exists and it may be tried again.
  ASSERT_EQ(creates.size(), 32U);
  EXPECT_EQ(creates[1].at.monotonic_ns - h.start, 1 * kSecond);
  EXPECT_EQ(creates[31].at.monotonic_ns - h.start, 40 * kSecond);
  EXPECT_EQ(creates[0].status.text, "gateway service unavailable");
  for (const WorkerEvent& create : creates) {
    EXPECT_STREQ(create.note, "client_new");
    EXPECT_FALSE(create.status.ok());
    EXPECT_LE(create.next_attempt_ns - create.at.monotonic_ns, 10 * kSecond);
  }
  EXPECT_EQ(h.client.count("init_comms"), 0U);
  EXPECT_EQ(h.client.count("subscribe"), 0U);
  EXPECT_FALSE(h.worker.client_lost());
}

TEST(GatewayWorker, AFailedInitCommsLosesTheClientForTheProcess) {
  Harness h;
  // The status of the feasibility run when a second process with the same subject started.
  h.client.FailInitComms(GatewayResult{13, "Failed to create identity for IviFrameRelay with SD IdentityAgent"});
  h.RunFor(60 * kSecond);
  const auto lost = h.Of(WorkerEventKind::kClientLost);
  ASSERT_EQ(lost.size(), 1U);
  EXPECT_STREQ(lost[0].note, "init_comms");
  EXPECT_EQ(lost[0].status.code, 13);
  EXPECT_TRUE(h.worker.client_lost());
  // One Client_new and one initComms in the whole minute: no delete, no second client.
  EXPECT_EQ(h.client.count("client_new"), 1U);
  EXPECT_EQ(h.client.count("init_comms"), 1U);
  EXPECT_EQ(h.client.count("destroy"), 0U);
  EXPECT_EQ(h.client.count("subscribe"), 0U);
  EXPECT_EQ(h.client.second_clients(), 0);
}

TEST(GatewayWorker, ReadsHandOnEverySlotInOrderAndUnchanged) {
  Harness h;
  h.RunFor(1 * kMs);
  const Bytes first = FrameSlot(1, 1000);
  const Bytes second = FrameSlot(2, 2000);
  Bytes odd(100, 0x7E);  // a slot that is no wrapper is handed on too
  h.client.QueueSlot(first);
  h.client.QueueSlot(second);
  h.client.QueueSlot(odd);
  h.RunFor(50 * kMs);
  const auto messages = h.Of(WorkerEventKind::kMessage);
  ASSERT_EQ(messages.size(), 3U);
  EXPECT_EQ(messages[0].slot, first);
  EXPECT_EQ(messages[1].slot, second);
  odd.resize(kSlotBytes, 0U);
  EXPECT_EQ(messages[2].slot, odd);
  EXPECT_EQ(messages[0].subscription, 1U);
  // The read buffer holds the 16 slots of the publication's queue.
  EXPECT_EQ(h.client.last_read_capacity(), 16U * kSlotBytes);
}

TEST(GatewayWorker, ReadBufferIsBounded) {
  Harness h;
  h.client.SetMetadata(kSlotBytes, 1000);
  h.RunFor(30 * kMs);
  EXPECT_EQ(h.client.last_read_capacity(), 64U * kSlotBytes);
  Harness large;
  large.client.SetMetadata(1U << 20U, 16);
  large.RunFor(30 * kMs);
  EXPECT_EQ(large.client.last_read_capacity(), 4U << 20U);
}

TEST(GatewayWorker, DataLossIsAGapAndTheSubscriptionGoesOn) {
  Harness h;
  h.RunFor(1 * kMs);
  h.client.QueueSlot(FrameSlot(1, 1000));
  h.client.QueueDataLoss();
  h.client.QueueSlot(FrameSlot(3, 3000));
  h.RunFor(100 * kMs);
  std::vector<WorkerEventKind> kinds;
  for (const WorkerEvent& event : h.sink.events) {
    if (event.kind == WorkerEventKind::kMessage || event.kind == WorkerEventKind::kDataLoss ||
        event.kind == WorkerEventKind::kSubscriptionEnded) {
      kinds.push_back(event.kind);
    }
  }
  EXPECT_EQ(kinds, (std::vector<WorkerEventKind>{WorkerEventKind::kMessage, WorkerEventKind::kDataLoss,
                                                 WorkerEventKind::kMessage}));
  EXPECT_EQ(h.Of(WorkerEventKind::kDataLoss)[0].status.code, 15);
  EXPECT_TRUE(h.worker.subscribed());
}

TEST(GatewayWorker, DataLossAfterAReadStallIsASignOfLifeAndTheFreshSlotsAreRead) {
  Harness h;
  h.RunFor(1 * kMs);
  h.client.QueueSlot(FrameSlot(1, 1000));
  h.RunFor(10 * kMs);
  // The worker cannot read for 3.3 s (a slow call, or the VM paused); the
  // queue overflows: the next read gives DATA_LOSS, then fresh slots.
  h.clock.Advance(3300 * kMs);
  h.client.QueueDataLoss();
  h.client.QueueSlot(FrameSlot(40, 4000));
  h.client.QueueSlot(FrameSlot(41, 4100));
  h.RunFor(50 * kMs);
  std::vector<WorkerEventKind> kinds;
  for (const WorkerEvent& event : h.sink.events) {
    if (event.kind == WorkerEventKind::kMessage || event.kind == WorkerEventKind::kDataLoss ||
        event.kind == WorkerEventKind::kSubscriptionEnded) {
      kinds.push_back(event.kind);
    }
  }
  EXPECT_EQ(kinds, (std::vector<WorkerEventKind>{WorkerEventKind::kMessage, WorkerEventKind::kDataLoss,
                                                 WorkerEventKind::kMessage, WorkerEventKind::kMessage}));
  EXPECT_TRUE(h.worker.subscribed());
  // A DATA_LOSS also restarts the 3 s: no end 2.9 s after it, without messages.
  h.RunFor(2900 * kMs);
  EXPECT_TRUE(h.Of(WorkerEventKind::kSubscriptionEnded).empty());
}

TEST(GatewayWorker, ReadFailureIsHandedOnAndTheSubscriptionGoesOn) {
  Harness h;
  h.RunFor(1 * kMs);
  h.client.QueueReadFailure(GatewayResult{3, "bad publication id"});
  h.RunFor(100 * kMs);
  ASSERT_EQ(h.Of(WorkerEventKind::kReadFailed).size(), 1U);
  EXPECT_EQ(h.Of(WorkerEventKind::kReadFailed)[0].status.text, "bad publication id");
  EXPECT_TRUE(h.worker.subscribed());
}

TEST(GatewayWorker, NoMessageForThreeSecondsEndsTheSubscriptionAndSubscribesAgain) {
  Harness h;
  h.RunFor(1 * kMs);
  h.client.QueueSlot(FrameSlot(1, 1000));
  h.RunFor(10 * kMs);
  const std::int64_t last_message = h.Of(WorkerEventKind::kMessage).back().at.monotonic_ns;
  h.RunFor(2900 * kMs);
  EXPECT_TRUE(h.Of(WorkerEventKind::kSubscriptionEnded).empty());
  h.RunFor(200 * kMs);
  const auto ended = h.Of(WorkerEventKind::kSubscriptionEnded);
  ASSERT_EQ(ended.size(), 1U);
  EXPECT_EQ(ended[0].end, SubscriptionEnd::kSilenceTimeout);
  EXPECT_EQ(ended[0].messages, 1U);
  EXPECT_GE(ended[0].at.monotonic_ns - last_message, 3 * kSecond);
  EXPECT_LT(ended[0].at.monotonic_ns - last_message, 3 * kSecond + 25 * kMs);
  EXPECT_EQ(h.client.count("unsubscribe:2"), 1U);
  // Break before make: one subscription at a time, and the next one at once.
  const auto subscribed = h.Of(WorkerEventKind::kSubscribed);
  ASSERT_EQ(subscribed.size(), 2U);
  EXPECT_LE(subscribed[1].at.monotonic_ns - ended[0].at.monotonic_ns, 1 * kMs);
}

TEST(GatewayWorker, ThreeSilentSubscriptionsInARowMakeItWaitFiveSeconds) {
  Harness h;
  h.RunFor(25 * kSecond);
  const auto subscribed = h.Of(WorkerEventKind::kSubscribed);
  std::vector<std::int64_t> at;
  for (const WorkerEvent& event : subscribed) {
    at.push_back((event.at.monotonic_ns - h.start) / kMs);
  }
  // 0, 3 and 6 s at once after each timeout; the third silent end at 9 s
  // starts the wait of 5 s: 14 s, then 17 + 5 = 22 s.
  EXPECT_EQ(at, (std::vector<std::int64_t>{0, 3000, 6000, 14000, 22000}));
  const auto ended = h.Of(WorkerEventKind::kSubscriptionEnded);
  ASSERT_GE(ended.size(), 3U);
  EXPECT_EQ(ended[2].consecutive_silent, 3U);
  EXPECT_STREQ(ended[2].rule, "silent_subscriptions_back_off");
}

TEST(GatewayWorker, PublicationDestroyedEndsItAndRetriesEvery100MsUntilTheNewPublication) {
  Harness h;
  h.RunFor(1 * kMs);
  const std::int32_t old_id = h.worker.publication().publication_id;
  h.client.DestroyPublication();
  const std::int64_t destroyed = h.clock.Now().monotonic_ns;
  h.RunFor(2 * kSecond);
  const auto ended = h.Of(WorkerEventKind::kSubscriptionEnded);
  ASSERT_EQ(ended.size(), 1U);
  EXPECT_EQ(ended[0].end, SubscriptionEnd::kPublicationDestroyed);
  EXPECT_EQ(h.client.count("unsubscribe:" + std::to_string(old_id)), 1U);
  const auto failed = h.Of(WorkerEventKind::kSubscribeFailed);
  ASSERT_EQ(failed.size(), 21U);  // 0, 100, ..., 2000 ms after it
  for (std::size_t index = 0; index < failed.size(); ++index) {
    EXPECT_EQ(failed[index].at.monotonic_ns - destroyed, static_cast<std::int64_t>(index) * 100 * kMs) << index;
    EXPECT_EQ(failed[index].status.code, kNoPublication.code);
    EXPECT_EQ(failed[index].status.text, kNoPublication.text);
    EXPECT_STREQ(failed[index].rule, "publication_destroyed_first_5_s");
  }
  h.client.RestorePublication();
  h.RunFor(150 * kMs);
  const auto subscribed = h.Of(WorkerEventKind::kSubscribed);
  ASSERT_EQ(subscribed.size(), 2U);
  EXPECT_NE(subscribed[1].publication.publication_id, old_id);
  EXPECT_EQ(subscribed[1].subscription, 2U);
}

TEST(GatewayWorker, AfterFiveSecondsWithoutAPublicationItRetriesEverySecond) {
  Harness h;
  h.RunFor(1 * kMs);
  h.client.DestroyPublication();
  const std::int64_t destroyed = h.clock.Now().monotonic_ns;
  h.RunFor(8 * kSecond);
  const auto failed = h.Of(WorkerEventKind::kSubscribeFailed);
  // 51 attempts in the first 5 s (0 to 5000 ms), then 6 s, 7 s and 8 s.
  ASSERT_EQ(failed.size(), 51U + 3U);
  EXPECT_EQ(failed[50].at.monotonic_ns - destroyed, 5000 * kMs);
  EXPECT_STREQ(failed[49].rule, "publication_destroyed_first_5_s");
  EXPECT_STREQ(failed[50].rule, "every_second");  // its period: the first 5 s are over
  EXPECT_EQ(failed[51].at.monotonic_ns - destroyed, 6000 * kMs);
  EXPECT_EQ(failed[53].at.monotonic_ns - destroyed, 8000 * kMs);
  EXPECT_STREQ(failed[51].rule, "every_second");
}

TEST(GatewayWorker, LateNotificationsOfOldGenerationsChangeNothing) {
  Harness h;
  h.RunFor(1 * kMs);
  GatewayNotification late;
  late.kind = GatewayNotificationKind::kPublicationDestroyed;
  late.subscription_generation = h.client.subscription_generation() + 7;
  late.publication_id = 99;
  h.client.Send(late);
  GatewayNotification old_client;
  old_client.kind = GatewayNotificationKind::kDisconnected;
  old_client.client_generation = h.client.client_generation() + 3;
  h.client.Send(old_client);
  h.RunFor(10 * kMs);
  const auto notes = h.Of(WorkerEventKind::kNotification);
  ASSERT_EQ(notes.size(), 2U);
  EXPECT_STREQ(notes[0].note, "ignored_not_the_current_subscription");
  EXPECT_STREQ(notes[1].note, "ignored_not_the_current_client");
  EXPECT_TRUE(h.worker.subscribed());
  EXPECT_TRUE(h.Of(WorkerEventKind::kSubscriptionEnded).empty());
}

TEST(GatewayWorker, DisconnectedLosesTheClientForTheProcess) {
  Harness h;
  h.RunFor(1 * kMs);
  h.client.Disconnect();
  h.RunFor(600 * kSecond);  // ten minutes
  const auto ended = h.Of(WorkerEventKind::kSubscriptionEnded);
  ASSERT_EQ(ended.size(), 1U);
  EXPECT_EQ(ended[0].end, SubscriptionEnd::kDisconnected);
  const auto lost = h.Of(WorkerEventKind::kClientLost);
  ASSERT_EQ(lost.size(), 1U);
  EXPECT_STREQ(lost[0].note, "disconnected");
  EXPECT_EQ(lost[0].raw_type, 3);
  EXPECT_GT(lost[0].at.monotonic_ns, ended[0].at.monotonic_ns - 1);
  // No unsubscribe on a gone client, no delete, no second client: the process ends.
  EXPECT_EQ(h.client.count("unsubscribe:2"), 0U);
  EXPECT_EQ(h.client.count("destroy"), 0U);
  EXPECT_EQ(h.client.count("client_new"), 1U);
  EXPECT_EQ(h.client.second_clients(), 0);
  EXPECT_EQ(h.client.count("subscribe"), 1U);
  EXPECT_TRUE(h.worker.client_lost());
  h.worker.Finish();  // at the exit: nothing to unsubscribe, nothing to delete
  EXPECT_EQ(h.client.count("destroy"), 0U);
}

TEST(GatewayWorker, RefusedMetadataIsAFailedAttempt) {
  Harness h;
  h.client.SetMetadata(0, 16);
  h.RunFor(1500 * kMs);
  const auto failed = h.Of(WorkerEventKind::kSubscribeFailed);
  ASSERT_EQ(failed.size(), 2U);
  EXPECT_STREQ(failed[0].note, "metadata_refused");
  EXPECT_EQ(h.client.count("unsubscribe:2"), 2U);
  EXPECT_FALSE(h.worker.subscribed());
}

TEST(GatewayWorker, FinishUnsubscribesAndDeletesTheClient) {
  Harness h;
  h.RunFor(1 * kMs);
  h.worker.RequestStop();
  EXPECT_TRUE(h.worker.stop_requested());
  h.worker.Finish();
  const auto ended = h.Of(WorkerEventKind::kSubscriptionEnded);
  ASSERT_EQ(ended.size(), 1U);
  EXPECT_EQ(ended[0].end, SubscriptionEnd::kRelayStop);
  EXPECT_EQ(h.client.count("unsubscribe:2"), 1U);
  EXPECT_EQ(h.client.count("destroy"), 1U);
  EXPECT_FALSE(h.client.has_client());
  EXPECT_STREQ(h.Of(WorkerEventKind::kClientDestroyed).at(0).note, "relay_stop");
}

}  // namespace
