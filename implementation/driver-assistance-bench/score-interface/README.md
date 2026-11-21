# DE4SDV S-CORE interface for VisionPilot

Status: draft, not yet validated. The S-CORE build (`../score-build/`) has compiled and linked this module into
VisionPilot on the S-CORE host since 2026-11-18, and the candidate has run on the bench with it. In p10-1 try 4 (SID
20261119T160111Z, 2026-11-19, `eae0a6ef`) it sent 109 driving commands (C4), and its first pass took 1749.2 ms (C6). In
p10-2 attempt 3 (SID 20261120T092051Z, 2026-11-20, `39a964a2`) and S1 (SID 20261121T014447Z, 2026-11-21, `508649ba`) it
drove every run. In S1 the warm start of patch 0005 ran in all 16 runs (2 passes, 678.3 to 706.8 ms). Each of the 14
runs of SC-DRIVING-012 to SC-DRIVING-015 (10 of them meet their entry conditions) still drops 23 or 24 camera images
in its first 5 s and 0 to 2 isolated images later. The steering calibration run drops 34 in its first 5 s and 4
later. The stop run drops 24 in its first 5 s and then 8 in a row right after the stop instant (sim 2870.36 to
2871.06 s): the interface keeps receiving images and drops them, because the candidate that takes them is stopped.

## The problem

INC-DRIVING-002 runs VisionPilot at `014e0e7a56ee8e597c2cab8175233f74edd9b856` as an Eclipse S-CORE application.
At the pin, VisionPilot reads its camera and its vehicle from video files, V4L2, CAN or ROS 2. It has no S-CORE
input or output, and it does not publish its warnings. This folder holds the change that makes VisionPilot run on
S-CORE. It ships as a patch series against the pin, so upstream's code is not copied into this repository.

## What is here

| Path | Content |
|---|---|
| `patches/0001-de4sdv-visualization-recorder.diff` | the VIS8 visualization recorder (the probe's patch, sha256 `29a1f5d0…`) with the `sim_time_s` column of `frames.csv` (brief item B3); its upstream hunks are the probe's, unchanged |
| `patches/0002-de4sdv-score-interface.diff` | the S-CORE interface; it applies on top of 0001 |
| `patches/0003-de4sdv-headless-display.diff` | `LocalDisplay` closes windows only when it opened one (C-2, below); it applies on top of 0002 |
| `patches/0005-de4sdv-warm-start.diff` | the warm start (D-S1-1, below): one warm inference on a dummy image before the module starts; it applies on top of 0003, and with the same hunks on top of the candidate's 0004 |
| `patches/SHA256SUMS` | the sha256 of the patches of `patches/` |
| `module/` | the new files of 0002 and 0005, as they land in `VisionPilot/modules/de4sdv/score_interface/`. A test checks that they equal the patches |
| `check_patch.sh` | applies the series to a fresh `git clone --shared` at the pin |
| `candidates/pr427/0004-de4sdv-port-of-upstream-pr427.diff`, `candidates/pr427/SHA256SUMS` | optional: DE4SDV's port of the two fixes of upstream draft PR #427 (the closing-speed sign and `fusion.ad_only_needs_as_track`), the second candidate of decision D4. Its header names the upstream commits and the lines taken at `a38f227c` and at the pin; it applies on top of 0003 |
| `series.sh` | the series of the candidate `DA_CANDIDATE` (`pin`, the default: 0001-0003 and 0005; `pr427`: 0001-0005), in file-name order: `list`, `extra`, `check`, and `facts <dir>`, the bundle's source difference with a `SHA256SUMS` that lists every diff |
| `tests/` | unit tests with fakes for mw::com and the CARLA client, and a pytest wrapper |

The module is chosen by `source.mode = score` in `vision_pilot.conf` (or `3`, like upstream's numeric aliases), and
built with `ENABLE_SCORE_INTERFACE`. Its own settings are in `config/de4sdv_score_interface.conf`, or at the path in
`DE4SDV_SCORE_INTERFACE_CONFIG`. The keys are `mw_com.config`, `carla.host`, `carla.port`, `carla.timeout_s`,
`carla.attach_timeout_s`, `carla.hero_role`, `carla.camera_role` and `log.path`. The module includes
`de4sdv/driver_assistance/payloads.h` from `../interfaces/include`. That directory is a build input
(`DE4SDV_DA_INTERFACES_INCLUDE_DIR` in CMake), not a copy.

## The hunks and the model

The mapping ids are those of the phase 8 realization,
`textual-notation-of-model/packages/features/driving/driver_assistance_physical_software_realization.sysml`.

| Hunk in 0002 (upstream file) | What it does | Mapping |
|---|---|---|
| `CMakeLists.txt`, `app/CMakeLists.txt` | the `ENABLE_SCORE_INTERFACE` option, the module, the link | none (build) |
| `config/vision_pilot_config.hpp`, `config/src/vision_pilot_config.cpp` | `SourceMode::Score`, parsed from `score` or `3` only under `ENABLE_SCORE_INTERFACE` | none (configuration) |
| `vision_pilot.cpp`, the includes and the declaration | the module object, destroyed after the two interfaces it shares | none |
| `vision_pilot.cpp`, the S-CORE branch beside `:59-79` | starts the module and takes its camera and vehicle interfaces | MAP-DRIVING-DA-CAMERA-IMAGE, MAP-DRIVING-DA-VEHICLE-SPEED, MAP-DRIVING-DA-COMMAND, MAP-DRIVING-DA-CANDIDATE-RECORD |
| `vision_pilot.cpp`, after `:174` | the warning hand-off: one event per plan | MAP-DRIVING-DA-PLANNED-WARNINGS, MAP-DRIVING-DA-WARNING-REQUEST |
| `vision_pilot.cpp`, the loop head | leaves the loop on SIGTERM, so that `Rerun::shutdown()` (`:189`) and the recorder's stop run | none (supervision) |
| `vision_pilot.cpp`, after `:174`, in the same block | the pass's capture simulation time to the visualization recorder, for its `frames.csv` (brief item B3) | MAP-DRIVING-DA-CAMERA-IMAGE |
| `vision_pilot.cpp`, after `:174`, in the same block, after the warning hand-off | `CycleCompleted()`: one alive notification to the Launch Manager per pass with a result | none (the supervision decision of 2026-11-18) |

The new files map to the model's parts as follows:

- `ScoreCameraInterface` is SCORECameraInterface (MAP-DRIVING-DA-CAMERA-IMAGE). It hands on the newest image as BGR,
  drops older ones, and counts and logs each one it drops. It keeps the capture simulation time for the pass.
- `ScoreVehicleInterface` is SCOREVehicleInterface:
  - `read()` gives |velocity| in m/s from the newest world snapshot (MAP-DRIVING-DA-VEHICLE-SPEED);
  - `write()` sends a `DrivingCommandEventPayload` (MAP-DRIVING-DA-COMMAND). It has issueTime, sequenceCount from 1,
    the check value from `DrivingCommandCheckValue`, and `steeringAngle = -steering[1] * 180 / pi`. It sends nothing
    before a well-formed candidate record has arrived (MAP-DRIVING-DA-CANDIDATE-RECORD, REQ-DRIVING-044).
- `ScoreWarningRequestPublisher` is SCOREWarningRequestPublisher (MAP-DRIVING-DA-WARNING-REQUEST). `requested` is
  true when the plan's warnings hold FCW or AEB. It sends the 8 bytes of `EncodeWarningRequestSomeip`.

## The visualization's simulation time (brief item B3)

VIS8 stamped each frame of the visualization at its arrival in the loop, because the file interface has no capture
time. The cut of the bench's recording aligns the visualization with the chase view by the simulation time of the
world tick (`../recording/compose_side_by_side.py --inset`), so `<video>.frames.csv` needs that time:

- 0001 adds `VisualizationRecorder::set_pass_sim_time(double)`. It holds the time for the next `submit()` only,
  and then clears it. The worker writes it as the last column, `sim_time_s`, with six decimals. The field is empty
  when the loop gave no time, as in upstream's file mode. The recorder's other columns, its threads and its
  hand-off stay as VIS8 measured them. 0001's hunks in upstream's files are byte-identical to the probe's patch.
- 0002 calls it in its guarded block after the warning hand-off, before the recorder's hand-off, with
  `ScoreInterface::pass_capture_time_s()`. That is the capture simulation time the camera interface keeps for the
  pass (MAP-DRIVING-DA-CAMERA-IMAGE), the same time the driving command carries as its issue time.

The recorder runs only when `DE4SDV_VISUALIZATION_RECORD` names its video. The Launch Manager configuration's
`vision_pilot` environment does not set it yet (`../launch-manager/config/launch_manager_config.json`), so it is
open for the Launch Manager lane.

## Supervision by the Launch Manager

The supervision decision of 2026-11-18 has S-CORE Lifecycle's Launch Manager supervise the candidate's process by
its alive notifications. `CycleSupervision` (in `core.hpp`) does the module's part:

- the loop calls `CycleCompleted()` in each pass with a result (a plan), inside the block of
  `if (const auto r = pipeline.process(...))`, after the warning hand-off; each call gives one alive notification
  (`Alive::ReportAlive`). A pass without a result gives none;
- the first such pass first reports the process running (`score_mw_lifecycle_report_running`). The Launch Manager
  starts supervising only then, so the network sessions, the first frames and the first inference fall under its
  ready timeout, not under the alive supervision. Upstream's pipeline gives no result for the first frame
  (`VisionPilot/modules/models/src/inference.cpp:152-159` at the pin, a two-frame buffer), so the first inference
  runs in the second pass, before the first call. Why: with the call at the end of every pass that handled a frame,
  p10-1 run 20261119T134840Z reported running after the 6 ms first pass, and the cold first inference (724 ms on
  the L4) tripped the supervision;
- once SIGTERM has arrived, no notification follows;
- the event log gets `supervision.start` at the first pass with a result, `supervision.stop` with the count at the
  end, and
  `supervision.off` with the reason when the process runs unsupervised (no `LCM_ALIVE_INTERFACE_PATH`, that is, the
  Launch Manager did not start it as a supervised component). The summary holds `alive_reported`.

`src/lifecycle_bindings.cpp` is the real client, on `//score/launch_manager:lifecycle_cc` and `:alive_cc` of
Lifecycle v0.10.0. The supervision values, the run targets and the reaction are in
[`../launch-manager/README.md`](../launch-manager/README.md). There is no ASIL claim: VisionPilot and its GPU
libraries are not developed or qualified to ASIL B.

The module, the visualization recorder and these hunks make up the source difference against the pin. The candidate
record of REQ-DRIVING-044 carries that difference (MAP-DRIVING-DA-CANDIDATE-RECORD). It is the diff of the three
patches, 0001, 0002 and 0003, never empty.

## A display without a window (patch 0003, C-2)

Upstream's `LocalDisplay` opens its window only when `show_window_` is set
(`VisionPilot/modules/visualization/src/local_display.cpp:13` at the pin), but calls `cv::destroyAllWindows()` in its
destructor (`:18`) and in `stop()` (`:106`) without that check. The bundle's OpenCV 4.6.0 has no GUI backend, and
there `cvDestroyAllWindows` throws (`modules/highgui/src/window.cpp:1258-1262`). The bench stages
`visualization_on = false`, so every end of the candidate's loop (a SIGTERM from the Launch Manager included) ended in
an abort (exit 134) before `~ScoreInterface` ran, and the run record lost `supervision.stop` and the module's counters
(p10-1 run 20261119T134840Z). 0003 guards both calls with `show_window_`; nothing else changes. It is an upstream bug
candidate; the issue draft is not posted.

## The warm start (patch 0005, D-S1-1)

The model judges no run whose window holds a dropped image, and for an every-run criterion the window is the whole
run. Attempt 3 (SID 20261120T092051Z) dropped 15 and 14 images (`drop.camera_image` in `score_interface.jsonl`), 12
and 11 of them in the first 1.34 s after the go. The module's attach waits for the world's first tick, the go
(`src/carla_client.cpp:47-75`; a client sees no actor while the world holds), and in 0002's order the candidate built
its pipeline (three CUDA sessions, about 0.55 s) only after the attach, then ran its cold first inference (726 and
742 ms) in the second pass. Images come every 0.1 s from the go, so 5-6 were dropped in each of the two stretches.

0005 builds the pipeline and runs it on a black image of the networks' size until a pass gives a result (the
networks ran once), resets it (`InferencePipeline::reset()`: the two-frame buffer, the counters and both fusions), and
only then starts the module (`WarmStart()` in `module/include/de4sdv/score_interface/warm_start.hpp`). The S-CORE
branch beside upstream's sources no longer starts the module. So:

- the first image of the run still gives no result, and nothing of the dummy image reaches a plan;
- the candidate reports running at its first pass with a result, as before (C-1), now about 0.1 s after the go;
- the warm start's passes, result and duration go to the candidate's output (`[DE4SDV] warm start before the
  attach: ...`, the Launch Manager's log).

`tests/warm_start_test.cpp` runs the start and the loop on a virtual clock with a first inference of 724 ms: 0002's
order drops 11 of 100 images, the warm start none. 0005's lines in `vision_pilot.cpp` all lie under
`ENABLE_SCORE_INTERFACE`. It applies last in both series: `series.sh list` sorts by file name, so the candidate's
0004 still applies on 0003 as it was made, and 0005's hunks, which lie before 0004's in `vision_pilot.cpp`, apply on
either (`check_patch.sh` re-creates 0005's body on top of 0004 except its `index` lines).

## What the local checks do not compile

- `module/src/lola_bindings.cpp` holds the mw::com skeletons and the proxy. It needs the S-CORE Communication headers.
  Here it only passes a syntax check against the closed-loop driving bench's local mock, which is not S-CORE.
- `module/src/carla_client.cpp` is the one C++20 unit; it needs the CARLA 1.0 client. Nothing here compiles it.
- `module/src/lifecycle_bindings.cpp` needs S-CORE Lifecycle. Here it only passes a syntax check against
  declarations of the Lifecycle v0.10.0 API in `../launch-manager/tests/lifecycle_mock/`, which are not S-CORE code.
- The local checks do not build or link the patched VisionPilot as a whole. The S-CORE Bazel build, item B2 of the
  implementation brief, builds it with the three binding units (status above).

`check_patch.sh` can run a syntax check of the patched `vision_pilot.cpp` and `vision_pilot_config.cpp`, with the
macro and without it. That check needs OpenCV, ONNX Runtime and Eigen headers.

The adapter test compiles the adapters against upstream's own headers at the pin. Those are `camera_interface.hpp`,
`vehicle_interface.hpp` and `types.hpp`, extracted with `git show`, with the OpenCV 4.8 headers of the host. Without a
clone of the pin, that test is skipped.

## Open points

- The ICD fixes the 8 warning bytes but not their mw::com container. `lola_bindings.cpp` uses
  `PreSerializedData<2048>`, the closed-loop bench's size. It must equal gatewayd's `max_message_size` (B6).
- The record subscription uses a max sample count of 1. The ICD gives none.
- The event log (`log.path`, JSON lines) is this module's proposal. The ICD defines no log for this bench.
- The camera role of the front camera comes from the world side (B7). The module requires it in its settings.

## Running the tests

`test_visualization_recorder_writes_the_sim_time_column` builds the patched recorder with upstream's visualization at
the pin, and runs it through the ffmpeg route with a stand-in ffmpeg. It needs `VISIONPILOT_CLONE`, `ORT_INCLUDE`,
`EIGEN_INCLUDE` and OpenCV 4. Without them it is skipped.

```bash
python -m pytest -q implementation/driver-assistance-bench/score-interface/tests
# with the adapters against upstream's headers:
VISIONPILOT_CLONE=<clone holding 014e0e7a> python -m pytest -q implementation/driver-assistance-bench/score-interface/tests
# the patch series:
implementation/driver-assistance-bench/score-interface/check_patch.sh <clone holding 014e0e7a> [scratch-dir]
```

The suite is registered in `tools/run_bench_unit_tests.py`.

The check values in the tests were computed with Python's `zlib.crc32` and `struct`. `test_score_interface.py`
recomputes every vector of `core_test --vectors` the same way, at test time.
