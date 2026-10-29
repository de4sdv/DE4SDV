// Pure core of the AutowareToSCORE adapter: the frame splitter.
//
// The INC-AEBS-010 frame assembler serves its frames on port 4721 (the
// adapter connects to 127.0.0.1:4721) as a byte stream: each frame follows a
// 4-byte little-endian length prefix that counts the frame bytes. The
// splitter reads the prefix only to find where a frame ends. It hands each
// frame on unchanged, together with its prefix, as one sample of at most
// max_sample_bytes (the 2048-byte sample of the gateway's
// PreSerializedData<2048>). A frame whose sample would be larger is
// skipped byte for byte and counted; it is never truncated and never shifts
// the framing of the frames after it (REQ-MW-015). Reset() is called when the
// stream connection ends, so a frame torn by the end of a connection is never
// handed on. The frame content stays opaque.
//
// Threads: Feed() and Reset() run in the frame ingest thread. stats() may
// run in any thread: each counter is an atomic, so a snapshot is free of data
// races, although the four values are not read at one instant.

#ifndef DE4SDV_SCORE_ADAPTER_FRAME_SPLITTER_HPP
#define DE4SDV_SCORE_ADAPTER_FRAME_SPLITTER_HPP

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <vector>

namespace de4sdv::score_adapter {

class FrameSplitter {
 public:
  static constexpr std::size_t kPrefixBytes = 4;

  // Called with prefix plus frame, size <= max_sample_bytes. The pointer is
  // valid only during the call.
  using FrameHandler = std::function<void(const std::uint8_t* sample, std::size_t sample_size)>;

  struct Stats {
    std::uint64_t bytes_read{0};
    std::uint64_t frames_forwarded{0};
    std::uint64_t frames_dropped_oversize{0};
    std::uint64_t partial_frames_discarded{0};
  };

  explicit FrameSplitter(std::size_t max_sample_bytes);

  void Feed(const std::uint8_t* data, std::size_t size, const FrameHandler& on_frame);

  // Forget a partly read frame (the stream connection ended).
  void Reset() noexcept;

  bool HasPartialFrame() const noexcept;

  // A snapshot of the counters.
  Stats stats() const noexcept;

 private:
  enum class State { kPrefix, kFrame, kSkip };

  void StartFrame(const FrameHandler& on_frame);

  std::size_t max_sample_bytes_;
  State state_{State::kPrefix};
  std::array<std::uint8_t, kPrefixBytes> prefix_{};
  std::size_t prefix_filled_{0};
  std::vector<std::uint8_t> sample_;
  std::size_t sample_expected_{0};
  std::uint64_t skip_remaining_{0};
  std::atomic<std::uint64_t> bytes_read_{0};
  std::atomic<std::uint64_t> frames_forwarded_{0};
  std::atomic<std::uint64_t> frames_dropped_oversize_{0};
  std::atomic<std::uint64_t> partial_frames_discarded_{0};
};

}  // namespace de4sdv::score_adapter

#endif  // DE4SDV_SCORE_ADAPTER_FRAME_SPLITTER_HPP
