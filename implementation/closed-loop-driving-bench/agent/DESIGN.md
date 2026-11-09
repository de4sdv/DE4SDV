# drivingAgent: design (slice 10b, WP2)

The FEO agent of phase 8 (`DrivingAgentApplication`): one process on the S-CORE host, one FEO primary agent (`signalling_direct_mpsc`), four activities in one chain on one worker, each a Rust shell over a C++ library. The interfaces are in `../interfaces/ICD.md`. This file fixes the inside of the agent.

## Chain and pacing

```text
LibCarla threads ──(frame set N complete, or its deadline)──► datagram to FEO_PACE_SOCKET
FEO scheduler (event-trigger patch): wake → drain → one chain:
  0 conditionInputs ─► FEO topic driving/inputs (InputsMsg) + driving/condition (ConditionMsg) + driving/ego (EgoMsg)
                       └► mw::com ego_motion_sample
  1 inferPlan       ─► FEO topic driving/plan (PlanMsg)                 └► mw::com plan
  2 superviseLoop   ─► FEO topic driving/valid_plan + driving/mode      └► mw::com mode
  3 commandVehicle  ─► mw::com command (to the actuation adapter)
dependencies: 1←0, 2←1, 3←2 (and 3←0 for the ego sample)
```

## Frame store (C++, process-global, in `agent_common`)

- **Ring of 8 slots.** Each slot is keyed by the CARLA world frame number. It holds:
  - six camera images: BGRA bytes, width, height, fov, image frame number, arrival monotonic ns;
  - the hero's snapshot of that frame: transform, velocity, acceleration, angular velocity, arrival monotonic ns;
  - the rasters (`map_context`, `route_mask`), filled by `conditionInputs`.
- **When a slot is ready:**
  - Normally, when its snapshot and all six images are in.
  - Otherwise at a deadline of 95 ms of monotonic time after its snapshot arrived. This lets a missing or late camera become an input condition (REQ-DRIVING-023) instead of a stall.
  - A ready slot sends one datagram to the pace socket.
- **Slot ownership:**
  - LibCarla callbacks write only into slots that are not ready.
  - `conditionInputs` takes the newest ready slot and locks it until `inferPlan` releases it.
  - Older ready slots are counted as skipped.

## conditionInputs (input activity)

- **startup:**
  - connects the client to the simulator host and waits for the hero (role_name `hero`);
  - finds its six cameras by role_name `cam_front`, `cam_front_left`, `cam_front_right`, `cam_rear_left`, `cam_rear`, `cam_rear_right`, the names the world-side rig gives them, and `Listen`s;
  - registers `OnTick`;
  - loads the map and route through the navigation library (S3);
  - offers the mw::com `ego_motion_sample` skeleton.
- **step:**
  - takes the newest ready slot;
  - computes the capture times from the frame index (`CaptureTimeMicros`; each camera's own image frame number gives its capture time);
  - updates the camera history (per camera, the frame references the checkpoint's history layout needs) and the 64-row ego-motion history;
  - gives the checkpoint the history's yaw rate and curvature as zero (REQ-DRIVING-008 as amended on 2026-11-09, GAP-DRIVING-010; the owner's history-mask decision of 2026-11-09). It is upstream's own closed-loop check (`experiment/closed-loop/replay_driver.py`: `egomotion[:, 2:] = 0`), applied to the raw [speed, acceleration, yaw rate, curvature] rows before `adapt_egomotion_history`. The measured yaw rate still goes into the published ego-motion sample and the C1 world record; C2 records the zeroed copy the checkpoint took, as REQ-DRIVING-008's criterion reads it. CL5 showed the effect: lane kept, clean stop/restart at a light, but straight on at a left-turn junction;
  - rasterizes the route and the map at the ego pose of the step;
  - fills the input condition, one bit per cause of REQ-DRIVING-023 to -025;
  - writes the FEO topics;
  - publishes the ego-motion sample (VSS units) on mw::com.
- **Frame of the motion sample:** CARLA's velocity and acceleration are rotated into the vehicle frame. The signs follow the model's VSS signals: yaw rate positive to the left, CARLA's z angular velocity negated, in deg/s.

## inferPlan (inference activity, embeds CPython)

- **startup:**
  - `Py_InitializeFromConfig` with `executable` set to the pinned venv's python and `install_signal_handlers = 0`, so FEO keeps SIGINT/SIGTERM;
  - imports `de4sdv_planner`;
  - `setup(config)`:
    - checkpoint SHA-256 against the configuration, refusing on a mismatch or a missing name (REQ-DRIVING-035);
    - cuDNN version check;
    - load with the runtime patches;
    - warm-up;
    - parity on the recorded sample;
    - `run_record.json` (REQ-DRIVING-033).
  - After `setup`, the GIL is released.
- **On refusal:** the activity starts but never plans. superviseLoop reports `kRefused` with `kCheckpointRefused`, and the commander commands the stop response from the first step.
- **step:**
  - `PyGILState_Ensure`;
  - `step(slot view)`: memoryviews over the slot's image buffers, the histories and the rasters; capture-safe preprocessing; the model call; the controls integrated into the pose;
  - returns 64 × (a, κ, x, y, ψ);
  - C++ fills `PlanMsg`/`DrivingPlanPayload`, stamped with the capture time of the newest image of the step and the production monotonic time (REQ-DRIVING-031), and the run record (REQ-DRIVING-034);
  - publishes it on the FEO topic and mw::com.
- **while the agent primes:** `warm(frame)`, no plan (see "Warm-up while priming" below).

## superviseLoop

- Judges per step:
  - the input condition (REQ-DRIVING-023 to -025);
  - the plan: 64 finite pairs (REQ-DRIVING-027);
  - the plan's age against the step: a plan older than 300 ms of simulation time from the capture of its newest image (REQ-DRIVING-026).
- Passes the newest valid plan on, decides the mode (latching) and publishes it on both channels. It issues no command.

## commandVehicle

- The mode is driving:
  - Take the newest valid plan's sample at `k = round((step capture time − plan capture time) / 0.1 s)`, clamped to 0..63.
  - `acceleration = a[k]`.
  - `steeringAngle = deg(atan(wheelbase · κ[k]))`.
  - Limits and steering rate come from the vehicle configuration (REQ-DRIVING-011, -012).
  - This is the configured command law `first_control`. A `pure_pursuit` law on the integrated path, with the speed from the current motion sample, is the alternative if the closed loop oscillates; the run record names the law.
- The mode is stop:
  - `acceleration = -4`, with the steering held at the last value computed from a valid plan (REQ-DRIVING-020, -021);
  - the same at standstill (REQ-DRIVING-022; the adapter holds the brake).
- REQ-DRIVING-026 is checked again at the command.
- Publish on mw::com `command`, stamped with the plan reference and the issue monotonic time (REQ-DRIVING-032).

## Process

- **Rust main:**
  - `de4sdv_agent_init(config_path)`, before the primary starts: the configuration and the run logs; the engine (`setup`: the pin, load, compile, warm-up, parity; or the refusal); with `source = carla` the attach to the world side's hero; the run record; then the mw::com runtime with the manifest and the offers;
  - builds the four activities on worker 40;
  - `PrimaryConfig { cycle_time: 100 ms (unused with the pace socket), timeout: 5 s, startup_timeout: 30 s }`. FEO waits for each activity's ready signal with `timeout`, so no startup may take 5 s (see stage 2).
- **Environment:** `FEO_PACE_SOCKET=/tmp/de4sdv_feo_pace.sock`, `LD_LIBRARY_PATH` = the uv CPython lib dir.
- **Logs:** `<run_dir>/score/drivingAgent.jsonl`. Every activity writes its `in.`/`out.` records, and the scheduler's `FEO_PACE` lines go to stderr, captured as `drivingAgent.stderr`.

## Decisions taken while building (2026-11-09)

- **Activities and data:**
  - The FEO topics carry `#[repr(C)]` mirrors of the C structs in `cc/agent_ffi.h`.
  - The plan travels as a byte-identical `DrivingPlanPayload`. The agent compares the C and Rust sizes at start and refuses to run on a difference.
  - Images, tensors and histories stay behind the FFI.
- **Embedded planner:**
  - The interpreter starts in `de4sdv_agent_init` on the main thread, and `setup` builds the engine there (stage 2). inferPlan's startup binds the engine to worker 40 (`bind_thread`). conditionInputs calls `de4sdv_planner.condition` for the GPU tiles, the camera history and the ego-motion rows; inferPlan calls `infer`. Both run on worker 40 under the GIL, so torch's thread-local autocast region, entered by `bind_thread`, holds.
  - Images reach Python as memoryviews over the frame-store buffers. They are released after every call; a view still exported fails the call.
- **Ego-motion history:**
  - Computed from the REF poses of frames k−65 … k with the CL harness's differences (`numpy.gradient`, rows `[1:-1]`, so the newest row is frame k−1). It is bit-identical with the harness: maximum difference 0.0 over 200 random trajectories (`python/tests`).
  - The pose of a frame comes from the hero's world snapshot of that frame, where the harness used the front image's sensor transform: the same matrix up to float32 rounding.
- **Rasters:** S3's library renders them at the step's REF pose in C++ (`cc/navigation_input`, stage 2) and hands them to the planner as float32 buffers. The camera-only context is used when they are absent.
- **Commander:**
  - `pure_pursuit` takes its acceleration from `a[k]`, as `first_control` does; no speed controller is added.
  - A stop command issued without any valid plan names `planReference = "none"`.
- **Manifests:** each process's manifest is checked against the ICD's service table (`interfaces/tests/test_mw_com_manifests.py`). It caught the state publisher's swapped 7401/7402.

## Stage 1b: the decision logic and the frame store in the agent (2026-11-09)

- **Units:**
  - `cc/agent_logic` covers input conditions, supervision, the commander and the records the evaluators read.
  - `cc/frame_store` and `cc/pace_signal` cover the slots and the pace datagram.
  - Both are pure C++17 with their own tests: `cc/tests/run_tests.sh` runs them plain, with sanitizers (address, undefined behaviour, thread), the records check against `case-evaluators`, and `--mutations`.
  - `cc/rig.h` holds the one camera count both share.
  - The rule-to-code maps are in `cc/agent_logic.md` and `cc/frame_store.md`.
- **Stop reference:** a stop command names the plan its held steering was computed from, frozen when the stop begins. It is `none` when no driving command was ever computed (ICD section 4; REQ-DRIVING-011, -021; VC-DRIVING-022).
- **Cause order:** one cause per stop, in pipeline order (ICD section 4):
  1. the input conditions;
  2. an invalid plan that arrived in this step;
  3. the age of the newest valid plan.
- **Frame store use:** conditionInputs takes the newest ready slot. It releases the slot after the planner has copied the images, so no slot outlives its step. A step with an input condition is not conditioned and not inferred; the stop starts instead.
- **Run record (ICD section 8):** `de4sdv_agent_init` writes it once through `de4sdv_planner.write_run_record`, after the engine and the attach (stage 2; stage 1b wrote it in inferPlan's startup).
  - Its identity is the first 16 hex digits of the record's SHA-256, computed with Python's `hashlib`.
  - `runRecord` and every `planReference` use that identity.
  - A refused checkpoint still writes the record; the bridge's `module_ready_` is separate from `started_`.
- **Refusal:** `kRefused` from the first step and no plan. Every command is the braking stop command naming `none`, which keeps the vehicle stopped (VC-DRIVING-035). There is no `stop_response.begin` record: the refusal is a mode, not a stop.
- **Records:**
  - C2 is `out.checkpoint_inputs` in the shape `runio.input_steps` reads: per camera the `name`, image frame, capture and arrival stamps, `valid`, `status` and history; `ego_motion_history`; `input_conditions`.
  - The commander logs its view, `in.plan`, whenever the newest valid plan changes.
- **Stage 1b found and fixed:**
  - the stage-1a C2 record had the wrong event name and field names;
  - plans named the stage instead of the run identity.
- **Open:**
  - `Supervisor::EndRun` is not called at shutdown. A `kRunEnd` stop record at the end of a nominal run would enter the stop-window evaluators; the bench controller's run end decides this.
  - ~~The LibCarla source must convert CARLA's angular velocity (deg/s) and its axes to the snapshot's convention before the frame store sees it.~~ Done in stage 2 (`cc/ego_motion.h`).

## Stage 2: the engine before FEO, the CARLA source and the route channel (2026-11-09)

- **Engine before FEO.** The G4 run of 14:35 UTC failed: FEO aborted after 5 s (`Timeout(5s, "waiting for ready signal")`) while inferPlan's startup built the engine for 57 s. FEO's startup loop waits for every ready signal with the receive timeout (`timeout`, 5 s); `startup_timeout` only bounds the whole loop. So:
  - `setup` runs in `de4sdv_agent_init` (main thread) before the primary starts; a refused checkpoint is decided there too;
  - inferPlan's startup calls `bind_thread` on worker 40: it enters the persistent no_grad + bf16 autocast region on that thread and makes three timed calls per context on fresh caches (the thread's first cuBLAS and cuDNN use); the stub engine reports the thread;
  - the frame source starts in conditionInputs' startup, after the engine, so no pace datagram queues up during the build.
- **CARLA source (`cc/carla_source`, LibCarla 0.9.16):**
  - Attach, before FEO starts: connect, wait for the actors with role names `hero` and the six `cam_*` (sensor.camera.rgb, parent = the hero), read their sizes and fov. The world side spawns them; the agent never spawns, ticks or controls.
  - The rig comes from one world frame. The wheels come from `GetPhysicsControl` (an RPC), the matrices from the snapshot; the read counts only if the RPC returned within 50 ms of the tick and no newer tick arrived meanwhile. In the synchronous world nothing moves between ticks.
  - Start (conditionInputs' startup): `Listen` on the six cameras (BGRA, frame index, fov) and `OnTick` for the hero's `ActorSnapshot`, both into the frame store; a 5 ms thread sweeps the deadlines.
  - Rig gate: with CARLA as the source, a camera mount read back more than 10 mm off the profile (set_rig's `rig_pose_err_mm`) fails the startup.
  - The run record's `simulatorBuild` is the server's version (`GetServerVersion`).
- **Kinematics (`cc/ego_motion.h`, tests/ego_motion_test.cpp):** CARLA's world velocity and acceleration rotated into the vehicle frame with `GetMatrix`'s axes; the published sample in VSS signs (ISO 8855: lateral acceleration and yaw rate positive to the left), so CARLA's y and z enter negated. Stage 1b's conversion did not negate them; the fake world drove straight with zero yaw and hid it. The checkpoint's rows come from the REF poses in Python and were not affected. The test is RED (4 failures) on the stage-1b signs.
- **`world_from_vehicle`** carries the rotation (stage 1b passed the translation only).
- **Route channel (`cc/route_listener`, `cc/navigation_input`):**
  - The listener keeps the newest valid `RouteAnnouncement` (272 bytes, interface version 2) from 127.0.0.1:47110; wrong sizes and versions are counted and dropped.
  - A new file or SHA-256 loads the route; the file's SHA-256 must equal the announced one. An announcement without a corridor withdraws the route (route_empty).
  - The raster pose is the harness's: REF from set_rig's origin, `x = p.x`, `y = -p.y`, `yaw = atan2(-fwd.y, fwd.x)`.
  - `set_rig` runs in conditionInputs' startup, so the origin exists at the first step (the route condition needs the raster, the raster needs the origin).
  - C2 gains `map_context_render_sim_ms`, `destination_cell_count`, `mapContext` {channels, height, width, geometry}, `routeMask` {channels, height, width, geometry, corridorCells, routeSha256, waypointsInWindow, waypointsOnCorridor}, `rasterPose` and `render_ms`: the fields OBSERVABLES.md lists as missing for VC-DRIVING-006 and -007.
  - Coverage uses upstream's geometry (`map_to_ego`, `ego_to_pixel`): the route's waypoints inside the window, 2 px clear of its edges and of the 10 m rear clip, must fall on corridor cells. Two mutations of the mapping (mirrored lateral axis, swapped axes) fail the test.
  - Without `nav_map` the route channel is the stand-in, and the stage label says `-route-stand-in`.
- **Fake world:** per-camera sizes from a rig file (`fake_rig`, from `scripts/make_fake_rig.py`: the profile-exact rig at 1920 px), and `fake_route` to drive along a route's centre line.

## Warm-up while priming (2026-11-09)

- **What the G4 run showed.** The checkpoint planned in 119 ms per call (91 ms in setup), only in bursts of 5, each followed by 67 frames without a plan; the supervision stopped on `kPlanStale`.
  - The checkpoint keeps one camera history cache stream per 100 ms phase. A call is warm only when its stream holds the 7 history frames and its last commit was exactly 0.5 s earlier. Otherwise the model re-encodes the 7 history frames from the raw tiles: cold, longer than a frame.
  - The first plan of each phase was cold, so the first five plans overran the 100 ms chain. The event trigger merged the backlog into one chain for the newest frame (`FEO_PACE`: 26 cycles with `skipped` > 0).
  - The merged frame was never conditioned, so the 66-pose ego history broke and the agent primed again for 66 frames, with every stream cold again.
- **The warm-up.** While the agent primes (camera history complete, ego history not yet), inferPlan calls `warm(frame)` and produces no plan:
  - One engine call on the frame's phase stream: the real tiles, projections and capture timestamp, the recorded sample's ego history and the camera-only context. The output is discarded.
  - The cache holds only the model's base camera pyramid of each frame; its signature is the stream's dimensions, dtype and device. The call therefore leaves the cache exactly as a planning call would.
  - `warmup.WarmupScheduler` decides. A call that keeps a warm stream warm costs less than a frame and runs. A call that primes a cold stream runs only when the lag it leaves stays within 50 ms; the lag is how far the chain start trails the 100 ms frame grid, measured at conditionInputs' calls.
  - The cost estimates come from bind_thread's calls (the first on a fresh cache is cold, the next two warm) and follow the measured calls.
  - The camera history needs 36 frames and the ego history 66, so the warm-up has 30 frames; by the first plan every stream is warm.
- **Records:** `warm` {frame, stream, warm: `warm` | `cold` | `skip`, reason, lag_ms, ms} for each decision once the camera history is complete; `stop` gains `warmCalls`. Each plan's `planner` record keeps `cache_before` (7 when the call was warm) and `counts`.
- **Tests (`python/tests/test_warmup.py`):**
  - A discrete-event model of the chain: one chain per frame event, the backlog merged into the newest frame, the cache rule.
  - Without the warm-up it reproduces the G4 failure: 5 cold plans, a merged frame, a 67-frame gap.
  - With it every plan is warm and no frame is lost, also under ±4 ms jitter.
  - The engine glue on fake caches. Six mutations of the scheduler and the glue fail the tests.
- **Not yet shown on the G4.** A merged frame still breaks the ego history; conditioning every merged frame is the next change.
