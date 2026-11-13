#include "de4sdv_score_adapter/frame_splitter.hpp"

#include <algorithm>

namespace de4sdv::score_adapter {

FrameSplitter::FrameSplitter(std::size_t max_sample_bytes) : max_sample_bytes_{max_sample_bytes} {
  sample_.reserve(max_sample_bytes_);
}

void FrameSplitter::Feed(const std::uint8_t* data, std::size_t size, const FrameHandler& on_frame) {
  std::size_t position = 0;
  while (position < size) {
    const std::size_t available = size - position;
    switch (state_) {
      case State::kPrefix: {
        const std::size_t take = std::min(kPrefixBytes - prefix_filled_, available);
        std::copy_n(data + position, take, prefix_.begin() + static_cast<std::ptrdiff_t>(prefix_filled_));
        prefix_filled_ += take;
        position += take;
        if (prefix_filled_ == kPrefixBytes) {
          StartFrame(on_frame);
        }
        break;
      }
      case State::kFrame: {
        const std::size_t take = std::min(sample_expected_ - sample_.size(), available);
        sample_.insert(sample_.end(), data + position, data + position + take);
        position += take;
        if (sample_.size() == sample_expected_) {
          on_frame(sample_.data(), sample_.size());
          frames_forwarded_.fetch_add(1U, std::memory_order_relaxed);
          sample_.clear();
          state_ = State::kPrefix;
        }
        break;
      }
      case State::kSkip: {
        const std::size_t take = static_cast<std::size_t>(
            std::min<std::uint64_t>(skip_remaining_, static_cast<std::uint64_t>(available)));
        skip_remaining_ -= take;
        position += take;
        if (skip_remaining_ == 0U) {
          state_ = State::kPrefix;
        }
        break;
      }
    }
  }
  bytes_read_.fetch_add(static_cast<std::uint64_t>(size), std::memory_order_relaxed);
}

void FrameSplitter::StartFrame(const FrameHandler& on_frame) {
  const std::uint32_t length = static_cast<std::uint32_t>(prefix_[0]) |
                               (static_cast<std::uint32_t>(prefix_[1]) << 8U) |
                               (static_cast<std::uint32_t>(prefix_[2]) << 16U) |
                               (static_cast<std::uint32_t>(prefix_[3]) << 24U);
  prefix_filled_ = 0;
  const std::uint64_t sample_size = static_cast<std::uint64_t>(kPrefixBytes) + length;
  if (sample_size > static_cast<std::uint64_t>(max_sample_bytes_)) {
    frames_dropped_oversize_.fetch_add(1U, std::memory_order_relaxed);
    skip_remaining_ = length;
    state_ = State::kSkip;
    return;
  }
  sample_.assign(prefix_.begin(), prefix_.end());
  sample_expected_ = static_cast<std::size_t>(sample_size);
  if (length == 0U) {
    on_frame(sample_.data(), sample_.size());
    frames_forwarded_.fetch_add(1U, std::memory_order_relaxed);
    sample_.clear();
    state_ = State::kPrefix;
    return;
  }
  state_ = State::kFrame;
}

void FrameSplitter::Reset() noexcept {
  if (HasPartialFrame() && state_ != State::kSkip) {
    partial_frames_discarded_.fetch_add(1U, std::memory_order_relaxed);
  }
  state_ = State::kPrefix;
  prefix_filled_ = 0;
  sample_.clear();
  sample_expected_ = 0;
  skip_remaining_ = 0;
}

bool FrameSplitter::HasPartialFrame() const noexcept {
  return state_ != State::kPrefix || prefix_filled_ != 0U;
}

FrameSplitter::Stats FrameSplitter::stats() const noexcept {
  Stats stats;
  stats.bytes_read = bytes_read_.load(std::memory_order_relaxed);
  stats.frames_forwarded = frames_forwarded_.load(std::memory_order_relaxed);
  stats.frames_dropped_oversize = frames_dropped_oversize_.load(std::memory_order_relaxed);
  stats.partial_frames_discarded = partial_frames_discarded_.load(std::memory_order_relaxed);
  return stats;
}

}  // namespace de4sdv::score_adapter
