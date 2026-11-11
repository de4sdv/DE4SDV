#!/usr/bin/env python3
"""Single-point mutation probes for the driving agent's frame store.

Each entry replaces exactly one source fragment, rebuilds the unit and stress
tests, and reports whether a test caught it. The sources are restored after
every probe; the script exits non-zero if any mutation survives.
"""
import hashlib
import os
import subprocess
import sys

# The unit lives in agent/cc/; this script and the tests in agent/cc/tests/.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.environ.get("FRAME_STORE_MUT_BUILD", os.path.join(ROOT, ".build", "mut"))
STRESS_FRAMES = "800"

CXXFLAGS = ["-std=c++17", "-O2", "-Wall", "-Wextra", "-Werror", "-pthread", "-I" + ROOT]

MUTATIONS = [
    {
        "name": "M01 deadline 95 ms -> 195 ms",
        "file": "frame_store.h",
        "old": "inline constexpr std::int64_t kDefaultDeadlineNs = 95'000'000;",
        "new": "inline constexpr std::int64_t kDefaultDeadlineNs = 195'000'000;",
    },
    {
        "name": "M02 readiness needs 5 cameras, not 6",
        "file": "frame_store.cpp",
        "old": "    if (slot.hasSnapshot && slot.presentMask == kAllCamerasMask) {",
        "new": "    if (slot.hasSnapshot && (slot.presentMask & 0x1FU) == 0x1FU) {",
    },
    {
        "name": "M03 skip not counted in RetireLocked",
        "file": "frame_store.cpp",
        "old": "    if (!slot.skipCounted) {\n      ++skipped_;\n      slot.skipCounted = true;\n    }",
        "new": "    if (!slot.skipCounted) {\n      slot.skipCounted = true;\n    }",
    },
    {
        "name": "M04 late image may modify a ready slot",
        "file": "frame_store.cpp",
        "old": "    if (slot.state == SlotState::kReady || (slot.presentMask & bit) != 0U) {",
        "new": "    if ((slot.presentMask & bit) != 0U) {",
    },
    {
        "name": "M05 late_images not incremented for a ready slot",
        "file": "frame_store.cpp",
        "old": "      // the ring holds: both are late arrivals.\n      ++lateImages_[camera];",
        "new": "      // the ring holds: both are late arrivals.",
    },
    {
        "name": "M06 eviction picks the newest, not the oldest",
        "file": "frame_store.cpp",
        "old": "    if (oldest == kNoSlot || slot.frame < slots_[oldest].frame) oldest = index;",
        "new": "    if (oldest == kNoSlot || slot.frame > slots_[oldest].frame) oldest = index;",
    },
    {
        "name": "M07 newest-ready picks the oldest",
        "file": "frame_store.cpp",
        "old": "    if (newest == kNoSlot || slot.frame > slots_[newest].frame) newest = index;",
        "new": "    if (newest == kNoSlot || slot.frame < slots_[newest].frame) newest = index;",
    },
    {
        "name": "M08 second Take without Release allowed",
        "file": "frame_store.cpp",
        "old": "  if (lockedCount_ != 0) {\n    ++misuse_;  // one take at a time: the caller forgot a Release\n    return handle;\n  }",
        "new": "  if (lockedCount_ != 0) {\n    ++misuse_;  // one take at a time: the caller forgot a Release\n  }",
    },
    {
        "name": "M09 poll re-marks ready slots",
        "file": "frame_store.cpp",
        "old": "      if (slot.state != SlotState::kFilling || !slot.hasSnapshot) continue;",
        "new": "      if (slot.state == SlotState::kEmpty || !slot.hasSnapshot) continue;",
    },
    {
        "name": "M10 size validation always valid",
        "file": "frame_store.cpp",
        "old": "    view.valid = data != nullptr && size == expected &&",
        "new": "    view.valid = data != nullptr &&",
    },
    {
        "name": "M11 pace payload big-endian",
        "file": "pace_signal.cpp",
        "old": "    out[i] = static_cast<std::uint8_t>((frame >> (8U * i)) & 0xFFU);",
        "new": "    out[i] = static_cast<std::uint8_t>((frame >> (8U * (7U - i))) & 0xFFU);",
    },
    {
        "name": "M12 deadline fires one nanosecond late",
        "file": "frame_store.cpp",
        "old": "      if (nowMonoNs < slot.deadlineNs) continue;",
        "new": "      if (nowMonoNs <= slot.deadlineNs) continue;",
    },
    {
        "name": "M13 overflow not counted",
        "file": "frame_store.cpp",
        "old": "      if (index == kNoSlot) {\n        ++overflow_;\n        ++overflowSnapshots_;\n        return false;\n      }",
        "new": "      if (index == kNoSlot) {\n        ++overflowSnapshots_;\n        return false;\n      }",
    },
    {
        "name": "M14 skipCounted guard removed (double count)",
        "file": "frame_store.cpp",
        "old": "    if (!slot.skipCounted) {",
        "new": "    if (true) {",
    },
    {
        "name": "M15 a retired frame may be resurrected by an image",
        "file": "frame_store.cpp",
        "old": "      if (static_cast<std::int64_t>(imageFrame) <= retiredThrough_) {",
        "new": "      if (false) {",
    },
    {
        "name": "M16 Take retires only ready slots, not filling ones",
        "file": "frame_store.cpp",
        "old": "    if (slot.state == SlotState::kEmpty || slot.locked || slot.frame >= newestFrame) continue;",
        "new": "    if (slot.state != SlotState::kReady || slot.locked || slot.frame >= newestFrame) continue;",
    },
    # Merged frames (DESIGN.md "Merged frames"): the take hands older ready frames over instead of skipping them.
    {
        "name": "M17 merged frames never handed over",
        "file": "frame_store.cpp",
        "old": "  if (merged != nullptr) {\n    while (mergedCount < kMaxMerged) {",
        "new": "  if (false) {\n    while (mergedCount < kMaxMerged) {",
    },
    {
        "name": "M18 merged frames handed over newest first",
        "file": "frame_store.cpp",
        "old": "[this](std::size_t a, std::size_t b) { return slots_[a].frame < slots_[b].frame; });",
        "new": "[this](std::size_t a, std::size_t b) { return slots_[a].frame > slots_[b].frame; });",
    },
    {
        "name": "M19 merged cap one lower",
        "file": "frame_store.cpp",
        "old": "    while (mergedCount < kMaxMerged) {",
        "new": "    while (mergedCount + 1 < kMaxMerged) {",
    },
    {
        "name": "M20 merged slot not locked",
        "file": "frame_store.cpp",
        "old": "    slots_[mergedSlots[m]].locked = true;\n    ++merged_;",
        "new": "    ++merged_;",
    },
    {
        "name": "M21 merged frame not counted",
        "file": "frame_store.cpp",
        "old": "    slots_[mergedSlots[m]].locked = true;\n    ++merged_;",
        "new": "    slots_[mergedSlots[m]].locked = true;",
    },
    {
        "name": "M22 Release leaves the take locked",
        "file": "frame_store.cpp",
        "old": "  if (lockedCount_ > 0) --lockedCount_;\n",
        "new": "",
    },
    {
        "name": "M23 a filling older frame may be merged",
        "file": "frame_store.cpp",
        "old": "        if (index == newest || slot.state != SlotState::kReady || slot.locked ||",
        "new": "        if (index == newest || slot.state == SlotState::kEmpty || slot.locked ||",
    },
    {
        "name": "M24 merged picks the oldest older frames, not the newest",
        "file": "frame_store.cpp",
        "old": "        if (pick == kNoSlot || slot.frame > slots_[pick].frame) pick = index;",
        "new": "        if (pick == kNoSlot || slot.frame < slots_[pick].frame) pick = index;",
    },
    {
        "name": "M25 the take retires its own merged slots",
        "file": "frame_store.cpp",
        "old": "    if (index == newest || isMerged(index)) continue;",
        "new": "    if (index == newest) continue;",
    },
    {
        "name": "M26 the snapshot sink gets the frame's deadline, not its arrival",
        "file": "frame_store.cpp",
        "old": "  if (config_.snapshotSink) config_.snapshotSink(frame, snapshot, arrivalMonoNs);",
        "new": "  if (config_.snapshotSink) config_.snapshotSink(frame, snapshot, arrivalMonoNs + config_.deadlineNs);",
    },
    {
        "name": "M27 the snapshot sink runs after the ready sink",
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
            rows.append((entry["name"], entry["file"] + ":?", "PATTERN-%d" % count))
            survivors += 1
            continue
        index = text.index(entry["old"])
        line = line_of(text, index)
        mutated = text.replace(entry["old"], entry["new"])
        tag = "m%02d" % number
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(mutated)
            unit, stress, errors = build(tag)
            if unit is None:
                rows.append((entry["name"], "%s:%d" % (entry["file"], line), "BUILD-ERROR"))
                survivors += 1
                continue
            unit_code, unit_out = run([unit], {})
            stress_code, stress_out = run([stress], {"STRESS_FRAMES": STRESS_FRAMES})
            if unit_code != 0:
                detail = "unit (timeout)" if unit_code == 124 else "unit"
            elif stress_code != 0:
                detail = "stress (timeout)" if stress_code == 124 else "stress"
            else:
                detail = "none"
            verdict = "killed by " + detail if detail != "none" else "SURVIVED"
            if detail == "none":
                survivors += 1
            # First failing check, for the record.
            first = ""
            for blob in (unit_out, stress_out):
                for text_line in blob.splitlines():
                    if text_line.startswith("FAIL "):
                        first = text_line.strip()
                        break
                if first:
                    break
            rows.append((entry["name"], "%s:%d" % (entry["file"], line), verdict, first))
        finally:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(text)

        for original_path, original_hash in originals.items():
            if sha(original_path) != original_hash:
                print("FATAL: %s was not restored" % original_path)
                return 2

    width = max(len(row[0]) for row in rows)
    print("\n%-*s  %-24s  %-22s  %s" % (width, "mutation", "location", "verdict", "first failing check"))
    print("-" * (width + 80))
    for row in rows:
        name, location, verdict = row[0], row[1], row[2]
        first = row[3] if len(row) > 3 else ""
        print("%-*s  %-24s  %-22s  %s" % (width, name, location, verdict, first))
    print("\n%d mutations, %d survived" % (len(rows), survivors))
    return 0 if survivors == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
