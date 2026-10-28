#include "de4sdv_someip_receiver/discard_policy.hpp"

namespace de4sdv::someip_receiver {

const char* ToText(FrameVerdict verdict) noexcept {
  switch (verdict) {
    case FrameVerdict::kDeliver:
      return "delivered";
    case FrameVerdict::kDropFieldNotPositive:
      return "field_not_positive";
    case FrameVerdict::kDropOlderThanPhase:
      return "older_than_phase";
    case FrameVerdict::kDropCopyInPhase:
      return "copy_in_phase";
  }
  return "unknown";
}

PhaseStartDiscardPolicy::PhaseStartDiscardPolicy(std::size_t copy_memory_frames)
    : served_(copy_memory_frames == 0U ? 1U : copy_memory_frames) {}

void PhaseStartDiscardPolicy::ClearMemory() noexcept {
  served_next_ = 0;
  served_count_ = 0;
}

void PhaseStartDiscardPolicy::OnPhaseStart(std::int64_t realtime_ns) {
  in_phase_ = true;
  phase_start_realtime_ns_ = realtime_ns;
  ClearMemory();
}

void PhaseStartDiscardPolicy::OnPhaseEnd() {
  in_phase_ = false;
  ClearMemory();
}

FrameVerdict PhaseStartDiscardPolicy::Admit(const FrameFields& frame) {
  if (frame.sequence == 0U || frame.frame_timestamp_ns <= 0) {
    return FrameVerdict::kDropFieldNotPositive;
  }
  if (!in_phase_ || frame.frame_timestamp_ns < phase_start_realtime_ns_ - kPhaseStartMarginNs) {
    return FrameVerdict::kDropOlderThanPhase;
  }
  for (std::size_t index = 0; index < served_count_; ++index) {
    const FrameFields& served = served_[index];
    if (served.sequence == frame.sequence && served.frame_timestamp_ns == frame.frame_timestamp_ns) {
      return FrameVerdict::kDropCopyInPhase;
    }
  }
  served_[served_next_] = frame;  // the ring forgets the oldest served frame
  served_next_ = (served_next_ + 1U) % served_.size();
  if (served_count_ < served_.size()) {
    ++served_count_;
  }
  return FrameVerdict::kDeliver;
}

}  // namespace de4sdv::someip_receiver
