// DE4SDV driver-assistance bench (INC-DRIVING-002): the test publisher of the warning request (P10-3).
//
// It sends each planned request (injection_plan.h) on the candidate's mw::com event
// de4sdv/driver_assistance/warning_request (ICD.md: service 7412), as the 8 SOME/IP bytes the candidate sends, at
// its offset after the lead-in. Each send is logged with the S-CORE host's real and monotonic clocks read right
// before and right after the send: the start of the 0.1 s path share of REQ-DRIVING-042 is the publisher's send,
// and the IVI receives on its own clock, so the evaluator needs the real time here and the clock bound of the
// session (brief R9). Evidence of the path, not of the candidate (brief R1).
//
// No middleware and no clock here: warning_injector_main.cpp gives the mw::com sink and the clocks; the tests give
// fakes.
#pragma once

#include <cstddef>
#include <cstdint>
#include <functional>
#include <string>

#include "injection_plan.h"
#include "run_log.h"

namespace de4sdv::driver_assistance::injector {

class WarningSink {
 public:
  virtual ~WarningSink() = default;
  virtual bool Offer(std::string* error) = 0;
  // The bytes as the payload of the event, data[0..size), nothing in front.
  virtual bool Send(const std::uint8_t* bytes, std::size_t size) = 0;
  virtual void StopOffer() = 0;
};

struct Clocks {
  std::function<std::int64_t()> mono_ns;
  std::function<std::int64_t()> real_ns;
  // Sleeps until the monotonic time; returns false when a stop was requested meanwhile.
  std::function<bool(std::int64_t mono_ns)> sleep_until;
};

struct InjectionOptions {
  double lead_in_s = 5.0;  // after the offer, so gatewayd finds the service and subscribes first
  double tail_s = 2.0;     // after the last send, before the offer ends
};

enum InjectStatus : int {
  kInjected = 0,
  kOfferFailed = 4,
  kSendFailed = 5,
  kStopped = 6,
};

// Runs the whole plan. Records (run_log.h): offer, out.warning_request (one per send), error, stop.
int Inject(const InjectionPlan& plan, const InjectionOptions& options, WarningSink* sink, const Clocks& clocks,
           RecordSink* log);

}  // namespace de4sdv::driver_assistance::injector
