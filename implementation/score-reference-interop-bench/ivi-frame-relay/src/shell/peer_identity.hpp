// The peer process of a loopback client of the DE4SDV IVI frame relay.
//
// The model takes the HMI application as subscribed while "the ingress is
// connected", and any local process can connect to 127.0.0.1:4731. So the
// relay names the peer of each client in its client_connected and
// client_refused lines, and the bench checks it against the ingress. The
// relay serves the first client whoever it is; the check is the bench's.
// The lookup is the relay's reading, not a value of the model.
// SO_PEERCRED gives no credentials on a TCP socket (pid 0, uid -1). So the
// relay finds the client's socket in /proc/net/tcp, by its local endpoint
// (the peer of the accepted socket) and its remote endpoint (the relay's
// listener): that line holds the uid and the inode of the socket. A line
// that is not ESTABLISHED (state 01) or has inode 0 is an orphan, for
// example a client that closed before the lookup: it names no owner (its
// uid reads 0), so the relay takes the peer as unknown and does not scan.
// The pid is the process that holds socket:[inode] in /proc/<pid>/fd; that
// scan checks its time budget at each descriptor, so it never stalls the
// main thread for much longer than the budget. The lines log the inode too,
// so the bench can look for it in /proc/<pid of the ingress>/fd when the pid
// stays unknown. On the IVI VM of the bench the relay runs as system in a
// permissive domain, and the ingress runs as system too, so both reads are
// allowed.

#ifndef DE4SDV_IVI_FRAME_RELAY_PEER_IDENTITY_HPP
#define DE4SDV_IVI_FRAME_RELAY_PEER_IDENTITY_HPP

#include <cstdint>
#include <optional>
#include <string>

#include "de4sdv_ivi_frame_relay/relay_core.hpp"

namespace de4sdv::ivi_frame_relay {

struct TcpSocketEntry {
  int state{0};  // the TCP state of the line: 0x01 is ESTABLISHED
  std::int64_t uid{-1};
  std::uint64_t inode{0};
};

constexpr int kTcpEstablished = 0x01;

// An entry that names an owner: ESTABLISHED and with an inode.
bool UsableTcpEntry(const TcpSocketEntry& entry) noexcept;

// The line of /proc/net/tcp with this local and remote endpoint. The
// addresses are the raw 32-bit values of sin_addr.s_addr, as the kernel
// prints them; the ports are in host order.
std::optional<TcpSocketEntry> FindTcpSocket(const std::string& proc_net_tcp, std::uint32_t local_address,
                                            std::uint16_t local_port, std::uint32_t remote_address,
                                            std::uint16_t remote_port);

// The process that holds socket:[inode], scanned in /proc/<pid>/fd within
// budget_ns of CLOCK_MONOTONIC.
std::optional<std::int64_t> FindSocketOwner(std::uint64_t inode, std::int64_t budget_ns);

// The peer of the accepted loopback socket fd.
PeerIdentity LookUpLoopbackPeer(int fd, std::int64_t budget_ns);

}  // namespace de4sdv::ivi_frame_relay

#endif  // DE4SDV_IVI_FRAME_RELAY_PEER_IDENTITY_HPP
