// The injected warning requests' plan (injection_plan.h). C++17.
#include "injection_plan.h"

#include <cmath>
#include <cstdint>
#include <cstdlib>
#include <set>
#include <sstream>
#include <string>

#include "de4sdv/driver_assistance/payloads.h"

namespace de4sdv::driver_assistance::injector {

namespace {

bool ParseDouble(const std::string& text, double* out) {
  if (text.empty()) return false;
  char* end = nullptr;
  const double v = std::strtod(text.c_str(), &end);
  if (end == nullptr || *end != '\0' || !std::isfinite(v)) return false;
  *out = v;
  return true;
}

}  // namespace

bool ParsePlan(const std::string& text, InjectionPlan* plan, std::string* error) {
  InjectionPlan result;
  std::set<std::uint32_t> issue_times;
  std::istringstream lines(text);
  std::string line;
  int number = 0;
  bool have_previous = false;
  bool previous_requested = false;
  while (std::getline(lines, line)) {
    ++number;
    const std::size_t hash = line.find('#');
    if (hash != std::string::npos) line.erase(hash);
    std::istringstream fields(line);
    std::string offset, value, issue, extra;
    if (!(fields >> offset)) continue;  // blank or comment
    const std::string where = "line " + std::to_string(number) + ": ";
    if (!(fields >> value >> issue) || (fields >> extra)) {
      *error = where + "expected <offset_s> <true|false> <issue_time_sim_s>";
      return false;
    }
    PlannedRequest r;
    if (!ParseDouble(offset, &r.offset_s) || r.offset_s < 0.0) {
      *error = where + "the offset is not a number of seconds from 0";
      return false;
    }
    if (!result.requests.empty() && !(r.offset_s > result.requests.back().offset_s)) {
      *error = where + "the offsets must rise strictly";
      return false;
    }
    if (value == "true" || value == "1") {
      r.requested = true;
    } else if (value == "false" || value == "0") {
      r.requested = false;
    } else {
      *error = where + "requested must be true, false, 1 or 0";
      return false;
    }
    if (!ParseDouble(issue, &r.issue_time_sim_s)) {
      *error = where + "the issue time is not a number";
      return false;
    }
    const WarningRequest w{r.requested, r.issue_time_sim_s};
    if (!EncodeWarningRequestSomeip(w, r.bytes)) {
      *error = where + "the issue time cannot be carried as 32-bit milliseconds";
      return false;
    }
    r.issue_time_sim_ms = (static_cast<std::uint32_t>(r.bytes[4]) << 24) |
                          (static_cast<std::uint32_t>(r.bytes[5]) << 16) |
                          (static_cast<std::uint32_t>(r.bytes[6]) << 8) | static_cast<std::uint32_t>(r.bytes[7]);
    if (!issue_times.insert(r.issue_time_sim_ms).second) {
      *error = where + "issue time " + std::to_string(r.issue_time_sim_ms) +
               " ms is used twice: a receipt could not be matched to one send";
      return false;
    }
    if (r.requested && (!have_previous || !previous_requested)) ++result.rising_edges;
    if (!r.requested && have_previous && previous_requested) ++result.falling_edges;
    have_previous = true;
    previous_requested = r.requested;
    result.requests.push_back(r);
  }
  if (result.requests.empty()) {
    *error = "the plan holds no request";
    return false;
  }
  *plan = result;
  return true;
}

std::string HexBytes(const std::uint8_t* bytes, std::size_t size) {
  static const char* const kHex = "0123456789abcdef";
  std::string out;
  for (std::size_t i = 0; i < size; ++i) {
    out += kHex[bytes[i] >> 4];
    out += kHex[bytes[i] & 0xF];
  }
  return out;
}

}  // namespace de4sdv::driver_assistance::injector
