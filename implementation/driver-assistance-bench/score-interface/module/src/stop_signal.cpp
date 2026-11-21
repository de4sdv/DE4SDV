// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot). See stop_signal.hpp.
#include "de4sdv/score_interface/stop_signal.hpp"

#include <signal.h>

#include <csignal>
#include <cstring>

namespace de4sdv::score_interface {

namespace {

volatile std::sig_atomic_t g_stop = 0;

extern "C" void OnStopSignal(int /*signal*/) { g_stop = 1; }

}  // namespace

bool InstallStopHandler() {
  struct sigaction action;
  std::memset(&action, 0, sizeof action);
  action.sa_handler = OnStopSignal;
  sigemptyset(&action.sa_mask);
  action.sa_flags = 0;  // no SA_RESTART: a blocking call returns EINTR and the loop gets to the flag
  return sigaction(SIGTERM, &action, nullptr) == 0;
}

bool StopRequested() { return g_stop != 0; }

}  // namespace de4sdv::score_interface
