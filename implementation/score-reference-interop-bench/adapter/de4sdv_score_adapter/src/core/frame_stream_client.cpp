#include "de4sdv_score_adapter/frame_stream_client.hpp"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <cerrno>
#include <utility>
#include <vector>

namespace de4sdv::score_adapter {

namespace {
constexpr int kPollTimeoutMs = 100;
constexpr std::size_t kReceiveBufferBytes = 8192;
}  // namespace

FrameStreamClient::FrameStreamClient(std::string host, std::uint16_t port, FrameSplitter& splitter,
                                     FramePathController& controller, ReconnectBackoff backoff, SleepFunction sleep,
                                     FrameStreamEvents* events)
    : host_{std::move(host)},
      port_{port},
      splitter_{splitter},
      controller_{controller},
      backoff_{backoff},
      sleep_{std::move(sleep)},
      events_{events} {}

void FrameStreamClient::Run(const std::atomic<bool>& stop) {
  sockaddr_in address{};
  address.sin_family = AF_INET;
  address.sin_port = htons(port_);
  if (inet_pton(AF_INET, host_.c_str(), &address.sin_addr) != 1) {
    if (events_ != nullptr) {
      events_->OnInvalidAddress();
    }
    return;
  }
  std::vector<std::uint8_t> buffer(kReceiveBufferBytes);
  bool waiting_reported = false;
  while (!stop.load()) {
    const int fd = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    if (fd < 0 || ::connect(fd, reinterpret_cast<const sockaddr*>(&address), sizeof(address)) != 0) {
      if (fd >= 0) {
        ::close(fd);
      }
      if (!waiting_reported && events_ != nullptr) {
        events_->OnWaiting();
      }
      waiting_reported = true;
      sleep_(backoff_.NextDelay());
      continue;
    }
    waiting_reported = false;
    controller_.OnConnectionEstablished();
    if (events_ != nullptr) {
      events_->OnConnected();
    }
    bool complete_frame = false;
    const auto on_frame = [this, &complete_frame](const std::uint8_t* sample, std::size_t size) {
      controller_.OnFrame(sample, size);
      if (!complete_frame) {
        // Only a complete frame shows that the stream works.
        complete_frame = true;
        backoff_.Reset();
      }
    };
    while (!stop.load()) {
      pollfd poll_fd{fd, POLLIN, 0};
      const int ready = ::poll(&poll_fd, 1, kPollTimeoutMs);
      if (ready < 0) {
        if (errno == EINTR) {
          continue;
        }
        break;
      }
      if (ready == 0) {
        continue;
      }
      const ssize_t received = ::recv(fd, buffer.data(), buffer.size(), 0);
      if (received > 0) {
        splitter_.Feed(buffer.data(), static_cast<std::size_t>(received), on_frame);
        continue;
      }
      if (received < 0 && (errno == EINTR || errno == EAGAIN)) {
        continue;
      }
      break;  // closed by the frame assembler, or an error
    }
    ::close(fd);
    splitter_.Reset();
    if (stop.load()) {
      break;  // the adapter's own shutdown, not a loss of the stream
    }
    controller_.OnConnectionLost();  // rule 3: the offer stays
    const std::chrono::milliseconds delay = backoff_.NextDelay();
    if (events_ != nullptr) {
      events_->OnLost(delay);
    }
    sleep_(delay);
  }
}

}  // namespace de4sdv::score_adapter
