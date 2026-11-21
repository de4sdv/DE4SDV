// The actuation adapter's alive supervision by the Launch Manager of S-CORE
// Lifecycle v0.10.0: the supervision decision of 2026-11-18. The receive loop
// of actuation_adapter_main.cpp calls Tick() on every pass; the ticker gives
// one alive notification per period of the command cycle (0.1 s), so the
// notifications show that the loop that takes the driving commands still
// runs, whether or not a command arrives. Supervision starts with Start(),
// once the adapter has subscribed to the command event: it reports the
// process running, and the Launch Manager starts supervising then. After a
// stop request no notification follows.
//
// No clock is read here: the caller passes monotonic seconds. The real
// client (lifecycle_client_score.cpp) is compiled only by the S-CORE Bazel
// build; the host's tests use a fake.
#pragma once

#include <cstdint>
#include <memory>
#include <string>

#include "adapter_shell.h"

namespace de4sdv::driver_assistance::actuation {

class LifecycleClient {
 public:
  virtual ~LifecycleClient() = default;
  // score_mw_lifecycle_report_running(): the process is ready.
  virtual bool ReportRunning() = 0;
  // score::mw::lifecycle::Alive::ReportAlive(): one alive notification; one thread only.
  virtual void ReportAlive() = 0;
};

// Defined in lifecycle_client_score.cpp. nullptr, with the reason, when the
// Launch Manager did not start this process as a supervised component
// (LCM_ALIVE_INTERFACE_PATH unset) or the Alive instance fails.
std::unique_ptr<LifecycleClient> MakeLifecycleClient(std::string* reason);

// Records (log_records.h): supervision {state: "start", period_s,
// running_reported, t_mono_s} | {state: "error", reason, t_mono_s} |
// {state: "off", reason, t_mono_s} | {state: "stop", alive_reported, t_mono_s}.
class AliveTicker {
 public:
  // client may be null: unsupervised, recorded once by Start().
  AliveTicker(LifecycleClient* client, double periodS, RecordWriter* records);

  // Reports the process running and gives the first notification. Returns
  // false when report_running fails (recorded as state "error").
  bool Start(double nowMonoS, const std::string& offReason);
  // One pass of the receive loop: a notification when the period is due.
  // After a stall, one notification and the period again, never a burst.
  void Tick(double nowMonoS, bool stopRequested);
  // No notification after it; one "stop" record.
  void Stop(double nowMonoS);

  std::uint64_t AliveCount() const { return alive_; }

 private:
  void Report(double nowMonoS);

  LifecycleClient* client_;
  double periodS_;
  RecordWriter* records_;
  bool started_ = false;
  bool stopped_ = false;
  bool stopRecorded_ = false;
  double nextDueMonoS_ = 0.0;
  std::uint64_t alive_ = 0;
};

}  // namespace de4sdv::driver_assistance::actuation
