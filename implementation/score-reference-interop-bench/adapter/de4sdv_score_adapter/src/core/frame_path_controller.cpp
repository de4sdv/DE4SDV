#include "de4sdv_score_adapter/frame_path_controller.hpp"

#include <algorithm>

namespace de4sdv::score_adapter {

FramePathController::FramePathController(FrameEventPort& event) : event_{event} {}

bool FramePathController::Start() {
  std::lock_guard<std::mutex> lock{mutex_};
  if (offer_attempted_ || stopped_) {
    return offered_;
  }
  offer_attempted_ = true;
  offered_ = event_.Offer();
  if (offered_) {
    offers_.fetch_add(1U, std::memory_order_relaxed);
  }
  return offered_;
}

void FramePathController::OnFrame(const std::uint8_t* sample, std::size_t sample_size) {
  std::lock_guard<std::mutex> lock{mutex_};
  if (!offered_) {
    frames_not_offered_.fetch_add(1U, std::memory_order_relaxed);
    return;
  }
  switch (event_.Send(sample, sample_size)) {
    case FrameSendResult::kSent:
      frames_sent_.fetch_add(1U, std::memory_order_relaxed);
      break;
    case FrameSendResult::kTooLarge:
      frames_too_large_.fetch_add(1U, std::memory_order_relaxed);
      break;
    case FrameSendResult::kAllocateFailed:
      frames_allocate_failed_.fetch_add(1U, std::memory_order_relaxed);
      break;
    case FrameSendResult::kSendFailed:
      frames_send_failed_.fetch_add(1U, std::memory_order_relaxed);
      break;
    case FrameSendResult::kNotOffered:
      frames_not_offered_.fetch_add(1U, std::memory_order_relaxed);
      break;
  }
}

void FramePathController::OnConnectionEstablished() noexcept {
  connections_.fetch_add(1U, std::memory_order_relaxed);
}

void FramePathController::OnConnectionLost() noexcept {
  // Rule 3: the offer stays; only the stream is reconnected.
  connection_losses_.fetch_add(1U, std::memory_order_relaxed);
}

void FramePathController::Stop() {
  std::lock_guard<std::mutex> lock{mutex_};
  if (stopped_) {
    return;
  }
  stopped_ = true;
  if (offered_) {
    event_.StopOfferAndDestroy();
    offered_ = false;
  }
}

bool FramePathController::offered() const {
  std::lock_guard<std::mutex> lock{mutex_};
  return offered_;
}

FramePathCounters FramePathController::counters() const noexcept {
  FramePathCounters counters;
  counters.offers = offers_.load(std::memory_order_relaxed);
  counters.connections = connections_.load(std::memory_order_relaxed);
  counters.connection_losses = connection_losses_.load(std::memory_order_relaxed);
  counters.frames_sent = frames_sent_.load(std::memory_order_relaxed);
  counters.frames_too_large = frames_too_large_.load(std::memory_order_relaxed);
  counters.frames_allocate_failed = frames_allocate_failed_.load(std::memory_order_relaxed);
  counters.frames_send_failed = frames_send_failed_.load(std::memory_order_relaxed);
  counters.frames_not_offered = frames_not_offered_.load(std::memory_order_relaxed);
  return counters;
}

ReconnectBackoff::ReconnectBackoff(std::chrono::milliseconds initial, std::chrono::milliseconds max)
    : initial_{initial}, max_{max}, next_{initial} {}

std::chrono::milliseconds ReconnectBackoff::NextDelay() noexcept {
  const std::chrono::milliseconds delay = next_;
  next_ = std::min(next_ * 2, max_);
  return delay;
}

void ReconnectBackoff::Reset() noexcept { next_ = initial_; }

}  // namespace de4sdv::score_adapter
