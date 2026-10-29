#include "de4sdv_ivi_frame_relay/options.hpp"

#include <functional>
#include <map>

#include "de4sdv_ivi_frame_relay/discard_policy.hpp"
#include "de4sdv_ivi_frame_relay/gateway_worker.hpp"
#include "de4sdv_ivi_frame_relay/retry_schedule.hpp"

namespace de4sdv::ivi_frame_relay {

namespace {

// Decimal, without sign, at most max.
std::optional<std::uint64_t> ParseUnsigned(const std::string& text, std::uint64_t max) {
  if (text.empty()) {
    return std::nullopt;
  }
  std::uint64_t value = 0;
  for (const char c : text) {
    if (c < '0' || c > '9') {
      return std::nullopt;
    }
    const auto digit = static_cast<std::uint64_t>(c - '0');
    if (value > (max - digit) / 10U) {
      return std::nullopt;
    }
    value = value * 10U + digit;
  }
  return value;
}

// A name for the C API: not empty, at most max_chars, printable ASCII
// without spaces.
bool ValidName(const std::string& text, std::size_t max_chars) {
  if (text.empty() || text.size() > max_chars) {
    return false;
  }
  for (const char c : text) {
    if (c <= ' ' || c > '~') {
      return false;
    }
  }
  return true;
}

// An option that names a margin or a bound would set the discard margin.
bool NamesAMargin(const std::string& argument) {
  return argument.rfind("--", 0) == 0 &&
         (argument.find("margin") != std::string::npos || argument.find("bound") != std::string::npos);
}

std::string Ipv4Text(std::uint32_t address) {
  return std::to_string(address >> 24U) + "." + std::to_string((address >> 16U) & 0xFFU) + "." +
         std::to_string((address >> 8U) & 0xFFU) + "." + std::to_string(address & 0xFFU);
}

}  // namespace

std::string Usage() {
  return "usage: de4sdv_ivi_frame_relay [options]\n"
         "  --publication-vm <name>       VM of the broker's publication (instance1)\n"
         "  --publication-package <name>  package of the broker (com.android.sdv.someip)\n"
         "  --publication-bundle <name>   service bundle of the broker (SomeIpBroker)\n"
         "  --publication-unit <name>     service unit of the frame topic (de4sdv-score-aebs-signal-frame)\n"
         "  --subject-package <name>      the relay's package for initComms (de4sdv.ivi_frame_relay)\n"
         "  --subject-bundle <name>       the relay's service bundle (IviFrameRelay)\n"
         "  --subject-instance <name>     the relay's service instance (default)\n"
         "  --status-period-s <s>         period of the status line (10)\n"
         "  --log-frames                  one log line per served frame\n"
         "  --announce-property <name=value>  set this system property once the loopback\n"
         "                                server listens (Android only; repeatable, in order)\n"
         "  --ingress-start-property <name>  set it to 0 and then 1 once the loopback server\n"
         "                                listens, and every 1 s until the first client\n"
         "                                connects, at most 10 times\n"
         "The relay serves 127.0.0.1:4731 and subscribes with\n"
         "ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE. The discard margin is fixed at 20 ms:\n"
         "an option that names a margin or a bound stops the relay at start.\n";
}

ParsedOptions ParseOptions(const std::vector<std::string>& arguments) {
  ParsedOptions result;
  RelayOptions options;

  auto fail = [&result](const std::string& message) {
    result.options.reset();
    result.error = message;
    return result;
  };

  using Setter = std::function<bool(const std::string&)>;
  auto name = [](std::string& target, std::size_t max_chars) -> Setter {
    return [&target, max_chars](const std::string& text) {
      if (!ValidName(text, max_chars)) {
        return false;
      }
      target = text;
      return true;
    };
  };

  const std::map<std::string, Setter> valued = {
      {"--publication-vm", name(options.publication.vm, kMaxVmNameChars)},
      {"--publication-package", name(options.publication.package, kMaxPackageNameChars)},
      {"--publication-bundle", name(options.publication.bundle, kMaxBundleNameChars)},
      {"--publication-unit", name(options.publication.unit, kMaxUnitNameChars)},
      {"--subject-package", name(options.subject.package, kMaxPackageNameChars)},
      {"--subject-bundle", name(options.subject.bundle, kMaxBundleNameChars)},
      {"--subject-instance", name(options.subject.instance, kMaxInstanceNameChars)},
      {"--ingress-start-property",
       [&](const std::string& text) {
         if (text.empty() || text.find('=') != std::string::npos) {
           return false;
         }
         options.relay.ingress_start_property = text;
         return true;
       }},
      {"--announce-property",
       [&](const std::string& text) {
         std::string property;
         std::string value;
         if (!SplitProperty(text, &property, &value)) {
           return false;
         }
         options.announce_properties.push_back(text);
         return true;
       }},
      {"--status-period-s",
       [&](const std::string& text) {
         const auto value = ParseUnsigned(text, 3600);
         if (!value.has_value() || *value == 0U) {
           return false;
         }
         options.status_period_ns = static_cast<std::int64_t>(*value) * kNanosecondsPerSecond;
         return true;
       }},
  };

  for (std::size_t i = 0; i < arguments.size(); ++i) {
    const std::string& argument = arguments[i];
    if (NamesAMargin(argument)) {
      return fail(argument + ": no option sets the discard margin; it is fixed at 20 ms (ASM-MW-030)");
    }
    if (argument == "--help" || argument == "-h") {
      result.help = true;
      return result;
    }
    if (argument == "--log-frames") {
      options.relay.log_frames = true;
      continue;
    }
    const auto setter = valued.find(argument);
    if (setter == valued.end()) {
      return fail("unknown option " + argument);
    }
    if (i + 1 >= arguments.size()) {
      return fail("missing value of " + argument);
    }
    if (!setter->second(arguments[++i])) {
      return fail("invalid value of " + argument + ": " + arguments[i]);
    }
  }
  result.options = options;
  return result;
}

bool SplitProperty(const std::string& text, std::string* name, std::string* value) {
  const std::size_t equals = text.find('=');
  if (equals == std::string::npos || equals == 0U) {
    return false;
  }
  *name = text.substr(0, equals);
  *value = text.substr(equals + 1);
  return true;
}

LogRecord StartRecord(const RelayOptions& options, const char* policy_name, std::int64_t pid) {
  LogRecord record{"start"};
  record.Signed("pid", pid)
      .Text("publication_vm", options.publication.vm)
      .Text("publication_package", options.publication.package)
      .Text("publication_bundle", options.publication.bundle)
      .Text("publication_unit", options.publication.unit)
      .Text("subject_package", options.subject.package)
      .Text("subject_bundle", options.subject.bundle)
      .Text("subject_instance", options.subject.instance)
      .Unsigned("subscriber_flags", kSubscriberFlagNone)
      .Text("subscriber_flag", "ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE")
      .Text("listen", Ipv4Text(kListenAddress) + ":" + std::to_string(kListenPort))
      .Unsigned("max_payload_bytes", kMaxPayloadBytes)
      .Text("discard_policy", policy_name)
      .Signed("phase_start_margin_ns", PhaseStartDiscardPolicy::kPhaseStartMarginNs)
      .Unsigned("copy_memory_frames", PhaseStartDiscardPolicy::kCopyMemoryFrames)
      .Signed("silence_timeout_ns", kSilenceTimeoutNs)
      .Signed("destroyed_retry_period_ns", kDestroyedRetryPeriodNs)
      .Signed("destroyed_fast_window_ns", kDestroyedFastWindowNs)
      .Signed("retry_period_ns", kRetryPeriodNs)
      .Unsigned("silent_subscriptions_before_back_off", kSilentSubscriptionsBeforeBackOff)
      .Signed("silent_back_off_ns", kSilentBackOffNs)
      .Signed("start_diagnostic_ns", kStartDiagnosticNs)
      .Signed("slow_retry_period_ns", kSlowRetryPeriodNs)
      .Signed("client_fast_retry_window_ns", kClientFastRetryWindowNs)
      .Signed("read_poll_period_ns", kReadPollPeriodNs)
      .Signed("gateway_call_stall_ns", options.relay.gateway_call_stall_ns)
      .Unsigned("announce_properties", options.announce_properties.size())
      .Text("ingress_start_property", options.relay.ingress_start_property)
      .Signed("ingress_retrigger_period_ns", kIngressRetriggerPeriodNs)
      .Unsigned("ingress_retrigger_limit", kIngressRetriggerLimit)
      .Signed("status_period_ns", options.status_period_ns)
      .Signed("client_write_timeout_ns", options.client_write_timeout_ns)
      .Bool("log_frames", options.relay.log_frames);
  return record;
}

}  // namespace de4sdv::ivi_frame_relay
