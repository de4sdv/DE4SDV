// Unit tests of the provisional discard policy of the pure receiver core:
// a frame is delivered only if its sequence is greater than the last one
// delivered to the current loopback client and its frame_timestamp_ns is
// not older than the phase start minus the clock-offset bound.

#include <gtest/gtest.h>

#include <cstdint>

#include "de4sdv_someip_receiver/discard_policy.hpp"

namespace {

using de4sdv::someip_receiver::FrameFields;
using de4sdv::someip_receiver::FrameVerdict;
using de4sdv::someip_receiver::PhaseCause;
using de4sdv::someip_receiver::ProvisionalDiscardPolicy;

constexpr std::int64_t kMs = 1'000'000;
constexpr std::int64_t kBound = 50 * kMs;
constexpr std::int64_t kStart = 1'793'116'443'934'013'818;

FrameFields Frame(std::uint64_t sequence, std::int64_t timestamp_ns) { return FrameFields{sequence, timestamp_ns}; }

ProvisionalDiscardPolicy InPhase(PhaseCause cause = PhaseCause::kClientConnected) {
  ProvisionalDiscardPolicy policy{kBound};
  policy.OnPhaseStart(cause, kStart);
  return policy;
}

TEST(ProvisionalDiscardPolicy, NoFrameIsDeliveredBeforeAPhaseStarts) {
  ProvisionalDiscardPolicy policy{kBound};
  EXPECT_FALSE(policy.in_phase());
  EXPECT_EQ(policy.Admit(Frame(1, kStart)), FrameVerdict::kDropOlderThanPhase);
}

TEST(ProvisionalDiscardPolicy, TheBoundIsInclusive) {
  auto policy = InPhase();
  EXPECT_EQ(policy.Admit(Frame(1, kStart - kBound - 1)), FrameVerdict::kDropOlderThanPhase);
  EXPECT_EQ(policy.Admit(Frame(2, kStart - kBound)), FrameVerdict::kDeliver);
  EXPECT_EQ(policy.Admit(Frame(3, kStart + 10 * kMs)), FrameVerdict::kDeliver);
}

TEST(ProvisionalDiscardPolicy, ZeroBoundDropsEveryFrameBeforeThePhaseStart) {
  ProvisionalDiscardPolicy policy{0};
  policy.OnPhaseStart(PhaseCause::kSubscriptionAcknowledged, kStart);
  EXPECT_EQ(policy.Admit(Frame(1, kStart - 1)), FrameVerdict::kDropOlderThanPhase);
  EXPECT_EQ(policy.Admit(Frame(2, kStart)), FrameVerdict::kDeliver);
}

TEST(ProvisionalDiscardPolicy, SequenceMustIncrease) {
  auto policy = InPhase();
  EXPECT_EQ(policy.Admit(Frame(5, kStart)), FrameVerdict::kDeliver);
  EXPECT_EQ(policy.Admit(Frame(5, kStart + kMs)), FrameVerdict::kDropSequenceNotIncreasing);
  EXPECT_EQ(policy.Admit(Frame(4, kStart + 2 * kMs)), FrameVerdict::kDropSequenceNotIncreasing);
  EXPECT_EQ(policy.Admit(Frame(7, kStart + 3 * kMs)), FrameVerdict::kDeliver);
  EXPECT_EQ(policy.last_delivered_sequence(), 7U);
}

TEST(ProvisionalDiscardPolicy, SequenceZeroIsNeverDelivered) {
  auto policy = InPhase();
  EXPECT_EQ(policy.Admit(Frame(0, kStart)), FrameVerdict::kDropSequenceNotIncreasing);
}

TEST(ProvisionalDiscardPolicy, StoredFramesAfterANewSubscriptionAreDropped) {
  auto policy = InPhase(PhaseCause::kClientConnected);
  EXPECT_EQ(policy.Admit(Frame(40, kStart + 100 * kMs)), FrameVerdict::kDeliver);
  // The subscription is lost and acknowledged again 5 s later; the layer then
  // sends nine frames that it stored about 4 s before the new phase.
  const std::int64_t resubscribed = kStart + 5000 * kMs;
  policy.OnPhaseStart(PhaseCause::kSubscriptionAcknowledged, resubscribed);
  for (std::uint64_t sequence = 42; sequence <= 50; ++sequence) {
    const std::int64_t produced = resubscribed - 4100 * kMs + static_cast<std::int64_t>(sequence - 42) * 100 * kMs;
    EXPECT_EQ(policy.Admit(Frame(sequence, produced)), FrameVerdict::kDropOlderThanPhase) << sequence;
  }
  EXPECT_EQ(policy.Admit(Frame(51, resubscribed + 10 * kMs)), FrameVerdict::kDeliver);
}

TEST(ProvisionalDiscardPolicy, NewSubscriptionKeepsTheFloorOfTheSameClient) {
  auto policy = InPhase(PhaseCause::kClientConnected);
  EXPECT_EQ(policy.Admit(Frame(10, kStart)), FrameVerdict::kDeliver);
  const std::int64_t resubscribed = kStart + 1000 * kMs;
  policy.OnPhaseStart(PhaseCause::kSubscriptionAcknowledged, resubscribed);
  // A frame already delivered comes again with a fresh timestamp: still a duplicate.
  EXPECT_EQ(policy.Admit(Frame(10, resubscribed)), FrameVerdict::kDropSequenceNotIncreasing);
  EXPECT_EQ(policy.Admit(Frame(11, resubscribed - kBound - 1)), FrameVerdict::kDropOlderThanPhase);
  EXPECT_EQ(policy.Admit(Frame(12, resubscribed)), FrameVerdict::kDeliver);
}

TEST(ProvisionalDiscardPolicy, NewClientResetsTheFloor) {
  auto policy = InPhase(PhaseCause::kClientConnected);
  EXPECT_EQ(policy.Admit(Frame(100, kStart)), FrameVerdict::kDeliver);
  const std::int64_t reconnected = kStart + 2000 * kMs;
  policy.OnPhaseStart(PhaseCause::kClientConnected, reconnected);
  EXPECT_EQ(policy.last_delivered_sequence(), 0U);
  EXPECT_EQ(policy.Admit(Frame(99, reconnected - kBound - 1)), FrameVerdict::kDropOlderThanPhase);
  EXPECT_EQ(policy.Admit(Frame(3, reconnected)), FrameVerdict::kDeliver);
}

TEST(ProvisionalDiscardPolicy, NegativeTimestampIsOlderThanAnyPhase) {
  auto policy = InPhase();
  EXPECT_EQ(policy.Admit(Frame(1, INT64_MIN)), FrameVerdict::kDropOlderThanPhase);
}

}  // namespace
