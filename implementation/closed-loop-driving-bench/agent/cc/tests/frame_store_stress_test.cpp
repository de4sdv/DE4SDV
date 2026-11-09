// Multi-threaded stress test of the frame store.
//
// Six LibCarla image threads, one world-tick thread, one consumer and one
// deadline-poll thread, run at an accelerated 10 Hz equivalent (2 ms per
// frame). Images jitter, 2% of them are withheld, and the consumer sometimes
// takes longer than a frame period, so slots complete, age out at the
// deadline, get skipped and, under pressure, overflow.
//
// Invariants asserted at the end (all counters are read after a full drain):
//   1. frames = snapshots + overflowSnapshots + lateSnapshots
//   2. snapshots = readyComplete + readyDeadline + droppedIncompleteSnapshot
//                  + inFlightSnapshot            (inFlightSnapshot = 0)
//   3. slotsCreated = readyComplete + readyDeadline + droppedIncomplete
//                     + inFlightSnapshot + inFlightNoSnapshot
//   4. readyComplete + readyDeadline = taken + skipped + readyUntaken
//      (readyUntaken = 0) -- every ready slot is consumed or counted once
//   5. frames taken are strictly increasing
//   6. the image bytes of a locked slot never change between Take and Release
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <random>
#include <string>
#include <thread>
#include <vector>

#include <atomic>

#include "frame_store.h"

using de4sdv::driving::agent::CountersSnapshot;
using de4sdv::driving::agent::FrameHandle;
using de4sdv::driving::agent::FrameStore;
using de4sdv::driving::agent::FrameStoreConfig;
using de4sdv::driving::agent::HeroSnapshot;
using de4sdv::driving::agent::kCameraCount;
using Clock = std::chrono::steady_clock;

namespace {

int g_failures = 0;
int g_checks = 0;

void Check(bool condition, const char* expression, const char* file, int line) {
  ++g_checks;
  if (!condition) {
    ++g_failures;
    std::printf("FAIL %s:%d: %s\n", file, line, expression);
  }
}

#define CHECK(condition) Check((condition), #condition, __FILE__, __LINE__)

constexpr int kWidth = 48;
constexpr int kHeight = 32;
constexpr std::size_t kImageBytes =
    static_cast<std::size_t>(kWidth) * static_cast<std::size_t>(kHeight) * 4U;
constexpr std::int64_t kPeriodNs = 2'000'000;      // 2 ms: 50x real time
constexpr std::int64_t kDeadlineNs = 12'000'000;   // 95 ms at that speed

std::int64_t NowNs() {
  return std::chrono::duration_cast<std::chrono::nanoseconds>(
             Clock::now().time_since_epoch())
      .count();
}

void SleepUntil(Clock::time_point target) {
  std::this_thread::sleep_until(target);
}

std::uint8_t Pattern(std::size_t camera, std::uint64_t frame, std::size_t index) {
  return static_cast<std::uint8_t>((camera * 131U + frame * 17U + index * 3U) & 0xFFU);
}

std::uint64_t Checksum(const de4sdv::driving::agent::FrameView& view) {
  std::uint64_t hash = 1469598103934665603ULL;
  for (const auto& camera : view.cameras) {
    if (camera.size == 0 || camera.data == nullptr) continue;
    for (std::size_t i = 0; i < camera.size; ++i) {
      hash ^= camera.data[i];
      hash *= 1099511628211ULL;
    }
  }
  return hash;
}

struct Shared {
  std::atomic<bool> stopRequested{false};
  std::atomic<std::uint64_t> imagesAttempted{0};
  std::atomic<std::uint64_t> imagesWithheld{0};
  std::atomic<std::uint64_t> checksumFailures{0};
};

void ImageThread(FrameStore* store, std::size_t camera, std::uint64_t frames,
                 Clock::time_point t0, Shared* shared, std::uint32_t seed) {
  std::mt19937 rng(seed);
  std::uniform_int_distribution<int> jitterMs(0, 3);
  std::uniform_int_distribution<int> lateMs(8, 19);
  std::uniform_int_distribution<int> percent(0, 99);
  std::vector<std::uint8_t> bytes(kImageBytes);
  for (std::uint64_t frame = 0; frame < frames; ++frame) {
    std::int64_t offset =
        static_cast<std::int64_t>(frame) * kPeriodNs +
        static_cast<std::int64_t>(jitterMs(rng)) * 1'000'000;
    if (percent(rng) < 5) {
      // A stale delivery: this camera's frame lands after readiness.
      offset += static_cast<std::int64_t>(lateMs(rng)) * 1'000'000;
    }
    if (percent(rng) >= 5) SleepUntil(t0 + std::chrono::nanoseconds(offset));  // bursts
    if (percent(rng) < 2) {
      shared->imagesWithheld.fetch_add(1, std::memory_order_relaxed);
      continue;
    }
    for (std::size_t i = 0; i < kImageBytes; ++i) bytes[i] = Pattern(camera, frame, i);
    shared->imagesAttempted.fetch_add(1, std::memory_order_relaxed);
    store->OnImage(camera, frame, bytes.data(), bytes.size(), kWidth, kHeight, 90.0, NowNs());
  }
}

void SnapshotThread(FrameStore* store, std::uint64_t frames, Clock::time_point t0) {
  for (std::uint64_t frame = 0; frame < frames; ++frame) {
    SleepUntil(t0 + std::chrono::nanoseconds(static_cast<std::int64_t>(frame) * kPeriodNs));
    HeroSnapshot snapshot;
    snapshot.pose.x = 0.5 * static_cast<double>(frame);
    snapshot.pose.yaw = 0.001 * static_cast<double>(frame);
    snapshot.velocity.x = 12.0;
    snapshot.acceleration.x = -0.2;
    snapshot.angularVelocity.z = 0.01;
    store->OnSnapshot(frame, snapshot, NowNs());
  }
}

void ConsumerThread(FrameStore* store, Shared* shared, std::vector<std::uint64_t>* taken,
                    std::uint32_t seed) {
  std::mt19937 rng(seed);
  std::uniform_int_distribution<int> workUs(0, 2500);   // about one frame period
  std::uniform_int_distribution<int> slowUs(4000, 14000);  // longer: backlog and skips
  std::uniform_int_distribution<int> slow(0, 99);
  for (;;) {
    FrameHandle handle = store->TakeNewestReady();
    if (!handle.valid()) {
      if (shared->stopRequested.load(std::memory_order_acquire)) break;
      std::this_thread::sleep_for(std::chrono::microseconds(200));
      continue;
    }
    const std::uint64_t before = Checksum(handle.view());
    taken->push_back(handle.frame());
    const int delay = slow(rng) < 12 ? slowUs(rng) : workUs(rng);
    std::this_thread::sleep_for(std::chrono::microseconds(delay));
    const std::uint64_t after = Checksum(handle.view());
    if (before != after) shared->checksumFailures.fetch_add(1, std::memory_order_relaxed);
    store->Release(handle);
  }
}

void DeadlineThread(FrameStore* store, Shared* shared) {
  while (!shared->stopRequested.load(std::memory_order_acquire)) {
    store->PollDeadlines(NowNs());
    std::this_thread::sleep_for(std::chrono::microseconds(300));
  }
}

std::uint64_t EnvOr(const char* name, std::uint64_t fallback) {
  const char* value = std::getenv(name);
  if (value == nullptr || *value == '\0') return fallback;
  return static_cast<std::uint64_t>(std::strtoull(value, nullptr, 10));
}

void PrintCounters(const CountersSnapshot& c) {
  std::printf(
      "STRESS counters: complete=%llu deadline=%llu skipped=%llu dropped_incomplete=%llu "
      "(with snapshot %llu) overflow=%llu (snap %llu, img %llu) misuse=%llu late_snap=%llu "
      "dup_snap=%llu late_images=[%llu %llu %llu %llu %llu %llu] snapshots=%llu "
      "slots=%llu sink=%llu\n",
      static_cast<unsigned long long>(c.readyComplete),
      static_cast<unsigned long long>(c.readyDeadline),
      static_cast<unsigned long long>(c.skipped),
      static_cast<unsigned long long>(c.droppedIncomplete),
      static_cast<unsigned long long>(c.droppedIncompleteSnapshot),
      static_cast<unsigned long long>(c.overflow),
      static_cast<unsigned long long>(c.overflowSnapshots),
      static_cast<unsigned long long>(c.overflowImages),
      static_cast<unsigned long long>(c.misuse),
      static_cast<unsigned long long>(c.lateSnapshots),
      static_cast<unsigned long long>(c.duplicateSnapshots),
      static_cast<unsigned long long>(c.lateImages[0]),
      static_cast<unsigned long long>(c.lateImages[1]),
      static_cast<unsigned long long>(c.lateImages[2]),
      static_cast<unsigned long long>(c.lateImages[3]),
      static_cast<unsigned long long>(c.lateImages[4]),
      static_cast<unsigned long long>(c.lateImages[5]),
      static_cast<unsigned long long>(c.snapshots),
      static_cast<unsigned long long>(c.slotsCreated),
      static_cast<unsigned long long>(c.sinkInvocations));
}

}  // namespace

int main() {
  const std::uint64_t frames = EnvOr("STRESS_FRAMES", 2000);
  std::printf("STRESS start: frames=%llu period=%lld ns deadline=%lld ns\n",
              static_cast<unsigned long long>(frames),
              static_cast<long long>(kPeriodNs), static_cast<long long>(kDeadlineNs));

  FrameStoreConfig config;
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    config.cameras[camera].width = kWidth;
    config.cameras[camera].height = kHeight;
  }
  config.ringSize = 8;
  config.deadlineNs = kDeadlineNs;

  std::atomic<std::uint64_t> sinkCount{0};
  config.readySink = [&sinkCount](std::uint64_t, bool) {
    sinkCount.fetch_add(1, std::memory_order_relaxed);
  };

  FrameStore store(config);
  Shared shared;
  std::vector<std::uint64_t> taken;
  taken.reserve(frames);
  const Clock::time_point t0 = Clock::now();

  std::thread consumer(ConsumerThread, &store, &shared, &taken, 0xC0FFEEU);
  std::thread poller(DeadlineThread, &store, &shared);

  std::thread tick(SnapshotThread, &store, frames, t0);
  std::vector<std::thread> cameras;
  cameras.reserve(kCameraCount);
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    cameras.emplace_back(ImageThread, &store, camera, frames, t0, &shared,
                         0x1234U + static_cast<std::uint32_t>(camera) * 7919U);
  }

  for (auto& thread : cameras) thread.join();
  tick.join();

  // Producers are done: let the consumer and the poller finish their queues.
  std::this_thread::sleep_for(std::chrono::milliseconds(20));
  shared.stopRequested.store(true, std::memory_order_release);
  poller.join();
  consumer.join();

  // Full drain: every deadline that can fire does, then everything ready is
  // taken and released, so the counters describe the run and not the moment.
  // Drained frames are older than the consumer's last take, so they are
  // counted separately and kept out of the ordering check.
  std::uint64_t drained = 0;
  for (int round = 0; round < 2; ++round) {
    store.PollDeadlines(NowNs() + 10'000'000'000LL);
    for (;;) {
      FrameHandle handle = store.TakeNewestReady();
      if (!handle.valid()) break;
      ++drained;
      store.Release(handle);
    }
  }
  const std::uint64_t total_taken = taken.size() + drained;

  const CountersSnapshot c = store.Counters();
  PrintCounters(c);

  // 1. Producer side: every frame is either stored or overflowed.
  CHECK(c.snapshots + c.overflowSnapshots + c.lateSnapshots == frames);
  CHECK(c.misuse == 0);

  // 2. Snapshot identity.
  CHECK(c.inFlightSnapshot == 0);
  CHECK(c.snapshots ==
        c.readyComplete + c.readyDeadline + c.droppedIncompleteSnapshot + c.inFlightSnapshot);

  // 3. Slot identity.
  CHECK(c.slotsCreated == c.readyComplete + c.readyDeadline + c.droppedIncomplete +
                             c.inFlightSnapshot + c.inFlightNoSnapshot);

  // 4. Ready disposition: consumed, skipped, or still untaken (none).
  CHECK(c.readyUntaken == 0);
  CHECK(c.locked == 0);
  CHECK(c.readyComplete + c.readyDeadline == total_taken + c.skipped + c.readyUntaken);

  // 5. The signal count matches the ready transitions.
  CHECK(sinkCount.load() == c.readyComplete + c.readyDeadline);
  CHECK(c.sinkInvocations == c.readyComplete + c.readyDeadline);

  // 6. Frames are handed over in increasing order.
  bool increasing = true;
  for (std::size_t i = 1; i < taken.size(); ++i) {
    if (taken[i] <= taken[i - 1]) increasing = false;
  }
  CHECK(increasing);

  // 7. The locked slot never changed under the consumer.
  CHECK(shared.checksumFailures.load() == 0);

  // 8. The paths this test exists to exercise were taken.
  CHECK(c.readyComplete > 0);
  CHECK(c.readyDeadline > 0);
  CHECK(c.skipped > 0);
  std::uint64_t late = 0;
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) late += c.lateImages[camera];
  CHECK(late > 0);

  std::printf(
      "STRESS summary: frames=%llu taken=%zu snapshots=%llu complete=%llu deadline=%llu "
      "skipped=%llu dropped=%llu overflow_snap=%llu late_images=%llu sink=%llu\n",
      static_cast<unsigned long long>(frames), taken.size(),
      static_cast<unsigned long long>(c.snapshots),
      static_cast<unsigned long long>(c.readyComplete),
      static_cast<unsigned long long>(c.readyDeadline),
      static_cast<unsigned long long>(c.skipped),
      static_cast<unsigned long long>(c.droppedIncomplete),
      static_cast<unsigned long long>(c.overflowSnapshots),
      static_cast<unsigned long long>(late),
      static_cast<unsigned long long>(c.sinkInvocations));

  std::printf("STRESS %s: %d checks, %d failures\n", g_failures == 0 ? "PASS" : "FAIL",
              g_checks, g_failures);
  return g_failures == 0 ? 0 : 1;
}
