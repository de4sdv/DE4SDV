// DE4SDV facade over Eclipse S-CORE communication (mw::com) for the
// AutowareToSCORE adapter (INC-MW-011, GAP-MW-035).
//
// Build route: Bazel compiles this facade with the S-CORE SOME/IP gateway's
// own toolchain inside a throwaway checkout of the gateway and bundles it,
// with communication and baselibs, into one static archive
// (cc_static_library). That archive carries no libstdc++. The adapter's
// ament_cmake package then links the archive with rclcpp, g++ and the shared
// libstdc++, so the process holds one C++ runtime.
//
// This header uses plain types only (bool, integers, double, byte pointers,
// C function pointers). No S-CORE type and no standard library class crosses
// it, so the two compilers never have to agree on a class layout. Every
// function is noexcept; errors come back as return values, with a message
// from LastError().

#ifndef DE4SDV_SCORE_FACADE_SCORE_FACADE_H
#define DE4SDV_SCORE_FACADE_SCORE_FACADE_H

#include <cstddef>
#include <cstdint>

namespace de4sdv::score_facade {

// A sample of the frame event holds the length prefix and the frame.
constexpr std::size_t kFrameSampleBytes = 2048;

enum class SubscriptionState : std::uint8_t {
  kNotSubscribed = 0,
  kSubscriptionPending = 1,
  kSubscribed = 2,
};

enum class SendResult : std::uint8_t {
  kSent = 0,
  kTooLarge = 1,
  kAllocateFailed = 2,
  kSendFailed = 3,
  kNotOffered = 4,
};

// Called by mw::com under its own lock: the callee must not call back into
// the same SpeedSubscriber.
using StateCallback = void (*)(void* context, SubscriptionState state);
using ReceiveCallback = void (*)(void* context);
using SpeedSampleCallback = void (*)(void* context, double speed_kmh);

// Initializes the mw::com runtime once per process with the given
// configuration file. Returns false, and initializes nothing, when the file
// cannot be read. mw::com itself terminates the process on an invalid
// configuration.
bool InitializeRuntime(const char* mw_com_configuration_path) noexcept;

// mw::com proxy of the reference vehicle speed event.
class SpeedSubscriber {
 public:
  explicit SpeedSubscriber(const char* instance_specifier) noexcept;
  // Destroys a remaining proxy only when it is not subscribed. A subscribed
  // proxy is released without destruction, because destroying it aborts the
  // process (GAP-MW-041).
  ~SpeedSubscriber() noexcept;
  SpeedSubscriber(const SpeedSubscriber&) = delete;
  SpeedSubscriber& operator=(const SpeedSubscriber&) = delete;

  // One FindService. Creates the proxy when the provider is found and
  // returns true when a proxy exists.
  bool FindAndCreate() noexcept;
  bool HasProxy() const noexcept;

  bool SetStateHandler(StateCallback callback, void* context) noexcept;
  void UnsetStateHandler() noexcept;
  bool SetReceiveHandler(ReceiveCallback callback, void* context) noexcept;
  void UnsetReceiveHandler() noexcept;
  bool Subscribe(std::size_t max_samples) noexcept;
  void Unsubscribe() noexcept;
  SubscriptionState State() const noexcept;
  // Calls callback once per new sample, oldest first, and releases each
  // sample before the next. Returns the number of samples, or -1.
  std::int64_t ReadNewSamples(std::size_t max_samples, SpeedSampleCallback callback, void* context) noexcept;
  void DestroyProxy() noexcept;

  const char* LastError() const noexcept;

 private:
  struct Impl;
  Impl* impl_;
};

// mw::com skeleton of the AEBS signal frame event.
class FramePublisher {
 public:
  explicit FramePublisher(const char* instance_specifier) noexcept;
  ~FramePublisher() noexcept;
  FramePublisher(const FramePublisher&) = delete;
  FramePublisher& operator=(const FramePublisher&) = delete;

  bool Create() noexcept;
  bool Offer() noexcept;
  // Copies sample_size bytes (at most kFrameSampleBytes) into one allocated
  // sample and sends it. A sample that finds no free slot is not sent.
  SendResult Send(const std::uint8_t* sample, std::size_t sample_size) noexcept;
  void StopOfferAndDestroy() noexcept;

  const char* LastError() const noexcept;

 private:
  struct Impl;
  Impl* impl_;
};

}  // namespace de4sdv::score_facade

#endif  // DE4SDV_SCORE_FACADE_SCORE_FACADE_H
