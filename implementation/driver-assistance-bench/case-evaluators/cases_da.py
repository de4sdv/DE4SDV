"""The S1 case evaluators of INC-DRIVING-002: VC-DRIVING-036 to -038 and -040 to -044.

Pattern: the INC-DRIVING-001 frame (`implementation/closed-loop-driving-bench/case-evaluators/cases.py:236-316`:
a `Result` per case, `ok`/`bad`/`inconclusive`, a registry of `@case` evaluators). Each case judges every run it
reads (a run entry with its own outcome, measured values and missing-evidence texts), then combines the runs by the
campaign rule (OBSERVABLES.md, "Outcomes"). The outcome literals are the six of `AssistanceEvidenceOutcome`
(`driver_assistance_verification_evidence.sysml:120-138`), the verdict that of `MapAssistanceEvidenceOutcomeToVerdict`
(`:140-148`).
"""

from __future__ import annotations

import bisect

import terms
from runio_da import EvidenceError, MissingEvidence, Run, Session

PASS = "passBoundedVerification"
PASS_VALIDATION = "passBoundedValidation"
FAIL = "failObservedBehavior"
INCONCLUSIVE = "inconclusiveMissingEvidence"
BLOCKED = "blockedTargetRuntime"
ERROR = "errorEvidence"
OUTCOMES = (PASS, PASS_VALIDATION, FAIL, INCONCLUSIVE, BLOCKED, ERROR)
VERDICT = {PASS: "pass", PASS_VALIDATION: "pass", FAIL: "fail", ERROR: "error"}   # otherwise inconclusive

NR = "textual-notation-of-model/packages/features/driving/driver_assistance_needs_requirements.sysml"
REQUIREMENT = {
    "VC-DRIVING-036": ("REQ-DRIVING-036", f"{NR}:278"),
    "VC-DRIVING-037": ("REQ-DRIVING-037", f"{NR}:288"),
    "VC-DRIVING-038": ("REQ-DRIVING-038", f"{NR}:298"),
    "VC-DRIVING-040": ("REQ-DRIVING-040", f"{NR}:318"),
    "VC-DRIVING-041": ("REQ-DRIVING-041", f"{NR}:328"),
    "VC-DRIVING-042": ("REQ-DRIVING-042", f"{NR}:338"),
    "VC-DRIVING-043": ("REQ-DRIVING-043", f"{NR}:348"),
    "VC-DRIVING-044": ("REQ-DRIVING-044", f"{NR}:358"),
}
DROP_RULE = "MAP-DRIVING-DA-CAMERA-IMAGE; driver_assistance_verification_evidence.sysml:204-207"


def verdict(outcome: str) -> str:
    return VERDICT.get(outcome, "inconclusive")


def combine(outcomes: list[str], missing: list[str]) -> str:
    """The campaign rule: fail, else error, else blocked, else inconclusive (any missing evidence), else pass."""
    for o in (FAIL, ERROR, BLOCKED):
        if o in outcomes:
            return o
    if missing or INCONCLUSIVE in outcomes or not outcomes:
        return INCONCLUSIVE
    return PASS


def entry(run: Run, outcome: str, measured: dict | None = None, missing: list | None = None,
          notes: list | None = None) -> dict:
    return {"run": run.run_id, "setting": run.setting_id, "repetition": run.repetition, "outcome": outcome,
            "measured": measured or {}, "missing": missing or [], "notes": notes or []}


def guarded(fn, run: Run, *args) -> dict:
    """One run through a per-run evaluator: missing evidence and unreadable records become its outcome."""
    try:
        return fn(run, *args)
    except MissingEvidence as exc:
        return entry(run, INCONCLUSIVE, missing=[str(exc)])
    except EvidenceError as exc:
        return entry(run, ERROR, missing=[str(exc)])


def no_drop_in(run: Run, w0: float, w1: float) -> None:
    drops = run.drops_in(w0, w1)
    if drops:
        shown = ", ".join(f"{d['sim_s']:.3f}" for d in drops[:5]) + (" ..." if len(drops) > 5 else "")
        raise MissingEvidence(f"{run.label('score')}: {len(drops)} drop.camera_image at sim {shown} s inside the "
                              f"judged window {w0:.3f}-{w1:.3f} s ({DROP_RULE})")


def whole_run(run: Run) -> tuple[float, float]:
    """The judged window of a criterion over every run: the whole run, first to last world tick."""
    w0, w1 = run.run_span()
    no_drop_in(run, w0, w1)
    return w0, w1


def judged(run: Run) -> tuple[list, terms.SettingTerms, dict]:
    """The judged-run context of 036, 037 and 042; missing evidence when the run is not a judged run."""
    st = terms.SETTINGS.get(run.setting_id)
    if st is None:
        raise MissingEvidence(f"run {run.run_id}: unknown setting {run.setting_id!r}")
    ticks = run.ticks()
    jr = terms.judged_run(ticks, st)
    if not jr["judged"]:
        raise MissingEvidence(f"run {run.run_id} ({run.label('world')}) is not a judged run: "
                              + "; ".join(jr["missed"]))
    no_drop_in(run, *jr["windowS"])
    return ticks, st, jr


def last_command_at(cmds: list[dict], times: list[float], t: float) -> dict | None:
    i = bisect.bisect_right(times, t + 1e-9) - 1
    return cmds[i] if i >= 0 else None


def result(vc: str, outcome: str, runs: list, missing: list, thresholds: dict, notes: list | None = None,
           measured: dict | None = None) -> dict:
    req, clause = REQUIREMENT[vc]
    m = {"runs": runs}
    m.update(measured or {})
    return {"vc": vc, "requirement": req, "successClause": clause, "outcome": outcome, "verdict": verdict(outcome),
            "measured": m, "thresholds": thresholds, "missing": missing, "notes": notes or []}


def judged_settings_campaign(vc: str, sess: Session, per_run, thresholds: dict) -> dict:
    """036, 037, 042: every setting of SC-DRIVING-012 and -013 judged (both runs judged runs), each judged run met.
    A judged run that fails gives fail; a setting not judged gives inconclusive, never pass."""
    by = sess.by_setting()
    runs, missing = [], []
    for sid in terms.JUDGED_SETTINGS:
        have = by.get(sid, [])
        if len(have) != 2:
            missing.append(f"setting {sid}: {len(have)} run{'' if len(have) == 1 else 's'} of 2 (a setting is "
                           "judged when both of its runs are judged runs)")
        entries = [guarded(per_run, r) for r in have]
        runs += entries
        for e in entries:
            if e["outcome"] not in (PASS, FAIL):
                missing.append(f"setting {sid} not judged: run {e['run']}: " + "; ".join(e["missing"]))
    outcome = combine([e["outcome"] for e in runs], missing)
    return result(vc, outcome, runs, missing, thresholds)


# ------------------------------------------------------------------ VC-DRIVING-036
def run_036(run: Run) -> dict:
    ticks, st, jr = judged(run)
    fp = jr["functionalPart"]
    cmds = run.commands()
    if not cmds:
        raise MissingEvidence(f"{run.label('score')}: no out.driving_command ({run.run_id})")
    times = [c["issueTime_sim_s"] for c in cmds]
    instants, misses = 0, []
    for i in range(fp["startIndex"], fp["endIndex"] + 1):
        t = ticks[i]
        rel = t.get("relative") or {}
        needed = terms.needed_deceleration(rel.get("gapM"), rel.get("closingMps"))
        if needed is None or needed < terms.EMERGENCY_BRAKING_MPS2 - terms.EPS:
            continue
        instants += 1
        c = last_command_at(cmds, times, t["simTimeS"])
        if c is None or c["acceleration"] > -terms.EMERGENCY_BRAKING_MPS2 + terms.EPS:
            misses.append({"frame": t.get("frame"), "simTimeS": t["simTimeS"], "neededDecelMps2": needed,
                           "commandSeq": None if c is None else c["seq"],
                           "acceleration": None if c is None else c["acceleration"]})
    measured = {"instants": instants, "missedInstants": len(misses), "firstMiss": misses[0] if misses else None,
                "functionalPart": [fp["startSimS"], fp["endSimS"]], "endReason": fp["endReason"]}
    return entry(run, FAIL if misses else PASS, measured)


# ------------------------------------------------------------------ VC-DRIVING-037
def run_037(run: Run) -> dict:
    ticks, st, jr = judged(run)
    rs = terms.relative_speeds(ticks, jr["functionalPart"])
    measured = dict(rs, limitKmh=None)
    if rs["approachKmh"] is None:
        if rs["contact"]:
            raise MissingEvidence(f"run {run.run_id}: contact with the target at frame {rs['contactFrame']} with "
                                  "no imminent tick before it: no relative approach speed")
        return entry(run, PASS, measured, notes=["the collision never became imminent and the vehicles did not "
                                                 "touch: relative impact speed 0 km/h"])
    limit = terms.max_relative_impact_kmh(rs["approachKmh"])
    measured["limitKmh"] = limit
    if limit is None:
        raise MissingEvidence(f"run {run.run_id}: relative approach speed {rs['approachKmh']:.2f} km/h is above "
                              "60 km/h, where the model gives no maximum relative impact speed")
    if rs["impactKmh"] is None:
        raise MissingEvidence(f"run {run.run_id}: no closing speed on the tick before the contact")
    return entry(run, PASS if rs["impactKmh"] <= limit + terms.EPS else FAIL, measured)


# ------------------------------------------------------------------ VC-DRIVING-042
def run_042(run: Run) -> dict:
    ticks, st, jr = judged(run)
    fp = jr["functionalPart"]
    imminent = [ticks[i] for i in range(fp["startIndex"], fp["endIndex"] + 1)
                if terms.is_imminent((ticks[i].get("relative") or {}).get("gapM"),
                                     (ticks[i].get("relative") or {}).get("closingMps"))]
    if not imminent:
        return entry(run, PASS, {"imminent": False}, notes=["the collision never became imminent"])
    starts = [w for w in terms.warning_starts(run.warnings()) if w["issueTime_sim_s"] <= fp["endSimS"] + 1e-9]
    ebs = terms.emergency_braking_starts(run.commands())
    t_eb = min((c["issueTime_sim_s"] for c in ebs), default=None)
    measured = {"imminent": True, "firstImminentSimS": imminent[0]["simTimeS"], "warningStarts": len(starts),
                "firstWarningStartSimS": starts[0]["issueTime_sim_s"] if starts else None,
                "firstEmergencyBrakingSimS": t_eb, "leadS": None}
    if not starts:
        return entry(run, FAIL, measured, notes=["no warning request started although the collision became "
                                                 "imminent"])
    if t_eb is None:
        return entry(run, PASS, measured, notes=["the run has no emergency braking"])
    measured["leadS"] = t_eb - starts[0]["issueTime_sim_s"]
    ok = any(t_eb - w["issueTime_sim_s"] >= terms.WARNING_LEAD_S - 1e-6 for w in starts)
    return entry(run, PASS if ok else FAIL, measured)


THRESHOLDS = {
    "VC-DRIVING-036": {"neededDecelMps2AtLeast": 5.0, "commandAccelerationAtMost": -5.0},
    "VC-DRIVING-037": {"maxRelativeImpactKmh": [list(x) for x in terms.IMPACT_LIMITS_KMH],
                       "imminent": {"ttcSAtMost": 4.0, "neededDecelMps2AtLeast": 1.0}},
    "VC-DRIVING-042": {"warningLeadSAtLeast": 1.0, "emergencyBrakingMps2": 5.0,
                       "imminent": {"ttcSAtMost": 4.0, "neededDecelMps2AtLeast": 1.0}},
}

CASES = {
    "VC-DRIVING-036": lambda sess, desk: judged_settings_campaign("VC-DRIVING-036", sess, run_036,
                                                                 THRESHOLDS["VC-DRIVING-036"]),
    "VC-DRIVING-037": lambda sess, desk: judged_settings_campaign("VC-DRIVING-037", sess, run_037,
                                                                 THRESHOLDS["VC-DRIVING-037"]),
    "VC-DRIVING-042": lambda sess, desk: judged_settings_campaign("VC-DRIVING-042", sess, run_042,
                                                                 THRESHOLDS["VC-DRIVING-042"]),
}


def evaluate(session: Session, desk: dict | None = None) -> dict:
    """Every case on one session: {vc: result}."""
    return {vc: fn(session, desk) for vc, fn in CASES.items()}
