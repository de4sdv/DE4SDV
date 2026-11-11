# DE4SDV closed-loop driving bench (INC-DRIVING-001 slice 10b)

This bench drives a vehicle in CARLA in a closed loop:

- CARLA renders six cameras.
- drivingAgent, an Eclipse S-CORE FEO application, conditions the inputs and
  runs the pinned AutoE2E checkpoint in its own process.
- Its plans become vehicle commands, which the actuation adapter applies to
  the CARLA vehicle.
- The operational state travels over SOME/IP to an observer on the AAOS IVI.
- Every component writes the run records the 35 verification cases of
  INC-DRIVING-001 read. The evaluators in `case-evaluators/` turn those
  records into verdicts.

## Claim boundary

This directory is bench tooling, test stand-ins and evaluators.

- It is **not** evidence of record and verifies no requirement by itself. Every
  verdict stays draft until independent review.
- No safety, cybersecurity, compliance or homologation statement is made.
- The stub engine is a stand-in planner for integration runs. Its plans,
  including its route-following mode, are never model results; records name it
  `stub` / `stub-pure-pursuit`.
- The pinned checkpoint does not follow the route through junctions, and it
  does not keep the vehicle in its lane. On a straight road, in two of three
  runs the vehicle crossed the marking on its right 31.5 s and 35.1 s after
  the first plan. In the third it was 1.0 m left of the route after 20 s and
  1.4 m after 30 s, following a turn of 1.6 degrees that no command asked for;
  the cause of that turn is not determined. The plans did not steer back: of
  the 269 plans reaching 10 m ahead that were made with the vehicle more than
  0.3 m right of the route, none pointed back toward it. The runs verify the
  bench and the agent against their requirements; they do not validate
  driving quality.

## Path

```text
CARLA 0.9.16 (simulator host) -- six camera images, world ticks -->
  drivingAgent (S-CORE host): conditionInputs -> inferPlan (pinned checkpoint, in process)
                              -> superviseLoop -> commandVehicle
  -- vehicle command (mw::com) --> actuation adapter -- control --> CARLA vehicle
drivingAgent -- operational state (SOME/IP) --> SDV Core broker --> IVI observer
world side (CARLA pacer) --> C1 world record      route provider -- UDP route --> drivingAgent
```

The interface contract is `interfaces/ICD.md` (v2 with amendments 1 and 2, rulings A1 to A34).

## Layout

| Directory | Component | State |
|---|---|---|
| `interfaces/` | ICD, payload headers, run-log helper | compiled into every C++ component |
| `agent/` | drivingAgent: FEO Rust shells, a C ABI, embedded CPython planner (stub and checkpoint engines), CARLA and fake frame sources, frame store, navigation input, supervision and commander | runs with the fake world and the real route provider on a CPU host; the checkpoint engine builds and passes its parity check inside the binary on the GPU host; build steps in `agent/workspace/README.md` |
| `world-side/` | CARLA synchronous pacer: hero and six-camera rig, handover, world faults, C1 record | tested against a fake `carla` module that models the 0.9.16 behaviour the code relies on |
| `actuation-adapter/` | vehicle commands to CARLA control, command watchdog | unit tests; builds with the S-CORE toolchain |
| `state-publisher/` | operational state to the SOME/IP struct | unit tests and golden byte vectors |
| `navigation/` | CARLA map and route export, a rasterizer at parity with upstream AutoE2E, route provider | parity tests on synthetic and real Town10HD_Opt data |
| `ivi-observer/` | typed observation path on the IVI | local checks; ran end to end across three hosts with SELinux permissive on the IVI VM, not under enforcing (`ivi-observer/sepolicy/README.md`) |
| `case-evaluators/` | the verification-case evaluators | tested on synthetic runs; run on real agent runs |

## Tests

| Component | Command (from this directory) |
|---|---|
| agent, C++ | `cd agent/cc && bash tests/run_tests.sh` (add `--mutations` for the mutation probes; the navigation test reads `NAV_MAP` and `NAV_ROUTE`) |
| agent, Python | `python -m pytest agent/python/tests` (numpy) |
| world side | `python -m pytest world-side/tests` (numpy; Python 3.10 or later) |
| navigation | `cd navigation && python -m pytest tests` |
| case evaluators | `cd case-evaluators && python -m pytest tests` |
| adapter, publisher | see their READMEs |

## Known limits

- **C2 bundles and C11 reference inference are not built.**
  - C2 bundles are the input tensors of sampled steps; C11 re-runs the checkpoint on them offline.
  - Until both exist, VC-DRIVING-002 stays undecided.
- **The FEO workspace patch is local.** It covers the event trigger and the module set (`agent/workspace/`). Issue 124 of `eclipse-score/feo` describes the event trigger upstream; the patch has not been proposed there as a change. Its build turns the strict clippy aspect off.
- **The LibCarla 0.9.16 client build recipe** is not in the repository yet.
- **No warm-up.** The world side starts the hero at rest with no autopilot warm-up; see `world-side/README.md` for why.
- **SELinux on the IVI VM.** Every recorded run of the observation path was made with the guest permissive. Whether the observer app reaches the gateway under enforcing is not known; see `ivi-observer/sepolicy/README.md`.
- **A stalling camera stream.** Both closed-loop runs recorded with the observation path ended in a stop response for a stale camera: one camera stream between the simulator host and the planner host stalled. The cause is open.
- **The evaluators read the observation records, and one case stays blind without a producer change.** The observer app and statePublisher write `in.operational_state` and `out.operational_state` with a kind; the evaluators now read them as `interfaces/ICD.md`'s amendment A34 defines them, with the publisher's record of a message as its publication time. On the two closed-loop runs recorded with the observation path, VC-DRIVING-015, -017 and -029 pass. VC-DRIVING-016 stays inconclusive: no record holds when a motion sample reached the driving system, the time REQ-DRIVING-016 counts from, and the case names the missing field.
- **The observer's stale rule has run in unit tests only.** The IVI app marks its screen stale when it has no health newer than 500 ms, the receiver rule in the rationale of REQ-DRIVING-017, and marks a plan or a vehicle state that stopped arriving. Its tests show that on a plain JDK. The change has not been built for Android or run on the IVI, and a health stream that stops alone cannot be produced on the real path: statePublisher has no switch that stops one event.
- **No run on this tree.** The recorded runs were made on integrations of the changes that existed at the time. None of them carried the adapter's stop fix or the world side's camera-alive fix, so those two have run in their tests only, not against CARLA.
