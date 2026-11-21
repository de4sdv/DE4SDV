// The test publisher of the warning request (injector_shell.h). C++17.
#include "injector_shell.h"

#include <cstdint>
#include <string>

namespace de4sdv::driver_assistance::injector {

namespace {

using ::de4sdv::driver_assistance::JsonNumber;
using ::de4sdv::driver_assistance::JsonString;

std::string Tag(const char* name, const std::string& value) { return "\"" + std::string(name) + "\":" + value; }

}  // namespace

int Inject(const InjectionPlan& plan, const InjectionOptions& options, WarningSink* sink, const Clocks& clocks,
           RecordSink* log) {
  std::uint64_t seq = 0;
  std::string error;
  if (!sink->Offer(&error)) {
    log->Write("error", ++seq, "{" + Tag("stage", JsonString("offer")) + "," + Tag("reason", JsonString(error)) + "}");
    return kOfferFailed;
  }
  const std::int64_t offered_mono = clocks.mono_ns();
  const std::int64_t start_mono = offered_mono + static_cast<std::int64_t>(options.lead_in_s * 1e9);
  log->Write("offer", ++seq,
             "{" + Tag("offered_mono_ns", std::to_string(offered_mono)) + "," +
                 Tag("sequence_start_mono_ns", std::to_string(start_mono)) + "," +
                 Tag("requests", std::to_string(plan.requests.size())) + "," +
                 Tag("rising_edges", std::to_string(plan.rising_edges)) + "," +
                 Tag("falling_edges", std::to_string(plan.falling_edges)) + "}");
  int status = kInjected;
  std::size_t sent = 0;
  for (std::size_t i = 0; i < plan.requests.size(); ++i) {
    const PlannedRequest& r = plan.requests[i];
    const std::int64_t due = start_mono + static_cast<std::int64_t>(r.offset_s * 1e9);
    if (!clocks.sleep_until(due)) {
      status = kStopped;
      break;
    }
    const std::int64_t before_mono = clocks.mono_ns();
    const std::int64_t before_real = clocks.real_ns();
    const bool ok = sink->Send(r.bytes, sizeof r.bytes);
    const std::int64_t after_mono = clocks.mono_ns();
    const std::int64_t after_real = clocks.real_ns();
    if (ok) ++sent;
    log->Write("out.warning_request", ++seq,
               "{" + Tag("index", std::to_string(i)) + "," + Tag("requested", r.requested ? "true" : "false") + "," +
                   Tag("issueTime_sim_s", JsonNumber(r.issue_time_sim_s)) + "," +
                   Tag("issue_time_sim_ms", std::to_string(r.issue_time_sim_ms)) + "," +
                   Tag("bytes", JsonString(HexBytes(r.bytes, sizeof r.bytes))) + "," +
                   Tag("planned_mono_ns", std::to_string(due)) + "," +
                   Tag("send_mono_ns", std::to_string(before_mono)) + "," +
                   Tag("send_real_ns", std::to_string(before_real)) + "," +
                   Tag("sent_mono_ns", std::to_string(after_mono)) + "," +
                   Tag("sent_real_ns", std::to_string(after_real)) + "," + Tag("ok", ok ? "true" : "false") + "}");
    if (!ok) status = kSendFailed;
  }
  if (status != kStopped) {
    const std::int64_t end = clocks.mono_ns() + static_cast<std::int64_t>(options.tail_s * 1e9);
    clocks.sleep_until(end);
  }
  sink->StopOffer();
  log->Write("stop", ++seq,
             "{" + Tag("sent", std::to_string(sent)) + "," + Tag("planned", std::to_string(plan.requests.size())) +
                 "," + Tag("status", std::to_string(status)) + "}");
  return status;
}

}  // namespace de4sdv::driver_assistance::injector
