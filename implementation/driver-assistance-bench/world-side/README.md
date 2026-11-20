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
| The seven settings: SC-DRIVING-012 at 20 (20-22), 42 (40-42), 60 (58-60) km/h; SC-DRIVING-013 at 30 (30-32) and 60 (58-60) km/h behind a target at 20 (18-20) km/h; SC-DRIVING-014 at 30 (28-30) km/h; SC-DRIVING-015 at 40 (38-40) km/h behind its vehicle ahead at the same speed | `scenarios.SETTINGS` | model (NR :188-195); the test reads the model file |
| Judged-run terms for SC-DRIVING-012 and -013 only; the stop run (`stop`) is no run of a setting | `Setting.judgeable`, `evaluate_entry` | model (NR :196-211) |
| Functional part, TTC 4 s, 0.2 m for 2 s | `scenarios.evaluate_entry` | model (NR) |
| "Comes to the speed of the target": at rest (stationary target); closing speed <= 0 after it was > 0 (SC-DRIVING-013) | `AT_REST_MPS`, `AT_TARGET_SPEED_CLOSING_MPS` | bench reading |
| "Travels straight": heading within 2 deg of the target's | `STRAIGHT_HEADING_MAX_DEG` | proposal |
| Targets 150 / 220 / 280 m (012), 40 / 115 m (013), 30 m (015) ahead; 014's where its site puts it; run caps 60 s (015: 75 s; stop run: 22 s, the path stopped at go + 12 s) | `Setting` | proposal (S1 plan section 3) |
| Sites `sc014-curve`, `sc015-turnoff` (built by `sites.resolve`, lane A2) | `Setting.site` | lead contract 2 |
| Road behind a moving target: to where the vehicle, at 1.0 m/s2 to its approach speed, reaches it, plus 40 m | `scenarios.road_needed_m` | proposal |
| The SC-DRIVING-013 target at 20 km/h from the run's first tick: `enable_constant_velocity` where the API has it, else posed by `set_transform` each tick (physics off; its speed then recorded from the world side's motion) | `TargetMotion` | proposal (S1 plan A3) |
| `vehiclesAhead`: every vehicle up to 300 m ahead (gap, closing, TTC, needed deceleration, `inLane` by the map lane on the ego's lane ahead, `overlapRatio` across the ego's heading) | `WorldSide.vehicles_ahead` | lead contract 1; `inLane` and `overlapRatio` are bench readings |
| `speed_limit` at the middle of the tolerance (5.833 m/s at 20 km/h) | `Setting.speed_limit_mps` | proposal |
| Map Town06_Opt (AdditionalMaps pack), a straight with two lanes in one direction | `DEFAULT_MAP`, `survey` | brief R7, proposal; the map by the real server's survey ("The maps pack") |
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
- The record (`calibration_steering.json`) gives (the judgement fix of the attempt-3 diagnosis, 2026-11-20):
  - the judgement from the first tick at the setting's speed (`settledAtS`: the band's low end, 20 km/h), not
    while the hero still accelerates;
  - the yaw rate, the least-squares slope of CARLA's yaw over the first window of 3 s, sliding from that tick to
    the first tick at or across the lane centre, whose slope reaches 0.1 deg/s; the steepest window beside it.
    CARLA's yaw is clockwise seen from above, so a left turn is a falling yaw;
  - the offset trend from that tick: its start, the minimum |offset| and when, the first tick at or across the
    lane centre, and the end;
  - the cut at the candidate's last command (`cut`): no tick after it is judged, since the world holds the last
    applied control. The world side has no command record during the run, so its own record is marked
    `provisional`; the fetched record is judged with the S-CORE side's `out.driving_command` records by
    `calibration.py steer --world <world.jsonl> --score <score_interface.jsonl> --setting-low-kmh 20 --out <f>`;
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

**Open: the flat mesh.** The default mesh is the engine's 1 m plane, `/Engine/BasicShapes/Plane.Plane`. The
package cooks it, but its material does not take the texture: the game mode sets only texture parameters named
`BaseColor`, `Difuse` (and `Difuse 2` to `4`), `Normal`, `Emissive` or `ORMH` (`CarlaGameModeBase.cpp:505-548` at
`14ac3b1a50`), and the engine plane's material has none of them. On the real server (Town06_Opt) the boards render
as flat grey: grey p5-p95 about 130-159 under the map's default sky (the world-maps rehearsal's frame), and 76-86
under `ClearNoon`, with `Diffuse` alone and with `Diffuse,Emissive` alike (rehearsal of lane/da-p10-2-ready).
Upstream's script then finds 0 checkerboards. A flat mesh whose material takes the texture is not found yet.

**The capture's pre-check.** `camera-capture` sets its own weather (`--weather`, default `ClearNoon`), applies the
texture as each `--texture-params` name (default `Diffuse`), and then judges its own frame before it exits 0:
every board's central region (60 % of its side, projected with the capture's own camera pose) must span at least
`--precheck-min-spread` grey levels (p95 - p5, default 100, a proposal), and where the Python has OpenCV, upstream's
own detection loop must find all four boards. A frame that fails exits 2 with a named reason ("board tl washed out:
grey p5-p95 76-82 ..."), keeps the frame, and writes the verdict into `camera_capture.json` (`precheck`). So a
washed-out frame ends a session at its `calibrate` step instead of at `make_h` on the lead host. Tests: a 4x
downscaled grey copy of the real frame (`tests/data/town06_washed_out_frame_x4.png`, 74 KB) fails, a full-contrast
render of the same geometry passes.

If the frame shows no boards, the procedure stops there and reports. It does not fall back to the computed H.

**The settings source (p10-2).** The lead decided on 2026-11-19, with the owner informed, that p10-2's calibration
file comes from the simulated camera's settings, because no board renders (above). The source is chosen only by a
flag: `make-h --source settings`, set by the session's `--camcal settings`. The default stays `--source
checkerboard`, upstream's procedure on the frame, and it never falls back to the settings.

- What it writes: `H.yaml` holds `H_settings`, the homography of the road plane (z = 0 above the capture's
  `groundZ`). It is computed from the front camera's world pose and the hero's at the capture, and from the lens
  (1920x1280, FOV 50). It uses upstream's `H.yaml` layout (image (u, v) to ground (X forward, Y left), h33 = 1).
  `homography_C_matrix.yaml` is derived from it by upstream's `find_homography_C_matrix.py`, unchanged, as upstream's
  build does (VisionPilot/CMakeLists.txt:49-53 at 014e0e7a).
- What the record holds: `camera_calibration_record.json` records `source` `settings`, the reason (`sourceReason`)
  and `crossCheck` "not run: no board rendered". It also keeps the frame's sha256 and the capture's pre-check
  verdict (`capturePrecheck`).
- The capture with this source: `calibrate.sh <out> settings` still runs `camera-capture` and keeps its frame. It
  runs with `--precheck record`, so the verdict goes into `camera_capture.json` (`precheck.enforced` false) and a
  washed-out frame does not end the step.
- The gate: the model needs only that the candidate's homography matches the simulated camera
  (`gapCameraImageAndGeometry`); it names no calibration procedure. The gate is
  `test_gate_settings_h_yaml_agrees_with_upstreams_procedure_on_full_contrast_boards_at_the_g4_pose`. It renders four
  full-contrast boards at the real G4 capture's camera pose (`tests/data/town06_g4_capture.json`) and runs upstream's
  unchanged script on them through make-h's shims. Upstream's H agrees with the settings' `H.yaml` to 0.30 % of the
  distance at 10-60 m (`AGREE_TOLERANCE` 2 %), and laterally to within 5 cm.
- A real-frame sanity view: the real Town06_Opt capture frame, warped into a bird's-eye view with this `H.yaml`. Its
  four lane lines run straight and parallel (fitted angles within 0.05 deg of each other), 3.49-3.51 m apart, and the
  boards' gray squares sit where they were placed. The record is under
  `~/.hermes/outputs/inc-driving-002/phase10/p10-2-ready-20261119/`.
- What is lost: upstream's procedure is not exercised on a real frame, and no real-frame cross-check exists. The
  settings' H is only as right as the camera settings the world side reads back from the simulator.
  `gapCameraImageAndGeometry` stays open.

## The maps pack

The highways come with CARLA's AdditionalMaps pack, not with the base package. The base package's server lists four
maps (EmptyMap, Town10HD_Opt, Town12, Town15). `load_world` takes only a name that `get_available_maps()` lists, so a
host without the pack refuses the world side's map, and so does a near name. The paid p10-1 of 20261119T123937Z
ended at its warm-up that way.

What the real server showed (1.0-14ac3b1a5 on the G4, 2026-11-19; the probe's facts are in
`inc-driving-002/phase10/p10-1-world-maps-20261119/FACTS.md` under the lead host's outputs):

- with the pack, the server lists sixteen maps, bare names, among them `Town04_Opt` and `Town06_Opt`;
  `load_world('Town04_Opt')` took 3.4 s;
- on `Town04_Opt` the longest straight under the survey's rule is 235 m. That is short of the 320 m of
  SC-DRIVING-012@60 (the warm-up's survey) and of the 300 m of `calib-decel`. So the world side uses `Town06_Opt`,
  whose straights reach 400 m and more;
- on `Town06_Opt` the world side's whole p10-1 and p10-2 sequence ran. The survey, the warm-up, the run's handshake
  (ready.json, go, run_end.json, release), `calib-decel`, `camera-capture` and `calib-steer` all exited 0;
- there is no `vehicle.lincoln.mkz_2020`. `VEHICLE_CANDIDATES` falls back to `vehicle.lincoln.mkz`. The target
  `vehicle.tesla.model3` and `static.prop.mesh` are in the library.

The map name is set in one place for the session: `DEFAULT_MAP` in `da_world_side.py` and `WORLD_MAP` in
`scripts/common.sh`, which a test keeps equal. The session's `sim_setup.sh` checks that `WORLD_MAP` is in the
server's `get_available_maps()` before it reports the server ready. Without the pack it fails with
`FAIL map(s) not on the server: Town06_Opt ...`, so a session ends at sim_setup and not at the warm-up.

### One-time install on the simulator host

`sim_setup.sh` does not install the pack. Install it once on the host's disk. It survives VM stops, and a server
start picks it up. The package's own `README` says to install a pack with
`python3 Tools/carla_pack.py install <pack>.tar.gz --server .`. That command reads a tarball file and extracts it
into `CarlaUnreal/Packs/<Pack>`. On the G4 the same steps run as a stream instead, so that the sha256 is checked
while streaming and no 6.8 GB tarball stays on the disk. The steps are the `install` command's own: extract into a
staging folder in `Packs/`, `verify`, check against the server, move.

- the object: `gs://de4sdv-carla-d19a-packages/carla-1.0-14ac3b1a5/CARLA_UE5_Weekly_AdditionalMaps.tar.gz`;
- its size and sha256: 6830970575 bytes, sha256 `33678e7c1571892f15df71a88feb2000dadacc0f71ae8e72f9e45813d60930d6`;
- the install path on the G4: `/opt/sim20g4/pkg/Carla-1.0-Linux-Shipping/CarlaUnreal/Packs/AdditionalMaps`;
- the disk it takes: 7.3 GB; `sim_setup.sh` needs 8 GiB free after it.

Run it on the simulator host, as the user that runs CARLA. The VM's own token reads the bucket (scope
`devstorage.read_only`):

```bash
CR=$(cat /opt/sim20g4/carla_root)                    # /opt/sim20g4/pkg/Carla-1.0-Linux-Shipping
PACKS=$CR/CarlaUnreal/Packs; STAGE=$PACKS/.AdditionalMaps.stage
OBJ=carla-1.0-14ac3b1a5%2FCARLA_UE5_Weekly_AdditionalMaps.tar.gz
WANT=33678e7c1571892f15df71a88feb2000dadacc0f71ae8e72f9e45813d60930d6
TOKEN=$(curl -s -H 'Metadata-Flavor: Google' \
  http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token |
  python3 -c 'import json, sys; print(json.load(sys.stdin)["access_token"])')
[ ! -e "$PACKS/AdditionalMaps" ] && mkdir -p "$STAGE" || exit 1
curl -sS --fail -H @<(printf 'Authorization: Bearer %s\n' "$TOKEN") \
  "https://storage.googleapis.com/storage/v1/b/de4sdv-carla-d19a-packages/o/$OBJ?alt=media" |
  tee >(sha256sum | cut -d' ' -f1 > ~/maps.sha256) | tar -xzf - -C "$STAGE" || exit 1
sleep 2; [ "$(cat ~/maps.sha256)" = "$WANT" ] || { echo "sha256 mismatch: not installed"; exit 1; }
python3 "$CR/Tools/carla_pack.py" verify "$STAGE/AdditionalMaps" || exit 1                  # OK: 35 files verified
python3 "$CR/Tools/carla_pack.py" inspect "$STAGE/AdditionalMaps" --server "$CR" || exit 1  # Compatible: yes
mv "$STAGE/AdditionalMaps" "$PACKS/AdditionalMaps" && rmdir "$STAGE"
```

On 2026-11-19 this took 42 s on the G4 (`maps_install.log` in the facts folder). Then start CARLA again
(`sim_setup.sh`) and look for `Town06_Opt` in `server_probe.txt`'s `available_maps` line.

## The scenario sites (`sites.py`)

SC-DRIVING-014 needs a tight curve and SC-DRIVING-015 a turn-off junction; neither is a straight road, so the
survey cannot find them. `sites.resolve(world_map, site_id, setting)` reads the map's own OpenDRIVE
(`world_map.to_opendrive()`) and returns a `SiteSpec`: the hero's start as `road:lane:s` (what `--start` takes), the
target (its pose, and for SC-DRIVING-015 its path and speed script, `SiteSpec.target_motion().at(t)`), the props,
the geometry read off the map, the checks that refuse a bad site, and the regulation's guidance values for
`setting_record.json` (`SiteSpec.as_record()`). Every bench reading and proposal is a named constant in `sites.py`
and is listed in the record.

- `sc014-curve`: a non-junction curve whose lane-centre radius in the hero's lane is at most 25 m over at least
  90 deg, at least 120 m of approach, guard pipes (the server's `static.prop.streetbarrier`: the server lists no
  guard pipe) on the outer shoulder from 10 m before the curve to its end, and a stationary
  `vehicle.tesla.model3` on the tangent extension of the lane centre at the curve entry, its body 0.5 m clear of
  every road surface and of the pipes. A curve whose outer road edge is also within 25 m ranks first. The target's
  body is checked as its bounding box (`target_box_check`): a box that touches or overlaps any road surface, or
  comes within 0.5 m of one, is refused with the surface named; the record keeps the measured clearance
  (`checks.targetClearanceFromRoadSurfaceM`; 0.586 m from road 10's outer shoulder on the real map).
- `sc015-turnoff`: a junction lane with a straight and a right-turn connector and at least 200 m of straight
  approach; the target starts 30 m ahead of the hero, accelerates at 1.5 m/s2 to 40 km/h, holds at least 4 s,
  brakes at 2.0 m/s2 to 10 km/h at the junction and turns right at 10 km/h; the hero's lane goes straight on.

The approach rule is `straight` by default (heading within 2 deg of the entry's, within 0.5 m of its tangent). On
the real Town06_Opt (the G4 read of 2026-11-20) no tight curve has 120 m of straight approach: road 10 is preceded by
a 16 deg bend of radius 27 m about 17 m before its entry, so `sc014-curve` refuses there and names the curves it
found. `approach_rule="gentle-bend"` (heading within 20 deg, no lane-centre radius at or under 25 m) is a second
reading, chosen only by name and recorded in the site record; it gives road 10's middle lane (lane-centre radius
13.0 to 13.4 m, outer road edge 19.8 m, 267 m of approach). The outermost lane has 97 m under that reading.

### The SC-DRIVING-014 site rule (a bench choice of 2026-11-20)

The model fixes neither the lane nor the approach: "toward a curve of at most 25 m radius"
(`driver_assistance_needs_requirements.sysml:192-193`), the guard pipes on the outer side and the target just outside
them on the extension of the lane centre (`driver_assistance_operational_context.sysml:280-284`). The SC-DRIVING-014 site
decision of 2026-11-20 selects, by name in the setting (`scenarios.SITE_RULE_014`), never as a fallback:

- the outermost driving lane (`lane_rule="outermost"`), since the regulation's guidance has the vehicle drive
  "outer lane than the centre of the road" (R152:1744-1756);
- the gentle-bend approach reading, since no tight curve of Town06_Opt has the plan's 120 m of straight approach;
- at least 90 m of approach (`approach_min_m=90`): in attempt 3 the candidate reached 20.9 km/h within 15 m of its
  first move, and 29 km/h needs about 35 m. A shorter approach is refused with the rule and the best candidates named.

The middle lane (267 m of approach) is the alternative; it is not the source's lane. The record keeps the reading, the
lane, the minimum, the reason and the chosen curve in `site.benchReadings.siteSelection`. On the real map read:

| Item | Value |
|---|---|
| Curve | road 10, lane -5 (outermost of three), 206 deg left |
| Radius | 16.47 to 16.93 m at the lane centre, 19.82 m at the outer road edge |
| Approach | 97.04 m (gentle-bend; 17.16 m straight); the hero starts at its far end, `54:6:62.56` |
| Guard pipes | 44 `static.prop.streetbarrier` at radius 19.25 m on the outer shoulder, none on a driving lane |
| Target | 15.5 m along the tangent from the entry `10:-5:11.941`; its box 0.586 m from road 10's outer shoulder (lane -7), 2.80 m from the hero's path |
| Turn-in | gap 10.71 m: TTC 1.29 s at 30 km/h (guidance at most 1.6 s), 1.75 s at 22 km/h |

### How the world side builds a site

For a setting with a site, `da_world_side.py` calls `sites.resolve(map, site, setting,
props_available=<the server's static.prop.* list>, approach_rule=..., approach_min_m=..., lane_rule=...,
rule_reason=...)` with the setting's own rule. It spawns the hero at `start_pose` (`start` in the record, beside the
distance to the server's own waypoint at that `road:lane:s`), every prop at its pose with physics off, and the target
at its pose. The session's road (`--start`) is not used for a site setting; the record names it as not used. A site
the map refuses ends the run as a bench error that names the reason. `setting_record.json["site"]` is
`SiteSpec.as_record()`, guidance included. SC-DRIVING-015's target follows its script along its path on every tick
by `set_transform`, with physics off: the pose after each tick is `SiteSpec.target_motion().at(t + 0.05 s)`, and
each world tick carries the script's phase (`target.motionPhase`). SC-DRIVING-013's target keeps
`enable_constant_velocity`. The props spacing uses the server's own streetbarrier extent (the G4 read,
`sites.PROP_EXTENTS_G4`).

The tests replay the real read (`tests/data/town06_opt_g4_read.json`, `tests/data/town06_opt_g4.xodr.xz`: the map's
OpenDRIVE of sha256 a90b6131..., part of CARLA's map content): the fake's `Map.to_opendrive()` gives those bytes
for Town06_Opt and refuses for a map without a read, and its blueprint library lists the server's 83
`static.prop.*` names, so an unknown prop is refused. The lane centres of `sites.Xodr` equal the server's own
waypoints (`tests/data/town06_opt_g4_waypoints_sites.json`) within 1 cm (0.8 mm at most over 12,956 of the 12,958; two name a lane the section does not hold).

## Commands on the simulator host (the first closed loop)

Python: the G4's CARLA 1.0 venv (the package's cp310 wheel). `$WS` is this folder, `$R` the session's run root. The
order matters: the candidate and the adapter attach to `role_name hero` and must not run during `calib-decel` or
`camera-capture`, whose vehicle has another role.

```bash
PY=<the CARLA 1.0 venv>/bin/python
git -C <VisionPilot clone> show 014e0e7a:Calibration/checkerboard-bw-4x4.png > $R/checkerboard-bw-4x4.png
# 1. road: one start for every setting, from the longest need (60 km/h: 280 + 40 m)
$PY $WS/da_world_side.py survey --map Town06_Opt --setting SC-DRIVING-012@60 --run-dir $R/survey
START=<candidates[0].start from $R/survey/simulator/survey.json>
# 2. warm-up pass, hero, front camera and target along the road (the recorder may attach)
$PY $WS/da_world_side.py warmup --map Town06_Opt --setting SC-DRIVING-012@20 --start $START --run-dir $R/warmup
# 3. ASM-DRIVING-005, no candidate client running
$PY $WS/da_world_side.py calib-decel --map Town06_Opt --setting SC-DRIVING-012@20 --start $START \
    --speeds 20,42,60 --decels 1,2,3,4,5 --run-dir $R/calib_decel
# 4. camera calibration frame, no candidate client running; then the file, on a host with OpenCV
$PY $WS/da_world_side.py camera-capture --map Town06_Opt --start $START \
    --checkerboard $R/checkerboard-bw-4x4.png --run-dir $R/camcal
python3 $WS/camera_calibration.py make-h --capture $R/camcal/simulator/camera_capture.json \
    --vp-clone <VisionPilot clone> --out-dir $R/camcal/h
#    (p10-2: add --precheck record to camera-capture and --source settings to make-h, see "The settings source")
#    -> H.yaml and homography_C_matrix.yaml into the candidate's working directory, before the identity record
# 5. ASM-DRIVING-006: the world side first, then the S-CORE side once simulator/ready.json exists
$PY $WS/da_world_side.py calib-steer --map Town06_Opt --setting SC-DRIVING-012@20 --start $START --run-dir $R/calib_steer
# 6. SC-DRIVING-012 at 20 km/h, twice; speed_limit = 5.833 (the setting record's candidateSpeedLimitMps)
$PY $WS/da_world_side.py run --map Town06_Opt --setting SC-DRIVING-012@20 --start $START --run-dir $R/run1
```

Each subcommand exits 0 when it completed. It exits 2 on a bench error, written to `simulator/error.json`. `--dry-run`
prints the plan without a client.

## The session's entries (`scripts/`)

A bench session (`../session/`) runs these on the simulator host, with the bench folder as the working directory and
`SIM_PY` set to the CARLA 1.0 venv's Python:

| Script | Entry | What it runs | Exit |
|---|---|---|---|
| `warmup.sh <out>` | `ENTRY_SIM_WARMUP` | `survey` with SC-DRIVING-012@60 (the longest need), the first candidate as the session's road in `world_start.json`, then `warmup` with SC-DRIVING-012@20 | 0; 2 a bench error; 3 no road |
| `calibrate.sh <out> [checkerboard\|settings]` | `ENTRY_SIM_CALIBRATE` | `calib-decel` (20, 42, 60 km/h; 1 to 5 m/s²), then `camera-capture` with the checkerboard the session took from the pin; both with role `de4sdv_calibration`, before any S-CORE side start. The second argument is the session's `--camcal`: `checkerboard` (default) enforces the capture's pre-check (`--precheck on`), `settings` records it only (`--precheck record`) | 0; the world side's status; 2 an unknown source |
| `run_scenario.sh <out> <scenario> <setting>` | `ENTRY_SIM_RUN` | `run` (SC-DRIVING-012 to -015: `SC-DRIVING-012 20kmh`, or a setting id of `s1_runs.tsv` such as `SC-DRIVING-013 SC-DRIVING-013@30`; the stop run as `SC-DRIVING-012 stop`) or `calib-steer` (ASM-DRIVING-006), at the session's road or the setting's site, with the handshake below | 0; 2 a bench error; 64 bad arguments |

Every entry passes `DA_ACKERMANN_GAINS` through to `da_world_side.py` and prints its value (or "unset (default)")
before each world-side command.

`camera_calibration.py make-h` needs OpenCV, which the simulator host's venv does not carry, so the session runs it
on the lead host on the fetched capture. It puts `H.yaml` and `homography_C_matrix.yaml` on the S-CORE host and
names that folder in `DA_CAMERA_CALIBRATION_DIR` for every S-CORE side start, before the identity record.

The handshake of a run (`--go-file`, `--release-file`):

1. the world spawns the hero, its camera and the target and writes `simulator/ready.json`; it does not tick;
2. the session starts the S-CORE side and touches `<out>/go`: the first paced tick follows (`--go-wait-s`, 900 s;
   without the file the run is a bench error and has no tick);
3. at the run's end (contact, at rest, cap) the world writes the entry checks, the setting record and
   `simulator/run_end.json`, and keeps ticking (phase `hold`, in `hold.jsonl`, not in `world.jsonl`);
4. the session stops the S-CORE side, then touches `<out>/release`; the world leaves synchronous mode
   (`--release-wait-s`, 300 s, ends the hold anyway).

So the Launch Manager stops while the world still ticks (`../launch-manager/README.md`), and the candidate's ready
timeout (420 s) covers the time from its start to the go file.

## The Ackermann gains (`DA_ACKERMANN_GAINS`)

The hero's Ackermann controller follows a commanded deceleration only partly with CARLA's own gains (the
ASM-DRIVING-005 probe of 2026-11-20, `phase10/s1-map/FACTS.md`). `DA_ACKERMANN_GAINS` chooses the gains:

- unset or `default`: CARLA's own (speed_kp 0.15, speed_ki 0, speed_kd 0.25, accel_kp 0.01, accel_ki 0, accel_kd 0.01
  on `vehicle.lincoln.mkz`); nothing is applied. This stays the default until the owner decides D-S1-2;
- `v1`: the probe's variant v1 (`asm005_probe_table.json`): speed_kp 0.3 and accel_kp 0.1, the other four as above.

Any other value, an empty one included, is refused before the world is touched (exit 2, the reason named). The world
side applies the gains through `AckermannControllerSettings` to every hero right after its spawn, reads them back after
the settle ticks, and ends with a bench error when the read-back differs. `setting_record.json`,
`calibration_decel.json` and `calibration_steering.json` carry `ackermannGains`: the requested name, the values, and
per spawned hero what was applied and read back.

## What each run also records

- **`simulator/tick_times.csv`**, `sim_time_s,unix_s`: one row for every tick of the process, the setup and teardown
  ticks included. `sim_time_s` is the snapshot's `elapsed_seconds` after the tick, `unix_s` this host's real time
  when the tick returned. It is the chase view's time base: `../recording/compose_side_by_side.py --tick-times`.
- **In every setting record**, `benchReadings.travelsStraight`: the bench reads "travels straight" as a heading
  within 2 deg of the target's (lead answer of 2026-11-18; the model gives no number yet).
- **`runFlags`** in the setting record of a run (rewritten at its end): where the functional part starts (time,
  speed, time to collision) and `tooFast`, true when the speed rose above the tolerance after that start. The
  literal entry check stays as it is; the evaluators decide what the flag means. Leaving the band downward after
  the start is the braking and is only reported (`firstBelowToleranceS`).
- **`hero.wheelbase`**: the hero's wheelbase against `vision_pilot.conf`'s `L = 2.860` (`:21` at the pin, which
  stays upstream's), `flagged` when they differ by more than 2 %. CARLA 1.0's `WheelPhysicsControl` has no wheel
  position (`PythonAPI/carla/src/Control.cpp:439-462` at `14ac3b1a50`), so the physics control is recorded and the
  wheel positions come from the wheel bones (`get_bone_names`, `get_bone_world_transforms`, `Actor.cpp:123,126`
  there). No position gives `unmeasured`, never a pass. Upstream's comment calls `L` "Front axle to CoG" and the
  wheelbase "L = Lf + Lr"; the lead reads `L` as the wheelbase.

## Requirements, code and tests

| What | Where | Tests (`tests/`) |
|---|---|---|
| The fake CARLA 1.0 (brief B0) | `tests/fake_carla/carla/` | `test_world_side_fake_carla.py` |
| Settings and entry checks | `scenarios.py` | `test_world_side_scenarios.py`, `test_world_side_run.py` |
| Spawn, rig, target, records, pacing, teardown, no control | `da_world_side.py` | `test_world_side_run.py` |
| Session entries, handshake, tick times, setting-record flags, wheelbase | `scripts/`, `da_world_side.py` | `test_world_side_scripts.py` |
| ASM-DRIVING-005/006 | `calibration.py`, `calib-decel`, `calib-steer` | `test_world_side_calibrations.py` |
| Camera calibration file | `camera_calibration.py`, `camera-capture` | `test_world_side_camera_calibration.py` |

The test with upstream's script needs the VisionPilot clone (`VISIONPILOT_CLONE`) and a Python with OpenCV
(`DE4SDV_CV_PYTHON`, default `/usr/bin/python3`). Without them it is skipped.

## What the local tests cannot show

The first closed loop must show the following on CARLA 1.0:

- `vehicle.lincoln.mkz` is in the library;
- Town06_Opt loads, and the survey finds a straight of 320 m with two lanes in one direction (shown on the G4 on
  2026-11-19, "The maps pack");
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
- `L = 2.860` (`vision_pilot.conf:21`) stays upstream's value (lead answer of 2026-11-18); each run records the
  hero's wheelbase against it (above). Whether the wheel bones of `vehicle.lincoln.mkz` carry the word "wheel" in
  CARLA 1.0 is unverified.
