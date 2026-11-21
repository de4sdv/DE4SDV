// DE4SDV driver-assistance bench (INC-DRIVING-002): the injected warning requests of P10-3.
//
// Brief risk R1: the candidate at the pin may give no warning request in a judged run, so the warning path's timing
// and REQ-DRIVING-043's matching are exercised by injected requests on the candidate's own mw::com event
// (MAP-DRIVING-DA-WARNING-REQUEST), evidence of the path, not of the candidate. This is the sequence of those
// requests: one send per line, at an offset from the start of the sequence, with its requested value and issue time.
//
// The file: one "<offset_s> <true|false|1|0> <issue_time_sim_s>" per line; '#' starts a comment. The offsets rise
// strictly. Each issue time is a simulation time as the candidate would give it (whole milliseconds at the 0.05 s
// step); no two sends share one, so every receipt on the guest matches one send by its bytes. Each one must be
// encodable as the 8 SOME/IP bytes of payloads.h (EncodeWarningRequestSomeip).
#pragma once

#include <cstddef>
#include <cstdint>
#include <string>
#include <vector>

namespace de4sdv::driver_assistance::injector {

struct PlannedRequest {
  double offset_s = 0.0;
  bool requested = false;
  double issue_time_sim_s = 0.0;
  std::uint32_t issue_time_sim_ms = 0;
  std::uint8_t bytes[8] = {};
};

struct InjectionPlan {
  std::vector<PlannedRequest> requests;
  std::size_t rising_edges = 0;   // a true after a false (or first)
  std::size_t falling_edges = 0;  // a false after a true
};

// False, with "line <n>: <reason>", on the first bad line.
bool ParsePlan(const std::string& text, InjectionPlan* plan, std::string* error);

std::string HexBytes(const std::uint8_t* bytes, std::size_t size);

}  // namespace de4sdv::driver_assistance::injector
