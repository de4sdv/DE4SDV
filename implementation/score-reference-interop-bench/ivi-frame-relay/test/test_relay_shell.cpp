// Tests of the POSIX shell with its two threads, real loopback sockets and
// the fake gateway client: frames served unchanged to the one client, a
// second client refused, the ingress connection kept across a restart of the
// publication, a loopback server that does not wait for a blocked gateway
// call, and a stop that leaves a blocked worker behind and says so.

#include <arpa/inet.h>
#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <gtest/gtest.h>

#include <algorithm>
#include <atomic>
#include <chrono>
#include <cstdint>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include "fake_gateway_client.hpp"
#include "shell/relay_shell.hpp"

namespace {

using de4sdv::ivi_frame_relay::Clock;
using de4sdv::ivi_frame_relay::DropReason;
using de4sdv::ivi_frame_relay::EventLog;
using de4sdv::ivi_frame_relay::LogRecord;
using de4sdv::ivi_frame_relay::PropertySetter;
using de4sdv::ivi_frame_relay::PublicationName;
using de4sdv::ivi_frame_relay::RealClock;
using de4sdv::ivi_frame_relay::RelayConfig;
using de4sdv::ivi_frame_relay::RelayShell;
using de4sdv::ivi_frame_relay::ShellConfig;
using de4sdv::ivi_frame_relay::ShellResult;
using de4sdv::ivi_frame_relay::SubjectIdentity;
using de4sdv::ivi_frame_relay::WorkerConfig;
using de4sdv::ivi_frame_relay::test::Bytes;
using de4sdv::ivi_frame_relay::test::FakeGatewayClient;
using de4sdv::ivi_frame_relay::test::FramePayload;
using de4sdv::ivi_frame_relay::test::kMs;
using de4sdv::ivi_frame_relay::test::kSecond;
using de4sdv::ivi_frame_relay::test::WrapLikeBroker;

constexpr auto kWait = std::chrono::seconds{10};

bool WaitUntil(const std::function<bool()>& condition) {
  const auto end = std::chrono::steady_clock::now() + kWait;
  while (std::chrono::steady_clock::now() < end) {
    if (condition()) {
      return true;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds{2});
  }
  return condition();
}

// Thread-safe; the waits poll, because the ThreadSanitizer of GCC 11 does not
// see timed waits of std::condition_variable.
class SharedLog final : public EventLog {
 public:
  void Log(const Clock& now, const LogRecord& record) override {
    const std::lock_guard<std::mutex> lock{mutex_};
    events_.push_back(record.event());
    lines_.push_back(record.ToJson(now));
  }
  std::size_t Count(const std::string& event) const {
    const std::lock_guard<std::mutex> lock{mutex_};
    return static_cast<std::size_t>(std::count(events_.begin(), events_.end(), event));
  }
  bool WaitFor(const std::string& event, std::size_t count = 1) const {
    return WaitUntil([&] { return Count(event) >= count; });
  }
  std::string Last(const std::string& event) const {
    const std::lock_guard<std::mutex> lock{mutex_};
    for (std::size_t index = events_.size(); index > 0; --index) {
      if (events_[index - 1] == event) {
        return lines_[index - 1];
      }
    }
    return {};
  }

 private:
  mutable std::mutex mutex_;
  std::vector<std::string> events_;
  std::vector<std::string> lines_;
};

class NoProperties final : public PropertySetter {
 public:
  bool SetProperty(const Clock&, const std::string&, const std::string&) override { return true; }
};

int Connect(std::uint16_t port) {
  const int fd = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
  sockaddr_in address{};
  address.sin_family = AF_INET;
  address.sin_port = htons(port);
  address.sin_addr.s_addr = htonl(0x7F000001U);
  if (::connect(fd, reinterpret_cast<const sockaddr*>(&address), sizeof(address)) != 0) {
    ::close(fd);
    return -1;
  }
  return fd;
}

// Reads exactly size bytes within the wait, or fewer on EOF or timeout.
Bytes ReadBytes(int fd, std::size_t size) {
  Bytes data;
  const auto end = std::chrono::steady_clock::now() + kWait;
  while (data.size() < size && std::chrono::steady_clock::now() < end) {
    pollfd readable{fd, POLLIN, 0};
    if (::poll(&readable, 1, 50) <= 0) {
      continue;
    }
    std::uint8_t buffer[4096];
    const ssize_t got = ::recv(fd, buffer, std::min(sizeof(buffer), size - data.size()), 0);
    if (got <= 0) {
      break;
    }
    data.insert(data.end(), buffer, buffer + got);
  }
  return data;
}

// True when nothing arrives and the peer does not close within ms.
bool QuietFor(int fd, int ms) {
  pollfd readable{fd, POLLIN, 0};
  return ::poll(&readable, 1, ms) == 0;
}

bool ClosedByPeer(int fd) {
  pollfd readable{fd, POLLIN, 0};
  if (::poll(&readable, 1, static_cast<int>(std::chrono::milliseconds{kWait}.count())) <= 0) {
    return false;
  }
  std::uint8_t byte = 0;
  return ::recv(fd, &byte, 1, 0) == 0;
}

struct Running {
  explicit Running(ShellConfig shell_config = {}, RelayConfig relay = {}) {
    shell_config.listen_port = 0;
    shell_config.status_period_ns = 1 * kSecond;
    shell = std::make_unique<RelayShell>(
        shell_config, relay,
        WorkerConfig{SubjectIdentity{"de4sdv.ivi_frame_relay", "IviFrameRelay", "default"},
                     PublicationName{"instance1", "com.android.sdv.someip", "SomeIpBroker",
                                     "de4sdv-score-aebs-signal-frame"}},
        client, log, properties, clock);
  }
  ~Running() {
    if (runner.joinable()) {
      stop.store(true);
      runner.join();
    }
    for (const int fd : fds) {
      ::close(fd);
    }
  }

  void Start() {
    std::string error;
    ASSERT_TRUE(shell->Open(&error)) << error;
    ASSERT_NE(shell->port(), 0);
    runner = std::thread{[this] { result = shell->Run([this] { return stop.load(); }); }};
  }
  ShellResult Stop() {
    stop.store(true);
    runner.join();
    return result;
  }
  int Client() {
    const int fd = Connect(shell->port());
    EXPECT_GE(fd, 0);
    fds.push_back(fd);
    return fd;
  }
  Bytes QueueFrame(std::uint64_t sequence, std::int64_t age_ns = 0) {
    const Bytes payload = FramePayload(sequence, clock.Now().realtime_ns - age_ns, 40);
    client.QueueSlot(WrapLikeBroker(payload));
    return payload;
  }

  RealClock clock;
  FakeGatewayClient client;
  SharedLog log;
  NoProperties properties;
  std::unique_ptr<RelayShell> shell;
  std::atomic<bool> stop{false};
  std::thread runner;
  ShellResult result;
  std::vector<int> fds;
};

TEST(RelayShell, ServesTheFramesUnchangedToTheOneClientAndRefusesASecond) {
  Running r;
  r.Start();
  ASSERT_TRUE(WaitUntil([&] { return r.client.subscribed(); }));
  const int ingress = r.Client();
  ASSERT_TRUE(r.log.WaitFor("phase_start"));
  Bytes expected;
  for (std::uint64_t sequence = 1; sequence <= 3; ++sequence) {
    const Bytes payload = r.QueueFrame(sequence);
    expected.insert(expected.end(), payload.begin(), payload.end());
  }
  EXPECT_EQ(ReadBytes(ingress, expected.size()), expected);
  const int second = r.Client();
  EXPECT_TRUE(ClosedByPeer(second));
  ASSERT_TRUE(r.log.WaitFor("client_refused"));
  const ShellResult result = r.Stop();
  EXPECT_TRUE(result.worker_joined);
  EXPECT_EQ(r.shell->counters().frames_delivered, 3U);
  EXPECT_EQ(r.shell->counters().clients_refused, 1U);
  EXPECT_EQ(r.client.count("destroy"), 1U);
  EXPECT_GE(r.client.count("unsubscribe:2"), 1U);
  EXPECT_NE(r.log.Last("final_status").find("\"frames_delivered\":3"), std::string::npos);
}

TEST(RelayShell, KeepsTheIngressConnectionAcrossARestartOfThePublication) {
  Running r;
  r.Start();
  ASSERT_TRUE(WaitUntil([&] { return r.client.subscribed(); }));
  const int ingress = r.Client();
  ASSERT_TRUE(r.log.WaitFor("phase_start"));
  const Bytes first = r.QueueFrame(1);
  EXPECT_EQ(ReadBytes(ingress, first.size()), first);
  r.client.DestroyPublication();
  ASSERT_TRUE(r.log.WaitFor("phase_end"));
  EXPECT_NE(r.log.Last("phase_end").find("\"cause\":\"publication_destroyed\""), std::string::npos);
  EXPECT_NE(r.log.Last("phase_end").find("\"layer_caused\":true"), std::string::npos);
  EXPECT_TRUE(QuietFor(ingress, 300));  // still open, and nothing served
  r.client.RestorePublication();
  ASSERT_TRUE(r.log.WaitFor("phase_start", 2));
  r.QueueFrame(2, 900 * kMs);  // stored before the new phase: dropped
  const Bytes fresh = r.QueueFrame(3);
  EXPECT_EQ(ReadBytes(ingress, fresh.size()), fresh);
  EXPECT_TRUE(QuietFor(ingress, 100));
  r.Stop();
  EXPECT_EQ(r.shell->counters().drops.at(static_cast<std::size_t>(DropReason::kOlderThanPhase)), 1U);
  EXPECT_EQ(r.shell->counters().clients_lost, 0U);
  EXPECT_EQ(r.shell->counters().phases_ended_by_layer, 1U);
}

TEST(RelayShell, TheLoopbackServerDoesNotWaitForABlockedGatewayCall) {
  RelayConfig relay;
  relay.gateway_call_stall_ns = 100 * kMs;
  Running r{ShellConfig{}, relay};
  r.client.BlockCreate();
  r.Start();
  ASSERT_TRUE(WaitUntil([&] { return r.client.create_waiting(); }));
  const int ingress = r.Client();
  ASSERT_TRUE(r.log.WaitFor("client_connected"));
  ASSERT_TRUE(r.log.WaitFor("gateway_call_stalled"));
  EXPECT_NE(r.log.Last("gateway_call_stalled").find("\"call\":\"create_client\""), std::string::npos);
  r.client.ReleaseCreate();
  ASSERT_TRUE(r.log.WaitFor("gateway_call_returned"));
  ASSERT_TRUE(r.log.WaitFor("phase_start"));
  const Bytes payload = r.QueueFrame(1);
  EXPECT_EQ(ReadBytes(ingress, payload.size()), payload);
  EXPECT_TRUE(r.Stop().worker_joined);
}

TEST(RelayShell, StopLeavesABlockedWorkerBehindAndSaysSo) {
  ShellConfig shell_config;
  shell_config.stop_join_timeout_ns = 50 * kMs;
  Running r{shell_config};
  r.client.BlockCreate();
  r.Start();
  ASSERT_TRUE(WaitUntil([&] { return r.client.create_waiting(); }));
  const ShellResult result = r.Stop();
  EXPECT_FALSE(result.worker_joined);
  EXPECT_EQ(r.log.Count("gateway_worker_not_joined"), 1U);
  EXPECT_NE(r.log.Last("gateway_worker_not_joined").find("\"call\":\"create_client\""), std::string::npos);
  EXPECT_EQ(r.log.Count("final_status"), 1U);
  // The process would end here; the test lets the worker finish first.
  r.client.ReleaseCreate();
  ASSERT_TRUE(WaitUntil([&] { return r.shell->worker_done(); }));
}

}  // namespace
