// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot). See core.hpp.
#include "de4sdv/score_interface/core.hpp"

#include <time.h>

#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

namespace de4sdv::score_interface {

namespace da = driver_assistance;

namespace {

constexpr double kPi = 3.14159265358979323846;

std::int64_t ClockNs(clockid_t id) {
  timespec ts{};
  clock_gettime(id, &ts);
  return static_cast<std::int64_t>(ts.tv_sec) * 1000000000LL + ts.tv_nsec;
}

// A double as the shortest text that reads back to the same value.
std::string Number(double v) {
  char buf[32];
  for (int precision = 15; precision <= 17; ++precision) {
    std::snprintf(buf, sizeof buf, "%.*g", precision, v);
    if (std::strtod(buf, nullptr) == v) break;
  }
  return buf;
}

bool TerminatedHex(const char* text, std::size_t capacity, std::size_t digits) {
  if (std::memchr(text, '\0', capacity) == nullptr) return false;
  if (std::strlen(text) != digits) return false;
  for (std::size_t i = 0; i < digits; ++i) {
    const char c = text[i];
    if (!((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f') || (c >= 'A' && c <= 'F'))) return false;
  }
  return true;
}

}  // namespace

std::int64_t MonotonicNs() { return ClockNs(CLOCK_MONOTONIC); }
std::int64_t RealtimeNs() { return ClockNs(CLOCK_REALTIME); }

bool ConvertBgraToBgr(const CameraImageView& image, std::uint8_t* dst, std::size_t dst_bytes) {
  if (image.bgra == nullptr || dst == nullptr || image.width <= 0 || image.height <= 0) return false;
  const std::size_t width = static_cast<std::size_t>(image.width);
  const std::size_t height = static_cast<std::size_t>(image.height);
  if (image.row_bytes < 4 * width) return false;
  if (dst_bytes < 3 * width * height) return false;
  for (std::size_t y = 0; y < height; ++y) {
    const std::uint8_t* s = image.bgra + y * image.row_bytes;
    std::uint8_t* d = dst + y * 3 * width;
    for (std::size_t x = 0; x < width; ++x, s += 4, d += 3) {
      d[0] = s[0];
      d[1] = s[1];
      d[2] = s[2];
    }
  }
  return true;
}

double SpeedOf(const EgoVelocity& v) { return std::sqrt(v.x * v.x + v.y * v.y + v.z * v.z); }

float SteeringAngleDegrees(double steering_rad) {
  return static_cast<float>(-steering_rad * 180.0 / kPi);  // MAP-DRIVING-DA-COMMAND
}

da::DrivingCommandEventPayload MakeDrivingCommand(double steering_rad, double acceleration, double issue_time_s,
                                                  std::uint32_t sequence_count) {
  da::DrivingCommandEventPayload p{};
  p.acceleration = static_cast<float>(acceleration);  // unchanged (MAP-DRIVING-DA-COMMAND)
  p.steeringAngle = SteeringAngleDegrees(steering_rad);
  p.issueTime = issue_time_s;
  p.sequenceCount = sequence_count;
  p.checkValue = da::DrivingCommandCheckValue(p);
  return p;
}

bool WellFormedCandidateRecord(const da::CandidateRecordEventPayload& r) {
  return TerminatedHex(r.recordSha256, sizeof r.recordSha256, 64) &&
         TerminatedHex(r.upstreamRevision, sizeof r.upstreamRevision, 40) && r.diffBytes > 0u &&
         std::memchr(r.recordPath, '\0', sizeof r.recordPath) != nullptr && r.recordPath[0] != '\0';
}

CandidateRecordGate::CandidateRecordGate(CandidateRecordSource* source, LineLog log)
    : source_(source), log_(std::move(log)) {}

bool CandidateRecordGate::Open() {
  if (open_) return true;
  da::CandidateRecordEventPayload record{};
  if (source_ == nullptr || !source_->TakeNewest(&record)) return false;
  const bool good = WellFormedCandidateRecord(record);
  if (!good) ++rejected_;
  if (log_) {
    // Only the well-formed record's strings are printed; a malformed one may lack its terminator.
    std::string line = "{\"kind\":\"in.candidate_record\",\"accepted\":";
    line += good ? "true" : "false";
    if (good) {
      line += ",\"recordSha256\":\"" + std::string(record.recordSha256) + "\",\"upstreamRevision\":\"" +
              std::string(record.upstreamRevision) + "\",\"diffBytes\":" + std::to_string(record.diffBytes);
    }
    line += ",\"mono_ns\":" + std::to_string(MonotonicNs()) + ",\"real_ns\":" + std::to_string(RealtimeNs()) + "}";
    log_(line);
  }
  open_ = good;
  return open_;
}

DrivingCommandWriter::DrivingCommandWriter(DrivingCommandSink* sink, CandidateRecordGate* gate,
                                           const PassClock* clock, LineLog log)
    : sink_(sink), gate_(gate), clock_(clock), log_(std::move(log)) {}

bool DrivingCommandWriter::Write(double steering_rad, double acceleration) {
  if (!gate_->Open()) {  // REQ-DRIVING-044: nothing before the record has arrived
    ++counters_.withheld_before_record;
    return false;
  }
  if (!clock_->valid) {
    ++counters_.withheld_without_capture_time;
    return false;
  }
  const da::DrivingCommandEventPayload p =
      MakeDrivingCommand(steering_rad, acceleration, clock_->capture_time_s, ++last_sequence_);
  const bool sent = sink_->Send(p);
  if (sent) {
    ++counters_.sent;
  } else {
    ++counters_.send_failed;
  }
  if (log_) {
    char crc[11];
    std::snprintf(crc, sizeof crc, "0x%08x", p.checkValue);
    log_(std::string("{\"kind\":\"out.driving_command\",\"seq\":") + std::to_string(p.sequenceCount) +
         ",\"crc\":\"" + crc + "\",\"issueTime_sim_s\":" + Number(p.issueTime) +
         ",\"frame\":" + std::to_string(clock_->frame) + ",\"acceleration\":" + Number(p.acceleration) +
         ",\"steeringAngle_deg\":" + Number(p.steeringAngle) + ",\"sent\":" + (sent ? "true" : "false") +
         ",\"mono_ns\":" + std::to_string(MonotonicNs()) + ",\"real_ns\":" + std::to_string(RealtimeNs()) + "}");
  }
  return sent;
}

WarningRequestWriter::WarningRequestWriter(WarningRequestSink* sink, const PassClock* clock, LineLog log)
    : sink_(sink), clock_(clock), log_(std::move(log)) {}

bool WarningRequestWriter::Write(bool requested) {
  std::uint8_t bytes[da::kWarningRequestSomeipSize];
  if (!clock_->valid || !da::EncodeWarningRequestSomeip({requested, clock_->capture_time_s}, bytes)) {
    ++counters_.not_encodable;
    return false;
  }
  const bool sent = sink_->Send(bytes, sizeof bytes);
  if (sent) {
    ++counters_.sent;
    if (requested) ++counters_.requested;
  } else {
    ++counters_.send_failed;
  }
  if (log_) {
    char hex[2 * sizeof bytes + 1];
    for (std::size_t i = 0; i < sizeof bytes; ++i) std::snprintf(hex + 2 * i, 3, "%02x", bytes[i]);
    log_(std::string("{\"kind\":\"out.warning_request\",\"requested\":") + (requested ? "true" : "false") +
         ",\"issueTime_sim_s\":" + Number(clock_->capture_time_s) + ",\"frame\":" + std::to_string(clock_->frame) +
         ",\"bytes\":\"" + hex + "\",\"sent\":" + (sent ? "true" : "false") +
         ",\"mono_ns\":" + std::to_string(MonotonicNs()) + ",\"real_ns\":" + std::to_string(RealtimeNs()) + "}");
  }
  return sent;
}

}  // namespace de4sdv::score_interface
