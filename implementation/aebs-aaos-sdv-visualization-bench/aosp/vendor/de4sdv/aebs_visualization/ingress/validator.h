// DE4SDV INC-AEBS-010 ingress validator interface.
//
// The validation contract mirrors the Python FrameValidator in the bridge
// (implementation/aebs-aaos-sdv-visualization-bench/src/de4sdv_aebs_010_bridge/
// de4sdv_aebs_010_bridge/frame_assembler.py). Field semantics come from the
// SysML model; this header adds none.

#pragma once

#include <cstdint>
#include <string>

// Forward declarations of the generated protobuf types
// (de4sdv.aebs_visualization.v1). Generated at build time from
// implementation/aebs-aaos-sdv-visualization-bench/interface/aebs_visualization.proto.
namespace de4sdv {
namespace aebs_visualization {
namespace v1 {
class VisualizationFrame;
class FieldValue;
}  // namespace v1

// Aliased for validator use; the .cc includes the generated header.
namespace aebs_visualization {
using v1::VisualizationFrame;
using v1::FieldValue;

struct ValidationResult {
  bool accepted = false;
  std::string reason;
};

ValidationResult validate_frame(const VisualizationFrame& frame,
                                uint64_t last_accepted_sequence,
                                int64_t now_ns,
                                int64_t max_future_skew_ns,
                                int64_t stale_timeout_ns);

}  // namespace aebs_visualization
}  // namespace de4sdv
