// Tests of the peer lookup of a loopback client (/proc/net/tcp, then the
// owner of the socket inode) and of the mask that keeps the stop signals off
// the threads that the relay creates.

#include <arpa/inet.h>
#include <netinet/in.h>
#include <pthread.h>
#include <signal.h>
#include <sys/socket.h>
#include <unistd.h>

#include <gtest/gtest.h>

#include <string>
#include <thread>

#include "shell/peer_identity.hpp"
#include "shell/relay_shell.hpp"

namespace {

using de4sdv::ivi_frame_relay::BlockStopSignals;
using de4sdv::ivi_frame_relay::FindTcpSocket;
using de4sdv::ivi_frame_relay::LookUpLoopbackPeer;
using de4sdv::ivi_frame_relay::PeerIdentity;

// Two lines of /proc/net/tcp on a little-endian host: the relay's accepted
// socket (local 4731) and the client's socket (local 47266, remote 4731).
const char* const kProcNetTcp =
    "  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode\n"
    "   0: 0100007F:127B 00000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 5131250 1 0 100 0 0 10 0\n"
    "   1: 0100007F:127B 0100007F:B8A2 01 00000000:00000000 00:00000000 00000000  1000        0 5131253 1 0 20 4 30 10 -1\n"
    "   2: 0100007F:B8A2 0100007F:127B 01 00000000:00000000 00:00000000 00000000  1001        0 5131252 1 0 20 4 30 10 -1\n";

constexpr std::uint32_t kLoopbackRaw = 0x0100007FU;  // 127.0.0.1 as s_addr on a little-endian host

TEST(PeerIdentity, FindsTheClientSocketByItsTwoEndpoints) {
  const auto client = FindTcpSocket(kProcNetTcp, kLoopbackRaw, 47266, kLoopbackRaw, 4731);
  ASSERT_TRUE(client.has_value());
  EXPECT_EQ(client->uid, 1001);
  EXPECT_EQ(client->inode, 5131252U);
  const auto relay_side = FindTcpSocket(kProcNetTcp, kLoopbackRaw, 4731, kLoopbackRaw, 47266);
  ASSERT_TRUE(relay_side.has_value());
  EXPECT_EQ(relay_side->inode, 5131253U);
  EXPECT_FALSE(FindTcpSocket(kProcNetTcp, kLoopbackRaw, 47267, kLoopbackRaw, 4731).has_value());
  EXPECT_FALSE(FindTcpSocket("garbage\n0: x y\n", kLoopbackRaw, 47266, kLoopbackRaw, 4731).has_value());
}

TEST(PeerIdentity, NamesTheProcessOfARealLoopbackClient) {
  const int server = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
  sockaddr_in address{};
  address.sin_family = AF_INET;
  address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
  ASSERT_EQ(::bind(server, reinterpret_cast<const sockaddr*>(&address), sizeof(address)), 0);
  ASSERT_EQ(::listen(server, 1), 0);
  socklen_t length = sizeof(address);
  ASSERT_EQ(::getsockname(server, reinterpret_cast<sockaddr*>(&address), &length), 0);
  const int client = ::socket(AF_INET, SOCK_STREAM | SOCK_CLOEXEC, 0);
  ASSERT_EQ(::connect(client, reinterpret_cast<const sockaddr*>(&address), sizeof(address)), 0);
  const int accepted = ::accept(server, nullptr, nullptr);
  ASSERT_GE(accepted, 0);
  const PeerIdentity peer = LookUpLoopbackPeer(accepted, 2'000'000'000);
  EXPECT_STREQ(peer.source, "proc_net_tcp");
  EXPECT_NE(peer.port, 0);
  EXPECT_TRUE(peer.uid_known);
  EXPECT_EQ(peer.uid, static_cast<std::int64_t>(::getuid()));
  EXPECT_TRUE(peer.pid_known);
  EXPECT_EQ(peer.pid, static_cast<std::int64_t>(::getpid()));
  ::close(accepted);
  ::close(client);
  ::close(server);
}

bool StopSignalsBlocked() {
  sigset_t mask{};
  pthread_sigmask(SIG_SETMASK, nullptr, &mask);
  return sigismember(&mask, SIGTERM) == 1 && sigismember(&mask, SIGINT) == 1;
}

TEST(BlockStopSignals, AThreadCreatedInItsScopeNeverTakesTheStopSignals) {
  ASSERT_FALSE(StopSignalsBlocked());
  bool blocked_in_thread = false;
  {
    const BlockStopSignals blocked;
    std::thread thread{[&] { blocked_in_thread = StopSignalsBlocked(); }};
    thread.join();
  }
  EXPECT_TRUE(blocked_in_thread);
  EXPECT_FALSE(StopSignalsBlocked());  // the creating thread gets its mask back
}

}  // namespace
