// DE4SDV driver-assistance bench (INC-DRIVING-002): payloads on the Eclipse
// S-CORE path. Document: ../../../ICD.md.
//
// The model is the authority: the signal mappings MAP-DRIVING-DA-COMMAND,
// MAP-DRIVING-DA-WARNING-REQUEST and MAP-DRIVING-DA-CANDIDATE-RECORD in
// textual-notation-of-model/packages/features/driving/
// driver_assistance_physical_software_realization.sysml. The ids, the CRC
// variant and the byte layouts below are bench proposals where the model
// leaves them open; ICD.md marks each one.
#pragma once

#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <type_traits>

namespace de4sdv::driver_assistance {

// CRC-32 as in IEEE 802.3 and zlib's crc32: reflected polynomial 0xEDB88320,
// initial value 0xFFFFFFFF, final XOR 0xFFFFFFFF ("123456789" -> 0xCBF43926).
inline std::uint32_t Crc32(const std::uint8_t* data, std::size_t size) {
  std::uint32_t crc = 0xFFFFFFFFu;
  for (std::size_t i = 0; i < size; ++i) {
    crc ^= data[i];
    for (int bit = 0; bit < 8; ++bit) {
      crc = (crc >> 1) ^ (0xEDB88320u & (0u - (crc & 1u)));
    }
  }
  return crc ^ 0xFFFFFFFFu;
}

// MAP-DRIVING-DA-COMMAND: one event per command, from the candidate's
// vehicle interface to the actuation adapter.
struct DrivingCommandEventPayload {
  float acceleration;           // m/s^2, negative decelerates
  float steeringAngle;          // degrees, positive to the left
  double issueTime;             // simulation s: capture time of the frame
  std::uint32_t sequenceCount;  // from 1 in each run
  std::uint32_t checkValue;     // DrivingCommandCheckValue() of the above
};
static_assert(std::is_standard_layout_v<DrivingCommandEventPayload>);
static_assert(std::is_trivially_copyable_v<DrivingCommandEventPayload>);
static_assert(sizeof(DrivingCommandEventPayload) == 24);
static_assert(offsetof(DrivingCommandEventPayload, steeringAngle) == 4);
static_assert(offsetof(DrivingCommandEventPayload, issueTime) == 8);
static_assert(offsetof(DrivingCommandEventPayload, sequenceCount) == 16);
static_assert(offsetof(DrivingCommandEventPayload, checkValue) == 20);

namespace detail {
inline void PutLe32(std::uint8_t* out, std::uint32_t v) {
  for (int i = 0; i < 4; ++i) out[i] = static_cast<std::uint8_t>(v >> (8 * i));
}
inline void PutLe64(std::uint8_t* out, std::uint64_t v) {
  for (int i = 0; i < 8; ++i) out[i] = static_cast<std::uint8_t>(v >> (8 * i));
}
inline void PutBe32(std::uint8_t* out, std::uint32_t v) {
  for (int i = 0; i < 4; ++i) {
    out[i] = static_cast<std::uint8_t>(v >> (8 * (3 - i)));
  }
}
}  // namespace detail

// The check value covers the little-endian bytes of acceleration,
// steeringAngle, issueTime and sequenceCount, in this order (20 bytes),
// whatever the byte order of the host.
inline std::uint32_t DrivingCommandCheckValue(
    const DrivingCommandEventPayload& p) {
  std::uint8_t bytes[20];
  std::uint32_t a = 0;
  std::uint32_t s = 0;
  std::uint64_t t = 0;
  std::memcpy(&a, &p.acceleration, sizeof a);
  std::memcpy(&s, &p.steeringAngle, sizeof s);
  std::memcpy(&t, &p.issueTime, sizeof t);
  detail::PutLe32(bytes, a);
  detail::PutLe32(bytes + 4, s);
  detail::PutLe64(bytes + 8, t);
  detail::PutLe32(bytes + 16, p.sequenceCount);
  return Crc32(bytes, sizeof bytes);
}

// MAP-DRIVING-DA-WARNING-REQUEST: one event per plan. requested is true when
// the plan's warnings hold FCW or AEB; issueTime is the capture simulation
// time of the frame the plan was computed from.
struct WarningRequest {
  bool requested;
  double issueTime;  // simulation s
};

// The SOME/IP payload of the warning request (service 0x4df1, event 0x8001):
// big-endian, no length field: requested UINT32 (0 or 1), issue_time_sim_ms
// UINT32. The candidate's mw::com event carries these 8 bytes as they are;
// gatewayd copies them unread.
inline constexpr std::size_t kWarningRequestSomeipSize = 8;

// Returns false, and writes nothing, when the issue time cannot be carried
// as whole milliseconds in 32 bits (negative, not finite, or too large).
inline bool EncodeWarningRequestSomeip(const WarningRequest& w,
                                       std::uint8_t out[8]) {
  if (!std::isfinite(w.issueTime) || w.issueTime < 0.0) return false;
  const double ms = std::round(w.issueTime * 1000.0);
  if (ms > 4294967295.0) return false;
  detail::PutBe32(out, w.requested ? 1u : 0u);
  detail::PutBe32(out + 4, static_cast<std::uint32_t>(ms));
  return true;
}

// MAP-DRIVING-DA-CANDIDATE-RECORD: the event that tells the vehicle interface
// that the record of the run exists. The record itself is the JSON file at
// recordPath; recordSha256 is its SHA-256. Strings are NUL-terminated.
struct CandidateRecordEventPayload {
  char recordSha256[65];      // 64 hex digits
  char upstreamRevision[41];  // 40 hex digits
  std::uint32_t diffBytes;    // size of the source difference, never 0
  char recordPath[256];
};
static_assert(std::is_standard_layout_v<CandidateRecordEventPayload>);
static_assert(std::is_trivially_copyable_v<CandidateRecordEventPayload>);
static_assert(sizeof(CandidateRecordEventPayload) == 368);

}  // namespace de4sdv::driver_assistance
