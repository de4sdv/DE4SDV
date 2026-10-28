// The thin POSIX shell of the DE4SDV minimal SOME/IP receiver.
//
// One thread and one poll() loop over four sockets: the SOME/IP-SD socket
// (UDP, bound to the SD port, member of the SD multicast group unless
// --no-multicast), the TCP connection to the reliable endpoint of someipd,
// the loopback listener of the frame server and its one client. The pure
// core decides everything; the shell turns socket events into core calls
// and core actions into socket calls. It never calls back into the core
// from inside a core call: a connect result waits for the next loop turn.
//
// Log lines are JSON objects on stdout (Linux) or liblog lines with the tag
// de4sdv_someip_receiver (Android). SIGTERM or SIGINT stop the receiver: it
// sends StopSubscribeEventgroup, writes a final status line and exits 0.

#include <arpa/inet.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <signal.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <csignal>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

#ifdef __ANDROID__
#include <android/log.h>
#include <sys/system_properties.h>
#endif

#include "de4sdv_someip_receiver/discard_policy.hpp"
#include "de4sdv_someip_receiver/event_log.hpp"
#include "de4sdv_someip_receiver/options.hpp"
#include "de4sdv_someip_receiver/receiver_core.hpp"

namespace {

using de4sdv::someip_receiver::Clock;
using de4sdv::someip_receiver::EventLog;
using de4sdv::someip_receiver::FrameSink;
using de4sdv::someip_receiver::Ipv4Endpoint;
using de4sdv::someip_receiver::Ipv4ToText;
using de4sdv::someip_receiver::kL4ProtocolTcp;
using de4sdv::someip_receiver::kNanosecondsPerMillisecond;
using de4sdv::someip_receiver::kNoDeadline;
using de4sdv::someip_receiver::LogRecord;
using de4sdv::someip_receiver::ParseOptions;
using de4sdv::someip_receiver::PhaseStartDiscardPolicy;
using de4sdv::someip_receiver::ReceiverCore;
using de4sdv::someip_receiver::ReceiverOptions;
using de4sdv::someip_receiver::SplitProperty;
using de4sdv::someip_receiver::StartRecord;
using de4sdv::someip_receiver::SubscriptionTransport;
using de4sdv::someip_receiver::Usage;

constexpr int kExitUsage = 2;
constexpr int kExitListenFailed = 3;
constexpr int kExitSdSocketFailed = 4;
constexpr std::int64_t kMaxPollWaitNs = 100 * kNanosecondsPerMillisecond;
constexpr int kMaxReadsPerTurn = 32;

volatile std::sig_atomic_t g_stop_requested = 0;

void OnStopSignal(int) { g_stop_requested = 1; }

std::int64_t ClockNs(clockid_t clock) {
  timespec value{};
  clock_gettime(clock, &value);
  return static_cast<std::int64_t>(value.tv_sec) * 1'000'000'000 + value.tv_nsec;
}

Clock Now() { return Clock{ClockNs(CLOCK_MONOTONIC), ClockNs(CLOCK_REALTIME)}; }

sockaddr_in SocketAddress(std::uint32_t address, std::uint16_t port) {
  sockaddr_in socket_address{};
  socket_address.sin_family = AF_INET;
  socket_address.sin_port = htons(port);
  socket_address.sin_addr.s_addr = htonl(address);
  return socket_address;
}

void CloseFd(int& fd) {
  if (fd >= 0) {
    ::close(fd);
    fd = -1;
  }
}

class LineLog final : public EventLog {
 public:
  void Log(const Clock& now, const LogRecord& record) override { Write(record.ToJson(now)); }

  static void Write(const std::string& line) {
#ifdef __ANDROID__
    __android_log_write(ANDROID_LOG_INFO, "de4sdv_someip_receiver", line.c_str());
#else
    std::fputs(line.c_str(), stdout);
    std::fputc('\n', stdout);
    std::fflush(stdout);
#endif
  }
};

class Shell final : public SubscriptionTransport, public FrameSink {
 public:
  Shell(const ReceiverOptions& options, LineLog& log) : options_{options}, log_{log} {}
  ~Shell() override {
    CloseFd(tcp_fd_);
    CloseFd(client_fd_);
    CloseFd(listen_fd_);
    CloseFd(sd_fd_);
  }
  Shell(const Shell&) = delete;
  Shell& operator=(const Shell&) = delete;

  void Attach(ReceiverCore* core) { core_ = core; }

  bool OpenListener(std::string* error) {
    listen_fd_ = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
    if (listen_fd_ < 0) {
      *error = std::string{"socket: "} + std::strerror(errno);
      return false;
    }
    const int one = 1;
    ::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    const sockaddr_in address = SocketAddress(options_.listen_address, options_.listen_port);
    if (::bind(listen_fd_, reinterpret_cast<const sockaddr*>(&address), sizeof(address)) != 0 ||
        ::listen(listen_fd_, 1) != 0) {
      *error = std::string{"bind/listen "} + Ipv4ToText(options_.listen_address) + ":" +
               std::to_string(options_.listen_port) + ": " + std::strerror(errno);
      CloseFd(listen_fd_);
      return false;
    }
    return true;
  }

  // Binds the SD port on all local addresses; joins the group unless disabled.
  bool OpenSdSocket(std::string* error, std::string* multicast_result) {
    sd_fd_ = ::socket(AF_INET, SOCK_DGRAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
    if (sd_fd_ < 0) {
      *error = std::string{"socket: "} + std::strerror(errno);
      return false;
    }
    const int one = 1;
    ::setsockopt(sd_fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    ::setsockopt(sd_fd_, IPPROTO_IP, IP_PKTINFO, &one, sizeof(one));
    const sockaddr_in address = SocketAddress(INADDR_ANY, options_.receiver.subscription.sd_port);
    if (::bind(sd_fd_, reinterpret_cast<const sockaddr*>(&address), sizeof(address)) != 0) {
      *error = std::string{"bind SD port "} + std::to_string(options_.receiver.subscription.sd_port) + ": " +
               std::strerror(errno);
      CloseFd(sd_fd_);
      return false;
    }
    if (!options_.join_multicast) {
      *multicast_result = "not_joined_by_option";
      return true;
    }
    ip_mreq membership{};
    membership.imr_multiaddr.s_addr = htonl(options_.multicast_group);
    membership.imr_interface.s_addr = htonl(options_.multicast_interface);
    if (::setsockopt(sd_fd_, IPPROTO_IP, IP_ADD_MEMBERSHIP, &membership, sizeof(membership)) != 0) {
      // Not fatal: the unicast fallback still connects and subscribes.
      *multicast_result = std::string{"join_failed: "} + std::strerror(errno);
      return true;
    }
    *multicast_result = "joined";
    return true;
  }

  // SubscriptionTransport
  void ConnectTcp(const Ipv4Endpoint& server) override {
    CloseFd(tcp_fd_);
    ++tcp_generation_;
    tcp_connected_ = false;
    pending_connect_errno_ = 0;
    tcp_fd_ = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC | SOCK_NONBLOCK, 0);
    if (tcp_fd_ < 0) {
      pending_connect_errno_ = errno;
      return;
    }
    const sockaddr_in address = SocketAddress(server.address, server.port);
    if (::connect(tcp_fd_, reinterpret_cast<const sockaddr*>(&address), sizeof(address)) != 0 &&
        errno != EINPROGRESS) {
      pending_connect_errno_ = errno;  // reported in the next loop turn
      CloseFd(tcp_fd_);
    }
  }

  void CloseTcp() override {
    CloseFd(tcp_fd_);
    ++tcp_generation_;
    tcp_connected_ = false;
    pending_connect_errno_ = 0;
  }

  bool SendSd(const std::vector<std::uint8_t>& datagram, std::uint32_t address, std::uint16_t port) override {
    const sockaddr_in target = SocketAddress(address, port);
    const ssize_t sent = ::sendto(sd_fd_, datagram.data(), datagram.size(), 0,
                                  reinterpret_cast<const sockaddr*>(&target), sizeof(target));
    return sent == static_cast<ssize_t>(datagram.size());
  }

  // FrameSink: the whole payload or nothing; a failed or slow write closes the client.
  bool Forward(const std::uint8_t* payload, std::size_t size) override {
    if (client_fd_ < 0) {
      return false;
    }
    const std::int64_t deadline = ClockNs(CLOCK_MONOTONIC) + options_.client_write_timeout_ns;
    std::size_t written = 0;
    while (written < size) {
      const ssize_t sent = ::send(client_fd_, payload + written, size - written, MSG_NOSIGNAL);
      if (sent > 0) {
        written += static_cast<std::size_t>(sent);
        continue;
      }
      if (sent < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) {
        const std::int64_t left = deadline - ClockNs(CLOCK_MONOTONIC);
        if (left <= 0) {
          break;
        }
        pollfd writable{client_fd_, POLLOUT, 0};
        ::poll(&writable, 1, static_cast<int>(std::max<std::int64_t>(1, left / kNanosecondsPerMillisecond)));
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

  // One loop turn: wait for the sockets or the next deadline and dispatch.
  void Turn(std::int64_t status_deadline_ns) {
    ReportPendingConnectError();
    const Clock before = Now();
    std::int64_t wait_ns = std::min({core_->NextDeadline(), status_deadline_ns, before.monotonic_ns + kMaxPollWaitNs}) -
                           before.monotonic_ns;
    wait_ns = std::max<std::int64_t>(0, wait_ns);
    std::vector<pollfd> fds;
    fds.push_back(pollfd{sd_fd_, POLLIN, 0});
    fds.push_back(pollfd{listen_fd_, POLLIN, 0});
    const std::size_t client_index = fds.size();
    if (client_fd_ >= 0) {
      fds.push_back(pollfd{client_fd_, POLLIN, 0});
    }
    const std::size_t tcp_index = fds.size();
    // A socket number can come back for a new socket in the same turn; the
    // generation tells the polled TCP socket from a newer one.
    const std::uint64_t tcp_generation = tcp_generation_;
    if (tcp_fd_ >= 0) {
      fds.push_back(pollfd{tcp_fd_, static_cast<short>(tcp_connected_ ? POLLIN : POLLOUT), 0});
    }
    const int timeout_ms = static_cast<int>((wait_ns + kNanosecondsPerMillisecond - 1) / kNanosecondsPerMillisecond);
    const int ready = ::poll(fds.data(), static_cast<nfds_t>(fds.size()), timeout_ms);
    if (ready < 0 && errno != EINTR) {
      log_.Log(Now(), LogRecord{"poll_failed"}.Text("error", std::strerror(errno)));
    }
    if (ready > 0) {
      if (fds[0].revents != 0) {
        ReadSd();
      }
      if (fds[1].revents != 0) {
        Accept();
      }
      if (client_fd_ >= 0 && client_index < fds.size() && fds[client_index].fd == client_fd_ &&
          fds[client_index].revents != 0) {
        ReadClient();
      }
      if (tcp_fd_ >= 0 && tcp_generation == tcp_generation_ && tcp_index < fds.size() &&
          fds[tcp_index].revents != 0) {
        if (tcp_connected_) {
          ReadTcp();
        } else {
          FinishConnect();
        }
      }
    }
    core_->OnTick(Now());
  }

  std::uint64_t client_bytes_ignored() const noexcept { return client_bytes_ignored_; }

 private:
  void ReportPendingConnectError() {
    if (pending_connect_errno_ != 0) {
      const int error_number = pending_connect_errno_;
      pending_connect_errno_ = 0;
      core_->OnTcpConnectFailed(Now(), error_number);
    }
  }

  void FinishConnect() {
    int error_number = 0;
    socklen_t length = sizeof(error_number);
    if (::getsockopt(tcp_fd_, SOL_SOCKET, SO_ERROR, &error_number, &length) != 0) {
      error_number = errno;
    }
    if (error_number != 0) {
      CloseFd(tcp_fd_);
      core_->OnTcpConnectFailed(Now(), error_number);
      return;
    }
    sockaddr_in local{};
    socklen_t local_length = sizeof(local);
    if (::getsockname(tcp_fd_, reinterpret_cast<sockaddr*>(&local), &local_length) != 0) {
      const int name_error = errno;
      CloseFd(tcp_fd_);
      core_->OnTcpConnectFailed(Now(), name_error);
      return;
    }
    tcp_connected_ = true;
    core_->OnTcpConnected(Now(), Ipv4Endpoint{ntohl(local.sin_addr.s_addr), ntohs(local.sin_port), kL4ProtocolTcp});
  }

  void ReadTcp() {
    for (int read = 0; read < kMaxReadsPerTurn && tcp_fd_ >= 0 && tcp_connected_; ++read) {
      const ssize_t received = ::recv(tcp_fd_, buffer_.data(), buffer_.size(), 0);
      if (received > 0) {
        core_->OnTcpData(Now(), buffer_.data(), static_cast<std::size_t>(received));
        continue;
      }
      if (received < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) {
        return;
      }
      CloseFd(tcp_fd_);
      tcp_connected_ = false;
      core_->OnTcpClosed(Now());
      return;
    }
  }

  void ReadSd() {
    for (int read = 0; read < kMaxReadsPerTurn; ++read) {
      sockaddr_in source{};
      iovec io{buffer_.data(), buffer_.size()};
      alignas(cmsghdr) char control[CMSG_SPACE(sizeof(in_pktinfo))];
      msghdr message{};
      message.msg_name = &source;
      message.msg_namelen = sizeof(source);
      message.msg_iov = &io;
      message.msg_iovlen = 1;
      message.msg_control = control;
      message.msg_controllen = sizeof(control);
      const ssize_t received = ::recvmsg(sd_fd_, &message, 0);
      if (received < 0) {
        return;  // EAGAIN, or an error that the next datagram shows again
      }
      bool multicast = false;
      for (cmsghdr* header = CMSG_FIRSTHDR(&message); header != nullptr; header = CMSG_NXTHDR(&message, header)) {
        if (header->cmsg_level == IPPROTO_IP && header->cmsg_type == IP_PKTINFO) {
          in_pktinfo info{};
          std::memcpy(&info, CMSG_DATA(header), sizeof(info));
          multicast = IN_MULTICAST(ntohl(info.ipi_addr.s_addr));
        }
      }
      if ((message.msg_flags & MSG_TRUNC) != 0) {
        continue;  // larger than the buffer: not an SD message of this service
      }
      core_->OnSdDatagram(Now(), ntohl(source.sin_addr.s_addr), multicast, buffer_.data(),
                          static_cast<std::size_t>(received));
    }
  }

  void Accept() {
    const int fd = ::accept4(listen_fd_, nullptr, nullptr, SOCK_CLOEXEC | SOCK_NONBLOCK);
    if (fd < 0) {
      return;
    }
    // One client only: the core refuses a second one, logs it, and the shell
    // closes it. A refused client is not served and starts no phase.
    if (!core_->OnClientAccepted(Now())) {
      ::close(fd);
      return;
    }
    const int one = 1;
    ::setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
    client_fd_ = fd;
  }

  void ReadClient() {
    char discard[256];
    for (int read = 0; read < kMaxReadsPerTurn; ++read) {
      const ssize_t received = ::recv(client_fd_, discard, sizeof(discard), 0);
      if (received > 0) {
        client_bytes_ignored_ += static_cast<std::uint64_t>(received);  // the ingress sends nothing
        continue;
      }
      if (received < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR)) {
        return;
      }
      CloseFd(client_fd_);
      core_->OnClientDisconnected(Now());
      return;
    }
  }

  const ReceiverOptions& options_;
  LineLog& log_;
  ReceiverCore* core_{nullptr};
  int sd_fd_{-1};
  int listen_fd_{-1};
  int client_fd_{-1};
  int tcp_fd_{-1};
  bool tcp_connected_{false};
  std::uint64_t tcp_generation_{0};
  int pending_connect_errno_{0};
  std::uint64_t client_bytes_ignored_{0};
  std::vector<std::uint8_t> buffer_ = std::vector<std::uint8_t>(65536);
};

}  // namespace

int main(int argc, char** argv) {
  std::vector<std::string> arguments(argv + 1, argv + argc);
  const auto parsed = ParseOptions(arguments);
  if (parsed.help) {
    std::fputs(Usage().c_str(), stdout);
    return 0;
  }
  if (!parsed.options.has_value()) {
    std::fprintf(stderr, "de4sdv_someip_receiver: %s\n%s", parsed.error.c_str(), Usage().c_str());
    return kExitUsage;
  }
  const ReceiverOptions options = *parsed.options;

  struct sigaction action {};
  action.sa_handler = OnStopSignal;
  sigemptyset(&action.sa_mask);
  sigaction(SIGTERM, &action, nullptr);
  sigaction(SIGINT, &action, nullptr);
  std::signal(SIGPIPE, SIG_IGN);

  LineLog log;
  PhaseStartDiscardPolicy policy;
  Shell shell{options, log};
  std::string error;
  if (!shell.OpenListener(&error)) {
    log.Log(Now(), LogRecord{"listen_failed"}.Text("error", error));
    return kExitListenFailed;
  }
  std::string multicast_result;
  if (!shell.OpenSdSocket(&error, &multicast_result)) {
    log.Log(Now(), LogRecord{"sd_socket_failed"}.Text("error", error));
    return kExitSdSocketFailed;
  }
  ReceiverCore core{options.receiver, shell, shell, policy, log};
  shell.Attach(&core);
  log.Log(Now(), StartRecord(options, policy.Name(), static_cast<std::int64_t>(::getpid()))
                     .Text("multicast_membership", multicast_result));
  if (!options.announce_property.empty()) {
    // The loopback server listens now, so the ingress may start (it exits when nothing listens).
    std::string name;
    std::string value;
    SplitProperty(options.announce_property, &name, &value);
#ifdef __ANDROID__
    const int result = __system_property_set(name.c_str(), value.c_str());
    log.Log(Now(), LogRecord{"property_announced"}.Text("name", name).Text("value", value).Bool("ok", result == 0));
#else
    log.Log(Now(), LogRecord{"property_not_announced"}.Text("name", name).Text("reason", "not Android"));
#endif
  }

  std::int64_t next_status_ns = Now().monotonic_ns + options.status_period_ns;
  while (g_stop_requested == 0) {
    shell.Turn(next_status_ns);
    const Clock now = Now();
    if (now.monotonic_ns >= next_status_ns) {
      log.Log(now, core.Status("status").Unsigned("client_bytes_ignored", shell.client_bytes_ignored()));
      next_status_ns += options.status_period_ns;
      if (next_status_ns <= now.monotonic_ns) {
        next_status_ns = now.monotonic_ns + options.status_period_ns;
      }
    }
  }
  const Clock stop = Now();
  log.Log(stop, LogRecord{"stop_requested"});
  core.Stop(stop);
  log.Log(Now(), core.Status("final_status").Unsigned("client_bytes_ignored", shell.client_bytes_ignored()));
  log.Log(Now(), LogRecord{"exit"}.Signed("code", 0));
  return 0;
}
