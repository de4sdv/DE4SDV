// Unit tests of the speed translation of the pure adapter core: the km/h
// sample of the reference vehicle speed becomes the float32 longitudinal
// velocity in m/s, and a sample that cannot give a finite float32 value is
// withheld (REQ-MW-010, REQ-MW-011).

#include <gtest/gtest.h>

#include <cfloat>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <limits>

#include "de4sdv_score_adapter/speed_translation.hpp"

namespace {

using de4sdv::score_adapter::TranslateSpeed;
using de4sdv::score_adapter::TranslationOutcome;

std::uint32_t Bits(float value) {
  std::uint32_t bits = 0;
  std::memcpy(&bits, &value, sizeof(bits));
  return bits;
}

TEST(SpeedTranslation, ThirtySixKilometresPerHourGiveTenMetresPerSecondBitExact) {
  const auto result = TranslateSpeed(36.0);
  ASSERT_EQ(result.outcome, TranslationOutcome::kPublish);
  EXPECT_EQ(Bits(result.longitudinal_velocity_mps), Bits(10.0F));
}

TEST(SpeedTranslation, SeventyTwoKilometresPerHourGiveTwentyMetresPerSecondBitExact) {
  const auto result = TranslateSpeed(72.0);
  ASSERT_EQ(result.outcome, TranslationOutcome::kPublish);
  EXPECT_EQ(Bits(result.longitudinal_velocity_mps), Bits(20.0F));
}

TEST(SpeedTranslation, DividesByThreePointSixInDoubleBeforeTheFloatConversion) {
  const double speed_kmh = 50.0;
  const auto result = TranslateSpeed(speed_kmh);
  ASSERT_EQ(result.outcome, TranslationOutcome::kPublish);
  EXPECT_EQ(Bits(result.longitudinal_velocity_mps), Bits(static_cast<float>(speed_kmh / 3.6)));
}

TEST(SpeedTranslation, NotANumberIsWithheld) {
  const auto result = TranslateSpeed(std::numeric_limits<double>::quiet_NaN());
  EXPECT_EQ(result.outcome, TranslationOutcome::kWithheldNonFinite);
}

TEST(SpeedTranslation, PositiveInfinityIsWithheld) {
  const auto result = TranslateSpeed(std::numeric_limits<double>::infinity());
  EXPECT_EQ(result.outcome, TranslationOutcome::kWithheldNonFinite);
}

TEST(SpeedTranslation, NegativeInfinityIsWithheld) {
  const auto result = TranslateSpeed(-std::numeric_limits<double>::infinity());
  EXPECT_EQ(result.outcome, TranslationOutcome::kWithheldNonFinite);
}

TEST(SpeedTranslation, FiniteSampleBeyondTheFloat32RangeIsWithheldNotPublishedAsInfinity) {
  const auto result = TranslateSpeed(1.0e300);
  EXPECT_EQ(result.outcome, TranslationOutcome::kWithheldOutOfRange);
  const auto negative = TranslateSpeed(-1.0e300);
  EXPECT_EQ(negative.outcome, TranslationOutcome::kWithheldOutOfRange);
}

TEST(SpeedTranslation, LargestValueInsideTheFloat32RangeIsPublishedFinite) {
  const double speed_kmh = static_cast<double>(FLT_MAX) * 3.6 * (1.0 - 1.0e-12);
  const auto result = TranslateSpeed(speed_kmh);
  ASSERT_EQ(result.outcome, TranslationOutcome::kPublish);
  EXPECT_TRUE(std::isfinite(result.longitudinal_velocity_mps));
}

TEST(SpeedTranslation, NegativeFiniteSampleIsPublished) {
  const auto result = TranslateSpeed(-18.0);
  ASSERT_EQ(result.outcome, TranslationOutcome::kPublish);
  EXPECT_EQ(Bits(result.longitudinal_velocity_mps), Bits(-5.0F));
}

TEST(SpeedTranslation, ZeroKeepsItsSign) {
  EXPECT_EQ(Bits(TranslateSpeed(0.0).longitudinal_velocity_mps), Bits(0.0F));
  EXPECT_EQ(Bits(TranslateSpeed(-0.0).longitudinal_velocity_mps), Bits(-0.0F));
}

TEST(SpeedTranslation, WithheldResultCarriesNoValue) {
  const auto result = TranslateSpeed(std::numeric_limits<double>::quiet_NaN());
  EXPECT_EQ(Bits(result.longitudinal_velocity_mps), Bits(0.0F));
}

}  // namespace
