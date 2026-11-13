// Unit tests of the retry schedule of the gateway worker: the periods of the
// model after each end, the back-off after three silent subscriptions, the
// slow period after the start diagnostic, and the bounded client retry.

#include <gtest/gtest.h>

#include <cstdint>

#include "de4sdv_ivi_frame_relay/retry_schedule.hpp"

namespace {

using de4sdv::ivi_frame_relay::EndedByLayer;
using de4sdv::ivi_frame_relay::kClientFastRetryWindowNs;
using de4sdv::ivi_frame_relay::kDestroyedFastWindowNs;
using de4sdv::ivi_frame_relay::kDestroyedRetryPeriodNs;
using de4sdv::ivi_frame_relay::kRetryPeriodNs;
using de4sdv::ivi_frame_relay::kSilenceTimeoutNs;
using de4sdv::ivi_frame_relay::kSilentBackOffNs;
using de4sdv::ivi_frame_relay::kSlowRetryPeriodNs;
using de4sdv::ivi_frame_relay::kStartDiagnosticNs;
using de4sdv::ivi_frame_relay::RetrySchedule;
using de4sdv::ivi_frame_relay::SubscriptionEnd;
using de4sdv::ivi_frame_relay::ToText;

constexpr std::int64_t kMs = 1'000'000;
constexpr std::int64_t kS = 1'000'000'000;
constexpr std::int64_t kT0 = 7'000 * kS;

TEST(RetrySchedule, TimingIsTheModels) {
  EXPECT_EQ(kSilenceTimeoutNs, 3 * kS);
  EXPECT_EQ(kDestroyedRetryPeriodNs, 100 * kMs);
  EXPECT_EQ(kDestroyedFastWindowNs, 5 * kS);
  EXPECT_EQ(kRetryPeriodNs, 1 * kS);
  EXPECT_EQ(kSilentBackOffNs, 5 * kS);
  EXPECT_EQ(kStartDiagnosticNs, 30 * kS);
  EXPECT_EQ(kSlowRetryPeriodNs, 10 * kS);
}

TEST(RetrySchedule, StartTriesEverySecondThenEveryTenSecondsAfterThirtySeconds) {
  const RetrySchedule schedule{kT0};
  EXPECT_EQ(schedule.FirstAttemptNs(kT0), kT0);
  EXPECT_EQ(schedule.NextAttemptNs(kT0, kT0 + 5 * kMs), kT0 + 1 * kS);
  EXPECT_STREQ(schedule.SubscribeRule(kT0 + 29 * kS), "start");
  EXPECT_EQ(schedule.NextAttemptNs(kT0 + 29 * kS, kT0 + 29 * kS), kT0 + 30 * kS);
  EXPECT_STREQ(schedule.SubscribeRule(kT0 + 30 * kS), "start_after_diagnostic");
  EXPECT_EQ(schedule.NextAttemptNs(kT0 + 30 * kS, kT0 + 30 * kS), kT0 + 40 * kS);
}

TEST(RetrySchedule, PublicationDestroyedRetriesEvery100MsForFiveSecondsThenEverySecond) {
  RetrySchedule schedule{kT0};
  schedule.OnSubscribed();
  const std::int64_t destroyed = kT0 + 60 * kS;
  schedule.OnEnded(SubscriptionEnd::kPublicationDestroyed, 500, destroyed);
  EXPECT_EQ(schedule.FirstAttemptNs(destroyed), destroyed);
  EXPECT_EQ(schedule.NextAttemptNs(destroyed, destroyed + 2 * kMs), destroyed + 100 * kMs);
  EXPECT_STREQ(schedule.SubscribeRule(destroyed + 4900 * kMs), "publication_destroyed_first_5_s");
  EXPECT_EQ(schedule.NextAttemptNs(destroyed + 4900 * kMs, destroyed + 4900 * kMs), destroyed + 5000 * kMs);
  EXPECT_STREQ(schedule.SubscribeRule(destroyed + 5000 * kMs), "every_second");
  EXPECT_EQ(schedule.NextAttemptNs(destroyed + 5000 * kMs, destroyed + 5000 * kMs), destroyed + 6000 * kMs);
}

TEST(RetrySchedule, AnAttemptLongerThanItsPeriodIsFollowedAtOnce) {
  RetrySchedule schedule{kT0};
  schedule.OnSubscribed();
  schedule.OnEnded(SubscriptionEnd::kPublicationDestroyed, 1, kT0);
  EXPECT_EQ(schedule.NextAttemptNs(kT0, kT0 + 250 * kMs), kT0 + 250 * kMs);
}

TEST(RetrySchedule, SilenceResubscribesAtOnceThenBacksOffAfterThreeSilentSubscriptions) {
  RetrySchedule schedule{kT0};
  schedule.OnSubscribed();
  std::int64_t at = kT0 + 10 * kS;
  schedule.OnEnded(SubscriptionEnd::kSilenceTimeout, 120, at);  // brought messages, then went quiet
  EXPECT_EQ(schedule.consecutive_silent(), 0U);
  EXPECT_EQ(schedule.FirstAttemptNs(at), at);
  EXPECT_EQ(schedule.NextAttemptNs(at, at), at + 1 * kS);
  for (std::uint64_t silent = 1; silent <= 2; ++silent) {
    at += 4 * kS;
    schedule.OnSubscribed();
    schedule.OnEnded(SubscriptionEnd::kSilenceTimeout, 0, at);
    EXPECT_EQ(schedule.consecutive_silent(), silent);
    EXPECT_EQ(schedule.FirstAttemptNs(at), at) << silent;
  }
  at += 4 * kS;
  schedule.OnSubscribed();
  schedule.OnEnded(SubscriptionEnd::kSilenceTimeout, 0, at);
  EXPECT_EQ(schedule.consecutive_silent(), 3U);
  EXPECT_EQ(schedule.FirstAttemptNs(at), at + 5 * kS);
  EXPECT_STREQ(schedule.SubscribeRule(at + 5 * kS), "silent_subscriptions_back_off");
  EXPECT_EQ(schedule.NextAttemptNs(at + 5 * kS, at + 5 * kS), at + 10 * kS);
  // A subscription that brings a message ends the back-off.
  schedule.OnSubscribed();
  schedule.OnEnded(SubscriptionEnd::kSilenceTimeout, 1, at + 20 * kS);
  EXPECT_EQ(schedule.consecutive_silent(), 0U);
  EXPECT_EQ(schedule.FirstAttemptNs(at + 20 * kS), at + 20 * kS);
}

TEST(RetrySchedule, PublicationDestroyedKeepsItsFastRetriesAfterSilentSubscriptions) {
  RetrySchedule schedule{kT0};
  for (int silent = 0; silent < 3; ++silent) {
    schedule.OnSubscribed();
    schedule.OnEnded(SubscriptionEnd::kSilenceTimeout, 0, kT0 + silent * 4 * kS);
  }
  schedule.OnSubscribed();
  schedule.OnEnded(SubscriptionEnd::kPublicationDestroyed, 0, kT0 + 20 * kS);
  EXPECT_EQ(schedule.consecutive_silent(), 4U);
  EXPECT_EQ(schedule.FirstAttemptNs(kT0 + 20 * kS), kT0 + 20 * kS);
  EXPECT_EQ(schedule.NextAttemptNs(kT0 + 20 * kS, kT0 + 20 * kS), kT0 + 20 * kS + 100 * kMs);
}

TEST(RetrySchedule, ClientCreationRetriesEverySecondThenEveryTenSeconds) {
  RetrySchedule schedule{kT0};
  EXPECT_EQ(schedule.NextClientAttemptNs(kT0, kT0), kT0 + 1 * kS);
  EXPECT_EQ(schedule.NextClientAttemptNs(kT0 + 29 * kS, kT0 + 29 * kS), kT0 + 30 * kS);
  EXPECT_EQ(schedule.NextClientAttemptNs(kT0 + 30 * kS, kT0 + 30 * kS), kT0 + 40 * kS);
  EXPECT_EQ(kClientFastRetryWindowNs, 30 * kS);
}

TEST(RetrySchedule, OnlyTheLayersEndsAreLayerCaused) {
  EXPECT_TRUE(EndedByLayer(SubscriptionEnd::kPublicationDestroyed));
  EXPECT_TRUE(EndedByLayer(SubscriptionEnd::kDisconnected));
  EXPECT_TRUE(EndedByLayer(SubscriptionEnd::kSilenceTimeout));
  EXPECT_FALSE(EndedByLayer(SubscriptionEnd::kRelayStop));
  EXPECT_STREQ(ToText(SubscriptionEnd::kSilenceTimeout), "silence_timeout");
}

}  // namespace
