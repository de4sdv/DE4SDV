// The late subscriber's check (record_probe.h). C++17.
#include "record_probe.h"

#include <cstring>
#include <string>

#include "sha256.h"

namespace de4sdv::driver_assistance::identity {

namespace {

bool Terminated(const char* text, std::size_t capacity) { return std::memchr(text, '\0', capacity) != nullptr; }

}  // namespace

ProbeVerdict CheckReceivedRecord(const CandidateRecordEventPayload& payload, const FileSystem& fs) {
  ProbeVerdict v;
  if (!Terminated(payload.recordSha256, sizeof payload.recordSha256) ||
      !Terminated(payload.upstreamRevision, sizeof payload.upstreamRevision) ||
      !Terminated(payload.recordPath, sizeof payload.recordPath)) {
    v.reason = "a string of the event has no terminator";
    return v;
  }
  v.record_sha256 = payload.recordSha256;
  v.record_path = payload.recordPath;
  const std::string revision = payload.upstreamRevision;
  if (!IsLowerHex(v.record_sha256, 64) || !IsLowerHex(revision, 40) || payload.diffBytes == 0u ||
      v.record_path.empty()) {
    v.reason = "the event is not well formed";
    return v;
  }
  std::string bytes;
  if (!fs.ReadFile(v.record_path, &bytes)) {
    v.reason = "the record file " + v.record_path + " is not readable";
    return v;
  }
  if (Sha256Hex(bytes) != v.record_sha256) {
    v.reason = "the record file's SHA-256 differs from the event's";
    return v;
  }
  if (bytes.find("\"upstream_revision\":\"" + revision + "\"") == std::string::npos) {
    v.reason = "the record file names another upstream revision";
    return v;
  }
  if (bytes.find("\"source_difference\":{\"bytes\":" + std::to_string(payload.diffBytes) + ",") ==
      std::string::npos) {
    v.reason = "the record file gives another size of the difference";
    return v;
  }
  v.ok = true;
  return v;
}

}  // namespace de4sdv::driver_assistance::identity
