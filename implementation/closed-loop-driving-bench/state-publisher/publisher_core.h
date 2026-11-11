// DE4SDV INC-DRIVING-001 slice 10b, S1: the operational-state publisher's
// logic, pure C++17 with no S-CORE dependency (the shell in
// state_publisher_main.cpp only moves bytes and logs). Interface Control
// Document: ../../interfaces/ICD.md, section 3 (the message), section 6 (logs).
//
// The publisher is fed typed inputs with their receipt time on the host's
// CLOCK_MONOTONIC and is ticked with the current monotonic time. It emits
// frames in the layout of the P4 probe: bytes 0-3 little-endian message length
// (bytes 0-1 carry it), the ICD v2 section 3 SOME/IP struct from byte 4 (43
// fields, table order, big-endian, AUTOSAR strings and dynamic float arrays).
// The shell sends the struct alone: data[0..size) = bytes 4.., size =
// messageBytes (ICD section 2, A33); the vectors keep the whole frame.
//
// Rules implemented here (ICD section 3, REQ-DRIVING-015 to -019, -029):
//   * one PLAN frame per plan, at once;
//   * one VEHICLE_STATE frame per ego-motion sample, at once, carrying the
//     sample's receipt time on the monotonic clock;
//   * one HEALTH frame every 100 ms of monotonic time regardless of inputs,
//     and one immediately when a stop enters (a mode of kStopResponse,
//     kStandstill or kRefused from the agent, or stopInForce from the
//     actuation adapter), with the source that named it; the stop latches for
//     the rest of the run and the first cause wins;
//   * per-kind sequence numbers from 1 without gaps (ICD 3); a frame that
//     cannot be built consumes no sequence number;
//   * a message over message_capacity_bytes (2044 by default) is dropped and
//     counted in dropped_samples.
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <string_view>
#include <vector>

#include "de4sdv/driving/payloads.h"

namespace de4sdv::driving::publisher {

// ---------------------------------------------------------------- constants
inline constexpr std::size_t kFrameBytes = 2048;                 // PreSerializedData<2048>
inline constexpr std::size_t kMaxMessageBytes = kFrameBytes - 4;  // 2044, ICD section 2
inline constexpr double kHealthPeriodSeconds = 0.1;              // 100 ms, ICD section 3
inline constexpr std::uint32_t kSchemaMajor = 2;                 // ICD section 3, field 1
inline constexpr std::uint32_t kSchemaMinor = 0;                 // ICD section 3, field 2
inline constexpr const char* kDefaultProducer = "statePublisher";
// The refusal detail strings of fields 41-43: 64 hex characters for the two
// SHA-256 values, a short token for the reason ("mismatch", "no_pin", "").
inline constexpr std::size_t kRefusalShaLength = 64;
inline constexpr std::size_t kRefusalReasonLength = 32;

// The Kind enum of the ICD's struct (field 3).
enum class Kind : std::uint32_t {
  kUnspecified = 0,
  kPlan = 1,
  kVehicleState = 2,
  kHealth = 3,
};

// The three mw::com events of the operational-state skeleton.
enum class Port : std::uint32_t {
  kPlan = 0,
  kVehicleState = 1,
  kHealth = 2,
};

const char* KindName(Kind kind);       // "PLAN", "VEHICLE_STATE", "HEALTH"
const char* ModeName(Mode mode);       // "kStopResponse", ...
const char* CauseName(Cause cause);    // "kCommandTimeout", ...
const char* PortName(Port port);       // "plan", "vehicle_state", "health"

// ------------------------------------------------------------ time splitting
// Seconds on a host clock -> the ICD's (u32 seconds, u32 nanoseconds) pair.
// The nanoseconds are rounded from the double (llround(x * 1e9)) and the carry
// lands in the seconds, so .9999999996 s is (1, 0) and nanoseconds are always
// in [0, 999999999]. Non-positive or non-finite input is (0, 0); a time past
// 2^32-1 s saturates.
struct TimeSplit {
  std::uint32_t seconds = 0;
  std::uint32_t nanos = 0;
};
TimeSplit SplitSeconds(double seconds);
// The same split of an exact nanosecond count. Real time is built as
// mono_ns + offset_ns in integers (the offset is fixed by chrony), so the
// nanoseconds do not wobble with the ~238 ns resolution of a double at 1.7e9 s.
TimeSplit SplitNanos(std::int64_t totalNanos);

// Simulation milliseconds: llround(seconds * 1000), saturating at 2^32-1,
// 0 for non-positive or non-finite input. ICD section 1: simulation time is
// the frame index x 100 ms; this conversion is used only where the payload has
// no frame index (ego-motion samples), and to cross-check a plan's capture time
// against its frame index.
std::uint32_t SimulationMs(double seconds);

// ------------------------------------------------------------------- frames
// One ready-to-send frame in the PreSerializedData<2048> layout, with the
// metadata the shell needs to send and log it. Never returned with size == 0:
// a message that cannot be built is dropped and counted instead.
struct Frame {
  Kind kind = Kind::kUnspecified;
  Port port = Port::kPlan;
  std::uint64_t sequence = 0;    // per kind, from 1, no gaps
  std::uint32_t messageBytes = 0;  // value of the length prefix
  std::uint32_t size = 0;          // 4 + messageBytes (the sample sent carries messageBytes)
  std::uint8_t bytes[kFrameBytes] = {};  // prefix in 0-3, struct from 4
  // The record data of ICD section 6 for the out.operational_state crossing:
  // the wire fields (enums by name), every time field suffixed with its clock.
  std::string logDataJson;
};

// One JSONL record the shell writes with run_log.h apart from the frames:
// stop_response.begin, stop_response.standstill, drop, error.
struct LogRecord {
  std::string event;
  std::uint64_t seq = 0;
  std::string dataJson;
};

struct Options {
  std::string producer = kDefaultProducer;
  // Capacity of the struct message. The contract value is kMaxMessageBytes
  // (2044). Tests lower it to exercise the oversize path, which no well-formed
  // payload of the ICD can reach.
  std::size_t messageCapacityBytes = kMaxMessageBytes;
};

// -------------------------------------------------------------- the publisher
class PublisherCore {
 public:
  explicit PublisherCore(Options options = Options{});

  // Sets the offset between the host's monotonic clock and CLOCK_REALTIME
  // (chrony keeps it constant): real = mono + offset. The shell calls this
  // once after start-up; the logic library itself reads no clock.
  void SetRealTimeAtMono(double monoSeconds, double realSeconds);
  double RealOffsetSeconds() const { return static_cast<double>(realOffsetNanos_) / 1e9; }
  std::int64_t RealOffsetNanos() const { return realOffsetNanos_; }

  // Inputs. `receiptMono` is the monotonic time at which this process received
  // the sample. Every call returns the frames to send, in emission order; the
  // first call of any kind also emits the priming health.
  std::vector<Frame> OnPlan(const DrivingPlanPayload& plan, double receiptMono);
  std::vector<Frame> OnEgoMotionSample(const EgoMotionSamplePayload& sample, double receiptMono);
  std::vector<Frame> OnMode(const DrivingModePayload& mode, double receiptMono);
  std::vector<Frame> OnActuationState(const ActuationStatePayload& state, double receiptMono);

  // Time step: emits the due health publications.
  std::vector<Frame> Tick(double nowMono);

  // The checkpoint-identity refusal detail of HEALTH fields 41-43
  // (REQ-DRIVING-035). A setter only: the detail rides the next health
  // publication (at most 100 ms later, or the immediate health of the kRefused
  // stop). Call it as soon as the refusal is known.
  void SetRefusal(std::string_view expectedSha, std::string_view actualSha,
                  std::string_view reason);

  // Non-frame log records produced so far (stop_response.*, drop, error).
  std::vector<LogRecord> DrainLog();

  // A frame the shell could not hand to mw::com (Allocate or Send failed).
  // Counts as a publisher-side drop and is logged.
  void NoteDownstreamDrop(std::string_view reason);

  // ---------------------------------------------------------------- state
  std::uint64_t Sequence(Kind kind) const;
  std::uint64_t DroppedSamples() const { return droppedSamples_; }
  bool StopLatched() const { return stopLatched_; }
  Mode ReportedMode() const;
  Cause ReportedCause() const;
  std::string_view ReportedModeSource() const;
  std::uint64_t LastPlanFrameIndex() const { return lastPlanFrameIndex_; }
  std::uint32_t LastPlanCaptureMs() const { return lastPlanCaptureMs_; }
  std::uint32_t StepCaptureMs() const { return stepCaptureMs_; }
  double LastPlanProductionMono() const { return lastPlanProductionMono_; }
  bool RefusalSet() const { return !refusalReason_.empty(); }
  double NextHealthMono() const { return nextHealthMono_; }

 private:
  struct Header {
    Kind kind = Kind::kUnspecified;
    std::uint64_t sequence = 0;
    TimeSplit publishReal;
    TimeSplit publishMono;
    std::int64_t publishRealNs = 0;
    std::int64_t publishMonoNs = 0;
  };

  Header MakeHeader(Kind kind, std::uint64_t sequence, double nowMono) const;
  void EnsureStarted(double nowMono, std::vector<Frame>& frames);
  Frame EmitHealth(double nowMono);
  void CommitFrame(Frame& frame, const std::uint8_t* message, std::size_t length);
  void NoteDrop(std::string_view reason, Kind kind);
  // ICD section 1: a plan's simulation ms is its frame index x 100, exactly.
  // The capture time must agree; a disagreement is logged once, not per plan.
  std::uint32_t CheckPlanCaptureMs(const DrivingPlanPayload& plan);

  Options options_;
  std::int64_t realOffsetNanos_ = 0;

  bool started_ = false;
  double nextHealthMono_ = 0.0;

  std::uint64_t sequence_[4] = {0, 0, 0, 0};  // indexed by Kind
  std::uint64_t droppedSamples_ = 0;

  bool haveMode_ = false;
  Mode lastMode_ = Mode::kStarting;
  Cause lastCause_ = Cause::kNone;

  bool stopLatched_ = false;
  Mode stopMode_ = Mode::kStopResponse;
  Cause stopCause_ = Cause::kNone;
  std::string stopSource_;
  double causeSinceMono_ = 0.0;
  bool standstillLogged_ = false;

  std::uint64_t lastPlanFrameIndex_ = 0;
  std::uint32_t lastPlanCaptureMs_ = 0;       // HEALTH 36
  std::uint32_t stepCaptureMs_ = 0;           // HEALTH 37, newest step seen
  double lastPlanProductionMono_ = 0.0;       // HEALTH 38-39

  std::string refusalExpected_;               // HEALTH 41
  std::string refusalActual_;                 // HEALTH 42
  std::string refusalReason_;                 // HEALTH 43

  bool captureMismatchLogged_ = false;

  std::vector<LogRecord> log_;
};

// --------------------------------------------------- log payload formatting
// The ICD section 6 payload objects of the inbound crossings, built here so the
// shell carries no formatting decisions. Enums go out by name, floats as JSON
// numbers (non-finite as null). Payload time fields keep their model names and
// a sibling `clocks` object names each one's clock and unit; the times this
// process stamps itself carry the suffix (_mono_ns, _real_ns, _sim_ms).
namespace logjson {
std::string Plan(const DrivingPlanPayload& plan, double receiptMono);
std::string EgoMotionSample(const EgoMotionSamplePayload& sample, double receiptMono);
std::string ModeEvent(const DrivingModePayload& mode, double receiptMono);
std::string ActuationState(const ActuationStatePayload& state, double receiptMono);
}  // namespace logjson

}  // namespace de4sdv::driving::publisher
