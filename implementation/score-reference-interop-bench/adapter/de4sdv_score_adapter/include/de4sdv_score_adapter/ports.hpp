// Ports of the pure adapter core. The core never includes an S-CORE or a
// ROS 2 header: the adapter executable implements these ports with the
// DE4SDV S-CORE facade (mw::com) and with rclcpp, and the unit tests
// implement them with fakes.

#ifndef DE4SDV_SCORE_ADAPTER_PORTS_HPP
#define DE4SDV_SCORE_ADAPTER_PORTS_HPP

#include <cstddef>
#include <cstdint>
#include <functional>

namespace de4sdv::score_adapter {

// The three subscription states of an mw::com proxy event.
enum class SubscriptionState : std::uint8_t {
  kNotSubscribed,
  kSubscriptionPending,
  kSubscribed,
};

// The mw::com proxy event of the reference vehicle speed (port
// referenceSpeedIn of the phase-8 realization).
class SpeedEventPort {
 public:
  using SampleSink = std::function<void(double speed_kmh)>;

  virtual ~SpeedEventPort() = default;

  // Register the subscription state handler and the receive handler of the
  // adapter with the proxy event; false when mw::com refuses.
  virtual bool SetStateHandler() = 0;
  virtual bool SetReceiveHandler() = 0;
  virtual bool Subscribe(std::size_t max_samples) = 0;
  virtual void Unsubscribe() = 0;
  virtual SubscriptionState State() const = 0;
  // Hands the new samples to sink, oldest first, at most max_samples. As in
  // LoLa, when more than max_samples new samples wait, only the newest
  // max_samples come; the older ones are skipped for good. Returns the
  // number of samples, or -1 when the read failed. No sample stays held
  // after the call.
  virtual std::int64_t ReadNewSamples(std::size_t max_samples, const SampleSink& sink) = 0;
  virtual void UnsetReceiveHandler() = 0;
  virtual void UnsetStateHandler() = 0;
  virtual void DestroyProxy() = 0;
};

// The ROS 2 publisher of /de4sdv/middleware/velocity_status (port
// middlewareVelocityStatusOut). The implementation stamps each message with
// the receipt time.
class VelocityPublisherPort {
 public:
  virtual ~VelocityPublisherPort() = default;
  virtual void Publish(float longitudinal_velocity_mps) = 0;
};

// The result of one send on the frame event.
enum class FrameSendResult : std::uint8_t {
  kSent,
  kTooLarge,
  kAllocateFailed,  // no free sample slot (GAP-MW-037)
  kSendFailed,
  kNotOffered,
};

// The mw::com skeleton event of the AEBS signal frame (port
// aebsSignalFrameOut).
class FrameEventPort {
 public:
  virtual ~FrameEventPort() = default;
  virtual bool Offer() = 0;
  virtual FrameSendResult Send(const std::uint8_t* sample, std::size_t sample_size) = 0;
  // Stops the offer and destroys the skeleton.
  virtual void StopOfferAndDestroy() = 0;
};

}  // namespace de4sdv::score_adapter

#endif  // DE4SDV_SCORE_ADAPTER_PORTS_HPP
