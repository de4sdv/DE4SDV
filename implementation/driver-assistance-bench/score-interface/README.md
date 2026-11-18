# DE4SDV S-CORE interface for VisionPilot

Status: draft, not yet validated. Nothing here has run on the bench. The S-CORE build has not compiled any of it yet.

## The problem

INC-DRIVING-002 runs VisionPilot at `014e0e7a56ee8e597c2cab8175233f74edd9b856` as an Eclipse S-CORE application.
At the pin, VisionPilot reads its camera and its vehicle from video files, V4L2, CAN or ROS 2. It has no S-CORE
input or output, and it does not publish its warnings. This folder holds the change that makes VisionPilot run on
S-CORE. It ships as a patch series against the pin, so upstream's code is not copied into this repository.

## What is here

| Path | Content |
|---|---|
| `patches/0001-de4sdv-visualization-recorder.diff` | the VIS8 visualization recorder, byte-identical to the probe's patch (sha256 `29a1f5d0…`) |
| `patches/0002-de4sdv-score-interface.diff` | the S-CORE interface; it applies on top of 0001 |
| `patches/SHA256SUMS` | the sha256 of both patches |
| `module/` | the new files of 0002, as they land in `VisionPilot/modules/de4sdv/score_interface/`. A test checks that they equal the patch |
| `check_patch.sh` | applies the series to a fresh `git clone --shared` at the pin |
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

The module, the visualization recorder and these hunks make up the source difference against the pin. The candidate
record of REQ-DRIVING-044 carries that difference (MAP-DRIVING-DA-CANDIDATE-RECORD). It is the diff of both patches,
0001 and 0002, never empty.

## What is not compiled yet

- `module/src/lola_bindings.cpp` holds the mw::com skeletons and the proxy. It needs the S-CORE Communication headers.
  Here it only passes a syntax check against the closed-loop driving bench's local mock, which is not S-CORE.
- `module/src/carla_client.cpp` is the one C++20 unit; it needs the CARLA 1.0 client. Nothing here compiles it.
- The patched VisionPilot as a whole has not been built or linked. Both binding units are left to the S-CORE Bazel
  build, item B2 of the implementation brief.

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
