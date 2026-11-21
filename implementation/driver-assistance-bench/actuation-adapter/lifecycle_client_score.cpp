// The actuation adapter's lifecycle client on S-CORE Lifecycle v0.10.0
// (eclipse-score/lifecycle 2afae116): report_running from
// //score/launch_manager:lifecycle_cc and the Alive API from
// //score/launch_manager:alive_cc, in the pattern of upstream's
// examples/c_supervised_app/main.c:42-58. Only the S-CORE Bazel build compiles
// this unit; the host's tests check it for syntax against the API
// declarations in ../launch-manager/tests/lifecycle_mock.
//
// The Launch Manager sets LCM_ALIVE_INTERFACE_PATH only for a component of
// type Reporting_And_Supervised or State_Manager.
#include <cstdint>
#include <cstdlib>
#include <exception>
#include <memory>
#include <string>
#include <utility>

#include "alive_ticker.h"
#include "score/mw/lifecycle/alive.h"
#include "score/mw/lifecycle/report_running.h"

namespace de4sdv::driver_assistance::actuation {

namespace {

constexpr const char* kAliveInstance = "de4sdv/driver_assistance/actuation_adapter";  // unused by v0.10.0

class ScoreLifecycleClient final : public LifecycleClient {
 public:
  explicit ScoreLifecycleClient(std::unique_ptr<score::mw::lifecycle::Alive> alive)
      : alive_(std::move(alive)) {}
  bool ReportRunning() override { return score_mw_lifecycle_report_running() == 0; }
  void ReportAlive() override { alive_->ReportAlive(); }

 private:
  std::unique_ptr<score::mw::lifecycle::Alive> alive_;
};

}  // namespace

std::unique_ptr<LifecycleClient> MakeLifecycleClient(std::string* reason) {
  const char* path = std::getenv("LCM_ALIVE_INTERFACE_PATH");
  if (path == nullptr || path[0] == '\0') {
    *reason =
        "LCM_ALIVE_INTERFACE_PATH is unset: the Launch Manager did not start this process as a "
        "supervised component";
    return nullptr;
  }
  try {
    return std::make_unique<ScoreLifecycleClient>(
        std::make_unique<score::mw::lifecycle::Alive>(kAliveInstance));
  } catch (const std::exception& e) {
    *reason = std::string("the Alive instance failed: ") + e.what();
    return nullptr;
  }
}

}  // namespace de4sdv::driver_assistance::actuation
