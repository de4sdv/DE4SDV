// Unit tests of the frame path controller of the pure adapter core: the third
// LoLa rule of the adapter (phase-8 realization of INC-MW-011). The adapter
// offers its frame skeleton once at start. It does not stop the offer when
// the frame stream on 127.0.0.1:4721 goes away; it reconnects with a bounded
// backoff. The skeleton is destroyed only at exit (GAP-MW-036 notes the abort
// of a skeleton that stops its offer under a subscribed proxy and offers
// again).

#include <gtest/gtest.h>

#include <chrono>
#include <cstdint>
#include <string>
#include <vector>

#include "de4sdv_score_adapter/frame_path_controller.hpp"

namespace {

using de4sdv::score_adapter::FrameEventPort;
using de4sdv::score_adapter::FramePathController;
using de4sdv::score_adapter::FrameSendResult;
using de4sdv::score_adapter::ReconnectBackoff;
using Bytes = std::vector<std::uint8_t>;
using std::chrono::milliseconds;

class FakeFrameEvent final : public FrameEventPort {
 public:
  std::vector<std::string> calls;
  std::vector<Bytes> sent;
  FrameSendResult next_result{FrameSendResult::kSent};
  bool offer_result{true};

  bool Offer() override {
    calls.push_back("Offer");
    return offer_result;
  }
  FrameSendResult Send(const std::uint8_t* sample, std::size_t sample_size) override {
    calls.push_back("Send");
    if (next_result == FrameSendResult::kSent) {
      sent.emplace_back(sample, sample + sample_size);
    }
    return next_result;
  }
  void StopOfferAndDestroy() override { calls.push_back("StopOfferAndDestroy"); }
};

const Bytes kFrame{0x02, 0x00, 0x00, 0x00, 0xAB, 0xCD};

TEST(FramePathController, StartOffersTheSkeletonOnce) {
  FakeFrameEvent event;
  FramePathController controller{event};
  EXPECT_TRUE(controller.Start());
  EXPECT_TRUE(controller.Start());
  EXPECT_EQ(event.calls, (std::vector<std::string>{"Offer"}));
  EXPECT_EQ(controller.counters().offers, 1U);
}

TEST(FramePathController, FailedOfferIsReported) {
  FakeFrameEvent event;
  event.offer_result = false;
  FramePathController controller{event};
  EXPECT_FALSE(controller.Start());
  EXPECT_FALSE(controller.offered());
}

TEST(FramePathController, FrameBeforeTheOfferIsNotSent) {
  FakeFrameEvent event;
  FramePathController controller{event};
  controller.OnFrame(kFrame.data(), kFrame.size());
  EXPECT_TRUE(event.calls.empty());
  EXPECT_EQ(controller.counters().frames_not_offered, 1U);
}

TEST(FramePathController, FrameIsSentUnchanged) {
  FakeFrameEvent event;
  FramePathController controller{event};
  ASSERT_TRUE(controller.Start());
  controller.OnFrame(kFrame.data(), kFrame.size());
  ASSERT_EQ(event.sent.size(), 1U);
  EXPECT_EQ(event.sent[0], kFrame);
  EXPECT_EQ(controller.counters().frames_sent, 1U);
}

TEST(FramePathController, FrameWithoutAFreeSlotIsDroppedAndCountedWithoutRetry) {
  FakeFrameEvent event;
  FramePathController controller{event};
  ASSERT_TRUE(controller.Start());
  event.next_result = FrameSendResult::kAllocateFailed;
  controller.OnFrame(kFrame.data(), kFrame.size());
  EXPECT_EQ(controller.counters().frames_allocate_failed, 1U);
  EXPECT_EQ(event.calls, (std::vector<std::string>{"Offer", "Send"}));
}

TEST(FramePathController, OtherSendFailuresAreCountedApart) {
  FakeFrameEvent event;
  FramePathController controller{event};
  ASSERT_TRUE(controller.Start());
  event.next_result = FrameSendResult::kSendFailed;
  controller.OnFrame(kFrame.data(), kFrame.size());
  event.next_result = FrameSendResult::kTooLarge;
  controller.OnFrame(kFrame.data(), kFrame.size());
  EXPECT_EQ(controller.counters().frames_send_failed, 1U);
  EXPECT_EQ(controller.counters().frames_too_large, 1U);
}

TEST(FramePathController, LossOfTheFrameStreamNeverStopsTheOffer) {
  FakeFrameEvent event;
  FramePathController controller{event};
  ASSERT_TRUE(controller.Start());
  for (int i = 0; i < 5; ++i) {
    controller.OnConnectionEstablished();
    controller.OnConnectionLost();
  }
  EXPECT_EQ(event.calls, (std::vector<std::string>{"Offer"}));
  EXPECT_EQ(controller.counters().connection_losses, 5U);
  EXPECT_EQ(controller.counters().connections, 5U);
  controller.OnFrame(kFrame.data(), kFrame.size());
  EXPECT_EQ(event.sent.size(), 1U);
}

TEST(FramePathController, StopDestroysTheSkeletonOnceAndEndsSending) {
  FakeFrameEvent event;
  FramePathController controller{event};
  ASSERT_TRUE(controller.Start());
  controller.Stop();
  controller.Stop();
  controller.OnFrame(kFrame.data(), kFrame.size());
  EXPECT_EQ(event.calls, (std::vector<std::string>{"Offer", "StopOfferAndDestroy"}));
  EXPECT_FALSE(controller.offered());
}

TEST(FramePathController, StopWithoutAnOfferDestroysNothing) {
  FakeFrameEvent event;
  FramePathController controller{event};
  controller.Stop();
  EXPECT_TRUE(event.calls.empty());
}

TEST(FramePathController, NoOfferAfterStop) {
  FakeFrameEvent event;
  FramePathController controller{event};
  ASSERT_TRUE(controller.Start());
  controller.Stop();
  EXPECT_FALSE(controller.Start());
  EXPECT_EQ(event.calls, (std::vector<std::string>{"Offer", "StopOfferAndDestroy"}));
}

TEST(ReconnectBackoff, DoublesUpToTheCapAndResets) {
  ReconnectBackoff backoff{milliseconds{100}, milliseconds{1000}};
  EXPECT_EQ(backoff.NextDelay(), milliseconds{100});
  EXPECT_EQ(backoff.NextDelay(), milliseconds{200});
  EXPECT_EQ(backoff.NextDelay(), milliseconds{400});
  EXPECT_EQ(backoff.NextDelay(), milliseconds{800});
  EXPECT_EQ(backoff.NextDelay(), milliseconds{1000});
  EXPECT_EQ(backoff.NextDelay(), milliseconds{1000});
  backoff.Reset();
  EXPECT_EQ(backoff.NextDelay(), milliseconds{100});
}

}  // namespace
