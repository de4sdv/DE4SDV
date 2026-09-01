// DE4SDV INC-AEBS-010 ingress frame validator (pure C++ core).
//
// Mirrors the sink-side validation contract of the Python FrameValidator:
// schema identity, monotonic sequence, timestamp bounds, and finite
// non-negative numeric values. Keep the two implementations in lockstep; a
// divergence is a validation-contract defect.

#include "validator.h"

#include <cmath>
#include <cstdint>

namespace de4sdv_aebs010 {

namespace {
constexpr uint32_t kSchemaMajor = 1;

bool field_value_valid(const de4sdv::aebs_visualization::v1::FieldValue& value) {
  if (value.has_numeric_value()) {
    return std::isfinite(value.numeric_value()) && value.numeric_value() >= 0.0;
  }
  return value.has_bool_value() || value.has_enum_value();
}
}  // namespace

ValidationResult validate_frame(
    const de4sdv::aebs_visualization::v1::VisualizationFrame& frame,
    uint64_t last_accepted_sequence,
    int64_t now_ns,
    int64_t max_future_skew_ns,
    int64_t stale_timeout_ns) {
  ValidationResult result;
  if (frame.schema_major() != kSchemaMajor) {
    result.reason = "unsupported schema major";
    return result;
  }
  if (frame.sequence() <= last_accepted_sequence) {
    result.reason = "non-monotonic sequence";
    return result;
  }
  if (frame.frame_timestamp_ns() > now_ns + max_future_skew_ns) {
    result.reason = "frame timestamp in the future";
    return result;
  }
  if (now_ns - frame.frame_timestamp_ns() > stale_timeout_ns) {
    result.reason = "frame timestamp older than stale timeout";
    return result;
  }
  const de4sdv::aebs_visualization::v1::FieldValue* numeric_fields[] = {
      &frame.rss_distance(), &frame.target_range(), &frame.target_bearing(),
      &frame.ego_speed()};
  // schema_minor 1: target_points are finite, bounded cluster points.
  if (static_cast<int>(frame.target_points().size()) > 24) {
    result.reason = "target_points exceed bound";
    return result;
  }
  for (const auto& point : frame.target_points()) {
    if (!std::isfinite(point.forward_m()) || !std::isfinite(point.lateral_m()) ||
        point.forward_m() < 0.0f) {
      result.reason = "target point invalid";
      return result;
    }
  }
  for (const auto* value : numeric_fields) {
    if ((value->has_numeric_value() || value->has_bool_value() || value->has_enum_value()) &&
        !field_value_valid(*value)) {
      result.reason = "numeric field invalid";
      return result;
    }
  }
  result.accepted = true;
  result.reason = "ok";
  return result;
}

}  // namespace de4sdv_aebs010
