// Pure core of the AutowareToSCORE adapter: the frame path controller, with
// the third LoLa rule of the phase-8 realization (INC-MW-011).
//
// Rule 3, frame provider: the adapter offers the frame skeleton once at
// start. It keeps the offer when the frame stream on 127.0.0.1:4721 goes
// away and reconnects with a bounded backoff; it destroys the skeleton only
// at exit. A frame that finds no free sample slot is dropped and counted,
// never retried (GAP-MW-037).
//
// Threads: OnFrame() and the connection events run in the frame ingest
// thread; Start() and Stop() run in the main thread; counters() may run in
// any thread.

#ifndef DE4SDV_SCORE_ADAPTER_FRAME_PATH_CONTROLLER_HPP
#define DE4SDV_SCORE_ADAPTER_FRAME_PATH_CONTROLLER_HPP

#include <atomic>
#include <chrono>
#include <cstddef>
#include <cstdint>
#include <mutex>

#include "de4sdv_score_adapter/ports.hpp"

namespace de4sdv::score_adapter {

struct FramePathCounters {
  std::uint64_t offers{0};
  std::uint64_t connections{0};
  std::uint64_t connection_losses{0};
  std::uint64_t frames_sent{0};
  std::uint64_t frames_too_large{0};
  std::uint64_t frames_allocate_failed{0};
  std::uint64_t frames_send_failed{0};
  std::uint64_t frames_not_offered{0};
};

class FramePathController {
 public:
  explicit FramePathController(FrameEventPort& event);

  // Offers the skeleton the first time; later calls return the state.
  bool Start();
  void OnFrame(const std::uint8_t* sample, std::size_t sample_size);
  void OnConnectionEstablished() noexcept;
  void OnConnectionLost() noexcept;
  // Stops the offer and destroys the skeleton, once.
  void Stop();

  bool offered() const;
  FramePathCounters counters() const noexcept;

 private:
  FrameEventPort& event_;
  mutable std::mutex mutex_;
  bool offer_attempted_{false};
  bool offered_{false};
  bool stopped_{false};

  std::atomic<std::uint64_t> offers_{0};
  std::atomic<std::uint64_t> connections_{0};
  std::atomic<std::uint64_t> connection_losses_{0};
  std::atomic<std::uint64_t> frames_sent_{0};
  std::atomic<std::uint64_t> frames_too_large_{0};
  std::atomic<std::uint64_t> frames_allocate_failed_{0};
  std::atomic<std::uint64_t> frames_send_failed_{0};
  std::atomic<std::uint64_t> frames_not_offered_{0};
};

// Delay between connection attempts to the frame stream: doubles from
// initial to max, back to initial after Reset(). The frame stream client
// resets it only after a complete frame.
class ReconnectBackoff {
 public:
  ReconnectBackoff(std::chrono::milliseconds initial, std::chrono::milliseconds max);
  std::chrono::milliseconds NextDelay() noexcept;
  void Reset() noexcept;

 private:
  std::chrono::milliseconds initial_;
  std::chrono::milliseconds max_;
  std::chrono::milliseconds next_;
};

}  // namespace de4sdv::score_adapter

#endif  // DE4SDV_SCORE_ADAPTER_FRAME_PATH_CONTROLLER_HPP
