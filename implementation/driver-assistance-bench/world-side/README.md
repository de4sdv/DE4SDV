# World side and the calibrations (INC-DRIVING-002)

Status: draft, not yet validated. The unit tests pass on a fake CARLA; nothing here has run against CARLA 1.0.

## The problem

The bench judges VisionPilot's driving in SC-DRIVING-012 to SC-DRIVING-015 on CARLA 1.0. A run counts only if
the simulated world is set up as the model says and the run meets the entry conditions of its setting. The
candidate's own driving has to reach and hold the approach speed. Nothing but the candidate, through the actuation
adapter, may control the vehicle. Before the first judged run, two assumptions need a calibration run:
ASM-DRIVING-005 and ASM-DRIVING-006. The candidate's distance estimate also needs a camera calibration file that
matches the simulated camera.

This folder is the simulator host's part of that:

- `da_world_side.py`: the world side;
- `scenarios.py`: the settings and the entry-condition checks;
- `calibration.py`: the analyses and records of the two calibrations;
- `camera_calibration.py`: the camera calibration file.

Model sources (PSR = `driver_assistance_physical_software_realization.sysml`, NR =
`driver_assistance_needs_requirements.sysml`, both under `textual-notation-of-model/packages/features/driving/`):

- `DriverAssistanceSimulationServer`, `FrontCameraRig` and the step decision of 2026-11-17 (PSR);
- MAP-DRIVING-DA-CAMERA-IMAGE and MAP-DRIVING-DA-COMMAND (PSR);
- ASM-DRIVING-005 and ASM-DRIVING-006 (PSR);
- the terms `termsOfTheDriverAssistanceRequirements` and the comment `vehicleTargetCriteriaFixedInPhase5` (NR).

## What it does and does not do

It does:

- run CARLA in synchronous mode at a fixed step of 0.05 s. It paces the ticks on the wall clock, with a schedule
  of its own for each phase, and restores the settings at the end;
- spawn the hero (`role_name hero`) on a straight driving lane. The default vehicle is `vehicle.lincoln.mkz`,
  because CARLA 1.0 has no `vehicle.lincoln.mkz_2020` (PSR `FrontCameraRig`);
- attach the front camera (`role_name front`): 1920 x 1280, fov 50, `sensor_tick 0.1`, so one image per 0.1 s of
  simulation time. Its pose is upstream's (`Simulation/CARLA/ROS2/config/carla916.json:5-15`), converted to CARLA's
  frame as `config_carla.py:91-99` does it: x 1.544, y 0.0243, z 2.116 m, roll -0.10, pitch -0.11, yaw -0.23 deg;
- place the stationary target of SC-DRIVING-012, a `vehicle.tesla.model3` held by its hand brake, on the hero's
  lane, the distance ahead that the setting proposes;
- write a world record per tick (`simulator/world.jsonl`). Each tick has:
  - the simulation time, on the same clock as the adapter's snapshot time;
  - the ego and target poses and speeds;
  - the distance, the closing speed, the time to collision and the needed deceleration;
  - the hero's offset from the target's center line;
  - the vehicle control as the hero applies it;
  - the collisions and lane invasions;
- write a setting record per run, the entry-condition checks at its end, and a list of stalls (a tick started
  more than 0.2 s after the one before);
- run the two calibrations and the camera-calibration capture.

It does not:

- apply any control to the hero in a run of a setting or in the ASM-DRIVING-006 run. It never sets the autopilot
  and never creates a Traffic Manager. The candidate brings the hero from rest to the approach speed: "the own
  driving of the candidate holds them" (NR `vehicleTargetCriteriaFixedInPhase5`). It drives through the adapter
  from the first tick to the last, and no recorded, replayed, scripted or overlaid control reaches the actuation
  (the phase 10a case of REQ-DRIVING-038). The tests check this on the fake's per-client control log;
- set the candidate's `speed_limit`. Each setting proposes a value and the setting record states it. The
  candidate's configuration is another lane's;
- judge a criterion. The case evaluators do that from the records.

## Values and their source

| Value | Where | Source |
|---|---|---|
| Step 0.05 s, synchronous, paced | `STEP_S`, `Pacer` | model (PSR) |
| Front camera 1920 x 1280, fov 50, one image per 0.1 s, upstream's pose | `FRONT_CAMERA`, `FRONT_SENSOR_TICK_S` | model (PSR), pose from upstream's files |
| Hero `vehicle.lincoln.mkz` | `VEHICLE_CANDIDATES` | brief B7 (the model says only "another vehicle") |
| Roles `hero` and `front` | `HERO_ROLE`, `CAMERA_ROLE` | bench contract with the adapter and the camera interface |
| SC-DRIVING-012 at 20 (20-22), 42 (40-42), 60 (58-60) km/h | `scenarios.SETTINGS` | model (NR); the test reads the model file |
| Functional part, TTC 4 s, 0.2 m for 2 s | `scenarios.evaluate_entry` | model (NR) |
| "Travels straight": heading within 2 deg of the target's | `STRAIGHT_HEADING_MAX_DEG` | proposal |
| Target 150 / 220 / 280 m ahead, run cap 90 s | `Setting` | proposal |
| `speed_limit` at the middle of the tolerance (5.833 m/s at 20 km/h) | `Setting.speed_limit_mps` | proposal |
| Map Town04, a straight with two lanes in one direction | `DEFAULT_MAP`, `survey` | brief R7, proposal |
| Calibration tolerances, windows, the 0.5 m offset | `calibration.py` | proposal |
| Boards 2.5 m at 8 and 13 m, +-1.6 m | `camera_calibration.py` | proposal |

## The calibrations

**ASM-DRIVING-005** (`calib-decel`):

- The world side itself commands the Ackermann control by the adapter's rule (MAP-DRIVING-DA-COMMAND):
  - `speed = max(0, v + 2 * acceleration)`, with v from the newest snapshot;
  - the acceleration unchanged;
  - jerk 10.0, steer 0, steer speed 0;
  - one command per 0.1 s.
- It runs on the setting's vehicle and road. It accelerates to each approach speed, holds it for 2 s, then brakes
  at each commanded deceleration up to 5.0 m/s².
- The record (`calibration_decel.json`) gives, per pass:
  - the achieved deceleration, a least-squares slope of the speed over the steady part;
  - its ratio to the commanded value;
  - the time to 90 %.
- The vehicle's role is `de4sdv_calibration`, so no candidate client attaches to it. This is no run of a setting.
- The adapter binary is not in this loop. The B5 unit tests cover the adapter's conversion. This run covers the
  simulator's answer to the rule.

**ASM-DRIVING-006** (`calib-steer`):

- The hero starts 0.5 m right of its lane center, with no target, and the candidate drives through the adapter.
- The record (`calibration_steering.json`) gives:
  - the yaw rate, the least-squares slope of CARLA's yaw over the 3 s after the hero first reaches 2 m/s. CARLA's
    yaw is clockwise seen from above, so a left turn is a falling yaw;
  - the offset at the start and at the end;
  - the mean applied steer;
  - `shown`, true when the turn is left.

**The camera calibration file.** The owner decided on 2026-11-18: an `H.yaml` for the CARLA camera, computed with
upstream's script, hashed and named in every verdict. The procedure:

1. `camera-capture` (simulator host) lays four copies of upstream's `Calibration/checkerboard-bw-4x4.png` flat on
   the road. Each is a `static.prop.mesh` with `mesh_path` and `scale` (`StaticMeshFactory.cpp:15-36` at CARLA
   `14ac3b1a50`), textured with `Actor.apply_texture(MaterialParameter.Diffuse, TextureColor)`
   (`PythonAPI/carla/src/Actor.cpp:59-73,149` there). It saves one front image and the boards' true centers in
   upstream's frame: X forward, Y left, origin at the front bumper's center on the ground
   (`Calibration/README.md:23`).
2. `camera_calibration.py make-h` runs on any host with OpenCV and numpy. It takes the pinned blob of
   `Calibration/calc_front_camera_homography.py`, unchanged, and runs it under two recorded shims:
   - the GUI calls are stubbed;
   - `cornerSubPix`'s result is reshaped from (N, 1, 2) to (N, 2). Without that, the script stops at `:99` under
     OpenCV 4.11, because it indexes the corners as (N, 2) points.

   Then it runs upstream's `VisionPilot/scripts/find_homography_C_matrix.py`. The candidate also reads
   `homography_C_matrix.yaml` (`image_preprocessor.cpp:7`), and upstream's build derives that file from `H.yaml`
   (`VisionPilot/CMakeLists.txt:49-53`). Last, it cross-checks upstream's H against the homography computed from
   the camera's settings and its pose in the simulator. The record (`camera_calibration_record.json`) holds the
   sha256 of both files.

   On a synthetic frame rendered from the rig, upstream's script found the board centers within 0.1 px of the
   prediction. Its H agreed with the settings' H within 0.13 % of the distance from 10 to 60 m, and within 0.26 % at
   120 m (`test_upstream_script_on_a_synthetic_frame_agrees_with_the_settings`). For comparison, upstream's shipped
   OpenLane `H.yaml` puts the same ground points 21 % to 52 % too far, from 10 to 120 m. That figure is computed,
   not measured.

**Open: the flat mesh.** The default mesh is the engine's 1 m plane, `/Engine/BasicShapes/Plane.Plane`. Two
things are unverified:

- whether the package cooks that mesh;
- whether its material takes the texture. The game mode sets only the texture parameters `BaseColor` and `Difuse`
  (`CarlaGameModeBase.cpp:505-533`).

If the frame shows no boards, the procedure stops there and reports. It does not fall back to the computed H.

## Commands on the simulator host (the first closed loop)

Python: the G4's CARLA 1.0 venv (the package's cp310 wheel). `$WS` is this folder, `$R` the session's run root. The
order matters: the candidate and the adapter attach to `role_name hero` and must not run during `calib-decel` or
`camera-capture`, whose vehicle has another role.

```bash
PY=<the CARLA 1.0 venv>/bin/python
git -C <VisionPilot clone> show 014e0e7a:Calibration/checkerboard-bw-4x4.png > $R/checkerboard-bw-4x4.png
# 1. road: one start for every setting, from the longest need (60 km/h: 280 + 40 m)
$PY $WS/da_world_side.py survey --map Town04 --setting SC-DRIVING-012@60 --run-dir $R/survey
START=<candidates[0].start from $R/survey/simulator/survey.json>
# 2. warm-up pass, hero, front camera and target along the road (the recorder may attach)
$PY $WS/da_world_side.py warmup --map Town04 --setting SC-DRIVING-012@20 --start $START --run-dir $R/warmup
# 3. ASM-DRIVING-005, no candidate client running
$PY $WS/da_world_side.py calib-decel --map Town04 --setting SC-DRIVING-012@20 --start $START \
    --speeds 20,42,60 --decels 1,2,3,4,5 --run-dir $R/calib_decel
# 4. camera calibration frame, no candidate client running; then the file, on a host with OpenCV
$PY $WS/da_world_side.py camera-capture --map Town04 --start $START \
    --checkerboard $R/checkerboard-bw-4x4.png --run-dir $R/camcal
python3 $WS/camera_calibration.py make-h --capture $R/camcal/simulator/camera_capture.json \
    --vp-clone <VisionPilot clone> --out-dir $R/camcal/h
#    -> H.yaml and homography_C_matrix.yaml into the candidate's working directory, before the identity record
# 5. ASM-DRIVING-006: the world side first, then the S-CORE side once simulator/ready.json exists
$PY $WS/da_world_side.py calib-steer --map Town04 --setting SC-DRIVING-012@20 --start $START --run-dir $R/calib_steer
# 6. SC-DRIVING-012 at 20 km/h, twice; speed_limit = 5.833 (the setting record's candidateSpeedLimitMps)
$PY $WS/da_world_side.py run --map Town04 --setting SC-DRIVING-012@20 --start $START --run-dir $R/run1
```

Each subcommand exits 0 when it completed. It exits 2 on a bench error, written to `simulator/error.json`. `--dry-run`
prints the plan without a client.

## Requirements, code and tests

| What | Where | Tests (`tests/`) |
|---|---|---|
| The fake CARLA 1.0 (brief B0) | `tests/fake_carla/carla/` | `test_world_side_fake_carla.py` |
| Settings and entry checks | `scenarios.py` | `test_world_side_scenarios.py`, `test_world_side_run.py` |
| Spawn, rig, target, records, pacing, teardown, no control | `da_world_side.py` | `test_world_side_run.py` |
| ASM-DRIVING-005/006 | `calibration.py`, `calib-decel`, `calib-steer` | `test_world_side_calibrations.py` |
| Camera calibration file | `camera_calibration.py`, `camera-capture` | `test_world_side_camera_calibration.py` |

The test with upstream's script needs the VisionPilot clone (`DE4SDV_VP_CLONE`) and a Python with OpenCV
(`DE4SDV_CV_PYTHON`, default `/usr/bin/python3`). Without them it is skipped.

## What the local tests cannot show

The first closed loop must show the following on CARLA 1.0:

- `vehicle.lincoln.mkz` is in the library;
- Town04 loads, and the survey finds a straight of 320 m with two lanes in one direction;
- the camera delivers one 1920 x 1280 image per 0.1 s at the 0.05 s step, and the first frames' stall stays in the
  warm-up;
- a hero with no control stays at rest until the adapter's first command;
- the gap computed from the bounding boxes matches the scene;
- the textured plane shows the board in the front image, and upstream's script finds four boards;
- the achieved deceleration for each command;
- the sign of the candidate's turn;
- whether the candidate's own driving reaches and holds 20 to 22 km/h with `speed_limit` 5.833 m/s.

## Open questions

- An approach above the tolerance still has a functional part. The term reads "the latest instant at which the
  vehicle travels at its approach speed within the tolerance with a time to collision of at least 4 s". A hero
  that passes through 20 to 22 km/h while it accelerates, far from the target, and then holds 24 km/h meets that
  at the pass. The checks follow the term and report the start's speed, time to collision and time.
- The model has no number for "travels straight". This bench proposes a heading within 2 deg of the target's.
- The model names `H.yaml` as the calibration the candidate reads. The candidate also reads
  `homography_C_matrix.yaml`, which upstream derives from `H.yaml`, so the identity record should hash both.
- The CARLA vehicle's front axle to center-of-gravity distance (`vision_pilot.conf:21`, `L = 2.860`) is upstream's
  value for its own vehicle. Whether the bench sets it for `vehicle.lincoln.mkz` is open.
