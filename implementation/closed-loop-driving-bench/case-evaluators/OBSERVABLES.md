# Observables of the 35 verification cases against ICD v2

INC-DRIVING-001, slice 10b. One row per verification case of
`closed_loop_driving_verification_evidence.sysml`: the scenario, the
requirement, the exact observables the case's `processData` needs (component,
log event, field, clock), the computation, the pass threshold, and whether ICD
v2 as written records them.

**Status against ICD v2 (as amended): 33 SUPPORTED (with stated caveats), 2
MISSING.** A MISSING case cannot pass on an ICD v2 run: `evaluate_run.py`
returns `inconclusiveMissingEvidence`, naming the field and the producer that
must add it. Every number of a pass threshold is one that the requirement's
statement or success criterion states, with these exceptions:

- VC-DRIVING-004, 1 ms: the evaluator's tolerance on the age of each history
  image.
- VC-DRIVING-012, 3.0, 8.0, 35 and 180: the limits of the shipped vehicle
  configuration, `actuation-adapter/config/vehicle_limits.json`; the evaluator
  reads the limits of the configuration that the run record names.
- VC-DRIVING-016, 1e-3: the evaluator's tolerance between a published value and
  its record.
- VC-DRIVING-021, 1e-6°: the evaluator's tolerance on the held steering angle.
- VC-DRIVING-022, 0.1 km/h: the speed below which ICD section 4 counts the
  vehicle as at standstill.

No text of the driving model states the numbers of VC-DRIVING-004, -016, -021
and -022.

Clock vocabulary, from ICD section 1: **sim** = simulation time = frame ×
100 ms (`CaptureTimeMicros`), carried as `_sim_ms`; **mono** =
`CLOCK_MONOTONIC` of the S-CORE host, carried as `_mono_s`/`_mono_ns`;
**real** = `CLOCK_REALTIME`, chrony-synchronised, used only across hosts,
carried as `_real_ns`. Payload crossings keep the model field names and carry
a sibling `clocks` object (section 6).

Reading the table: `agent` = `score/drivingAgent.jsonl`, `adapter` =
`score/actuationAdapter.jsonl`, `publisher` = `score/statePublisher.jsonl`,
`observer` = `guest/observer.jsonl`, `world` = `simulator/world.jsonl`,
`inputs` = `score/checkpointInputs.jsonl`, `bundles` =
`score/bundles/<frame>.npz`, `injection` = `bench/injection.jsonl`.

The observation records are read as their producers write them (ICD A34). The
observer writes one `in.operational_state` record per message it received: the
43 fields of section 3 for every kind, with `kind`, `mode` and `cause` as u32
values (kind 1 PLAN, 2 VEHICLE_STATE, 3 HEALTH). The publisher writes one
`out.operational_state` record per message it sent: `kind`, `mode` and
`cause` by name, and its own stamps as whole nanosecond counts (`_mono_ns`,
`_real_ns`) and simulation milliseconds (`_sim_ms`), not as the section 3
`_s`/`_ns` pairs. A run that holds only the earlier names (`rx.plan`,
`rx.vehicle_state`, `rx.health`, `out.health`) is missing evidence.

## 1. The table

| VC | Scen. | Req | Observables (ICD v2) | Computation | Pass threshold | Status |
|---|---|---|---|---|---|---|
| 001 | S1 | 001 | agent `out.plan` {frameIndex, captureTime(sim, `clocks`)}; agent `priming.complete` {frame, sim_ms}; C2 {frame, primed, conditioned, mergedFrames}; `stop_response.begin`; world tick existence, when the run has a world record | for each 100 ms step in [end of priming, end of the run or the step before the stop start]: a new plan (an `out.plan` of that frame) or not; without a stop response the run ends at the world's last tick, or at the last C2 step when that is later, so an agent that stops planning while the world ticks on fails; a run without a world record ends at the last C2 step, with a note; merged frames (A23) counted among the steps without one; a `priming.complete` on a step C2 shows not conditioned (before A26) is flagged and the end of priming is the first conditioned primed C2 step | no two consecutive steps without a new plan (REQ-DRIVING-001 as amended), none doubled, capture stamp = frame × 100 ms | **SUPPORTED C10, C9, C2** |
| 002 | S1 | 002 | sampled `out.plan` {runRecord, samples[].acceleration/.curvature}; `run_record.checkpointSha256`; `score/referenceInference.jsonl`; `bundles` | compare every sampled plan with the offline inference of the pinned checkpoint on the retained bundle | every acceleration and curvature within 1 % of the signal's largest magnitude in that plan; every sampled step has its bundle and reference | **SUPPORTED C11, C2** (sampled steps only: 12 of 637 plans on the nominal run) |
| 003 | S1 | 003 | `inputs.cameras[6]` {name, order, image_frame, capture_sim_ms, width, height, front_hi_res}; front high-resolution image | order, size, currentness | six 512×512 current images in order, plus the front at 1024×1024 | **SUPPORTED C2, A17, A11** — the six sizes and the front `front_hi_res` are per-step metadata; the images themselves are only in the sampled bundles, so the verdict is bounded to the producer's statement |
| 004 | S1 | 004 | `inputs.cameras[].history[7]` (frame indices) | ages = (step frame − history frame) × 100 ms | seven images at 0.5…3.5 s before the step (±1 ms) | **SUPPORTED C2** |
| 005 | S1 | 005 | `inputs.projections[]` {camera, matrix 3×4, image_size, images_covered}; `marker` {vehicleFrame, imagePx} | project the marker's vehicle-frame point through the operator; compare with its image position | one operator per image; error ≤ 2 px | **MISSING C2** — the operator is recorded; the marker's pixel and per-image coverage are not |
| 006 | S1 | 006 | `inputs.map_context_render_sim_ms`; `mapContext` {channels, width, height, geometry} | size, geometry tag, render age | 14 ch, 450×300, `autoe2e-bev-450x300-0p4m-v1`, rendered ≤ 500 ms sim before the step | **SUPPORTED C2, A11** — channels, size, tag and render age are decided per step from the producer's metadata; the raster itself is only in the sampled bundles |
| 007 | S1 | 007 | `inputs.routeMask` {channels, width, height, geometry, corridorCells, routeSha256, waypointsInWindow, waypointsOnCorridor}; `rasterPose`; `navigation/route.json` | geometry and route sha per step; every in-window count re-derived from the retained route file and the raster pose; on-corridor = in-window | two channels, right geometry, the run's route sha, the corridor covers every in-window waypoint, and at least one step has one | **SUPPORTED C2, A16, A11** — decided per step, with the A16 recount when the route file is retained; a left-right mirrored raster is not detectable from counts and needs the bundles |
| 008 | S1 | 008 | `inputs.ego_motion_history[64]` rows (speed, accel, yaw, curvature); world `egoPose` {x, y, yaw} of frames step − 65 … step; agent `rig` {result.origin} | each pose moved to the rig origin; speed = norm of `numpy.gradient` of the positions at 0.1 s, acceleration = `numpy.gradient` of that speed, rows [1:-1], as upstream's closed-loop driver works them out (A29); row j is frame step − 64 + j (the engine's newest row is step − 1); judged on plan steps only | 64 rows, oldest first, the newest 100 ms before the step; within 0.05 m/s and 0.1 m/s²; yaw rate and curvature 0 (REQ-DRIVING-008 as amended on 2026-11-10) | **SUPPORTED C1, C2** (no `rig` record: inconclusive) |
| 009 | S1 | 009 | `inputs.cameras[].history`; `out.ego_motion_sample` count and captureTime; adapter actuations; world speed | release frame = max(first step with 8 images per camera 0.5 s apart, first step with 64 samples) | no motion and no positive command before the release; motion after it | **SUPPORTED C1, C2, C9** |
| 010 | S1 | 010 | `inputs` history frame refs; ego rows; world tick existence | membership of every history element in the run's captures; duplicates per history; judged on plan steps only | every element names a capture record of the run; no record twice in one history | **SUPPORTED C2, C1** (caveat: ego rows are identified positionally, frame = step − 64 + k; the engine's newest row is frame step − 1) |
| 011 | S1 | 011 | `out.command` {planReference, step_capture_sim_ms}; `in.plan` {runRecord, producer}; world {controlSource, autopilotEnabled, trafficManagerEnabled}; `injection` {plan_inject} | chain command→plan→inference; every tick's control source; steering sign around the test plan | every command names its plan; no autopilot/TM/scripted control ever; sign reverses ≤ 100 ms after the test plan | **SUPPORTED C1, C8** |
| 012 | S1 | 012 | adapter actuations {acceleration, steeringAngle, actuationTime(sim)}; `run_record.vehicleConfiguration`; `injection` | clamp and rate check over every applied command, with an over-limit test plan in place | within max ±3.0/−8.0 m/s² and ±35°, rate ≤ 180 °/s | **SUPPORTED C7, C8, C9** |
| 013 | S1 | 013 | `inputs.cameras[].arrival_mono_ns`; `out.plan.productionTime` (mono); `priming.complete` (t_mono_ns, t_real_ns); `out.mode`; world {sim_ms, t_real_ns} | window = 60 s of wall clock from the end of priming; every plan in it made in kDriving and the plans span it; per plan: production − newest image arrival; real-time factor over the same window | RTF ≥ 0.95 over the window (else inconclusive); ≥ 99 % of plans ≤ 100 ms; no two consecutive misses | **SUPPORTED C2, C9, C10, C1** |
| 014 | S1 | 014 | agent `out.plan`/`out.command`, adapter `in.command`, actuation planReference; `injection` {comm_stop} | match every actuation to its plan through the S-CORE records; look for plan-derived actuations after the stop | every actuation matched; none computed from a plan after the stop | **SUPPORTED C8, C9** |
| 015 | S1 | 015 | `out.plan` {frameIndex, productionTime}; observer `in.operational_state` of kind 1 (ICD A34) {plan_production_mono_s/_ns, plan_producer, plan_sample_count, plan_horizon_s, arrays, plan_reference}; publisher `out.operational_state` of kind `PLAN` {envelope t_mono_ns, plan_frame_index} (written after the send, ICD A34) | receipts per plan; publisher records per plan; publisher record − production (S-CORE monotonic; the message's `publish_mono` is the publisher's receipt, before the send, and ends no interval); published production time = the record's within 1 µs; array equality; producer equality | one receipt and one publisher record per plan, equal to its record, published ≤ 100 ms after production, over 60 s (records spanning less than 60 s: inconclusive; no publisher `PLAN` records: inconclusive) | **SUPPORTED C12** |
| 016 | S1 | 016 | `out.ego_motion_sample` (captureTime + `clocks`; speed, longitudinalAcceleration, lateralAcceleration, yawRate; **`arrival_mono_ns`, not written by the agent**); observer `in.operational_state` of kind 2 (ICD A34) {producer, sample_capture_ms, speed_kmh, longitudinal_acceleration, lateral_acceleration, yaw_rate_dps}; publisher `out.operational_state` of kind `VEHICLE_STATE` {envelope t_mono_ns, sample_capture_sim_ms} (written after the send, ICD A34) | receipts per step; publisher records per step; the four values against the record (same units: km/h, m/s², m/s², deg/s); publisher record − arrival (S-CORE monotonic; the message's `publish_mono` equals its `sample_receipt_mono`, the publisher's receipt, and ends no interval) | one receipt and one publisher record per step, each value within 1e-3 of its record, published ≤ 100 ms after the arrival, over 60 s (records spanning less than 60 s: inconclusive); a definite problem fails; without the arrival: inconclusive, naming the field and C13 | **MISSING** the arrival (C13; C9 recorded) |
| 017 | S1 | 017 | observer `in.operational_state` of kind 3 (ICD A34) {t_real, mode, cause, producer, publish_mono_s/_ns, last_plan_capture_ms, step_capture_ms, last_plan_production_mono_s} | every receipt of the run, not the first 60 s: they span at least 60 s (the least the criterion's window needs) and show priming (kStarting), driving (kDriving) and a stop (kStopResponse or kStandstill); consecutive gaps over the whole run; mode, cause while stopped, plan age, producer and time on every receipt; the plan age is reported while driving (before the first plan `last_plan_capture_ms` is 0, so the difference is no age) | no gap > 200 ms anywhere in the run; every publication holds the mode, the cause while stopped and the age of the newest valid plan; receipts spanning less than 60 s, or showing no priming, no driving or no stop: inconclusive, naming what is absent | **SUPPORTED C5** |
| 018 | S4 | 018 | four runs: plan samples, command {acceleration, steeringAngle}; `run_record` {campaignId, runRole, inputReplay.digest} | max-abs per signal (accel, curvature, cmd accel, cmd steer) on plans/commands present in both, and the number of plans and of commands present in one run only; compare with ref2 vs ref1; a signal a run holds no record of is not comparable (inconclusive); report every number | late and stopped differ from ref1 by no more than ref2 differs | **SUPPORTED C4** (campaign) |
| 019 | S4 | 019 | `inputs.cameras[].arrival_mono_ns`; `out.plan.productionTime`, per run; run roles | 99th percentile of planning time per run; largest pairwise difference | ≤ 10 ms between any two of the four | **SUPPORTED C2, C4** (campaign) |
| 020 | S3 | 020 | `stop_response.begin` {capture_sim_ms}, `stop_response.standstill`; actuations {acceleration, actuationTime(sim)}; world speed at T0 | commanded deceleration over [T0, standstill]; entry speed | −4 m/s² ± 0.2 from the start of the stop to standstill, in runs entered at 10 and at 20 m/s | **SUPPORTED C1, C9** |
| 021 | S3 | 021 | last applied actuation before T0 {steeringAngle, planReference}; actuations [T0, standstill] | compare each stop steering command with the last valid-plan value | equal (1e-6°) from the start of the stop to standstill | **SUPPORTED C9** |
| 022 | S3 | 022 | world speed after standstill; actuations after standstill; `out.plan.captureTime` of the plan each command names | speed to the end; plans made after T0; commands that pull | speed < 0.1 km/h to the end; no command from a plan captured after T0; no positive command after standstill | **SUPPORTED C1, C9** |
| 023 | S3, S1 | 023 | `inputs.cameras` {valid, status, capture_sim_ms}; `mergedFrames`; `priming.complete`; `out.mode`; `stop_response.begin` {capture_sim_ms, cause} | both halves: a camera condition per the README reading (no valid image to date, invalid, or newest image > 200 ms old); baseline = first condition at a step at or after priming.complete while kDriving (README, Readings) | no camera-caused stop without a condition in the 100 ms before it; the stop begins ≤ 100 ms sim after the baseline, with its cause. Without a baseline: S1 passes, S3 is inconclusive | **SUPPORTED C2, C10** |
| 024 | S3 | 024 | `out.ego_motion_sample` {captureTime(sim) + `clocks`, record order, speed null}; `stop_response.begin` | baseline = first step whose sample is non-finite or older than 200 ms | stop begins ≤ 100 ms sim after the baseline, cause kMotionInvalid/kMotionStale | **SUPPORTED C9** |
| 025 | S3 | 025 | `route_provider out.route_announcement` {issueTime(sim) + `clocks`, corridorPoints}; `stop_response.begin` | baseline = first step the newest announcement is > 1 s old, or the empty-corridor announcement | stop begins ≤ 100 ms sim after the baseline, cause kRouteStale/kRouteEmpty | **SUPPORTED C9** |
| 026 | S3 | 026 | `out.command` {step_capture_sim_ms, plan_capture_sim_ms}; `in.plan` (commander view: captureTime, sampleCount, finiteness); `stop_response.begin` | age = command step_capture_sim_ms − newest valid plan capture stamp, at each command | stop begins ≤ 100 ms sim after the age first passes 300 ms, cause kPlanStale | **SUPPORTED C3, C9** |
| 027 | S3 | 027 | `injection` {plan_inject, t_sim_ms, detail.invalid}; `in.plan`; `stop_response.begin`; commands by planReference | baseline = the invalid plan's arrival; look for a command naming it | stop ≤ 100 ms sim after arrival, cause kPlanInvalid; no command computed from it | **SUPPORTED C8** |
| 028 | S1 | 028 | actuations {stopInForce, cause, actuationTime(sim), planReference} | stop-in-force − last applied command | ≤ 300 ms sim (A24), cause kCommandTimeout, and the stop held to the end: every adapter `out.vehicle_control` from the stop on has trigger `stop` (none recorded: inconclusive) | **SUPPORTED C9** |
| 029 | S1/S3 | 029 | `stop_response.begin` {t_mono_ns}; publisher `out.operational_state` of kind `HEALTH` (ICD A34) {envelope t_mono_ns (written after the send), mode, cause} | publisher record of the first stopped health with the stop's cause − stop begin, both on the S-CORE monotonic clock (the message's `publish_mono_ns` is the time it was made, before the send, and ends no interval); every later record's mode | stop published ≤ 100 ms monotonic after the stop, with that run's cause; all later healths stopped | **SUPPORTED** (monotonic at the publisher, per the S5 answer) |
| 030 | S1 | 030 | `inputs.cameras[].capture_sim_ms`; `out.ego_motion_sample` {captureTime + `clocks`} | every image and sample stamp marked as simulation time | every stamp present and marked `simulation` (suffix or `clocks`) | **SUPPORTED C2, C9** |
| 031 | S1 | 031 | `out.plan` {captureTime + clock, productionTime + clock} | the two stamps and their marks | capture time marked simulation; production time marked monotonic; both present on every plan | **SUPPORTED C9** |
| 032 | S1 | 032 | actuationTime(sim), plan.captureTime(sim), plan.productionTime(mono), `inputs.cameras[].arrival_mono_ns`, adapter `in.command` t_mono | input age at actuation and planning interval (sim); planning time and transport delay (mono); no mixed-domain quantity | for every command all four computable from stamps of one domain; commands joined to the adapter's `in.command` by productionTime, never by planReference (stop commands share one); no range (the model states none), values reported | **SUPPORTED C2, C9** |
| 033 | S1 | 033 | `run_record` {writtenAtMonoNs, checkpointPath, configurationPath, vehicleConfiguration, navigationMap, route}; retained files | record write time vs first plan; SHA-256 of every named file vs the recorded value | record precedes the first plan; hashes equal; source revision named | **SUPPORTED C7** (the checkpoint copy is one per campaign; the evaluator resolves it next to the run) |
| 034 | S1 | 034 | `out.plan.runRecord`; SHA-256(run_record.json)[:16] | equality per plan | every plan names this run's record | **SUPPORTED** (run record frozen before the first plan) |
| 035 | Ref. | 035 | absence of `out.plan`; world speed; observer `in.operational_state` of kind 3 (ICD A34) {cause, checkpoint_expected_sha256, checkpoint_actual_sha256, refusal_reason}; agent `error` | no plan produced; vehicle at rest in every world tick (no tick: inconclusive); the refusal names the reason of the run's start, `checkpointCase` mismatch: `mismatch` with both SHA-256, unpinned: `no_pin` (another reason fails; another start is inconclusive) | no plan, standstill to the end, health names the mismatch (or the missing pin) | **SUPPORTED C6, C1** |

## 2. Against ICD v2

**33 SUPPORTED, 2 MISSING.** The cases below are the whole remaining gap. Each
is inconclusive, never a pass, and names the field in `missing`.

| VC | Missing field | Producer | What would close it | Bundles needed |
|---|---|---|---|---|
| VC-DRIVING-005 | `checkpointInputs.marker.image_px` (and per-image operator coverage) — A11 logs the producer's marker pixel, but the case needs where the marker actually appears | `drivingAgent/conditionInputs` + a measured image | measure the marker in a bundle image, independently of the operator | 1 bundle at frame 300 of the nominal run, all six cameras valid; a person measures the marker in each image |
| VC-DRIVING-016 | `out.ego_motion_sample.arrival_mono_ns` — when the world snapshot the motion sample comes from arrived at the agent (whole nanoseconds, S-CORE monotonic, `clocks.arrival_mono_ns = "monotonic"`). The criterion counts from when the driving system received the sample; the agent's record carries no arrival time (ICD A34), and the frame store may hold a sample up to 95 ms before the agent hands it on | `drivingAgent` (`agent/cc/agent_ffi.cpp`, `out.ego_motion_sample`); the frame store knows it (`FrameView::snapshotArrivalMonoNs`, `agent/cc/frame_store.h`) | the agent writes the arrival in its record of the sample: change **C13**, proposed, not in ICD v2 | none |

VC-DRIVING-003, VC-DRIVING-006 and VC-DRIVING-007 were removed from this table by the ICD
amendments, in `gaps.AMENDMENT_CHANGES`: A11 adds the per-step `mapContext`,
`routeMask` and `front_hi_res`; A16 adds the waypoint counts and the raster
pose, so the in-window count is re-derived from the route file; A17 fixes what
a camera `width`/`height` means. They are decided by `cases.py` now, with the
limits stated in their rows (the producer's metadata, the sampled bundles, and
the mirrored-raster blind spot of counts).

### Bundle ledger (C2 sampling: every 50th step, plus ±0.5 s around a fault)

| Run | Steps | Bundles | Sampled plan steps VC-DRIVING-002 can judge |
|---|---|---|---|
| nominal | 700 | 14 (frames 0, 50, …, 650) | 12 (frames 100, 150, …, 650) |
| fault-camera_missing / fault-plan_stale / stop-entry10 / stop-entry20 | 400 | 18 (0…350 every 50, plus 245…255) | 8 (100, 150, 200, 245…249) |
| comm-stop | 620 | 23 (0…600 every 50, plus 495…505) | 21 |
| aaos-ref1/ref2/late/stopped | 350 | 7 (0…300 every 50) | 5 (100…300) |

VC-DRIVING-002 is judged on the nominal run and therefore needs **12 sampled plan
steps, frames 100–650 every 50, with their bundles and the matching
`referenceInference` entries**. A sampled step whose bundle or reference entry
is absent is `inconclusiveMissingEvidence`, naming C2/C11 — never a pass. The
case's verdict is bounded to those 12 plans; `measured.coverage` says so.

VC-DRIVING-005 needs **1 bundle, frame 300 of the nominal run** (all six cameras
valid); a person measures the marker in the image and the case compares that
with the operator.

## 3. The world-side record the simulator host must log

`simulator/world.jsonl` is the only record of what actually happened to the
vehicle. ICD v2 C1 gives it field definitions; it records **no image digest**,
because the pacer does not receive images.

| Observable | Why a case needs it | ICD v2 |
|---|---|---|
| `frame`, `sim_ms` | every simulation-time computation; duplication check | field names fixed (C1) |
| `egoPose` {x, y, yaw} | BEV projection (007), route coverage, standstill (022), the ego-motion history (008: the poses of each plan step's 66 frames) | field names fixed (C1) |
| `velocity` {speed_mps, heading_rad} | standstill thresholds (009, 022), entry speed (020) | field names fixed (C1) |
| `acceleration` {longitudinal_mps2, lateral_mps2} | no case reads it: VC-DRIVING-008 works acceleration out of the poses (A29) | field names fixed (C1) |
| `angular_velocity` {roll, pitch, yaw_rad_s} | no case reads it: the history gives yaw rate and curvature as zero (REQ-DRIVING-008) | field names fixed (C1) |
| `lane` {road, lane, lat_m, junction} | lane context; no case judges it yet | field names fixed (C1) |
| `control` {throttle, brake, steer, accelMps2} | what was applied, at which tick (011, 012, 020) | field names fixed (C1) |
| `controlSource` ∈ {actuationAdapter, autopilot} | "no autopilot, traffic-manager, recorded or scripted control reached the actuation" (011) | C1 |
| `autopilotEnabled`, `trafficManagerEnabled` | the negative half of 011, per tick | C1 |
| `sensors[]` {name, actor_id, alive, attached} | camera rig health; **no capture time** — staleness comes from C2 | C1 |
| `collisions[]`, `laneInvasions[]` | no case reads them; they bound the claim | named as lists, no element spec |
| `rtf` (or the pair that gives it) | REQ-DRIVING-013's ≥ 0.95 condition; derivable from `sim_ms` and the envelope `t_real_ns` | derivable |

Two worlds are needed: the simulator host writes ticks for SC-DRIVING-001 and
SC-DRIVING-003; for SC-DRIVING-004 (replayed inputs) there is no simulator and no
`world.jsonl`, and VC-DRIVING-018/VC-DRIVING-019 must not require one.

## 4. What the recordings must show

The recordings decide no case; they are the corroboration a reviewer uses when
a log says "the vehicle stopped" and a person wants to see it.

- `simulator/view.mp4` (chase view, NVENC): the vehicle on the mapped route
  while `world.jsonl` reports the route progress; the stop response as a
  visible deceleration; the standstill with the vehicle stationary. All three
  from the same run, with the clocks the run record names.
- `guest/ivi_screen.mp4` (screenrecord of the IVI VM): the observer showing
  the plan, the vehicle state and the health it received over SOME/IP,
  including the stop publication of REQ-DRIVING-029.
- `terminals/*.cast` (asciinema): the Launch Manager starting the programs, the
  route provider announcing, and the bench's acts with the instant they
  happened. A recording is not a record: no case can be judged from it.
- One thing a person must *measure* on a bundle image: the reference marker's
  pixel in each camera image (VC-DRIVING-005). A logged `marker.image_px` turns it into
  arithmetic.

## 5. The ICD v2 records, and what each supplies

| Change | Record | Cases that need it |
|---|---|---|
| **C1** | `simulator/world.jsonl`: sensors, ego kinematics, control source | 008, 009, 011, 020, 022, 035 |
| **C2** | `score/checkpointInputs.jsonl` per step + `score/bundles/*.npz` sampled | 002, 003, 004, 005, 006, 007, 008, 009, 010, 013, 019, 023, 030, 032 |
| **C3** | `out.command` {step_capture_sim_ms, plan_capture_sim_ms} | 026 |
| **C4** | `run_record.json`: campaignId, runRole, scenarioVariant, inputReplay | 018, 019 (campaign), 020–022, 035 (run grouping) |
| **C5** | HEALTH 36–39 (`last_plan_capture_ms`, `step_capture_ms`, plan production stamps) | 017 |
| **C6** | HEALTH 41–43 + drivingAgent `error` | 035 |
| **C7** | `run_record.json`: checkpoint/config/vehicle/map/route paths + SHA-256, write times | 012, 033 |
| **C8** | `bench/injection.jsonl` | 011, 012, 014, 027 |
| **C9** | section 6 clock suffixes and `clocks` objects | 001, 009, 012, 013, 014, 016, 020, 021, 022, 024, 025, 026, 028, 030, 031, 032 |
| **C10** | `priming.complete` | 001 |
| **C11** | `score/referenceInference.jsonl` | 002 |
| **C12** | PLAN 16–18 (`plan_producer`, `plan_sample_count`, `plan_horizon_s`) | 015 |

The list is derived from the evaluators' `needs`; `tests/test_gaps.py`
asserts the two agree.

VC-DRIVING-008 also reads the agent's `rig` record (`result.origin`: the
origin of the camera rig, in vehicle axes, metres), which drivingAgent logs
once before the first step (A29). It is no ICD change, so no change id names
it; a run without it leaves the case inconclusive.

## 6. Cases that cannot be decided from logs alone

| VC | Why | What would decide it |
|---|---|---|
| 002 | the case *is* an inference: the pinned checkpoint must be run again on the recorded inputs. A log reader can only compare a plan with a retained reference inference (C11) on the retained bundles. | the C11 artifact; and, for the every-plan claim, a bundle for every plan step (C2 samples) |
| 005 | needs where the marker *appears* in each image; A11 logs `marker.image_px`, but that is the producer's own statement | a measured `marker.image_px` in a retained bundle image, taken independently of the operator |
| 033 (second half) | "another engineer checks out the named source revision" is an act, not a record | a signed re-derivation entry (`independentObserverIdentity`) |
| 011 (negative half) | "no recorded, replayed or scripted control reached the actuation" is a statement about absence | `controlSource`/`autopilotEnabled`/`trafficManagerEnabled` per tick (C1), plus the recording |
| 018 / 019 | "differ by no more than" fixes no metric. The evaluator fixes max-abs per signal on the produced plans and commands, counts the plans and commands one run holds and the other does not as a difference, and reports every number so a reviewer can re-judge. | the owner's metric recorded in the case (the S5 answer chose max-abs per signal) |

No case is decided by a recording. `view.mp4` cannot show that a plan was
produced in 30 ms, and `ivi_screen.mp4` cannot show a publish time.

## 7. Open questions for the owner

1. **C2's remaining field.** One case needs one small addition to the
   per-step metadata: the marker pixel (VC-DRIVING-005), measured independently of the
   operator. A11 already logs the producer's `marker.image_px`; the open
   question is whether a measured value from a retained bundle image is
   acceptable, or the producer's value should be compared with a second,
   independent measurement.
2. **The bundle key convention.** C2 says `score/bundles/<frame>.npz` holds
   "the tensors as handed to the checkpoint" but names no keys. The A11/A16/A17
   metadata now decides VC-DRIVING-003/VC-DRIVING-006/VC-DRIVING-007 without the tensors,
   but VC-DRIVING-005 still needs a
   bundle image; a key list (or a manifest) would make that sample auditable.
3. **VC-DRIVING-002's scope.** With sampled bundles the case proves 12 of 637 plans on
   the nominal run. Is a bounded verdict acceptable for REQ-DRIVING-002, or must the
   campaign retain a bundle for every plan step of one designated run?
4. **VC-DRIVING-033's checkpoint.** C7 retains one checkpoint copy per campaign. The
   evaluator resolves it next to the run; if the campaign directory is not
   mounted at evaluation time, VC-DRIVING-033 is inconclusive on that one hash.
5. **Route completion is not verified by any case.** SC-DRIVING-001's claim
   ("the vehicle is driven along the route") rests on the recording, not on a
   VC. Is a case wanted, or is it a claim boundary?
6. **The 10 and 20 m/s pair of REQ-DRIVING-020** must be the same fault and the same
   route with only the entry speed differing; the case documentation does not
   say which fault. The fixture uses the camera fault for both.
