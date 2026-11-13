// Pure core of the DE4SDV IVI frame relay: structured log events.
//
// The core reports what it does as named events with typed fields; the
// shell writes each event as one JSON object per line,
// {"monotonic_ns":..,"realtime_ns":..,"event":..,...}, on stdout (Linux)
// or to liblog with the tag de4sdv_ivi_frame_relay (Android). The clocks of a
// line are those of the moment the event happened, also when the gateway
// thread saw it and the main thread logs it later.

#ifndef DE4SDV_IVI_FRAME_RELAY_EVENT_LOG_HPP
#define DE4SDV_IVI_FRAME_RELAY_EVENT_LOG_HPP

#include <cstdint>
#include <string>
#include <utility>

namespace de4sdv::ivi_frame_relay {

// Both clocks of one moment: CLOCK_MONOTONIC for timers and delays,
// CLOCK_REALTIME for the comparison with frame_timestamp_ns.
struct Clock {
  std::int64_t monotonic_ns{0};
  std::int64_t realtime_ns{0};
};

class LogRecord {
 public:
  explicit LogRecord(std::string event) : event_{std::move(event)} {}

  LogRecord& Text(const char* key, const std::string& value);
  LogRecord& Unsigned(const char* key, std::uint64_t value);
  LogRecord& Signed(const char* key, std::int64_t value);
  LogRecord& Bool(const char* key, bool value);

  const std::string& event() const noexcept { return event_; }
  // The fields as "key":value pairs, comma-separated, without braces.
  const std::string& fields() const noexcept { return fields_; }
  // The whole line without the clock fields' values: {"event":..,...}
  std::string ToJson(const Clock& now) const;

 private:
  void Key(const char* key);

  std::string event_;
  std::string fields_;
};

std::string JsonQuote(const std::string& text);

class EventLog {
 public:
  virtual ~EventLog() = default;
  virtual void Log(const Clock& now, const LogRecord& record) = 0;
};

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_EVENT_LOG_HPP
