#!/usr/bin/env python3
"""Judge the cases that need more than one run.

Four campaigns, one per group of runs the cases name:

* obs-independence  (SC-DRIVING-004): ref1, ref2 (on time), late (every
  publication 1 s late), stopped. Gives VC-DRIVING-018 and VC-DRIVING-019.
* stop-response     (SC-DRIVING-003): entry10, entry20. Aggregates
  VC-DRIVING-020, -021, -022.
* checkpoint-refusal: mismatch, unpinned. Aggregates VC-DRIVING-035.
* degraded: the fault runs; no campaign case, but its runs are used by
  evaluate_run.py.

A campaign judges every run it holds. Where a case is aggregated from the
verdicts of single runs (VC-DRIVING-020, -021, -022, -035), a role passes only
if each of its runs passes, and measured.runs lists every run. VC-DRIVING-018
and -019 compare one run of each role; a role with more than one run makes
them inconclusive.

The difference metric of REQ-018 is not fixed by the requirement. This script
fixes it and reports every number so a reviewer can re-judge: for each signal
(plan acceleration, plan curvature, command acceleration, command steering)
the largest absolute difference over the plans/commands present in both runs,
compared signal by signal with the reference-versus-reference difference. The
same metric is applied to the late run and to the stopped run.

Usage:
    python evaluate_campaign.py <runs_root> [--out campaign_verdicts.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

import cases
from cases import FAIL, PASS, Result, ev
from runio import MissingEvidence, Run, RunFormatError

REQUIRED_ROLES = {
    "obs-independence": ("ref1", "ref2", "late", "stopped"),
    "stop-response": ("entry10", "entry20"),
    "checkpoint-refusal": ("mismatch", "unpinned"),
}

SIGNALS = ("plan_acceleration", "plan_curvature", "command_acceleration",
           "command_steering")

SPREAD_TOL = 1e-9          # a reference pair on identical inputs must agree to this
P99_SPREAD_TOL = 0.010     # REQ-019


def load_runs(root: Path) -> dict[str, list[Run]]:
    groups: dict[str, list[Run]] = {}
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not (d / "run_record.json").exists():
            continue
        try:
            run = Run(d)
        except (RunFormatError, MissingEvidence):
            continue
        cid = run.campaign() or "unassigned"
        groups.setdefault(cid, []).append(run)
    return groups


def by_role(runs: list[Run]) -> dict[str, list[Run]]:
    """Every run of each role, in directory order.

    A role is never reduced to one of its runs: two runs with the same runRole
    are both judged (aggregate) or make the case inconclusive (vc018, vc019).
    """
    out: dict[str, list[Run]] = {}
    for i, r in enumerate(runs):
        out.setdefault(r.role() or f"unnamed{i}", []).append(r)
    return out


def run_entry(run: Run, res: Result | None = None) -> dict:
    """One run as measured.runs lists it, with its outcome when it was judged."""
    entry: dict = {"path": str(run.root), "run_record_identity": run.identity()}
    if res is not None:
        entry.update({"outcome": res.outcome, "measured": res.measured,
                      "missing": res.missing, "notes": res.notes})
    return entry


def one_run_per_role(vc: str, runs: list[Run], need: tuple[str, ...]) -> dict[str, Run] | Result:
    """The run of each role a case compares, or the inconclusive result when a
    role has no run or more than one: the case compares one run of each role
    and cannot tell which of two runs with the same role is the campaign's."""
    r = by_role(runs)
    missing = [x for x in need if x not in r]
    if missing:
        return cases.inconclusive(vc, f"runs: {', '.join(missing)}", "C4",
                                  "the campaign has no run with these roles")
    doubled = [x for x in need if len(r[x]) > 1]
    if doubled:
        return cases.inconclusive(
            vc, f"one run of role {doubled[0]}", "C4",
            "the campaign holds more than one run of role "
            + ", ".join(f"{x} ({len(r[x])})" for x in doubled)
            + "; the case compares one run of each role",
            {"runs": {x: [run_entry(y) for y in r[x]] for x in doubled}})
    return {x: r[x][0] for x in need}


# ------------------------------------------------------------------ metric
def plan_series(run: Run) -> dict[int, dict]:
    out = {}
    for p in run.plans(required=False):
        f = p.get("frame")
        if not isinstance(f, int):
            continue
        acc = np.array([s["acceleration"] for s in p["samples"]], dtype=float)
        cur = np.array([s["curvature"] for s in p["samples"]], dtype=float)
        out[f] = {"acceleration": acc, "curvature": cur,
                  "reference": p.get("reference")}
    return out


def _command_key(reference: str, fallback: float) -> str:
    """Commands are matched across runs by the plan frame they name, not by the
    plan reference: the reference starts with the run record identity, which
    differs between runs by construction."""
    if reference and "/" in reference:
        tail = reference.rsplit("/", 1)[-1]
        if tail.isdigit():
            return tail
    return f"@{fallback}"


def command_series(run: Run) -> dict[str, dict]:
    out = {}
    for c in run.commands():
        key = _command_key(c["reference"] or "", c["production_mono"] or 0.0)
        out[key] = {"acceleration": c["accel"], "steering": c["steer"]}
    return out


def diff_runs(a: Run, b: Run) -> dict:
    """Largest absolute difference per signal between two runs."""
    pa, pb = plan_series(a), plan_series(b)
    ca, cb = command_series(a), command_series(b)
    common = sorted(set(pa) & set(pb))
    res: dict = {"frames_only_in_a": len(set(pa) - set(pb)),
                 "frames_only_in_b": len(set(pb) - set(pa)),
                 "commands_only_in_a": len(set(ca) - set(cb)),
                 "commands_only_in_b": len(set(cb) - set(ca)),
                 "plans_compared": len(common)}
    if not common:
        res.update({s: None for s in SIGNALS})
        return res
    da = dc = 0.0
    for f in common:
        x, y = pa[f], pb[f]
        if x["acceleration"].size != y["acceleration"].size:
            res["size_mismatch"] = f
            da = dc = float("inf")
            break
        da = max(da, float(np.max(np.abs(x["acceleration"] - y["acceleration"]))))
        dc = max(dc, float(np.max(np.abs(x["curvature"] - y["curvature"]))))
    res["plan_acceleration"] = da
    res["plan_curvature"] = dc
    shared = sorted(set(ca) & set(cb))
    if shared:
        res["command_acceleration"] = max(
            abs((ca[r]["acceleration"] or 0.0) - (cb[r]["acceleration"] or 0.0))
            for r in shared)
        res["command_steering"] = max(
            abs((ca[r]["steering"] or 0.0) - (cb[r]["steering"] or 0.0)) for r in shared)
    else:
        res["command_acceleration"] = res["command_steering"] = None
    return res


def planning_times(run: Run) -> list[float]:
    arr = {}
    for step in run.input_steps():
        arrivals = [c["arrival_mono_ns"] for c in step["cameras"]
                    if c.get("arrival_mono_ns") is not None]
        if arrivals:
            arr[step["frame"]] = max(arrivals) / 1e9
    out = []
    for p in run.plans(required=False):
        f = p.get("frame")
        if not isinstance(f, int) or p.get("production_mono") is None:
            continue
        cand = [k for k in arr if k <= f]
        if not cand:
            continue
        out.append(p["production_mono"] - arr[max(cand)])
    return out


# ------------------------------------------------------------------ cases
def vc018(runs: list[Run]) -> Result:
    vc = "VC-DRIVING-018"
    r = one_run_per_role(vc, runs, REQUIRED_ROLES["obs-independence"])
    if isinstance(r, Result):
        return r
    ref1, ref2, late, stopped = (r["ref1"], r["ref2"], r["late"], r["stopped"])
    digests = {x.record.get("inputReplay", {}).get("digest")
               for x in (ref1, ref2, late, stopped)}
    if len(digests) != 1 or None in digests:
        return cases.inconclusive(vc, "run_record.inputReplay.digest", "C4",
                                  "the four runs do not name the same replayed inputs")
    floor = diff_runs(ref2, ref1)
    dl = diff_runs(late, ref1)
    ds = diff_runs(stopped, ref1)
    over = {}
    for sig in SIGNALS:
        base = floor.get(sig)
        if base is None or dl.get(sig) is None or ds.get(sig) is None:
            over[sig] = "not comparable"
            continue
        if dl[sig] > base + SPREAD_TOL or ds[sig] > base + SPREAD_TOL:
            over[sig] = {"reference_spread": base, "late": dl[sig], "stopped": ds[sig]}
    measured = {"reference_spread": floor, "late_vs_reference": dl,
                "stopped_vs_reference": ds, "over_the_spread": over,
                "replay_digest": digests.pop()}
    th = {"metric": "max abs difference per signal, signal by signal",
          "allowed": "no more than the reference-versus-reference difference",
          "tolerance": SPREAD_TOL}
    evid = [ev(p["file"], p["rec"]) for p in (ref1.plans(required=False)[:1]
                                              + late.plans(required=False)[:1])]
    if over:
        return cases.bad(vc, measured, th, evid,
                         [f"{sig}: late {over[sig]['late'] if isinstance(over[sig], dict) else over[sig]}"
                          for sig in over])
    return cases.ok(vc, measured, th, evid,
                    ["the metric is this evaluator's; REQ-018 does not fix one"])


def vc019(runs: list[Run]) -> Result:
    vc = "VC-DRIVING-019"
    need = REQUIRED_ROLES["obs-independence"]
    r = one_run_per_role(vc, runs, need)
    if isinstance(r, Result):
        return r
    p99, counts = {}, {}
    for role in need:
        lat = planning_times(r[role])
        if not lat:
            return cases.inconclusive(vc, f"planning times of {role}", "C2",
                                      "no plan can be timed against its newest image")
        p99[role] = float(np.percentile(np.array(lat), 99))
        counts[role] = len(lat)
    worst = max(abs(a - b) for i, a in enumerate(p99.values())
                for b in list(p99.values())[i + 1:])
    measured = {"p99_planning_time_s": p99, "plans": counts,
                "largest_difference_s": worst}
    th = {"p99_spread_s": P99_SPREAD_TOL}
    evid = []
    if worst > P99_SPREAD_TOL + 1e-12:
        return cases.bad(vc, measured, th, evid,
                         [f"the 99th percentile of planning time differs by "
                          f"{worst * 1000:.1f} ms between runs, limit 10 ms"])
    return cases.ok(vc, measured, th, evid)


def aggregate(vc: str, runs: list[Run], roles: tuple[str, ...]) -> Result:
    """Judge every run of every role; a role passes only if each of its runs
    passes, and measured.runs lists every run with its outcome."""
    r = by_role(runs)
    missing = [x for x in roles if x not in r]
    if missing:
        return cases.inconclusive(vc, f"runs: {', '.join(missing)}", "C4",
                                  "the campaign has no run with these roles")
    outcomes = {x: [run_entry(run, cases.evaluate_case(run, vc)) for run in r[x]]
                for x in roles}
    judged = [(x, o) for x in roles for o in outcomes[x]]
    failed = [(x, o) for x, o in judged if o["outcome"] == FAIL]
    if failed:
        return cases.bad(vc, {"runs": outcomes}, {"all_runs_must_pass": True}, [],
                         [f"{x} run {o['run_record_identity']} ({o['path']}) fails"
                          for x, o in failed])
    open_runs = [(x, o) for x, o in judged if o["outcome"] != PASS]
    if open_runs:
        x, o = open_runs[0]
        return cases.inconclusive(vc, f"{x} run {o['run_record_identity']}: {o['missing']}",
                                  "C4", "a run of the campaign is inconclusive",
                                  {"runs": outcomes})
    return cases.ok(vc, {"runs": outcomes}, {"all_runs_must_pass": True}, [])


def evaluate_campaign(root: Path) -> dict:
    groups = load_runs(Path(root))
    out: dict[str, dict] = {}
    skipped: dict[str, str] = {}
    # a run whose records contradict its label (cases.label_conflicts) is
    # flagged here: a campaign is never passed over silently because of it
    conflicts = {str(r.root): cases.label_conflicts(r)
                 for rs in groups.values() for r in rs if cases.label_conflicts(r)}
    for cid, runs in groups.items():
        if cid == "obs-independence":
            out["VC-DRIVING-018"] = vc018(runs).as_dict()
            out["VC-DRIVING-019"] = vc019(runs).as_dict()
        elif cid == "stop-response":
            for vc in ("VC-DRIVING-020", "VC-DRIVING-021", "VC-DRIVING-022"):
                out[vc] = aggregate(vc, runs, REQUIRED_ROLES["stop-response"]).as_dict()
        elif cid == "checkpoint-refusal":
            out["VC-DRIVING-035"] = aggregate(
                "VC-DRIVING-035", runs, REQUIRED_ROLES["checkpoint-refusal"]).as_dict()
        else:
            skipped[cid] = (f"{len(runs)} run(s); no multi-run case of this campaign "
                            "(use evaluate_run.py per run)")
    summary = {"pass": 0, "fail": 0, "inconclusive": 0, "error": 0}
    for v in out.values():
        summary[v["verdict"]] = summary.get(v["verdict"], 0) + 1
    return {"schema": "de4sdv.driving.campaign-verdicts.v1",
            "runs": {cid: [{"path": str(r.root), "role": r.role(),
                           "scenario": r.scenario,
                           "run_record_identity": r.identity()} for r in rs]
                     for cid, rs in groups.items()},
            "cases": out, "skipped_campaigns": skipped, "label_conflicts": conflicts,
            "summary": summary}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("runs_root", type=Path)
    ap.add_argument("--out", type=Path, default=None)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    report = evaluate_campaign(args.runs_root)
    out = args.out or (args.runs_root / "campaign_verdicts.json")
    out.write_text(json.dumps(report, indent=1) + "\n")
    if not args.quiet:
        s = report["summary"]
        print(f"{args.runs_root}: pass={s['pass']} fail={s['fail']} "
              f"inconclusive={s['inconclusive']} error={s['error']}")
        for vc, v in report["cases"].items():
            why = (v["missing"][0] if v["missing"] else
                   (v["notes"][0] if v["notes"] else ""))[:110]
            print(f"  {vc}  {v['outcome']:<32} {why}")
        for path, why in report["label_conflicts"].items():
            print(f"  LABEL CONFLICT {path}: {why[0]}")
        print(f"  -> {out}")
    return 1 if (report["summary"]["fail"] or report["summary"]["error"]
                 or report["label_conflicts"]) else 0


if __name__ == "__main__":
    sys.exit(main())
