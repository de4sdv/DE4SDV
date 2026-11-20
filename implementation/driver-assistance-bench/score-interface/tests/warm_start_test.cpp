// Unit tests of the warm start (patch 0005, warm_start.hpp; D-S1-1 of the S1 build plan): no upstream header, no
// OpenCV. The candidate's start and loop run on a virtual clock against fakes of upstream's pipeline (a two-frame
// buffer, then one inference per pass; the first inference costs 724 ms, as on the L4) and of the world (one image
// every 0.1 s from the go, into the module's own LatestSlot, which counts every replaced image as a drop).
//
// Build: g++ -std=c++17 -Wall -Wextra -Werror -I<module>/include -I<bench>/interfaces/include warm_start_test.cpp
//        <module>/src/core.cpp
// Run:   warm_start_test
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <string>
#include <vector>

#include "de4sdv/score_interface/core.hpp"
#include "de4sdv/score_interface/warm_start.hpp"
#include "fakes.hpp"

namespace si = de4sdv::score_interface;

static int failures = 0;
#define EXPECT(cond)                                              \
  do {                                                            \
    if (!(cond)) {                                                \
      std::printf("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond); \
      ++failures;                                                 \
    }                                                             \
  } while (0)

namespace {

constexpr int kDummy = -1;  // the frame id of the warm start's dummy image

// The virtual clock, ms. The world holds its first tick until the go; from then on one image per period.
struct World {
  double now_ms = 0.0;
  double go_ms = 5000.0;
  double period_ms = 100.0;
};

// Upstream's InferencePipeline as the loop sees it (inference.cpp:146-215 at the pin): process() buffers the frame;
// with fewer than two frames it returns no result; otherwise it runs the networks on (previous, current). The first
// inference of the process is the cold one.
struct FakePipeline {
  explicit FakePipeline(World* w) : world(w) {}
  World* world;
  double first_inference_ms = 724.0;
  double inference_ms = 45.0;
  double buffer_ms = 2.0;
  int buffered = 0;
  int prev = kDummy - 1, curr = kDummy - 1;
  bool warm = false;
  int inferences = 0;
  int resets = 0;
  std::vector<std::pair<int, int>> results;  // (previous, current) of each result
  bool never_result = false;                 // a pipeline that never gives a result

  bool Process(int frame) {
    prev = (buffered == 0) ? frame : curr;
    curr = frame;
    buffered = std::min(buffered + 1, 2);
    if (buffered < 2 || never_result) {
      world->now_ms += buffer_ms;
      return false;
    }
    world->now_ms += warm ? inference_ms : first_inference_ms;
    warm = true;
    ++inferences;
    results.emplace_back(prev, curr);
    return true;
  }
  void Reset() {
    buffered = 0;
    prev = curr = kDummy - 1;
    ++resets;
  }
};

// The world's images and the module's camera slot (ScoreCameraInterface keeps only the newest image in a LatestSlot).
struct Camera {
  explicit Camera(World* w) : world(w) {}
  World* world;
  bool attached = false;
  int next = 0;
  si::LatestSlot<int> slot;
  void Deliver() {
    if (!attached) return;
    while (world->go_ms + next * world->period_ms <= world->now_ms) slot.Put(next++);
  }
};

struct Run {
  std::uint64_t drops = 0;
  std::uint64_t received = 0;
  double running_reported_ms = -1.0;
  double longest_alive_gap_ms = 0.0;
  int attaches = 0;
  bool attached_before_any_inference = false;
  std::vector<std::pair<int, int>> real_results;
};

// The start in the order of the patched vision_pilot.cpp. warm: patch 0005 (the pipeline is built, warmed and reset
// before the module starts); otherwise 0002's order (the module starts first, then the pipeline is built). Then the
// loop for run_ms after the go: take the newest image, one pass, one alive notification per pass with a result.
Run Simulate(bool warm, double engine_build_ms, double run_ms, FakePipeline* pipeline_out = nullptr) {
  World world;
  FakePipeline pipeline{&world};
  Camera camera{&world};
  fakes::LifecycleClient lifecycle;
  si::CycleSupervision supervision(&lifecycle, nullptr);
  Run run;
  auto attach = [&]() {  // ScoreInterface::Start(): the attach returns at the go's first tick
    ++run.attaches;
    run.attached_before_any_inference = pipeline.inferences == 0;
    world.now_ms = std::max(world.now_ms, world.go_ms);
    camera.attached = true;
    return true;
  };
  if (warm) {
    world.now_ms += engine_build_ms;  // OnnxEngine and InferencePipeline, before the module starts
    si::WarmStartRecord record;
    const bool started = si::WarmStart([&] { return pipeline.Process(kDummy); }, [&] { pipeline.Reset(); }, attach,
                                       &record);
    EXPECT(started);
    EXPECT(record.passes == 2 && record.result);
    EXPECT(record.end_mono_ns >= record.begin_mono_ns);
  } else {
    attach();
    world.now_ms += engine_build_ms;  // 0002: the pipeline is built after the attach
  }
  const std::size_t warm_results = pipeline.results.size();
  double last_alive_ms = -1.0;
  while (world.now_ms < world.go_ms + run_ms) {
    camera.Deliver();
    int frame = 0;
    if (!camera.slot.Take(&frame)) {
      world.now_ms += 5.0;  // upstream's loop sleeps 5 ms on an empty frame (vision_pilot.cpp:120-123)
      continue;
    }
    if (pipeline.Process(frame)) {
      supervision.CycleCompleted(false);
      if (run.running_reported_ms < 0) run.running_reported_ms = world.now_ms;
      if (last_alive_ms >= 0) run.longest_alive_gap_ms = std::max(run.longest_alive_gap_ms, world.now_ms - last_alive_ms);
      last_alive_ms = world.now_ms;
    }
    camera.Deliver();  // the images that came during the pass
  }
  run.drops = camera.slot.dropped();
  run.received = camera.slot.received();
  run.real_results.assign(pipeline.results.begin() + static_cast<long>(warm_results), pipeline.results.end());
  EXPECT(lifecycle.Count("running") == 1);
  if (pipeline_out != nullptr) *pipeline_out = pipeline;
  return run;
}

void TheFakeReproducesAttempt3() {
  // 0002's order with a 724 ms cold first inference and ~0.55 s of pipeline construction after the attach: drops
  // in the first 1.3 s after the go, as in attempt 3 (run1 12, run2 11).
  const Run run = Simulate(false, 550.0, 10000.0);
  std::printf("0002 order: %llu of %llu images dropped\n", static_cast<unsigned long long>(run.drops),
              static_cast<unsigned long long>(run.received));
  EXPECT(run.drops >= 6);
  EXPECT(run.longest_alive_gap_ms < 400.0);  // the supervision starts only after the cold inference (C-1)
}

void AFirstInferenceOf724MsGivesNoDropAfterTheGo() {
  FakePipeline pipeline{nullptr};
  const Run run = Simulate(true, 550.0, 10000.0, &pipeline);
  std::printf("warm start: %llu of %llu images dropped\n", static_cast<unsigned long long>(run.drops),
              static_cast<unsigned long long>(run.received));
  EXPECT(run.drops == 0);
  EXPECT(run.received >= 100);
  EXPECT(run.attaches == 1);
  EXPECT(!run.attached_before_any_inference);  // the networks ran before the attach
  EXPECT(pipeline.resets == 1);
  // nothing of the dummy reaches a plan: the first real result pairs two real images, the first and the second
  EXPECT(!run.real_results.empty());
  if (!run.real_results.empty()) {
    EXPECT(run.real_results.front().first == 0 && run.real_results.front().second == 1);
  }
  for (const auto& r : run.real_results) EXPECT(r.first != kDummy && r.second != kDummy);
  // the candidate reports running at its first pass with a result, after the go, and every pass stays in the cycle
  EXPECT(run.running_reported_ms > 5000.0);
  EXPECT(run.longest_alive_gap_ms <= 110.0);
}

void APipelineWithoutAResultStillStartsOnce() {
  World world;
  FakePipeline pipeline{&world};
  pipeline.never_result = true;
  int starts = 0;
  si::WarmStartRecord record;
  const int value = si::WarmStart([&] { return pipeline.Process(kDummy); }, [&] { pipeline.Reset(); },
                                  [&] { return ++starts; }, &record);
  EXPECT(value == 1 && starts == 1);
  EXPECT(record.passes == si::kWarmStartMaxPasses && !record.result);
  EXPECT(pipeline.resets == 1);
}

void TheStartComesAfterTheResetAndItsValueIsReturned() {
  std::vector<std::string> order;
  int passes = 0;
  const std::string value = si::WarmStart(
      [&] {
        order.push_back("pass");
        return ++passes == 2;
      },
      [&] { order.push_back("reset"); }, [&] {
        order.push_back("start");
        return std::string("module");
      },
      nullptr);
  EXPECT(value == "module");
  EXPECT((order == std::vector<std::string>{"pass", "pass", "reset", "start"}));
}

}  // namespace

int main() {
  TheFakeReproducesAttempt3();
  AFirstInferenceOf724MsGivesNoDropAfterTheGo();
  APipelineWithoutAResultStillStartsOnce();
  TheStartComesAfterTheResetAndItsValueIsReturned();
  if (failures != 0) {
    std::printf("warm_start_test: %d failed\n", failures);
    return 1;
  }
  std::printf("warm_start_test: all passed\n");
  return 0;
}
