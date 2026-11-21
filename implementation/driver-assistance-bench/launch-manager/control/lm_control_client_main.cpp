// DE4SDV driver-assistance bench (INC-DRIVING-002): the Launch Manager control client of the stop run, bound to S-CORE
// Lifecycle v0.10.0's ILmControl (//score/launch_manager:control_cc) over S-CORE Communication v0.6.0.
//
//   lm_control_client --run-target path_stopped --mw-com-config <mw_com_config_lm_control_client.json>
//                     [--instance StateManager/LaunchManager/Instance] [--connect-timeout-ms 5000]
//                     [--settle-timeout-ms 30000] [--drain-ms 200]
//
// Prints one JSON line (lm_control_client.h, OutcomeJson) and exits with its rc. It runs as root beside the Launch
// Manager (both read the same mw::com shared memory); score-path/scripts/path_stop.sh calls it. The mw::com
// configuration names the proxy side of the daemon's LmControl instance (launch-manager/config/
// mw_com_config_lm_control_client.json, application id 3418).
#include <time.h>

#include <chrono>
#include <cstdint>
#include <cstdio>
#include <memory>
#include <string>
#include <string_view>
#include <thread>

#include "lm_control_client.h"
#include "score/mw/com/runtime.h"
#include "score/mw/lifecycle/ilm_control.hpp"

namespace lm = de4sdv::lm_control;
namespace lc = score::mw::lifecycle;

namespace {

class SystemClock final : public lm::Clock {
 public:
  std::int64_t RealNs() override { return Now(CLOCK_REALTIME); }
  std::int64_t MonoNs() override { return Now(CLOCK_MONOTONIC); }
  void SleepMs(int ms) override { std::this_thread::sleep_for(std::chrono::milliseconds(ms)); }

 private:
  static std::int64_t Now(clockid_t id) {
    timespec ts{};
    clock_gettime(id, &ts);
    return static_cast<std::int64_t>(ts.tv_sec) * 1000000000LL + ts.tv_nsec;
  }
};

lm::Source ToSource(lc::RunTargetActivationSource source) {
  switch (source) {
    case lc::RunTargetActivationSource::kInitialActivation: return lm::Source::kInitial;
    case lc::RunTargetActivationSource::kStateManagerRequest: return lm::Source::kRequest;
    case lc::RunTargetActivationSource::kRecoveryAction: return lm::Source::kRecovery;
  }
  return lm::Source::kUnknown;
}

class LmControlPort final : public lm::ControlPort {
 public:
  explicit LmControlPort(std::unique_ptr<lc::ILmControl> control) : control_(std::move(control)) {}

  bool RegisterCallback(Callback callback, std::string* error) override {
    const auto result = control_->register_run_target_activation_callback(
        [callback](lc::RunTargetActivationSource source, lc::RunTargetName target) {
          callback(ToSource(source), std::string(target.as_string_view()));
        });
    if (!result.has_value()) *error = std::string(result.error().Message());
    return result.has_value();
  }
  bool WaitForConnection(int timeout_ms, std::string* error) override {
    const auto result = control_->wait_for_connection(std::chrono::milliseconds(timeout_ms));
    if (!result.has_value()) *error = std::string(result.error().Message());
    return result.has_value();
  }
  bool Activate(const std::string& target, std::string* error) override {
    const auto result = control_->activate_run_target(lc::RunTargetName{std::string_view{target}}, true);
    if (!result.has_value()) *error = std::string(result.error().Message());
    return result.has_value();
  }

 private:
  std::unique_ptr<lc::ILmControl> control_;
};

}  // namespace

int main(int argc, char** argv) {
  lm::Options options;
  std::string error;
  SystemClock clock;
  if (!lm::ParseArguments(argc, argv, &options, &error)) {
    std::fprintf(stderr, "lm_control_client: %s\n", error.c_str());
    lm::Outcome outcome;
    outcome.rc = lm::kUsage;
    outcome.error = error;
    outcome.request_real_ns = clock.RealNs();
    outcome.request_mono_ns = clock.MonoNs();
    std::printf("%s\n", lm::OutcomeJson(options, outcome).c_str());
    return lm::kUsage;
  }
  score::mw::com::runtime::InitializeRuntime(score::mw::com::runtime::RuntimeConfiguration{options.mw_com_config});
  auto created = lc::ILmControl::Create(options.instance_specifier);
  lm::Outcome outcome;
  if (!created.has_value()) {
    outcome.rc = lm::kNotConnected;
    outcome.error = "ILmControl::Create: " + std::string(created.error().Message());
    outcome.request_real_ns = clock.RealNs();
    outcome.request_mono_ns = clock.MonoNs();
  } else {
    LmControlPort port(std::move(created).value());
    outcome = lm::ActivateAndSettle(port, clock, options);
  }
  std::printf("%s\n", lm::OutcomeJson(options, outcome).c_str());
  std::fflush(stdout);
  return outcome.rc;
}
