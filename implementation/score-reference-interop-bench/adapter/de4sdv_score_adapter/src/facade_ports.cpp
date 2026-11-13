#include "facade_ports.hpp"

namespace de4sdv::score_adapter {

namespace {

void DeliverSample(void* context, double speed_kmh) {
  (*static_cast<const SpeedEventPort::SampleSink*>(context))(speed_kmh);
}

}  // namespace

SubscriptionState FromFacade(score_facade::SubscriptionState state) noexcept {
  switch (state) {
    case score_facade::SubscriptionState::kSubscribed:
      return SubscriptionState::kSubscribed;
    case score_facade::SubscriptionState::kSubscriptionPending:
      return SubscriptionState::kSubscriptionPending;
    case score_facade::SubscriptionState::kNotSubscribed:
    default:
      return SubscriptionState::kNotSubscribed;
  }
}

const char* ToText(SubscriptionState state) noexcept {
  switch (state) {
    case SubscriptionState::kSubscribed:
      return "subscribed";
    case SubscriptionState::kSubscriptionPending:
      return "subscription_pending";
    case SubscriptionState::kNotSubscribed:
    default:
      return "not_subscribed";
  }
}

std::int64_t FacadeSpeedEventPort::ReadNewSamples(std::size_t max_samples, const SampleSink& sink) {
  return subscriber_.ReadNewSamples(max_samples, &DeliverSample, const_cast<SampleSink*>(&sink));
}

FrameSendResult FacadeFrameEventPort::Send(const std::uint8_t* sample, std::size_t sample_size) {
  switch (publisher_.Send(sample, sample_size)) {
    case score_facade::SendResult::kSent:
      return FrameSendResult::kSent;
    case score_facade::SendResult::kTooLarge:
      return FrameSendResult::kTooLarge;
    case score_facade::SendResult::kAllocateFailed:
      return FrameSendResult::kAllocateFailed;
    case score_facade::SendResult::kNotOffered:
      return FrameSendResult::kNotOffered;
    case score_facade::SendResult::kSendFailed:
    default:
      return FrameSendResult::kSendFailed;
  }
}

}  // namespace de4sdv::score_adapter
