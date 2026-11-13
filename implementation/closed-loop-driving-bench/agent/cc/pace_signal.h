// DE4SDV INC-DRIVING-001 slice 10b: the pace datagram.
//
// LibCarla threads do not wake the FEO scheduler; the frame store's ReadySink
// does, by sending one datagram per ready slot to FEO_PACE_SOCKET. The
// scheduler (patched event trigger) wakes on that datagram and runs one chain;
// its conditionInputs then takes the newest ready slot. A datagram that finds
// nobody listening is a normal startup condition, not an error: it is counted
// and dropped, never retried and never blocked on.
#pragma once

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <string>

namespace de4sdv::driving::agent {

inline constexpr std::size_t kPacePayloadBytes = 8;  // frame number, little-endian

// The payload of one pace datagram: the frame number, 8 bytes little-endian.
void EncodePacePayload(std::uint64_t frame, std::uint8_t out[kPacePayloadBytes]);
std::uint64_t DecodePacePayload(const std::uint8_t in[kPacePayloadBytes]);

// The socket path from the environment, or an empty string when unset.
std::string DefaultPaceSocketPath();

class PaceSignal {
 public:
  // Binds nothing: a datagram sender needs no address. `socketPath` empty
  // means "use FEO_PACE_SOCKET"; if that is unset too, every send fails.
  explicit PaceSignal(const std::string& socketPath = std::string());
  ~PaceSignal();

  PaceSignal(const PaceSignal&) = delete;
  PaceSignal& operator=(const PaceSignal&) = delete;

  // Non-blocking. Returns true when the kernel took the datagram.
  bool Send(std::uint64_t frame);

  const std::string& socketPath() const { return path_; }
  bool hasSocket() const { return fd_ >= 0; }
  std::uint64_t sent() const { return sent_.load(std::memory_order_relaxed); }
  std::uint64_t failures() const { return failures_.load(std::memory_order_relaxed); }

 private:
  int fd_ = -1;
  std::string path_;
  std::atomic<std::uint64_t> sent_{0};
  std::atomic<std::uint64_t> failures_{0};
};

}  // namespace de4sdv::driving::agent
