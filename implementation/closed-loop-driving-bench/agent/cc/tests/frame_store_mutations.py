#!/usr/bin/env python3
"""Single-point mutation probes for the driving agent's frame store.

Each entry replaces exactly one source fragment, rebuilds the unit and stress
tests, and reports whether a test caught it. The sources are restored after
every probe; the script exits non-zero if any mutation survives.

    python3 tests/frame_store_mutations.py

(`tests/run_tests.sh --mutations` runs it and writes its output to
`.build/frame_store_mutations.log`.) It prints one table row per mutation: the
rule of frame_store.md it breaks, the result and the tests that killed it
(`mutation_report.py`): the unit test's, or the stress test's when the unit
test passes.
"""
import hashlib
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mutation_report import killed_by, print_table  # noqa: E402

# The unit lives in agent/cc/; this script and the tests in agent/cc/tests/.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.environ.get("FRAME_STORE_MUT_BUILD", os.path.join(ROOT, ".build", "mut"))
STRESS_FRAMES = "800"

CXXFLAGS = ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-pthread", "-I" + ROOT]

MUTATIONS = [
    {
        "name": "M01 deadline 95 ms -> 195 ms",
        "rule": "ready by deadline: the snapshot's arrival + 95 ms",
        "file": "frame_store.h",
        "old": "inline constexpr std::int64_t kDefaultDeadlineNs = 95'000'000;",
        "new": "inline constexpr std::int64_t kDefaultDeadlineNs = 195'000'000;",
    },
    {
        "name": "M02 readiness needs 5 cameras, not 6",
        "rule": "ready by completeness: the snapshot and all six images",
        "file": "frame_store.cpp",
        "old": "    if (slot.hasSnapshot && slot.presentMask == kAllCamerasMask) {",
        "new": "    if (slot.hasSnapshot && (slot.presentMask & 0x1FU) == 0x1FU) {",
    },
    {
        "name": "M03 skip not counted in RetireLocked",
        "rule": "accounting (R): a ready slot retired untaken counts as skipped",
        "file": "frame_store.cpp",
        "old": "    if (!slot.skipCounted) {\n      ++skipped_;\n      slot.skipCounted = true;\n    }",
        "new": "    if (!slot.skipCounted) {\n      slot.skipCounted = true;\n    }",
    },
    {
        "name": "M04 late image may modify a ready slot",
        "rule": "ready slots are immutable",
        "file": "frame_store.cpp",
        "old": "    if (slot.state == SlotState::kReady || (slot.presentMask & bit) != 0U) {",
        "new": "    if ((slot.presentMask & bit) != 0U) {",
    },
    {
        "name": "M05 late_images not incremented for a ready slot",
        "rule": "a late image is dropped and counted",
        "file": "frame_store.cpp",
        "old": "      // the ring holds: both are late arrivals.\n      ++lateImages_[camera];",
        "new": "      // the ring holds: both are late arrivals.",
    },
    {
        "name": "M06 eviction picks the newest, not the oldest",
        "rule": "eviction takes the oldest evictable slot",
        "file": "frame_store.cpp",
        "old": "    if (oldest == kNoSlot || slot.frame < slots_[oldest].frame) oldest = index;",
        "new": "    if (oldest == kNoSlot || slot.frame > slots_[oldest].frame) oldest = index;",
    },
    {
        "name": "M07 newest-ready picks the oldest",
        "rule": "the consumer takes the newest ready slot",
        "file": "frame_store.cpp",
        "old": "    if (newest == kNoSlot || slot.frame > slots_[newest].frame) newest = index;",
        "new": "    if (newest == kNoSlot || slot.frame < slots_[newest].frame) newest = index;",
    },
    {
        "name": "M08 second Take without Release allowed",
        "rule": "one take at a time",
        "file": "frame_store.cpp",
        "old": "  if (lockedCount_ != 0) {\n    ++misuse_;  // one take at a time: the caller forgot a Release\n    return handle;\n  }",
        "new": "  if (lockedCount_ != 0) {\n    ++misuse_;  // one take at a time: the caller forgot a Release\n  }",
    },
    {
        "name": "M09 poll re-marks ready slots",
        "rule": "the ready sink runs once per slot that becomes ready",
        "file": "frame_store.cpp",
        "old": "      if (slot.state != SlotState::kFilling || !slot.hasSnapshot) continue;",
        "new": "      if (slot.state == SlotState::kEmpty || !slot.hasSnapshot) continue;",
    },
    {
        "name": "M10 size validation always valid",
        "rule": "presence, not validity: an image of the wrong size is present and invalid",
        "file": "frame_store.cpp",
        "old": "    view.valid = data != nullptr && size == expected &&",
        "new": "    view.valid = data != nullptr &&",
    },
    {
        "name": "M11 pace payload big-endian",
        "rule": "the pace datagram is the 8-byte little-endian frame number",
        "file": "pace_signal.cpp",
        "old": "    out[i] = static_cast<std::uint8_t>((frame >> (8U * i)) & 0xFFU);",
        "new": "    out[i] = static_cast<std::uint8_t>((frame >> (8U * (7U - i))) & 0xFFU);",
    },
    {
        "name": "M12 deadline fires one nanosecond late",
        "rule": "ready by deadline: now >= deadline fires",
        "file": "frame_store.cpp",
        "old": "      if (nowMonoNs < slot.deadlineNs) continue;",
        "new": "      if (nowMonoNs <= slot.deadlineNs) continue;",
    },
    {
        "name": "M13 overflow not counted",
        "rule": "overflow is counted",
        "file": "frame_store.cpp",
        "old": "      if (index == kNoSlot) {\n        ++overflow_;\n        ++overflowSnapshots_;\n        return false;\n      }",
        "new": "      if (index == kNoSlot) {\n        ++overflowSnapshots_;\n        return false;\n      }",
    },
    {
        "name": "M14 skipCounted guard removed (double count)",
        "rule": "accounting (R): a skipped slot counts once",
        "file": "frame_store.cpp",
        "old": "    if (!slot.skipCounted) {",
        "new": "    if (true) {",
    },
    {
        "name": "M15 a retired frame may be resurrected by an image",
        "rule": "the take raises the retire floor: data for a retired frame is late",
        "file": "frame_store.cpp",
        "old": "      if (static_cast<std::int64_t>(imageFrame) <= retiredThrough_) {",
        "new": "      if (false) {",
    },
    {
        "name": "M16 Take retires only ready slots, not filling ones",
        "rule": "the take retires every older slot, filling ones as dropped_incomplete",
        "file": "frame_store.cpp",
        "old": "    if (slot.state == SlotState::kEmpty || slot.locked || slot.frame >= newestFrame) continue;",
        "new": "    if (slot.state != SlotState::kReady || slot.locked || slot.frame >= newestFrame) continue;",
    },
    # Merged frames (DESIGN.md "Merged frames"): the take hands older ready frames over instead of skipping them.
    {
        "name": "M17 merged frames never handed over",
        "rule": "merged take: the older ready slots are handed over",
        "file": "frame_store.cpp",
        "old": "  if (merged != nullptr) {\n    while (mergedCount < kMaxMerged) {",
        "new": "  if (false) {\n    while (mergedCount < kMaxMerged) {",
    },
    {
        "name": "M18 merged frames handed over newest first",
        "rule": "merged take: oldest first",
        "file": "frame_store.cpp",
        "old": "[this](std::size_t a, std::size_t b) { return slots_[a].frame < slots_[b].frame; });",
        "new": "[this](std::size_t a, std::size_t b) { return slots_[a].frame > slots_[b].frame; });",
    },
    {
        "name": "M19 merged cap one lower",
        "rule": "merged take: at most kMaxMerged (4)",
        "file": "frame_store.cpp",
        "old": "    while (mergedCount < kMaxMerged) {",
        "new": "    while (mergedCount + 1 < kMaxMerged) {",
    },
    {
        "name": "M20 merged slot not locked",
        "rule": "merged take: each merged slot is locked",
        "file": "frame_store.cpp",
        "old": "    slots_[mergedSlots[m]].locked = true;\n    ++merged_;",
        "new": "    ++merged_;",
    },
    {
        "name": "M21 merged frame not counted",
        "rule": "merged take: each merged slot counts as merged",
        "file": "frame_store.cpp",
        "old": "    slots_[mergedSlots[m]].locked = true;\n    ++merged_;",
        "new": "    slots_[mergedSlots[m]].locked = true;",
    },
    {
        "name": "M22 Release leaves the take locked",
        "rule": "one take at a time: Release ends the take",
        "file": "frame_store.cpp",
        "old": "  if (lockedCount_ > 0) --lockedCount_;\n",
        "new": "",
    },
    {
        "name": "M23 a filling older frame may be merged",
        "rule": "merged take: ready slots only",
        "file": "frame_store.cpp",
        "old": "        if (index == newest || slot.state != SlotState::kReady || slot.locked ||",
        "new": "        if (index == newest || slot.state == SlotState::kEmpty || slot.locked ||",
    },
    {
        "name": "M24 merged picks the oldest older frames, not the newest",
        "rule": "merged take: the newest of the older ready slots",
        "file": "frame_store.cpp",
        "old": "        if (pick == kNoSlot || slot.frame > slots_[pick].frame) pick = index;",
        "new": "        if (pick == kNoSlot || slot.frame < slots_[pick].frame) pick = index;",
    },
    {
        "name": "M25 the take retires its own merged slots",
        "rule": "merged take: a merged slot is handed over, not retired",
        "file": "frame_store.cpp",
        "old": "    if (index == newest || isMerged(index)) continue;",
        "new": "    if (index == newest) continue;",
    },
    {
        "name": "M26 the snapshot sink gets the frame's deadline, not its arrival",
        "rule": "the snapshot sink gets (frame, snapshot, arrival)",
        "file": "frame_store.cpp",
        "old": "  if (config_.snapshotSink) config_.snapshotSink(frame, snapshot, arrivalMonoNs);",
        "new": "  if (config_.snapshotSink) config_.snapshotSink(frame, snapshot, arrivalMonoNs + config_.deadlineNs);",
    },
    {
        "name": "M27 the snapshot sink runs after the ready sink",
        "rule": "the snapshot sink runs before the ready sink",
        "file": "frame_store.cpp",
        "old": "  if (config_.snapshotSink) config_.snapshotSink(frame, snapshot, arrivalMonoNs);\n  DeliverPending(pending, pendingCount);",
        "new": "  DeliverPending(pending, pendingCount);\n  if (config_.snapshotSink) config_.snapshotSink(frame, snapshot, arrivalMonoNs);",
    },
]


def sha(path):
    with open(path, "rb") as handle:
        return hashlib.sha256(handle.read()).hexdigest()


def line_of(text, index):
    return text[:index].count("\n") + 1


def build(name):
    unit = os.path.join(BUILD, name + "_unit")
    stress = os.path.join(BUILD, name + "_stress")
    for target, source in ((unit, "tests/frame_store_test.cpp"), (stress, "tests/frame_store_stress_test.cpp")):
        command = ["g++"] + CXXFLAGS + [os.path.join(ROOT, source),
                                        os.path.join(ROOT, "frame_store.cpp"),
                                        os.path.join(ROOT, "pace_signal.cpp"),
                                        "-o", target]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode != 0:
            return None, None, result.stderr.strip().splitlines()[-6:]
    return unit, stress, []


def run(command, env_extra):
    env = dict(os.environ)
    env.update(env_extra)
    try:
        result = subprocess.run(command, capture_output=True, text=True, env=env, timeout=120)
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    return result.returncode, result.stdout + result.stderr


def main():
    os.makedirs(BUILD, exist_ok=True)
    originals = {}
    for entry in MUTATIONS:
        path = os.path.join(ROOT, entry["file"])
        if path not in originals:
            originals[path] = sha(path)

    rows = []
    survivors = 0
    for number, entry in enumerate(MUTATIONS, start=1):
        path = os.path.join(ROOT, entry["file"])
        with open(path, "r", encoding="utf-8") as handle:
            text = handle.read()
        count = text.count(entry["old"])
        if count != 1:
            rows.append((entry["name"], entry["rule"], "NOT APPLIED", "%d matches" % count, entry["file"]))
            survivors += 1
            continue
        index = text.index(entry["old"])
        line = line_of(text, index)
        mutated = text.replace(entry["old"], entry["new"])
        tag = "m%02d" % number
        where = "%s:%d" % (entry["file"], line)
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(mutated)
            unit, stress, errors = build(tag)
            if unit is None:
                rows.append((entry["name"], entry["rule"], "BUILD ERROR", " ".join(errors), where))
                survivors += 1
                continue
            unit_code, unit_out = run([unit], {})
            stress_code, stress_out = run([stress], {"STRESS_FRAMES": STRESS_FRAMES})
            if unit_code != 0:
                rows.append((entry["name"], entry["rule"], "killed", "unit: " + killed_by(unit_out, unit_code), where))
            elif stress_code != 0:
                rows.append((entry["name"], entry["rule"], "killed",
                             "stress: " + killed_by(stress_out, stress_code), where))
            else:
                survivors += 1
                rows.append((entry["name"], entry["rule"], "SURVIVED", "", where))
        finally:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)

        for original_path, original_hash in originals.items():
            if sha(original_path) != original_hash:
                print("FATAL: %s was not restored" % original_path)
                return 2

    print()
    print_table([(name, rule, result, by if result == "killed" else "") for name, rule, result, by, _ in rows])
    print("\n%d mutations, %d survived" % (len(rows), survivors))
    for name, rule, result, detail, where in rows:
        if result != "killed":
            print("  - %s (%s): %s %s" % (name, where, result, detail))
    return 0 if survivors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
