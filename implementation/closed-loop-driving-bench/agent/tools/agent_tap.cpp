// DE4SDV closed-loop driving bench: agent_tap, a second process that subscribes to the four mw::com
// services drivingAgent offers and reports what crossed the process boundary. Bench tool only (the
// state publisher and the actuation adapter are the real consumers).
//
// Usage: agent_tap <seconds> <out.json>   (MW_COM config via -service_instance_manifest or env)
#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <thread>

#include "score/mw/com/runtime.h"

#include "de4sdv/driving/payloads.h"
#include "de4sdv/driving/run_log.h"
#include "services.h"

namespace dd = de4sdv::driving;
namespace da = de4sdv::driving::agent;

namespace {

struct Stats {
  std::uint64_t n = 0;
  std::uint64_t first = 0;
  std::uint64_t last = 0;
  std::uint64_t out_of_order = 0;  // frame below the previous one
  std::uint64_t repeated = 0;      // frame equal to the previous one (commands: the stop's frozen plan)
  void Add(std::uint64_t frame) {
    if (n == 0) first = frame;
    if (n > 0 && frame < last) ++out_of_order;
    if (n > 0 && frame == last) ++repeated;
    if (n == 0 || frame > last) last = frame;
    ++n;
  }
  std::string Json() const {
    return "{\"n\":" + std::to_string(n) + ",\"first\":" + std::to_string(first) + ",\"last\":" +
           std::to_string(last) + ",\"out_of_order\":" + std::to_string(out_of_order) +
           ",\"repeated\":" + std::to_string(repeated) + "}";
  }
};

template <typename ProxyT>
std::optional<ProxyT> Connect(const char* specifier_text, int tries) {
  auto specifier = score::mw::com::InstanceSpecifier::Create(std::string{specifier_text});
  if (!specifier.has_value()) return std::nullopt;
  for (int i = 0; i < tries; ++i) {
    auto handles = ProxyT::FindService(specifier.value());
    if (handles.has_value() && !handles.value().empty()) {
      auto proxy = ProxyT::Create(handles.value().front());
      if (proxy.has_value()) return std::move(proxy).value();
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
  return std::nullopt;
}

}  // namespace

int main(int argc, const char** argv) {
  if (argc < 3) {
    std::fprintf(stderr, "usage: agent_tap <seconds> <out.json> [mw_com_config]\n");
    return 2;
  }
  const double seconds = std::atof(argv[1]);
  const std::string out_path = argv[2];
  if (argc > 3) {
    score::mw::com::runtime::InitializeRuntime(score::mw::com::runtime::RuntimeConfiguration{std::string(argv[3])});
  }
  auto ego = Connect<da::EgoMotionSampleProxy>(da::kEgoMotionSampleSpecifier, 300);
  auto plan = Connect<da::PlanProxy>(da::kPlanSpecifier, 300);
  auto mode = Connect<da::ModeProxy>(da::kModeSpecifier, 300);
  auto command = Connect<da::CommandProxy>(da::kCommandSpecifier, 300);
  if (!ego || !plan || !mode || !command) {
    std::fprintf(stderr, "agent_tap: service not found (ego %d plan %d mode %d command %d)\n", !!ego, !!plan, !!mode,
                 !!command);
    return 3;
  }
  if (!ego->ego_motion_sample.Subscribe(8).has_value() || !plan->plan.Subscribe(8).has_value() ||
      !mode->mode.Subscribe(8).has_value() || !command->command.Subscribe(8).has_value()) {
    std::fprintf(stderr, "agent_tap: subscribe failed\n");
    return 4;
  }
  Stats s_ego, s_plan, s_mode, s_cmd;
  std::uint64_t plan_bad = 0, cmd_no_ref = 0, mode_driving = 0;
  double plan_latency_max = 0.0;  // receipt - productionTime, both CLOCK_MONOTONIC on this host
  const auto end = std::chrono::steady_clock::now() + std::chrono::milliseconds(static_cast<int>(seconds * 1000));
  while (std::chrono::steady_clock::now() < end) {
    ego->ego_motion_sample.GetNewSamples(
        [&](score::mw::com::SamplePtr<dd::EgoMotionSamplePayload> p) {
          s_ego.Add(static_cast<std::uint64_t>(std::llround(p->captureTime * 10.0)));
        },
        8);
    plan->plan.GetNewSamples(
        [&](score::mw::com::SamplePtr<dd::DrivingPlanPayload> p) {
          s_plan.Add(p->frameIndex);
          if (p->sampleCount != dd::kPlanSamples) ++plan_bad;
          plan_latency_max = std::max(plan_latency_max, dd::MonotonicSeconds() - p->productionTime);
        },
        8);
    mode->mode.GetNewSamples(
        [&](score::mw::com::SamplePtr<dd::DrivingModePayload> p) {
          s_mode.Add(p->frameIndex);
          if (p->mode == dd::Mode::kDriving) ++mode_driving;
        },
        8);
    command->command.GetNewSamples(
        [&](score::mw::com::SamplePtr<dd::VehicleMotionCommandPayload> p) {
          const std::string ref(p->planReference, strnlen(p->planReference, dd::kIdLength));
          const auto slash = ref.rfind('/');
          s_cmd.Add(slash == std::string::npos ? 0 : std::stoull(ref.substr(slash + 1)));
          if (ref.empty()) ++cmd_no_ref;
        },
        8);
    std::this_thread::sleep_for(std::chrono::milliseconds(2));
  }
  std::ofstream out(out_path);
  out << "{\"ego_motion_sample\":" << s_ego.Json() << ",\"plan\":" << s_plan.Json() << ",\"mode\":" << s_mode.Json()
      << ",\"command\":" << s_cmd.Json() << ",\"plan_sample_count_not_64\":" << plan_bad
      << ",\"command_without_plan_reference\":" << cmd_no_ref << ",\"mode_driving\":" << mode_driving
      << ",\"plan_receipt_minus_production_max_s\":" << dd::JsonNumber(plan_latency_max) << "}\n";
  std::printf("agent_tap: ego %llu plan %llu mode %llu command %llu\n", (unsigned long long)s_ego.n,
              (unsigned long long)s_plan.n, (unsigned long long)s_mode.n, (unsigned long long)s_cmd.n);
  return 0;
}
