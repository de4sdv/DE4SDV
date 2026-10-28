#include "de4sdv_score_adapter/speed_path_controller.hpp"

#include <thread>

namespace de4sdv::score_adapter {

namespace {
// A bound on consecutive full reads, so one call cannot spin forever on a
// provider that sends faster than the adapter reads.
constexpr int kMaxReadsPerCall = 64;
}  // namespace

SpeedPathController::SpeedPathController(SpeedEventPort& event, VelocityPublisherPort& publisher,
                                         std::size_t max_samples, SpeedPathEvents* events)
    : event_{event}, publisher_{publisher}, max_samples_{max_samples}, events_{events} {
  buffer_.reserve(max_samples_);
}

const char* ToText(SubscribeResult result) noexcept {
  switch (result) {
    case SubscribeResult::kSubscribed:
      return "subscribed";
    case SubscribeResult::kStateHandlerFailed:
      return "state_handler_failed";
    case SubscribeResult::kReceiveHandlerFailed:
      return "receive_handler_failed";
    case SubscribeResult::kSubscribeFailed:
      return "subscribe_failed";
    case SubscribeResult::kShutDown:
    default:
      return "shut_down";
  }
}

SubscribeResult SpeedPathController::Subscribe() {
  std::lock_guard<std::mutex> lock{read_mutex_};
  if (shut_down_) {
    return SubscribeResult::kShutDown;
  }
  // From here on Shutdown() handles the proxy by rule 2, whatever step
  // mw::com refuses below.
  proxy_present_ = true;
  if (!event_.SetStateHandler()) {
    return SubscribeResult::kStateHandlerFailed;
  }
  if (!event_.SetReceiveHandler()) {
    return SubscribeResult::kReceiveHandlerFailed;
  }
  if (!event_.Subscribe(max_samples_)) {
    return SubscribeResult::kSubscribeFailed;
  }
  return SubscribeResult::kSubscribed;
}

void SpeedPathController::OnSubscriptionStateChanged(SubscriptionState new_state) noexcept {
  state_changes_.fetch_add(1U, std::memory_order_relaxed);
  if (new_state != SubscriptionState::kSubscribed) {
    // Every leave of kSubscribed opens a new epoch; its first stable read in
    // kSubscribed is the discard read of rule 1.
    leave_epoch_.fetch_add(1U, std::memory_order_acq_rel);
  }
}

void SpeedPathController::ReadAvailable() {
  for (int i = 0; i < kMaxReadsPerCall; ++i) {
    if (!ReadOnce()) {
      return;
    }
  }
}

bool SpeedPathController::ReadOnce() {
  std::lock_guard<std::mutex> lock{read_mutex_};
  if (shut_down_ || !proxy_present_) {
    return false;
  }
  const std::uint64_t epoch_before = leave_epoch_.load(std::memory_order_acquire);
  if (event_.State() != SubscriptionState::kSubscribed) {
    return false;
  }
  buffer_.clear();
  const std::int64_t delivered =
      event_.ReadNewSamples(max_samples_, [this](double speed_kmh) { buffer_.push_back(speed_kmh); });
  reads_.fetch_add(1U, std::memory_order_relaxed);
  if (delivered < 0) {
    read_errors_.fetch_add(1U, std::memory_order_relaxed);
    return false;
  }
  samples_read_.fetch_add(buffer_.size(), std::memory_order_relaxed);
  const SubscriptionState state_after = event_.State();
  const std::uint64_t epoch_after = leave_epoch_.load(std::memory_order_acquire);
  if (state_after != SubscriptionState::kSubscribed || epoch_after != epoch_before) {
    samples_dropped_unstable_.fetch_add(buffer_.size(), std::memory_order_relaxed);
    if (events_ != nullptr && !buffer_.empty()) {
      events_->OnUnstableReadDropped(buffer_.size());
    }
    return false;
  }
  const bool more_may_wait = buffer_.size() >= max_samples_;
  if (discarded_epoch_ != epoch_before) {
    // Rule 1: the discard of this epoch goes on while the reads are full.
    if (!more_may_wait) {
      discarded_epoch_ = epoch_before;
    }
    discard_reads_.fetch_add(1U, std::memory_order_relaxed);
    samples_discarded_stored_.fetch_add(buffer_.size(), std::memory_order_relaxed);
    if (events_ != nullptr) {
      events_->OnStoredSamplesDiscarded(buffer_.size());
    }
    return more_may_wait;
  }
  for (const double speed_kmh : buffer_) {
    PublishOrWithhold(speed_kmh);
  }
  return more_may_wait;
}

void SpeedPathController::PublishOrWithhold(double speed_kmh) {
  const Translation translation = TranslateSpeed(speed_kmh);
  switch (translation.outcome) {
    case TranslationOutcome::kPublish:
      publisher_.Publish(translation.longitudinal_velocity_mps);
      samples_published_.fetch_add(1U, std::memory_order_relaxed);
      break;
    case TranslationOutcome::kWithheldNonFinite:
      samples_withheld_non_finite_.fetch_add(1U, std::memory_order_relaxed);
      break;
    case TranslationOutcome::kWithheldOutOfRange:
      samples_withheld_out_of_range_.fetch_add(1U, std::memory_order_relaxed);
      break;
  }
  if (translation.outcome != TranslationOutcome::kPublish && events_ != nullptr) {
    events_->OnSampleWithheld(speed_kmh, translation.outcome);
  }
}

ShutdownResult SpeedPathController::Shutdown(std::chrono::milliseconds unsubscribe_timeout) {
  {
    std::lock_guard<std::mutex> lock{read_mutex_};
    shut_down_ = true;
    if (!proxy_present_) {
      return ShutdownResult::kNoProxy;
    }
  }
  // No sample is held here: reads copy each value and release the sample.
  event_.UnsetReceiveHandler();
  event_.Unsubscribe();
  const auto deadline = std::chrono::steady_clock::now() + unsubscribe_timeout;
  while (event_.State() != SubscriptionState::kNotSubscribed) {
    if (std::chrono::steady_clock::now() >= deadline) {
      return ShutdownResult::kStillSubscribed;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds{1});
  }
  event_.UnsetStateHandler();
  event_.DestroyProxy();
  return ShutdownResult::kProxyDestroyed;
}

SpeedPathCounters SpeedPathController::counters() const noexcept {
  SpeedPathCounters counters;
  counters.state_changes = state_changes_.load(std::memory_order_relaxed);
  counters.subscription_leaves = leave_epoch_.load(std::memory_order_relaxed) - 1U;
  counters.reads = reads_.load(std::memory_order_relaxed);
  counters.discard_reads = discard_reads_.load(std::memory_order_relaxed);
  counters.read_errors = read_errors_.load(std::memory_order_relaxed);
  counters.samples_read = samples_read_.load(std::memory_order_relaxed);
  counters.samples_discarded_stored = samples_discarded_stored_.load(std::memory_order_relaxed);
  counters.samples_dropped_unstable = samples_dropped_unstable_.load(std::memory_order_relaxed);
  counters.samples_published = samples_published_.load(std::memory_order_relaxed);
  counters.samples_withheld_non_finite = samples_withheld_non_finite_.load(std::memory_order_relaxed);
  counters.samples_withheld_out_of_range = samples_withheld_out_of_range_.load(std::memory_order_relaxed);
  return counters;
}

}  // namespace de4sdv::score_adapter
