#include "route_listener.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cstring>

namespace de4sdv::driving::agent {

namespace {
std::int64_t MonoNs() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch())
      .count();
}
}  // namespace

RouteListener::~RouteListener() { Stop(); }

bool RouteListener::Start(const std::string& host, int port, std::string* error) {
  if (running_.load()) return true;
  fd_ = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC, 0);
  if (fd_ < 0) {
    *error = std::string("route listener: socket: ") + std::strerror(errno);
    return false;
  }
  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_port = htons(static_cast<std::uint16_t>(port));
  if (::inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1) {
    *error = "route listener: bad host " + host;
    ::close(fd_);
    fd_ = -1;
    return false;
  }
  if (::bind(fd_, reinterpret_cast<const sockaddr*>(&addr), sizeof(addr)) != 0) {
    *error = "route listener: bind " + host + ":" + std::to_string(port) + ": " + std::strerror(errno);
    ::close(fd_);
    fd_ = -1;
    return false;
  }
  socklen_t len = sizeof(addr);
  ::getsockname(fd_, reinterpret_cast<sockaddr*>(&addr), &len);
  port_ = ntohs(addr.sin_port);
  running_ = true;
  thread_ = std::thread([this] { Loop(); });
  return true;
}

void RouteListener::Stop() {
  running_ = false;
  if (thread_.joinable()) thread_.join();
  if (fd_ >= 0) {
    ::close(fd_);
    fd_ = -1;
  }
}

RouteState RouteListener::Newest() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return state_;
}

void RouteListener::Loop() {
  unsigned char buf[1024];
  while (running_.load()) {
    pollfd p{fd_, POLLIN, 0};
    if (::poll(&p, 1, 100) <= 0) continue;
    const ssize_t n = ::recv(fd_, buf, sizeof(buf), 0);
    if (n < 0) continue;
    RouteAnnouncement a{};
    const bool size_ok = static_cast<std::size_t>(n) == sizeof(RouteAnnouncement);
    if (size_ok) std::memcpy(&a, buf, sizeof(a));
    std::lock_guard<std::mutex> lock(mutex_);
    if (!size_ok || a.version != kInterfaceVersion) {
      ++state_.rejected;
      continue;
    }
    state_.newest = a;
    state_.has_announcement = true;
    state_.received_mono_ns = MonoNs();
    ++state_.received;
  }
}

}  // namespace de4sdv::driving::agent
