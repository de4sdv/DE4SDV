// DE4SDV driver-assistance bench (INC-DRIVING-002): the core of the Launch Manager control client (see the header).
#include "lm_control_client.h"

#include <chrono>
#include <condition_variable>
#include <memory>
#include <cstdlib>
#include <mutex>
#include <string>

namespace de4sdv::lm_control {

namespace {

bool ParseInt(const std::string& text, int* out) {
  if (text.empty()) return false;
  char* end = nullptr;
  const long value = std::strtol(text.c_str(), &end, 10);
  if (end == nullptr || *end != '\0' || value < 0 || value > 3600000) return false;
  *out = static_cast<int>(value);
  return true;
}

std::string Json(const std::string& text) {
  std::string out = "\"";
  for (const char c : text) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (static_cast<unsigned char>(c) < 0x20) {
          static const char* hex = "0123456789abcdef";
          out += "\\u00";
          out += hex[(c >> 4) & 0xf];
          out += hex[c & 0xf];
        } else {
          out += c;
        }
    }
  }
  return out + "\"";
}

}  // namespace

bool ParseArguments(int argc, const char* const* argv, Options* options, std::string* error) {
  for (int i = 1; i < argc; ++i) {
    const std::string name = argv[i];
    if (i + 1 >= argc) {
      *error = "missing value of " + name;
      return false;
    }
    const std::string value = argv[++i];
    bool ok = true;
    if (name == "--run-target") {
      options->run_target = value;
    } else if (name == "--mw-com-config") {
      options->mw_com_config = value;
    } else if (name == "--instance") {
      options->instance_specifier = value;
    } else if (name == "--connect-timeout-ms") {
      ok = ParseInt(value, &options->connect_timeout_ms);
    } else if (name == "--settle-timeout-ms") {
      ok = ParseInt(value, &options->settle_timeout_ms);
    } else if (name == "--drain-ms") {
      ok = ParseInt(value, &options->drain_ms);
    } else {
      *error = "unknown argument " + name;
      return false;
    }
    if (!ok) {
      *error = "bad value of " + name + ": " + value;
      return false;
    }
  }
  if (options->run_target.empty() || options->run_target.size() > 128) {
    *error = "--run-target needs a name of 1 to 128 characters";
    return false;
  }
  if (options->mw_com_config.empty()) {
    *error = "--mw-com-config is required";
    return false;
  }
  if (options->instance_specifier.empty()) {
    *error = "--instance is empty";
    return false;
  }
  return true;
}

const char* SourceName(Source source) {
  switch (source) {
    case Source::kInitial: return "initial";
    case Source::kRequest: return "request";
    case Source::kRecovery: return "recovery";
    default: return "unknown";
  }
}

Outcome ActivateAndSettle(ControlPort& port, Clock& clock, const Options& options) {
  struct Shared {
    std::mutex mutex;
    std::condition_variable changed;
    bool requested = false;
    bool settled = false;
    int earlier = 0;
    Source source = Source::kUnknown;
    std::string target;
    std::int64_t real_ns = 0;
    std::int64_t mono_ns = 0;
  };
  auto shared = std::make_shared<Shared>();
  Outcome outcome;
  std::string error;
  const bool registered = port.RegisterCallback(
      [shared, &clock](Source source, const std::string& target) {
        const std::int64_t real_ns = clock.RealNs();
        const std::int64_t mono_ns = clock.MonoNs();
        std::lock_guard<std::mutex> lock(shared->mutex);
        if (!shared->requested) {
          ++shared->earlier;  // the start's activation, read at the subscription: not ours
          return;
        }
        if (shared->settled) return;
        if (source == Source::kInitial) {
          ++shared->earlier;
          return;
        }
        shared->settled = true;
        shared->source = source;
        shared->target = target;
        shared->real_ns = real_ns;
        shared->mono_ns = mono_ns;
        shared->changed.notify_all();
      },
      &error);
  if (!registered) {
    outcome.rc = kNotConnected;
    outcome.error = "register callback: " + error;
    outcome.request_real_ns = clock.RealNs();
    outcome.request_mono_ns = clock.MonoNs();
    return outcome;
  }
  if (!port.WaitForConnection(options.connect_timeout_ms, &error)) {
    outcome.rc = kNotConnected;
    outcome.error = "no LmControl service within " + std::to_string(options.connect_timeout_ms) + " ms: " + error;
    outcome.request_real_ns = clock.RealNs();
    outcome.request_mono_ns = clock.MonoNs();
    return outcome;
  }
  if (options.drain_ms > 0) clock.SleepMs(options.drain_ms);
  {
    std::lock_guard<std::mutex> lock(shared->mutex);
    shared->requested = true;
    outcome.earlier_results = shared->earlier;
  }
  outcome.request_real_ns = clock.RealNs();
  outcome.request_mono_ns = clock.MonoNs();
  if (!port.Activate(options.run_target, &error)) {
    outcome.rc = kRejected;
    outcome.error = "activate_run_target(" + options.run_target + "): " + error;
    return outcome;
  }
  std::unique_lock<std::mutex> lock(shared->mutex);
  const bool settled = shared->changed.wait_for(lock, std::chrono::milliseconds(options.settle_timeout_ms),
                                                [&] { return shared->settled; });
  outcome.earlier_results = shared->earlier;
  if (!settled) {
    outcome.rc = kNotSettled;
    outcome.error = "no activation reported within " + std::to_string(options.settle_timeout_ms) + " ms";
    return outcome;
  }
  outcome.settled_target = shared->target;
  outcome.settled_source = SourceName(shared->source);
  outcome.settled_real_ns = shared->real_ns;
  outcome.settled_mono_ns = shared->mono_ns;
  if (shared->source == Source::kRequest && shared->target == options.run_target) {
    outcome.rc = kSettled;
  } else {
    outcome.rc = kSettledElsewhere;
    outcome.error = "the activation after the request settled on " + shared->target + " (" +
                    SourceName(shared->source) + ")";
  }
  return outcome;
}

std::string OutcomeJson(const Options& options, const Outcome& outcome) {
  return "{\"runTarget\":" + Json(options.run_target) + ",\"stopInstantRealNs\":" +
         std::to_string(outcome.StopRealNs()) + ",\"stopInstantMonoNs\":" + std::to_string(outcome.StopMonoNs()) +
         ",\"rc\":" + std::to_string(outcome.rc) + ",\"requestRealNs\":" + std::to_string(outcome.request_real_ns) +
         ",\"requestMonoNs\":" + std::to_string(outcome.request_mono_ns) +
         ",\"settledRealNs\":" + std::to_string(outcome.settled_real_ns) +
         ",\"settledMonoNs\":" + std::to_string(outcome.settled_mono_ns) +
         ",\"settledTarget\":" + Json(outcome.settled_target) + ",\"settledSource\":" + Json(outcome.settled_source) +
         ",\"earlierResults\":" + std::to_string(outcome.earlier_results) + ",\"error\":" + Json(outcome.error) + "}";
}

}  // namespace de4sdv::lm_control
