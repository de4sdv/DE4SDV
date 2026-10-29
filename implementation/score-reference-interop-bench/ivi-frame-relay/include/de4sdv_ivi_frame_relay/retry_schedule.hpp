// Pure core of the DE4SDV IVI frame relay: when the gateway worker tries
// again (iviFrameRelay of the phase-8 model, owner decision of 2026-10-29).
//
// The relay keeps one subscription for its lifetime, with or without a
// client, and it holds at most one subscription at a time: break before make,
// because the feasibility runs did not test whether a second subscription
// adds a stream. A subscription ends on PublicationDestroyed, on Disconnected
// of the client, or when no message comes for 3 s. The 3 s are above the
// longest pause of a healthy source: the adapter's reconnect delay of at most
// 2 s plus one frame period. Then the relay subscribes again:
// - after PublicationDestroyed: at once, then every 100 ms for the first 5 s,
//   then every second;
// - after the 3 s timeout: at once, then every second. After three
//   subscriptions in a row that brought no message, it waits 5 s before each
//   attempt;
// - after Disconnected: once the client exists again, at once, then every
//   second.
// Until the first subscription of the process succeeds, the relay tries
// every second. If none succeeds within 30 s of its start, the relay core
// reports a likely fault of the ACL or of the mapping, and from then on the
// relay tries every 10 s.
// The relay's own choice, not a value of the model: a failed creation of the
// gateway client is tried again every second, and every 10 s once the
// failures have lasted 30 s, so each wait is bounded.
// A period runs from the start of one attempt to the start of the next. An
// attempt that took longer than its period is followed at once.

#ifndef DE4SDV_IVI_FRAME_RELAY_RETRY_SCHEDULE_HPP
#define DE4SDV_IVI_FRAME_RELAY_RETRY_SCHEDULE_HPP

#include <cstdint>

namespace de4sdv::ivi_frame_relay {

constexpr std::int64_t kNanosecondsPerMillisecond = 1'000'000;
constexpr std::int64_t kNanosecondsPerSecond = 1'000'000'000;

// The timing of the model (owner decision of 2026-10-29).
constexpr std::int64_t kSilenceTimeoutNs = 3 * kNanosecondsPerSecond;
constexpr std::int64_t kDestroyedRetryPeriodNs = 100 * kNanosecondsPerMillisecond;
constexpr std::int64_t kDestroyedFastWindowNs = 5 * kNanosecondsPerSecond;
constexpr std::int64_t kRetryPeriodNs = 1 * kNanosecondsPerSecond;
constexpr std::uint64_t kSilentSubscriptionsBeforeBackOff = 3;
constexpr std::int64_t kSilentBackOffNs = 5 * kNanosecondsPerSecond;
constexpr std::int64_t kStartDiagnosticNs = 30 * kNanosecondsPerSecond;
constexpr std::int64_t kSlowRetryPeriodNs = 10 * kNanosecondsPerSecond;
// The relay's own choice for the creation of the gateway client.
constexpr std::int64_t kClientFastRetryWindowNs = 30 * kNanosecondsPerSecond;

enum class SubscriptionEnd : std::uint8_t {
  kPublicationDestroyed,
  kDisconnected,
  kSilenceTimeout,
  kRelayStop,
};

const char* ToText(SubscriptionEnd end) noexcept;
// PublicationDestroyed, Disconnected and the timeout are caused by the
// layer, not by the HMI application (relaySubscriptionPhaseDiscardRule).
bool EndedByLayer(SubscriptionEnd end) noexcept;

class RetrySchedule {
 public:
  explicit RetrySchedule(std::int64_t start_ns) noexcept;

  void OnSubscribed() noexcept;
  // A subscription ended at at_ns and brought messages messages.
  void OnEnded(SubscriptionEnd end, std::uint64_t messages, std::int64_t at_ns) noexcept;
  // The client was lost at at_ns: its creation starts a new retry window.
  void OnClientLost(std::int64_t at_ns) noexcept;

  // The first subscribe attempt after an end at at_ns, or after the client
  // was created at at_ns.
  std::int64_t FirstAttemptNs(std::int64_t at_ns) const noexcept;
  // The attempt after a failed one that started at attempt_start_ns and
  // returned at now_ns.
  std::int64_t NextAttemptNs(std::int64_t attempt_start_ns, std::int64_t now_ns) const noexcept;
  // The client creation after a failed one.
  std::int64_t NextClientAttemptNs(std::int64_t attempt_start_ns, std::int64_t now_ns) const noexcept;

  // The period of a subscribe attempt that starts at attempt_start_ns, and
  // the name of the rule that sets it.
  std::int64_t SubscribePeriodNs(std::int64_t attempt_start_ns) const noexcept;
  const char* SubscribeRule(std::int64_t attempt_start_ns) const noexcept;

  bool ever_subscribed() const noexcept { return ever_subscribed_; }
  std::uint64_t consecutive_silent() const noexcept { return consecutive_silent_; }
  std::int64_t start_ns() const noexcept { return start_ns_; }

 private:
  bool BackingOff() const noexcept;

  std::int64_t start_ns_;
  bool ever_subscribed_{false};
  bool ended_{false};
  SubscriptionEnd last_end_{SubscriptionEnd::kRelayStop};
  std::int64_t last_end_ns_{0};
  std::uint64_t consecutive_silent_{0};
  std::int64_t client_window_start_ns_;
};

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_RETRY_SCHEDULE_HPP
