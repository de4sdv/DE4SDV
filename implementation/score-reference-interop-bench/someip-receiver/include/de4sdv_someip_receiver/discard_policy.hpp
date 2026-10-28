// Pure core of the DE4SDV minimal SOME/IP receiver: the discard policy of
// the frames that reach the receiver in a subscription phase.
//
// After each new subscription, the S-CORE layer on the Linux host can send
// frames that it stored before (GAP-MW-039). Such a frame must not reach
// the HMI ingress (REQ-MW-019). The policy is a separate component behind
// FrameDiscardPolicy, so that the final rule can replace the provisional
// one without a change to the rest of the receiver.
//
// Provisional rule, until the phase-8 model revision states the final one:
// - A subscription phase starts at each SubscribeEventgroupAck after a
//   not-subscribed state and at each new loopback client connection, at the
//   receiver's CLOCK_REALTIME time of that event.
// - In a phase, a frame is delivered only if its sequence is greater than
//   the sequence of the last frame delivered, and its frame_timestamp_ns is
//   not older than the phase start minus the clock-offset bound.
// - "The last frame delivered" means the last frame delivered to the
//   current loopback client. A new client has received no frame, so its
//   connection resets that floor to 0; a new subscription with the same
//   client keeps it. Sequence 0 is therefore never delivered, as in the
//   HMI ingress.
//
// The receiver calls Admit() only while it is subscribed and a client is
// connected. Every Admit() outside a started phase drops the frame.

#ifndef DE4SDV_SOMEIP_RECEIVER_DISCARD_POLICY_HPP
#define DE4SDV_SOMEIP_RECEIVER_DISCARD_POLICY_HPP

#include <cstdint>

#include "de4sdv_someip_receiver/frame_fields.hpp"

namespace de4sdv::someip_receiver {

enum class PhaseCause : std::uint8_t {
  kSubscriptionAcknowledged,
  kClientConnected,
};

const char* ToText(PhaseCause cause) noexcept;

enum class FrameVerdict : std::uint8_t {
  kDeliver,
  kDropSequenceNotIncreasing,
  kDropOlderThanPhase,
};

const char* ToText(FrameVerdict verdict) noexcept;

class FrameDiscardPolicy {
 public:
  virtual ~FrameDiscardPolicy() = default;
  virtual const char* Name() const noexcept = 0;
  virtual void OnPhaseStart(PhaseCause cause, std::int64_t realtime_ns) = 0;
  // kDeliver counts the frame as delivered.
  virtual FrameVerdict Admit(const FrameFields& frame) = 0;
};

class ProvisionalDiscardPolicy final : public FrameDiscardPolicy {
 public:
  explicit ProvisionalDiscardPolicy(std::int64_t clock_offset_bound_ns);

  const char* Name() const noexcept override { return "provisional_sequence_and_phase_start"; }
  void OnPhaseStart(PhaseCause cause, std::int64_t realtime_ns) override;
  FrameVerdict Admit(const FrameFields& frame) override;

  bool in_phase() const noexcept { return in_phase_; }
  std::int64_t phase_start_realtime_ns() const noexcept { return phase_start_realtime_ns_; }
  std::uint64_t last_delivered_sequence() const noexcept { return last_delivered_sequence_; }
  std::int64_t clock_offset_bound_ns() const noexcept { return clock_offset_bound_ns_; }

 private:
  std::int64_t clock_offset_bound_ns_;
  bool in_phase_{false};
  std::int64_t phase_start_realtime_ns_{0};
  std::uint64_t last_delivered_sequence_{0};
};

}  // namespace de4sdv::someip_receiver

#endif  // DE4SDV_SOMEIP_RECEIVER_DISCARD_POLICY_HPP
