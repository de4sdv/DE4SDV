// DE4SDV INC-AEBS-010 ingress validator tests.
//
// Runs via AOSP atest (De4sdvAebsIngressValidatorTest). Expected results
// mirror the Python FrameValidator tests in
// src/de4sdv_aebs_010_bridge/test/test_frame_assembler.py.

#include <gtest/gtest.h>

#include "validator.h"

namespace {

using de4sdv_aebs010::ValidationResult;
using de4sdv_aebs010::validate_frame;
using de4sdv::aebs_visualization::v1::FieldValue;
using de4sdv::aebs_visualization::v1::SourceKind;
using de4sdv::aebs_visualization::v1::VisualizationFrame;

constexpr int64_t kNowNs = 1'000'000'300;
constexpr int64_t kMaxFutureSkewNs = 100'000'000;
constexpr int64_t kStaleTimeoutNs = 1'000'000'000;

FieldValue NativeRss(double value) {
  FieldValue field;
  field.set_source_kind(SourceKind::SOURCE_KIND_NATIVE_AUTOWARE_AEB);
  field.set_source_timestamp_ns(1'000'000'000);
  field.set_units("m");
  field.set_coordinate_frame("base_link");
  field.set_numeric_value(value);
  return field;
}

VisualizationFrame ValidFrame() {
  VisualizationFrame frame;
  frame.set_schema_major(1);
  frame.set_schema_minor(0);
  frame.set_sequence(1);
  frame.set_frame_timestamp_ns(1'000'000'200);
  frame.set_bridge_receipt_timestamp_ns(1'000'000'250);
  frame.set_source_identity("de4sdv_aebs_010_bridge");
  *frame.mutable_rss_distance() = NativeRss(12.5);
  return frame;
}

TEST(AebsIngressValidator, AcceptsValidFrame) {
  const ValidationResult result =
      validate_frame(ValidFrame(), 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_TRUE(result.accepted) << result.reason;
}

TEST(AebsIngressValidator, RejectsUnsupportedSchemaMajor) {
  VisualizationFrame frame = ValidFrame();
  frame.set_schema_major(99);
  const ValidationResult result =
      validate_frame(frame, 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("schema"), std::string::npos);
}

TEST(AebsIngressValidator, RejectsNonMonotonicSequence) {
  const ValidationResult result =
      validate_frame(ValidFrame(), 5, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("sequence"), std::string::npos);
}

TEST(AebsIngressValidator, RejectsStaleTimestamp) {
  VisualizationFrame frame = ValidFrame();
  frame.set_frame_timestamp_ns(1'000'000'200 - 2'000'000'000);
  const ValidationResult result =
      validate_frame(frame, 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("older"), std::string::npos);
}

TEST(AebsIngressValidator, RejectsFutureTimestamp) {
  VisualizationFrame frame = ValidFrame();
  frame.set_frame_timestamp_ns(kNowNs + 500'000'000);
  const ValidationResult result =
      validate_frame(frame, 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("future"), std::string::npos);
}

TEST(AebsIngressValidator, RejectsNegativeNumericField) {
  VisualizationFrame frame = ValidFrame();
  frame.mutable_rss_distance()->set_numeric_value(-1.0);
  const ValidationResult result =
      validate_frame(frame, 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
  EXPECT_NE(result.reason.find("invalid"), std::string::npos);
}

TEST(AebsIngressValidator, RejectsNonFiniteNumericField) {
  VisualizationFrame frame = ValidFrame();
  frame.mutable_rss_distance()->set_numeric_value(std::nan(""));
  const ValidationResult result =
      validate_frame(frame, 0, kNowNs, kMaxFutureSkewNs, kStaleTimeoutNs);
  EXPECT_FALSE(result.accepted);
}

}  // namespace
