#!/usr/bin/env python3
"""Judge the verification cases of one bench run.

Reads an ICD v2 run directory (sections 6-8), selects the cases that apply
to the run's scenario (run_record.json `scenario`), evaluates each, and writes
verdicts.json:

    {
      "schema": "de4sdv.driving.case-verdicts.v1",
      "run": {...},
      "cases": {"VC-DRIVING-001": {outcome, verdict, measured, thresholds,
                                   evidence, missing, notes, icd_changes}, ...},
      "skipped": {"VC-DRIVING-018": "campaign case ..."},
      "summary": {"pass": n, "fail": n, "inconclusive": n, "error": n}
    }

`outcome` is a DrivingEvidenceOutcome literal of the model. A case whose
record is missing gives inconclusiveMissingEvidence, never a pass; a record
that cannot be read gives errorEvidence.

Usage:
    python evaluate_run.py <run_dir> [--out verdicts.json] [--only VC-DRIVING-023]

A case that needs a record ICD v2 does not define is inconclusive, whether or
not the record is present: the outcome names the record that would supply it.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import cases
import gaps
from runio import Run, RunFormatError, MissingEvidence


def evaluate(run_dir: str | Path, only: list[str] | None = None) -> dict:
    root = Path(run_dir)
    try:
        run = Run(root)
    except (RunFormatError, MissingEvidence) as exc:
        # No run record: nothing can be selected. Every case is an error, which
        # is what an unreadable record is, not a pass and not a silent skip.
        return {
            "schema": "de4sdv.driving.case-verdicts.v1",
            "run": {"path": str(root), "readable": False, "error": str(exc)},
            "cases": {vc: {"vc": vc, "outcome": cases.ERROR, "verdict": "error",
                           "measured": {}, "thresholds": {}, "evidence": [],
                           "missing": [], "notes": [str(exc)], "icd_changes": []}
                      for vc in sorted(cases.CASES)},
            "skipped": {},
            "summary": {"pass": 0, "fail": 0, "inconclusive": 0, "error": 35},
        }

    conflicts = cases.label_conflicts(run)
    selected = cases.applicable(run)
    if only:
        unknown = set(only) - set(cases.CASES)
        if unknown:
            raise SystemExit(f"unknown case(s): {', '.join(sorted(unknown))}")
        selected = [vc for vc in selected if vc in only]

    out: dict[str, dict] = {}
    skipped: dict[str, str] = {}
    for vc in selected:
        if vc in ("VC-DRIVING-018", "VC-DRIVING-019"):
            skipped[vc] = ("campaign case: it needs the four runs of SC-DRIVING-004; "
                           "run evaluate_campaign.py")
            continue
        res = cases.evaluate_case(run, vc)
        res.notes = conflicts + list(res.notes)
        if res.outcome == cases.NOT_APPLICABLE:
            skipped[vc] = "; ".join(res.notes) or "not applicable to this run"
            continue
        out[vc] = res.as_dict()
        out[vc]["amendments"] = gaps.amendments_for(vc)

    # a case whose evaluator chose not to apply itself (e.g. REQ-029 on a run
    # without a stop) is reported in skipped, never dropped silently
    summary = {"pass": 0, "fail": 0, "inconclusive": 0, "error": 0}
    for v in out.values():
        summary[v["verdict"]] = summary.get(v["verdict"], 0) + 1
    return {
        "schema": "de4sdv.driving.case-verdicts.v1",
        "run": {
            "path": str(root),
            "readable": True,
            "run_record_identity": run.identity(),
            "scenario": run.scenario,
            "scenario_variant": run.variant,
            "campaign_id": run.campaign(),
            "run_role": run.role(),
            "contract_identity": run.record.get("contractIdentity"),
        },
        "cases": dict(sorted(out.items())),
        "skipped": skipped,
        "label_conflicts": conflicts,
        "summary": summary,
        "evaluated_at_real_ns": int(time.time() * 1e9),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("run_dir", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--only", nargs="+", default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()

    report = evaluate(args.run_dir, args.only)
    out = args.out or (args.run_dir / "verdicts.json")
    out.write_text(json.dumps(report, indent=1, sort_keys=False) + "\n")
    if not args.quiet:
        s = report["summary"]
        print(f"{args.run_dir}: {report['run'].get('scenario')} "
              f"role={report['run'].get('run_role')}  "
              f"pass={s['pass']} fail={s['fail']} inconclusive={s['inconclusive']} "
              f"error={s['error']} skipped={len(report['skipped'])}")
        for vc, v in report["cases"].items():
            why = ""
            if v["outcome"] != cases.PASS:
                why = (v["missing"][0] if v["missing"] else
                       (v["notes"][0] if v["notes"] else ""))[:110]
            print(f"  {vc}  {v['outcome']:<32} {why}")
        for vc, why in report["skipped"].items():
            print(f"  {vc}  skipped: {why[:100]}")
        print(f"  -> {out}")
    # exit code: 0 when nothing failed and nothing errored
    for c in report.get("label_conflicts", []):
        print(f"  LABEL CONFLICT: {c}")
    return 1 if (report["summary"]["fail"] or report["summary"]["error"]
                 or report.get("label_conflicts")) else 0


if __name__ == "__main__":
    sys.exit(main())
