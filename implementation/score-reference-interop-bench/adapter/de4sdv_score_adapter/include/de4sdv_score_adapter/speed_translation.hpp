// Pure core of the AutowareToSCORE adapter: the speed translation.
//
// The reference vehicle speed arrives as speed_kmh (double, km/h). The
// adapter publishes it as the float32 longitudinal_velocity of an Autoware
// VelocityReport in m/s: speed_kmh / 3.6 (REQ-MW-010). A sample that cannot
// give a finite float32 value is withheld and counted, never published
// (REQ-MW-011). No ROS 2 or S-CORE header is needed here.

#ifndef DE4SDV_SCORE_ADAPTER_SPEED_TRANSLATION_HPP
#define DE4SDV_SCORE_ADAPTER_SPEED_TRANSLATION_HPP

namespace de4sdv::score_adapter {

enum class TranslationOutcome {
  kPublish,             // finite sample, finite float32 value
  kWithheldNonFinite,   // NaN, +inf or -inf sample (REQ-MW-011)
  kWithheldOutOfRange,  // finite sample whose m/s value is outside the float32 range
};

struct Translation {
  TranslationOutcome outcome;
  // Set only for kPublish; 0.0F otherwise.
  float longitudinal_velocity_mps;
};

Translation TranslateSpeed(double speed_kmh) noexcept;

}  // namespace de4sdv::score_adapter

#endif  // DE4SDV_SCORE_ADAPTER_SPEED_TRANSLATION_HPP
