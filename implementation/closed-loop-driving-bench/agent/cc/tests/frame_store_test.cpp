// Unit tests of the driving agent's frame store and pace datagram.
//
// Build and run:
//   g++ -std=c++17 -O2 -Wall -Wextra -Werror -pthread -I.
//       tests/frame_store_test.cpp frame_store.cpp pace_signal.cpp
//       -o .build/frame_store_test
//   .build/frame_store_test
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <poll.h>

#include <chrono>
#include <future>
#include <thread>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>
#include <vector>

#include "frame_store.h"
#include "pace_signal.h"

using de4sdv::driving::agent::CameraIndex;
using de4sdv::driving::agent::CameraView;
using de4sdv::driving::agent::CountersSnapshot;
using de4sdv::driving::agent::FrameHandle;
using de4sdv::driving::agent::FrameStore;
using de4sdv::driving::agent::FrameStoreConfig;
using de4sdv::driving::agent::FrameView;
using de4sdv::driving::agent::HeroSnapshot;
using de4sdv::driving::agent::kCameraCount;
using de4sdv::driving::agent::kDefaultDeadlineNs;
using de4sdv::driving::agent::kFront;
using de4sdv::driving::agent::kFrontLeft;
using de4sdv::driving::agent::kMaxMerged;
using de4sdv::driving::agent::kRear;
using de4sdv::driving::agent::kRearLeft;
using de4sdv::driving::agent::kRearRight;
using de4sdv::driving::agent::PaceSignal;

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

constexpr int kWidth = 16;
constexpr int kHeight = 8;
constexpr std::size_t kImageBytes =
    static_cast<std::size_t>(kWidth) * static_cast<std::size_t>(kHeight) * 4U;

std::uint8_t Pattern(std::size_t camera, std::uint64_t frame, std::size_t index) {
  return static_cast<std::uint8_t>((camera * 37U + frame * 11U + index * 7U) & 0xFFU);
}

std::vector<std::uint8_t> ImageBytes(std::size_t camera, std::uint64_t frame,
                                     std::size_t size) {
  std::vector<std::uint8_t> bytes(size);
  for (std::size_t i = 0; i < size; ++i) bytes[i] = Pattern(camera, frame, i);
  return bytes;
}

std::uint64_t Fnv1a(const std::uint8_t* data, std::size_t size) {
  std::uint64_t hash = 1469598103934665603ULL;
  for (std::size_t i = 0; i < size; ++i) {
    hash ^= data[i];
    hash *= 1099511628211ULL;
  }
  return hash;
}

std::uint64_t ChecksumAll(const FrameView& view) {
  std::uint64_t hash = 1469598103934665603ULL;
  for (const CameraView& camera : view.cameras) {
    if (camera.size == 0 || camera.data == nullptr) continue;
    hash ^= Fnv1a(camera.data, camera.size);
    hash *= 1099511628211ULL;
  }
  return hash;
}

HeroSnapshot MakeSnapshot(std::uint64_t frame) {
  HeroSnapshot snapshot;
  snapshot.pose.x = 10.0 + static_cast<double>(frame);
  snapshot.pose.y = -2.5;
  snapshot.pose.z = 0.4;
  snapshot.pose.yaw = 0.125 * static_cast<double>(frame);
  snapshot.velocity.x = 12.5;
  snapshot.velocity.y = 0.1;
  snapshot.acceleration.x = -0.75;
  snapshot.angularVelocity.z = 0.03;
  return snapshot;
}

struct SinkLog {
  std::vector<std::uint64_t> frames;
  std::vector<char> byDeadline;
  std::uint64_t Count() const { return frames.size(); }
  bool WasByDeadline(std::size_t index) const {
    return index < byDeadline.size() && byDeadline[index] != 0;
  }
  bool FrameAt(std::size_t index, std::uint64_t* frame) const {
    if (index >= frames.size()) return false;
    *frame = frames[index];
    return true;
  }
};

FrameStoreConfig MakeConfig(std::size_t ring = 8, std::int64_t deadlineNs = kDefaultDeadlineNs,
                            SinkLog* log = nullptr, int width = kWidth, int height = kHeight) {
  FrameStoreConfig config;
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    config.cameras[camera].width = width;
    config.cameras[camera].height = height;
  }
  config.ringSize = ring;
  config.deadlineNs = deadlineNs;
  if (log != nullptr) {
    config.readySink = [log](std::uint64_t frame, bool byDeadline) {
      log->frames.push_back(frame);
      log->byDeadline.push_back(byDeadline);
    };
  }
  return config;
}

// Feeds one camera image with the standard pattern.
bool FeedImage(FrameStore& store, std::size_t camera, std::uint64_t frame,
               std::int64_t arrival, std::size_t size = kImageBytes, int width = kWidth,
               int height = kHeight) {
  const std::vector<std::uint8_t> bytes = ImageBytes(camera, frame, size);
  return store.OnImage(camera, frame, bytes.data(), size, width, height, 90.0, arrival);
}

void FeedAllImages(FrameStore& store, std::uint64_t frame, std::int64_t arrival) {
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    CHECK(FeedImage(store, camera, frame, arrival));
  }
}

// The two accounting identities the stress test also asserts.
void CheckAccounting(const CountersSnapshot& c, std::uint64_t taken, const char* where) {
  ++g_checks;
  const std::uint64_t terminated =
      c.readyComplete + c.readyDeadline + c.droppedIncompleteSnapshot;
  if (c.snapshots != terminated + c.inFlightSnapshot) {
    ++g_failures;
    std::printf(
        "FAIL %s: snapshot identity %llu != %llu + %llu + %llu + %llu\n", where,
        static_cast<unsigned long long>(c.snapshots),
        static_cast<unsigned long long>(c.readyComplete),
        static_cast<unsigned long long>(c.readyDeadline),
        static_cast<unsigned long long>(c.droppedIncompleteSnapshot),
        static_cast<unsigned long long>(c.inFlightSnapshot));
  }
  ++g_checks;
  const std::uint64_t created = c.readyComplete + c.readyDeadline + c.droppedIncomplete +
                                c.inFlightSnapshot + c.inFlightNoSnapshot;
  if (c.slotsCreated != created) {
    ++g_failures;
    std::printf("FAIL %s: slot identity %llu != %llu\n", where,
                static_cast<unsigned long long>(c.slotsCreated),
                static_cast<unsigned long long>(created));
  }
  ++g_checks;
  const std::uint64_t ready = c.readyComplete + c.readyDeadline;
  if (ready != taken + c.merged + c.skipped + c.readyUntaken) {
    ++g_failures;
    std::printf("FAIL %s: ready identity %llu != %llu + %llu (merged) + %llu + %llu\n", where,
                static_cast<unsigned long long>(ready),
                static_cast<unsigned long long>(taken),
                static_cast<unsigned long long>(c.merged),
                static_cast<unsigned long long>(c.skipped),
                static_cast<unsigned long long>(c.readyUntaken));
  }
}

// ---------------------------------------------------------------- tests

// The snapshot sink (nav prefetch): once per accepted snapshot, with that snapshot and its arrival,
// never for a duplicate, a late or an overflowing one, and outside the store's lock (the sink may
// call back into the store).
void TestSnapshotSinkPerAcceptedSnapshot() {
  struct Seen {
    std::uint64_t frame;
    double x;
    std::int64_t arrival;
    std::uint64_t snapshotsCounted;
  };
  auto scenario = []() {
    std::vector<Seen> seen;
    FrameStore* self = nullptr;
    FrameStoreConfig config = MakeConfig(2);
    config.snapshotSink = [&seen, &self](std::uint64_t frame, const HeroSnapshot& snapshot,
                                         std::int64_t arrival) {
      // Counters() takes the store's lock: this deadlocks when the sink runs under it.
      seen.push_back({frame, snapshot.pose.x, arrival, self->Counters().snapshots});
    };
    FrameStore s(config);
    self = &s;
    CHECK(s.OnSnapshot(5, MakeSnapshot(5), 1'000));
    CHECK(seen.size() == 1);
    if (seen.size() == 1) {
      CHECK(seen[0].frame == 5);
      CHECK(seen[0].x == MakeSnapshot(5).pose.x);
      CHECK(seen[0].arrival == 1'000);
      CHECK(seen[0].snapshotsCounted == 1);   // the store counts the snapshot before the sink runs
    }
    CHECK(!s.OnSnapshot(5, MakeSnapshot(5), 2'000));   // duplicate
    CHECK(seen.size() == 1);
    CHECK(s.OnSnapshot(6, MakeSnapshot(6), 3'000));
    CHECK(seen.size() == 2);
    FeedAllImages(s, 6, 5'000);
    FrameHandle h = s.TakeNewestReady();               // takes 6, retires 5
    CHECK(h.valid() && h.frame() == 6);
    CHECK(!s.OnSnapshot(5, MakeSnapshot(5), 6'000));   // late: frame 5 is retired
    CHECK(seen.size() == 2);
    // Overflow as in TestOverflowWhenNothingEvictable: slot of 6 locked, 7 the protected newest ready.
    CHECK(s.OnSnapshot(7, MakeSnapshot(7), 7'000));
    FeedAllImages(s, 7, 7'500);
    CHECK(seen.size() == 3);
    CHECK(!s.OnSnapshot(8, MakeSnapshot(8), 8'000));   // neither slot can take frame 8
    CHECK(s.Counters().overflowSnapshots == 1);
    CHECK(seen.size() == 3);
    s.Release(h);
    return seen.size();
  };
  auto run = std::async(std::launch::async, scenario);
  if (run.wait_for(std::chrono::seconds(5)) != std::future_status::ready) {
    CHECK(!"snapshot sink deadlocked: it runs under the store's lock");
    std::fflush(stdout);
    std::_Exit(1);
  }
  CHECK(run.get() == 3);
}

// A snapshot that completes a slot (its images came first) is handed to the snapshot sink before the
// ready sink announces the step, so a prefetch is always submitted before the step can be taken.
void TestSnapshotSinkBeforeReadySink() {
  std::vector<std::string> order;
  FrameStoreConfig config = MakeConfig(4);
  config.readySink = [&order](std::uint64_t, bool) { order.push_back("ready"); };
  config.snapshotSink = [&order](std::uint64_t, const HeroSnapshot&, std::int64_t) { order.push_back("snapshot"); };
  FrameStore s(config);
  FeedAllImages(s, 9, 1'000);
  CHECK(order.empty());
  CHECK(s.OnSnapshot(9, MakeSnapshot(9), 2'000));
  CHECK(order.size() == 2);
  CHECK(order.size() == 2 && order[0] == "snapshot" && order[1] == "ready");
}

void TestConfigDefaults() {
  FrameStoreConfig config;
  CHECK(config.ringSize == 8);
  CHECK(config.deadlineNs == 95'000'000);
  CHECK(kDefaultDeadlineNs == 95'000'000);
  // Record names are the checkpoint's slot names (C2, ICD A25), not the CARLA role names `cam_*`.
  CHECK(std::string(de4sdv::driving::agent::CameraName(kFront)) == "front");
  CHECK(std::string(de4sdv::driving::agent::CameraName(kFrontLeft)) == "front_left");
  CHECK(std::string(de4sdv::driving::agent::CameraName(kRearLeft)) == "rear_left");
  CHECK(std::string(de4sdv::driving::agent::CameraName(kRear)) == "rear");
  CHECK(std::string(de4sdv::driving::agent::CameraName(kRearRight)) == "rear_right");
  CHECK(std::string(de4sdv::driving::agent::CameraName(9)) == "unknown");
}

void TestCompleteSlot() {
  SinkLog log;
  FrameStore s(MakeConfig(8, kDefaultDeadlineNs, &log));
  std::uint64_t firstFrame = 0;

  const std::int64_t arrival = 1'000'000;
  CHECK(s.OnSnapshot(7, MakeSnapshot(7), arrival));
  CountersSnapshot c = s.Counters();
  CHECK(c.snapshots == 1);
  CHECK(c.slotsCreated == 1);
  CHECK(c.inFlightSnapshot == 1);
  CHECK(c.readyComplete == 0);

  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    CHECK(FeedImage(s, camera, 7, arrival + 5000 + static_cast<std::int64_t>(camera)));
    if (camera + 1 < kCameraCount) {
      CHECK(s.Counters().readyComplete == 0);  // five images are not enough
    }
  }
  c = s.Counters();
  CHECK(c.readyComplete == 1);
  CHECK(c.readyDeadline == 0);
  CHECK(c.sinkInvocations == 1);
  CHECK(log.Count() == 1);
  CHECK(log.FrameAt(0, &firstFrame) && firstFrame == 7);
  CHECK(!log.WasByDeadline(0));
  CHECK(c.inFlightSnapshot == 0);
  CHECK(c.readyUntaken == 1);
  CHECK(c.locked == 0);

  FrameHandle handle = s.TakeNewestReady();
  CHECK(handle.valid());
  if (!handle.valid()) return;
  const FrameView& view = handle.view();
  CHECK(view.frame == 7);
  CHECK(view.readyByDeadline == false);
  CHECK(view.snapshotArrivalMonoNs == arrival);
  CHECK(view.deadlineMonoNs == arrival + 95'000'000);
  CHECK(view.snapshot.pose.x == 17.0);
  CHECK(view.snapshot.velocity.x == 12.5);
  CHECK(view.allPresent());
  CHECK(view.missingCount() == 0);
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    const CameraView& cam = view.cameras[camera];
    CHECK(cam.present && cam.valid && !cam.missing());
    CHECK(cam.imageFrame == 7);
    CHECK(cam.width == kWidth && cam.height == kHeight);
    CHECK(cam.fov == 90.0);
    CHECK(cam.size == kImageBytes);
    CHECK(cam.arrivalMonoNs == arrival + 5000 + static_cast<std::int64_t>(camera));
    CHECK(Fnv1a(cam.data, cam.size) == Fnv1a(ImageBytes(camera, 7, kImageBytes).data(), kImageBytes));
  }
  CHECK(s.Counters().locked == 1);

  s.Release(handle);
  CHECK(!handle.valid());
  c = s.Counters();
  CHECK(c.skipped == 0);
  CHECK(c.droppedIncomplete == 0);
  CHECK(c.locked == 0);
  CHECK(c.readyUntaken == 0);
  CHECK(c.inFlightSnapshot == 0);
  CheckAccounting(c, 1, "complete-slot");

  // The slot is free again: the next frame reuses the ring.
  CHECK(s.OnSnapshot(8, MakeSnapshot(8), arrival + 100'000'000));
  CHECK(s.Counters().slotsCreated == 2);
}

void TestDeadlineSlot() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  const std::int64_t arrival = 5'000'000;
  CHECK(store.OnSnapshot(1, MakeSnapshot(1), arrival));
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    if (camera == kRear) continue;  // one camera missing
    CHECK(FeedImage(store, camera, 1, arrival + 1000));
  }
  CHECK(store.Counters().readyComplete == 0);

  CHECK(store.PollDeadlines(arrival + 95'000'000 - 1) == 0);
  CHECK(store.Counters().readyDeadline == 0);
  CHECK(store.PollDeadlines(arrival + 95'000'000) == 1);  // the boundary fires
  CHECK(store.Counters().readyDeadline == 1);
  CHECK(store.Counters().sinkInvocations == 1);
  CHECK(log.Count() == 1);
  CHECK(log.WasByDeadline(0));

  // Polling again must not re-signal a ready slot.
  CHECK(store.PollDeadlines(arrival + 500'000'000) == 0);
  CHECK(store.Counters().sinkInvocations == 1);

  FrameHandle handle = store.TakeNewestReady();
  CHECK(handle.valid());
  if (!handle.valid()) return;
  const FrameView& view = handle.view();
  CHECK(view.readyByDeadline);
  CHECK(view.cameras[kRear].missing());
  CHECK(!view.cameras[kRear].present);
  CHECK(!view.cameras[kRear].valid);
  CHECK(view.cameras[kRear].size == 0);
  CHECK(view.missingCount() == 1);
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    if (camera == kRear) continue;
    CHECK(view.cameras[camera].present && view.cameras[camera].valid);
  }
  store.Release(handle);
  const CountersSnapshot c = store.Counters();
  CHECK(c.skipped == 0);
  CHECK(c.droppedIncomplete == 0);
  CheckAccounting(c, 1, "deadline-slot");
}

void TestImageBeforeSnapshot() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  const std::int64_t early = 2'000'000;

  // An image may arrive before its world tick.
  CHECK(FeedImage(store, kFront, 3, early));
  CountersSnapshot c = store.Counters();
  CHECK(c.inFlightNoSnapshot == 1);
  CHECK(c.inFlightSnapshot == 0);
  CHECK(store.PollDeadlines(early + 10'000'000'000LL) == 0);  // no deadline without a snapshot
  CHECK(c.slotsCreated == 1);

  CHECK(store.OnSnapshot(3, MakeSnapshot(3), early + 5000));
  CHECK(store.Counters().inFlightSnapshot == 1);
  for (std::size_t camera = 1; camera < kCameraCount; ++camera) {
    CHECK(FeedImage(store, camera, 3, early + 6000));
  }
  c = store.Counters();
  CHECK(c.readyComplete == 1);
  CHECK(c.readyDeadline == 0);

  FrameHandle handle = store.TakeNewestReady();
  CHECK(handle.valid());
  if (!handle.valid()) return;
  CHECK(handle.view().cameras[kFront].arrivalMonoNs == early);  // the early image was kept
  store.Release(handle);
  CheckAccounting(store.Counters(), 1, "image-before-snapshot");
}

void TestImageOnlyFrameAgesOutByEviction() {
  SinkLog log;
  FrameStore store(MakeConfig(2, 95'000'000, &log));
  CHECK(FeedImage(store, kFront, 0, 0));
  CHECK(store.PollDeadlines(10'000'000'000LL) == 0);
  CountersSnapshot c = store.Counters();
  CHECK(c.inFlightNoSnapshot == 1);
  CHECK(c.readyComplete + c.readyDeadline == 0);

  // Ring of two: the images-only frame is evicted, not made ready.
  CHECK(store.OnSnapshot(1, MakeSnapshot(1), 1000));
  CHECK(store.OnSnapshot(2, MakeSnapshot(2), 2000));
  c = store.Counters();
  CHECK(c.droppedIncomplete == 1);
  CHECK(c.droppedIncompleteSnapshot == 0);
  CHECK(c.readyComplete == 0);
  CHECK(log.Count() == 0);
  CheckAccounting(c, 0, "image-only-evicted");
}

void TestInvalidSizeImage() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));

  CHECK(store.OnSnapshot(2, MakeSnapshot(2), 1000));
  // Wrong width/height and twice the bytes: present, invalid, copied up to the
  // buffer bound only.
  const std::vector<std::uint8_t> big = ImageBytes(kFront, 2, 4 * kImageBytes);
  CHECK(store.OnImage(kFront, 2, big.data(), big.size(), 2 * kWidth, 2 * kHeight, 90.0, 1100));
  // Too few bytes: present, invalid, only what fits exists.
  const std::vector<std::uint8_t> small = ImageBytes(kFront, 2, 100);
  CHECK(store.OnImage(kFront + 1, 2, small.data(), small.size(), kWidth, kHeight, 90.0, 1200));
  for (std::size_t camera = 2; camera < kCameraCount; ++camera) {
    CHECK(FeedImage(store, camera, 2, 1300));
  }
  // Readiness needs presence, not validity: the input condition reports it.
  CHECK(store.Counters().readyComplete == 1);

  FrameHandle handle = store.TakeNewestReady();
  CHECK(handle.valid());
  if (!handle.valid()) return;
  const FrameView& view = handle.view();
  CHECK(view.cameras[kFront].present);
  CHECK(!view.cameras[kFront].valid);
  CHECK(view.cameras[kFront].width == 2 * kWidth);
  CHECK(view.cameras[kFront].height == 2 * kHeight);
  CHECK(view.cameras[kFront].size == kImageBytes);  // clamped to the slot buffer
  CHECK(Fnv1a(view.cameras[kFront].data, view.cameras[kFront].size) ==
        Fnv1a(big.data(), kImageBytes));
  CHECK(view.cameras[kFront + 1].present);
  CHECK(!view.cameras[kFront + 1].valid);
  CHECK(view.cameras[kFront + 1].size == 100);
  CHECK(Fnv1a(view.cameras[kFront + 1].data, 100) == Fnv1a(small.data(), 100));
  store.Release(handle);
  CheckAccounting(store.Counters(), 1, "invalid-size");
}

void TestLateImageAfterReady() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  CHECK(store.OnSnapshot(4, MakeSnapshot(4), 1000));
  FeedAllImages(store, 4, 2000);
  CHECK(store.Counters().readyComplete == 1);

  FrameHandle handle = store.TakeNewestReady();
  CHECK(handle.valid());
  if (!handle.valid()) return;
  const std::uint64_t checksum = ChecksumAll(handle.view());
  CHECK(checksum != 0);
  store.Release(handle);

  // A ready slot is immutable: the late image is dropped and counted.
  CHECK(!FeedImage(store, kRear, 4, 3000, kImageBytes));
  CHECK(store.Counters().lateImages[kRear] == 1);
  CHECK(store.Counters().readyComplete == 1);  // no new ready transition

  // A late image for a ready-by-deadline slot with a missing camera must not
  // fill the hole.
  SinkLog log2;
  FrameStore other(MakeConfig(8, 95'000'000, &log2));
  CHECK(other.OnSnapshot(5, MakeSnapshot(5), 1000));
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    if (camera == kRear) continue;
    CHECK(FeedImage(other, camera, 5, 1100));
  }
  CHECK(other.PollDeadlines(1000 + 95'000'000) == 1);
  CHECK(!FeedImage(other, kRear, 5, 2000));
  CountersSnapshot c = other.Counters();
  CHECK(c.lateImages[kRear] == 1);
  CHECK(c.readyDeadline == 1);
  CHECK(c.readyComplete == 0);
  FrameHandle h2 = other.TakeNewestReady();
  CHECK(h2.valid());
  if (h2.valid()) {
    CHECK(h2.view().cameras[kRear].missing());
    CHECK(h2.view().cameras[kRear].size == 0);
    CHECK(h2.view().cameras[kRear].data != nullptr);  // preallocated, just empty
    other.Release(h2);
  }
  (void)checksum;
}

void TestNewestReadySelectionAndSkips() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  for (std::uint64_t frame = 10; frame <= 12; ++frame) {
    CHECK(store.OnSnapshot(frame, MakeSnapshot(frame), static_cast<std::int64_t>(frame) * 1000));
    FeedAllImages(store, frame, static_cast<std::int64_t>(frame) * 1000 + 500);
  }
  CountersSnapshot c = store.Counters();
  CHECK(c.readyComplete == 3);
  CHECK(c.readyUntaken == 3);
  CHECK(c.sinkInvocations == 3);

  FrameHandle newest = store.TakeNewestReady();
  CHECK(newest.valid());
  if (!newest.valid()) return;
  CHECK(newest.frame() == 12);
  c = store.Counters();
  CHECK(c.skipped == 2);
  CHECK(c.readyUntaken == 0);
  CHECK(c.locked == 1);
  store.Release(newest);
  c = store.Counters();
  CHECK(c.skipped == 2);  // the taken slot is consumed, never counted as skipped
  CHECK(store.Counters().readyUntaken == 0);

  FrameHandle none = store.TakeNewestReady();
  CHECK(!none.valid());
  CHECK(store.Counters().misuse == 0);
  CheckAccounting(store.Counters(), 1, "newest-selection");

  // Skips are counted once even when the skipped slot is later retired.
  SinkLog log2;
  FrameStore two(MakeConfig(2, 95'000'000, &log2));
  for (std::uint64_t frame = 0; frame <= 1; ++frame) {
    CHECK(two.OnSnapshot(frame, MakeSnapshot(frame), 1000));
    FeedAllImages(two, frame, 1500);
  }
  FrameHandle h = two.TakeNewestReady();
  CHECK(h.valid() && h.frame() == 1);
  CHECK(two.Counters().skipped == 1);
  if (h.valid()) two.Release(h);
  CHECK(two.Counters().skipped == 1);
}

void TestEvictionCounters() {
  SinkLog log;
  FrameStore store(MakeConfig(4, 95'000'000, &log));
  for (std::uint64_t frame = 0; frame <= 2; ++frame) {
    CHECK(store.OnSnapshot(frame, MakeSnapshot(frame), static_cast<std::int64_t>(frame)));
  }
  CHECK(store.OnSnapshot(3, MakeSnapshot(3), 3000));
  FeedAllImages(store, 3, 3100);
  CHECK(store.Counters().readyComplete == 1);

  // Ring of four is full; frame 4 evicts the oldest filling slot (frame 0),
  // never the newest ready one (frame 3).
  CHECK(store.OnSnapshot(4, MakeSnapshot(4), 4000));
  CountersSnapshot c = store.Counters();
  CHECK(c.droppedIncomplete == 1);
  CHECK(c.droppedIncompleteSnapshot == 1);
  CHECK(c.skipped == 0);
  CHECK(c.readyComplete == 1);
  CHECK(c.readyUntaken == 1);
  CHECK(c.inFlightSnapshot == 3);
  CheckAccounting(c, 0, "eviction");

  FrameHandle handle = store.TakeNewestReady();
  CHECK(handle.valid() && handle.frame() == 3);
  if (handle.valid()) store.Release(handle);
  CheckAccounting(store.Counters(), 1, "eviction-after-take");
}

void TestEvictionPicksOldest() {
  SinkLog log;
  FrameStore store(MakeConfig(3, 95'000'000, &log));
  CHECK(store.OnSnapshot(3, MakeSnapshot(3), 1000));
  FeedAllImages(store, 3, 1500);                       // ready and protected
  CHECK(store.OnSnapshot(4, MakeSnapshot(4), 2000));   // filling
  CHECK(store.OnSnapshot(5, MakeSnapshot(5), 3000));   // filling
  CHECK(store.OnSnapshot(6, MakeSnapshot(6), 4000));   // ring full: evicts frame 4

  CountersSnapshot c = store.Counters();
  CHECK(c.droppedIncomplete == 1);
  CHECK(c.droppedIncompleteSnapshot == 1);
  CHECK(c.readyUntaken == 1);  // frame 3 survives: it is the newest ready slot

  // Frame 4 is gone and frame 5 is still alive, so it can still complete.
  FeedAllImages(store, 5, 4500);
  CHECK(store.Counters().readyComplete == 2);
  FrameHandle handle = store.TakeNewestReady();
  CHECK(handle.valid() && handle.frame() == 5);
  if (handle.valid()) {
    CHECK(handle.view().allPresent());
    store.Release(handle);
  }
}

void TestReadySlotEvictedIsSkipped() {
  SinkLog log;
  FrameStore store(MakeConfig(2, 95'000'000, &log));
  for (std::uint64_t frame = 0; frame <= 1; ++frame) {
    CHECK(store.OnSnapshot(frame, MakeSnapshot(frame), 1000));
    FeedAllImages(store, frame, 1500);
  }
  CHECK(store.Counters().readyComplete == 2);
  CHECK(store.OnSnapshot(2, MakeSnapshot(2), 2000));
  CountersSnapshot c = store.Counters();
  CHECK(c.skipped == 1);  // frame 0 was ready and never taken
  CHECK(c.droppedIncomplete == 0);
  CHECK(c.readyUntaken == 1);  // frame 1, the protected newest
  CHECK(c.inFlightSnapshot == 1);
  CheckAccounting(c, 0, "ready-evicted");
}

void TestOverflowWhenNothingEvictable() {
  SinkLog log;
  FrameStore store(MakeConfig(2, 95'000'000, &log));
  CHECK(store.OnSnapshot(0, MakeSnapshot(0), 1000));
  FeedAllImages(store, 0, 1500);
  FrameHandle locked = store.TakeNewestReady();
  CHECK(locked.valid() && locked.frame() == 0);

  // Slot 0 locked, slot 1 becomes the protected newest ready slot.
  CHECK(store.OnSnapshot(1, MakeSnapshot(1), 2000));
  FeedAllImages(store, 1, 2500);
  CHECK(store.Counters().readyUntaken == 1);

  // Frame 2 can take neither slot: overflow, and nothing is overwritten.
  CHECK(!store.OnSnapshot(2, MakeSnapshot(2), 3000));
  CHECK(!FeedImage(store, kFront, 2, 3100));
  CountersSnapshot c = store.Counters();
  CHECK(c.overflow == 2);
  CHECK(c.overflowSnapshots == 1);
  CHECK(c.overflowImages == 1);
  CHECK(c.readyComplete == 2);
  CHECK(c.inFlightSnapshot == 0);  // frame 2 was never stored
  CHECK(c.locked == 1);

  // The locked slot still shows the frame it was taken with.
  CHECK(locked.view().frame == 0);
  CHECK(locked.view().allPresent());
  store.Release(locked);
  FrameHandle next = store.TakeNewestReady();
  CHECK(next.valid() && next.frame() == 1);
  if (next.valid()) store.Release(next);
  CheckAccounting(store.Counters(), 2, "overflow");
}

void TestTakeRetiresOlderSlots() {
  SinkLog log;
  FrameStore store(MakeConfig(4, 95'000'000, &log));
  CHECK(FeedImage(store, kFront, 9, 500));              // images only: frame 9
  CHECK(store.OnSnapshot(8, MakeSnapshot(8), 600));     // snapshot only: frame 8
  CHECK(store.OnSnapshot(10, MakeSnapshot(10), 1000));
  FeedAllImages(store, 10, 1500);
  CHECK(store.OnSnapshot(12, MakeSnapshot(12), 3000));  // newer than the taken frame

  FrameHandle handle = store.TakeNewestReady();
  CHECK(handle.valid() && handle.frame() == 10);
  CountersSnapshot c = store.Counters();
  CHECK(c.droppedIncomplete == 2);           // frames 8 and 9, filled and superseded
  CHECK(c.droppedIncompleteSnapshot == 1);   // only frame 8 had its snapshot
  CHECK(c.skipped == 0);
  CHECK(c.inFlightSnapshot == 1);            // frame 12 survived: newer than 10
  if (handle.valid()) store.Release(handle);

  // The retired frames cannot be resurrected by a late snapshot or image.
  CHECK(!store.OnSnapshot(9, MakeSnapshot(9), 4000));
  CHECK(!FeedImage(store, kFront, 9, 4100));
  c = store.Counters();
  CHECK(c.lateSnapshots == 1);
  CHECK(c.lateImages[kFront] == 1);
  CheckAccounting(c, 1, "take-retires");

  // The sequence of frames handed to the consumer only increases.
  CHECK(store.PollDeadlines(10'000'000'000LL) == 1);  // frame 12 at its deadline
  FrameHandle next = store.TakeNewestReady();
  CHECK(next.valid());
  if (next.valid()) {
    CHECK(next.frame() == 12);
    store.Release(next);
  }
}

void TestMisuse() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  CHECK(store.OnSnapshot(9, MakeSnapshot(9), 1000));
  FeedAllImages(store, 9, 1500);

  FrameHandle first = store.TakeNewestReady();
  CHECK(first.valid());
  FrameHandle second = store.TakeNewestReady();
  CHECK(!second.valid());
  CHECK(store.Counters().misuse == 1);
  CHECK(store.Counters().locked == 1);  // the first handle still owns the slot

  // Even with another ready slot available, a second Take is refused.
  CHECK(store.OnSnapshot(10, MakeSnapshot(10), 2000));
  FeedAllImages(store, 10, 2500);
  FrameHandle third = store.TakeNewestReady();
  CHECK(!third.valid());
  CHECK(store.Counters().misuse == 2);
  CHECK(store.Counters().locked == 1);

  store.Release(first);
  CHECK(store.Counters().misuse == 2);
  store.Release(first);  // an invalidated handle
  CHECK(store.Counters().misuse == 3);
  FrameHandle empty;
  store.Release(empty);
  CHECK(store.Counters().misuse == 4);

  CHECK(!store.OnImage(kCameraCount, 11, nullptr, 0, kWidth, kHeight, 90.0, 0));
  CHECK(store.Counters().misuse == 5);
  CHECK(store.Counters().locked == 0);
}

void TestSinkCalledExactlyOncePerSlot() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  CHECK(store.OnSnapshot(0, MakeSnapshot(0), 1000));
  FeedAllImages(store, 0, 1500);
  CHECK(log.Count() == 1);
  CHECK(store.PollDeadlines(10'000'000'000LL) == 0);
  CHECK(log.Count() == 1);

  CHECK(store.OnSnapshot(1, MakeSnapshot(1), 2000));  // deadline path
  CHECK(store.PollDeadlines(2000 + 95'000'000) == 1);
  CHECK(log.Count() == 2);
  CHECK(store.PollDeadlines(20'000'000'000LL) == 0);
  CHECK(log.Count() == 2);

  const CountersSnapshot c = store.Counters();
  CHECK(c.sinkInvocations == 2);
  CHECK(c.sinkInvocations == c.readyComplete + c.readyDeadline);
  CHECK(c.readyComplete == 1 && c.readyDeadline == 1);
  (void)store.TakeNewestReady();
}

void TestRetiredFrameDataIsLate() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  CHECK(store.OnSnapshot(3, MakeSnapshot(3), 1000));
  FeedAllImages(store, 3, 1500);
  FrameHandle handle = store.TakeNewestReady();
  CHECK(handle.valid());
  if (handle.valid()) store.Release(handle);

  CHECK(!FeedImage(store, kFront, 3, 2000));
  CHECK(!store.OnSnapshot(3, MakeSnapshot(3), 2100));
  CountersSnapshot c = store.Counters();
  CHECK(c.lateImages[kFront] == 1);
  CHECK(c.lateSnapshots == 1);
  CHECK(c.inFlightNoSnapshot == 0);
  CHECK(c.slotsCreated == 1);  // no slot was resurrected for a retired frame
  CheckAccounting(c, 1, "retired");
}

void TestDuplicateSnapshotAndImage() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  CHECK(store.OnSnapshot(9, MakeSnapshot(9), 1000));
  CHECK(!store.OnSnapshot(9, MakeSnapshot(9), 5000));
  CountersSnapshot c = store.Counters();
  CHECK(c.duplicateSnapshots == 1);
  CHECK(c.snapshots == 1);

  CHECK(FeedImage(store, kFront, 9, 1100));
  const std::vector<std::uint8_t> other = ImageBytes(kFront, 9, kImageBytes);
  std::vector<std::uint8_t> overwrite(kImageBytes, 0xAB);
  CHECK(!store.OnImage(kFront, 9, overwrite.data(), overwrite.size(), kWidth, kHeight, 90.0,
                       1200));
  CHECK(store.Counters().lateImages[kFront] == 1);

  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    if (camera == kFront) continue;
    CHECK(FeedImage(store, camera, 9, 1300));
  }
  FrameHandle handle = store.TakeNewestReady();
  CHECK(handle.valid());
  if (!handle.valid()) return;
  CHECK(Fnv1a(handle.view().cameras[kFront].data, kImageBytes) ==
        Fnv1a(other.data(), kImageBytes));  // the first image survived
  CHECK(handle.view().deadlineMonoNs == 1000 + 95'000'000);
  store.Release(handle);
  CheckAccounting(store.Counters(), 1, "duplicates");
}

void TestInvalidConfiguration() {
  FrameStoreConfig config = MakeConfig(1);
  bool threw = false;
  try {
    FrameStore store(config);
  } catch (const std::invalid_argument&) {
    threw = true;
  }
  CHECK(threw);

  FrameStoreConfig zero_camera = MakeConfig(8);
  zero_camera.cameras[3].width = 0;
  threw = false;
  try {
    FrameStore store(zero_camera);
  } catch (const std::invalid_argument&) {
    threw = true;
  }
  CHECK(threw);

  FrameStoreConfig zero_deadline = MakeConfig(8, 0);
  threw = false;
  try {
    FrameStore store(zero_deadline);
  } catch (const std::invalid_argument&) {
    threw = true;
  }
  CHECK(threw);
}

// ---------------------------------------------------------------- pace datagram

std::string SocketPath(const char* tag) {
  return std::string("pace_") + tag + "_" + std::to_string(static_cast<long>(::getpid())) +
         ".sock";
}

int BindReceiver(const std::string& path) {
  ::unlink(path.c_str());
  const int fd = ::socket(AF_UNIX, SOCK_DGRAM, 0);
  if (fd < 0) return -1;
  sockaddr_un address{};
  address.sun_family = AF_UNIX;
  std::snprintf(address.sun_path, sizeof address.sun_path, "%s", path.c_str());
  if (::bind(fd, reinterpret_cast<const sockaddr*>(&address), sizeof address) != 0) {
    ::close(fd);
    return -1;
  }
  return fd;
}

std::uint64_t ReceiveLittleEndian(int fd, bool* ok) {
  // Bounded wait: a missing datagram must fail the check, not hang the test.
  pollfd ready{fd, POLLIN, 0};
  if (::poll(&ready, 1, 1000) <= 0) {
    *ok = false;
    return 0;
  }
  std::uint8_t buffer[64];
  const ssize_t read = ::recv(fd, buffer, sizeof buffer, 0);
  *ok = read == 8;
  if (!*ok) return 0;
  std::uint64_t frame = 0;
  for (std::size_t i = 0; i < 8; ++i) {
    frame |= static_cast<std::uint64_t>(buffer[i]) << (8U * i);
  }
  return frame;
}

void TestPaceDatagram() {
  const std::string path = SocketPath("main");
  const int receiver = BindReceiver(path);
  CHECK(receiver >= 0);
  if (receiver < 0) return;

  PaceSignal pace(path);
  CHECK(pace.hasSocket());
  CHECK(pace.socketPath() == path);
  CHECK(pace.sent() == 0);
  CHECK(pace.Send(0x1122334455667788ULL));
  bool ok = false;
  const std::uint64_t received = ReceiveLittleEndian(receiver, &ok);
  CHECK(ok);
  CHECK(received == 0x1122334455667788ULL);
  CHECK(pace.sent() == 1);
  CHECK(pace.failures() == 0);

  CHECK(pace.Send(0));
  const std::uint64_t zero = ReceiveLittleEndian(receiver, &ok);
  CHECK(ok && zero == 0);

  // A datagram to a path nobody bound is counted, not retried, not fatal.
  const std::string absent = SocketPath("absent");
  ::unlink(absent.c_str());
  PaceSignal nobody(absent);
  CHECK(!nobody.Send(7));
  CHECK(nobody.failures() == 1);
  CHECK(nobody.sent() == 0);

  // No path at all: every send fails, nothing blocks.
  const std::string empty_path;
  PaceSignal unset(empty_path);
  CHECK(!unset.Send(1));
  CHECK(unset.failures() == 1);

  // A receiver that never drains must not stall the sender.
  const std::string full = SocketPath("full");
  const int stuck = BindReceiver(full);
  CHECK(stuck >= 0);
  if (stuck >= 0) {
    PaceSignal flood(full);
    const auto start = std::chrono::steady_clock::now();
    constexpr int kAttempts = 20000;
    for (int i = 0; i < kAttempts; ++i) flood.Send(static_cast<std::uint64_t>(i));
    const double seconds =
        std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    CHECK(flood.sent() + flood.failures() == static_cast<std::uint64_t>(kAttempts));
    CHECK(seconds < 2.0);  // non-blocking: the queue filled and the sends returned
    std::printf("PACE flood: %llu sent, %llu failed, %.3f s\n",
                static_cast<unsigned long long>(flood.sent()),
                static_cast<unsigned long long>(flood.failures()), seconds);
    ::close(stuck);
    ::unlink(full.c_str());
  }
  ::close(receiver);
  ::unlink(path.c_str());
}

void TestReadySendsOnePaceDatagram() {
  // The sink is the pace sender: one ready slot, one datagram, nothing else.
  const std::string path = SocketPath("ready");
  const int receiver = BindReceiver(path);
  CHECK(receiver >= 0);
  if (receiver < 0) return;
  PaceSignal pace(path);
  FrameStoreConfig config = MakeConfig(8, 95'000'000, nullptr);
  config.readySink = [&pace](std::uint64_t frame, bool) { pace.Send(frame); };
  FrameStore store(config);

  CHECK(store.OnSnapshot(41, MakeSnapshot(41), 1000));
  bool ok = false;
  CHECK(::recv(receiver, nullptr, 0, MSG_DONTWAIT) < 0);  // nothing before readiness
  FeedAllImages(store, 41, 1500);
  const std::uint64_t frame = ReceiveLittleEndian(receiver, &ok);
  CHECK(ok);
  CHECK(frame == 41);
  CHECK(pace.sent() == 1);
  // A deadline ready slot signals once too, and only once.
  CHECK(store.OnSnapshot(42, MakeSnapshot(42), 2000));
  CHECK(store.PollDeadlines(2000 + 95'000'000) == 1);
  CHECK(ReceiveLittleEndian(receiver, &ok) == 42);
  CHECK(ok);
  CHECK(store.PollDeadlines(20'000'000'000LL) == 0);
  CHECK(pace.Send(7));
  CHECK(pace.sent() == 3);  // 41, 42, and the explicit one
  ::close(receiver);
  ::unlink(path.c_str());
}

void TestPacePayloadCodec() {
  std::uint8_t bytes[8];
  de4sdv::driving::agent::EncodePacePayload(0x0102030405060708ULL, bytes);
  CHECK(bytes[0] == 0x08);
  CHECK(bytes[1] == 0x07);
  CHECK(bytes[6] == 0x02);
  CHECK(bytes[7] == 0x01);
  CHECK(de4sdv::driving::agent::DecodePacePayload(bytes) == 0x0102030405060708ULL);
}

}  // namespace

// Merged frames: a take with `merged` hands the older ready frames over too, oldest first and
// locked, instead of skipping them, so the planner's histories see every frame (REQ-DRIVING-008).
void TestTakeHandsOverMergedFrames() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  for (std::uint64_t frame = 10; frame <= 12; ++frame) {
    CHECK(store.OnSnapshot(frame, MakeSnapshot(frame), static_cast<std::int64_t>(frame) * 1000));
    FeedAllImages(store, frame, static_cast<std::int64_t>(frame) * 1000 + 500);
  }
  std::vector<FrameHandle> merged;
  FrameHandle newest = store.TakeNewestReady(&merged);
  CHECK(newest.valid() && newest.frame() == 12);
  CHECK(merged.size() == 2);
  if (!newest.valid() || merged.size() != 2) return;
  CHECK(merged[0].valid() && merged[0].frame() == 10);
  CHECK(merged[1].valid() && merged[1].frame() == 11);
  CHECK(merged[0].view().snapshot.pose.x == MakeSnapshot(10).pose.x);
  CHECK(merged[1].view().allPresent());
  CountersSnapshot c = store.Counters();
  CHECK(c.merged == 2);
  CHECK(c.skipped == 0);
  CHECK(c.locked == 3);
  CHECK(c.readyUntaken == 0);
  CheckAccounting(c, 1, "merged-locked");

  // One take at a time: none while any of the three slots is locked.
  std::vector<FrameHandle> again;
  FrameHandle second = store.TakeNewestReady(&again);
  CHECK(!second.valid() && again.empty());
  CHECK(store.Counters().misuse == 1);

  // The consumer conditions the merged frames and releases them, then the newest.
  store.Release(merged[0]);
  store.Release(merged[1]);
  CHECK(store.Counters().locked == 1);
  store.Release(newest);
  c = store.Counters();
  CHECK(c.locked == 0);
  CHECK(c.merged == 2 && c.skipped == 0 && c.misuse == 1);
  CheckAccounting(c, 1, "merged-released");

  // A released handle is reset; data for a merged frame is late from then on.
  CHECK(!merged[0].valid());
  CHECK(!FeedImage(store, kFront, 11, 20'000));
  CHECK(store.Counters().lateImages[kFront] == 1);
}

// At most kMaxMerged older ready frames are handed over, the newest of them; older ones are
// skipped as without `merged`.
void TestMergedFramesAreCapped() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  for (std::uint64_t frame = 0; frame <= 6; ++frame) {
    CHECK(store.OnSnapshot(frame, MakeSnapshot(frame), static_cast<std::int64_t>(frame) * 1000 + 1));
    FeedAllImages(store, frame, static_cast<std::int64_t>(frame) * 1000 + 500);
  }
  std::vector<FrameHandle> merged;
  FrameHandle newest = store.TakeNewestReady(&merged);
  CHECK(newest.valid() && newest.frame() == 6);
  CHECK(merged.size() == kMaxMerged);
  for (std::size_t i = 0; i < merged.size(); ++i) {
    CHECK(merged[i].frame() == 6 - kMaxMerged + i);   // 2, 3, 4, 5
  }
  CountersSnapshot c = store.Counters();
  CHECK(c.merged == kMaxMerged);
  CHECK(c.skipped == 7 - 1 - kMaxMerged);             // frames 0 and 1
  for (FrameHandle& m : merged) store.Release(m);
  if (newest.valid()) store.Release(newest);
  CHECK(store.Counters().locked == 0);
  CheckAccounting(store.Counters(), 1, "merged-capped");
}

// An older frame still filling is dropped as incomplete, never handed over.
void TestMergedSkipsFillingFrames() {
  SinkLog log;
  FrameStore store(MakeConfig(8, 95'000'000, &log));
  CHECK(store.OnSnapshot(10, MakeSnapshot(10), 1000));
  FeedAllImages(store, 10, 1500);
  CHECK(store.OnSnapshot(11, MakeSnapshot(11), 2000));   // no images: filling
  CHECK(store.OnSnapshot(12, MakeSnapshot(12), 3000));
  FeedAllImages(store, 12, 3500);
  std::vector<FrameHandle> merged;
  FrameHandle newest = store.TakeNewestReady(&merged);
  CHECK(newest.valid() && newest.frame() == 12);
  CHECK(merged.size() == 1 && merged[0].frame() == 10);
  CountersSnapshot c = store.Counters();
  CHECK(c.droppedIncomplete == 1);
  CHECK(c.merged == 1 && c.skipped == 0);
  for (FrameHandle& m : merged) store.Release(m);
  if (newest.valid()) store.Release(newest);
  CheckAccounting(store.Counters(), 1, "merged-filling");
}

int main() {
  std::printf("FRAME_STORE_TESTS start\n");

  TestConfigDefaults();
  TestCompleteSlot();
  TestDeadlineSlot();
  TestImageBeforeSnapshot();
  TestImageOnlyFrameAgesOutByEviction();
  TestInvalidSizeImage();
  TestLateImageAfterReady();
  TestNewestReadySelectionAndSkips();
  TestEvictionCounters();
  TestEvictionPicksOldest();
  TestReadySlotEvictedIsSkipped();
  TestOverflowWhenNothingEvictable();
  TestTakeRetiresOlderSlots();
  TestTakeHandsOverMergedFrames();
  TestMergedFramesAreCapped();
  TestMergedSkipsFillingFrames();
  TestMisuse();
  TestSinkCalledExactlyOncePerSlot();
  TestSnapshotSinkPerAcceptedSnapshot();
  TestSnapshotSinkBeforeReadySink();
  TestRetiredFrameDataIsLate();
  TestDuplicateSnapshotAndImage();
  TestInvalidConfiguration();
  TestPaceDatagram();
  TestReadySendsOnePaceDatagram();
  TestPacePayloadCodec();

  std::printf("FRAME_STORE_TESTS %s: %d checks, %d failures\n",
              g_failures == 0 ? "PASS" : "FAIL", g_checks, g_failures);
  return g_failures == 0 ? 0 : 1;
}
