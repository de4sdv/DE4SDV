# Case evaluators, INC-DRIVING-001 (slice 10b)

Judges the 35 verification cases of the closed-loop driving bench from the
records a run leaves behind, and says which of the observables those cases need
the bench's interface contract does not yet record.

The owner's decision is *run first, evaluate later*: in the next seven days the
bench executes every run the 35 cases need and keeps the raw records, and the
cases are judged offline. A missing observable wastes the run. So the first
deliverable is the gap report, and the second is the evaluator that turns a run
directory into verdicts.

**Start with [`OBSERVABLES.md`](OBSERVABLES.md).** It has one row per case: the
scenario, the requirement, the exact observables (component, log event, field,
clock), the computation, the threshold, and whether ICD v2 records them.
Status: **34 SUPPORTED (with stated caveats), 1 MISSING**, the exact remaining
field + producer for the missing case, and the C2 bundle ledger.

## What is here

| File | What it does |
|---|---|
| `OBSERVABLES.md` | the gap report: 35 cases × observables × status, the world-side records, what the recordings must show, the change list, the cases that logs cannot decide, open questions |
| `runio.py` | reads a run directory per ICD section 6/7 into the views the cases need; a missing record raises `MissingEvidence` (carrying the ICD change), a malformed one raises `RunFormatError` |
| `cases.py` | the 35 evaluators, one per case, each with the thresholds it judges against; `THRESHOLDS` holds every number in one place |
| `evaluate_run.py` | one run directory → `verdicts.json`, selecting the cases of the run's `scenario` |
| `evaluate_campaign.py` | many runs → the cases that need more than one run (VC-DRIVING-018, VC-DRIVING-019, VC-DRIVING-035, and the VC-DRIVING-020/VC-DRIVING-021/VC-DRIVING-022 pair) |
| `make_synthetic_run.py` | writes synthetic run directories: nominal, each SC-DRIVING-003 fault, the AAOS replay campaign, the two checkpoint-refusal starts |
| `gaps.py` | the ICD change list as data (`C1`..`C12`), with the cases each unblocks, and the amendments (`A11`..`A26`) each case relies on, named per case in `verdicts.json` |
| `strip.py` | removes one change's records from a copy of a run — how the tests prove a case that needs a record cannot pass without it |
| `tests/` | 153 tests |

## Use

```bash
uv venv .venv && uv pip install --python .venv/bin/python pytest numpy
.venv/bin/python make_synthetic_run.py --out /tmp/runs --all   # 21 fixture runs
.venv/bin/python evaluate_run.py /tmp/runs/nominal
.venv/bin/python evaluate_campaign.py /tmp/runs
.venv/bin/python -m pytest tests/ -q
```

`evaluate_run.py` writes `verdicts.json` next to the run (or to `--out`) and
prints a line per case. It exits 1 if any case failed or errored, or if the
run's records contradict its scenario label (`label_conflicts`), 0 otherwise.
An inconclusive case is never counted as a pass.

The cases are selected by the run's scenario. A run whose `checkpointCase` is
not `pinned`, or whose agent logged a kRefused mode, is judged as
checkpointRefusal (VC-DRIVING-035) whatever its label says, and the conflict is
reported; `evaluate_campaign.py` reports it too and exits 1.

## The verdict file

```json
{
  "schema": "de4sdv.driving.case-verdicts.v1",
  "run": {"run_record_identity": "…", "scenario": "degradedInputOrPlan",
          "scenario_variant": {"fault": "camera_stale", "entrySpeedMps": 10.0}},
  "cases": {
    "VC-DRIVING-023": {
      "vc": "VC-DRIVING-023",
      "outcome": "passBoundedVerification",       // a DrivingEvidenceOutcome literal
      "verdict": "pass",                          // MapDrivingEvidenceOutcomeToVerdict
      "measured": {"baseline_sim_s": 25.2, "stop_begin_sim_s": 25.2, "delay_s": 0.0,
                   "cause": "kCameraStale"},
      "thresholds": {"stop_begin_latency_s": 0.1, "expected_cause": "kCameraStale"},
      "evidence": [{"file": "score/drivingAgent.jsonl", "seq": 1502}],
      "missing": [], "notes": [], "icd_changes": [], "amendments": ["A23", "A26"]
    }
  },
  "skipped": {"VC-DRIVING-024": "this run's fault is 'camera_stale'; …"},
  "label_conflicts": [],
  "summary": {"pass": 5, "fail": 0, "inconclusive": 0, "error": 0}
}
```

Rules the evaluators enforce, because a wasted run is the failure mode this
slice exists to prevent:

* a record that is absent → `inconclusiveMissingEvidence`, **never** a pass;
  `missing` names the field and `icd_changes` the change that would supply it;
* a record that cannot be read (bad JSON, broken envelope) → `errorEvidence`;
* a case whose fault this run does not carry → not in `cases`; `skipped` says
  why, and never silently drops it;
* `notApplicable` (e.g. REQ-DRIVING-029 on a run with no stop) is never counted as a
  pass.

## What the tests establish

153 tests, all passing. `tests/test_review_findings.py` holds one group of
tests per finding of the independent review (R1 to R16), each written to fail
on the code before its fix:

* **every SUPPORTED case passes on the synthetic run of its own bench**, and
  **every MISSING case is inconclusiveMissingEvidence** naming its gap;
* **a case that needs a record turns `inconclusiveMissingEvidence` when that
  record is stripped**, one strip per case, and the missing list names the
  change; a case with no `needs` still passes with every change stripped;
* **a sampled plan step without its bundle makes VC-DRIVING-002 inconclusive and leaves
  VC-DRIVING-004 passing** — the C2 sampling rule is enforced where it applies;
* **VC-DRIVING-029 is judged on the S-CORE monotonic clock**: a 5 s real-time skew at
  the stop begin does not move the verdict, and a health published 1 s late on
  the monotonic clock fails;
* **targeted mutations fail** (`failObservedBehavior`): a plan published
  101 ms after production; a health gap of 201 ms; a stop begun 101 ms of
  simulation time after a stale camera; a command after standstill that pulls;
  replay plans differing beyond the on-time spread; plus a missing and a
  doubled plan step, a plan age of 350 ms, an adapter stop 400 ms after the last
  command, a sample published 150 ms late, a command over the acceleration
  limit, a 3 m/s² stop, a reference inference off by 0.5 m/s², a plan naming
  another run record, one byte changed in the checkpoint, and the two C3
  columns removed from `out.command` (026 must name C3);
* **malformed → error, missing → inconclusive, unknown scenario → nothing
  selected**, and an unreadable run record turns all 35 into `errorEvidence`;
* the change list in `gaps.py` and the `needs` of the evaluators agree, and so
  does the table of `OBSERVABLES.md`.

## Readings

Where a requirement leaves room, the evaluators take the reading below. Each
is a reading the owner may change; the code names it where it applies.

* **The stop response presupposes a driving vehicle (VC-DRIVING-023, -024,
  -025).** While starting, the agent logs a fault, starts no stop and primes
  again. The baseline of a degraded-input case is the first condition at a
  step at or after `priming.complete` whose previous mode record is
  `kDriving`. Without such a step the case is inconclusive.
* **A camera condition (VC-DRIVING-023, no-fault half, runs of
  SC-DRIVING-001).** REQ-DRIVING-023 with its rationale "one late image is
  tolerated, a second means the camera has stopped": a camera condition exists
  at a step when the camera has had no image to date, its image is invalid, or
  its newest image is more than 200 ms of simulation time older than the step
  (`cases.CAMERA_NEWEST_IMAGE_LIMIT_MS`). A step whose own image missed the
  deadline while the camera's newest image is at most 200 ms old is not a
  condition. The newest image is the latest in any C2 step so far, or in a
  merged frame the agent conditioned (A23). A camera-caused stop without such a
  condition in the 100 ms before it fails the no-fault half. A condition while
  the agent drives must begin the stop within 100 ms.
* **Route coverage (VC-DRIVING-007, A16).** The recount counts the points of
  the route's centre lines as the navigation library builds them: one centre
  line per run of constant road id with two or more points
  (`ParseRouteJson`); a run of one point is dropped. A step without an accepted
  route (`routeSha256` null) has both counts 0 and is not recounted; a null
  sha on a step with a plan fails. Without a route in the run record, each
  step is compared with the route announcement in force at it.
* **Per-plan cases (VC-DRIVING-003, -004, -006, -007, -008, -010).** The
  criteria hold for the inputs of every plan, so only steps with an `out.plan`
  are judged; a run without plans is inconclusive. The engine's newest
  ego-motion row is frame k − 1 (agent `DESIGN.md`).
* **60 s windows (VC-DRIVING-013, -015, -016, -017).** Records spanning less
  than the window make the case inconclusive. VC-DRIVING-013's window starts at
  `priming.complete`, holds only plans made in `kDriving`, and its real-time
  factor is taken over the same window; below 0.95 the run cannot show the
  criterion (inconclusive).
* **VC-DRIVING-032.** The success criterion states no range: the four
  quantities are computed per command, each from stamps of one domain, and
  reported. Commands are joined to the adapter by `productionTime`. A
  negative value of any of the four makes the case inconclusive: a later stamp
  then precedes an earlier one on the same clock, so a join or a stamp is wrong.
* **Engine and names (VC-DRIVING-002, -003, -013).** A run of the stub engine
  (A17) makes all three inconclusive: it makes no checkpoint inference, so its
  images and its plan times say nothing about the driving system's. The camera names `cam_<slot>` written before A25
  are read as the slots, with a note.
* **Files named by the run record (VC-DRIVING-012, -033).** An absolute path
  names a file on the bench host. A copy retained in the run or campaign
  directory is used; a file at that path on the evaluating host only when its
  SHA-256 is the recorded one. VC-DRIVING-012 uses the vehicle limits only
  from a file with the recorded SHA-256.
* **`priming.complete` before A26 (VC-DRIVING-001).** A record on a step the
  engine did not condition is flagged, and the end of priming is the engine's
  first conditioned primed step.
* **No command law is assumed.** No evaluator derives a command's steering
  from the plan: VC-DRIVING-011 checks the sign reversal, VC-DRIVING-012 the
  limits, VC-DRIVING-021 the held steering. They hold for `first_control` and
  `pure_pursuit` (A27). The fixture runs use `first_control`.

## The synthetic runs

`make_synthetic_run.py` writes a run directory that follows ICD v2 section 7
(`run_record.json`, `config/`, `navigation/`, `score/*.jsonl`,
`score/bundles/*.npz`, `simulator/world.jsonl`, `guest/observer.jsonl`,
`bench/injection.jsonl`). The records follow the producers' shapes (agent,
actuation adapter, route provider; each fixture writer cites its producer).
The C2 metadata is written for every step from the agent's first step, primed
or not, as the agent writes it; full bundles are written on the C2 schedule (every 50th step and
±0.5 s around a fault); `referenceInference.jsonl` exists only for sampled plan
steps. The operational state is written as the decoded §3 struct. The
kinematics are a kinematic bicycle model on a 100 m radius route: the vehicle
accelerates to 8 m/s, drives, and — in the fault runs — stops at −4 m/s² to
standstill. The AAOS campaign's four runs are identical by construction, which
is the point: two replays on the same inputs must agree, so any difference in
the late or stopped run is the driving system reacting to its observer.

**These runs are test fixtures, not evidence.** The bundle tensors are small
placeholder arrays, there are no recordings, and the hashes are hashes of
synthetic bytes. `verdicts.json` from a synthetic run says the evaluator works;
it does not say the driving system met a requirement.

## Limits, stated plainly

* VC-DRIVING-002 is bounded to the C2 sampled steps: the pinned checkpoint is re-run on
  the retained bundles only (12 of 635 plans on the nominal run). The every-plan
  claim would need a bundle per plan step.
* VC-DRIVING-005 needs the marker's true image position, measured independently of the
  operator it checks. A11 logs the producer's `marker.image_px`, so the case
  still needs a measured bundle image.
* VC-DRIVING-003, VC-DRIVING-006 and VC-DRIVING-007 are decided from the A11/A16/A17 per-step metadata
  (the front hi-res size, the map_context shape/geometry, the route_mask
  geometry, sha and waypoint counts). The verdicts rest on the producer's
  metadata; the rasters themselves are only in the sampled bundles, and a
  left-right mirrored raster cannot be detected from counts (A16).
* VC-DRIVING-033's independence claim ("another engineer hashes the files and checks out
  the revision") is an act; the evaluator can only compare hashes and ordering.
  The checkpoint copy is one per campaign, resolved next to the run.
* VC-DRIVING-018's "differ by no more than" fixes no metric. The evaluator uses max-abs
  per signal on the produced plans and commands, against the
  reference-vs-reference spread, and reports every number so a reviewer can
  re-judge.
* VC-DRIVING-029 is judged on the S-CORE host's monotonic clock at the publisher
  (`score/statePublisher.jsonl`, `out.health`), as the S5 answer directs.

Nothing in this directory edits the ICD or the model. `OBSERVABLES.md` and
`gaps.py` record the remaining metadata gap.
