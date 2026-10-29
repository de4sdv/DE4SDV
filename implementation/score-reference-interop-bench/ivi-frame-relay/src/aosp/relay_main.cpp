// The main of the DE4SDV IVI frame relay for the IVI VM (AOSP only).
//
// It parses the options, starts the AOSP gateway client and runs the shell.
// Log lines are JSON objects in liblog with the tag de4sdv_ivi_frame_relay.
// SIGTERM or SIGINT stop the relay: it ends the phase, unsubscribes,
// deletes the client, writes a final status line and exits 0. A refused
// option, among them any option that names a margin or a bound, stops the
// relay at start with code 2.

#include <signal.h>
#include <unistd.h>

#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <vector>

#include "aosp/sdv_gateway_client.hpp"
#include "de4sdv_ivi_frame_relay/event_log.hpp"
#include "de4sdv_ivi_frame_relay/options.hpp"
#include "shell/relay_shell.hpp"

namespace {

using de4sdv::ivi_frame_relay::LineLog;
using de4sdv::ivi_frame_relay::LogRecord;
using de4sdv::ivi_frame_relay::ParseOptions;
using de4sdv::ivi_frame_relay::RealClock;
using de4sdv::ivi_frame_relay::RelayOptions;
using de4sdv::ivi_frame_relay::RelayShell;
using de4sdv::ivi_frame_relay::SdvGatewayClient;
using de4sdv::ivi_frame_relay::ShellConfig;
using de4sdv::ivi_frame_relay::ShellResult;
using de4sdv::ivi_frame_relay::StartRecord;
using de4sdv::ivi_frame_relay::SystemProperties;
using de4sdv::ivi_frame_relay::Usage;
using de4sdv::ivi_frame_relay::WorkerConfig;

constexpr int kExitUsage = 2;
constexpr int kExitListenFailed = 3;

volatile std::sig_atomic_t g_stop_requested = 0;

void OnStopSignal(int) { g_stop_requested = 1; }

}  // namespace

int main(int argc, char** argv) {
  const std::vector<std::string> arguments(argv + 1, argv + argc);
  const auto parsed = ParseOptions(arguments);
  RealClock clock;
  LineLog log;
  if (parsed.help) {
    std::fputs(Usage().c_str(), stdout);
    return 0;
  }
  if (!parsed.options.has_value()) {
    log.Log(clock.Now(), LogRecord{"start_refused"}.Text("error", parsed.error).Signed("code", kExitUsage));
    std::fprintf(stderr, "de4sdv_ivi_frame_relay: %s\n%s", parsed.error.c_str(), Usage().c_str());
    return kExitUsage;
  }
  const RelayOptions options = *parsed.options;

  struct sigaction action {};
  action.sa_handler = OnStopSignal;
  sigemptyset(&action.sa_mask);
  sigaction(SIGTERM, &action, nullptr);
  sigaction(SIGINT, &action, nullptr);
  std::signal(SIGPIPE, SIG_IGN);

  SystemProperties properties{log};
  SdvGatewayClient client;  // starts the binder thread pool for the callbacks
  ShellConfig shell_config;
  shell_config.status_period_ns = options.status_period_ns;
  shell_config.client_write_timeout_ns = options.client_write_timeout_ns;
  shell_config.announce_properties = options.announce_properties;
  RelayShell shell{shell_config, options.relay, WorkerConfig{options.subject, options.publication}, client, log,
                   properties, clock};
  std::string error;
  if (!shell.Open(&error)) {
    log.Log(clock.Now(), LogRecord{"listen_failed"}.Text("error", error));
    return kExitListenFailed;
  }
  // The start line comes after listen(): the ingress may connect from now on.
  const auto started = clock.Now();
  log.Log(started, StartRecord(options, shell.policy_name(), static_cast<std::int64_t>(::getpid()))
                       .Signed("realtime_minus_monotonic_ns", started.realtime_ns - started.monotonic_ns));
  const ShellResult result = shell.Run([] { return g_stop_requested != 0; });
  log.Log(clock.Now(), LogRecord{"exit"}.Signed("code", result.exit_code).Bool("worker_joined", result.worker_joined));
  if (!result.worker_joined) {
    // The worker is still inside a gateway call and uses the shell: end the
    // process without destroying it.
    std::_Exit(result.exit_code);
  }
  return result.exit_code;
}
