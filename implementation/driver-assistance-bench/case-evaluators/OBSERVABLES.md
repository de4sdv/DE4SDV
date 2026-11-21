# Observables of the S1 verification cases (INC-DRIVING-002)

The evaluators of VC-DRIVING-036 to -038 and -040 to -044 read the records of one S1 session. This file is the
contract between the evaluators and the producers. It names every record, field and clock that a case reads, the
terms that the cases compute from them, and the text that a case writes when a field is missing. VC-DRIVING-039 is an
analysis of the realization and reads no run (`driver_assistance_verification_evidence.sysml:434-465`); it has no
evaluator here.

Paths: `M/` = `textual-notation-of-model/packages/features/driving/`, `B/` =
`implementation/driver-assistance-bench/`. The model files are read-only for the bench.

The names below are the producers' own where the lead's merge contracts of 2026-11-20 pin them (decisions file of
the increment, entry of 2026-11-20 about 16:40 CET), read at the named commits:

| Contract | Producer, commit | What the readers take |
|---|---|---|
| 1. guidance | `B/world-side/sites.py` `SiteSpec.as_record()` (:625-630), `GUIDANCE_014` and `GUIDANCE_015` (:39-48), lane/da-s1-sites b9938fe9 | `setting_record.json` `site.guidance` |
| 2. stop run | `B/world-side/scenarios.py` `STOP_RUN = "stop"` (:45, :122), lane/da-s1-world db6bf573; `B/session/da_session.sh` run list (:1269-1290), lane/da-s1-session a0bd4bd7 | run id `stop`, setting `stop`; its setting record says kind `run` (`da_world_side.py` `cmd_run`) |
| 3. stop instant | `B/score-path/scripts/path_stop.sh` (its one JSON line), lane/da-s1-score a9384a0c; `B/session/da_session.sh` `path_stop` (:1658-1685) and the s1 block of session.json (:1105-1121), a0bd4bd7 | session.json `s1.stop_instant`, else the line in `s1.path_stop.line` |
| 4. rehearsal | the session (lane I-S adds it) | session.json `rehearsal` |
| 5. Ackermann gains | lanes I-S and I-W; names not fixed yet | any key naming Ackermann gains, at any depth (below) |

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
is not judged. A setting that is not judged never gives pass (VC-DRIVING-036 doc `:333-335`).

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
| P | the stop instant of contract 3: session.json `s1.stop_instant` | S-CORE host; `stopInstantMonoNs` | `score-path/scripts/path_stop.sh` through `session/da_session.sh` |
| D | `score_<run>/candidate_rrd.json`, `score_<run>/staging.json`, `rec_<run>/chase_view.mp4` | S-CORE host; simulator host | the S-CORE stop and start (`B/score-path/`), the chase recorder |
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
| `control` `{throttle, steer, brake, handBrake}` | 038 stop clause, a note only | `hero.get_control()`: the output of the simulator's Ackermann controller at the tick, which changes under a held target with no command; never the criterion |
| `worldSideControlCalls` | 038 and its stop clause | the world side's control calls on the vehicle since the run began: 0 on every tick of the 14 runs; no rise after the stop in the stop run |

W-set: `setting.setting_id` (the run's setting; `stop` for the stop run), `setting.scenario`, `kind` (`run` for
every run of `run_scenario.sh`, the stop run included), `controlOfTheHero` (the world's statement that no autopilot
and no Traffic Manager controls the hero; 038), `simulator.versions.server` (lane D), and `site` (014 and 015 only:
`SiteSpec.as_record()`, contract 1). 040 and 041 read `site.guidance`, the speeds and times to collision that the
record must hold for 014 and 015 (`M/driver_assistance_verification_evidence.sysml:474-476`), by the keys of
`sites.py`:

| Scenario | Keys of `site.guidance` that must hold a value |
|---|---|
| SC-DRIVING-014 | `approachKmh`, `atCurveEntryMinKmh`, `ttcAtTurnInMaxS`, `inCurveMinKmh`, `ttcAtOverlapZeroMaxS` |
| SC-DRIVING-015 | `bothKmh`, `targetTurnKmh`, `egoAtTurnBeginMinKmh`, `ttcAtTurnBeginMaxS`, `egoAfterMinKmh`, `ttcAtOverlapZeroMaxS` |

A key without a value gives inconclusive and the text names it. The guidance is recorded, not judged
(`sites.py:18`).

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

`receipt`: `seq`, `requested` (0 or 1), `issue_time_sim_ms`, `t_real_ns`. `lifecycle`: `message` (the message type
of the warning request on the guests, `de4sdv.driving.v1.CollisionWarningRequest` in attempt 3), `unit`,
`translation` (lane D, contractIdentity). The file holds the whole session; the
receipts of a run are those whose `issue_time_sim_ms` lies in the run's sim span or whose `t_real_ns` lies in the
run's wall span (from the S `start` line to its last line). C: the line `after_second_set` (else the last line),
`offset_s` and `bound_s` (guest minus host).

### P: the stop instant (lead contract 3)

`path_stop.sh` prints one line on the S-CORE host at go + 12 s:
`{"runTarget":"path_stopped","stopInstantRealNs":<int>,"stopInstantMonoNs":<int>,"rc":<int>}`. `da_session.sh`
keeps it in session.json `s1`:

- `s1.stop_instant`: the parsed line when it was good (runTarget `path_stopped`, both instants integers, rc 0);
  otherwise `null`, and the session ends (exit 5);
- `s1.path_stop`: `{label, go_unix_s, call_unix_s, after_go_s, line, stop_instant}`, with the raw `line`.

The evaluators read `s1.stop_instant`; when it is `null` they read the line in `s1.path_stop.line` (its `label` the
stop run's), whose rc not 0 gives `blockedTargetRuntime`. No other object in session.json and no other file is read
as the stop instant. `stopInstantMonoNs` is on the S-CORE host's monotonic clock, the clock of S and A.

### J: session.json

Per run, as `da_session.sh` (a0bd4bd7) writes `score_runs.<run>` for kind s1: `setting` (cross-checked against
W-set), `run_id`, `runIdentity` (`SC-DRIVING-012@20/r1`, the stop run `stop/further`), `scenario`,
`simulatedConfiguration` `{sha256, files, rule}`. The run labels are the run list's (`012_20_r1`, `stop`). The
evaluators do not need `runIdentity` to place a run: the two runs of a setting are taken in the order of their first
world tick.

Session level: `rehearsal` (contract 4): any value other than absent, `null` or `false` makes the campaign refuse the
session; the output names the reason, holds no case, and the command exits 3. `bench_commit`, `candidate`
`{name, bundle}`, `internal_ips_from_gcloud` `{sim, score, guest}` (lane D).

### The Ackermann gains (contract 5)

The field names are not fixed. The campaign reports, in the measured values of VC-DRIVING-036 and -037 beside the
calib-decel summary (`calibrationDecel`), `ackermannGains`: `requested`, every key of session.json whose name holds
"ackermann" and "gain" (any case, any depth, `DA_ACKERMANN_GAINS` included), and `readBack`, every such key of each
`setting_record.json` and each `calibration_*.json` of the session, each as `{file, key, value}`. Either is
`"unrecorded"` when no such key exists. The gains are reported, not judged.

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
(`M/driver_assistance_verification_evidence.sysml:23-27` and `:203-207`;
`M/driver_assistance_physical_software_realization.sysml:1193-1194`). The case gives `inconclusiveMissingEvidence`
for that run and names the drops. The model fixes the window as the whole run only for a criterion over every run
(`:23-27`, `:206-207`); for 036, 037 and 042 the window is the case's own, by the lead decision of 2026-11-20.

| Cases | Judged window |
|---|---|
| 036, 037, 042 | lead decision of 2026-11-20 (lane B's reading): from 2.0 s before the functional part (the straight-before span of the judged run) to its end |
| 038, 040, 041, 043, 044 | the whole run: from the first to the last W tick (`:206-207`: "for a criterion over every run, the judged window is the whole run") |

## Cases

| VC (REQ) | Runs read | Rule | Success clause |
|---|---|---|---|
| 036 | judged runs of 012@20/42/60, 013@30/60 | at each functional-part tick with needed >= 5.0, the last command has `acceleration <= -5.0`; a tick with no command before it is a miss | `M/driver_assistance_needs_requirements.sysml:278` |
| 037 | as 036 | impact (km/h) <= the limit at the approach speed; never imminent and no contact is met | `:288` |
| 038 | the 14 runs, and the stop run's stop clause | every A `out.ackermann_control` has an A `in.driving_command` of its `seq` with `crc_ok` and an S `out.driving_command` of that `seq` whose `crc` equals `checkValue`; `controlSource` is `actuationAdapter`; `worldSideControlCalls` 0 on every tick; W-set `controlOfTheHero` present. Stop clause (no driving command reaches the actuation after the stop): no `out.ackermann_control` with `t_mono_ns` after `stopInstantMonoNs`, and no rise of `worldSideControlCalls` on the ticks from the frame after the last control applied before the stop; the changes of W `control` on those ticks are reported as `controlChangesAfterStop`, a note | `:298` |
| 040 | the 14 runs | every warning start falls on a tick with an imminent vehicle ahead in the lane (`vehiclesAhead`); 014/015 runs hold `guidance` | `:318` |
| 041 | the 14 runs | as 040, for every emergency braking start | `:328` |
| 042 | as 036 | a judged run with an imminent tick in its functional part has a warning start at or before the functional part's end; when the run has an emergency braking start, a warning start at least 1.0 s of sim time before the first one (a lead of 0.99 s fails, 1.0 s passes); a run with no emergency braking needs the warning start only. A warning still on at the braking is not asked | `:338` |
| 043 | the 10 runs of 012/013, and the stop run's stop clause | every R receipt of the run equals an S `out.warning_request` with `sent` true, byte for byte (`requested`, `issue_time_sim_ms` encoded as S `bytes`). Stop clause: no receipt whose `issue_time_sim_ms` is after the newest image the candidate took before the stop, and none whose IVI `t_real_ns`, less the clock offset, is later than `stopInstantRealNs` by more than the clock bound | `:348` |
| 044 | the 14 runs | the S `in.candidate_record` with `accepted` comes (S-CORE mono) before the first `out.driving_command`; its `diffBytes` > 0 (a build with changes upstream has not merged records a non-empty difference). The reproduction by another engineer is a desk step (plan lane F2): without a desk record `reproduction_044.json` the case gives inconclusive | `:358` |

## Lane D: the evidence record (RetainedAssistanceRunEvidence)

`evidence_record.py` fills each attribute of `RetainedAssistanceRunEvidence`
(`M/driver_assistance_verification_evidence.sysml:150-243`) for every run, the stop run included, from one record.
An attribute that its record does not fill stays empty, and the record names it with the file and the field
(`<attribute>: <text>`); the record's outcome is then `inconclusiveMissingEvidence`, otherwise `complete`. The
campaign puts each run's record into its output (`evidenceRecords`). A run whose record is partial gives
`inconclusiveMissingEvidence` for that run, never pass and never fail ("A missing or partial record gives
inconclusive, never pass", `:211-212`; "missing or partial evidence gives inconclusiveMissingEvidence", `:126-127`;
the lead's reading of 2026-11-21). The case is combined again from the runs' outcomes so read: a fail stands only
when a run that shows it has a complete record, and a pass with any partial record read becomes inconclusive. The
outcomes of the clauses that no run shows (044's desk reproduction, `measured.outcomesWithoutRun`) are kept. A note
names the outcome observed before the rule. `setting` is left empty for the stop run (`:182-183`).

PROPOSAL marks a field that no producer writes yet: its name is this contract's proposal to lanes I-S and I-W.

| Attribute | Record and field |
|---|---|
| `configurationIdentity` | session.json `configuration_identity` (PROPOSAL) |
| `receiptSha256` | session.json `configuration_receipt_sha256` (PROPOSAL) |
| `modelRevision` | session.json `bench_commit` (the commit the kit came from; EVALUATOR READING: it holds the model) |
| `candidateRecordIdentity` | I `identityRecorder.jsonl` event `record` `data.sha256`, `data.path` |
| `upstreamRevision` | I `candidate_record.json` `upstream_revision` |
| `sourceDifference` | I `candidate_record.json` `source_difference.sha256`, `.bytes`, `.files[].name` |
| `networkFileSha256`, `configurationFileSha256` | I `candidate_record.json` `network_files[]`, `configuration_files[]` (`role`, `path`, `sha256`) |
| `launchSettings` | I `candidate_record.json` `launch_settings`: its SHA-256 as canonical JSON (verbatim in that record) |
| `candidateBuild` | session.json `candidate.bundle` (else `score_<run>/staging.json` `bundle`), with the upstream revision and the patch names |
| `visualizationRecorderDelay` | the run's own: session.json `score_runs.<run>.visualization_recorder_delay` when a run states it; else the model's sentence (`evidence_config.json` `model_delay`) when every GPU in `score_runs.<run>.score_gpu` is the model's; else, the run's GPU unread, session.json `visualization_recorder_delay` (`session/evidence_fields.py`) |
| `scoreLifecycleVersion`, `scoreCommunicationVersion`, `scoreSOMEIPGatewayCommit` | session.json `score_runs.<run>.score_platform.lifecycle_version`, `.communication_version`, `.someip_gateway_commit` (the run's own start), else the session's `score_platform.*` (`session/evidence_fields.py`, absent when any started run lacks its line) |
| `simulatorBuild` | W-set `simulator.versions.server` |
| `scenario` | W-set `setting.scenario`, else session.json `score_runs.<run>.scenario` |
| `setting` | the run's setting; empty for the stop run |
| `runIdentity`, `simulatedConfiguration` | session.json `score_runs.<run>.runIdentity`, `.simulatedConfiguration.sha256` (s1) |
| `simulationClockSpan` | W `data.simTimeS` of the first and the last tick |
| `wallClockSpan` | W `t_real_ns` of the first and the last tick line (the simulator host's real clock) |
| `executionEnvironmentIdentity` | session.json `internal_ips_from_gcloud.sim`, `.score`, `.guest`, the run's own `score_runs.<run>.score_gpu` (else `execution_environment.score_gpu`), and `execution_environment.sdv_core_image`, `.ivi_image` (`session/evidence_fields.py`) |
| `contractIdentity` | R `lifecycle` `message`, `unit`, `translation` |
| `criteriaRecordIdentity`, `evaluatorRevision` | the campaign's own (`evaluate_da_campaign.py`) |
| `rawObservationArtifact` | the SHA-256 of `candidate_record.json`, `identityRecorder.jsonl`, `score_interface.jsonl`, `actuationAdapter.jsonl` (with S: the communication records of the S-CORE path, EVALUATOR READING), `world.jsonl`, `app_record_warning.jsonl`, and the `.rrd` named in `score_<run>/candidate_rrd.json` |
| `benchRecordingArtifact` | `rec_<run>/chase_view.mp4` (its SHA-256) and the candidate's visualization recording, session.json `score_runs.<run>.visualization_recording.sha256` (`da_session.sh` write_record, from the S-CORE stop's `visualization_recording.json`); without a sha256 the record quotes the entry's own `reason` |
| `independentEngineerIdentity` | `reproduction_044.json` `engineer` (plan lane F2) |
| `claimBoundary` | written by the record: the run's case outcomes, and what the record does not prove |

## Missing-evidence texts

Each `missing` entry names the file, the field and its producer, for example: `world_run1/simulator/world.jsonl
tick data.vehiclesAhead (shared contract 1, lane A6)`, `score_run1 score_interface.jsonl drop.camera_image at sim
601.161 s inside the judged window 601.111-634.511 s (MAP-DRIVING-DA-CAMERA-IMAGE)`, `setting SC-DRIVING-012@42:
no run`. B7 reads every such text of attempt 3 (lane README).
