#include "shell/relay_shell.hpp"

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <chrono>
#include <cstdio>
#include <cstring>
#include <limits>
#include <utility>

#ifdef __ANDROID__
#include <android/log.h>
#include <sys/system_properties.h>
#endif

namespace de4sdv::ivi_frame_relay {

namespace {

constexpr std::int64_t kMaxPollWaitNs = 100 * kNanosecondsPerMillisecond;
constexpr int kMaxReadsPerTurn = 32;
// A blocked write to the client, and the wait at stop, check this often.
constexpr std::int64_t kCheckPeriodMs = 10;
constexpr std::int64_t kMailboxRoomWaitMs = 20;

std::int64_t ClockNs(clockid_t clock) {
  timespec value{};
  clock_gettime(clock, &value);
  return static_cast<std::int64_t>(value.tv_sec) * kNanosecondsPerSecond + value.tv_nsec;
}

void CloseFd(int& fd) {
  if (fd >= 0) {
    ::close(fd);
    fd = -1;
  }
}

int PollTimeoutMs(std::int64_t wait_ns) {
  const std::int64_t clamped = std::clamp<std::int64_t>(wait_ns, 0, kMaxPollWaitNs);
  return static_cast<int>((clamped + kNanosecondsPerMillisecond - 1) / kNanosecondsPerMillisecond);
}

}  // namespace

Clock RealClock::Now() {
  Clock best{};
  std::int64_t best_window = std::numeric_limits<std::int64_t>::max();
  for (int attempt = 0; attempt < 3; ++attempt) {
    const std::int64_t before = ClockNs(CLOCK_MONOTONIC);
    const std::int64_t realtime = ClockNs(CLOCK_REALTIME);
    const std::int64_t after = ClockNs(CLOCK_MONOTONIC);
    if (after - before < best_window) {
      best_window = after - before;
      best = Clock{before + best_window / 2, realtime};
    }
    if (best_window < 100'000) {
      break;
    }
  }
  return best;
}

void LineLog::Log(const Clock& now, const LogRecord& record) {
  const std::string line = record.ToJson(now);
  const std::lock_guard<std::mutex> lock{mutex_};
  Write(line);
}

void LineLog::Write(const std::string& line) {
#ifdef __ANDROID__
  __android_log_write(ANDROID_LOG_INFO, "de4sdv_ivi_frame_relay", line.c_str());
#else
  std::fputs(line.c_str(), stdout);
  std::fputc('\n', stdout);
  std::fflush(stdout);
#endif
}

bool SystemProperties::SetProperty(const Clock& now, const std::string& name, const std::string& value) {
#ifdef __ANDROID__
  const bool ok = __system_property_set(name.c_str(), value.c_str()) == 0;
  log_.Log(now, LogRecord{"property_announced"}.Text("name", name).Text("value", value).Bool("ok", ok));
  return ok;
#else
  log_.Log(now, LogRecord{"property_not_announced"}.Text("name", name).Text("value", value).Text("reason",
                                                                                                  "not Android"));
  return true;
#endif
}

WakePipe::~WakePipe() {
  CloseFd(pipe_[0]);
  CloseFd(pipe_[1]);
}

bool WakePipe::Open(std::string* error) {
  if (::pipe(pipe_) != 0) {
    *error = std::string{"pipe: "} + std::strerror(errno);
    return false;
  }
  for (const int fd : pipe_) {
    ::fcntl(fd, F_SETFD, FD_CLOEXEC);
    ::fcntl(fd, F_SETFL, ::fcntl(fd, F_GETFL) | O_NONBLOCK);
  }
  return true;
}

void WakePipe::Wake() noexcept {
  if (pipe_[1] >= 0) {
    const char byte = 1;
    (void)!::write(pipe_[1], &byte, 1);  // a full pipe already wakes the reader
  }
}

void WakePipe::Drain() {
  char drain[64];
  while (pipe_[0] >= 0 && ::read(pipe_[0], drain, sizeof(drain)) > 0) {
  }
}

void WakePipe::Wait(int timeout_ms) {
  if (timeout_ms > 0) {
    pollfd readable{pipe_[0], POLLIN, 0};
    ::poll(&readable, 1, timeout_ms);
  }
  Drain();
}

EventMailbox::EventMailbox(std::size_t capacity) : capacity_{std::max<std::size_t>(capacity, 1U)} {}

bool EventMailbox::Open(std::string* error) { return ready_.Open(error) && room_.Open(error); }

void EventMailbox::Wake() { ready_.Wake(); }

void EventMailbox::Post(WorkerEvent&& event) {
  std::unique_lock<std::mutex> lock{mutex_};
  while (queue_.size() >= capacity_ && !closed_) {
    poster_waiting_ = true;
    lock.unlock();
    room_.Wait(static_cast<int>(kMailboxRoomWaitMs));
    lock.lock();
  }
  poster_waiting_ = false;
  if (queue_.size() >= capacity_) {
    ++dropped_;
    return;
  }
  const bool was_empty = queue_.empty();
  queue_.push_back(std::move(event));
  if (was_empty) {
    ready_.Wake();
  }
}

std::deque<WorkerEvent> EventMailbox::TakeAll() {
  std::deque<WorkerEvent> taken;
  const std::lock_guard<std::mutex> lock{mutex_};
  taken.swap(queue_);
  ready_.Drain();
  if (poster_waiting_) {
    room_.Wake();
  }
  return taken;
}

void EventMailbox::Close() {
  const std::lock_guard<std::mutex> lock{mutex_};
  closed_ = true;
  room_.Wake();
}

std::uint64_t EventMailbox::dropped() const {
  const std::lock_guard<std::mutex> lock{mutex_};
  return dropped_;
}

RelayShell::RelayShell(ShellConfig shell, const RelayConfig& relay, WorkerConfig worker, GatewayClient& client,
                       EventLog& log, PropertySetter& properties, ClockSource& clock)
    : config_{std::move(shell)},
      log_{log},
      properties_{properties},
      clock_{clock},
      mailbox_{config_.mailbox_capacity},
      worker_{std::move(worker), client, mailbox_, clock_, &monitor_, &worker_wake_},
      core_{relay, *this, policy_, log_, &properties_, &monitor_} {}

RelayShell::~RelayShell() {
  if (worker_thread_.joinable()) {
    // Only after a stop that left the worker behind; the caller should have
    // ended the process instead.
    worker_.RequestStop();
    worker_thread_.join();
  }
  CloseFd(client_fd_);
  CloseFd(listen_fd_);
}

bool RelayShell::Open(std::string* error) {
  if (!mailbox_.Open(error) || !worker_wake_.Open(error)) {
    return false;
  }
  listen_fd_ = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
  if (listen_fd_ < 0) {
    *error = std::string{"socket: "} + std::strerror(errno);
    return false;
  }
  const int one = 1;
  ::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
  sockaddr_in address{};
  address.sin_family = AF_INET;
  address.sin_port = htons(config_.listen_port);
  address.sin_addr.s_addr = htonl(config_.listen_address);
  if (::bind(listen_fd_, reinterpret_cast<const sockaddr*>(&address), sizeof(address)) != 0 ||
      ::listen(listen_fd_, 1) != 0) {
    *error = "bind/listen port " + std::to_string(config_.listen_port) + ": " + std::strerror(errno);
    CloseFd(listen_fd_);
    return false;
  }
  sockaddr_in bound{};
  socklen_t length = sizeof(bound);
  if (::getsockname(listen_fd_, reinterpret_cast<sockaddr*>(&bound), &length) == 0) {
    port_ = ntohs(bound.sin_port);
  }
  return true;
}

void RelayShell::WorkerMain() {
  while (!worker_.stop_requested()) {
    const std::int64_t deadline = worker_.Step();
    const std::int64_t wait_ns = deadline - clock_.Now().monotonic_ns;
    if (wait_ns > 0) {
      // Rounded up, so the wait does not end just before the deadline.
      const std::int64_t wait_ms =
          std::min<std::int64_t>((wait_ns + kNanosecondsPerMillisecond - 1) / kNanosecondsPerMillisecond, 60'000);
      worker_wake_.Wait(static_cast<int>(wait_ms));
    } else {
      worker_wake_.Drain();
    }
  }
  worker_.Finish();
  mailbox_.Wake();
  worker_done_.store(true);  // the last access to the shell from this thread
}

bool RelayShell::Forward(const std::uint8_t* payload, std::size_t size) {
  if (client_fd_ < 0) {
    return false;
  }
  const std::int64_t deadline = ClockNs(CLOCK_MONOTONIC) + config_.client_write_timeout_ns;
  std::size_t written = 0;
  while (written < size) {
    const ssize_t sent = ::send(client_fd_, payload + written, size - written, MSG_NOSIGNAL);
    if (sent > 0) {
      written += static_cast<std::size_t>(sent);
      continue;
    }
    if (sent < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) {
      // A stop request ends the wait: init's gentle_kill gives 200 ms
      // between SIGTERM and SIGKILL, and the write timeout is longer.
      const std::int64_t left = deadline - ClockNs(CLOCK_MONOTONIC);
      if (left <= 0 || (stop_requested_ != nullptr && (*stop_requested_)())) {
        break;
      }
      pollfd writable{client_fd_, POLLOUT, 0};
      ::poll(&writable, 1,
             static_cast<int>(std::clamp<std::int64_t>(left / kNanosecondsPerMillisecond, 1, kCheckPeriodMs)));
      continue;
    }
    break;
  }
  if (written == size) {
    return true;
  }
  CloseFd(client_fd_);
  return false;
}

void RelayShell::DrainMailbox() {
  for (const WorkerEvent& event : mailbox_.TakeAll()) {
    core_.OnWorkerEvent(event);
  }
}

void RelayShell::Accept() {
  const int fd = ::accept4(listen_fd_, nullptr, nullptr, SOCK_CLOEXEC | SOCK_NONBLOCK);
  if (fd < 0) {
    return;
  }
  // One client only: the core refuses a second one, logs it, and the shell
  // closes it. A refused client is not served and starts no phase.
  if (!core_.OnClientAccepted(clock_.Now())) {
    ::close(fd);
    return;
  }
  const int one = 1;
  ::setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
  client_fd_ = fd;
}

void RelayShell::ReadClient() {
  char discard[256];
  for (int read = 0; read < kMaxReadsPerTurn && client_fd_ >= 0; ++read) {
    const ssize_t received = ::recv(client_fd_, discard, sizeof(discard), 0);
    if (received > 0) {
      client_bytes_ignored_ += static_cast<std::uint64_t>(received);  // the ingress sends nothing
      continue;
    }
    if (received < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) {
      return;
    }
    CloseFd(client_fd_);
    core_.OnClientDisconnected(clock_.Now());
    return;
  }
}

void RelayShell::Snapshot() {
  const std::lock_guard<std::mutex> lock{snapshot_mutex_};
  snapshot_ = core_.counters();
  snapshot_in_phase_ = core_.in_phase();
}

RelayCounters RelayShell::counters() const {
  const std::lock_guard<std::mutex> lock{snapshot_mutex_};
  return snapshot_;
}

bool RelayShell::in_phase() const {
  const std::lock_guard<std::mutex> lock{snapshot_mutex_};
  return snapshot_in_phase_;
}

void RelayShell::Turn(std::int64_t status_deadline_ns) {
  const Clock before = clock_.Now();
  const std::int64_t deadline = std::min(core_.NextDeadline(), status_deadline_ns);
  std::vector<pollfd> fds;
  fds.push_back(pollfd{mailbox_.wake_fd(), POLLIN, 0});
  fds.push_back(pollfd{listen_fd_, POLLIN, 0});
  const int polled_client = client_fd_;
  if (polled_client >= 0) {
    fds.push_back(pollfd{polled_client, POLLIN, 0});
  }
  const int ready = ::poll(fds.data(), static_cast<nfds_t>(fds.size()), PollTimeoutMs(deadline - before.monotonic_ns));
  if (ready < 0 && errno != EINTR) {
    log_.Log(clock_.Now(), LogRecord{"poll_failed"}.Text("error", std::strerror(errno)));
  }
  if (ready > 0) {
    if (fds[0].revents != 0) {
      DrainMailbox();
    }
    if (fds[1].revents != 0) {
      Accept();
    }
    // A failed write in DrainMailbox may have closed the polled client.
    if (polled_client >= 0 && client_fd_ == polled_client && fds.size() > 2U && fds[2].revents != 0) {
      ReadClient();
    }
  }
  core_.OnTick(clock_.Now());
  Snapshot();
}

ShellResult RelayShell::Run(const std::function<bool()>& stop_requested) {
  stop_requested_ = &stop_requested;
  core_.OnStart(clock_.Now());
  // The loopback server listens: the properties of the ingress, then its
  // first start trigger (the core repeats it until the first client).
  for (const std::string& property : config_.announce_properties) {
    std::string name;
    std::string value;
    if (SplitProperty(property, &name, &value)) {
      properties_.SetProperty(clock_.Now(), name, value);
    }
  }
  core_.OnListening(clock_.Now());
  worker_.Start();
  worker_thread_ = std::thread{[this] { WorkerMain(); }};

  std::int64_t next_status_ns = clock_.Now().monotonic_ns + config_.status_period_ns;
  while (!stop_requested()) {
    Turn(next_status_ns);
    const Clock now = clock_.Now();
    if (now.monotonic_ns >= next_status_ns) {
      log_.Log(now, core_.Status("status").Unsigned("client_bytes_ignored", client_bytes_ignored_));
      next_status_ns += config_.status_period_ns;
      if (next_status_ns <= now.monotonic_ns) {
        next_status_ns = now.monotonic_ns + config_.status_period_ns;
      }
    }
  }

  const Clock stop = clock_.Now();
  log_.Log(stop, LogRecord{"stop_requested"});
  core_.Stop(stop);
  worker_.RequestStop();
  const std::int64_t give_up_ns = stop.monotonic_ns + config_.stop_join_timeout_ns;
  while (!worker_done_.load() && clock_.Now().monotonic_ns < give_up_ns) {
    pollfd wake{mailbox_.wake_fd(), POLLIN, 0};
    ::poll(&wake, 1, static_cast<int>(kCheckPeriodMs));
    DrainMailbox();
  }
  ShellResult result;
  if (worker_done_.load()) {
    worker_thread_.join();
    DrainMailbox();
  } else {
    const auto call = monitor_.Current();
    log_.Log(clock_.Now(), LogRecord{"gateway_worker_not_joined"}
                               .Text("call", call.has_value() ? call->name : "")
                               .Signed("running_ns", call.has_value() ? clock_.Now().monotonic_ns - call->since_ns : 0)
                               .Signed("waited_ns", config_.stop_join_timeout_ns));
    mailbox_.Close();
    worker_thread_.detach();
    result.worker_joined = false;
  }
  Snapshot();
  log_.Log(clock_.Now(), core_.Status("final_status")
                             .Unsigned("client_bytes_ignored", client_bytes_ignored_)
                             .Unsigned("mailbox_dropped", mailbox_.dropped()));
  CloseFd(client_fd_);
  stop_requested_ = nullptr;
  return result;
}

}  // namespace de4sdv::ivi_frame_relay
