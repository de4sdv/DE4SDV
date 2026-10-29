// Pure core of the DE4SDV IVI frame relay: the discard rule of the frames in
// a subscription phase (relaySubscriptionPhaseDiscardRule of the phase-8
// realization model).
//
// A frame that the AEBS stack produced before the HMI application's current
// subscription must not reach it (REQ-MW-019). The relay core tracks the
// subscription phase: it holds while the relay holds a subscription, through
// the SDV Gateway on IVI, to the broker's publication of the frame topic, and
// the ingress is the one client of its loopback server. Outside a phase the
// core drops every frame. In a phase it asks this policy. The policy is a
// separate component behind FrameDiscardPolicy, so a later rule can replace
// it.
//
// The rule in a phase:
// - A frame whose sequence or frame_timestamp_ns has no positive value is
//   dropped.
// - A frame whose frame_timestamp_ns is earlier than the phase start less
//   20 ms is dropped. 20 ms is the bound of ASM-MW-030 on the offset of the
//   host clock and the clock of the IVI VM. The frame assembler stamps each
//   frame with the host clock; the phase start comes from CLOCK_REALTIME of
//   the IVI VM. The margin is fixed: no option sets it.
// - A copy of a frame already served in this phase, with the same sequence
//   and frame_timestamp_ns, is dropped.
// - Every other frame is served in the order it comes, also a frame older
//   than one already served: the rule does not filter on sequence order.
//
// The copy memory is bounded by slots, not by reads. A copy comes only from
// the stored frames that a new subscription in the host half reads after a
// restart during the phase (GAP-MW-039). A stored frame is still in a sample
// slot: 20 slots in the adapter's frame event and 20 in gatewayd's bridged
// service. The broker's topic adds no copy: a subscriber with
// ASDVGATEWAY_SUBSCRIBER_OPTIONS_FLAG_NONE reads only the messages published
// after its subscription. The memory keeps the 40 frames served last and is
// cleared at each phase start. A copy of a frame that left the memory would
// pass.

#ifndef DE4SDV_IVI_FRAME_RELAY_DISCARD_POLICY_HPP
#define DE4SDV_IVI_FRAME_RELAY_DISCARD_POLICY_HPP

#include <cstddef>
#include <cstdint>
#include <vector>

#include "de4sdv_ivi_frame_relay/frame_fields.hpp"

namespace de4sdv::ivi_frame_relay {

enum class FrameVerdict : std::uint8_t {
  kDeliver,
  kDropFieldNotPositive,
  kDropOlderThanPhase,
  kDropCopyInPhase,
};

const char* ToText(FrameVerdict verdict) noexcept;

class FrameDiscardPolicy {
 public:
  virtual ~FrameDiscardPolicy() = default;
  virtual const char* Name() const noexcept = 0;
  // A phase starts at realtime_ns (CLOCK_REALTIME of the IVI VM).
  virtual void OnPhaseStart(std::int64_t realtime_ns) = 0;
  virtual void OnPhaseEnd() = 0;
  // Decides one frame of the current phase; kDeliver counts it as served.
  virtual FrameVerdict Admit(const FrameFields& frame) = 0;
};

class PhaseStartDiscardPolicy final : public FrameDiscardPolicy {
 public:
  static constexpr std::int64_t kPhaseStartMarginNs = 20'000'000;  // ASM-MW-030
  static constexpr std::size_t kCopyMemoryFrames = 40;  // 20 + 20 sample slots

  // The memory size is a parameter for the tests only; the relay uses 40.
  explicit PhaseStartDiscardPolicy(std::size_t copy_memory_frames = kCopyMemoryFrames);

  const char* Name() const noexcept override { return "relay_subscription_phase_discard_rule"; }
  void OnPhaseStart(std::int64_t realtime_ns) override;
  void OnPhaseEnd() override;
  FrameVerdict Admit(const FrameFields& frame) override;

  bool in_phase() const noexcept { return in_phase_; }
  std::int64_t phase_start_realtime_ns() const noexcept { return phase_start_realtime_ns_; }
  std::size_t served_in_memory() const noexcept { return served_count_; }

 private:
  void ClearMemory() noexcept;

  bool in_phase_{false};
  std::int64_t phase_start_realtime_ns_{0};
  std::vector<FrameFields> served_;
  std::size_t served_next_{0};
  std::size_t served_count_{0};
};

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_DISCARD_POLICY_HPP
