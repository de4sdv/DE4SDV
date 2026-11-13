// DE4SDV facade over Eclipse S-CORE communication (mw::com); see
// score_facade.h. Compiled by Bazel inside the throwaway gateway checkout.

#include "de4sdv_score_facade/score_facade.h"

#include <cstdio>
#include <cstring>
#include <memory>
#include <string>
#include <utility>

#include "de4sdv_score_interface/aebs_signal_frame_service.h"
#include "de4sdv_score_interface/reference_vehicle_speed_service.h"
#include "score/filesystem/path.h"
#include "score/mw/com/runtime.h"
#include "score/mw/com/types.h"

namespace de4sdv::score_facade {

namespace {

using de4sdv::score_interface::AebsSignalFrameSkeleton;
using de4sdv::score_interface::ReferenceVehicleSpeedProxy;

static_assert(kFrameSampleBytes == de4sdv::score_interface::kAebsSignalFrameSampleBytes,
              "the facade and the service interface must agree on the frame sample size");

SubscriptionState ToFacade(score::mw::com::SubscriptionState state) noexcept {
  switch (state) {
    case score::mw::com::SubscriptionState::kSubscribed:
      return SubscriptionState::kSubscribed;
    case score::mw::com::SubscriptionState::kSubscriptionPending:
      return SubscriptionState::kSubscriptionPending;
    case score::mw::com::SubscriptionState::kNotSubscribed:
    default:
      return SubscriptionState::kNotSubscribed;
  }
}

template <typename ErrorType>
std::string Describe(const char* what, const ErrorType& error) {
  std::string text{what};
  text += ": ";
  text += std::string{error.Message()};
  const auto user_message = error.UserMessage();
  if (!user_message.empty()) {
    text += " (";
    text += std::string{user_message};
    text += ")";
  }
  return text;
}

}  // namespace

bool InitializeRuntime(const char* mw_com_configuration_path) noexcept {
  if (mw_com_configuration_path == nullptr) {
    return false;
  }
  std::FILE* file = std::fopen(mw_com_configuration_path, "rb");
  if (file == nullptr) {
    return false;
  }
  std::fclose(file);
  score::mw::com::runtime::InitializeRuntime(
      score::mw::com::runtime::RuntimeConfiguration{score::filesystem::Path{mw_com_configuration_path}});
  return true;
}

struct SpeedSubscriber::Impl {
  std::string instance_specifier;
  std::unique_ptr<ReferenceVehicleSpeedProxy> proxy;
  std::string last_error;
};

SpeedSubscriber::SpeedSubscriber(const char* instance_specifier) noexcept : impl_{new Impl{}} {
  impl_->instance_specifier = instance_specifier != nullptr ? instance_specifier : "";
}

SpeedSubscriber::~SpeedSubscriber() noexcept {
  if (impl_->proxy != nullptr &&
      impl_->proxy->vehicle_speed_.GetSubscriptionState() != score::mw::com::SubscriptionState::kNotSubscribed) {
    // Never destroy a subscribed proxy (GAP-MW-041): the process ends anyway.
    static_cast<void>(impl_->proxy.release());
  }
  delete impl_;
}

bool SpeedSubscriber::FindAndCreate() noexcept {
  if (impl_->proxy != nullptr) {
    return true;
  }
  auto specifier = score::mw::com::InstanceSpecifier::Create(std::string{impl_->instance_specifier});
  if (!specifier.has_value()) {
    impl_->last_error = Describe("InstanceSpecifier::Create", specifier.error());
    return false;
  }
  auto handles = ReferenceVehicleSpeedProxy::FindService(specifier.value());
  if (!handles.has_value()) {
    impl_->last_error = Describe("FindService", handles.error());
    return false;
  }
  if (handles.value().empty()) {
    impl_->last_error = "FindService: no provider of " + impl_->instance_specifier;
    return false;
  }
  auto proxy = ReferenceVehicleSpeedProxy::Create(handles.value().front());
  if (!proxy.has_value()) {
    impl_->last_error = Describe("Proxy::Create", proxy.error());
    return false;
  }
  impl_->proxy = std::make_unique<ReferenceVehicleSpeedProxy>(std::move(proxy).value());
  return true;
}

bool SpeedSubscriber::HasProxy() const noexcept { return impl_->proxy != nullptr; }

bool SpeedSubscriber::SetStateHandler(StateCallback callback, void* context) noexcept {
  if (impl_->proxy == nullptr || callback == nullptr) {
    impl_->last_error = impl_->proxy == nullptr ? "SetStateHandler: no proxy" : "SetStateHandler: no callback";
    return false;
  }
  auto result = impl_->proxy->vehicle_speed_.SetSubscriptionStateChangeHandler(
      [callback, context](score::mw::com::SubscriptionState state) -> bool {
        callback(context, ToFacade(state));
        return true;
      });
  if (!result.has_value()) {
    impl_->last_error = Describe("SetSubscriptionStateChangeHandler", result.error());
    return false;
  }
  return true;
}

void SpeedSubscriber::UnsetStateHandler() noexcept {
  if (impl_->proxy != nullptr) {
    static_cast<void>(impl_->proxy->vehicle_speed_.UnsetSubscriptionStateChangeHandler());
  }
}

bool SpeedSubscriber::SetReceiveHandler(ReceiveCallback callback, void* context) noexcept {
  if (impl_->proxy == nullptr || callback == nullptr) {
    impl_->last_error = impl_->proxy == nullptr ? "SetReceiveHandler: no proxy" : "SetReceiveHandler: no callback";
    return false;
  }
  auto result = impl_->proxy->vehicle_speed_.SetReceiveHandler([callback, context]() { callback(context); });
  if (!result.has_value()) {
    impl_->last_error = Describe("SetReceiveHandler", result.error());
    return false;
  }
  return true;
}

void SpeedSubscriber::UnsetReceiveHandler() noexcept {
  if (impl_->proxy != nullptr) {
    static_cast<void>(impl_->proxy->vehicle_speed_.UnsetReceiveHandler());
  }
}

bool SpeedSubscriber::Subscribe(std::size_t max_samples) noexcept {
  if (impl_->proxy == nullptr) {
    impl_->last_error = "Subscribe: no proxy";
    return false;
  }
  auto result = impl_->proxy->vehicle_speed_.Subscribe(max_samples);
  if (!result.has_value()) {
    impl_->last_error = Describe("Subscribe", result.error());
    return false;
  }
  return true;
}

void SpeedSubscriber::Unsubscribe() noexcept {
  if (impl_->proxy != nullptr) {
    impl_->proxy->vehicle_speed_.Unsubscribe();
  }
}

SubscriptionState SpeedSubscriber::State() const noexcept {
  if (impl_->proxy == nullptr) {
    return SubscriptionState::kNotSubscribed;
  }
  return ToFacade(impl_->proxy->vehicle_speed_.GetSubscriptionState());
}

std::int64_t SpeedSubscriber::ReadNewSamples(std::size_t max_samples, SpeedSampleCallback callback,
                                             void* context) noexcept {
  if (impl_->proxy == nullptr || callback == nullptr) {
    impl_->last_error = "ReadNewSamples: no proxy";
    return -1;
  }
  auto result = impl_->proxy->vehicle_speed_.GetNewSamples(
      [callback, context](auto sample) noexcept {
        // The value is copied out; the sample is released when it leaves scope.
        callback(context, sample->speed_kmh);
      },
      max_samples);
  if (!result.has_value()) {
    impl_->last_error = Describe("GetNewSamples", result.error());
    return -1;
  }
  return static_cast<std::int64_t>(result.value());
}

void SpeedSubscriber::DestroyProxy() noexcept { impl_->proxy.reset(); }

const char* SpeedSubscriber::LastError() const noexcept { return impl_->last_error.c_str(); }

struct FramePublisher::Impl {
  std::string instance_specifier;
  std::unique_ptr<AebsSignalFrameSkeleton> skeleton;
  bool offered{false};
  std::string last_error;
};

FramePublisher::FramePublisher(const char* instance_specifier) noexcept : impl_{new Impl{}} {
  impl_->instance_specifier = instance_specifier != nullptr ? instance_specifier : "";
}

FramePublisher::~FramePublisher() noexcept {
  StopOfferAndDestroy();
  delete impl_;
}

bool FramePublisher::Create() noexcept {
  if (impl_->skeleton != nullptr) {
    return true;
  }
  auto specifier = score::mw::com::InstanceSpecifier::Create(std::string{impl_->instance_specifier});
  if (!specifier.has_value()) {
    impl_->last_error = Describe("InstanceSpecifier::Create", specifier.error());
    return false;
  }
  auto skeleton = AebsSignalFrameSkeleton::Create(specifier.value());
  if (!skeleton.has_value()) {
    impl_->last_error = Describe("Skeleton::Create", skeleton.error());
    return false;
  }
  impl_->skeleton = std::make_unique<AebsSignalFrameSkeleton>(std::move(skeleton).value());
  return true;
}

bool FramePublisher::Offer() noexcept {
  if (impl_->skeleton == nullptr) {
    impl_->last_error = "OfferService: no skeleton";
    return false;
  }
  auto result = impl_->skeleton->OfferService();
  if (!result.has_value()) {
    impl_->last_error = Describe("OfferService", result.error());
    return false;
  }
  impl_->offered = true;
  return true;
}

SendResult FramePublisher::Send(const std::uint8_t* sample, std::size_t sample_size) noexcept {
  if (impl_->skeleton == nullptr || !impl_->offered) {
    return SendResult::kNotOffered;
  }
  if (sample == nullptr || sample_size > kFrameSampleBytes) {
    return SendResult::kTooLarge;
  }
  auto allocated = impl_->skeleton->aebs_signal_frame_.Allocate();
  if (!allocated.has_value()) {
    impl_->last_error = Describe("Allocate", allocated.error());
    return SendResult::kAllocateFailed;
  }
  auto slot = std::move(allocated).value();
  slot->size = sample_size;
  std::memcpy(slot->data, sample, sample_size);
  auto sent = impl_->skeleton->aebs_signal_frame_.Send(std::move(slot));
  if (!sent.has_value()) {
    impl_->last_error = Describe("Send", sent.error());
    return SendResult::kSendFailed;
  }
  return SendResult::kSent;
}

void FramePublisher::StopOfferAndDestroy() noexcept {
  if (impl_->skeleton != nullptr) {
    if (impl_->offered) {
      impl_->skeleton->StopOfferService();
      impl_->offered = false;
    }
    impl_->skeleton.reset();
  }
}

const char* FramePublisher::LastError() const noexcept { return impl_->last_error.c_str(); }

}  // namespace de4sdv::score_facade
