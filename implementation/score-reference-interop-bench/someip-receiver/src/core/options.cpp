#include "de4sdv_someip_receiver/options.hpp"

#include <functional>
#include <map>

#include "de4sdv_someip_receiver/discard_policy.hpp"

namespace de4sdv::someip_receiver {

namespace {

// Decimal or 0x-prefixed hexadecimal, without sign, at most max.
std::optional<std::uint64_t> ParseUnsigned(const std::string& text, std::uint64_t max) {
  std::size_t start = 0;
  unsigned base = 10;
  if (text.size() > 2 && text[0] == '0' && (text[1] == 'x' || text[1] == 'X')) {
    start = 2;
    base = 16;
  }
  if (start >= text.size()) {
    return std::nullopt;
  }
  std::uint64_t value = 0;
  for (std::size_t i = start; i < text.size(); ++i) {
    const char c = text[i];
    unsigned digit = 0;
    if (c >= '0' && c <= '9') {
      digit = static_cast<unsigned>(c - '0');
    } else if (base == 16 && c >= 'a' && c <= 'f') {
      digit = static_cast<unsigned>(c - 'a' + 10);
    } else if (base == 16 && c >= 'A' && c <= 'F') {
      digit = static_cast<unsigned>(c - 'A' + 10);
    } else {
      return std::nullopt;
    }
    if (value > (max - digit) / base) {
      return std::nullopt;
    }
    value = value * base + digit;
  }
  return value;
}

std::string Hex16(std::uint16_t value) {
  static const char digits[] = "0123456789abcdef";
  std::string text = "0x";
  for (int shift = 12; shift >= 0; shift -= 4) {
    text += digits[(value >> static_cast<unsigned>(shift)) & 0xFU];
  }
  return text;
}

}  // namespace

std::string Usage() {
  return "usage: de4sdv_someip_receiver --server-address <ipv4> [options]\n"
         "  --sd-port <port>              SOME/IP-SD port (30490)\n"
         "  --reliable-port <port>        TCP port of the event without an offer (30509)\n"
         "  --multicast-group <ipv4>      SD multicast group (224.244.224.245)\n"
         "  --multicast-interface <ipv4>  local address of the multicast interface (0.0.0.0: by route)\n"
         "  --no-multicast                do not join the group: unicast fallback only\n"
         "  --service <id> --instance <id> --major-version <n> --eventgroup <id> --event <id>\n"
         "                                (0x4dee, 0x0001, 1, 0x0001, 0x8001)\n"
         "  --ttl-s <s>                   TTL of the subscription (3)\n"
         "  --renew-period-ms <ms>        renewal period, less than the TTL (1000)\n"
         "  --subscribe-delay-ms <ms>     delay of the first subscribe after the TCP connect (20)\n"
         "  --subscribe-timeout-ms <ms>   no Ack in this time closes the connection (6000)\n"
         "  --connect-timeout-ms <ms>     TCP connect timeout (2000)\n"
         "  --connect-retry-ms <ms>       period of the connection attempts (500)\n"
         "  --listen-address <ipv4>       loopback address of the frame server (127.0.0.1)\n"
         "  --listen-port <port>          port of the frame server (4731)\n"
         "  --max-payload-bytes <n>       largest payload: prefix and frame (2048)\n"
         "  --status-period-s <s>         period of the status line (10)\n"
         "  --log-frames                  one log line per frame of the event\n"
         "  --announce-property <name=value>  set this system property once the loopback\n"
         "                                server listens (Android only)\n";
}

ParsedOptions ParseOptions(const std::vector<std::string>& arguments) {
  ParsedOptions result;
  ReceiverOptions options;
  bool has_server = false;
  SubscriptionConfig& s = options.receiver.subscription;
  std::string error;

  auto fail = [&result](const std::string& message) {
    result.options.reset();
    result.error = message;
    return result;
  };

  using Setter = std::function<bool(const std::string&)>;
  auto number = [](std::uint64_t max, std::function<void(std::uint64_t)> store) -> Setter {
    return [max, store](const std::string& text) {
      const auto value = ParseUnsigned(text, max);
      if (!value.has_value()) {
        return false;
      }
      store(*value);
      return true;
    };
  };
  auto address = [](std::function<void(std::uint32_t)> store) -> Setter {
    return [store](const std::string& text) {
      const auto value = ParseIpv4(text);
      if (!value.has_value()) {
        return false;
      }
      store(*value);
      return true;
    };
  };
  auto milliseconds = [&number](std::int64_t& target, std::uint64_t max) -> Setter {
    return number(max, [&target](std::uint64_t value) {
      target = static_cast<std::int64_t>(value) * kNanosecondsPerMillisecond;
    });
  };

  const std::map<std::string, Setter> valued = {
      {"--server-address", address([&](std::uint32_t v) { s.server_address = v; has_server = true; })},
      {"--announce-property", [&](const std::string& text) {
         std::string name;
         std::string value;
         if (!SplitProperty(text, &name, &value)) {
           return false;
         }
         options.announce_property = text;
         return true;
       }},
      {"--sd-port", number(65535, [&](std::uint64_t v) { s.sd_port = static_cast<std::uint16_t>(v); })},
      {"--reliable-port", number(65535, [&](std::uint64_t v) { s.reliable_port = static_cast<std::uint16_t>(v); })},
      {"--multicast-group", address([&](std::uint32_t v) { options.multicast_group = v; })},
      {"--multicast-interface", address([&](std::uint32_t v) { options.multicast_interface = v; })},
      {"--service", number(0xFFFE, [&](std::uint64_t v) { s.service_id = static_cast<std::uint16_t>(v); })},
      {"--instance", number(0xFFFF, [&](std::uint64_t v) { s.instance_id = static_cast<std::uint16_t>(v); })},
      {"--major-version", number(0xFF, [&](std::uint64_t v) { s.major_version = static_cast<std::uint8_t>(v); })},
      {"--eventgroup", number(0xFFFF, [&](std::uint64_t v) { s.eventgroup_id = static_cast<std::uint16_t>(v); })},
      {"--event", number(0xFFFF, [&](std::uint64_t v) { options.receiver.event_id = static_cast<std::uint16_t>(v); })},
      {"--ttl-s", number(kMaxTtl, [&](std::uint64_t v) { s.ttl_s = static_cast<std::uint32_t>(v); })},
      {"--renew-period-ms", milliseconds(s.renew_period_ns, 600'000)},
      {"--subscribe-delay-ms", milliseconds(s.subscribe_delay_ns, 10'000)},
      {"--subscribe-timeout-ms", milliseconds(s.subscribe_timeout_ns, 600'000)},
      {"--connect-timeout-ms", milliseconds(s.connect_timeout_ns, 600'000)},
      {"--connect-retry-ms", milliseconds(s.connect_retry_period_ns, 600'000)},
      {"--listen-address", address([&](std::uint32_t v) { options.listen_address = v; })},
      {"--listen-port", number(65535, [&](std::uint64_t v) { options.listen_port = static_cast<std::uint16_t>(v); })},
      {"--max-payload-bytes",
       number(65536, [&](std::uint64_t v) { options.receiver.max_payload_bytes = static_cast<std::size_t>(v); })},
      {"--status-period-s", number(3600, [&](std::uint64_t v) {
         options.status_period_ns = static_cast<std::int64_t>(v) * kNanosecondsPerSecond;
       })},
  };

  for (std::size_t i = 0; i < arguments.size(); ++i) {
    const std::string& argument = arguments[i];
    if (argument == "--help" || argument == "-h") {
      result.help = true;
      return result;
    }
    if (argument == "--no-multicast") {
      options.join_multicast = false;
      continue;
    }
    if (argument == "--log-frames") {
      options.receiver.log_frames = true;
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

  if (!has_server) {
    return fail("--server-address is required");
  }
  if (s.sd_port == 0 || s.reliable_port == 0 || options.listen_port == 0) {
    return fail("a port must not be 0");
  }
  if ((options.listen_address >> 24U) != 127U) {
    return fail("--listen-address must be a loopback address");
  }
  if ((options.multicast_group >> 28U) != 0xEU) {
    return fail("--multicast-group must be an IPv4 multicast address");
  }
  if (s.ttl_s == 0U) {
    return fail("--ttl-s must be at least 1");
  }
  if (s.renew_period_ns <= 0 || s.renew_period_ns >= static_cast<std::int64_t>(s.ttl_s) * kNanosecondsPerSecond) {
    return fail("--renew-period-ms must be greater than 0 and less than the TTL");
  }
  if (s.subscribe_timeout_ns <= 0 || s.connect_timeout_ns <= 0 || s.connect_retry_period_ns <= 0) {
    return fail("timeouts and the retry period must be greater than 0");
  }
  if (options.receiver.max_payload_bytes < 4U) {
    return fail("--max-payload-bytes must hold the 4-byte prefix");
  }
  if (options.status_period_ns <= 0) {
    return fail("--status-period-s must be at least 1");
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

LogRecord StartRecord(const ReceiverOptions& options, const char* policy_name, std::int64_t pid) {
  const SubscriptionConfig& s = options.receiver.subscription;
  LogRecord record{"start"};
  record.Signed("pid", pid)
      .Text("server_address", Ipv4ToText(s.server_address))
      .Unsigned("sd_port", s.sd_port)
      .Unsigned("reliable_port", s.reliable_port)
      .Unsigned("service_id", s.service_id)
      .Text("service_hex", Hex16(s.service_id))
      .Unsigned("instance_id", s.instance_id)
      .Unsigned("major_version", s.major_version)
      .Unsigned("eventgroup_id", s.eventgroup_id)
      .Unsigned("event_id", options.receiver.event_id)
      .Text("event_id_hex", Hex16(options.receiver.event_id))
      .Bool("join_multicast", options.join_multicast)
      .Text("multicast_group", Ipv4ToText(options.multicast_group))
      .Text("multicast_interface", Ipv4ToText(options.multicast_interface))
      .Unsigned("subscription_ttl_s", s.ttl_s)
      .Signed("renew_period_ns", s.renew_period_ns)
      .Signed("subscribe_delay_ns", s.subscribe_delay_ns)
      .Signed("subscribe_timeout_ns", s.subscribe_timeout_ns)
      .Signed("connect_timeout_ns", s.connect_timeout_ns)
      .Signed("connect_retry_period_ns", s.connect_retry_period_ns)
      .Text("listen", Ipv4ToText(options.listen_address) + ":" + std::to_string(options.listen_port))
      .Unsigned("max_payload_bytes", options.receiver.max_payload_bytes)
      .Text("discard_policy", policy_name)
      .Signed("phase_start_margin_ns", PhaseStartDiscardPolicy::kPhaseStartMarginNs)
      .Unsigned("copy_memory_frames", PhaseStartDiscardPolicy::kCopyMemoryFrames)
      .Text("announce_property", options.announce_property)
      .Signed("status_period_ns", options.status_period_ns)
      .Signed("client_write_timeout_ns", options.client_write_timeout_ns)
      .Bool("log_frames", options.receiver.log_frames);
  return record;
}

}  // namespace de4sdv::someip_receiver
