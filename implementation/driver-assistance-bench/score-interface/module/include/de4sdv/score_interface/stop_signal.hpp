// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// A clean exit from the main loop on SIGTERM, the signal the Launch Manager stops a process with. At the pin only
// video mode leaves the loop (vision_pilot.cpp:120); with this flag the loop breaks and upstream's shutdown after
// it runs, Rerun::shutdown() among it (vision_pilot.cpp:189). The handler only sets a flag.
#pragma once

namespace de4sdv::score_interface {

// Installs the SIGTERM handler. Returns false if sigaction fails.
bool InstallStopHandler();

// True once SIGTERM arrived after InstallStopHandler(). Async-signal-safe to set, cheap to read.
bool StopRequested();

}  // namespace de4sdv::score_interface
