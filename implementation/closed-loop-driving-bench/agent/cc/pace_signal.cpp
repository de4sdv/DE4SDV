// Pace datagram sender: one Unix datagram socket, non-blocking, no retries.
#include "pace_signal.h"

#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <cerrno>
#include <cstdlib>
#include <cstring>

namespace de4sdv::driving::agent {
namespace {

constexpr std::size_t kMaxPathBytes = sizeof(sockaddr_un::sun_path);

}  // namespace

void EncodePacePayload(std::uint64_t frame, std::uint8_t out[kPacePayloadBytes]) {
  for (std::size_t i = 0; i < kPacePayloadBytes; ++i) {
    out[i] = static_cast<std::uint8_t>((frame >> (8U * i)) & 0xFFU);
  }
}

std::uint64_t DecodePacePayload(const std::uint8_t in[kPacePayloadBytes]) {
  std::uint64_t frame = 0;
  for (std::size_t i = 0; i < kPacePayloadBytes; ++i) {
    frame |= static_cast<std::uint64_t>(in[i]) << (8U * i);
  }
  return frame;
}

std::string DefaultPaceSocketPath() {
  const char* value = std::getenv("FEO_PACE_SOCKET");
  return value == nullptr ? std::string() : std::string(value);
}

PaceSignal::PaceSignal(const std::string& socketPath) {
  path_ = socketPath.empty() ? DefaultPaceSocketPath() : socketPath;
  // SOCK_NONBLOCK: a full receive queue or a missing peer must never stall a
  // LibCarla callback thread. SOCK_CLOEXEC: the FEO process must not leak it.
  fd_ = ::socket(AF_UNIX, SOCK_DGRAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
  if (fd_ < 0) {
    fd_ = -1;
    path_.clear();
  }
}

PaceSignal::~PaceSignal() {
  if (fd_ >= 0) ::close(fd_);
}

bool PaceSignal::Send(std::uint64_t frame) {
  if (fd_ < 0 || path_.empty() || path_.size() >= kMaxPathBytes) {
    failures_.fetch_add(1, std::memory_order_relaxed);
    return false;
  }
  sockaddr_un address{};
  address.sun_family = AF_UNIX;
  std::memcpy(address.sun_path, path_.data(), path_.size());
  address.sun_path[path_.size()] = '\0';

  std::uint8_t payload[kPacePayloadBytes];
  EncodePacePayload(frame, payload);

  const ssize_t written =
      ::sendto(fd_, payload, sizeof payload, MSG_DONTWAIT | MSG_NOSIGNAL,
               reinterpret_cast<const sockaddr*>(&address),
               static_cast<socklen_t>(sizeof address));
  if (written == static_cast<ssize_t>(sizeof payload)) {
    sent_.fetch_add(1, std::memory_order_relaxed);
    return true;
  }
  // ENOENT/ECONNREFUSED: the scheduler is not listening yet.
  // EAGAIN: its queue is full. Neither is retried here.
  failures_.fetch_add(1, std::memory_order_relaxed);
  return false;
}

}  // namespace de4sdv::driving::agent
