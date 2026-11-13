# Frame store (DE4SDV INC-DRIVING-001, slice 10b)

The shared object between the LibCarla glue and the FEO input activity: one
ring of preallocated slots keyed by the CARLA world frame number, each holding
six camera images and the hero snapshot of that frame, ready when complete or
at 95 ms of monotonic time after the snapshot arrived.

Implements the "Frame store" and "Chain and pacing" sections of
`agent/DESIGN.md` and the clocks of `interfaces/ICD.md` §1. It is standalone:
it does not include `payloads.h`, so the consumer converts
`CaptureTimeMicros(frame)` and adapts the snapshot itself.

## Files

| File | Contents |
|---|---|
| `frame_store.h` | `HeroSnapshot`, `FrameView`, `FrameHandle`, `CountersSnapshot`, `FrameStore` |
| `frame_store.cpp` | slot allocation, readiness, deadline sweep, consumer handover |
| `pace_signal.h` | `PaceSignal`, payload codec, `FEO_PACE_SOCKET` lookup |
| `pace_signal.cpp` | one non-blocking AF_UNIX `SOCK_DGRAM` sender |
| `tests/frame_store_test.cpp` | 26 unit tests, 685 checks |
| `tests/frame_store_stress_test.cpp` | 9 threads, 2000 frames, 17 checks |
| `tests/frame_store_mutations.py` | 27 single-point mutation probes; `tests/mutation_report.py` prints their table |

## Build and run

```bash
mkdir -p .build
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pthread -I. \
    tests/frame_store_test.cpp frame_store.cpp pace_signal.cpp -o .build/frame_store_test
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pthread -I. \
    tests/frame_store_stress_test.cpp frame_store.cpp pace_signal.cpp -o .build/stress_test
./.build/frame_store_test && ./.build/stress_test

# ThreadSanitizer
g++ -std=c++17 -O1 -g -fsanitize=thread -Wall -Wextra -Werror -pthread -I. \
    tests/frame_store_stress_test.cpp frame_store.cpp pace_signal.cpp -o .build/stress_test_tsan
./.build/stress_test_tsan

# AddressSanitizer + UndefinedBehaviorSanitizer
g++ -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer \
    -Wall -Wextra -Werror -pthread -I. \
    tests/frame_store_stress_test.cpp frame_store.cpp pace_signal.cpp -o .build/stress_test_asan
./.build/stress_test_asan

# mutation probes (rebuilds and restores the sources itself)
python3 tests/frame_store_mutations.py   # 27 mutations, 0 survived
```

## Behaviour

A slot is `kEmpty`, `kFilling` or `kReady`. `OnSnapshot` and `OnImage` create
the slot for a frame if it does not exist yet (an image may arrive first), so
allocation happens on the callback path but never allocates memory.

- **Ready by completeness** when the snapshot and all six images are present.
  Presence, not validity: an image with the wrong size is present and invalid,
  and the input activity turns that into `kCameraInvalid` (REQ-DRIVING-023).
- **Ready by deadline** when `PollDeadlines(now)` sees a filling slot with a
  snapshot whose `arrival + 95 ms` has passed (`now >= deadline` fires). A slot
  with images but no snapshot has no deadline and only ages out by eviction.
- **Ready slots are immutable.** A late image, a duplicate image or a second
  snapshot is dropped and counted; it never changes a ready slot.
- **The consumer takes the newest ready slot** and locks it. With `merged`,
  the older ready slots not yet taken are handed over too: oldest first, at
  most `kMaxMerged` (4, the newest of them), each locked and counted as
  `merged` (agent `DESIGN.md`, "Merged frames"). Every other slot older than
  the newest frame is retired in the same call (ready ones as `skipped`,
  filling ones as `dropped_incomplete`), and the retire floor rises to the
  newest frame. That is what makes the sequence of handed-over frames strictly
  increasing and what stops a stale frame from being resurrected by data that
  arrives later.
- **One take at a time.** A second `TakeNewestReady()` before every slot of
  the previous take is released returns an empty handle and counts one
  `misuse`; the locked slots are untouched (one of the two behaviours the
  brief allows, tested).
- **Overflow** is counted when a frame cannot get a slot at all: every slot is
  locked or is the protected newest ready slot, so nothing is evictable. The
  incoming data is dropped; a locked slot is never overwritten and a callback
  never blocks.
- **The sink runs outside the lock**, once per slot that becomes ready, with
  `(frame, ready_by_deadline)`. A `PollDeadlines` pass may make up to
  `kMaxRingSize` slots ready at once; they are delivered from a fixed stack
  batch after the unlock.
- **The snapshot sink** (`snapshotSink`, may be empty) runs outside the lock
  as well, once per accepted snapshot, with `(frame, snapshot, arrival)`. It
  does not run for a duplicate, late or overflowing snapshot. When that
  snapshot completes its slot, the snapshot sink runs before the ready sink.
  The agent's nav prefetch uses it (`../DESIGN.md`).

`PaceSignal` sends the 8-byte little-endian frame number to `FEO_PACE_SOCKET`
(or the path given at construction) from that sink: one datagram per ready
slot, `sendto` with `MSG_DONTWAIT` on a `SOCK_NONBLOCK | SOCK_CLOEXEC` socket.
A missing or full receiver is counted in `failures()` and never retried.

## Accounting identity

At any quiescent point (no slot filling), with `C = Counters()`:

```text
frames             = snapshots + overflowSnapshots + lateSnapshots          (F)
snapshots          = readyComplete + readyDeadline
                     + droppedIncompleteSnapshot + inFlightSnapshot          (S)
slotsCreated       = readyComplete + readyDeadline + droppedIncomplete
                     + inFlightSnapshot + inFlightNoSnapshot                  (L)
readyComplete + readyDeadline = taken + merged + skipped + readyUntaken       (R)
```

- `frames` counts `OnSnapshot` calls; `snapshots` only the first snapshot that
  was stored in a slot. `lateSnapshots` (frame already retired) and
  `overflowSnapshots` (no slot) are the two ways a frame is not stored.
- `droppedIncomplete` is the brief's counter and includes images-only slots.
  `droppedIncompleteSnapshot` is the subset whose frame had arrived, which is
  what the per-frame identity needs. `slotsCreated` closes the same books from
  the slot side, including images-only slots.
- (R) is the disposition of every ready slot: taken or merged (consumed),
  skipped (never handed over, counted once), or still ready and untaken. It holds after the stress
  test's drain with `readyUntaken == 0`.

The stress test asserts (F), (S), (L) and (R) with `inFlightSnapshot == 0`,
plus: strictly increasing handed-over frames (its consumer takes with and
without `merged`, at random), an unchanged checksum of every locked slot
between `Take` and `Release`, `sinkInvocations == readyComplete +
readyDeadline`, and that the complete, deadline, skip, merge and late-image
paths all actually fired.

## Mutation probes

`python3 tests/frame_store_mutations.py` applies each edit, found by its text
(exactly once), rebuilds both tests, runs them (stress at `STRESS_FRAMES=800`),
restores the sources and verifies their SHA-256. M17 to M25 probe the merged take
(agent `DESIGN.md`, "Merged frames"), M26 and M27 the snapshot sink.

How the table is produced: `bash tests/run_tests.sh --mutations` runs the script
and keeps its output in `.build/frame_store_mutations.log`; the table below is
that output, copied unchanged. *rule* is the behaviour above that the mutation
breaks. *killed by* names the test that failed (`unit`: `tests/frame_store_test.cpp`;
`stress`: `tests/frame_store_stress_test.cpp`, reported only when the unit test
passes), the functions that hold its failing checks, in the order they failed (at
most three, then a count), and the number of failing checks
(`tests/mutation_report.py`). A lower-case name such as `complete-slot` or
`overflow` is the label of an accounting-identity check (`CheckAccounting`),
which prints a label instead of a line. The table holds no line numbers. Latest
run (2026-11-11): **27 mutations, 0 survived**; the unit test kills all 27.

| mutation | rule | result | killed by |
|---|---|---|---|
| M01 deadline 95 ms -> 195 ms | ready by deadline: the snapshot's arrival + 95 ms | killed | unit: `TestConfigDefaults`, `TestCompleteSlot` (3 failing checks) |
| M02 readiness needs 5 cameras, not 6 | ready by completeness: the snapshot and all six images | killed | unit: `TestCompleteSlot`, `TestImageBeforeSnapshot`, `TestInvalidSizeImage` and 5 more (50 failing checks) |
| M03 skip not counted in RetireLocked | accounting (R): a ready slot retired untaken counts as skipped | killed | unit: `TestNewestReadySelectionAndSkips`, `newest-selection`, `TestReadySlotEvictedIsSkipped` and 3 more (9 failing checks) |
| M04 late image may modify a ready slot | ready slots are immutable | killed | unit: `TestLateImageAfterReady` (5 failing checks) |
| M05 late_images not incremented for a ready slot | a late image is dropped and counted | killed | unit: `TestLateImageAfterReady`, `TestDuplicateSnapshotAndImage` (2 failing checks) |
| M06 eviction picks the newest, not the oldest | eviction takes the oldest evictable slot | killed | unit: `TestImageOnlyFrameAgesOutByEviction`, `FeedAllImages`, `TestEvictionPicksOldest` (9 failing checks) |
| M07 newest-ready picks the oldest | the consumer takes the newest ready slot | killed | unit: `TestNewestReadySelectionAndSkips`, `newest-selection`, `TestEvictionPicksOldest` and 3 more (21 failing checks) |
| M08 second Take without Release allowed | one take at a time | killed | unit: `TestMisuse` (3 failing checks) |
| M09 poll re-marks ready slots | the ready sink runs once per slot that becomes ready | killed | unit: `TestDeadlineSlot`, `deadline-slot`, `TestSinkCalledExactlyOncePerSlot` and 1 more (17 failing checks) |
| M10 size validation always valid | presence, not validity: an image of the wrong size is present and invalid | killed | unit: `TestInvalidSizeImage` (1 failing check) |
| M11 pace payload big-endian | the pace datagram is the 8-byte little-endian frame number | killed | unit: `TestPaceDatagram`, `TestReadySendsOnePaceDatagram`, `TestPacePayloadCodec` (8 failing checks) |
| M12 deadline fires one nanosecond late | ready by deadline: now >= deadline fires | killed | unit: `TestDeadlineSlot`, `TestLateImageAfterReady`, `TestSinkCalledExactlyOncePerSlot` and 1 more (20 failing checks) |
| M13 overflow not counted | overflow is counted | killed | unit: `TestOverflowWhenNothingEvictable` (1 failing check) |
| M14 skipCounted guard removed (double count) | accounting (R): a skipped slot counts once | killed | unit: `TestCompleteSlot`, `complete-slot`, `TestDeadlineSlot` and 14 more (18 failing checks) |
| M15 a retired frame may be resurrected by an image | the take raises the retire floor: data for a retired frame is late | killed | unit: `TestLateImageAfterReady`, `TestTakeRetiresOlderSlots`, `TestTakeHandsOverMergedFrames` and 1 more (11 failing checks) |
| M16 Take retires only ready slots, not filling ones | the take retires every older slot, filling ones as dropped_incomplete | killed | unit: `TestTakeRetiresOlderSlots`, `TestMergedSkipsFillingFrames` (7 failing checks) |
| M17 merged frames never handed over | merged take: the older ready slots are handed over | killed | unit: `TestTakeHandsOverMergedFrames`, `TestMergedFramesAreCapped`, `TestMergedSkipsFillingFrames` (6 failing checks) |
| M18 merged frames handed over newest first | merged take: oldest first | killed | unit: `TestTakeHandsOverMergedFrames`, `TestMergedFramesAreCapped` (7 failing checks) |
| M19 merged cap one lower | merged take: at most kMaxMerged (4) | killed | unit: `TestMergedFramesAreCapped` (6 failing checks) |
| M20 merged slot not locked | merged take: each merged slot is locked | killed | unit: `TestTakeHandsOverMergedFrames`, `merged-locked`, `merged-released` and 2 more (7 failing checks) |
| M21 merged frame not counted | merged take: each merged slot counts as merged | killed | unit: `TestTakeHandsOverMergedFrames`, `merged-locked`, `merged-released` and 4 more (8 failing checks) |
| M22 Release leaves the take locked | one take at a time: Release ends the take | killed | unit: `TestNewestReadySelectionAndSkips`, `TestOverflowWhenNothingEvictable`, `overflow` and 1 more (4 failing checks) |
| M23 a filling older frame may be merged | merged take: ready slots only | killed | unit: `TestMergedSkipsFillingFrames`, `merged-filling` (4 failing checks) |
| M24 merged picks the oldest older frames, not the newest | merged take: the newest of the older ready slots | killed | unit: `TestMergedFramesAreCapped` (4 failing checks) |
| M25 the take retires its own merged slots | merged take: a merged slot is handed over, not retired | killed | unit: `TestTakeHandsOverMergedFrames`, `merged-locked`, `merged-released` and 4 more (18 failing checks) |
| M26 the snapshot sink gets the frame's deadline, not its arrival | the snapshot sink gets (frame, snapshot, arrival) | killed | unit: `TestSnapshotSinkPerAcceptedSnapshot` (1 failing check) |
| M27 the snapshot sink runs after the ready sink | the snapshot sink runs before the ready sink | killed | unit: `TestSnapshotSinkBeforeReadySink` (1 failing check) |

## Decisions taken beyond the brief

1. **One mutex, sink and datagram outside it.** The `PollDeadlines` batch is a
   fixed stack array (`kMaxRingSize`), so no allocation happens while locked or
   on the callback path. `sinkInvocations` is the only atomic, because it is
   written by whichever thread completed the slot.
2. **`Take` retires every slot older than the taken frame**, not only ready
   ones (ready -> `skipped`, filling -> `dropped_incomplete`), and raises the
   retire floor to the taken frame. Without it, an out-of-order late snapshot
   could complete a lower frame after a higher one was taken, and the consumer
   would see simulation time go backwards.
3. **Images with the wrong size are copied up to `min(size, expected)`** and
   reported with `size` equal to the bytes actually stored, so a consumer that
   reads `size` bytes can never read past the slot buffer. `valid` is false in
   that case; presence and validity are separate bits.
4. **A duplicate snapshot, or a second image for the same camera and frame, is
   dropped and counted** (`duplicateSnapshots`, `lateImages[camera]`) instead
   of being silently ignored, so a misbehaving rig shows up in C2.
5. **Extra counters** beyond the brief's set: `snapshots`, `slotsCreated`,
   `droppedIncompleteSnapshot`, `overflowSnapshots`, `overflowImages`,
   `lateSnapshots`, `duplicateSnapshots`, `sinkInvocations`, `inFlightSnapshot`,
   `inFlightNoSnapshot`, `readyUntaken`, `locked`. They exist to make the
   accounting identity checkable; the brief's counters keep their meaning.
6. **`retiredThrough_` is an `int64` sentinel of -1**, so frame number 0 is a
   valid frame (CARLA starts at 0).
7. **Ring size is configurable in [2, 64]** (64 is the sink batch bound), and
   the constructor throws `std::invalid_argument` for a smaller ring, a
   non-positive deadline or a non-positive camera expectation.
8. **The deadline is per frame, from the snapshot's arrival**, never per camera
   and never from the image arrival: a camera that never arrives still yields
   a ready slot at the deadline.
9. **No thread of its own.** Deadline polling is owner-driven, as the brief
   asks: every 5 ms the sweep thread that `CarlaSource::Start`
   (`carla_source.cpp`) starts calls `PollDeadlines(now)`, and with the fake
   world `FakeWorld::PollLoop` (`agent_ffi.cpp`) does.
10. **`PaceSignal` binds nothing.** A datagram sender needs no address; the
    kernel autobinds. `MSG_NOSIGNAL` keeps a vanished peer from raising
    SIGPIPE. The socket is created in the constructor, so a `sendto` costs one
    syscall on the callback path.
11. **`CameraName` uses the rig role names** (`cam_front`, `cam_front_left`,
    `cam_front_right`, `cam_rear_left`, `cam_rear`, `cam_rear_right`) for the
    log records of ICD §10 C2.

## Open questions

1. Camera resolutions are not fixed in the design: 8 slots x 6 cameras x
   800x600 BGRA is about 92 MB. Confirm the six rig resolutions (and whether
   the front camera uses the hi-res size of C2 `front_hi_res`) before the
   production config allocates. First-touch cost at startup may argue for
   `mmap` with `MAP_POPULATE` instead of `std::vector`.
2. One datagram per ready slot means a `PollDeadlines` pass that ages several
   slots at once sends several datagrams. If the patched scheduler must see one
   per wake-up, the sink should send only the newest frame of the batch; the
   brief says one per ready slot, so that is what is implemented.
3. The scheduler patch's payload is assumed to be the 8-byte frame number. If
   it reads a 4-byte value, only `EncodePacePayload` changes.
4. `late_images` currently covers both "arrived after ready" and "second image
   for the same camera and frame". If C2 needs them apart, split the counter.
5. A snapshot for a frame whose images arrived but whose slot was retired is
   counted as `lateSnapshots`, not as overflow. Confirm how C2 should map that
   to `missing` versus `stale`.
6. `dropped_incomplete` has no C2 field of its own; the input condition only
   reports per-camera missing/invalid/stale. If the bench wants an explicit
   "frame dropped before ready" cause, REQ-DRIVING-023 needs a bit for it.
