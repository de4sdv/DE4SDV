# Closed-loop driving bench (INC-DRIVING-001, slice 10b): Interface Control Document v2

> **Amendment 1 (2026-11-09, before first deployment; `kInterfaceVersion` stays 2):** rulings A1–A15 of the v2 interface review. Payload change: `DrivingModePayload` gains `checkpointExpectedSha256[64]`, `checkpointActualSha256[64]`, `refusalReason[16]` (A5).

Version 2, 2026-11-09. v1 is `ICD-v1.md`. The changes from v1:
- §3 encodes the operational state as a SOME/IP struct. The broker translates it into the typed `DrivingOperationalState`, as phase 8's MAP-DRIVING-OPERATIONAL-STATE states.
- §2 adds the service id table.
- §4 and §5 take the adapter rules.
- §6 adds clock suffixes.
- §7 and §8 take the run directory and run record additions.
- §10 adds the records the 35 verification cases need.

The model is the authority:
- phase 8 of INC-DRIVING-001, in `closed_loop_driving_physical_software_realization.sysml` on `main`;
- the MAP-DRIVING-* items;
- REQ-DRIVING-001 to -035.

If this document and the model disagree, the model wins: report it, don't guess. The C++ types are in `include/de4sdv/driving/payloads.h` and the log writer is in `run_log.h`.

## 1. Hosts, processes, clocks

| Host (phase 8 part) | Machine | Processes |
|---|---|---|
| S-CORE host `linuxHost : ClosedLoopDrivingLinuxHost` | G4 (RTX PRO 6000), europe-west1-b, 10.132.0.2 | `drivingAgent` (FEO, 4 activities), `actuationAdapter`, `statePublisher`, `gatewayd` + `someipd`, `routeProvider`, bench controller; started by the Launch Manager (root) |
| simulator host `simulatorHost : ClosedLoopDrivingSimulatorHost` | L4 VM, 10.10.0.2 | CARLA 0.9.16 (synchronous, 0.1 s), world-side pacer + rig + scenario (scenario tooling), chase-view recorder |
| guest host `guestHost : AAOSGuestHost` | aaos-build (KVM) | SDV Core VM, IVI VM (observer app) |

There are three clocks. Every time field in a record names its clock by a suffix (§6):
- **Simulation time:** the frame index × 100 ms, exact. Never the simulator's float stamp. CARLA's world frame number is the frame index.
- **Monotonic:** `CLOCK_MONOTONIC` of the S-CORE host. It stamps a plan's production time, a mode's decision time and a command's issue time (REQ-DRIVING-031, -032), and is valid on that host only.
- **Real time:** `CLOCK_REALTIME`, chrony-synchronised. It is used only for comparisons across hosts.

## 2. mw::com events on the S-CORE host (LoLa, one service per specifier)

| Event | Producer | Consumers | Instance specifier | Service id | Payload | When | REQ |
|---|---|---|---|---|---|---|---|
| ego-motion sample | agent / conditionInputs | statePublisher | `de4sdv/driving/ego_motion_sample` | 7401 | `EgoMotionSamplePayload` | once per step | 016, 030 |
| plan | agent / inferPlan | statePublisher | `de4sdv/driving/plan` | 7402 | `DrivingPlanPayload` | once per plan | 015, 027, 031, 034 |
| mode | agent / superviseLoop | statePublisher | `de4sdv/driving/mode` | 7403 | `DrivingModePayload` | once per step, and at once on a change | 029 |
| command | agent / commandVehicle | actuationAdapter | `de4sdv/driving/command` | 7404 | `VehicleMotionCommandPayload` | once per step | 011, 012, 014, 020–022, 032 |
| actuation state | actuationAdapter | statePublisher | `de4sdv/driving/actuation_state` | 7405 | `ActuationStatePayload` | once per applied command; at once when the adapter's stop begins | 028, 029, 032 |
| operational state | statePublisher | gatewayd → SOME/IP | `de4sdv/driving/operational_state` | 7406 | three events `plan`, `vehicle_state`, `health`, each `PreSerializedData<2048>` (bytes 0–1 little-endian length, the §3 struct from byte 4) | §3 | 015–019, 029 |

- The event name of each of the first five services is the last segment of its specifier. Instance id is 1.
- Proxies subscribe with a max sample count of 8. A consumer never blocks a producer: a full slot is a dropped sample, which is counted and logged.
- Every event has `numberOfSampleSlots` ≥ `maxSubscribers` × 8 + 1. LoLa rejects a subscription once the subscribers' sample counts would exceed the slots, and the producer needs one slot that no subscriber holds.
  - The agent's four events allow 3 subscribers (the consumer above, the bench tap, one spare) and have 25 slots.
  - `actuation_state` allows 2 and has 20.
  - Each `operational_state` event allows 1 and has 9.
  - Every manifest that declares an event gives the same two numbers.

## 3. The operational state on SOME/IP (MAP-DRIVING-OPERATIONAL-STATE)

**Service:**
- service `0x4DF0`, instance `0x0001`;
- events `0x8001` plan, `0x8002` vehicle state, `0x8003` health;
- eventgroup `0x0001`, reliable (TCP), port 30510.

**Encoding:**
- Every event carries one `DrivingOperationalState`, encoded as a SOME/IP struct in field order, with no struct length field, big-endian.
- `u32` is UINT32. `f32` is FLOAT32.
- `str` is a UTF8 string per AUTOSAR: a 4-byte length (covering the BOM, the bytes and the terminating NUL), then the BOM `EF BB BF`, the bytes, and `00`.
- `f32[]` is a dynamic array: a 4-byte length in bytes, then the elements.
- Fields of the other kinds are zero, empty strings or empty arrays.

**The broker:** SDV Core's broker maps all three events with `message_translation_mode: REFLECTION` and a `type_definition` listing the same field names and types. It translates them into the typed VSIDL message `de4sdv.driving.v1.DrivingOperationalState`: proto3, the same field names, `uint32` / `float` / `string` / `repeated float`. The IVI observer consumes that typed topic.

| # | Field | Type | Meaning |
|---|---|---|---|
| 1 | schema_major | u32 | 2 |
| 2 | schema_minor | u32 | 0 |
| 3 | kind | u32 | 1 PLAN, 2 VEHICLE_STATE, 3 HEALTH |
| 4 | sequence | u32 | per kind, from 1, no gaps |
| 5 | producer | str | `statePublisher` |
| 6 | publish_real_s | u32 | real time at encoding, seconds |
| 7 | publish_real_ns | u32 | nanoseconds part |
| 8 | publish_mono_s | u32 | monotonic at encoding, seconds |
| 9 | publish_mono_ns | u32 | nanoseconds part |
| 10 | plan_frame_index | u32 | PLAN: the step the plan was made from |
| 11 | plan_capture_ms | u32 | PLAN: simulation ms of its newest camera image (= frame × 100) |
| 12 | plan_production_mono_s | u32 | PLAN: the plan's own production time (REQ-DRIVING-031) |
| 13 | plan_production_mono_ns | u32 | |
| 14 | plan_reference | str | PLAN: `<runRecord>/<frameIndex>` |
| 15 | run_record | str | PLAN: run record identity (REQ-DRIVING-034) |
| 16 | plan_producer | str | PLAN: `drivingAgent/inferPlan` (REQ-DRIVING-015) |
| 17 | plan_sample_count | u32 | PLAN: the payload's raw `sampleCount` (64 when well-formed); the arrays carry min(count, 64) samples (A4) |
| 18 | plan_horizon_s | f32 | PLAN |
| 19 | plan_acceleration | f32[] | PLAN: 64, m/s² |
| 20 | plan_curvature | f32[] | PLAN: 64, 1/m, positive left |
| 21 | plan_x | f32[] | PLAN: 64, m, forward |
| 22 | plan_y | f32[] | PLAN: 64, m, left |
| 23 | speed_kmh | f32 | VEHICLE_STATE: VSS Vehicle.Speed |
| 24 | longitudinal_acceleration | f32 | VEHICLE_STATE: m/s² |
| 25 | lateral_acceleration | f32 | VEHICLE_STATE: m/s² |
| 26 | yaw_rate_dps | f32 | VEHICLE_STATE: deg/s, positive left |
| 27 | sample_capture_ms | u32 | VEHICLE_STATE: simulation ms (REQ-DRIVING-016, -030) = round(captureTime·1000), exact since captureTime = frame × 0.1 s (A1) |
| 28 | sample_receipt_mono_s | u32 | VEHICLE_STATE: when the publisher received it |
| 29 | sample_receipt_mono_ns | u32 | |
| 30 | mode | u32 | HEALTH: `Mode` value |
| 31 | cause | u32 | HEALTH: `Cause` value; the first stop cause wins and latches |
| 32 | mode_source | str | HEALTH: `superviseLoop`, `actuationAdapter`, or "" while starting |
| 33 | cause_since_mono_s | u32 | HEALTH: when the stop began (monotonic); 0 if none. Adapter stop: `ActuationStatePayload.stopSinceMono`; the publisher's own causes: when it detected the cause (A3) |
| 34 | cause_since_mono_ns | u32 | |
| 35 | last_plan_frame_index | u32 | HEALTH |
| 36 | last_plan_capture_ms | u32 | HEALTH: simulation ms of the newest plan's newest image (REQ-DRIVING-017) |
| 37 | step_capture_ms | u32 | HEALTH: the largest step capture time (simulation ms) among the ego-motion samples and plans received (A2) |
| 38 | last_plan_production_mono_s | u32 | HEALTH |
| 39 | last_plan_production_mono_ns | u32 | |
| 40 | dropped_samples | u32 | HEALTH: publisher-side drops so far |
| 41 | checkpoint_expected_sha256 | str | HEALTH, refusal only (REQ-DRIVING-035); from `DrivingModePayload.checkpointExpectedSha256` of the kRefused mode (A5) |
| 42 | checkpoint_actual_sha256 | str | HEALTH, refusal only; from `DrivingModePayload.checkpointActualSha256` (A5) |
| 43 | refusal_reason | str | HEALTH: `mismatch`, `no_pin`, or ""; from `DrivingModePayload.refusalReason` (A5) |

**Publisher timing:**
- Plan: each plan within 100 ms after its production (REQ-DRIVING-015).
- Vehicle state: each motion sample within 100 ms after its receipt (REQ-DRIVING-016).
- Health: every 100 ms of monotonic time, also without plans (REQ-DRIVING-017). Also published at once when a stop begins: the mode becomes `kStopResponse`, `kStandstill` or `kRefused`, or an actuation state reports `stopInForce` (REQ-DRIVING-029).
- The publisher receives nothing from the observation path (REQ-DRIVING-018, -019).

## 4. Stop response (REQ-DRIVING-020 to -029)

- **Causes:** the `Cause` values.
  - The supervision decides 023 to 027 at the step.
  - The commander checks 026 again at the command.
  - The adapter decides 028.
  - `kRouteEmpty` means no corridor cell in the step's `route_mask`. That covers an empty announcement and an ego vehicle that has left the route.
  - One cause per stop, in pipeline order: the step's input conditions first (023 to 025, lowest `Cause` value among them), then a plan that arrived in this step and is invalid (027), then the age of the newest valid plan (026). The first stop cause latches for the run.
- **The stop itself:**
  - The command is `acceleration = -min(4, max_deceleration)`.
  - The steering is held at the last value computed from a valid plan.
  - Every stop command names that plan in `planReference`, frozen when the stop begins, never a plan captured later (REQ-DRIVING-011, VC-DRIVING-022). It is `none` when no driving command was ever computed.
  - At standstill (speed < 0.1 km/h), the vehicle is held until the run ends. The stop latches for the run.
- **Adapter:**
  - Before the first valid command, it holds the brake, without latching a stop.
  - After that, more than 200 ms of simulation time without a valid applied command starts its own stop (`kCommandTimeout`), from the actuation time of the last valid one (A24).
  - It publishes the stop with `stopInForce = 1` and `stopSinceMono`.
- **Valid command:**
  - finite values within the limits of §5;
  - non-empty `planReference`;
  - `-5 ms <= age <= 300 ms` of monotonic time at arrival.
  - An invalid command is dropped, counted and logged, and changes nothing.

## 5. Vehicle configuration (REQ-DRIVING-012)

One JSON file is named by the run record; the commander and the adapter read it:

```json
{"vehicle_blueprint": "vehicle.lincoln.mkz_2020", "wheelbase_m": 2.85,
 "max_acceleration_mps2": 3.0, "max_deceleration_mps2": 8.0,
 "max_road_wheel_angle_deg": 35.0, "max_steering_rate_deg_per_s": 180.0,
 "command_law": "pure_pursuit",
 "longitudinal_controller": {"table": [[-8.0, 0.0, 1.0], [0.0, 0.0, 0.0], [3.0, 0.75, 0.0]],
                             "kp": 0.3, "ki": 0.05, "integrator_limit": 0.3}}
```

- The numbers are placeholders. Bench calibration replaces them; the adapter logs the vehicle's physics control as a `config` record. The steer's full scale is not one of them: the adapter reads it from the vehicle at start-up (A30).
- **Commander:**
  - `steeringAngle` by `command_law` (A27), clamped to ±max_road_wheel_angle and rate-limited per step:
    - `pure_pursuit` (shipped): on the plan's path in the plan's own frame (A32), lookahead 4 m + 0.8 s · speed (4 to 15 m), target the first sample after sample k at least the lookahead from the origin, `deg(atan(wheelbase · 2y/d²))` of its x, y;
    - `first_control`: `deg(atan(wheelbase·κ[k]))`;
  - `acceleration = clamp(a, -max_deceleration, +max_acceleration)`.
- **Adapter:** `steer = clamp(-steeringAngle / max_steer_angle, -1, 1)`, with `max_steer_angle` the hero's front-wheel `max_steer_angle` read from CARLA at start-up (A30); `max_road_wheel_angle` only bounds a valid command (§4). Throttle and brake come from the table plus PI (S2 README).

## 6. Logs

- **Files:** each process writes `<run_dir>/<host>/<component>.jsonl`, using `run_log.h` or the same format.
- **Records:** every record has `t_mono_ns`, `t_real_ns`, `host`, `component`, `event`, `seq`, `data`.
  - `event` is `in.<port>` or `out.<port>` for each crossing, with the full payload. Lifecycle events are `start`, `ready`, `stop`, `drop`, `error`, `config`. The stop events are `stop_response.begin` and `stop_response.standstill`, with the cause.
- **Clock suffixes:** every time field inside `data` names its clock: `_sim_ms` or `_sim_s` (simulation), `_mono_ns` or `_mono_s` (monotonic), `_real_ns` (real time). Payload fields keep their model names, and a sibling `clocks` object maps each payload time field to its clock (REQ-DRIVING-030 to -032).
  - Amendment 1 (A7): `clocks` values are `simulation`, `monotonic` or `real`; payload time fields are seconds (double).
- **No computed latencies:** components log stamps, and the evaluators compute.
- **Non-finite values** are JSON `null`, and evaluators treat `null` as non-finite.

## 7. Run directory

```text
<run_dir>/run_record.json             # §8; frozen before the first plan
<run_dir>/config/                     # agent configuration, vehicle configuration (as used)
<run_dir>/navigation/map.json         # exported map; route file
<run_dir>/score/*.jsonl               # drivingAgent, actuationAdapter, statePublisher, route_provider,
                                      # checkpointInputs (§10 C2), gatewayd/someipd logs
<run_dir>/score/bundles/*.npz         # sampled full input bundles (§10 C2)
<run_dir>/score/drivingAgent.stderr   # FEO_PACE lines (events, skipped)
<run_dir>/simulator/world.jsonl       # pacer, one record per tick (§10 C1)
<run_dir>/simulator/view.mp4          # chase view (NVENC) + recorder summary.json
<run_dir>/guest/observer.jsonl        # observer receipts (IVI real time + decoded message)
<run_dir>/guest/ivi_screen.mp4
<run_dir>/bench/injection.jsonl       # §10 C8
<run_dir>/terminals/*.cast            # real terminal sessions
<run_dir>/MANIFEST.sha256
```

## 8. Run record (REQ-DRIVING-033, -034, -035)

`run_record.json` is written by inferPlan before the first plan and then frozen. Its identity is the first 16 hex digits of its SHA-256.

It holds the `RetainedDrivingRunEvidence` fields known at start:
- configurationIdentity, checkpointSha256, autoE2ESourceRevision, configurationSha256;
- scoreFEORevision (with the event-trigger patch SHA-256), scoreCommunicationVersion, scoreLifecycleVersion, scoreSOMEIPGatewayCommit;
- simulatorBuild, scenario, executionEnvironmentIdentity;
- contractIdentity = `de4sdv.driving.icd.v2`.

It also holds:
- the cuDNN version, the parity result, the warm-up step count and the command law;
- C4: `campaignId`, `runRole`, `scenarioVariant {fault, entrySpeedMps, aaosMode, checkpointCase}`, `inputReplay {sourceRun, digest}`;
- C7: `checkpointPath`, `configurationPath`, `vehicleConfiguration {path, sha256}`, `navigationMap {path, sha256}`, `route {path, sha256}`, `writtenAtMonoNs`, `writtenAtRealNs`.

The checkpoint itself is retained once per campaign, not per run.

## 9. Route (MAP-DRIVING-ROUTE)

- **Route file:** JSON `{"map": "Town10HD_Opt", "waypoints": [[x, y, heading_rad, road_id], ...], "destination": [x, y]}`. It is in the map frame (`x = x_carla`, `y = -y_carla`, `yaw = -yaw_carla`; S3 `carla_frame.py`).
- **Provider:** sends `RouteAnnouncement` to UDP 127.0.0.1:47110 every 500 ms of simulation time. `routeSha256` is exactly 64 hex characters, with no NUL.
- **Fault knobs:** `--stale-after-s`, `--empty-after-s`.
- **Log:** `score/route_provider.jsonl`.

## 10. Records for the verification cases (S5 change list, as adopted)

- **C1, `simulator/world.jsonl`:** the pacer writes one record per tick:
  - `frame`, `sim_ms`;
  - the ego pose, velocity, acceleration and angular velocity;
  - lane: `road`, `lane`, `lat_m`, `junction`;
  - `sensors[]`: per rig camera `{name, actor_id, alive, attached}`;
  - `controlSource` (`actuationAdapter`, or the autopilot during an announced warm-up), `autopilotEnabled`, `trafficManagerEnabled`;
  - collision and lane-invasion events.
  - It records no image digests: the pacer does not receive images.
- **C2, `score/checkpointInputs.jsonl`:** conditionInputs writes one record per step:
  - the step frame and `sim_ms`;
  - per camera: the image frame, `capture_sim_ms`, `arrival_mono_ns`, width, height, valid/missing/stale;
  - each camera's history references (frame indices);
  - the ego-motion history rows (64 × 4);
  - the projection operators (once per run, plus on any change);
  - the raster render time, the corridor cell count, the destination cell count;
  - the input-condition bits.
  - **Bundles:** full input bundles (`score/bundles/<frame>.npz`: the tensors as handed to the checkpoint) for every 50th step and for every step within ±0.5 s of an injected fault, written off the critical path.
- **C3:** commandVehicle's `out.command` record carries `step_capture_sim_ms` and the plan's `capture_sim_ms`. The payload stays exact.
- **C5, C6, C12:** in §3 (HEALTH 36–39, 41–43; PLAN 16–18). The agent also logs `error {code: checkpoint_refused, expectedSha256, actualSha256, reason}` before any plan.
- **C8, `bench/injection.jsonl`:** the bench controller writes `{action: plan_inject|comm_stop|fault_begin|fault_end|camera_stop|..., t_sim_ms, t_mono_ns, t_real_ns, detail}`.
- **C9:** the clock suffixes of §6.
- **C10:** conditionInputs logs `priming.complete {frame, sim_ms, historiesReady}`.
- **C11:** after each campaign, on the G4, the pinned checkpoint's Python reference runs on the retained bundles. Output: `score/referenceInference.jsonl {frameIndex, checkpointSha256, sourceRevision, acceleration[64], curvature[64]}`.

### Amendment 1 additions to §7 and §10

- **§7 `world.jsonl` (A10):** the schema is S5's C1 world record in `case-evaluators/OBSERVABLES.md`. That record is `sensors[] {name, actor_id, alive, attached}`, ego kinematics and `controlSource`, with no digests. The world/pacer process writes it.
- **§10 C2 per-step metadata (A11).** Add four fields; the producer is agent/conditionInputs:
  - `cameras[front].front_hi_res {width, height}`;
  - `marker {image_px, operator_coverage}`;
  - `mapContext {channels, width, height, geometry}`;
  - `routeMask {corridorCells, geometry, routeSha256}`.
- **§10 C2 bundle keys (A12):** the bundle keys are upstream's model-input names, as in the upstream input sample:
  - `camera_tiles`, `front_camera_tile`, `camera_history_tiles`;
  - `egomotion_history`, `map_context`, `route_mask`;
  - `map_valid`, `route_valid`, `visual_history`;
  - `camera_projection_matrix`, `camera_history_projection_matrix`, `front_camera_projection_matrix`;
  - plus `plan_controls` (64×2).
  - A C11 reference inference feeds a bundle to the model unchanged.
- **VC-DRIVING-002 sampling (A13):** the offline re-inference covers the bundled steps (every 50th step and around faults). The evidence states the sample count; the verdict is at most `passBoundedVerification`.

### Amendment 2 (2026-11-09, found while integrating the agent, world side and route provider; `kInterfaceVersion` stays 2)

No payload changes.

- **A16, C2 route coverage.** `routeMask` adds `waypointsInWindow` and `waypointsOnCorridor`. The step adds `rasterPose {x_map_m, y_map_m, yaw_map_rad}`: the REF pose (map frame, §9) both rasters were rendered at.
  - A route centre-line point is in the window when its REF-frame position (x forward, y left; upstream `map_to_ego`) satisfies −10 m + 0.8 m < x < 120 m − 0.8 m and −60 m + 0.8 m < y < 60 m − 0.8 m. That is the window of geometry `autoe2e-bev-450x300-0p4m-v1` with the 10 m route rear clip, shrunk by two pixels.
  - Its cell is row ⌊(120 − x)/0.4⌋, column ⌊(60 − y)/0.4⌋. `waypointsOnCorridor` counts the in-window points whose cell is set in route_mask channel 0.
  - With no accepted route both counts are 0.
  - The window is symmetric left to right, so the counts cannot reveal a mirrored raster; only a retained raster (C2 bundle) can.
- **A17, C2 image sizes.** A camera's `width`/`height` is the size of the image handed to the checkpoint: the 512×512 tile for the checkpoint engine; the stub engine hands the simulator image as it is. `source_width`/`source_height` is the simulator image. `cameras[front].front_hi_res` is as in A11.
- **A18, route provider log (§6).** Each datagram is logged as `out.route_announcement` with `clocks {issueTime: simulation}`. VC-DRIVING-025 reads this record.
- **A19, run record (§8).** Adds `navigationMap {path, sha256}`, `route {path, sha256}` and `cameraProfile {path, sha256}`.
  - `route` is the route file the provider announces; the bench names it in the agent configuration (`route_file`).
  - `cameraProfile` is the camera calibration profile, which shapes every tile and projection.
- **A20, C1 world side.**
  - No autopilot warm-up by default. REQ-DRIVING-011 allows the autopilot no control at any time of the run, so the hero rests at the route start until the agent drives.
  - Kinematics are in the map frame, as in `case-evaluators/OBSERVABLES.md` §3: yaw rate positive counter-clockwise, lateral acceleration positive to the left. `summary.yawRateCheck` compares CARLA's yaw rate with the logged poses on every run.
  - The rig's REF origin is read only after the hero has been simulated and has settled. These setup ticks are not run ticks; `simulator/worldSide.jsonl` logs them as `setup`.
- **A21, mw::com slot sizing (§2).** No payload change.
  - On the simulator host the bench tap and the actuation adapter each subscribed to `command` with 8 samples while the event had 8 slots. Whichever subscribed second was rejected (LoLa: slot overflow): in one run the adapter never drove the vehicle, in two the tap saw nothing.
  - §2 now sizes every event for all its allowed subscribers plus the producer. `interfaces/tests/test_mw_com_manifests.py` checks every manifest and every `Subscribe` call of the bench.
- **A22, drivingAgent warm-up records (§6).** No payload change.
  - While the agent primes, inferPlan may call the checkpoint engine to warm its camera history cache (agent `DESIGN.md`, "Warm-up while priming"). No plan is produced.
  - drivingAgent logs `warm` {frame, stream, warm, reason, lag_ms, ms} for each decision, and `stop` gains `warmCalls`. No evaluator reads them.
- **A23, merged frames (§6, §10 C2).** No payload change.
  - When FEO merges several frame events into one chain, conditionInputs conditions the older ready frames into the planner's histories, oldest first, and plans only the newest (agent `DESIGN.md`, "Merged frames"). Before, they were skipped, and the histories primed again.
  - C2: the newest frame's step record gains `mergedFrames`, one entry per merged frame: `{frame, conditioned, why, condition_ms, readyByDeadline}`. `why` (`camera_not_valid`, `no_planner`, `refused`) appears only when `conditioned` is false. The list is empty when nothing was merged.
  - A merged frame has no C2 record of its own; C2 stays one record per step.
  - `stop` gains `mergedConditioned`, `mergedNotConditioned` and `frameStore.merged`. No evaluator reads them yet.
- **A24, adapter command timeout (§4).** No payload change.
  - The adapter's stop begins once *more than* 200 ms of simulation time have passed since the actuation time of the last valid command: at the third tick after it, not the second.
  - A command arrives about one period after its frame's tick. One late command, arriving just after the next tick, therefore sees exactly 200 ms at the tick before it, as one missed command does. REQ-DRIVING-028 stops on two missed commands.
  - On the simulator host the earlier rule (200 ms or more) stopped the vehicle about 2 s into a run in which no command was missing.
  - After a lost command path, the stop reaches the actuation 300 ms of simulation time after the last applied command, the limit VC-DRIVING-028 checks.
- **A25, C2 camera names (§10).** No payload change.
  - C2 names each camera by the checkpoint's slot: `cameras[].name` and `projections[].camera` are `front`, `front_left`, `front_right`, `rear_left`, `rear`, `rear_right`, in that order. These are the model's camera positions, and the names the evaluators and A11 (`cameras[front]`) use.
  - drivingAgent wrote the CARLA role names (`cam_front`, ...) before, so VC-DRIVING-003 found every real step's camera order wrong.
  - The CARLA role names stay what the world-side rig gives its actors and what the agent searches for; C1 `sensors[].name` keeps them.
- **A26, primed and priming.complete (§10 C2, C10).** No payload change.
  - C2 `primed` and C10 `priming.complete` come from the planner's engine. A step the engine did not condition (an input condition, a refused checkpoint) is not primed.
  - Before, such a step fell back to the number of steps since the first one. On the simulator host, a step with a camera missing at the deadline logged `priming.complete` at frame 113, but the engine's histories were first complete at frame 179. VC-DRIVING-001 reads `priming.complete`, so it would have counted the 66 steps from 113 to 178 as steps without a plan.
  - Without an engine (the stand-in), the step count stays.
  - inferPlan no longer calls the warm-up on a step with an input condition. That step was not conditioned, so there is nothing to warm, and `warmCalls` counted it.
- **A27, shipped command law (§5).** No payload change.
  - The shipped vehicle configuration names `pure_pursuit`: the steering follows the plan's path from sample k, with a lookahead of 4 m + 0.8 s · speed (4 to 15 m). `first_control` stays available and is still named by the run record when configured.
  - The checkpoint's first curvature sample leans right in its outputs: about −0.05 1/m at rest and −0.044 1/m while moving, in every moving plan of a simulator run, while the same plans' paths bent left by +0.5 to +1.0 m at 5 to 10 m ahead.
  - Under `first_control` the vehicle steered about −8° from its first command and left the road within 23 s. Re-judged on the same plans, `pure_pursuit` steers a median of +0.6° while moving and 0° at rest.
  - The readiness probe with yaw rate and curvature given as zero in the history (REQ-DRIVING-008), in which the plans no longer turned off the lane within seconds, steered by pure pursuit on the plan's path.
  - The acceleration stays `a[k]` under both laws.
- **A28, late camera image (§4, REQ-DRIVING-023).** No payload change.
  - A camera whose image for the step missed the frame deadline is judged by its newest valid image to date. Only an image *more than* 200 ms of simulation time older than the step is a condition (`kCameraStale`). With a camera's images withheld from step k, the stop therefore begins at step k+2, as A24 reads the adapter's limit. `kCameraMissing` now means no valid image of that camera to date; an invalid image of the step is `kCameraInvalid` at once, as before.
  - Before A28 the step's own missing image was `kCameraMissing`, so one late image stopped the vehicle. A run on the simulator host stopped that way after a single image arrived late.
  - The step without that image has no plan of its own. It still goes into the histories with its pose; the checkpoint gets no image for that camera, so the frame has no camera tiles. With the checkpoint engine, the steps that take that frame as a camera-history frame (k+5 to k+35) have no plan either, and the next plan on that phase (k+40) re-encodes its camera history (a cold call). The supervision keeps the newest valid plan in force meanwhile; these steps are single steps without their own plan, 0.5 s apart.
  - The images of a frame merged into a later step count as received when that frame went into the histories (all six valid), as the case evaluators count them. A merged frame with a late camera is still left out of the histories, as before.
  - C2 and `out.condition` keep their form. A camera's C2 slot describes the step's own image (`status` "missing", null stamps). `out.condition` names no cause for a late camera until its newest valid image is more than 200 ms old (`kCameraStale`).
- **A29, ego-motion history against the poses (§10 C1, C2; REQ-DRIVING-008).** No payload change.
  - REQ-DRIVING-008 as amended on 2026-11-10 compares like with like. VC-DRIVING-008 reads the C1 `egoPose` and drivingAgent's `rig` record, not the speed and acceleration CARLA reports (`velocity.speed_mps`, `acceleration.longitudinal_mps2`).
  - For each plan's step k it works speed and acceleration out of the poses of frames k−65 … k as upstream's closed-loop driver does (`egomotion_from_poses`): each pose moved to the origin of the camera rig, `numpy.gradient` of the positions at 0.1 s, the speed its norm, the acceleration `numpy.gradient` of the speed, rows [1:-1]. Row j is frame k−64+j, the newest k−1. Each C2 row is within 0.05 m/s and 0.1 m/s² of those, with yaw rate and curvature 0.
  - The origin is `rig` `result.origin`: the REF origin set_rig returned, `[x, y, z]` in vehicle axes (x forward, y right, z up), metres, logged once before the first step. In the map frame a pose moves by (x, −y) in its own axes. A run without that record leaves the case inconclusive; a missing tick in a step's 66 frames fails that step.
  - Before A29 the rows were compared with CARLA's reported values. Those differ from the poses' at a start from standstill, around contacts and in the edge rows' acceleration, where `numpy.gradient` is one-sided, so the case failed on runs whose rows were within 0.003 m/s and 0.02 m/s² of the poses'.
- **A30, steering full scale (§5, REQ-DRIVING-012).** No payload change.
  - The adapter's steer is the commanded road-wheel angle over the vehicle's maximum steering angle, as the model's actuation mapping reads. That maximum is the hero's front-wheel `max_steer_angle`, which the adapter reads from CARLA's physics control at start-up and logs as `steer_full_scale_deg` in its `config` record: 70° for `vehicle.lincoln.mkz_2020`.
  - `max_road_wheel_angle_deg` (35°) stays the command limit: the commander's clamp and the adapter's validity check.
  - The adapter does not start when CARLA gives no front-wheel `max_steer_angle`, or one below the command limit: it logs an `error` record and exits.
  - Before A30 the steer was the angle over `max_road_wheel_angle_deg`, so CARLA turned the road wheels by twice the commanded angle. On the straight route the commands before the first contact had a median of 0.64° and the applied steer turned the wheels 1.29°; the vehicle turned as the doubled angle predicts.
- **A31, nav prefetch (§10 C2; REQ-DRIVING-006, -007, -013).** No payload change.
  - drivingAgent draws a step's `map_context` and `route_mask` when the step's snapshot arrives, on a thread of its own, about 40 ms before the step's last image. The step uses that render only when it is for the same frame and pose, and for the route the listener's newest announcement names at the step. Otherwise the step renders on the chain as before. The rasters are byte-identical to a render on the chain (agent `DESIGN.md`).
  - C2 gains `navPrefetch`: `{outcome, take_ms}`, or null without the prefetch. `outcome` is one of `hit`, `not_submitted`, `timed_out`, `route_changed`, `pose_changed` and `render_failed`; `take_ms` is the step's time to take it. `render_ms` stays the render's own time, on whichever thread it ran.
  - drivingAgent's `ready` record gains `navigation.prefetch` (`{waitMs}` or null); `stop` gains `navPrefetch` (the prefetch's counters and the takes' outcomes). A `route` record can now carry a frame that had no step of its own: the frame whose render raised the change.
  - Configuration: `nav_prefetch` (default true) and `nav_prefetch_wait_ms` (default 5).
- **A32, pure-pursuit anchor (§5, REQ-DRIVING-011).** No payload change.
  - `pure_pursuit` reads the plan's path in the plan's own frame: the vehicle is at the origin and heads along x, as it did when the plan's frame was captured. The target is the first sample after sample k that lies at least the lookahead from the origin, and the steering is `deg(atan(wheelbase · 2y/d²))` of that sample's x and y. No sample's position or heading stands in for the vehicle's.
  - Before A32 the commander took sample k's pose, heading included, for the vehicle's and shifted the path to it. A sample's pose is where the plan expects the vehicle 0.1 s · (k+1) later. The checkpoint's first samples head right (A27; a median of −0.57° at sample 0 in moving plans) while its path stays on the vehicle's line, and the vehicle does not follow that first heading. Turning the path by it moved every target to the left.
  - Two simulator runs on a straight route show the size. All 189 and 188 moving commands before the first contact were further left than the same plans read from their origin, by a median of 0.61°. The commands asked for a heading change of +9.9° and +9.7° over 21.6 s; the vehicle turned +9.3° in both and left its lane. Read from the origin, the same plans ask for −0.7° and −0.9°. The "+0.6° while moving" of A27 was this shift, not the plans' demand.
  - Sample k still starts the target search, so a plan that is k steps old is not steered toward a sample it has already passed. On a path of constant curvature the steering is the same for every k.
  - The vehicle's travel since the plan's capture is not compensated. On those runs the vehicle was 0.24 m (median) further along the path, and 5 mm to its side, when the command acted.
