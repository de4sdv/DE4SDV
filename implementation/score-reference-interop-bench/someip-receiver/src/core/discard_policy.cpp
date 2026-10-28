#include "de4sdv_someip_receiver/discard_policy.hpp"

namespace de4sdv::someip_receiver {

const char* ToText(PhaseCause cause) noexcept {
  switch (cause) {
    case PhaseCause::kSubscriptionAcknowledged:
      return "subscription_acknowledged";
    case PhaseCause::kClientConnected:
      return "client_connected";
  }
  return "unknown";
}

const char* ToText(FrameVerdict verdict) noexcept {
  switch (verdict) {
    case FrameVerdict::kDeliver:
      return "delivered";
    case FrameVerdict::kDropSequenceNotIncreasing:
      return "sequence_not_increasing";
    case FrameVerdict::kDropOlderThanPhase:
      return "older_than_phase";
  }
  return "unknown";
}

ProvisionalDiscardPolicy::ProvisionalDiscardPolicy(std::int64_t clock_offset_bound_ns)
    : clock_offset_bound_ns_{clock_offset_bound_ns < 0 ? 0 : clock_offset_bound_ns} {}

void ProvisionalDiscardPolicy::OnPhaseStart(PhaseCause cause, std::int64_t realtime_ns) {
  in_phase_ = true;
  phase_start_realtime_ns_ = realtime_ns;
  if (cause == PhaseCause::kClientConnected) {
    last_delivered_sequence_ = 0;  // the new client has received no frame
  }
}

FrameVerdict ProvisionalDiscardPolicy::Admit(const FrameFields& frame) {
  if (!in_phase_) {
    return FrameVerdict::kDropOlderThanPhase;
  }
  if (frame.sequence <= last_delivered_sequence_) {
    return FrameVerdict::kDropSequenceNotIncreasing;
  }
  if (frame.frame_timestamp_ns < phase_start_realtime_ns_ - clock_offset_bound_ns_) {
    return FrameVerdict::kDropOlderThanPhase;
  }
  last_delivered_sequence_ = frame.sequence;
  return FrameVerdict::kDeliver;
}

}  // namespace de4sdv::someip_receiver
