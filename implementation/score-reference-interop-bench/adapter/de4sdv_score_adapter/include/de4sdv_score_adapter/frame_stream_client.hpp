// Pure core of the AutowareToSCORE adapter: the client of the frame stream
// (port aebsSignalFrameIn), with the reconnect part of the third LoLa rule
// of the phase-8 realization (INC-MW-011).
//
// The client connects to the INC-AEBS-010 frame assembler at host:port and
// feeds the received bytes to the frame splitter, which hands each complete
// frame to the frame path controller. When a connect fails or the stream
// ends, the client waits before the next attempt. The delay doubles from
// initial to max, and it goes back to initial only after a complete frame
// came over a connection. So a peer that accepts and closes at once, or a
// second client that takes the stream over, cannot make the client
// reconnect in a tight loop. The client never touches the skeleton offer.
//
// Threads: Run() runs in the frame ingest thread. The sleep function must
// return early when stop is set.

#ifndef DE4SDV_SCORE_ADAPTER_FRAME_STREAM_CLIENT_HPP
#define DE4SDV_SCORE_ADAPTER_FRAME_STREAM_CLIENT_HPP

#include <atomic>
#include <chrono>
#include <cstdint>
#include <functional>
#include <string>

#include "de4sdv_score_adapter/frame_path_controller.hpp"
#include "de4sdv_score_adapter/frame_splitter.hpp"

namespace de4sdv::score_adapter {

// Optional observer of the connection, for the adapter's log. Called in the
// frame ingest thread.
class FrameStreamEvents {
 public:
  virtual ~FrameStreamEvents() = default;
  // The first failed connect at start or after a lost stream.
  virtual void OnWaiting() = 0;
  virtual void OnConnected() = 0;
  // The stream ended; the client waits next_delay before it connects again.
  virtual void OnLost(std::chrono::milliseconds next_delay) = 0;
  // host is not an IPv4 address; Run() returns.
  virtual void OnInvalidAddress() = 0;
};

class FrameStreamClient {
 public:
  using SleepFunction = std::function<void(std::chrono::milliseconds)>;

  FrameStreamClient(std::string host, std::uint16_t port, FrameSplitter& splitter, FramePathController& controller,
                    ReconnectBackoff backoff, SleepFunction sleep, FrameStreamEvents* events = nullptr);

  // Runs until stop is set; returns at once for an invalid host.
  void Run(const std::atomic<bool>& stop);

 private:
  std::string host_;
  std::uint16_t port_;
  FrameSplitter& splitter_;
  FramePathController& controller_;
  ReconnectBackoff backoff_;
  SleepFunction sleep_;
  FrameStreamEvents* events_;
};

}  // namespace de4sdv::score_adapter

#endif  // DE4SDV_SCORE_ADAPTER_FRAME_STREAM_CLIENT_HPP
