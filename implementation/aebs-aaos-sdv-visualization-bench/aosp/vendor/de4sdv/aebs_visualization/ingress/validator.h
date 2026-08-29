// DE4SDV INC-AEBS-010 ingress validator interface.
//
// The validation contract mirrors the Python FrameValidator in the bridge
// (implementation/aebs-aaos-sdv-visualization-bench/src/de4sdv_aebs_010_bridge/
// de4sdv_aebs_010_bridge/frame_assembler.py). Field semantics come from the
// SysML model; this header adds none.
//
// Generated protobuf types live in ::de4sdv::aebs_visualization::v1 (the
// proto package). Include "aebs_visualization.pb.h" before this header or
// rely on the proto_lite static library exporting it.

#pragma once

#include <cstdint>
#include <string>

#include "aebs_visualization.pb.h"

namespace de4sdv_aebs010 {

struct ValidationResult {
  bool accepted = false;
  std::string reason;
};

// Validates one decoded frame against the wire contract:
// schema major, monotonic sequence, timestamp bounds, numeric sanity.
// last_accepted_sequence: highest sequence accepted so far (0 initially).
// now_ns: sink-side clock at validation time.
// max_future_skew_ns: allowed positive clock skew.
// stale_timeout_ns: frames older than this are rejected as stale.
ValidationResult validate_frame(
    const de4sdv::aebs_visualization::v1::VisualizationFrame& frame,
    uint64_t last_accepted_sequence,
    int64_t now_ns,
    int64_t max_future_skew_ns,
    int64_t stale_timeout_ns);

}  // namespace de4sdv_aebs010
