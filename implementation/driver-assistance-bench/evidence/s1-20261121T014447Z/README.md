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
- The 14 runs of the seven settings of SC-DRIVING-012 to SC-DRIVING-015 (6 of
  them judged runs; SC-DRIVING-014 and SC-DRIVING-015 have no judged-run term),
  the run that stops the S-CORE path, and the calibration runs before the first
  judged run.
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
| `commanded_deceleration.json` | The strongest deceleration among the driving commands that the actuation adapter of each run accepted, and for each run of SC-DRIVING-012 the speed that they, fully achieved, would have taken off before the contact, with the method |
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
Session `20261121T014447Z`, criteriaRecordIdentity `sha256:c84925741d1bada6e0f1b1d99aca85ebfcb07ee77effb119e13cbe41cc17e136`, evaluatorRevision `blobs:a79e202591ff4e583acaa5ca958be6b67e3931d7ee612c70ebcda23f80f3ca68`.

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
the distribution, never a rate). Each of the 14 runs of SC-DRIVING-012 to
SC-DRIVING-015 drops 23 or 24 images in the first 5 s after its first image, 2
to 6 in the last 0.6 s of its image stream, which goes on after the run's last
world tick until the S-CORE side stops, and 0 to 3 isolated images in between.
The file gives each run's end from `run_end.json` and the ticks that
`tick_times.csv` records after it.

The warm start of D-S1-1 (patch 0005 of the bench) ran before the attach in
every run: the Launch Manager log of each run records 2 passes with the result
yes, in 678.3 to 706.8 ms (`score_side/state/launch_manager.log`). It did not
keep the first 5 s after the first image free of dropped images.
`drop_counts.json` gives each run's value.

The case evaluators at `508649ba` judge a criterion over every run in the window
from the run's first to its last world tick (`world.jsonl`) and count each
`drop.camera_image` whose simulation time lies in it (`Run.drops_in` in
`runio_da.py`, `whole_run` in `cases_da.py`): 23 to 25 in each of the 14 runs,
the start-up drops and the isolated drops inside the run, and none of the end of
the image stream; 32 in the run that stops the path. The final verdicts come
from the case evaluators at `44fe1608` (the evaluatorRevision of
`verdicts.json`), whose `Run.drops_in` and `whole_run` are those of `508649ba`.
The records show no cause of the drops.

## The commanded deceleration

In no run of SC-DRIVING-012 did the candidate command a deceleration stronger
than 0.533 m/s²: the strongest driving command that the actuation adapter
accepted holds 0.46 and 0.53 m/s² at 20 km/h; 0.18 and 0.18 m/s² at 42 km/h;
0.23 and 0.18 m/s² at 60 km/h (rounded to two decimals;
`commanded_deceleration.json` holds three). The last command that holds a
deceleration came 0.7 and 0.6 s before the contact at 20 km/h; 0.3 and 0.3 s at
42 km/h; 0.2 and 0.3 s at 60 km/h.

The commanded decelerations of each run, fully achieved, would have lowered its
speed before the contact by at most 2.4 km/h: by at most 2.1 and 2.4 km/h from
19.7 and 19.2 km/h at 20 km/h; 0.4 and 0.5 km/h from 40.6 and 40.6 km/h at 42
km/h; 0.3 and 0.3 km/h from 58.6 and 58.6 km/h at 60 km/h (rounded up to one
decimal; `commanded_deceleration.json` states the method). Each accepted command
is held until the next, up to the first world tick with a collision or a target
contact, and the speed is that of the tick before it. The condition on
ASM-DRIVING-005 concerns how the simulated vehicle achieves a commanded
deceleration: it bears on a pass of VC-DRIVING-036 and VC-DRIVING-037 and does
not bear on these fails, since no calibration of the achieved deceleration turns
them into passes (the deceleration calibration decision of 2026-11-21).

## Open bench item B1

The second runs of SC-DRIVING-013, `013_30_r2` and `013_60_r2`, ended after
62 ticks at the speed of the target, with the vehicle at 1.3 km/h and the
target at 20 km/h. At the first tick of each the target was at rest (8e-08 and
8.5e-05 m/s); in the first runs it already moved at 5.2 m/s. The end check of
the world side (`_run_loop` in `world-side/da_world_side.py` at `508649ba`)
counts the vehicle as closing on the target while the closing speed is above
0.0 m/s, and ends the run 3.0 s after the first later tick at which it is not:
at the first tick of the second runs the vehicle closed at 0.0023 m/s on the
target at rest, at the second the target moved at 5.26 m/s, so each run ended
3.05 s after its first tick. Why the target was at rest at the first tick of
the second runs only, the records do not show. `013_60_r1` ended in contact
with the target but has no functional part: no tick in the band with a time
to collision of at least 4 s. So SC-DRIVING-013 has one judged run,
`013_30_r1`.

It is not fixed for S1: a fix would change a file that ran in S1 and void the
condition of record. It is open for the next session (GAP-DRIVING-014).

## Open bench item B3

The case evaluators at `44fe1608` (`site_guidance` in
`case-evaluators/cases_da.py`) look for the speeds and times to collision of the
source's guidance for SC-DRIVING-014 and SC-DRIVING-015, `approachKmh` and
`bothKmh` among them, under `site.guidance` of each run's `setting_record.json`;
the world side writes them one level lower, under `site.guidance.regulation`
(`SiteSpec.as_record()` in `world-side/sites.py`). So VC-DRIVING-040 and
VC-DRIVING-041 find them absent in each of the four runs of SC-DRIVING-014 and
SC-DRIVING-015 (`measured.withoutDropRule` of these runs in `verdicts.json`) and
read the runs as inconclusive even with the rule on dropped images set aside.
The verdicts of S1 do not change: by that rule the runs are inconclusive
already.

The fix belongs to the case evaluators, which judge the fetched records after
the session: it changes no file that ran on a host and does not void the
condition of record. It is not made for S1; it is open for the next reading of
the records (GAP-DRIVING-014).

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
