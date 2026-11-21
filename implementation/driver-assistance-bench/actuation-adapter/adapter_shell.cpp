#include "adapter_shell.h"

#include <cmath>
#include <cstdint>
#include <utility>

#include "log_records.h"

namespace de4sdv::driver_assistance::actuation {
namespace {

// Also catches a double too large for a float.
bool Finite(const simulator::AppliedAckermannControl& c) {
  return std::isfinite(c.steer) && std::isfinite(c.steerSpeed) && std::isfinite(c.speed) &&
         std::isfinite(c.acceleration) && std::isfinite(c.jerk);
}

}  // namespace

simulator::AppliedAckermannControl ToApplied(const AckermannControl& control) {
  simulator::AppliedAckermannControl applied;
  applied.steer = static_cast<float>(control.steer);
  applied.steerSpeed = static_cast<float>(control.steerSpeed);
  applied.speed = static_cast<float>(control.speed);
  applied.acceleration = static_cast<float>(control.acceleration);
  applied.jerk = static_cast<float>(control.jerk);
  return applied;
}

void AdapterShell::OnSnapshot(const simulator::SnapshotSample& sample) {
  std::lock_guard<std::mutex> lock(mutex_);
  bool kept = false;
  if (sample.egoPresent) {
    WorldSnapshot world;
    world.frame = sample.frame;
    world.simTimeS = sample.simTimeS;
    world.speedMps = sample.speedMps;
    const bool had = core_.HasWorld();
    const std::uint64_t before = core_.NewestWorld().frame;
    core_.OnWorldSnapshot(world);
    kept = !had || core_.NewestWorld().frame != before;
  }
  records_->Write("in.world_snapshot", records::InWorldSnapshot(sample, kept));
  if (!sample.egoPresent && !ego_absent_logged_) {
    ego_absent_logged_ = true;
    records_->Write("error", records::Error("ego vehicle absent from the world snapshot"));
  }
}

void AdapterShell::OnCommand(const DrivingCommandEventPayload& command, double arrivalMonoS) {
  std::lock_guard<std::mutex> lock(mutex_);
  const CommandDecision decision = core_.OnCommand(command);
  records_->Write("in.driving_command", records::InDrivingCommand(command, decision, arrivalMonoS));
  if (!decision.accepted) {
    // Nothing in its place: the simulator keeps the last valid control.
    ++dropped_;
    records_->Write("drop", records::Drop(command, decision));
    return;
  }
  const simulator::AppliedAckermannControl applied = ToApplied(decision.control);
  // The model has no rule for a command whose values give a non-finite control
  // (README.md, open question); such a control is not sent.
  if (!decision.controlFinite || !Finite(applied)) {
    records_->Write("error", records::Error("non-finite Ackermann control"));
    return;
  }
  std::string error;
  if (!simulator::ApplyAckermannControl(applied, &error)) {
    records_->Write("error", records::Error("ApplyAckermannControl failed", error));
    return;
  }
  ++applied_;
  records_->Write("out.ackermann_control",
                  records::OutAckermannControl(decision.world, command.sequenceCount, applied));
}

std::uint64_t AdapterShell::AppliedCount() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return applied_;
}

std::uint64_t AdapterShell::DroppedCount() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return dropped_;
}

bool AttachToSimulator(AdapterShell* shell, std::string* error) {
  return simulator::StartSnapshots(
      [shell](const simulator::SnapshotSample& sample) { shell->OnSnapshot(sample); }, error);
}

}  // namespace de4sdv::driver_assistance::actuation
