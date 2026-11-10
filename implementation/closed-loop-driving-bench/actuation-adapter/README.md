# Actuation adapter (S2) — INC-DRIVING-001, slice 10b

The adapter is the only element that touches the simulated vehicle control. It
subscribes to the `de4sdv/driving/command` mw::com event (ICD v2 §2, service id
7404), converts the commanded acceleration and front-wheel angle into CARLA's
`VehicleControl` (throttle, brake, steer), applies it to the `hero` vehicle, and
publishes its actuation state on `de4sdv/driving/actuation_state` (service id
7405). When no valid command reaches the actuation for 200 ms of simulation
time, it applies the stop response itself (REQ-DRIVING-028) and latches it for
the run.

| File | What |
|---|---|
| `adapter_core.{h,cpp}` | decision logic, pure C++17, no simulator or middleware; thread-safe |
| `adapter_config.{h,cpp}` | ICD v2 §5 vehicle configuration + calibration table |
| `log_records.h` | the §6 JSONL record builders (header-only, unit tested) |
| `json_lite.{h,cpp}` | minimal JSON parser for the one configuration document |
| `tests/adapter_core_test.cpp` | simulation-based unit tests (plain g++) |
| `tests/simulated_vehicle.h` | longitudinal point mass + lag + kinematic bicycle, steering with its own maximum (70°, CARLA's mkz_2020) |
| `tests/fit_calibration_test.py` | tests the calibration fitter on synthetic step responses |
| `tests/test_libcarla_shell.py`, `tests/test_shell_vehicle_steering.py` | static checks of the LibCarla shell: list lifetime; the steer's full scale from the vehicle |
| `scripts/fit_calibration.py` | fits the acceleration→pedal table from `world.jsonl` |
| `actuation_adapter_main.cpp` | S-CORE mw::com + LibCarla shell |
| `BUILD.bazel` | Bazel targets (S-CORE toolchain, LibCarla 0.9.16) |
| `mw_com_config_actuation_adapter.json` | mw::com service types/instances (7404, 7405) |
| `config/vehicle_limits.json` | placeholder run configuration, ICD v2 §5 shape |

## Build and test (this machine)

```sh
cd implementation/closed-loop-driving-bench/actuation-adapter
g++ -std=c++17 -Wall -Wextra -Werror -I. -I../interfaces/include -Itests \
    tests/adapter_core_test.cpp adapter_core.cpp adapter_config.cpp json_lite.cpp \
    -o .build/adapter_core_test
.build/adapter_core_test config/vehicle_limits.json
python3 tests/fit_calibration_test.py
python3 -m pytest -q tests/test_libcarla_shell.py tests/test_shell_vehicle_steering.py
```

Both exit 0 on this machine (aarch64, g++ 11.4). The numbers are in
[Verification](#verification).

## Decision logic

State: the newest valid command, the simulation time of its actuation
(`CaptureTimeMicros(frame)`), the reference speed, the PI integral, the stop
latch, and the stop's monotonic stamp.

**Command validity** (ICD v2 §4), checked at arrival on the mw::com thread:

1. `acceleration`, `steeringAngle`, `productionTime` finite;
2. `acceleration ∈ [-max_deceleration, +max_acceleration]`,
   `|steeringAngle| <= max_road_wheel_angle`;
3. `planReference` has at least one non-NUL character;
4. `-5 ms <= arrival − productionTime <= 300 ms` (monotonic, same host).

The lower bound is the v2 addition: a stamp in the future is not trusted, so a
command produced more than 5 ms after its arrival (clock skew or a replayed
sample) is dropped. An invalid command changes nothing and is counted per
reason; the shell logs it as `in.command` with `valid:false` plus a `drop`
record with the reason. A command that arrives before the first world snapshot
is held and applied at the first tick (its actuation time is that tick). A
command that arrives after the stop is latched is rejected with `stop_latched`.

**Watchdog.** On every world tick, if a command is in force and
`tickMicros − lastActuationMicros > 200000`, the adapter starts its stop. The
comparison is in integer microseconds, so the stop begins at the third tick
after the last actuation (300 ms), not at the second (200 ms): with a command
every 100 ms, two missed commands mean the path has stopped (REQ-DRIVING-028).
A command arrives about one period after its frame's tick, so one late command
sees exactly 200 ms at the tick before it, as one missed command does; neither
starts the stop. On the simulator host the earlier `>= 200000` stopped the
vehicle about 2 s into a run in which no command was missing: one command
arrived 2 ms after the next tick. The stop then reaches the actuation 300 ms of
simulation time after the last applied command, REQ-DRIVING-028's limit. The
stop latches: later commands are rejected, and the latch never clears within
the run.

**The stop.** `acceleration = −min(4, max_deceleration)`: −4 m/s² on the
placeholder vehicle, −3 on a vehicle configured to brake at most 3 m/s², so the
stop never violates REQ-DRIVING-012. Steering is held at the last valid
command's `steeringAngle` (0 if none was ever applied). At standstill (speed <
0.1 km/h, `standstill_speed_kmh`) the brake is held for the rest of the run.
The stop never applies throttle. A contact can slow the vehicle faster than the
stop's profile, and the speed error would then call for throttle. When it does,
the reference speed is set to the measured speed and the integral keeps no
forward part, so the stop brakes with at least its feedforward. While the
vehicle follows the profile, the stop is the same as before.
The stop publishes `stopInForce = 1`, `cause = kCommandTimeout`,
`stopSince` (simulation seconds of the stop-begin tick) and `stopSinceMono`
(CLOCK_MONOTONIC seconds of the same tick, ICD v2 §4). The core takes the
monotonic time as an input (`WorldTick::monotonicSeconds`), so both stamps are
testable without a clock.

**Steering.** `steer = clamp(-steeringAngle / vehicle_max_steer_angle_deg, -1, 1)`:
the commanded road-wheel angle over the vehicle's maximum steering angle, as the
model's actuation mapping reads (ICD A30). The shell reads that maximum from
CARLA at start-up, the front wheels' `max_steer_angle` (70° for
`vehicle.lincoln.mkz_2020`); `max_road_wheel_angle_deg` (35°) only bounds a valid
command. The command is positive left, CARLA's `steer` positive right.

**Longitudinal.** A feedforward lookup plus a PI correction on the speed error
against a reference speed integrated from the commanded acceleration:

- `s_ff = throttle_ff(a) − brake_ff(a)`, linear interpolation of the config
  table (clamped at both ends);
- the reference speed is anchored to the measured speed at the first applied
  command (and re-anchored only if the vehicle diverges more than 5 m/s from it,
  e.g. blocked or teleported); each tick `v_ref += a·dt`, clamped at 0;
- `s = s_ff + kp·(v_ref − v) + ki·∫(v_ref − v)dt`, error clamped to ±5 m/s,
  integral clamped to ±`integrator_limit`; conditional integration stops while
  the effort is saturated in the direction of the error (anti-windup);
- `throttle = max(s, 0)`, `brake = max(−s, 0)`: one pedal, never both;
- `hand_brake` is always false (the model keeps the client's hand brake,
  reverse and gear at their defaults).

**Before the first command** the adapter holds the brake (no latch, no state
event). This is ICD v2 §4's rule: "Before the first valid command, it holds the
brake, without latching a stop."

## Configuration (ICD v2 §5)

One JSON file per run; the commander and the adapter read the same one. The ICD
v2 shape is what `config/vehicle_limits.json` holds:

```json
{"vehicle_blueprint": "vehicle.lincoln.mkz_2020", "wheelbase_m": 2.85,
 "max_acceleration_mps2": 3.0, "max_deceleration_mps2": 8.0,
 "max_road_wheel_angle_deg": 35.0, "max_steering_rate_deg_per_s": 180.0,
 "command_law": "pure_pursuit",
 "longitudinal_controller": {"table": [[-8.0, 0.0, 1.0], [0.0, 0.0, 0.0], [3.0, 0.75, 0.0]],
                             "kp": 0.3, "ki": 0.05, "integrator_limit": 0.3}}
```

The adapter reads:

- the limits and `vehicle_blueprint` (validity, steering clamp, `config` record);
- `command_law`: accepted, logged as `commandLaw`, then **ignored** — the
  commander owns the law, the adapter applies whatever command arrives;
- `longitudinal_controller.table`: rows are `[acceleration_mps2, throttle,
  brake]`; the older object row `{"acceleration_mps2":..,"throttle":..,"brake":..}`
  is still accepted (the calibration fitter used to write it);
- `longitudinal_controller.kp`/`ki` → `speed_kp`/`speed_ki`. The earlier names
  `speed_kp`/`speed_ki` remain valid aliases; `kp`/`ki` win when both are given;
- `longitudinal_controller.integrator_limit`.

Adapter-only extensions, documented here because the ICD does not name them:

| Key | Default | Why |
|---|---|---|
| `longitudinal_controller.standstill_brake` | 1.0 | brake held at standstill |
| `longitudinal_controller.standstill_speed_kmh` | 0.1 | REQ-DRIVING-022 standstill threshold |
| object table rows | — | older calibration files still parse |

Absent `longitudinal_controller`, a built-in demo table is used and the `config`
record says `table_source: "default"`. The numbers in the checked-in file are
placeholders; the run's calibration replaces the table (below).

## Logs (ICD v2 §6)

`<run_dir>/<host-name>/actuationAdapter.jsonl`, one record per line via
`run_log.h`: `t_mono_ns`, `t_real_ns`, `host`, `component`, `event`, `seq`,
`data`. Events: `start`, `config`, `ready`, `in.command`, `drop`,
`out.vehicle_control`, `out.actuation_state`, `stop_response.begin`,
`stop_response.standstill`, `error`, `stop`.

Clock naming follows §6 as follows (`log_records.h` builds and tests these):

- payload fields keep their model names and a sibling `clocks` object names the
  clock of each time field — `out.actuation_state`:
  `"clocks":{"actuationTime":"simulation","stopSince":"simulation","stopSinceMono":"monotonic"}`,
  `in.command`/`drop`: `"clocks":{"productionTime":"monotonic"}`;
- shell-only time fields carry the suffix themselves: `t_sim_ms` (frame × 100,
  exact integer) and `arrival_mono_s`;
- no computed latencies: `in.command` logs `productionTime` and
  `arrival_mono_s`, and the evaluators compute the age;
- `drop` carries the reason, both stamps and `droppedTotal` (the adapter's
  running count of dropped commands, ICD v2 §4 "counted");
- non-finite numbers are JSON `null`.

`out.vehicle_control` carries what was applied:
`{"frame":37,"t_sim_ms":3700,"throttle":..,"brake":..,"steer":..,
"handBrake":false,"trigger":"command|tick|stop|hold",
"controlSource":"actuationAdapter","clocks":{"t_sim_ms":"simulation"}}`.
`stop_response.begin` carries the cause, `actuationTime`, `stopSinceMono` and
the applied acceleration/angle; `stop_response.standstill` carries the cause,
`frame`, `t_sim_ms` and the speed.

## Calibration

The table is the steady-state pedal that holds each acceleration on the pinned
simulator and vehicle. It is speed-independent by design; the PI absorbs the
speed dependence (drag, gear) within its authority.

1. Run a calibration run with **open-loop pedal steps**: constant throttle and
   brake plateaus of 1.5–3 s each, over 0.05 pedal steps, at several speeds
   (5–25 m/s), with the pacer logging `world.jsonl`. A normal closed-loop run
   has few constant-pedal plateaus and gives a poor fit.
2. Fit:

   ```sh
   python3 scripts/fit_calibration.py \
       --world <run_dir>/simulator/world.jsonl \
       --out <run_dir>/calibration_table.json
   ```

   The script takes the central difference of speed as acceleration, keeps
   quasi-steady ticks (pedals constant over the neighbouring ticks), and for
   each target acceleration takes the median pedal within ±0.3 m/s² on the
   matching side. It prints the residual RMS and writes ICD v2 array rows.
3. Merge the table into the run's vehicle configuration:

   ```sh
   jq -s '.[0] * {longitudinal_controller:
            (.[0].longitudinal_controller + {table: .[1].longitudinal_controller.table})}' \
       config/vehicle_limits.json <run_dir>/calibration_table.json \
       > <run_dir>/vehicle_limits.json
   ```

4. Check that `fit.residual_rms_mps2` is small (the synthetic test gets 0.027)
   and that the row near −4 m/s² has a brake value the stop test can use.

`world.jsonl` field names are not fixed by ICD §7 yet. The fitter accepts, at
top level or under `data`: time (`t_sim`, `sim_time`, `capture_time`, `time`,
`t`, or `frame`/`frame_index` at 0.1 s), speed (`speed_mps`, `speed`,
`speed_kmh`, or `velocity` as `[x,y,z]`/`{x,y,z}`), and the applied control
(`control.throttle`/`.brake`, `control_applied.*`, or `throttle`/`brake`). It
must be the *applied* pedal.

## S-CORE shell

```sh
bazel build --config=x86_64-linux //...:actuation_adapter
MW_COM_CONFIG=$PWD/mw_com_config_actuation_adapter.json \
  ./actuation_adapter --run-dir /runs/r1 --config /runs/r1/vehicle_limits.json \
                      --host-name score --carla-host 10.10.0.2
```

- Service ids in `mw_com_config_actuation_adapter.json`: command 7404,
  actuation state 7405, both `instanceId` 1, event name = last specifier
  segment (ICD v2 §2). A different id in a peer's configuration means the two
  processes do not bind to each other.
- Connects to `--carla-host:2000`, waits up to 20 s for a vehicle whose
  `role_name` attribute is `hero`, reads its physics control (wheel positions →
  wheelbase, front wheels' `max_steer_angle`), logs a `config` record with the
  CARLA values next to the configured ones, their deltas, the `command_law` and
  the table source. The front wheels' `max_steer_angle` becomes the steer's full
  scale (`steer_full_scale_deg` in that record). Without one, or with one below
  `max_road_wheel_angle_deg`, the adapter logs an `error` record and exits with
  status 14 before it applies any control.
- Registers `World::OnTick`; the mw::com receive loop runs on its own thread.
  One mutex serialises the core call, `ApplyControl`, the skeleton send and the
  log write in both paths. Each tick passes `MonotonicSeconds()` as
  `WorldTick::monotonicSeconds` — that value becomes `stopSinceMono` when the
  watchdog stop begins.

## Verification

```
$ .build/adapter_core_test config/vehicle_limits.json
TRACKING target=+1.50 m/s^2 mean_accel=+1.5222 error=+0.0222 m/s^2 ...
TRACKING target=+0.00 m/s^2 mean_accel=-0.0010 error=-0.0010 m/s^2 ...
TRACKING target=-2.00 m/s^2 mean_accel=-1.9882 error=+0.0118 m/s^2 ...
STOP mean_decel=-3.9609 m/s^2 duration=5.10 s states=1
STOP_CLAMPED mean_decel=-2.9656 m/s^2 duration=6.80 s min=-3.5384
ADAPTER_CORE_TESTS PASS: 631 checks, 0 failures

$ python3 tests/fit_calibration_test.py
FIT_TABLE rows=23 mean_abs_reproduction_error=0.120 m/s^2 max=0.500 m/s^2
FIT_CALIBRATION_TESTS PASS: 76 checks, 0 failures
```

The same test binary built with `-fsanitize=address,undefined` passes 631/631
with no sanitizer report.

Covered: constant-acceleration tracking (above), the watchdog at 300 ms and not
at 100 or 200 ms, one late or missed command not stopping the vehicle (the
simulator-host case), a command at the boundary preventing the stop, an invalid command
not refreshing the watchdog, stop to standstill at ≈4 m/s² with held steering,
standstill hold to the end, latching with rejection afterwards, the validity
window at both edges (−5 ms and 300 ms; `future_production_time` below it),
`stopSinceMono` equal to the tick's monotonic input and zero on applied
commands, the stop clamped to a 3 m/s² vehicle (state, control and mean
deceleration), invalid commands changing nothing (NaN, out of limits, empty
reference, stale, future, non-finite production time), steering signs and clip,
the steer scaled by the vehicle's maximum steering angle so the simulated
vehicle's wheels turn by the commanded angle (70° at steer ±1 against the 35°
limit), that maximum refused when not finite and positive or below the limit, a
straight steer without it,
agent stop as an ordinary command, the 3 s startup hold without latch, the
actuation-state bookkeeping, the ICD v2 §5 document verbatim (array rows,
`kp`/`ki`/`integrator_limit`, `command_law`) with its error cases, and the log
records (field names, `clocks` maps, `t_sim_ms`, `controlSource`, JSON `null`
for non-finite).

## What is untested

- **The shell is not compiled here.** There is no S-CORE, LibCarla or CARLA on
  this machine. It is syntax-checked (`-fsyntax-only`, `-Wall -Wextra -Werror`)
  against hand-written minimal stubs of the API surface it uses; that catches
  C++ mistakes, not API mismatches with Communication v0.6.0 or LibCarla 0.9.16.
- `Event<struct>` with the payload structs: assumed supported because they are
  standard-layout and trivially copyable (the reason `payloads.h` locks that in).
  Not verified on the S-CORE toolchain.
- The CARLA vehicle response: the table in `config/vehicle_limits.json` is a
  placeholder (ICD §5 says so); no CARLA run was made. The wheelbase and max
  steer angle reported by the Lincoln are unknown until the first run's
  `config` record.
- Real latency, drops under load, and mw::com reconnection after the agent
  restarts. The shell counts drops only through the core's reject counts and
  skeleton allocate failures.
- Concurrent-stress of the two threads beyond correctness of the locking design.

## ICD v2 issues still open (reported, not patched here)

1. **§6 says two different things about time fields.** "Every time field inside
   `data` names its clock by a suffix" cannot hold for payload fields, because
   the payload name is fixed by the model (`productionTime`, `actuationTime`,
   `stopSince`). Implemented as: payload fields keep their names with the
   sibling `clocks` map; shell-only fields take the suffix. Proposed: say
   exactly that in §6, and fix the `clocks` values as `simulation` /
   `monotonic` / `real` (the document does not name the strings).
2. **§2's service id table is not implemented by the other component.**
   `state-publisher/mw_com_config_state_publisher.json` uses 21001–21005 (and
   `Driving*` type names) for the same events, so statePublisher would not bind
   to 7401–7406. Needs the same edit outside this package.
3. **`stop_response.standstill` "with the cause"** — ambiguous whether the
   standstill record also carries the cause. Implemented with it.
4. **§7 `world.jsonl` field names** are still unfixed, so the calibration
   extractor guesses (`t_sim`/`speed_mps`/`control.{throttle,brake}` proposed
   earlier and still the sensible set).
5. **`ActuationStatePayload` has no actuation-issue time**, so an evaluator
   cannot compute issue→actuation latency for a stop from the payload alone; the
   log records carry both stamps.
