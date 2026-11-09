# World side of the closed-loop driving bench

`world_side.py` is the process on the simulator host that owns CARLA. It runs
CARLA 0.9.16 in synchronous mode at 0.1 s per tick, paced on the wall clock,
spawns the hero and its six-camera rig, announces the handover frame (optionally
after an autopilot warm-up along the route), injects the world-side faults of
SC-DRIVING-003, and writes the per-tick C1 world record the case evaluators read
(ICD v2 §10 C1, `case-evaluators/OBSERVABLES.md` §3).

It needs Python 3.10 on the simulator host, the `carla` 0.9.16 PythonAPI and
numpy. It imports `carla` only when it connects, so `--dry-run` and the error
paths run without a server.

```bash
python3.10 world_side.py \
  --host 127.0.0.1 --port 2000 --tm-port 8000 --map Town10HD_Opt \
  --route <run_dir>/navigation/route.json \
  --profile /opt/de4sdv-p2/.../calibration/nuplan.json \
  --rig-path <agent>/python/de4sdv_planner/rig.py \
  --width 1024 --front-width 1920 \
  --run-dir <run_dir> --run-s 120 --seed 7 \
  --fault camera_stop:rear_left@12.5
```

`--dry-run` prints the plan (route in both frames, spawn rule, camera table,
`F_h` offset, resolved faults) and creates no client.

## Requirements, code and tests

| Req | Where in `world_side.py` | Test |
|---|---|---|
| R1 CLI | `build_parser`, `print_plan`, `Route`, `WorldSide.pick_spawn`, `WorldSide.ensure_map` | `test_cli_defaults`, `test_dry_run_prints_plan_and_spawns_nothing`, `test_dry_run_rejects_an_unknown_fault`, `test_map_loaded_only_when_different`, `test_spawn_point_is_the_nearest_within_two_metres`, `test_spawn_point_far_away_is_loud`, `test_spawn_index_out_of_range_is_loud`, `test_cli_dry_run_as_a_subprocess` |
| R2 settings + teardown | `apply_settings`, `restore_settings`, `teardown`, `main` | `test_settings_applied_and_restored`, `test_settings_restored_when_a_camera_fails_to_spawn`, `test_teardown_is_idempotent`, `test_every_actor_goes_while_the_world_is_still_synchronous`, `test_the_last_tick_gets_time_to_arrive_before_teardown`, `test_no_wait_when_no_tick_was_made`, `test_the_summary_is_on_disk_when_teardown_dies` |
| R3 pacing | `Pacer`, `WorldSide._do_tick`, `summary` | `test_one_tick_per_hundred_ms_of_wall_time`, `test_a_slow_tick_moves_the_schedule_and_is_counted`, `test_a_late_wake_is_counted_and_logged`, `test_the_pacer_never_runs_a_tick_before_its_deadline` |
| R4 hero and rig | `spawn_hero`, `spawn_rig`, `load_rig_module` | `test_six_cameras_named_from_the_profile`, `test_rig_pose_is_actor_pose_in_vehicle`, `test_rig_uses_the_real_agent_module` |
| R5 handover marker | `run` (F_h), `spawn_marker`, `tick_data` (`handoverFrame`), `summary` | `test_handover_marker_names_the_frame` |
| R6 warm-up and handover | `start_warmup`, `_apply_due`, `tick_data` (`controlSource`, `autopilotEnabled`, `trafficManagerEnabled`) | `test_autopilot_off_before_the_handover_tick`, `test_warmup_follows_the_route_in_carla_coordinates`, `test_warmup_path_lies_at_the_spawn_height`, `test_no_warmup_leaves_the_adapter_in_control_from_the_first_tick`, `test_autopilot_state_follows_the_vehicle_when_the_api_offers_it` |
| R7 world-side faults | `parse_fault`, `FAULT_PARSERS`, `_apply_due`, `_fire_camera_stop` | `test_camera_stop_timing_record_and_sensor_state`, `test_camera_stop_at_the_handover_frame`, `test_a_fault_after_the_run_never_fires`, `test_fault_parser_is_extensible_and_strict` |
| R8 C1 record | `tick_data`, `write_tick`, `_lane`, `_control`, `_on_collision`, `_on_lane_invasion`, `take_events`, `JsonlWriter` | `test_every_record_has_exactly_the_c1_fields`, `test_world_jsonl_holds_ticks_only_and_lifecycle_goes_to_the_side_log`, `test_envelope_is_the_route_provider_envelope`, `test_pose_is_the_map_frame_of_icd_section_9`, `test_non_finite_kinematics_are_null_not_dropped`, `test_collision_and_lane_events_are_attached_to_their_frame`, `test_a_callback_that_arrives_late_is_kept_and_counted`, `test_runio_reads_the_world_records`, `test_cases_helpers_read_the_world_records`, `test_vc011_cannot_judge_a_world_only_run` |
| R9 run end | `run`, `_route_end`, `summary`, the `stop` record | `test_stop_after_the_run_duration`, `test_stop_at_the_route_destination`, `test_stop_on_a_stop_request`, `test_stop_on_ctrl_c`, `test_sigint_handler_requests_a_stop` |
| R10 loud errors | `main`, `write_startup_error`, `BenchError`, the `error` record | `test_missing_route_is_loud`, `test_missing_profile_is_loud`, `test_hero_spawn_failure_is_loud_and_tears_down`, `test_map_load_failure_is_loud`, `test_route_map_mismatch_is_loud`, `test_settings_restored_when_a_camera_fails_to_spawn`, `test_cli_error_exits_non_zero_as_a_subprocess`, `test_python_3_10_syntax` |

Run the tests with the evaluators' environment (numpy + pytest):

```bash
<bench>/case-evaluators/.venv/bin/python -m pytest -q <bench>/world-side/tests
```

The suite passes under both the evaluators' venv (Python 3.12) and
`/usr/bin/python3.10` (the simulator host's interpreter, numpy 1.21.5).

The tests use a fake `carla` package (`tests/fake_carla/carla`), a synthetic
calibration profile with the keys the agent's `rig.py` reads, the real
`agent/python/de4sdv_planner/rig.py`, and the evaluators' own `runio.py` and
`cases.py`. No CARLA server and no network are needed.

## Output

| File | Content |
|---|---|
| `<run_dir>/simulator/world.jsonl` | C1: one `tick` record per world tick, and nothing else |
| `<run_dir>/simulator/worldSide.jsonl` | lifecycle records `start`, `config`, `stop`, `error` |
| `<run_dir>/bench/injection.jsonl` | C8: one `injection` record per fired world-side fault |
| `<run_dir>/simulator/summary.json` | ticks, real-time factor, late-tick counts, F_h, cameras, faults |

**Why the lifecycle records are not in `world.jsonl`.** `runio.world_by_frame()`
iterates every record of `world.jsonl` and raises `RunFormatError` on a record
whose `data` has no integer `frame`. A `start`, `stop` or `error` record there
would make the whole run unreadable (or, with a borrowed frame, silently
overwrite a tick). So `world.jsonl` holds ticks only and the §6 envelope is
reused in `simulator/worldSide.jsonl`, which is `<run_dir>/<host>/<component>.jsonl`
of ICD §6. `test_world_jsonl_holds_ticks_only_and_lifecycle_goes_to_the_side_log`
and `test_runio_reads_the_world_records` pin this.

## The C1 record

Every record is `{"t_mono_ns", "t_real_ns", "host", "component", "event", "seq", "data"}`
with `host = "simulator"`, `component = "worldSide"`, `event = "tick"`, `seq`
from 1 without gaps, and the same field order as `navigation/route_provider.py`'s
`RunLog` (`test_envelope_is_the_route_provider_envelope`). Non-finite numbers are
JSON `null` (ICD §6).

| Field | Frame | Unit / value |
|---|---|---|
| `frame` | — | CARLA world frame index (int); simulation time is `frame × 100 ms`, never the float stamp |
| `sim_ms` | — | simulation ms, `frame × 100` (int) |
| `handoverFrame` | — | F_h, the first frame on which `controlSource` is `actuationAdapter` (R5) |
| `egoPose.x`, `.y` | **map** | m, `x_map = x_carla`, `y_map = -y_carla` (ICD §9) |
| `egoPose.yaw` | **map** | rad, `-radians(yaw_carla)`, CCW positive |
| `velocity.speed_mps` | — | m/s, norm of CARLA's velocity vector |
| `velocity.heading_rad` | **map** | rad, the vehicle's heading, same value as `egoPose.yaw` |
| `acceleration.longitudinal_mps2` | vehicle axes | m/s², CARLA acceleration projected on the forward axis, positive forward |
| `acceleration.lateral_mps2` | vehicle axes, **map** sense | m/s², positive to the vehicle's **left** (CARLA's y is right, so its right-axis component negated); in a planar turn it equals `speed_mps × yaw_rad_s`, as in the evaluators' reference producer |
| `angular_velocity.roll_rad_s`, `.pitch_rad_s`, `.yaw_rad_s` | **map** | rad/s from `carla`'s deg/s. Angular velocity is a pseudovector: under the y reflection CARLA's `(wx, wy, wz)` becomes `(-wx, wy, -wz)`. `yaw_rad_s` is counter-clockwise positive, the sign of d`egoPose.yaw`/dt; `summary.yawRateCheck` measures that agreement on every run |
| `lane.road` | — | CARLA `road_id` (int) of `map.get_waypoint(project_to_road=True)` |
| `lane.lane` | — | CARLA `lane_id` (int) |
| `lane.lat_m` | CARLA axes | m from the lane centre; positive to the driver's right |
| `lane.junction` | — | bool, `waypoint.is_junction` |
| `control.throttle`, `.brake`, `.steer` | — | `hero.get_control()`: CARLA's normalised pedal and steer (+1 right) |
| `control.accelMps2` | — | `null`: OBSERVABLES defines it as what was applied, and the adapter's commanded acceleration never reaches this process; the measured value is `acceleration.longitudinal_mps2` |
| `controlSource` | — | the control authority the world side granted, not an observation: `autopilot` for `frame < handoverFrame` (warm-up runs only), `actuationAdapter` from F_h on. The world side never applies control; who applied what is the adapter's log |
| `autopilotEnabled` | — | bool, the hero's autopilot state (`get_autopilot()` when the build offers it, else the tool's switch, which it is the only writer of) |
| `trafficManagerEnabled` | — | bool, the Traffic Manager was driving the hero (autopilot on and TM in synchronous mode) |
| `sensors[]` | — | six `{name, actor_id, alive, attached}` for `cam_front`, `cam_front_left`, `cam_front_right`, `cam_rear_left`, `cam_rear`, `cam_rear_right` |
| `collisions[]` | — | `{frame, other_actor, other_actor_id, impulse_mps {x,y,z}}` of the tick |
| `laneInvasions[]` | — | `{frame, markings[]}` of the tick |
| `tickDurationMonoNs` | — | ns of the `world.tick()` call (R3) |
| `latenessMonoNs` | — | ns the tick started after its deadline (R3) |

The world side records no image digests; it never listens to the cameras
(`test_six_cameras_named_from_the_profile` asserts the camera actors have no
listeners).

Runtime reference frame: the map frame of ICD §9 is
`x_map = x_carla, y_map = -y_carla, yaw_map = -yaw_carla`, as in
`navigation/carla_frame.py`; the conversion is repeated here so the tool has no
import dependency beyond `carla` and numpy.

## Pacing

One tick per 100 ms of wall time. The pacer takes its deadlines from
`time.monotonic` (injected as `clock` in the tests, so no test sleeps) and never
bursts: a tick that overruns its slot moves the schedule forward and is counted
as a `scheduleSlip`. A tick that started more than 1 ms after its deadline is a
`lateTick`. `summary.json` has `ticks`, `simSeconds`, `wallSeconds`,
`realTimeFactor` (`simSeconds / wallSeconds`), `lateTicks`, `scheduleSlips`,
`maxLatenessMonoNs`, `maxSlipMonoNs`, `frameSkips` and the per-tick extremes.

`simSeconds` is `ticks × 0.1`; `wallSeconds` is the last tick end minus the
first tick start. On a real run of hundreds of ticks the two agree to within one
tick.

## Setup ticks

In synchronous mode a new actor is in no world snapshot before the next tick:
its transform reads as zero, while `get_physics_control()` (an RPC) already
answers with world wheel positions, and a spawned vehicle drops onto its
suspension over the first ticks. So after spawning the hero the tool ticks
(unpaced) until the hero has been simulated and rests (z change < 2 mm and
speed < 0.05 m/s between two ticks; at least 2, at most 50 ticks), and only
then reads the REF origin and spawns the rig. Read before the first tick, the
origin came out 0.85 m off on a hero away from the world origin (review test
`test_rig_origin_is_the_settled_vehicle_origin`), which the agent's 10 mm rig
check refuses. Setup ticks are not run ticks: no C1 record; one `setup` record
in `worldSide.jsonl` (`setupTicks`, `settledAtFrame`, `heroZ`, `speedMps`) and
`summary.setup`. The run's first frame follows them.

## Warm-up and handover

* **Default: no warm-up** (`--warmup-s 0`). REQ-DRIVING-011's criterion allows
  the autopilot and the Traffic Manager no control of the vehicle at any time of
  the run, and VC-DRIVING-011 checks every tick. So the hero rests at the route
  start and the agent drives from rest once its histories are primed. A run
  with `--warmup-s > 0` logs its warm-up ticks honestly as `autopilot` and fails
  VC-DRIVING-011, unless the run start is defined as the handover (ICD C1
  mentions an "announced warm-up"; the requirement does not).
* F_h = (frame of the first run tick) + `round(warmup_s / 0.1)`. The
  marker actor `static.prop.*` with `role_name = de4sdv_handover_<F_h>` (decimal,
  no padding) sits at CARLA `(0, 0, -500)` with physics disabled; other clients
  read F_h from it at startup.
* Before F_h the hero is on the Traffic Manager: `set_path` with the route
  waypoints converted back to CARLA coordinates (`x, -y`), desired speed
  `--warmup-speed-kmh`, `auto_lane_change(False)`, speed difference 0,
  `ignore_lights_percentage(100)`, seed `--seed`.
  **Lights are ignored**: the exported `Town10HD_Opt` route crosses signalised
  junctions and a red light would stall the warm-up so it never reaches F_h
  inside `--warmup-s`. Lane changes are off, as required.
* Before the tick of frame F_h the tool calls `set_autopilot(False, tm_port)`.
  The tool never applies vehicle control itself.
* With `--warmup-s 0` (the default) no autopilot is engaged at all, F_h is the
  first run tick and every record is `actuationAdapter`. A `camera_stop` at 0 s
  then fires before the second tick, because F_h is only known after the first
  one.
* Start order on the bench: the agent first (it builds its engine before FEO
  starts and then waits up to `carla_attach_timeout_s` for the hero and the six
  cameras), then the world side.

## Faults

`--fault camera_stop:<slot>@<seconds after handover>` destroys that camera
before the tick of `frame = F_h + round(seconds / 0.1)`, then writes to
`bench/injection.jsonl`:

```json
{"event": "injection",
 "data": {"action": "camera_stop", "t_sim_ms": 23200,
          "t_mono_ns": 1762699000123456789, "t_real_ns": 1762699123456789012,
          "detail": {"camera": "cam_rear_left", "actor_id": 103,
                     "fault": "camera_missing", "handoverFrame": 2200,
                     "afterHandoverS": 12.0}}}
```

From that tick on, the camera's `sensors[]` entry is `alive=false,
attached=false`; the other five stay true. A fault past the end of the run
never fires and is reported as `fired: false` in `summary.json`.
`run_end_brake` is accepted (the world side applies no control, so it has no
world-side effect). `FAULT_PARSERS` is the extension point; an unknown kind is
rejected with the list of supported kinds.

## Decisions taken beyond the brief

1. **`world.jsonl` holds ticks only**; lifecycle records go to
   `simulator/worldSide.jsonl` (see above). Without this `runio` cannot read the
   run at all.
2. **`control` is recorded** (OBSERVABLES §3 lists it; ICD C1 does not). Values
   come from `hero.get_control()`; `accelMps2` is `null`, because the adapter's
   command never reaches this process (changed in review: it held the measured
   acceleration under a name that says applied).
3. **`tickDurationMonoNs` and `latenessMonoNs` are in every record** (R3 allows
   the record or the summary; both carry them).
4. **`handoverFrame` is in every record** (R5) and in `summary.json`, so a
   consumer does not have to parse the marker to know where the switch is.
5. **Extra CLI options**: `--rig-path` (run the agent's `rig.py` without a
   package install), `--vehicle-config` (ICD §5 JSON; its `vehicle_blueprint`
   names the hero, default `vehicle.lincoln.mkz_2020`), `--client-timeout`,
   `--no-collision-sensors`.
6. **`lane.road` is CARLA's integer `road_id` and `lane.lane` its `lane_id`**;
   the synthetic fixture in `case-evaluators/make_synthetic_run.py` uses a map
   name and a lane number. No case reads `lane`, so the CARLA-native value wins;
   the field names are the ones OBSERVABLES fixes.
7. **The kinematics are in the map frame** (changed in review). The first
   version wrote `angular_velocity` and `lateral_mps2` in CARLA's sense, opposite
   to `egoPose` in the same record and to the evaluators' reference producer.
8. **`autopilotEnabled` reads `get_autopilot()` when the build has it** and
   falls back to the tool's own switch, which is truthful because this process
   issues every `set_autopilot` call.
9. **Sensor callbacks are attached to the record of the frame they report**; a
   callback that arrives after its frame's record was written is attached to the
   next record written, keeps its own `frame`, and is counted in
   `summary.lateSensorEvents`.
10. **Marker blueprint**: the first of `static.prop.trafficcone01`,
    `static.prop.constructioncone`, `static.prop.streetbarrier` present in the
    library, else any `static.prop.*`. CARLA 0.9.16 props carry a modifiable
    `role_name` (blueprint library documentation). `BlueprintLibrary.find`
    raises `IndexError` for an unknown id, so every lookup goes through
    `find_blueprint` (changed in review: the `is None` checks were dead code
    against the real API).
11. **Exit codes**: 1 for a bench error (after teardown, with an `error`
    record), 2 for a usage error (a non-positive width).
12. **Teardown order** (changed after the first runs on the simulator host).
    After the last tick the tool waits `LAST_FRAME_DRAIN_S` (0.3 s) so that the
    last tick's images reach drivingAgent, stops and destroys every actor while
    the world is still synchronous, and only then restores the settings. The
    first order restored asynchronous mode first: the server ran free with the
    hero and the cameras in place, and drivingAgent took a frame after the run's
    last tick, with its images missing. `summary.json` is written before
    teardown as well as after it, because a server that dies during teardown
    makes the client library's timeout abort the process.
13. **Render width** (owner decision of 2026-11-09, after the first runs on the
    simulator host). The front camera renders 1920 px wide, the five others
    1024 px (`--front-width`, `--width`). The checkpoint's input is the same
    either way: each camera resized to 512 by 512, the front also to 1024 by
    1024 (REQ-DRIVING-003). CARLA's game thread delivers the six images one
    after another, 10–12 ms apart. With all six at 1920 the sixth image came up
    to 87 ms after the tick on one host, 8 ms inside drivingAgent's 95 ms frame
    deadline, and with the planner on a second host 13 % of the frames missed
    the deadline. With the five others at 1024 it came by 69 ms on one host and
    by 82 ms across two, and no frame missed the deadline.

## Known limits

* Records are appended (the ICD §6 writer convention), so a rerun must use a
  fresh run directory or `world_by_frame()` will see duplicate frames.
* VC-DRIVING-011 loops over every world tick and requires
  `controlSource == "actuationAdapter"` (`cases.py`), without a handover filter,
  as REQ-DRIVING-011's criterion reads ("at any time of the run"). A warm-up run
  therefore fails it by design; the default run has no warm-up. Allowing an
  announced warm-up would need the run start defined as the handover, in the
  requirement's reading and in the case: an owner decision, not a world-side one.
* The C1 frame and sign conventions of `angular_velocity` rest on CARLA
  reporting deg/s about its left-handed world axes with a positive z rate for a
  right turn. `summary.yawRateCheck` (`signAgreement` against the logged poses)
  confirms or refutes that on the first CARLA run; the fake cannot.
* The `--fault` vocabulary covers `camera_stop` (and the inert
  `run_end_brake`). Other C8 actions belong to the bench controller.
* CARLA 0.9.16 crashed (signal 11) at the end of two of seven runs on the
  simulator host, as teardown began, under the first teardown order. Whether
  the order of decision 12 prevents it is not yet shown.
