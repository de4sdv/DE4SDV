// DE4SDV closed-loop driving bench, slice 10b: actuation adapter logic core.
//
// Pure C++17, no simulator, middleware or clock dependency. The S-CORE shell
// (actuation_adapter_main.cpp) feeds it the two inputs and applies what it
// returns:
//
//   OnCommand()    a VehicleMotionCommandPayload arrived on mw::com at a
//                  CLOCK_MONOTONIC time (the arrival time, same host);
//   OnWorldTick()  a CARLA world snapshot: frame index, ego speed (m/s) and
//                  longitudinal acceleration (m/s^2).
//
// Both return an ActuationOutput: the VehicleControlCommand to apply now (if
// any), the ActuationStatePayload to publish (if any) and the bookkeeping the
// shell logs. The class is internally synchronised: OnCommand may run on the
// mw::com receive thread and OnWorldTick on the CARLA callback thread.
//
// Rules (ICD sections 4 and 5, requirements REQ-DRIVING-012, -014, -020 to
// -022, -028, -032):
//
//  * A command is valid when both values are finite and inside the configured
//    limits, planReference is non-empty and its productionTime is between
//    5 ms in the future and 300 ms old at arrival (-5 ms <= age <= 300 ms of
//    monotonic time). An invalid command changes nothing and is counted with
//    its reason (drop, count, log).
//  * The adapter applies the newest valid command. Its actuation time is the
//    simulation time of the world snapshot in hand at application,
//    CaptureTimeMicros(frame) (never the simulator's float stamp).
//  * If 200 ms of simulation time pass without a valid command applied
//    (measured from the actuation time of the last one), the adapter applies
//    the stop response itself: -min(4, max_deceleration) m/s^2, steering held
//    at the last valid command's angle, until standstill (speed < 0.1 km/h),
//    then a brake hold until the run ends. The stop latches: later commands
//    are rejected. The stop's monotonic stamp is the WorldTick time at which
//    it began (ActuationStatePayload::stopSinceMono).
//  * Steering: steer = clamp(-steeringAngle / max_road_wheel_angle_deg, -1, 1)
//    (CARLA steers right for positive steer, the command is positive left).
//  * Longitudinal: feedforward lookup (acceleration -> throttle or brake from
//    the calibration table) plus a PI correction on the speed error against a
//    reference speed integrated from the commanded acceleration, with
//    anti-windup. Throttle and brake are never applied together.
#pragma once

#include <array>
#include <cstdint>
#include <mutex>
#include <string>
#include <vector>

#include "adapter_config.h"
#include "de4sdv/driving/payloads.h"

namespace de4sdv::driving::actuation {

// Why a received command was not applied. kNone means it was applied (or is
// pending the first world snapshot).
enum class RejectReason : std::uint8_t {
  kNone = 0,
  kNonFinite = 1,
  kAccelerationOutOfLimits = 2,
  kSteeringOutOfLimits = 3,
  kEmptyPlanReference = 4,
  kStaleProductionTime = 5,
  kFutureProductionTime = 6,
  kStopLatched = 7,
};
inline constexpr std::size_t kRejectReasonCount = 8;
const char* RejectReasonName(RejectReason reason);

struct CommandValidity {
  bool valid = false;
  RejectReason reason = RejectReason::kNone;
  double ageSeconds = 0.0;  // arrival - productionTime (negative: stamp in the future)
};

// One CARLA world snapshot. monotonicSeconds is CLOCK_MONOTONIC of the S-CORE
// host at the snapshot's arrival; it is what stamps the adapter's own stop
// (ActuationStatePayload::stopSinceMono).
struct WorldTick {
  std::uint64_t frameIndex = 0;
  double speedMps = 0.0;
  double longitudinalAccelerationMps2 = 0.0;
  double monotonicSeconds = 0.0;
};

struct VehicleControlCommand {
  double throttle = 0.0;  // [0, 1]
  double brake = 0.0;     // [0, 1], never non-zero together with throttle
  double steer = 0.0;     // [-1, 1], CARLA sign (positive right)
  bool handBrake = false; // never set by this adapter (model: stays default)
};

struct ActuationOutput {
  bool hasControl = false;         // the shell applies `control` now
  VehicleControlCommand control;
  bool appliedCommand = false;     // an external command was applied by this call
  bool stopBegan = false;          // the adapter's own stop began at this call
  bool standstillReached = false;  // the stop reached standstill at this call
  bool hasState = false;           // publish `state` on the actuation-state event
  ActuationStatePayload state{};
  RejectReason reject = RejectReason::kNone;
  double actuationTime = 0.0;  // simulation seconds of the snapshot used
  std::uint64_t frameIndex = 0;
};

class ActuationAdapter {
 public:
  explicit ActuationAdapter(AdapterConfig config);

  // A command arrived on mw::com. `arrivalMonotonicSeconds` is
  // CLOCK_MONOTONIC on the S-CORE host. When no world snapshot has been seen
  // yet the command is held and applied at the first tick.
  ActuationOutput OnCommand(const VehicleMotionCommandPayload& command,
                            double arrivalMonotonicSeconds);

  // A world snapshot arrived. Runs the watchdog and returns the control to
  // apply at this snapshot.
  ActuationOutput OnWorldTick(const WorldTick& tick);

  // Validity without side effects (used by tests and by the shell's logging).
  CommandValidity CheckCommand(const VehicleMotionCommandPayload& command,
                               double arrivalMonotonicSeconds) const;

  bool StopLatched() const;
  // The cause of the adapter's own stop (kNone when no stop is held). The
  // adapter stops only on kCommandTimeout today (REQ-DRIVING-028).
  Cause StopCause() const;
  bool StandstillHold() const;
  double ReferenceSpeedMps() const;
  double LastActuationTime() const;  // simulation seconds, < 0 before the first command
  // CLOCK_MONOTONIC seconds at which the stop began; 0 while no stop is held.
  double StopSinceMonoSeconds() const;
  std::uint32_t RejectedCommandCount() const;
  std::uint32_t RejectCount(RejectReason reason) const;
  const AdapterConfig& config() const { return config_; }

 private:
  CommandValidity CheckCommandLocked(const VehicleMotionCommandPayload& command,
                                     double arrivalMonotonicSeconds) const;
  VehicleControlCommand ComputeControlLocked(double accelerationMps2, double steeringAngleDeg,
                                             double dtSeconds);
  VehicleControlCommand StopControlLocked(double dtSeconds);
  VehicleControlCommand StandstillControlLocked() const;
  VehicleControlCommand HoldControlLocked() const;
  double FeedforwardLocked(double accelerationMps2) const;
  ActuationStatePayload AppliedStateLocked(const VehicleMotionCommandPayload& command,
                                           std::int64_t actuationMicros) const;
  ActuationStatePayload StopStateLocked(std::int64_t actuationMicros) const;
  void BeginStopLocked(std::int64_t tickMicros, double tickMonotonicSeconds, ActuationOutput* out);
  void AnchorReferenceLocked();

  AdapterConfig config_;
  mutable std::mutex mutex_;

  bool have_snapshot_ = false;
  std::uint64_t snapshot_frame_ = 0;
  double snapshot_speed_mps_ = 0.0;
  double snapshot_acceleration_mps2_ = 0.0;
  std::int64_t last_tick_micros_ = 0;
  bool have_last_tick_ = false;

  bool have_current_command_ = false;
  VehicleMotionCommandPayload current_command_{};
  bool have_pending_command_ = false;  // arrived before the first snapshot
  VehicleMotionCommandPayload pending_command_{};

  std::int64_t last_actuation_micros_ = -1;
  double reference_speed_mps_ = 0.0;
  bool reference_anchored_ = false;
  double integral_ = 0.0;

  bool stop_latched_ = false;
  Cause stop_cause_ = Cause::kNone;
  bool standstill_ = false;
  std::int64_t stop_since_micros_ = 0;      // simulation time the stop began
  double stop_since_mono_seconds_ = 0.0;    // CLOCK_MONOTONIC at the same tick
  double held_steering_deg_ = 0.0;

  std::uint32_t rejected_commands_ = 0;
  std::array<std::uint32_t, kRejectReasonCount> reject_counts_{};
};

// ---- helpers shared with the shell and the tests ----

// Copies a fixed-size, NUL-terminated-or-not char field into `out`, always
// NUL-terminating.
void CopyPlanReference(const char (&source)[kIdLength], char (&out)[kIdLength]);
// True when a fixed-size char field holds at least one non-NUL character.
bool PlanReferenceNonEmpty(const char (&reference)[kIdLength]);
// The simulation time of a snapshot in seconds.
double CaptureTimeSeconds(std::uint64_t frame_index);

}  // namespace de4sdv::driving::actuation
