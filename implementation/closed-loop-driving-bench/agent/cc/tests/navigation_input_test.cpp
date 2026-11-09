// navigation_input: the route channel and the rasters at the step's REF pose, against the real
// Town10HD_Opt map and route of the bench (exported from CARLA 0.9.16), over loopback UDP.
//   navigation_input_test <map.json> <route.json>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <sstream>
#include <string>
#include <thread>

#include "navigation_input.h"

namespace dd = de4sdv::driving;
namespace da = de4sdv::driving::agent;

static int g_checks = 0, g_fail = 0;
#define CHECK(c)                                                    \
  do {                                                              \
    ++g_checks;                                                     \
    if (!(c)) {                                                     \
      ++g_fail;                                                     \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #c);     \
    }                                                               \
  } while (0)
#define CHECK_NEAR(a, b, tol) CHECK(std::fabs((a) - (b)) <= (tol))

static void Send(int port, const dd::RouteAnnouncement& a) {
  const int fd = ::socket(AF_INET, SOCK_DGRAM, 0);
  sockaddr_in to{};
  to.sin_family = AF_INET;
  to.sin_port = htons(static_cast<std::uint16_t>(port));
  ::inet_pton(AF_INET, "127.0.0.1", &to.sin_addr);
  ::sendto(fd, &a, sizeof(a), 0, reinterpret_cast<const sockaddr*>(&to), sizeof(to));
  ::close(fd);
}

static dd::RouteAnnouncement Announcement(const std::string& file, const std::string& sha, std::uint32_t points,
                                          double issue) {
  dd::RouteAnnouncement a{};
  a.version = dd::kInterfaceVersion;
  a.corridorPoints = points;
  a.issueTime = issue;
  std::snprintf(a.routeFile, sizeof(a.routeFile), "%s", file.c_str());
  std::memcpy(a.routeSha256, sha.data(), 64);
  return a;
}

// Renders until the listener has taken the newest datagram (its issue time shows in the step).
static da::NavigationInput::Step RenderAfter(da::NavigationInput& nav, const da::Pose& pose, const double o[3],
                                             double issue) {
  da::NavigationInput::Step st;
  std::string error;
  for (int i = 0; i < 200; ++i) {
    if (!nav.Render(pose, o, &st, &error)) std::printf("render error: %s\n", error.c_str());
    if (st.route.has_announcement && st.route.issue_time == issue) return st;
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  return st;
}

int main(int argc, char** argv) {
  if (argc != 3) {
    std::printf("usage: %s <map.json> <route.json>\n", argv[0]);
    return 2;
  }
  const std::string map_path = argv[1], route_path = argv[2];
  // sha256 of the route file, as the route provider announces it
  std::string sha;
  {
    const std::string cmd = "sha256sum '" + route_path + "'";
    FILE* p = ::popen(cmd.c_str(), "r");
    char buf[128] = {};
    if (p != nullptr && std::fgets(buf, sizeof(buf), p) != nullptr) sha.assign(buf, 64);
    if (p != nullptr) ::pclose(p);
  }
  CHECK(sha.size() == 64);

  // REF pose math: vehicle at (10, 20, 0.5) UE heading yaw 90 (world +y); REF 1.4 m behind, 0.3 m down.
  {
    da::Pose p{10.0, 20.0, 0.5, 0.0, 0.0, 90.0};
    const double o[3] = {-1.4, 0.0, -0.3};
    const da::MapPose m = da::RefPoseInMap(p, o);
    CHECK_NEAR(m.x, 10.0, 1e-9);
    CHECK_NEAR(m.y, -(20.0 - 1.4), 1e-9);  // y_map = -y_carla
    CHECK_NEAR(m.yaw, -M_PI / 2.0, 1e-12);  // yaw_map = -yaw_carla
  }

  da::NavigationInput nav;
  std::string error;
  CHECK(nav.Start(map_path, "127.0.0.1", 0, &error));
  if (!error.empty()) std::printf("start: %s\n", error.c_str());
  CHECK(nav.map_version() == "Town10HD_Opt");

  // The route's first waypoint (map frame) as a UE vehicle pose, REF at the vehicle origin.
  const double wx = -64.82615661621094, wy = -24.50389862060547, wyaw = -0.0027785214782865796;
  const da::Pose start{wx, -wy, 0.0, 0.0, 0.0, -wyaw * 180.0 / M_PI};
  const double o0[3] = {0.0, 0.0, 0.0};

  da::NavigationInput::Step st;
  CHECK(nav.Render(start, o0, &st, &error));
  CHECK(!st.route.has_announcement);
  CHECK(st.route.raster_corridor_cells == 0);
  CHECK(nav.map_context().size() == 14u * 450u * 300u);
  CHECK(nav.route_mask().size() == 2u * 450u * 300u);
  std::size_t map_nonzero = 0;
  for (float v : nav.map_context()) map_nonzero += v != 0.0f ? 1u : 0u;
  CHECK(map_nonzero > 1000);  // lanes and road around the start
  std::printf("map context non-zero cells at the route start: %zu, render %.2f ms\n", map_nonzero, st.render_ms);

  // The correct announcement: route loaded, corridor in the raster at the route start.
  Send(nav.listener_port(), Announcement(route_path, sha, 282, 500.0));
  st = RenderAfter(nav, start, o0, 500.0);
  CHECK(st.route.corridor_points == 282);
  CHECK(st.route_in_raster);
  CHECK(st.route_event.find("\"route\":\"loaded\"") != std::string::npos);
  CHECK(st.route_event.find("\"effectiveRouteValid\":true") != std::string::npos);
  CHECK(st.route.raster_corridor_cells > 100);
  std::printf("corridor cells at the route start: %u; event %s\n", st.route.raster_corridor_cells, st.route_event.c_str());
  CHECK(st.route_sha256 == sha);
  CHECK(st.waypoints_in_window > 10);
  CHECK(st.waypoints_on_corridor == st.waypoints_in_window);
  std::printf("coverage at the route start: %u of %u waypoints in the window on the corridor\n",
              st.waypoints_on_corridor, st.waypoints_in_window);
  {  // 30 m before the destination (map frame), heading towards it: the destination marker shows
    const double dx = 106.02881622314453, dy = -67.41998291015625;
    const da::Pose near_end{dx - 30.0, -dy, 0.0, 0.0, 0.0, 0.0};
    da::NavigationInput::Step e;
    CHECK(nav.Render(near_end, o0, &e, &error));
    std::printf("near the destination: destination cells %u, corridor cells %u, coverage %u/%u\n", e.destination_cells,
                e.route.raster_corridor_cells, e.waypoints_on_corridor, e.waypoints_in_window);
    CHECK(e.destination_cells > 0);
    CHECK(e.waypoints_on_corridor == e.waypoints_in_window);
  }
  for (std::size_t i = 0; i < nav.route_mask().size(); ++i) {
    const float v = nav.route_mask()[i];
    if (v != 0.0f && v != 1.0f) {
      CHECK(false && "route mask is not 0/1");
      break;
    }
  }

  // The same announcement again: nothing reloads.
  Send(nav.listener_port(), Announcement(route_path, sha, 282, 500.5));
  st = RenderAfter(nav, start, o0, 500.5);
  CHECK(st.route_event.empty());
  CHECK(st.route.raster_corridor_cells > 100);

  // Far from the route (600 m away): the map raster may hold other roads, the corridor none.
  const da::Pose far{wx + 600.0, -wy, 0.0, 0.0, 0.0, 0.0};
  CHECK(nav.Render(far, o0, &st, &error));
  CHECK(st.route.raster_corridor_cells == 0);

  // A wrong SHA-256: refused, no corridor.
  std::string bad = sha;
  bad[0] = bad[0] == 'a' ? 'b' : 'a';
  Send(nav.listener_port(), Announcement(route_path, bad, 282, 501.0));
  st = RenderAfter(nav, start, o0, 501.0);
  CHECK(st.route_event.find("sha256_mismatch") != std::string::npos);
  CHECK(!st.route_in_raster);
  CHECK(st.route.raster_corridor_cells == 0);

  // The right one again, then a withdrawal (corridorPoints 0).
  Send(nav.listener_port(), Announcement(route_path, sha, 282, 501.5));
  st = RenderAfter(nav, start, o0, 501.5);
  CHECK(st.route_in_raster && st.route.raster_corridor_cells > 100);
  Send(nav.listener_port(), Announcement(route_path, sha, 0, 502.0));
  st = RenderAfter(nav, start, o0, 502.0);
  CHECK(st.route_event.find("withdrawn") != std::string::npos);
  CHECK(st.waypoints_in_window == 0 && st.route_sha256.empty());
  CHECK(st.route.corridor_points == 0);
  CHECK(st.route.raster_corridor_cells == 0);

  // A missing file: load_failed.
  Send(nav.listener_port(), Announcement("/nonexistent/route.json", sha, 282, 502.5));
  st = RenderAfter(nav, start, o0, 502.5);
  CHECK(st.route_event.find("load_failed") != std::string::npos);
  CHECK(st.route.raster_corridor_cells == 0);

  nav.Stop();
  std::printf("%d checks, %d failures\n", g_checks, g_fail);
  return g_fail == 0 ? 0 : 1;
}
