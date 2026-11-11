// route_listener: the newest valid RouteAnnouncement over real loopback UDP; wrong sizes and versions
// rejected and counted; Stop() ends the thread promptly.
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cstdio>
#include <cstring>
#include <string>
#include <thread>

#include "route_listener.h"

namespace dd = de4sdv::driving;
namespace da = de4sdv::driving::agent;

static int g_checks = 0, g_fail = 0;
#define CHECK(c)                                                       \
  do {                                                                 \
    ++g_checks;                                                        \
    if (!(c)) {                                                        \
      ++g_fail;                                                        \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c);        \
    }                                                                  \
  } while (0)

static void Send(int port, const void* data, std::size_t n) {
  const int fd = ::socket(AF_INET, SOCK_DGRAM, 0);
  sockaddr_in to{};
  to.sin_family = AF_INET;
  to.sin_port = htons(static_cast<std::uint16_t>(port));
  ::inet_pton(AF_INET, "127.0.0.1", &to.sin_addr);
  ::sendto(fd, data, n, 0, reinterpret_cast<const sockaddr*>(&to), sizeof(to));
  ::close(fd);
}

static da::RouteState WaitFor(const da::RouteListener& l, std::uint64_t received, std::uint64_t rejected) {
  for (int i = 0; i < 200; ++i) {
    const da::RouteState s = l.Newest();
    if (s.received >= received && s.rejected >= rejected) return s;
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  return l.Newest();
}

static dd::RouteAnnouncement Announcement(std::uint32_t corridor, double issue) {
  dd::RouteAnnouncement a{};
  a.version = dd::kInterfaceVersion;
  a.corridorPoints = corridor;
  a.issueTime = issue;
  std::snprintf(a.routeFile, sizeof(a.routeFile), "%s", "/opt/de4sdv-bench/route.json");
  std::memset(a.routeSha256, 'a', sizeof(a.routeSha256));  // 64 hex, no NUL
  return a;
}

int main() {
  static_assert(sizeof(dd::RouteAnnouncement) == 272, "ICD section 9: 272 bytes");
  da::RouteListener l;
  std::string error;
  CHECK(l.Start("127.0.0.1", 0, &error));
  CHECK(l.port() > 0);
  CHECK(!l.Newest().has_announcement);

  dd::RouteAnnouncement a = Announcement(282, 512.3);
  Send(l.port(), &a, sizeof(a));
  da::RouteState s = WaitFor(l, 1, 0);
  CHECK(s.has_announcement && s.received == 1);
  CHECK(s.newest.corridorPoints == 282);
  CHECK(s.newest.issueTime == 512.3);
  CHECK(std::string(s.newest.routeFile) == "/opt/de4sdv-bench/route.json");
  CHECK(std::memcmp(s.newest.routeSha256, std::string(64, 'a').data(), 64) == 0);
  CHECK(s.received_mono_ns > 0);

  // Wrong size and wrong version: rejected, the newest valid one stays.
  Send(l.port(), &a, sizeof(a) - 1);
  dd::RouteAnnouncement v1 = Announcement(5, 600.0);
  v1.version = 1;
  Send(l.port(), &v1, sizeof(v1));
  s = WaitFor(l, 1, 2);
  CHECK(s.rejected == 2);
  CHECK(s.newest.corridorPoints == 282 && s.newest.issueTime == 512.3);

  // An empty corridor is a valid announcement (route_empty fault): it replaces the newest.
  dd::RouteAnnouncement empty = Announcement(0, 513.0);
  Send(l.port(), &empty, sizeof(empty));
  s = WaitFor(l, 2, 2);
  CHECK(s.received == 2 && s.newest.corridorPoints == 0 && s.newest.issueTime == 513.0);

  // A second listener cannot bind the same port.
  da::RouteListener other;
  CHECK(!other.Start("127.0.0.1", l.port(), &error));

  const auto t0 = std::chrono::steady_clock::now();
  l.Stop();
  const double ms = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - t0).count();
  CHECK(ms < 250.0);
  l.Stop();  // idempotent
  std::printf("%d checks, %d failures (stop %.1f ms)\n", g_checks, g_fail, ms);
  return g_fail == 0 ? 0 : 1;
}
