// The actuation adapter's JSONL records, in the style of the closed-loop
// driving bench's ICD section 6: every record has t_mono_ns, t_real_ns, host,
// component, event, seq and data (run_log.h); events are in.<port> and
// out.<port> for each crossing, drop, error and the lifecycle events start,
// config, ready and stop; every time field names its clock by its suffix
// (_sim_s: simulation seconds, _mono_s: monotonic seconds); non-finite numbers
// are null; components log stamps and the evaluators compute (no latencies,
// no ages).
//
// The field names are this component's proposal; the driver-assistance ICD has
// no log section yet.
//
//   in.world_snapshot      {frame, t_sim_s, egoPresent, speed_mps, kept}
//   in.driving_command     {seq, crc_ok, issueTime_sim_s, newestWorldTime_sim_s,
//                           newestWorldFrame, verdict, acceleration, steeringAngle,
//                           checkValue, referenceSeq, arrival_mono_s}
//   drop                   {reason, seq, referenceSeq, issueTime_sim_s,
//                           newestWorldTime_sim_s}
//   out.ackermann_control  {frame, t_sim_s, seq, steer, steerSpeed, speed,
//                           acceleration, jerk, controlSource}
//
// seq inside data is the command's sequenceCount; the record's own seq is the
// log's counter. referenceSeq is the reference count the decision was made
// against, before this command (actuation_core.h): the highest sequence count
// among the earlier commands whose check value holds, 0 before the first.
// newestWorldTime_sim_s and newestWorldFrame are null before the first world
// snapshot. out.ackermann_control holds the five floats the
// simulator client was given, in the model's names (SimulatorAckermannControl),
// with the frame and time of the newest snapshot at the application.
#pragma once

#include <cstdint>
#include <string>

#include "actuation_core.h"
#include "run_log.h"
#include "simulator_client.h"

namespace de4sdv::driver_assistance::actuation::records {

namespace detail {
inline std::string Tag(const char* name, const std::string& value) {
  return "\"" + std::string(name) + "\":" + value;
}
inline std::string Bool(bool value) { return value ? "true" : "false"; }
inline std::string Unsigned(std::uint64_t value) { return std::to_string(value); }
}  // namespace detail

inline std::string InWorldSnapshot(const simulator::SnapshotSample& sample, bool kept) {
  using detail::Tag;
  return "{" + Tag("frame", detail::Unsigned(sample.frame)) + "," +
         Tag("t_sim_s", JsonNumber(sample.simTimeS)) + "," +
         Tag("egoPresent", detail::Bool(sample.egoPresent)) + "," +
         Tag("speed_mps", sample.egoPresent ? JsonNumber(sample.speedMps) : "null") + "," +
         Tag("kept", detail::Bool(kept)) + "}";
}

inline std::string InDrivingCommand(const DrivingCommandEventPayload& command,
                                    const CommandDecision& decision, double arrivalMonoS) {
  using detail::Tag;
  const std::string newestTime = decision.worldKnown ? JsonNumber(decision.world.simTimeS) : "null";
  const std::string newestFrame =
      decision.worldKnown ? detail::Unsigned(decision.world.frame) : "null";
  return "{" + Tag("seq", detail::Unsigned(command.sequenceCount)) + "," +
         Tag("crc_ok", detail::Bool(decision.crcOk)) + "," +
         Tag("issueTime_sim_s", JsonNumber(command.issueTime)) + "," +
         Tag("newestWorldTime_sim_s", newestTime) + "," + Tag("newestWorldFrame", newestFrame) +
         "," + Tag("verdict", JsonString(decision.accepted ? "accepted" : "rejected")) + "," +
         Tag("acceleration", JsonNumber(command.acceleration)) + "," +
         Tag("steeringAngle", JsonNumber(command.steeringAngle)) + "," +
         Tag("checkValue", detail::Unsigned(command.checkValue)) + "," +
         Tag("referenceSeq", detail::Unsigned(decision.referenceSequence)) + "," +
         Tag("arrival_mono_s", JsonNumber(arrivalMonoS)) + "}";
}

inline std::string Drop(const DrivingCommandEventPayload& command,
                        const CommandDecision& decision) {
  using detail::Tag;
  const std::string newestTime = decision.worldKnown ? JsonNumber(decision.world.simTimeS) : "null";
  return "{" + Tag("reason", JsonString(DropReasonName(decision.reason))) + "," +
         Tag("seq", detail::Unsigned(command.sequenceCount)) + "," +
         Tag("referenceSeq", detail::Unsigned(decision.referenceSequence)) + "," +
         Tag("issueTime_sim_s", JsonNumber(command.issueTime)) + "," +
         Tag("newestWorldTime_sim_s", newestTime) + "}";
}

inline std::string OutAckermannControl(const WorldSnapshot& world, std::uint32_t sequence,
                                       const simulator::AppliedAckermannControl& control) {
  using detail::Tag;
  return "{" + Tag("frame", detail::Unsigned(world.frame)) + "," +
         Tag("t_sim_s", JsonNumber(world.simTimeS)) + "," +
         Tag("seq", detail::Unsigned(sequence)) + "," +
         Tag("steer", JsonNumber(control.steer)) + "," +
         Tag("steerSpeed", JsonNumber(control.steerSpeed)) + "," +
         Tag("speed", JsonNumber(control.speed)) + "," +
         Tag("acceleration", JsonNumber(control.acceleration)) + "," +
         Tag("jerk", JsonNumber(control.jerk)) + "," +
         Tag("controlSource", JsonString("actuationAdapter")) + "}";
}

inline std::string Error(const std::string& what, const std::string& message = std::string()) {
  using detail::Tag;
  std::string out = "{" + Tag("what", JsonString(what));
  if (!message.empty()) out += "," + Tag("message", JsonString(message));
  return out + "}";
}

}  // namespace de4sdv::driver_assistance::actuation::records
