// Frame store implementation. One mutex; the ReadySink is called after it is
// released. No allocation happens after construction.
#include "frame_store.h"

#include <algorithm>
#include <cstring>
#include <stdexcept>
#include <string>

namespace de4sdv::driving::agent {
namespace {

constexpr std::size_t kNoSlot = static_cast<std::size_t>(-1);
constexpr std::uint8_t kAllCamerasMask = 0x3Fu;  // six bits

std::string CameraLabel(std::size_t camera) {
  return std::to_string(camera);
}

}  // namespace

const char* CameraName(std::size_t camera) {
  static const char* const kNames[kCameraCount] = {
      "cam_front",  "cam_front_left", "cam_front_right",
      "cam_rear_left", "cam_rear",    "cam_rear_right",
  };
  return camera < kCameraCount ? kNames[camera] : "cam_unknown";
}

FrameStore::FrameStore(const FrameStoreConfig& config) : config_(config) {
  if (config_.ringSize < 2 || config_.ringSize > kMaxRingSize) {
    throw std::invalid_argument("FrameStore: ringSize must be in [2, " +
                                std::to_string(kMaxRingSize) + "]");
  }
  if (config_.deadlineNs <= 0) {
    throw std::invalid_argument("FrameStore: deadlineNs must be positive");
  }
  std::size_t offset = 0;
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    const CameraConfig& expectation = config_.cameras[camera];
    if (expectation.width <= 0 || expectation.height <= 0) {
      throw std::invalid_argument("FrameStore: camera " + CameraLabel(camera) +
                                  " has a non-positive expectation");
    }
    cameraOffset_[camera] = offset;
    expectedBytes_[camera] = static_cast<std::size_t>(expectation.width) *
                             static_cast<std::size_t>(expectation.height) * 4U;
    offset += expectedBytes_[camera];
  }
  slotStride_ = offset;
  // Every image buffer exists before the first callback: no allocation and no
  // page fault on the LibCarla threads' first write.
  buffers_.assign(config_.ringSize * slotStride_, 0);
  slots_.resize(config_.ringSize);
  for (std::size_t index = 0; index < slots_.size(); ++index) ResetSlotLocked(index);
}

bool FrameStore::OnSnapshot(std::uint64_t frame, const HeroSnapshot& snapshot,
                            std::int64_t arrivalMonoNs) {
  PendingReady pending[1];
  std::size_t pendingCount = 0;
  bool accepted = false;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    std::size_t index = FindFrameLocked(frame);
    if (index == kNoSlot) {
      if (static_cast<std::int64_t>(frame) <= retiredThrough_) {
        ++lateSnapshots_;
        return false;
      }
      index = AcquireSlotLocked(frame);
      if (index == kNoSlot) {
        ++overflow_;
        ++overflowSnapshots_;
        return false;
      }
    }
    Slot& slot = slots_[index];
    if (slot.state == SlotState::kReady || slot.hasSnapshot) {
      // Never touch a ready slot; a second snapshot for one frame is noise.
      ++duplicateSnapshots_;
      return false;
    }
    slot.hasSnapshot = true;
    slot.snapshot = snapshot;
    slot.snapshotArrivalNs = arrivalMonoNs;
    slot.deadlineNs = arrivalMonoNs + config_.deadlineNs;
    ++snapshots_;
    accepted = true;
    if (slot.presentMask == kAllCamerasMask) {
      MakeReadyLocked(index, false, pending, pendingCount);
    }
  }
  DeliverPending(pending, pendingCount);
  return accepted;
}

bool FrameStore::OnImage(std::size_t camera, std::uint64_t imageFrame,
                         const std::uint8_t* data, std::size_t size, int width,
                         int height, double fov, std::int64_t arrivalMonoNs) {
  if (camera >= kCameraCount) {
    std::lock_guard<std::mutex> lock(mutex_);
    ++misuse_;
    return false;
  }
  PendingReady pending[1];
  std::size_t pendingCount = 0;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    std::size_t index = FindFrameLocked(imageFrame);
    if (index == kNoSlot) {
      if (static_cast<std::int64_t>(imageFrame) <= retiredThrough_) {
        ++lateImages_[camera];
        return false;
      }
      index = AcquireSlotLocked(imageFrame);
      if (index == kNoSlot) {
        ++overflow_;
        ++overflowImages_;
        return false;
      }
    }
    Slot& slot = slots_[index];
    const std::uint8_t bit = static_cast<std::uint8_t>(1U << camera);
    if (slot.state == SlotState::kReady || (slot.presentMask & bit) != 0U) {
      // A ready slot is immutable, and one image per camera per frame is all
      // the ring holds: both are late arrivals.
      ++lateImages_[camera];
      return false;
    }

    const std::size_t expected = expectedBytes_[camera];
    const std::size_t copyBytes =
        data == nullptr ? 0U : std::min(size, expected);  // never past the buffer
    if (copyBytes != 0U) std::memcpy(MutableBuffer(index, camera), data, copyBytes);

    SlotCamera& view = slot.cameras[camera];
    view.present = true;
    view.imageFrame = imageFrame;
    view.width = width;
    view.height = height;
    view.fov = fov;
    view.arrivalMonoNs = arrivalMonoNs;
    view.size = copyBytes;
    view.valid = data != nullptr && size == expected &&
                 width == config_.cameras[camera].width &&
                 height == config_.cameras[camera].height;
    slot.presentMask |= bit;
    if (view.valid) slot.validMask |= bit;

    if (slot.hasSnapshot && slot.presentMask == kAllCamerasMask) {
      MakeReadyLocked(index, false, pending, pendingCount);
    }
  }
  DeliverPending(pending, pendingCount);
  return true;
}

std::size_t FrameStore::PollDeadlines(std::int64_t nowMonoNs) {
  PendingReady pending[kMaxRingSize];
  std::size_t pendingCount = 0;
  std::size_t madeReady = 0;
  {
    std::lock_guard<std::mutex> lock(mutex_);
    for (std::size_t index = 0; index < slots_.size(); ++index) {
      Slot& slot = slots_[index];
      if (slot.state != SlotState::kFilling || !slot.hasSnapshot) continue;
      if (nowMonoNs < slot.deadlineNs) continue;
      MakeReadyLocked(index, true, pending, pendingCount);
      ++madeReady;
    }
  }
  DeliverPending(pending, pendingCount);
  return madeReady;
}

FrameHandle FrameStore::TakeNewestReady(std::vector<FrameHandle>* merged) {
  FrameHandle handle;
  std::lock_guard<std::mutex> lock(mutex_);
  if (lockedCount_ != 0) {
    ++misuse_;  // one take at a time: the caller forgot a Release
    return handle;
  }
  const std::size_t newest = NewestReadyUntakenLocked();
  if (newest == kNoSlot) return handle;
  const std::uint64_t newestFrame = slots_[newest].frame;

  // Merged frames: when the caller asks, the newest older ready untaken slots (at most kMaxMerged)
  // are handed over with the newest one, so the consumer's histories see every frame.
  std::size_t mergedSlots[kMaxMerged];
  std::size_t mergedCount = 0;
  auto isMerged = [&](std::size_t index) {
    for (std::size_t m = 0; m < mergedCount; ++m) {
      if (mergedSlots[m] == index) return true;
    }
    return false;
  };
  if (merged != nullptr) {
    while (mergedCount < kMaxMerged) {
      std::size_t pick = kNoSlot;
      for (std::size_t index = 0; index < slots_.size(); ++index) {
        const Slot& slot = slots_[index];
        if (index == newest || slot.state != SlotState::kReady || slot.locked ||
            slot.frame >= newestFrame || isMerged(index)) {
          continue;
        }
        if (pick == kNoSlot || slot.frame > slots_[pick].frame) pick = index;
      }
      if (pick == kNoSlot) break;
      mergedSlots[mergedCount++] = pick;
    }
  }

  // Everything else older than the newest frame the consumer gets is superseded: a ready one is
  // counted as skipped, a filling one as dropped incomplete. Retiring them, and raising the retire
  // floor to the taken frame, is what makes the sequence of handed-over frames strictly
  // increasing (merged ones are older than the newest and newer than the previous take).
  for (std::size_t index = 0; index < slots_.size(); ++index) {
    if (index == newest || isMerged(index)) continue;
    const Slot& slot = slots_[index];
    if (slot.state == SlotState::kEmpty || slot.locked || slot.frame >= newestFrame) continue;
    RetireLocked(index);
  }
  if (static_cast<std::int64_t>(newestFrame) > retiredThrough_) {
    retiredThrough_ = static_cast<std::int64_t>(newestFrame);
  }

  std::sort(mergedSlots, mergedSlots + mergedCount,
            [this](std::size_t a, std::size_t b) { return slots_[a].frame < slots_[b].frame; });
  for (std::size_t m = 0; m < mergedCount; ++m) {
    slots_[mergedSlots[m]].locked = true;
    ++merged_;
    merged->push_back(FrameHandle(this, mergedSlots[m], BuildViewLocked(mergedSlots[m])));
  }
  slots_[newest].locked = true;
  lockedCount_ = 1 + mergedCount;
  handle = FrameHandle(this, newest, BuildViewLocked(newest));
  return handle;
}

void FrameStore::Release(FrameHandle& handle) {
  std::lock_guard<std::mutex> lock(mutex_);
  if (!handle.valid() || handle.store_ != this) {
    ++misuse_;
    handle.Reset();
    return;
  }
  const std::size_t index = handle.slot_;
  if (index >= slots_.size() || !slots_[index].locked ||
      slots_[index].state != SlotState::kReady ||
      slots_[index].frame != handle.view_.frame) {
    ++misuse_;
    handle.Reset();
    return;
  }
  slots_[index].locked = false;
  slots_[index].skipCounted = true;  // consumed (taken or merged), not skipped
  RetireLocked(index);
  if (lockedCount_ > 0) --lockedCount_;
  handle.Reset();
}

CountersSnapshot FrameStore::Counters() const {
  std::lock_guard<std::mutex> lock(mutex_);
  CountersSnapshot counters;
  counters.readyComplete = readyComplete_;
  counters.readyDeadline = readyDeadline_;
  counters.skipped = skipped_;
  counters.merged = merged_;
  counters.droppedIncomplete = droppedIncomplete_;
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    counters.lateImages[camera] = lateImages_[camera];
  }
  counters.overflow = overflow_;
  counters.misuse = misuse_;
  counters.snapshots = snapshots_;
  counters.slotsCreated = slotsCreated_;
  counters.droppedIncompleteSnapshot = droppedIncompleteSnapshot_;
  counters.overflowSnapshots = overflowSnapshots_;
  counters.overflowImages = overflowImages_;
  counters.lateSnapshots = lateSnapshots_;
  counters.duplicateSnapshots = duplicateSnapshots_;
  counters.sinkInvocations = sinkInvocations_.load(std::memory_order_relaxed);
  counters.inFlightSnapshot = 0;
  counters.inFlightNoSnapshot = 0;
  counters.readyUntaken = 0;
  counters.locked = 0;
  for (const Slot& slot : slots_) {
    if (slot.state == SlotState::kFilling) {
      if (slot.hasSnapshot) {
        ++counters.inFlightSnapshot;
      } else {
        ++counters.inFlightNoSnapshot;
      }
    } else if (slot.state == SlotState::kReady) {
      if (slot.locked) {
        ++counters.locked;
      } else {
        ++counters.readyUntaken;
      }
    }
  }
  return counters;
}

std::size_t FrameStore::FindFrameLocked(std::uint64_t frame) const {
  for (std::size_t index = 0; index < slots_.size(); ++index) {
    if (slots_[index].state != SlotState::kEmpty && slots_[index].frame == frame) {
      return index;
    }
  }
  return kNoSlot;
}

std::size_t FrameStore::AcquireSlotLocked(std::uint64_t frame) {
  for (std::size_t index = 0; index < slots_.size(); ++index) {
    if (slots_[index].state == SlotState::kEmpty) {
      ResetSlotLocked(index);
      slots_[index].state = SlotState::kFilling;
      slots_[index].frame = frame;
      ++slotsCreated_;
      return index;
    }
  }
  // Every slot holds a frame: evict the oldest one that is neither locked nor
  // the newest ready unconsumed slot (that one is the consumer's next take).
  const std::size_t protectedSlot = NewestReadyUntakenLocked();
  std::size_t oldest = kNoSlot;
  for (std::size_t index = 0; index < slots_.size(); ++index) {
    const Slot& slot = slots_[index];
    if (slot.locked || index == protectedSlot) continue;
    if (oldest == kNoSlot || slot.frame < slots_[oldest].frame) oldest = index;
  }
  if (oldest == kNoSlot) return kNoSlot;  // nothing evictable: overflow

  RetireLocked(oldest);
  slots_[oldest].state = SlotState::kFilling;
  slots_[oldest].frame = frame;
  ++slotsCreated_;
  return oldest;
}

std::size_t FrameStore::NewestReadyUntakenLocked() const {
  std::size_t newest = kNoSlot;
  for (std::size_t index = 0; index < slots_.size(); ++index) {
    const Slot& slot = slots_[index];
    if (slot.state != SlotState::kReady || slot.locked) continue;
    if (newest == kNoSlot || slot.frame > slots_[newest].frame) newest = index;
  }
  return newest;
}

void FrameStore::MakeReadyLocked(std::size_t index, bool byDeadline,
                                 PendingReady* pending, std::size_t& count) {
  Slot& slot = slots_[index];
  slot.state = SlotState::kReady;
  slot.readyByDeadline = byDeadline;
  if (byDeadline) {
    ++readyDeadline_;
  } else {
    ++readyComplete_;
  }
  pending[count].frame = slot.frame;
  pending[count].byDeadline = byDeadline;
  ++count;
}

void FrameStore::RetireLocked(std::size_t index) {
  Slot& slot = slots_[index];
  if (slot.state == SlotState::kReady) {
    if (!slot.skipCounted) {
      ++skipped_;
      slot.skipCounted = true;
    }
  } else if (slot.state == SlotState::kFilling) {
    ++droppedIncomplete_;
    if (slot.hasSnapshot) ++droppedIncompleteSnapshot_;
  }
  if (slot.state != SlotState::kEmpty &&
      static_cast<std::int64_t>(slot.frame) > retiredThrough_) {
    retiredThrough_ = static_cast<std::int64_t>(slot.frame);
  }
  ResetSlotLocked(index);
}

void FrameStore::ResetSlotLocked(std::size_t index) {
  Slot& slot = slots_[index];
  slot.state = SlotState::kEmpty;
  slot.hasSnapshot = false;
  slot.locked = false;
  slot.readyByDeadline = false;
  slot.skipCounted = false;
  slot.frame = 0;
  slot.snapshot = HeroSnapshot{};
  slot.snapshotArrivalNs = 0;
  slot.deadlineNs = 0;
  slot.presentMask = 0;
  slot.validMask = 0;
  for (SlotCamera& camera : slot.cameras) camera = SlotCamera{};
}

void FrameStore::DeliverPending(const PendingReady* pending, std::size_t count) {
  for (std::size_t i = 0; i < count; ++i) {
    sinkInvocations_.fetch_add(1, std::memory_order_relaxed);
    if (config_.readySink) config_.readySink(pending[i].frame, pending[i].byDeadline);
  }
}

FrameView FrameStore::BuildViewLocked(std::size_t index) const {
  const Slot& slot = slots_[index];
  FrameView view;
  view.frame = slot.frame;
  view.snapshot = slot.snapshot;
  view.snapshotArrivalMonoNs = slot.snapshotArrivalNs;
  view.deadlineMonoNs = slot.deadlineNs;
  view.readyByDeadline = slot.readyByDeadline;
  for (std::size_t camera = 0; camera < kCameraCount; ++camera) {
    const SlotCamera& stored = slot.cameras[camera];
    CameraView& out = view.cameras[camera];
    out.present = stored.present;
    out.valid = stored.valid;
    out.imageFrame = stored.imageFrame;
    out.width = stored.width;
    out.height = stored.height;
    out.fov = stored.fov;
    out.arrivalMonoNs = stored.arrivalMonoNs;
    out.data = Buffer(index, camera);
    out.size = stored.size;
  }
  return view;
}

std::uint8_t* FrameStore::MutableBuffer(std::size_t slot, std::size_t camera) {
  return buffers_.data() + slot * slotStride_ + cameraOffset_[camera];
}

const std::uint8_t* FrameStore::Buffer(std::size_t slot, std::size_t camera) const {
  return buffers_.data() + slot * slotStride_ + cameraOffset_[camera];
}

}  // namespace de4sdv::driving::agent
