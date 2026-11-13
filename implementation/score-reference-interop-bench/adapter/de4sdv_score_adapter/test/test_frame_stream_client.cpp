// Unit tests of the frame stream client of the pure adapter core: the
// reconnect part of the third LoLa rule (phase-8 realization of INC-MW-011).
// After a failed connect or a lost stream the client waits before the next
// attempt; the delay doubles and goes back to its initial value only after a
// complete frame came over a connection. A scripted TCP server on the
// loopback plays the frame assembler; the client's sleep function records
// the delays instead of sleeping.

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <gtest/gtest.h>

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstdint>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "de4sdv_score_adapter/frame_stream_client.hpp"

namespace {

using de4sdv::score_adapter::FrameEventPort;
using de4sdv::score_adapter::FramePathController;
using de4sdv::score_adapter::FrameSendResult;
using de4sdv::score_adapter::FrameSplitter;
using de4sdv::score_adapter::FrameStreamClient;
using de4sdv::score_adapter::FrameStreamEvents;
using de4sdv::score_adapter::ReconnectBackoff;
using std::chrono::milliseconds;

class FakeFrameEvent final : public FrameEventPort {
 public:
  std::atomic<int> sent{0};
  bool Offer() override { return true; }
  FrameSendResult Send(const std::uint8_t* /*sample*/, std::size_t /*size*/) override {
    ++sent;
    return FrameSendResult::kSent;
  }
  void StopOfferAndDestroy() override {}
};

class RecordingEvents final : public FrameStreamEvents {
 public:
  std::atomic<int> waiting{0};
  std::atomic<int> connected{0};
  std::atomic<int> lost{0};
  std::atomic<int> invalid{0};
  void OnWaiting() override { ++waiting; }
  void OnConnected() override { ++connected; }
  void OnLost(milliseconds /*next_delay*/) override { ++lost; }
  void OnInvalidAddress() override { ++invalid; }
};

enum class Behavior { kCloseAtOnce, kSendFrameThenClose, kSendPartialFrameThenClose, kHoldOpen };

// Accepts connections one after the other on 127.0.0.1 and treats each by
// the next behavior of the script; after the script, it closes at once.
class ScriptedServer {
 public:
  explicit ScriptedServer(std::vector<Behavior> script) : script_{std::move(script)} {
    listen_fd_ = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
    const int reuse = 1;
    ::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
    sockaddr_in address{};
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    address.sin_port = 0;
    ::bind(listen_fd_, reinterpret_cast<const sockaddr*>(&address), sizeof(address));
    ::listen(listen_fd_, 8);
    socklen_t length = sizeof(address);
    ::getsockname(listen_fd_, reinterpret_cast<sockaddr*>(&address), &length);
    port_ = ntohs(address.sin_port);
    thread_ = std::thread{[this] { Serve(); }};
  }
  ~ScriptedServer() {
    stop_.store(true);
    ::shutdown(listen_fd_, SHUT_RDWR);
    ::close(listen_fd_);
    release_.store(true);
    thread_.join();
  }
  std::uint16_t port() const { return port_; }
  int accepted() const { return accepted_.load(); }
  void ReleaseHeldConnection() { release_.store(true); }

 private:
  void Serve() {
    std::size_t next = 0;
    while (!stop_.load()) {
      const int client = ::accept(listen_fd_, nullptr, nullptr);
      if (client < 0) {
        return;
      }
      ++accepted_;
      const Behavior behavior = next < script_.size() ? script_[next] : Behavior::kCloseAtOnce;
      ++next;
      const std::vector<std::uint8_t> frame{0x02, 0x00, 0x00, 0x00, 0xAB, 0xCD};
      if (behavior == Behavior::kSendFrameThenClose) {
        ::send(client, frame.data(), frame.size(), MSG_NOSIGNAL);
      } else if (behavior == Behavior::kSendPartialFrameThenClose) {
        ::send(client, frame.data(), 5, MSG_NOSIGNAL);
      } else if (behavior == Behavior::kHoldOpen) {
        while (!release_.load()) {
          std::this_thread::sleep_for(milliseconds{5});
        }
      }
      ::close(client);
    }
  }

  std::vector<Behavior> script_;
  int listen_fd_{-1};
  std::uint16_t port_{0};
  std::atomic<bool> stop_{false};
  std::atomic<bool> release_{false};
  std::atomic<int> accepted_{0};
  std::thread thread_;
};

// Runs a client until it has asked for stop_after delays, and records them.
struct ClientRun {
  FakeFrameEvent event;
  FramePathController controller{event};
  FrameSplitter splitter{2048};
  RecordingEvents events;
  std::mutex mutex;
  std::vector<milliseconds> delays;
  std::atomic<bool> stop{false};

  void Run(const std::string& host, std::uint16_t port, std::size_t stop_after) {
    ASSERT_TRUE(controller.Start());
    FrameStreamClient client{host, port, splitter, controller, ReconnectBackoff{milliseconds{100}, milliseconds{2000}},
                             [this, stop_after](milliseconds delay) {
                               std::lock_guard<std::mutex> lock{mutex};
                               delays.push_back(delay);
                               if (delays.size() >= stop_after) {
                                 stop.store(true);
                               }
                             },
                             &events};
    client.Run(stop);
  }
};

TEST(FrameStreamClient, WaitsAfterEveryLostStreamAndDoublesTheDelayWithoutAFrame) {
  ScriptedServer server{{Behavior::kCloseAtOnce, Behavior::kCloseAtOnce, Behavior::kCloseAtOnce}};
  ClientRun run;
  run.Run("127.0.0.1", server.port(), 3);
  EXPECT_EQ(run.delays, (std::vector<milliseconds>{milliseconds{100}, milliseconds{200}, milliseconds{400}}));
  EXPECT_EQ(run.controller.counters().connections, 3U);
  EXPECT_EQ(run.controller.counters().connection_losses, 3U);
  EXPECT_EQ(run.events.lost.load(), 3);
}

TEST(FrameStreamClient, ResetsTheDelayOnlyAfterACompleteFrame) {
  ScriptedServer server{{Behavior::kCloseAtOnce, Behavior::kCloseAtOnce, Behavior::kSendFrameThenClose,
                         Behavior::kCloseAtOnce}};
  ClientRun run;
  run.Run("127.0.0.1", server.port(), 4);
  EXPECT_EQ(run.delays, (std::vector<milliseconds>{milliseconds{100}, milliseconds{200}, milliseconds{100},
                                                   milliseconds{200}}));
  EXPECT_EQ(run.event.sent.load(), 1);
}

TEST(FrameStreamClient, APartialFrameDoesNotResetTheDelay) {
  ScriptedServer server{{Behavior::kCloseAtOnce, Behavior::kSendPartialFrameThenClose, Behavior::kCloseAtOnce}};
  ClientRun run;
  run.Run("127.0.0.1", server.port(), 3);
  EXPECT_EQ(run.delays, (std::vector<milliseconds>{milliseconds{100}, milliseconds{200}, milliseconds{400}}));
  EXPECT_EQ(run.event.sent.load(), 0);
  EXPECT_EQ(run.splitter.stats().partial_frames_discarded, 1U);
}

TEST(FrameStreamClient, WaitsBetweenFailedConnectsUpToTheCap) {
  std::uint16_t closed_port = 0;
  {
    ScriptedServer server{{}};
    closed_port = server.port();
  }
  ClientRun run;
  run.Run("127.0.0.1", closed_port, 7);
  EXPECT_EQ(run.delays, (std::vector<milliseconds>{milliseconds{100}, milliseconds{200}, milliseconds{400},
                                                   milliseconds{800}, milliseconds{1600}, milliseconds{2000},
                                                   milliseconds{2000}}));
  EXPECT_EQ(run.events.waiting.load(), 1);
  EXPECT_EQ(run.controller.counters().connections, 0U);
}

TEST(FrameStreamClient, StopDuringAConnectionEndsTheRunWithoutALoss) {
  ScriptedServer server{{Behavior::kHoldOpen}};
  ClientRun run;
  std::thread client_thread{[&run, &server] { run.Run("127.0.0.1", server.port(), 100); }};
  const auto deadline = std::chrono::steady_clock::now() + std::chrono::seconds{5};
  while (run.events.connected.load() == 0 && std::chrono::steady_clock::now() < deadline) {
    std::this_thread::sleep_for(milliseconds{5});
  }
  run.stop.store(true);
  client_thread.join();
  server.ReleaseHeldConnection();
  EXPECT_EQ(run.events.connected.load(), 1);
  EXPECT_EQ(run.controller.counters().connection_losses, 0U);
  EXPECT_TRUE(run.delays.empty());
}

TEST(FrameStreamClient, AnInvalidHostEndsTheRunAtOnce) {
  ClientRun run;
  run.Run("not-an-address", 4721, 1);
  EXPECT_EQ(run.events.invalid.load(), 1);
  EXPECT_TRUE(run.delays.empty());
}

}  // namespace
