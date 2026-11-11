// DE4SDV INC-DRIVING-001 slice 10b: the driving agent's frame store.
//
// One ring of preallocated slots keyed by the simulator (CARLA world) frame
// number. LibCarla calls OnSnapshot once per world tick and OnImage once per
// camera frame from its own callback threads; the input activity takes the
// newest ready slot and locks it until the plan is out.
//
// A slot is ready when its snapshot and all six images are present, or, if a
// camera is missing or late, at 95 ms of monotonic time after its snapshot
// arrived (DESIGN.md "Frame store", REQ-DRIVING-023). A ready slot is
// signalled once through ReadySink, outside the store's lock; the sink sends
// the pace datagram.
//
// Namespace: de4sdv::driving::agent. No dependency on the repository headers (rig.h is the
// agent's own camera count):
// the consumer converts CaptureTimeMicros(frame) itself and adapts the
// snapshot to the payload structs, so this unit builds standalone.
#pragma once

#include "rig.h"

#include <array>
#include <atomic>
#include <cstddef>
#include <cstdint>
#include <functional>
#include <mutex>
#include <vector>

namespace de4sdv::driving::agent {

// kCameraCount: rig.h
inline constexpr std::size_t kMaxRingSize = 64;      // ReadySink batch bound
inline constexpr std::int64_t kDefaultDeadlineNs = 95'000'000;  // 95 ms
// The most older ready frames one take hands over as merged (DESIGN.md "Merged frames").
inline constexpr std::size_t kMaxMerged = 4;

// Index order fixed by the brief. CameraName gives the name the agent's records use: the checkpoint's
// slot name (C2, ICD A25). The CARLA actors are found by their role names (`cam_front`, ...;
// carla_source.h), the names the world-side rig gives them (DESIGN.md "conditionInputs / startup").
enum CameraIndex : std::size_t {
  kFront = 0,
  kFrontLeft = 1,
  kFrontRight = 2,
  kRearLeft = 3,
  kRear = 4,
  kRearRight = 5,
};

const char* CameraName(std::size_t camera);

struct Pose {
  double x = 0.0;
  double y = 0.0;
  double z = 0.0;
  double roll = 0.0;
  double pitch = 0.0;
  double yaw = 0.0;
};

struct Vector3 {
  double x = 0.0;
  double y = 0.0;
  double z = 0.0;
};

// The hero's snapshot of one world frame: POD, copied by value.
struct HeroSnapshot {
  Pose pose;
  Vector3 velocity;          // m/s, vehicle frame
  Vector3 acceleration;      // m/s^2, vehicle frame
  Vector3 angularVelocity;   // rad/s, CARLA world axes
};

struct CameraConfig {
  int width = 0;
  int height = 0;
};

// Called exactly once for every slot that becomes ready, outside the store's
// lock, with the frame number and whether the deadline (not completeness)
// made it ready. It must not call back into the store.
using ReadySink = std::function<void(std::uint64_t frame, bool readyByDeadline)>;
// Called once per accepted snapshot (not for a duplicate, late or overflowing one), after the
// store's lock is released and before the ready sink of a step the snapshot completes, on the
// LibCarla tick thread: it must return quickly. The agent uses it to render the step's navigation
// raster while the camera images are still arriving.
using SnapshotSink =
    std::function<void(std::uint64_t frame, const HeroSnapshot& snapshot, std::int64_t arrivalMonoNs)>;

struct FrameStoreConfig {
  CameraConfig cameras[kCameraCount];   // expected width/height, BGRA
  std::size_t ringSize = 8;
  std::int64_t deadlineNs = kDefaultDeadlineNs;
  ReadySink readySink;                  // may be empty
  SnapshotSink snapshotSink;            // may be empty
};

// Read-only view of one camera image in a taken slot.
struct CameraView {
  bool present = false;        // an image arrived for this camera and frame
  bool valid = false;          // size/width/height matched the expectation
  std::uint64_t imageFrame = 0;
  int width = 0;               // as reported by the callback
  int height = 0;
  double fov = 0.0;
  std::int64_t arrivalMonoNs = 0;
  const std::uint8_t* data = nullptr;  // the slot's preallocated buffer
  std::size_t size = 0;                // bytes copied and readable (0 when absent)

  bool missing() const { return !present; }
};

// Read-only view of one taken slot. The pointers stay valid until Release;
// after Release the slot may be reused for another frame.
struct FrameView {
  std::uint64_t frame = 0;
  HeroSnapshot snapshot;
  std::int64_t snapshotArrivalMonoNs = 0;
  std::int64_t deadlineMonoNs = 0;
  bool readyByDeadline = false;
  CameraView cameras[kCameraCount];

  bool allPresent() const {
    for (const CameraView& camera : cameras) {
      if (!camera.present) return false;
    }
    return true;
  }
  std::size_t missingCount() const {
    std::size_t count = 0;
    for (const CameraView& camera : cameras) {
      if (!camera.present) ++count;
    }
    return count;
  }
};

class FrameStore;

// A locked slot. Copyable and movable (cheap). The store admits one Take until
// every slot it locked (the newest and its merged slots) is released.
class FrameHandle {
 public:
  FrameHandle() = default;
  bool valid() const { return store_ != nullptr; }
  const FrameView& view() const { return view_; }
  std::uint64_t frame() const { return view_.frame; }

 private:
  friend class FrameStore;
  FrameHandle(FrameStore* store, std::size_t slot, FrameView view)
      : store_(store), slot_(slot), view_(view) {}
  void Reset() {
    store_ = nullptr;
    slot_ = static_cast<std::size_t>(-1);
    view_ = FrameView{};
  }
  FrameStore* store_ = nullptr;
  std::size_t slot_ = static_cast<std::size_t>(-1);
  FrameView view_;
};

// Counters, read atomically under the lock. The first block is the ICD set;
// the second block exists for the accounting identity and for the tests.
struct CountersSnapshot {
  // ICD / brief set.
  std::uint64_t readyComplete = 0;
  std::uint64_t readyDeadline = 0;
  std::uint64_t skipped = 0;
  std::uint64_t merged = 0;   // older ready slots handed over with a newer one
  std::uint64_t droppedIncomplete = 0;
  std::uint64_t lateImages[kCameraCount] = {};
  std::uint64_t overflow = 0;
  std::uint64_t misuse = 0;

  // Accounting detail.
  std::uint64_t snapshots = 0;                 // frames whose first snapshot was accepted
  std::uint64_t slotsCreated = 0;              // slots ever allocated to a frame
  std::uint64_t droppedIncompleteSnapshot = 0;  // subset of droppedIncomplete with a snapshot
  std::uint64_t overflowSnapshots = 0;         // subset of overflow from OnSnapshot
  std::uint64_t overflowImages = 0;            // subset of overflow from OnImage
  std::uint64_t lateSnapshots = 0;             // snapshot for an already retired frame
  std::uint64_t duplicateSnapshots = 0;        // second snapshot for a live frame
  std::uint64_t sinkInvocations = 0;           // ready notifications delivered
  std::size_t inFlightSnapshot = 0;            // filling slots holding a snapshot
  std::size_t inFlightNoSnapshot = 0;          // filling slots holding images only
  std::size_t readyUntaken = 0;                // ready slots not taken and not locked
  std::size_t locked = 0;                      // 0 .. 1 + kMaxMerged
};

class FrameStore {
 public:
  explicit FrameStore(const FrameStoreConfig& config);
  FrameStore(const FrameStore&) = delete;
  FrameStore& operator=(const FrameStore&) = delete;

  // LibCarla world tick. Returns true when the snapshot was accepted.
  bool OnSnapshot(std::uint64_t frame, const HeroSnapshot& snapshot,
                  std::int64_t arrivalMonoNs);

  // LibCarla camera callback. `camera` is a CameraIndex. The bytes are copied;
  // the caller keeps ownership of `data`. Returns true when the image was
  // stored (present), false when it was dropped as late, duplicate or overflow.
  bool OnImage(std::size_t camera, std::uint64_t imageFrame, const std::uint8_t* data,
               std::size_t size, int width, int height, double fov,
               std::int64_t arrivalMonoNs);

  // Owner-driven deadline sweep (the orchestrator's 5 ms timer). Marks every
  // filling slot whose snapshot deadline has passed ready, returns how many.
  std::size_t PollDeadlines(std::int64_t nowMonoNs);

  // Newest ready, untaken slot; locks it. With `merged`, the older ready untaken
  // slots, at most kMaxMerged (the newest of them), are locked too and appended
  // oldest first: the consumer conditions them into its histories and releases
  // each. Without `merged`, and beyond the cap, older ready untaken slots are
  // counted as skipped and released. Older filling slots are dropped as
  // incomplete. Returns an invalid handle when nothing is ready, and an invalid
  // handle plus one `misuse` when a slot is still locked.
  FrameHandle TakeNewestReady(std::vector<FrameHandle>* merged = nullptr);

  // Unlocks and frees the slot. Counts `misuse` and ignores the call when the
  // handle is not a locked one.
  void Release(FrameHandle& handle);

  CountersSnapshot Counters() const;

  const FrameStoreConfig& config() const { return config_; }
  std::size_t ringSize() const { return slots_.size(); }
  std::size_t bytesPerSlot() const { return slotStride_; }

 private:
  enum class SlotState : std::uint8_t { kEmpty = 0, kFilling = 1, kReady = 2 };

  struct SlotCamera {
    bool present = false;
    bool valid = false;
    std::uint64_t imageFrame = 0;
    int width = 0;
    int height = 0;
    double fov = 0.0;
    std::int64_t arrivalMonoNs = 0;
    std::size_t size = 0;   // bytes copied into the slot buffer
  };

  struct Slot {
    SlotState state = SlotState::kEmpty;
    bool hasSnapshot = false;
    bool locked = false;
    bool readyByDeadline = false;
    bool skipCounted = false;  // already accounted as skipped/consumed
    std::uint64_t frame = 0;
    HeroSnapshot snapshot;
    std::int64_t snapshotArrivalNs = 0;
    std::int64_t deadlineNs = 0;
    std::uint8_t presentMask = 0;
    std::uint8_t validMask = 0;
    SlotCamera cameras[kCameraCount];
  };

  struct PendingReady {
    std::uint64_t frame = 0;
    bool byDeadline = false;
  };

  std::size_t FindFrameLocked(std::uint64_t frame) const;
  std::size_t AcquireSlotLocked(std::uint64_t frame);
  std::size_t NewestReadyUntakenLocked() const;
  void MakeReadyLocked(std::size_t index, bool byDeadline, PendingReady* pending,
                       std::size_t& count);
  void RetireLocked(std::size_t index);
  void ResetSlotLocked(std::size_t index);
  void DeliverPending(const PendingReady* pending, std::size_t count);
  FrameView BuildViewLocked(std::size_t index) const;
  std::uint8_t* MutableBuffer(std::size_t slot, std::size_t camera);
  const std::uint8_t* Buffer(std::size_t slot, std::size_t camera) const;

  FrameStoreConfig config_;
  std::array<std::size_t, kCameraCount> cameraOffset_{};
  std::array<std::size_t, kCameraCount> expectedBytes_{};
  std::size_t slotStride_ = 0;
  std::vector<std::uint8_t> buffers_;
  std::vector<Slot> slots_;

  mutable std::mutex mutex_;
  std::size_t lockedCount_ = 0;     // the newest taken slot plus its merged slots
  std::int64_t retiredThrough_ = -1;  // frames at or below this are gone

  std::uint64_t readyComplete_ = 0;
  std::uint64_t readyDeadline_ = 0;
  std::uint64_t skipped_ = 0;
  std::uint64_t merged_ = 0;
  std::uint64_t droppedIncomplete_ = 0;
  std::uint64_t droppedIncompleteSnapshot_ = 0;
  std::uint64_t lateImages_[kCameraCount] = {};
  std::uint64_t overflow_ = 0;
  std::uint64_t overflowSnapshots_ = 0;
  std::uint64_t overflowImages_ = 0;
  std::uint64_t misuse_ = 0;
  std::uint64_t snapshots_ = 0;
  std::uint64_t slotsCreated_ = 0;
  std::uint64_t lateSnapshots_ = 0;
  std::uint64_t duplicateSnapshots_ = 0;
  // Written outside the lock by whichever thread completed or aged the slot.
  std::atomic<std::uint64_t> sinkInvocations_{0};
};

}  // namespace de4sdv::driving::agent
