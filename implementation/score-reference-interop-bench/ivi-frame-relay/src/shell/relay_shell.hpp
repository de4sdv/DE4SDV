// The POSIX shell of the DE4SDV IVI frame relay: the loopback server, the
// mailbox from the gateway worker, the worker thread and the poll loop of the
// main thread.
//
// Two threads. The worker thread runs the GatewayWorker: every call into the
// gateway client. The main thread runs the RelayCore and the loopback server
// on 127.0.0.1:4731 with its one client, the HMI ingress. The main thread
// never calls the gateway client and never waits for the worker, so the
// loopback server and the ingress connection do not depend on it. The worker
// hands its events to the main thread through a bounded mailbox; when the
// mailbox is full, the worker waits for room in slices of 20 ms, and the
// queue of the publication holds the messages meanwhile. Every wait is a
// poll() on a pipe with a timeout of CLOCK_MONOTONIC, so a step of the
// realtime clock does not change it.
//
// At stop, the main thread ends the phase, asks the worker to stop and waits
// at most 150 ms for it to unsubscribe and delete the client: init's
// gentle_kill gives 200 ms between SIGTERM and SIGKILL. A worker that is
// still inside a gateway call then is left behind: the shell logs
// gateway_worker_not_joined, and the caller must end the process without
// destroying the shell.
//
// The shell builds on Linux and on Android. Only the AOSP build has the
// gateway client of AOSP; the tests run the shell with a fake client.

#ifndef DE4SDV_IVI_FRAME_RELAY_RELAY_SHELL_HPP
#define DE4SDV_IVI_FRAME_RELAY_RELAY_SHELL_HPP

#include <atomic>
#include <cstddef>
#include <cstdint>
#include <deque>
#include <functional>
#include <memory>
#include <mutex>
#include <string>
#include <thread>
#include <vector>

#include "de4sdv_ivi_frame_relay/discard_policy.hpp"
#include "de4sdv_ivi_frame_relay/event_log.hpp"
#include "de4sdv_ivi_frame_relay/gateway_client.hpp"
#include "de4sdv_ivi_frame_relay/gateway_worker.hpp"
#include "de4sdv_ivi_frame_relay/options.hpp"
#include "de4sdv_ivi_frame_relay/relay_core.hpp"

namespace de4sdv::ivi_frame_relay {

// CLOCK_REALTIME read between two reads of CLOCK_MONOTONIC; the reading with
// the shortest window, so that a preemption between the reads does not look
// like a clock step.
class RealClock final : public ClockSource {
 public:
  Clock Now() override;
};

// JSON lines on stdout (Linux) or to liblog with the tag
// de4sdv_ivi_frame_relay (Android).
class LineLog final : public EventLog {
 public:
  void Log(const Clock& now, const LogRecord& record) override;
  static void Write(const std::string& line);

 private:
  std::mutex mutex_;
};

// System properties of the HMI ingress: set on Android, logged elsewhere.
class SystemProperties final : public PropertySetter {
 public:
  explicit SystemProperties(EventLog& log) : log_{log} {}
  bool SetProperty(const Clock& now, const std::string& name, const std::string& value) override;

 private:
  EventLog& log_;
};

// A non-blocking pipe: Wake() writes a byte, Wait() polls and drains it.
class WakePipe final : public WorkerWaker {
 public:
  WakePipe() = default;
  ~WakePipe() override;
  WakePipe(const WakePipe&) = delete;
  WakePipe& operator=(const WakePipe&) = delete;

  bool Open(std::string* error);
  int fd() const noexcept { return pipe_[0]; }
  void Wake() noexcept override;
  // Waits at most timeout_ms for a wake, then drains the pipe.
  void Wait(int timeout_ms);
  void Drain();

 private:
  int pipe_[2]{-1, -1};
};

// The bounded mailbox from the worker to the main thread, with a pipe that
// wakes the main thread's poll and one that tells a waiting worker of room.
class EventMailbox final : public WorkerEventSink {
 public:
  explicit EventMailbox(std::size_t capacity);
  ~EventMailbox() override = default;
  EventMailbox(const EventMailbox&) = delete;
  EventMailbox& operator=(const EventMailbox&) = delete;

  bool Open(std::string* error);
  int wake_fd() const noexcept { return ready_.fd(); }
  // Worker: waits for room in slices of 20 ms; once closed, a full mailbox
  // drops the event and counts it.
  void Post(WorkerEvent&& event) override;
  // Main thread: every queued event, in order.
  std::deque<WorkerEvent> TakeAll();
  void Wake();
  void Close();
  std::uint64_t dropped() const;

 private:
  const std::size_t capacity_;
  mutable std::mutex mutex_;
  std::deque<WorkerEvent> queue_;
  bool closed_{false};
  bool poster_waiting_{false};
  std::uint64_t dropped_{0};
  WakePipe ready_;
  WakePipe room_;
};

struct ShellConfig {
  std::uint32_t listen_address{kListenAddress};
  std::uint16_t listen_port{kListenPort};  // the tests use 0: a free port
  std::int64_t status_period_ns{10 * kNanosecondsPerSecond};
  std::int64_t client_write_timeout_ns{500 * kNanosecondsPerMillisecond};
  std::int64_t stop_join_timeout_ns{150 * kNanosecondsPerMillisecond};
  std::vector<std::string> announce_properties;
  std::size_t mailbox_capacity{1024};
};

struct ShellResult {
  int exit_code{0};
  bool worker_joined{true};
};

class RelayShell final : private FrameSink {
 public:
  RelayShell(ShellConfig shell, const RelayConfig& relay, WorkerConfig worker, GatewayClient& client, EventLog& log,
             PropertySetter& properties, ClockSource& clock);
  ~RelayShell() override;
  RelayShell(const RelayShell&) = delete;
  RelayShell& operator=(const RelayShell&) = delete;

  // Opens the loopback server and the mailbox.
  bool Open(std::string* error);
  std::uint16_t port() const noexcept { return port_; }
  const char* policy_name() const noexcept { return policy_.Name(); }
  // Runs until stop_requested() is true, then stops the worker. The start
  // line of the caller comes before; the final status line comes from here.
  ShellResult Run(const std::function<bool()>& stop_requested);
  // A copy of the counters; safe from another thread.
  RelayCounters counters() const;
  bool in_phase() const;
  // True once the worker thread has finished, also one that Run left behind.
  bool worker_done() const noexcept { return worker_done_.load(); }

 private:
  bool Forward(const std::uint8_t* payload, std::size_t size) override;
  void WorkerMain();
  void Turn(std::int64_t status_deadline_ns);
  void DrainMailbox();
  void Accept();
  void ReadClient();
  void Snapshot();

  ShellConfig config_;
  EventLog& log_;
  PropertySetter& properties_;
  ClockSource& clock_;
  PhaseStartDiscardPolicy policy_;
  GatewayCallMonitor monitor_;
  EventMailbox mailbox_;
  WakePipe worker_wake_;
  GatewayWorker worker_;
  RelayCore core_;
  std::thread worker_thread_;
  std::atomic<bool> worker_done_{false};
  const std::function<bool()>* stop_requested_{nullptr};
  int listen_fd_{-1};
  int client_fd_{-1};
  std::uint16_t port_{0};
  std::uint64_t client_bytes_ignored_{0};
  mutable std::mutex snapshot_mutex_;
  RelayCounters snapshot_{};
  bool snapshot_in_phase_{false};
};

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_RELAY_SHELL_HPP
