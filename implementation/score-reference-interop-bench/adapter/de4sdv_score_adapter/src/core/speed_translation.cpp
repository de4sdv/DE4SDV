#include "de4sdv_score_adapter/speed_translation.hpp"

#include <cfloat>
#include <cmath>

namespace de4sdv::score_adapter {

Translation TranslateSpeed(double speed_kmh) noexcept {
  if (!std::isfinite(speed_kmh)) {
    return {TranslationOutcome::kWithheldNonFinite, 0.0F};
  }
  const double speed_mps = speed_kmh / 3.6;
  // A double outside the float32 range would convert to an infinity; such a
  // value is withheld like a non-finite sample.
  if (std::fabs(speed_mps) > static_cast<double>(FLT_MAX)) {
    return {TranslationOutcome::kWithheldOutOfRange, 0.0F};
  }
  return {TranslationOutcome::kPublish, static_cast<float>(speed_mps)};
}

}  // namespace de4sdv::score_adapter
