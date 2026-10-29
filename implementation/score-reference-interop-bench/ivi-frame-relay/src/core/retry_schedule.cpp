#include "de4sdv_ivi_frame_relay/retry_schedule.hpp"

#include <algorithm>

namespace de4sdv::ivi_frame_relay {

const char* ToText(SubscriptionEnd end) noexcept {
  switch (end) {
    case SubscriptionEnd::kPublicationDestroyed:
      return "publication_destroyed";
    case SubscriptionEnd::kDisconnected:
      return "disconnected";
    case SubscriptionEnd::kSilenceTimeout:
      return "silence_timeout";
    case SubscriptionEnd::kRelayStop:
      return "relay_stop";
  }
  return "unknown";
}

bool EndedByLayer(SubscriptionEnd end) noexcept {
  return end == SubscriptionEnd::kPublicationDestroyed || end == SubscriptionEnd::kDisconnected ||
         end == SubscriptionEnd::kSilenceTimeout;
}

RetrySchedule::RetrySchedule(std::int64_t start_ns) noexcept : start_ns_{start_ns} {}

void RetrySchedule::OnSubscribed() noexcept { ever_subscribed_ = true; }

void RetrySchedule::OnEnded(SubscriptionEnd end, std::uint64_t messages, std::int64_t at_ns) noexcept {
  ended_ = true;
  last_end_ = end;
  last_end_ns_ = at_ns;
  if (end == SubscriptionEnd::kRelayStop) {
    return;
  }
  consecutive_silent_ = messages == 0U ? consecutive_silent_ + 1U : 0U;
}

bool RetrySchedule::BackingOff() const noexcept {
  return ended_ && last_end_ == SubscriptionEnd::kSilenceTimeout &&
         consecutive_silent_ >= kSilentSubscriptionsBeforeBackOff;
}

std::int64_t RetrySchedule::SubscribePeriodNs(std::int64_t attempt_start_ns) const noexcept {
  if (!ever_subscribed_) {
    return attempt_start_ns - start_ns_ < kStartDiagnosticNs ? kRetryPeriodNs : kSlowRetryPeriodNs;
  }
  if (ended_ && last_end_ == SubscriptionEnd::kPublicationDestroyed &&
      attempt_start_ns - last_end_ns_ < kDestroyedFastWindowNs) {
    return kDestroyedRetryPeriodNs;
  }
  return BackingOff() ? kSilentBackOffNs : kRetryPeriodNs;
}

const char* RetrySchedule::SubscribeRule(std::int64_t attempt_start_ns) const noexcept {
  if (!ever_subscribed_) {
    return attempt_start_ns - start_ns_ < kStartDiagnosticNs ? "start" : "start_after_diagnostic";
  }
  if (ended_ && last_end_ == SubscriptionEnd::kPublicationDestroyed &&
      attempt_start_ns - last_end_ns_ < kDestroyedFastWindowNs) {
    return "publication_destroyed_first_5_s";
  }
  return BackingOff() ? "silent_subscriptions_back_off" : "every_second";
}

std::int64_t RetrySchedule::FirstAttemptNs(std::int64_t at_ns) const noexcept {
  return BackingOff() ? at_ns + kSilentBackOffNs : at_ns;
}

std::int64_t RetrySchedule::NextAttemptNs(std::int64_t attempt_start_ns, std::int64_t now_ns) const noexcept {
  return std::max(attempt_start_ns + SubscribePeriodNs(attempt_start_ns), now_ns);
}

std::int64_t RetrySchedule::NextClientAttemptNs(std::int64_t attempt_start_ns, std::int64_t now_ns) const noexcept {
  const std::int64_t period =
      attempt_start_ns - start_ns_ < kClientFastRetryWindowNs ? kRetryPeriodNs : kSlowRetryPeriodNs;
  return std::max(attempt_start_ns + period, now_ns);
}

}  // namespace de4sdv::ivi_frame_relay
