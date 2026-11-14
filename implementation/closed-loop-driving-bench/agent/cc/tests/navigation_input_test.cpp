// navigation_input: the route channel and the rasters at the step's REF pose, against the real
// Town10HD_Opt map and route of the bench (exported from CARLA 0.9.16), over loopback UDP.
//   navigation_input_test <map.json> <route.json>
#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <memory>
#include <sstream>
#include <string>
#include <thread>
#include <vector>

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

// ---- The step's take of the nav prefetch (TakeNavPrefetch), with the real renderer, map and route.

struct Bench {
  std::string map_path, route_path, sha;
};

using Prefetch = da::NavPrefetch<da::NavPrefetchResult>;
constexpr std::int64_t kMs = 1'000'000;
static const double kOrigin[3] = {0.0, 0.0, 0.0};

// The route's first waypoint (map frame) as a UE vehicle pose, REF at the vehicle origin; and a pose
// 600 m from the route. Their rasters differ (asserted below).
static da::Pose RouteStartPose() {
  const double wx = -64.82615661621094, wy = -24.50389862060547, wyaw = -0.0027785214782865796;
  return da::Pose{wx, -wy, 0.0, 0.0, 0.0, -wyaw * 180.0 / M_PI};
}
static da::Pose FarPose() {
  const double wx = -64.82615661621094, wy = -24.50389862060547;
  return da::Pose{wx + 600.0, -wy, 0.0, 0.0, 0.0, 0.0};
}

static bool Same(const std::vector<float>& a, const std::vector<float>& b) {
  return a.size() == b.size() && std::memcmp(a.data(), b.data(), a.size() * sizeof(float)) == 0;
}

// Until the listener holds the announcement issued at `issue`.
static bool WaitNewest(const da::NavigationInput& nav, double issue) {
  for (int i = 0; i < 400; ++i) {
    const da::RouteState rs = nav.NewestRoute();
    if (rs.has_announcement && rs.newest.issueTime == issue) return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  return false;
}

// Until the prefetch thread has finished `n` renders.
static bool WaitRendered(const Prefetch& p, std::uint64_t n) {
  for (int i = 0; i < 2000; ++i) {
    if (p.Stats().rendered >= n) return true;
    std::this_thread::sleep_for(std::chrono::milliseconds(5));
  }
  return false;
}

// The agent's prefetch, rendering with RenderNavPrefetch as drivingAgent starts it. With `gate`, each
// render first waits until *gate is true: a render still in flight at the take.
static std::unique_ptr<Prefetch> StartPrefetch(da::NavigationInput* nav, std::atomic<bool>* gate = nullptr) {
  auto p = std::make_unique<Prefetch>();
  p->Start([nav, gate](std::uint64_t frame, const da::Pose& pose, std::int64_t, da::NavPrefetchResult* r) {
    while (gate != nullptr && !gate->load()) std::this_thread::sleep_for(std::chrono::milliseconds(1));
    da::RenderNavPrefetch(nav, kOrigin, frame, pose, r);
  });
  p->Arm(true);
  return p;
}

static std::string Outcome(const da::NavPrefetchTake& t) { return da::NavPrefetchOutcomeName(t.outcome); }

// A use hands the checkpoint THIS frame's prefetched rasters, in the caller's buffers: never the
// chain's (map_context(), route_mask(), here a render at another pose), nor an earlier use's.
static void TestTakeUseHandsOverThisFramesRasters(const Bench& b) {
  da::NavigationInput nav;
  std::string error;
  CHECK(nav.Start(b.map_path, "127.0.0.1", 0, &error));
  Send(nav.listener_port(), Announcement(b.route_path, b.sha, 282, 600.0));
  CHECK(WaitNewest(nav, 600.0));
  const da::Pose start = RouteStartPose(), far = FarPose();
  // The references: either pose's rasters, drawn here (a render at the same pose and route is
  // byte-identical, tested above).
  std::vector<float> start_map, start_route, far_map, far_route;
  da::NavigationInput::Step s;
  CHECK(nav.RenderInto(start, kOrigin, &s, &start_map, &start_route, &error));
  CHECK(nav.RenderInto(far, kOrigin, &s, &far_map, &far_route, &error));
  CHECK(!Same(start_map, far_map));       // the two poses' map contexts differ
  CHECK(!Same(start_route, far_route));   // and their route masks (the corridor shows at the start only)
  auto prefetch = StartPrefetch(&nav);
  std::vector<float> hit_map, hit_route;  // the agent's nav_hit_map and nav_hit_route
  // Frame 10 prefetched at the start; the chain's last render is the far one.
  CHECK(prefetch->Submit(10, start, 0));
  CHECK(WaitRendered(*prefetch, 1));
  CHECK(nav.Render(far, kOrigin, &s, &error));
  da::NavPrefetchTake t = da::TakeNavPrefetch(prefetch.get(), nav, 10, start, 200 * kMs, &hit_map, &hit_route);
  CHECK(Outcome(t) == "hit");
  CHECK(t.map_context == &hit_map && t.route_mask == &hit_route);   // the caller keeps them until its next use
  CHECK(t.map_context != nullptr && Same(*t.map_context, start_map));
  CHECK(t.route_mask != nullptr && Same(*t.route_mask, start_route));
  CHECK(t.map_context != nullptr && !Same(*t.map_context, nav.map_context()));
  CHECK(t.route_mask != nullptr && !Same(*t.route_mask, nav.route_mask()));
  // Frame 11 prefetched far away, the chain at the start: this use hands frame 11's rasters, not 10's.
  CHECK(prefetch->Submit(11, far, 0));
  CHECK(WaitRendered(*prefetch, 2));
  CHECK(nav.Render(start, kOrigin, &s, &error));
  t = da::TakeNavPrefetch(prefetch.get(), nav, 11, far, 200 * kMs, &hit_map, &hit_route);
  CHECK(Outcome(t) == "hit");
  CHECK(t.map_context != nullptr && Same(*t.map_context, far_map));
  CHECK(t.route_mask != nullptr && Same(*t.route_mask, far_route));
  CHECK(t.map_context != nullptr && !Same(*t.map_context, nav.map_context()));
  CHECK(t.route_mask != nullptr && !Same(*t.route_mask, nav.route_mask()));
  prefetch->Stop();
  nav.Stop();
}

// Each outcome of the take, with C2's exact strings. Only "hit" hands rasters over; after any other
// the step renders on the chain.
static void TestTakeOutcomes(const Bench& b) {
  da::NavigationInput nav;
  std::string error;
  CHECK(nav.Start(b.map_path, "127.0.0.1", 0, &error));
  Send(nav.listener_port(), Announcement(b.route_path, b.sha, 282, 610.0));
  CHECK(WaitNewest(nav, 610.0));
  const da::Pose start = RouteStartPose();
  std::vector<float> hit_map, hit_route;
  const auto none = [](const da::NavPrefetchTake& t) { return t.map_context == nullptr && t.route_mask == nullptr; };
  {
    auto prefetch = StartPrefetch(&nav);
    const auto take = [&](std::uint64_t frame, const da::Pose& pose) {
      return da::TakeNavPrefetch(prefetch.get(), nav, frame, pose, 200 * kMs, &hit_map, &hit_route);
    };
    // Not submitted: frame 1 was never requested.
    da::NavPrefetchTake t = take(1, start);
    CHECK(Outcome(t) == "not_submitted" && none(t));
    // Hit and use: the same frame, pose and route.
    CHECK(prefetch->Submit(2, start, 0));
    CHECK(WaitRendered(*prefetch, 1));
    t = take(2, start);
    CHECK(Outcome(t) == "hit" && !none(t));
    // Pose changed: the step's yaw differs from the drawn one by 1e-6 degree.
    CHECK(prefetch->Submit(3, start, 0));
    CHECK(WaitRendered(*prefetch, 2));
    da::Pose turned = start;
    turned.yaw += 1e-6;
    t = take(3, turned);
    CHECK(Outcome(t) == "pose_changed" && none(t));
    // Route changed: a withdrawal announced after the render.
    CHECK(prefetch->Submit(4, start, 0));
    CHECK(WaitRendered(*prefetch, 3));
    Send(nav.listener_port(), Announcement(b.route_path, b.sha, 0, 611.0));
    CHECK(WaitNewest(nav, 611.0));
    t = take(4, start);
    CHECK(Outcome(t) == "route_changed" && none(t));
    prefetch->Stop();
  }
  {  // Timed out: the frame's render still runs when the wait ends.
    std::atomic<bool> gate{false};
    auto prefetch = StartPrefetch(&nav, &gate);
    CHECK(prefetch->Submit(5, start, 0));
    std::this_thread::sleep_for(std::chrono::milliseconds(20));   // 5 in flight, held at the gate
    const da::NavPrefetchTake t = da::TakeNavPrefetch(prefetch.get(), nav, 5, start, 5 * kMs, &hit_map, &hit_route);
    CHECK(Outcome(t) == "timed_out" && none(t));
    CHECK(t.take_ms >= 4.0);   // it waited about the 5 ms bound
    gate = true;
    prefetch->Stop();
  }
  {  // Render failed. No input is known that makes the real renderer fail; this render function
     // stands in for one that did, as RenderNavPrefetch leaves its result.
    Prefetch prefetch;
    prefetch.Start([](std::uint64_t, const da::Pose& pose, std::int64_t, da::NavPrefetchResult* r) {
      r->pose = pose;
      r->ok = false;
      r->error = "stand-in render failure";
    });
    prefetch.Arm(true);
    CHECK(prefetch.Submit(6, start, 0));
    CHECK(WaitRendered(prefetch, 1));
    const da::NavPrefetchTake t = da::TakeNavPrefetch(&prefetch, nav, 6, start, 200 * kMs, &hit_map, &hit_route);
    CHECK(Outcome(t) == "render_failed" && none(t));
    prefetch.Stop();
  }
  nav.Stop();
}

// The route events the take returns for the step to log, in order: the changes of renders no step
// used first (a result the take passed over, the late render of a timed-out take), then this frame's
// own change when the step does not use it. A used render's change is the step's own
// (Step::route_event), which the step logs once with its frame: the take does not return it too.
static void TestTakeRouteEvents(const Bench& b) {
  da::NavigationInput nav;   // no route loaded yet: the first render after the announcement loads it
  std::string error;
  CHECK(nav.Start(b.map_path, "127.0.0.1", 0, &error));
  const da::Pose start = RouteStartPose(), far = FarPose();
  std::vector<float> hit_map, hit_route;
  const auto starts = [](const std::string& s, const std::string& prefix) { return s.rfind(prefix, 0) == 0; };
  auto prefetch = StartPrefetch(&nav);
  Send(nav.listener_port(), Announcement(b.route_path, b.sha, 282, 620.0));
  CHECK(WaitNewest(nav, 620.0));
  CHECK(prefetch->Submit(20, start, 0));   // frame 20's render loads the route; no take of frame 20 follows
  CHECK(WaitRendered(*prefetch, 1));
  Send(nav.listener_port(), Announcement(b.route_path, b.sha, 0, 621.0));
  CHECK(WaitNewest(nav, 621.0));
  CHECK(prefetch->Submit(21, start, 0));   // frame 21's render withdraws it
  CHECK(WaitRendered(*prefetch, 2));
  // Frame 21 taken at another pose, so not used: frame 20's change (carried) first, then frame 21's own.
  da::NavPrefetchTake t = da::TakeNavPrefetch(prefetch.get(), nav, 21, far, 200 * kMs, &hit_map, &hit_route);
  CHECK(Outcome(t) == "pose_changed");
  CHECK(t.route_events.size() == 2);
  CHECK(t.route_events.size() > 0 && starts(t.route_events[0], "{\"frame\":20,\"event\":{\"route\":\"loaded\""));
  CHECK(t.route_events.size() > 1 && starts(t.route_events[1], "{\"frame\":21,\"event\":{\"route\":\"withdrawn\""));
  // The route again: frame 22's render loads it and the step uses that render.
  Send(nav.listener_port(), Announcement(b.route_path, b.sha, 282, 622.0));
  CHECK(WaitNewest(nav, 622.0));
  CHECK(prefetch->Submit(22, start, 0));
  CHECK(WaitRendered(*prefetch, 3));
  t = da::TakeNavPrefetch(prefetch.get(), nav, 22, start, 200 * kMs, &hit_map, &hit_route);
  CHECK(Outcome(t) == "hit");
  CHECK(t.route_events.empty());
  CHECK(starts(t.step.route_event, "{\"route\":\"loaded\""));
  prefetch->Stop();
  {  // A render the step timed out on: its change reaches the next take, here a use.
    std::atomic<bool> gate{false};
    auto gated = StartPrefetch(&nav, &gate);
    std::string bad = b.sha;
    bad[0] = bad[0] == 'a' ? 'b' : 'a';
    Send(nav.listener_port(), Announcement(b.route_path, bad, 282, 623.0));
    CHECK(WaitNewest(nav, 623.0));
    CHECK(gated->Submit(23, start, 0));
    std::this_thread::sleep_for(std::chrono::milliseconds(20));   // 23 in flight, held at the gate
    t = da::TakeNavPrefetch(gated.get(), nav, 23, start, 1 * kMs, &hit_map, &hit_route);
    CHECK(Outcome(t) == "timed_out" && t.route_events.empty());
    gate = true;
    CHECK(WaitRendered(*gated, 1));   // frame 23's render refuses the SHA-256
    CHECK(gated->Submit(24, start, 0));
    CHECK(WaitRendered(*gated, 2));
    t = da::TakeNavPrefetch(gated.get(), nav, 24, start, 200 * kMs, &hit_map, &hit_route);
    CHECK(Outcome(t) == "hit");
    CHECK(t.route_events.size() == 1);
    CHECK(t.route_events.size() > 0 && starts(t.route_events[0], "{\"frame\":23,\"event\":{\"route\":\"sha256_mismatch\""));
    CHECK(t.step.route_event.empty());
    gated->Stop();
  }
  nav.Stop();
}

// On a use, the step's route observation is the announcement read at the take, as a render there
// reads it, not the one the prefetch thread read when it drew: here the same route re-announced
// with another corridor count and issue time after the render.
static void TestTakeObservesTheAnnouncementAtTheTake(const Bench& b) {
  da::NavigationInput nav;
  std::string error;
  CHECK(nav.Start(b.map_path, "127.0.0.1", 0, &error));
  const da::Pose start = RouteStartPose();
  std::vector<float> hit_map, hit_route;
  auto prefetch = StartPrefetch(&nav);
  Send(nav.listener_port(), Announcement(b.route_path, b.sha, 282, 630.0));
  CHECK(WaitNewest(nav, 630.0));
  CHECK(prefetch->Submit(30, start, 0));
  CHECK(WaitRendered(*prefetch, 1));
  {  // what that render read: the announcement of 630.0 with 282 corridor points
    std::vector<float> m, r;
    da::NavigationInput::Step s;
    CHECK(nav.RenderInto(start, kOrigin, &s, &m, &r, &error));
    CHECK(s.route.issue_time == 630.0 && s.route.corridor_points == 282);
  }
  Send(nav.listener_port(), Announcement(b.route_path, b.sha, 281, 630.5));   // same file and SHA-256
  CHECK(WaitNewest(nav, 630.5));
  const da::NavPrefetchTake t =
      da::TakeNavPrefetch(prefetch.get(), nav, 30, start, 200 * kMs, &hit_map, &hit_route);
  CHECK(Outcome(t) == "hit");   // the same route identity: used
  CHECK(t.step.route.has_announcement);
  CHECK(t.step.route.issue_time == 630.5);
  CHECK(t.step.route.corridor_points == 281);
  CHECK(t.step.route.raster_corridor_cells > 100);   // the raster's own count stays the render's
  prefetch->Stop();
  nav.Stop();
}

// The agent's timing: the request from the snapshot's thread, the take on the step's while the render
// is usually still in flight. Every use holds its own frame's rasters; consecutive frames alternate
// between the two poses. Under ThreadSanitizer this covers the result's way from the prefetch thread
// to the step through the take, and the free of the previous use's rasters there.
static void TestTakeWhileThePrefetchThreadRenders(const Bench& b) {
  da::NavigationInput nav;
  std::string error;
  CHECK(nav.Start(b.map_path, "127.0.0.1", 0, &error));
  Send(nav.listener_port(), Announcement(b.route_path, b.sha, 282, 640.0));
  CHECK(WaitNewest(nav, 640.0));
  const da::Pose poses[2] = {RouteStartPose(), FarPose()};
  std::vector<float> ref_map[2], ref_route[2];
  for (int i = 0; i < 2; ++i) {
    da::NavigationInput::Step s;
    CHECK(nav.RenderInto(poses[i], kOrigin, &s, &ref_map[i], &ref_route[i], &error));
  }
  auto prefetch = StartPrefetch(&nav);
  constexpr std::uint64_t kFrames = 20;
  std::atomic<std::uint64_t> submitted{0}, taken{0};
  std::thread snapshots([&] {   // one request at a time: frame f once the step has taken f - 1
    for (std::uint64_t f = 1; f <= kFrames; ++f) {
      while (taken.load() < f - 1) std::this_thread::sleep_for(std::chrono::microseconds(100));
      prefetch->Submit(f, poses[f % 2], 0);
      submitted = f;
    }
  });
  std::vector<float> hit_map, hit_route;
  int used = 0, wrong = 0, waited = 0;
  for (std::uint64_t f = 1; f <= kFrames; ++f) {
    while (submitted.load() < f) std::this_thread::sleep_for(std::chrono::microseconds(100));
    const da::NavPrefetchTake t =
        da::TakeNavPrefetch(prefetch.get(), nav, f, poses[f % 2], 2000 * kMs, &hit_map, &hit_route);
    if (t.take_ms > 1.0) ++waited;
    if (t.map_context != nullptr && t.route_mask != nullptr) {
      ++used;
      if (!Same(*t.map_context, ref_map[f % 2]) || !Same(*t.route_mask, ref_route[f % 2])) ++wrong;
    }
    taken = f;
  }
  snapshots.join();
  std::printf("take while rendering: %d of %d takes used, %d waited more than 1 ms\n", used,
              static_cast<int>(kFrames), waited);
  CHECK(used == static_cast<int>(kFrames));
  CHECK(wrong == 0);
  prefetch->Stop();
  nav.Stop();
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
  // The route identity (nav prefetch, DESIGN.md): what the raster was drawn with, comparable with the
  // listener's newest announcement at the step's take.
  CHECK(st.route_identity == "none");
  CHECK(st.route_identity == da::NavigationInput::RouteIdentity(nav.NewestRoute()));
  {  // The take's observation equals the render's (nav prefetch): nothing announced yet.
    da::RouteObservation obs;
    obs.has_announcement = true;
    obs.corridor_points = 7;
    obs.issue_time = 1.0;
    da::NavigationInput::ObserveAnnouncement(nav.NewestRoute(), &obs);
    CHECK(obs.has_announcement == st.route.has_announcement && obs.corridor_points == st.route.corridor_points &&
          obs.issue_time == st.route.issue_time);
  }
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
  const std::string loaded_identity = st.route_identity;
  CHECK(loaded_identity == da::NavigationInput::RouteIdentity(nav.NewestRoute()));
  CHECK(loaded_identity.find(route_path) != std::string::npos && loaded_identity.find(sha) != std::string::npos);
  {  // Same pose, same route: byte-identical rasters and step fields (what makes a prefetch exact).
    const std::vector<float> map1 = nav.map_context(), route1 = nav.route_mask();
    da::NavigationInput::Step again;
    CHECK(nav.Render(start, o0, &again, &error));
    CHECK(map1.size() == nav.map_context().size() &&
          std::memcmp(map1.data(), nav.map_context().data(), map1.size() * sizeof(float)) == 0);
    CHECK(route1.size() == nav.route_mask().size() &&
          std::memcmp(route1.data(), nav.route_mask().data(), route1.size() * sizeof(float)) == 0);
    CHECK(again.route.raster_corridor_cells == st.route.raster_corridor_cells);
    CHECK(again.destination_cells == st.destination_cells && again.waypoints_in_window == st.waypoints_in_window &&
          again.waypoints_on_corridor == st.waypoints_on_corridor);
    CHECK(again.pose.x == st.pose.x && again.pose.y == st.pose.y && again.pose.yaw == st.pose.yaw);
    CHECK(again.route_identity == loaded_identity && again.route_event.empty());
    // RenderInto: the same rasters in the caller's buffers, the members untouched.
    std::vector<float> map2, route2;
    da::NavigationInput::Step into;
    const std::vector<float> members_before = nav.map_context();
    CHECK(nav.RenderInto(start, o0, &into, &map2, &route2, &error));
    CHECK(map2.size() == map1.size() && std::memcmp(map2.data(), map1.data(), map1.size() * sizeof(float)) == 0);
    CHECK(route2.size() == route1.size() && std::memcmp(route2.data(), route1.data(), route1.size() * sizeof(float)) == 0);
    CHECK(into.route_identity == loaded_identity && into.route.raster_corridor_cells == st.route.raster_corridor_cells);
    da::NavigationInput::Step far_into;
    const da::Pose far_pose{wx + 600.0, -wy, 0.0, 0.0, 0.0, 0.0};
    CHECK(nav.RenderInto(far_pose, o0, &far_into, &map2, &route2, &error));
    CHECK(std::memcmp(members_before.data(), nav.map_context().data(), members_before.size() * sizeof(float)) == 0);
    // One render at a time: RenderInto on another thread while Render runs here (the agent's prefetch
    // thread and a fallback render on the chain). The ThreadSanitizer build reports a missing lock.
    std::thread other([&nav, &start, &o0] {
      for (int i = 0; i < 4; ++i) {
        std::vector<float> m, r;
        da::NavigationInput::Step s;
        std::string e;
        nav.RenderInto(start, o0, &s, &m, &r, &e);
      }
    });
    for (int i = 0; i < 4; ++i) {
      da::NavigationInput::Step s;
      CHECK(nav.Render(far_pose, o0, &s, &error));
    }
    other.join();
  }
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
  CHECK(st.route_identity == loaded_identity);   // a re-announcement (new issue time only) keeps the identity
  {  // ... and the take reads the new issue time as the render did
    da::RouteObservation obs;
    da::NavigationInput::ObserveAnnouncement(nav.NewestRoute(), &obs);
    CHECK(obs.has_announcement && obs.corridor_points == 282 && obs.issue_time == 500.5);
    CHECK(obs.has_announcement == st.route.has_announcement && obs.corridor_points == st.route.corridor_points &&
          obs.issue_time == st.route.issue_time);
  }
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
  CHECK(st.route_identity != loaded_identity);
  CHECK(st.route_identity == da::NavigationInput::RouteIdentity(nav.NewestRoute()));
  CHECK(!st.route_in_raster);
  CHECK(st.route.raster_corridor_cells == 0);

  // The right one again, then a withdrawal (corridorPoints 0).
  Send(nav.listener_port(), Announcement(route_path, sha, 282, 501.5));
  st = RenderAfter(nav, start, o0, 501.5);
  CHECK(st.route_in_raster && st.route.raster_corridor_cells > 100);
  Send(nav.listener_port(), Announcement(route_path, sha, 0, 502.0));
  st = RenderAfter(nav, start, o0, 502.0);
  CHECK(st.route_event.find("withdrawn") != std::string::npos);
  CHECK(st.route_identity != loaded_identity);
  CHECK(st.waypoints_in_window == 0 && st.route_sha256.empty());
  CHECK(st.route.corridor_points == 0);
  CHECK(st.route.raster_corridor_cells == 0);

  // A missing file: load_failed.
  Send(nav.listener_port(), Announcement("/nonexistent/route.json", sha, 282, 502.5));
  st = RenderAfter(nav, start, o0, 502.5);
  CHECK(st.route_event.find("load_failed") != std::string::npos);
  CHECK(st.route_identity != loaded_identity && st.route_identity.find("/nonexistent/route.json") != std::string::npos);
  CHECK(st.route.raster_corridor_cells == 0);

  nav.Stop();
  // The step's take of the nav prefetch, each test with a navigation input of its own.
  const Bench bench{map_path, route_path, sha};
  TestTakeUseHandsOverThisFramesRasters(bench);
  TestTakeOutcomes(bench);
  TestTakeRouteEvents(bench);
  TestTakeObservesTheAnnouncementAtTheTake(bench);
  TestTakeWhileThePrefetchThreadRenders(bench);
  std::printf("%d checks, %d failures\n", g_checks, g_fail);
  return g_fail == 0 ? 0 : 1;
}
