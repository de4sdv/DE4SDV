// Unit tests of the speed path controller of the pure adapter core: the first
// and second LoLa rules of the adapter (phase-8 realization of INC-MW-011).
//
// Rule 1 (stored samples, GAP-MW-039): a new LoLa subscription returns the
// samples that the provider sent before it. So the first read after each
// entry into kSubscribed (the first subscription, and every return after the
// subscription left kSubscribed, for example on a provider restart) is read
// and discarded; only samples that arrive after it are published
// (REQ-MW-013). A read that does not stay inside one stable kSubscribed phase
// is dropped too.
//
// Rule 2 (shutdown, GAP-MW-041): on SIGTERM the adapter stops reading, unsets
// the receive handler, holds no sample, calls Unsubscribe(), waits for
// kNotSubscribed and only then destroys the proxy. It never destroys a
// subscribed proxy.

#include <gtest/gtest.h>

#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <deque>
#include <functional>
#include <limits>
#include <string>
#include <vector>

#include "de4sdv_score_adapter/speed_path_controller.hpp"

namespace {

using de4sdv::score_adapter::ShutdownResult;
using de4sdv::score_adapter::SpeedEventPort;
using de4sdv::score_adapter::SpeedPathController;
using de4sdv::score_adapter::SpeedPathEvents;
using de4sdv::score_adapter::SubscriptionState;
using de4sdv::score_adapter::TranslationOutcome;
using de4sdv::score_adapter::VelocityPublisherPort;

class FakeSpeedEvent final : public SpeedEventPort {
 public:
  SubscriptionState state{SubscriptionState::kNotSubscribed};
  std::deque<double> pending;  // samples a read would return, oldest first
  std::vector<std::string> calls;
  std::function<void()> during_read;  // simulates a transition inside a read
  int unsubscribe_reaches_not_subscribed_after_polls{0};
  bool proxy_destroyed{false};
  bool fail_reads{false};

  bool Subscribe(std::size_t max_samples) override {
    calls.push_back("Subscribe(" + std::to_string(max_samples) + ")");
    return true;
  }
  void Unsubscribe() override {
    calls.push_back("Unsubscribe");
    if (unsubscribe_reaches_not_subscribed_after_polls == 0) {
      state = SubscriptionState::kNotSubscribed;
    }
  }
  SubscriptionState State() const override {
    if (unsubscribe_reaches_not_subscribed_after_polls > 0 && !calls.empty() && calls.back() == "Unsubscribe") {
      auto* self = const_cast<FakeSpeedEvent*>(this);
      if (--self->unsubscribe_reaches_not_subscribed_after_polls == 0) {
        self->state = SubscriptionState::kNotSubscribed;
      }
    }
    return state;
  }
  std::int64_t ReadNewSamples(std::size_t max_samples, const SampleSink& sink) override {
    calls.push_back("Read");
    if (fail_reads) {
      return -1;
    }
    std::int64_t delivered = 0;
    while (!pending.empty() && static_cast<std::size_t>(delivered) < max_samples) {
      sink(pending.front());
      pending.pop_front();
      ++delivered;
    }
    if (during_read) {
      auto hook = during_read;
      during_read = nullptr;
      hook();
    }
    return delivered;
  }
  void UnsetReceiveHandler() override { calls.push_back("UnsetReceiveHandler"); }
  void UnsetStateHandler() override { calls.push_back("UnsetStateHandler"); }
  void DestroyProxy() override {
    calls.push_back("DestroyProxy");
    if (state != SubscriptionState::kNotSubscribed) {
      ADD_FAILURE() << "a subscribed proxy was destroyed";
    }
    proxy_destroyed = true;
  }
};

class FakePublisher final : public VelocityPublisherPort {
 public:
  std::vector<float> published;
  void Publish(float longitudinal_velocity_mps) override { published.push_back(longitudinal_velocity_mps); }
};

constexpr std::size_t kMaxSamples = 5;

struct Fixture {
  FakeSpeedEvent event;
  FakePublisher publisher;
  SpeedPathController controller{event, publisher, kMaxSamples};

  // The provider is found, the proxy subscribes, LoLa enters kSubscribed.
  void SubscribeAndEnter() {
    ASSERT_TRUE(controller.Subscribe());
    event.state = SubscriptionState::kSubscribed;
    controller.OnSubscriptionStateChanged(SubscriptionState::kSubscribed);
  }
  // The subscription leaves kSubscribed (for example the provider stops its
  // offer) and comes back when the provider offers again.
  void LeaveAndReenter() {
    event.state = SubscriptionState::kSubscriptionPending;
    controller.OnSubscriptionStateChanged(SubscriptionState::kSubscriptionPending);
    event.state = SubscriptionState::kSubscribed;
    controller.OnSubscriptionStateChanged(SubscriptionState::kSubscribed);
  }
};

TEST(SpeedPathController, SubscribesWithTheConfiguredSampleCount) {
  Fixture f;
  ASSERT_TRUE(f.controller.Subscribe());
  EXPECT_EQ(f.event.calls, (std::vector<std::string>{"Subscribe(5)"}));
}

TEST(SpeedPathController, FirstReadAfterTheSubscriptionDiscardsTheStoredSamples) {
  Fixture f;
  f.SubscribeAndEnter();
  f.event.pending = {10.0, 20.0, 30.0};  // sent before the subscription
  f.controller.ReadAvailable();
  EXPECT_TRUE(f.publisher.published.empty());
  EXPECT_EQ(f.controller.counters().samples_discarded_stored, 3U);
  f.event.pending = {36.0};  // the first sample after the discard read
  f.controller.ReadAvailable();
  ASSERT_EQ(f.publisher.published.size(), 1U);
  EXPECT_EQ(f.publisher.published[0], 10.0F);
}

TEST(SpeedPathController, DiscardReadHappensEvenWhenNoSampleWasStored) {
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();  // empty discard read
  EXPECT_EQ(f.controller.counters().discard_reads, 1U);
  f.event.pending = {72.0};
  f.controller.ReadAvailable();
  ASSERT_EQ(f.publisher.published.size(), 1U);
  EXPECT_EQ(f.publisher.published[0], 20.0F);
}

TEST(SpeedPathController, EveryReturnToSubscribedDiscardsAgain) {
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();
  f.event.pending = {36.0};
  f.controller.ReadAvailable();
  ASSERT_EQ(f.publisher.published.size(), 1U);

  f.LeaveAndReenter();  // provider restart that reuses the shared memory
  f.event.pending = {36.0, 72.0};  // stored samples the new subscription returns
  f.controller.ReadAvailable();
  EXPECT_EQ(f.publisher.published.size(), 1U);
  EXPECT_EQ(f.controller.counters().discard_reads, 2U);
  f.event.pending = {108.0};
  f.controller.ReadAvailable();
  ASSERT_EQ(f.publisher.published.size(), 2U);
  EXPECT_EQ(f.publisher.published[1], 30.0F);
}

TEST(SpeedPathController, NoReadWhileTheSubscriptionIsNotSubscribed) {
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();
  f.event.state = SubscriptionState::kSubscriptionPending;
  f.controller.OnSubscriptionStateChanged(SubscriptionState::kSubscriptionPending);
  f.event.pending = {36.0};
  const auto reads_before = f.controller.counters().reads;
  f.controller.ReadAvailable();
  EXPECT_EQ(f.controller.counters().reads, reads_before);
  EXPECT_TRUE(f.publisher.published.empty());
  EXPECT_EQ(f.event.pending.size(), 1U);
}

TEST(SpeedPathController, ReadThatSpansALeaveAndReturnIsDroppedAndTheNextReadDiscards) {
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();
  f.event.pending = {36.0, 72.0};
  f.event.during_read = [&f]() { f.LeaveAndReenter(); };
  f.controller.ReadAvailable();
  EXPECT_TRUE(f.publisher.published.empty());
  EXPECT_EQ(f.controller.counters().samples_dropped_unstable, 2U);
  f.event.pending = {108.0};  // stored sample of the new phase
  f.controller.ReadAvailable();
  EXPECT_TRUE(f.publisher.published.empty());
  f.event.pending = {36.0};
  f.controller.ReadAvailable();
  ASSERT_EQ(f.publisher.published.size(), 1U);
}

TEST(SpeedPathController, ReadThatEndsOutsideSubscribedIsDropped) {
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();
  f.event.pending = {36.0};
  f.event.during_read = [&f]() {
    f.event.state = SubscriptionState::kSubscriptionPending;
    f.controller.OnSubscriptionStateChanged(SubscriptionState::kSubscriptionPending);
  };
  f.controller.ReadAvailable();
  EXPECT_TRUE(f.publisher.published.empty());
}

TEST(SpeedPathController, ATransitionIntoSubscribedThatTheReadSeesFirstStillGetsItsDiscard) {
  // LoLa stores the new state before it calls the state handler. A read that
  // runs in that gap sees kSubscribed while the handler has not run yet; the
  // leave notification came earlier, so that read is the discard read.
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();
  f.event.state = SubscriptionState::kSubscriptionPending;
  f.controller.OnSubscriptionStateChanged(SubscriptionState::kSubscriptionPending);
  f.event.state = SubscriptionState::kSubscribed;  // handler not called yet
  f.event.pending = {36.0};
  f.controller.ReadAvailable();
  EXPECT_TRUE(f.publisher.published.empty());
  f.controller.OnSubscriptionStateChanged(SubscriptionState::kSubscribed);  // late handler
  f.event.pending = {72.0};
  f.controller.ReadAvailable();
  ASSERT_EQ(f.publisher.published.size(), 1U);
  EXPECT_EQ(f.publisher.published[0], 20.0F);
}

TEST(SpeedPathController, PublishesInArrivalOrderAndReadsUntilEmpty) {
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();
  const std::vector<double> sent{3.6, 7.2, 10.8, 14.4, 18.0, 21.6, 25.2};  // more than one read holds
  f.event.pending.assign(sent.begin(), sent.end());
  f.controller.ReadAvailable();
  ASSERT_EQ(f.publisher.published.size(), sent.size());
  for (std::size_t i = 0; i < sent.size(); ++i) {
    EXPECT_EQ(f.publisher.published[i], static_cast<float>(sent[i] / 3.6));
  }
}

TEST(SpeedPathController, WithholdsNonFiniteSamplesAndCountsThem) {
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();
  f.event.pending = {36.0,
                     std::numeric_limits<double>::quiet_NaN(),
                     std::numeric_limits<double>::infinity(),
                     -std::numeric_limits<double>::infinity(),
                     1.0e300,
                     72.0};
  f.controller.ReadAvailable();
  ASSERT_EQ(f.publisher.published.size(), 2U);
  EXPECT_EQ(f.publisher.published[0], 10.0F);
  EXPECT_EQ(f.publisher.published[1], 20.0F);
  EXPECT_EQ(f.controller.counters().samples_withheld_non_finite, 3U);
  EXPECT_EQ(f.controller.counters().samples_withheld_out_of_range, 1U);
  EXPECT_EQ(f.controller.counters().samples_published, 2U);
}

class RecordingEvents final : public SpeedPathEvents {
 public:
  std::vector<std::string> events;
  void OnSampleWithheld(double speed_kmh, TranslationOutcome outcome) override {
    const char* kind = outcome == TranslationOutcome::kWithheldNonFinite ? "non_finite" : "out_of_range";
    events.push_back(std::string{"withheld "} + kind + (std::isnan(speed_kmh) ? " nan" : ""));
  }
  void OnStoredSamplesDiscarded(std::size_t count) override {
    events.push_back("discarded " + std::to_string(count));
  }
  void OnUnstableReadDropped(std::size_t count) override { events.push_back("unstable " + std::to_string(count)); }
};

TEST(SpeedPathController, ReportsEachWithheldSampleAndEachDiscardRead) {
  FakeSpeedEvent event;
  FakePublisher publisher;
  RecordingEvents events;
  SpeedPathController controller{event, publisher, kMaxSamples, &events};
  ASSERT_TRUE(controller.Subscribe());
  event.state = SubscriptionState::kSubscribed;
  controller.OnSubscriptionStateChanged(SubscriptionState::kSubscribed);
  event.pending = {1.0, 2.0};
  controller.ReadAvailable();
  event.pending = {std::numeric_limits<double>::quiet_NaN(), 1.0e300, 36.0};
  controller.ReadAvailable();
  event.pending = {36.0};
  event.during_read = [&]() {
    event.state = SubscriptionState::kSubscriptionPending;
    controller.OnSubscriptionStateChanged(SubscriptionState::kSubscriptionPending);
  };
  controller.ReadAvailable();
  EXPECT_EQ(events.events, (std::vector<std::string>{"discarded 2", "withheld non_finite nan", "withheld out_of_range",
                                                     "unstable 1"}));
}

TEST(SpeedPathController, FailedReadIsCountedAndPublishesNothing) {
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();
  f.event.fail_reads = true;
  f.controller.ReadAvailable();
  EXPECT_EQ(f.controller.counters().read_errors, 1U);
  EXPECT_TRUE(f.publisher.published.empty());
}

TEST(SpeedPathController, ShutdownFollowsTheSecondRuleInOrder) {
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();
  f.event.calls.clear();
  const ShutdownResult result = f.controller.Shutdown(std::chrono::milliseconds{100});
  EXPECT_EQ(result, ShutdownResult::kProxyDestroyed);
  EXPECT_EQ(f.event.calls,
            (std::vector<std::string>{"UnsetReceiveHandler", "Unsubscribe", "UnsetStateHandler", "DestroyProxy"}));
  EXPECT_TRUE(f.event.proxy_destroyed);
}

TEST(SpeedPathController, ShutdownWaitsUntilTheSubscriptionIsGone) {
  Fixture f;
  f.SubscribeAndEnter();
  f.event.unsubscribe_reaches_not_subscribed_after_polls = 3;
  EXPECT_EQ(f.controller.Shutdown(std::chrono::milliseconds{1000}), ShutdownResult::kProxyDestroyed);
  EXPECT_TRUE(f.event.proxy_destroyed);
}

TEST(SpeedPathController, ShutdownNeverDestroysAProxyThatStaysSubscribed) {
  Fixture f;
  f.SubscribeAndEnter();
  f.event.unsubscribe_reaches_not_subscribed_after_polls = 1000000;
  EXPECT_EQ(f.controller.Shutdown(std::chrono::milliseconds{30}), ShutdownResult::kStillSubscribed);
  EXPECT_FALSE(f.event.proxy_destroyed);
}

TEST(SpeedPathController, NoReadAfterShutdown) {
  Fixture f;
  f.SubscribeAndEnter();
  f.controller.ReadAvailable();
  ASSERT_EQ(f.controller.Shutdown(std::chrono::milliseconds{100}), ShutdownResult::kProxyDestroyed);
  f.event.calls.clear();
  f.event.pending = {36.0};
  f.controller.ReadAvailable();
  EXPECT_TRUE(f.event.calls.empty());
  EXPECT_TRUE(f.publisher.published.empty());
}

TEST(SpeedPathController, ShutdownWithoutAProxyTouchesNothing) {
  FakeSpeedEvent event;
  FakePublisher publisher;
  SpeedPathController controller{event, publisher, kMaxSamples};
  EXPECT_EQ(controller.Shutdown(std::chrono::milliseconds{10}), ShutdownResult::kNoProxy);
  EXPECT_TRUE(event.calls.empty());
}

}  // namespace
