// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// The LoLa/mw::com bindings behind seams.hpp (MakeLolaPorts). NOT COMPILED on the DE4SDV host: it needs the S-CORE
// Communication headers and library, which only the S-CORE Bazel build (brief item B2) provides. The calls follow the
// API that the readiness probe of 2026-11-15 compiled (Communication 0.6.0) and the closed-loop driving bench's state
// publisher.
//
// Events (interfaces/ICD.md; ids and the instance specifiers are bench proposals, the service ids live in the mw::com
// configuration):
//   de4sdv/driver_assistance/driving_command   skeleton, event "driving_command", DrivingCommandEventPayload
//   de4sdv/driver_assistance/warning_request   skeleton, event "warning_request", the 8 SOME/IP bytes in a
//                                              PreSerializedData sample for gatewayd (size = 8, data[0..8))
//   de4sdv/driver_assistance/candidate_record  proxy, event "candidate_record", CandidateRecordEventPayload
#include <cstring>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <type_traits>
#include <utility>

#include "de4sdv/driver_assistance/payloads.h"
#include "de4sdv/score_interface/seams.hpp"
#include "score/mw/com/runtime.h"
#include "score/mw/com/types.h"
#include "score/serializer/pre_serialized_data.h"

namespace de4sdv::score_interface {

namespace da = driver_assistance;

namespace {

// OPEN: the capacity of the warning-request sample. ICD.md fixes the 8 bytes, not the container; gatewayd's null
// serializer reads a PreSerializedData sample, whose capacity must equal the gateway's max_message_size in the
// gateway configuration (brief item B6). 2048 is the closed-loop driving bench's value.
constexpr std::size_t kWarningRequestSampleCapacity = 2048;
using WarningRequestSample = score::someip_gateway::serializer::PreSerializedData<kWarningRequestSampleCapacity>;
static_assert(std::is_standard_layout_v<WarningRequestSample>);
static_assert(da::kWarningRequestSomeipSize <= kWarningRequestSampleCapacity);

// OPEN: the subscriber's max sample count (ICD.md gives none). The record is re-published every 1 s; one sample is
// enough. The mw::com configuration's slots must allow it.
constexpr std::size_t kRecordMaxSampleCount = 1;

constexpr const char* kCommandSpecifier = "de4sdv/driver_assistance/driving_command";
constexpr const char* kWarningSpecifier = "de4sdv/driver_assistance/warning_request";
constexpr const char* kRecordSpecifier = "de4sdv/driver_assistance/candidate_record";

template <typename Trait>
struct DrivingCommandService : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<da::DrivingCommandEventPayload> driving_command{*this, "driving_command"};
};
using DrivingCommandSkeleton = score::mw::com::AsSkeleton<DrivingCommandService>;

template <typename Trait>
struct WarningRequestService : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<WarningRequestSample> warning_request{*this, "warning_request"};
};
using WarningRequestSkeleton = score::mw::com::AsSkeleton<WarningRequestService>;

template <typename Trait>
struct CandidateRecordService : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<da::CandidateRecordEventPayload> candidate_record{*this, "candidate_record"};
};
using CandidateRecordProxy = score::mw::com::AsProxy<CandidateRecordService>;

class LolaCommandSink : public DrivingCommandSink {
 public:
  explicit LolaCommandSink(DrivingCommandSkeleton skeleton) : skeleton_(std::move(skeleton)) {}
  ~LolaCommandSink() override { skeleton_.StopOfferService(); }
  bool Send(const da::DrivingCommandEventPayload& payload) override {
    auto slot = skeleton_.driving_command.Allocate();
    if (!slot.has_value()) return false;
    auto sample = std::move(slot).value();
    *sample = payload;
    return skeleton_.driving_command.Send(std::move(sample)).has_value();
  }

 private:
  DrivingCommandSkeleton skeleton_;
};

class LolaWarningSink : public WarningRequestSink {
 public:
  explicit LolaWarningSink(WarningRequestSkeleton skeleton) : skeleton_(std::move(skeleton)) {}
  ~LolaWarningSink() override { skeleton_.StopOfferService(); }
  bool Send(const std::uint8_t* bytes, std::size_t size) override {
    if (size > kWarningRequestSampleCapacity) return false;
    auto slot = skeleton_.warning_request.Allocate();
    if (!slot.has_value()) return false;
    auto sample = std::move(slot).value();
    sample->size = size;  // gatewayd copies data[0..size) onto the SOME/IP payload, no prefix
    std::memcpy(sample->data, bytes, size);
    return skeleton_.warning_request.Send(std::move(sample)).has_value();
  }

 private:
  WarningRequestSkeleton skeleton_;
};

// Finds the record service asynchronously; the loop thread creates the proxy and subscribes in TakeNewest(), as the
// closed-loop bench's state publisher does, so every proxy call happens on one thread.
class LolaRecordSource : public CandidateRecordSource {
 public:
  using HandleType = CandidateRecordProxy::HandleType;
  ~LolaRecordSource() override {
    if (find_handle_.has_value()) static_cast<void>(CandidateRecordProxy::StopFindService(find_handle_.value()));
  }
  bool StartFind(std::string* error) {
    auto specifier = score::mw::com::InstanceSpecifier::Create(std::string{kRecordSpecifier});
    if (!specifier.has_value()) {
      *error = std::string("instance specifier ") + kRecordSpecifier;
      return false;
    }
    auto started = CandidateRecordProxy::StartFindService(
        [this](score::mw::com::ServiceHandleContainer<HandleType> handles, score::mw::com::FindServiceHandle) {
          std::lock_guard<std::mutex> lock(mutex_);
          if (handle_.has_value() || handles.empty()) return;
          handle_.emplace(handles.front());
        },
        specifier.value());
    if (!started.has_value()) {
      *error = "StartFindService " + std::string(kRecordSpecifier);
      return false;
    }
    find_handle_.emplace(started.value());
    return true;
  }
  bool TakeNewest(da::CandidateRecordEventPayload* out) override {
    if (!proxy_) {
      std::optional<HandleType> handle;
      {
        std::lock_guard<std::mutex> lock(mutex_);
        handle = handle_;
      }
      if (!handle.has_value()) return false;
      auto created = CandidateRecordProxy::Create(handle.value());
      if (!created.has_value()) return false;
      proxy_ = std::make_unique<CandidateRecordProxy>(std::move(created).value());
      if (!proxy_->candidate_record.Subscribe(kRecordMaxSampleCount).has_value()) {
        proxy_.reset();
        return false;
      }
    }
    bool got = false;
    static_cast<void>(proxy_->candidate_record.GetNewSamples(
        [&](score::mw::com::SamplePtr<da::CandidateRecordEventPayload> sample) {
          *out = *sample;
          got = true;
        },
        kRecordMaxSampleCount));
    return got;
  }

 private:
  std::mutex mutex_;
  std::optional<HandleType> handle_;
  std::optional<score::mw::com::FindServiceHandle> find_handle_;
  std::unique_ptr<CandidateRecordProxy> proxy_;
};

template <typename Skeleton>
std::optional<Skeleton> Offer(const char* specifier_text, std::string* error) {
  auto specifier = score::mw::com::InstanceSpecifier::Create(std::string{specifier_text});
  if (!specifier.has_value()) {
    *error = std::string("instance specifier ") + specifier_text;
    return std::nullopt;
  }
  auto created = Skeleton::Create(specifier.value());
  if (!created.has_value()) {
    *error = std::string("skeleton ") + specifier_text;
    return std::nullopt;
  }
  Skeleton skeleton = std::move(created).value();
  if (!skeleton.OfferService().has_value()) {
    *error = std::string("OfferService ") + specifier_text;
    return std::nullopt;
  }
  return std::optional<Skeleton>(std::move(skeleton));
}

}  // namespace

MwComPorts MakeLolaPorts(const std::string& mw_com_config_path, std::string* error) {
  score::mw::com::runtime::InitializeRuntime(score::mw::com::runtime::RuntimeConfiguration{mw_com_config_path});
  MwComPorts ports;
  auto command = Offer<DrivingCommandSkeleton>(kCommandSpecifier, error);
  if (!command) return ports;
  auto warning = Offer<WarningRequestSkeleton>(kWarningSpecifier, error);
  if (!warning) return ports;
  auto record = std::make_unique<LolaRecordSource>();
  if (!record->StartFind(error)) return ports;
  ports.command = std::make_unique<LolaCommandSink>(std::move(*command));
  ports.warning = std::make_unique<LolaWarningSink>(std::move(*warning));
  ports.record = std::move(record);
  return ports;
}

}  // namespace de4sdv::score_interface
