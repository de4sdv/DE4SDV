// Unit tests of the discard rule in a subscription phase
// (receiverSubscriptionPhaseDiscardRule): the 20 ms margin before the phase
// start, the copy check, the positive fields, and no filter on order.

#include <gtest/gtest.h>

#include <cstdint>

#include "de4sdv_someip_receiver/discard_policy.hpp"

namespace {

using de4sdv::someip_receiver::FrameFields;
using de4sdv::someip_receiver::FrameVerdict;
using de4sdv::someip_receiver::PhaseStartDiscardPolicy;

constexpr std::int64_t kMs = 1'000'000;
constexpr std::int64_t kStart = 1'793'116'443'934'013'818;

FrameFields Frame(std::uint64_t sequence, std::int64_t timestamp_ns) { return FrameFields{sequence, timestamp_ns}; }

PhaseStartDiscardPolicy InPhase(std::int64_t start = kStart) {
  PhaseStartDiscardPolicy policy;
  policy.OnPhaseStart(start);
  return policy;
}

TEST(PhaseStartDiscardPolicy, MarginIsTwentyMilliseconds) {
  auto policy = InPhase();
  EXPECT_EQ(policy.Admit(Frame(1, kStart - 19 * kMs)), FrameVerdict::kDeliver);
  EXPECT_EQ(policy.Admit(Frame(2, kStart - 21 * kMs)), FrameVerdict::kDropOlderThanPhase);
  EXPECT_EQ(policy.Admit(Frame(3, kStart - 20 * kMs)), FrameVerdict::kDeliver);
  EXPECT_EQ(policy.Admit(Frame(4, kStart - 20 * kMs - 1)), FrameVerdict::kDropOlderThanPhase);
}

TEST(PhaseStartDiscardPolicy, OlderFrameThatIsNoCopyPasses) {
  auto policy = InPhase();
  EXPECT_EQ(policy.Admit(Frame(10, kStart + 100 * kMs)), FrameVerdict::kDeliver);
  // Older by sequence and by stamp, but produced in the phase and never served.
  EXPECT_EQ(policy.Admit(Frame(9, kStart + 50 * kMs)), FrameVerdict::kDeliver);
  EXPECT_EQ(policy.Admit(Frame(8, kStart)), FrameVerdict::kDeliver);
}

TEST(PhaseStartDiscardPolicy, CopyHasTheSameSequenceAndStamp) {
  auto policy = InPhase();
  EXPECT_EQ(policy.Admit(Frame(5, kStart + 1 * kMs)), FrameVerdict::kDeliver);
  EXPECT_EQ(policy.Admit(Frame(5, kStart + 1 * kMs)), FrameVerdict::kDropCopyInPhase);
  // Same sequence, other stamp (a restarted source): no copy.
  EXPECT_EQ(policy.Admit(Frame(5, kStart + 2 * kMs)), FrameVerdict::kDeliver);
  // Same stamp, other sequence: no copy.
  EXPECT_EQ(policy.Admit(Frame(6, kStart + 1 * kMs)), FrameVerdict::kDeliver);
}

TEST(PhaseStartDiscardPolicy, FieldsMustBePositive) {
  auto policy = InPhase();
  EXPECT_EQ(policy.Admit(Frame(0, kStart)), FrameVerdict::kDropFieldNotPositive);
  EXPECT_EQ(policy.Admit(Frame(1, 0)), FrameVerdict::kDropFieldNotPositive);
  EXPECT_EQ(policy.Admit(Frame(1, -5)), FrameVerdict::kDropFieldNotPositive);
  EXPECT_EQ(policy.Admit(Frame(1, kStart)), FrameVerdict::kDeliver);
}

TEST(PhaseStartDiscardPolicy, NoFrameIsServedOutsideAPhase) {
  PhaseStartDiscardPolicy policy;
  EXPECT_EQ(policy.Admit(Frame(1, kStart)), FrameVerdict::kDropOlderThanPhase);
  policy.OnPhaseStart(kStart);
  policy.OnPhaseEnd();
  EXPECT_FALSE(policy.in_phase());
  EXPECT_EQ(policy.Admit(Frame(2, kStart + 1 * kMs)), FrameVerdict::kDropOlderThanPhase);
}

TEST(PhaseStartDiscardPolicy, CopyMemoryBelongsToOnePhase) {
  auto policy = InPhase();
  EXPECT_EQ(policy.Admit(Frame(7, kStart + 5 * kMs)), FrameVerdict::kDeliver);
  policy.OnPhaseEnd();
  // A new phase that starts 10 ms later: the frame lies in its margin and was
  // not served in this phase, so it passes (the band of GAP-MW-045).
  policy.OnPhaseStart(kStart + 10 * kMs);
  EXPECT_EQ(policy.served_in_memory(), 0U);
  EXPECT_EQ(policy.Admit(Frame(7, kStart + 5 * kMs)), FrameVerdict::kDeliver);
}

TEST(PhaseStartDiscardPolicy, StoredFramesOfARestartInThePhaseAreCopiesOrLate) {
  auto policy = InPhase();
  for (std::uint64_t sequence = 1; sequence <= 30; ++sequence) {
    ASSERT_EQ(policy.Admit(Frame(sequence, kStart + static_cast<std::int64_t>(sequence) * 100 * kMs)),
              FrameVerdict::kDeliver);
  }
  // gatewayd restarts in the phase; its first read returns the 10 newest
  // stored frames: 23 to 30 were served, 31 and 32 came while it was down.
  for (std::uint64_t sequence = 23; sequence <= 30; ++sequence) {
    EXPECT_EQ(policy.Admit(Frame(sequence, kStart + static_cast<std::int64_t>(sequence) * 100 * kMs)),
              FrameVerdict::kDropCopyInPhase)
        << sequence;
  }
  EXPECT_EQ(policy.Admit(Frame(31, kStart + 3100 * kMs)), FrameVerdict::kDeliver);
  EXPECT_EQ(policy.Admit(Frame(32, kStart + 3200 * kMs)), FrameVerdict::kDeliver);
}

TEST(PhaseStartDiscardPolicy, CopyMemoryKeepsTheFortyFramesServedLast) {
  auto policy = InPhase();
  for (std::uint64_t sequence = 1; sequence <= 100; ++sequence) {
    ASSERT_EQ(policy.Admit(Frame(sequence, kStart + static_cast<std::int64_t>(sequence) * kMs)),
              FrameVerdict::kDeliver);
  }
  EXPECT_EQ(policy.served_in_memory(), PhaseStartDiscardPolicy::kCopyMemoryFrames);
  EXPECT_EQ(policy.Admit(Frame(61, kStart + 61 * kMs)), FrameVerdict::kDropCopyInPhase);
  EXPECT_EQ(policy.Admit(Frame(100, kStart + 100 * kMs)), FrameVerdict::kDropCopyInPhase);
  // Frame 60 left the memory: a repeat of it now passes.
  EXPECT_EQ(policy.Admit(Frame(60, kStart + 60 * kMs)), FrameVerdict::kDeliver);
}

// 12 stored frames arrive after 12 newer ones: 12 frames were served, then
// 12 newer frames, then the 12 first frames come again from the slots.
std::size_t ServedTwice(std::size_t memory_frames) {
  PhaseStartDiscardPolicy policy{memory_frames};
  policy.OnPhaseStart(kStart);
  for (std::uint64_t sequence = 1; sequence <= 24; ++sequence) {
    EXPECT_EQ(policy.Admit(Frame(sequence, kStart + static_cast<std::int64_t>(sequence) * kMs)),
              FrameVerdict::kDeliver);
  }
  std::size_t twice = 0;
  for (std::uint64_t sequence = 1; sequence <= 12; ++sequence) {
    if (policy.Admit(Frame(sequence, kStart + static_cast<std::int64_t>(sequence) * kMs)) == FrameVerdict::kDeliver) {
      ++twice;
    }
  }
  return twice;
}

TEST(PhaseStartDiscardPolicy, MemoryOfFortyServesNoStoredFrameTwice) {
  EXPECT_EQ(ServedTwice(10), 12U);
  EXPECT_EQ(ServedTwice(20), 12U);
  EXPECT_EQ(ServedTwice(PhaseStartDiscardPolicy::kCopyMemoryFrames), 0U);
}

}  // namespace
