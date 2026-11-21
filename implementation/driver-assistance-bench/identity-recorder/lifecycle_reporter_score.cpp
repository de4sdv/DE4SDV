// The identity recorder's lifecycle client on S-CORE Lifecycle v0.10.0 (eclipse-score/lifecycle 2afae116):
// score_mw_lifecycle_report_running() from //score/launch_manager:lifecycle_cc. The component is of type Reporting
// (launch-manager/config/launch_manager_config.json), so the Launch Manager waits for this report before it starts
// the candidate's process and the actuation adapter. A Reporting component gets no alive supervision, so no
// LCM_ALIVE_INTERFACE_PATH and no Alive instance here. Only the S-CORE Bazel build compiles this unit; the host's
// tests check it for syntax against ../launch-manager/tests/lifecycle_mock.
#include <cstdint>
#include <memory>
#include <string>

#include "recorder_shell.h"
#include "score/mw/lifecycle/report_running.h"

namespace de4sdv::driver_assistance::identity {

namespace {

class ScoreLifecycleReporter final : public LifecycleReporter {
 public:
  bool ReportRunning() override { return score_mw_lifecycle_report_running() == 0; }
};

}  // namespace

std::unique_ptr<LifecycleReporter> MakeLifecycleReporter(std::string* off_reason) {
  off_reason->clear();
  return std::make_unique<ScoreLifecycleReporter>();
}

}  // namespace de4sdv::driver_assistance::identity
