# INC-DRIVING-002 evidence of record: the judged session S1

This directory holds the small machine-readable records of the judged session
S1 of INC-DRIVING-002, session `20261121T014447Z`, and the identities of
everything it leaves outside Git. The model reads these files: the evidence
records and the case statuses of
[`driver_assistance_verification_evidence.sysml`](../../../../textual-notation-of-model/packages/features/driving/driver_assistance_verification_evidence.sysml)
are generated from them. Repository presence proves only that the records are
controlled at a revision; the rules are in
[Evidence Management](../../../../docs/evidence-management.md).

Status: draft. Nothing in this directory or in the session tree is published.
The results are not shown to the VisionPilot maintainers yet, and the owner
approves any text before they are.

## What ran

- Three hosts in one session: the simulator host with CARLA 1.0, the S-CORE
  host with its NVIDIA L4 running the pinned candidate (VisionPilot at
  014e0e7a with the DE4SDV changes that `records.json` names) under the
  Eclipse S-CORE Launch Manager, and the guest host with the SDV Core and the
  IVI guests. `session.json` records the hosts, the bench commit, the
  Ackermann gains (`v1`) and the exit code (0).
- The fourteen judged runs of the seven settings, the run that stops the
  S-CORE path, and the calibration runs before the first judged run.
- Bench commit `508649ba` of pull request #549 (the branch
  `impl/da-bench`). The case evaluators ran after the session on the fetched
  records; `verdicts.json` names their revision.
- The session cost 4.952 EUR (`cost.log` in the session tree). The later
  fetch of the candidate's visualization recordings from the S-CORE host is
  stated at the on-demand rate of the L4 host, 0.806 EUR/h; its own cost
  record uses the Spot rate, 0.483 EUR/h, because its command line lacked the
  host's rate.

## The condition of record

S1 is the evidence of record on one condition (the evidence-of-record
decision of 2026-11-21): the bench files that ran on a host are byte-identical
to those that #549 merges. Once #549 merges at `<merged>`, check:

```bash
git diff --stat 508649ba <merged> -- implementation/driver-assistance-bench
```

It must list only files that did not run on a host: the case evaluators,
which judge the fetched records after the session, their tests, and
documentation. A file of the session runner, the world side, the S-CORE side,
the actuation adapter, the guest apps or the scenario definitions in that list
voids the condition.

## The files

| File | What it is |
|---|---|
| `verdicts.json` | The case evaluators' verdicts: each case's outcome, verdict, per-run values and reasons |
| `records.json` | One `RetainedAssistanceRunEvidence` record per run, with its empty attributes |
| `analysis_039.json` | The full desk analysis of REQ-DRIVING-039, with its findings, the retained record |
| `analysis_039.generator.json` | Its reduction to the keys the generator reads |
| `reproduction_044.json` | The desk reproduction of the candidate identity of REQ-DRIVING-044 |
| `session.json`, `scenario_digests.json` | The session's own record and the digests of the scenario definitions |
| `drop_counts.json` | Where the camera images of each run drop, from its score-interface record, with the run's end and the drops the evaluators count over the whole run |
| `SHA256SUMS` | The SHA-256 of every file of the fetched session tree, by relative path |
| `external-media.json` | The recordings and archives of the tree, with identity and retention |

The two desk records come from independent agent sessions dispatched by the
lead on 2026-11-21, with no access to the lead's notes; each record says so.

## The verdicts

Generated from `verdicts.json` and `analysis_039.generator.json`; never edit
the table by hand. The case outcomes judge the pinned candidate on this bench
in simulation and nothing else: a fail is a fail of that build there, and no
outcome is a statement about compliance, approval or on-road behavior.

<!-- BEGIN generated verdict table: tools/refresh_driver_assistance_s1_evidence.py -->
Session `20261121T014447Z`, criteriaRecordIdentity `sha256:ac70a39e05e2c51962e9a335aa67d2140757907d4f06c7d0795cdb9b10f51100`, evaluatorRevision `blobs:92cca76362b09c509fe9fe6fa77b926b624d9d60668f383975594bdb7fd4248f`.

| Case | Requirement | Outcome | Verdict |
|---|---|---|---|
| VC-DRIVING-036 | REQ-DRIVING-036 | `failObservedBehavior` | fail |
| VC-DRIVING-037 | REQ-DRIVING-037 | `failObservedBehavior` | fail |
| VC-DRIVING-038 | REQ-DRIVING-038 | `inconclusiveMissingEvidence` | inconclusive |
| VC-DRIVING-039 | REQ-DRIVING-039 | `passBoundedVerification` | pass |
| VC-DRIVING-040 | REQ-DRIVING-040 | `inconclusiveMissingEvidence` | inconclusive |
| VC-DRIVING-041 | REQ-DRIVING-041 | `inconclusiveMissingEvidence` | inconclusive |
| VC-DRIVING-042 | REQ-DRIVING-042 | `failObservedBehavior` | fail |
| VC-DRIVING-043 | REQ-DRIVING-043 | `inconclusiveMissingEvidence` | inconclusive |
| VC-DRIVING-044 | REQ-DRIVING-044 | `inconclusiveMissingEvidence` | inconclusive |

| Run | VC-DRIVING-036 | VC-DRIVING-037 | VC-DRIVING-038 | VC-DRIVING-040 | VC-DRIVING-041 | VC-DRIVING-042 | VC-DRIVING-043 | VC-DRIVING-044 |
|---|---|---|---|---|---|---|---|---|
| SC-DRIVING-012@20/r1 | fail | fail (19.7 km/h) | inconclusive | inconclusive | inconclusive | fail | inconclusive | inconclusive |
| SC-DRIVING-012@20/r2 | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive |
| SC-DRIVING-012@42/r1 | fail | fail (40.6 km/h) | inconclusive | inconclusive | inconclusive | fail | inconclusive | inconclusive |
| SC-DRIVING-012@42/r2 | fail | fail (40.6 km/h) | inconclusive | inconclusive | inconclusive | fail | inconclusive | inconclusive |
| SC-DRIVING-012@60/r1 | fail | fail (58.6 km/h) | inconclusive | inconclusive | inconclusive | fail | inconclusive | inconclusive |
| SC-DRIVING-012@60/r2 | fail | fail (58.6 km/h) | inconclusive | inconclusive | inconclusive | fail | inconclusive | inconclusive |
| SC-DRIVING-013@30/r1 | pass | pass (0.0 km/h) | inconclusive | inconclusive | inconclusive | pass | inconclusive | inconclusive |
| SC-DRIVING-013@30/r2 | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive |
| SC-DRIVING-013@60/r1 | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive |
| SC-DRIVING-013@60/r2 | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive | inconclusive |
| SC-DRIVING-014@30/r1 | not read | not read | inconclusive | inconclusive | inconclusive | not read | not read | inconclusive |
| SC-DRIVING-014@30/r2 | not read | not read | inconclusive | inconclusive | inconclusive | not read | not read | inconclusive |
| SC-DRIVING-015@40/r1 | not read | not read | inconclusive | inconclusive | inconclusive | not read | not read | inconclusive |
| SC-DRIVING-015@40/r2 | not read | not read | inconclusive | inconclusive | inconclusive | not read | not read | inconclusive |
| stop/further | not read | not read | inconclusive (stop clause) | not read | not read | not read | inconclusive (stop clause) | not read |

The impact speed in brackets is the relative impact speed that VC-DRIVING-037 measured. An outcome of a case over a run is that run's part of the case; the case's own outcome is in the first table.
<!-- END generated verdict table -->

By the rule of phase 8 (`MAP-DRIVING-DA-CAMERA-IMAGE`), no run whose judged
window holds a dropped image is judged; for the cases over every run that
window is the whole run. The drop rule stands (the drop-rule decision of
2026-11-21). `verdicts.json` also holds readings with the drop rule set aside
(`measured.withoutDropRule`): they are diagnosis only, never a verdict, and no
table here or in the model quotes them as one.

## The dropped images

`drop_counts.json` places the `drop.camera_image` events of each run's
score-interface record by their simulation time (the correction of 2026-11-21:
the distribution, never a rate). Each judged run drops 23 or 24 images in the
first 5 s after its first image, 2 to 6 in the last 0.6 s of its image stream,
which goes on after the run's last world tick until the S-CORE side stops, and
0 to 3 isolated images in between. The file gives each run's end from
`run_end.json` and the ticks that `tick_times.csv` records after it.

The case evaluators at `508649ba` judge a criterion over every run in the
window from the run's first to its last world tick (`world.jsonl`) and count
each `drop.camera_image` whose simulation time lies in it (`Run.drops_in` in
`runio_da.py`, `whole_run` in `cases_da.py`): 23 to 25 in each judged run,
the start-up drops and the isolated drops inside the run, and none of the end
of the image stream; 32 in the run that stops the path. The records show
no cause of the drops.

## Where the rest is retained

- **The fetched session tree** (about 2 GB, every file listed in
  `SHA256SUMS`) is retained on the maintainer's host, outside Git. Check it
  with `sha256sum -c SHA256SUMS` from the root of the tree.
- **The media** (chase views, display captures, screen captures, the
  candidate's visualization recordings and data logs, and the archives) are
  listed in `external-media.json`; their disposition is in
  [VIDEO-EVIDENCE-DISPOSITION.md](VIDEO-EVIDENCE-DISPOSITION.md). None is in
  Git, none is published, and the location is a maintainer archive, not
  public evidence.
- **The records that name files on the S-CORE host** (`/home/mrk/da-kit/...`,
  `/tmp/de4sdv-da-bench/...`) name them by the path they had there and by
  their SHA-256.

## Regenerate

One command rewrites every file above that comes from a verdict file, a desk
record or the session tree, the table above, and the model's evidence records
and case statuses:

```bash
python tools/refresh_driver_assistance_s1_evidence.py \
    --eval-dir <dir with verdicts.json and records.json> \
    --analysis-039 <analysis_039.json> --reproduction-044 <reproduction_044.json> \
    --session-tree <fetched session tree>
```

Then run `tests/test_driver_assistance_s1_evidence_directory.py` and
`tests/test_driver_assistance_verification_evidence.py`.
