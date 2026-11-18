// The actuation adapter's alive supervision; see alive_ticker.h.
#include "alive_ticker.h"

#include <cstdint>
#include <string>

#include "run_log.h"

namespace de4sdv::driver_assistance::actuation {

namespace {

// Two passes that the floating-point sum of periods puts 1 ns apart count as the same instant.
constexpr double kSlackS = 1e-9;

std::string Field(const char* name, const std::string& value) {
  return "\"" + std::string(name) + "\":" + value;
}

}  // namespace

AliveTicker::AliveTicker(LifecycleClient* client, double periodS, RecordWriter* records)
    : client_(client), periodS_(periodS), records_(records) {}

bool AliveTicker::Start(double nowMonoS, const std::string& offReason) {
  if (started_ || stopped_) return false;
  started_ = true;
  if (client_ == nullptr) {
    records_->Write("supervision", "{" + Field("state", JsonString("off")) + "," +
                                       Field("reason", JsonString(offReason)) + "," +
                                       Field("t_mono_s", JsonNumber(nowMonoS)) + "}");
    return true;
  }
  const bool running = client_->ReportRunning();
  if (running) {
    records_->Write("supervision", "{" + Field("state", JsonString("start")) + "," +
                                       Field("period_s", JsonNumber(periodS_)) + "," +
                                       Field("running_reported", "true") + "," +
                                       Field("t_mono_s", JsonNumber(nowMonoS)) + "}");
  } else {
    records_->Write("supervision", "{" + Field("state", JsonString("error")) + "," +
                                       Field("reason", JsonString("report_running failed")) + "," +
                                       Field("t_mono_s", JsonNumber(nowMonoS)) + "}");
  }
  Report(nowMonoS);
  nextDueMonoS_ = nowMonoS + periodS_;
  return running;
}

void AliveTicker::Tick(double nowMonoS, bool stopRequested) {
  if (stopRequested) stopped_ = true;
  if (!started_ || stopped_ || client_ == nullptr) return;
  if (nowMonoS + kSlackS < nextDueMonoS_) return;
  Report(nowMonoS);
  nextDueMonoS_ += periodS_;
  if (nowMonoS + kSlackS >= nextDueMonoS_) nextDueMonoS_ = nowMonoS + periodS_;  // after a stall: no burst
}

void AliveTicker::Stop(double nowMonoS) {
  stopped_ = true;
  if (!started_ || client_ == nullptr || stopRecorded_) return;
  stopRecorded_ = true;
  records_->Write("supervision", "{" + Field("state", JsonString("stop")) + "," +
                                     Field("alive_reported", std::to_string(alive_)) + "," +
                                     Field("t_mono_s", JsonNumber(nowMonoS)) + "}");
}

void AliveTicker::Report(double /*nowMonoS*/) {
  client_->ReportAlive();
  ++alive_;
}

}  // namespace de4sdv::driver_assistance::actuation
