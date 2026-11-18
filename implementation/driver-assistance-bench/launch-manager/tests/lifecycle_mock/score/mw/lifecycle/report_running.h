// Test-only declarations, not S-CORE code: the public API of score/mw/lifecycle/report_running.h at
// eclipse-score/lifecycle v0.10.0 (2afae116, score/launch_manager/src/lifecycle_client/src/report_running.h), for a
// syntax check on the host. The real header comes from //score/launch_manager:lifecycle_cc in the S-CORE Bazel build.
#pragma once

#include <cstdint>

namespace score::mw::lifecycle {
void report_running() noexcept;
}  // namespace score::mw::lifecycle

extern "C" {
std::int8_t score_mw_lifecycle_report_running(void);  // int8_t in upstream's C declaration
}
