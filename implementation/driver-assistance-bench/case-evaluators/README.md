# Case evaluators of the driver-assistance bench (INC-DRIVING-002, S1)

The evaluators judge the records of one S1 session against the success criteria of REQ-DRIVING-036 to -038 and
-040 to -044 and give each verification case one of the six outcomes of `AssistanceEvidenceOutcome`. They read the
fetched session tree as it is; they do not run the bench. REQ-DRIVING-039 is an analysis of the realization and has
no evaluator here.

Status: draft, not yet validated. The evaluators at `44fe1608` judged S1 (SID 20261121T014447Z, 2026-11-21, `508649ba`)
on 2026-11-21, with the VC-DRIVING-044 desk record: VC-DRIVING-036, -037 and -042 fail; VC-DRIVING-038, -040, -041, -043
and -044 are inconclusive, because each run's judged window holds dropped camera images. Of the 14 runs, 6 are judged
runs: four runs of SC-DRIVING-012 and SC-DRIVING-013 miss their entry conditions (`012_20_r2`, `013_30_r2`, `013_60_r1`,
`013_60_r2`), and SC-DRIVING-014 and SC-DRIVING-015 have no judged-run term. VC-DRIVING-039 passes by a desk analysis,
outside these evaluators. A fail is a fail of the pinned candidate on this bench in simulation. No outcome here is an
approval or a compliance claim. The evidence records and the case statuses come in the phase 10 evidence pull request.

## Files

| File | What it holds |
|---|---|
| [`OBSERVABLES.md`](OBSERVABLES.md) | The contract: records, fields, clocks, terms, judged windows, case rules, missing-evidence texts |
| `terms.py` | The terms of the requirements: settings, time to collision, needed deceleration, imminence, functional part, judged run, warning and emergency-braking starts, the impact-speed limits |
| `runio_da.py` | Finds every run of a session tree by file name and reads its records |
| `cases_da.py` | The per-run evaluators of each case and the campaign rule |
| `evaluate_da_campaign.py` | The command line: one session in, one verdicts file out |
| `evidence_record.py` | The evidence record of each run (RetainedAssistanceRunEvidence), every attribute or the reason it is empty |
| `da_criteria_record.json` | The criteria record: each success criterion quoted from the model, the thresholds, the readings |
| `make_da_synthetic_run.py` | Synthetic sessions in the real line format, for the tests |

## Use

```bash
python3 evaluate_da_campaign.py --session <incoming session root> --out verdicts.json [--desk-044 reproduction_044.json]
```

Each case in `verdicts.json` names its `criteriaRecordIdentity` (the SHA-256 of `da_criteria_record.json`) and its
`evaluatorRevision` (a SHA-256 over the git blob ids of the evaluator files). After a change of a threshold in
`cases_da.py`, regenerate the criteria record with `--write-criteria`; a test fails while the two disagree.

## Rules worth knowing

- A setting of SC-DRIVING-012 or -013 is judged only when both of its runs are judged runs. A setting not judged
  gives inconclusive, never pass. A judged run that fails gives fail even when another setting is missing.
- A run whose judged window holds a `drop.camera_image` is inconclusive for that case. For 038, 040, 041, 043 and
  044 the window is the whole run. Such a run also reports `measured.withoutDropRule`, the reading with the rule set
  aside, for diagnosis only.
- The stop clause of VC-DRIVING-038 judges what reaches the actuation after the stop: the actuation adapter's
  `out.ackermann_control` and the world side's control calls. The control that the world records is the simulator's
  Ackermann controller output, which changes under a held target; its changes are a note only.
- VC-DRIVING-044 needs the desk reproduction by another engineer (`reproduction_044.json`, plan lane F2); without it
  the case is inconclusive.
- A run whose evidence record is partial gives inconclusive for that run, never pass and never fail (the lead's
  reading of 2026-11-21). A case's fail stands only when a run that shows it has a complete record; a pass with any
  partial record read becomes inconclusive. A note names the outcome observed before the rule. The fail of 044's
  desk reproduction is no run's and stands.
- A session whose session.json says `rehearsal` true is not judged: the command writes the reason and exits 3.

## Tests

```bash
env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 python -B -m pytest -p no:cacheprovider -rs tests/test_terms.py
```

Run each test file alone. `tests/test_attempt3_records.py` reads the real attempt-3 records when
`DA_ATTEMPT3_ROOT` points at them, and skips otherwise.
