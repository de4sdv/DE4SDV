# agent_logic: the pure decision logic of the DE4SDV driving agent (slice 10b, WP2)

The FEO agent of phase 8 has four activities in one chain per 100 ms step. The
orchestrator writes the Rust shells; this library is the decision logic they
call, with no S-CORE, CARLA, Python or wall clock inside:

| activity | entry point | requirements |
|---|---|---|
| `conditionInputs` | `JudgeConditions` | REQ-DRIVING-023, -024, -025 |
| `superviseLoop` | `Supervisor::Step` / `Latch` / `EndRun` | REQ-DRIVING-020..-022, -026, -027, -035 |
| `commandVehicle` | `Commander::Step` | REQ-DRIVING-011, -012, -020..-022, -026 |
| log records | `namespace record` | ICD v2 §6, §10 C3/C6, Amendment 1 A5/A7 |

Every age is computed from frame indices (`AgeMs`), never from a float stamp, so
the same inputs give the same outputs in a test, on the bench and after review.
The caller passes the monotonic time in; the library never reads a clock.

## Files

| file | lines | content |
|---|---|---|
| `agent_logic.h` | 321 | the contract: conditions, supervisor, commander, config, records |
| `agent_logic.cpp` | 698 | the rules and the record builders |
| `json_lite.h` / `json_lite.cpp` | 68 / 354 | copied from `actuation-adapter/` with a one-line provenance block; `diff` against the source differs only in that block |
| `tests/agent_logic_test.cpp` | 1432 | unit tests, boundaries, the scripted run, the JSONL emitter |
| `tests/test_records_against_evaluators.py` | 438 | the records parsed by the evaluators' own `runio.py`, VC-DRIVING-026 and VC-DRIVING-027 decided |
| `mutations.py` | 279 | 22 single-point mutation probes |

Payloads come from the bench (`-I <bench>/interfaces/include`); `payloads.h` is
not copied.

## Build and test

```bash
B="$(git rev-parse --show-toplevel)/implementation/closed-loop-driving-bench"
g++ -std=c++17 -O2 -Wall -Wextra -Werror -I. -I$B/interfaces/include \
    tests/agent_logic_test.cpp agent_logic.cpp json_lite.cpp -o .build/agent_logic_test
./.build/agent_logic_test                      # 640 checks, 0 failures

g++ -std=c++17 -O1 -g -Wall -Wextra -Werror -fsanitize=address,undefined \
    -fno-omit-frame-pointer -I. -I$B/interfaces/include \
    tests/agent_logic_test.cpp agent_logic.cpp json_lite.cpp -o .build/agent_logic_test_san
./.build/agent_logic_test_san                  # 640 checks, 0 failures, no sanitizer report

python3 tests/test_records_against_evaluators.py   # 116 checks, 0 failures
python3 mutations.py                               # 22 mutations, 22 killed
```

`tests/test_records_against_evaluators.py` writes three run directories under
`.build/runs/` (`plan_stale`, `plan_invalid`, `camera_missing`), runs the C++
emitter, and reads the resulting `score/drivingAgent.jsonl` with
`case-evaluators/runio.py` imported from the bench (read-only). It then calls
`cases.vc026` and `cases.vc027` and requires `passBoundedVerification` from both,
and requires VC-DRIVING-020..023/032 to stay inconclusive where their evidence comes from
another component.

The C++ scenario test drives Supervisor+Commander for 100 steps three times:
priming (0..19) → driving (20..) → a fault at 60 → stop → standstill.
* plan stall: the newest plan is frame 59, so the stop begins at frame 63
  (age 400 ms), and frames 63..99 command −4 m/s²;
* camera missing: the stop begins at the fault step 60 with kCameraMissing, and
  frames 60..99 command −4 m/s² with the steering held;
* invalid plan: the stop begins at frame 60 with kPlanInvalid, and no command
  names the invalid plan (asserted through `cases.vc027` in the Python test and
  in `TestSupervisorStopLatching`).

## Rule to code

| rule | where |
|---|---|
| one frame = 100 ms; `age_ms = (step − other) × 100` | `AgeMs`, `FrameMs`, `FrameSeconds` |
| route issue time compared in integer ms | `IssueTimeMs` (rounds once) |
| camera missing / invalid / stale (>200 ms) | `JudgeConditions`, camera loop |
| motion invalid (no sample or non-finite) / stale (>200 ms) | `JudgeConditions`, motion block |
| route stale (none or >1 s) / empty (0 points or 0 raster cells) | `JudgeConditions`, route block |
| one bit per cause, ascending cause list | `CauseBit`, `ConditionResult::Lowest`, sort at the end |
| plan validity: 64 pairs, all acceleration and curvature finite | `IsPlanValid` |
| latching mode machine, kRefused permanent | `Supervisor::Step` |
| lowest cause of the step wins, latched | `Step` (kDriving branch), `EnterStop` |
| kStarting faults logged, never stop | `Step` (kStarting branch) |
| stop → standstill below 0.1 km/h | `Step` (kStopResponse branch) |
| external latch, first cause wins, `EndRun` = kRunEnd | `Latch`, `EndRun` |
| mode payload, refusal fields only for kRefused | `FillModePayload` |
| -min(4, max_deceleration), steering held, reference named | `EmitStopCommand` |
| k = step − plan frame, clamped 0..63 | `PlanSampleIndex` |
| REQ-DRIVING-026 re-check at the command | `Step` (kDriving, before the sample) |
| acceleration clamp for both laws | `Step` |
| `first_control`: deg(atan(wheelbase·κ)) | `FirstControlSteeringDeg` |
| `pure_pursuit`: the plan's path from its origin (A31), Ld, 2y/d² | `PurePursuitSteeringDeg`, `PurePursuitLookaheadM` |
| angle clamp, then per-step rate limit | `Commander::LimitSteering` |
| ICD §5 configuration, rejecting bad values and laws | `ParseVehicleConfig`, `LoadVehicleConfigFile` |
| record builders | `namespace record` |

## Records and who reads them

`out.condition` is the input-condition word (`bits`, `causes`, and the
`input_conditions` object the C2 record embeds). `out.plan` is inferPlan's view,
`in.plan` the commander's view (the newest valid plan, one per step). Every time
field carries a clock suffix or sits in a sibling `clocks` map; payload time
fields are seconds.

The Python test re-derives this table mechanically: every key marked *read* must
appear in `runio.py`/`cases.py`, every key marked *component* or *human* must
not, so a rename on either side fails the test.

| field | who reads it | matches |
|---|---|---|
| `frameIndex`, `sampleCount`, `samples[].acceleration/.curvature` | `runio._plan_payload`, `cases.vc026`/`vc027` valid filter | yes |
| `samples[].x/.y/.heading` | `runio._plan_payload` (pure pursuit path) | yes |
| `captureTime` + `clocks.captureTime = simulation` | `runio._sim_stamp`, VC-DRIVING-026 age, VC-DRIVING-031 | yes |
| `productionTime` + `clocks.productionTime = monotonic` | `runio._plan_payload`, VC-DRIVING-032 | yes |
| `horizon` | `runio._plan_payload` | yes |
| `producer`, `runRecord`, `planReference` | VC-DRIVING-011 chain, VC-DRIVING-034 | yes |
| `mode` (int), `cause` (int) | `runio.modes`, `cases.enum_name` | yes |
| `decisionTime` + `clocks.decisionTime = monotonic` | `runio.modes` | yes |
| `capture_sim_ms`, `frame`, `cause` (name), `source` | `runio.stops`, `cases.stop_timing` (VC-DRIVING-020..027) | yes |
| `step_capture_sim_ms`, `plan_capture_sim_ms` | `runio._command`, VC-DRIVING-026 | yes |
| `acceleration`, `steeringAngle`, `productionTime`, `planReference` | `runio._command`, VC-DRIVING-020/-021/-022 | yes |
| `bits`, `causes`, `input_conditions`, `sim_ms` | `runio.input_steps` (C2 embedding) | yes |
| `reason` | `cases.vc011`/`vc012` injection detail (same spelling) | yes |
| `checkpointExpectedSha256`, `checkpointActualSha256`, `refusalReason` | **not read by the evaluators**: statePublisher maps them to HEALTH 41-43 (`checkpoint_expected_sha256`, …), and VC-DRIVING-035 reads the observer | component |
| `modeName`, `causeName`, `causeValue`, `speedKmh`, `speedMps`, `commandLaw`, `sampleIndex`, `decision_mono_s`, `bits`/`causes` duplicates in the condition record, `code`, `expectedSha256`, `actualSha256` | humans, log inspection, `strip.py` | human |

`code`/`expectedSha256`/`actualSha256` are ICD v2 §10 C6's `error` record: no
evaluator reads them today (VC-DRIVING-035 decides from the observer's health), so the
record is written for the run's evidence, not for a verdict.

## Contradictions found (listed, not silently chosen; C2 and C3 resolved in review)

**C1 — the sample index: integer frames vs DESIGN's rounding formula.**
`agent/DESIGN.md:84` says `k = round((step capture time − plan capture time) / 0.1 s)`,
a float division and rounding. `interfaces/ICD.md:28-31` (section 1) and the brief
require frame arithmetic. The two agree whenever `captureTime == frame × 0.1`, which
`interfaces/ICD.md:75` fixes (`plan_capture_ms = frame × 100`) and
`payloads.h:77` repeats. Implemented: `PlanSampleIndex(step_frame, plan_frame)`,
integer subtraction, clamped 0..63. Note the clamp is defensive: because
REQ-DRIVING-026 stops at age > 300 ms, k in kDriving is 0..3, so 63 is unreachable
through `Commander::Step`; `PlanSampleIndex` is public so the clamp is still
tested (and mutated).

**C2 — the stop command's `planReference`: newest plan vs VC-DRIVING-022. Resolved in review.**
The brief said a stop command names the *newest valid plan*. REQ-DRIVING-011 says a
command names the plan it was computed from, REQ-DRIVING-021 holds the steering at the
last value computed from a valid plan, and VC-DRIVING-022 (`cases.vc022`) fails any
command after T0 that names a plan captured after T0. The brief was wrong; the model
decides. Implemented: the commander keeps the reference and frame of the plan its held
steering came from (`held_plan_reference_`, `held_plan_frame_`), and every stop
command names that plan, frozen at the stop; `"none"` when no driving command was ever
computed. Pinned by `TestCommanderStopModes`, `TestCommanderPlanStale`,
`TestStopReferenceFrozenInScenario`, by VC-DRIVING-022's predicate over `runio` in
`test_records_against_evaluators.py` (the run keeps planning after T0, so the check is
not vacuous; it fails on the old naming), and by a mutation.

**C3 — cause priority when a plan is both stale and invalid. Resolved in review.**
The brief's rule "lowest `Cause` value wins" made `kPlanStale` (8) outrank
`kPlanInvalid` (9) at a step where the newest valid plan turns stale as an invalid plan
arrives, while VC-DRIVING-027 (`cases.vc027`) expects `kPlanInvalid` from the arrival
step. The model fixes no precedence (REQ-DRIVING-026 and REQ-DRIVING-027 each require the stop
response). Implemented: one cause per stop in pipeline order (`ICD.md` section 4): the
input conditions first (lowest value among them), then a plan that arrived in this
step and is invalid, then the age of the newest valid plan. Pinned by
`TestPlanInvalidOutranksStaleInOneStep` and two mutations.

**C4 — `in.plan` carries no step frame.**
The commander view is the plan payload (`runio.plans_in`), so its `frameIndex`
is the plan's frame, repeated at every step until a newer plan replaces it. The
evaluator therefore identifies the view by capture time only; nothing in the
record says at which step the commander saw it. Implemented as the payload
dictates (no invented field). VC-DRIVING-011's `modes.get(f)` lookup uses the *command's*
step frame, which is present, so the chain still closes.

## Decisions beyond the brief

1. **`kRefused` does not report `stop_began`.** The refusal is a mode, not a
   stop event; the commander still emits the stop command from the first step.
   VC-DRIVING-035 decides from health and world speed, and `cases.means_stopped` does not
   count `kRefused` as stopped, so publishing a `stop_response.begin` for a
   refusal would move VC-DRIVING-029's evidence without a requirement asking for it.
2. **A present image without a frame index is `kCameraInvalid`.** It cannot be
   dated, and treating "unknown" as fresh would hide a delivery defect. The
   brief lists empty and wrong-size images; this is the third unusable case.
3. **`EgoMotionSamplePayload.captureTime` is not judged for finiteness.** The
   rule judges the four measured signals; the capture time is derived from the
   frame index and never used for an age.
4. **No announcement ⇒ `kRouteStale` only, not `kRouteEmpty`.** "The newest
   announcement's corridor" does not exist before the first announcement; the
   raster's cell count is still judged.
5. **`kStarting` retains valid plans.** A valid plan that arrives while starting
   is kept, so the first clean step drives with it; `has_valid_plan()` is true
   before the mode leaves kStarting.
6. **The rate limiter is bypassed in the stop modes.** The held angle equals the
   last rate-limited value, so reapplying the limiter would be a no-op; skipping
   it makes the "held, not rate-limited" rule explicit and testable.
7. **`EndRun` while stopped changes nothing** (first cause wins); `EndRun` while
   driving latches `kRunEnd` and reports `stop_began` on the next `Step`, or via
   `stop_pending()` if the shell does not step again.
8. **A latch while the vehicle already stands still reports kStandstill in the
   same step**, with `stop_began = true` — the stop began and was complete at
   once. Pinned by a test.
9. **Stop commands carry `plan_capture_sim_ms: null` when no plan ever existed.**
   Honest: there is no plan to name. Such runs are gated out of VC-DRIVING-026
   (`scenarioVariant.fault`), and VC-DRIVING-011 skips commands outside kDriving.
10. **`out.condition` is an extra record** (`bits`, `causes`, `input_conditions`)
    that the shell embeds in C2's `out.checkpoint_inputs`; it is not a
    replacement for that record, which still needs the per-camera metadata
    VC-DRIVING-023 reads (`cases.py:233-257`).

## Open questions

1. (C2, resolved: the reference is frozen at the stop.)
2. (C3, resolved: pipeline order.)
3. The commander's REQ-DRIVING-026 re-check currently *returns* the stop command and
   reports `plan_stale`; the shell latches `kPlanStale` afterwards. If the shell
   skips the latch, the mode stays kDriving while the vehicle brakes — should
   `Commander::Step` also return the cause to latch (a `Cause` field) so the
   shell cannot forget it?
4. `mode_changed` is true on the first `Step` (there is no previous mode). The
   publisher publishes once per step anyway; is the extra "at once" publish at
   start wanted, or should the first step report `mode_changed = false`?
5. `Standstill` also emits `speedKmh` and `speedMps`; the adapter's builder emits
   `speedMps` only. Should the two components share one spelling in
   `stop_response.standstill`? No evaluator reads it today.

## Mutation probes

`mutations.py` applies one textual change at a time to `agent_logic.h`/`.cpp`,
rebuilds with `-Werror`, runs the C++ test, and requires a failure. It records
the line of the changed rule, restores the source in a `finally`, and compares
SHA-256 with the pre-run values (plus an `.orig` recovery file if a run is
killed). Latest run: **22 mutations, 22 killed, sources restored byte-identical**.

| mutation | file:line | rule |
|---|---|---|
| camera stale threshold 200 → 300 ms | agent_logic.h:39 | REQ-DRIVING-023 |
| camera stale `>` → `>=` | agent_logic.cpp:217 | REQ-DRIVING-023 boundary |
| motion stale threshold 200 → 300 ms | agent_logic.h:41 | REQ-DRIVING-024 |
| motion finiteness drops yawRate | agent_logic.cpp:227 | REQ-DRIVING-024 |
| route stale threshold 1000 → 900 ms | agent_logic.h:43 | REQ-DRIVING-025 |
| plan stale threshold 300 → 400 ms | agent_logic.h:45 | REQ-DRIVING-026 |
| plan age `>` → `>=` | agent_logic.cpp:346 | REQ-DRIVING-026 boundary |
| plan validity accepts 63 pairs | agent_logic.cpp:256 | REQ-DRIVING-027 |
| plan validity drops the curvature check | agent_logic.cpp:259 | REQ-DRIVING-027 |
| lowest cause → highest cause | agent_logic.cpp:184 | cause order |
| first cause wins → overwritten | agent_logic.cpp:285 | latching |
| kStarting lets a fault stop | agent_logic.cpp:332 | priming |
| stop deceleration -4 → -5 | agent_logic.h:49 | REQ-DRIVING-020 |
| standstill 0.1 → 0.2 km/h | agent_logic.h:51 | REQ-DRIVING-022 |
| standstill `<` → `>` | agent_logic.cpp:357 | REQ-DRIVING-022 |
| stop command drops the held steering | agent_logic.cpp:509 | REQ-DRIVING-021 |
| sample index floor 0 → 1 | agent_logic.cpp:131 | k clamp |
| sample index ceiling 63 → 62 | agent_logic.cpp:132 | k clamp |
| steering rate limit doubled | agent_logic.cpp:492 | REQ-DRIVING-012 |
| road-wheel angle clamp removed | agent_logic.cpp:491 | REQ-DRIVING-012 |
| unknown command law accepted | agent_logic.cpp:418 | REQ-DRIVING-012 |
| kRefused not permanent | agent_logic.cpp:328 | REQ-DRIVING-035 |

Line numbers are from the run recorded here; `mutations.py` prints them fresh on
every run.
