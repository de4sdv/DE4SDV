// DE4SDV INC-DRIVING-001 slice 10b: the payloads of the S-CORE contract on the
// S-CORE host (mw::com events) and the route channel. Interface Control
// Document: ../../ICD.md. Every struct is standard-layout and trivially
// copyable (mw::com LoLa places samples in shared memory: no pointers, no
// std::string, fixed arrays only).
#pragma once

#include <cstddef>
#include <cstdint>
#include <type_traits>

namespace de4sdv::driving {

inline constexpr std::uint32_t kInterfaceVersion = 2;  // ICD v2 (2026-11-09)
inline constexpr std::size_t kPlanSamples = 64;     // REQ-DRIVING-027: 64 pairs
inline constexpr std::size_t kIdLength = 64;        // NUL-terminated, truncated
inline constexpr double kStepSeconds = 0.1;         // one step = 100 ms of simulation time
inline constexpr std::int64_t kStepMicros = 100000;

// Simulation time of a frame: frame index x 100 ms, exact in microseconds
// (bench rule of 2026-11-09: never the simulator's float stamp).
constexpr std::int64_t CaptureTimeMicros(std::uint64_t frame_index) {
  return static_cast<std::int64_t>(frame_index) * kStepMicros;
}

// ---------------------------------------------------------------- causes, modes
enum class Mode : std::uint8_t {
  kStarting = 0,      // before the first valid plan (run identity, warm-up, parity)
  kDriving = 1,
  kStopResponse = 2,  // REQ-DRIVING-020/-021: -4 m/s^2, steering held
  kStandstill = 3,    // REQ-DRIVING-022: held until the run ends
  kRefused = 4,       // REQ-DRIVING-035: checkpoint identity refused, no plan ever
};

enum class Cause : std::uint8_t {
  kNone = 0,
  kCameraMissing = 1,      // REQ-DRIVING-023
  kCameraInvalid = 2,      // REQ-DRIVING-023
  kCameraStale = 3,        // REQ-DRIVING-023: captured > 200 ms sim before the step
  kMotionInvalid = 4,      // REQ-DRIVING-024
  kMotionStale = 5,        // REQ-DRIVING-024: > 200 ms sim old
  kRouteStale = 6,         // REQ-DRIVING-025: > 1 s sim old
  kRouteEmpty = 7,         // REQ-DRIVING-025: no route corridor
  kPlanStale = 8,          // REQ-DRIVING-026: > 300 ms sim old at a command
  kPlanInvalid = 9,        // REQ-DRIVING-027: not 64 finite pairs
  kCommandTimeout = 10,    // REQ-DRIVING-028: at the actuation, 200 ms sim without a valid command
  kCheckpointRefused = 11, // REQ-DRIVING-035
  kRunEnd = 12,            // orderly end of a run (not a fault)
};

// ---------------------------------------------------------------- payloads
// MAP-DRIVING-EGO-MOTION, exact fields. VSS units: km/h, m/s^2, deg/s.
struct EgoMotionSamplePayload {
  float speed;                     // Vehicle.Speed, km/h
  float longitudinalAcceleration;  // Vehicle.Acceleration.Longitudinal, m/s^2
  float lateralAcceleration;       // Vehicle.Acceleration.Lateral, m/s^2
  float yawRate;                   // Vehicle.AngularVelocity.Yaw, deg/s
  double captureTime;              // simulation seconds = CaptureTimeMicros(frame)/1e6
};

// One plan sample: the output head's pair (exact, REQ-DRIVING-027) and the
// pose integrated from it (derived, ego frame at the capture time; x forward,
// y left, heading counter-clockwise).
struct PlanSample {
  float acceleration;  // m/s^2
  float curvature;     // 1/m, positive to the left
  float x;             // m
  float y;             // m
  float heading;       // rad
};

// MAP-DRIVING-PLAN (candidate fields). REQ-DRIVING-031: the capture time of
// its newest camera image (simulation) and its production time on the
// monotonic clock of the host. REQ-DRIVING-034: the run record it names.
struct DrivingPlanPayload {
  std::uint64_t frameIndex;          // the step it was planned from
  double captureTime;                // simulation seconds of the newest camera image
  double productionTime;             // CLOCK_MONOTONIC seconds of the S-CORE host
  float horizon;                     // seconds covered by the samples
  std::uint32_t sampleCount;         // kPlanSamples when well-formed
  PlanSample samples[kPlanSamples];
  char producer[kIdLength];          // "drivingAgent/inferPlan"
  char runRecord[kIdLength];         // run record identity (sha256 prefix of the run record)
  char planReference[kIdLength];     // "<runRecord>/<frameIndex>"
};

// MAP-DRIVING-MODE. Decision time on the monotonic clock of the host.
struct DrivingModePayload {
  Mode mode;
  Cause cause;
  std::uint8_t reserved[6];
  std::uint64_t frameIndex;   // the step the decision was made at
  double captureTime;         // simulation seconds of that step
  double decisionTime;        // CLOCK_MONOTONIC seconds
  // ICD v2 amendment 1 (A5): the checkpoint refusal detail of REQ-DRIVING-035,
  // carried to statePublisher for HEALTH fields 41-43. Zero-filled unless
  // mode == kRefused.
  char checkpointExpectedSha256[kIdLength];  // 64 hex characters, no NUL
  char checkpointActualSha256[kIdLength];    // 64 hex characters, no NUL
  char refusalReason[16];                    // "mismatch", "no_pin" or empty, NUL-padded
};

// MAP-DRIVING-COMMAND, exact fields; the two commanded quantities are
// DE4SDV_VSS_Extensions candidates. steeringAngle = front road-wheel angle,
// degrees, positive to the left. REQ-DRIVING-032: issue time on the monotonic
// clock of the host; the actuation time is the adapter's (ActuationState).
struct VehicleMotionCommandPayload {
  float acceleration;          // m/s^2, negative decelerates
  float steeringAngle;         // degrees, positive left
  double productionTime;       // CLOCK_MONOTONIC seconds (issue time)
  char planReference[kIdLength];
};

// MAP-DRIVING-ACTUATION-STATE (candidate fields). Times in simulation seconds.
struct ActuationStatePayload {
  std::uint8_t applied;        // 1: this sample reports an applied command
  std::uint8_t stopInForce;    // 1: the adapter's stop response is in force
  Cause cause;                 // kCommandTimeout when the adapter stopped by itself
  std::uint8_t reserved[5];
  float acceleration;          // the applied command's m/s^2 (or -4 in the stop)
  float steeringAngle;         // the applied command's degrees (held in the stop)
  double actuationTime;        // simulation seconds of the world snapshot at application
  double stopSince;            // simulation seconds; 0 when no stop is in force
  char planReference[kIdLength];
  double stopSinceMono;        // ICD v2: CLOCK_MONOTONIC seconds of the S-CORE host when the stop began; 0 if none
};

// Route channel (route provider -> input activity; not S-CORE, local UDP
// 127.0.0.1:47110, one datagram per publication). The route content is fixed
// per run; the provider republishes it every 500 ms of simulation time so the
// input activity can judge its age (REQ-DRIVING-025). Waypoints are in the
// file the header names (map frame, metres/radians); the datagram carries the
// identity and the time, or corridorPoints = 0 for "no route corridor".
struct RouteAnnouncement {
  std::uint32_t version;       // kInterfaceVersion
  std::uint32_t corridorPoints;
  double issueTime;            // simulation seconds of the provider's newest world tick
  char routeFile[192];         // absolute path of the route JSON on the S-CORE host
  char routeSha256[kIdLength]; // exactly 64 hex characters of the file's SHA-256, NO terminating NUL (ICD v2 §9)
};

static_assert(std::is_standard_layout_v<DrivingPlanPayload> && std::is_trivially_copyable_v<DrivingPlanPayload>);
static_assert(std::is_standard_layout_v<DrivingModePayload> && std::is_trivially_copyable_v<DrivingModePayload>);
static_assert(std::is_standard_layout_v<EgoMotionSamplePayload> && std::is_trivially_copyable_v<EgoMotionSamplePayload>);
static_assert(std::is_standard_layout_v<VehicleMotionCommandPayload> && std::is_trivially_copyable_v<VehicleMotionCommandPayload>);
static_assert(std::is_standard_layout_v<ActuationStatePayload> && std::is_trivially_copyable_v<ActuationStatePayload>);
static_assert(std::is_standard_layout_v<RouteAnnouncement> && std::is_trivially_copyable_v<RouteAnnouncement>);

}  // namespace de4sdv::driving
