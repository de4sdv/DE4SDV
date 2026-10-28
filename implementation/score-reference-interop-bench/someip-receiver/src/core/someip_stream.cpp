#include "de4sdv_someip_receiver/someip_stream.hpp"

#include <algorithm>

namespace de4sdv::someip_receiver {

SomeipStreamReassembler::SomeipStreamReassembler(std::size_t max_payload_bytes)
    : max_payload_bytes_{max_payload_bytes} {
  payload_.reserve(max_payload_bytes_);
}

bool SomeipStreamReassembler::Feed(const std::uint8_t* data, std::size_t size, const MessageHandler& on_message) {
  if (state_ == State::kLost) {
    return false;
  }
  stats_.bytes_read += size;
  std::size_t position = 0;
  while (position < size && state_ != State::kLost) {
    const std::size_t available = size - position;
    switch (state_) {
      case State::kHeader: {
        const std::size_t take = std::min(kHeaderBytes - header_filled_, available);
        std::copy_n(data + position, take, header_bytes_.begin() + static_cast<std::ptrdiff_t>(header_filled_));
        header_filled_ += take;
        position += take;
        if (header_filled_ == kHeaderBytes) {
          StartMessage(on_message);
        }
        break;
      }
      case State::kPayload: {
        const std::size_t take = std::min(payload_expected_ - payload_.size(), available);
        payload_.insert(payload_.end(), data + position, data + position + take);
        position += take;
        if (payload_.size() == payload_expected_) {
          ++stats_.messages;
          on_message(header_, payload_.data(), payload_.size());
          payload_.clear();
          state_ = State::kHeader;
        }
        break;
      }
      case State::kSkip: {
        const auto take = static_cast<std::size_t>(
            std::min<std::uint64_t>(skip_remaining_, static_cast<std::uint64_t>(available)));
        skip_remaining_ -= take;
        position += take;
        if (skip_remaining_ == 0U) {
          state_ = State::kHeader;
        }
        break;
      }
      case State::kLost:
        break;
    }
  }
  return state_ != State::kLost;
}

void SomeipStreamReassembler::StartMessage(const MessageHandler& on_message) {
  header_filled_ = 0;
  header_ = *ParseHeader(header_bytes_.data(), header_bytes_.size());
  if (header_.length < kLengthFieldHeaderPart) {
    ++stats_.framing_errors;
    state_ = State::kLost;
    return;
  }
  const std::uint64_t payload_size = static_cast<std::uint64_t>(header_.length) - kLengthFieldHeaderPart;
  if (payload_size > kSkipLimitBytes) {
    ++stats_.framing_errors;
    state_ = State::kLost;
    return;
  }
  if (payload_size > max_payload_bytes_) {
    ++stats_.messages_oversize_skipped;
    skip_remaining_ = payload_size;
    state_ = State::kSkip;
    return;
  }
  payload_.clear();
  payload_expected_ = static_cast<std::size_t>(payload_size);
  if (payload_expected_ == 0U) {
    ++stats_.messages;
    on_message(header_, payload_.data(), 0);
    state_ = State::kHeader;
    return;
  }
  state_ = State::kPayload;
}

void SomeipStreamReassembler::Reset() noexcept {
  if (HasPartialMessage() && state_ != State::kLost) {
    ++stats_.partial_messages_discarded;
  }
  state_ = State::kHeader;
  header_filled_ = 0;
  payload_.clear();
  payload_expected_ = 0;
  skip_remaining_ = 0;
}

bool SomeipStreamReassembler::HasPartialMessage() const noexcept {
  return state_ == State::kPayload || state_ == State::kSkip || header_filled_ != 0U;
}

}  // namespace de4sdv::someip_receiver
