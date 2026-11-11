# Closed-loop driving bench (INC-DRIVING-001, slice 10b): Interface Control Document

Version 1, 2026-11-09. This document fixes the interfaces of the bench's components, so each component can be built and tested on its own. The model is the authority: phase 8 of INC-DRIVING-001 (`textual-notation-of-model/packages/features/driving/closed_loop_driving_physical_software_realization.sysml`, as amended by PR #496), the MAP-DRIVING-* mapping items there, and the requirements REQ-DRIVING-001 to -035 (`closed_loop_driving_needs_requirements.sysml`). If this document and the model disagree, the model wins: report the disagreement, don't guess. The C++ payload types live in `include/de4sdv/driving/payloads.h`, and the log writer lives in `include/de4sdv/driving/run_log.h`.

## 1. Hosts, processes, clocks

| Host (phase 8 part) | Machine | Processes (phase 8 part) |
|---|---|---|
| S-CORE host `linuxHost : ClosedLoopDrivingLinuxHost` | GCE G4, RTX PRO 6000, Ubuntu 22.04, europe-west1-b, 10.132.0.2 | `drivingAgent` (FEO agent, 4 activities), `actuationAdapter`, `statePublisher`, `gatewayd` + `someipd`, `routeProvider`, all started by the Launch Manager |
| simulator host `simulatorHost : ClosedLoopDrivingSimulatorHost` | GCE L4 VM, 10.10.0.2 | CARLA 0.9.16 server (synchronous mode, 0.1 s fixed step), world-side pacer, chase-view recorder |
| guest host `guestHost : AAOSGuestHost` | GCE aaos-build, KVM | SDV Core VM (192.168.98.3), IVI VM; IVI runs the observer |

- **Simulation time** is the frame index times 100 ms, exact in microseconds (`CaptureTimeMicros`). Never use the simulator's float timestamp. CARLA's world frame number is the frame index.
- **Monotonic time** is `CLOCK_MONOTONIC` of the S-CORE host. Plan production time, mode decision time and command issue time use it (REQ-DRIVING-031, -032). It is valid only on that host.
- **Real time** is `CLOCK_REALTIME`, chrony-synchronised on every host. It is used only for comparisons across hosts, so every log record carries it next to the monotonic time.

## 2. mw::com events on the S-CORE host (LoLa binding, one service per event)

| Event | Producer | Consumers | Instance specifier | Payload | When | Requirements |
|---|---|---|---|---|---|---|
| ego-motion sample | agent / conditionInputs | statePublisher | `de4sdv/driving/ego_motion_sample` | `EgoMotionSamplePayload` | once per step | 016, 030 |
| plan | agent / inferPlan | statePublisher | `de4sdv/driving/plan` | `DrivingPlanPayload` | once per plan | 015, 027, 031, 034 |
| mode | agent / superviseLoop | statePublisher | `de4sdv/driving/mode` | `DrivingModePayload` | once per step, and at once on each change | 029 |
| command | agent / commandVehicle | actuationAdapter | `de4sdv/driving/command` | `VehicleMotionCommandPayload` | once per step | 011, 012, 014, 020 to 022, 032 |
| actuation state | actuationAdapter | statePublisher | `de4sdv/driving/actuation_state` | `ActuationStatePayload` | once per applied command, and at once when the adapter's stop begins | 028, 029, 032 |
| operational state | statePublisher | gatewayd → SOME/IP | `de4sdv/driving/operational_state` | three events `plan`, `vehicle_state`, `health`, each `PreSerializedData<2048>` (layout of the P4 publisher: bytes 0–1 little-endian length, the protobuf message from byte 4); the gateway maps each to its SOME/IP event (§3) | see §3 | 015 to 019, 029 |

The event name inside each of the first five service interfaces is the last segment of the specifier, for example `plan`. Each skeleton is offered once. The proxies use `FindService` on the specifier and subscribe with a max sample count of 8. A consumer never blocks a producer: a full slot is a dropped sample, which gets counted and logged, never waited on.

## 3. The operational state on SOME/IP (MAP-DRIVING-OPERATIONAL-STATE)

There is one SOME/IP service with three events, and each carries one `DrivingOperationalState` message. The VSIDL message of the typed path has the same name and fields.

| | value |
|---|---|
| service / instance | `0x4DF0` / `0x0001` (the AEBS frame of P4 is `0x4DEE`) |
| events | `0x8001` plan, `0x8002` vehicle state, `0x8003` health; eventgroup `0x0001`; reliable (TCP), port 30510 |
| serialization | protobuf wire format (proto3) of the message below; repeated scalars packed |

```proto
syntax = "proto3";
package de4sdv.driving.v1;
enum Kind { KIND_UNSPECIFIED = 0; PLAN = 1; VEHICLE_STATE = 2; HEALTH = 3; }
message DrivingOperationalState {
  uint32 schema_major = 1;        // 1
  uint32 schema_minor = 2;        // 0
  Kind kind = 3;
  uint64 sequence = 4;            // per kind, from 1, no gaps
  string producer = 5;            // "statePublisher"
  double publish_time_real = 6;   // CLOCK_REALTIME seconds at serialization
  double publish_time_mono = 7;   // CLOCK_MONOTONIC seconds of the S-CORE host
  // kind == PLAN
  uint64 plan_frame_index = 10;
  double plan_capture_time = 11;  // simulation seconds
  double plan_production_time = 12; // monotonic seconds (the plan's own stamp)
  string plan_reference = 13;
  string run_record = 14;
  repeated float plan_acceleration = 15;  // 64, m/s^2
  repeated float plan_curvature = 16;     // 64, 1/m
  repeated float plan_x = 17;             // 64, m
  repeated float plan_y = 18;             // 64, m
  // kind == VEHICLE_STATE (the motion sample, VSS units)
  float speed_kmh = 20;
  float longitudinal_acceleration = 21;
  float lateral_acceleration = 22;
  float yaw_rate_dps = 23;
  double sample_capture_time = 24;        // simulation seconds
  double sample_receipt_time_mono = 25;   // when the publisher received it
  // kind == HEALTH
  uint32 mode = 30;              // de4sdv::driving::Mode value
  uint32 cause = 31;             // de4sdv::driving::Cause value
  string mode_source = 32;       // "superviseLoop" or "actuationAdapter"
  double cause_since_mono = 33;  // when the stop began (monotonic), 0 if none
  uint64 last_plan_frame_index = 34;
  uint64 dropped_samples = 35;   // publisher-side drops so far
}
```

Publisher timing:
- Plan: each plan is published within 100 ms after its production (REQ-DRIVING-015).
- Vehicle state: each motion sample is published within 100 ms after its receipt (REQ-DRIVING-016).
- Health: published every 100 ms of monotonic time whether or not plans arrive, which leaves margin under the 200 ms limit of REQ-DRIVING-017. It is also published at once when the mode becomes `kStopResponse`/`kStandstill`/`kRefused`, or when an actuation state reports `stopInForce`, with the cause (REQ-DRIVING-029).
- The publisher receives nothing from the observation path (REQ-DRIVING-018, -019).

## 4. Stop response (REQ-DRIVING-020 to -029)

- **Causes:** every cause is a `Cause` value. The supervision decides 023 to 027 at the step. The commander also checks 026 at the command. The adapter decides 028.
- **In the stop response:**
  - The command is `acceleration = -4.0`, with `steeringAngle` held at the last value computed from a valid plan.
  - At standstill (speed < 0.1 km/h), the command is `acceleration = -4.0` with brake applied, held until the run ends. The stop never clears within a run.
- **Adapter:** if no valid command has reached it for 200 ms of simulation time, measured from the actuation time of the last applied valid command, it applies the same stop response by itself. It then publishes an `ActuationStatePayload` with `stopInForce = 1` and `cause = kCommandTimeout`.
- **Valid command:**
  - both values are finite and inside the limits of §5;
  - `planReference` is non-empty;
  - `productionTime` is no more than 300 ms of monotonic time old at arrival.

## 5. Vehicle limits configuration (REQ-DRIVING-012)

There is one JSON file per run, named by the run record. Both the commander and the adapter read it:

```json
{"vehicle_blueprint": "vehicle.lincoln.mkz_2020", "wheelbase_m": 2.85,
 "max_acceleration_mps2": 3.0, "max_deceleration_mps2": 8.0,
 "max_road_wheel_angle_deg": 35.0, "max_steering_rate_deg_per_s": 180.0}
```

These values are placeholders. The bench calibration replaces them from the vehicle's physics control: the wheelbase from the wheel positions, the angle from the front wheels' `max_steer_angle`.

- **Commander:**
  - `steeringAngle = clamp(deg(atan(wheelbase * curvature)), ±max_road_wheel_angle)`;
  - `acceleration = clamp(a, -max_deceleration, +max_acceleration)`;
  - the steering rate is limited per step.
- **Adapter:**
  - `steer = clamp(-steeringAngle / max_road_wheel_angle, -1, 1)`. CARLA steers right for positive values.
  - Throttle and brake come from the commanded acceleration through the adapter's longitudinal controller (§S2 of the bench plan).

## 6. Logs (every component, every port crossing)

Each process writes one JSONL file `<run_dir>/<host>/<component>.jsonl` through `run_log.h` (C++) or the same format from Python:

```json
{"t_mono_ns": 123, "t_real_ns": 456, "host": "score", "component": "statePublisher", "event": "out.operational_state", "seq": 7, "data": {...}}
```

- **`event`:** `in.<port>` or `out.<port>` for each sample received or sent, carrying the full payload in `data` (floats as JSON numbers, enums as their names). Lifecycle events are `start`, `ready`, `stop`, `drop`, `error`, `config`.
- **Stop response:** the moment a stop starts (`stop_response.begin`) and the moment it reaches standstill (`stop_response.standstill`) are logged, with the cause.
- **Timing:** never compute a latency in the component. Log both stamps; the evaluators compute.
- **Ordering:** records are flushed line by line. The order within one file is the order of writing.

## 7. Run directory

```text
<run_dir>/run_record.json          # identity: §8
<run_dir>/score/*.jsonl            # agent, adapter, publisher, gatewayd/someipd logs, route provider
<run_dir>/simulator/world.jsonl    # pacer: one record per tick (frame, sim time, ego pose, velocity, control applied, collisions, lane invasions)
<run_dir>/simulator/view.mp4       # chase view (NVENC), recorder summary.json
<run_dir>/guest/observer.jsonl     # observer receipts (real time + decoded message)
<run_dir>/guest/ivi_screen.mp4     # screenrecord
<run_dir>/terminals/*.cast         # real terminal sessions (asciinema)
<run_dir>/MANIFEST.sha256
```

## 8. Run record (REQ-DRIVING-033, -034, -035)

`run_record.json` is written by the inference activity before the first plan. It holds:
- the fields of `RetainedDrivingRunEvidence` that are known at start: configurationIdentity, checkpointSha256, autoE2ESourceRevision, configurationSha256, scoreFEORevision, scoreCommunicationVersion, scoreLifecycleVersion, scoreSOMEIPGatewayCommit, simulatorBuild, scenario, executionEnvironmentIdentity, contractIdentity = `de4sdv.driving.icd.v1`;
- the cuDNN version, the parity check result and the warm-up step count.

Its identity (`runRecord` in each plan) is the first 16 hex digits of the SHA-256 of the file.

## 9. Route (MAP-DRIVING-ROUTE)

- **Route file:** JSON `{"map": "Town10HD_Opt", "waypoints": [[x, y, heading_rad, road_id], ...], "destination": [x, y]}`. It is in the map frame, right-handed: CARLA's y is negated, and the converter documents its conversion.
- **Provider:** sends a `RouteAnnouncement` to UDP 127.0.0.1:47110 every 500 ms of simulation time. It learns the simulation time from the world ticks.
- **Fault knobs:**
  - stop announcing, which leaves the route stale;
  - announce `corridorPoints = 0`, which is "no corridor".
