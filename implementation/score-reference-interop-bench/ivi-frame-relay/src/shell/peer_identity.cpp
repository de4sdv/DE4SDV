#include "shell/peer_identity.hpp"

#include <arpa/inet.h>
#include <dirent.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <time.h>
#include <unistd.h>

#include <cerrno>
#include <cstdlib>
#include <fstream>
#include <sstream>
#include <vector>

namespace de4sdv::ivi_frame_relay {

namespace {

std::int64_t MonotonicNs() {
  timespec value{};
  clock_gettime(CLOCK_MONOTONIC, &value);
  return static_cast<std::int64_t>(value.tv_sec) * 1'000'000'000 + value.tv_nsec;
}

// "0100007F:B8A2" into its address and port; false when malformed.
bool ParseEndpoint(const std::string& text, std::uint32_t* address, std::uint16_t* port) {
  const std::size_t colon = text.find(':');
  if (colon != 8U || text.size() != 13U) {
    return false;
  }
  // Named strings: end points into them, so they must outlive the checks.
  const std::string address_text = text.substr(0, 8);
  const std::string port_text = text.substr(9);
  char* end = nullptr;
  const unsigned long raw_address = std::strtoul(address_text.c_str(), &end, 16);
  if (end == nullptr || *end != '\0') {
    return false;
  }
  const unsigned long raw_port = std::strtoul(port_text.c_str(), &end, 16);
  if (end == nullptr || *end != '\0' || raw_port > 0xFFFFUL) {
    return false;
  }
  *address = static_cast<std::uint32_t>(raw_address);
  *port = static_cast<std::uint16_t>(raw_port);
  return true;
}

bool IsNumber(const char* text) {
  if (*text == '\0') {
    return false;
  }
  for (; *text != '\0'; ++text) {
    if (*text < '0' || *text > '9') {
      return false;
    }
  }
  return true;
}

}  // namespace

std::optional<TcpSocketEntry> FindTcpSocket(const std::string& proc_net_tcp, std::uint32_t local_address,
                                            std::uint16_t local_port, std::uint32_t remote_address,
                                            std::uint16_t remote_port) {
  std::istringstream lines{proc_net_tcp};
  std::string line;
  while (std::getline(lines, line)) {
    std::istringstream fields{line};
    std::vector<std::string> tokens;
    std::string token;
    while (fields >> token && tokens.size() < 10U) {
      tokens.push_back(token);
    }
    // sl local rem st tx:rx tr:when retrnsmt uid timeout inode
    if (tokens.size() < 10U) {
      continue;
    }
    std::uint32_t address = 0;
    std::uint16_t port = 0;
    std::uint32_t peer_address = 0;
    std::uint16_t peer_port = 0;
    if (!ParseEndpoint(tokens[1], &address, &port) || !ParseEndpoint(tokens[2], &peer_address, &peer_port)) {
      continue;
    }
    if (address != local_address || port != local_port || peer_address != remote_address ||
        peer_port != remote_port) {
      continue;
    }
    char* end = nullptr;
    const long long uid = std::strtoll(tokens[7].c_str(), &end, 10);
    const unsigned long long inode = std::strtoull(tokens[9].c_str(), &end, 10);
    TcpSocketEntry entry;
    entry.uid = static_cast<std::int64_t>(uid);
    entry.inode = static_cast<std::uint64_t>(inode);
    return entry;
  }
  return std::nullopt;
}

std::optional<std::int64_t> FindSocketOwner(std::uint64_t inode, std::int64_t budget_ns) {
  const std::int64_t give_up = MonotonicNs() + budget_ns;
  const std::string wanted = "socket:[" + std::to_string(inode) + "]";
  DIR* processes = ::opendir("/proc");
  if (processes == nullptr) {
    return std::nullopt;
  }
  std::optional<std::int64_t> owner;
  while (!owner.has_value() && MonotonicNs() < give_up) {
    const dirent* process = ::readdir(processes);
    if (process == nullptr) {
      break;
    }
    if (!IsNumber(process->d_name)) {
      continue;
    }
    const std::string fd_dir = std::string{"/proc/"} + process->d_name + "/fd";
    DIR* fds = ::opendir(fd_dir.c_str());
    if (fds == nullptr) {
      continue;  // gone, or not readable for this uid
    }
    while (const dirent* fd = ::readdir(fds)) {
      if (!IsNumber(fd->d_name)) {
        continue;
      }
      char target[64];
      const std::string link = fd_dir + "/" + fd->d_name;
      const ssize_t length = ::readlink(link.c_str(), target, sizeof(target) - 1);
      if (length > 0) {
        target[length] = '\0';
        if (wanted == target) {
          owner = std::strtoll(process->d_name, nullptr, 10);
          break;
        }
      }
    }
    ::closedir(fds);
  }
  ::closedir(processes);
  return owner;
}

PeerIdentity LookUpLoopbackPeer(int fd, std::int64_t budget_ns) {
  PeerIdentity peer;
  sockaddr_in remote{};
  sockaddr_in local{};
  socklen_t remote_length = sizeof(remote);
  socklen_t local_length = sizeof(local);
  if (::getpeername(fd, reinterpret_cast<sockaddr*>(&remote), &remote_length) != 0 ||
      ::getsockname(fd, reinterpret_cast<sockaddr*>(&local), &local_length) != 0 || remote.sin_family != AF_INET) {
    return peer;
  }
  peer.port = ntohs(remote.sin_port);
  std::ifstream file{"/proc/net/tcp"};
  if (!file) {
    return peer;
  }
  std::stringstream text;
  text << file.rdbuf();
  // The client's socket: its local end is the peer of fd, its remote end the listener.
  const auto entry =
      FindTcpSocket(text.str(), remote.sin_addr.s_addr, peer.port, local.sin_addr.s_addr, ntohs(local.sin_port));
  if (!entry.has_value()) {
    return peer;
  }
  peer.source = "proc_net_tcp";
  peer.uid_known = true;
  peer.uid = entry->uid;
  if (const auto pid = FindSocketOwner(entry->inode, budget_ns)) {
    peer.pid_known = true;
    peer.pid = *pid;
  }
  return peer;
}

}  // namespace de4sdv::ivi_frame_relay
