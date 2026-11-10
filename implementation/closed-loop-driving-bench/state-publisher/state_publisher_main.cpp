// DE4SDV INC-DRIVING-001 slice 10b, S1: the operational-state publisher as one
// S-CORE mw::com application. Interface Control Document: ../../interfaces/ICD.md
// (sections 1, 2, 3, 6). The model's part is
// closedLoopDrivingPhysicalSystem.linuxHost.drivingSoftware.statePublisherApplication
// (MAP-DRIVING-OPERATIONAL-STATE, MAP-DRIVING-MODE, MAP-DRIVING-ACTUATION-STATE).
//
// This file is the thin shell: it moves samples between mw::com and the logic
// library (publisher_core.h), stamps receipt times, sends the frames the
// library built and writes the JSONL log. Every decision - what to publish,
// when, with which sequence, and what the health says - lives in the library,
// which is unit-tested without S-CORE (tests/run_tests.sh).
//
// Consumes (proxies, one event each, event name = last segment of the
// instance specifier, max sample count 8, never blocks a producer):
//   de4sdv/driving/plan                 DrivingPlanPayload      <- agent/inferPlan
//   de4sdv/driving/ego_motion_sample    EgoMotionSamplePayload  <- agent/conditionInputs
//   de4sdv/driving/mode                 DrivingModePayload      <- agent/superviseLoop
//   de4sdv/driving/actuation_state      ActuationStatePayload   <- actuationAdapter
// Offers (skeleton, three PreSerializedData<2048> events for gatewayd):
//   de4sdv/driving/operational_state    plan, vehicle_state, health
// Each sample carries the ICD v2 section 3 SOME/IP struct (43 fields, big-endian)
// alone, from data[0], with size = its length (ICD section 2, A31); gatewayd and
// someipd offer it as service 0x4DF0, events 0x8001-0x8003, and the SDV Core
// broker translates it (REFLECTION) into the typed DrivingOperationalState. No
// protobuf anywhere.
//
// Usage:
//   state_publisher --run-dir <dir> [--host-name score] [--mw-com-config <json>]
//
// The mw::com calls are checked against the declared API of S-CORE
// Communication v0.6.0 (c5efd74f): ProxyBase::StartFindService returns
// Result<FindServiceHandle> and takes FindServiceHandler<HandleType>
// (impl/proxy_base.h:105, impl/find_service_handler.h); HandleType and
// FindServiceHandle have no default constructor (impl/handle_type.h:52,
// impl/find_service_handle.h:44); Subscribe and GetNewSamples are members of
// the proxy EVENT, not of the proxy (impl/proxy_event_base.h:82,
// impl/proxy_event.h:125); the receiver gets SamplePtr<T> by rvalue
// (impl/tracing/proxy_event_tracing.h:82). A syntax-only compile against those
// headers passes; the first Bazel build on the build VM is still the real test.
//
// The sample layout is gatewayd's (inc_someip_gateway d9eac670,
// score/serializer/pre_serialized_data.h): `std::size_t size` first, then
// `alignas(std::max_align_t) std::byte data[N]`. gatewayd's null serializer
// copies data[0..size) onto the wire unread (null_serializer.cpp:65-70) and
// someipd removes only gatewayd's own 16-byte header
// (someipd/impl/local_network_service.cpp:124-135). So whatever sits in
// data[0..size) IS the SOME/IP payload: this shell writes the ICD section 3
// struct from data[0] with size = the struct's length, and drops the library
// frame's 4-byte little-endian length prefix (bytes 0-3 of Frame::bytes).

#include <atomic>
#include <chrono>
#include <csignal>
#include <cstddef>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
#include <memory>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <type_traits>
#include <utility>
#include <vector>

#include "score/mw/com/runtime.h"
#include "score/mw/com/types.h"
#include "score/serializer/pre_serialized_data.h"

#include "de4sdv/driving/payloads.h"
#include "de4sdv/driving/run_log.h"

#include "publisher_core.h"

namespace {

using de4sdv::driving::ActuationStatePayload;
using de4sdv::driving::DrivingModePayload;
using de4sdv::driving::DrivingPlanPayload;
using de4sdv::driving::EgoMotionSamplePayload;

std::atomic<bool> g_stop{false};

void OnSignal(int /*signal*/) { g_stop.store(true, std::memory_order_relaxed); }

std::int64_t NowNs(clockid_t clock) {
  timespec ts{};
  clock_gettime(clock, &ts);
  return static_cast<std::int64_t>(ts.tv_sec) * 1000000000LL + ts.tv_nsec;
}

double RealSeconds() { return static_cast<double>(NowNs(CLOCK_REALTIME)) / 1e9; }

// ICD section 2: the proxies subscribe with a max sample count of 8.
constexpr std::size_t kMaxSampleCount = 8;
// The loop polls at 2 ms, well inside the 100 ms budget of REQ-DRIVING-015,
// -016 and -029 and the 100 ms health period. The poll never blocks: a full
// slot is a dropped sample, which mw::com counts on its side.
constexpr auto kPollInterval = std::chrono::milliseconds{2};

using Sample = score::someip_gateway::serializer::PreSerializedData<2048>;

// The layout gatewayd's null serializer reads through PreSerializedData<0>:
// `size` at offset 0, the bytes at alignof(std::max_align_t). A different
// header (the old local mock put `data` first) would make gatewayd read the
// payload's first eight bytes as the size.
static_assert(std::is_standard_layout_v<Sample>, "PreSerializedData must be standard-layout");
static_assert(offsetof(Sample, size) == 0, "gatewayd reads PreSerializedData::size at offset 0");
static_assert(offsetof(Sample, data) == alignof(std::max_align_t),
              "gatewayd reads PreSerializedData::data at alignof(max_align_t)");
static_assert(sizeof(Sample::data) == de4sdv::driving::publisher::kFrameBytes,
              "the frame capacity must equal the gateway's max_message_size");

// ------------------------------------------------------------ service traits
// One event per service interface, named by the last segment of the instance
// specifier (ICD section 2).
template <typename Trait>
struct PlanService : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<DrivingPlanPayload> plan{*this, "plan"};
};
using PlanProxy = score::mw::com::AsProxy<PlanService>;

template <typename Trait>
struct EgoMotionSampleService : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<EgoMotionSamplePayload> ego_motion_sample{*this, "ego_motion_sample"};
};
using EgoMotionSampleProxy = score::mw::com::AsProxy<EgoMotionSampleService>;

template <typename Trait>
struct ModeService : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<DrivingModePayload> mode{*this, "mode"};
};
using ModeProxy = score::mw::com::AsProxy<ModeService>;

template <typename Trait>
struct ActuationStateService : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<ActuationStatePayload> actuation_state{*this, "actuation_state"};
};
using ActuationStateProxy = score::mw::com::AsProxy<ActuationStateService>;

template <typename Trait>
struct OperationalStateService : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<Sample> plan{*this, "plan"};
  typename Trait::template Event<Sample> vehicle_state{*this, "vehicle_state"};
  typename Trait::template Event<Sample> health{*this, "health"};
};
using OperationalStateSkeleton = score::mw::com::AsSkeleton<OperationalStateService>;

// The one event of each consumed service. Subscribe/GetNewSamples are members
// of the proxy event (ProxyEventBase / ProxyEvent), so the consumer reaches
// the event through these overloads; a member pointer such as &Proxy::plan
// would name the interface base and fail deduction.
auto& EventOf(PlanProxy& proxy) { return proxy.plan; }
auto& EventOf(EgoMotionSampleProxy& proxy) { return proxy.ego_motion_sample; }
auto& EventOf(ModeProxy& proxy) { return proxy.mode; }
auto& EventOf(ActuationStateProxy& proxy) { return proxy.actuation_state; }

// ------------------------------------------------------------------ consumer
// One proxy of one service. The find-service callback runs on an mw::com
// thread and only records the handle; the proxy is created and subscribed by
// the main loop, so all proxy calls happen on one thread.
template <typename ProxyT>
class Consumer {
 public:
  using HandleType = typename ProxyT::HandleType;

  explicit Consumer(std::string port) : port_(std::move(port)) {}
  Consumer(const Consumer&) = delete;
  Consumer& operator=(const Consumer&) = delete;
  // The find-service handler holds `this`: stop it before the object goes.
  ~Consumer() { StopFindService(); }

  bool StartFindService(const char* specifierText, de4sdv::driving::RunLog& log) {
    auto specifier = score::mw::com::InstanceSpecifier::Create(std::string{specifierText});
    if (!specifier.has_value()) {
      log.Write("error", 0,
                std::string{"{\"port\":"} + de4sdv::driving::JsonString(port_) +
                    ",\"error\":\"instance_specifier_create_failed\",\"specifier\":" +
                    de4sdv::driving::JsonString(specifierText) + "}");
      return false;
    }
    // FindServiceHandler<HandleType> = score::cpp::callback<void(
    //   ServiceHandleContainer<HandleType>, FindServiceHandle)> (32-byte capacity);
    // it is called on every availability change, with an empty container when
    // the service goes away.
    auto started = ProxyT::StartFindService(
        [this](score::mw::com::ServiceHandleContainer<HandleType> handles,
               score::mw::com::FindServiceHandle /*findHandle*/) {
          std::lock_guard<std::mutex> lock(mutex_);
          if (found_ || handles.empty()) return;
          handle_.emplace(handles.front());
          found_ = true;
        },
        specifier.value());
    if (!started.has_value()) {
      log.Write("error", 0,
                std::string{"{\"port\":"} + de4sdv::driving::JsonString(port_) +
                    ",\"error\":\"start_find_service_failed\",\"message\":" +
                    de4sdv::driving::JsonString(std::string{started.error().Message()}) + "}");
      return false;
    }
    findHandle_.emplace(started.value());
    return true;
  }

  void StopFindService() {
    if (findHandle_.has_value()) {
      static_cast<void>(ProxyT::StopFindService(findHandle_.value()));
      findHandle_.reset();
    }
  }

  // Main thread: creates the proxy once the service is found.
  bool TrySubscribe(de4sdv::driving::RunLog& log) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (proxy_) return true;
    if (!found_ || !handle_.has_value()) return false;
    auto created = ProxyT::Create(handle_.value());
    if (!created.has_value()) {
      log.Write("error", 0,
                std::string{"{\"port\":"} + de4sdv::driving::JsonString(port_) +
                    ",\"error\":\"proxy_create_failed\",\"message\":" +
                    de4sdv::driving::JsonString(std::string{created.error().Message()}) + "}");
      // Retry from discovery: the found instance may have gone.
      found_ = false;
      handle_.reset();
      return false;
    }
    proxy_ = std::make_unique<ProxyT>(std::move(created).value());
    const auto subscribed = EventOf(*proxy_).Subscribe(kMaxSampleCount);
    if (!subscribed.has_value()) {
      log.Write("error", 0,
                std::string{"{\"port\":"} + de4sdv::driving::JsonString(port_) +
                    ",\"error\":\"subscribe_failed\",\"message\":" +
                    de4sdv::driving::JsonString(std::string{subscribed.error().Message()}) + "}");
      proxy_.reset();
      return false;
    }
    log.Write("config", 0,
              std::string{"{\"port\":"} + de4sdv::driving::JsonString(port_) +
                  ",\"subscribed\":true,\"max_sample_count\":" + std::to_string(kMaxSampleCount) +
                  "}");
    return true;
  }

  bool Ready() const {
    std::lock_guard<std::mutex> lock(mutex_);
    return proxy_ != nullptr;
  }

  // Non-blocking drain of up to kMaxSampleCount samples; `fn` gets the payload.
  // GetNewSamples hands each sample over as an rvalue SamplePtr<T>; the sample
  // slot is released when the SamplePtr goes out of scope at the end of the
  // lambda. A failing call is logged once until a call succeeds again.
  template <typename Fn>
  void Poll(Fn&& fn, de4sdv::driving::RunLog& log) {
    std::lock_guard<std::mutex> lock(mutex_);
    if (!proxy_) return;
    const auto result =
        EventOf(*proxy_).GetNewSamples([&fn](auto sample) { fn(*sample); }, kMaxSampleCount);
    if (!result.has_value()) {
      if (!pollFailing_) {
        log.Write("error", 0, std::string{"{\"port\":"} + de4sdv::driving::JsonString(port_) +
                                  ",\"error\":\"get_new_samples_failed\",\"message\":" +
                                  de4sdv::driving::JsonString(std::string{result.error().Message()}) +
                                  "}");
      }
      pollFailing_ = true;
    } else {
      pollFailing_ = false;
    }
  }

 private:
  std::string port_;
  mutable std::mutex mutex_;
  std::optional<score::mw::com::FindServiceHandle> findHandle_;
  std::optional<HandleType> handle_;
  bool found_ = false;
  bool pollFailing_ = false;
  std::unique_ptr<ProxyT> proxy_;
};

struct Options {
  std::string runDir;
  std::string hostName = "score";
  std::string mwComConfig;
};

void Usage(const char* program) {
  std::fprintf(stderr,
               "usage: %s --run-dir <dir> [--host-name <name>] [--mw-com-config <json>]\n"
               "  --run-dir       run directory of the bench; the log goes to\n"
               "                  <run-dir>/<host-name>/statePublisher.jsonl (ICD section 6)\n"
               "  --host-name     host segment of the log path, default \"score\"\n"
               "  --mw-com-config mw::com configuration JSON; the process default when absent\n",
               program);
}

}  // namespace

int main(int argc, char* argv[]) {
  Options options;
  for (int i = 1; i < argc; ++i) {
    const std::string arg = argv[i];
    if (arg == "--run-dir" && i + 1 < argc) {
      options.runDir = argv[++i];
    } else if (arg == "--host-name" && i + 1 < argc) {
      options.hostName = argv[++i];
    } else if (arg == "--mw-com-config" && i + 1 < argc) {
      options.mwComConfig = argv[++i];
    } else {
      Usage(argv[0]);
      return 1;
    }
  }
  if (options.runDir.empty()) {
    Usage(argv[0]);
    return 1;
  }

  std::signal(SIGTERM, OnSignal);
  std::signal(SIGINT, OnSignal);

  const std::string logPath =
      options.runDir + "/" + options.hostName + "/statePublisher.jsonl";
  de4sdv::driving::RunLog log(logPath, options.hostName, "statePublisher");
  if (!log.ok()) {
    std::fprintf(stderr, "state_publisher: cannot open %s\n", logPath.c_str());
    return 2;
  }
  log.Write("start", 0,
            std::string{"{\"run_dir\":"} + de4sdv::driving::JsonString(options.runDir) +
                ",\"host\":" + de4sdv::driving::JsonString(options.hostName) +
                ",\"interface_version\":" + std::to_string(de4sdv::driving::kInterfaceVersion) +
                ",\"contract\":\"de4sdv.driving.icd.v2\"" +
                ",\"encoding\":\"someip_struct_43_fields_big_endian\"" +
                ",\"schema_major\":" +
                std::to_string(de4sdv::driving::publisher::kSchemaMajor) +
                ",\"mw_com_config\":" + de4sdv::driving::JsonString(options.mwComConfig) +
                ",\"health_period_s\":" +
                std::to_string(de4sdv::driving::publisher::kHealthPeriodSeconds) + "}");

  // ---- mw::com runtime, skeleton and offer -------------------------------
  if (options.mwComConfig.empty()) {
    score::mw::com::runtime::InitializeRuntime(
        score::mw::com::runtime::RuntimeConfiguration{});
  } else {
    score::mw::com::runtime::InitializeRuntime(
        score::mw::com::runtime::RuntimeConfiguration{options.mwComConfig});
  }

  auto specifier =
      score::mw::com::InstanceSpecifier::Create(std::string{"de4sdv/driving/operational_state"});
  if (!specifier.has_value()) {
    log.Write("error", 0, "{\"error\":\"instance_specifier_create_failed\"}");
    return 3;
  }
  auto created = OperationalStateSkeleton::Create(specifier.value());
  if (!created.has_value()) {
    log.Write("error", 0,
              std::string{"{\"error\":\"skeleton_create_failed\",\"message\":"} +
                  de4sdv::driving::JsonString(std::string{created.error().Message()}) + "}");
    return 4;
  }
  auto skeleton = std::move(created).value();
  const auto offered = skeleton.OfferService();
  if (!offered.has_value()) {
    log.Write("error", 0,
              std::string{"{\"error\":\"offer_failed\",\"message\":"} +
                  de4sdv::driving::JsonString(std::string{offered.error().Message()}) + "}");
    return 5;
  }

  de4sdv::driving::publisher::PublisherCore core;
  // Clock pairing: the message carries CLOCK_REALTIME and CLOCK_MONOTONIC of
  // this host (ICD section 1); the logic library reads no clock.
  core.SetRealTimeAtMono(de4sdv::driving::MonotonicSeconds(), RealSeconds());
  // The mw::com service ids and the SOME/IP identity gatewayd publishes
  // (ICD v2 section 2 and section 3).
  log.Write("ready", 0,
            std::string{"{\"service\":\"de4sdv/driving/operational_state\",\"events\":[\"plan\","
                        "\"vehicle_state\",\"health\"],\"queue_policy\":\"non_blocking\","
                        "\"frame_capacity_bytes\":"} +
                std::to_string(de4sdv::driving::publisher::kFrameBytes) +
                ",\"mw_com_service_ids\":{\"plan\":7402,\"ego_motion_sample\":7401,"
                "\"mode\":7403,\"command\":7404,\"actuation_state\":7405,"
                "\"operational_state\":7406}"
                ",\"someip\":{\"service_id\":\"0x4DF0\",\"instance_id\":\"0x0001\","
                "\"eventgroup\":\"0x0001\",\"events\":{\"plan\":\"0x8001\","
                "\"vehicle_state\":\"0x8002\",\"health\":\"0x8003\"},"
                "\"transport\":\"tcp\",\"port\":30510}"
                ",\"sample_layout\":\"size_then_data;someip_payload=data[0..size)=icd_v2_s3_struct\"}");

  // ---- proxies -----------------------------------------------------------
  Consumer<PlanProxy> plans{"plan"};
  Consumer<EgoMotionSampleProxy> samples{"ego_motion_sample"};
  Consumer<ModeProxy> modes{"mode"};
  Consumer<ActuationStateProxy> actuations{"actuation_state"};
  // Each find service starts regardless of the others' outcome: a missing
  // producer is a waiting proxy, not a startup failure.
  const bool planFind = plans.StartFindService("de4sdv/driving/plan", log);
  const bool sampleFind = samples.StartFindService("de4sdv/driving/ego_motion_sample", log);
  const bool modeFind = modes.StartFindService("de4sdv/driving/mode", log);
  const bool actuationFind = actuations.StartFindService("de4sdv/driving/actuation_state", log);
  const bool consumersStarted = planFind && sampleFind && modeFind && actuationFind;
  if (!consumersStarted) {
    log.Write("error", 0, "{\"error\":\"find_service_start_failed\"}");
    skeleton.StopOfferService();
    return 6;
  }

  // ---- the loop ----------------------------------------------------------
  // Sends every frame the library produced and logs the outbound crossing
  // after the send, plus the library's non-frame records (stop_response.*,
  // drop).
  auto sendFrames = [&](std::vector<de4sdv::driving::publisher::Frame> frames) {
    using de4sdv::driving::publisher::Kind;
    // The library's records first: stop_response.begin explains the health
    // that follows.
    for (const auto& record : core.DrainLog()) {
      log.Write(record.event, record.seq, record.dataJson);
    }
    for (const auto& frame : frames) {
      auto& event = frame.kind == Kind::kPlan       ? skeleton.plan
                    : frame.kind == Kind::kVehicleState ? skeleton.vehicle_state
                                                        : skeleton.health;
      auto allocated = event.Allocate();
      if (!allocated.has_value()) {
        core.NoteDownstreamDrop("allocate_failed");
        continue;
      }
      auto slot = std::move(allocated).value();
      // The SOME/IP payload is data[0..size): the ICD section 3 struct alone,
      // without the library frame's 4-byte little-endian length prefix
      // (Frame::bytes[0..3]); `size` carries the length instead.
      std::memcpy(reinterpret_cast<std::uint8_t*>(slot->data), frame.bytes + 4, frame.messageBytes);
      slot->size = frame.messageBytes;
      const auto sent = event.Send(std::move(slot));
      if (!sent.has_value()) {
        core.NoteDownstreamDrop("send_failed");
        continue;
      }
      log.Write("out.operational_state", frame.sequence, frame.logDataJson);
    }
    for (const auto& record : core.DrainLog()) {
      log.Write(record.event, record.seq, record.dataJson);
    }
  };

  while (!g_stop.load(std::memory_order_relaxed)) {
    plans.TrySubscribe(log);
    samples.TrySubscribe(log);
    modes.TrySubscribe(log);
    actuations.TrySubscribe(log);

    // The receipt stamp is taken inside the callback, as close to the arrival
    // as this process can see it (ICD section 3: within 100 ms of receipt).
    // One receipt stamp per sample: the log record and the message both carry
    // it, so an evaluator never sees two different receipts for one crossing.
    plans.Poll(
        [&](const DrivingPlanPayload& payload) {
          const double receipt = de4sdv::driving::MonotonicSeconds();
          log.Write("in.plan", 0, de4sdv::driving::publisher::logjson::Plan(payload, receipt));
          sendFrames(core.OnPlan(payload, receipt));
        },
        log);
    modes.Poll(
        [&](const DrivingModePayload& payload) {
          const double receipt = de4sdv::driving::MonotonicSeconds();
          log.Write("in.mode", 0, de4sdv::driving::publisher::logjson::ModeEvent(payload, receipt));
          sendFrames(core.OnMode(payload, receipt));
        },
        log);
    samples.Poll(
        [&](const EgoMotionSamplePayload& payload) {
          const double receipt = de4sdv::driving::MonotonicSeconds();
          log.Write("in.ego_motion_sample", 0,
                    de4sdv::driving::publisher::logjson::EgoMotionSample(payload, receipt));
          sendFrames(core.OnEgoMotionSample(payload, receipt));
        },
        log);
    actuations.Poll(
        [&](const ActuationStatePayload& payload) {
          const double receipt = de4sdv::driving::MonotonicSeconds();
          log.Write("in.actuation_state", 0,
                    de4sdv::driving::publisher::logjson::ActuationState(payload, receipt));
          sendFrames(core.OnActuationState(payload, receipt));
        },
        log);

    // The health period, whether or not any input arrived (REQ-DRIVING-017).
    sendFrames(core.Tick(de4sdv::driving::MonotonicSeconds()));

    std::this_thread::sleep_for(kPollInterval);
  }

  log.Write("stop", 0,
            std::string{"{\"dropped_samples\":"} + std::to_string(core.DroppedSamples()) +
                ",\"stop_latched\":" + (core.StopLatched() ? "true" : "false") +
                ",\"mode\":" +
                de4sdv::driving::JsonString(de4sdv::driving::publisher::ModeName(core.ReportedMode())) +
                ",\"cause\":" +
                de4sdv::driving::JsonString(de4sdv::driving::publisher::CauseName(core.ReportedCause())) +
                ",\"sequences\":{\"plan\":" +
                std::to_string(core.Sequence(de4sdv::driving::publisher::Kind::kPlan)) +
                ",\"vehicle_state\":" +
                std::to_string(core.Sequence(de4sdv::driving::publisher::Kind::kVehicleState)) +
                ",\"health\":" +
                std::to_string(core.Sequence(de4sdv::driving::publisher::Kind::kHealth)) + "}}");

  plans.StopFindService();
  samples.StopFindService();
  modes.StopFindService();
  actuations.StopFindService();
  skeleton.StopOfferService();
  std::printf("state_publisher: stopped, dropped=%llu plan_seq=%llu vehicle_seq=%llu health_seq=%llu\n",
              static_cast<unsigned long long>(core.DroppedSamples()),
              static_cast<unsigned long long>(
                  core.Sequence(de4sdv::driving::publisher::Kind::kPlan)),
              static_cast<unsigned long long>(
                  core.Sequence(de4sdv::driving::publisher::Kind::kVehicleState)),
              static_cast<unsigned long long>(
                  core.Sequence(de4sdv::driving::publisher::Kind::kHealth)));
  return 0;
}
