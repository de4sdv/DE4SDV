// DE4SDV driver-assistance bench (INC-DRIVING-002): the test publisher of the warning request for P10-3, an
// S-CORE application in the place of the candidate's warning request publisher (MAP-DRIVING-DA-WARNING-REQUEST).
//
//   out  mw::com skeleton  de4sdv/driver_assistance/warning_request, event "warning_request" (ICD.md: service
//                          7412): the 8 SOME/IP bytes of payloads.h in a PreSerializedData<2048> sample, size = 8,
//                          nothing in front, as score-interface's lola_bindings.cpp sends them
//
// Its manifest (mw_com_config_warning_injector.json) has the candidate's warning-request instance as it is (QM, 20
// slots, one subscriber) and the candidate's global ASIL B, so gatewayd (QM) receives from an ASIL B process as it
// will from the candidate. It runs only while the candidate does not (the path-only Launch Manager configuration):
// both offer the same instance. The rules are the shell's (injector_shell.h); this file wires mw::com and the clocks.
// It builds against S-CORE Communication v0.6.0 in the B2 workspace; the host's tests check it for syntax only.
//
// Usage: warning_injector --sequence <file> --log <jsonl> [--lead-in-s 5] [--tail-s 2] [--host-name score]
// MW_COM_CONFIG names the manifest. Exit status: 0 every send went out; 1 usage; 2 MW_COM_CONFIG unset or the log
// not writable; 3 a bad sequence; 4 the offer failed; 5 a send failed; 6 stopped by a signal.
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <optional>
#include <string>
#include <thread>
#include <type_traits>
#include <utility>

#include "de4sdv/driver_assistance/payloads.h"
#include "injection_plan.h"
#include "injector_shell.h"
#include "run_log.h"
#include "score/mw/com/runtime.h"
#include "score/mw/com/types.h"
#include "score/serializer/pre_serialized_data.h"

namespace inj = de4sdv::driver_assistance::injector;
using de4sdv::driver_assistance::NowNs;
using de4sdv::driver_assistance::RunLog;

namespace {

// The capacity of gatewayd's null serializer (score-path/config: max_message_size 2048), as the candidate's.
constexpr std::size_t kWarningRequestSampleCapacity = 2048;
using WarningRequestSample = score::someip_gateway::serializer::PreSerializedData<kWarningRequestSampleCapacity>;
static_assert(std::is_standard_layout_v<WarningRequestSample>);

constexpr const char* kWarningSpecifier = "de4sdv/driver_assistance/warning_request";

template <typename Trait>
struct WarningRequestService : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<WarningRequestSample> warning_request{*this, "warning_request"};
};
using WarningRequestSkeleton = score::mw::com::AsSkeleton<WarningRequestService>;

class LolaWarningSink final : public inj::WarningSink {
 public:
  bool Offer(std::string* error) override {
    auto specifier = score::mw::com::InstanceSpecifier::Create(std::string(kWarningSpecifier));
    if (!specifier.has_value()) {
      *error = "bad instance specifier";
      return false;
    }
    auto created = WarningRequestSkeleton::Create(specifier.value());
    if (!created.has_value()) {
      *error = "skeleton create failed";
      return false;
    }
    skeleton_.emplace(std::move(created).value());
    if (!skeleton_->OfferService().has_value()) {
      skeleton_.reset();
      *error = "OfferService failed (is the candidate running? it offers the same instance)";
      return false;
    }
    return true;
  }
  bool Send(const std::uint8_t* bytes, std::size_t size) override {
    if (!skeleton_ || size > kWarningRequestSampleCapacity) return false;
    auto slot = skeleton_->warning_request.Allocate();
    if (!slot.has_value()) return false;
    auto sample = std::move(slot).value();
    sample->size = size;  // gatewayd copies data[0..size) onto the SOME/IP payload
    std::memcpy(sample->data, bytes, size);
    return skeleton_->warning_request.Send(std::move(sample)).has_value();
  }
  void StopOffer() override {
    if (skeleton_) skeleton_->StopOfferService();
    skeleton_.reset();
  }

 private:
  std::optional<WarningRequestSkeleton> skeleton_;
};

std::atomic<bool> g_stop{false};
void OnSignal(int /*signal*/) { g_stop.store(true); }

bool SleepUntil(std::int64_t mono_ns) {
  while (!g_stop.load()) {
    const std::int64_t now = NowNs(CLOCK_MONOTONIC);
    if (now >= mono_ns) return true;
    const std::int64_t left = mono_ns - now;
    std::this_thread::sleep_for(std::chrono::nanoseconds(left > 20000000 ? 20000000 : left));
  }
  return false;
}

}  // namespace

int main(int argc, char** argv) {
  std::string sequence_path;
  std::string log_path;
  std::string host_name = "score";
  inj::InjectionOptions options;
  for (int i = 1; i < argc; ++i) {
    const std::string argument = argv[i];
    if (i + 1 >= argc) {
      std::fprintf(stderr, "%s needs a value\n", argument.c_str());
      return 1;
    }
    const std::string value = argv[++i];
    if (argument == "--sequence") {
      sequence_path = value;
    } else if (argument == "--log") {
      log_path = value;
    } else if (argument == "--lead-in-s") {
      options.lead_in_s = std::atof(value.c_str());
    } else if (argument == "--tail-s") {
      options.tail_s = std::atof(value.c_str());
    } else if (argument == "--host-name") {
      host_name = value;
    } else {
      std::fprintf(stderr, "unknown argument: %s\n", argument.c_str());
      return 1;
    }
  }
  if (sequence_path.empty() || log_path.empty()) {
    std::fprintf(stderr, "usage: %s --sequence <file> --log <jsonl> [--lead-in-s S] [--tail-s S]\n", argv[0]);
    return 1;
  }
  const char* mw_config = std::getenv("MW_COM_CONFIG");
  if (mw_config == nullptr) {
    std::fprintf(stderr, "warningInjector: MW_COM_CONFIG is unset\n");
    return 2;
  }
  RunLog log(log_path, host_name, "warningInjector");
  if (!log.ok()) {
    std::fprintf(stderr, "warningInjector: cannot write %s\n", log_path.c_str());
    return 2;
  }
  std::string text;
  if (std::FILE* f = std::fopen(sequence_path.c_str(), "rb")) {
    char buffer[4096];
    std::size_t got = 0;
    while ((got = std::fread(buffer, 1, sizeof buffer, f)) > 0) text.append(buffer, got);
    std::fclose(f);
  }
  inj::InjectionPlan plan;
  std::string error;
  if (!inj::ParsePlan(text, &plan, &error)) {
    std::fprintf(stderr, "warningInjector: %s: %s\n", sequence_path.c_str(), error.c_str());
    log.Write("error", 1, "{\"stage\":\"plan\",\"reason\":" + de4sdv::driver_assistance::JsonString(error) + "}");
    return 3;
  }
  std::signal(SIGINT, OnSignal);
  std::signal(SIGTERM, OnSignal);
  score::mw::com::runtime::InitializeRuntime(score::mw::com::runtime::RuntimeConfiguration{std::string(mw_config)});
  LolaWarningSink sink;
  inj::Clocks clocks;
  clocks.mono_ns = [] { return NowNs(CLOCK_MONOTONIC); };
  clocks.real_ns = [] { return NowNs(CLOCK_REALTIME); };
  clocks.sleep_until = SleepUntil;
  return inj::Inject(plan, options, &sink, clocks, &log);
}
