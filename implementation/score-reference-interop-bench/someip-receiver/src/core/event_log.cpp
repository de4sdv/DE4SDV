#include "de4sdv_someip_receiver/event_log.hpp"

#include <cstdio>

namespace de4sdv::someip_receiver {

std::string JsonQuote(const std::string& text) {
  std::string out;
  out.reserve(text.size() + 2);
  out += '"';
  for (const char c : text) {
    switch (c) {
      case '"':
        out += "\\\"";
        break;
      case '\\':
        out += "\\\\";
        break;
      case '\n':
        out += "\\n";
        break;
      default:
        if (static_cast<unsigned char>(c) < 0x20U) {
          char escaped[8];
          std::snprintf(escaped, sizeof(escaped), "\\u%04x", static_cast<unsigned>(static_cast<unsigned char>(c)));
          out += escaped;
        } else {
          out += c;
        }
    }
  }
  out += '"';
  return out;
}

void LogRecord::Key(const char* key) {
  if (!fields_.empty()) {
    fields_ += ',';
  }
  fields_ += JsonQuote(key);
  fields_ += ':';
}

LogRecord& LogRecord::Text(const char* key, const std::string& value) {
  Key(key);
  fields_ += JsonQuote(value);
  return *this;
}

LogRecord& LogRecord::Unsigned(const char* key, std::uint64_t value) {
  Key(key);
  fields_ += std::to_string(value);
  return *this;
}

LogRecord& LogRecord::Signed(const char* key, std::int64_t value) {
  Key(key);
  fields_ += std::to_string(value);
  return *this;
}

LogRecord& LogRecord::Bool(const char* key, bool value) {
  Key(key);
  fields_ += value ? "true" : "false";
  return *this;
}

std::string LogRecord::ToJson(const Clock& now) const {
  std::string line = "{\"monotonic_ns\":" + std::to_string(now.monotonic_ns) +
                     ",\"realtime_ns\":" + std::to_string(now.realtime_ns) + ",\"event\":" + JsonQuote(event_);
  if (!fields_.empty()) {
    line += ',';
    line += fields_;
  }
  line += '}';
  return line;
}

}  // namespace de4sdv::someip_receiver
