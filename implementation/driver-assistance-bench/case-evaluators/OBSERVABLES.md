# Observables of the S1 verification cases (INC-DRIVING-002)

The evaluators of VC-DRIVING-036 to -038 and -040 to -044 read the records of one S1 session. This file is the
contract between the evaluators and the producers. It names every record, field and clock that a case reads, the
terms that the cases compute from them, and the text that a case writes when a field is missing. VC-DRIVING-039 is an
analysis of the realization and reads no run (`driver_assistance_verification_evidence.sysml:434-465`); it has no
evaluator here.

Paths: `M/` = `textual-notation-of-model/packages/features/driving/`, `B/` =
`implementation/driver-assistance-bench/`. The model files are read-only for the bench.

## Outcomes

Each case gives one of the six literals of `AssistanceEvidenceOutcome` (`M/driver_assistance_verification_evidence.sysml:120-138`),
and its verdict by `MapAssistanceEvidenceOutcomeToVerdict` (`:140-148`):

| Outcome | Verdict | When |
|---|---|---|
| `passBoundedVerification` | pass | the criterion met on every run it reads, every setting it needs judged |
| `passBoundedValidation` | pass | never: no case of this slice validates (`:129-130`) |
| `failObservedBehavior` | fail | a judged run, or a run the criterion reads, shows the criterion not met |
| `inconclusiveMissingEvidence` | inconclusive | a missing run, record or field; a setting not judged; a dropped image in the judged window |
| `blockedTargetRuntime` | inconclusive | the bench could not perform the run (the stop run's `path_stop` with `rc` not 0) |
| `errorEvidence` | error | a record that cannot be read (a line that is not JSON, a field of the wrong type) |

Campaign rule (`evaluate_da_campaign.py`): a fail on any run read gives fail; otherwise an error gives error;
otherwise a blocked run gives blocked; otherwise any missing evidence gives inconclusive; otherwise pass. An
observed failure is evidence on its own: a setting with one judged run that fails gives fail even when its other run
is not judged. A setting that is not judged never gives pass (VC-036 doc `:333-335`).

## Records

The evaluators read the records as the session fetches them: the incoming session tree, the same layout the
attempt-3 records have (`sessions/incoming_20261120T092051Z/`). `runio_da.py` finds each file of a run under the
session root by its name pattern; two different copies of one file are an `errorEvidence`.

| Key | File (pattern under the session root) | Host, clock | Producer |
|---|---|---|---|
| W | `world_<run>/simulator/world.jsonl`, event `tick` | simulator; `data.simTimeS` (sim), `data.frame` | `B/world-side/da_world_side.py:505-561` |
| W-set | `world_<run>/simulator/setting_record.json` | simulator | `B/world-side/da_world_side.py:706-729` |
| S | `score_<run>/score_side/run/score/score_interface.jsonl` | S-CORE host; `sim_s`, `issueTime_sim_s` (sim), `mono_ns` | `B/score-interface/` |
| A | `score_<run>/score_side/run/score/actuationAdapter.jsonl` | S-CORE host; `t_mono_ns`, `data.t_sim_s` | `B/actuation-adapter/` |
| I | `score_<run>/score_side/run/score/identityRecorder.jsonl`, `candidate_record.json` | S-CORE host | `B/identity-recorder/` |
| R | `capture_<run>/app_record_warning.jsonl`, event `receipt` | IVI guest; `t_real_ns` (IVI real) | `B/ivi-warning-app/.../MainActivity.java:21,149` |
| C | `ivi_clock_<run>/clock.jsonl` | guest host and IVI | the session's `ivi_clock` step |
| P | the stop record of contract 3: a JSON object with `runTarget` `path_stopped` | S-CORE host; `stopInstantMonoNs` | `score-path/scripts/path_stop.sh` (lane C4) |
| J | `session.json` | lead host | `B/session/da_session.sh` |

### W: world tick (`data` of each `tick` line)

| Field | Read by | Notes |
|---|---|---|
| `frame`, `simTimeS`, `scenarioTimeS` | all | the join key to S is `frame`; sim time is monotonic over the session |
| `ego.speedMps` | 036, 037, 042 (functional part) | |
| `relative.gapM`, `relative.closingMps` | 036, 037, 042 | the primary target (shared contract 1: "`data.relative` stays as it is"). The evaluators recompute the time to collision and the needed deceleration from these two |
| `relative.centerLineOffsetM`, `relative.headingDiffDeg` | 036, 037, 042 (judged run) | |
| `targetContact` | 037 and the functional part | |
| `vehiclesAhead[]` | 040, 041 | **shared contract 1 (lane A6)**: per vehicle up to 300 m ahead in the direction of travel `{actorId, role, gapM, closingMps, ttcS, neededDecelMps2, inLane, overlapRatio}`. The cases read `inLane`, `gapM`, `closingMps`, and recompute the time to collision and the needed deceleration |
| `control` `{throttle, steer, brake, handBrake}` | 038 stop clause | the control the vehicle holds at the tick |
| `worldSideControlCalls` | 038 | 0 on every tick |

W-set: `setting.setting_id` (the run's setting), `kind` (`run`; the stop run may say `stop`), `controlOfTheHero`
(the world's statement that no autopilot and no Traffic Manager controls the hero, `da_world_side.py:725-726`; 038),
`guidance` (014 and 015 only: the guidance speeds and times to collision that VC-040 and VC-041 ask the record to hold,
`M/driver_assistance_verification_evidence.sysml:474-476`, lane A4; the field name is this contract's proposal).

### S: the candidate's boundary (`kind` of each line)

| Kind | Fields read | Read by |
|---|---|---|
| `out.driving_command` | `seq`, `crc` (hex), `issueTime_sim_s`, `frame`, `acceleration`, `mono_ns` | 036, 038, 041, 042, 044 |
| `out.warning_request` | `requested`, `issueTime_sim_s`, `frame`, `bytes` (8 bytes hex: `requested` UINT32, `issue_time_sim_ms` UINT32, big-endian; `B/interfaces/include/de4sdv/driver_assistance/payloads.h:91-94`), `sent` | 040, 042, 043 |
| `drop.camera_image` | `sim_s` (the capture time of the dropped image), `frame` | every case (the dropped-image rule) |
| `in.camera_image` | `sim_s`, `mono_ns` | 043 stop clause (the stop instant in sim time) |
| `in.candidate_record` | `accepted`, `recordSha256`, `upstreamRevision`, `diffBytes`, `mono_ns` | 044 |

### A: the actuation adapter (`event`, `data`)

| Event | Fields read | Read by |
|---|---|---|
| `in.driving_command` | `seq`, `crc_ok`, `checkValue` (uint32 of the S `crc`), `verdict` | 038 |
| `out.ackermann_control` | `seq`, `frame`, `controlSource`, `t_mono_ns` of the line | 038 and its stop clause |

### R and C: the IVI app

`receipt`: `seq`, `requested` (0 or 1), `issue_time_sim_ms`, `t_real_ns`. The file holds the whole session; the
receipts of a run are those whose `issue_time_sim_ms` lies in the run's sim span or whose `t_real_ns` lies in the
run's wall span (from the S `start` line to its last line). C: the line `after_second_set` (else the last line),
`offset_s` and `bound_s` (guest minus host).

### P: the stop record (shared contract 3)

`{"runTarget":"path_stopped","stopInstantRealNs":<int>,"stopInstantMonoNs":<int>,"rc":<int>}`, printed by
`path_stop.sh` on the S-CORE host at go + 12 s. The evaluators take it from `session.json` (any object holding
`runTarget` `path_stopped`) or from a file `path_stop_<run>.*` under the session root (its last JSON line with
`runTarget`). `stopInstantMonoNs` is on the S-CORE host's monotonic clock, the clock of S and A.

### J: session.json

Per run, read where present: `score_runs.<run>.setting` (cross-checked against W-set), and the fields that lane
C5 adds per run, `setting`, `runIdentity` and the scenario digest (`simulatedConfiguration`). The evaluators do not
need `runIdentity` to place a run: the two runs of a setting are taken in the order of their first world tick.

## Terms (`terms.py`)

Every number below is a model number, except those marked EVALUATOR READING.

| Term | Rule | Source |
|---|---|---|
| Setting | the seven settings, their bands and target bands | `M/driver_assistance_needs_requirements.sysml:188-195`; identities `M/driver_assistance_verification_evidence.sysml:95-118` |
| Time to collision | `gapM / closingMps`, no value while `closingMps <= 0` | `:212-215` |
| Needed deceleration | `closingMps^2 / (2 gapM)`, no value while not closing | `:216-220` |
| Imminent | a vehicle ahead in the lane with TTC <= 4.0 s and needed >= 1.0 m/s2 | `:221-225`, `:183` (vehicle ahead: in its lane) |
| Functional part | from the latest tick in the band with TTC >= 4 s, to the end: the first `targetContact`, or the vehicle at the target's speed (stationary target: `closingMps <= 0.05`, `B/world-side/scenarios.py:33-34`; moving target: `closingMps <= 0`, plan A2). EVALUATOR READING: the end search starts at the first tick in the band that closes on the target | `:196-200` |
| Judged run | 2 s before the functional part with `|centerLineOffsetM| <= 0.2` and `|headingDiffDeg| <= 2.0` (BENCH READING, `scenarios.py:29-31`) on every tick | `:201-211` |
| Warning start | an `out.warning_request` with `requested` true whose predecessor is false, or the first one when it is true; at `issueTime_sim_s` | `:232-234` |
| Emergency braking start | an `out.driving_command` (in `seq` order) with `acceleration <= -5.0` whose predecessor is `> -5.0`, or the first one when it is `<= -5.0` | `:235-242` |
| Relative approach speed | `closingMps` at the first imminent tick of the functional part | `:259-260` |
| Relative impact speed | `closingMps` at the last tick before the first `targetContact`; 0 when no contact. EVALUATOR READING: the contact tick's own closing is the rebound (attempt 3 run1: -1.284 m/s at frame 2962397, 5.259 m/s one tick before) | `:261-262` |
| Maximum relative impact speed | approach <= 42 km/h: 0; <= 45: 15; <= 50: 25; <= 55: 30; <= 60: 35 km/h; above 60 km/h no limit (inconclusive) | `:263-267` |
| Instant join | the last driving command at a tick is the newest `out.driving_command` with `issueTime_sim_s <= simTimeS` | plan section 2, 036 |
| Tick of an S record | the W tick of the same `frame`; without `frame`, the last tick with `simTimeS <= issueTime_sim_s` | |

## Judged window and the dropped-image rule

A run is not judged for a criterion when its judged window holds a `drop.camera_image` whose `sim_s` lies in it
(`M/driver_assistance_verification_evidence.sysml:204-207`; `M/driver_assistance_physical_software_realization.sysml:1193-1194`).
The case gives `inconclusiveMissingEvidence` for that run and names the drops.

| Cases | Judged window |
|---|---|
| 036, 037, 042 | EVALUATOR READING: from 2.0 s before the functional part (the straight-before span of the judged run) to its end |
| 038, 040, 041, 043, 044 | the whole run: from the first to the last W tick (`:206-207`: "for a criterion over every run, the judged window is the whole run") |

## Cases

| VC (REQ) | Runs read | Rule | Success clause |
|---|---|---|---|
| 036 | judged runs of 012@20/42/60, 013@30/60 | at each functional-part tick with needed >= 5.0, the last command has `acceleration <= -5.0`; a tick with no command before it is a miss | `M/driver_assistance_needs_requirements.sysml:278` |
| 037 | as 036 | impact (km/h) <= the limit at the approach speed; never imminent and no contact is met | `:288` |
| 038 | the 14 runs, and the stop run's stop clause | every A `out.ackermann_control` has an A `in.driving_command` of its `seq` with `crc_ok` and an S `out.driving_command` of that `seq` whose `crc` equals `checkValue`; `controlSource` is `actuationAdapter`; `worldSideControlCalls` 0 on every tick; W-set `controlOfTheHero` present. Stop clause: no `out.ackermann_control` with `t_mono_ns` after `stopInstantMonoNs`, and W `control` constant from the frame after the last control applied before the stop | `:298` |
| 040 | the 14 runs | every warning start falls on a tick with an imminent vehicle ahead in the lane (`vehiclesAhead`); 014/015 runs hold `guidance` | `:318` |
| 041 | the 14 runs | as 040, for every emergency braking start | `:328` |
| 042 | as 036 | a judged run with an imminent tick in its functional part has a warning start at or before the functional part's end; when the run has an emergency braking start, a warning start at least 1.0 s of sim time before it | `:338` |
| 043 | the 10 runs of 012/013, and the stop run's stop clause | every R receipt of the run equals an S `out.warning_request` with `sent` true, byte for byte (`requested`, `issue_time_sim_ms` encoded as S `bytes`). Stop clause: no receipt whose `issue_time_sim_ms` is after the newest image the candidate took before the stop, and none whose IVI `t_real_ns`, less the clock offset, is later than `stopInstantRealNs` by more than the clock bound | `:348` |
| 044 | the 14 runs | the S `in.candidate_record` with `accepted` comes (S-CORE mono) before the first `out.driving_command`; its `diffBytes` > 0 (a build with changes upstream has not merged records a non-empty difference). The reproduction by another engineer is a desk step (plan lane F2): without a desk record `reproduction_044.json` the case gives inconclusive | `:358` |

## Missing-evidence texts

Each `missing` entry names the file, the field and its producer, for example: `world_run1/simulator/world.jsonl
tick data.vehiclesAhead (shared contract 1, lane A6)`, `score_run1 score_interface.jsonl drop.camera_image at sim
601.161 s inside the judged window 601.111-634.511 s (MAP-DRIVING-DA-CAMERA-IMAGE)`, `setting SC-DRIVING-012@42:
no run`. B7 reads every such text of attempt 3 (lane README).
