// DE4SDV driver-assistance bench (INC-DRIVING-002): the actuation adapter, an
// S-CORE application (PSR DrivingCommandActuationAdapter).
//
//   in   mw::com proxy  de4sdv/driver_assistance/driving_command, event
//                       "driving_command" (ICD.md: service 7411,
//                       DrivingCommandEventPayload; MAP-DRIVING-DA-COMMAND)
//   in   simulator      the newest world snapshot: simulation time and the ego
//                       vehicle's speed (simulator_client.h)
//   out  simulator      the Ackermann control of the ego vehicle
//
// The rules are the core's (actuation_core.h); the shell (adapter_shell.h)
// applies and logs. This file only starts, wires and stops: it builds against
// S-CORE Communication v0.6.0 in the B2 workspace, and the host's tests check
// it only for syntax, against the closed-loop bench's local mw::com mock.
//
// Order: the simulator client connects and finds the ego vehicle first, its
// snapshots start, and only then does the adapter subscribe to the command
// event, so that the first command meets a world snapshot. On a stop signal the
// receive loop ends before the snapshots stop. The adapter publishes nothing:
// the model gives it no output on S-CORE communication.
//
// Supervision (the supervision decision of 2026-11-18): once subscribed, the
// adapter reports running to the Launch Manager, and its receive loop gives one
// alive notification per 0.1 s (alive_ticker.h). The values the Launch Manager
// checks them against are in ../launch-manager/README.md.
//
// Usage:
//   actuation_adapter --run-dir <dir> --config <adapter.json> [--host-name score]
// MW_COM_CONFIG names this process's mw::com configuration
// (mw_com_config_actuation_adapter.json).
//
// Log: <run_dir>/<host-name>/actuationAdapter.jsonl (log_records.h): start,
// config, ready, supervision, in.world_snapshot, in.driving_command, drop,
// out.ackermann_control, error, stop.
#include <atomic>
#include <chrono>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <memory>
#include <string>
#include <thread>
#include <unistd.h>

#include "adapter_config.h"
#include "adapter_shell.h"
#include "alive_ticker.h"
#include "de4sdv/driver_assistance/payloads.h"
#include "log_records.h"
#include "run_log.h"
#include "score/mw/com/runtime.h"
#include "score/mw/com/types.h"
#include "simulator_client.h"

using de4sdv::driver_assistance::DrivingCommandEventPayload;
using de4sdv::driver_assistance::JsonNumber;
using de4sdv::driver_assistance::JsonString;
using de4sdv::driver_assistance::MonotonicSeconds;
using de4sdv::driver_assistance::RunLog;
using de4sdv::driver_assistance::actuation::AdapterConfig;
using de4sdv::driver_assistance::actuation::AdapterShell;
using de4sdv::driver_assistance::actuation::AliveTicker;
using de4sdv::driver_assistance::actuation::LifecycleClient;
using de4sdv::driver_assistance::actuation::MakeLifecycleClient;
using de4sdv::driver_assistance::actuation::AttachToSimulator;
using de4sdv::driver_assistance::actuation::LoadAdapterConfigFile;
using de4sdv::driver_assistance::actuation::RecordWriter;
namespace records = de4sdv::driver_assistance::actuation::records;
namespace sim = de4sdv::driver_assistance::actuation::simulator;

namespace {

template <typename Trait>
struct DrivingCommandInterface : public Trait::Base {
  using Trait::Base::Base;
  typename Trait::template Event<DrivingCommandEventPayload> driving_command{*this,
                                                                            "driving_command"};
};
using DrivingCommandProxy = score::mw::com::AsProxy<DrivingCommandInterface>;

constexpr const char* kDrivingCommandSpecifier = "de4sdv/driver_assistance/driving_command";

// One alive notification per command cycle of 0.1 s (../launch-manager/README.md).
constexpr double kAlivePeriodS = 0.1;

std::atomic<bool> g_stop{false};
void OnSignal(int /*signal*/) { g_stop.store(true); }

std::string Tag(const char* name, const std::string& value) {
  return "\"" + std::string(name) + "\":" + value;
}

void Usage(const char* program) {
  std::fprintf(stderr, "usage: %s --run-dir <dir> --config <adapter.json> [--host-name score]\n",
               program);
}

}  // namespace

int main(int argc, char** argv) {
  std::string run_dir;
  std::string host_name = "score";
  std::string config_path;
  for (int i = 1; i < argc; ++i) {
    const std::string argument = argv[i];
    if ((argument == "--run-dir" || argument == "--config" || argument == "--host-name") &&
        i + 1 >= argc) {
      std::fprintf(stderr, "%s needs a value\n", argument.c_str());
      return 1;
    }
    if (argument == "--run-dir") {
      run_dir = argv[++i];
    } else if (argument == "--config") {
      config_path = argv[++i];
    } else if (argument == "--host-name") {
      host_name = argv[++i];
    } else if (argument == "--help" || argument == "-h") {
      Usage(argv[0]);
      return 0;
    } else {
      std::fprintf(stderr, "unknown argument: %s\n", argument.c_str());
      Usage(argv[0]);
      return 1;
    }
  }
  if (run_dir.empty() || config_path.empty()) {
    Usage(argv[0]);
    return 1;
  }
  const char* mw_config = std::getenv("MW_COM_CONFIG");
  if (mw_config == nullptr) {
    std::fprintf(stderr, "actuationAdapter: MW_COM_CONFIG is unset\n");
    return 2;
  }
  bool config_ok = false;
  std::string config_error;
  const AdapterConfig config = LoadAdapterConfigFile(config_path, &config_ok, &config_error);
  if (!config_ok) {
    std::fprintf(stderr, "actuationAdapter: %s\n", config_error.c_str());
    return 3;
  }

  std::error_code directory_error;
  std::filesystem::create_directories(std::filesystem::path(run_dir) / host_name, directory_error);
  const std::string log_path =
      (std::filesystem::path(run_dir) / host_name / "actuationAdapter.jsonl").string();
  RunLog log(log_path, host_name, "actuationAdapter");
  if (!log.ok()) {
    std::fprintf(stderr, "actuationAdapter: cannot write %s\n", log_path.c_str());
    return 4;
  }
  RecordWriter writer(&log);
  writer.Write("start", "{" + Tag("pid", std::to_string(static_cast<long long>(::getpid()))) +
                            "," + Tag("config", JsonString(config_path)) + "," +
                            Tag("mw_com_config", JsonString(mw_config)) + "," +
                            Tag("run_dir", JsonString(run_dir)) + "}");
  std::signal(SIGINT, OnSignal);
  std::signal(SIGTERM, OnSignal);

  // The simulator client first: connect and find the ego vehicle.
  sim::ClientOptions options;
  options.host = config.carla_host;
  options.port = config.carla_port;
  options.timeoutS = config.client_timeout_s;
  options.heroRoleName = config.hero_role_name;
  options.heroWaitS = config.hero_wait_s;
  sim::ClientInfo info;
  std::string error;
  if (!sim::Connect(options, &info, &error)) {
    std::fprintf(stderr, "actuationAdapter: %s\n", error.c_str());
    writer.Write("error", records::Error("simulator client", error));
    return 5;
  }
  writer.Write("config",
               "{" + Tag("carla_host", JsonString(config.carla_host)) + "," +
                   Tag("carla_port", std::to_string(config.carla_port)) + "," +
                   Tag("client_timeout_s", JsonNumber(config.client_timeout_s)) + "," +
                   Tag("hero_role_name", JsonString(config.hero_role_name)) + "," +
                   Tag("clientVersion", JsonString(info.clientVersion)) + "," +
                   Tag("serverVersion", JsonString(info.serverVersion)) + "," +
                   Tag("heroActorId", std::to_string(info.heroActorId)) + "," +
                   Tag("heroTypeId", JsonString(info.heroTypeId)) + "}");

  AdapterShell shell(&writer);
  if (!AttachToSimulator(&shell, &error)) {
    std::fprintf(stderr, "actuationAdapter: %s\n", error.c_str());
    writer.Write("error", records::Error("simulator snapshots", error));
    sim::Disconnect();
    return 6;
  }

  // Then the command event.
  score::mw::com::runtime::InitializeRuntime(
      score::mw::com::runtime::RuntimeConfiguration{std::string(mw_config)});
  auto specifier =
      score::mw::com::InstanceSpecifier::Create(std::string(kDrivingCommandSpecifier));
  if (!specifier.has_value()) {
    writer.Write("error", records::Error("bad driving-command specifier"));
    sim::StopSnapshots();
    sim::Disconnect();
    return 7;
  }
  auto handles = DrivingCommandProxy::FindService(specifier.value());
  for (int attempt = 0; attempt < 600 && !g_stop.load(); ++attempt) {
    handles = DrivingCommandProxy::FindService(specifier.value());
    if (handles.has_value() && !handles.value().empty()) break;
    std::this_thread::sleep_for(std::chrono::milliseconds(100));
  }
  if (!handles.has_value() || handles.value().empty()) {
    writer.Write("error", records::Error("driving-command service not found"));
    sim::StopSnapshots();
    sim::Disconnect();
    return 8;
  }
  auto proxy_result = DrivingCommandProxy::Create(handles.value().front());
  if (!proxy_result.has_value()) {
    writer.Write("error", records::Error("proxy create failed"));
    sim::StopSnapshots();
    sim::Disconnect();
    return 9;
  }
  auto& proxy = proxy_result.value();
  if (!proxy.driving_command.Subscribe(8).has_value()) {
    writer.Write("error", records::Error("subscribe failed"));
    sim::StopSnapshots();
    sim::Disconnect();
    return 10;
  }

  writer.Write("ready", "{}");
  std::string supervision_off_reason;
  const std::unique_ptr<LifecycleClient> lifecycle = MakeLifecycleClient(&supervision_off_reason);
  AliveTicker alive(lifecycle.get(), kAlivePeriodS, &writer);
  alive.Start(MonotonicSeconds(), supervision_off_reason);
  bool receive_failed = false;
  while (!g_stop.load()) {
    alive.Tick(MonotonicSeconds(), g_stop.load());
    const auto received = proxy.driving_command.GetNewSamples(
        [&shell](score::mw::com::SamplePtr<DrivingCommandEventPayload> sample) {
          shell.OnCommand(*sample, MonotonicSeconds());
        },
        8);
    if (!received.has_value()) {
      receive_failed = true;
      break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
  alive.Stop(MonotonicSeconds());
  if (receive_failed) writer.Write("error", records::Error("GetNewSamples failed"));

  // The receive loop has ended; now the snapshots.
  sim::StopSnapshots();
  sim::Disconnect();
  writer.Write("stop", "{" + Tag("applied", std::to_string(shell.AppliedCount())) + "," +
                           Tag("dropped", std::to_string(shell.DroppedCount())) + "}");
  return receive_failed ? 11 : 0;
}
