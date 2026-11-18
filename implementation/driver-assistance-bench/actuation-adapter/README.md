# Actuation adapter (INC-DRIVING-002)

Status: draft, not yet validated. The host's unit tests pass; nothing here has run against CARLA or
S-CORE.

## The problem

The bench judges VisionPilot's driving command on the Eclipse S-CORE path. The command must reach the
simulated vehicle over that path and nowhere else (REQ-DRIVING-038), and the actuation must be able to detect
a command that the path lost, delayed, repeated or corrupted (REQ-DRIVING-039) and must not apply it
(REQ-MW-006). The adapter is the actuation end of that path: the part def `DrivingCommandActuationAdapter` of
the phase 8 realization
(`textual-notation-of-model/packages/features/driving/driver_assistance_physical_software_realization.sysml`,
cited below as PSR).

## What it does and does not do

It does:

- subscribe to the `driving_command` event (ICD.md: service 7411, `DrivingCommandEventPayload`);
- take the simulation time and the ego vehicle's speed from each world snapshot of its simulator client;
- reject a command it detects as lost, repeated, corrupted or delayed, and apply nothing in its place;
- apply an accepted command once, at its arrival, as CARLA's Ackermann control;
- log every input and output.

It does not:

- run a PI loop or any other controller;
- run a watchdog, stop the vehicle or apply a neutral control. The model gives it no stop response
  (the part def: "It has no stop response of its own"), so after a rejection the simulator keeps the last valid
  control;
- set the autopilot or apply any other control (the part def: "The autopilot of the ego vehicle stays off");
- tick the world, or publish anything on S-CORE communication.

## Rules and their source

All come from the `transformationRule` of the signal mapping `MAP-DRIVING-DA-COMMAND` ("rule" below) and the
part def `DrivingCommandActuationAdapter` ("part def"), as the adapter counting decision of 2026-11-18 amended
them. `tests/test_actuation_adapter_model_rules.py` reads the rule and the numbers from the model file at test
time and compares them with `actuation_core.h`.

| Rule | Implemented as | PSR element |
|---|---|---|
| Reference count | the highest `sequenceCount` among the commands received earlier in the run whose check value holds; 0 before the first | rule, part def |
| Corruption | `DrivingCommandCheckValue(command) != checkValue` (ICD.md's CRC32), checked first; the reference stays | rule, part def |
| Repetition | `sequenceCount <= reference`, also an older count; the reference stays | rule, part def |
| Loss | `sequenceCount > reference + 1`: the command that reveals the gap is rejected and its count becomes the reference | rule, part def |
| First command | the reference starts at 0, so the first command must carry 1 ("from 1 in each run") | `dataTypeAndUnit`, part def |
| Delay | for `sequenceCount == reference + 1`: `round(newest * 1000) - round(issue * 1000) > 100`, in whole milliseconds; the count becomes the reference, accepted or not; no snapshot yet, or a time that is not finite, is a delay | rule, part def |
| Nothing in its place | a rejected command is logged and dropped | rule, part def |
| Steer | `-steeringAngle * pi / 180` rad, positive to the right | rule |
| Speed | `max(0, v + 2 * acceleration)`, v from the newest snapshot | rule, part def |
| Acceleration, jerk, steer speed | unchanged; `10.0`; `0.0` | rule |

The constants match upstream's own simulator path at `014e0e7a`
(`Simulation/CARLA/ROS2/src/carla_control_publisher/carla_control_publisher/carla_control_publisher_node.py:44-53`).

What the reference count costs: a late command or a repetition costs that one command; a loss or a
corruption costs the lost or corrupted command and the next one, which reveals the gap. None of them makes later
valid commands fail. A corruption that the check value misses is not one of them: with a higher count it would
become the reference count, and later valid commands would be rejected as repetitions. A gap of k lost commands
in a row costs k + 1 commands: the k lost ones and the one that reveals the gap. A lost count that arrives late is
a repetition.

Readings the model leaves open:

- **Delay boundary.** The 0.05 s step makes every simulation time a whole number of milliseconds (ICD.md), so
  two steps are not a delay, although `12.55 - 12.45` is `0.10000000000000142` as doubles.
- **An issue time newer than the newest world time** is accepted; the model rejects only an older one.
- **A non-finite control**: the core accepts the command (its count becomes the reference); the shell does
  not send the control and logs an `error`.

## Records

`<run_dir>/<host>/actuationAdapter.jsonl`, in the record format of the closed-loop bench. The field names are
this component's proposal.

| Event | Data |
|---|---|
| `in.world_snapshot` | `frame`, `t_sim_s`, `egoPresent`, `speed_mps`, `kept` |
| `in.driving_command` | `seq`, `crc_ok`, `issueTime_sim_s`, `newestWorldTime_sim_s`, `verdict`, `referenceSeq` and the command's fields |
| `drop` | `reason` (`loss`, `repetition`, `corruption`, `delay`), `seq`, `referenceSeq` and both times |
| `out.ackermann_control` | `frame`, `t_sim_s` (of the newest snapshot), `seq` and the five floats given to the client |
| lifecycle | `start`, `config`, `ready`, `error`, `stop` |
| `supervision` | `state` `start` (`period_s`, `running_reported`), `stop` (`alive_reported`), `off` or `error` (`reason`), and `t_mono_s` |

`referenceSeq` is the reference count the decision was made against, before the command.

## Supervision by the Launch Manager

The supervision decision of 2026-11-18 has the Launch Manager supervise the adapter by its alive notifications
(`alive_ticker.h`). Once subscribed to the command event, after the `ready` record, the adapter reports running;
from then on its receive loop gives one alive notification per 0.1 s, whether or not a command arrives, and none
after a stop signal. After a stall of the loop it gives one notification and then the period again, never a burst.
`lifecycle_client_score.cpp` is the client on Lifecycle v0.10.0 (`alive_cc`, `lifecycle_cc`). Without
`LCM_ALIVE_INTERFACE_PATH`, that is, not started by the Launch Manager as a supervised component, the adapter runs
unsupervised and records `supervision` with `state` `off`. The values, the run targets and the reaction are in
[`../launch-manager/README.md`](../launch-manager/README.md).

## mw::com values pending the B6 manifests

ICD.md fixes the service id 7411, the specifier `de4sdv/driver_assistance/driving_command` and the event name.
The rest of `mw_com_config_actuation_adapter.json` is the lead's choice, after the warning request's pattern,
pending the B6 manifests; the candidate's configuration must say the same:

| Value | Choice |
|---|---|
| Service type name | `/de4sdv/driver_assistance/DrivingCommand` |
| Event id, instance id, binding | 1, 1, SHM |
| Subscribers | 1, the adapter |
| Sample slots | 25, as INC-DRIVING-001's driving command event (7404), the same kind of event: one command per plan, from the planner's process to the actuation adapter |
| ASIL level | `B` on the instance and `global.asil-level` `B`, by the supervision decision of 2026-11-18; Communication v0.6.0 requires the global level with it. No ASIL claim |
| Application id | 3413, distinct from the host's other processes, which share one uid |

The candidate's side is `../score-path/config/mw_com_config_vision_pilot.json`.

## Files and tests

`actuation_core` holds the rules (C++17); `adapter_shell` applies and logs; `simulator_client.h` is the
simulator client as a plain function interface; `simulator_client_carla.cpp` is its CARLA 1.0 unit (C++20);
`actuation_adapter_main.cpp` is the S-CORE application.

```sh
python -m pytest -q implementation/driver-assistance-bench/actuation-adapter/tests
```

The suite is registered in `SUITES` of `tools/run_bench_unit_tests.py`. It builds the core and shell tests
with g++ as C++17 and C++20, drives the shell against a fake client, and checks the CARLA unit and the main by
their text. The main is compiled for syntax against the closed-loop bench's mw::com mock, which is not S-CORE.

## What the B2 workspace still has to show

- **The CARLA 1.0 unit compiles, links and runs.** No LibCarla is on this host. The readiness probe h of phase 8 ran part of
  its calls on CARLA 1.0; `World::OnTick`, `RemoveOnTick`, `WorldSnapshot::Find`, `GetActors`,
  `ActorList::Filter` and `Actor::GetAttributes` it did not. Their signatures were read in the 1.0 headers,
  not compiled. At stop, a snapshot callback already running when `RemoveOnTick` returns is not waited for.
- **The mw::com binding works.** The real proxy finds, subscribes to and receives the event with the values
  above.
- **The labels resolve**: `//de4sdv_da_bench/interfaces:driver_assistance`, `@libcarla//:client`,
  `@score_communication//score/mw/com` and `@score_lifecycle//score/launch_manager:alive_cc` and `:lifecycle_cc`.

## What the second phase 10 probe must show

That probe runs the simulator host and the S-CORE host together.

- **ASM-DRIVING-005**: the commanded against the achieved deceleration up to 5.0 m/s², with a
  jerk of 10.0, on the scenario's vehicle and road.
- **ASM-DRIVING-006**: the steering sign on the simulated vehicle. With the ego vehicle placed
  to the right of its lane centre, the candidate's commands turn it left, by the sign of the yaw rate.
- **The drops of a real run.** The candidate's issue times must stay within 0.1 s of simulation time of the
  newest snapshot. A single drop costs at most two commands, and a gap of k lost commands k + 1, during which
  the simulator keeps the last valid control.
