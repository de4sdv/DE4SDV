# IVI warning presentation (INC-DRIVING-002, B10)

Status: draft, not yet validated. Nothing in this folder has run on a guest yet.

## The problem

When the candidate's plan warns of a collision, the driver must see the warning on the display and
hear a sound. The model gives the AAOS SDV 0.2 s of wall-clock time from the request to each mode,
0.1 s of it for this app: from its receipt of the request to the first displayed frame with the
warning and to the start of the sound. The app must also log those three moments so that phase 10
can measure them.

This folder is that app: `CollisionWarningPresentationApplication` of
`driver_assistance_physical_software_realization.sysml`, the end of the mapping
MAP-DRIVING-DA-WARNING-REQUEST (hop 8 of [`../ivi-warning/README.md`](../ivi-warning/README.md)). It
is not the AEBS visualization of the INC-AEBS-010 increment and sends nothing to the candidate.

## What it does

- It subscribes by name, through the SDV Gateway, to the unit `de4sdv-driving-warning-request` that
  the SOME/IP broker (`com.android.sdv.someip` / `SomeIpBroker`) of the SDV Core VM publishes, as
  subject `org.de4sdv.collisionwarning` / `CollisionWarningPresentation`. Every id comes from
  [`../interfaces/service_ids.json`](../interfaces/service_ids.json); the ACLs are those of
  [`../ivi-warning/interop/acl/`](../ivi-warning/interop/acl/). The message arrives typed
  (`de4sdv.driving.v1.CollisionWarningRequest`, REFLECTION at the broker).
- Each message goes through `WarningRequestReducer`. The model says that a request starts with the
  first event that is true after one that is false:

  | Verdict | Message | Effect |
  |---|---|---|
  | `START` | `requested` 1 after 0, or the app's first message | the warning on the display, the sound starts |
  | `HOLD` | `requested` 1 again | nothing shown again |
  | `CLEAR` | `requested` 0 while shown | the warning is taken off, the sound stops |
  | `IDLE` | `requested` 0 while nothing is shown | none |
  | `STALE` | `issue_time_sim_ms` not after the last accepted | refused, no change |
  | `MALFORMED` | `requested` not 0 or 1, or a slot that does not parse | refused, no change |

- On `START` the sound (`AudioTrack.play()` of a prepared static looped beep) is started on the
  subscriber's thread right after the read, and the screen change goes to the front of the UI queue.

## The record

One JSONL line per event in `files/warning.jsonl` of the app, and the same line in logcat under
`DE4SDV_COLLISION_WARNING`. Every line has `t_mono_ns` (the IVI VM's `CLOCK_MONOTONIC`) and
`t_real_ns` (the IVI VM's real time, millisecond granularity).

| Event | When | Use in the phase 10 probe |
|---|---|---|
| `receipt` | every message read, stamped at the read: `seq`, `requested`, `issue_time_sim_ms`, `verdict`, `request` | the end of the path share; `t_real_ns` against the publisher's send, with the clock bound |
| `display_drawn` | the first `onDraw` with the warning of a request | upper bound of the app's draw |
| `display_committed` | the frame-commit callback of that frame (submitted to the swap chain) | `since_receipt_ns` is the app's own display figure |
| `sound_play_called` | just before `AudioTrack.play()` | |
| `sound_head_moved` | the first 2 ms poll with the playback head past frame 0 | |
| `sound_timestamp` | the first `AudioTrack.getTimestamp()` past frame 0: `presented_mono_ns`, `start_estimate_mono_ns` | the app's own sound figure, if the platform answers |
| `display_cleared`, `sound_stopped` | the request ended | |
| `lifecycle`, `status`, `error`, `drop`, `sound_*` | start, link, configuration, counts every 5 s, failures | |

Differences on one clock (`since_receipt_ns`) are safe to quote. The app computes no cross-host
latency. The guest clock free-runs, so the session sets it immediately before each window.

## Build and install

[`scripts/stage_ivi_warning_app.sh`](scripts/stage_ivi_warning_app.sh) `check | stage | build |
install | start | verify | pull | unstage`. `build` copies `app/`, `contract/Android.bp`, the proto
of [`../ivi-warning/contract/`](../ivi-warning/contract/) and the tree's Gateway Java client sources
to `samples/de4sdv_collision_warning/`, then builds the modules `De4sdvCollisionWarningPresentation`
and `De4sdvCollisionWarningPresentationTests` with the IVI product's recorded variant
(`sdv_ivi_cf-cp2a-userdebug`) only. Another variant makes the build system delete the IVI images.
`install` pushes the subject grant, the broker object policy (merged into the guest's file
when another subscriber already owns it) and the APK into `/vendor/priv-app`, then reboots the IVI
VM. [`../guest-build/`](../guest-build/) runs these steps on the guest host.

Restart the app before each window (`start`, `am start -S`): issue times restart with every run,
and the reducer refuses times that are not newer.

## Tests

`tests/` runs in the `driver-assistance-bench (INC-DRIVING-002)` suite of
`tools/run_bench_unit_tests.py`:

- `test_app_jvm.py`: the 27 JVM tests of `app/tests/` (edge, repeat, clear, stale, malformed,
  record format, one mark per request, tone, screen text) with the host's JDK and a stand-in for
  JUnit, and a compile of every app source against compile-only stand-ins of the Android, Gateway
  client and protobuf APIs (`tests/jvm/stubs/`). Without a JDK (`DE4SDV_JDK`, `JAVA_HOME` or
  `javac` on `PATH`) these skip.
- `test_app_build_files.py`: the manifest package, the modules and their split, the proto module,
  and the ids in the code against `service_ids.json` and the ACLs.

## Deviations and choices

- The model says when a request starts, not when the presentation ends. The app ends it with the
  request (`CLEAR` on `requested` 0). A lead or owner decision can change that.
- Before its first message the app holds no request, as after a false event, so a first `true`
  shows the warning.
- The subscription does not fetch the publication's last message: after the restart before a
  window it could be the `true` of an earlier run. The next plan's event follows within one
  simulation step.
- Staleness is judged by issue time only; there is no age check against the IVI clock, and the
  warning stays shown if the stream stops while it is shown.
- The sound: a 2000 Hz beep, 150 ms on and 100 ms off, `USAGE_ALARM`, transient focus requested
  after `play()`. The form of the sound is the bench's choice.

## What the local tests cannot show

These need the phase 10 probe of the guests:

- that the app installs under `/vendor/priv-app`, its `initComms` and discovery succeed, and under
  which SELinux mode (an earlier app needed a permissive IVI for the gateway lookup);
- that it subscribes once the broker publishes the unit, and reads each injected request;
- the times of the display and the sound against the receipt, and whether `getTimestamp()` answers
  for a static track on the Cuttlefish IVI. If the sound is not observable, report it as unmeasured;
- that the screen shows the warning on the display a recording captures.
