// DE4SDV driver-assistance bench (INC-DRIVING-002): the Launch Manager control client of the stop run.
//
// The stop run of REQ-DRIVING-038 and -043 (S1-BUILD-PLAN.md section 4) switches the Launch Manager to the run target
// path_stopped (launch-manager/config/launch_manager_config.json) through its LmControl service. Lifecycle v0.10.0 has
// the client library (//score/launch_manager:control_cc, ILmControl, src/lm_control/src/ilm_control.hpp) but no
// command-line client: its examples' lmcontrol talks to a control_daemon over a socket, and that daemon would have to
// be a component of the configuration (examples/control_application/). So this small client is built into the bundle.
//
// The core here holds the order and the outcome; it knows ILmControl only through ControlPort, so the host's tests run
// it with a fake. lm_control_client_main.cpp binds the port to ILmControl over mw::com.
#pragma once

#include <cstdint>
#include <functional>
#include <string>

namespace de4sdv::lm_control {

// Exit codes and the record's "rc".
enum Rc : int {
  kSettled = 0,         // the Launch Manager reported the requested target active after the request
  kUsage = 2,           // bad arguments or environment
  kNotConnected = 3,    // no LmControl service within the connect timeout
  kRejected = 4,        // the Launch Manager refused the request (or the call failed)
  kNotSettled = 5,      // accepted, but no activation of the target reported within the settle timeout
  kSettledElsewhere = 6,  // an activation after the request settled on another target (a recovery)
};

struct Options {
  std::string run_target;
  std::string mw_com_config;
  std::string instance_specifier = "StateManager/LaunchManager/Instance";
  int connect_timeout_ms = 5000;
  int settle_timeout_ms = 30000;
  int drain_ms = 200;  // after the connection: earlier activation results (the start's) arrive and are set aside
};

// Parses --run-target <name> --mw-com-config <file> [--instance <specifier>] [--connect-timeout-ms N]
// [--settle-timeout-ms N] [--drain-ms N]. False, with the reason, on anything else.
bool ParseArguments(int argc, const char* const* argv, Options* options, std::string* error);

// What caused an activation (Lifecycle v0.10.0 run_target_activation_source.hpp: 0 initial, 1 state manager request,
// 2 recovery action).
enum class Source : int { kInitial = 0, kRequest = 1, kRecovery = 2, kUnknown = 3 };
const char* SourceName(Source source);

// The seam over ILmControl. Activate() is activate_run_target(name, force = true): Lifecycle v0.10.0 rejects a queued
// request (daemon control_provider.hpp:131-138, kNotImplemented).
class ControlPort {
 public:
  using Callback = std::function<void(Source source, const std::string& target)>;
  virtual ~ControlPort() = default;
  virtual bool RegisterCallback(Callback callback, std::string* error) = 0;
  virtual bool WaitForConnection(int timeout_ms, std::string* error) = 0;
  virtual bool Activate(const std::string& target, std::string* error) = 0;
};

class Clock {
 public:
  virtual ~Clock() = default;
  virtual std::int64_t RealNs() = 0;  // CLOCK_REALTIME
  virtual std::int64_t MonoNs() = 0;  // CLOCK_MONOTONIC, the clock of the bench's mono_ns records on the host
  virtual void SleepMs(int ms) = 0;
};

struct Outcome {
  int rc = kUsage;
  std::int64_t request_real_ns = 0;  // just before the request was sent
  std::int64_t request_mono_ns = 0;
  std::int64_t settled_real_ns = 0;  // when the activation of the target was reported (0: none)
  std::int64_t settled_mono_ns = 0;
  std::string settled_target;
  std::string settled_source;
  int earlier_results = 0;  // activation results received before the request (set aside)
  std::string error;
  // The stop instant of the record: the settlement when the target was reported active, the request otherwise.
  std::int64_t StopRealNs() const { return rc == kSettled ? settled_real_ns : request_real_ns; }
  std::int64_t StopMonoNs() const { return rc == kSettled ? settled_mono_ns : request_mono_ns; }
};

// Registers the callback, waits for the connection, lets earlier results drain, takes the request instant, requests
// the target and waits for its activation: the first result after the request that a state manager request caused
// (or a recovery: kSettledElsewhere).
Outcome ActivateAndSettle(ControlPort& port, Clock& clock, const Options& options);

// One JSON object on one line, without the newline: runTarget, stopInstantRealNs, stopInstantMonoNs, rc, then the
// request and settlement instants, the settled target and source, the count of earlier results and the error.
std::string OutcomeJson(const Options& options, const Outcome& outcome);

}  // namespace de4sdv::lm_control
