// DE4SDV INC-AEBS-010 ingress validator tests.
//
// Host-runnable via AOSP atest (De4sdvAebsIngressValidatorTest); also
// compilable standalone against any protobuf-generated headers for quick
// local checks. Expected results mirror the Python FrameValidator tests.

#include <gtest/gtest.h>

#include "validator.h"
#include "aebs_visualization.pb.h"

namespace {

using de4sdv::aebs_visualization::aebs_visualization::ValidationResult;
using de4sdv::aebs_visualization::aebs_visualization::validate_frame;
using de4sdv::aebs_visualization::v1::FieldValue;
using de4sdv::aebs_visualization::v1::VisualizationFrame;

constexpr int64_t kNowNs = 1'000'000'300;
constexpr int64_t kMaxFutureSkewNs = 100'000'000;
constexpr int64_t kStaleTimeoutNs = 1'000'000'000;

VisualizationFrame ValidFrame() {
  VisualizationFrame frame;
  frame.set_schema_major(1);
  frame.set_schema_minor(0);
  frame.set_sequence(1);
  frame.set_frame_timestamp_ns(1'000'000'200);
  frame.set_bridge_receipt_timestamp_ns(1'000'000'250);
  frame.set_source_identity("de4sdv_aebs_010_bridge");
  auto* rss = frame.mutable_rss_distance();
  rss->set_source_kind(de4sdv::aebs_visualization::v1::SOURCE_KIND_NATIVE_AUTOWARE_AEB);
  rss->set_source_timestamp_ns(1'000'000'000);
  rss->set_units("m");
  rss->set_coordinate_frame("base_link");
  rss->set_numeric_value(12.5);
  return frame;
}

TEST(AebsIngressValidator, AcceptsValidFrame) {
  const ValidationResult result = validate_frame(ValidFrame(), 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_TRUE(result.accepted) << result.reason;
}

TEST(AebsIngressValidator, RejectsUnsupportedSchemaMajor) {
  VisualizationFrame frame = ValidFrame();
  frame.set_schema_major(99);
  const ValidationResult result = validate_frame(frame, 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("schema"), std::string::npos);
}

TEST(AebsIngressValidator, RejectsNonMonotonicSequence) {
  const ValidationResult result = validate_frame(ValidFrame(), 5, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("sequence"), std::string::npos);
}

TEST(AebsIngressValidator, RejectsStaleTimestamp) {
  VisualizationFrame frame = ValidFrame();
  frame.set_frame_timestamp_ns(1'000'000'200 - 2'000'000'000);
  const ValidationResult result = validate_frame(frame, 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("older"), std::string::npos);
}

TEST(AebsIngressValidator, RejectsFutureTimestamp) {
  VisualizationFrame frame = ValidFrame();
  frame.set_frame_timestamp_ns(kNowNs + 500'000'000);
  const ValidationResult result = validate_frame(frame, 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("future"), std::string::npos);
}

TEST(AebsIngressValidator, RejectsNegativeNumericField) {
  VisualizationFrame frame = ValidFrame();
  frame.mutable_rss_distance()->set_numeric_value(-1.0);
  const ValidationResult result = validate_frame(frame, 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("invalid"), std::string::npos);
}

TEST(AebsIngressValidator, RejectsNonFiniteNumericField) {
  VisualizationFrame frame = ValidFrame();
  frame.mutable_rss_distance()->set_numeric_value(std::nan(""));
  const ValidationResult result = validate_frame(frame, 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
}

}  // namespace
