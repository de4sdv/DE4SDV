// DE4SDV INC-AEBS-010 ingress frame validator (pure C++ core).
//
// Mirrors the sink-side validation contract of the Python FrameValidator:
// schema identity, monotonic sequence, timestamp bounds, and finite
// non-negative numeric values. Keep the two implementations in lockstep; a
// divergence is a validation-contract defect.

#include "validator.h"

#include <cmath>
#include <cstdint>

namespace de4sdv::aebs_visualization {

namespace {
constexpr uint32_t kSchemaMajor = 1;

bool field_value_valid(const FieldValue& value) {
  if (!value.has_value_case()) return false;
  switch (value.value_case()) {
    case FieldValue::kNumericValue:
      return std::isfinite(value.numeric_value()) && value.numeric_value() >= 0.0;
    case FieldValue::kBoolValue:
    case FieldValue::kEnumValue:
      return true;
    case FieldValue::VALUE_NOT_SET:
      return false;
  }
  return false;
}
}  // namespace

ValidationResult validate_frame(const VisualizationFrame& frame,
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
  const FieldValue* numeric_fields[] = {
      &frame.rss_distance(), &frame.target_range(), &frame.target_bearing()};
  for (const FieldValue* value : numeric_fields) {
    if (value->has_value_case() && !field_value_valid(*value)) {
      result.reason = "numeric field invalid";
      return result;
    }
  }
  result.accepted = true;
  result.reason = "ok";
  return result;
}

}  // namespace de4sdv::aebs_visualization
