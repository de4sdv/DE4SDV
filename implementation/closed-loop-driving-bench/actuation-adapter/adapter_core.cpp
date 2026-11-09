#include "adapter_core.h"

#include <algorithm>
#include <cmath>
#include <cstring>

namespace de4sdv::driving::actuation {
namespace {

// REQ-DRIVING-028: the stop begins once more than 200 ms of simulation time have passed since the last
// actuation, at the third tick. A command arrives about one period after its frame's tick, so one late
// command sees exactly 200 ms at the tick before it, as one missed command does; the requirement stops
// on two missed commands.
constexpr std::int64_t kWatchdogMicros = 200000;
// REQ-DRIVING-028 validity: -5 ms <= age <= 300 ms at arrival (ICD v2 §4).
constexpr double kMaxCommandAgeSeconds = 0.300;
constexpr double kFutureProductionToleranceSeconds = 0.005;
// 1 ns of slack on both comparisons (double subtraction of two
// CLOCK_MONOTONIC seconds values is exact enough, the slack only avoids a
// boundary artefact in tests).
constexpr double kAgeEpsilonSeconds = 1e-9;
// The reference speed is re-anchored to the measured speed only when the
// vehicle has diverged this far from the intended trajectory (the PI handles
// everything below; this recovers from a blocked or teleported vehicle).
constexpr double kMaxReferenceDivergenceMps = 5.0;
// The PI sees at most this speed error; beyond it the reference is no longer
// meaningful and the feedforward dominates.
constexpr double kMaxSpeedErrorMps = 5.0;
// One integration step is capped at 1 s of simulation time (a frame gap).
constexpr double kMaxControlDtSeconds = 1.0;

double Clamp(double value, double low, double high) {
  return std::min(high, std::max(low, value));
}

}  // namespace

const char* RejectReasonName(RejectReason reason) {
  switch (reason) {
    case RejectReason::kNone: return "none";
    case RejectReason::kNonFinite: return "non_finite";
    case RejectReason::kAccelerationOutOfLimits: return "acceleration_out_of_limits";
    case RejectReason::kSteeringOutOfLimits: return "steering_out_of_limits";
    case RejectReason::kEmptyPlanReference: return "empty_plan_reference";
    case RejectReason::kStaleProductionTime: return "stale_production_time";
    case RejectReason::kFutureProductionTime: return "future_production_time";
    case RejectReason::kStopLatched: return "stop_latched";
  }
  return "unknown";
}

void CopyPlanReference(const char (&source)[kIdLength], char (&out)[kIdLength]) {
  std::size_t length = 0;
  while (length < kIdLength && source[length] != '\0') ++length;
  if (length == kIdLength) length = kIdLength - 1;
  std::memset(out, 0, kIdLength);
  std::memcpy(out, source, length);
}

bool PlanReferenceNonEmpty(const char (&reference)[kIdLength]) {
  for (std::size_t i = 0; i < kIdLength; ++i) {
    if (reference[i] != '\0') return true;
  }
  return false;
}

double CaptureTimeSeconds(std::uint64_t frame_index) {
  return static_cast<double>(CaptureTimeMicros(frame_index)) / 1e6;
}

ActuationAdapter::ActuationAdapter(AdapterConfig config) : config_(std::move(config)) {
  if (config_.longitudinal.table.empty()) {
    config_.longitudinal.table = DefaultLongitudinalTable();
    config_.setTableSource(TableSource::kDefault);
  }
}

CommandValidity ActuationAdapter::CheckCommand(const VehicleMotionCommandPayload& command,
                                               double arrivalMonotonicSeconds) const {
  std::lock_guard<std::mutex> lock(mutex_);
  return CheckCommandLocked(command, arrivalMonotonicSeconds);
}

CommandValidity ActuationAdapter::CheckCommandLocked(const VehicleMotionCommandPayload& command,
                                                     double arrivalMonotonicSeconds) const {
  CommandValidity validity;
  const double acceleration = static_cast<double>(command.acceleration);
  const double steering = static_cast<double>(command.steeringAngle);
  const double production = static_cast<double>(command.productionTime);

  if (!std::isfinite(acceleration) || !std::isfinite(steering) || !std::isfinite(production) ||
      !std::isfinite(arrivalMonotonicSeconds)) {
    validity.reason = RejectReason::kNonFinite;
    return validity;
  }
  validity.ageSeconds = arrivalMonotonicSeconds - production;

  if (acceleration > config_.limits.max_acceleration_mps2 + 1e-6 ||
      acceleration < -config_.limits.max_deceleration_mps2 - 1e-6) {
    validity.reason = RejectReason::kAccelerationOutOfLimits;
    return validity;
  }
  if (std::fabs(steering) > config_.limits.max_road_wheel_angle_deg + 1e-6) {
    validity.reason = RejectReason::kSteeringOutOfLimits;
    return validity;
  }
  if (!PlanReferenceNonEmpty(command.planReference)) {
    validity.reason = RejectReason::kEmptyPlanReference;
    return validity;
  }
  if (validity.ageSeconds > kMaxCommandAgeSeconds + kAgeEpsilonSeconds) {
    validity.reason = RejectReason::kStaleProductionTime;
    return validity;
  }
  if (validity.ageSeconds < -kFutureProductionToleranceSeconds - kAgeEpsilonSeconds) {
    validity.reason = RejectReason::kFutureProductionTime;
    return validity;
  }
  validity.valid = true;
  return validity;
}

void ActuationAdapter::AnchorReferenceLocked() {
  reference_speed_mps_ = snapshot_speed_mps_;
  reference_anchored_ = true;
}

ActuationOutput ActuationAdapter::OnCommand(const VehicleMotionCommandPayload& command,
                                            double arrivalMonotonicSeconds) {
  std::lock_guard<std::mutex> lock(mutex_);
  ActuationOutput out;

  if (stop_latched_) {
    out.reject = RejectReason::kStopLatched;
    ++rejected_commands_;
    ++reject_counts_[static_cast<std::size_t>(RejectReason::kStopLatched)];
    return out;
  }

  const CommandValidity validity = CheckCommandLocked(command, arrivalMonotonicSeconds);
  if (!validity.valid) {
    out.reject = validity.reason;
    ++rejected_commands_;
    ++reject_counts_[static_cast<std::size_t>(validity.reason)];
    return out;
  }

  if (!have_snapshot_) {
    // The first command can arrive before the first tick. Hold it; the first
    // tick applies it with that snapshot's actuation time.
    pending_command_ = command;
    have_pending_command_ = true;
    return out;
  }

  current_command_ = command;
  have_current_command_ = true;
  have_pending_command_ = false;

  if (!reference_anchored_ ||
      std::fabs(reference_speed_mps_ - snapshot_speed_mps_) > kMaxReferenceDivergenceMps) {
    AnchorReferenceLocked();
  }

  last_actuation_micros_ = CaptureTimeMicros(snapshot_frame_);
  out.hasControl = true;
  out.control = ComputeControlLocked(static_cast<double>(command.acceleration),
                                     static_cast<double>(command.steeringAngle), 0.0);
  out.appliedCommand = true;
  out.hasState = true;
  out.state = AppliedStateLocked(command, last_actuation_micros_);
  out.actuationTime = CaptureTimeSeconds(snapshot_frame_);
  out.frameIndex = snapshot_frame_;
  return out;
}

ActuationOutput ActuationAdapter::OnWorldTick(const WorldTick& tick) {
  std::lock_guard<std::mutex> lock(mutex_);
  ActuationOutput out;

  have_snapshot_ = true;
  snapshot_frame_ = tick.frameIndex;
  snapshot_speed_mps_ = std::isfinite(tick.speedMps) ? tick.speedMps : 0.0;
  snapshot_acceleration_mps2_ =
      std::isfinite(tick.longitudinalAccelerationMps2) ? tick.longitudinalAccelerationMps2 : 0.0;

  const std::int64_t tick_micros = CaptureTimeMicros(tick.frameIndex);
  double dt = 0.0;
  if (have_last_tick_ && tick_micros > last_tick_micros_) {
    dt = std::min(kMaxControlDtSeconds, static_cast<double>(tick_micros - last_tick_micros_) / 1e6);
  }
  if (!have_last_tick_ || tick_micros > last_tick_micros_) {
    last_tick_micros_ = tick_micros;
    have_last_tick_ = true;
  }

  out.frameIndex = tick.frameIndex;
  out.actuationTime = CaptureTimeSeconds(tick.frameIndex);

  if (have_pending_command_) {
    current_command_ = pending_command_;
    have_current_command_ = true;
    have_pending_command_ = false;
    last_actuation_micros_ = tick_micros;
    if (!reference_anchored_) AnchorReferenceLocked();
    out.hasControl = true;
    out.control = ComputeControlLocked(static_cast<double>(current_command_.acceleration),
                                       static_cast<double>(current_command_.steeringAngle), 0.0);
    out.appliedCommand = true;
    out.hasState = true;
    out.state = AppliedStateLocked(current_command_, tick_micros);
    return out;
  }

  if (stop_latched_) {
    if (!standstill_ &&
        snapshot_speed_mps_ * 3.6 < config_.longitudinal.standstill_speed_kmh) {
      standstill_ = true;
      integral_ = 0.0;
      reference_speed_mps_ = 0.0;
      out.standstillReached = true;
      out.hasControl = true;
      out.control = StandstillControlLocked();
      return out;
    }
    out.hasControl = true;
    out.control = StopControlLocked(dt);
    return out;
  }

  if (have_current_command_) {
    if (tick_micros - last_actuation_micros_ > kWatchdogMicros) {
      BeginStopLocked(tick_micros, tick.monotonicSeconds, &out);
      return out;
    }
    out.hasControl = true;
    out.control = ComputeControlLocked(static_cast<double>(current_command_.acceleration),
                                       static_cast<double>(current_command_.steeringAngle), dt);
    return out;
  }

  // Nothing has been commanded yet: hold the vehicle with the brake but do
  // not latch the stop (the watchdog starts at the first applied command).
  out.hasControl = true;
  out.control = HoldControlLocked();
  return out;
}

void ActuationAdapter::BeginStopLocked(std::int64_t tick_micros, double tick_monotonic_seconds,
                                       ActuationOutput* out) {
  stop_latched_ = true;
  stop_cause_ = Cause::kCommandTimeout;
  standstill_ = false;
  stop_since_micros_ = tick_micros;
  stop_since_mono_seconds_ =
      std::isfinite(tick_monotonic_seconds) ? tick_monotonic_seconds : 0.0;
  held_steering_deg_ =
      have_current_command_ ? static_cast<double>(current_command_.steeringAngle) : 0.0;
  reference_speed_mps_ = snapshot_speed_mps_;
  reference_anchored_ = true;
  integral_ = 0.0;

  out->stopBegan = true;
  out->hasControl = true;
  out->control = ComputeControlLocked(config_.StopAccelerationMps2(), held_steering_deg_, 0.0);
  out->hasState = true;
  out->state = StopStateLocked(tick_micros);
}

double ActuationAdapter::FeedforwardLocked(double accelerationMps2) const {
  const std::vector<LongitudinalPoint>& table = config_.longitudinal.table;
  if (table.empty()) return 0.0;
  if (accelerationMps2 <= table.front().acceleration_mps2) {
    return table.front().throttle - table.front().brake;
  }
  if (accelerationMps2 >= table.back().acceleration_mps2) {
    return table.back().throttle - table.back().brake;
  }
  std::size_t high = 1;
  while (high < table.size() && table[high].acceleration_mps2 < accelerationMps2) ++high;
  const LongitudinalPoint& lower = table[high - 1];
  const LongitudinalPoint& upper = table[high];
  const double span = upper.acceleration_mps2 - lower.acceleration_mps2;
  const double weight = span > 0.0 ? (accelerationMps2 - lower.acceleration_mps2) / span : 0.0;
  const double throttle = lower.throttle + weight * (upper.throttle - lower.throttle);
  const double brake = lower.brake + weight * (upper.brake - lower.brake);
  return throttle - brake;
}

VehicleControlCommand ActuationAdapter::ComputeControlLocked(double accelerationMps2,
                                                            double steeringAngleDeg,
                                                            double dtSeconds) {
  if (dtSeconds > 0.0) {
    reference_speed_mps_ = std::max(0.0, reference_speed_mps_ + accelerationMps2 * dtSeconds);
  }
  const double error =
      Clamp(reference_speed_mps_ - snapshot_speed_mps_, -kMaxSpeedErrorMps, kMaxSpeedErrorMps);
  const double feedforward = FeedforwardLocked(accelerationMps2);

  double effort = feedforward + config_.longitudinal.speed_kp * error +
                  config_.longitudinal.speed_ki * integral_;

  // Conditional integration: do not wind up while the pedal is saturated in
  // the direction of the error.
  const bool saturated =
      (effort >= 1.0 && error > 0.0) || (effort <= -1.0 && error < 0.0);
  if (dtSeconds > 0.0 && !saturated) {
    integral_ = Clamp(integral_ + error * dtSeconds, -config_.longitudinal.integral_limit,
                      config_.longitudinal.integral_limit);
    effort = feedforward + config_.longitudinal.speed_kp * error +
             config_.longitudinal.speed_ki * integral_;
  }
  effort = Clamp(effort, -1.0, 1.0);

  VehicleControlCommand control;
  // One effort scalar, one pedal: throttle and brake can never both be set.
  control.throttle = effort > 0.0 ? effort : 0.0;
  control.brake = effort < 0.0 ? -effort : 0.0;
  const double max_angle = config_.limits.max_road_wheel_angle_deg;
  control.steer = Clamp(-steeringAngleDeg / max_angle, -1.0, 1.0);
  control.handBrake = false;
  return control;
}

VehicleControlCommand ActuationAdapter::StopControlLocked(double dtSeconds) {
  if (standstill_) return StandstillControlLocked();
  return ComputeControlLocked(config_.StopAccelerationMps2(), held_steering_deg_, dtSeconds);
}

VehicleControlCommand ActuationAdapter::StandstillControlLocked() const {
  VehicleControlCommand control;
  control.throttle = 0.0;
  control.brake = config_.longitudinal.standstill_brake;
  control.steer = Clamp(-held_steering_deg_ / config_.limits.max_road_wheel_angle_deg, -1.0, 1.0);
  control.handBrake = false;
  return control;
}

VehicleControlCommand ActuationAdapter::HoldControlLocked() const {
  VehicleControlCommand control;
  control.throttle = 0.0;
  control.brake = config_.longitudinal.standstill_brake;
  control.steer = 0.0;
  control.handBrake = false;
  return control;
}

ActuationStatePayload ActuationAdapter::AppliedStateLocked(
    const VehicleMotionCommandPayload& command, std::int64_t actuationMicros) const {
  ActuationStatePayload state{};
  state.applied = 1;
  state.stopInForce = 0;
  state.cause = Cause::kNone;
  state.acceleration = command.acceleration;
  state.steeringAngle = command.steeringAngle;
  state.actuationTime = static_cast<double>(actuationMicros) / 1e6;
  state.stopSince = 0.0;
  state.stopSinceMono = 0.0;
  CopyPlanReference(command.planReference, state.planReference);
  return state;
}

ActuationStatePayload ActuationAdapter::StopStateLocked(std::int64_t actuationMicros) const {
  ActuationStatePayload state{};
  state.applied = 0;
  state.stopInForce = 1;
  state.cause = stop_cause_;
  state.acceleration = static_cast<float>(config_.StopAccelerationMps2());
  state.steeringAngle = static_cast<float>(held_steering_deg_);
  state.actuationTime = static_cast<double>(actuationMicros) / 1e6;
  state.stopSince = static_cast<double>(stop_since_micros_) / 1e6;
  state.stopSinceMono = stop_since_mono_seconds_;
  // No plan: the stop is the adapter's own (REQ-DRIVING-028).
  std::memset(state.planReference, 0, sizeof state.planReference);
  return state;
}

bool ActuationAdapter::StopLatched() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return stop_latched_;
}

Cause ActuationAdapter::StopCause() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return stop_cause_;
}

bool ActuationAdapter::StandstillHold() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return standstill_;
}

double ActuationAdapter::ReferenceSpeedMps() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return reference_speed_mps_;
}

double ActuationAdapter::StopSinceMonoSeconds() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return stop_since_mono_seconds_;
}

double ActuationAdapter::LastActuationTime() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return last_actuation_micros_ < 0 ? -1.0 : static_cast<double>(last_actuation_micros_) / 1e6;
}

std::uint32_t ActuationAdapter::RejectedCommandCount() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return rejected_commands_;
}

std::uint32_t ActuationAdapter::RejectCount(RejectReason reason) const {
  std::lock_guard<std::mutex> lock(mutex_);
  return reject_counts_[static_cast<std::size_t>(reason)];
}

}  // namespace de4sdv::driving::actuation
