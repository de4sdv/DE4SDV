// Tests of nav_prefetch.h with a fake renderer: plain g++, no framework (tests/run_tests.sh).
#include <atomic>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <string>
#include <thread>
#include <vector>

#include "nav_prefetch.h"

using de4sdv::driving::agent::NavPrefetch;
using de4sdv::driving::agent::Pose;
using de4sdv::driving::agent::TakeOutcome;
using de4sdv::driving::agent::DecideUse;
using de4sdv::driving::agent::UseDecision;

namespace {

int g_checks = 0;
int g_failures = 0;

void Check(bool ok, const char* what, const char* file, int line) {
  ++g_checks;
  if (!ok) {
    ++g_failures;
    std::printf("FAIL %s:%d: %s\n", file, line, what);
  }
}
#define CHECK(condition) Check((condition), #condition, __FILE__, __LINE__)

struct R {
  std::uint64_t frame = 0;
  double value = 0.0;           // what the fake renderer drew: a function of the pose and the frame
  std::int64_t arrival = 0;
  std::string route_event;
};

double Drawn(std::uint64_t frame, const Pose& p) { return p.x * 1000.0 + p.yaw + static_cast<double>(frame); }

Pose PoseOf(std::uint64_t frame) {
  Pose p;
  p.x = 3.0 + static_cast<double>(frame);
  p.yaw = 0.25 * static_cast<double>(frame);
  return p;
}

NavPrefetch<R>::RenderFn Fake(int sleep_ms = 0, std::vector<std::uint64_t> event_frames = {}) {
  return [sleep_ms, event_frames](std::uint64_t frame, const Pose& pose, std::int64_t arrival, R* out) {
    if (sleep_ms > 0) std::this_thread::sleep_for(std::chrono::milliseconds(sleep_ms));
    out->frame = frame;
    out->value = Drawn(frame, pose);
    out->arrival = arrival;
    for (auto f : event_frames) {
      if (f == frame) out->route_event = "{\"frame\":" + std::to_string(frame) + "}";
    }
  };
}

constexpr std::int64_t kMs = 1'000'000;

void TestUnarmedRefusesAndTakeFallsBack() {
  NavPrefetch<R> p;
  p.Start(Fake());
  CHECK(!p.Submit(1, PoseOf(1), 10));            // not armed
  R r;
  std::vector<std::string> carried;
  CHECK(p.Take(1, 50 * kMs, &r, &carried) == TakeOutcome::kNotSubmitted);
  CHECK(p.Stats().refusedUnarmed == 1);
  CHECK(p.Stats().notSubmitted == 1);
}

void TestHitIsWhatTheRendererDrewForThatPose() {
  NavPrefetch<R> p;
  p.Start(Fake());
  p.Arm(true);
  CHECK(p.Submit(5, PoseOf(5), 1234));
  R r;
  std::vector<std::string> carried;
  CHECK(p.Take(5, 200 * kMs, &r, &carried) == TakeOutcome::kHit);
  CHECK(r.frame == 5);
  CHECK(r.value == Drawn(5, PoseOf(5)));
  CHECK(r.arrival == 1234);
  CHECK(carried.empty());
  // Taken once: a second take of the same frame has nothing left.
  CHECK(p.Take(5, 10 * kMs, &r, &carried) == TakeOutcome::kNotSubmitted);
}

void TestTakeWaitsForAnInFlightRender() {
  NavPrefetch<R> p;
  p.Start(Fake(30));
  p.Arm(true);
  CHECK(p.Submit(7, PoseOf(7), 0));
  std::this_thread::sleep_for(std::chrono::milliseconds(10));   // 7 in flight, no longer queued
  R r;
  std::vector<std::string> carried;
  double waited = 0.0;
  CHECK(p.Take(7, 500 * kMs, &r, &carried, &waited) == TakeOutcome::kHit);
  CHECK(r.value == Drawn(7, PoseOf(7)));
  CHECK(waited >= 10.0);                         // it waited for the render
  CHECK(waited < 400.0);                         // and not for the whole bound
}

void TestTimeoutAndTheLateResultIsDiscardedWithItsEvent() {
  NavPrefetch<R> p;
  p.Start(Fake(80, {3}));
  p.Arm(true);
  CHECK(p.Submit(3, PoseOf(3), 0));
  R r;
  std::vector<std::string> carried;
  CHECK(p.Take(3, 5 * kMs, &r, &carried) == TakeOutcome::kTimedOut);
  CHECK(p.Stats().timedOut == 1);
  std::this_thread::sleep_for(std::chrono::milliseconds(150));   // frame 3's render finishes after its take
  CHECK(p.Submit(4, PoseOf(4), 0));
  CHECK(p.Take(4, 500 * kMs, &r, &carried) == TakeOutcome::kHit);
  CHECK(r.frame == 4);
  // Frame 3 was never planned from its prefetch, but the route change its render raised is kept.
  CHECK(carried.size() == 1 && carried[0] == "{\"frame\":3}");
}

void TestOlderResultsAreDiscardedAndTheirEventsCarriedOldestFirst() {
  NavPrefetch<R> p;
  p.Start(Fake(0, {1, 3}));
  p.Arm(true);
  for (std::uint64_t f = 1; f <= 3; ++f) CHECK(p.Submit(f, PoseOf(f), 0));
  std::this_thread::sleep_for(std::chrono::milliseconds(50));
  R r;
  std::vector<std::string> carried;
  CHECK(p.Take(3, 200 * kMs, &r, &carried) == TakeOutcome::kHit);
  CHECK(r.route_event == "{\"frame\":3}");       // the taken frame's own event stays with it
  CHECK(carried.size() == 1 && carried[0] == "{\"frame\":1}");
  CHECK(p.Stats().discarded == 2);               // frames 1 and 2
}

void TestFullQueueDropsTheOldestRequest() {
  std::atomic<bool> release{false};
  NavPrefetch<R> p(2, 8);
  p.Start([&release](std::uint64_t frame, const Pose& pose, std::int64_t, R* out) {
    while (!release.load()) std::this_thread::sleep_for(std::chrono::milliseconds(1));
    out->frame = frame;
    out->value = Drawn(frame, pose);
  });
  p.Arm(true);
  CHECK(p.Submit(10, PoseOf(10), 0));
  std::this_thread::sleep_for(std::chrono::milliseconds(20));   // 10 is in flight, blocked
  for (std::uint64_t f = 11; f <= 14; ++f) CHECK(p.Submit(f, PoseOf(f), 0));
  CHECK(p.Stats().droppedQueue == 2);            // 11 and 12 dropped, 13 and 14 queued
  release = true;
  R r;
  std::vector<std::string> carried;
  CHECK(p.Take(12, 10 * kMs, &r, &carried) == TakeOutcome::kNotSubmitted);   // dropped: render on the chain
  CHECK(p.Take(13, 500 * kMs, &r, &carried) == TakeOutcome::kHit);            // the newest two were kept
  CHECK(r.value == Drawn(13, PoseOf(13)));
  CHECK(p.Take(14, 500 * kMs, &r, &carried) == TakeOutcome::kHit);
  CHECK(r.value == Drawn(14, PoseOf(14)));
}

// A take of a later frame while an earlier one still renders: that render is never planned, and the
// route change it raised reaches the next take.
void TestRenderOvertakenByALaterTakeKeepsItsEvent() {
  NavPrefetch<R> p;
  p.Start(Fake(60, {3}));
  p.Arm(true);
  CHECK(p.Submit(3, PoseOf(3), 0));
  std::this_thread::sleep_for(std::chrono::milliseconds(10));   // 3 in flight
  R r;
  std::vector<std::string> carried;
  CHECK(p.Take(4, 1 * kMs, &r, &carried) == TakeOutcome::kNotSubmitted);   // 4 never requested
  CHECK(carried.empty());
  std::this_thread::sleep_for(std::chrono::milliseconds(120));             // 3 finishes, already taken past
  CHECK(p.Submit(5, PoseOf(5), 0));
  CHECK(p.Take(5, 500 * kMs, &r, &carried) == TakeOutcome::kHit);
  CHECK(carried.size() == 1 && carried[0] == "{\"frame\":3}");
  CHECK(p.Stats().discarded == 1);
}

// The step's use of a prefetched render (TakeNavPrefetch, navigation_input.cpp): every pose field, the
// route identity and the render's own success decide.
void TestDecideUse() {
  const Pose base = PoseOf(9);
  const std::string route = "route /r.json sha256 ab";
  CHECK(DecideUse(true, base, base, route, route) == UseDecision::kUse);
  CHECK(DecideUse(false, base, base, route, route) == UseDecision::kRenderFailed);
  for (int field = 0; field < 6; ++field) {
    Pose moved = base;
    double* f[] = {&moved.x, &moved.y, &moved.z, &moved.roll, &moved.pitch, &moved.yaw};
    *f[field] += 1e-9;
    CHECK(DecideUse(true, base, moved, route, route) == UseDecision::kPoseChanged);
  }
  CHECK(DecideUse(true, base, base, route, "withdrawn") == UseDecision::kRouteChanged);
  CHECK(DecideUse(true, base, base, route, "route /r.json sha256 ac") == UseDecision::kRouteChanged);
  CHECK(DecideUse(false, base, PoseOf(10), route, "none") == UseDecision::kRenderFailed);   // failure first
}

void TestStopJoinsAndRefusesLaterRequests() {
  NavPrefetch<R> p;
  p.Start(Fake(5));
  p.Arm(true);
  for (std::uint64_t f = 1; f <= 3; ++f) p.Submit(f, PoseOf(f), 0);
  const auto t0 = std::chrono::steady_clock::now();
  p.Stop();
  CHECK(std::chrono::steady_clock::now() - t0 < std::chrono::seconds(2));
  CHECK(!p.Submit(9, PoseOf(9), 0));
}

// Producer on the tick thread, consumer on the chain, 400 frames 1 ms apart: every hit holds exactly
// what was drawn for its own frame and pose (run under ThreadSanitizer too).
void TestConcurrentProducerAndConsumer() {
  NavPrefetch<R> p;
  p.Start(Fake(0));
  p.Arm(true);
  std::atomic<std::uint64_t> produced{0};
  std::thread producer([&] {
    for (std::uint64_t f = 1; f <= 400; ++f) {
      p.Submit(f, PoseOf(f), static_cast<std::int64_t>(f));
      produced = f;
      std::this_thread::sleep_for(std::chrono::microseconds(1000));
    }
  });
  int hits = 0, wrong = 0;
  std::uint64_t next = 1;
  while (next <= 400) {
    if (produced.load() < next) {
      std::this_thread::sleep_for(std::chrono::microseconds(200));
      continue;
    }
    R r;
    std::vector<std::string> carried;
    if (p.Take(next, 50 * kMs, &r, &carried) == TakeOutcome::kHit) {
      ++hits;
      if (r.frame != next || r.value != Drawn(next, PoseOf(next)) || r.arrival != static_cast<std::int64_t>(next)) ++wrong;
    }
    next += 1 + (next % 7 == 0 ? 1 : 0);          // skip a frame now and then, as merged or dropped steps do
  }
  producer.join();
  CHECK(wrong == 0);
  CHECK(hits > 300);
}

}  // namespace

int main(int argc, char** argv) {
  // With an argument, only that test (1-based): run_tests.sh runs each in its own process under
  // ThreadSanitizer, which keeps the state of a std::mutex at a reused stack address across tests.
  void (*tests[])() = {TestUnarmedRefusesAndTakeFallsBack, TestHitIsWhatTheRendererDrewForThatPose,
                       TestTakeWaitsForAnInFlightRender, TestTimeoutAndTheLateResultIsDiscardedWithItsEvent,
                       TestOlderResultsAreDiscardedAndTheirEventsCarriedOldestFirst, TestFullQueueDropsTheOldestRequest,
                       TestStopJoinsAndRefusesLaterRequests, TestConcurrentProducerAndConsumer,
                       TestRenderOvertakenByALaterTakeKeepsItsEvent, TestDecideUse};
  const int n = static_cast<int>(sizeof(tests) / sizeof(tests[0]));
  std::printf("NAV_PREFETCH_TESTS start\n");
  const int only = argc > 1 ? std::atoi(argv[1]) : 0;
  if (only == -1) {
    std::printf("%d\n", n);
    return 0;
  }
  for (int i = 1; i <= n; ++i) {
    if (only == 0 || only == i) tests[i - 1]();
  }
  std::printf("NAV_PREFETCH_TESTS %s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
  return g_failures == 0 ? 0 : 1;
}
