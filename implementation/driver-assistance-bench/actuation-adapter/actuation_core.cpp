#include "actuation_core.h"

#include <algorithm>
#include <cmath>

namespace de4sdv::driver_assistance::actuation {
namespace {

bool AllFinite(const AckermannControl& c) {
  return std::isfinite(c.steer) && std::isfinite(c.steerSpeed) && std::isfinite(c.speed) &&
         std::isfinite(c.acceleration) && std::isfinite(c.jerk);
}

}  // namespace

const char* DropReasonName(DropReason reason) {
  switch (reason) {
    case DropReason::kNone: return "none";
    case DropReason::kLoss: return "loss";
    case DropReason::kRepetition: return "repetition";
    case DropReason::kCorruption: return "corruption";
    case DropReason::kDelay: return "delay";
  }
  return "unknown";
}

// MAP-DRIVING-DA-COMMAND: "steer = -steeringAngle * pi / 180 in rad ...;
// speed = max(0, v + 2 * acceleration) with v the speed of the ego vehicle in
// the newest world snapshot, acceleration unchanged and jerk = 10.0 ...;
// steerSpeed stays at its default of 0.0."
AckermannControl ToAckermannControl(const DrivingCommandEventPayload& command, double speedMps) {
  const double acceleration = static_cast<double>(command.acceleration);
  AckermannControl control;
  control.steer = -static_cast<double>(command.steeringAngle) * kPi / 180.0;
  control.steerSpeed = kSteerSpeed;
  control.speed = std::max(0.0, speedMps + kSpeedHorizonS * acceleration);
  control.acceleration = acceleration;
  control.jerk = kJerk;
  return control;
}

// "whose issue time is older than the newest world time by more than 0.1 s of
// simulation time": whole milliseconds, each time rounded to the nearest one.
// std::round on doubles: no integer conversion, so no overflow for any finite
// value.
bool IssueTimeTooOld(double issueTimeS, double newestWorldTimeS) {
  if (!std::isfinite(issueTimeS) || !std::isfinite(newestWorldTimeS)) return true;
  const double ageMs = std::round(newestWorldTimeS * 1000.0) - std::round(issueTimeS * 1000.0);
  return ageMs > kMaxCommandAgeMs;
}

void ActuationCore::OnWorldSnapshot(const WorldSnapshot& snapshot) {
  if (has_world_ && snapshot.frame <= world_.frame) return;
  world_ = snapshot;
  has_world_ = true;
}

CommandDecision ActuationCore::OnCommand(const DrivingCommandEventPayload& command) {
  CommandDecision decision;
  decision.lastAcceptedSequence = last_accepted_;
  decision.worldKnown = has_world_;
  decision.world = world_;
  decision.crcOk = DrivingCommandCheckValue(command) == command.checkValue;

  // 64 bits, so that the count after 0xFFFFFFFF does not wrap to 0.
  const std::uint64_t expected = static_cast<std::uint64_t>(last_accepted_) + 1u;
  const std::uint64_t sequence = command.sequenceCount;
  if (!decision.crcOk) {
    decision.reason = DropReason::kCorruption;
  } else if (sequence > expected) {
    decision.reason = DropReason::kLoss;
  } else if (sequence < expected) {
    decision.reason = DropReason::kRepetition;
  } else if (!has_world_ || IssueTimeTooOld(command.issueTime, world_.simTimeS)) {
    decision.reason = DropReason::kDelay;
  }
  if (decision.reason != DropReason::kNone) return decision;

  decision.accepted = true;
  decision.control = ToAckermannControl(command, world_.speedMps);
  decision.controlFinite = AllFinite(decision.control);
  last_accepted_ = command.sequenceCount;
  return decision;
}

}  // namespace de4sdv::driver_assistance::actuation
