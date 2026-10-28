// The ports of the pure core, implemented with the DE4SDV S-CORE facade.

#ifndef DE4SDV_SCORE_ADAPTER_FACADE_PORTS_HPP
#define DE4SDV_SCORE_ADAPTER_FACADE_PORTS_HPP

#include "de4sdv_score_adapter/ports.hpp"
#include "de4sdv_score_facade/score_facade.h"

namespace de4sdv::score_adapter {

SubscriptionState FromFacade(score_facade::SubscriptionState state) noexcept;
const char* ToText(SubscriptionState state) noexcept;

class FacadeSpeedEventPort final : public SpeedEventPort {
 public:
  explicit FacadeSpeedEventPort(score_facade::SpeedSubscriber& subscriber) : subscriber_{subscriber} {}

  // The handlers that SetStateHandler() and SetReceiveHandler() register.
  void BindHandlers(score_facade::StateCallback state_callback, score_facade::ReceiveCallback receive_callback,
                    void* context) noexcept {
    state_callback_ = state_callback;
    receive_callback_ = receive_callback;
    context_ = context;
  }

  bool SetStateHandler() override { return subscriber_.SetStateHandler(state_callback_, context_); }
  bool SetReceiveHandler() override { return subscriber_.SetReceiveHandler(receive_callback_, context_); }
  bool Subscribe(std::size_t max_samples) override { return subscriber_.Subscribe(max_samples); }
  void Unsubscribe() override { subscriber_.Unsubscribe(); }
  SubscriptionState State() const override { return FromFacade(subscriber_.State()); }
  std::int64_t ReadNewSamples(std::size_t max_samples, const SampleSink& sink) override;
  void UnsetReceiveHandler() override { subscriber_.UnsetReceiveHandler(); }
  void UnsetStateHandler() override { subscriber_.UnsetStateHandler(); }
  void DestroyProxy() override { subscriber_.DestroyProxy(); }

 private:
  score_facade::SpeedSubscriber& subscriber_;
  score_facade::StateCallback state_callback_{nullptr};
  score_facade::ReceiveCallback receive_callback_{nullptr};
  void* context_{nullptr};
};

class FacadeFrameEventPort final : public FrameEventPort {
 public:
  explicit FacadeFrameEventPort(score_facade::FramePublisher& publisher) : publisher_{publisher} {}

  bool Offer() override { return publisher_.Offer(); }
  FrameSendResult Send(const std::uint8_t* sample, std::size_t sample_size) override;
  void StopOfferAndDestroy() override { publisher_.StopOfferAndDestroy(); }

 private:
  score_facade::FramePublisher& publisher_;
};

}  // namespace de4sdv::score_adapter

#endif  // DE4SDV_SCORE_ADAPTER_FACADE_PORTS_HPP
