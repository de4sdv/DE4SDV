// DE4SDV S-CORE interface for VisionPilot (INC-DRIVING-002, not part of upstream VisionPilot).
//
// The warm start of the candidate under S-CORE (patch 0005, decision D-S1-1 of the S1 build plan). The module's
// attach waits for the world's first tick, the go, and from then on the world sends an image every 0.1 s. In
// attempt 3 (SID 20261120T092051Z) the pipeline's construction (about 0.55 s) and the cold first inference (724 ms
// on the L4) both ran after the attach, so 11 to 12 images per run were dropped in the first 1.3 s after the go.
// WarmStart() runs the pipeline on a dummy image until one pass gives a result (the networks ran once), puts the
// pipeline back to its fresh state, and only then starts the module. So the first image of the run still gives no
// result (upstream's two-frame buffer), nothing of the dummy reaches a plan, and the candidate reports running at its
// first pass with a result, as before (CycleSupervision in core.hpp).
#pragma once

#include <cstdint>

#include "de4sdv/score_interface/core.hpp"

namespace de4sdv::score_interface {

// What the warm start did, for the candidate's log line.
struct WarmStartRecord {
  int passes = 0;                  // passes of the pipeline on the dummy image
  bool result = false;             // one of them gave a result: the networks ran once
  std::int64_t begin_mono_ns = 0;  // before the first pass
  std::int64_t end_mono_ns = 0;    // after the reset, before the start
};

// Upstream's pipeline gives its first result at the second pass (inference.cpp:152-159 at the pin); one more pass is
// the margin. A pipeline that gives none by then starts cold, as without the warm start.
inline constexpr int kWarmStartMaxPasses = 3;

// pass():  one pass of the pipeline on the dummy image; true when it gave a result.
// reset(): the pipeline back to its fresh state (InferencePipeline::reset()).
// start(): the module's start; its attach waits for the go. Called once, after the reset, whatever the passes gave.
// Returns what start() returns; *record (when given) gets the passes and the times.
template <typename Pass, typename Reset, typename Start>
auto WarmStart(Pass&& pass, Reset&& reset, Start&& start, WarmStartRecord* record) -> decltype(start()) {
  WarmStartRecord r;
  r.begin_mono_ns = MonotonicNs();
  while (!r.result && r.passes < kWarmStartMaxPasses) {
    ++r.passes;
    r.result = pass();
  }
  reset();
  r.end_mono_ns = MonotonicNs();
  if (record != nullptr) *record = r;
  return start();
}

}  // namespace de4sdv::score_interface
