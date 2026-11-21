// DE4SDV driver-assistance bench (INC-DRIVING-002): one JSONL line per record.
//
// The record format of the closed-loop driving bench (its ICD section 6 and
// interfaces/include/de4sdv/driving/run_log.h): every record has t_mono_ns,
// t_real_ns, host, component, event, seq and data. This copy keeps that format
// so the bench's evaluators read both benches alike; it lives here because the
// driver-assistance interface folder has no log header.
//
// Header-only, thread-safe, line-flushed. C++17 and POSIX clock_gettime.
#pragma once

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <ctime>
#include <mutex>
#include <string>

namespace de4sdv::driver_assistance {

inline std::int64_t NowNs(clockid_t clock) {
  timespec ts{};
  clock_gettime(clock, &ts);
  return static_cast<std::int64_t>(ts.tv_sec) * 1000000000LL + ts.tv_nsec;
}
inline double MonotonicSeconds() { return static_cast<double>(NowNs(CLOCK_MONOTONIC)) / 1e9; }

// Escapes a string for JSON.
inline std::string JsonString(const std::string& s) {
  std::string out = "\"";
  for (unsigned char c : s) {
    switch (c) {
      case '"': out += "\\\""; break;
      case '\\': out += "\\\\"; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default:
        if (c < 0x20) {
          char b[8];
          std::snprintf(b, sizeof b, "\\u%04x", c);
          out += b;
        } else {
          out += static_cast<char>(c);
        }
    }
  }
  return out + "\"";
}

// JSON number; non-finite values become null (JSON has no NaN).
inline std::string JsonNumber(double v) {
  if (!std::isfinite(v)) return "null";
  char b[40];
  std::snprintf(b, sizeof b, "%.17g", v);
  return b;
}

// Where the shell's records go. The run's file in the shell, a capture in the
// tests.
class RecordSink {
 public:
  virtual ~RecordSink() = default;
  // data_json must be a complete JSON object, built by the caller.
  virtual void Write(const std::string& event, std::uint64_t seq, const std::string& data_json) = 0;
};

class RunLog : public RecordSink {
 public:
  RunLog(const std::string& path, std::string host, std::string component)
      : host_(std::move(host)), component_(std::move(component)) {
    file_ = std::fopen(path.c_str(), "a");
  }
  ~RunLog() override {
    if (file_) std::fclose(file_);
  }
  RunLog(const RunLog&) = delete;
  RunLog& operator=(const RunLog&) = delete;
  bool ok() const { return file_ != nullptr; }

  void Write(const std::string& event, std::uint64_t seq, const std::string& data_json) override {
    const std::int64_t mono = NowNs(CLOCK_MONOTONIC);
    const std::int64_t real = NowNs(CLOCK_REALTIME);
    std::lock_guard<std::mutex> lock(mutex_);
    if (!file_) return;
    std::fprintf(file_,
                 "{\"t_mono_ns\":%lld,\"t_real_ns\":%lld,\"host\":%s,\"component\":%s,"
                 "\"event\":%s,\"seq\":%llu,\"data\":%s}\n",
                 static_cast<long long>(mono), static_cast<long long>(real),
                 JsonString(host_).c_str(), JsonString(component_).c_str(),
                 JsonString(event).c_str(), static_cast<unsigned long long>(seq),
                 data_json.empty() ? "{}" : data_json.c_str());
    std::fflush(file_);
  }

 private:
  std::string host_;
  std::string component_;
  std::FILE* file_ = nullptr;
  std::mutex mutex_;
};

}  // namespace de4sdv::driver_assistance
