# Frame store (DE4SDV INC-DRIVING-001, slice 10b, WP2)

The shared object between the LibCarla glue and the FEO input activity: one
ring of preallocated slots keyed by the CARLA world frame number, each holding
six camera images and the hero snapshot of that frame, ready when complete or
at 95 ms of monotonic time after the snapshot arrived.

Implements the "Frame store" and "Chain and pacing" sections of
`agent/DESIGN.md` and the clocks of `interfaces/ICD.md` §1. It is standalone:
it does not include `payloads.h`, so the consumer converts
`CaptureTimeMicros(frame)` and adapts the snapshot itself.

## Files

| File | Lines | Contents |
|---|---|---|
| `frame_store.h` | 289 | `HeroSnapshot`, `FrameView`, `FrameHandle`, `CountersSnapshot`, `FrameStore` |
| `frame_store.cpp` | 408 | slot allocation, readiness, deadline sweep, consumer handover |
| `pace_signal.h` | 52 | `PaceSignal`, payload codec, `FEO_PACE_SOCKET` lookup |
| `pace_signal.cpp` | 80 | one non-blocking AF_UNIX `SOCK_DGRAM` sender |
| `tests/frame_store_test.cpp` | 929 | 21 unit tests, 513 checks |
| `tests/stress_test.cpp` | 320 | 9 threads, 2000 frames, 16 invariants |
| `mutations.py` | 225 | 16 single-point mutation probes |

## Build and run

```bash
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pthread -I. \
    tests/frame_store_test.cpp frame_store.cpp pace_signal.cpp -o .build/frame_store_test
g++ -std=c++17 -O2 -Wall -Wextra -Werror -pthread -I. \
    tests/stress_test.cpp frame_store.cpp pace_signal.cpp -o .build/stress_test
./.build/frame_store_test && ./.build/stress_test

# ThreadSanitizer
g++ -std=c++17 -O1 -g -fsanitize=thread -Wall -Wextra -Werror -pthread -I. \
    tests/stress_test.cpp frame_store.cpp pace_signal.cpp -o .build/stress_test_tsan
./.build/stress_test_tsan

# AddressSanitizer + UndefinedBehaviorSanitizer
g++ -std=c++17 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer \
    -Wall -Wextra -Werror -pthread -I. \
    tests/stress_test.cpp frame_store.cpp pace_signal.cpp -o .build/stress_test_asan
./.build/stress_test_asan

# mutation probes (rebuilds and restores the sources itself)
python3 mutations.py
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

`python3 tests/frame_store_mutations.py` applies each edit, rebuilds both tests, runs them
(stress at `STRESS_FRAMES=800`), restores the sources and verifies their
SHA-256. All 25 are killed by the unit tests; none survives. M17 to M25 probe
the merged take (agent `DESIGN.md`, "Merged frames").

| # | Mutation | Location | Killed |
|---|---|---|---|
| M01 | deadline 95 ms -> 195 ms | `frame_store.h:34` | yes |
| M02 | readiness needs 5 cameras, not 6 | `frame_store.cpp:151` | yes |
| M03 | skip not counted in `RetireLocked` | `frame_store.cpp:371` | yes |
| M04 | late image may modify a ready slot | `frame_store.cpp:125` | yes |
| M05 | `late_images` not incremented for a ready slot | `frame_store.cpp:127` | yes |
| M06 | eviction picks the newest, not the oldest | `frame_store.cpp:332` | yes |
| M07 | newest-ready picks the oldest | `frame_store.cpp:348` | yes |
| M08 | second `Take` without `Release` allowed | `frame_store.cpp:180` | yes |
| M09 | poll re-marks ready slots (double signal) | `frame_store.cpp:167` | yes |
| M10 | size validation always valid | `frame_store.cpp:145` | yes |
| M11 | pace payload big-endian | `pace_signal.cpp:21` | yes |
| M12 | deadline fires one nanosecond late | `frame_store.cpp:168` | yes |
| M13 | overflow not counted | `frame_store.cpp:72` | yes |
| M14 | `skipCounted` guard removed (double count) | `frame_store.cpp:371` | yes |
| M15 | a retired frame may be resurrected by an image | `frame_store.cpp:112` | yes |
| M16 | `Take` retires only ready slots, not filling ones | `frame_store.cpp:221` | yes |
| M17 | merged frames never handed over | `frame_store.cpp:198` | yes |
| M18 | merged frames handed over newest first | `frame_store.cpp:229` | yes |
| M19 | merged cap one lower | `frame_store.cpp:199` | yes |
| M20 | merged slot not locked | `frame_store.cpp:231` | yes |
| M21 | merged frame not counted | `frame_store.cpp:231` | yes |
| M22 | `Release` leaves the take locked | `frame_store.cpp:259` | yes |
| M23 | a filling older frame may be merged | `frame_store.cpp:203` | yes |
| M24 | merged picks the oldest older frames, not the newest | `frame_store.cpp:207` | yes |
| M25 | the take retires its own merged slots | `frame_store.cpp:219` | yes |

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
   asks; the orchestrator's 5 ms timer calls `PollDeadlines(now)`.
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
