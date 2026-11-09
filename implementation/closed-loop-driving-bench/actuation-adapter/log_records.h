// The adapter's JSONL records (ICD v2 section 6), built from payloads so the
// shell and the tests share one definition.
//
// Rules applied here:
//  * payload fields keep their model names (productionTime, actuationTime,
//    stopSince, stopSinceMono, planReference, ...);
//  * a sibling "clocks" object maps every payload time field to its clock
//    (REQ-DRIVING-030 to -032);
//  * shell-only time fields carry the suffix themselves (t_sim_ms,
//    arrival_mono_s);
//  * no computed latencies: stamps only, the evaluators compute;
//  * non-finite numbers are JSON null (JsonNumber from run_log.h).
//
// out.vehicle_control carries frame, t_sim_ms, throttle, brake, steer and
// controlSource = "actuationAdapter" (ICD v2 §10 C1's world.jsonl uses the same
// controlSource spelling).
#pragma once

#include <cstdint>
#include <string>

#include "de4sdv/driving/payloads.h"
#include "de4sdv/driving/run_log.h"

namespace de4sdv::driving::log {

namespace detail {

inline std::string Tag(const char* name, const std::string& value) {
  return "\"" + std::string(name) + "\":" + value;
}

// A fixed-size char field as a std::string, stopping at NUL or the capacity.
inline std::string FixedField(const char* data, std::size_t capacity) {
  std::size_t length = 0;
  while (length < capacity && data[length] != '\0') ++length;
  return std::string(data, length);
}

inline std::string Clocks(const char* pairs) {
  return Tag("clocks", std::string("{") + pairs + "}");
}

}  // namespace detail

// in.command (or, for a rejected one, the same record plus the shell's drop).
inline std::string InCommand(const VehicleMotionCommandPayload& command,
                             double arrivalMonotonicSeconds, const char* rejectReasonName) {
  using detail::Clocks;
  using detail::FixedField;
  using detail::Tag;
  return "{" + Tag("acceleration", JsonNumber(command.acceleration)) + "," +
         Tag("steeringAngle", JsonNumber(command.steeringAngle)) + "," +
         Tag("productionTime", JsonNumber(command.productionTime)) + "," +
         Tag("planReference",
             JsonString(FixedField(command.planReference, kIdLength))) + "," +
         Tag("arrival_mono_s", JsonNumber(arrivalMonotonicSeconds)) + "," +
         Tag("valid", rejectReasonName != nullptr && std::string(rejectReasonName) == "none"
                          ? "true"
                          : "false") + "," +
         Tag("rejectReason", JsonString(rejectReasonName != nullptr ? rejectReasonName : "none")) +
         "," + Clocks("\"productionTime\":\"monotonic\"") + "}";
}

// drop: why a command was not applied, with its stamps and the running count.
inline std::string Drop(const VehicleMotionCommandPayload& command,
                        double arrivalMonotonicSeconds, const char* rejectReasonName,
                        std::uint32_t droppedTotal) {
  using detail::Clocks;
  using detail::FixedField;
  using detail::Tag;
  return "{" + Tag("reason", JsonString(rejectReasonName != nullptr ? rejectReasonName : "none")) +
         "," +
         Tag("planReference",
             JsonString(FixedField(command.planReference, kIdLength))) + "," +
         Tag("productionTime", JsonNumber(command.productionTime)) + "," +
         Tag("arrival_mono_s", JsonNumber(arrivalMonotonicSeconds)) + "," +
         Tag("droppedTotal", std::to_string(droppedTotal)) + "," +
         Clocks("\"productionTime\":\"monotonic\"") + "}";
}

// out.vehicle_control: what was applied to the simulator at this tick.
inline std::string VehicleControl(std::uint64_t frame, double throttle, double brake,
                                  double steer, bool handBrake, const char* trigger) {
  using detail::Clocks;
  using detail::Tag;
  return "{" + Tag("frame", std::to_string(frame)) + "," +
         Tag("t_sim_ms",
             std::to_string(static_cast<long long>(CaptureTimeMicros(frame)) / 1000)) + "," +
         Tag("throttle", JsonNumber(throttle)) + "," + Tag("brake", JsonNumber(brake)) + "," +
         Tag("steer", JsonNumber(steer)) + "," +
         Tag("handBrake", handBrake ? "true" : "false") + "," +
         Tag("trigger", JsonString(trigger != nullptr ? trigger : "")) + "," +
         Tag("controlSource", JsonString("actuationAdapter")) + "," +
         Clocks("\"t_sim_ms\":\"simulation\"") + "}";
}

// out.actuation_state: the payload as published, field for field.
inline std::string ActuationState(const ActuationStatePayload& state, const char* causeName) {
  using detail::Clocks;
  using detail::FixedField;
  using detail::Tag;
  return "{" + Tag("applied", std::to_string(static_cast<unsigned>(state.applied))) + "," +
         Tag("stopInForce", std::to_string(static_cast<unsigned>(state.stopInForce))) + "," +
         Tag("cause", JsonString(causeName != nullptr ? causeName : "")) + "," +
         Tag("acceleration", JsonNumber(state.acceleration)) + "," +
         Tag("steeringAngle", JsonNumber(state.steeringAngle)) + "," +
         Tag("actuationTime", JsonNumber(state.actuationTime)) + "," +
         Tag("stopSince", JsonNumber(state.stopSince)) + "," +
         Tag("stopSinceMono", JsonNumber(state.stopSinceMono)) + "," +
         Tag("planReference", JsonString(FixedField(state.planReference, kIdLength))) + "," +
         Clocks("\"actuationTime\":\"simulation\",\"stopSince\":\"simulation\","
                "\"stopSinceMono\":\"monotonic\"") +
         "}";
}

// stop_response.begin: the adapter's own stop starts here.
inline std::string StopResponseBegin(const ActuationStatePayload& state, const char* causeName) {
  using detail::Clocks;
  using detail::Tag;
  return "{" + Tag("cause", JsonString(causeName != nullptr ? causeName : "")) + "," +
         Tag("actuationTime", JsonNumber(state.actuationTime)) + "," +
         Tag("stopSinceMono", JsonNumber(state.stopSinceMono)) + "," +
         Tag("acceleration", JsonNumber(state.acceleration)) + "," +
         Tag("steeringAngle", JsonNumber(state.steeringAngle)) + "," +
         Clocks("\"actuationTime\":\"simulation\",\"stopSinceMono\":\"monotonic\"") + "}";
}

// stop_response.standstill: the stop reached the standstill threshold.
inline std::string StopResponseStandstill(std::uint64_t frame, double speedMps,
                                          const char* causeName) {
  using detail::Clocks;
  using detail::Tag;
  return "{" + Tag("cause", JsonString(causeName != nullptr ? causeName : "")) + "," +
         Tag("frame", std::to_string(frame)) + "," +
         Tag("t_sim_ms",
             std::to_string(static_cast<long long>(CaptureTimeMicros(frame)) / 1000)) + "," +
         Tag("speedMps", JsonNumber(speedMps)) + "," +
         Clocks("\"t_sim_ms\":\"simulation\"") + "}";
}

}  // namespace de4sdv::driving::log
